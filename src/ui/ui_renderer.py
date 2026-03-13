"""
ui_renderer.py - Cogmind 스타일 UI 렌더링 유틸리티

더블라인 박스, 선택 항목 펄스 하이라이트, 메뉴 스크램블 효과 등
기존 draw_frame 대비 향상된 시각적 UI를 제공하는 독립 유틸리티.

주요 클래스/함수:
    draw_styled_box     - 더블라인 문자 박스 + 타이틀 장식 + 구분선
    SelectionHighlight  - math.sin 기반 배경색 펄스 (선택 항목 글로우)
    MenuScrambleEffect  - 메뉴 진입 시 텍스트 순차 디코딩 효과
    DynamicSeparator    - 구분선 색상 미세 펄스
    PanelTransition     - 패널 열기/닫기 스케일+페이드
"""

import math
import random
import time
from typing import Tuple, List, Optional

import tcod.console

# ── 더블라인 박스 문자 ─────────────────────────────────────────────────────
# ╔═╗
# ║ ║
# ╠═╣  (구분선)
# ║ ║
# ╚═╝
_BOX_TL = "╔"
_BOX_TR = "╗"
_BOX_BL = "╚"
_BOX_BR = "╝"
_BOX_H = "═"
_BOX_V = "║"
_BOX_SL = "╠"  # separator left
_BOX_SR = "╣"  # separator right
_BOX_TITLE_L = "╡"
_BOX_TITLE_R = "╞"

# 스크램블 문자 세트
_SCRAMBLE_CHARS = "░▒▓█▀▄▌▐│─┌┐└┘├┤┬┴┼╔╗╚╝═║@#$%&*<>{}[]01"

Color = Tuple[int, int, int]


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    """두 색상 사이를 선형 보간"""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


# ── draw_styled_box ────────────────────────────────────────────────────────

def draw_styled_box(
    console: tcod.console.Console,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str = "",
    fg: Color = (200, 200, 200),
    bg: Color = (20, 20, 40),
    title_fg: Optional[Color] = None,
    separator_y: Optional[int] = None,
    clear: bool = True,
) -> None:
    """
    더블라인 문자 박스를 그린다. draw_frame()의 드롭인 교체용.

    Args:
        console: tcod 콘솔
        x, y: 좌상단 좌표
        w, h: 너비, 높이
        title: 상단 타이틀 (╡ 제목 ╞ 장식)
        fg: 테두리 색상
        bg: 배경 색상
        title_fg: 타이틀 색상 (None이면 fg 사용)
        separator_y: 구분선 y 좌표 (절대값). None이면 구분선 없음.
        clear: True면 내부 배경 채우기
    """
    # 방어: title이 None으로 전달되는 경우 대비
    if title is None:
        title = ""
    if title_fg is None:
        title_fg = fg

    # 내부 채우기
    if clear:
        for dy in range(1, h - 1):
            for dx in range(1, w - 1):
                console.print(x + dx, y + dy, " ", bg=bg)

    # 모서리
    console.print(x, y, _BOX_TL, fg=fg, bg=bg)
    console.print(x + w - 1, y, _BOX_TR, fg=fg, bg=bg)
    console.print(x, y + h - 1, _BOX_BL, fg=fg, bg=bg)
    console.print(x + w - 1, y + h - 1, _BOX_BR, fg=fg, bg=bg)

    # 가로선 (상단/하단)
    for dx in range(1, w - 1):
        console.print(x + dx, y, _BOX_H, fg=fg, bg=bg)
        console.print(x + dx, y + h - 1, _BOX_H, fg=fg, bg=bg)

    # 세로선 (좌/우)
    for dy in range(1, h - 1):
        console.print(x, y + dy, _BOX_V, fg=fg, bg=bg)
        console.print(x + w - 1, y + dy, _BOX_V, fg=fg, bg=bg)

    # 구분선
    if separator_y is not None and y < separator_y < y + h - 1:
        console.print(x, separator_y, _BOX_SL, fg=fg, bg=bg)
        console.print(x + w - 1, separator_y, _BOX_SR, fg=fg, bg=bg)
        for dx in range(1, w - 1):
            console.print(x + dx, separator_y, _BOX_H, fg=fg, bg=bg)

    # 타이틀
    if title:
        # 타이틀이 박스 너비를 초과하지 않도록 자르기
        max_title_len = w - 6  # ╡ + 공백 + 제목 + 공백 + ╞ + 여유
        display_title = title[:max_title_len] if len(title) > max_title_len else title
        title_x = x + (w - len(display_title) - 4) // 2
        console.print(title_x, y, _BOX_TITLE_L, fg=fg, bg=bg)
        console.print(title_x + 1, y, f" {display_title} ", fg=title_fg, bg=bg)
        console.print(title_x + len(display_title) + 3, y, _BOX_TITLE_R, fg=fg, bg=bg)


# ── SelectionHighlight ─────────────────────────────────────────────────────

class SelectionHighlight:
    """
    선택 항목 배경색 펄스 (글로우 효과).

    math.sin() 기반으로 base_bg ↔ pulse_bg 사이를 부드럽게 순환.

    사용 예시::

        highlight = SelectionHighlight()
        # 게임 루프:
        highlight.update(dt)
        bg = highlight.get_bg_color()
        console.draw_rect(x, y, w, 1, ord(" "), bg=bg)
    """

    def __init__(
        self,
        base_bg: Color = (40, 40, 60),
        pulse_bg: Color = (60, 60, 100),
        speed: float = 3.0,
    ) -> None:
        self.base_bg = base_bg
        self.pulse_bg = pulse_bg
        self.speed = speed
        self._elapsed: float = 0.0

    def update(self, dt: float) -> None:
        """시간 갱신"""
        self._elapsed += dt

    def get_bg_color(self) -> Color:
        """현재 배경색 반환"""
        # sin 함수로 0~1 사이 펄스 값 생성
        t = (math.sin(self._elapsed * self.speed) + 1.0) * 0.5
        return _lerp_color(self.base_bg, self.pulse_bg, t)


# ── MenuScrambleEffect ─────────────────────────────────────────────────────

class MenuScrambleEffect:
    """
    메뉴 진입 시 텍스트 순차 디코딩 효과.

    TextScrambler 패턴을 기반으로 여러 메뉴 항목에 stagger(지연) 적용.

    사용 예시::

        effect = MenuScrambleEffect(["파티 상태", "인벤토리", "설정"])
        # 게임 루프:
        effect.update(dt)
        texts = effect.get_display_texts()
    """

    def __init__(
        self,
        items: List[str],
        duration: float = 0.4,
        stagger: float = 0.06,
    ) -> None:
        """
        Args:
            items: 메뉴 항목 텍스트 리스트
            duration: 각 항목 디코딩 소요 시간 (초)
            stagger: 항목 간 시작 지연 (초)
        """
        self.items = items
        self.duration = max(duration, 0.01)
        self.stagger = stagger
        self._elapsed: float = 0.0

        # 각 항목별 스크램블 버퍼
        self._scramble_bufs: List[List[str]] = []
        for text in items:
            buf = [
                random.choice(_SCRAMBLE_CHARS) if ch != " " else " "
                for ch in text
            ]
            self._scramble_bufs.append(buf)

    def update(self, dt: float) -> None:
        """시간 갱신"""
        self._elapsed += dt

    @property
    def is_complete(self) -> bool:
        """모든 항목 디코딩 완료 여부"""
        if not self.items:
            return True
        last_start = (len(self.items) - 1) * self.stagger
        return self._elapsed >= last_start + self.duration

    def get_display_texts(self) -> List[str]:
        """현재 표시할 텍스트 리스트 반환"""
        result = []
        for i, text in enumerate(self.items):
            item_start = i * self.stagger
            item_elapsed = self._elapsed - item_start

            if item_elapsed <= 0:
                # 아직 시작 안 됨 - 전부 스크램블
                result.append("".join(self._scramble_bufs[i]))
            elif item_elapsed >= self.duration:
                # 디코딩 완료
                result.append(text)
            else:
                # 디코딩 진행 중
                progress = item_elapsed / self.duration
                chars = []
                for j, ch in enumerate(text):
                    # 왼쪽에서 오른쪽으로 순차 해독
                    resolve_at = j / max(len(text), 1)
                    if progress >= resolve_at:
                        chars.append(ch)
                    else:
                        # 스크램블 문자 순환
                        self._scramble_bufs[i][j] = random.choice(_SCRAMBLE_CHARS) if ch != " " else " "
                        chars.append(self._scramble_bufs[i][j])
                result.append("".join(chars))

        return result


# ── DynamicSeparator ───────────────────────────────────────────────────────

class DynamicSeparator:
    """
    구분선 색상 미세 펄스.

    사용 예시::

        sep = DynamicSeparator(width=30)
        sep.update(dt)
        sep.render(console, x, y)
    """

    def __init__(
        self,
        width: int,
        fg: Color = (100, 100, 150),
        pulse_fg: Color = (140, 140, 200),
        speed: float = 2.0,
    ) -> None:
        self.width = width
        self.fg = fg
        self.pulse_fg = pulse_fg
        self.speed = speed
        self._elapsed: float = 0.0

    def update(self, dt: float) -> None:
        """시간 갱신"""
        self._elapsed += dt

    def get_fg_color(self) -> Color:
        """현재 구분선 색상"""
        t = (math.sin(self._elapsed * self.speed) + 1.0) * 0.5
        return _lerp_color(self.fg, self.pulse_fg, t)

    def render(self, console: tcod.console.Console, x: int, y: int, bg: Optional[Color] = None) -> None:
        """구분선 렌더링"""
        color = self.get_fg_color()
        for dx in range(self.width):
            if bg:
                console.print(x + dx, y, "─", fg=color, bg=bg)
            else:
                console.print(x + dx, y, "─", fg=color)


# ── PanelTransition ────────────────────────────────────────────────────────

class PanelTransition:
    """
    패널 열기/닫기 트랜지션 (스케일 + 페이드).

    패널이 중앙에서 확장되는 효과를 시뮬레이션.

    사용 예시::

        transition = PanelTransition(duration=0.2)
        transition.start_open()
        # 게임 루프:
        transition.update(dt)
        if transition.is_visible:
            # 패널 실제 크기 계산
            scale = transition.get_scale()
    """

    def __init__(self, duration: float = 0.2) -> None:
        self.duration = max(duration, 0.01)
        self._elapsed: float = 0.0
        self._opening: bool = True
        self._active: bool = False

    def start_open(self) -> None:
        """열기 트랜지션 시작"""
        self._elapsed = 0.0
        self._opening = True
        self._active = True

    def start_close(self) -> None:
        """닫기 트랜지션 시작"""
        self._elapsed = 0.0
        self._opening = False
        self._active = True

    def update(self, dt: float) -> None:
        """시간 갱신"""
        if self._active:
            self._elapsed += dt
            if self._elapsed >= self.duration:
                self._elapsed = self.duration
                self._active = False

    @property
    def is_visible(self) -> bool:
        """패널이 보여야 하는지"""
        if self._opening:
            return True
        return self._active  # 닫히는 중이면 아직 보임

    @property
    def is_complete(self) -> bool:
        """트랜지션 완료 여부"""
        return not self._active

    def get_scale(self) -> float:
        """현재 스케일 (0.0 ~ 1.0)"""
        progress = min(self._elapsed / self.duration, 1.0)
        if self._opening:
            # ease-out: 빠르게 나타나고 끝에서 감속
            return 1.0 - (1.0 - progress) ** 2
        else:
            # ease-in: 처음 느리다가 빠르게 사라짐
            return 1.0 - progress ** 2

    def get_alpha(self) -> float:
        """현재 알파 (0.0 ~ 1.0) - 배경 밝기 조절용"""
        return self.get_scale()
