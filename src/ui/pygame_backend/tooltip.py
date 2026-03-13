"""
마우스 호버 툴팁 시스템

셀 좌표 기반 툴팁 표시. PygameConsole 위에 오버레이로 렌더링.
"""

import time
from typing import Callable, Dict, List, Optional, Tuple

import pygame

from src.core.logger import get_logger

logger = get_logger("tooltip")


class Tooltip:
    """단일 툴팁 데이터"""

    def __init__(
        self,
        text: str,
        x: int,
        y: int,
        fg: Tuple[int, int, int] = (220, 220, 220),
        bg: Tuple[int, int, int] = (20, 20, 40),
        border: Tuple[int, int, int] = (100, 100, 150),
    ) -> None:
        self.text = text
        self.lines = text.split('\n')
        self.x = x
        self.y = y
        self.fg = fg
        self.bg = bg
        self.border = border
        # 크기 (셀 단위)
        self.width = max(len(line) for line in self.lines) + 2  # 패딩
        self.height = len(self.lines) + 2


class TooltipManager:
    """
    마우스 호버 툴팁 관리자

    사용법:
        1. register_zone(x, y, w, h, text) 로 호버 영역 등록
        2. on_mouse_move(cell_x, cell_y) 로 마우스 위치 업데이트
        3. render(console) 로 활성 툴팁 렌더링
    """

    def __init__(self, hover_delay: float = 0.3) -> None:
        self.hover_delay = hover_delay  # 툴팁 표시까지 대기 시간
        self._zones: List[Dict] = []
        self._active_tooltip: Optional[Tooltip] = None
        self._hover_start: float = 0.0
        self._hover_cell: Tuple[int, int] = (-1, -1)
        self._visible: bool = False

        # 동적 콜백 (zone 외 실시간 조회)
        self._dynamic_provider: Optional[Callable] = None

    def register_zone(
        self,
        x: int, y: int, width: int, height: int,
        text: str,
        fg: Tuple[int, int, int] = (220, 220, 220),
        bg: Tuple[int, int, int] = (20, 20, 40),
    ) -> None:
        """호버 영역 등록"""
        self._zones.append({
            'x': x, 'y': y, 'w': width, 'h': height,
            'text': text, 'fg': fg, 'bg': bg,
        })

    def set_dynamic_provider(self, provider: Optional[Callable]) -> None:
        """동적 툴팁 제공자 설정

        provider(cell_x, cell_y) -> Optional[str] 형태의 콜백.
        zone에 해당하지 않을 때 호출됩니다.
        """
        self._dynamic_provider = provider

    def clear_zones(self) -> None:
        """모든 호버 영역 제거"""
        self._zones.clear()

    def on_mouse_move(self, cell_x: int, cell_y: int) -> None:
        """마우스 이동 시 호출"""
        if (cell_x, cell_y) == self._hover_cell:
            # 같은 셀 위: 딜레이 체크
            if not self._visible and time.time() - self._hover_start >= self.hover_delay:
                self._show_tooltip(cell_x, cell_y)
            return

        # 새로운 셀: 리셋
        self._hover_cell = (cell_x, cell_y)
        self._hover_start = time.time()
        self._visible = False
        self._active_tooltip = None

    def _show_tooltip(self, cell_x: int, cell_y: int) -> None:
        """툴팁 표시"""
        # zone 검색
        for zone in self._zones:
            if (zone['x'] <= cell_x < zone['x'] + zone['w'] and
                    zone['y'] <= cell_y < zone['y'] + zone['h']):
                self._active_tooltip = Tooltip(
                    text=zone['text'],
                    x=cell_x + 1,
                    y=cell_y + 1,
                    fg=zone['fg'],
                    bg=zone['bg'],
                )
                self._visible = True
                return

        # 동적 제공자
        if self._dynamic_provider:
            text = self._dynamic_provider(cell_x, cell_y)
            if text:
                self._active_tooltip = Tooltip(
                    text=text,
                    x=cell_x + 1,
                    y=cell_y + 1,
                )
                self._visible = True
                return

        self._visible = False
        self._active_tooltip = None

    def render(self, console) -> None:
        """활성 툴팁을 콘솔에 렌더링

        Args:
            console: PygameConsole 인스턴스
        """
        if not self._visible or self._active_tooltip is None:
            return

        tip = self._active_tooltip

        # 화면 밖으로 나가지 않도록 위치 조정
        tx = min(tip.x, console.width - tip.width)
        ty = min(tip.y, console.height - tip.height)
        tx = max(0, tx)
        ty = max(0, ty)

        # 프레임 그리기
        console.draw_frame(
            tx, ty, tip.width, tip.height,
            fg=tip.border, bg=tip.bg,
        )

        # 텍스트
        for i, line in enumerate(tip.lines):
            console.print(tx + 1, ty + 1 + i, line, fg=tip.fg, bg=tip.bg)

    @property
    def is_visible(self) -> bool:
        return self._visible
