"""
멀티플레이어 전투 동기화 정밀 시뮬레이션 테스트

호스트-권위 모델의 핵심 동기화 시나리오를 검증:
1. 클라이언트 턴 처리 격리 (독립 턴 처리 방지)
2. ACTION_SELECTION_START → 클라이언트 턴 활성화
3. COMBAT_ACTION → 호스트 실행 → ACTION_RESULT 브로드캐스트
4. 하트비트 STATE_UPDATE → 클라이언트 상태 동기화
5. 전투 종료 동기화
"""

import asyncio
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.combat.combat_manager import ActionType, CombatState
from src.multiplayer.combat_sync import CombatSyncManager
from src.multiplayer.protocol import MessageBuilder, MessageType, NetworkMessage
from src.ui.combat_ui import CombatUI, CombatUIState


# ── 헬퍼: 미니멀 오브젝트 팩토리 ──────────────────────────────────────────


def _make_character(name: str, player_id: str, *, hp: int = 200, mp: int = 50,
                    brv: int = 100, speed: int = 60, is_enemy: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"{name.lower().replace(' ', '_')}",
        name=name,
        player_id=player_id,
        owner_player_id=player_id,
        current_hp=hp, max_hp=hp,
        current_mp=mp, max_mp=mp,
        current_brv=brv, max_brv=300,
        speed=speed,
        is_alive=True,
        is_ghost=False,
        is_broken=False,
        is_enemy=is_enemy,
        active_buffs={},
        status_manager=SimpleNamespace(
            status_effects=[],
            can_act=lambda: True,
            update_duration=lambda: [],
        ),
    )


def _make_enemy(name: str, *, hp: int = 300, brv: int = 80) -> SimpleNamespace:
    char = _make_character(name, "enemy", hp=hp, brv=brv, is_enemy=True)
    char.enemy_id = name.lower().replace(" ", "_")
    return char


def _make_gauge(owner: Any, current: float = 0.0, threshold: int = 1000) -> SimpleNamespace:
    return SimpleNamespace(
        owner=owner,
        current=current,
        max_gauge=2000,
        threshold=threshold,
        is_casting=False,
        is_stunned=False,
        is_paralyzed=False,
        is_sleeping=False,
        is_confused=False,
        haste_multiplier=1.0,
        slow_multiplier=1.0,
        last_acted_turn=0,
        can_act=property(lambda self: self.current >= self.threshold),
    )


def _make_atb_system(combatants: List[Any], ready_ids: Optional[set] = None):
    """ATB 시스템 모의 생성 (ready_ids에 있는 캐릭터만 행동 가능)"""
    ready_ids = ready_ids or set()
    # SimpleNamespace는 unhashable → id 기반 dict + lookup 함수 사용
    gauges_by_id = {}
    for c in combatants:
        g = SimpleNamespace(
            current=1000.0 if c.id in ready_ids else 500.0,
            max_gauge=2000,
            threshold=1000,
            is_casting=False,
            last_acted_turn=0,
            can_act=(c.id in ready_ids) and getattr(c, 'is_alive', True),
        )
        gauges_by_id[c.id] = g

    def _get_gauge(char):
        cid = getattr(char, 'id', None)
        return gauges_by_id.get(cid)

    atb = MagicMock()
    atb.get_gauge = _get_gauge
    atb.get_action_order = lambda: [c for c in combatants if c.id in ready_ids and getattr(c, 'is_alive', True)]
    atb.consume_atb = MagicMock()
    atb.set_player_selecting = MagicMock()
    atb.players_selecting_action = set()
    atb.enabled = True
    atb.gauges = gauges_by_id
    atb.combatants = combatants
    return atb


def _make_combat_manager(allies, enemies, atb=None):
    cm = SimpleNamespace(
        allies=allies,
        enemies=enemies,
        atb=atb or _make_atb_system(allies + enemies),
        state=CombatState.IN_PROGRESS,
        turn_count=0,
        update=MagicMock(),
        _on_turn_end=MagicMock(),
        execute_action=MagicMock(return_value={"success": True, "damage": 150}),
        execute_enemy_turn=MagicMock(return_value={"success": True, "damage": 80}),
        pending_chain_abilities=[],
        affinity_manager=None,
    )
    return cm


def _build_combat_ui(
    combat_manager: Any,
    *,
    local_player_id: str,
    is_host: bool,
    session: Any = None,
    network_manager: Any = None,
) -> CombatUI:
    """미니멀 CombatUI 생성 (update 루프 테스트용)"""
    ui = CombatUI.__new__(CombatUI)
    ui.local_player_id = local_player_id
    ui.session = session
    ui.network_manager = network_manager
    ui.combat_manager = combat_manager
    # is_multiplayer = (combat_sync_manager is not None) 이므로 기본적으로 설정
    # 싱글플레이 테스트에서는 호출 후 ui.combat_sync_manager = None으로 재설정
    ui.combat_sync_manager = MagicMock()
    ui.bot_manager = None
    ui.display_context = None

    ui.state = CombatUIState.WAITING_ATB
    ui.current_actor = None
    ui.action_menu = None
    ui.selected_action = None
    ui.selected_skill = None
    ui.selected_target = None
    ui.selected_item = None
    ui.selected_item_index = None
    ui.selected_card = None
    ui.card_hand = []
    ui.card_cursor = 0

    ui.messages = []
    ui.hit_queue = []
    ui.hit_delay_counter = 0
    ui.phase_message_timer = 0
    ui.phase_message_duration = 180
    ui.revival_message_timer = 0
    ui.revival_message_duration = 180
    ui.battle_ended = False
    ui.battle_result = None

    ui.local_party_ids = set()
    ui.is_mp_host = is_host
    ui._remote_action_timeout = 0.0
    ui._remote_action_actor = None
    ui._mp_combat_end_received = False
    ui._mp_combat_end_result = None
    ui._pending_remote_actors = {}
    ui._pending_remote_timeouts = {}

    ui.action_delay_frames = 0
    ui.action_delay_max = 90
    ui.action_delay_owner_player_id = None

    ui.process_hit_queue = MagicMock()
    ui.add_message = MagicMock()
    ui._create_action_menu = MagicMock(return_value="menu")
    ui._set_action_delay = MagicMock()
    ui._show_action_result = MagicMock()
    ui._is_action_delay_blocking_actor = MagicMock(return_value=False)
    ui._select_next_ready_actor = CombatUI._select_next_ready_actor.__get__(ui)

    return ui


# ── 시나리오 1: 클라이언트 턴 처리 격리 ───────────────────────────────────


class TestClientTurnIsolation:
    """클라이언트가 독립적으로 턴을 처리하지 않는지 검증"""

    def test_client_skips_combat_manager_update(self, monkeypatch):
        """클라이언트는 combat_manager.update()를 호출하지 않아야 함"""
        host_ally = _make_character("Host Warrior", "host_player")
        client_ally = _make_character("Client Mage", "client_player")
        enemy = _make_enemy("Goblin")

        atb = _make_atb_system([host_ally, client_ally, enemy])
        cm = _make_combat_manager([host_ally, client_ally], [enemy], atb)

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: True),
        )

        ui.update(delta_time=1.0)

        # 클라이언트는 combat_manager.update()를 호출하지 않아야 함
        cm.update.assert_not_called()

    def test_client_shows_action_menu_for_ready_local_character(self, monkeypatch):
        """클라이언트는 로컬 캐릭터 ATB 100%면 행동 메뉴를 직접 표시"""
        client_ally = _make_character("Client Mage", "client_player")
        enemy = _make_enemy("Goblin")

        # client_ally가 행동 가능 상태
        atb = _make_atb_system([client_ally, enemy], ready_ids={client_ally.id})
        cm = _make_combat_manager([client_ally], [enemy], atb)

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        monkeypatch.setattr("src.ui.combat_ui.play_sfx", lambda *a, **kw: None)

        ui.update(delta_time=1.0)

        # 클라이언트는 로컬 캐릭터 ATB가 차면 직접 행동 메뉴 표시
        assert ui.current_actor is client_ally
        assert ui.state == CombatUIState.ACTION_MENU

    def test_client_does_not_execute_enemy_ai(self, monkeypatch):
        """클라이언트에서 적 AI가 실행되지 않아야 함"""
        client_ally = _make_character("Client Mage", "client_player")
        enemy = _make_enemy("Goblin")

        # 적이 행동 가능 상태
        atb = _make_atb_system([client_ally, enemy], ready_ids={enemy.id})
        cm = _make_combat_manager([client_ally], [enemy], atb)

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: True),
        )

        ui.update(delta_time=1.0)

        # 적 AI가 실행되지 않아야 함
        cm.execute_enemy_turn.assert_not_called()

    def test_host_still_processes_turns_normally(self, monkeypatch):
        """호스트는 여전히 정상적으로 턴을 처리해야 함"""
        host_ally = _make_character("Host Warrior", "host_player")
        enemy = _make_enemy("Goblin")

        # host_ally가 행동 가능 상태
        atb = _make_atb_system([host_ally, enemy], ready_ids={host_ally.id})
        cm = _make_combat_manager([host_ally], [enemy], atb)

        ui = _build_combat_ui(cm, local_player_id="host_player", is_host=True)

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: True),
        )
        monkeypatch.setattr("src.ui.combat_ui.play_sfx", lambda *a, **kw: None)

        ui.update(delta_time=1.0)

        # 호스트는 combat_manager.update()를 호출해야 함
        cm.update.assert_called_once()
        # 호스트는 current_actor를 설정해야 함
        assert ui.current_actor is host_ally
        assert ui.state == CombatUIState.ACTION_MENU

    def test_singleplayer_unaffected(self, monkeypatch):
        """싱글플레이어는 영향 받지 않아야 함"""
        ally = _make_character("Solo Warrior", "solo_player")
        enemy = _make_enemy("Goblin")

        atb = _make_atb_system([ally, enemy], ready_ids={ally.id})
        cm = _make_combat_manager([ally], [enemy], atb)

        ui = _build_combat_ui(cm, local_player_id="solo_player", is_host=False)
        ui.is_mp_host = False  # 싱글플레이
        ui.combat_sync_manager = None  # 싱글플레이는 combat_sync_manager 없음

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: False),
        )
        monkeypatch.setattr("src.ui.combat_ui.play_sfx", lambda *a, **kw: None)

        ui.update(delta_time=1.0)

        # 싱글플레이는 정상 처리
        cm.update.assert_called_once()
        assert ui.current_actor is ally
        assert ui.state == CombatUIState.ACTION_MENU


# ── 시나리오 2: ACTION_SELECTION_START 콜백 턴 활성화 ─────────────────────


class TestActionSelectionStartCallback:
    """클라이언트가 ACTION_SELECTION_START 콜백으로만 턴을 활성화하는지 검증"""

    def test_callback_activates_local_character_turn(self):
        """ACTION_SELECTION_START 콜백이 로컬 캐릭터의 턴을 활성화"""
        client_ally = _make_character("Client Mage", "client_player")
        enemy = _make_enemy("Goblin")
        cm = _make_combat_manager([client_ally], [enemy])

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        sync = MagicMock()
        sync._find_character_by_id = MagicMock(return_value=client_ally)
        ui.combat_sync_manager = sync

        with patch("src.ui.combat_ui.play_sfx", lambda *a, **kw: None):
            ui._on_mp_action_selection_start(
                client_ally.id, client_ally.name, "client_player"
            )

        assert ui.current_actor is client_ally
        assert ui.state == CombatUIState.ACTION_MENU

    def test_callback_ignores_other_player_characters(self):
        """다른 플레이어의 캐릭터에 대한 콜백은 무시"""
        client_ally = _make_character("Client Mage", "client_player")
        host_ally = _make_character("Host Warrior", "host_player")
        cm = _make_combat_manager([client_ally, host_ally], [])

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        sync = MagicMock()
        sync._find_character_by_id = MagicMock(return_value=host_ally)
        ui.combat_sync_manager = sync

        ui._on_mp_action_selection_start(
            host_ally.id, host_ally.name, "host_player"
        )

        # 다른 플레이어의 캐릭터이므로 무시
        assert ui.current_actor is None


# ── 시나리오 3: 호스트 원격 액션 실행 ─────────────────────────────────────


class TestHostRemoteActionExecution:
    """호스트가 원격 플레이어의 액션을 수신하고 실행하는 흐름 검증"""

    def test_host_executes_remote_action_and_broadcasts(self):
        """호스트가 원격 액션 실행 후 결과를 브로드캐스트"""
        client_ally = _make_character("Client Mage", "client_player")
        enemy = _make_enemy("Goblin")

        network = MagicMock()
        network.broadcast = AsyncMock()

        cm = _make_combat_manager([client_ally], [enemy])

        sync = CombatSyncManager(
            session=MagicMock(),
            network_manager=network,
            combat_manager=cm,
            is_host=True,
        )

        result = asyncio.run(
            sync._execute_and_broadcast_action(
                "client_player",
                client_ally,
                ActionType.BRV_ATTACK,
                target=enemy,
            )
        )

        # 액션 실행 확인
        cm.execute_action.assert_called_once()
        # 브로드캐스트 확인
        network.broadcast.assert_awaited()

    def test_host_rejects_unauthorized_action(self):
        """호스트가 소유하지 않은 캐릭터에 대한 액션 거부"""
        host_ally = _make_character("Host Warrior", "host_player")
        cm = _make_combat_manager([host_ally], [])

        network = MagicMock()
        sync = CombatSyncManager(
            session=MagicMock(),
            network_manager=network,
            combat_manager=cm,
            is_host=True,
        )

        # 다른 플레이어가 호스트 캐릭터로 액션 시도
        message = MagicMock()
        message.player_id = "hacker_player"
        message.data = {
            "actor_id": host_ally.id,
            "action": {"action_type": "brv_attack"},
        }

        asyncio.run(sync._handle_combat_action(message, "hacker_player"))

        # 액션 실행되지 않아야 함
        cm.execute_action.assert_not_called()


# ── 시나리오 4: 하트비트 상태 동기화 ──────────────────────────────────────


class TestHeartbeatStateSync:
    """하트비트 STATE_UPDATE를 통한 클라이언트 상태 동기화 검증"""

    def test_heartbeat_syncs_hp_brv_status(self):
        """하트비트가 HP, BRV, 상태이상을 동기화"""
        ally = _make_character("Client Mage", "client_player", hp=200, brv=100)
        enemy = _make_enemy("Goblin", hp=300, brv=80)

        cm = _make_combat_manager([ally], [enemy])
        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=cm,
            is_host=False,
        )

        # 호스트에서 전투가 진행되어 HP/BRV가 변경됨
        sync._sync_combat_state({
            "allies": [{
                "id": ally.id,
                "current_hp": 150,
                "current_mp": 30,
                "current_brv": 200,
                "is_alive": True,
                "is_broken": False,
            }],
            "enemies": [{
                "id": enemy.id,
                "current_hp": 180,
                "current_brv": 0,
                "is_alive": True,
                "is_broken": True,
            }],
            "combat_state": "in_progress",
            "turn_count": 5,
        })

        # 동기화 확인
        assert ally.current_hp == 150
        assert ally.current_mp == 30
        assert ally.current_brv == 200
        assert enemy.current_hp == 180
        assert enemy.current_brv == 0
        assert enemy.is_broken is True
        assert cm.turn_count == 5

    def test_heartbeat_syncs_atb_values(self):
        """하트비트가 ATB 게이지 값을 동기화"""
        ally = _make_character("Client Mage", "client_player")
        cm = _make_combat_manager([ally], [])

        gauge = SimpleNamespace(current=0.0, max_gauge=2000)
        cm.atb = MagicMock()
        cm.atb.get_gauge = MagicMock(return_value=gauge)

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=cm,
            is_host=False,
        )

        sync._sync_combat_state({
            "allies": [{
                "id": ally.id,
                "current_hp": 200,
                "is_alive": True,
                "atb_current": 850.5,
                "atb_max": 2000,
            }],
            "enemies": [],
            "combat_state": "in_progress",
            "turn_count": 1,
        })

        assert gauge.current == 850.5
        assert gauge.max_gauge == 2000

    def test_heartbeat_syncs_death_state(self):
        """하트비트가 캐릭터 사망 상태를 동기화"""
        ally = _make_character("Client Mage", "client_player", hp=200)
        cm = _make_combat_manager([ally], [])

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=cm,
            is_host=False,
        )

        sync._sync_combat_state({
            "allies": [{
                "id": ally.id,
                "current_hp": 0,
                "is_alive": False,
            }],
            "enemies": [],
            "combat_state": "in_progress",
            "turn_count": 8,
        })

        assert ally.current_hp == 0
        assert ally.is_alive is False

    def test_state_update_with_action_triggers_ui_callback(self):
        """STATE_UPDATE에 포함된 액션 결과가 UI 콜백을 트리거"""
        ally = _make_character("Host Warrior", "host_player")
        enemy = _make_enemy("Goblin")

        cm = _make_combat_manager([ally], [enemy])
        cm.atb = MagicMock()
        cm.atb.get_gauge = MagicMock(return_value=None)
        cm.atb.consume_atb = MagicMock()

        callback_results = []

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=cm,
            is_host=False,
        )
        sync.on_action_result_callback = lambda data: callback_results.append(data)

        # 호스트의 액션 결과가 STATE_UPDATE에 포함
        message = MagicMock(spec=NetworkMessage)
        message.data = {
            "data": {
                "combat_action": {
                    "player_id": "host_player",
                    "actor_id": ally.id,
                    "action_type": "brv_attack",
                    "target_id": enemy.id,
                    "result": {"damage": 150, "brv_damage": 200},
                    "sequence": 1,
                },
                "combat_state": {
                    "allies": [{"id": ally.id, "current_hp": 200, "is_alive": True}],
                    "enemies": [{"id": enemy.id, "current_hp": 150, "is_alive": True}],
                    "combat_state": "in_progress",
                    "turn_count": 1,
                },
            }
        }

        asyncio.run(sync._handle_combat_state_update(message))

        # UI 콜백이 트리거되었는지 확인
        assert len(callback_results) == 1
        assert callback_results[0]["damage"] == 150
        assert callback_results[0]["brv_damage"] == 200


# ── 시나리오 5: 전투 종료 동기화 ──────────────────────────────────────────


class TestCombatEndSync:
    """전투 종료가 모든 플레이어에게 동기화되는지 검증"""

    def test_host_broadcasts_combat_end_on_victory(self):
        """호스트가 승리 시 COMBAT_END 브로드캐스트"""
        network = MagicMock()
        network.broadcast = AsyncMock()

        cm = _make_combat_manager([], [])
        sync = CombatSyncManager(
            session=MagicMock(),
            network_manager=network,
            combat_manager=cm,
            is_host=True,
        )

        asyncio.run(sync.broadcast_combat_end("victory"))

        network.broadcast.assert_awaited_once()

    def test_client_receives_combat_end(self):
        """클라이언트가 COMBAT_END를 수신하면 전투를 종료"""
        ally = _make_character("Client Mage", "client_player")
        cm = _make_combat_manager([ally], [])

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        ui._on_mp_combat_end("victory", None)

        assert ui._mp_combat_end_received is True
        assert ui.battle_ended is True
        assert ui.state == CombatUIState.BATTLE_END

    def test_client_combat_end_detected_in_update(self, monkeypatch):
        """클라이언트 update() 루프에서 COMBAT_END 수신을 감지"""
        ally = _make_character("Client Mage", "client_player")
        cm = _make_combat_manager([ally], [])

        ui = _build_combat_ui(cm, local_player_id="client_player", is_host=False)

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: True),
        )

        # COMBAT_END 수신 플래그 설정 (콜백에서 설정됨)
        ui._mp_combat_end_received = True
        cm.state = CombatState.VICTORY

        ui.update(delta_time=1.0)

        assert ui.battle_ended is True
        assert ui.state == CombatUIState.BATTLE_END


# ── 시나리오 6: 호스트 원격 턴 대기 및 타임아웃 ──────────────────────────


class TestHostRemoteTurnWaiting:
    """호스트가 원격 플레이어의 행동 대기 및 타임아웃 처리 검증"""

    def test_host_sends_action_selection_start_for_remote_character(self, monkeypatch):
        """호스트가 원격 플레이어 캐릭터의 턴에 ACTION_SELECTION_START 전송 (비차단)"""
        host_ally = _make_character("Host Warrior", "host_player")
        client_ally = _make_character("Client Mage", "client_player")

        atb = _make_atb_system([host_ally, client_ally], ready_ids={client_ally.id})
        cm = _make_combat_manager([host_ally, client_ally], [], atb)

        ui = _build_combat_ui(cm, local_player_id="host_player", is_host=True)
        sync = MagicMock()
        ui.combat_sync_manager = sync

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: True),
        )
        monkeypatch.setattr("src.ui.combat_ui.play_sfx", lambda *a, **kw: None)

        ui.update(delta_time=1.0)

        # 비차단: WAITING_REMOTE_ACTION이 아닌 WAITING_ATB 유지
        assert ui.state != CombatUIState.WAITING_REMOTE_ACTION
        # _pending_remote_actors에 추적됨
        remote_key = f"client_player:{client_ally.id}"
        assert remote_key in ui._pending_remote_actors
        # ACTION_SELECTION_START 전송 확인
        sync.send_action_selection_start_sync.assert_called_once_with(
            client_ally, "client_player"
        )

    def test_host_timeout_triggers_ai_auto_action(self, monkeypatch):
        """호스트의 원격 행동 대기 타임아웃 시 AI 자동 행동 (비차단)"""
        client_ally = _make_character("Client Mage", "client_player")
        cm = _make_combat_manager([client_ally], [])

        ui = _build_combat_ui(cm, local_player_id="host_player", is_host=True)
        # 비차단 방식: _pending_remote_actors에 타임아웃 임박 항목 추가
        remote_key = f"client_player:{client_ally.id}"
        ui._pending_remote_actors[remote_key] = (client_ally, 1)  # 1프레임 남음
        ui._execute_default_bot_action = MagicMock()

        monkeypatch.setattr(
            "src.multiplayer.game_mode.get_game_mode_manager",
            lambda: SimpleNamespace(is_multiplayer=lambda: True),
        )

        ui.update(delta_time=1.0)

        # 타임아웃 후 AI 자동 행동 실행
        ui._execute_default_bot_action.assert_called_once_with(client_ally)
        assert remote_key not in ui._pending_remote_actors

    def test_host_remote_action_callback_removes_pending(self):
        """호스트가 원격 액션 실행 완료 콜백으로 _pending_remote_actors에서 제거"""
        client_ally = _make_character("Client Mage", "client_player")
        cm = _make_combat_manager([client_ally], [])

        ui = _build_combat_ui(cm, local_player_id="host_player", is_host=True)
        remote_key = f"client_player:{client_ally.id}"
        ui._pending_remote_actors[remote_key] = (client_ally, 600)

        result = {"success": True, "damage": 100}
        ui._on_mp_remote_action_executed(client_ally, result)

        # _pending_remote_actors에서 제거됨
        assert remote_key not in ui._pending_remote_actors
        ui._show_action_result.assert_called_once_with(result)


# ── 시나리오 7: 전체 동기화 흐름 통합 테스트 ─────────────────────────────


class TestFullSyncFlow:
    """호스트 ↔ 클라이언트 전체 동기화 흐름 통합 검증"""

    def test_state_snapshot_contains_all_required_fields(self):
        """상태 스냅샷에 필요한 모든 필드가 포함"""
        ally = _make_character("Host Warrior", "host_player")
        enemy = _make_enemy("Goblin")

        cm = _make_combat_manager([ally], [enemy])

        sync = CombatSyncManager(
            session=MagicMock(),
            combat_manager=cm,
            is_host=True,
        )

        snapshot = sync._get_combat_state_snapshot()

        assert "combat_state" in snapshot
        assert "turn_count" in snapshot
        assert "allies" in snapshot
        assert "enemies" in snapshot
        assert len(snapshot["allies"]) == 1
        assert len(snapshot["enemies"]) == 1

        ally_data = snapshot["allies"][0]
        assert "id" in ally_data
        assert "current_hp" in ally_data
        assert "current_mp" in ally_data
        assert "current_brv" in ally_data
        assert "is_alive" in ally_data
        assert "status_effects" in ally_data

    def test_client_action_request_sends_to_host(self):
        """클라이언트가 액션 요청을 호스트에 전송"""
        client_ally = _make_character("Client Mage", "client_player")
        enemy = _make_enemy("Goblin")

        network = MagicMock()
        network.send = AsyncMock()

        cm = _make_combat_manager([client_ally], [enemy])

        sync = CombatSyncManager(
            session=MagicMock(),
            network_manager=network,
            combat_manager=cm,
            is_host=False,
        )

        result = asyncio.run(
            sync.send_action_request(
                player_id="client_player",
                actor=client_ally,
                action_type=ActionType.BRV_ATTACK,
                target=enemy,
            )
        )

        assert result is True
        network.send.assert_awaited_once()

    def test_host_only_sends_heartbeat(self, monkeypatch):
        """호스트만 하트비트를 전송"""
        ally = _make_character("Host Warrior", "host_player")
        cm = _make_combat_manager([ally], [])

        # 호스트 sync
        host_network = MagicMock()
        host_network.broadcast = AsyncMock()
        host_sync = CombatSyncManager(
            session=MagicMock(),
            network_manager=host_network,
            combat_manager=cm,
            is_host=True,
        )
        host_sync._last_heartbeat_time = 0  # 강제로 하트비트 트리거

        asyncio.run(host_sync.send_heartbeat())
        host_network.broadcast.assert_awaited_once()

        # 클라이언트 sync
        client_network = MagicMock()
        client_network.broadcast = AsyncMock()
        client_sync = CombatSyncManager(
            session=MagicMock(),
            network_manager=client_network,
            combat_manager=cm,
            is_host=False,
        )

        asyncio.run(client_sync.send_heartbeat())
        client_network.broadcast.assert_not_awaited()
