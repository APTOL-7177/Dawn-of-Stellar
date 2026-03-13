"""
Pygame-CE 기반 렌더링 백엔드

tcod.console.Console / tcod.context.Context 호환 API를 제공하여
기존 84개 UI 파일을 변경 없이 pygame 렌더러로 전환.
"""

from src.ui.pygame_backend.pygame_console import PygameConsole
from src.ui.pygame_backend.font_atlas import FontAtlas
from src.ui.pygame_backend.pygame_context import PygameContext
from src.ui.pygame_backend.event_adapter import EventAdapter
from src.ui.pygame_backend.pygame_display import PygameDisplay

__all__ = [
    "PygameConsole",
    "FontAtlas",
    "PygameContext",
    "EventAdapter",
    "PygameDisplay",
]
