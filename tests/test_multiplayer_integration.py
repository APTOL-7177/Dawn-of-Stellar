"""
멀티플레이 통합 테스트

전체 시스템을 통합하여 테스트합니다.
"""

import pytest
import asyncio
from src.multiplayer.test_helper import create_test_session
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.game_mode import get_game_mode_manager, GameMode
from src.core.logger import get_logger


class TestMultiplayerIntegration:
    """멀티플레이 통합 테스트"""
    
    def test_full_session_lifecycle(self):
        """전체 세션 생명주기 테스트"""
        # 세션 생성
        session, helper = create_test_session(player_count=2)
        
        assert session is not None
        assert len(session.players) == 2
        assert session.host_id is not None
        assert session.is_full() is True  # max_players=2이고 2명이므로 가득 참
        
        # 이미 2명이 있고 max_players=2이므로 가득 참
        # 더 추가 시도 (실패해야 함)
        initial_count = session.player_count
        result = session.add_player(
            MultiplayerPlayer(player_id="should_fail", player_name="실패해야함")
        )
        assert result is False
        assert session.player_count == initial_count
        
        # 4인 세션으로 재생성하여 추가 테스트
        session, helper = create_test_session(player_count=4)
        assert len(session.players) == 4
        assert session.is_full() is True
        
        # 더 추가 시도 (실패해야 함)
        initial_count = session.player_count
        result = session.add_player(
            MultiplayerPlayer(player_id="should_fail2", player_name="실패해야함2")
        )
        assert result is False
        assert session.player_count == initial_count
    
    def test_host_transfer(self):
        """호스트 이전 테스트"""
        session, helper = create_test_session(player_count=3)
        
        original_host_id = session.host_id
        assert original_host_id is not None
        
        # 호스트 플레이어 제거
        session.remove_player(original_host_id)
        
        # 새로운 호스트가 자동으로 선택되었는지 확인
        assert session.host_id is not None
        assert session.host_id != original_host_id
        assert session.host_id in session.players
        
        # 새로운 호스트가 호스트 플래그를 가지고 있는지 확인
        new_host = session.players[session.host_id]
        assert new_host.is_host is True
    
    def test_player_position_sync(self):
        """플레이어 위치 동기화 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 초기 위치 가져오기
        initial_positions = helper.get_player_positions()
        assert len(initial_positions) == 2
        
        # 플레이어 위치 업데이트
        player_id = list(session.players.keys())[0]
        player = session.players[player_id]
        
        old_x, old_y = player.x, player.y
        player.x += 1
        player.y += 1
        
        # 위치가 업데이트되었는지 확인
        new_positions = helper.get_player_positions()
        new_x, new_y = new_positions[player_id]
        
        assert new_x == old_x + 1
        assert new_y == old_y + 1
    
    def test_session_seed_consistency(self):
        """세션 시드 일관성 테스트"""
        session, _ = create_test_session(player_count=2)
        
        original_seed = session.session_seed
        
        # 같은 층에 대한 시드는 항상 같아야 함
        seed1 = session.generate_dungeon_seed_for_floor(1)
        seed2 = session.generate_dungeon_seed_for_floor(1)
        
        assert seed1 == seed2
        
        # 다른 층은 다른 시드
        seed3 = session.generate_dungeon_seed_for_floor(2)
        assert seed1 != seed3
        
        # 세션 시드는 변경되지 않아야 함
        assert session.session_seed == original_seed
    
    def test_game_mode_manager(self):
        """게임 모드 관리자 테스트"""
        manager = get_game_mode_manager()
        
        # 싱글플레이 모드 설정
        manager.set_single_player()
        assert manager.is_single_player() is True
        assert manager.is_multiplayer() is False
        assert manager.get_max_players() == 1
        
        # 멀티플레이 모드 설정 (2인)
        manager.set_multiplayer(player_count=2, is_host=True)
        assert manager.is_single_player() is False
        assert manager.is_multiplayer() is True
        assert manager.get_max_players() == 2
        
        # 멀티플레이 모드 설정 (4인)
        manager.set_multiplayer(player_count=4, is_host=True)
        assert manager.get_max_players() == 4
    
    def test_player_serialization(self):
        """플레이어 직렬화/역직렬화 테스트"""
        original_player = MultiplayerPlayer(
            player_id="test_player",
            player_name="테스트 플레이어"
        )
        original_player.x = 10
        original_player.y = 20
        original_player.is_host = True
        original_player.ping = 50.5
        
        # 직렬화
        serialized = original_player.serialize()
        
        assert serialized["player_id"] == "test_player"
        assert serialized["player_name"] == "테스트 플레이어"
        assert serialized["x"] == 10
        assert serialized["y"] == 20
        assert serialized["ping"] == 50.5
        
        # 역직렬화
        deserialized = MultiplayerPlayer.deserialize(serialized)
        
        assert deserialized.player_id == original_player.player_id
        assert deserialized.player_name == original_player.player_name
        assert deserialized.x == original_player.x
        assert deserialized.y == original_player.y
        assert deserialized.ping == original_player.ping
    
    def test_session_serialization(self):
        """세션 직렬화 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 직렬화
        serialized = session.serialize()
        
        assert "session_id" in serialized
        assert "max_players" in serialized
        assert "host_id" in serialized
        assert "player_count" in serialized
        assert "players" in serialized
        assert len(serialized["players"]) == 2
    
    def test_edge_case_empty_session(self):
        """엣지 케이스: 빈 세션 테스트"""
        session = MultiplayerSession(max_players=2)
        
        # 빈 세션에서 플레이어 제거 시도 (실패해야 함)
        result = session.remove_player("nonexistent")
        assert result is False
        
        # 호스트가 없는 상태에서 호스트 여부 확인
        assert session.is_host("nonexistent") is False
    
    def test_edge_case_duplicate_player(self):
        """엣지 케이스: 중복 플레이어 추가 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 같은 플레이어를 두 번 추가 시도
        player_id = list(session.players.keys())[0]
        player = session.players[player_id]
        
        initial_count = session.player_count
        result = session.add_player(player)
        
        assert result is False
        assert session.player_count == initial_count
    
    def test_edge_case_max_players(self):
        """엣지 케이스: 최대 인원 초과 테스트"""
        session, helper = create_test_session(player_count=4)
        
        # 이미 4명이 있으므로 가득 참
        assert session.is_full() is True
        
        # 더 추가 시도
        new_player = MultiplayerPlayer(
            player_id="overflow",
            player_name="오버플로우"
        )
        result = session.add_player(new_player)
        
        assert result is False
        assert session.player_count == 4
        assert "overflow" not in session.players


class TestMultiplayerErrorHandling:
    """멀티플레이 에러 처리 테스트"""
    
    def test_invalid_player_count(self):
        """잘못된 플레이어 수 테스트"""
        with pytest.raises(ValueError):
            create_test_session(player_count=1)  # 1명은 불가
        
        with pytest.raises(ValueError):
            create_test_session(player_count=5)  # 5명은 불가
    
    def test_invalid_session_operations(self):
        """잘못된 세션 작업 테스트"""
        session, _ = create_test_session(player_count=2)
        
        # 존재하지 않는 플레이어 제거
        result = session.remove_player("nonexistent_id")
        assert result is False
        
        # None 플레이어 추가 시도 (TypeError 발생)
        with pytest.raises(TypeError):
            session.add_player(None)
        
        # 잘못된 타입 추가 시도 (TypeError 발생)
        with pytest.raises(TypeError):
            session.add_player("not_a_player")  # type: ignore
    
    def test_session_integrity(self):
        """세션 무결성 테스트"""
        session, helper = create_test_session(player_count=2)
        
        # 플레이어 제거 후 세션 상태 확인
        player_id = list(session.players.keys())[0]
        session.remove_player(player_id)
        
        # 플레이어 카운트와 실제 딕셔너리 크기가 일치하는지 확인
        assert session.player_count == len(session.players)
        
        # 제거된 플레이어가 실제로 없는지 확인
        assert player_id not in session.players

