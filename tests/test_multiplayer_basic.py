"""
멀티플레이 기본 테스트

Phase 1: 기반 구조 테스트
"""

import pytest
import asyncio
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.protocol import NetworkMessage, MessageType, MessageBuilder
from src.multiplayer.config import MultiplayerConfig


class TestMultiplayerPlayer:
    """플레이어 객체 테스트"""
    
    def test_player_creation(self):
        """플레이어 생성 테스트"""
        player = MultiplayerPlayer(
            player_id="test_player_1",
            player_name="테스트 플레이어"
        )
        
        assert player.player_id == "test_player_1"
        assert player.player_name == "테스트 플레이어"
        assert player.x == 0
        assert player.y == 0
        assert player.is_connected is True
    
    def test_player_position_update(self):
        """플레이어 위치 업데이트 테스트"""
        player = MultiplayerPlayer(
            player_id="test_player_1",
            player_name="테스트 플레이어"
        )
        
        player.update_position(10, 20)
        
        assert player.x == 10
        assert player.y == 20
        assert player.velocity_x == 10
        assert player.velocity_y == 20
    
    def test_player_serialization(self):
        """플레이어 직렬화 테스트"""
        player = MultiplayerPlayer(
            player_id="test_player_1",
            player_name="테스트 플레이어",
            x=10,
            y=20
        )
        
        serialized = player.serialize()
        
        assert serialized["player_id"] == "test_player_1"
        assert serialized["player_name"] == "테스트 플레이어"
        assert serialized["x"] == 10
        assert serialized["y"] == 20


class TestMultiplayerSession:
    """세션 관리 테스트"""
    
    def test_session_creation(self):
        """세션 생성 테스트"""
        session = MultiplayerSession(max_players=4)
        
        assert session.max_players == 4
        assert session.player_count == 0
        assert session.session_id is not None
        assert session.session_seed is not None
        assert session.is_active is True
    
    def test_add_player(self):
        """플레이어 추가 테스트"""
        session = MultiplayerSession(max_players=4)
        player = MultiplayerPlayer(
            player_id="test_player_1",
            player_name="테스트 플레이어"
        )
        
        success = session.add_player(player)
        
        assert success is True
        assert session.player_count == 1
        assert session.host_id == "test_player_1"
        assert "test_player_1" in session.players
    
    def test_add_player_max_limit(self):
        """최대 인원 제한 테스트"""
        session = MultiplayerSession(max_players=2)
        
        # 2명 추가
        for i in range(2):
            player = MultiplayerPlayer(
                player_id=f"test_player_{i}",
                player_name=f"테스트 플레이어 {i}"
            )
            session.add_player(player)
        
        # 3번째 플레이어 추가 시도 (실패해야 함)
        player3 = MultiplayerPlayer(
            player_id="test_player_3",
            player_name="테스트 플레이어 3"
        )
        success = session.add_player(player3)
        
        assert success is False
        assert session.player_count == 2
    
    def test_remove_player(self):
        """플레이어 제거 테스트"""
        session = MultiplayerSession(max_players=4)
        player = MultiplayerPlayer(
            player_id="test_player_1",
            player_name="테스트 플레이어"
        )
        session.add_player(player)
        
        success = session.remove_player("test_player_1")
        
        assert success is True
        assert session.player_count == 0
        assert "test_player_1" not in session.players
    
    def test_host_migration(self):
        """호스트 마이그레이션 테스트"""
        session = MultiplayerSession(max_players=4)
        
        # 첫 번째 플레이어 (호스트)
        player1 = MultiplayerPlayer(
            player_id="player_1",
            player_name="플레이어 1"
        )
        session.add_player(player1)
        
        # 두 번째 플레이어
        player2 = MultiplayerPlayer(
            player_id="player_2",
            player_name="플레이어 2"
        )
        session.add_player(player2)
        
        assert session.host_id == "player_1"
        
        # 호스트 제거
        session.remove_player("player_1")
        
        # 두 번째 플레이어가 호스트가 되어야 함
        assert session.host_id == "player_2"
    
    def test_dungeon_seed_generation(self):
        """던전 시드 생성 테스트"""
        session = MultiplayerSession(max_players=4)
        
        # 같은 층은 항상 같은 시드
        seed1 = session.generate_dungeon_seed_for_floor(1)
        seed2 = session.generate_dungeon_seed_for_floor(1)
        
        assert seed1 == seed2
        
        # 다른 층은 다른 시드
        seed3 = session.generate_dungeon_seed_for_floor(2)
        assert seed1 != seed3


class TestNetworkProtocol:
    """네트워크 프로토콜 테스트"""
    
    def test_message_creation(self):
        """메시지 생성 테스트"""
        message = NetworkMessage(
            type=MessageType.CONNECT,
            player_id="test_player_1",
            data={"test": "data"}
        )
        
        assert message.type == MessageType.CONNECT
        assert message.player_id == "test_player_1"
        assert message.data["test"] == "data"
    
    def test_message_serialization(self):
        """메시지 직렬화 테스트"""
        message = NetworkMessage(
            type=MessageType.CONNECT,
            player_id="test_player_1",
            data={"test": "data"}
        )
        
        json_str = message.to_json()
        assert isinstance(json_str, str)
        
        # 역직렬화
        message2 = NetworkMessage.from_json(json_str)
        
        assert message2.type == message.type
        assert message2.player_id == message.player_id
        assert message2.data == message.data
    
    def test_message_builder(self):
        """메시지 빌더 테스트"""
        # 연결 메시지
        connect_msg = MessageBuilder.connect("player_1", "테스트 플레이어", "5.0.0")
        
        assert connect_msg.type == MessageType.CONNECT
        assert connect_msg.player_id == "player_1"
        assert connect_msg.data["player_name"] == "테스트 플레이어"
        assert connect_msg.data["version"] == "5.0.0"
        
        # 플레이어 이동 메시지
        move_msg = MessageBuilder.player_move("player_1", 10, 20)
        
        assert move_msg.type == MessageType.PLAYER_MOVE
        assert move_msg.player_id == "player_1"
        assert move_msg.data["x"] == 10
        assert move_msg.data["y"] == 20
    
    def test_message_compression(self):
        """메시지 압축 테스트"""
        # 큰 데이터가 있는 메시지
        large_data = {"data": "x" * 5000}  # 5KB 데이터
        message = NetworkMessage(
            type=MessageType.CHAT_MESSAGE,
            player_id="player_1",
            data=large_data
        )
        
        # 압축
        compressed = message.compress()
        assert isinstance(compressed, bytes)
        assert len(compressed) < len(message.to_json())
        
        # 압축 해제
        decompressed = NetworkMessage.decompress(compressed)
        
        assert decompressed.type == message.type
        assert decompressed.player_id == message.player_id
        assert decompressed.data == message.data


class TestMultiplayerConfig:
    """멀티플레이 설정 테스트"""
    
    def test_config_constants(self):
        """설정 상수 테스트"""
        assert MultiplayerConfig.action_wait_time == 1.5
        assert MultiplayerConfig.atb_reduction_multiplier == 0.02  # 1/50
        assert MultiplayerConfig.participation_radius == 5
        assert MultiplayerConfig.message_compression is True
        assert MultiplayerConfig.max_latency_allowed == 0.5
    
    def test_config_instance(self):
        """설정 인스턴스 테스트"""
        config = MultiplayerConfig()
        
        assert config.action_wait_time == 1.5
        assert config.atb_reduction_multiplier == 0.02
        assert config.participation_radius == 5

