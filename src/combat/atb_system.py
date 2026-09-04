"""
ATB System - Active Time Battle 시스템

상대적 속도 기반 ATB 시스템
ATB 증가량 = (해당 전투원의 SPD / 모든 전투원의 평균 SPD) * base_rate

속도 기반 게이지 증가 (effective_speed * delta_time / 10.0)
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

        # 마지막 행동 턴 카운터 (라운드 로빈용 - 낮을수록 오래 전에 행동)
        self.last_acted_turn: int = 0

    @property
    def percentage(self) -> float:
        """게이지 퍼센트 (0.0 ~ 1.0)"""
        if self.max_gauge <= 0:
            return 0.0
        # 1.0을 넘지 않도록 클램핑
        return min(1.0, self.current / self.max_gauge)

    @property
    def can_act(self) -> bool:
        """행동 가능 여부"""
        # 죽은 캐릭터는 행동 불가
        is_alive = getattr(self.owner, 'is_alive', True)
        if not is_alive:
            return False

        # ATB 게이지가 threshold를 넘지 않았으면 행동 불가
        if self.current < self.threshold:
            return False
        
        # 캐스팅 중이면 행동 불가
        if self.is_casting:
            return False
        
        # status_manager가 있으면 실제 상태이상 상태 확인
        if hasattr(self.owner, 'status_manager'):
            if not self.owner.status_manager.can_act():
                return False
        
        # 레거시 플래그 확인 (status_manager가 없는 경우)
        if self.is_stunned or self.is_sleeping or self.is_paralyzed:
            return False

        return True

    def get_effective_speed(self) -> float:
        """실제 속도 계산 (버프/디버프 포함)"""
        # 죽은 캐릭터는 ATB 증가 안함
        is_alive = getattr(self.owner, 'is_alive', True)
        if not is_alive:
            return 0.0

        # 기절/마비/수면 상태에서도 ATB는 증가해야 함 (기절이 풀리면 바로 행동할 수 있도록)
        # 상태이상은 can_act에서만 행동 불가능을 체크함

        base_speed = getattr(self.owner, "speed", 10)

        # 헤이스트/슬로우 효과
        speed_modifier = self.haste_multiplier / self.slow_multiplier

        # 혼란 상태에서는 속도 감소
        if self.is_confused:
            speed_modifier *= 0.7

        # 버프/디버프 적용 (speed_up, speed_down)
        if hasattr(self.owner, 'active_buffs') and self.owner.active_buffs:
            if 'speed_up' in self.owner.active_buffs:
                buff_value = self.owner.active_buffs['speed_up'].get('value', 0.0)
                speed_modifier *= (1.0 + buff_value)
            if 'speed_down' in self.owner.active_buffs:
                debuff_value = self.owner.active_buffs['speed_down'].get('value', 0.0)
                speed_modifier *= (1.0 - debuff_value)
        
        # [NEW] SCATTER 상태 속도 감소
        if hasattr(self.owner, "is_scattered") and self.owner.is_scattered:
            slow_base = 0.30
            
            # 특성 체크: 유압 피스톤 (hydraulic_piston) -> 45%로 강화
            source = getattr(self.owner, "scatter_source", None)
            if source:
                 if hasattr(source, "system_traits") and "hydraulic_piston" in source.system_traits:
                     slow_base = 0.45
                 elif hasattr(source, "traits"): 
                     for t in source.traits:
                         if t.id == "hydraulic_piston":
                             slow_base = 0.45
                             break
            
            speed_modifier *= (1.0 - slow_base)
            # self.logger.debug 필요 시 추가 (너무 잦은 호출 방지 위해 생략)
        
        # 환경 효과 스탯 수정치 적용
        if hasattr(self.owner, 'env_stat_modifiers'):
            env_speed = self.owner.env_stat_modifiers.get('speed', 1.0)
            speed_modifier *= env_speed

        return base_speed * speed_modifier

    def increase(self, amount: float, force: bool = False) -> None:
        """게이지 증가
        
        Args:
            amount: 증가량
            force: True이면 threshold 체크 무시 (팀워크 스킬 등 특수 상황)
        """
        # 죽은 캐릭터는 ATB 증가하지 않음
        is_alive = getattr(self.owner, 'is_alive', True)
        if not is_alive:
            return
        
        # 캐스팅 중이면 증가하지 않음
        if self.is_casting:
            return
        
        # 이미 threshold를 넘었으면 더 이상 증가하지 않음 (100% 초과 방지)
        # force=True이면 이 체크를 건너뜀 (팀워크 스킬 ATB 회복 등)
        if not force and self.current >= self.threshold:
            # 안전 장치: 이미 넘어간 경우 max_gauge로 제한
            self.current = min(self.current, self.max_gauge)
            return

        # max_gauge를 넘지 않도록 클램핑 (안전 장치)
        new_current = self.current + amount
        self.current = min(new_current, self.max_gauge)
        # 추가 안전 장치: 음수 방지
        self.current = max(0.0, self.current)

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

        # 글로벌 턴 카운터 (라운드 로빈 공정성용)
        self._global_turn_counter: int = 0

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
        """모든 전투원의 평균 속도 계산 (살아있는 전투원만)"""
        if not self.combatants:
            self._average_speed = 1.0
            return

        # 살아있는 전투원만 계산
        alive_combatants = [c for c in self.combatants if getattr(c, 'is_alive', True)]
        if not alive_combatants:
            self._average_speed = 1.0
            return

        total_speed = sum(getattr(c, "speed", 10) for c in alive_combatants)
        self._average_speed = total_speed / len(alive_combatants)

        self.logger.debug(f"평균 속도 업데이트: {self._average_speed:.2f} (살아있는 전투원: {len(alive_combatants)}명)")

    def calculate_atb_increase(self, combatant: Any, is_player_turn: bool = False) -> float:
        """
        ATB 증가량 계산

        ATB 증가량 = (해당 전투원의 유효 SPD / 모든 전투원의 평균 유효 SPD) * base_rate

        Args:
            combatant: 전투원
            is_player_turn: 플레이어 턴 중인지 여부

        Returns:
            ATB 증가량
        """
        # 살아있는 전투원들의 유효 속도 평균 계산
        alive_speeds = []
        for c, g in self.gauges.items():
            if getattr(c, 'is_alive', True):
                alive_speeds.append(g.get_effective_speed())
        avg_speed = sum(alive_speeds) / len(alive_speeds) if alive_speeds else 1.0
        if avg_speed <= 0:
            avg_speed = 1.0

        gauge = self.gauges.get(combatant)
        effective_speed = gauge.get_effective_speed() if gauge else getattr(combatant, "speed", 10)

        # 상대적 속도 계산
        speed_ratio = effective_speed / avg_speed

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

        # ATB 기본 속도 10배 감소 (동기화 오차 및 체감 속도 조정)
        atb_base_reduction = 0.1

        bullet_time_multiplier = atb_base_reduction  # 비불릿타임: 0.1 (10배 감소)
        # 플레이어 턴 중에는 불릿타임 적용 (추가 감소, 기존 절대 속도 유지)
        if is_player_turn:
            difficulty = self.config.get("game.difficulty", "normal")
            if difficulty == "easy":
                bullet_time_multiplier = atb_base_reduction * 0.03125   # 0.003125 (기존과 동일)
            elif difficulty == "hard":
                bullet_time_multiplier = atb_base_reduction * 0.125     # 0.0125 (기존과 동일)
            elif difficulty == "expert":
                bullet_time_multiplier = atb_base_reduction * 0.25      # 0.025 (기존과 동일)
            else:
                bullet_time_multiplier = atb_base_reduction * 0.0625    # 0.00625 (기존과 동일)

        # 캐스팅 시스템 가져오기
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()

        # 살아있는 전투원들의 유효 속도 평균 계산 (상대값 기반)
        alive_effective_speeds = []
        for c, g in self.gauges.items():
            if getattr(c, 'is_alive', True):
                alive_effective_speeds.append(g.get_effective_speed())
        avg_effective_speed = (
            sum(alive_effective_speeds) / len(alive_effective_speeds)
            if alive_effective_speeds else 1.0
        )
        # 안전 장치: 평균 속도가 0 이하면 1.0으로 보정
        if avg_effective_speed <= 0:
            avg_effective_speed = 1.0

        for combatant, gauge in self.gauges.items():
            # 죽은 캐릭터는 ATB 업데이트 건너뛰기
            is_alive = getattr(combatant, 'is_alive', True)
            if not is_alive:
                # 죽은 캐릭터의 ATB는 0으로 유지
                gauge.current = 0
                continue

            # 상태이상 효과가 반영된 속도 사용
            effective_speed = gauge.get_effective_speed()

            # 상대 속도 기반 ATB 증가량 = (유효 속도 / 평균 유효 속도) * base_rate
            # 이렇게 하면 레벨이 올라도 전체적인 ATB 충전 속도가 일정하게 유지됨
            speed_ratio = effective_speed / avg_effective_speed
            increase = speed_ratio * self.base_rate * delta_time * bullet_time_multiplier

            # 캐스팅 중인지 확인
            is_casting = casting_system.is_casting(combatant)
            gauge.is_casting = is_casting

            if is_casting:
                # 캐스팅 중이면 캐스팅 진행도 업데이트 (ATB는 증가하지 않음, 소수점 유지)
                casting_system.update(combatant, increase)
            else:
                # 캐스팅 중이 아니면 항상 ATB 증가 (기절/수면 상태에서도 ATB는 증가해야 함)
                # 기절이 풀리면 바로 행동할 수 있도록 ATB를 미리 채워둠
                gauge.increase(increase)

                # 행동 가능 상태가 되면 이벤트 발행
                if gauge.can_act:
                    event_bus.publish(Events.COMBAT_TURN_START, {
                        "combatant": combatant,
                        "atb_gauge": gauge.current
                    })

    def get_action_order(self) -> List[Any]:
        """
        행동 순서 가져오기 (공정한 라운드 로빈 정렬)

        ATB가 threshold 이상인 캐릭터들 사이에서는 가장 오래 행동하지 않은
        캐릭터가 먼저 행동합니다. 이를 통해 빠른 캐릭터가 오버슈트 차이로
        항상 우선되는 기아(starvation) 문제를 방지합니다.

        Returns:
            행동 가능한 전투원 리스트
        """
        ready_combatants = [
            (combatant, gauge)
            for combatant, gauge in self.gauges.items()
            if gauge.can_act
        ]

        # 정렬 기준: last_acted_turn 오름차순 (오래 전에 행동한 캐릭터 우선)
        # threshold 이상인 캐릭터들은 모두 행동 가능하므로, ATB 오버슈트 차이가
        # 아닌 "누가 더 오래 기다렸는가"로 공정하게 순서 결정
        ready_combatants.sort(key=lambda x: x[1].last_acted_turn)

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

            # 라운드 로빈: 행동한 캐릭터에 현재 턴 카운터를 기록하고 증가
            gauge.last_acted_turn = self._global_turn_counter
            self._global_turn_counter += 1

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
            # 기절 시 ATB 즉시 0으로 리셋
            gauge.current = 0
            self.logger.info(f"{getattr(combatant, 'name', 'Unknown')}: 기절 상태이상 적용 → ATB 0으로 리셋")
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
                    f"[BREAK] {getattr(defender, 'name', 'Unknown')}의 ATB 게이지 초기화"
                )

    def clear(self) -> None:
        """시스템 초기화"""
        self.gauges.clear()
        self.combatants.clear()
        self._average_speed = 0.0
        self._global_turn_counter = 0


# 전역 인스턴스
_atb_system: Optional[ATBSystem] = None


def get_atb_system() -> ATBSystem:
    """전역 ATB 시스템 인스턴스"""
    global _atb_system
    
    # 멀티플레이 모드 확인
    try:
        from src.multiplayer.game_mode import get_game_mode_manager
        game_mode_manager = get_game_mode_manager()
        is_multiplayer = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False
        
        if is_multiplayer:
            # 멀티플레이 모드: MultiplayerATBSystem 사용
            from src.multiplayer.atb_multiplayer import MultiplayerATBSystem
            if _atb_system is None or not isinstance(_atb_system, MultiplayerATBSystem):
                _atb_system = MultiplayerATBSystem()
                logger = get_logger("atb")
                logger.info("멀티플레이 ATB 시스템 초기화 (MultiplayerATBSystem)")
            return _atb_system
    except Exception as e:
        # 멀티플레이 모드 확인 실패 시 일반 시스템 사용
        logger = get_logger("atb")
        logger.debug(f"멀티플레이 모드 확인 실패: {e}, 일반 ATB 시스템 사용")
    
    # 싱글플레이 모드: 일반 ATBSystem 사용
    if _atb_system is None:
        _atb_system = ATBSystem()
    else:
        # 싱글플레이 모드: MultiplayerATBSystem이 남아 있으면 일반 시스템으로 교체
        try:
            from src.multiplayer.atb_multiplayer import MultiplayerATBSystem
            if isinstance(_atb_system, MultiplayerATBSystem):
                _atb_system = ATBSystem()
                logger = get_logger("atb")
                logger.info("싱글플레이 전환: 일반 ATBSystem으로 교체")
        except ImportError:
            pass
    
    return _atb_system
