"""
전리품 동기화 시스템

멀티플레이에서 전리품 선점 및 창고 공유 관리
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from src.core.logger import get_logger


logger = get_logger("loot_sync")


class LootSyncManager:
    """
    전리품 동기화 매니저
    
    멀티플레이에서 전리품 풀 관리 및 선점 시스템
    호스트가 권위자로 동작
    """
    
    def __init__(self, session: Any, network_manager: Any = None):
        """
        Args:
            session: 멀티플레이 세션
            network_manager: 네트워크 매니저 (브로드캐스트용)
        """
        self.session = session
        self.network_manager = network_manager
        
        # 전리품 풀 (아이템 리스트)
        self.loot_pool: List[Any] = []
        
        # 선점된 아이템 (item_id -> player_id)
        self.claimed_items: Dict[str, str] = {}
        
        logger.info("전리품 동기화 매니저 초기화")
    
    def set_loot_pool(self, items: List[Any]):
        """
        전리품 풀 설정
        
        Args:
            items: 전리품 아이템 리스트
        """
        self.loot_pool = list(items)  # 복사
        self.claimed_items = {}
        logger.info(f"전리품 풀 설정: {len(items)}개 아이템")
    
    def claim_item(self, player_id: str, index: int) -> bool:
        """
        아이템 선점 (호스트 권위)
        
        Args:
            player_id: 선점 요청 플레이어 ID
            index: 전리품 풀 인덱스
            
        Returns:
            성공 여부
        """
        # 유효성 검사
        if index < 0 or index >= len(self.loot_pool):
            logger.warning(f"잘못된 전리품 인덱스: {index} (풀 크기: {len(self.loot_pool)})")
            return False
        
        # 아이템 가져오기
        item = self.loot_pool[index]
        item_name_raw = getattr(item, 'name', 'unknown')
        item_id = getattr(item, 'item_id', f"loot_{index}_{item_name_raw}")
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        
        # 이미 선점된 아이템인지 확인
        if item_id in self.claimed_items:
            logger.warning(f"이미 선점된 아이템: {item_name} by {self.claimed_items[item_id]}")
            return False
        
        # 선점 처리
        self.claimed_items[item_id] = player_id
        self.loot_pool.pop(index)
        
        logger.info(f"아이템 선점: {item_name} -> {player_id}")
        
        # 브로드캐스트 (다른 플레이어에게 알림)
        self._broadcast_claim(player_id, item_id, item_name)
        
        return True
    
    def _broadcast_claim(self, player_id: str, item_id: str, item_name: str):
        """선점 결과 브로드캐스트"""
        if not self.network_manager:
            return
        
        try:
            from src.multiplayer.protocol import NetworkMessage, MessageType

            msg_type = MessageType.GAME_STATE
            message = NetworkMessage(
                type=msg_type,
                data={
                    "action": "loot_claimed",
                    "player_id": player_id,
                    "item_id": item_id,
                    "item_name": item_name,
                    "remaining_count": len(self.loot_pool)
                }
            )

            # 비동기 브로드캐스트
            import asyncio
            if hasattr(self.network_manager, '_server_event_loop') and self.network_manager._server_event_loop:
                asyncio.run_coroutine_threadsafe(
                    self.network_manager.broadcast(message),
                    self.network_manager._server_event_loop
                )
            else:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.network_manager.broadcast(message))
                
        except Exception as e:
            logger.error(f"전리품 선점 브로드캐스트 실패: {e}")
    
    def distribute_gold(self, total_gold: int) -> Dict[str, int]:
        """
        골드 균등 분배
        
        Args:
            total_gold: 총 골드
            
        Returns:
            플레이어별 골드 (player_id -> gold)
        """
        if not self.session or not self.session.players:
            return {}
        
        player_count = len(self.session.players)
        if player_count == 0:
            return {}
        
        # 균등 분배
        base_gold = total_gold // player_count
        remainder = total_gold % player_count
        
        distribution: Dict[str, int] = {}
        
        for player_id in self.session.players.keys():
            distribution[player_id] = base_gold
        
        # 나머지는 호스트에게 (호스트가 플레이어 목록에 있는 경우에만)
        if remainder > 0 and self.session.host_id and self.session.host_id in distribution:
            distribution[self.session.host_id] += remainder
        
        logger.info(f"골드 분배: {total_gold} -> {distribution}")
        
        return distribution
    
    def get_loot_pool(self) -> List[Any]:
        """현재 전리품 풀 반환"""
        return self.loot_pool
    
    def is_empty(self) -> bool:
        """전리품 풀이 비었는지 확인"""
        return len(self.loot_pool) == 0


class StorageSyncManager:
    """
    창고 동기화 매니저
    
    멀티플레이에서 호스트 창고를 모든 플레이어가 공유
    """
    
    def __init__(self, session: Any, network_manager: Any = None):
        """
        Args:
            session: 멀티플레이 세션
            network_manager: 네트워크 매니저
        """
        self.session = session
        self.network_manager = network_manager
        
        # 호스트 창고 참조
        self._host_storage: Optional[Any] = None
        
        logger.info("창고 동기화 매니저 초기화")
    
    def set_host_storage(self, storage: Any):
        """
        호스트 창고 설정
        
        Args:
            storage: 창고 객체
        """
        self._host_storage = storage
        logger.info("호스트 창고 설정 완료")
    
    def get_storage_for_player(self, player_id: str) -> Optional[Any]:
        """
        플레이어용 창고 반환 (모든 플레이어가 호스트 창고 공유)
        
        Args:
            player_id: 플레이어 ID
            
        Returns:
            창고 객체 (호스트 창고)
        """
        return self._host_storage
    
    def request_add_item(self, player_id: str, item: Any) -> bool:
        """
        창고에 아이템 추가 요청
        
        Args:
            player_id: 요청 플레이어 ID
            item: 추가할 아이템
            
        Returns:
            성공 여부
        """
        if not self._host_storage:
            logger.warning("호스트 창고가 설정되지 않음")
            return False
        
        try:
            result = self._host_storage.add_item(item)
            
            if result:
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                logger.info(f"창고 아이템 추가: {item_name} (by {player_id})")
                
                # 동기화 브로드캐스트
                self._broadcast_storage_update()
            
            return result
            
        except Exception as e:
            logger.error(f"창고 아이템 추가 실패: {e}")
            return False
    
    def request_remove_item(self, player_id: str, index: int) -> Optional[Any]:
        """
        창고에서 아이템 제거 요청
        
        Args:
            player_id: 요청 플레이어 ID
            index: 슬롯 인덱스
            
        Returns:
            제거된 아이템 (없으면 None)
        """
        if not self._host_storage:
            logger.warning("호스트 창고가 설정되지 않음")
            return None
        
        try:
            item = self._host_storage.remove_item(index)
            
            if item:
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                logger.info(f"창고 아이템 제거: {item_name} (by {player_id})")
                
                # 동기화 브로드캐스트
                self._broadcast_storage_update()
            
            return item
            
        except Exception as e:
            logger.error(f"창고 아이템 제거 실패: {e}")
            return None
    
    def _broadcast_storage_update(self):
        """창고 변경 브로드캐스트"""
        if not self.network_manager:
            return
        
        try:
            from src.multiplayer.protocol import NetworkMessage, MessageType

            message = NetworkMessage(
                type=MessageType.GAME_STATE,
                data={
                    "action": "storage_update",
                    "storage_size": len(self._host_storage.items) if hasattr(self._host_storage, 'items') else 0
                }
            )

            # 비동기 브로드캐스트
            import asyncio
            if hasattr(self.network_manager, '_server_event_loop') and self.network_manager._server_event_loop:
                asyncio.run_coroutine_threadsafe(
                    self.network_manager.broadcast(message),
                    self.network_manager._server_event_loop
                )
            else:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.network_manager.broadcast(message))
                
        except Exception as e:
            logger.error(f"창고 동기화 브로드캐스트 실패: {e}")


# 전역 인스턴스
_loot_sync_manager: Optional[LootSyncManager] = None
_storage_sync_manager: Optional[StorageSyncManager] = None


def get_loot_sync_manager() -> Optional[LootSyncManager]:
    """전역 전리품 동기화 매니저 반환"""
    return _loot_sync_manager


def set_loot_sync_manager(manager: LootSyncManager):
    """전역 전리품 동기화 매니저 설정"""
    global _loot_sync_manager
    _loot_sync_manager = manager


def get_storage_sync_manager() -> Optional[StorageSyncManager]:
    """전역 창고 동기화 매니저 반환"""
    return _storage_sync_manager


def set_storage_sync_manager(manager: StorageSyncManager):
    """전역 창고 동기화 매니저 설정"""
    global _storage_sync_manager
    _storage_sync_manager = manager
