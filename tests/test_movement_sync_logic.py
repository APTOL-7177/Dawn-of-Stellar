"""
MovementSyncManager 로직 단위 테스트

경쟁 상태 및 타임스탬프 처리를 집중적으로 테스트합니다.
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock

from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.protocol import MessageType, NetworkMessage, MessageBuilder

class TestMovementSyncLogic:
    """이동 동기화 로직 테스트"""
    
    @pytest.fixture
    def session(self):
        """세션 픽스처"""
        session = MultiplayerSession(max_players=4)
        player = MultiplayerPlayer(player_id="p1", player_name="TestPlayer")
        session.add_player(player)
        return session

    @pytest.fixture
    def manager(self, session):
        """매니저 픽스처"""
        network = MagicMock()
        manager = MovementSyncManager(session, network_manager=network, is_host=True)
        return manager

    @pytest.mark.asyncio
    async def test_out_of_order_packets(self, session, manager):
        """순서가 뒤바뀐 패킷 처리 테스트"""
        player = session.get_player("p1")
        
        # 초기 상태
        assert player.x == 0
        assert player.y == 0
        
        current_time = time.time()
        
        # 1. 최신 패킷 수신 (t=10) -> (10, 10)
        msg_latest = MessageBuilder.player_move("p1", 10, 10, timestamp=current_time + 10)
        await manager._handle_player_move(msg_latest)
        
        assert player.x == 10
        assert player.y == 10
        assert player.last_movement_timestamp == current_time + 10
        
        # 2. 과거 패킷 수신 (t=5) -> (5, 5)
        # 이 패킷은 무시되어야 함
        msg_old = MessageBuilder.player_move("p1", 5, 5, timestamp=current_time + 5)
        await manager._handle_player_move(msg_old)
        
        assert player.x == 10  # 변하지 않아야 함
        assert player.y == 10
        assert player.last_movement_timestamp == current_time + 10  # 타임스탬프도 유지
        
        # 3. 더 최신 패킷 수신 (t=20) -> (20, 20)
        msg_newest = MessageBuilder.player_move("p1", 20, 20, timestamp=current_time + 20)
        await manager._handle_player_move(msg_newest)
        
        assert player.x == 20
        assert player.y == 20
        assert player.last_movement_timestamp == current_time + 20

    @pytest.mark.asyncio
    async def test_host_priority_logic(self, session, manager):
        """호스트 우선권 로직 테스트 (타임스탬프 로직과 충돌 여부 확인)"""
        # 호스트 플레이어 설정
        session.host_id = "p1"
        player = session.get_player("p1")
        player.is_host = True
        
        current_time = time.time()
        
        # 1. 호스트 패킷 수신
        msg = MessageBuilder.player_move("p1", 10, 10, timestamp=current_time + 10)
        await manager._handle_player_move(msg)
        
        assert player.x == 10
        assert player.y == 10
        
        # 2. 호스트의 과거 패킷 수신
        # 호스트라 하더라도 타임스탬프가 더 낮으면 무시되어야 함 (순서가 꼬인 것이므로)
        msg_old = MessageBuilder.player_move("p1", 5, 5, timestamp=current_time + 5)
        await manager._handle_player_move(msg_old)
        
        assert player.x == 10  # 무시되어야 함
        assert player.y == 10
