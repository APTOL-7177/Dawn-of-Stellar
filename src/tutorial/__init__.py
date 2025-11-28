"""
튜토리얼 시스템 - Dawn of Stellar

v2: 실제 던전 플레이 + 봇 조언자 방식
15층까지 가이드 모드로 진행
"""

from src.tutorial.tutorial_manager import TutorialManager, get_tutorial_manager
from src.tutorial.tutorial_step import TutorialStep, TutorialMessage
from src.tutorial.tutorial_ui import TutorialUI
from src.tutorial.story_tutorial_manager import (
    StoryTutorialManager,
    get_story_tutorial_manager,
    unlock_job_from_tutorial,
    StoryChapter,
    NPCGuide,
    JobChoice
)
from src.tutorial.job_selection_ui import (
    JobSelectionUI,
    JobChoiceInfo,
    show_job_selection
)

# 새로운 튜토리얼 시스템 v2
from src.tutorial.story_runner import (
    run_story_tutorial,
    on_tutorial_complete,
    show_tutorial_intro,
    show_tutorial_complete,
    BotUIRenderer,
    Colors,
)

# 봇 조언자 시스템
from src.tutorial.tutorial_bot import (
    TutorialBot,
    get_tutorial_bot,
    reset_tutorial_bot,
    BotMessage,
    BotPersonality,
    SituationType,
)

# 튜토리얼 모드 설정
from src.tutorial.tutorial_mode import (
    TutorialModeConfig,
    TutorialProgress,
    get_tutorial_config,
    get_tutorial_progress,
    start_tutorial_mode,
    end_tutorial_mode,
    is_tutorial_mode,
    is_tutorial_already_completed,
    is_easy_mode,
    should_enable_bot,
    apply_tutorial_enemy_stats,
    apply_tutorial_player_stats,
    apply_tutorial_healing,
    should_auto_revive,
    get_revive_stats,
    check_tutorial_completion,
)

__all__ = [
    # 기본 튜토리얼
    "TutorialManager",
    "get_tutorial_manager",
    "TutorialStep",
    "TutorialMessage",
    "TutorialUI",
    # 스토리 튜토리얼 매니저
    "StoryTutorialManager",
    "get_story_tutorial_manager",
    "unlock_job_from_tutorial",
    "StoryChapter",
    "NPCGuide",
    "JobChoice",
    # 직업 선택 UI
    "JobSelectionUI",
    "JobChoiceInfo",
    "show_job_selection",
    # 튜토리얼 v2 - 메인 함수
    "run_story_tutorial",
    "on_tutorial_complete",
    "show_tutorial_intro",
    "show_tutorial_complete",
    "BotUIRenderer",
    # 봇 조언자
    "TutorialBot",
    "get_tutorial_bot",
    "reset_tutorial_bot",
    "BotMessage",
    "BotPersonality",
    "SituationType",
    # 튜토리얼 모드
    "TutorialModeConfig",
    "TutorialProgress",
    "get_tutorial_config",
    "get_tutorial_progress",
    "start_tutorial_mode",
    "end_tutorial_mode",
    "is_tutorial_mode",
    "is_tutorial_already_completed",
    "is_easy_mode",
    "should_enable_bot",
    "apply_tutorial_enemy_stats",
    "apply_tutorial_player_stats",
    "should_auto_revive",
    "check_tutorial_completion",
]
