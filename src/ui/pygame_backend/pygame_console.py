"""
PygameConsole - tcod.console.Console 호환 드롭인 대체

내부: numpy 구조체 배열 (ch: int32, fg: 3xu8, bg: 3xu8)
tcod.console.Console과 동일한 API로 기존 UI 코드 무변경 사용.
"""

import unicodedata
from typing import Optional, Tuple, Union

import numpy as np
import pygame

from src.core.logger import get_logger

logger = get_logger("pygame_console")


def _east_asian_width(ch: int) -> int:
    """문자의 셀 폭 반환

    BDF 폰트의 FONTBOUNDINGBOX가 모든 글리프(한글 포함)를 수용하므로
    기본적으로 1셀. 폰트 바운딩 박스보다 넓은 특수 문자만 2셀.
    """
    return 1


# tcod bg_blend 상수 호환
BKGND_SET = 1
BKGND_NONE = 0


class PygameConsole:
    """
    tcod.console.Console 호환 콘솔

    기존 tcod 코드에서 사용하는 다음 API를 미러링:
      .width, .height
      .clear(), .print(), .draw_rect(), .draw_frame(), .blit()
    """

    def __init__(self, width: int, height: int, order: str = "C") -> None:
        self.width: int = width
        self.height: int = height

        # 셀 데이터: ch(int32), fg(3xu8), bg(3xu8)
        # shape = (height, width)
        self.ch = np.full((height, width), ord(' '), dtype=np.int32)
        self.fg = np.full((height, width, 3), 255, dtype=np.uint8)
        self.bg = np.zeros((height, width, 3), dtype=np.uint8)

        # dirty tracking: 변경된 셀 추적
        self._dirty = np.ones((height, width), dtype=np.bool_)
        self._all_dirty = True

    # ------------------------------------------------------------------
    # tcod.console.Console 호환 API
    # ------------------------------------------------------------------

    def clear(
        self,
        ch: int = 0x20,
        fg: Tuple[int, int, int] = (255, 255, 255),
        bg: Tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """콘솔 전체 초기화"""
        self.ch[:] = ch
        self.fg[:] = fg
        self.bg[:] = bg
        self._dirty[:] = True
        self._all_dirty = True

    def print(
        self,
        x: int,
        y: int,
        string: str,
        fg: Optional[Tuple[int, int, int]] = None,
        bg: Optional[Tuple[int, int, int]] = None,
        alignment: int = 0,  # 0=LEFT, 1=RIGHT, 2=CENTER
        bg_blend: int = BKGND_SET,
    ) -> None:
        """문자열 출력 (tcod.console.Console.print 호환)

        Args:
            x, y: 셀 좌표
            string: 출력 문자열
            fg: 전경색 (None이면 유지)
            bg: 배경색 (None이면 유지)
            alignment: 0=LEFT, 1=RIGHT, 2=CENTER
            bg_blend: 배경 블렌드 모드 (1=SET, 0=NONE)
        """
        if y < 0 or y >= self.height:
            return

        # 문자열 렌더링 폭 계산 (정렬용)
        str_width = 0
        for c in string:
            str_width += _east_asian_width(ord(c))

        # 정렬 적용
        if alignment == 2:  # CENTER
            x = x - str_width // 2
        elif alignment == 1:  # RIGHT
            x = x - str_width

        # 셀 단위 쓰기
        cx = x
        for c in string:
            cp = ord(c)
            cw = _east_asian_width(cp)

            if cx >= self.width:
                break
            if cx < 0:
                cx += cw
                continue

            # 주 셀 쓰기
            self.ch[y, cx] = cp
            if fg is not None:
                self.fg[y, cx] = fg
            if bg is not None and bg_blend != BKGND_NONE:
                self.bg[y, cx] = bg
            self._dirty[y, cx] = True

            # CJK 2셀 문자: 다음 셀을 연속 마커로 표시
            if cw == 2 and cx + 1 < self.width:
                self.ch[y, cx + 1] = 0  # 연속 셀 (렌더링 건너뜀)
                if fg is not None:
                    self.fg[y, cx + 1] = fg
                if bg is not None and bg_blend != BKGND_NONE:
                    self.bg[y, cx + 1] = bg
                self._dirty[y, cx + 1] = True

            cx += cw

    def draw_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        ch: int = 0,
        fg: Optional[Tuple[int, int, int]] = None,
        bg: Optional[Tuple[int, int, int]] = None,
        bg_blend: int = BKGND_SET,
    ) -> None:
        """사각형 영역 채우기 (tcod.console.Console.draw_rect 호환)"""
        # 범위 클리핑
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + width)
        y1 = min(self.height, y + height)

        if x0 >= x1 or y0 >= y1:
            return

        if ch != 0:
            self.ch[y0:y1, x0:x1] = ch
        if fg is not None:
            self.fg[y0:y1, x0:x1] = fg
        if bg is not None and bg_blend != BKGND_NONE:
            self.bg[y0:y1, x0:x1] = bg
        self._dirty[y0:y1, x0:x1] = True

    def print_box(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        string: str,
        fg: Optional[Tuple[int, int, int]] = None,
        bg: Optional[Tuple[int, int, int]] = None,
        alignment: int = 0,
        bg_blend: int = BKGND_SET,
    ) -> int:
        """박스 영역 내 텍스트 출력 (자동 줄바꿈, tcod.console.Console.print_box 호환)

        Args:
            x, y: 셀 좌표 (좌상단)
            width, height: 박스 크기
            string: 출력 문자열
            fg: 전경색
            bg: 배경색
            alignment: 정렬 (0=LEFT, 1=RIGHT, 2=CENTER)
            bg_blend: 배경 블렌드 모드

        Returns:
            사용된 줄 수
        """
        if width <= 0 or height <= 0:
            return 0

        lines: list[str] = []
        for paragraph in string.split("\n"):
            if not paragraph:
                lines.append("")
                continue
            # 단어 단위 줄바꿈
            current_line = ""
            current_width = 0
            for ch in paragraph:
                cw = _east_asian_width(ord(ch))
                if current_width + cw > width:
                    lines.append(current_line)
                    current_line = ch
                    current_width = cw
                else:
                    current_line += ch
                    current_width += cw
            if current_line:
                lines.append(current_line)

        row = 0
        for line in lines:
            if row >= height:
                break
            self.print(x, y + row, line, fg=fg, bg=bg, alignment=alignment, bg_blend=bg_blend)
            row += 1

        return row

    def draw_frame(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str = "",
        clear: bool = True,
        fg: Optional[Tuple[int, int, int]] = None,
        bg: Optional[Tuple[int, int, int]] = None,
        bg_blend: int = BKGND_SET,
    ) -> None:
        """테두리가 있는 프레임 그리기 (tcod.console.Console.draw_frame 호환)

        유니코드 박스 드로잉 문자 사용:
        ┌─┐
        │ │
        └─┘
        """
        if width < 2 or height < 2:
            return

        # 내부 채우기
        if clear:
            self.draw_rect(x + 1, y + 1, width - 2, height - 2,
                           ch=ord(' '), fg=fg, bg=bg, bg_blend=bg_blend)

        # 테두리
        _fg = fg if fg is not None else (255, 255, 255)
        _bg = bg

        # 모서리
        self._set_cell(x, y, 0x250C, _fg, _bg, bg_blend)                # ┌
        self._set_cell(x + width - 1, y, 0x2510, _fg, _bg, bg_blend)    # ┐
        self._set_cell(x, y + height - 1, 0x2514, _fg, _bg, bg_blend)   # └
        self._set_cell(x + width - 1, y + height - 1, 0x2518, _fg, _bg, bg_blend)  # ┘

        # 수평선
        for cx in range(x + 1, x + width - 1):
            self._set_cell(cx, y, 0x2500, _fg, _bg, bg_blend)           # ─ (상단)
            self._set_cell(cx, y + height - 1, 0x2500, _fg, _bg, bg_blend)  # ─ (하단)

        # 수직선
        for cy in range(y + 1, y + height - 1):
            self._set_cell(x, cy, 0x2502, _fg, _bg, bg_blend)           # │ (좌)
            self._set_cell(x + width - 1, cy, 0x2502, _fg, _bg, bg_blend)  # │ (우)

        # 타이틀
        if title:
            # 타이틀을 프레임 상단 중앙에 표시
            title_x = x + (width - len(title)) // 2
            self.print(title_x, y, title, fg=_fg, bg=_bg, bg_blend=bg_blend)

    def blit(
        self,
        dest: "PygameConsole",
        dest_x: int = 0,
        dest_y: int = 0,
        src_x: int = 0,
        src_y: int = 0,
        width: int = 0,
        height: int = 0,
    ) -> None:
        """다른 콘솔에 복사 (tcod.console.Console.blit 호환)"""
        if width <= 0:
            width = self.width
        if height <= 0:
            height = self.height

        # 소스 범위 클리핑
        sw = min(width, self.width - src_x)
        sh = min(height, self.height - src_y)

        # 대상 범위 클리핑
        dw = min(sw, dest.width - dest_x)
        dh = min(sh, dest.height - dest_y)

        if dw <= 0 or dh <= 0:
            return

        # numpy 슬라이스 복사
        sy = slice(src_y, src_y + dh)
        sx = slice(src_x, src_x + dw)
        dy = slice(dest_y, dest_y + dh)
        dx = slice(dest_x, dest_x + dw)

        dest.ch[dy, dx] = self.ch[sy, sx]
        dest.fg[dy, dx] = self.fg[sy, sx]
        dest.bg[dy, dx] = self.bg[sy, sx]
        dest._dirty[dy, dx] = True

    # ------------------------------------------------------------------
    # tcod 호환 속성 (numpy 배열 직접 접근용)
    # ------------------------------------------------------------------

    @property
    def tiles_rgb(self):
        """tcod 호환: tiles_rgb 속성 (일부 코드에서 직접 접근)

        반환 형식은 tcod의 구조체 배열과 유사한 인터페이스 제공
        """
        return _TilesRGBView(self)

    @property
    def rgb(self):
        """tcod 호환: console.rgb 속성

        사용 패턴:
          console.rgb["bg"][y, x] = (r, g, b)
          console.rgb["ch"][:, :] = ord(' ')
          console.rgb[y, x] = (ch, fg, bg)
        """
        return _TilesRGBView(self)

    # ------------------------------------------------------------------
    # 내부 유틸리티
    # ------------------------------------------------------------------

    def _set_cell(
        self,
        x: int,
        y: int,
        ch: int,
        fg: Optional[Tuple[int, int, int]],
        bg: Optional[Tuple[int, int, int]],
        bg_blend: int = BKGND_SET,
    ) -> None:
        """단일 셀 설정 (범위 체크 포함)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.ch[y, x] = ch
            if fg is not None:
                self.fg[y, x] = fg
            if bg is not None and bg_blend != BKGND_NONE:
                self.bg[y, x] = bg
            self._dirty[y, x] = True

    def mark_all_dirty(self) -> None:
        """전체 dirty 설정 (리사이즈 등)"""
        self._dirty[:] = True
        self._all_dirty = True

    def reset_dirty(self) -> None:
        """dirty 플래그 초기화 (렌더링 후 호출)"""
        self._dirty[:] = False
        self._all_dirty = False


class _TilesRGBView:
    """tcod console.tiles_rgb / console.rgb 접근 패턴 호환 래퍼

    지원 패턴:
      view["ch"]           → console.ch (numpy 배열)
      view["bg"][y, x]     → console.bg[y, x]
      view["ch"][:, :]     → console.ch[:, :]
      view[y, x] = (ch, fg, bg)  → 셀 일괄 할당
    """

    def __init__(self, console: PygameConsole):
        self._console = console

    def __getitem__(self, key):
        # 패턴 1: view["ch"], view["fg"], view["bg"]
        if isinstance(key, str):
            if key == "ch":
                return self._console.ch
            elif key == "fg":
                return self._console.fg
            elif key == "bg":
                return self._console.bg
            raise KeyError(f"Unknown field: {key}")

        # 패턴 2: view[y, x] → (ch, fg, bg) 튜플
        if isinstance(key, tuple) and len(key) == 2:
            y, x = key
            return (
                int(self._console.ch[y, x]),
                tuple(self._console.fg[y, x]),
                tuple(self._console.bg[y, x]),
            )

        raise KeyError(f"Unsupported key: {key}")

    def __setitem__(self, key, value):
        # 패턴 1: view["ch"] = ..., view["fg"] = ..., view["bg"] = ...
        if isinstance(key, str):
            if key == "ch":
                self._console.ch[:] = value
                self._console._dirty[:] = True
                return
            elif key == "fg":
                self._console.fg[:] = value
                self._console._dirty[:] = True
                return
            elif key == "bg":
                self._console.bg[:] = value
                self._console._dirty[:] = True
                return
            raise KeyError(f"Unknown field: {key}")

        # 패턴 2: view[y, x] = (ch, fg, bg)
        if isinstance(key, tuple) and len(key) == 2:
            y, x = key
            if isinstance(value, tuple) and len(value) == 3:
                self._console.ch[y, x] = value[0]
                self._console.fg[y, x] = value[1]
                self._console.bg[y, x] = value[2]
                self._console._dirty[y, x] = True
                return

        raise KeyError(f"Unsupported key: {key}")
