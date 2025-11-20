"""
멀티플레이 시스템

P2P 멀티플레이 모드를 지원합니다.
"""

from src.multiplayer.session import MultiplayerSession
from src.multiplayer.config import MultiplayerConfig
from src.multiplayer.party_setup import MultiplayerPartySetup, MultiplayerPartyValidator
from src.multiplayer.player_state import PlayerStateManager
from src.multiplayer.revival_system import RevivalSystem
from src.multiplayer.skill_revival_handler import SkillRevivalHandler
from src.multiplayer.game_mode import GameMode, MultiplayerMode, GameModeManager, get_game_mode_manager
from src.multiplayer.test_helper import MultiplayerTestHelper, LocalMultiplayerTest, create_test_session
from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.enemy_sync import EnemySyncManager
from src.multiplayer.atb_multiplayer import MultiplayerATBSystem
from src.multiplayer.validation import (
    validate_player_id, validate_player_name, validate_position,
    validate_session_id, validate_max_players, sanitize_player_name
)

# 네트워크 모듈은 lazy import (websockets 패키지 필요)
try:
    from src.multiplayer.network import NetworkManager, HostNetworkManager, ClientNetworkManager
    __all__ = [
        "MultiplayerSession",
        "MultiplayerConfig",
        "MultiplayerPartySetup",
        "MultiplayerPartyValidator",
        "PlayerStateManager",
        "RevivalSystem",
        "SkillRevivalHandler",
        "GameMode",
        "MultiplayerMode",
        "GameModeManager",
        "get_game_mode_manager",
        "MultiplayerTestHelper",
        "LocalMultiplayerTest",
        "create_test_session",
        "MovementSyncManager",
        "EnemySyncManager",
        "MultiplayerATBSystem",
        "CombatJoinHandler",
        "CombatSyncManager",
        "validate_player_id",
        "validate_player_name",
        "validate_position",
        "validate_session_id",
        "validate_max_players",
        "sanitize_player_name",
        "NetworkManager",
        "HostNetworkManager",
        "ClientNetworkManager",
    ]
except ImportError:
    __all__ = [
        "MultiplayerSession",
        "MultiplayerConfig",
        "MultiplayerPartySetup",
        "MultiplayerPartyValidator",
        "PlayerStateManager",
        "RevivalSystem",
    ]

