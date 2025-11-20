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
        
        # 이동 요청 핸들러 (호스트만)
        if self.is_host:
            self.network_manager.register_handler(
                MessageType.MOVE_REQUEST,
                self._handle_move_request
            )
        
        # 플레이어 이동 메시지 핸들러 (모두)
        self.network_manager.register_handler(
            MessageType.PLAYER_MOVE,
            self._handle_player_move
        )
        
        # 위치 동기화 메시지 핸들러 (클라이언트만)
        if not self.is_host:
            self.network_manager.register_handler(
                MessageType.POSITION_SYNC,
                self._handle_position_sync
            )
    
    async def request_move(
        self,
        player_id: str,
        dx: int,
        dy: int
    ) -> bool:
        """
        이동 요청 (클라이언트에서 호스트로)
        
        Args:
            player_id: 플레이어 ID
            dx: X 방향 이동량 (-1, 0, 1)
            dy: Y 방향 이동량 (-1, 0, 1)
            
        Returns:
            요청 전송 성공 여부
        """
        if self.is_host:
            # 호스트는 직접 처리
            return await self._process_move(player_id, dx, dy)
        
        if not self.network_manager:
            self.logger.warning("네트워크 관리자가 없어 이동 요청을 보낼 수 없습니다")
            return False
        
        # 클라이언트: 호스트에게 이동 요청 전송
        message = MessageBuilder.move_request(
            player_id=player_id,
            dx=dx,
            dy=dy
        )
        
        try:
            await self.network_manager.send(message)
            self.logger.debug(f"이동 요청 전송: {player_id} ({dx}, {dy})")
            return True
        except Exception as e:
            self.logger.error(f"이동 요청 전송 실패: {e}", exc_info=True)
            return False
    
    async def _handle_move_request(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        이동 요청 처리 (호스트)
        
        Args:
            message: 이동 요청 메시지
            sender_id: 발신자 ID
        """
        if not self.is_host:
            return
        
        player_id = message.player_id or sender_id
        if not player_id:
            self.logger.warning("이동 요청에 플레이어 ID가 없습니다")
            return
        
        dx = message.data.get("dx", 0)
        dy = message.data.get("dy", 0)
        
        # 이동 처리 및 브로드캐스트
        await self._process_move(player_id, dx, dy)
    
    async def _process_move(
        self,
        player_id: str,
        dx: int,
        dy: int
    ) -> bool:
        """
        이동 처리 및 브로드캐스트 (호스트)
        
        Args:
            player_id: 플레이어 ID
            dx: X 방향 이동량
            dy: Y 방향 이동량
            
        Returns:
            이동 성공 여부
        """
        try:
            if not player_id or not isinstance(player_id, str):
                self.logger.warning(f"잘못된 플레이어 ID: {player_id}")
                return False
            
            if not isinstance(dx, int) or not isinstance(dy, int):
                self.logger.warning(f"잘못된 이동량: dx={dx}, dy={dy}")
                return False
            
            if player_id not in self.session.players:
                self.logger.warning(f"플레이어 {player_id}가 세션에 없습니다")
                return False
            
            player = self.session.players[player_id]
            if not player:
                self.logger.error(f"플레이어 {player_id} 객체가 None입니다")
                return False
            
            if not hasattr(player, 'x') or not hasattr(player, 'y'):
                self.logger.error(f"플레이어 {player_id}에 위치 속성이 없습니다")
                return False
            
            try:
                current_x = int(player.x)
                current_y = int(player.y)
                new_x = current_x + dx
                new_y = current_y + dy
            except (ValueError, TypeError, AttributeError) as e:
                self.logger.error(f"플레이어 {player_id}의 위치를 읽을 수 없음: {e}")
                return False
            
            # 위치 업데이트
            if hasattr(player, 'update_position'):
                try:
                    player.update_position(new_x, new_y)
                except Exception as e:
                    self.logger.error(f"플레이어 위치 업데이트 실패: {e}", exc_info=True)
                    return False
            else:
                # update_position 메서드가 없으면 직접 설정
                try:
                    player.x = new_x
                    player.y = new_y
                except Exception as e:
                    self.logger.error(f"플레이어 위치 직접 설정 실패: {e}", exc_info=True)
                    return False
            
            # 모든 클라이언트에게 이동 브로드캐스트
            if self.network_manager:
                try:
                    move_message = MessageBuilder.player_move(
                        player_id=player_id,
                        x=new_x,
                        y=new_y
                    )
                    await self.network_manager.broadcast(move_message)
                except Exception as e:
                    self.logger.error(f"이동 브로드캐스트 실패: {e}", exc_info=True)
            
            player_name = getattr(player, 'player_name', player_id)
            self.logger.debug(
                f"플레이어 {player_name} 이동: "
                f"({current_x}, {current_y}) -> ({new_x}, {new_y})"
            )
            
            return True
        except Exception as e:
            self.logger.error(f"이동 처리 실패: {e}", exc_info=True)
            return False
    
    async def _handle_player_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        플레이어 이동 메시지 처리 (모든 클라이언트)
        
        Args:
            message: 플레이어 이동 메시지
            sender_id: 발신자 ID (호스트)
        """
        player_id = message.player_id
        if not player_id:
            self.logger.warning("플레이어 이동 메시지에 플레이어 ID가 없습니다")
            return
        
        if player_id not in self.session.players:
            self.logger.warning(f"플레이어 {player_id}가 세션에 없습니다")
            return
        
        player = self.session.players[player_id]
        
        # 로컬 플레이어는 이미 처리되었으므로 무시 (호스트에서 처리)
        if self.is_host and player_id == self.session.host_id:
            return
        
        # 위치 업데이트
        x = message.data.get("x", player.x)
        y = message.data.get("y", player.y)
        timestamp = message.timestamp
        
        # 타임스탬프 기반 예측 보간 (선택적)
        player.update_position(x, y)
        
        self.logger.debug(
            f"플레이어 {player.player_name} 위치 동기화: ({x}, {y}) "
            f"(타임스탬프: {timestamp})"
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

