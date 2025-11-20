"""
멀티플레이 ATB 시스템

실시간 전투를 위한 ATB 시스템 개조
- 항상 ATB 증가
- 행동 선택 중 1/50 감소
- 1.5초 대기 예외 처리
"""

import time
from typing import Dict, Set, Any, Optional
from src.combat.atb_system import ATBSystem, ATBGauge
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class MultiplayerATBSystem(ATBSystem):
    """멀티플레이 전용 ATB 시스템"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("multiplayer.atb")
        
        # 행동 선택 중인 플레이어 추적
        self.players_selecting_action: Set[str] = set()
        
        # 액션 확인 시간 기록 (전역 시간 - 모든 플레이어와 적에게 적용)
        # 어떤 플레이어가든 행동을 확정하면 모든 ATB가 1.5초 정지
        self.last_action_confirmed_time: Optional[float] = None
        
        # 설정 값
        self.action_wait_time = MultiplayerConfig.action_wait_time  # 1.5초
        self.atb_reduction_multiplier = MultiplayerConfig.atb_reduction_multiplier  # 1/50 = 0.02
    
    def set_player_selecting(self, player_id: str, is_selecting: bool):
        """
        플레이어가 행동 선택 중인지 설정
        
        Args:
            player_id: 플레이어 ID
            is_selecting: 행동 선택 중 여부
        """
        try:
            if not player_id or not isinstance(player_id, str):
                self.logger.warning(f"잘못된 플레이어 ID: {player_id}")
                return
            
            if not isinstance(is_selecting, bool):
                self.logger.warning(f"잘못된 선택 상태: {is_selecting}")
                return
            
            if is_selecting:
                self.players_selecting_action.add(player_id)
                self.logger.debug(f"플레이어 {player_id} 행동 선택 시작")
            else:
                self.players_selecting_action.discard(player_id)
                # 액션 확인 시간 기록 (전역 시간 - 모든 플레이어와 적에게 적용)
                self.last_action_confirmed_time = time.time()
                self.logger.debug(f"플레이어 {player_id} 행동 선택 완료 (모든 ATB 1.5초 정지)")
        except Exception as e:
            self.logger.error(f"플레이어 선택 상태 설정 실패: {e}", exc_info=True)
    
    def is_in_action_wait(self) -> bool:
        """
        액션 확인 후 대기 시간 중인지 확인 (전역 - 모든 플레이어와 적에게 적용)
        
        Returns:
            대기 시간 중 여부
        """
        if self.last_action_confirmed_time is None:
            return False
        
        elapsed = time.time() - self.last_action_confirmed_time
        return elapsed < self.action_wait_time
    
    def _get_player_id_from_combatant(self, combatant: Any) -> Optional[str]:
        """
        전투원에서 플레이어 ID 추출
        
        Args:
            combatant: 전투원 객체
            
        Returns:
            플레이어 ID (없으면 None)
        """
        # 직접 player_id 속성이 있는지 확인
        if hasattr(combatant, 'player_id'):
            return getattr(combatant, 'player_id', None)
        
        # Character 객체인 경우
        if hasattr(combatant, 'owner') and hasattr(combatant.owner, 'player_id'):
            return getattr(combatant.owner, 'player_id', None)
        
        return None
    
    def calculate_atb_increase(self, combatant: Any, delta_time: float = 1.0, is_player_turn: bool = False) -> float:
        """
        ATB 증가량 계산 (멀티플레이 규칙 적용)
        
        멀티플레이 규칙:
        1. 행동 선택 중인 플레이어가 있으면 모든 ATB가 1/50로 감소
        2. 캐스팅 중인 경우도 1/50로 감소
        3. 액션 확인 후 1.5초 대기 중이면 모든 플레이어와 적의 ATB가 정지됨
        
        Args:
            combatant: 전투원
            delta_time: 경과 시간
            is_player_turn: 플레이어 턴 중인지 (멀티플레이에서는 무시됨)
            
        Returns:
            ATB 증가량
        """
        # 기본 증가량 계산 (부모 클래스 메서드 사용)
        base_increase = super().calculate_atb_increase(combatant, is_player_turn=False)
        
        # delta_time 반영 (속도 기반 증가)
        gauge = self.get_gauge(combatant)
        if gauge:
            effective_speed = gauge.get_effective_speed()
            # 속도 기반 증가량 (기존 로직과 동일)
            speed_based_increase = (effective_speed * delta_time) / 5.0
            base_increase = speed_based_increase
        
        # 1. 액션 확인 후 1.5초 대기 중이면 모든 플레이어와 적의 ATB가 정지됨
        if self.is_in_action_wait():
            return 0.0
        
        # 2. 행동 선택 중인 플레이어가 있으면 1/50로 감소
        if self.players_selecting_action:
            base_increase *= self.atb_reduction_multiplier
        
        # 3. 캐스팅 중인 경우도 1/50로 감소
        if gauge and gauge.is_casting:
            base_increase *= self.atb_reduction_multiplier
        
        return base_increase
    
    def update(self, delta_time: float = 1.0, is_player_turn: bool = False) -> None:
        """
        ATB 업데이트 (멀티플레이 - 항상 진행)
        
        멀티플레이에서는 is_player_turn이 True여도 ATB가 증가합니다.
        단, 멀티플레이 규칙(행동 선택 중 감소, 1.5초 대기 등)이 적용됩니다.
        
        Args:
            delta_time: 경과 시간
            is_player_turn: 플레이어 턴 중인지 (멀티플레이에서는 무시됨)
        """
        if not self.enabled:
            return
        
        # 오래된 대기 시간 정리 (1.5초 이상 지난 경우)
        self.cleanup_old_waits()
        
        # 멀티플레이에서는 항상 ATB 증가 (is_player_turn 무시)
        # 캐스팅 시스템 가져오기
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()
        
        for combatant, gauge in self.gauges.items():
            # 죽은 캐릭터는 ATB 업데이트 건너뛰기
            is_alive = getattr(combatant, 'is_alive', True)
            if not is_alive:
                gauge.current = 0
                continue
            
            # ATB 증가량 계산 (멀티플레이 규칙 적용)
            increase = self.calculate_atb_increase(combatant, delta_time, is_player_turn=False)
            
            # 캐스팅 중인지 확인
            is_casting = casting_system.is_casting(combatant)
            gauge.is_casting = is_casting
            
            if is_casting:
                # 캐스팅 중이면 캐스팅 진행도 업데이트 (ATB는 증가하지 않음)
                # 단, 멀티플레이 규칙(1/50 감소)이 이미 calculate_atb_increase에서 적용됨
                casting_system.update(combatant, int(increase))
            else:
                # ATB 증가
                gauge.increase(increase)
                
                # 행동 가능 상태가 되면 이벤트 발행
                if gauge.can_act:
                    from src.core.event_bus import event_bus, Events
                    event_bus.publish(Events.COMBAT_TURN_START, {
                        "combatant": combatant,
                        "atb_gauge": gauge.current
                    })
    
    def clear_action_wait(self):
        """
        액션 대기 시간 초기화 (1.5초 지난 후 자동으로 호출되거나 수동 호출)
        """
        if self.last_action_confirmed_time is not None:
            self.last_action_confirmed_time = None
            self.logger.debug("액션 대기 시간 종료 (모든 ATB 재개)")
    
    def cleanup_old_waits(self):
        """
        오래된 액션 대기 시간 기록 정리 (1.5초 이상 지난 경우)
        """
        if self.last_action_confirmed_time is None:
            return
        
        current_time = time.time()
        if current_time - self.last_action_confirmed_time >= self.action_wait_time:
            self.clear_action_wait()

