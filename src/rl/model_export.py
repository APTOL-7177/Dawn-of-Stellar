"""SB3 모델 -> TorchScript 변환 (게임 추론용, SB3 의존성 없음)

훈련된 SB3 MaskablePPO 모델을 TorchScript로 변환하여
게임 런타임에서 SB3 없이 추론할 수 있도록 합니다.
"""

import os
from typing import Optional, Any
from pathlib import Path
from src.core.logger import get_logger

logger = get_logger("rl.model_export")


class _PolicyWrapper:
    """SB3 정책을 TorchScript 추적용 래퍼로 변환 (내부 사용)"""
    pass


class ModelExporter:
    """모델 내보내기

    SB3 MaskablePPO(.zip) -> TorchScript(.pt) 변환을 담당합니다.
    변환된 .pt 파일은 SB3 없이 torch.jit.load()로 로드 가능합니다.
    """

    @staticmethod
    def export_torchscript(
        sb3_model_path: str,
        output_path: str = "data/models/combat_agent.pt",
        observation_dim: int = 517,
        action_dim: int = 114,
    ) -> str:
        """SB3 모델을 TorchScript로 변환

        Args:
            sb3_model_path: SB3 모델 경로 (.zip)
            output_path: TorchScript 출력 경로 (.pt)
            observation_dim: 관측 공간 차원 (기본: 517)
            action_dim: 행동 공간 차원 (기본: 114)

        Returns:
            저장된 TorchScript 파일 경로

        Raises:
            ImportError: torch 또는 sb3-contrib 미설치
            FileNotFoundError: 모델 파일 없음
        """
        try:
            import torch
        except ImportError:
            raise ImportError("PyTorch가 필요합니다: pip install torch")

        try:
            from sb3_contrib import MaskablePPO
        except ImportError:
            raise ImportError("sb3-contrib가 필요합니다: pip install sb3-contrib")

        # 모델 경로 정규화 (.zip 확장자 처리)
        model_path = Path(sb3_model_path)
        if not model_path.exists() and not model_path.with_suffix(".zip").exists():
            if not str(sb3_model_path).endswith(".zip"):
                model_path = model_path.with_suffix(".zip")
            if not model_path.exists():
                raise FileNotFoundError(f"SB3 모델 파일 없음: {sb3_model_path}")

        logger.info(f"SB3 모델 로드: {model_path}")
        sb3_model = MaskablePPO.load(str(model_path))

        # 정책 네트워크 추출
        policy = sb3_model.policy
        policy.eval()
        policy.set_training_mode(False)

        # TorchScript 추적용 래퍼 클래스
        class PolicyForwardWrapper(torch.nn.Module):
            """행동 로짓 반환 래퍼 (action_masks 없이 로짓만 반환)"""

            def __init__(self, inner_policy: Any):
                super().__init__()
                self.features_extractor = inner_policy.features_extractor
                self.mlp_extractor = inner_policy.mlp_extractor
                self.action_net = inner_policy.action_net

            def forward(self, obs: torch.Tensor) -> torch.Tensor:
                """관측값 -> 행동 로짓 반환"""
                features = self.features_extractor(obs)
                latent_pi, _ = self.mlp_extractor(features)
                return self.action_net(latent_pi)

        wrapper = PolicyForwardWrapper(policy)
        wrapper.eval()

        # 모델이 있는 디바이스 감지 후 CPU로 이동 (TorchScript 호환성)
        device = next(wrapper.parameters()).device
        wrapper = wrapper.cpu()

        # 더미 입력으로 TorchScript 추적
        dummy_obs = torch.zeros(1, observation_dim, dtype=torch.float32)
        logger.info("TorchScript 추적 중...")

        try:
            traced = torch.jit.trace(wrapper, dummy_obs)
        except Exception as e:
            logger.warning(f"trace 실패, script 방식으로 재시도: {e}")
            traced = torch.jit.script(wrapper)

        # 검증: 더미 입력으로 순전파 확인
        with torch.no_grad():
            test_out = traced(dummy_obs)
        if test_out.shape != (1, action_dim):
            logger.warning(
                f"출력 shape 불일치: {test_out.shape} (기대: (1, {action_dim})). "
                "내보내기 계속 진행합니다."
            )

        # 저장
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        traced.save(str(out_path))

        file_size_mb = out_path.stat().st_size / (1024 * 1024)
        logger.info(f"TorchScript 저장 완료: {out_path} ({file_size_mb:.1f} MB)")
        return str(out_path)

    @staticmethod
    def load_torchscript(path: str) -> Any:
        """TorchScript 모델 로드 (추론용)

        Args:
            path: TorchScript 파일 경로 (.pt)

        Returns:
            로드된 TorchScript 모델

        Raises:
            ImportError: PyTorch 미설치
            FileNotFoundError: 파일 없음
        """
        try:
            import torch
        except ImportError:
            raise ImportError("PyTorch가 필요합니다: pip install torch")

        load_path = Path(path)
        if not load_path.exists():
            raise FileNotFoundError(f"TorchScript 파일 없음: {path}")

        model = torch.jit.load(str(load_path), map_location="cpu")
        model.eval()
        logger.info(f"TorchScript 모델 로드: {load_path}")
        return model
