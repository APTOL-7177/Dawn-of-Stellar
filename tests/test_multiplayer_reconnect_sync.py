"""
멀티 재접속·합류·부활 상태 동기화 테스트 (설계 t_7846bbe3 §7 시나리오 기반)

E2E-M1~M6 축약 단위/E2E 테스트:
- epoch/revision 필드와 신규 메시지 타입
- 세대 토큰 기반 중복 player_id 재접속 경쟁 제거 (M3)
- HOST_MIGRATED 발송 제거 + 수신 no-op (M6)
- FULL_SNAPSHOT 통합 복원 (M1/M2)
- late COMBAT_JOIN grace window (M4)
- revival 호스트 경유 브로드캐스트 (M5)
"""

import asyncio
import pytest

from src.multiplayer.protocol import NetworkMessage, MessageType, MessageBuilder
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.combat_join import CombatJoinHandler


# ---------------------------------------------------------------- helpers

def make_player(pid: str, name: str = None) -> MultiplayerPlayer:
    return MultiplayerPlayer(player_id=pid, player_name=name or pid, x=0, y=0, party=[], is_host=False)


# ---------------------------------------------------------------- protocol

class TestProtocolEpochFields:
    def test_message_has_epoch_revision_seq_defaults(self):
        msg = MessageBuilder.ping_request()
        assert msg.epoch == 0
        assert msg.revision == 0
        assert msg.seq == 0

    def test_epoch_revision_roundtrip(self):
        msg = MessageBuilder.ping_request()
        msg.epoch = 7
        msg.revision = 3
        msg.seq = 11
        restored = NetworkMessage.from_dict(msg.to_dict())
        assert restored.epoch == 7
        assert restored.revision == 3
        assert restored.seq == 11

    def test_legacy_message_without_fields_is_compatible(self):
        legacy = {
            "type": "ping_request",
            "player_id": "p1",
            "timestamp": 123.0,
            "data": {},
        }
        msg = NetworkMessage.from_dict(legacy)
        assert msg.epoch == 0 and msg.revision == 0 and msg.seq == 0

    def test_new_message_types_exist(self):
        assert MessageType.SESSION_STALE.value == "session_stale"
        assert MessageType.SESSION_ENDED.value == "session_ended"
        assert MessageType.REQUEST_SNAPSHOT.value == "request_snapshot"
        assert MessageType.FULL_SNAPSHOT.value == "full_snapshot"

    def test_connect_includes_protocol_version_and_epoch(self):
        msg = MessageBuilder.connect("p1", "플레이어1", epoch=5)
        assert msg.data["protocol_version"] >= 2
        assert msg.data["epoch"] == 5

    def test_session_stale_builder(self):
        msg = MessageBuilder.session_stale(server_epoch=9, client_epoch=4)
        assert msg.type == MessageType.SESSION_STALE
        assert msg.data["server_epoch"] == 9
        assert msg.data["client_epoch"] == 4

    def test_session_ended_builder(self):
        msg = MessageBuilder.session_ended(reason="host_left")
        assert msg.type == MessageType.SESSION_ENDED
        assert msg.data["reason"] == "host_left"

    def test_full_snapshot_builder(self):
        snap = {"session": {"a": 1}, "players": {}, "positions": {}, "combat": None}
        msg = MessageBuilder.full_snapshot(epoch=2, revision=10, snapshot=snap)
        assert msg.type == MessageType.FULL_SNAPSHOT
        assert msg.epoch == 2
        assert msg.revision == 10
        assert msg.data["snapshot"]["session"] == {"a": 1}

    def test_request_snapshot_builder(self):
        msg = MessageBuilder.request_snapshot("p1", epoch=2)
        assert msg.type == MessageType.REQUEST_SNAPSHOT
        assert msg.data["epoch"] == 2

    def test_character_revival_includes_epoch(self):
        msg = MessageBuilder.character_revival("p1", "char1", (3, 4), epoch=2, revision=8, hp_pct=0.5)
        assert msg.epoch == 2
        assert msg.revision == 8
        assert msg.data["hp_pct"] == 0.5
        assert msg.data["character_id"] == "char1"
        # 하위 호환: 위치 튜플 시그니처 유지
        legacy = MessageBuilder.character_revival("p1", "char1", (1, 2))
        assert legacy.data["x"] == 1 and legacy.data["y"] == 2


# ---------------------------------------------------------------- session

class TestSessionEpoch:
    def test_session_has_epoch(self):
        s = MultiplayerSession(max_players=4, host_id="h")
        assert isinstance(s.epoch, int) and s.epoch >= 1

    def test_state_revision_increments(self):
        s = MultiplayerSession(max_players=4, host_id="h")
        before = s.state_revision
        s.bump_revision()
        s.bump_revision()
        assert s.state_revision == before + 2

    def test_serialize_includes_epoch_revision(self):
        s = MultiplayerSession(max_players=4, host_id="h")
        data = s.serialize()
        assert data["epoch"] == s.epoch
        assert data["state_revision"] == s.state_revision


# ---------------------------------------------------------------- host migration policy

class TestHostMigrationDisabled:
    def test_host_does_not_broadcast_host_migrated_on_client_drop(self):
        """호스트가 클라이언트 소실을 처리할 때 HOST_MIGRATED를 발송하지 않는다 (M6)."""
        async def scenario():
            host = HostNetworkManager(port=5801)
            sent = []

            class FakeWS:
                pass

            fake_ws = FakeWS()
            host._register_client_socket("c1", fake_ws)
            # PLAYER_LEFT를 받을 잔여 클라이언트 (브로드캐스트 조건: self.clients 비어있지 않아야 함)
            host._register_client_socket("c2", FakeWS())

            async def fake_broadcast(msg, exclude=None):
                sent.append(msg.type)

            host.broadcast = fake_broadcast
            host.session = MultiplayerSession(max_players=4, host_id="host")
            host.session.add_player(make_player("host"))
            host.session.add_player(make_player("c1"))

            # finally 정리 로직을 직접 실행: 소켓 정리 + PLAYER_LEFT만 발송
            await host._cleanup_client("c1")

            assert MessageType.PLAYER_LEFT in sent
            assert MessageType.HOST_MIGRATED not in sent

        asyncio.run(scenario())

    def test_combat_sync_host_migrated_handler_is_noop(self):
        """HOST_MIGRATED 수신 시 로컬 플래그를 뒤집지 않는다 (정책 비활성화)."""
        from src.multiplayer.combat_sync import CombatSyncManager

        async def scenario():
            sync = CombatSyncManager.__new__(CombatSyncManager)
            import logging
            sync.logger = logging.getLogger("test")
            sync.is_host = False
            sync.combat_manager = None
            sync.network_manager = None

            msg = MessageBuilder.host_migrated("c1")
            await sync._handle_host_migrated(msg, None)
            assert sync.is_host is False  # 전환 없음

        asyncio.run(scenario())

    def test_exploration_host_migrated_is_noop(self):
        from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem

        async def scenario():
            import logging
            ex = MultiplayerExplorationSystem.__new__(MultiplayerExplorationSystem)
            ex.logger = logging.getLogger("test")
            ex.is_host = False
            ex.enemy_sync = None

            # 이벤트 데이터로 직접 호출 (event_bus 우회)
            MultiplayerExplorationSystem._on_host_migrated(ex, {"is_new_host": True, "new_host_id": "c1"})
            assert ex.is_host is False  # 전환 없음

        scenario()


# ---------------------------------------------------------------- reconnect supersede

class TestReconnectSupersede:
    def test_supersede_closes_old_socket_and_keeps_generation(self):
        """동일 player_id 재접속 시 구 소켓 교체, 구 세대 finally는 정리 건너뜀 (M3)."""
        async def scenario():
            host = HostNetworkManager(port=5802)

            class FakeWS:
                def __init__(self):
                    self.closed = False
                    self.code = None

                async def close(self, code=None, reason=None):
                    self.closed = True
                    self.code = code

            old_ws, new_ws = FakeWS(), FakeWS()
            host._register_client_socket("c1", old_ws)
            host._register_client_socket("c1", new_ws)

            # 구 소켓은 superseded로 닫혀야 함 (비동기 close 태스크 플러시)
            await asyncio.sleep(0.05)
            assert old_ws.closed is True
            assert old_ws.code == 4000
            # 신 소켓이 현재 세대
            assert host.clients["c1"] is new_ws

            # 구 세대 토큰으로 정리 시도 → 무시됨
            stale_token = host._client_generations["c1"] - 1
            host.session = MultiplayerSession(max_players=4, host_id="host")
            host.session.add_player(make_player("host"))
            host.session.add_player(make_player("c1"))

            cleaned = await host._cleanup_client("c1", generation=stale_token)
            assert cleaned is False
            assert "c1" in host.session.players  # 유령 퇴장 없음

            # 현재 세대 토큰으로 정리 → 실제 정리
            current_token = host._client_generations["c1"]
            cleaned = await host._cleanup_client("c1", generation=current_token)
            assert cleaned is True
            assert "c1" not in host.session.players

        asyncio.run(scenario())


# ---------------------------------------------------------------- late combat join

class TestLateCombatJoinGrace:
    def _handler(self, grace: float = 10.0):
        h = CombatJoinHandler()
        h.late_join_grace = grace
        return h

    def test_join_within_grace_allowed(self):
        h = self._handler(grace=10.0)
        h.register_combat("cbt1", (5, 5))
        import time as _t
        start = _t.time() - 5.0
        ok, reason = h.validate_late_join("p1", "cbt1", epoch=1, combat_epoch_start=start, server_epoch=1)
        assert ok is True

    def test_join_beyond_grace_rejected(self):
        h = self._handler(grace=10.0)
        h.register_combat("cbt1", (5, 5))
        import time as _t
        start = _t.time() - 15.0
        ok, reason = h.validate_late_join("p1", "cbt1", epoch=1, combat_epoch_start=start, server_epoch=1)
        assert ok is False
        assert reason == "grace_exceeded"

    def test_join_epoch_mismatch_rejected(self):
        h = self._handler()
        h.register_combat("cbt1", (5, 5))
        import time as _t
        ok, reason = h.validate_late_join("p1", "cbt1", epoch=2, combat_epoch_start=_t.time(), server_epoch=1)
        assert ok is False
        assert reason == "epoch_mismatch"

    def test_join_unknown_combat_rejected(self):
        h = self._handler()
        import time as _t
        ok, reason = h.validate_late_join("p1", "nope", epoch=1, combat_epoch_start=_t.time(), server_epoch=1)
        assert ok is False
        assert reason == "combat_not_active"

    def test_join_dead_player_rejected(self):
        h = self._handler()
        h.register_combat("cbt1", (5, 5))
        import time as _t
        ok, reason = h.validate_late_join(
            "p1", "cbt1", epoch=1, combat_epoch_start=_t.time(), server_epoch=1,
            requester_alive=False,
        )
        assert ok is False
        assert reason == "requester_dead"

    def test_join_twice_rejected(self):
        h = self._handler()
        h.register_combat("cbt1", (5, 5))
        h.mark_player_joined("cbt1", "p1")
        import time as _t
        ok, reason = h.validate_late_join("p1", "cbt1", epoch=1, combat_epoch_start=_t.time(), server_epoch=1)
        assert ok is False
        assert reason == "already_joined"


# ---------------------------------------------------------------- revival broadcast hook

class TestRevivalBroadcastHook:
    def test_revival_system_has_network_hook(self):
        """부활 성공 시 네트워크 전파 훅이 호출된다 (M5)."""
        from src.multiplayer.revival_system import RevivalSystem

        calls = []

        class FakePSM:
            session = None

            def handle_character_revival(self, player, character, pos):
                return 0, 0

        rs = RevivalSystem(FakePSM())
        rs.on_revival_broadcast = lambda pid, cid, x, y, hp_pct: calls.append((pid, cid, x, y, hp_pct))

        class FakeChar:
            name = "테스터"
            is_alive = False
            current_hp = 0
            max_hp = 100
            current_mp = 0
            max_mp = 50

        class FakePlayer:
            player_id = "p1"
            party = []

        ok = rs.revive_character(FakePlayer(), FakeChar(), hp_percentage=0.5)
        assert ok is True
        assert len(calls) == 1
        pid, cid, x, y, hp_pct = calls[0]
        assert pid == "p1"
        assert hp_pct == 0.5


# ---------------------------------------------------------------- config

class TestLateJoinConfig:
    def test_late_join_grace_config_exists(self):
        from src.multiplayer.config import MultiplayerConfig
        assert hasattr(MultiplayerConfig, "combat_join_grace_window")
        assert MultiplayerConfig.combat_join_grace_window >= 1.0

    def test_protocol_version_config(self):
        from src.multiplayer.config import MultiplayerConfig
        assert MultiplayerConfig.protocol_version >= 2
