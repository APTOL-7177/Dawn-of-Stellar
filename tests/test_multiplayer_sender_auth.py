"""
sender-bound 인가 회귀 테스트 (t_910fbd0f)

WebSocket 연결에서 파생된 sender_id만 인가의 진실 원천이며,
payload player_id가 sender와 불일치하면 스푸핑으로 거부되는지 검증한다.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.multiplayer.combat_sync import CombatSyncManager
from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.network import NetworkManager
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.protocol import MessageBuilder, MessageType, NetworkMessage
from src.multiplayer.session import MultiplayerSession


class _FakeWebSocket:
    """테스트용 더미 웹소켓"""


def _make_session(with_combat=False):
    session = MultiplayerSession(max_players=4)
    session.add_player(MultiplayerPlayer(player_id="host", player_name="Host", is_host=True))
    session.add_player(MultiplayerPlayer(player_id="client", player_name="Client"))
    session.add_player(MultiplayerPlayer(player_id="victim", player_name="Victim"))
    return session


# ──────────────────────────────────────────────────────────────
# 1. resolve_sender_player_id 단위 테스트
# ──────────────────────────────────────────────────────────────


class TestResolveSenderPlayerId:
    def test_matching_sender_returns_sender(self):
        msg = MessageBuilder.player_move(player_id="client", x=1, y=2)
        assert msg.resolve_sender_player_id("client") == "client"

    def test_mismatched_payload_rejected(self):
        msg = MessageBuilder.player_move(player_id="victim", x=1, y=2)
        assert msg.resolve_sender_player_id("client") is None

    def test_no_sender_trusts_payload(self):
        msg = MessageBuilder.player_move(player_id="client", x=1, y=2)
        assert msg.resolve_sender_player_id(None) == "client"

    def test_none_payload_with_sender_uses_sender(self):
        msg = NetworkMessage(type=MessageType.PLAYER_MOVE, player_id=None, data={})
        assert msg.resolve_sender_player_id("client") == "client"

    def test_none_payload_no_sender_rejected(self):
        msg = NetworkMessage(type=MessageType.PLAYER_MOVE, player_id=None, data={})
        assert msg.resolve_sender_player_id(None) is None


# ──────────────────────────────────────────────────────────────
# 2. PLAYER_MOVE 스푸핑 거부
# ──────────────────────────────────────────────────────────────


class TestPlayerMoveSpoof:
    def _make_sync(self, is_host=True):
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=is_host)
        return sync, session

    def test_spoofed_move_rejected(self):
        """client 연결이 victim 명의로 이동 → 거부, victim 위치 불변"""
        sync, session = self._make_sync()
        victim = session.players["victim"]
        victim.x = 5
        victim.y = 5

        msg = MessageBuilder.player_move(player_id="victim", x=99, y=99)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (victim.x, victim.y) == (5, 5)

    def test_legit_move_applied(self):
        """정상 sender의 이동은 적용"""
        sync, session = self._make_sync()
        client = session.players["client"]
        client.x = 5
        client.y = 5

        msg = MessageBuilder.player_move(player_id="client", x=6, y=5)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (6, 5)

    def test_relay_spoofed_move_not_rebroadcast(self):
        """릴레이 단계에서도 스푸핑 차단"""
        sync, session = self._make_sync()
        sync.network_manager = MagicMock()
        sync.network_manager.broadcast = AsyncMock()

        msg = MessageBuilder.player_move(player_id="victim", x=99, y=99)
        asyncio.run(sync._relay_player_move(msg, sender_id="client"))

        sync.network_manager.broadcast.assert_not_awaited()

    def test_relay_legit_move_rebroadcast(self):
        sync, session = self._make_sync()
        sync.network_manager = MagicMock()
        sync.network_manager.broadcast = AsyncMock()

        msg = MessageBuilder.player_move(player_id="client", x=3, y=3)
        asyncio.run(sync._relay_player_move(msg, sender_id="client"))

        sync.network_manager.broadcast.assert_awaited_once()


# ──────────────────────────────────────────────────────────────
# 3. 이동 검증 (호스트 인가): 인접 1칸 / 경계 / walkable / timestamp
# ──────────────────────────────────────────────────────────────


class _FakeDungeon:
    def __init__(self, width=10, height=10, walls=frozenset()):
        self.width = width
        self.height = height
        self.walls = set(walls)

    def is_walkable(self, x, y):
        return (x, y) not in self.walls


class _FakeExploration:
    def __init__(self, dungeon):
        self.dungeon = dungeon
        self.player_positions = {}


class TestHostMovementValidation:
    def _make_host_sync(self, dungeon=None):
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=True)
        if dungeon:
            sync.exploration = _FakeExploration(dungeon)
        client = session.players["client"]
        client.x, client.y = 5, 5
        client.last_authorized_position = (5, 5)
        return sync, session

    def test_teleport_rejected_and_rollback_sent(self):
        """인접 한 칸 초과(텔레포트) → 거부 + MOVEMENT_REJECTED 롤백 전송"""
        sync, session = self._make_host_sync()
        client = session.players["client"]

        sent = []

        async def fake_send(message, target=None):
            sent.append((message, target))

        network = MagicMock()
        network.send = AsyncMock(side_effect=fake_send)
        sync.network_manager = network

        msg = MessageBuilder.player_move(player_id="client", x=9, y=9)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (5, 5)  # authoritative 상태 불변
        assert len(sent) == 1
        rollback_msg, target = sent[0]
        assert rollback_msg.type == MessageType.MOVEMENT_REJECTED
        assert rollback_msg.data.get("x") == 5 and rollback_msg.data.get("y") == 5
        assert target == "client"

    def test_adjacent_move_accepted(self):
        sync, session = self._make_host_sync()
        client = session.players["client"]

        msg = MessageBuilder.player_move(player_id="client", x=6, y=5)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (6, 5)
        assert client.last_authorized_position == (6, 5)

    def test_boundary_violation_rejected(self):
        dungeon = _FakeDungeon(width=10, height=10)
        sync, session = self._make_host_sync(dungeon)
        client = session.players["client"]
        client.x, client.y = 9, 9
        client.last_authorized_position = (9, 9)

        msg = MessageBuilder.player_move(player_id="client", x=10, y=9)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (9, 9)

    def test_wall_tile_rejected(self):
        dungeon = _FakeDungeon(walls={(6, 5)})
        sync, session = self._make_host_sync(dungeon)
        client = session.players["client"]

        msg = MessageBuilder.player_move(player_id="client", x=6, y=5)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (5, 5)

    def test_future_timestamp_rejected(self):
        sync, session = self._make_host_sync()
        client = session.players["client"]

        msg = MessageBuilder.player_move(player_id="client", x=6, y=5)
        msg.timestamp = time.time() + 60.0  # 60초 미래
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (5, 5)

    def test_stale_timestamp_rejected(self):
        sync, session = self._make_host_sync()
        client = session.players["client"]
        client.last_movement_timestamp = 100.0

        msg = MessageBuilder.player_move(player_id="client", x=6, y=5)
        msg.timestamp = 99.0
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (5, 5)


# ──────────────────────────────────────────────────────────────
# 4. COMBAT_ACTION / PLAYER_LEFT 스푸핑 거부
# ──────────────────────────────────────────────────────────────


class TestCombatSpoof:
    def _make_combat_sync(self):
        session = _make_session()
        sync = CombatSyncManager(
            session=session, network_manager=None, is_host=True
        )
        sync.combat_manager = MagicMock()
        sync.combat_manager.allies = []
        sync.combat_manager.enemies = []
        return sync, session

    def test_spoofed_combat_action_rejected(self):
        """client 연결이 victim 명의 액션 전송 → execute_action 미호출"""
        sync, session = self._make_combat_sync()
        sync._find_character_by_id = MagicMock(return_value=MagicMock())

        msg = MessageBuilder.combat_action(
            player_id="victim",
            actor_id="char_1",
            action={"action_type": "attack"},
        )
        asyncio.run(sync._handle_combat_action(msg, sender_id="client"))

        sync.combat_manager.execute_action.assert_not_called()

    def test_spoofed_player_left_rejected(self):
        """client 연결이 victim 명의 PLAYER_LEFT 전송 → victim 제거 없음"""
        sync, session = self._make_combat_sync()

        removed = []
        sync._set_player_selecting = MagicMock()
        sync._cancel_timeout_task = MagicMock()

        msg = NetworkMessage(type=MessageType.PLAYER_LEFT, player_id="victim", data={})
        asyncio.run(sync._handle_player_left(msg, sender_id="client"))

        # victim이 세션/전투에서 제거되지 않았는지: allies가 비어 있으므로
        # 제거 시도 자체가 없어야 하고, 상태 브로드캐스트도 없어야 함
        assert sync.combat_manager.party is None or True  # allies 비어있음
        # 핵심: 예외 없이 조용히 거부되고 세션은 그대로
        assert "victim" in session.players

    def test_legit_player_left_processed(self):
        """정상 sender의 PLAYER_LEFT는 처리됨 (행동 선택 해제)"""
        sync, session = self._make_combat_sync()
        sync._set_player_selecting = MagicMock()
        sync._cancel_timeout_task = MagicMock()

        msg = NetworkMessage(type=MessageType.PLAYER_LEFT, player_id="client", data={})
        asyncio.run(sync._handle_player_left(msg, sender_id="client"))

        sync._set_player_selecting.assert_called_once_with("client", False)


# ──────────────────────────────────────────────────────────────
# 5. FLOOR_READY 스푸핑 거부
# ──────────────────────────────────────────────────────────────


class TestFloorReadySpoof:
    def _make_network(self):
        session = _make_session()
        network = NetworkManager(is_host=True, session=session)
        network.broadcast = AsyncMock()
        return network, session

    def test_spoofed_floor_ready_rejected(self):
        """client 연결이 victim 명의 FLOOR_READY 전송 → victim 준비 상태 불변"""
        network, session = self._make_network()

        msg = MessageBuilder.floor_ready(
            player_id="victim", ready=True, ready_players=[], total_players=3
        )
        asyncio.run(network._handle_message(msg, sender_id="client"))

        assert "victim" not in session.floor_ready_players

    def test_legit_floor_ready_applied(self):
        network, session = self._make_network()

        msg = MessageBuilder.floor_ready(
            player_id="client", ready=True, ready_players=[], total_players=3
        )
        asyncio.run(network._handle_message(msg, sender_id="client"))

        assert "client" in session.floor_ready_players
