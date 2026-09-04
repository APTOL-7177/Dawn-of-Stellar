from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.session import MultiplayerSession


def test_explicit_non_host_session_does_not_promote_first_local_player():
    session = MultiplayerSession(max_players=4, auto_assign_host=False)
    local_player = MultiplayerPlayer(
        player_id="client",
        player_name="Client",
        is_host=False,
    )

    assert session.add_player(local_player) is True
    assert session.host_id is None
    assert local_player.is_host is False
