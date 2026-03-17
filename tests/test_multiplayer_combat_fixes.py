import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.combat.combat_manager import CombatState
from src.multiplayer.combat_sync import CombatSyncManager
from src.multiplayer.enemy_sync import EnemySyncManager
from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
from src.multiplayer.protocol import MessageType
from src.ui.combat_ui import CombatUI, CombatUIState


def test_legacy_request_action_wrapper_sends_message():
    network_manager = MagicMock()
    network_manager.send = AsyncMock()

    actor = SimpleNamespace(id="actor_1", player_id="client1")
    combat_manager = MagicMock()
    combat_manager.allies = [actor]
    combat_manager.enemies = []

    sync_manager = CombatSyncManager(
        session=MagicMock(),
        network_manager=network_manager,
        combat_manager=combat_manager,
        is_host=False
    )

    success = asyncio.run(
        sync_manager.request_action(
            player_id="client1",
            actor_id="actor_1",
            action_data={"action_type": "brv_attack"}
        )
    )

    assert success is True
    network_manager.send.assert_awaited_once()


def test_sync_combat_state_updates_atb_gauge():
    gauge = SimpleNamespace(current=0.0, max_gauge=2000)
    ally = SimpleNamespace(
        id="ally_1",
        current_hp=100,
        current_mp=50,
        current_brv=0,
        is_alive=True
    )

    atb = MagicMock()
    atb.get_gauge.return_value = gauge

    combat_manager = SimpleNamespace(
        allies=[ally],
        enemies=[],
        atb=atb,
        state=CombatState.IN_PROGRESS,
        turn_count=0
    )

    sync_manager = CombatSyncManager(
        session=MagicMock(),
        combat_manager=combat_manager,
        is_host=False
    )

    sync_manager._sync_combat_state(
        {
            "allies": [
                {
                    "id": "ally_1",
                    "current_hp": 80,
                    "current_mp": 40,
                    "current_brv": 120,
                    "is_alive": True,
                    "atb_current": 777,
                    "atb_max": 1500
                }
            ],
            "enemies": [],
            "combat_state": "in_progress",
            "turn_count": 3
        }
    )

    assert ally.current_hp == 80
    assert ally.current_mp == 40
    assert ally.current_brv == 120
    assert gauge.current == 777
    assert gauge.max_gauge == 1500
    assert combat_manager.turn_count == 3


def test_enemy_sync_uses_stable_id_when_enemy_moves():
    manager = EnemySyncManager(session=MagicMock(), is_host=True)
    enemy = SimpleNamespace(enemy_id="goblin", spawn_x=3, spawn_y=5, x=3, y=5)

    first_id = manager._get_enemy_id(enemy)
    enemy.x = 10
    enemy.y = 11
    second_id = manager._get_enemy_id(enemy)

    assert first_id == "goblin_3_5"
    assert first_id == second_id


def test_select_next_ready_actor_skips_remote_allies():
    ui = CombatUI.__new__(CombatUI)
    ui.local_player_id = "local"
    ui.session = None
    ui.combat_manager = SimpleNamespace(enemies=[])

    remote_actor = SimpleNamespace(player_id="remote")
    local_actor = SimpleNamespace(player_id="local")

    selected = ui._select_next_ready_actor(
        [remote_actor, local_actor],
        is_multiplayer=True
    )
    assert selected is local_actor

    selected_none = ui._select_next_ready_actor([remote_actor], is_multiplayer=True)
    assert selected_none is None


def _build_minimal_ui_for_update(
    ready_actor: SimpleNamespace,
    *,
    local_player_id: str,
    delay_owner_player_id: str,
    delay_frames: int = 30
) -> CombatUI:
    ui = CombatUI.__new__(CombatUI)
    ui.local_player_id = local_player_id
    ui.session = None
    ui.network_manager = None
    ui.combat_sync_manager = None
    ui.bot_manager = None

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

    # 멀티플레이 전투 동기화 필드
    ui.local_party_ids = set()
    ui.is_mp_host = False
    ui._remote_action_timeout = 0.0
    ui._remote_action_actor = None
    ui._mp_combat_end_received = False
    ui._mp_combat_end_result = None

    ui.action_delay_frames = delay_frames
    ui.action_delay_max = 90
    ui.action_delay_owner_player_id = delay_owner_player_id

    ui.process_hit_queue = MagicMock()
    ui.add_message = MagicMock()
    ui._create_action_menu = MagicMock(return_value="menu")

    ready_gauge = SimpleNamespace(current=1000, threshold=1000)
    atb = MagicMock()
    atb.get_action_order.return_value = [ready_actor]
    atb.get_gauge.side_effect = lambda actor: ready_gauge if actor is ready_actor else None
    atb.set_player_selecting = MagicMock()
    atb.players_selecting_action = set()
    atb.consume_atb = MagicMock()

    ui.combat_manager = SimpleNamespace(
        allies=[ready_actor],
        enemies=[],
        atb=atb,
        state=CombatState.IN_PROGRESS,
        update=MagicMock(),
        _on_turn_end=MagicMock()
    )
    return ui


def test_multiplayer_delay_allows_other_player_ready_turn(monkeypatch):
    actor = SimpleNamespace(name="Remote Ally", player_id="remote")
    ui = _build_minimal_ui_for_update(
        actor,
        local_player_id="remote",
        delay_owner_player_id="host"
    )

    monkeypatch.setattr(
        "src.multiplayer.game_mode.get_game_mode_manager",
        lambda: SimpleNamespace(is_multiplayer=lambda: True)
    )
    monkeypatch.setattr("src.ui.combat_ui.play_sfx", lambda *args, **kwargs: None)

    ui.update(delta_time=1.0)

    assert ui.current_actor is actor
    assert ui.state == CombatUIState.ACTION_MENU


def test_singleplayer_delay_still_blocks_ready_turn(monkeypatch):
    actor = SimpleNamespace(name="Solo Ally", player_id="solo")
    ui = _build_minimal_ui_for_update(
        actor,
        local_player_id="solo",
        delay_owner_player_id="solo"
    )

    monkeypatch.setattr(
        "src.multiplayer.game_mode.get_game_mode_manager",
        lambda: SimpleNamespace(is_multiplayer=lambda: False)
    )
    monkeypatch.setattr("src.ui.combat_ui.play_sfx", lambda *args, **kwargs: None)

    ui.update(delta_time=1.0)

    assert ui.current_actor is None
    assert ui.state == CombatUIState.WAITING_ATB


def test_select_next_auto_advance_ally_skips_remote_allies():
    ui = CombatUI.__new__(CombatUI)
    ui.local_player_id = "host"
    ui.session = None

    remote_actor = SimpleNamespace(player_id="remote")
    local_actor = SimpleNamespace(player_id="host")
    ui.combat_manager = SimpleNamespace(allies=[remote_actor, local_actor], enemies=[])

    selected = ui._select_next_auto_advance_ally(
        [remote_actor, local_actor],
        is_multiplayer=True
    )
    assert selected is local_actor

    selected_none = ui._select_next_auto_advance_ally([remote_actor], is_multiplayer=True)
    assert selected_none is None


def test_enemy_sync_can_skip_internal_interval_gate_when_already_gated():
    network_manager = MagicMock()
    network_manager.broadcast = AsyncMock()

    manager = EnemySyncManager(
        session=MagicMock(),
        network_manager=network_manager,
        is_host=True
    )
    enemy = SimpleNamespace(enemy_id="goblin", spawn_x=2, spawn_y=4, x=3, y=5)

    manager.last_move_time = 100.0
    current_time = 100.1  # 기본 interval(0.65)보다 짧음

    asyncio.run(manager.sync_enemy_positions([enemy], current_time=current_time))
    network_manager.broadcast.assert_not_called()

    asyncio.run(
        manager.sync_enemy_positions(
            [enemy],
            check_interval=False,
            current_time=current_time
        )
    )
    network_manager.broadcast.assert_awaited_once()


def test_enemy_sync_sync_fallback_broadcasts_without_server_loop():
    network_manager = MagicMock()
    network_manager.broadcast_sync = MagicMock()
    network_manager._server_event_loop = None

    manager = EnemySyncManager(
        session=MagicMock(),
        network_manager=network_manager,
        is_host=True
    )
    enemy = SimpleNamespace(enemy_id="goblin", spawn_x=3, spawn_y=5, x=7, y=9)

    manager.sync_enemy_positions_sync(
        [enemy],
        check_interval=False,
        current_time=123.0
    )

    network_manager.broadcast_sync.assert_called_once()
    sent_message = network_manager.broadcast_sync.call_args.args[0]
    assert sent_message.type == MessageType.ENEMY_MOVE
    assert sent_message.data["enemies"]["goblin_3_5"]["x"] == 7
    assert sent_message.data["enemies"]["goblin_3_5"]["y"] == 9


def test_update_enemy_movement_avoids_double_sync_call():
    exploration = MultiplayerExplorationSystem.__new__(MultiplayerExplorationSystem)
    exploration.is_multiplayer = True
    exploration.is_host = True
    exploration.enemy_sync = MagicMock()
    exploration._move_all_enemies = MagicMock()
    exploration.last_enemy_move = 0.0
    exploration.enemy_move_interval = 0.65

    asyncio.run(exploration.update_enemy_movement(10.0))

    exploration._move_all_enemies.assert_called_once()
    exploration.enemy_sync.sync_enemy_positions.assert_not_called()


def test_move_all_enemies_skips_double_timing_gate_for_sync_call():
    exploration = MultiplayerExplorationSystem.__new__(MultiplayerExplorationSystem)
    exploration.is_multiplayer = True
    exploration.is_host = True
    exploration.enemy_sync = MagicMock()
    exploration.enemy_sync.can_move_enemies.return_value = True
    exploration.enemies = []
    exploration.last_enemy_move = 0.0

    with patch("src.world.exploration.ExplorationSystem._move_all_enemies", return_value=None):
        exploration._move_all_enemies()

    exploration.enemy_sync.sync_enemy_positions_sync.assert_called_once()
    assert (
        exploration.enemy_sync.sync_enemy_positions_sync.call_args.kwargs["check_interval"]
        is False
    )
