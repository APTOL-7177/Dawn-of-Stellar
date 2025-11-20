"""
적 이동 동기화 시스템

멀티플레이에서 적의 0.65초 간격 움직임을 관리합니다.
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class EnemySyncManager:
    """적 이동 동기화 관리자"""
    
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
        self.logger = get_logger("multiplayer.enemy_sync")
        
        # 적 이동 간격 (0.65초)
        self.move_interval = MultiplayerConfig.SYNC_INTERVAL_ENEMY
        self.last_move_time = 0.0
        
        # 적 위치 캐시
        self.enemy_positions: Dict[str, Tuple[int, int]] = {}  # {enemy_id: (x, y)}
        
        # 네트워크 메시지 핸들러 등록
        if self.network_manager:
            self._register_handlers()
    
    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        if not self.network_manager:
            return
        
        # 적 이동 메시지 핸들러 (클라이언트만)
        if not self.is_host:
            self.network_manager.register_handler(
                MessageType.ENEMY_MOVE,
                self._handle_enemy_move
            )
    
    def can_move_enemies(self, current_time: float) -> bool:
        """
        적 이동 가능 여부 확인
        
        Args:
            current_time: 현재 시간
            
        Returns:
            이동 가능 여부
        """
        # 호스트만 적을 이동시킬 수 있음
        if not self.is_host:
            return False
        
        # 0.65초 간격 체크
        if current_time - self.last_move_time < self.move_interval:
            return False
        
        return True
    
    def update_move_time(self, current_time: float):
        """
        이동 시간 업데이트
        
        Args:
            current_time: 현재 시간
        """
        self.last_move_time = current_time
    
    async def sync_enemy_positions(self, enemies: List[Any]):
        """
        적 위치 동기화 (호스트 -> 모든 클라이언트)
        
        Args:
            enemies: 적 리스트
        """
        try:
            if not self.is_host or not self.network_manager:
                return
            
            if not isinstance(enemies, list):
                self.logger.warning(f"잘못된 적 리스트 타입: {type(enemies)}")
                return
            
            current_time = time.time()
            
            # 이동 가능 여부 확인
            if not self.can_move_enemies(current_time):
                return
            
            # 모든 적 위치 수집
            enemy_positions = {}
            for enemy in enemies:
                try:
                    if not enemy:
                        continue
                    
                    # 적 ID 생성
                    enemy_id = self._get_enemy_id(enemy)
                    if not enemy_id:
                        continue
                    
                    # 적 위치 확인
                    if not hasattr(enemy, 'x') or not hasattr(enemy, 'y'):
                        continue
                    
                    try:
                        x = int(enemy.x)
                        y = int(enemy.y)
                    except (ValueError, TypeError, AttributeError):
                        self.logger.warning(f"적 {enemy_id}의 위치를 읽을 수 없음")
                        continue
                    
                    enemy_positions[enemy_id] = {
                        "x": x,
                        "y": y,
                        "timestamp": current_time
                    }
                except Exception as e:
                    self.logger.error(f"적 위치 수집 실패: {e}", exc_info=True)
                    continue
            
            if not enemy_positions:
                return
            
            # 적 이동 메시지 전송
            try:
                move_message = MessageBuilder.enemy_move(enemy_positions)
                await self.network_manager.broadcast(move_message)
                
                # 이동 시간 업데이트
                self.update_move_time(current_time)
                
                self.logger.debug(f"적 위치 동기화 브로드캐스트: {len(enemy_positions)}마리")
            except Exception as e:
                self.logger.error(f"적 위치 동기화 브로드캐스트 실패: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"적 위치 동기화 실패: {e}", exc_info=True)
    
    async def _handle_enemy_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        적 이동 메시지 처리 (클라이언트)
        
        Args:
            message: 적 이동 메시지
            sender_id: 발신자 ID (호스트)
        """
        if self.is_host:
            return
        
        enemy_positions = message.data.get("enemies", {})
        
        # 적 위치 업데이트는 ExplorationSystem에서 처리
        # 여기서는 캐시만 업데이트
        self.enemy_positions = {}
        for enemy_id, pos_data in enemy_positions.items():
            x = pos_data.get("x", 0)
            y = pos_data.get("y", 0)
            self.enemy_positions[enemy_id] = (x, y)
        
        self.logger.debug(f"적 위치 동기화 수신: {len(enemy_positions)}마리")
    
    def _get_enemy_id(self, enemy: Any) -> str:
        """
        적 ID 생성
        
        Args:
            enemy: 적 객체
            
        Returns:
            적 ID
        """
        # 고유 ID가 있으면 사용
        if hasattr(enemy, 'id') and enemy.id:
            return str(enemy.id)
        
        # 없으면 위치 기반 ID (임시)
        return f"enemy_{enemy.x}_{enemy.y}"
    
    def get_enemy_position(self, enemy_id: str) -> Optional[Tuple[int, int]]:
        """
        적 위치 가져오기
        
        Args:
            enemy_id: 적 ID
            
        Returns:
            (x, y) 위치, 없으면 None
        """
        return self.enemy_positions.get(enemy_id)

