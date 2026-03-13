"""
PygameContext - tcod.context.Context 호환 드롭인 대체

pygame 윈도우 관리 및 콘솔 → 화면 렌더링.
present() 메서드로 PygameConsole의 셀 그리드를 화면에 표시.
"""

import platform
import time
from typing import Optional, Tuple

import pygame

from src.core.logger import get_logger
from src.ui.pygame_backend.font_atlas import FontAtlas
from src.ui.pygame_backend.pygame_console import PygameConsole
from src.ui.pygame_backend.gauge_tiles import is_gauge_tile, get_gauge_tile_manager
from src.ui.pygame_backend.effects import EffectManager

logger = get_logger("pygame_context")


class PygameContext:
    """
    tcod.context.Context 호환 pygame 윈도우 컨텍스트

    pygame 윈도우를 생성/관리하고 PygameConsole을
    실제 화면에 렌더링합니다.
    """

    def __init__(
        self,
        columns: int,
        rows: int,
        font_atlas: FontAtlas,
        title: str = "Dawn of Stellar",
        pixel_width: int = 0,
        pixel_height: int = 0,
        vsync: bool = True,
        borderless: bool = False,
        borderless_fullscreen: bool = False,
        keep_aspect: bool = True,
    ) -> None:
        self.columns = columns
        self.rows = rows
        self.font_atlas = font_atlas
        self.title = title
        self.keep_aspect = keep_aspect

        # 타일 크기 (폰트 네이티브)
        self.tile_width = font_atlas.tile_width
        self.tile_height = font_atlas.tile_height

        # 렌더링 타일 크기 = 폰트 네이티브 크기 (글리프 잘림 방지)
        # 화면 비율은 present()의 스케일링이 처리
        self._render_tw = self.tile_width
        self._render_th = self.tile_height

        # 콘솔 픽셀 크기 (네이티브)
        self._console_pixel_w = columns * self._render_tw
        self._console_pixel_h = rows * self._render_th

        # 창 크기 결정
        if pixel_width > 0 and pixel_height > 0:
            self._window_w = pixel_width
            self._window_h = pixel_height
        else:
            self._window_w = self._console_pixel_w
            self._window_h = self._console_pixel_h

        # pygame 디스플레이 초기화
        if not pygame.display.get_init():
            pygame.display.init()

        # 창 플래그
        flags = pygame.RESIZABLE | pygame.SCALED
        if borderless_fullscreen:
            flags |= pygame.NOFRAME
        elif borderless:
            flags |= pygame.NOFRAME

        # vsync 설정
        self._vsync = vsync

        # 메인 윈도우 생성
        try:
            self.screen = pygame.display.set_mode(
                (self._window_w, self._window_h),
                flags,
                vsync=1 if vsync else 0,
            )
        except pygame.error:
            # vsync 실패 시 재시도
            self.screen = pygame.display.set_mode(
                (self._window_w, self._window_h),
                flags,
            )

        pygame.display.set_caption(title)
        
        try:
            icon = pygame.image.load("assets/logo.png")
            pygame.display.set_icon(icon)
        except Exception as e:
            logger.warning(f"로고 아이콘 로드 실패: {e}")

        # 콘솔 렌더링용 오프스크린 서피스
        self._console_surface = pygame.Surface(
            (self._console_pixel_w, self._console_pixel_h)
        )

        # 종횡비 유지 관련
        self._aspect_ratio = self._console_pixel_w / max(1, self._console_pixel_h)

        # 이펙트 매니저
        self.effect_manager = EffectManager()
        self._last_frame_time = time.time()

        # borderless fullscreen이면 창 크기를 화면 해상도에 맞춤
        if borderless_fullscreen:
            self._apply_borderless_fullscreen()

        logger.info(
            f"PygameContext 생성: {columns}x{rows} 콘솔, "
            f"{self._window_w}x{self._window_h} 창, "
            f"타일: {self.tile_width}x{self.tile_height}"
        )

    def _apply_borderless_fullscreen(self) -> None:
        """테두리 없는 전체 창 모드 적용"""
        try:
            info = pygame.display.Info()
            self._window_w = info.current_w
            self._window_h = info.current_h
            self.screen = pygame.display.set_mode(
                (self._window_w, self._window_h),
                pygame.NOFRAME | pygame.FULLSCREEN,
            )
            logger.info(f"Borderless fullscreen: {self._window_w}x{self._window_h}")
        except Exception as e:
            logger.warning(f"Borderless fullscreen 실패: {e}")

    # ------------------------------------------------------------------
    # tcod.context.Context 호환 API
    # ------------------------------------------------------------------

    def present(
        self,
        console: PygameConsole,
        keep_aspect: Optional[bool] = None,
        integer_scaling: bool = False,
    ) -> None:
        """콘솔을 화면에 렌더링 (tcod.context.present 호환)

        Args:
            console: 렌더링할 PygameConsole
            keep_aspect: 종횡비 유지 여부 (None이면 기본값 사용)
            integer_scaling: 정수 배율 사용 여부
        """
        if keep_aspect is None:
            keep_aspect = self.keep_aspect

        # 프레임 dt 계산 (전환 효과 등에서 첫 프레임 dt 폭주 방지)
        now = time.time()
        dt = now - self._last_frame_time
        self._last_frame_time = now
        # dt 클램핑: 최대 50ms (20fps 이하 상황이거나 루프 간 갭)
        dt = min(dt, 0.05)

        # 콘솔 → 오프스크린 서피스 렌더링
        self._render_console(console)

        # 이펙트 파이프라인: 글로우 → 파티클 → 라이팅 (콘솔 해상도)
        self.effect_manager.update(dt)
        self.effect_manager.apply(self._console_surface)

        # 화면에 스케일링하여 출력
        screen_w, screen_h = self.screen.get_size()

        if keep_aspect:
            dest_rect = self._fit_rect(
                self._console_pixel_w, self._console_pixel_h,
                screen_w, screen_h,
                integer_scaling,
            )
            self.screen.fill((0, 0, 0))
            scaled = pygame.transform.scale(
                self._console_surface,
                (dest_rect[2], dest_rect[3]),
            )
            # 이펙트 파이프라인 후반: 셰이크 → 플래시 → CRT (스크린 해상도)
            self.effect_manager.apply_post(self.screen, scaled, dest_rect)
        else:
            scaled = pygame.transform.scale(
                self._console_surface,
                (screen_w, screen_h),
            )
            self.effect_manager.apply_post(
                self.screen, scaled, (0, 0, screen_w, screen_h)
            )

        # 마우스 좌표 변환용 dest_rect 저장
        self._last_dest_rect = dest_rect if keep_aspect else (0, 0, screen_w, screen_h)

        pygame.display.flip()

    def pixel_to_cell(self, px: int, py: int) -> Tuple[int, int]:
        """윈도우 픽셀 좌표를 콘솔 셀 좌표로 변환

        Args:
            px: 윈도우 X 픽셀
            py: 윈도우 Y 픽셀

        Returns:
            (cell_x, cell_y) 콘솔 셀 좌표
        """
        dr = getattr(self, '_last_dest_rect', None)
        if dr is None:
            # 폴백: 단순 나눗셈
            tw = self._render_tw or 10
            th = self._render_th or 13
            return (px // tw, py // th)

        dx, dy, dw, dh = dr
        # 윈도우 좌표 → 콘솔 픽셀 좌표
        if dw <= 0 or dh <= 0:
            return (0, 0)
        console_px = (px - dx) * self._console_pixel_w / dw
        console_py = (py - dy) * self._console_pixel_h / dh
        # 콘솔 픽셀 → 셀 좌표
        tw = self._render_tw or 10
        th = self._render_th or 13
        cell_x = int(console_px / tw)
        cell_y = int(console_py / th)
        return (cell_x, cell_y)

    def cell_to_console_pixel(self, cell_x: int, cell_y: int) -> Tuple[int, int]:
        """셀 좌표를 콘솔 해상도 픽셀로 변환 (파티클 이펙트용)"""
        tw = self._render_tw or 10
        th = self._render_th or 13
        return (cell_x * tw + tw // 2, cell_y * th + th // 2)

    def _render_console(self, console: PygameConsole) -> None:
        """PygameConsole의 셀 데이터를 _console_surface에 렌더링

        16:9 보정된 _render_tw/_render_th를 사용하여 타일 배치.
        폰트 네이티브 크기와 다르면 글리프를 스케일링.
        """
        fa = self.font_atlas
        rtw = self._render_tw   # 렌더링 타일 폭 (16:9 보정)
        rth = self._render_th   # 렌더링 타일 높이
        ntw = fa.tile_width     # 네이티브 폰트 타일 폭
        nth = fa.tile_height    # 네이티브 폰트 타일 높이
        surf = self._console_surface
        gauge_mgr = get_gauge_tile_manager()
        gauge_mgr.set_tile_size(rtw, rth)

        def _render_cell(cx, cy, ch, fg, bg):
            px = cx * rtw
            py = cy * rth

            if is_gauge_tile(ch):
                gauge_mgr.render_gauge_cell(surf, px, py, ch, fg, bg)
                return

            # 네이티브 크기로 직접 렌더링 (스케일/오프셋 불필요)
            fa.render_cell(surf, px, py, ch, fg, bg)

        if console._all_dirty:
            for cy in range(console.height):
                for cx in range(console.width):
                    ch = int(console.ch[cy, cx])
                    if ch == 0:
                        # CJK 연속 셀: 건너뜀 (앞 셀의 wide 렌더링이 이미 처리)
                        continue
                    fg_arr = console.fg[cy, cx]
                    bg_arr = console.bg[cy, cx]
                    fg = (int(fg_arr[0]), int(fg_arr[1]), int(fg_arr[2]))
                    bg = (int(bg_arr[0]), int(bg_arr[1]), int(bg_arr[2]))
                    _render_cell(cx, cy, ch, fg, bg)
        else:
            dirty_ys, dirty_xs = console._dirty.nonzero()
            for i in range(len(dirty_ys)):
                cy = int(dirty_ys[i])
                cx = int(dirty_xs[i])
                ch = int(console.ch[cy, cx])
                if ch == 0:
                    # CJK 연속 셀: 건너뜀
                    continue
                fg_arr = console.fg[cy, cx]
                bg_arr = console.bg[cy, cx]
                fg = (int(fg_arr[0]), int(fg_arr[1]), int(fg_arr[2]))
                bg = (int(bg_arr[0]), int(bg_arr[1]), int(bg_arr[2]))
                _render_cell(cx, cy, ch, fg, bg)

        console.reset_dirty()

    @staticmethod
    def _fit_rect(
        src_w: int, src_h: int,
        dst_w: int, dst_h: int,
        integer_scaling: bool = False,
    ) -> Tuple[int, int, int, int]:
        """종횡비 유지 스케일링 영역 계산 → (x, y, w, h)"""
        src_aspect = src_w / max(1, src_h)
        dst_aspect = dst_w / max(1, dst_h)

        if src_aspect > dst_aspect:
            # 소스가 더 넓음 → pillarbox (좌우 검은 띠) 아님, letterbox
            scale = dst_w / src_w
        else:
            # 소스가 더 높음 → letterbox (상하 검은 띠)
            scale = dst_h / src_h

        if integer_scaling and scale >= 1.0:
            scale = int(scale)

        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        x = (dst_w - new_w) // 2
        y = (dst_h - new_h) // 2

        return (x, y, new_w, new_h)

    # ------------------------------------------------------------------
    # tcod.context 호환 속성
    # ------------------------------------------------------------------

    @property
    def sdl_window_p(self):
        """SDL 윈도우 포인터 (호환성, None 반환)"""
        return None

    def convert_event(self, event) -> None:
        """tcod.context.convert_event 호환 (no-op)

        tcod 컨텍스트에서는 픽셀→타일 좌표 변환을 수행하지만,
        PygameContext에서는 별도 변환이 불필요하므로 아무 동작도 하지 않습니다.
        """
        pass

    def close(self) -> None:
        """컨텍스트 종료"""
        logger.info("PygameContext 종료")
        # pygame.display.quit()은 호출하지 않음 (다른 모듈에서 pygame 사용 가능)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
