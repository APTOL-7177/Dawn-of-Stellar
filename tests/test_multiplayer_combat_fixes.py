import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.combat.combat_manager import CombatState
from src.multiplayer.combat_sync import CombatSyncManager
from src.multiplayer.enemy_sync import EnemySyncManager
from src.ui.combat_ui import CombatUI


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
