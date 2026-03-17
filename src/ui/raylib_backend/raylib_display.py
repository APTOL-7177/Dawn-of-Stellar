"""
RaylibDisplay - PygameDisplay 호환 디스플레이 싱글톤

PygameDisplay의 공개 API를 미러링하여 get_display() 교체만으로
전체 게임을 raylib 백엔드로 전환.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Any, Optional, Tuple

from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger("raylib_display")


class RaylibDisplay:
    """
    PygameDisplay 호환 raylib 디스플레이 매니저

    동일한 공개 API:
      .screen_width, .screen_height
      .pixel_width, .pixel_height
      .map_width, .map_height, .sidebar_width, .message_height
      .console, .map_console, .sidebar_console, .message_console
      .context, .tileset (호환성)
      .clear(), .render_map(), .render_bar(), .compose(), .present(), .close()
    """

    @staticmethod
    def _detect_screen_resolution() -> Tuple[int, int]:
        """현재 모니터 해상도 감지"""
        try:
            if platform.system() == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                try:
                    user32.SetProcessDPIAware()
                except Exception:
                    pass
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
                if w > 0 and h > 0:
                    return (w, h)
        except Exception:
            pass

        return (1920, 1080)

    def __init__(self) -> None:
        self.logger = get_logger("display")
        self.config = get_config()
        self._headless = False

        # ── 설정 로드 (PygameDisplay와 동일) ──
        self.screen_width = self.config.get("display.screen_width", 80)
        self.screen_height = self.config.get("display.screen_height", 50)

        # display_mode 우선 사용 (borderless / fullscreen / windowed)
        display_mode = self.config.get("display.display_mode", None)
        if display_mode is not None:
            self.fullscreen = (display_mode == "fullscreen")
            self.borderless_fullscreen = (display_mode == "borderless")
            self.borderless = self.borderless_fullscreen
        else:
            # 기존 설정 호환
            self.fullscreen = self.config.get("display.fullscreen", False)
            self.borderless_fullscreen = self.config.get(
                "display.borderless_fullscreen", True
            )
            self.borderless = self.config.get("display.borderless", True)
            if self.borderless_fullscreen:
                self.borderless = True

        self.keep_aspect = self.config.get("display.keep_aspect", True)
        self.aspect_ratio_locked = self.config.get(
            "display.aspect_ratio_locked", True
        )

        self._fixed_aspect_ratio = 16 / 9

        # 창 크기
        if self.borderless_fullscreen or getattr(self, 'fullscreen', False):
            screen_res = self._detect_screen_resolution()
            self.pixel_width = screen_res[0]
            self.pixel_height = screen_res[1]
        else:
            self.pixel_width = self.config.get("display.pixel_width", 1920)
            self.pixel_height = self.config.get("display.pixel_height", 1080)

        # 패널 크기
        self.map_width = self.config.get("display.panels.map_width", 60)
        self.map_height = self.config.get("display.panels.map_height", 43)
        self.sidebar_width = self.config.get("display.panels.sidebar_width", 20)
        self.message_height = self.config.get("display.panels.message_height", 7)

        # 폰트 렌더러 (FontAtlas 대응)
        self.font_renderer = None

        # 콘솔
        self.console = None
        self.map_console = None
        self.sidebar_console = None
        self.message_console = None

        # 컨텍스트
        self.context = None

        # tcod 호환 속성
        self.tileset = None
        # PygameDisplay 호환: font_atlas 속성
        self.font_atlas = None

        self._initialize_raylib()

    def _initialize_raylib(self) -> None:
        """raylib 초기화"""
        # 지연 임포트 (raylib InitWindow는 한 번만 호출 가능)
        import pyray as rl
        from src.ui.raylib_backend.font_renderer import FontRenderer
        from src.ui.raylib_backend.raylib_console import RaylibConsole
        from src.ui.raylib_backend.raylib_context import RaylibContext
        from src.ui.raylib_backend import event_adapter

        # headless 체크
        env_headless = os.environ.get("DOS_HEADLESS", "").lower()
        config_headless = bool(self.config.get("display.headless", False))

        if config_headless or env_headless in {"1", "true", "yes"}:
            self._headless = True

        # ── 폰트 로드 ──
        self.font_renderer = FontRenderer()
        font_loaded = self._load_font()

        if not font_loaded:
            self.logger.warning("폰트 로드 실패 - 기본 크기 사용")
            self.font_renderer.tile_width = 10
            self.font_renderer.tile_height = 13

        # PygameDisplay 호환: font_atlas 속성 매핑
        self.font_atlas = self.font_renderer

        # ── 콘솔 생성 ──
        self.console = RaylibConsole(self.screen_width, self.screen_height)
        self.map_console = RaylibConsole(self.map_width, self.map_height)
        self.sidebar_console = RaylibConsole(
            self.sidebar_width, self.screen_height
        )
        self.message_console = RaylibConsole(
            self.map_width, self.message_height
        )

        # ── 컨텍스트 생성 ──
        if not self._headless:
            self.context = RaylibContext(
                columns=self.screen_width,
                rows=self.screen_height,
                font_renderer=self.font_renderer,
                title="Dawn of Stellar - 별빛의 여명",
                pixel_width=self.pixel_width,
                pixel_height=self.pixel_height,
                vsync=self.config.get("display.vsync", True),
                borderless=self.borderless,
                borderless_fullscreen=self.borderless_fullscreen,
                fullscreen=getattr(self, 'fullscreen', False),
                keep_aspect=self.keep_aspect,
            )

        # ── 지연 폰트 로드 (InitWindow 이후) ──
        if self.context:
            self._deferred_font_load()

        # ── 이벤트 어댑터 설치 ──
        adapter = event_adapter.install(
            tile_width=self.font_renderer.tile_width,
            tile_height=self.font_renderer.tile_height,
        )

        # wait() 중 화면 갱신 콜백 연결
        if self.context:
            adapter.set_repaint_callback(self.context.repaint)

        self.logger.info(
            f"RaylibDisplay 초기화 완료: "
            f"콘솔 {self.screen_width}x{self.screen_height}, "
            f"창 {self.pixel_width}x{self.pixel_height}, "
            f"타일 {self.font_renderer.tile_width}x{self.font_renderer.tile_height}"
        )

    def _load_font(self) -> bool:
        """폰트 로드 (PygameDisplay 폰트 검색 로직 미러링, BDF 포함)"""
        import pyray as rl
        from src.ui.raylib_backend.font_renderer import FontRenderer

        font_size = self.config.get("display.font_size", 32)
        char_spacing_adjust = self.config.get("display.char_spacing_adjust", 2)

        # 프로젝트 루트
        if hasattr(sys, '_MEIPASS'):
            exe_path = Path(sys.executable)
            if exe_path.parent.name == '_internal':
                project_root = exe_path.parent.parent
            else:
                project_root = exe_path.parent
        else:
            project_root = Path(__file__).parent.parent.parent.parent

        # 폰트 경로 목록 (BDF 1순위 — 비트맵 폰트 직접 파싱)
        if platform.system() == "Windows":
            windows_fonts = os.path.join(
                os.environ.get("WINDIR", r"C:\Windows"), "Fonts"
            )
            font_paths = [
                str(project_root / "GalmuriMono9.bdf"),
                str(project_root / "dalmoori.ttf"),
                str(project_root / "DOSMyungjo.ttf"),
                str(project_root / "GalmuriMono9.ttf"),
                str(project_root / "GalmuriMono9.ttc"),
                os.path.join(windows_fonts, "dalmoori.ttf"),
                os.path.join(windows_fonts, "GalmuriMono9.ttf"),
                os.path.join(windows_fonts, "malgun.ttf"),
            ]
        else:
            font_paths = [
                str(project_root / "GalmuriMono9.bdf"),
                str(project_root / "dalmoori.ttf"),
                str(project_root / "DOSMyungjo.ttf"),
                str(project_root / "GalmuriMono9.ttf"),
                "/usr/share/fonts/opentype/unifont/unifont.otf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            ]

        for font_path in font_paths:
            if not Path(font_path).exists():
                continue

            self.logger.info(f"폰트 시도: {font_path}")
            is_bdf = font_path.lower().endswith('.bdf')

            if is_bdf:
                # BDF: FONTBOUNDINGBOX에서 타일 크기 결정
                bbox = FontRenderer._parse_bdf_bbox(font_path)
                if bbox and bbox[0] > 0 and bbox[1] > 0:
                    self.font_renderer.tile_width = bbox[0]
                    self.font_renderer.tile_height = bbox[1]
                    self.font_renderer._font_path = font_path
                    self.logger.info(
                        f"BDF 폰트 크기 결정 (로드 대기): {font_path}, "
                        f"{bbox[0]}x{bbox[1]}"
                    )
                    return True
            else:
                # TTF: 폰트 크기 계산
                char_height = font_size // 2
                char_width = char_height + char_spacing_adjust

                if not rl.is_window_ready():
                    self.font_renderer.tile_width = char_width
                    self.font_renderer.tile_height = char_height
                    self.font_renderer._font_path = font_path
                    self.logger.info(
                        f"TTF 폰트 크기 결정 (로드 대기): {font_path}, "
                        f"{char_width}x{char_height}"
                    )
                    return True

                if self.font_renderer.load_font(font_path, char_width, char_height):
                    self.logger.info(f"TTF 폰트 로드 성공: {font_path}")
                    return True

        return False

    def _deferred_font_load(self) -> None:
        """컨텍스트 생성 후 폰트 실제 로드 (InitWindow 이후)"""
        if self.font_renderer.is_loaded:
            return  # 이미 로드됨

        path = self.font_renderer._font_path
        if path and Path(path).exists():
            if path.lower().endswith('.bdf'):
                if self.font_renderer.load_bdf(path):
                    self.logger.info(f"지연 BDF 폰트 로드 성공: {path}")
                else:
                    self.logger.warning(f"지연 BDF 폰트 로드 실패: {path}")
            else:
                tw = self.font_renderer.tile_width
                th = self.font_renderer.tile_height
                if self.font_renderer.load_font(path, tw, th):
                    self.logger.info(f"지연 TTF 폰트 로드 성공: {path}")
                else:
                    self.logger.warning(f"지연 TTF 폰트 로드 실패: {path}")

    # ------------------------------------------------------------------
    # PygameDisplay 호환 공개 API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """모든 콘솔 클리어"""
        if self.console:
            self.console.clear()
        if self.map_console:
            self.map_console.clear()
        if self.sidebar_console:
            self.sidebar_console.clear()
        if self.message_console:
            self.message_console.clear()

    def render_map(self, game_map: Any) -> None:
        """맵 렌더링 (PygameDisplay 호환)"""
        if not self.map_console:
            return
        self.map_console.clear()

    def render_bar(
        self,
        console: Any,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        fg_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
    ) -> None:
        """체력/마나 바 렌더링 (PygameDisplay.render_bar 호환)"""
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        if maximum > 0:
            filled = int((current / maximum) * width)
            if filled > 0:
                console.draw_rect(x, y, filled, 1, ord(" "), bg=fg_color)
        text = f"{current}/{maximum}"
        text_x = x + (width - len(text)) // 2
        console.print(text_x, y, text, fg=(255, 255, 255))

    def compose(self) -> None:
        """서브 콘솔을 메인 콘솔에 합성"""
        if not self.console:
            return
        if self.map_console:
            self.map_console.blit(self.console, dest_x=0, dest_y=0)
        if self.sidebar_console:
            self.sidebar_console.blit(
                self.console, dest_x=self.map_width, dest_y=0
            )
        if self.message_console:
            self.message_console.blit(
                self.console, dest_x=0, dest_y=self.map_height
            )

    def present(self) -> None:
        """화면에 표시"""
        # 지연 폰트 로드 (첫 present 호출 시)
        if self.font_renderer and not self.font_renderer.is_loaded:
            self._deferred_font_load()

        if self.context and self.console:
            self.context.present(
                self.console,
                keep_aspect=self.keep_aspect,
                integer_scaling=False,
            )

    def close(self) -> None:
        """디스플레이 종료"""
        if self.font_renderer:
            self.font_renderer.unload()
        if self.context:
            self.context.close()
        self.logger.info("RaylibDisplay 종료")

    # ------------------------------------------------------------------
    # PygameDisplay 호환 추가 속성/메서드
    # ------------------------------------------------------------------

    @property
    def _tile_width(self) -> int:
        return self.font_renderer.tile_width if self.font_renderer else 10

    @property
    def _tile_height(self) -> int:
        return self.font_renderer.tile_height if self.font_renderer else 13
