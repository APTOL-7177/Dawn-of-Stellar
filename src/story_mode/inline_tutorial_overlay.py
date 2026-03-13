"""
인라인 튜토리얼 오버레이
Dawn of Stellar - 별빛의 여명

전투/탐험 중 화면 위에 표시되는 튜토리얼 힌트 시스템
기존 BotUIRenderer (src/tutorial/story_runner.py) 패턴을 확장
"""

import math
import time
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

import tcod.console

from src.ui.tcod_display import Colors


# NPC 색상
NPC_COLORS = {
    "selena": (0, 200, 255),
    "karnos": (255, 100, 100),
    "mira": (255, 200, 100),
    "tord": (100, 200, 100),
    "lina": (255, 150, 200),
}

NPC_NAMES = {
    "selena": "셀레나",
    "karnos": "카르노스",
    "mira": "미라",
    "tord": "토르드",
    "lina": "리나",
}


@dataclass
class TutorialHint:
    """튜토리얼 힌트"""
    text: str
    speaker: Optional[str] = None  # NPC ID
    position: str = "bottom"  # "bottom", "top", "center"
    color: Tuple[int, int, int] = (255, 255, 0)
    duration: float = 0.0  # 0이면 수동 해제
    created_at: float = field(default_factory=time.time)


@dataclass
class HighlightArea:
    """UI 강조 영역"""
    x: int
    y: int
    width: int
    height: int
    label: str = ""
    color: Tuple[int, int, int] = (255, 255, 0)
    pulse: bool = True


class InlineTutorialOverlay:
    """
    전투/탐험 중 인라인 튜토리얼 힌트

    기존 UI 위에 오버레이로 렌더링됩니다.
    """

    def __init__(self):
        self.active_hints: List[TutorialHint] = []
        self.highlight_areas: List[HighlightArea] = []
        self.animation_frame: int = 0

    def show_hint(
        self,
        text: str,
        speaker: Optional[str] = None,
        position: str = "bottom",
        color: Tuple[int, int, int] = (255, 255, 0),
        duration: float = 0.0,
    ):
        """힌트 표시"""
        self.active_hints.clear()  # 이전 힌트 제거
        self.active_hints.append(
            TutorialHint(
                text=text,
                speaker=speaker,
                position=position,
                color=color,
                duration=duration,
            )
        )

    def highlight_menu_item(self, x: int, y: int, width: int, label: str = ""):
        """메뉴 항목 강조"""
        self.highlight_areas.append(
            HighlightArea(x=x, y=y, width=width, height=1, label=label, pulse=True)
        )

    def highlight_gauge(self, x: int, y: int, width: int, label: str = ""):
        """게이지 영역 강조"""
        self.highlight_areas.append(
            HighlightArea(
                x=x, y=y, width=width, height=1,
                label=label, color=(0, 255, 255), pulse=True,
            )
        )

    def clear(self):
        """모든 힌트/강조 제거"""
        self.active_hints.clear()
        self.highlight_areas.clear()

    def clear_highlights(self):
        """강조만 제거"""
        self.highlight_areas.clear()

    def has_hints(self) -> bool:
        """활성 힌트 여부"""
        return len(self.active_hints) > 0

    def render(self, console: tcod.console.Console):
        """오버레이 렌더링 (기존 UI 위에)"""
        self.animation_frame += 1
        now = time.time()

        # 만료된 힌트 제거
        self.active_hints = [
            h for h in self.active_hints
            if h.duration <= 0 or (now - h.created_at) < h.duration
        ]

        # 강조 영역 렌더링
        for area in self.highlight_areas:
            self._render_highlight(console, area)

        # 힌트 박스 렌더링
        for hint in self.active_hints:
            self._render_hint_box(console, hint)

    def _render_highlight(self, console: tcod.console.Console, area: HighlightArea):
        """강조 영역 렌더링 (노란 테두리 펄스)"""
        if area.pulse:
            pulse = abs(math.sin(self.animation_frame / 8.0))
            brightness = int(150 + 105 * pulse)
        else:
            brightness = 255

        color = (
            min(255, int(area.color[0] * brightness / 255)),
            min(255, int(area.color[1] * brightness / 255)),
            min(255, int(area.color[2] * brightness / 255)),
        )

        # 상단 테두리
        if area.y > 0:
            for x in range(area.x, min(area.x + area.width, console.width)):
                if 0 <= x < console.width and 0 <= area.y - 1 < console.height:
                    console.print(x, area.y - 1, "─", fg=color)

        # 하단 테두리
        by = area.y + area.height
        if by < console.height:
            for x in range(area.x, min(area.x + area.width, console.width)):
                if 0 <= x < console.width:
                    console.print(x, by, "─", fg=color)

        # 라벨
        if area.label:
            lx = area.x + area.width + 1
            if lx + len(area.label) < console.width:
                console.print(lx, area.y, f"← {area.label}", fg=color)

    def _render_hint_box(self, console: tcod.console.Console, hint: TutorialHint):
        """힌트 박스 렌더링"""
        w = console.width
        h = console.height

        # 텍스트 줄바꿈
        max_text_width = w - 8
        lines = []
        for raw_line in hint.text.split("\n"):
            while len(raw_line) > max_text_width:
                lines.append(raw_line[:max_text_width])
                raw_line = raw_line[max_text_width:]
            lines.append(raw_line)

        # 화자 헤더
        header = ""
        header_color = hint.color
        if hint.speaker:
            header = NPC_NAMES.get(hint.speaker, hint.speaker)
            header_color = NPC_COLORS.get(hint.speaker, hint.color)

        box_height = len(lines) + 3 + (1 if header else 0)
        box_width = min(max(max(len(l) for l in lines) + 6, 30), w - 4)

        # 위치 결정
        box_x = (w - box_width) // 2
        if hint.position == "bottom":
            box_y = h - box_height - 2
        elif hint.position == "top":
            box_y = 2
        else:  # center
            box_y = (h - box_height) // 2

        # 배경
        for dy in range(box_height):
            for dx in range(box_width):
                bx, by = box_x + dx, box_y + dy
                if 0 <= bx < w and 0 <= by < h:
                    console.print(bx, by, " ", bg=(15, 15, 30))

        # 테두리
        border_color = header_color
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            header if header else "",
            fg=border_color,
            bg=(15, 15, 30),
        )

        # 텍스트
        text_y = box_y + 1 + (1 if header and not header else 0)
        for i, line in enumerate(lines):
            console.print(box_x + 2, text_y + i, line, fg=hint.color)

        # 진행 안내
        help_text = "Space: 계속"
        console.print(
            box_x + box_width - len(help_text) - 2,
            box_y + box_height - 2,
            help_text,
            fg=Colors.GRAY,
        )
