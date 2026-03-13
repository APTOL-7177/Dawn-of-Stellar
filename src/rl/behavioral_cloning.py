"""행동 복제 (Behavioral Cloning) - LLM 플레이 로그로 사전 학습

LLM이 생성한 플레이 로그에서 전문가 행동을 학습하여
PPO 훈련의 초기 정책을 제공합니다.
"""

import json
import os
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from src.core.logger import get_logger

logger = get_logger("rl.behavioral_cloning")

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    Dataset = object  # 타입 힌트용 더미


class PlayLogDataset(Dataset if HAS_TORCH else object):
    """플레이 로그 데이터셋

    data/play_logs/ 디렉토리의 JSONL 파일을 로드합니다.
    각 레코드 형식: {"state": [...], "action": int, "reward": float, ...}
    """

    def __init__(self, states: np.ndarray, actions: np.ndarray):
        """
        Args:
            states: 상태 배열 (N, 517)
            actions: 행동 배열 (N,)
        """
        if not HAS_TORCH:
            raise ImportError("PyTorch가 필요합니다: pip install torch")

        import torch
        self.states = torch.FloatTensor(states)
        self.actions = torch.LongTensor(actions)

    def __len__(self) -> int:
        return len(self.states)

    def __getitem__(self, idx: int) -> Tuple["torch.Tensor", "torch.Tensor"]:
        return self.states[idx], self.actions[idx]


class BehavioralCloning:
    """행동 복제 학습기

    LLM 플레이 로그에서 상태-행동 쌍을 추출하여
    교차 엔트로피 손실로 정책 네트워크를 사전 학습합니다.
    """

    OBSERVATION_DIM = 517
    NUM_ACTIONS = 114

    def __init__(
        self,
        log_dir: str = "data/play_logs",
        model_dir: str = "data/models",
    ):
        self.log_dir = Path(log_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self._model: Optional[Any] = None
        self._trained = False

    def _build_model(self) -> "nn.Module":
        """BC용 간단한 정책 네트워크 생성"""
        if not HAS_TORCH:
            raise ImportError("PyTorch가 필요합니다: pip install torch")

        import torch.nn as nn_module
        return nn_module.Sequential(
            nn_module.Linear(self.OBSERVATION_DIM, 256),
            nn_module.ReLU(),
            nn_module.Linear(256, 256),
            nn_module.ReLU(),
            nn_module.Linear(256, self.NUM_ACTIONS),
        )

    def load_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """플레이 로그 로드 -> (states, actions) 배열

        Returns:
            states: (N, 517) float32 배열
            actions: (N,) int64 배열
        """
        states_list: List[np.ndarray] = []
        actions_list: List[int] = []

        if not self.log_dir.exists():
            logger.warning(f"플레이 로그 디렉토리 없음: {self.log_dir}")
            return np.empty((0, self.OBSERVATION_DIM), dtype=np.float32), np.empty(0, dtype=np.int64)

        log_files = list(self.log_dir.glob("*.jsonl"))
        if not log_files:
            logger.warning(f"JSONL 로그 파일 없음: {self.log_dir}")
            return np.empty((0, self.OBSERVATION_DIM), dtype=np.float32), np.empty(0, dtype=np.int64)

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        record = json.loads(line)
                        state = record.get("state")
                        action_raw = record.get("action")
                        if state is None or action_raw is None:
                            continue
                        # action이 dict인 경우 action_id 추출
                        if isinstance(action_raw, dict):
                            action = action_raw.get("action_id")
                            if action is None:
                                continue
                        else:
                            action = action_raw
                        action = int(action)
                        if len(state) != self.OBSERVATION_DIM:
                            logger.warning(f"잘못된 상태 차원: {len(state)} (기대: {self.OBSERVATION_DIM})")
                            continue
                        if not (0 <= action < self.NUM_ACTIONS):
                            logger.warning(f"잘못된 행동 인덱스: {action}")
                            continue
                        states_list.append(np.array(state, dtype=np.float32))
                        actions_list.append(action)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"로그 파일 파싱 오류 ({log_file.name}): {e}")

        if not states_list:
            logger.warning("유효한 플레이 로그 데이터 없음")
            return np.empty((0, self.OBSERVATION_DIM), dtype=np.float32), np.empty(0, dtype=np.int64)

        states = np.stack(states_list, axis=0)
        actions = np.array(actions_list, dtype=np.int64)
        logger.info(f"플레이 로그 로드 완료: {len(states)}개 샘플, {len(log_files)}개 파일")
        return states, actions

    def train(
        self,
        epochs: int = 50,
        batch_size: int = 256,
        lr: float = 1e-3,
    ) -> Dict[str, Any]:
        """BC 학습 실행

        Args:
            epochs: 학습 에폭 수
            batch_size: 미니배치 크기
            lr: 학습률

        Returns:
            {"loss": float, "accuracy": float, "epochs": int}
        """
        if not HAS_TORCH:
            raise ImportError("PyTorch가 필요합니다: pip install torch")

        import torch
        import torch.nn as nn_module

        states, actions = self.load_data()
        if len(states) == 0:
            logger.error("학습 데이터 없음 - BC 학습 불가")
            return {"loss": float("inf"), "accuracy": 0.0, "epochs": 0}

        dataset = PlayLogDataset(states, actions)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self._model = self._build_model()
        optimizer = torch.optim.Adam(self._model.parameters(), lr=lr)
        criterion = nn_module.CrossEntropyLoss()

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(device)
        logger.info(f"BC 학습 시작: {len(states)}샘플, {epochs}에폭, 디바이스={device}")

        final_loss = 0.0
        final_acc = 0.0

        for epoch in range(epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0

            self._model.train()
            for batch_states, batch_actions in dataloader:
                batch_states = batch_states.to(device)
                batch_actions = batch_actions.to(device)

                optimizer.zero_grad()
                logits = self._model(batch_states)
                loss = criterion(logits, batch_actions)
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item() * len(batch_states)
                preds = torch.argmax(logits, dim=-1)
                correct += (preds == batch_actions).sum().item()
                total += len(batch_states)

            avg_loss = epoch_loss / total
            accuracy = correct / total

            if (epoch + 1) % 10 == 0:
                logger.info(f"에폭 [{epoch+1}/{epochs}] 손실={avg_loss:.4f} 정확도={accuracy:.3f}")

            final_loss = avg_loss
            final_acc = accuracy

        self._trained = True
        result = {"loss": final_loss, "accuracy": final_acc, "epochs": epochs}
        logger.info(f"BC 학습 완료: {result}")
        return result

    def get_pretrained_weights(self) -> Dict[str, Any]:
        """학습된 가중치 반환 (SB3 policy 초기화용)

        Returns:
            state_dict: torch 가중치 딕셔너리
        """
        if not self._trained or self._model is None:
            raise RuntimeError("먼저 train()을 실행하세요")
        return self._model.state_dict()

    def save(self, path: str = "data/models/bc_weights.pt") -> None:
        """모델 가중치 저장"""
        if not HAS_TORCH:
            raise ImportError("PyTorch가 필요합니다")
        import torch
        if self._model is None:
            raise RuntimeError("저장할 모델이 없습니다. train()을 먼저 실행하세요.")
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.state_dict(), save_path)
        logger.info(f"BC 가중치 저장: {save_path}")

    def load(self, path: str = "data/models/bc_weights.pt") -> None:
        """저장된 가중치 로드"""
        if not HAS_TORCH:
            raise ImportError("PyTorch가 필요합니다")
        import torch
        load_path = Path(path)
        if not load_path.exists():
            raise FileNotFoundError(f"가중치 파일 없음: {load_path}")
        self._model = self._build_model()
        self._model.load_state_dict(torch.load(load_path, map_location="cpu"))
        self._trained = True
        logger.info(f"BC 가중치 로드: {load_path}")
