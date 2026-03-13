"""커스텀 신경망 - 직업 임베딩 + 공유 백본"""

import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    nn = object  # 타입 힌트용 더미

# SB3 임포트는 선택적 (훈련 전용)
try:
    from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
    HAS_SB3 = True
except ImportError:
    if HAS_TORCH:
        import torch.nn as nn
        BaseFeaturesExtractor = nn.Module
    else:
        BaseFeaturesExtractor = object
    HAS_SB3 = False


def _make_base_class():
    """PyTorch 2.8+ 호환성을 위한 동적 베이스 클래스 생성"""
    if HAS_SB3:
        return BaseFeaturesExtractor
    elif HAS_TORCH:
        import torch.nn as nn_module
        return nn_module.Module
    else:
        return object

_BaseClass = _make_base_class()


class JobEmbeddingExtractor(_BaseClass):
    """직업 임베딩 + 공유 백본 특성 추출기

    관측 공간(517차원)에서 직업 원-핫 인코딩을 임베딩으로 대체하여
    파라미터 효율적인 특성 추출을 수행합니다.

    관측 벡터 구조:
        - 전투원 8명 × 64차원 = 512차원
          - [0:3]   HP/MP/BRV 비율
          - [3:6]   ATB/생존/브레이크 상태
          - [6:41]  직업 원-핫 (35개 직업)
          - [41:64] 기타 전투원 특성
        - 글로벌 특성 5차원 (전투 페이즈, 팀 BRV 등)
    """

    OBSERVATION_DIM = 517
    NUM_JOBS = 35
    JOB_EMBEDDING_DIM = 16
    JOB_ONEHOT_START = 6   # HP/MP/BRV 비율(3) + ATB/생존/브레이크(3) 이후
    JOB_ONEHOT_END = 6 + 35  # = 41
    FEATURES_PER_COMBATANT = 64
    NUM_COMBATANTS = 8
    GLOBAL_FEATURES = 5

    def __init__(self, observation_space, features_dim: int = 512):
        if HAS_SB3:
            super().__init__(observation_space, features_dim)
        elif HAS_TORCH:
            super().__init__()

        if not HAS_TORCH:
            raise ImportError("PyTorch가 필요합니다: pip install torch")

        import torch.nn as nn_module

        # 직업 임베딩 (전체 전투원 공유)
        self.job_embedding = nn_module.Embedding(self.NUM_JOBS, self.JOB_EMBEDDING_DIM)

        # 원-핫 대체 후 전투원당 특성 차원:
        # 64 - 35(원-핫) + 16(임베딩) = 45
        combatant_feature_dim = (
            self.FEATURES_PER_COMBATANT - self.NUM_JOBS + self.JOB_EMBEDDING_DIM
        )

        # 입력 차원: 8전투원 × 45 + 5 글로벌 = 365
        input_dim = self.NUM_COMBATANTS * combatant_feature_dim + self.GLOBAL_FEATURES

        self.shared_backbone = nn_module.Sequential(
            nn_module.Linear(input_dim, features_dim),
            nn_module.ReLU(),
            nn_module.Linear(features_dim, features_dim),
            nn_module.ReLU(),
        )

        self._features_dim = features_dim

    def forward(self, observations: "torch.Tensor") -> "torch.Tensor":
        """순전파: 관측값 -> 특성 벡터 (벡터화 — for-loop 제거)"""
        B = observations.shape[0]
        C = self.NUM_COMBATANTS
        F = self.FEATURES_PER_COMBATANT

        # (B, 512) → (B, 8, 64): 전투원별로 reshape
        combatants = observations[:, :C * F].reshape(B, C, F)

        # 직업 원-핫 → 임베딩 (배치 전체 한 번에)
        job_onehot = combatants[:, :, self.JOB_ONEHOT_START:self.JOB_ONEHOT_END]  # (B, 8, 35)
        job_idx = torch.argmax(job_onehot, dim=-1)  # (B, 8)
        job_emb = self.job_embedding(job_idx)        # (B, 8, 16)

        # 비-직업 특성 추출 및 임베딩 결합
        non_job = torch.cat([
            combatants[:, :, :self.JOB_ONEHOT_START],
            combatants[:, :, self.JOB_ONEHOT_END:],
        ], dim=-1)  # (B, 8, 29)
        combined = torch.cat([non_job, job_emb], dim=-1)  # (B, 8, 45)

        # (B, 8, 45) → (B, 360) + 글로벌 5 = (B, 365)
        global_features = observations[:, C * F:]  # (B, 5)
        all_features = torch.cat([combined.reshape(B, -1), global_features], dim=-1)

        return self.shared_backbone(all_features)
