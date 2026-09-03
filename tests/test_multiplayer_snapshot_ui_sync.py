"""
멀티 snapshot UI·부활 수신·원호스트 재접속 테스트 (카드 t_ceed55de)

- (1) 호스트가 REQUEST_SNAPSHOT에 FULL_SNAPSHOT으로 응답한다 (§5.3)
- (2) 클라이언트가 CHARACTER_REVIVAL 수신 → player_state(마크/생존/HP) 반영
- (3) SESSION_STALE/SESSION_ENDED/FULL_SNAPSHOT 수신이 UI 확인용 플래그/알림으로 기록
- (4) 원래 호스트가 로비를 다시 열었을 때(같은 세션, 같은 epoch) 클라이언트의
      명시적 재접속(reconnect)이 승인되고 멤버십이 보존된다 (E2E)
"""

import asyncio

import pytest

from src.multiplayer.protocol import MessageBuilder, MessageType, NetworkMessage
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.player_state import PlayerStateManager


def make_player(pid: str, is_host: bool = False) -> MultiplayerPlayer:
    return MultiplayerPlayer(player_id=pid, player_name=pid, x=0, y=0, party=[], is_host=is_host)


class FakeWS:
    def __init__(self):
        self.sent = []
        self.closed = []

    async def send(self, data):
        self.sent.append(data)

    async def close(self, code=None, reason=None):
        self.closed.append((code, reason))


# ---------------------------------------------------------------- (1) snapshot 응답

class TestRequestSnapshotResponse:
    def test_host_responds_to_request_snapshot_with_full_snapshot(self):
        """호스트는 REQUEST_SNAPSHOT 수신 시 요청자에게 FULL_SNAPSHOT을 회신한다."""
        async def scenario():
            host = HostNetworkManager(port=5901)
            host.session = MultiplayerSession(max_players=4, host_id="host")
            host.session.add_player(make_player("host", is_host=True))
            host.session.add_player(make_player("p1"))
            host.session.bump_revision()

            ws = FakeWS()
            host.clients["p1"] = ws

            req = MessageBuilder.request_snapshot("p1", epoch=host.session.epoch)
            await host._handle_message(req, sender_id="p1")

            assert len(ws.sent) == 1, "FULL_SNAPSHOT 응답이 요청자에게 전송되어야 한다"
            reply = NetworkMessage.from_json(ws.sent[0].decode("utf-8")) if hasattr(NetworkMessage, "from_json") else None
            if reply is None:
                import json
                reply = NetworkMessage.from_dict(json.loads(ws.sent[0].decode("utf-8")))
            assert reply.type == MessageType.FULL_SNAPSHOT
            assert reply.epoch == host.session.epoch
            assert reply.revision == host.session.state_revision
            snap = reply.data["snapshot"]
            assert "session" in snap and "positions" in snap
            assert "p1" in snap["positions"]

        asyncio.run(scenario())

    def test_client_records_full_snapshot_and_notice(self):
        """클라이언트는 FULL_SNAPSHOT 수신 시 스냅샷 저장 + UI 알림을 기록한다."""
        async def scenario():
            client = ClientNetworkManager("127.0.0.1", 5902)
            client.connection_state = type(client.connection_state).CONNECTED

            msg = MessageBuilder.full_snapshot(epoch=3, revision=9, snapshot={"session": {}, "positions": {}})
            await client._handle_message(msg, sender_id=client.HOST_TRANSPORT_SENDER)

            assert client.last_full_snapshot is not None
            notices = [n for n in client.ui_notices if n["type"] == "full_snapshot"]
            assert notices and notices[-1]["revision"] == 9

        asyncio.run(scenario())


# ---------------------------------------------------------------- (2) 부활 수신 → player_state

class TestCharacterRevivalReceive:
    def test_client_revival_updates_player_state(self):
        """클라이언트는 CHARACTER_REVIVAL 수신 시 캐릭터를 부활시키고 마크를 복원한다."""
        async def scenario():
            client = ClientNetworkManager("127.0.0.1", 5903)
            client.connection_state = type(client.connection_state).CONNECTED
            client.session = MultiplayerSession(max_players=4, host_id="host")

            p1 = make_player("p1")

            class FakeChar:
                id = "char1"
                name = "테스터"
                is_alive = False
                current_hp = 0
                max_hp = 100
                is_ghost = True

            char = FakeChar()
            p1.party = [char]
            client.session.add_player(p1)

            # 사망 상태에서 마크 숨김 처리
            psm = PlayerStateManager()
            psm.update_player_state(p1)
            assert psm.is_mark_visible("p1") is False

            client.player_state_manager = psm

            msg = MessageBuilder.character_revival("p1", "char1", (4, 5), epoch=1, revision=2, hp_pct=0.7)
            await client._handle_message(msg, sender_id=client.HOST_TRANSPORT_SENDER)

            assert char.is_alive is True
            assert char.current_hp == 70
            assert char.is_ghost is False
            assert psm.is_mark_visible("p1") is True
            assert client.pending_revivals[-1] == ("p1", "char1", 4, 5)

        asyncio.run(scenario())

    def test_host_revival_message_is_ignored_by_host_branch(self):
        """호스트는 CHARACTER_REVIVAL 수신 시 클라이언트 복원 경로를 실행하지 않는다(브로드캐스트 전용)."""
        async def scenario():
            host = HostNetworkManager(port=5904)
            host.session = MultiplayerSession(max_players=4, host_id="host")
            host.session.add_player(make_player("host", is_host=True))

            msg = MessageBuilder.character_revival("host", "char1", (1, 2))
            await host._handle_message(msg, sender_id="host")
            assert getattr(host, "pending_revivals", []) == []

        asyncio.run(scenario())


# ---------------------------------------------------------------- (3) 세션 상태 UI 플래그

class TestSessionStateUiFlags:
    def test_client_session_ended_notice_recorded(self):
        async def scenario():
            client = ClientNetworkManager("127.0.0.1", 5905)
            client.connection_state = type(client.connection_state).CONNECTED

            msg = MessageBuilder.session_ended(reason="host_left")
            await client._handle_message(msg, sender_id=client.HOST_TRANSPORT_SENDER)

            assert client.session_ended is True
            assert any(n["type"] == "session_ended" and n["reason"] == "host_left"
                       for n in client.ui_notices)

        asyncio.run(scenario())

    def test_client_session_stale_notice_recorded(self):
        async def scenario():
            client = ClientNetworkManager("127.0.0.1", 5906)
            client.connection_state = type(client.connection_state).CONNECTED

            msg = MessageBuilder.session_stale(server_epoch=9, client_epoch=4)
            await client._handle_message(msg, sender_id=client.HOST_TRANSPORT_SENDER)

            assert client.session_stale is True
            assert any(n["type"] == "session_stale" for n in client.ui_notices)

        asyncio.run(scenario())


# ---------------------------------------------------------------- (4) 원호스트 재개 → 명시적 재접속 (E2E)

class TestOriginalHostReopenRejoin:
    def test_explicit_reconnect_after_host_reopens_same_session(self):
        """호스트 중지(SESSION_ENDED) → 같은 세션으로 서버 재개 → 클라이언트 명시 재접속 승인.

        epoch는 세션 객체에 귀속되므로 같은 세션을 재사용하면 재접속이 거부되지 않는다.
        """
        async def scenario():
            session = MultiplayerSession(max_players=4, host_id="host")
            session.add_player(make_player("host", is_host=True))

            host = HostNetworkManager(port=5907, session=session)
            await host.start_server()

            client = ClientNetworkManager("127.0.0.1", host.port)
            await client.connect("c1", "클라1")
            await asyncio.sleep(0.2)
            assert "c1" in host.session.players
            assert client.session_epoch == session.epoch

            # 호스트가 로비를 닫음 (정상 종료 → SESSION_ENDED)
            await host.stop_server()
            await asyncio.sleep(0.4)
            assert client.session_ended is True

            # 원래 호스트가 같은 세션으로 로비를 다시 열음 (같은 포트 재사용)
            reopened_port = host.port
            host2 = HostNetworkManager(port=reopened_port, session=session)
            await host2.start_server()

            # 클라이언트가 명시적으로 재접속 (UI "다시 접속" 버튼 경로)
            await client.reconnect()
            await asyncio.sleep(0.3)

            assert client.connection_state.value == "connected"
            assert "c1" in host2.session.players, "재접속 후 세션 멤버십이 보존되어야 한다"
            assert client.session_epoch == session.epoch

            await client.disconnect()
            await host2.stop_server()

        asyncio.run(scenario())
