"""
스토리 튜토리얼 플레이 모드
Dawn of Stellar - 시공의 여명

스토리와 함께 게임 시스템을 배우는 인터랙티브 튜토리얼

NOTE: 실제 구현은 story_runner.py에 있습니다.
      이 파일은 하위 호환성을 위해 유지됩니다.
"""

import tcod
import tcod.console
import tcod.event
from typing import Dict, Any

# 새로운 스토리 러너 시스템에서 임포트
from src.tutorial.story_runner import (
    StoryTutorialRunner,
    run_story_tutorial,
    get_story_runner,
    initialize_story_runner,
    DialogueRunner,
    MessageRenderer,
    TutorialCombatRunner,
    TutorialState,
    TutorialProgress,
    Colors,
    NPC_COLORS,
    NPC_NAMES,
)

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


# 하위 호환성을 위한 별칭
StoryTutorialPlayer = StoryTutorialRunner


__all__ = [
    "StoryTutorialRunner",
    "StoryTutorialPlayer",
    "run_story_tutorial",
    "get_story_runner",
    "initialize_story_runner",
    "DialogueRunner",
    "MessageRenderer",
    "TutorialCombatRunner",
    "TutorialState",
    "TutorialProgress",
    "Colors",
    "NPC_COLORS",
    "NPC_NAMES",
]
