"""PPO 훈련 - MaskablePPO + 행동 마스킹

sb3-contrib의 MaskablePPO를 사용하여 유효한 행동만 선택하도록
행동 마스킹이 적용된 PPO 에이전트를 훈련합니다.
"""

import os
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from src.core.logger import get_logger

logger = get_logger("rl.ppo_trainer")


class _LinearSchedule:
    """pickle 가능한 선형 LR 감소 스케줄 (클로저 대신 사용)"""

    def __init__(self, initial_lr: float, min_ratio: float = 0.1):
        self.initial_lr = initial_lr
        self.min_ratio = min_ratio

    def __call__(self, progress_remaining: float) -> float:
        return self.initial_lr * max(progress_remaining, self.min_ratio)

try:
    from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
    from stable_baselines3.common.callbacks import (
        CheckpointCallback,
        EvalCallback,
        BaseCallback,
    )
    HAS_SB3_BASE = True
except ImportError:
    HAS_SB3_BASE = False

try:
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
    HAS_SB3_CONTRIB = True
except ImportError:
    HAS_SB3_CONTRIB = False

HAS_SB3 = HAS_SB3_BASE and HAS_SB3_CONTRIB


if HAS_SB3_BASE:
    import time as _time

    class _ProgressCallback(BaseCallback):
        """초 단위 진행 상황 출력 콜백"""

        def __init__(self, interval: float = 1.0, total_timesteps: int = 0, verbose: int = 0):
            super().__init__(verbose)
            self.interval = interval
            self.total_target = total_timesteps
            self._last_time = 0.0
            self._last_steps = 0
            self._start_time = 0.0

        def _on_training_start(self) -> None:
            self._start_time = _time.time()
            self._last_time = self._start_time
            self._last_steps = 0

        def _on_step(self) -> bool:
            now = _time.time()
            if now - self._last_time >= self.interval:
                steps = self.num_timesteps
                elapsed = now - self._start_time
                recent_fps = (steps - self._last_steps) / max(now - self._last_time, 0.01)
                avg_fps = steps / max(elapsed, 0.01)
                pct = steps / max(self.total_target, 1) * 100

                eta_sec = (self.total_target - steps) / max(avg_fps, 1)
                eta_h = int(eta_sec // 3600)
                eta_m = int((eta_sec % 3600) // 60)

                print(
                    f"\r[{pct:5.1f}%] {steps:,}/{self.total_target:,} "
                    f"| fps: {int(recent_fps):,} (avg {int(avg_fps):,}) "
                    f"| ETA: {eta_h}h{eta_m:02d}m",
                    end="", flush=True
                )
                self._last_time = now
                self._last_steps = steps
            return True

        def _on_training_end(self) -> None:
            elapsed = _time.time() - self._start_time
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            print(f"\n[DONE] {self.num_timesteps:,} steps in {h}h{m:02d}m")
else:
    class _ProgressCallback:
        pass


def _make_env_factory(rank: int) -> Callable:
    """환경 팩토리 함수 생성 (SubprocVecEnv용)"""
    def _init():
        import traceback as _tb
        try:
            from src.gym.combat_env import CombatEnv
            env = CombatEnv()
            env.reset(seed=rank)
            return env
        except Exception as e:
            logger.error(f"[env#{rank}] 환경 생성 실패: {e}\n{_tb.format_exc()}")
            raise
    return _init


class PPOTrainer:
    """PPO 훈련 관리자

    MaskablePPO와 JobEmbeddingExtractor를 결합하여
    Dawn of Stellar 전투 AI를 훈련합니다.

    BC 사전 학습 가중치를 제공하면 웜스타트(warm-start)를 수행합니다.
    """

    DEFAULT_POLICY_KWARGS = {
        "net_arch": [512, 512],
        "share_features_extractor": True,
    }

    def __init__(
        self,
        n_envs: int = 8,
        total_timesteps: int = 5_000_000,
        learning_rate: float = 3e-4,
        n_steps: int = 1024,
        batch_size: int = 2048,
        n_epochs: int = 5,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        ent_coef: float = 0.01,
        model_dir: str = "data/models",
        log_dir: str = "data/rl_logs",
        bc_weights_path: Optional[str] = None,
        device: str = "auto",
    ):
        self.n_envs = n_envs
        self.total_timesteps = total_timesteps
        self.learning_rate = learning_rate
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.ent_coef = ent_coef
        self.model_dir = Path(model_dir)
        self.log_dir = Path(log_dir)
        self.bc_weights_path = bc_weights_path
        self.device = device

        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._model: Optional[Any] = None
        self._vec_env: Optional[Any] = None

    def _make_env(self) -> Callable:
        """단일 환경 팩토리 반환"""
        def _init():
            from src.gym.combat_env import CombatEnv
            return CombatEnv()
        return _init

    @staticmethod
    def _raise_fd_limit(n_envs: int) -> None:
        """SubprocVecEnv에 필요한 만큼 파일 디스크립터 한도를 올립니다."""
        import sys
        if sys.platform == "win32":
            return
        try:
            import resource
            needed = max(4096, n_envs * 4 + 512)
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            if soft < needed:
                target = min(needed, hard)
                resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
                logger.info(f"FD 한도 조정: {soft} → {target} (필요: {needed})")
        except Exception as e:
            logger.warning(f"FD 한도 조정 실패: {e} — ulimit -n 65536 권장")

    def setup(self) -> None:
        """훈련 환경 및 모델 설정

        - SubprocVecEnv로 병렬 환경 생성
        - MaskablePPO + JobEmbeddingExtractor 구성
        - BC 가중치가 있으면 웜스타트 적용
        """
        if not HAS_SB3:
            raise ImportError(
                "SB3 및 sb3-contrib가 필요합니다:\n"
                "pip install stable-baselines3 sb3-contrib"
            )

        from src.rl.network import JobEmbeddingExtractor

        logger.info(f"훈련 환경 설정: {self.n_envs}개 병렬 환경")

        # SubprocVecEnv는 환경당 소켓 페어가 필요하므로 FD 한도를 올림
        self._raise_fd_limit(self.n_envs)

        # n_envs > 1이면 SubprocVecEnv, 단일 환경은 DummyVecEnv
        env_fns = [_make_env_factory(i) for i in range(self.n_envs)]
        if self.n_envs > 1:
            self._vec_env = SubprocVecEnv(env_fns)
        else:
            self._vec_env = DummyVecEnv(env_fns)

        policy_kwargs = {
            **self.DEFAULT_POLICY_KWARGS,
            "features_extractor_class": JobEmbeddingExtractor,
            "features_extractor_kwargs": {"features_dim": 512},
        }

        # device 결정: "auto"면 CUDA 우선, 명시적 지정도 가능
        device = self.device
        if device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    gpu_name = torch.cuda.get_device_name(0)
                    props = torch.cuda.get_device_properties(0)
                    vram_gb = (getattr(props, "total_memory", 0) or getattr(props, "total_mem", 0)) / (1024**3)
                    logger.info(f"GPU 감지: {gpu_name} ({vram_gb:.1f} GB) — CUDA 사용")
                else:
                    device = "cpu"
                    logger.info("GPU 없음 — CPU 모드")
            except ImportError:
                device = "cpu"

        self._model = MaskablePPO(
            policy="MlpPolicy",
            env=self._vec_env,
            learning_rate=_LinearSchedule(self.learning_rate),
            n_steps=self.n_steps,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            gamma=self.gamma,
            gae_lambda=self.gae_lambda,
            ent_coef=self.ent_coef,
            tensorboard_log=str(self.log_dir),
            policy_kwargs=policy_kwargs,
            device=device,
            verbose=1,
        )

        # BC 가중치 웜스타트
        if self.bc_weights_path and Path(self.bc_weights_path).exists():
            self._apply_bc_weights(self.bc_weights_path)
        elif self.bc_weights_path:
            logger.warning(f"BC 가중치 파일 없음: {self.bc_weights_path} - 랜덤 초기화")

        logger.info("PPO 모델 설정 완료")

    def _apply_bc_weights(self, bc_path: str) -> None:
        """BC 사전 학습 가중치를 PPO 정책에 적용 (호환 레이어만)"""
        import torch
        bc_state = torch.load(bc_path, map_location="cpu")
        policy_state = self._model.policy.state_dict()

        matched = 0
        for key, value in bc_state.items():
            # BC 네트워크 레이어를 PPO 정책 mlp_extractor에 매핑 시도
            mapped_key = f"mlp_extractor.policy_net.{key}"
            if mapped_key in policy_state and policy_state[mapped_key].shape == value.shape:
                policy_state[mapped_key] = value
                matched += 1

        self._model.policy.load_state_dict(policy_state, strict=False)
        logger.info(f"BC 웜스타트 적용: {matched}개 레이어 로드 ({bc_path})")

    def train(self) -> str:
        """훈련 실행

        Returns:
            최종 모델 저장 경로
        """
        if self._model is None:
            raise RuntimeError("먼저 setup()을 실행하세요")

        checkpoint_path = str(self.model_dir / "checkpoints")
        os.makedirs(checkpoint_path, exist_ok=True)

        callbacks = []

        # 초 단위 진행 상황 출력
        if HAS_SB3_BASE:
            progress_cb = _ProgressCallback(
                interval=1.0,
                total_timesteps=self.total_timesteps,
            )
            callbacks.append(progress_cb)

        # 체크포인트 콜백: 100k 스텝마다 저장
        if HAS_SB3_BASE:
            checkpoint_cb = CheckpointCallback(
                save_freq=max(100_000 // self.n_envs, 1),
                save_path=checkpoint_path,
                name_prefix="ppo_combat",
                verbose=1,
            )
            callbacks.append(checkpoint_cb)

        logger.info(
            f"PPO 훈련 시작: {self.total_timesteps:,}스텝, "
            f"{self.n_envs}환경, 체크포인트={checkpoint_path}"
        )

        self._model.learn(
            total_timesteps=self.total_timesteps,
            callback=callbacks if callbacks else None,
            progress_bar=False,
        )

        final_path = str(self.model_dir / "ppo_final.zip")
        self._model.save(final_path)
        logger.info(f"PPO 훈련 완료 - 모델 저장: {final_path}")
        return final_path

    def resume(self, model_path: str) -> None:
        """체크포인트에서 훈련 재개

        Args:
            model_path: 저장된 모델 경로 (.zip)
        """
        if not HAS_SB3:
            raise ImportError("SB3 및 sb3-contrib가 필요합니다")

        if self._vec_env is None:
            env_fns = [_make_env_factory(i) for i in range(self.n_envs)]
            self._vec_env = SubprocVecEnv(env_fns) if self.n_envs > 1 else DummyVecEnv(env_fns)

        self._model = MaskablePPO.load(model_path, env=self._vec_env)
        logger.info(f"체크포인트에서 훈련 재개: {model_path}")

    def save(self, path: Optional[str] = None) -> str:
        """모델 저장

        Args:
            path: 저장 경로 (None이면 기본 경로 사용)

        Returns:
            실제 저장된 경로
        """
        if self._model is None:
            raise RuntimeError("저장할 모델이 없습니다")

        save_path = path or str(self.model_dir / "ppo_manual_save.zip")
        self._model.save(save_path)
        logger.info(f"모델 수동 저장: {save_path}")
        return save_path
