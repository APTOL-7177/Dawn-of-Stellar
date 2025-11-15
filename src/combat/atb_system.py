"""
ATB System - Active Time Battle 시스템

상대적 속도 기반 ATB 시스템
ATB 증가량 = (해당 전투원의 SPD / 모든 전투원의 평균 SPD) * base_rate

속도 기반 게이지 증가 (effective_speed * delta_time / 5.0)
상태이상 효과 반영 (기절/마비/헤이스트/슬로우)
"""

from typing import List, Dict, Any, Optional
from src.core.config import get_config
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events


class ATBGauge:
    """ATB 게이지 클래스"""

    def __init__(self, owner: Any, max_gauge: int = 2000, threshold: int = 1000) -> None:
        self.owner = owner
        self.max_gauge = max_gauge
        self.threshold = threshold
        self.current = 0

        # 상태 이상 플래그
        self.is_stunned = False
        self.is_paralyzed = False
        self.is_sleeping = False
        self.is_confused = False

        # 속도 배율 효과
        self.haste_multiplier = 1.0
        self.slow_multiplier = 1.0

        # 캐스팅 상태
        self.is_casting = False

    @property
    def percentage(self) -> float:
        """게이지 퍼센트 (0.0 ~ 1.0)"""
        return self.current / self.max_gauge if self.max_gauge > 0 else 0.0

    @property
    def can_act(self) -> bool:
        """행동 가능 여부"""
        # 죽은 캐릭터는 행동 불가
        is_alive = getattr(self.owner, 'is_alive', True)
        if not is_alive:
            return False

        return (self.current >= self.threshold and
                not self.is_stunned and
                not self.is_sleeping and
                not self.is_casting)

    def get_effective_speed(self) -> float:
        """실제 속도 계산 (버프/디버프 포함)"""
        # 죽은 캐릭터는 ATB 증가 안함
        is_alive = getattr(self.owner, 'is_alive', True)
        if not is_alive:
            return 0.0

        if self.is_stunned or self.is_paralyzed or self.is_sleeping:
            return 0.0

        base_speed = getattr(self.owner, "speed", 10)

        # 헤이스트/슬로우 효과
        speed_modifier = self.haste_multiplier / self.slow_multiplier

        # 혼란 상태에서는 속도 감소
        if self.is_confused:
            speed_modifier *= 0.7

        return base_speed * speed_modifier

    def increase(self, amount: float) -> None:
        """게이지 증가"""
        # 캐스팅 중이면 증가하지 않음
        if self.is_casting:
            return

        self.current = min(self.current + amount, self.max_gauge)

    def consume(self, amount: int) -> None:
        """게이지 소비 (행동 후)"""
        self.current = max(0, self.current - amount)

    def reset(self) -> None:
        """게이지 리셋"""
        self.current = 0


class ATBSystem:
    """
    ATB 시스템 매니저

    상대적 속도 기반으로 ATB 게이지를 관리합니다.
    """

    def __init__(self) -> None:
        self.logger = get_logger("atb")
        self.config = get_config()

        # 설정 로드
        self.enabled = self.config.get("combat.atb.enabled", True)
        self.max_gauge = self.config.get("combat.atb.max_gauge", 2000)
        self.threshold = self.config.get("combat.atb.action_threshold", 1000)
        self.base_rate = self.config.get("combat.atb.base_rate", 50)
        self.player_turn_enemy_rate = self.config.get("combat.atb.player_turn_enemy_atb_rate", 0.3)

        # ATB 게이지 저장소
        self.gauges: Dict[Any, ATBGauge] = {}

        # 전투원 목록
        self.combatants: List[Any] = []

        # 평균 속도 캐시
        self._average_speed: float = 0.0

        # BREAK 이벤트 구독 (BREAK 시 ATB 초기화)
        event_bus.subscribe("brave.break", self._on_break)

    def register_combatant(self, combatant: Any) -> None:
        """
        전투원 등록

        Args:
            combatant: 전투원 객체 (speed 속성 필요)
        """
        if combatant not in self.gauges:
            self.gauges[combatant] = ATBGauge(combatant, self.max_gauge, self.threshold)
            self.combatants.append(combatant)
            self._update_average_speed()

            self.logger.debug(
                f"전투원 등록: {getattr(combatant, 'name', 'Unknown')}",
                {"speed": getattr(combatant, "speed", 0)}
            )

    def unregister_combatant(self, combatant: Any) -> None:
        """전투원 제거"""
        if combatant in self.gauges:
            del self.gauges[combatant]
            self.combatants.remove(combatant)
            self._update_average_speed()

    def _update_average_speed(self) -> None:
        """모든 전투원의 평균 속도 계산"""
        if not self.combatants:
            self._average_speed = 1.0
            return

        total_speed = sum(getattr(c, "speed", 10) for c in self.combatants)
        self._average_speed = total_speed / len(self.combatants)

        self.logger.debug(f"평균 속도 업데이트: {self._average_speed:.2f}")

    def calculate_atb_increase(self, combatant: Any, is_player_turn: bool = False) -> float:
        """
        ATB 증가량 계산

        ATB 증가량 = (해당 전투원의 SPD / 평균 SPD) * base_rate

        Args:
            combatant: 전투원
            is_player_turn: 플레이어 턴 중인지 여부

        Returns:
            ATB 증가량
        """
        if self._average_speed <= 0:
            self._update_average_speed()

        combatant_speed = getattr(combatant, "speed", 10)

        # 상대적 속도 계산
        speed_ratio = combatant_speed / self._average_speed

        # 기본 증가량
        increase = speed_ratio * self.base_rate

        # 플레이어 턴 중 적의 ATB 감소
        if is_player_turn and hasattr(combatant, "is_enemy") and combatant.is_enemy:
            increase *= self.player_turn_enemy_rate

        return increase

    def update(self, delta_time: float = 1.0, is_player_turn: bool = False) -> None:
        """
        모든 게이지 업데이트

        Args:
            delta_time: 경과 시간 (프레임 기반)
            is_player_turn: 플레이어 턴 중인지 (True면 ATB 증가 정지)
        """
        if not self.enabled:
            return

        # 플레이어 턴 중에는 시간 정지 (ATB 증가 안 함)
        if is_player_turn:
            return

        # 캐스팅 시스템 가져오기
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()

        for combatant, gauge in self.gauges.items():
            # 상태이상 효과가 반영된 속도 사용
            effective_speed = gauge.get_effective_speed()

            # ATB 업데이트 속도를 1/5로 느리게 조정 (로그라이크_2 방식)
            increase = (effective_speed * delta_time) / 5.0

            # 캐스팅 중인지 확인
            is_casting = casting_system.is_casting(combatant)
            gauge.is_casting = is_casting

            if is_casting:
                # 캐스팅 중이면 캐스팅 진행도 업데이트 (ATB는 증가하지 않음)
                casting_system.update(combatant, int(increase))
            elif not gauge.can_act:
                # 캐스팅 중이 아니고 행동 불가능한 경우에만 ATB 증가
                gauge.increase(increase)

                # 행동 가능 상태가 되면 이벤트 발행
                if gauge.can_act:
                    event_bus.publish(Events.COMBAT_TURN_START, {
                        "combatant": combatant,
                        "atb_gauge": gauge.current
                    })

    def get_action_order(self) -> List[Any]:
        """
        행동 순서 가져오기 (ATB 게이지 기준 정렬)

        Returns:
            행동 가능한 전투원 리스트 (ATB 게이지 높은 순)
        """
        ready_combatants = [
            (combatant, gauge.current)
            for combatant, gauge in self.gauges.items()
            if gauge.can_act
        ]

        # ATB 게이지가 높은 순으로 정렬
        ready_combatants.sort(key=lambda x: x[1], reverse=True)

        return [combatant for combatant, _ in ready_combatants]

    def consume_atb(self, combatant: Any, amount: Optional[int] = None) -> None:
        """
        ATB 소비 (행동 후)

        Args:
            combatant: 전투원
            amount: 소비량 (None이면 threshold만큼 소비)
        """
        gauge = self.gauges.get(combatant)
        if gauge:
            if amount is None:
                amount = self.threshold

            gauge.consume(amount)

            self.logger.debug(
                f"ATB 소비: {getattr(combatant, 'name', 'Unknown')}",
                {"amount": amount, "remaining": gauge.current}
            )

    def get_gauge(self, combatant: Any) -> Optional[ATBGauge]:
        """게이지 가져오기"""
        return self.gauges.get(combatant)

    def get_gauge_percentage(self, combatant: Any) -> float:
        """게이지 퍼센트 가져오기"""
        gauge = self.get_gauge(combatant)
        return gauge.percentage if gauge else 0.0

    def reset_all(self) -> None:
        """모든 게이지 리셋"""
        for gauge in self.gauges.values():
            gauge.reset()

    def apply_status_effect(self, combatant: Any, effect_type: str, duration: float = 0.0) -> None:
        """
        상태 이상 적용

        Args:
            combatant: 전투원
            effect_type: 효과 타입 (stun, paralyze, confuse, sleep, haste, slow)
            duration: 지속 시간 (초)
        """
        gauge = self.get_gauge(combatant)
        if not gauge:
            return

        if effect_type == "stun":
            gauge.is_stunned = True
        elif effect_type == "paralyze":
            gauge.is_paralyzed = True
        elif effect_type == "confuse":
            gauge.is_confused = True
        elif effect_type == "sleep":
            gauge.is_sleeping = True
        elif effect_type == "haste":
            gauge.haste_multiplier = 1.5
        elif effect_type == "slow":
            gauge.slow_multiplier = 2.0

        self.logger.debug(
            f"상태이상 적용: {getattr(combatant, 'name', 'Unknown')}",
            {"effect": effect_type, "duration": duration}
        )

        # 지속 시간 관리는 StatusManager에서 담당
        # ATB 시스템은 속도 변경만 처리하고, 실제 효과 제거는 StatusManager.update()에서 처리됨

    def remove_status_effect(self, combatant: Any, effect_type: str) -> None:
        """
        상태 이상 제거

        Args:
            combatant: 전투원
            effect_type: 효과 타입
        """
        gauge = self.get_gauge(combatant)
        if not gauge:
            return

        if effect_type == "stun":
            gauge.is_stunned = False
        elif effect_type == "paralyze":
            gauge.is_paralyzed = False
        elif effect_type == "confuse":
            gauge.is_confused = False
        elif effect_type == "sleep":
            gauge.is_sleeping = False
        elif effect_type == "haste":
            gauge.haste_multiplier = 1.0
        elif effect_type == "slow":
            gauge.slow_multiplier = 1.0

    def get_status_effects(self, combatant: Any) -> List[str]:
        """
        활성 상태 이상 목록

        Args:
            combatant: 전투원

        Returns:
            상태 이상 목록
        """
        gauge = self.get_gauge(combatant)
        if not gauge:
            return []

        effects = []
        if gauge.is_stunned:
            effects.append("기절")
        if gauge.is_paralyzed:
            effects.append("마비")
        if gauge.is_confused:
            effects.append("혼란")
        if gauge.is_sleeping:
            effects.append("수면")
        if gauge.haste_multiplier > 1.0:
            effects.append("헤이스트")
        if gauge.slow_multiplier > 1.0:
            effects.append("슬로우")

        return effects

    def _on_break(self, data: Dict[str, Any]) -> None:
        """
        BREAK 이벤트 핸들러

        BREAK 당한 캐릭터의 ATB 게이지를 0으로 초기화합니다.

        Args:
            data: 이벤트 데이터 {"attacker": ..., "defender": ..., "brv_stolen": ...}
        """
        defender = data.get("defender")
        if defender:
            gauge = self.get_gauge(defender)
            if gauge:
                gauge.reset()
                self.logger.info(
                    f"⚡ BREAK! {getattr(defender, 'name', 'Unknown')}의 ATB 게이지 초기화"
                )

    def clear(self) -> None:
        """시스템 초기화"""
        self.gauges.clear()
        self.combatants.clear()
        self._average_speed = 0.0


# 전역 인스턴스
_atb_system: Optional[ATBSystem] = None


def get_atb_system() -> ATBSystem:
    """전역 ATB 시스템 인스턴스"""
    global _atb_system
    if _atb_system is None:
        _atb_system = ATBSystem()
    return _atb_system
