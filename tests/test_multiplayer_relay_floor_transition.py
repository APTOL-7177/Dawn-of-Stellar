"""
sender-bound 릴레이·층 전환 이동 인가 회귀 테스트 (t_c10c7a1e)

반려 사유 복구 검증:
1) 클라이언트 수신 루프는 host transport(sender_id="host")로 메시지를 받는다.
   host가 릴레이한 타인의 PLAYER_MOVE(sender="host", payload=원래 player_id)를
   클라이언트가 스푸핑으로 거부하지 않는지 검증한다.
   반대로 호스트는 여전히 sender-bound 스푸핑을 거부해야 한다.
2) last_authorized_position이 층 전환/스폰/전투 종료/롤백 등 좌표계 변경
   경로에서 확정 상태로 초기화되어 첫 이동이 거부되지 않는지 검증한다.
"""

import asyncio

import pytest

from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.protocol import MessageBuilder, MessageType
from src.multiplayer.session import MultiplayerSession


def _make_session():
    session = MultiplayerSession(max_players=4)
    session.add_player(MultiplayerPlayer(player_id="host", player_name="Host", is_host=True))
    session.add_player(MultiplayerPlayer(player_id="client", player_name="Client"))
    session.add_player(MultiplayerPlayer(player_id="other", player_name="Other"))
    return session


class TestClientReceivesHostRelayedMove:
    """반려 1) 클라이언트: host 릴레이 이동 수신 (transport != subject)"""

    def test_client_accepts_host_relayed_other_player_move(self):
        """client가 sender='host', payload player_id='other' 이동 수신 → 적용"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=False)
        other = session.players["other"]
        other.x, other.y = 5, 5

        msg = MessageBuilder.player_move(player_id="other", x=6, y=5)
        asyncio.run(sync._handle_player_move(msg, sender_id="host"))

        assert (other.x, other.y) == (6, 5)

    def test_client_accepts_host_own_move(self):
        """client가 sender='host', payload player_id='host' 이동 수신 → 적용"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=False)
        host = session.players["host"]
        host.x, host.y = 3, 3

        msg = MessageBuilder.player_move(player_id="host", x=4, y=3)
        asyncio.run(sync._handle_player_move(msg, sender_id="host"))

        assert (host.x, host.y) == (4, 3)

    def test_host_still_rejects_spoofed_move(self):
        """호스트는 여전히 sender-bound 스푸핑을 거부한다"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=True)
        victim = session.players["victim"] if "victim" in session.players else session.players["other"]
        victim.x, victim.y = 5, 5

        # client 연결이 other 명의로 이동 → 거부
        msg = MessageBuilder.player_move(player_id="other", x=99, y=99)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (victim.x, victim.y) == (5, 5)

    def test_relay_message_player_id_normalized(self):
        """호스트 릴레이가 payload player_id를 인가된 subject로 정규화"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=True)

        class _FakeNetwork:
            def __init__(self):
                self.broadcasted = []

            async def broadcast(self, message, exclude=None):
                self.broadcasted.append((message, exclude))

        network = _FakeNetwork()
        sync.network_manager = network

        # payload 없이 sender만 있는 메시지 (sender='client')
        msg = MessageBuilder.player_move(player_id="client", x=2, y=2)
        asyncio.run(sync._relay_player_move(msg, sender_id="client"))

        assert len(network.broadcasted) == 1
        relayed, excluded = network.broadcasted[0]
        assert relayed.player_id == "client"
        assert excluded == "client"


class TestAuthorizedPositionInitialization:
    """반려 2) 좌표계 변경 경로에서 last_authorized_position 확정"""

    def test_reset_movement_state_confirms_position(self):
        """reset_movement_state: 인가 기준점 확정 + 타임스탬프 리셋"""
        player = MultiplayerPlayer(player_id="client", player_name="Client")
        player.x, player.y = 7, 9
        player.last_movement_timestamp = 12345.0

        player.reset_movement_state()

        assert player.last_authorized_position == (7, 9)
        assert player.last_movement_timestamp == 0.0

    def test_reset_movement_state_with_coords(self):
        player = MultiplayerPlayer(player_id="client", player_name="Client")
        player.reset_movement_state(x=3, y=4)

        assert (player.x, player.y) == (3, 4)
        assert player.last_authorized_position == (3, 4)

    def test_first_move_after_floor_change_not_rejected(self):
        """층 전환 후 재인가된 플레이어의 첫 이동이 인접 검사를 통과"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=True)
        client = session.players["client"]
        client.x, client.y = 10, 10

        # 층 전환 시뮬레이션: 이전 층 마지막 인가 위치가 남아 있어도
        # reset_movement_state가 새 좌표계 기준점으로 교체
        client.last_authorized_position = (0, 0)  # 이전 층 좌표
        client.reset_movement_state()

        msg = MessageBuilder.player_move(player_id="client", x=11, y=10)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (11, 10)
        assert client.last_authorized_position == (11, 10)

    def test_position_sync_reauthorizes(self):
        """POSITION_SYNC 수신 시 타인 플레이어 인가 기준점도 갱신"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=False)
        other = session.players["other"]
        other.x, other.y = 1, 1

        msg = MessageBuilder.position_sync({
            "other": {"x": 8, "y": 8, "timestamp": 100.0}
        })
        asyncio.run(sync._handle_position_sync(msg, sender_id="host"))

        assert (other.x, other.y) == (8, 8)
        assert other.last_authorized_position == (8, 8)

    def test_uninitialized_authorized_position_skips_adjacency(self):
        """인가 기준점이 아직 없으면(None) 인접 검사 스킵 — 첫 이동 거부 없음"""
        session = _make_session()
        sync = MovementSyncManager(session=session, is_host=True)
        client = session.players["client"]
        client.x, client.y = 20, 20
        client.last_authorized_position = None  # 미확정 (동기화 전)

        msg = MessageBuilder.player_move(player_id="client", x=25, y=20)
        asyncio.run(sync._handle_player_move(msg, sender_id="client"))

        assert (client.x, client.y) == (25, 20)
        assert client.last_authorized_position == (25, 20)
