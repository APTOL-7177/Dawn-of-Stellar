"""RL 모델 평가 프레임워크

학습된 모델을 1000판 자동 평가하여 승률, 평균 턴, 직업별 성과,
스킬 다양성, BRV 관리 점수 등을 측정합니다.
"""

import numpy as np
from typing import Dict, List, Optional, Any
from collections import defaultdict
from src.core.logger import get_logger

logger = get_logger("rl.evaluation")

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from sb3_contrib import MaskablePPO
    HAS_SB3_CONTRIB = True
except ImportError:
    HAS_SB3_CONTRIB = False


def _compute_entropy(action_counts: Dict[int, int]) -> float:
    """행동 분포의 엔트로피 계산 (스킬 다양성 지표)"""
    total = sum(action_counts.values())
    if total == 0:
        return 0.0
    probs = np.array([c / total for c in action_counts.values()], dtype=np.float64)
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log(probs + 1e-10)))


class Evaluator:
    """1000판 자동 평가기

    평가 지표:
        - win_rate: 승률
        - avg_turns: 평균 전투 턴 수
        - avg_reward: 평균 누적 보상
        - job_win_rates: 직업별 승률 (플레이어 파티 직업 기준)
        - skill_diversity: 스킬 사용 엔트로피
        - brv_management_score: 브레이크 유발 - 브레이크 당한 횟수
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_episodes: int = 1000,
    ):
        self.model_path = model_path
        self.n_episodes = n_episodes
        self._model: Optional[Any] = None

    def _load_model(self) -> Optional[Any]:
        """SB3 모델 로드"""
        if self.model_path is None:
            return None

        import os
        if not os.path.exists(self.model_path) and not os.path.exists(self.model_path + ".zip"):
            logger.warning(f"모델 파일 없음: {self.model_path}")
            return None

        if not HAS_SB3_CONTRIB:
            logger.warning("sb3-contrib 미설치 - 평가 불가")
            return None

        model = MaskablePPO.load(self.model_path)
        logger.info(f"평가용 모델 로드: {self.model_path}")
        return model

    def evaluate(self) -> Dict[str, Any]:
        """전체 평가 실행

        Returns:
            평가 결과 딕셔너리:
            {
                "win_rate": float,
                "avg_turns": float,
                "avg_reward": float,
                "job_win_rates": Dict[str, float],
                "skill_diversity": float,
                "brv_management_score": float,
                "n_episodes": int,
                "n_wins": int,
            }
        """
        from src.gym.combat_env import CombatEnv

        model = self._load_model()
        env = CombatEnv()

        wins = 0
        total_turns = 0
        total_reward = 0.0
        job_wins: Dict[str, int] = defaultdict(int)
        job_games: Dict[str, int] = defaultdict(int)
        action_counts: Dict[int, int] = defaultdict(int)
        brv_score_total = 0.0

        logger.info(f"평가 시작: {self.n_episodes}판")

        for ep in range(self.n_episodes):
            episode_result = self.evaluate_single(env, model)

            if episode_result.get("won", False):
                wins += 1

            total_turns += episode_result.get("turns", 0)
            total_reward += episode_result.get("total_reward", 0.0)
            brv_score_total += episode_result.get("brv_management_score", 0.0)

            # 직업별 집계
            for job_id in episode_result.get("player_jobs", []):
                job_games[job_id] += 1
                if episode_result.get("won", False):
                    job_wins[job_id] += 1

            # 행동 분포 집계
            for action_id, count in episode_result.get("action_counts", {}).items():
                action_counts[action_id] += count

            if (ep + 1) % 100 == 0:
                logger.info(f"평가 진행: {ep+1}/{self.n_episodes}판 (현재 승률={wins/(ep+1):.3f})")

        env.close()

        # 직업별 승률 계산
        job_win_rates: Dict[str, float] = {}
        for job_id, games in job_games.items():
            job_win_rates[job_id] = job_wins[job_id] / games if games > 0 else 0.0

        results = {
            "win_rate": wins / self.n_episodes,
            "avg_turns": total_turns / self.n_episodes,
            "avg_reward": total_reward / self.n_episodes,
            "job_win_rates": job_win_rates,
            "skill_diversity": _compute_entropy(action_counts),
            "brv_management_score": brv_score_total / self.n_episodes,
            "n_episodes": self.n_episodes,
            "n_wins": wins,
        }

        logger.info(
            f"평가 완료: 승률={results['win_rate']:.3f}, "
            f"평균턴={results['avg_turns']:.1f}, "
            f"평균보상={results['avg_reward']:.2f}"
        )
        return results

    def evaluate_single(self, env: Any, model: Optional[Any]) -> Dict[str, Any]:
        """단일 에피소드 평가

        Args:
            env: CombatEnv 인스턴스
            model: MaskablePPO 모델 (None이면 랜덤 행동)

        Returns:
            단일 에피소드 결과 딕셔너리
        """
        obs, info = env.reset()
        terminated = False
        truncated = False
        total_reward = 0.0
        turns = 0
        action_counts: Dict[int, int] = defaultdict(int)
        breaks_caused = 0
        breaks_received = 0

        # 플레이어 직업 정보 추출
        player_jobs: List[str] = info.get("player_jobs", [])

        while not terminated and not truncated:
            if model is not None and hasattr(env, "action_masks"):
                action_masks = env.action_masks()
                action, _ = model.predict(
                    obs,
                    action_masks=action_masks,
                    deterministic=True,
                )
            else:
                # 랜덤 유효 행동 선택 (모델 없을 때)
                if hasattr(env, "action_masks"):
                    mask = env.action_masks()
                    valid_actions = np.where(mask)[0]
                    action = int(np.random.choice(valid_actions)) if len(valid_actions) > 0 else 0
                else:
                    action = env.action_space.sample()

            obs, reward, terminated, truncated, step_info = env.step(action)
            total_reward += float(reward)
            turns += 1
            action_counts[int(action)] += 1

            # BRV 관리 점수 집계
            breaks_caused += step_info.get("breaks_caused", 0)
            breaks_received += step_info.get("breaks_received", 0)

        won = info.get("player_won", False) or step_info.get("player_won", False)

        return {
            "won": won,
            "turns": turns,
            "total_reward": total_reward,
            "action_counts": dict(action_counts),
            "player_jobs": player_jobs,
            "brv_management_score": float(breaks_caused - breaks_received),
        }

    def report(self, results: Dict[str, Any]) -> str:
        """평가 결과 리포트 생성

        Args:
            results: evaluate()의 반환값

        Returns:
            사람이 읽을 수 있는 리포트 문자열
        """
        lines = [
            "=" * 50,
            "Dawn of Stellar RL 모델 평가 결과",
            "=" * 50,
            f"총 에피소드: {results.get('n_episodes', 0)}판",
            f"승리:        {results.get('n_wins', 0)}판",
            f"승률:        {results.get('win_rate', 0.0):.1%}",
            f"평균 턴:     {results.get('avg_turns', 0.0):.1f}턴",
            f"평균 보상:   {results.get('avg_reward', 0.0):.3f}",
            f"스킬 다양성: {results.get('skill_diversity', 0.0):.3f} (엔트로피)",
            f"BRV 관리:    {results.get('brv_management_score', 0.0):.2f} (유발-당함)",
            "",
            "직업별 승률:",
        ]

        job_win_rates = results.get("job_win_rates", {})
        if job_win_rates:
            for job_id, rate in sorted(job_win_rates.items(), key=lambda x: -x[1]):
                lines.append(f"  {job_id:<20}: {rate:.1%}")
        else:
            lines.append("  (데이터 없음)")

        lines.append("=" * 50)
        return "\n".join(lines)
