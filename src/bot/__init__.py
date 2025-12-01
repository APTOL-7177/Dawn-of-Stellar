"""
봇 연동 모듈

게임 상태를 외부 봇 클라이언트와 공유하기 위한 모듈
- export_combat_state: 전투 상태 내보내기
- export_exploration_state: 탐험 상태 내보내기
- export_menu_state: 메뉴 상태 내보내기
"""
from .game_state_exporter import (
    enable_export,
    is_export_enabled,
    export_combat_state,
    export_exploration_state,
    export_menu_state,
    STATE_FILE,
    COMMAND_FILE
)
