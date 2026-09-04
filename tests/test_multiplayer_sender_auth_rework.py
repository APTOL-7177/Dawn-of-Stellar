"""
sender-bound 인가 재수정 회귀 테스트 (t_8cd83a09)

t_910fbd0f의 리뷰 반영 재작업 검증:
1) host transport 경유 메시지(sender=HOST_TRANSPORT_SENDER)는 payload actor를 신뢰
2) last_authorized_position이 좌표계 전환 경로에서 재인가됨
3) combat_sync/network의 무관 변경 원복 확인
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.network import ClientNetworkManager, NetworkManager
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.player_state import PlayerStateManager
from src.multiplayer.protocol import MessageBuilder, MessageType, NetworkMessage
from src.multiplayer.session import MultiplayerSession


HOST_TRANSPORT = ClientNetworkManager.HOST_TRANSPORT_SENDER


# ──────────────────────────────────────────────────────────────
# 1. host transport sender와 payload actor 분리
# ──────────────────────────────────────────────────────────────


class TestHostTransportSender:
    def test_host_transport_marker_is_not_a_player_id(self):
        """표식은 리터럴 'host' 같은 충돌 소지가 없는 별도 값이어야 한다"""
        assert HOST_TRANSPORT != "host"
        assert isinstance(HOST_TRANSPORT, str)

    def test_client_receive_loop_uses_marker_not_host_literal(self):
        """클라이언트 수신 루프가 'host' 리터럴 대신 표식 상수를 쓰는지"""
        import inspect
        src = inspect.getsource(ClientNetworkManager)
        assert '"host")' not in src
        assert "HOST_TRANSPORT_SENDER" in src

    def test_host_transport_trusts_payload_actor(self):
        """host transport 경유 메시지: payload player_id가 실제 actor"""
        msg = MessageBuilder.player_move(player_id="host-uuid-123", x=3, y=4)
        assert msg.resolve_sender_player_id(HOST_TRANSPORT) == "host-uuid-123"

    def test_host_transport_with_empty_payload_is_none(self):
        msg = NetworkMessage(type=MessageType.PLAYER_MOVE, player_id=None, data={})
        assert msg.resolve_sender_player_id(HOST_TRANSPORT) is None

    def test_direct_connection_still_sender_bound(self):
        """서버-클라이언트 직접 연결(sender=client)은 여전히 sender-bound"""
        msg = MessageBuilder.player_move(player_id="victim", x=9, y=9)
        assert msg.resolve_sender_player_id("client") is None

    def test_host_self_move_via_client_dispatcher(self):
        """
        실제 client receive dispatcher 시나리오: 호스트가 자기 이동을
        broadcast하면 클라이언트는 transport sender=표식으로 받는다.
        payload actor(호스트 UUID)대로 적용되어야 한다.
        """
        session = MultiplayerSession(max_players=4)
        session.add_player(MultiplayerPlayer(player_id="host-uuid", player_name="H", is_host=True))
        session.add_player(MultiplayerPlayer(player_id="client-uuid", player_name="C"))
        sync = MovementSyncManager(session=session, is_host=False)
        host_player = session.players["host-uuid"]
        host_player.x = 10
        host_player.y = 10

        # 호스트 → 클라이언트 릴레이(호스트가 자기 이동 broadcast)
        msg = MessageBuilder.player_move(player_id="host-uuid", x=11, y=10)
        asyncio.run(sync._handle_player_move(msg, sender_id=HOST_TRANSPORT))
        assert (host_player.x, host_player.y) == (11, 10)

    def test_relayed_client_move_via_client_dispatcher(self):
        """다른 클라이언트 이동도 host transport로 릴레이되어 actor대로 적용"""
        session = MultiplayerSession(max_players=4)
        session.add_player(MultiplayerPlayer(player_id="host-uuid", player_name="H", is_host=True))
        session.add_player(MultiplayerPlayer(player_id="client-a", player_name="A"))
        session.add_player(MultiplayerPlayer(player_id="client-b", player_name="B"))
        sync = MovementSyncManager(session=session, is_host=False)
        b = session.players["client-b"]

        msg = MessageBuilder.player_move(player_id="client-b", x=2, y=2)
        asyncio.run(sync._handle_player_move(msg, sender_id=HOST_TRANSPORT))
        assert (b.x, b.y) == (2, 2)

    def test_spoofed_payload_via_marker_still_respects_actor_check(self):
        """표식 경유라도 payload actor가 세션에 없으면 상태 변경 불가"""
        session = MultiplayerSession(max_players=4)
        session.add_player(MultiplayerPlayer(player_id="host-uuid", player_name="H", is_host=True))
        sync = MovementSyncManager(session=session, is_host=False)

        # 세션에 없는 플레이어 명의 → 핸들러가 조기 반환 (상태 없음 확인만)
        msg = MessageBuilder.player_move(player_id="ghost", x=1, y=1)
        asyncio.run(sync._handle_player_move(msg, sender_id=HOST_TRANSPORT))
        assert "ghost" not in session.players


# ──────────────────────────────────────────────────────────────
# 2. last_authorized_position 재인가
# ──────────────────────────────────────────────────────────────


class _FakeDungeon:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height
        self.rooms = []

    def is_walkable(self, x, y):
        return True


def _make_exploration(session):
    dungeon = _FakeDungeon()
    exploration = MultiplayerExplorationSystem.__new__(MultiplayerExplorationSystem)
    exploration.dungeon = dungeon
    exploration.session = session
    exploration.local_player_id = "host"
    exploration.player = MagicMock()
    exploration.player.x = 5
    exploration.player.y = 5
    exploration.player_positions = {}
    exploration.logger = MagicMock()
    exploration.fov_system = MagicMock()
    exploration.explored_tiles = set()
    return exploration


class TestPositionReauthorization:
    def test_spawn_reauthorizes_position(self):
        """스폰 위치 결정 후 인가 기준점이 그 좌표로 설정"""
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="host", player_name="H", is_host=True)
        p.x, p.y = 7, 8
        session.add_player(p)
        exploration = _make_exploration(session)

        exploration._initialize_player_positions()
        assert p.last_authorized_position is not None
        # 위치가 유지되는 경로든 재탐색 경로든 현재 x,y와 일치
        assert p.last_authorized_position == (int(p.x), int(p.y))

    def test_rollback_reauthorizes_position(self):
        """rejection rollback 후 새 기준점 = 롤백 좌표 (무한 루프 방지)"""
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="host", player_name="H", is_host=True)
        p.x, p.y = 5, 5
        p.last_authorized_position = (5, 5)
        session.add_player(p)
        exploration = _make_exploration(session)

        exploration.rollback_player_position(3, 4)
        assert p.last_authorized_position == (3, 4)

    def test_no_rejection_loop_after_rollback(self):
        """롤백 후 같은 좌표에서 인접 이동하면 거부되지 않는다"""
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="host", player_name="H", is_host=True)
        p.x, p.y = 5, 5
        p.last_authorized_position = (5, 5)
        session.add_player(p)
        exploration = _make_exploration(session)

        # 원격 이동 거부 → (3,4) 롤백
        exploration.rollback_player_position(3, 4)

        # 다시 (3,4) 인접 이동은 인접 검사 통과해야 함
        sync = MovementSyncManager(session=session, is_host=True)
        msg = MessageBuilder.player_move(player_id="host", x=4, y=4)
        asyncio.run(sync._handle_player_move(msg, sender_id=None))
        assert p.last_authorized_position == (4, 4)

    def test_revival_reauthorizes_position(self):
        """부활 위치가 곧 인가 기준점"""
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="client", player_name="C")
        p.x, p.y = 5, 5
        p.last_authorized_position = (5, 5)
        session.add_player(p)
        manager = PlayerStateManager()
        revived = MagicMock()
        revived.name = "Hero"

        x, y = manager.handle_character_revival(p, revived, revive_position=(9, 9))
        assert (x, y) == (9, 9)
        assert p.last_authorized_position == (9, 9)


# ──────────────────────────────────────────────────────────────
# 3. sender-bound와 무관한 변경 원복 확인
# ──────────────────────────────────────────────────────────────


class TestUnrelatedChangesReverted:
    def test_heartbeat_interval_restored(self):
        from src.multiplayer.combat_sync import CombatSyncManager
        session = MultiplayerSession(max_players=2)
        sync = CombatSyncManager(session=session, is_host=True)
        assert sync._heartbeat_interval == 0.2

    def test_no_action_lock_attribute(self):
        from src.multiplayer.combat_sync import CombatSyncManager
        session = MultiplayerSession(max_players=2)
        sync = CombatSyncManager(session=session, is_host=True)
        assert not hasattr(sync, "_action_lock")

    def test_no_fallback_target_logic(self):
        import inspect
        from src.multiplayer.combat_sync import CombatSyncManager
        src = inspect.getsource(CombatSyncManager)
        assert "폴백 타겟" not in src

    def test_no_collision_enemy_side_effect(self):
        import inspect
        from src.multiplayer.network import NetworkManager
        src = inspect.getsource(NetworkManager)
        assert "collision_enemy = enemies" not in src
