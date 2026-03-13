"""
멀티플레이 ATB 시스템

호스트 권위 모델:
- 호스트만 ATB를 틱(증가)시킴
- 클라이언트는 호스트의 상태 동기화를 통해 ATB 값을 수신
- 액션 확정 후 1.5초 전역 대기 (모든 ATB 정지)
- 싱글플레이와 동일한 ATB 공식 사용 (부모 ATBSystem.update() 위임)
- 로컬 플레이어 선택 시 불릿타임 적용 (싱글과 동일)
"""

import time
from typing import Dict, Set, Any, Optional
from src.combat.atb_system import ATBSystem, ATBGauge
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class MultiplayerATBSystem(ATBSystem):
    """멀티플레이 전용 ATB 시스템 (호스트 권위 모델)"""

    def __init__(self):
        super().__init__()
        self.logger = get_logger("multiplayer.atb")

        # 호스트 여부 (None=미설정/싱글플레이 호환, True=호스트, False=클라이언트)
        # 클라이언트는 ATB를 자체 틱하지 않고 호스트 동기화에 의존
        self._is_host: Optional[bool] = None

        # 행동 선택 중인 플레이어 추적
        self.players_selecting_action: Set[str] = set()

        # 액션 확인 시간 기록 (전역 시간 - 모든 플레이어와 적에게 적용)
        # 어떤 플레이어가든 행동을 확정하면 모든 ATB가 1.5초 정지
        self.last_action_confirmed_time: Optional[float] = None

        # 설정 값
        self.action_wait_time = MultiplayerConfig.action_wait_time  # 1.5초

    def set_host_mode(self, is_host: bool):
        """
        호스트/클라이언트 모드 설정

        Args:
            is_host: True=호스트(ATB 틱 실행), False=클라이언트(ATB 틱 안함, 동기화만)
        """
        self._is_host = is_host
        self.logger.info(f"ATB 시스템 모드 설정: {'호스트 (ATB 틱 실행)' if is_host else '클라이언트 (동기화 전용)'}")

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

    def update(self, delta_time: float = 1.0, is_player_turn: bool = False) -> None:
        """
        ATB 업데이트 (멀티플레이 - 호스트만 실행)

        싱글플레이와 동일한 ATB 공식을 사용하되, 호스트/클라이언트 분기만 유지:
        - 호스트: 부모 ATBSystem.update() 그대로 호출 (싱글과 동일한 공식)
        - 클라이언트: ATB 틱을 실행하지 않음 (호스트 동기화 값만 사용)
        - 액션 확정 후 1.5초 전역 대기 (모든 ATB 정지)

        Args:
            delta_time: 경과 시간
            is_player_turn: 플레이어 턴 중인지 (싱글과 동일하게 불릿타임 적용)
        """
        if not self.enabled:
            return

        # 클라이언트는 ATB를 자체적으로 틱하지 않음 (호스트 동기화에 의존)
        if self._is_host is False:
            return

        # 오래된 대기 시간 정리 (1.5초 이상 지난 경우)
        self.cleanup_old_waits()

        # 액션 확정 후 1.5초 대기 중이면 모든 ATB 증가 정지
        if self.is_in_action_wait():
            return

        # 부모 ATBSystem.update() 그대로 호출 (싱글과 동일한 공식)
        super().update(delta_time, is_player_turn)

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
