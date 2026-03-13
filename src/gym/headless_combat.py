"""
헤드리스 전투 래퍼 - UI/오디오/진동 없이 전투 실행

RL 학습 환경에서 사용하기 위해 CombatManager를 래핑하여
사이드 이펙트(진동, 오디오, 보스 대사)를 억제합니다.
"""

from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock

from src.core.logger import get_logger
from src.combat.combat_manager import CombatManager, ActionType, CombatState

logger = get_logger("gym.headless")


def _ensure_config():
    """게임 설정이 초기화되어 있는지 확인하고, 안 되어 있으면 자동 초기화"""
    from src.core.config import get_config
    try:
        get_config()
    except RuntimeError:
        from src.core.config import initialize_config
        initialize_config("config.yaml")
        logger.debug("게임 설정 자동 초기화 완료")


@contextmanager
def _suppress_side_effects():
    """진동, 오디오, 보스 대사 등 사이드 이펙트를 일시 억제하는 컨텍스트 매니저"""
    noop = MagicMock()
    patches = [
        patch("src.combat.combat_manager.vibration_manager.vibrate", noop),
        patch("src.combat.combat_manager.play_sfx", noop),
        patch("src.core.vibration_system.vibration_manager.vibrate", noop),
    ]
    # 오디오 모듈 패치 (임포트 가능한 경우에만)
    try:
        import src.audio as _audio_mod
        patches.append(patch.object(_audio_mod, "play_sfx", noop))
        patches.append(patch.object(_audio_mod, "play_bgm", noop))
    except (ImportError, AttributeError):
        pass

    started = []
    try:
        for p in patches:
            try:
                p.start()
                started.append(p)
            except (AttributeError, ModuleNotFoundError):
                pass
        yield
    finally:
        for p in started:
            try:
                p.stop()
            except RuntimeError:
                pass


class HeadlessCombat:
    """
    헤드리스 전투 래퍼 - UI/오디오 없이 전투 실행

    CombatManager를 감싸 RL 환경에서 안전하게 호출할 수 있도록 합니다.
    진동, 오디오, 보스 대사를 모두 무시(no-op)합니다.
    """

    def __init__(self) -> None:
        _ensure_config()
        self.combat_manager = CombatManager()
        self.combat_manager.headless = True
        self._prev_state_snapshot: Dict = {}
        logger.debug("헤드리스 전투 래퍼 초기화")

    def setup(self, allies: List[Any], enemies: List[Any]) -> None:
        """
        전투 초기화

        Args:
            allies: 아군 캐릭터 리스트
            enemies: 적군 캐릭터 리스트
        """
        with _suppress_side_effects():
            self.combat_manager.start_combat(allies, enemies)
        logger.debug(f"헤드리스 전투 설정 완료: 아군 {len(allies)}명, 적 {len(enemies)}명")

    def tick(self, delta_time: float = 1.0) -> Optional[Any]:
        """
        ATB 진행 후 다음 행동 가능한 전투원 반환

        Args:
            delta_time: 경과 시간 (기본 1.0)

        Returns:
            행동 가능한 전투원 (None이면 아직 아무도 행동 불가)
        """
        if self.done:
            return None

        with _suppress_side_effects():
            self.combat_manager.update(delta_time)

        atb = self.combat_manager.atb

        # 아군 우선 확인 (RL 에이전트 제어)
        for ally in self.combat_manager.allies:
            if not ally.is_alive:
                continue
            gauge = atb.get_gauge(ally)
            if gauge and gauge.can_act:
                return ally

        # 적군 확인
        for enemy in self.combat_manager.enemies:
            if not getattr(enemy, "is_alive", True):
                continue
            gauge = atb.get_gauge(enemy)
            if gauge and gauge.can_act:
                return enemy

        return None

    def execute(
        self,
        actor: Any,
        action_type: str,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        item: Optional[Any] = None,
    ) -> Dict:
        """
        행동 실행 후 결과 반환

        Args:
            actor: 행동하는 캐릭터
            action_type: 행동 타입 문자열 (ActionType.value 또는 enum)
            target: 대상 캐릭터
            skill: 사용할 스킬 (SKILL 행동 시)
            item: 사용할 아이템 (ITEM 행동 시)

        Returns:
            행동 결과 딕셔너리
        """
        # 문자열 -> ActionType 변환
        if isinstance(action_type, str):
            try:
                action_enum = ActionType(action_type)
            except ValueError:
                # 언더스코어 방식도 허용 (예: "brv_attack")
                action_enum = ActionType(action_type.lower())
        else:
            action_enum = action_type

        with _suppress_side_effects():
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=action_enum,
                target=target,
                skill=skill,
                item=item,
            )

        if result is None:
            result = {}

        return result

    def get_state(self) -> Dict:
        """
        현재 전투 상태 스냅샷 반환

        Returns:
            전투 상태 딕셔너리 (HP, BRV, alive 여부 등)
        """
        allies_state = []
        for ally in self.combat_manager.allies:
            allies_state.append({
                "name": ally.name,
                "current_hp": getattr(ally, "current_hp", 0),
                "max_hp": getattr(ally, "max_hp", 1),
                "current_brv": getattr(ally, "current_brv", 0),
                "max_brv": getattr(ally, "max_brv", 1),
                "current_mp": getattr(ally, "current_mp", 0),
                "max_mp": getattr(ally, "max_mp", 1),
                "is_alive": getattr(ally, "is_alive", False),
            })

        enemies_state = []
        for enemy in self.combat_manager.enemies:
            enemies_state.append({
                "name": getattr(enemy, "name", "적"),
                "current_hp": getattr(enemy, "current_hp", 0),
                "max_hp": getattr(enemy, "max_hp", 1),
                "current_brv": getattr(enemy, "current_brv", 0),
                "max_brv": getattr(enemy, "max_brv", 1),
                "is_alive": getattr(enemy, "is_alive", False),
            })

        return {
            "allies": allies_state,
            "enemies": enemies_state,
            "turn_count": self.combat_manager.turn_count,
            "state": self.combat_manager.state.value,
        }

    @property
    def done(self) -> bool:
        """전투 종료 여부"""
        terminal = {CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED}
        return self.combat_manager.state in terminal

    @property
    def result(self) -> str:
        """
        전투 결과

        Returns:
            'victory', 'defeat', 'fled', 'in_progress' 중 하나
        """
        state = self.combat_manager.state
        if state == CombatState.VICTORY:
            return "victory"
        elif state == CombatState.DEFEAT:
            return "defeat"
        elif state == CombatState.FLED:
            return "fled"
        return "in_progress"

    def get_allies(self) -> List[Any]:
        """아군 리스트 반환"""
        return self.combat_manager.allies

    def get_enemies(self) -> List[Any]:
        """적군 리스트 반환"""
        return self.combat_manager.enemies
