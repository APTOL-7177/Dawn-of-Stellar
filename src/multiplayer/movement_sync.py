"""
플레이어 이동 동기화 시스템

네트워크를 통한 플레이어 이동 동기화를 관리합니다.
"""

import time
from typing import Dict, Optional, Any, Tuple
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class MovementSyncManager:
    """이동 동기화 관리자"""
    
    def __init__(
        self,
        session: MultiplayerSession,
        network_manager: Optional[NetworkManager] = None,
        is_host: bool = False
    ):
        """
        초기화
        
        Args:
            session: 멀티플레이 세션
            network_manager: 네트워크 관리자
            is_host: 호스트 여부
        """
        self.session = session
        self.network_manager = network_manager
        self.is_host = is_host
        self.logger = get_logger("multiplayer.movement_sync")
        self.exploration = None  # MultiplayerExplorationSystem 참조 (나중에 설정됨)
        
        # 이동 요청 큐 (클라이언트용)
        self.move_request_queue: list[Tuple[str, int, int, float]] = []  # [(player_id, dx, dy, timestamp)]
        
        # 위치 동기화 주기
        self.sync_interval = MultiplayerConfig.SYNC_INTERVAL_POSITION
        self.last_sync_time = 0.0
        
        # 네트워크 메시지 핸들러 등록
        if self.network_manager:
            self._register_handlers()
    
    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        if not self.network_manager:
            return
        
        # 호스트는 먼저 릴레이 핸들러를 등록 (클라이언트 메시지를 릴레이하기 위해)
        if self.is_host:
            self.network_manager.register_handler(
                MessageType.PLAYER_MOVE,
                self._relay_player_move
            )
        
        # 플레이어 이동 메시지 핸들러 (쌍방향 동기화)
        # 호스트: 클라이언트로부터 받은 메시지를 릴레이 후 위치 업데이트
        # 클라이언트: 호스트로부터 받은 메시지로 위치 업데이트
        self.network_manager.register_handler(
            MessageType.PLAYER_MOVE,
            self._handle_player_move
        )
    
    async def broadcast_move(
        self,
        player_id: str,
        x: int,
        y: int
    ) -> bool:
        """
        이동 메시지 전송 (쌍방향 동기화)
        - 모든 플레이어가 직접 브로드캐스트
        
        Args:
            player_id: 플레이어 ID
            x: 새로운 X 좌표
            y: 새로운 Y 좌표
            
        Returns:
            전송 성공 여부
        """
        if not self.network_manager:
            self.logger.warning("네트워크 관리자가 없어 이동을 전송할 수 없습니다")
            return False
        
        message = MessageBuilder.player_move(
            player_id=player_id,
            x=x,
            y=y
        )
        
        try:
            # 모든 플레이어가 직접 브로드캐스트 (쌍방향 동기화)
            await self.network_manager.broadcast(message)
            self.logger.debug(f"이동 브로드캐스트: {player_id} -> ({x}, {y})")
            return True
        except Exception as e:
            self.logger.error(f"이동 전송 실패: {e}", exc_info=True)
            return False
    
    async def _relay_player_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        플레이어 이동 메시지 릴레이 (호스트만)
        클라이언트로부터 받은 이동 메시지를 모든 클라이언트에게 브로드캐스트
        
        Args:
            message: 플레이어 이동 메시지
            sender_id: 발신자 ID (클라이언트 ID)
        """
        if not self.is_host or not self.network_manager:
            return
        
        # sender_id가 없으면 호스트가 직접 브로드캐스트한 것이므로 릴레이 불필요
        if not sender_id:
            self.logger.debug(f"호스트 자신의 이동 메시지 - 릴레이 불필요 (이미 브로드캐스트됨)")
            return
        
        # sender-bound 인가: 릴레이 전에 sender와 payload player_id 일치 확인.
        # 릴레이 메시지는 payload가 그대로 전파되므로 인가된 subject로 정규화한다.
        authorized_player_id = message.resolve_sender_player_id(sender_id)
        if not authorized_player_id:
            self.logger.warning(
                f"PLAYER_MOVE 릴레이 스푸핑 의심 거부: sender={sender_id}, "
                f"payload player_id={message.player_id}"
            )
            return
        message.player_id = authorized_player_id
        
        # 클라이언트로부터 받은 메시지를 모든 클라이언트에게 브로드캐스트 (발신자 제외)
        try:
            await self.network_manager.broadcast(message, exclude=sender_id)
            player_name = getattr(self.session.players.get(message.player_id), 'player_name', message.player_id) if message.player_id in self.session.players else message.player_id
            self.logger.info(f"플레이어 이동 메시지 릴레이: {player_name} ({message.player_id}) -> 모든 클라이언트 (발신자 제외: {sender_id})")
        except Exception as e:
            self.logger.error(f"플레이어 이동 메시지 릴레이 실패: {e}", exc_info=True)
    
    
    async def _handle_player_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        플레이어 이동 메시지 처리
        - 호스트: 클라이언트로부터 받은 메시지를 처리하고 위치 업데이트
        - 클라이언트: 호스트로부터 받은 메시지로 위치 업데이트
        호스트의 위치는 항상 우선시됩니다.
        
        Args:
            message: 플레이어 이동 메시지
            sender_id: 발신자 ID
        """
        # sender-bound 인가 (호스트만 강제):
        # - 호스트: WS 연결에서 파생된 sender_id가 인가의 진실 원천.
        #   payload player_id가 sender와 불일치하면 스푸핑 시도이므로 거부.
        # - 클라이언트: 발신자는 신뢰된 host transport이고, payload player_id는
        #   호스트가 이미 검증한 authoritative subject다 (호스트 본인 또는
        #   호스트가 릴레이한 타인의 이동). transport 표식을 플레이어 subject와
        #   혼동해 스푸핑으로 거부하지 않는다.
        if self.is_host:
            player_id = message.resolve_sender_player_id(sender_id)
            if not player_id:
                self.logger.warning(
                    f"PLAYER_MOVE 스푸핑 의심 거부: sender={sender_id}, "
                    f"payload player_id={message.player_id}"
                )
                return
        else:
            player_id = message.player_id or sender_id
        if not player_id:
            self.logger.warning("플레이어 이동 메시지에 플레이어 ID가 없습니다")
            return
        
        if player_id not in self.session.players:
            self.logger.warning(f"플레이어 {player_id}가 세션에 없습니다")
            return
        
        player = self.session.players[player_id]
        
        # 호스트 여부 확인 (호스트의 위치는 항상 우선시)
        is_host_player = hasattr(self.session, 'host_id') and player_id == self.session.host_id
        
        # 로컬 플레이어 여부 확인 (여러 방법으로 확인)
        is_local_player = False
        if hasattr(self, '_local_player_id'):
            is_local_player = player_id == getattr(self, '_local_player_id', None)
        elif hasattr(self, 'exploration') and self.exploration:
            if hasattr(self.exploration, 'local_player_id'):
                is_local_player = player_id == self.exploration.local_player_id
        
        # 위치 업데이트
        x = message.data.get("x", player.x)
        y = message.data.get("y", player.y)
        timestamp = message.timestamp
        
        # 타임스탬프 검사 (순서가 뒤바뀐 패킷 무시)
        # 호스트는 항상 최신으로 간주하지 않고, 타임스탬프를 확인하되
        # 호스트 패킷의 타임스탬프가 기존 것보다 작으면 무시 (하지만 호스트 권한으로 강제할 수도 있음)
        # 여기서는 단순히 타임스탬프 기준으로 최신 상태만 반영
        if hasattr(player, 'last_movement_timestamp'):
            if timestamp < player.last_movement_timestamp:
                self.logger.debug(
                    f"오래된 이동 패킷 무시: {player_id} (현재: {player.last_movement_timestamp}, 수신: {timestamp})"
                )
                return
            # 미래 타임스탬프 거부 (클럭 스큐/조작 방지) — 허용 오차 5초
            if timestamp > time.time() + 5.0:
                self.logger.warning(
                    f"미래 타임스탬프 이동 패킷 거부: {player_id} (수신: {timestamp})"
                )
                return
            player.last_movement_timestamp = timestamp
        
        # 이동 검증 (호스트 인가): sender의 현재 위치에서 인접 1칸 + 맵 경계 + walkable.
        # 거부 시 명시적 복구 경로: authoritative 좌표로 클라이언트 롤백 (MOVEMENT_REJECTED).
        if self.is_host:
            rejected = False
            reason = ""
            # 인접 한 칸 검사 (직전 인가 위치 기준)
            if hasattr(player, 'last_authorized_position') and player.last_authorized_position:
                ax, ay = player.last_authorized_position
                if abs(x - ax) + abs(y - ay) > 1:
                    rejected = True
                    reason = f"인접 한 칸 초과: ({ax}, {ay}) -> ({x}, {y})"
            # 맵 경계 검사
            if not rejected and self.exploration and hasattr(self.exploration, 'dungeon') and self.exploration.dungeon:
                dungeon = self.exploration.dungeon
                dungeon_width = getattr(dungeon, 'width', None)
                dungeon_height = getattr(dungeon, 'height', None)
                if dungeon_width is not None and dungeon_height is not None:
                    if not (0 <= x < dungeon_width and 0 <= y < dungeon_height):
                        rejected = True
                        reason = f"맵 경계 밖: ({x}, {y}) (던전 크기: {dungeon_width}x{dungeon_height})"
                    # walkable 검사
                    elif hasattr(dungeon, 'is_walkable') and not dungeon.is_walkable(x, y):
                        rejected = True
                        reason = f"이동 불가 타일: ({x}, {y})"
            
            if rejected:
                self.logger.warning(f"이동 거부: {player_id} - {reason}")
                # 명시적 복구 경로: authoritative 상태로 클라이언트를 롤백
                if self.network_manager and hasattr(self.network_manager, 'send'):
                    try:
                        rollback_msg = MessageBuilder.movement_rejected(
                            reason=reason,
                            correct_position=(player.x, player.y)
                        )
                        import asyncio
                        asyncio.create_task(
                            self.network_manager.send(rollback_msg, player_id)
                        )
                    except Exception as e:
                        self.logger.error(f"이동 거부 롤백 전송 실패: {e}", exc_info=True)
                return
            # 인가 위치 갱신
            player.last_authorized_position = (x, y)

        # 로컬 플레이어의 이동 메시지는 위치 업데이트 건너뛰기 (이미 로컬에서 처리됨)
        if is_local_player:
            self.logger.debug(f"로컬 플레이어 {player_id}의 이동 메시지 - 위치 업데이트 건너뛰기 (이미 처리됨)")
            return
        
        # 호스트의 이동 메시지는 항상 우선시 (로컬 플레이어가 아니거나, 호스트가 아닌 클라이언트인 경우)
        if is_host_player:
            # 호스트의 위치는 항상 업데이트 (우선순위 최우선)
            old_x = player.x
            old_y = player.y
            
            if hasattr(player, 'update_position'):
                player.update_position(x, y)
            else:
                player.x = x
                player.y = y
            
            # exploration 시스템의 player_positions도 업데이트 (렌더링용)
            if self.exploration and hasattr(self.exploration, 'player_positions'):
                self.exploration.player_positions[player_id] = (x, y)
            
            player_name = getattr(player, 'player_name', player_id)
            self.logger.info(
                f"[호스트 우선] 플레이어 {player_name} 위치 동기화: ({old_x}, {old_y}) -> ({x}, {y}) "
                f"(발신자: {sender_id}, 타임스탬프: {timestamp})"
            )
        else:
            # 일반 클라이언트 플레이어의 이동 메시지 처리
            old_x = player.x
            old_y = player.y
            
            # 위치 업데이트
            if hasattr(player, 'update_position'):
                player.update_position(x, y)
            else:
                player.x = x
                player.y = y
            
            # exploration 시스템의 player_positions도 업데이트 (렌더링용)
            if self.exploration and hasattr(self.exploration, 'player_positions'):
                self.exploration.player_positions[player_id] = (x, y)
            
            # 호스트인 경우: 이동한 플레이어가 자원을 밟았는지 확인 (자동 채집)
            if self.is_host and self.exploration:
                harvest_data = self.exploration.check_and_harvest(x, y, player_id)
                if harvest_data:
                    _, object_type_str = harvest_data
                    
                    # 채집 메시지 브로드캐스트
                    if self.network_manager:
                        try:
                            harvest_msg = MessageBuilder.harvest(
                                x=x,
                                y=y,
                                object_type=object_type_str
                            )
                            import asyncio
                            asyncio.create_task(self.network_manager.broadcast(harvest_msg))
                                
                            self.logger.info(f"플레이어 {player_id} 자동 채집: ({x}, {y}) {object_type_str}")
                        except Exception as e:
                            self.logger.error(f"자동 채집 브로드캐스트 실패: {e}", exc_info=True)
            
            player_name = getattr(player, 'player_name', player_id)
            self.logger.info(
                f"플레이어 {player_name} 위치 동기화: ({old_x}, {old_y}) -> ({x}, {y}) "
                f"(발신자: {sender_id}, 타임스탬프: {timestamp})"
            )
    
    async def _handle_position_sync(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        위치 동기화 메시지 처리 (클라이언트)
        
        Args:
            message: 위치 동기화 메시지
            sender_id: 발신자 ID (호스트)
        """
        if self.is_host:
            return
        
        positions = message.data.get("positions", {})
        
        # 모든 플레이어 위치 업데이트
        for player_id, pos_data in positions.items():
            if player_id not in self.session.players:
                continue
            
            player = self.session.players[player_id]
            
            # 로컬 플레이어는 제외 (자신의 위치는 직접 제어)
            if player_id == getattr(self, '_local_player_id', None):
                continue
            
            x = pos_data.get("x", player.x)
            y = pos_data.get("y", player.y)
            
            player.update_position(x, y)
            # 호스트가 보낸 위치는 이미 인가된 authoritative 좌표이므로
            # 이동 인가 기준점도 함께 갱신한다 (재접속/동기화 후 첫 이동 거부 방지).
            # 타임스탬프는 호스트 기준을 따라오므로 리셋하지 않는다.
            if hasattr(player, 'last_authorized_position'):
                player.last_authorized_position = (x, y)
    
    async def sync_positions(self):
        """
        위치 동기화 (주기적으로 호출)
        
        호스트가 모든 플레이어의 위치를 클라이언트에게 브로드캐스트
        """
        if not self.is_host or not self.network_manager:
            return
        
        current_time = time.time()
        
        # 동기화 주기 체크
        if current_time - self.last_sync_time < self.sync_interval:
            return
        
        self.last_sync_time = current_time
        
        # 모든 플레이어 위치 수집
        positions = {}
        for player_id, player in self.session.players.items():
            positions[player_id] = {
                "x": player.x,
                "y": player.y,
                "timestamp": current_time
            }
        
        # 위치 동기화 메시지 전송
        sync_message = MessageBuilder.position_sync(positions)
        await self.network_manager.broadcast(sync_message)
        
        self.logger.debug(f"위치 동기화 브로드캐스트: {len(positions)}명")
    
    def set_local_player_id(self, player_id: str):
        """
        로컬 플레이어 ID 설정
        
        Args:
            player_id: 로컬 플레이어 ID
        """
        self._local_player_id = player_id

