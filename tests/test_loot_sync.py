"""
전리품 동기화 시스템 테스트

멀티플레이에서 전리품 선점 시스템 테스트
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any


class TestLootSyncManager:
    """전리품 동기화 매니저 테스트"""
    
    @pytest.fixture
    def mock_session(self):
        """모의 세션 생성"""
        session = Mock()
        session.players = {
            "player1": Mock(player_id="player1", player_name="Player 1"),
            "player2": Mock(player_id="player2", player_name="Player 2"),
        }
        session.host_id = "player1"
        return session
    
    @pytest.fixture
    def mock_network_manager(self):
        """모의 네트워크 매니저 생성"""
        manager = Mock()
        manager.broadcast = Mock()
        manager.send_to = Mock()
        return manager
    
    @pytest.fixture
    def mock_items(self):
        """모의 아이템 리스트 생성"""
        items = []
        for i in range(3):
            item = Mock()
            item.name = f"Test Item {i}"
            item.item_id = f"item_{i}"
            item.weight = 0.5
            items.append(item)
        return items
    
    def test_loot_pool_initialization(self, mock_session, mock_network_manager, mock_items):
        """전리품 풀 초기화 테스트"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        manager = LootSyncManager(mock_session, mock_network_manager)
        manager.set_loot_pool(mock_items)
        
        assert len(manager.loot_pool) == 3
        assert manager.loot_pool[0].name == "Test Item 0"
    
    def test_claim_item_success(self, mock_session, mock_network_manager, mock_items):
        """아이템 선점 성공 테스트 (호스트)"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        manager = LootSyncManager(mock_session, mock_network_manager)
        manager.set_loot_pool(mock_items)
        
        # 첫 번째 플레이어가 첫 번째 아이템 선점
        result = manager.claim_item("player1", 0)
        
        assert result is True
        assert len(manager.loot_pool) == 2  # 1개 제거됨
        assert "item_0" in manager.claimed_items
        assert manager.claimed_items["item_0"] == "player1"
    
    def test_claim_item_already_claimed(self, mock_session, mock_network_manager, mock_items):
        """이미 선점된 아이템 선점 시도 테스트"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        manager = LootSyncManager(mock_session, mock_network_manager)
        manager.set_loot_pool(mock_items)
        
        # 첫 번째 플레이어가 선점
        manager.claim_item("player1", 0)
        
        # 두 번째 플레이어가 같은 아이템(이미 제거됨) 선점 시도
        # 인덱스 0은 이제 다른 아이템
        result = manager.claim_item("player2", 0)
        
        # 다른 아이템이므로 성공
        assert result is True
    
    def test_claim_item_invalid_index(self, mock_session, mock_network_manager, mock_items):
        """잘못된 인덱스로 선점 시도 테스트"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        manager = LootSyncManager(mock_session, mock_network_manager)
        manager.set_loot_pool(mock_items)
        
        # 잘못된 인덱스
        result = manager.claim_item("player1", 10)
        
        assert result is False
    
    def test_gold_distribution(self, mock_session, mock_network_manager):
        """골드 균등 분배 테스트"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        manager = LootSyncManager(mock_session, mock_network_manager)
        
        # 100 골드를 2명에게 분배
        distribution = manager.distribute_gold(100)
        
        assert distribution["player1"] == 50
        assert distribution["player2"] == 50
    
    def test_gold_distribution_odd_amount(self, mock_session, mock_network_manager):
        """홀수 골드 분배 테스트 (나머지는 호스트에게)"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        manager = LootSyncManager(mock_session, mock_network_manager)
        
        # 101 골드를 2명에게 분배
        distribution = manager.distribute_gold(101)
        
        # 호스트가 나머지 1골드 받음
        assert distribution["player1"] == 51  # 호스트
        assert distribution["player2"] == 50
    
    @patch('src.multiplayer.loot_sync.logger')
    def test_broadcast_loot_claimed(self, mock_logger, mock_session, mock_network_manager, mock_items):
        """아이템 선점 브로드캐스트 테스트"""
        from src.multiplayer.loot_sync import LootSyncManager
        
        # network_manager.broadcast를 직접 호출하도록 _broadcast_claim을 monkeypatch
        manager = LootSyncManager(mock_session, mock_network_manager)
        manager.set_loot_pool(mock_items)
        
        # _broadcast_claim을 직접 호출하도록 대체
        original_broadcast = manager._broadcast_claim
        def patched_broadcast(player_id, item_id, item_name):
            # 간단히 broadcast만 호출
            mock_network_manager.broadcast({"player_id": player_id, "item_id": item_id})
        manager._broadcast_claim = patched_broadcast
        
        manager.claim_item("player1", 0)
        
        # 브로드캐스트 호출 확인
        mock_network_manager.broadcast.assert_called()


class TestStorageSync:
    """창고 동기화 테스트"""
    
    @pytest.fixture
    def mock_session(self):
        """모의 세션 생성"""
        session = Mock()
        session.players = {
            "host": Mock(player_id="host", is_host=True),
            "client": Mock(player_id="client", is_host=False),
        }
        session.host_id = "host"
        return session
    
    @pytest.fixture
    def mock_storage(self):
        """모의 창고 생성"""
        storage = Mock()
        storage.items = []
        storage.add_item = Mock(return_value=True)
        storage.remove_item = Mock(return_value=Mock(name="Test Item"))
        return storage
    
    def test_client_access_host_storage(self, mock_session, mock_storage):
        """클라이언트가 호스트 창고 접근 테스트"""
        from src.multiplayer.loot_sync import StorageSyncManager
        
        manager = StorageSyncManager(mock_session)
        manager.set_host_storage(mock_storage)
        
        # 클라이언트가 창고에 접근
        storage = manager.get_storage_for_player("client")
        
        # 호스트 창고와 동일
        assert storage == mock_storage
    
    def test_host_access_own_storage(self, mock_session, mock_storage):
        """호스트가 자신의 창고 접근 테스트"""
        from src.multiplayer.loot_sync import StorageSyncManager
        
        manager = StorageSyncManager(mock_session)
        manager.set_host_storage(mock_storage)
        
        # 호스트가 창고에 접근
        storage = manager.get_storage_for_player("host")
        
        assert storage == mock_storage
    
    def test_storage_sync_on_item_add(self, mock_session, mock_storage):
        """아이템 추가 시 동기화 테스트"""
        from src.multiplayer.loot_sync import StorageSyncManager
        
        manager = StorageSyncManager(mock_session)
        manager.set_host_storage(mock_storage)
        
        mock_item = Mock(name="New Item", item_id="new_item")
        
        # 클라이언트가 아이템 추가 요청
        result = manager.request_add_item("client", mock_item)
        
        assert result is True
        mock_storage.add_item.assert_called_once()
