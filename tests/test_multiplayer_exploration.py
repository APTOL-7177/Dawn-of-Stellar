"""
멀티플레이 탐험 시스템 테스트

혼자서도 테스트할 수 있는 모의 클라이언트를 사용합니다.
"""

import pytest
import asyncio
from src.multiplayer.test_helper import create_test_session, MultiplayerTestHelper
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
from src.world.dungeon_generator import DungeonMap


class TestMultiplayerExploration:
    """멀티플레이 탐험 테스트"""
    
    def test_create_test_session(self):
        """테스트 세션 생성 테스트"""
        session, helper = create_test_session(player_count=2)
        
        assert session is not None
        assert helper is not None
        assert len(session.players) == 2
        assert session.host_id is not None
        
        # 호스트 확인
        host = session.players[session.host_id]
        assert host.is_host is True
        assert host.player_name == "호스트"
        
        # 봇 확인
        bot_count = len([p for p in session.players.values() if not p.is_host])
        assert bot_count == 1
    
    def test_add_mock_clients(self):
        """모의 클라이언트 추가 테스트"""
        session = MultiplayerSession(max_players=4)
        
        # 호스트 추가
        host = MultiplayerPlayer(
            player_id="host",
            player_name="호스트",
            is_host=True
        )
        session.add_player(host)
        session.host_id = host.player_id
        
        helper = MultiplayerTestHelper(session)
        
        # 봇 2명 추가
        bot1 = helper.add_mock_client("봇1")
        bot2 = helper.add_mock_client("봇2")
        
        assert len(session.players) == 3
        assert bot1.player_id in session.players
        assert bot2.player_id in session.players
    
    def test_player_positions(self):
        """플레이어 위치 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 플레이어 위치 확인
        positions = helper.get_player_positions()
        
        assert len(positions) == 2
        
        # 각 플레이어의 위치가 설정되어 있는지 확인
        for player_id, (x, y) in positions.items():
            assert isinstance(x, int)
            assert isinstance(y, int)
            assert x >= 0
            assert y >= 0
    
    def test_mock_client_movement(self):
        """모의 클라이언트 이동 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 첫 번째 봇 가져오기
        mock_client = helper.mock_clients[0]
        initial_x = mock_client.x
        initial_y = mock_client.y
        
        # 랜덤 이동 생성
        dx, dy = mock_client.generate_random_move()
        
        # 이동이 생성되었는지 확인
        assert isinstance(dx, int)
        assert isinstance(dy, int)
        assert -1 <= dx <= 1
        assert -1 <= dy <= 1
    
    def test_auto_simulation_setup(self):
        """자동 시뮬레이션 설정 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 시뮬레이션 초기 상태 확인
        assert helper.is_running is False
        assert helper.mock_clients is not None
        assert len(helper.mock_clients) > 0
    
    def test_multiplayer_exploration_initialization(self):
        """멀티플레이 탐험 시스템 초기화 테스트"""
        # 테스트 세션 생성
        session, helper = create_test_session(player_count=2)
        
        # 더미 던전 생성 (실제로는 DungeonGenerator 사용)
        from src.world.dungeon_generator import DungeonMap
        dungeon = DungeonMap(width=50, height=50)
        dungeon.rooms = []  # 빈 방 리스트
        
        # 멀티플레이 탐험 시스템 생성
        exploration = MultiplayerExplorationSystem(
            dungeon=dungeon,
            party=[],
            floor_number=1,
            session=session,
            network_manager=None,
            local_player_id=session.host_id
        )
        
        assert exploration.is_multiplayer is True
        assert exploration.session is not None
        
        # 플레이어 위치가 초기화되었는지 확인
        assert len(exploration.player_positions) > 0


def test_local_multiplayer_simulation_setup():
    """로컬 멀티플레이 시뮬레이션 설정 테스트"""
    # 2인 세션 생성
    session, helper = create_test_session(player_count=2)
    
    # 초기 위치 확인
    initial_positions = helper.get_player_positions()
    
    # 위치가 설정되었는지 확인
    assert len(initial_positions) == 2
    
    # 각 플레이어의 위치가 유효한지 확인
    for player_id, (x, y) in initial_positions.items():
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert x >= 0
        assert y >= 0

