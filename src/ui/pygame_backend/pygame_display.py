"""
PygameDisplay - TCODDisplay 호환 디스플레이 싱글톤

TCODDisplay의 공개 API를 미러링하여 get_display() 교체만으로
전체 게임을 pygame 백엔드로 전환.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Tuple, Any

import pygame

from src.core.config import get_config
from src.core.logger import get_logger
from src.ui.pygame_backend.font_atlas import FontAtlas
from src.ui.pygame_backend.pygame_console import PygameConsole
from src.ui.pygame_backend.pygame_context import PygameContext
from src.ui.pygame_backend import event_adapter

logger = get_logger("pygame_display")


class PygameDisplay:
    """
    TCODDisplay 호환 pygame 디스플레이 매니저

    TCODDisplay와 동일한 공개 API:
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

        # pygame 폴백
        try:
            if not pygame.display.get_init():
                pygame.display.init()
            info = pygame.display.Info()
            if info.current_w > 0 and info.current_h > 0:
                return (info.current_w, info.current_h)
        except Exception:
            pass

        return (1920, 1080)

    def __init__(self) -> None:
        self.logger = get_logger("display")
        self.config = get_config()
        self._headless = False

        # ── 설정 로드 (TCODDisplay와 동일) ──
        self.screen_width = self.config.get("display.screen_width", 80)
        self.screen_height = self.config.get("display.screen_height", 50)

        self.borderless = self.config.get("display.borderless", True)
        self.borderless_fullscreen = self.config.get("display.borderless_fullscreen", True)
        self.keep_aspect = self.config.get("display.keep_aspect", True)
        self.aspect_ratio_locked = self.config.get("display.aspect_ratio_locked", True)

        if self.borderless_fullscreen:
            self.borderless = True

        self._fixed_aspect_ratio = 16 / 9

        # 창 크기
        if self.borderless_fullscreen:
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

        # 폰트 아틀라스
        self.font_atlas: Optional[FontAtlas] = None

        # 콘솔
        self.console: Optional[PygameConsole] = None
        self.map_console: Optional[PygameConsole] = None
        self.sidebar_console: Optional[PygameConsole] = None
        self.message_console: Optional[PygameConsole] = None

        # 컨텍스트
        self.context: Optional[PygameContext] = None

        # tcod 호환 속성
        self.tileset = None  # tcod.tileset 호환 (PUA 타일용)

        self._initialize_pygame()

    def _install_x11_error_handler(self) -> None:
        """Linux X11 환경에서 치명적 X 에러를 비치명적으로 변환

        X11 BadLength 등의 에러는 기본적으로 프로세스를 즉시 종료시킴.
        이 핸들러를 설치하면 프로세스 종료 대신 플래그만 설정하여
        게임이 계속 실행될 수 있도록 합니다.
        """
        try:
            import ctypes
            import ctypes.util

            x11_name = ctypes.util.find_library('X11')
            if not x11_name:
                return

            x11 = ctypes.CDLL(x11_name)

            XERROR_HANDLER = ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )

            self._x11_error_occurred = False

            def _error_handler(display, event):
                self._x11_error_occurred = True
                self.logger.warning(
                    "X11 에러 감지 - 프로세스 종료를 방지합니다"
                )
                return 0

            self._x11_handler_ref = XERROR_HANDLER(_error_handler)
            x11.XSetErrorHandler(self._x11_handler_ref)
            self.logger.debug("X11 비치명적 에러 핸들러 설치 완료")
        except Exception as e:
            self.logger.debug(f"X11 에러 핸들러 설치 건너뜀: {e}")

    def _initialize_pygame(self) -> None:
        """pygame 초기화"""
        # headless 체크
        env_headless = os.environ.get("DOS_HEADLESS", "").lower()
        config_headless = bool(self.config.get("display.headless", False))

        if config_headless or env_headless in {"1", "true", "yes"}:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self._headless = True
        elif os.environ.get("SDL_VIDEODRIVER") == "dummy":
            self._headless = True
        elif (
            platform.system() == "Linux"
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            self.logger.warning(
                "DISPLAY/WAYLAND_DISPLAY 환경 변수 미설정 - "
                "SDL dummy 비디오 드라이버 사용"
            )
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            self._headless = True

        # Linux X11 BadLength 방지: MIT-SHM 비활성화
        # 큰 BDF 폰트/게이지 타일셋 사용 시 SharedMemory BadLength 에러 발생 방지
        if platform.system() == "Linux":
            os.environ.setdefault("SDL_VIDEO_X11_SHMAT", "0")
            self._install_x11_error_handler()

        # pygame 초기화
        if not pygame.get_init():
            pygame.init()

        # 키 반복 활성화 (키를 누르고 있으면 연속 입력)
        # delay=200ms 후 interval=50ms 간격으로 반복
        pygame.key.set_repeat(400, 50)

        # ── 폰트 로드 ──
        self.font_atlas = FontAtlas()
        font_loaded = self._load_font()

        if not font_loaded:
            self.logger.warning("폰트 로드 실패 - 기본 크기 사용")
            self.font_atlas.tile_width = 10
            self.font_atlas.tile_height = 13

        # ── 콘솔 생성 ──
        self.console = PygameConsole(self.screen_width, self.screen_height)
        self.map_console = PygameConsole(self.map_width, self.map_height)
        self.sidebar_console = PygameConsole(self.sidebar_width, self.screen_height)
        self.message_console = PygameConsole(self.map_width, self.message_height)

        # ── 게이지 타일 초기화 (Phase 2에서 완전 구현) ──
        self._init_gauge_tiles()

        # ── 컨텍스트 생성 ──
        if not self._headless:
            self.context = PygameContext(
                columns=self.screen_width,
                rows=self.screen_height,
                font_atlas=self.font_atlas,
                title="Dawn of Stellar - 별빛의 여명",
                pixel_width=self.pixel_width,
                pixel_height=self.pixel_height,
                vsync=self.config.get("display.vsync", True),
                borderless=self.borderless,
                borderless_fullscreen=self.borderless_fullscreen,
                keep_aspect=self.keep_aspect,
            )

        # ── 이벤트 어댑터 설치 ──
        event_adapter.install(
            tile_width=self.font_atlas.tile_width,
            tile_height=self.font_atlas.tile_height,
        )

        self.logger.info(
            f"PygameDisplay 초기화 완료: "
            f"콘솔 {self.screen_width}x{self.screen_height}, "
            f"창 {self.pixel_width}x{self.pixel_height}, "
            f"타일 {self.font_atlas.tile_width}x{self.font_atlas.tile_height}"
        )

    def _load_font(self) -> bool:
        """폰트 로드 (TCODDisplay 폰트 검색 로직 미러링)"""
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

        # 폰트 경로 목록 (TCODDisplay와 동일 순서)
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

            if font_path.lower().endswith('.bdf'):
                if self.font_atlas.load_bdf(font_path):
                    self.logger.info(f"BDF 폰트 로드 성공: {font_path}")
                    return True
            else:
                char_height = font_size // 2
                char_width = char_height + char_spacing_adjust
                if self.font_atlas.load_truetype(font_path, char_width, char_height):
                    self.logger.info(f"TTF 폰트 로드 성공: {font_path}")
                    return True

        return False

    def _init_gauge_tiles(self) -> None:
        """게이지 타일 초기화

        Phase 2에서 완전 구현. 현재는 tcod tileset 초기화 시도.
        tcod가 있으면 기존 방식 사용, 없으면 건너뜀.
        """
        try:
            import tcod.tileset
            # tcod tileset을 생성하여 게이지 타일 등록 (호환성)
            # 폰트 아틀라스의 타일 크기로 빈 tileset 생성
            tw = self.font_atlas.tile_width
            th = self.font_atlas.tile_height
            if tw > 0 and th > 0:
                self.tileset = tcod.tileset.Tileset(tw, th)
                from src.ui.gauge_tileset import initialize_gauge_tiles
                initialize_gauge_tiles(self.tileset)
                self.logger.info("게이지 타일셋 초기화 완료 (tcod tileset)")
        except Exception as e:
            self.logger.warning(f"게이지 타일 초기화 건너뜀: {e}")
            self.tileset = None

    # ------------------------------------------------------------------
    # TCODDisplay 호환 공개 API
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
        """맵 렌더링 (TCODDisplay 호환)"""
        if not self.map_console:
            return
        self.map_console.clear()
        # 기본 맵 렌더링은 TCODDisplay와 동일한 로직
        # (world_ui.py가 직접 console에 쓰므로 여기서는 최소 구현)

    def render_bar(
        self,
        console: PygameConsole,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        fg_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
    ) -> None:
        """체력/마나 바 렌더링 (TCODDisplay.render_bar 호환)"""
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
            self.sidebar_console.blit(self.console, dest_x=self.map_width, dest_y=0)
        if self.message_console:
            self.message_console.blit(self.console, dest_x=0, dest_y=self.map_height)

    def present(self) -> None:
        """화면에 표시"""
        if self.context and self.console:
            self.context.present(
                self.console,
                keep_aspect=self.keep_aspect,
                integer_scaling=False,
            )

    def close(self) -> None:
        """디스플레이 종료"""
        if self.context:
            self.context.close()
        self.logger.info("PygameDisplay 종료")

    # ------------------------------------------------------------------
    # TCODDisplay 호환 추가 속성/메서드
    # ------------------------------------------------------------------

    @property
    def _tile_width(self) -> int:
        return self.font_atlas.tile_width if self.font_atlas else 10

    @property
    def _tile_height(self) -> int:
        return self.font_atlas.tile_height if self.font_atlas else 13
