"""
Dawn of Stellar 전투 Gymnasium 환경

ATB+BRV 전투 시스템을 Gymnasium 표준 인터페이스로 래핑합니다.
gymnasium이 설치되지 않은 경우 gracefully 폴백합니다.
"""

from typing import Any, Dict, Optional, Tuple

import numpy as np

from src.core.logger import get_logger
from src.gym.headless_combat import HeadlessCombat
from src.gym.state_encoder import StateEncoder
from src.gym.action_space import ActionSpaceEncoder
from src.gym.reward_shaper import RewardShaper
from src.gym.episode_manager import EpisodeManager

logger = get_logger("gym.combat_env")

# 스킬 초기화 (프로세스당 한 번만)
_skills_initialized = False


def _ensure_skills():
    """Python 기반 스킬이 SkillManager에 등록되어 있는지 확인"""
    global _skills_initialized
    if _skills_initialized:
        return
    try:
        from src.character.skills.skill_initializer import initialize_all_skills
        initialize_all_skills()
        _skills_initialized = True
        logger.debug("스킬 초기화 완료 (CombatEnv)")
    except Exception as e:
        logger.warning(f"스킬 초기화 실패: {e}")


# gymnasium 선택적 임포트
try:
    import gymnasium
    from gymnasium import spaces
    _GYM_AVAILABLE = True
    _BaseEnv = gymnasium.Env
except ImportError:
    _GYM_AVAILABLE = False
    # gymnasium 미설치 시 더미 베이스 클래스
    class _BaseEnv:  # type: ignore
        """gymnasium 미설치 시 더미 베이스"""
        def reset(self, seed=None, options=None):
            raise NotImplementedError
        def step(self, action):
            raise NotImplementedError
        def render(self):
            pass
        def close(self):
            pass

    class spaces:  # type: ignore
        """더미 spaces 네임스페이스"""
        @staticmethod
        def Box(**kwargs):
            return None
        @staticmethod
        def Discrete(n):
            return n

    logger.warning("gymnasium 미설치. CombatEnv는 더미 모드로 동작합니다.")


# 최대 ATB 틱 (무한 루프 방지)
_MAX_ATB_TICKS = 10000


class CombatEnv(_BaseEnv):
    """
    Dawn of Stellar 전투 Gymnasium 환경

    observation_space: Box(0.0, 1.0, shape=(517,), dtype=float32)
    action_space: Discrete(114)

    에피소드 흐름:
        reset() -> 새 전투 시작, 첫 아군 턴까지 ATB 진행
        step(action_id) -> 행동 실행, 적 턴 자동 처리, 다음 아군 턴 반환
    """

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(
        self,
        render_mode: Optional[str] = None,
        max_turns: int = 200,
        difficulty: str = "보통",
    ) -> None:
        """
        Args:
            render_mode: 렌더링 모드 ('human', 'ansi', None)
            max_turns: 최대 턴 수 (초과 시 truncated=True)
            difficulty: 난이도 ('쉬움', '보통', '어려움', '매우 어려움')
        """
        super().__init__()
        _ensure_skills()

        if _GYM_AVAILABLE:
            self.observation_space = spaces.Box(
                low=0.0,
                high=1.0,
                shape=(StateEncoder.OBSERVATION_DIM,),
                dtype=np.float32,
            )
            self.action_space = spaces.Discrete(ActionSpaceEncoder.NUM_ACTIONS)

        self.render_mode = render_mode
        self.max_turns = max_turns
        self.difficulty = difficulty

        self.headless_combat: Optional[HeadlessCombat] = None
        self.episode_manager = EpisodeManager(difficulty)
        self.reward_shaper = RewardShaper()

        self.current_char: Optional[Any] = None
        self.turn_count: int = 0
        self._prev_snapshot: Dict = {}

        logger.debug(f"CombatEnv 초기화: max_turns={max_turns}, difficulty={difficulty}")

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        """
        환경 리셋 - 새 전투 시작

        Args:
            seed: 랜덤 시드
            options: 추가 옵션 (미사용)

        Returns:
            (observation, info) 튜플
        """
        if _GYM_AVAILABLE:
            super().reset(seed=seed)

        if seed is not None:
            np.random.seed(seed)
            import random
            random.seed(seed)

        # 새 에피소드 생성
        allies, enemies = self.episode_manager.create_random_episode()

        self.headless_combat = HeadlessCombat()
        self.headless_combat.setup(allies, enemies)
        self.turn_count = 0
        self.current_char = None

        # 첫 플레이어 턴까지 ATB 진행
        self._advance_to_player_turn()

        obs = StateEncoder.encode(self.headless_combat.combat_manager)
        self._prev_snapshot = RewardShaper.snapshot(self.headless_combat.combat_manager)

        info = {
            "turn": self.turn_count,
            "ally_count": len(allies),
            "enemy_count": len(enemies),
        }

        if self.render_mode == "human":
            self.render()

        return obs, info

    def step(self, action_id: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        행동 실행

        Args:
            action_id: 0~113 사이의 행동 인덱스

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        try:
            return self._step_inner(action_id)
        except Exception as e:
            # SubprocVecEnv에서 에러가 삼켜지지 않도록 로깅 후 안전 반환
            logger.error(f"step() 크래시: {e}", exc_info=True)
            obs = np.zeros(StateEncoder.OBSERVATION_DIM, dtype=np.float32)
            return obs, -1.0, True, False, {"error": str(e)}

    def _step_inner(self, action_id: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """step() 실제 구현"""
        assert self.headless_combat is not None, "reset()을 먼저 호출하세요."

        cm = self.headless_combat.combat_manager

        # 유효 행동 마스크 확인
        if self.current_char is not None:
            mask = ActionSpaceEncoder.get_valid_mask(cm, self.current_char)
            is_invalid = not mask[action_id]
        else:
            is_invalid = True

        if is_invalid:
            # 유효하지 않은 행동: 패널티만 주고 턴 소비 없이 반환
            obs = StateEncoder.encode(cm)
            reward = RewardShaper.INVALID_ACTION
            terminated = self.headless_combat.done
            truncated = self.turn_count >= self.max_turns
            info = {"invalid_action": True, "turn": self.turn_count}
            return obs, reward, terminated, truncated, info

        # 행동 실행
        action_dict = ActionSpaceEncoder.decode(action_id, cm, self.current_char)
        action_result = self.headless_combat.execute(
            actor=self.current_char,
            action_type=action_dict["action_type"],
            target=action_dict.get("target"),
            skill=action_dict.get("skill"),
            item=action_dict.get("item"),
        )
        self.turn_count += 1

        # 전투 종료 확인
        terminated = self.headless_combat.done
        truncated = self.turn_count >= self.max_turns

        # 새 상태 스냅샷
        new_snapshot = RewardShaper.snapshot(cm)

        # 보상 계산
        reward = RewardShaper.calculate(
            prev_state=self._prev_snapshot,
            new_state=new_snapshot,
            action_result=action_result,
            done=terminated or truncated,
            result=self.headless_combat.result,
            invalid_action=False,
        )

        # 승리 효율 보너스
        if terminated and self.headless_combat.result == "victory":
            reward += RewardShaper.get_efficiency_bonus(self.turn_count, self.max_turns)

        self._prev_snapshot = new_snapshot

        # 적 턴 자동 처리 & 다음 플레이어 턴까지 진행
        if not terminated and not truncated:
            self._advance_to_player_turn()

        obs = StateEncoder.encode(cm)

        info = {
            "turn": self.turn_count,
            "result": self.headless_combat.result,
            "action_result": action_result,
            "invalid_action": False,
        }

        if self.render_mode == "human":
            self.render()

        return obs, float(reward), terminated, truncated, info

    def action_masks(self) -> np.ndarray:
        """
        MaskablePPO용 행동 마스크 반환

        Returns:
            (114,) bool numpy 배열
        """
        if self.current_char is None or self.headless_combat is None:
            return np.zeros(ActionSpaceEncoder.NUM_ACTIONS, dtype=bool)
        return ActionSpaceEncoder.get_valid_mask(
            self.headless_combat.combat_manager, self.current_char
        )

    def _advance_to_player_turn(self) -> None:
        """
        적 턴을 자동으로 처리하고 다음 아군 턴까지 ATB를 진행

        아군의 ATB 게이지가 행동 임계치에 도달할 때까지
        ATB를 진행하며 도중에 행동 가능한 적은 규칙 기반 AI로 처리합니다.
        """
        if self.headless_combat is None or self.headless_combat.done:
            self.current_char = None
            return

        cm = self.headless_combat.combat_manager
        allies_set = set(id(a) for a in cm.allies)

        for _ in range(_MAX_ATB_TICKS):
            if self.headless_combat.done:
                self.current_char = None
                return

            actor = self.headless_combat.tick(delta_time=1.0)

            if actor is None:
                continue

            # 아군이 행동 가능하면 제어권 반환
            if id(actor) in allies_set and getattr(actor, "is_alive", False):
                self.current_char = actor
                return

            # 적 턴: 규칙 기반 AI 처리
            if not getattr(actor, "is_alive", True):
                continue

            self._execute_enemy_turn(actor)

        # 최대 틱 초과 시 경고
        logger.warning("ATB 최대 틱 초과: 플레이어 턴을 찾지 못했습니다.")
        self.current_char = None

    def _execute_enemy_turn(self, enemy: Any) -> None:
        """
        적 규칙 기반 AI 행동 실행

        Args:
            enemy: 행동할 적 캐릭터
        """
        cm = self.headless_combat.combat_manager
        alive_allies = [a for a in cm.allies if getattr(a, "is_alive", False)]

        if not alive_allies:
            return

        # 간단한 규칙: 랜덤 아군을 대상으로 BRV_ATTACK
        import random
        target = random.choice(alive_allies)

        try:
            self.headless_combat.execute(
                actor=enemy,
                action_type="brv_attack",
                target=target,
            )
        except Exception as e:
            logger.debug(f"적 행동 실행 실패 ({enemy.name}): {e}")
            # 실패 시 HP_ATTACK 시도
            try:
                self.headless_combat.execute(
                    actor=enemy,
                    action_type="hp_attack",
                    target=target,
                )
            except Exception:
                pass

    def render(self) -> Optional[str]:
        """
        환경 렌더링

        Returns:
            ansi 모드: 텍스트 문자열 반환
            human 모드: 콘솔 출력 후 None 반환
        """
        if self.headless_combat is None:
            return None

        state = self.headless_combat.get_state()

        lines = [
            f"=== 턴 {self.turn_count} | {state['state']} ===",
        ]

        lines.append("[ 아군 ]")
        for ally in state["allies"]:
            alive = "O" if ally["is_alive"] else "X"
            hp_pct = ally["current_hp"] / max(ally["max_hp"], 1) * 100
            lines.append(
                f"  {alive} {ally['name']}: HP {ally['current_hp']}/{ally['max_hp']} ({hp_pct:.0f}%)"
                f" BRV {ally['current_brv']}"
            )

        lines.append("[ 적군 ]")
        for enemy in state["enemies"]:
            alive = "O" if enemy["is_alive"] else "X"
            hp_pct = enemy["current_hp"] / max(enemy["max_hp"], 1) * 100
            lines.append(
                f"  {alive} {enemy['name']}: HP {enemy['current_hp']}/{enemy['max_hp']} ({hp_pct:.0f}%)"
                f" BRV {enemy['current_brv']}"
            )

        text = "\n".join(lines)

        if self.render_mode == "human":
            print(text)
            return None
        elif self.render_mode == "ansi":
            return text

        return None

    def close(self) -> None:
        """환경 종료 및 리소스 정리"""
        self.headless_combat = None
        self.current_char = None
        logger.debug("CombatEnv 종료")
