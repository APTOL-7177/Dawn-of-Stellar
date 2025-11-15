"""
Event Bus - 이벤트 기반 통신 시스템

모든 시스템 간 통신은 이벤트를 통해 이루어집니다.
"""

from typing import Callable, Dict, List, Any
from collections import defaultdict


class EventBus:
    """
    이벤트 버스 - Pub/Sub 패턴 구현

    시스템 간 느슨한 결합을 위한 중앙 이벤트 관리자
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: List[tuple] = []
        self._max_history = 100

    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """
        이벤트 구독

        Args:
            event_name: 이벤트 이름 (예: "combat.start")
            callback: 이벤트 발생 시 호출될 콜백 함수
        """
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """
        이벤트 구독 해제

        Args:
            event_name: 이벤트 이름
            callback: 제거할 콜백 함수
        """
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, data: Any = None) -> None:
        """
        이벤트 발행

        Args:
            event_name: 이벤트 이름
            data: 이벤트 데이터
        """
        # 이벤트 히스토리 기록
        self._event_history.append((event_name, data))
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # 구독자들에게 이벤트 전달
        for callback in self._subscribers[event_name]:
            try:
                callback(data)
            except Exception as e:
                # 콜백 실행 실패 시 로그 (Logger 순환 참조 방지를 위해 print 사용)
                print(f"[EventBus] 이벤트 콜백 실행 실패: {event_name} - {str(e)}")

    def clear_subscribers(self, event_name: str = None) -> None:
        """
        구독자 제거

        Args:
            event_name: 이벤트 이름 (None이면 모든 구독자 제거)
        """
        if event_name:
            self._subscribers[event_name].clear()
        else:
            self._subscribers.clear()

    def get_event_history(self, event_name: str = None) -> List[tuple]:
        """
        이벤트 히스토리 조회

        Args:
            event_name: 이벤트 이름 (None이면 전체 히스토리)

        Returns:
            이벤트 히스토리 리스트
        """
        if event_name:
            return [(name, data) for name, data in self._event_history if name == event_name]
        return self._event_history.copy()


# 전역 이벤트 버스 인스턴스
event_bus = EventBus()


# 주요 이벤트 이름 상수
class Events:
    """이벤트 이름 상수"""

    # Combat Events
    COMBAT_START = "combat.start"
    COMBAT_END = "combat.end"
    COMBAT_TURN_START = "combat.turn_start"
    COMBAT_TURN_END = "combat.turn_end"
    COMBAT_ACTION = "combat.action"
    COMBAT_DAMAGE_DEALT = "combat.damage_dealt"
    COMBAT_DAMAGE_TAKEN = "combat.damage_taken"

    # Character Events
    CHARACTER_CREATED = "character.created"
    CHARACTER_LEVEL_UP = "character.level_up"
    CHARACTER_HP_CHANGE = "character.hp_change"
    CHARACTER_MP_CHANGE = "character.mp_change"
    CHARACTER_BRV_CHANGE = "character.brv_change"
    CHARACTER_DEATH = "character.death"
    CHARACTER_REVIVE = "character.revive"

    # Skill Events
    SKILL_CAST_START = "skill.cast_start"
    SKILL_CAST_COMPLETE = "skill.cast_complete"
    SKILL_CAST_INTERRUPT = "skill.cast_interrupt"
    SKILL_EXECUTE = "skill.execute"

    # Status Effect Events
    STATUS_APPLIED = "status.applied"
    STATUS_REMOVED = "status.removed"
    STATUS_TICK = "status.tick"

    # World Events
    WORLD_FLOOR_CHANGE = "world.floor_change"
    WORLD_ITEM_PICKUP = "world.item_pickup"
    WORLD_DOOR_OPEN = "world.door_open"
    WORLD_ENEMY_SPAWN = "world.enemy_spawn"

    # Equipment Events
    EQUIPMENT_EQUIPPED = "equipment.equipped"
    EQUIPMENT_UNEQUIPPED = "equipment.unequipped"
    EQUIPMENT_BROKEN = "equipment.broken"

    # UI Events
    UI_MENU_OPEN = "ui.menu_open"
    UI_MENU_CLOSE = "ui.menu_close"
    UI_DIALOG_SHOW = "ui.dialog_show"

    # Audio Events
    AUDIO_BGM_CHANGE = "audio.bgm_change"
    AUDIO_SFX_PLAY = "audio.sfx_play"

    # Save Events
    SAVE_GAME = "save.game"
    LOAD_GAME = "load.game"
