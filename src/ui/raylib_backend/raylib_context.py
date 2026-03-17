"""
RaylibContext - PygameContext 호환 raylib 윈도우 컨텍스트

raylib 윈도우 관리 및 콘솔 → 화면 렌더링.
present() 메서드로 RaylibConsole의 셀 그리드를 화면에 표시.
"""

import time
from typing import Optional, Tuple

import pyray as rl

from src.core.logger import get_logger
from src.ui.raylib_backend.font_renderer import FontRenderer
from src.ui.raylib_backend.raylib_console import RaylibConsole
from src.ui.pygame_backend.gauge_tiles import is_gauge_tile
from src.ui.raylib_backend.gauge_tiles import get_raylib_gauge_manager
from src.ui.raylib_backend.effects import EffectManager
from src.ui.character_visual import CharacterVisual, get_sprite_manager

logger = get_logger("raylib_context")


class RaylibContext:
    """
    PygameContext 호환 raylib 윈도우 컨텍스트

    raylib 윈도우를 생성/관리하고 RaylibConsole을
    실제 화면에 렌더링합니다.
    """

    def __init__(
        self,
        columns: int,
        rows: int,
        font_renderer: FontRenderer,
        title: str = "Dawn of Stellar",
        pixel_width: int = 0,
        pixel_height: int = 0,
        vsync: bool = True,
        borderless: bool = False,
        borderless_fullscreen: bool = False,
        fullscreen: bool = False,
        keep_aspect: bool = True,
    ) -> None:
        self.columns = columns
        self.rows = rows
        self.font_renderer = font_renderer
        self.title = title
        self.keep_aspect = keep_aspect

        # 타일 크기 (폰트 네이티브)
        self.tile_width = font_renderer.tile_width
        self.tile_height = font_renderer.tile_height

        # 렌더링 타일 크기
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

        # raylib 창 플래그 설정 (InitWindow 전에 호출)
        flags = rl.ConfigFlags.FLAG_WINDOW_RESIZABLE
        if vsync:
            flags |= rl.ConfigFlags.FLAG_VSYNC_HINT
        if fullscreen:
            flags |= rl.ConfigFlags.FLAG_FULLSCREEN_MODE
        elif borderless_fullscreen:
            flags |= rl.ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE
        elif borderless:
            flags |= rl.ConfigFlags.FLAG_WINDOW_UNDECORATED

        rl.set_config_flags(flags)

        # 메인 윈도우 생성
        rl.init_window(self._window_w, self._window_h, title)
        rl.set_target_fps(60)
        rl.set_exit_key(0)  # ESC 키 자동 종료 비활성화 (게임에서 직접 처리)

        # 아이콘 설정
        try:
            icon = rl.load_image("assets/logo.png")
            rl.set_window_icon(icon)
            rl.unload_image(icon)
        except Exception as e:
            logger.warning(f"로고 아이콘 로드 실패: {e}")

        # borderless fullscreen이면 창 크기를 모니터에 맞춤
        if borderless_fullscreen:
            monitor = rl.get_current_monitor()
            self._window_w = rl.get_monitor_width(monitor)
            self._window_h = rl.get_monitor_height(monitor)
            rl.set_window_size(self._window_w, self._window_h)
            rl.set_window_position(0, 0)

        # 오프스크린 렌더 텍스처 (콘솔 해상도)
        self._render_texture = rl.load_render_texture(
            self._console_pixel_w, self._console_pixel_h
        )
        rl.set_texture_filter(
            self._render_texture.texture,
            rl.TextureFilter.TEXTURE_FILTER_POINT,
        )

        # 종횡비 관련
        self._aspect_ratio = self._console_pixel_w / max(1, self._console_pixel_h)

        # 마지막 dest_rect (좌표 변환용)
        self._last_dest_rect = None

        self._last_frame_time = time.time()

        # ── 스프라이트 오버레이 큐 ────────────────────────────────────
        # (CharacterVisual, cell_x, cell_y, cell_w, cell_h) 튜플 리스트
        self._sprite_overlays: list = []

        # ── 픽셀 오버레이 콜백 ──────────────────────────────────────
        # 콘솔 렌더 텍스처 위에 픽셀 단위로 그리는 콜백 목록
        # 시그니처: callback(dt: float) -> None
        # CombatRenderer, WorldRenderer 등이 등록
        self._pixel_overlay_callbacks: list = []

        # ── 스크린 오버레이 콜백 ────────────────────────────────────
        # 스크린 해상도(스케일링 후)로 그리는 콜백 목록
        # DamagePopup 등 화면 좌표 기반 UI 용
        # 시그니처: callback(dt: float, dest_rect: tuple) -> None
        self._screen_overlay_callbacks: list = []

        # ── 이펙트 매니저 ─────────────────────────────────────────────
        self._effect_manager = EffectManager(
            tile_width=self.tile_width,
            tile_height=self.tile_height,
        )

        logger.info(
            f"RaylibContext 생성: {columns}x{rows} 콘솔, "
            f"{self._window_w}x{self._window_h} 창, "
            f"타일: {self.tile_width}x{self.tile_height}"
        )

    # ------------------------------------------------------------------
    # PygameContext 호환 API
    # ------------------------------------------------------------------

    def present(
        self,
        console: RaylibConsole,
        keep_aspect: Optional[bool] = None,
        integer_scaling: bool = False,
    ) -> None:
        """콘솔을 화면에 렌더링 (PygameContext.present 호환)

        Args:
            console: 렌더링할 RaylibConsole
            keep_aspect: 종횡비 유지 여부 (None이면 기본값 사용)
            integer_scaling: 정수 배율 사용 여부
        """
        if keep_aspect is None:
            keep_aspect = self.keep_aspect

        # 프레임 dt 계산
        now = time.time()
        dt = min(now - self._last_frame_time, 0.05)
        self._last_frame_time = now

        # 이펙트 상태 업데이트
        self._effect_manager.update(dt)

        # 콘솔 → 렌더 텍스처 렌더링
        self._render_console(console)

        # 스프라이트 오버레이 렌더링 (콘솔 위에, 이펙트 전에)
        if self._sprite_overlays:
            mgr = get_sprite_manager()
            rl.begin_texture_mode(self._render_texture)
            for visual, cx, cy, cw, ch in self._sprite_overlays:
                px = cx * self._render_tw
                py = cy * self._render_th
                pw = cw * self._render_tw
                ph = ch * self._render_th
                mgr.draw_raylib(visual, px, py, pw, ph)
            rl.end_texture_mode()
            self._sprite_overlays.clear()

        # 픽셀 오버레이 콜백 실행 (콘솔 해상도, 스프라이트/위젯 등)
        if self._pixel_overlay_callbacks:
            rl.begin_texture_mode(self._render_texture)
            for cb in self._pixel_overlay_callbacks:
                try:
                    cb(dt)
                except Exception as e:
                    logger.error(f"픽셀 오버레이 콜백 오류: {e}", exc_info=True)
            rl.end_texture_mode()
            self._pixel_overlay_callbacks.clear()

        # 콘솔 해상도 이펙트 적용 (글로우/파티클/라이팅)
        rl.begin_texture_mode(self._render_texture)
        self._effect_manager.apply(
            self._console_pixel_w, self._console_pixel_h,
        )
        rl.end_texture_mode()

        # 화면에 스케일링하여 출력
        screen_w = rl.get_screen_width()
        screen_h = rl.get_screen_height()

        rl.begin_drawing()
        rl.clear_background(rl.BLACK)

        tex = self._render_texture.texture
        # 소스 rect: RenderTexture는 Y축 반전 (OpenGL 좌표계)
        source = rl.Rectangle(
            0.0, 0.0,
            float(tex.width), float(-tex.height),
        )

        if keep_aspect:
            dr = self._fit_rect(
                self._console_pixel_w, self._console_pixel_h,
                screen_w, screen_h, integer_scaling,
            )
            dest = rl.Rectangle(
                float(dr[0]), float(dr[1]),
                float(dr[2]), float(dr[3]),
            )
            self._last_dest_rect = dr
        else:
            dest = rl.Rectangle(0.0, 0.0, float(screen_w), float(screen_h))
            self._last_dest_rect = (0, 0, screen_w, screen_h)

        # 셰이크: 오프셋 적용
        sfx = self._effect_manager.screen_fx
        if sfx.enabled and sfx.is_shaking:
            ox, oy = sfx.shake_offset
            dest.x += ox
            dest.y += oy

        rl.draw_texture_pro(
            tex, source, dest,
            rl.Vector2(0.0, 0.0), 0.0, rl.WHITE,
        )

        # 스크린 오버레이 콜백 실행 (스크린 해상도, 데미지 팝업 등)
        if self._screen_overlay_callbacks:
            dr = self._last_dest_rect
            for cb in self._screen_overlay_callbacks:
                try:
                    cb(dt, dr)
                except Exception as e:
                    logger.debug(f"스크린 오버레이 콜백 오류: {e}")
            self._screen_overlay_callbacks.clear()

        # 스크린 해상도 이펙트 적용 (플래시/글리치/CRT/전환)
        self._effect_manager.apply_post(screen_w, screen_h)

        rl.end_drawing()

    def repaint(self) -> None:
        """마지막 렌더 텍스처를 다시 그림 (wait() 중 화면 갱신용)"""
        tex = self._render_texture.texture
        source = rl.Rectangle(
            0.0, 0.0,
            float(tex.width), float(-tex.height),
        )

        screen_w = rl.get_screen_width()
        screen_h = rl.get_screen_height()

        dr = self._last_dest_rect
        if dr:
            dest = rl.Rectangle(
                float(dr[0]), float(dr[1]),
                float(dr[2]), float(dr[3]),
            )
        else:
            dest = rl.Rectangle(0.0, 0.0, float(screen_w), float(screen_h))

        rl.draw_texture_pro(
            tex, source, dest,
            rl.Vector2(0.0, 0.0), 0.0, rl.WHITE,
        )

    def pixel_to_cell(self, px: int, py: int) -> Tuple[int, int]:
        """윈도우 픽셀 좌표를 콘솔 셀 좌표로 변환"""
        dr = self._last_dest_rect
        if dr is None:
            tw = self._render_tw or 10
            th = self._render_th or 13
            return (px // tw, py // th)

        dx, dy, dw, dh = dr
        if dw <= 0 or dh <= 0:
            return (0, 0)
        console_px = (px - dx) * self._console_pixel_w / dw
        console_py = (py - dy) * self._console_pixel_h / dh
        tw = self._render_tw or 10
        th = self._render_th or 13
        cell_x = int(console_px / tw)
        cell_y = int(console_py / th)
        return (cell_x, cell_y)

    def cell_to_console_pixel(self, cell_x: int, cell_y: int) -> Tuple[int, int]:
        """셀 좌표를 콘솔 해상도 픽셀로 변환"""
        tw = self._render_tw or 10
        th = self._render_th or 13
        return (cell_x * tw + tw // 2, cell_y * th + th // 2)

    def _render_console(self, console: RaylibConsole) -> None:
        """RaylibConsole의 셀 데이터를 렌더 텍스처에 렌더링"""
        fr = self.font_renderer
        rtw = self._render_tw
        rth = self._render_th

        rl.begin_texture_mode(self._render_texture)

        if console._all_dirty:
            rl.clear_background(rl.BLACK)
            for cy in range(console.height):
                for cx in range(console.width):
                    ch = int(console.ch[cy, cx])
                    if ch == 0:
                        continue
                    fg_arr = console.fg[cy, cx]
                    bg_arr = console.bg[cy, cx]
                    fg = (int(fg_arr[0]), int(fg_arr[1]), int(fg_arr[2]))
                    bg = (int(bg_arr[0]), int(bg_arr[1]), int(bg_arr[2]))
                    px = cx * rtw
                    py = cy * rth

                    if is_gauge_tile(ch):
                        self._render_gauge(px, py, ch, fg, bg)
                    else:
                        fr.render_cell(px, py, ch, fg, bg)
        else:
            dirty_ys, dirty_xs = console._dirty.nonzero()
            for i in range(len(dirty_ys)):
                cy = int(dirty_ys[i])
                cx = int(dirty_xs[i])
                ch = int(console.ch[cy, cx])
                if ch == 0:
                    continue
                fg_arr = console.fg[cy, cx]
                bg_arr = console.bg[cy, cx]
                fg = (int(fg_arr[0]), int(fg_arr[1]), int(fg_arr[2]))
                bg = (int(bg_arr[0]), int(bg_arr[1]), int(bg_arr[2]))
                px = cx * rtw
                py = cy * rth

                if is_gauge_tile(ch):
                    self._render_gauge(px, py, ch, fg, bg)
                else:
                    fr.render_cell(px, py, ch, fg, bg)

        rl.end_texture_mode()
        console.reset_dirty()

    def _render_gauge(
        self, px: int, py: int, ch: int,
        fg: Tuple[int, int, int], bg: Tuple[int, int, int],
    ) -> None:
        """게이지 타일 렌더링 (PUA 코드포인트 기반, 32분할 정밀)"""
        mgr = get_raylib_gauge_manager()
        mgr.render_gauge_cell(px, py, self._render_tw, self._render_th, ch, fg, bg)

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
            scale = dst_w / src_w
        else:
            scale = dst_h / src_h

        if integer_scaling and scale >= 1.0:
            scale = int(scale)

        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        x = (dst_w - new_w) // 2
        y = (dst_h - new_h) // 2

        return (x, y, new_w, new_h)

    # ------------------------------------------------------------------
    # 스프라이트 오버레이 API
    # ------------------------------------------------------------------

    def add_pixel_overlay(self, callback) -> None:
        """콘솔 해상도 픽셀 오버레이 콜백 등록 (1프레임)

        콘솔 렌더 텍스처 위에 직접 pyray로 그리는 콜백.
        CombatRenderer, WorldRenderer 등에서 사용.

        Args:
            callback: (dt: float) -> None
        """
        self._pixel_overlay_callbacks.append(callback)

    def add_screen_overlay(self, callback) -> None:
        """스크린 해상도 오버레이 콜백 등록 (1프레임)

        스케일링 후 화면에 직접 그리는 콜백.
        DamagePopup 등 화면 좌표 기반 UI 용.

        Args:
            callback: (dt: float, dest_rect: tuple) -> None
        """
        self._screen_overlay_callbacks.append(callback)

    def add_sprite_overlay(
        self, visual: CharacterVisual,
        cell_x: int, cell_y: int,
        cell_w: int = 2, cell_h: int = 3,
    ) -> None:
        """다음 프레임에 그릴 스프라이트 오버레이 추가

        Args:
            visual: 캐릭터 시각 정보
            cell_x, cell_y: 셀 좌표 (좌상단)
            cell_w, cell_h: 셀 단위 크기
        """
        self._sprite_overlays.append((visual, cell_x, cell_y, cell_w, cell_h))

    # ------------------------------------------------------------------
    # PygameContext 호환 속성
    # ------------------------------------------------------------------

    @property
    def effect_manager(self) -> EffectManager:
        """이펙트 매니저 접근 (CombatUI 등에서 사용)"""
        return self._effect_manager

    @property
    def sdl_window_p(self):
        """호환성, None 반환"""
        return None

    def convert_event(self, event) -> None:
        """PygameContext.convert_event 호환 (no-op)"""
        pass

    def close(self) -> None:
        """컨텍스트 종료"""
        logger.info("RaylibContext 종료")
        if self._render_texture:
            rl.unload_render_texture(self._render_texture)
        rl.close_window()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
