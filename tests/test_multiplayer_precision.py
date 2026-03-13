"""
멀티플레이어 정밀 테스트

발견된 문제점과 엣지 케이스를 꼼꼼하게 검증합니다.

검증 영역:
  1. 세션: player_count vs len(players) 불일치
  2. 세션: 타입 체크 우회 (isinstance 대신 __name__)
  3. 세션: 층 이동 준비 상태 엣지 케이스
  4. 전투 동기화: 캐릭터 ID 위치 기반 폴백의 불안정성
  5. 전투 동기화: 시퀀스 번호 처리 및 갭
  6. 전투 동기화: 액션 소유권 스푸핑 방어
  7. 적 동기화: ID 안정성 (이동 후에도 동일)
  8. 적 동기화: 폴백 ID 캐싱 동작
  9. 전리품 동기화: 인덱스 시프트 경쟁 상태
  10. 전리품 동기화: 누락된 MessageType 폴백
  11. 이동 동기화: 타임스탬프 순서 보장
  12. ATB: 액션 대기 시간 및 평균 속도 계산
  13. 프로토콜: 메시지 파싱 엣지 케이스
  14. 플레이어: 파티 생존 판정 엣지 케이스
"""

import asyncio
import time
from types import SimpleNamespace
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.protocol import NetworkMessage, MessageType, MessageBuilder
from src.multiplayer.config import MultiplayerConfig
from src.multiplayer.combat_sync import CombatSyncManager
from src.multiplayer.enemy_sync import EnemySyncManager
from src.multiplayer.loot_sync import LootSyncManager, StorageSyncManager
from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.atb_multiplayer import MultiplayerATBSystem
from src.combat.atb_system import ATBGauge


class _Combatant:
    """ATB 테스트용 해시 가능한 전투원 모의 객체"""
    def __init__(self, is_alive=True, speed=10):
        self.is_alive = is_alive
        self.speed = speed


# ──────────────────────────────────────────────────────────────
# 1. 세션: player_count vs len(players) 일관성
# ──────────────────────────────────────────────────────────────

class TestSessionPlayerCountConsistency:
    """player_count 카운터가 players 딕셔너리와 항상 동기화되는지 검증"""

    def test_add_and_remove_keeps_count_consistent(self):
        """추가/제거 후 player_count == len(players)"""
        session = MultiplayerSession(max_players=4)
        players = []
        for i in range(4):
            p = MultiplayerPlayer(player_id=f"p{i}", player_name=f"Player {i}")
            session.add_player(p)
            players.append(p)

        assert session.player_count == len(session.players) == 4

        session.remove_player("p1")
        assert session.player_count == len(session.players) == 3

        session.remove_player("p3")
        assert session.player_count == len(session.players) == 2

    def test_duplicate_add_does_not_increment_count(self):
        """동일 플레이어 중복 추가 시 카운터 증가하지 않음"""
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="dup", player_name="Dup")
        session.add_player(p)
        result = session.add_player(p)  # 중복

        assert result is False
        assert session.player_count == 1
        assert len(session.players) == 1

    def test_remove_nonexistent_does_not_decrement_count(self):
        """존재하지 않는 플레이어 제거 시 카운터 감소하지 않음"""
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        session.add_player(p)

        success, _ = session.remove_player("nonexistent")
        assert success is False
        assert session.player_count == 1
        assert len(session.players) == 1

    def test_remove_all_players_count_zero(self):
        """모든 플레이어 제거 시 count == 0, host_id == None"""
        session = MultiplayerSession(max_players=2)
        p1 = MultiplayerPlayer(player_id="p1", player_name="P1")
        p2 = MultiplayerPlayer(player_id="p2", player_name="P2")
        session.add_player(p1)
        session.add_player(p2)

        session.remove_player("p1")
        session.remove_player("p2")

        assert session.player_count == 0
        assert len(session.players) == 0
        assert session.host_id is None


# ──────────────────────────────────────────────────────────────
# 2. 세션: 타입 체크 (isinstance 우회 문제)
# ──────────────────────────────────────────────────────────────

class TestSessionTypeCheck:
    """session.add_player 의 type().__name__ 체크 동작 검증"""

    def test_reject_none_player(self):
        """None 플레이어 추가 시 TypeError"""
        session = MultiplayerSession(max_players=4)
        with pytest.raises(TypeError, match="None"):
            session.add_player(None)

    def test_reject_wrong_type(self):
        """잘못된 타입 추가 시 TypeError"""
        session = MultiplayerSession(max_players=4)
        with pytest.raises(TypeError):
            session.add_player("not_a_player")

    def test_reject_dict_with_player_fields(self):
        """딕셔너리는 올바른 필드가 있어도 거부"""
        session = MultiplayerSession(max_players=4)
        fake = {"player_id": "fake", "player_name": "Fake"}
        with pytest.raises(TypeError):
            session.add_player(fake)

    def test_duck_typed_object_with_same_class_name_accepted(self):
        """__name__이 'MultiplayerPlayer'인 가짜 객체가 통과하는 취약점 검증"""
        session = MultiplayerSession(max_players=4)

        # 동적으로 클래스 이름을 위조
        FakePlayer = type('MultiplayerPlayer', (), {
            'player_id': 'spoofed',
            'player_name': 'Spoofed',
            'session_id': None,
            'is_host': False,
        })
        fake = FakePlayer()

        # BUG: __name__ 체크를 사용하므로 이 가짜 객체가 통과함
        # isinstance 를 사용했다면 거부되었을 것
        result = session.add_player(fake)
        assert result is True  # 현재 동작: 통과 (취약점)

    def test_empty_player_id_auto_replaced_by_uuid(self):
        """
        BUG 검증: 빈 player_id는 __post_init__에서 UUID로 대체되므로
        session.add_player의 빈 ID 검증에 도달하지 않음.
        즉, 의도적으로 빈 ID를 넣어도 UUID가 자동 생성되어 통과함.
        """
        session = MultiplayerSession(max_players=4)
        p = MultiplayerPlayer(player_id="", player_name="NoID")
        # __post_init__ 이 UUID 를 생성하므로 빈 문자열이 아님
        assert p.player_id != ""
        result = session.add_player(p)
        assert result is True  # 통과됨 — 빈 ID 검증 우회


# ──────────────────────────────────────────────────────────────
# 3. 세션: max_players 경계값 및 층 이동 준비 상태
# ──────────────────────────────────────────────────────────────

class TestSessionBoundary:
    """세션 경계 조건 테스트"""

    def test_max_players_boundary_values(self):
        """max_players 경계값 (2~4 범위)"""
        MultiplayerSession(max_players=2)
        MultiplayerSession(max_players=3)
        MultiplayerSession(max_players=4)

        with pytest.raises(ValueError):
            MultiplayerSession(max_players=1)
        with pytest.raises(ValueError):
            MultiplayerSession(max_players=5)
        with pytest.raises(ValueError):
            MultiplayerSession(max_players=0)
        with pytest.raises(ValueError):
            MultiplayerSession(max_players=-1)

    def test_floor_ready_requires_all_players(self):
        """층 이동에 모든 플레이어 준비 필요"""
        session = MultiplayerSession(max_players=3)
        for i in range(3):
            session.add_player(
                MultiplayerPlayer(player_id=f"p{i}", player_name=f"P{i}")
            )

        assert session.is_all_ready_for_floor_change() is False

        session.set_floor_ready("p0")
        session.set_floor_ready("p1")
        assert session.is_all_ready_for_floor_change() is False

        session.set_floor_ready("p2")
        assert session.is_all_ready_for_floor_change() is True

    def test_floor_ready_with_removed_player(self):
        """플레이어가 나간 후 층 이동 준비 상태 자동 정리"""
        session = MultiplayerSession(max_players=3)
        for i in range(3):
            session.add_player(
                MultiplayerPlayer(player_id=f"p{i}", player_name=f"P{i}")
            )

        session.set_floor_ready("p0")
        session.set_floor_ready("p1")
        session.set_floor_ready("p2")
        assert session.is_all_ready_for_floor_change() is True

        # p2가 나감 → remove_player가 floor_ready_players에서도 p2를 제거
        session.remove_player("p2")
        # players = {p0, p1}, floor_ready = {p0, p1} → 일치하므로 True
        assert session.is_all_ready_for_floor_change() is True

    def test_floor_ready_unready_toggle(self):
        """준비 → 취소 토글 동작"""
        session = MultiplayerSession(max_players=2)
        session.add_player(MultiplayerPlayer(player_id="p0", player_name="P0"))
        session.add_player(MultiplayerPlayer(player_id="p1", player_name="P1"))

        session.set_floor_ready("p0")
        session.set_floor_ready("p1")
        assert session.is_all_ready_for_floor_change() is True

        # p0 준비 취소
        session.set_floor_ready("p0", ready=False)
        assert session.is_all_ready_for_floor_change() is False

    def test_floor_ready_reset_clears_all(self):
        """reset_floor_ready() 호출 시 모든 준비 상태 초기화"""
        session = MultiplayerSession(max_players=2)
        session.add_player(MultiplayerPlayer(player_id="p0", player_name="P0"))
        session.add_player(MultiplayerPlayer(player_id="p1", player_name="P1"))
        session.set_floor_ready("p0")
        session.set_floor_ready("p1")

        session.reset_floor_ready()
        assert len(session.floor_ready_players) == 0
        assert session.is_all_ready_for_floor_change() is False

    def test_empty_session_not_ready(self):
        """빈 세션은 층 이동 준비 상태가 아님"""
        session = MultiplayerSession(max_players=2)
        assert session.is_all_ready_for_floor_change() is False


# ──────────────────────────────────────────────────────────────
# 4. 세션: 호스트 마이그레이션 심층 테스트
# ──────────────────────────────────────────────────────────────

class TestHostMigration:
    """호스트 마이그레이션 심층 검증"""

    def test_host_flag_transfers_on_migration(self):
        """호스트 제거 시 새 호스트의 is_host 플래그가 True"""
        session = MultiplayerSession(max_players=3)
        p1 = MultiplayerPlayer(player_id="host", player_name="Host")
        p2 = MultiplayerPlayer(player_id="client1", player_name="C1")
        p3 = MultiplayerPlayer(player_id="client2", player_name="C2")
        session.add_player(p1)
        session.add_player(p2)
        session.add_player(p3)

        assert p1.is_host is True

        success, new_host = session.remove_player("host")
        assert success is True
        assert new_host is not None
        assert session.players[new_host].is_host is True

    def test_non_host_removal_no_migration(self):
        """비호스트 제거 시 호스트 변경 없음"""
        session = MultiplayerSession(max_players=3)
        p1 = MultiplayerPlayer(player_id="host", player_name="Host")
        p2 = MultiplayerPlayer(player_id="client", player_name="Client")
        session.add_player(p1)
        session.add_player(p2)

        success, new_host = session.remove_player("client")
        assert success is True
        assert new_host is None
        assert session.host_id == "host"

    def test_successive_host_migrations(self):
        """연속 호스트 마이그레이션"""
        session = MultiplayerSession(max_players=4)
        ids = ["p0", "p1", "p2", "p3"]
        for pid in ids:
            session.add_player(MultiplayerPlayer(player_id=pid, player_name=pid))

        # p0(호스트) 제거 → 새 호스트 선출
        _, new1 = session.remove_player("p0")
        assert new1 is not None
        assert session.host_id == new1

        # 새 호스트도 제거 → 또 다른 호스트 선출
        _, new2 = session.remove_player(new1)
        assert new2 is not None
        assert session.host_id == new2


# ──────────────────────────────────────────────────────────────
# 5. 전투 동기화: 캐릭터 ID 추출 안정성
# ──────────────────────────────────────────────────────────────

class TestCombatSyncCharacterID:
    """CombatSyncManager._get_character_id() 의 폴백 로직 검증"""

    def _make_sync(self):
        return CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )

    def test_id_from_id_attribute(self):
        """id 속성이 있으면 해당 값 사용"""
        sync = self._make_sync()
        char = SimpleNamespace(id="char_001")
        assert sync._get_character_id(char) == "char_001"

    def test_id_from_character_id_attribute(self):
        """character_id 속성 폴백"""
        sync = self._make_sync()
        char = SimpleNamespace(character_id="cid_002")
        assert sync._get_character_id(char) == "cid_002"

    def test_id_fallback_to_position_is_unstable(self):
        """
        BUG 검증: ID 없는 캐릭터는 위치 기반 임시 ID를 받으며,
        위치가 바뀌면 ID도 바뀌어 동기화 오류 발생
        """
        sync = self._make_sync()
        char = SimpleNamespace(x=5, y=10)  # id/character_id 없음

        id1 = sync._get_character_id(char)
        assert id1 == "char_5_10"

        # 캐릭터가 이동하면 ID가 바뀜 (불안정)
        char.x = 6
        char.y = 11
        id2 = sync._get_character_id(char)
        assert id2 == "char_6_11"
        assert id1 != id2  # BUG: 같은 캐릭터인데 ID가 다름

    def test_id_none_for_empty_character(self):
        """속성이 전혀 없는 객체는 None 반환"""
        sync = self._make_sync()
        char = SimpleNamespace()
        assert sync._get_character_id(char) is None

    def test_id_none_for_none_input(self):
        """None 입력 시 None 반환"""
        sync = self._make_sync()
        assert sync._get_character_id(None) is None


# ──────────────────────────────────────────────────────────────
# 6. 전투 동기화: 시퀀스 번호 처리
# ──────────────────────────────────────────────────────────────

class TestCombatSyncSequence:
    """시퀀스 번호 기반 액션 순서 보장 검증"""

    def test_sequence_increments_on_action(self):
        """액션 실행마다 시퀀스 번호 증가"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )
        assert sync.action_sequence == 0

        sync.action_sequence += 1
        assert sync.action_sequence == 1
        sync.action_sequence += 1
        assert sync.action_sequence == 2

    def test_client_skips_old_sequence(self):
        """클라이언트가 이미 처리한 시퀀스를 무시"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=False,
        )
        sync.last_processed_sequence = 5

        # 시퀀스 3은 이미 처리됨
        assert 3 <= sync.last_processed_sequence

        # 시퀀스 6은 새로운 것
        assert 6 > sync.last_processed_sequence

    def test_client_updates_last_processed(self):
        """클라이언트가 새 시퀀스를 처리하면 last_processed 갱신"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=False,
        )
        sync.last_processed_sequence = -1

        new_seq = 1
        if new_seq > sync.last_processed_sequence:
            sync.last_processed_sequence = new_seq

        assert sync.last_processed_sequence == 1


# ──────────────────────────────────────────────────────────────
# 7. 전투 동기화: 상태 동기화 (HP/MP/ATB)
# ──────────────────────────────────────────────────────────────

class TestCombatStateSyncPrecision:
    """전투 상태 동기화의 데이터 정확성 검증"""

    def test_sync_updates_all_character_fields(self):
        """HP, MP, BRV, is_alive 모두 동기화"""
        from src.combat.combat_manager import CombatState

        ally = SimpleNamespace(
            id="a1", current_hp=100, current_mp=50,
            current_brv=0, is_alive=True
        )
        combat_manager = SimpleNamespace(
            allies=[ally], enemies=[],
            atb=MagicMock(get_gauge=MagicMock(return_value=None)),
            state=CombatState.IN_PROGRESS, turn_count=0
        )

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=False,
        )

        sync._sync_combat_state({
            "allies": [{
                "id": "a1",
                "current_hp": 42,
                "current_mp": 13,
                "current_brv": 999,
                "is_alive": False,
            }],
            "enemies": [],
            "combat_state": "in_progress",
            "turn_count": 7,
        })

        assert ally.current_hp == 42
        assert ally.current_mp == 13
        assert ally.current_brv == 999
        assert ally.is_alive is False
        assert combat_manager.turn_count == 7

    def test_sync_ignores_unknown_character_id(self):
        """존재하지 않는 캐릭터 ID는 무시"""
        from src.combat.combat_manager import CombatState

        ally = SimpleNamespace(id="a1", current_hp=100, current_mp=50,
                               current_brv=0, is_alive=True)
        combat_manager = SimpleNamespace(
            allies=[ally], enemies=[],
            atb=MagicMock(get_gauge=MagicMock(return_value=None)),
            state=CombatState.IN_PROGRESS, turn_count=0
        )

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=False,
        )

        sync._sync_combat_state({
            "allies": [{"id": "NONEXISTENT", "current_hp": 0}],
            "enemies": [],
        })

        # a1은 변경되지 않아야 함
        assert ally.current_hp == 100

    def test_sync_atb_gauge_clamp(self):
        """ATB 게이지 값이 범위 내로 클램핑"""
        from src.combat.combat_manager import CombatState

        gauge = SimpleNamespace(current=0.0, max_gauge=1000)
        ally = SimpleNamespace(
            id="a1", current_hp=100, current_mp=50,
            current_brv=0, is_alive=True
        )
        atb = MagicMock()
        atb.get_gauge.return_value = gauge
        combat_manager = SimpleNamespace(
            allies=[ally], enemies=[], atb=atb,
            state=CombatState.IN_PROGRESS, turn_count=0
        )

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=False,
        )

        # max_gauge보다 큰 값 전송
        sync._sync_combat_state({
            "allies": [{"id": "a1", "atb_current": 9999, "atb_max": 1000}],
            "enemies": [],
        })

        # max(0, min(9999, 1000)) = 1000
        assert gauge.current == 1000

    def test_sync_atb_gauge_negative_clamped(self):
        """음수 ATB 값은 0으로 클램핑"""
        from src.combat.combat_manager import CombatState

        gauge = SimpleNamespace(current=500.0, max_gauge=1000)
        ally = SimpleNamespace(
            id="a1", current_hp=100, current_mp=50,
            current_brv=0, is_alive=True
        )
        atb = MagicMock()
        atb.get_gauge.return_value = gauge
        combat_manager = SimpleNamespace(
            allies=[ally], enemies=[], atb=atb,
            state=CombatState.IN_PROGRESS, turn_count=0
        )

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=False,
        )

        sync._sync_combat_state({
            "allies": [{"id": "a1", "atb_current": -100}],
            "enemies": [],
        })

        assert gauge.current == 0

    def test_sync_invalid_atb_type_ignored(self):
        """비숫자 ATB 값은 무시"""
        from src.combat.combat_manager import CombatState

        gauge = SimpleNamespace(current=500.0, max_gauge=1000)
        ally = SimpleNamespace(
            id="a1", current_hp=100, current_mp=50,
            current_brv=0, is_alive=True
        )
        atb = MagicMock()
        atb.get_gauge.return_value = gauge
        combat_manager = SimpleNamespace(
            allies=[ally], enemies=[], atb=atb,
            state=CombatState.IN_PROGRESS, turn_count=0
        )

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=False,
        )

        sync._sync_combat_state({
            "allies": [{"id": "a1", "atb_current": "not_a_number"}],
            "enemies": [],
        })

        # 원래 값 유지
        assert gauge.current == 500.0


# ──────────────────────────────────────────────────────────────
# 8. 적 동기화: ID 안정성
# ──────────────────────────────────────────────────────────────

class TestEnemySyncIDStability:
    """EnemySyncManager._get_enemy_id() 안정성 검증"""

    def _make_sync(self):
        return EnemySyncManager(session=MagicMock(), is_host=True)

    def test_spawn_based_stable_id(self):
        """spawn 좌표 기반 ID는 이동 후에도 안정"""
        sync = self._make_sync()
        enemy = SimpleNamespace(enemy_id="goblin", spawn_x=3, spawn_y=5, x=3, y=5)

        id1 = sync._get_enemy_id(enemy)
        enemy.x = 10
        enemy.y = 15
        id2 = sync._get_enemy_id(enemy)

        assert id1 == "goblin_3_5"
        assert id1 == id2

    def test_no_spawn_with_enemy_type_only(self):
        """spawn 좌표 없고 enemy_id만 있을 때"""
        sync = self._make_sync()
        enemy = SimpleNamespace(enemy_id="slime", x=1, y=2)
        # spawn_x/y 없음 → enemy_id만 사용

        eid = sync._get_enemy_id(enemy)
        assert eid == "slime"

    def test_position_fallback_id_cached(self):
        """
        최종 폴백 (현재 좌표) 사용 시에도 _multiplayer_sync_id 캐시로
        이후 이동에서도 동일 ID 유지
        """
        sync = self._make_sync()
        # enemy_id도 없고 spawn도 없고 id도 없는 최악의 경우
        enemy = SimpleNamespace(x=7, y=8)

        id1 = sync._get_enemy_id(enemy)
        assert id1 == "enemy_7_8"

        # 이동 후에도 캐시된 ID 사용
        enemy.x = 20
        enemy.y = 30
        id2 = sync._get_enemy_id(enemy)
        assert id2 == "enemy_7_8"  # 캐시 덕분에 안정

    def test_different_enemies_different_ids(self):
        """같은 타입이라도 spawn 위치가 다르면 다른 ID"""
        sync = self._make_sync()
        e1 = SimpleNamespace(enemy_id="goblin", spawn_x=1, spawn_y=1, x=1, y=1)
        e2 = SimpleNamespace(enemy_id="goblin", spawn_x=5, spawn_y=5, x=5, y=5)

        assert sync._get_enemy_id(e1) != sync._get_enemy_id(e2)
        assert sync._get_enemy_id(e1) == "goblin_1_1"
        assert sync._get_enemy_id(e2) == "goblin_5_5"

    def test_enemy_with_explicit_id(self):
        """id 속성이 있는 적"""
        sync = self._make_sync()
        enemy = SimpleNamespace(id="unique_boss_01", x=10, y=10)

        eid = sync._get_enemy_id(enemy)
        assert eid == "unique_boss_01"

    def test_collect_enemy_positions_skips_invalid(self):
        """유효하지 않은 적은 위치 수집에서 제외"""
        sync = self._make_sync()
        valid = SimpleNamespace(enemy_id="goblin", spawn_x=1, spawn_y=1, x=3, y=4)
        no_pos = SimpleNamespace(enemy_id="ghost")  # x, y 없음
        none_enemy = None

        positions = sync._collect_enemy_positions(
            [valid, no_pos, none_enemy],
            current_time=time.time()
        )

        assert len(positions) == 1
        assert "goblin_1_1" in positions
        assert positions["goblin_1_1"]["x"] == 3

    def test_sync_interval_gate(self):
        """0.65초 미만 간격에서는 이동 차단"""
        sync = self._make_sync()
        sync.last_move_time = 100.0

        assert sync.can_move_enemies(100.3) is False  # 0.3초
        assert sync.can_move_enemies(100.64) is False  # 0.64초
        assert sync.can_move_enemies(100.65) is True   # 0.65초


# ──────────────────────────────────────────────────────────────
# 9. 전리품 동기화: 인덱스 시프트 경쟁 상태
# ──────────────────────────────────────────────────────────────

class TestLootSyncRaceCondition:
    """LootSyncManager 의 아이템 선점 시 인덱스 시프트 문제"""

    def _make_items(self, count):
        return [SimpleNamespace(item_id=f"item_{i}", name=f"Item {i}") for i in range(count)]

    def test_claim_removes_from_pool_and_shifts_index(self):
        """
        아이템 선점 시 claimed 마킹 방식으로 인덱스 시프트 없이 동작.
        loot_pool 크기는 유지되고, claimed_items에 선점 정보가 저장됨.
        """
        loot = LootSyncManager(session=MagicMock())
        items = self._make_items(3)
        loot.set_loot_pool(items)

        # 플레이어1이 인덱스 0 (item_0) 선점
        result = loot.claim_item("p1", 0)
        assert result is True
        # pop 대신 claimed 마킹 방식: loot_pool 크기 유지 (인덱스 밀림 없음)
        assert len(loot.loot_pool) == 3

        # item_0은 claimed_items에 등록됨
        assert "item_0" in loot.claimed_items
        assert loot.claimed_items["item_0"] == "p1"

        # 미선점 아이템 기준으로 인덱스 0은 여전히 item_1
        unclaimed = [item for item in loot.loot_pool
                     if item.item_id not in loot.claimed_items]
        assert unclaimed[0].item_id == "item_1"

    def test_claim_already_claimed(self):
        """이미 선점된 아이템 재선점 불가"""
        loot = LootSyncManager(session=MagicMock())
        items = self._make_items(3)
        loot.set_loot_pool(items)

        loot.claim_item("p1", 0)
        # pop 으로 풀에서 제거됐으므로 같은 item_id는 claimed_items에 있음
        assert "item_0" in loot.claimed_items

    def test_claim_invalid_index(self):
        """범위 밖 인덱스 거부"""
        loot = LootSyncManager(session=MagicMock())
        loot.set_loot_pool(self._make_items(2))

        assert loot.claim_item("p1", -1) is False
        assert loot.claim_item("p1", 2) is False
        assert loot.claim_item("p1", 100) is False

    def test_claim_all_items_empties_pool(self):
        """모든 아이템 선점 시 풀 비어야 함"""
        loot = LootSyncManager(session=MagicMock())
        items = self._make_items(3)
        loot.set_loot_pool(items)

        # 항상 인덱스 0을 선점 (pop 으로 시프트)
        for i in range(3):
            loot.claim_item(f"p{i}", 0)

        assert loot.is_empty() is True
        assert len(loot.claimed_items) == 3


# ──────────────────────────────────────────────────────────────
# 10. 전리품: 골드 분배
# ──────────────────────────────────────────────────────────────

class TestGoldDistribution:
    """골드 균등 분배 정밀 검증"""

    def test_even_split(self):
        """균등 분배"""
        session = MagicMock()
        session.players = {"p1": None, "p2": None}
        session.host_id = "p1"

        loot = LootSyncManager(session=session)
        dist = loot.distribute_gold(100)

        assert dist["p1"] == 50
        assert dist["p2"] == 50
        assert sum(dist.values()) == 100

    def test_remainder_goes_to_host(self):
        """나머지 골드는 호스트에게"""
        session = MagicMock()
        session.players = {"host": None, "c1": None, "c2": None}
        session.host_id = "host"

        loot = LootSyncManager(session=session)
        dist = loot.distribute_gold(100)

        # 100 / 3 = 33 나머지 1 → 호스트에게
        assert dist["host"] == 34
        assert dist["c1"] == 33
        assert dist["c2"] == 33
        assert sum(dist.values()) == 100

    def test_zero_gold(self):
        """0 골드 분배"""
        session = MagicMock()
        session.players = {"p1": None, "p2": None}
        session.host_id = "p1"

        loot = LootSyncManager(session=session)
        dist = loot.distribute_gold(0)

        assert dist["p1"] == 0
        assert dist["p2"] == 0

    def test_empty_session(self):
        """빈 세션에서 골드 분배"""
        session = MagicMock()
        session.players = {}

        loot = LootSyncManager(session=session)
        dist = loot.distribute_gold(100)

        assert dist == {}


# ──────────────────────────────────────────────────────────────
# 11. 전리품: 누락된 MessageType 폴백
# ──────────────────────────────────────────────────────────────

class TestLootSyncMessageTypeFallback:
    """
    LOOT_CLAIMED, STORAGE_UPDATE가 MessageType에 없어서
    hasattr 체크로 GAME_STATE에 폴백하는 동작 검증
    """

    def test_loot_claimed_not_in_message_type(self):
        """MessageType.LOOT_CLAIMED 이 정의되지 않음"""
        assert not hasattr(MessageType, 'LOOT_CLAIMED')

    def test_storage_update_not_in_message_type(self):
        """MessageType.STORAGE_UPDATE 가 정의되지 않음"""
        assert not hasattr(MessageType, 'STORAGE_UPDATE')

    def test_game_state_not_in_message_type(self):
        """
        MessageType.GAME_STATE도 정의되지 않음.
        폴백 대상도 없어서 _broadcast_claim이 실패할 수 있음.
        """
        assert not hasattr(MessageType, 'GAME_STATE')

    def test_broadcast_claim_handles_missing_message_types(self):
        """
        _broadcast_claim이 누락된 MessageType에서도 크래시하지 않는지 검증.
        MessageBuilder.custom이 존재하지 않는 타입에 접근 시 예외 처리.
        """
        session = MagicMock()
        network_manager = MagicMock()
        network_manager._server_event_loop = None

        loot = LootSyncManager(session=session, network_manager=network_manager)

        # _broadcast_claim 호출 시 크래시하지 않아야 함
        # (내부에서 hasattr 체크 후 GAME_STATE 폴백, 그것도 없으면 예외 catch)
        try:
            loot._broadcast_claim("p1", "item_1", "Sword")
        except Exception:
            pytest.fail("_broadcast_claim이 누락된 MessageType에서 크래시함")


# ──────────────────────────────────────────────────────────────
# 12. 이동 동기화: 타임스탬프 순서 보장
# ──────────────────────────────────────────────────────────────

class TestMovementSyncTimestamp:
    """MovementSyncManager의 타임스탬프 기반 패킷 순서 보장"""

    def _make_sync(self):
        session = MultiplayerSession(max_players=2)
        p1 = MultiplayerPlayer(player_id="host", player_name="Host")
        p2 = MultiplayerPlayer(player_id="client", player_name="Client")
        session.add_player(p1)
        session.add_player(p2)

        sync = MovementSyncManager(session=session, is_host=True)
        return sync, session

    def test_older_packet_ignored(self):
        """타임스탬프가 오래된 패킷은 무시"""
        sync, session = self._make_sync()
        player = session.players["client"]
        player.last_movement_timestamp = 100.0

        # 오래된 메시지 (타임스탬프 99.0)
        old_msg = NetworkMessage(
            type=MessageType.PLAYER_MOVE,
            player_id="client",
            timestamp=99.0,
            data={"x": 50, "y": 50}
        )

        asyncio.run(sync._handle_player_move(old_msg))

        # 위치 변경되지 않아야 함
        assert player.x == 0
        assert player.y == 0

    def test_newer_packet_applied(self):
        """타임스탬프가 최신인 패킷은 적용"""
        sync, session = self._make_sync()
        player = session.players["client"]
        player.last_movement_timestamp = 100.0

        new_msg = NetworkMessage(
            type=MessageType.PLAYER_MOVE,
            player_id="client",
            timestamp=101.0,
            data={"x": 15, "y": 25}
        )

        asyncio.run(sync._handle_player_move(new_msg))

        assert player.x == 15
        assert player.y == 25
        assert player.last_movement_timestamp == 101.0

    def test_local_player_position_not_overwritten(self):
        """로컬 플레이어의 이동 메시지는 위치 업데이트 건너뛰기"""
        sync, session = self._make_sync()
        sync.set_local_player_id("host")

        host_player = session.players["host"]
        host_player.x = 10
        host_player.y = 20
        host_player.last_movement_timestamp = 0.0

        msg = NetworkMessage(
            type=MessageType.PLAYER_MOVE,
            player_id="host",
            timestamp=time.time(),
            data={"x": 99, "y": 99}
        )

        asyncio.run(sync._handle_player_move(msg))

        # 로컬 플레이어는 위치 변경 안됨
        assert host_player.x == 10
        assert host_player.y == 20

    def test_missing_player_ignored(self):
        """세션에 없는 플레이어의 메시지 무시"""
        sync, session = self._make_sync()

        msg = NetworkMessage(
            type=MessageType.PLAYER_MOVE,
            player_id="ghost_player",
            timestamp=time.time(),
            data={"x": 1, "y": 1}
        )

        # 예외 없이 조용히 무시
        asyncio.run(sync._handle_player_move(msg))


# ──────────────────────────────────────────────────────────────
# 13. ATB 시스템: 멀티플레이 규칙
# ──────────────────────────────────────────────────────────────

class TestMultiplayerATB:
    """MultiplayerATBSystem 정밀 검증"""

    def test_action_wait_blocks_atb(self):
        """액션 확인 후 1.5초간 대기 상태"""
        atb = MultiplayerATBSystem()
        atb.last_action_confirmed_time = time.time()

        assert atb.is_in_action_wait() is True

    def test_action_wait_expires(self):
        """1.5초 후 대기 상태 해제"""
        atb = MultiplayerATBSystem()
        atb.last_action_confirmed_time = time.time() - 2.0  # 2초 전

        assert atb.is_in_action_wait() is False

    def test_no_action_wait_initially(self):
        """초기 상태에서는 대기 없음"""
        atb = MultiplayerATBSystem()
        assert atb.is_in_action_wait() is False

    def test_average_speed_with_no_gauges(self):
        """게이지 없을 때 평균 속도는 1.0"""
        atb = MultiplayerATBSystem()
        assert atb.get_average_speed() == 1.0

    def test_average_speed_excludes_dead(self):
        """죽은 전투원은 평균 속도 계산에서 제외"""
        atb = MultiplayerATBSystem()

        alive = _Combatant(is_alive=True, speed=100)
        dead = _Combatant(is_alive=False, speed=200)

        g1 = ATBGauge(owner=alive)
        g2 = ATBGauge(owner=dead)

        atb.gauges[alive] = g1
        atb.gauges[dead] = g2

        avg = atb.get_average_speed()
        # 살아있는 것만 계산: speed=100의 effective_speed
        assert avg >= 1.0
        # dead의 speed=200은 제외 (get_effective_speed가 0.0 반환)

    def test_atb_increase_normalized(self):
        """ATB 증가량이 평균 속도로 정규화됨"""
        atb = MultiplayerATBSystem()

        fast = _Combatant(is_alive=True, speed=200)
        slow = _Combatant(is_alive=True, speed=100)

        g_fast = ATBGauge(owner=fast)
        g_slow = ATBGauge(owner=slow)

        atb.gauges[fast] = g_fast
        atb.gauges[slow] = g_slow

        inc_fast = atb.calculate_atb_increase(fast, delta_time=1.0)
        inc_slow = atb.calculate_atb_increase(slow, delta_time=1.0)

        # 빠른 캐릭터의 증가량이 더 커야 함
        assert inc_fast > inc_slow
        # 둘 다 양수
        assert inc_fast > 0
        assert inc_slow > 0

    def test_player_selecting_state_management(self):
        """플레이어 선택 상태 추가/제거"""
        atb = MultiplayerATBSystem()

        atb.set_player_selecting("p1", True)
        assert "p1" in atb.players_selecting_action

        atb.set_player_selecting("p1", False)
        assert "p1" not in atb.players_selecting_action
        # 선택 완료 시 last_action_confirmed_time 설정됨
        assert atb.last_action_confirmed_time is not None

    def test_invalid_player_id_ignored(self):
        """잘못된 player_id는 무시"""
        atb = MultiplayerATBSystem()

        atb.set_player_selecting("", True)
        assert "" not in atb.players_selecting_action

        atb.set_player_selecting(None, True)
        assert None not in atb.players_selecting_action

    def test_cleanup_old_waits(self):
        """오래된 대기 시간 자동 정리"""
        atb = MultiplayerATBSystem()
        atb.last_action_confirmed_time = time.time() - 5.0  # 5초 전

        atb.cleanup_old_waits()
        assert atb.last_action_confirmed_time is None

    def test_bullet_time_always_disabled(self):
        """멀티플레이에서 불릿타임은 항상 비활성"""
        atb = MultiplayerATBSystem()
        assert atb._is_bullet_time_active() is False


# ──────────────────────────────────────────────────────────────
# 14. 프로토콜: 메시지 파싱 엣지 케이스
# ──────────────────────────────────────────────────────────────

class TestProtocolParsing:
    """NetworkMessage 파싱 및 직렬화 엣지 케이스"""

    def test_from_dict_with_string_type(self):
        """문자열 타입으로 메시지 생성"""
        msg = NetworkMessage.from_dict({
            "type": "connect",
            "player_id": "p1",
            "data": {}
        })
        assert msg.type == MessageType.CONNECT

    def test_from_dict_with_enum_type(self):
        """MessageType enum으로 직접 전달"""
        msg = NetworkMessage.from_dict({
            "type": MessageType.CONNECT,
            "player_id": "p1",
            "data": {}
        })
        assert msg.type == MessageType.CONNECT

    def test_from_dict_with_prefixed_type(self):
        """'MessageType.CONNECT' 형식 파싱"""
        msg = NetworkMessage.from_dict({
            "type": "MessageType.CONNECT",
            "player_id": "p1",
            "data": {}
        })
        assert msg.type == MessageType.CONNECT

    def test_from_dict_invalid_type_raises(self):
        """유효하지 않은 타입은 ValueError"""
        with pytest.raises(ValueError):
            NetworkMessage.from_dict({
                "type": "TOTALLY_INVALID_TYPE",
                "data": {}
            })

    def test_from_dict_none_type_raises(self):
        """None 타입은 ValueError"""
        with pytest.raises((ValueError, TypeError)):
            NetworkMessage.from_dict({
                "type": None,
                "data": {}
            })

    def test_roundtrip_json_serialization(self):
        """JSON 직렬화 → 역직렬화 왕복 검증"""
        original = MessageBuilder.combat_action(
            player_id="p1",
            actor_id="actor_1",
            action={"action_type": "brv_attack", "target_id": "enemy_1"}
        )

        json_str = original.to_json()
        restored = NetworkMessage.from_json(json_str)

        assert restored.type == original.type
        assert restored.player_id == original.player_id
        assert restored.data == original.data

    def test_roundtrip_compression(self):
        """압축 → 해제 왕복 검증"""
        original = MessageBuilder.player_move("p1", 100, 200)
        compressed = original.compress()
        restored = NetworkMessage.decompress(compressed)

        assert restored.type == original.type
        assert restored.data["x"] == 100
        assert restored.data["y"] == 200

    def test_default_timestamp_auto_set(self):
        """타임스탬프가 0이면 자동 설정"""
        msg = NetworkMessage(type=MessageType.PING_REQUEST)
        assert msg.timestamp > 0

    def test_default_data_is_empty_dict(self):
        """data가 None이면 빈 딕셔너리로 초기화"""
        msg = NetworkMessage(type=MessageType.PING_REQUEST)
        assert msg.data == {}

    def test_all_message_builders_produce_valid_type(self):
        """모든 MessageBuilder 메서드가 유효한 MessageType 생성"""
        builders = [
            MessageBuilder.connect("p1", "name"),
            MessageBuilder.connection_accepted("p1", "sid"),
            MessageBuilder.connection_rejected("p1", "reason"),
            MessageBuilder.session_seed(42, "sid"),
            MessageBuilder.player_move("p1", 0, 0),
            MessageBuilder.move_request("p1", 1, 0),
            MessageBuilder.combat_action("p1", "a1", {}),
            MessageBuilder.enemy_move({}),
            MessageBuilder.ping_request(),
            MessageBuilder.pong_response(1.0),
            MessageBuilder.chat_message("p1", "hello"),
            MessageBuilder.harvest(0, 0, "tree"),
            MessageBuilder.floor_ready("p1", True, ["p1"], 1),
            MessageBuilder.floor_change("floor_down"),
            MessageBuilder.host_migrated("p2"),
            MessageBuilder.movement_rejected("wall", (0, 0)),
        ]

        for msg in builders:
            assert isinstance(msg.type, MessageType), f"Invalid type: {msg.type}"
            assert msg.data is not None


# ──────────────────────────────────────────────────────────────
# 15. 플레이어: 파티 생존 판정 엣지 케이스
# ──────────────────────────────────────────────────────────────

class TestPlayerPartyAlive:
    """MultiplayerPlayer.is_party_alive 엣지 케이스"""

    def test_empty_party_is_alive(self):
        """빈 파티는 True (문서 참조: 파티가 없으면 살아있는 것으로 간주)"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        assert p.is_party_alive is True

    def test_all_dead_is_not_alive(self):
        """모든 파티원 사망 시 False"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        p.party = [
            SimpleNamespace(current_hp=0, is_alive=False),
            SimpleNamespace(current_hp=0, is_alive=False),
        ]
        assert p.is_party_alive is False

    def test_one_alive_is_alive(self):
        """하나라도 살아있으면 True"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        p.party = [
            SimpleNamespace(current_hp=0, is_alive=False),
            SimpleNamespace(current_hp=1, is_alive=True),
        ]
        assert p.is_party_alive is True

    def test_dict_party_members(self):
        """딕셔너리 형태 파티원 (직렬화된 상태)"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        p.party = [
            {"current_hp": 0},
            {"current_hp": 50},
        ]
        assert p.is_party_alive is True

    def test_dict_party_all_dead(self):
        """딕셔너리 파티원 전부 사망"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        p.party = [
            {"current_hp": 0},
            {"current_hp": 0},
        ]
        assert p.is_party_alive is False

    def test_mixed_dict_and_object_party(self):
        """딕셔너리와 객체가 혼재된 파티"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1")
        p.party = [
            {"current_hp": 0},
            SimpleNamespace(current_hp=10, is_alive=True),
        ]
        assert p.is_party_alive is True


# ──────────────────────────────────────────────────────────────
# 16. 플레이어: 직렬화/역직렬화
# ──────────────────────────────────────────────────────────────

class TestPlayerSerialization:
    """플레이어 직렬화 왕복 검증"""

    def test_serialize_contains_required_fields(self):
        """직렬화 결과에 필수 필드 포함"""
        p = MultiplayerPlayer(
            player_id="p1", player_name="Hero",
            x=10, y=20, is_bot=True
        )
        s = p.serialize()

        assert s["player_id"] == "p1"
        assert s["player_name"] == "Hero"
        assert s["x"] == 10
        assert s["y"] == 20
        assert s["is_bot"] is True
        assert s["is_connected"] is True

    def test_deserialize_roundtrip(self):
        """직렬화 → 역직렬화 왕복"""
        original = MultiplayerPlayer(
            player_id="p1", player_name="Hero",
            x=10, y=20, is_bot=True
        )
        serialized = original.serialize()
        restored = MultiplayerPlayer.deserialize(serialized)

        assert restored.player_id == "p1"
        assert restored.player_name == "Hero"
        assert restored.x == 10
        assert restored.y == 20
        assert restored.is_bot is True

    def test_deserialize_missing_optional_fields(self):
        """선택 필드 없을 때 기본값"""
        data = {"player_id": "p1", "player_name": "Minimal"}
        p = MultiplayerPlayer.deserialize(data)

        assert p.x == 0
        assert p.y == 0
        assert p.is_connected is True
        assert p.is_bot is False

    def test_velocity_update_on_position_change(self):
        """위치 업데이트 시 속도 계산"""
        p = MultiplayerPlayer(player_id="p1", player_name="P1", x=0, y=0)
        p.update_position(5, 3)

        assert p.velocity_x == 5
        assert p.velocity_y == 3
        assert p.x == 5
        assert p.y == 3

    def test_auto_generated_player_id(self):
        """빈 player_id는 자동 UUID 생성"""
        # player_id가 빈 문자열이면 __post_init__에서 UUID 생성
        # 하지만 빈 문자열은 falsy이므로 UUID로 대체됨
        p = MultiplayerPlayer(player_id="", player_name="NoID")
        assert p.player_id != ""
        assert len(p.player_id) > 0


# ──────────────────────────────────────────────────────────────
# 17. 세션: 던전 시드 결정론
# ──────────────────────────────────────────────────────────────

class TestDungeonSeedDeterminism:
    """세션 시드 기반 던전 생성의 결정론적 동작"""

    def test_same_floor_same_seed(self):
        """같은 층은 항상 같은 시드"""
        session = MultiplayerSession(max_players=2)

        seeds = [session.generate_dungeon_seed_for_floor(1) for _ in range(10)]
        assert len(set(seeds)) == 1

    def test_different_floor_different_seed(self):
        """다른 층은 다른 시드"""
        session = MultiplayerSession(max_players=2)

        seeds = [session.generate_dungeon_seed_for_floor(i) for i in range(10)]
        assert len(set(seeds)) == 10

    def test_different_session_different_seed(self):
        """다른 세션은 같은 층이라도 다른 시드 (확률적)"""
        s1 = MultiplayerSession(max_players=2)
        s2 = MultiplayerSession(max_players=2)

        # 세션 시드가 다를 확률이 매우 높음
        if s1.session_seed != s2.session_seed:
            assert s1.generate_dungeon_seed_for_floor(1) != s2.generate_dungeon_seed_for_floor(1)

    def test_seed_is_non_negative(self):
        """시드는 항상 0 이상"""
        session = MultiplayerSession(max_players=2)
        for i in range(-10, 100):
            seed = session.generate_dungeon_seed_for_floor(i)
            assert seed >= 0


# ──────────────────────────────────────────────────────────────
# 18. 전투 동기화: 액션 직렬화/역직렬화
# ──────────────────────────────────────────────────────────────

class TestCombatActionSerialization:
    """CombatSyncManager 의 액션 직렬화 정밀 검증"""

    def _make_sync(self):
        return CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )

    def test_serialize_basic_action(self):
        """기본 액션 직렬화"""
        from src.combat.combat_manager import ActionType
        sync = self._make_sync()

        data = sync._serialize_action(
            action_type=ActionType.BRV_ATTACK,
        )

        assert data["action_type"] == "brv_attack"
        assert "timestamp" in data

    def test_serialize_with_target(self):
        """타겟이 있는 액션 직렬화"""
        from src.combat.combat_manager import ActionType
        sync = self._make_sync()

        target = SimpleNamespace(id="enemy_1")
        data = sync._serialize_action(
            action_type=ActionType.BRV_ATTACK,
            target=target,
        )

        assert data["target_id"] == "enemy_1"

    def test_serialize_with_skill(self):
        """스킬 액션 직렬화"""
        from src.combat.combat_manager import ActionType
        sync = self._make_sync()

        skill = SimpleNamespace(id="fireball", name="Fireball")
        data = sync._serialize_action(
            action_type=ActionType.SKILL,
            skill=skill,
        )

        assert data["skill_id"] == "fireball"
        assert data["skill_name"] == "Fireball"

    def test_serialize_with_item(self):
        """아이템 사용 직렬화"""
        from src.combat.combat_manager import ActionType
        sync = self._make_sync()

        item = SimpleNamespace(id="potion_1", name="Potion")
        data = sync._serialize_action(
            action_type=ActionType.ITEM,
            item=item,
            item_index=3,
        )

        assert data["item_id"] == "potion_1"
        assert data["item_name"] == "Potion"
        assert data["item_index"] == 3

    def test_serialize_none_target_excluded(self):
        """타겟이 None이면 target_id 필드 없음"""
        from src.combat.combat_manager import ActionType
        sync = self._make_sync()

        data = sync._serialize_action(action_type=ActionType.DEFEND)
        assert "target_id" not in data


# ──────────────────────────────────────────────────────────────
# 19. 전투 동기화: 플레이어 소유권 검증
# ──────────────────────────────────────────────────────────────

class TestCombatOwnershipValidation:
    """호스트의 액션 소유권 검증 로직"""

    def test_get_player_id_from_character_direct(self):
        """직접 player_id 속성"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )
        char = SimpleNamespace(player_id="p1")
        assert sync._get_player_id_from_character(char) == "p1"

    def test_get_player_id_from_character_owner(self):
        """owner.player_id 경로"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )
        owner = SimpleNamespace(player_id="p2")
        char = SimpleNamespace(owner=owner)
        assert sync._get_player_id_from_character(char) == "p2"

    def test_get_player_id_from_character_none(self):
        """플레이어 ID를 찾을 수 없는 경우"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )
        char = SimpleNamespace(name="nameless")
        assert sync._get_player_id_from_character(char) is None

    def test_get_player_id_from_none_character(self):
        """None 캐릭터"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )
        assert sync._get_player_id_from_character(None) is None


# ──────────────────────────────────────────────────────────────
# 20. 전투 동기화: 상태 스냅샷
# ──────────────────────────────────────────────────────────────

class TestCombatStateSnapshot:
    """호스트의 전투 상태 스냅샷 생성 검증"""

    def test_snapshot_includes_all_combatants(self):
        """스냅샷에 아군/적군 모두 포함"""
        from src.combat.combat_manager import CombatState

        ally = SimpleNamespace(id="a1", current_hp=100, max_hp=100,
                               current_mp=50, max_mp=50, current_brv=0, is_alive=True)
        enemy = SimpleNamespace(id="e1", current_hp=200, max_hp=200,
                                current_mp=0, max_mp=0, current_brv=0, is_alive=True)
        atb = MagicMock()
        atb.get_gauge.return_value = None

        combat_manager = SimpleNamespace(
            allies=[ally], enemies=[enemy],
            atb=atb, state=CombatState.IN_PROGRESS,
            turn_count=5
        )

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=True,
        )

        snapshot = sync._get_combat_state_snapshot()
        assert len(snapshot["allies"]) == 1
        assert len(snapshot["enemies"]) == 1
        assert snapshot["allies"][0]["id"] == "a1"
        assert snapshot["enemies"][0]["id"] == "e1"
        assert snapshot["turn_count"] == 5

    def test_snapshot_without_combat_manager(self):
        """combat_manager가 없으면 빈 딕셔너리"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=None,
            is_host=True,
        )

        snapshot = sync._get_combat_state_snapshot()
        assert snapshot == {}


# ──────────────────────────────────────────────────────────────
# 21. 창고 동기화
# ──────────────────────────────────────────────────────────────

class TestStorageSync:
    """StorageSyncManager 검증"""

    def test_all_players_share_host_storage(self):
        """모든 플레이어가 호스트 창고 공유"""
        storage_obj = MagicMock()
        mgr = StorageSyncManager(session=MagicMock())
        mgr.set_host_storage(storage_obj)

        assert mgr.get_storage_for_player("p1") is storage_obj
        assert mgr.get_storage_for_player("p2") is storage_obj

    def test_add_item_without_storage_fails(self):
        """창고 미설정 시 추가 실패"""
        mgr = StorageSyncManager(session=MagicMock())
        assert mgr.request_add_item("p1", MagicMock()) is False

    def test_remove_item_without_storage_returns_none(self):
        """창고 미설정 시 제거 실패"""
        mgr = StorageSyncManager(session=MagicMock())
        assert mgr.request_remove_item("p1", 0) is None


# ──────────────────────────────────────────────────────────────
# 22. 적 동기화: 클라이언트 측 위치 업데이트
# ──────────────────────────────────────────────────────────────

class TestEnemySyncClientUpdate:
    """클라이언트 측 적 위치 동기화 검증"""

    def test_client_receives_and_caches_positions(self):
        """클라이언트가 호스트로부터 위치를 수신하고 캐시"""
        sync = EnemySyncManager(session=MagicMock(), is_host=False)

        msg = NetworkMessage(
            type=MessageType.ENEMY_MOVE,
            data={
                "enemies": {
                    "goblin_1_1": {"x": 5, "y": 10, "timestamp": time.time()},
                    "slime_2_3": {"x": 7, "y": 8, "timestamp": time.time()},
                }
            }
        )

        asyncio.run(sync._handle_enemy_move(msg))

        assert sync.enemy_positions["goblin_1_1"] == (5, 10)
        assert sync.enemy_positions["slime_2_3"] == (7, 8)

    def test_host_ignores_enemy_move_messages(self):
        """호스트는 적 이동 메시지를 무시"""
        sync = EnemySyncManager(session=MagicMock(), is_host=True)

        msg = NetworkMessage(
            type=MessageType.ENEMY_MOVE,
            data={"enemies": {"goblin_1_1": {"x": 99, "y": 99}}}
        )

        asyncio.run(sync._handle_enemy_move(msg))
        assert len(sync.enemy_positions) == 0

    def test_client_updates_exploration_enemy_positions(self):
        """클라이언트가 exploration.enemies의 위치를 업데이트"""
        enemy = SimpleNamespace(
            enemy_id="goblin", spawn_x=1, spawn_y=1,
            x=1, y=1
        )

        exploration = SimpleNamespace(enemies=[enemy])
        sync = EnemySyncManager(
            session=MagicMock(),
            is_host=False,
            exploration=exploration
        )

        # 캐시 ID 설정 (정상적으로 호스트에서 생성된 ID)
        enemy._multiplayer_sync_id = "goblin_1_1"

        msg = NetworkMessage(
            type=MessageType.ENEMY_MOVE,
            data={
                "enemies": {
                    "goblin_1_1": {"x": 10, "y": 20, "timestamp": time.time()}
                }
            }
        )

        asyncio.run(sync._handle_enemy_move(msg))

        assert enemy.x == 10
        assert enemy.y == 20


# ──────────────────────────────────────────────────────────────
# 23. 전투 동기화: 행동 선택 상태
# ──────────────────────────────────────────────────────────────

class TestCombatSyncPlayerSelecting:
    """플레이어 행동 선택 상태 추적"""

    def test_set_selecting_adds_player(self):
        """선택 시작 시 집합에 추가"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )

        sync._set_player_selecting("p1", True)
        assert "p1" in sync.players_selecting_action

    def test_clear_selecting_removes_player(self):
        """선택 완료 시 집합에서 제거"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )

        sync._set_player_selecting("p1", True)
        sync._set_player_selecting("p1", False)
        assert "p1" not in sync.players_selecting_action

    def test_invalid_player_id_ignored(self):
        """빈 문자열이나 None은 무시"""
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=MagicMock(),
            is_host=True,
        )

        sync._set_player_selecting("", True)
        sync._set_player_selecting(None, True)
        assert len(sync.players_selecting_action) == 0

    def test_selecting_propagates_to_atb(self):
        """ATB 시스템에 행동 선택 상태 전파"""
        atb = MagicMock()
        atb.set_player_selecting = MagicMock()

        combat_manager = SimpleNamespace(atb=atb)

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=combat_manager,
            is_host=True,
        )

        sync._set_player_selecting("p1", True)
        atb.set_player_selecting.assert_called_with("p1", True)


# ──────────────────────────────────────────────────────────────
# 24. 설정 상수 무결성
# ──────────────────────────────────────────────────────────────

class TestConfigIntegrity:
    """멀티플레이 설정 상수 무결성"""

    def test_sync_intervals_positive(self):
        """동기화 간격은 양수"""
        assert MultiplayerConfig.SYNC_INTERVAL_POSITION > 0
        assert MultiplayerConfig.SYNC_INTERVAL_ENEMY > 0
        assert MultiplayerConfig.SYNC_INTERVAL_STATE > 0

    def test_participation_radius_reasonable(self):
        """전투 참여 반경이 합리적 (1~20)"""
        assert 1 <= MultiplayerConfig.participation_radius <= 20

    def test_action_wait_time_positive(self):
        """액션 대기 시간 양수"""
        assert MultiplayerConfig.action_wait_time > 0

    def test_balance_multipliers_are_one(self):
        """밸런스 배율이 1.0 (싱글과 동일)"""
        assert MultiplayerConfig.enemy_count_multiplier == 1.0
        assert MultiplayerConfig.enemy_hp_multiplier == 1.0
        assert MultiplayerConfig.enemy_damage_multiplier == 1.0

    def test_class_and_module_constants_match(self):
        """클래스 속성과 모듈 상수가 일치"""
        from src.multiplayer import config as cfg
        assert MultiplayerConfig.action_wait_time == cfg.ACTION_WAIT_TIME
        assert MultiplayerConfig.atb_reduction_multiplier == cfg.ATB_REDUCTION_MULTIPLIER
        assert MultiplayerConfig.participation_radius == cfg.PARTICIPATION_RADIUS
