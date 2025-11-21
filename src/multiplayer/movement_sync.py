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
        player_id = message.player_id
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
            if player_id == self.session.get_player(player_id) and hasattr(self, '_local_player_id'):
                if player_id == getattr(self, '_local_player_id', None):
                    continue
            
            x = pos_data.get("x", player.x)
            y = pos_data.get("y", player.y)
            
            player.update_position(x, y)
    
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

