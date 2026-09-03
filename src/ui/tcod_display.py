"""
TCOD Display - python-tcod 기반 디스플레이 시스템

tcod를 사용한 렌더링 및 UI 관리
"""

import tcod
import tcod.context
import tcod.console
import tcod.event
from typing import Optional, Tuple, Any, List, Dict
from pathlib import Path
import os
import platform
import sys
import shutil
import time

from src.core.config import get_config
from src.core.logger import get_logger
from src.ui.gauge_tileset import initialize_gauge_tiles
from src.ui.visual_tokens import rgb


class Colors:
    """색상 정의"""
    # 기본 색상
    BLACK = rgb("surface.base")
    WHITE = rgb("text.primary")
    GRAY = rgb("text.secondary")
    DARK_GRAY = rgb("text.muted")

    # 추가 색상
    RED = rgb("status.error")
    GREEN = rgb("status.success")
    BLUE = rgb("accent.blue")
    DARK_BLUE = rgb("surface.grid")
    LIGHT_BLUE = rgb("status.info")
    YELLOW = rgb("status.warning")
    CYAN = rgb("accent.cyan")
    MAGENTA = rgb("accent.violet")
    ORANGE = rgb("threat.high")
    PURPLE = rgb("rarity.epic")
    GOLD = rgb("rarity.legendary")

    # UI 색상
    UI_BG = rgb("surface.panel")
    UI_BORDER = rgb("line.default")
    UI_TEXT = rgb("text.primary")
    UI_TEXT_SELECTED = rgb("accent.amber")

    # HP/MP 바
    HP_FULL = rgb("status.hp_high")
    HP_HALF = rgb("status.hp_mid")
    HP_LOW = rgb("status.hp_low")
    HP_BG = rgb("surface.sunken")

    MP_FULL = rgb("status.mp")
    MP_BG = rgb("surface.sunken")

    # 상처
    WOUND = rgb("threat.high")

    # 음식 아이템
    FOOD = rgb("accent.amber")

    # 맵 색상
    FLOOR = rgb("surface.grid")
    WALL = rgb("surface.sunken")
    PLAYER = rgb("text.primary")
    ENEMY = rgb("threat.critical")
    ITEM = rgb("rarity.legendary")

    FOCUS = rgb("state.focus")
    HOVER_BG = rgb("state.hover")
    ACTIVE_BG = rgb("state.active")
    DISABLED = rgb("state.disabled")
    TOOLTIP_BG = rgb("state.tooltip")
    DRAG_BG = rgb("state.drag")


class TCODDisplay:
    """
    TCOD 디스플레이 매니저

    화면 렌더링 및 레이아웃 관리
    """
    
    @staticmethod
    def _detect_screen_resolution() -> Tuple[int, int]:
        """현재 모니터의 해상도 가져오기 (정적 메서드)"""
        try:
            if platform.system() == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                try:
                    user32.SetProcessDPIAware()
                except Exception:
                    pass
                width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                if width > 0 and height > 0:
                    return (width, height)
            else:
                # Linux/Mac: xrandr 파싱 시도 (tkinter 불필요)
                if platform.system() == "Linux":
                    try:
                        import subprocess
                        result = subprocess.run(
                            ["xrandr", "--current"],
                            capture_output=True, text=True, timeout=2
                        )
                        if result.returncode == 0:
                            import re
                            match = re.search(r'(\d+)x(\d+)\+0\+0', result.stdout)
                            if not match:
                                match = re.search(r'current\s+(\d+)\s*x\s*(\d+)', result.stdout)
                            if match:
                                w, h = int(match.group(1)), int(match.group(2))
                                if w > 0 and h > 0:
                                    return (w, h)
                    except Exception:
                        pass

                # 폴백: tkinter (설치되어 있을 때만)
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    width = root.winfo_screenwidth()
                    height = root.winfo_screenheight()
                    root.destroy()
                    if width > 0 and height > 0:
                        return (width, height)
                except Exception:
                    pass

                # 폴백: pygame 디스플레이 정보
                try:
                    import pygame
                    if not pygame.display.get_init():
                        pygame.display.init()
                    info = pygame.display.Info()
                    if info.current_w > 0 and info.current_h > 0:
                        return (info.current_w, info.current_h)
                except Exception:
                    pass
        except Exception:
            pass

        # 기본값: 1920x1080
        return (1920, 1080)

    def __init__(self) -> None:
        self.logger = get_logger("display")
        self.config = get_config()
        self._headless = False

        # 화면 크기 (기본값 - 콘솔 크기는 고정)
        self.screen_width = self.config.get("display.screen_width", 80)
        self.screen_height = self.config.get("display.screen_height", 50)
        
        # 디스플레이 설정 - display_mode 우선, 없으면 기존 설정에서 추론
        display_mode = self.config.get("display.display_mode", None)
        if display_mode is not None:
            self.fullscreen = (display_mode == "fullscreen")
            self.borderless_fullscreen = (display_mode == "borderless")
            self.borderless = self.borderless_fullscreen
        else:
            self.borderless = self.config.get("display.borderless", True)
            self.borderless_fullscreen = self.config.get("display.borderless_fullscreen", True)
            self.fullscreen = self.config.get("display.fullscreen", False)
            if self.borderless_fullscreen:
                self.borderless = True
        self.keep_aspect = self.config.get("display.keep_aspect", True)  # 종횡비 유지 (검은 띠)
        self.aspect_ratio_locked = self.config.get("display.aspect_ratio_locked", True)
        
        # 16:9 고정 종횡비 (1920/1080 = 1.777...)
        self._fixed_aspect_ratio = 16 / 9  # 1.7777...
        
        # 창 크기 설정
        if self.borderless_fullscreen or self.fullscreen:
            # 전체 창화면 / 전체화면: 모니터 해상도 사용
            screen_res = self._detect_screen_resolution()
            self.pixel_width = screen_res[0]
            self.pixel_height = screen_res[1]
            mode_name = "전체화면" if self.fullscreen else "전체 창화면"
            self.logger.info(f"{mode_name} 모드: {self.pixel_width}x{self.pixel_height}")
        else:
            # 창모드: 별도 창 크기 사용
            self.pixel_width = self.config.get("display.window_width", 1280)
            self.pixel_height = self.config.get("display.window_height", 720)
            self.logger.info(f"창모드: {self.pixel_width}x{self.pixel_height}")

        self.logger.info(
            f"콘솔 크기: {self.screen_width}x{self.screen_height}, "
            f"창 크기: {self.pixel_width}x{self.pixel_height}, "
            f"종횡비: 16:9 고정"
        )

        # 패널 크기
        self.map_width = self.config.get("display.panels.map_width", 60)
        self.map_height = self.config.get("display.panels.map_height", 43)
        self.sidebar_width = self.config.get("display.panels.sidebar_width", 20)
        self.message_height = self.config.get("display.panels.message_height", 7)

        # TCOD 초기화
        self.tileset: Optional[tcod.tileset.Tileset] = None
        self.context: Optional[tcod.context.Context] = None
        self.console: Optional[tcod.console.Console] = None

        # 서브 콘솔 (패널들)
        self.map_console: Optional[tcod.console.Console] = None
        self.sidebar_console: Optional[tcod.console.Console] = None
        self.message_console: Optional[tcod.console.Console] = None
        
        # 종횡비 유지 관련
        self._last_window_size = None
        self._aspect_ratio_check_counter = 0  # 프레임 카운터 (너무 자주 확인하지 않기 위해)

        # 사이드바 게이지 애니메이션 시스템
        self._sidebar_anim: Dict[str, Dict] = {}  # key: "hp"/"mp" → {current, previous, target, start_time}
        self._sidebar_prev_values: Dict[str, int] = {}  # 이전 프레임 실제 값 (변화 감지용)
        self._sidebar_popups: List[Dict] = []  # 데미지/힐 팝업 [{text, x, y, start_time, color, dy}]
        self._sidebar_last_time = time.time()

        self._initialize_tcod()

    def _enable_dummy_video_driver(self, reason: str) -> None:
        """헤드리스 환경을 위해 SDL dummy 비디오 드라이버 활성화"""
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            self._headless = True
            return
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.pop("DISPLAY", None)
        os.environ.pop("WAYLAND_DISPLAY", None)
        self._headless = True
        # SDL 리셋 시도 (tcod 버전에 따라 API가 다름)
        try:
            import ctypes
            lib_names = {
                "Linux": ["libSDL2-2.0.so.0", "libSDL2-2.0.so", "libSDL2.so"],
                "Windows": ["SDL2.dll"],
                "Darwin": ["libSDL2.dylib"],
            }
            for lib_name in lib_names.get(platform.system(), []):
                try:
                    sdl2 = ctypes.CDLL(lib_name)
                    sdl2.SDL_Quit()
                    break
                except OSError:
                    continue
        except Exception:
            pass  # SDL 리셋 실패해도 무시 - 이후 context 생성 시 재초기화됨
        self.logger.warning(f"{reason} - SDL dummy 비디오 드라이버 사용")

    def _install_x11_error_handler(self) -> None:
        """Linux X11 환경에서 치명적 X 에러를 비치명적으로 변환

        X11 BadLength 등의 에러는 기본적으로 프로세스를 즉시 종료시켜
        Python 예외 처리를 우회합니다. 이 핸들러를 설치하면
        X 에러 발생 시 프로세스 종료 대신 플래그만 설정하여
        fallback 로직이 실행될 수 있도록 합니다.
        """
        try:
            import ctypes
            import ctypes.util

            x11_name = ctypes.util.find_library('X11')
            if not x11_name:
                return

            x11 = ctypes.CDLL(x11_name)

            # XErrorHandler: int (*)(Display*, XErrorEvent*)
            XERROR_HANDLER = ctypes.CFUNCTYPE(
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )

            self._x11_error_occurred = False

            def _error_handler(display, event):
                self._x11_error_occurred = True
                self.logger.warning(
                    "X11 에러 감지 - 프로세스 종료를 방지하고 fallback 렌더러로 재시도합니다"
                )
                return 0

            # GC가 콜백을 수집하지 못하도록 인스턴스에 참조 유지
            self._x11_handler_ref = XERROR_HANDLER(_error_handler)
            x11.XSetErrorHandler(self._x11_handler_ref)
            self.logger.debug("X11 비치명적 에러 핸들러 설치 완료")
        except Exception as e:
            self.logger.debug(f"X11 에러 핸들러 설치 건너뜀: {e}")

    def _try_create_context(self, context_kwargs: dict, basic_kwargs: dict):
        """tcod 컨텍스트 생성 (X11 에러 감지 시 자동 fallback)

        시도 순서:
        1. 요청된 렌더러로 생성
        2. X11 에러 감지 시 → SDL2 렌더러로 재시도
        3. 실패 시 → 렌더러 미지정으로 재시도
        4. 실패 시 → 헤드리스 dummy 드라이버로 재시도
        """
        import traceback

        def _x11_error_detected() -> bool:
            """X11 에러 핸들러가 에러를 잡았는지 확인"""
            if getattr(self, '_x11_error_occurred', False):
                self._x11_error_occurred = False
                return True
            return False

        # 1차: 요청된 설정으로 시도
        try:
            if self._headless:
                context_kwargs.pop("renderer", None)
                context_kwargs["vsync"] = False
            ctx = tcod.context.new(**context_kwargs)
            if _x11_error_detected():
                self.logger.warning("X11 에러 감지 (1차 시도) - fallback 렌더러로 재시도")
                try:
                    ctx.close()
                except Exception:
                    pass
                raise RuntimeError("X11 BadLength detected")
            self.logger.info("TCOD 컨텍스트 생성 완료")
            return ctx
        except Exception as e:
            self.logger.error(f"컨텍스트 생성 오류 (1차): {e}")
            self.logger.debug(traceback.format_exc())

        # 2차: Linux에서 SDL2 렌더러로 재시도 (OpenGL이 실패한 경우)
        if not self._headless:
            for fallback_renderer, fallback_name in [
                (tcod.context.RENDERER_SDL2, "SDL2"),
                (None, "자동"),
            ]:
                try:
                    fb_kwargs = dict(basic_kwargs)
                    if fallback_renderer is not None:
                        fb_kwargs["renderer"] = fallback_renderer
                    fb_kwargs["vsync"] = context_kwargs.get("vsync", True)
                    ctx = tcod.context.new(**fb_kwargs)
                    if _x11_error_detected():
                        self.logger.warning(
                            f"X11 에러 감지 ({fallback_name} 렌더러) - 다음 fallback 시도"
                        )
                        try:
                            ctx.close()
                        except Exception:
                            pass
                        continue
                    self.logger.info(f"TCOD 컨텍스트 생성 완료 (fallback: {fallback_name} 렌더러)")
                    return ctx
                except Exception as fb_e:
                    self.logger.warning(f"fallback 컨텍스트 생성 실패 ({fallback_name}): {fb_e}")

        # 3차: 헤드리스 dummy 드라이버
        if not self._headless:
            self._enable_dummy_video_driver("디스플레이 초기화 실패 - 모든 렌더러 실패")
            try:
                fb_kwargs = dict(basic_kwargs)
                fb_kwargs["vsync"] = False
                ctx = tcod.context.new(**fb_kwargs)
                self.logger.info("TCOD 컨텍스트 생성 완료 (dummy video driver)")
                return ctx
            except Exception as dummy_e:
                self.logger.error(f"헤드리스 컨텍스트 생성도 실패: {dummy_e}")
                self.logger.error(traceback.format_exc())

        return None

    def _initialize_tcod(self) -> None:
        """TCOD 초기화"""
        # 한글 지원 TrueType 폰트 로드
        font_size = self.config.get("display.font_size", 32)
        char_spacing_adjust = self.config.get("display.char_spacing_adjust", 2)

        import platform
        import os

        # Linux X11: BadLength 등 치명적 X 에러 방지
        if platform.system() == "Linux":
            # MIT-SHM 비활성화: 대용량 타일셋을 SDL2로 X11에 업로드할 때
            # XShmPutImage가 XMaxRequestSize를 초과하는 BadLength 방지
            os.environ.setdefault("SDL_VIDEO_X11_SHMAT", "0")
            self._install_x11_error_handler()

        env_headless = os.environ.get("DOS_HEADLESS", "").lower()
        config_headless = bool(self.config.get("display.headless", False))

        if config_headless or env_headless in {"1", "true", "yes"}:
            self._enable_dummy_video_driver("헤드리스 모드 설정 감지")
        elif (
            platform.system() == "Linux"
            and not os.environ.get("DISPLAY")
            and not os.environ.get("WAYLAND_DISPLAY")
        ):
            self._enable_dummy_video_driver("DISPLAY/WAYLAND 환경 변수 미설정 감지")
        elif os.environ.get("SDL_VIDEODRIVER") == "dummy":
            self._headless = True
        elif platform.system() == "Linux":
            display_env = os.environ.get("DISPLAY")
            wayland_env = os.environ.get("WAYLAND_DISPLAY")
            if display_env and not self._headless:
                # X11 환경: Xauthority 검사 (Wayland에서는 불필요)
                if not wayland_env:
                    xauth_path = os.environ.get("XAUTHORITY") or str(Path.home() / ".Xauthority")
                    if not os.path.exists(xauth_path):
                        self.logger.debug(f"Xauthority 파일 없음: {xauth_path} - X11 인증 검사 건너뜀")
                    elif not os.access(xauth_path, os.R_OK):
                        self.logger.warning(f"Xauthority 파일 접근 불가: {xauth_path}")
                # 디스플레이 접근 확인 (xrandr/xdpyinfo)
                probe_cmd = None
                if shutil.which("xrandr"):
                    probe_cmd = ["xrandr", "--current"]
                elif shutil.which("xdpyinfo"):
                    probe_cmd = ["xdpyinfo"]
                if probe_cmd:
                    try:
                        import subprocess
                        probe = subprocess.run(
                            probe_cmd,
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if probe.returncode != 0:
                            reason = probe.stderr.strip() or probe.stdout.strip() or f"{probe_cmd[0]} 실패"
                            self.logger.warning(f"디스플레이 확인 경고: {reason}")
                    except Exception as probe_error:
                        self.logger.debug(f"디스플레이 확인 예외 (무시): {probe_error}")
                else:
                    self.logger.debug("디스플레이 확인용 유틸리티(xrandr/xdpyinfo) 없음 - 확인 건너뜀")

        # OS별 시스템 폰트 경로 (한글 지원)
        font_paths = []

        # 프로젝트 루트 경로 (PyInstaller 환경 고려)
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 패키징된 경우
            exe_path = Path(sys.executable)
            if exe_path.parent.name == '_internal':
                # _internal 폴더 안에 있는 경우 (onedir 모드)
                project_root = exe_path.parent.parent
                self.logger.info(f"PyInstaller onedir 환경 - 프로젝트 루트: {project_root.absolute()}")
            else:
                # 일반적인 경우
                project_root = exe_path.parent
                self.logger.info(f"PyInstaller 환경 - 프로젝트 루트: {project_root.absolute()}")
        else:
            # 일반 실행인 경우
            project_root = Path(__file__).parent.parent.parent
            self.logger.info(f"일반 환경 - 프로젝트 루트: {project_root.absolute()}")

        if platform.system() == "Windows":
            # Windows 시스템 폰트 (고정폭 우선 - 공백 제거)
            windows_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
            font_paths = [
                str(project_root / "GalmuriMono9.bdf"),          # 갈무리모노 비트맵 (1순위!)
                str(project_root / "dalmoori.ttf"),              # 달무리 (특수문자 완벽 지원!)
                str(project_root / "DOSMyungjo.ttf"),            # DOS명조 (특수문자 없음)
                str(project_root / "GalmuriMono9.ttf"),          # 갈무리모노
                str(project_root / "GalmuriMono9.ttc"),          # 갈무리모노 TTC
                os.path.join(windows_fonts, "dalmoori.ttf"),     # 시스템 달무리
                os.path.join(windows_fonts, "GalmuriMono9.ttf"), # 시스템 갈무리모노
                os.path.join(windows_fonts, "HTSMGOT.TTF"),      # 함초롬돋움 (고정폭)
                os.path.join(windows_fonts, "gulim.ttf"),        # 굴림 (TTF 버전)
                os.path.join(windows_fonts, "batang.ttf"),       # 바탕 (TTF 버전)
                os.path.join(windows_fonts, "malgunbd.ttf"),     # 맑은 고딕 Bold
                os.path.join(windows_fonts, "malgun.ttf"),       # 맑은 고딕
                os.path.join(windows_fonts, "msyh.ttf"),         # Microsoft YaHei
            ]
        else:
            # Linux/Mac 시스템 폰트
            font_paths = [
                str(project_root / "GalmuriMono9.bdf"),          # 갈무리모노 비트맵 (1순위!)
                str(project_root / "dalmoori.ttf"),              # 달무리 (특수문자 완벽 지원!)
                str(project_root / "DOSMyungjo.ttf"),            # DOS명조 (특수문자 없음)
                str(project_root / "GalmuriMono9.ttf"),          # 갈무리모노
                "/usr/share/fonts/opentype/unifont/unifont.otf",  # Unifont (유니코드 전체)
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # WenQuanYi (CJK)
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # 폴백
                "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # Mac 애플 고딕
            ]

        self.tileset = None
        self.logger.info(f"폰트 검색 시작 (총 {len(font_paths)}개 경로)")

        for i, font_path in enumerate(font_paths):
            self.logger.info(f"[{i+1}/{len(font_paths)}] 시도: {font_path}")

            try:
                if not Path(font_path).exists():
                    self.logger.warning(f"  → 파일 없음")
                    continue

                self.logger.info(f"  → 파일 발견! 로딩 시도...")

                # BDF 비트맵 폰트 vs TrueType 폰트 구분
                if font_path.lower().endswith('.bdf'):
                    # BDF 비트맵 폰트 (크기 고정)
                    self.logger.info(f"  → BDF 비트맵 폰트 감지")
                    self.tileset = tcod.tileset.load_bdf(font_path)

                    # 타일셋을 전역 기본값으로 설정
                    tcod.tileset.set_default(self.tileset)

                    self.logger.info(
                        f"  [OK] 비트맵 폰트 로드 성공: {font_path}\n"
                        f"    셀 크기: {self.tileset.tile_width}x{self.tileset.tile_height}"
                    )
                else:
                    # TrueType/OpenType 폰트
                    self.logger.info(f"  → TrueType 폰트 감지")

                    # 타일 크기 설정
                    char_height = font_size // 2
                    char_width = char_height + char_spacing_adjust

                    self.tileset = tcod.tileset.load_truetype_font(
                        font_path,
                        char_width,
                        char_height,
                    )

                    # 타일셋을 전역 기본값으로 설정
                    tcod.tileset.set_default(self.tileset)

                    self.logger.info(
                        f"  ✓ TrueType 폰트 로드 성공: {font_path}\n"
                        f"    셀 크기: {char_width}x{char_height}"
                    )

                # 게이지 타일셋 초기화 (픽셀 단위 게이지용)
                try:
                    initialize_gauge_tiles(self.tileset)
                    self.logger.info("  [OK] 게이지 타일셋 초기화 완료")
                except Exception as gauge_e:
                    self.logger.warning(f"  게이지 타일셋 초기화 실패: {gauge_e}")

                break

            except Exception as e:
                self.logger.warning(f"  ✗ 로드 실패: {e}")
                continue

        # 폴백: 기본 폰트
        if not self.tileset:
            self.logger.warning(
                "한글 시스템 폰트를 찾을 수 없습니다. "
                "기본 터미널 폰트를 사용합니다 (한글이 깨질 수 있음)."
            )
            self.tileset = None

        # 콘솔 생성
        self.console = tcod.console.Console(self.screen_width, self.screen_height)

        # 서브 콘솔 생성
        self.map_console = tcod.console.Console(self.map_width, self.map_height)
        self.sidebar_console = tcod.console.Console(self.sidebar_width, self.screen_height)
        self.message_console = tcod.console.Console(
            self.map_width,
            self.message_height
        )

        # 컨텍스트 생성
        if self.tileset:
            # 렌더러 선택 (config에서 가져오거나 자동 선택)
            renderer_name = self.config.get("display.renderer", "auto")
            renderer_map = {
                "sdl2": tcod.context.RENDERER_SDL2,
                "opengl": tcod.context.RENDERER_OPENGL,
                "opengl2": tcod.context.RENDERER_OPENGL2,
                "auto": None  # TCOD가 자동 선택
            }
            renderer = renderer_map.get(renderer_name.lower(), None)

            # 타일 크기 가져오기
            self._tile_width = getattr(self.tileset, 'tile_width', 10) if self.tileset else 10
            self._tile_height = getattr(self.tileset, 'tile_height', 13) if self.tileset else 13
            
            # 16:9 고정 종횡비 사용
            self._aspect_ratio = self._fixed_aspect_ratio
            
            # 콘솔 크기와 종횡비 확인
            console_aspect = self.screen_width / self.screen_height
            self.logger.info(
                f"콘솔 크기: {self.screen_width}x{self.screen_height} (고정), "
                f"콘솔 종횡비: {console_aspect:.4f}, "
                f"창 종횡비: 16:9 고정 ({self._aspect_ratio:.4f})"
            )

            context_kwargs = {
                "columns": self.screen_width,
                "rows": self.screen_height,
                "tileset": self.tileset,
                "title": "Dawn of Stellar - 별빛의 여명",
                "vsync": self.config.get("display.vsync", True),
            }

            # Linux에서 renderer=auto이면 OpenGL2를 우선 사용
            # X11 환경에서 대용량 타일셋(한글 BDF 폰트 + 게이지 타일)을
            # SDL2 소프트웨어 렌더러로 업로드 시 MIT-SHM BadLength 에러 발생 방지
            if renderer is None and platform.system() == "Linux" and not self._headless:
                renderer = tcod.context.RENDERER_OPENGL2
                renderer_name = "opengl2 (Linux 자동 선택)"
                self.logger.info(
                    f"Linux 환경 감지 - X11 BadLength 방지를 위해 OpenGL2 렌더러 사용"
                )

            if renderer is not None:
                context_kwargs["renderer"] = renderer
                self.logger.info(f"렌더러 사용: {renderer_name}")

            basic_kwargs = {
                "columns": self.screen_width,
                "rows": self.screen_height,
                "tileset": self.tileset,
                "title": "Dawn of Stellar - 별빛의 여명",
            }

            # context 생성
            self.context = self._try_create_context(context_kwargs, basic_kwargs)

            if self.context:
                if not self._headless:
                    # 전체 화면 모드 설정 (context 생성 후 SDL로 직접 설정)
                    if self.fullscreen:
                        self._set_exclusive_fullscreen_mode()
                    elif self.borderless_fullscreen:
                        self._set_fullscreen_desktop_mode()
                    elif self.borderless:
                        self._set_borderless_mode()

                    # 16:9 고정 종횡비 설정
                    self._set_aspect_ratio_constraint(self._fixed_aspect_ratio)

                    self.logger.info(
                        f"창 크기: {self.pixel_width}x{self.pixel_height}, "
                        f"종횡비: 16:9 고정"
                    )
                else:
                    self.logger.info(
                        "헤드리스 모드 감지 (SDL_VIDEODRIVER=dummy) - 창/전체화면 설정 건너뜀"
                    )
        else:
            try:
                self.context = tcod.context.new_terminal(
                    self.screen_width,
                    self.screen_height,
                    title="Dawn of Stellar - 별빛의 여명",
                    vsync=self.config.get("display.vsync", True)
                )
            except Exception as e:
                import traceback
                self.logger.error(f"터미널 컨텍스트 생성 실패: {e}")
                self.logger.error(traceback.format_exc())
                if not self._headless:
                    self._enable_dummy_video_driver("터미널 컨텍스트 생성 실패 감지")
                    try:
                        self.context = tcod.context.new_terminal(
                            self.screen_width,
                            self.screen_height,
                            title="Dawn of Stellar - 별빛의 여명",
                            vsync=False
                        )
                        self.logger.info("터미널 컨텍스트 생성 완료 (dummy video driver)")
                    except Exception as e2:
                        self.logger.error(f"헤드리스 터미널 컨텍스트 생성 실패: {e2}")

        self.logger.info(
            "TCOD 초기화 완료",
            {"width": self.screen_width, "height": self.screen_height}
        )

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

    def render_map(self, game_map: any) -> None:
        """
        맵 렌더링

        Args:
            game_map: 게임 맵 객체
        """
        if not self.map_console:
            return

        self.map_console.clear()

        # 실제 맵 렌더링 구현
        if hasattr(game_map, 'tiles') and hasattr(game_map, 'width') and hasattr(game_map, 'height'):
            # 맵 타일 렌더링
            for y in range(min(game_map.height, self.map_height)):
                for x in range(min(game_map.width, self.map_width)):
                    tile = game_map.tiles[y][x]

                    # 타일 타입에 따라 렌더링
                    if hasattr(tile, 'type'):
                        if tile.type == "floor" or tile.type == 1:
                            self.map_console.print(x, y, ".", fg=Colors.FLOOR)
                        elif tile.type == "wall" or tile.type == 0:
                            self.map_console.print(x, y, "#", fg=Colors.WALL)
                        elif tile.type == "door":
                            self.map_console.print(x, y, "+", fg=Colors.UI_TEXT)
                        elif tile.type == "stairs_up":
                            self.map_console.print(x, y, "<", fg=Colors.WHITE)
                        elif tile.type == "stairs_down":
                            self.map_console.print(x, y, ">", fg=Colors.WHITE)
                        else:
                            self.map_console.print(x, y, ".", fg=Colors.FLOOR)
                    else:
                        # 숫자로 표현된 타일
                        if tile == 1:
                            self.map_console.print(x, y, ".", fg=Colors.FLOOR)
                        else:
                            self.map_console.print(x, y, "#", fg=Colors.WALL)

            # 플레이어 위치 렌더링
            if hasattr(game_map, 'player_x') and hasattr(game_map, 'player_y'):
                self.map_console.print(game_map.player_x, game_map.player_y, "@", fg=Colors.PLAYER)
            else:
                # 기본 위치
                self.map_console.print(self.map_width // 2, self.map_height // 2, "@", fg=Colors.PLAYER)
        else:
            # 맵 데이터가 없는 경우 기본 맵 표시
            for y in range(self.map_height):
                for x in range(self.map_width):
                    self.map_console.print(x, y, ".", fg=Colors.FLOOR)

            # 테스트용 플레이어 표시
            self.map_console.print(
                self.map_width // 2,
                self.map_height // 2,
                "@",
                fg=Colors.PLAYER
            )

    def render_sidebar(self, character: any) -> None:
        """
        사이드바 렌더링 (캐릭터 정보)

        Args:
            character: 캐릭터 객체
        """
        if not self.sidebar_console:
            return

        self.sidebar_console.clear()

        y = 1
        # 이름
        self.sidebar_console.print(1, y, "캐릭터 정보", fg=Colors.UI_TEXT)
        y += 2

        # 실제 캐릭터 정보 표시
        if character:
            # 이름과 직업
            char_name = getattr(character, 'name', '알 수 없음')
            char_class = getattr(character, 'job_name', getattr(character, 'character_class', '모험가'))
            self.sidebar_console.print(1, y, f"이름: {char_name}", fg=Colors.WHITE)
            y += 1
            self.sidebar_console.print(1, y, f"직업: {char_class}", fg=Colors.WHITE)
            y += 1

            # 레벨
            level = getattr(character, 'level', 1)
            self.sidebar_console.print(1, y, f"레벨: {level}", fg=Colors.WHITE)
            y += 2

            # HP 바 (애니메이션)
            current_hp = getattr(character, 'current_hp', 100)
            max_hp = getattr(character, 'max_hp', 100)
            self.sidebar_console.print(1, y, "HP:", fg=Colors.UI_TEXT)
            y += 1
            self._render_bar(self.sidebar_console, 1, y, 18, current_hp, max_hp, Colors.HP_FULL, Colors.HP_BG, bar_key="hp")
            y += 2

            # MP 바 (애니메이션)
            current_mp = getattr(character, 'current_mp', 50)
            max_mp = getattr(character, 'max_mp', 50)
            self.sidebar_console.print(1, y, "MP:", fg=Colors.UI_TEXT)
            y += 1
            self._render_bar(self.sidebar_console, 1, y, 18, current_mp, max_mp, Colors.MP_FULL, Colors.MP_BG, bar_key="mp")
            y += 2

            # 주요 스탯 표시
            if hasattr(character, 'strength'):
                self.sidebar_console.print(1, y, f"STR: {character.strength}", fg=Colors.WHITE)
                y += 1
            if hasattr(character, 'defense'):
                self.sidebar_console.print(1, y, f"DEF: {character.defense}", fg=Colors.WHITE)
                y += 1
            if hasattr(character, 'magic'):
                self.sidebar_console.print(1, y, f"MAG: {character.magic}", fg=Colors.WHITE)
                y += 1
            if hasattr(character, 'speed'):
                self.sidebar_console.print(1, y, f"SPD: {character.speed}", fg=Colors.WHITE)
                y += 1
        else:
            # 캐릭터 정보가 없는 경우
            self.sidebar_console.print(1, y, "이름: 전사", fg=Colors.WHITE)
            y += 1
            self.sidebar_console.print(1, y, "레벨: 1", fg=Colors.WHITE)
            y += 2

            # HP 바
            self.sidebar_console.print(1, y, "HP:", fg=Colors.UI_TEXT)
            y += 1
            self._render_bar(self.sidebar_console, 1, y, 18, 100, 100, Colors.HP_FULL, Colors.HP_BG)
            y += 2

        # MP 바
        self.sidebar_console.print(1, y, "MP:", fg=Colors.UI_TEXT)
        y += 1
        self._render_bar(self.sidebar_console, 1, y, 18, 50, 50, Colors.MP_FULL, Colors.MP_BG)

        # 데미지/힐 팝업 렌더링
        self._render_sidebar_popups(self.sidebar_console)

    def render_messages(self, messages: list) -> None:
        """
        메시지 로그 렌더링

        Args:
            messages: 메시지 리스트
        """
        if not self.message_console:
            return

        self.message_console.clear()

        # 테두리
        self.message_console.draw_frame(
            0, 0,
            self.map_width,
            self.message_height,
            "메시지",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 메시지 표시 (최근 것부터)
        y = 1
        for i, message in enumerate(reversed(messages[-5:])):  # 최근 5개
            self.message_console.print(2, y + i, message, fg=Colors.UI_TEXT)

    def _render_bar(
        self,
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        fg_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
        bar_key: str = ""
    ) -> None:
        """
        애니메이션 바(HP/MP) 렌더링 - 트레일 + 숫자 애니메이션

        Args:
            console: 대상 콘솔
            x, y: 위치
            width: 바 너비
            current: 현재 실제 값
            maximum: 최대 값
            fg_color: 전경색
            bg_color: 배경색
            bar_key: 애니메이션 키 ("hp", "mp" 등)
        """
        if maximum <= 0:
            return

        now = time.time()
        anim_duration = 0.6  # 게이지 애니메이션 지속 시간
        trail_duration = 1.0  # 트레일 페이드 시간
        trail_delay = 0.3  # 트레일 시작 전 대기

        # 애니메이션 상태 초기화 / 업데이트
        if bar_key and bar_key not in self._sidebar_anim:
            self._sidebar_anim[bar_key] = {
                "display": float(current),  # 게이지 표시 값 (부드럽게 이동)
                "trail": float(current),    # 트레일 값 (뒤따라감)
                "target": float(current),
                "display_num": float(current),  # 숫자 표시 값
                "move_start": now,
                "trail_start": now,
                "prev_target": float(current),
            }

        if bar_key and bar_key in self._sidebar_anim:
            a = self._sidebar_anim[bar_key]

            # 값 변화 감지 → 애니메이션 시작
            if float(current) != a["target"]:
                a["prev_target"] = a["display"]  # 현재 표시 위치에서 시작
                a["target"] = float(current)
                a["move_start"] = now
                a["trail_start"] = now + trail_delay  # 트레일은 잠시 후 시작

                # 팝업 생성
                diff = current - int(a["prev_target"])
                if diff != 0 and bar_key == "hp":
                    popup_color = (100, 255, 100) if diff > 0 else (255, 80, 80)
                    popup_text = f"+{diff}" if diff > 0 else str(diff)
                    self._sidebar_popups.append({
                        "text": popup_text, "x": x + width // 2, "y": y - 1,
                        "start": now, "color": popup_color, "duration": 1.2
                    })

            # 게이지 부드러운 이동 (ease-out cubic)
            elapsed = now - a["move_start"]
            if elapsed < anim_duration:
                t = elapsed / anim_duration
                t = 1 - (1 - t) ** 3
                a["display"] = a["prev_target"] + (a["target"] - a["prev_target"]) * t
            else:
                a["display"] = a["target"]

            # 트레일 (지연 후 빠르게 따라감)
            if now >= a["trail_start"]:
                trail_elapsed = now - a["trail_start"]
                if trail_elapsed < trail_duration:
                    tt = trail_elapsed / trail_duration
                    tt = 1 - (1 - tt) ** 2
                    # prev_target → target으로 따라감
                    a["trail"] = a["prev_target"] + (a["target"] - a["prev_target"]) * tt
                else:
                    a["trail"] = a["target"]

            # 숫자 부드럽게 이동
            num_diff = current - a["display_num"]
            if abs(num_diff) < 1:
                a["display_num"] = float(current)
            else:
                speed = max(1.0, abs(num_diff) * 0.15)
                if num_diff > 0:
                    a["display_num"] = min(float(current), a["display_num"] + speed)
                else:
                    a["display_num"] = max(float(current), a["display_num"] - speed)

            display_val = a["display"]
            trail_val = a["trail"]
            display_num = int(a["display_num"])
        else:
            display_val = float(current)
            trail_val = float(current)
            display_num = current

        # 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 트레일 렌더링 (데미지: 빨간 잔상 / 힐: 밝은 잔상)
        if bar_key and trail_val != display_val:
            low = min(display_val, trail_val)
            high = max(display_val, trail_val)
            trail_start_w = int((low / maximum) * width)
            trail_end_w = int((high / maximum) * width)
            trail_w = trail_end_w - trail_start_w
            if trail_w > 0:
                if display_val < trail_val:
                    # 데미지: 빨간 트레일
                    trail_color = (200, 60, 60)
                else:
                    # 힐: 밝은 초록 트레일
                    trail_color = (100, 255, 130)
                console.draw_rect(x + trail_start_w, y, trail_w, 1, ord(" "), bg=trail_color)

        # 현재 게이지
        filled_width = int((display_val / maximum) * width)
        if filled_width > 0:
            console.draw_rect(x, y, filled_width, 1, ord(" "), bg=fg_color)

        # 텍스트 (애니메이션 숫자)
        text = f"{display_num}/{maximum}"
        text_x = x + (width - len(text)) // 2
        console.print(text_x, y, text, fg=Colors.WHITE)

    def _render_sidebar_popups(self, console: tcod.console.Console) -> None:
        """사이드바 데미지/힐 팝업 렌더링"""
        now = time.time()
        alive = []
        for popup in self._sidebar_popups:
            elapsed = now - popup["start"]
            if elapsed >= popup["duration"]:
                continue
            alive.append(popup)
            # 위로 떠오르는 효과
            rise = int(elapsed * 2.0)  # 초당 2칸 상승
            py = popup["y"] - rise
            if py < 0:
                continue
            # 페이드: 시간이 지날수록 어두워짐
            progress = elapsed / popup["duration"]
            r, g, b = popup["color"]
            fade = max(0.0, 1.0 - progress)
            color = (int(r * fade), int(g * fade), int(b * fade))
            px = max(1, popup["x"] - len(popup["text"]) // 2)
            console.print(px, py, popup["text"], fg=color)
        self._sidebar_popups = alive

    def compose(self) -> None:
        """모든 서브 콘솔을 메인 콘솔에 합성"""
        if not self.console:
            return

        # 맵 렌더링
        if self.map_console:
            self.map_console.blit(self.console, dest_x=0, dest_y=0)

        # 사이드바 렌더링
        if self.sidebar_console:
            self.sidebar_console.blit(self.console, dest_x=self.map_width, dest_y=0)

        # 메시지 로그 렌더링
        if self.message_console:
            self.message_console.blit(
                self.console,
                dest_x=0,
                dest_y=self.map_height
            )

    def present(self) -> None:
        """화면에 표시"""
        if self.context and self.console:
            # 창 크기 변경 이벤트 처리
            self._handle_window_resize_events()
            
            # 종횡비 유지하며 렌더링 (화면을 늘리지 않고 검은색 띠로 채움)
            # keep_aspect=True: 콘솔 종횡비 유지, 남는 공간은 검은색 배경
            # integer_scaling=False: 부드러운 스케일링 허용
            self.context.present(
                self.console, 
                keep_aspect=self.keep_aspect, 
                integer_scaling=False
            )
            
            # 백업: 주기적으로 종횡비 확인 (덜 자주)
            self._aspect_ratio_check_counter += 1
            if self._aspect_ratio_check_counter >= 60:  # 1초마다 (60fps 기준)
                self._set_aspect_ratio_constraint()
                self._aspect_ratio_check_counter = 0
    
    def _get_display_aspect_ratio(self) -> Optional[float]:
        """현재 디스플레이의 종횡비 가져오기"""
        try:
            if platform.system() == "Windows":
                try:
                    import ctypes
                    # Windows API 사용
                    user32 = ctypes.windll.user32
                    width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                    height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                    
                    if width > 0 and height > 0:
                        aspect_ratio = width / height
                        self.logger.info(f"Windows: 디스플레이 해상도 {width}x{height}, 종횡비 {aspect_ratio:.4f}")
                        return aspect_ratio
                except Exception as e:
                    self.logger.debug(f"Windows 디스플레이 종횡비 가져오기 실패: {e}")
            
            elif platform.system() == "Linux":
                try:
                    import subprocess
                    # xrandr 사용
                    result = subprocess.run(
                        ["xrandr", "--current"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if '*' in line:  # 현재 해상도 (별표 표시)
                                # 예: "   1920x1080      60.00*"
                                parts = line.split()
                                for part in parts:
                                    if 'x' in part and '*' in part:
                                        res = part.replace('*', '')
                                        width, height = map(int, res.split('x'))
                                        if width > 0 and height > 0:
                                            aspect_ratio = width / height
                                            self.logger.info(f"Linux: 디스플레이 해상도 {width}x{height}, 종횡비 {aspect_ratio:.4f}")
                                            return aspect_ratio
                except Exception as e:
                    self.logger.debug(f"Linux 디스플레이 종횡비 가져오기 실패: {e}")
            
            elif platform.system() == "Darwin":  # macOS
                try:
                    import subprocess
                    # system_profiler 사용
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        # 해상도 정보 파싱
                        for line in result.stdout.split('\n'):
                            if 'Resolution:' in line or 'UI Looks like:' in line:
                                # 예: "Resolution: 2560 x 1440 @ 60 Hz"
                                import re
                                match = re.search(r'(\d+)\s*x\s*(\d+)', line)
                                if match:
                                    width, height = int(match.group(1)), int(match.group(2))
                                    if width > 0 and height > 0:
                                        aspect_ratio = width / height
                                        self.logger.info(f"macOS: 디스플레이 해상도 {width}x{height}, 종횡비 {aspect_ratio:.4f}")
                                        return aspect_ratio
                except Exception as e:
                    self.logger.debug(f"macOS 디스플레이 종횡비 가져오기 실패: {e}")
            
            # 폴백: tkinter 사용 (더 호환성이 높음)
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()  # 창 표시 안 함
                width = root.winfo_screenwidth()
                height = root.winfo_screenheight()
                root.destroy()
                
                if width > 0 and height > 0:
                    aspect_ratio = width / height
                    self.logger.info(f"tkinter: 디스플레이 해상도 {width}x{height}, 종횡비 {aspect_ratio:.4f}")
                    return aspect_ratio
            except Exception as e:
                self.logger.debug(f"tkinter 디스플레이 종횡비 가져오기 실패: {e}")
        
        except Exception as e:
            self.logger.debug(f"디스플레이 종횡비 가져오기 실패: {e}")
        
        return None
    
    def _float_to_ratio(self, value: float, max_denominator: int = 100) -> Tuple[int, int]:
        """부동소수점 종횡비를 정수 비율로 변환 (예: 1.777... -> 16:9)"""
        from fractions import Fraction
        
        # Fraction을 사용하여 근사값 찾기
        fraction = Fraction(value).limit_denominator(max_denominator)
        return fraction.numerator, fraction.denominator
    
    def _set_aspect_ratio_constraint(self, aspect_ratio: Optional[float] = None) -> None:
        """SDL 창에 종횡비 제약 설정 - SDL_SetWindowAspectRatio 사용"""
        if not self.context:
            return
        
        # 종횡비 가져오기
        if aspect_ratio is None:
            if hasattr(self, '_aspect_ratio'):
                aspect_ratio = self._aspect_ratio
            else:
                return
        
        if not aspect_ratio or aspect_ratio <= 0:
            return
        
        try:
            import ctypes
            import sys
            
            # SDL2 라이브러리 로드
            try:
                if sys.platform == "win32":
                    sdl2 = ctypes.CDLL("SDL2.dll")
                elif sys.platform == "darwin":
                    sdl2 = ctypes.CDLL("libSDL2.dylib")
                else:
                    sdl2 = ctypes.CDLL("libSDL2.so")
            except OSError:
                # SDL2를 찾을 수 없으면 tcod.lib를 통해 시도
                try:
                    import tcod.lib
                    if hasattr(tcod.lib, 'SDL_SetWindowAspectRatio'):
                        window_p = self._get_sdl_window_pointer()
                        if window_p:
                            numerator, denominator = self._float_to_ratio(aspect_ratio)
                            tcod.lib.SDL_SetWindowAspectRatio(window_p, numerator, denominator)
                except:
                    pass
                return
            
            # SDL_SetWindowAspectRatio 함수 타입 지정
            sdl2.SDL_SetWindowAspectRatio.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            sdl2.SDL_SetWindowAspectRatio.restype = None
            
            # SDL 창 포인터 가져오기
            window_ptr = self._get_sdl_window_pointer()
            if not window_ptr:
                return
            
            # 포인터를 ctypes.c_void_p로 변환
            if isinstance(window_ptr, int):
                window_void_p = ctypes.c_void_p(window_ptr)
            else:
                # 이미 포인터인 경우
                window_void_p = ctypes.c_void_p(int(window_ptr))
            
            # 종횡비 설정 (SDL 2.0.5+ 필요)
            # 종횡비를 정수 비율로 변환 (예: 1.777... -> 16:9)
            numerator, denominator = self._float_to_ratio(aspect_ratio)
            
            try:
                sdl2.SDL_SetWindowAspectRatio(window_void_p, numerator, denominator)
                # 성공적으로 설정되었는지 로그는 처음 한 번만
                if not hasattr(self, '_aspect_ratio_set_logged'):
                    self.logger.info(
                        f"SDL_SetWindowAspectRatio로 종횡비 {aspect_ratio:.4f} "
                        f"({numerator}:{denominator}) 고정 활성화"
                    )
                    self._aspect_ratio_set_logged = True
            except Exception as e:
                if not hasattr(self, '_aspect_ratio_set_error_logged'):
                    self.logger.warning(f"SDL_SetWindowAspectRatio 호출 실패: {e}")
                    self._aspect_ratio_set_error_logged = True
            
        except (AttributeError, ImportError, Exception) as e:
            # 첫 번째 오류만 로그
            if not hasattr(self, '_aspect_ratio_constraint_error_logged'):
                self.logger.debug(f"SDL 창 종횡비 제약 설정 실패: {e}")
                self._aspect_ratio_constraint_error_logged = True
    
    def _get_sdl_window_pointer(self) -> Optional[int]:
        """SDL 창 포인터 가져오기 (여러 방법 시도) - OpenGL2 렌더러도 지원"""
        if not self.context:
            self.logger.warning("context가 None입니다")
            return None
        
        self.logger.info(f"context 타입: {type(self.context)}")
        self.logger.info(f"sdl_window_p 존재: {hasattr(self.context, 'sdl_window_p')}")
        
        try:
            # 방법 0: context.sdl_window_p 직접 사용
            window_p = self.context.sdl_window_p
            
            if window_p is None:
                self.logger.info("sdl_window_p가 None입니다")
                return None
            
            # CData 포인터 문자열에서 주소 추출
            # 형식: <cdata 'struct SDL_Window *' 0x0000019820DC7A40>
            ptr_str = str(window_p)
            self.logger.info(f"sdl_window_p 문자열: {ptr_str}")
            
            # NULL 포인터 체크 (정확히 0x0 또는 0x0000000000000000만)
            if 'NULL' in ptr_str:
                self.logger.info("sdl_window_p가 NULL입니다")
                return None
            
            # 16진수 주소 추출
            import re
            match = re.search(r'0x([0-9a-fA-F]+)', ptr_str)
            if match:
                ptr_int = int(match.group(0), 16)
                self.logger.info(f"추출된 포인터 주소: {ptr_int} (0x{ptr_int:X})")
                if ptr_int > 0:
                    return ptr_int
            
            self.logger.warning(f"포인터 주소를 추출할 수 없습니다: {ptr_str}")
            
        except Exception as e:
            self.logger.warning(f"SDL 창 포인터 가져오기 시도 중 오류: {e}")
        
        return None
    
    def _float_to_ratio(self, value: float, max_denominator: int = 100) -> Tuple[int, int]:
        """부동소수점 종횡비를 정수 비율로 변환 (예: 1.777... -> 16:9)"""
        from fractions import Fraction
        
        # Fraction을 사용하여 근사값 찾기
        fraction = Fraction(value).limit_denominator(max_denominator)
        return fraction.numerator, fraction.denominator
    
    def _handle_window_resize_events(self) -> None:
        """창 크기 변경 시 모니터 종횡비 유지 (검은색 띠 유지)"""
        if not self.context or not hasattr(self, '_aspect_ratio'):
            return
        
        try:
            # 이벤트 큐에서 창 크기 변경 이벤트 확인
            for event in tcod.event.get():
                if isinstance(event, tcod.event.WindowResized):
                    # 창 크기 변경 이벤트 발생 시 모니터 종횡비 강제 조정
                    new_width = event.width
                    new_height = event.height
                    
                    if new_height <= 0:
                        continue
                    
                    # 현재 종횡비 계산
                    current_aspect = new_width / new_height
                    
                    # 종횡비가 다르면 조정 (임계값: 0.02)
                    if abs(current_aspect - self._aspect_ratio) > 0.02:
                        # 모니터 종횡비에 맞춰 크기 계산
                        # 더 많이 변경된 축을 기준으로 계산
                        expected_width = int(new_height * self._aspect_ratio)
                        expected_height = int(new_width / self._aspect_ratio)
                        
                        width_diff = abs(new_width - expected_width)
                        height_diff = abs(new_height - expected_height)
                        
                        if width_diff > height_diff:
                            # 높이 기준으로 너비 조정
                            adjusted_width = int(new_height * self._aspect_ratio)
                            adjusted_height = new_height
                        else:
                            # 너비 기준으로 높이 조정
                            adjusted_width = new_width
                            adjusted_height = int(new_width / self._aspect_ratio)
                        
                        # 창 크기 조정 (SDL 직접 호출)
                        # 콘솔은 중앙에 배치되고 검은색 띠가 자동으로 생성됨
                        self._set_window_size_direct(adjusted_width, adjusted_height)
                        self._last_window_size = (adjusted_width, adjusted_height)
                    else:
                        self._last_window_size = (new_width, new_height)
                        
        except (AttributeError, ImportError, Exception) as e:
            # 오류 발생 시 무시
            pass
    
    def _enforce_aspect_ratio(self) -> None:
        """종횡비 강제 확인 (백업 메커니즘)"""
        if not self.context or not hasattr(self, '_aspect_ratio'):
            return
        
        try:
            import tcod.lib
            
            # SDL 창 포인터 가져오기
            window_p = None
            if hasattr(self.context, 'sdl_window_p'):
                window_p = self.context.sdl_window_p
            elif hasattr(self.context, '_sdl_window_p'):
                window_p = self.context._sdl_window_p
            
            if not window_p or not hasattr(tcod.lib, 'ffi'):
                return
            
            ffi = tcod.lib.ffi
            
            # 현재 창 크기 가져오기
            width_ptr = ffi.new("int*")
            height_ptr = ffi.new("int*")
            
            if not hasattr(tcod.lib, 'SDL_GetWindowSize'):
                return
                
            tcod.lib.SDL_GetWindowSize(window_p, width_ptr, height_ptr)
            
            current_width = width_ptr[0]
            current_height = height_ptr[0]
            
            if current_height <= 0:
                return
            
            # 현재 크기가 마지막 저장된 크기와 같으면 스킵
            current_size = (current_width, current_height)
            if self._last_window_size == current_size:
                return
            
            # 현재 종횡비 계산
            current_aspect = current_width / current_height
            
            # 종횡비가 다르면 조정 (임계값: 0.02)
            if abs(current_aspect - self._aspect_ratio) > 0.02:
                # 종횡비에 맞춰 크기 계산
                expected_width = int(current_height * self._aspect_ratio)
                expected_height = int(current_width / self._aspect_ratio)
                
                width_diff = abs(current_width - expected_width)
                height_diff = abs(current_height - expected_height)
                
                if width_diff > height_diff:
                    # 높이 기준으로 너비 조정
                    adjusted_width = int(current_height * self._aspect_ratio)
                    adjusted_height = current_height
                else:
                    # 너비 기준으로 높이 조정
                    adjusted_width = current_width
                    adjusted_height = int(current_width / self._aspect_ratio)
                
                # 창 크기 조정
                if hasattr(tcod.lib, 'SDL_SetWindowSize'):
                    tcod.lib.SDL_SetWindowSize(window_p, adjusted_width, adjusted_height)
                    self._last_window_size = (adjusted_width, adjusted_height)
            else:
                self._last_window_size = current_size
                
        except (AttributeError, ImportError, Exception):
            # 오류 발생 시 무시
            pass
    
    def _set_window_size_direct(self, width: int, height: int) -> None:
        """SDL을 통해 창 크기 직접 설정 (종횡비 유지용)"""
        try:
            import tcod.lib
            
            # SDL 창 포인터 가져오기
            window_p = None
            if hasattr(self.context, 'sdl_window_p'):
                window_p = self.context.sdl_window_p
            elif hasattr(self.context, 'sdl_window'):
                window_p = self.context.sdl_window
            elif hasattr(self.context, '_sdl_window_p'):
                window_p = self.context._sdl_window_p
            
            if not window_p:
                return
            
            # 창 크기 설정
            if hasattr(tcod.lib, 'SDL_SetWindowSize') and hasattr(tcod.lib, 'ffi'):
                tcod.lib.SDL_SetWindowSize(window_p, width, height)
        except (AttributeError, ImportError, Exception):
            pass
    
    def _load_sdl2(self):
        """SDL2 라이브러리 로드"""
        import ctypes
        
        if sys.platform == "win32":
            # 여러 경로에서 SDL2.dll 찾기
            search_paths = [
                "SDL2.dll",  # 시스템 PATH
            ]
            
            # tcod 패키지 내부 경로 추가
            try:
                import tcod
                tcod_path = Path(tcod.__file__).parent
                search_paths.extend([
                    str(tcod_path / "SDL2.dll"),
                    str(tcod_path / "lib" / "SDL2.dll"),
                    str(tcod_path / "_libtcod.pyd"),  # tcod가 SDL을 내장하고 있을 수 있음
                ])
            except:
                pass
            
            for path in search_paths:
                try:
                    return ctypes.CDLL(path)
                except OSError:
                    continue
            
            self.logger.warning("SDL2.dll을 찾을 수 없습니다")
            return None
        else:
            try:
                return ctypes.CDLL("libSDL2.so")
            except:
                try:
                    return ctypes.CDLL("libSDL2.dylib")
                except:
                    return None
    
    def _get_sdl_window_pointer(self) -> int:
        """SDL 창 포인터를 정수로 변환하여 반환"""
        if not self.context:
            return None
        
        try:
            window_p = self.context.sdl_window_p
            if window_p is None:
                return None
            
            # cffi CData 객체에서 정수 포인터 추출
            # 방법 1: ffi.cast를 사용
            try:
                from tcod._libtcod import ffi
                ptr_int = int(ffi.cast("uintptr_t", window_p))
                if ptr_int != 0:
                    self.logger.debug(f"SDL 창 포인터 (ffi.cast): {ptr_int}")
                    return ptr_int
            except Exception as e:
                self.logger.debug(f"ffi.cast 방법 실패: {e}")
            
            # 방법 2: id() 사용 (비표준이지만 작동할 수 있음)
            try:
                # CData 객체의 문자열 표현에서 주소 추출
                ptr_str = str(window_p)
                # '<cdata 'struct SDL_Window *' 0x7f1234567890>' 형식에서 주소 추출
                if '0x' in ptr_str:
                    import re
                    match = re.search(r'0x[0-9a-fA-F]+', ptr_str)
                    if match:
                        ptr_int = int(match.group(), 16)
                        if ptr_int != 0:
                            self.logger.debug(f"SDL 창 포인터 (regex): {ptr_int}")
                            return ptr_int
            except Exception as e:
                self.logger.debug(f"regex 방법 실패: {e}")
            
            return None
            
        except Exception as e:
            self.logger.warning(f"SDL 창 포인터 추출 실패: {e}")
            return None
    
    def _set_exclusive_fullscreen_mode(self) -> None:
        """독점 전체화면 모드 설정 (SDL_WINDOW_FULLSCREEN)"""
        if not self.context:
            self.logger.warning("context가 없어서 전체화면 설정 불가")
            return

        try:
            window_p = self.context.sdl_window_p
            if window_p is None or 'NULL' in str(window_p):
                self.logger.warning("SDL 창 포인터가 NULL입니다")
                return

            import ctypes
            try:
                sdl2 = ctypes.CDLL("SDL2.dll")
            except OSError:
                try:
                    sdl2 = ctypes.cdll.LoadLibrary("libSDL2.so")
                except OSError:
                    sdl2 = ctypes.cdll.LoadLibrary("libSDL2.dylib")

            window_ptr = ctypes.cast(int(self.context.sdl_window_p), ctypes.c_void_p)

            # SDL_WINDOW_FULLSCREEN = 0x00000001 (독점 전체화면)
            sdl2.SDL_SetWindowFullscreen.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            sdl2.SDL_SetWindowFullscreen.restype = ctypes.c_int
            result = sdl2.SDL_SetWindowFullscreen(window_ptr, 0x00000001)

            if result == 0:
                self.logger.info("독점 전체화면 모드 설정 완료")
            else:
                self.logger.warning(f"독점 전체화면 설정 실패 (SDL 반환값: {result}), borderless fallback")
                self._set_fullscreen_desktop_mode()
        except Exception as e:
            self.logger.warning(f"독점 전체화면 설정 실패: {e}, borderless fallback")
            self._set_fullscreen_desktop_mode()

    def _set_fullscreen_desktop_mode(self) -> None:
        """테두리 없는 전체 화면 모드 설정 (Windows/Linux/macOS 지원)"""
        if not self.context:
            self.logger.warning("context가 없어서 전체 화면 설정 불가")
            return
        
        try:
            # context.sdl_window_p는 cffi CData 객체
            window_p = self.context.sdl_window_p
            
            if window_p is None or 'NULL' in str(window_p):
                self.logger.warning("SDL 창 포인터가 NULL입니다")
                return
            
            self.logger.info(f"SDL 창 포인터: {window_p}, 플랫폼: {platform.system()}")
            
            # 리눅스/macOS에서는 ctypes로 직접 SDL2 호출
            if platform.system() in ("Linux", "Darwin"):
                try:
                    import ctypes
                    
                    # 플랫폼별 SDL2 라이브러리 로드
                    sdl2 = None
                    if platform.system() == "Linux":
                        # 리눅스: 여러 경로 시도
                        lib_names = ["libSDL2-2.0.so.0", "libSDL2-2.0.so", "libSDL2.so"]
                        for lib_name in lib_names:
                            try:
                                sdl2 = ctypes.CDLL(lib_name)
                                self.logger.info(f"SDL2 로드 성공: {lib_name}")
                                break
                            except OSError:
                                continue
                    else:  # Darwin (macOS)
                        try:
                            sdl2 = ctypes.CDLL("libSDL2.dylib")
                        except OSError:
                            # Homebrew 경로
                            try:
                                sdl2 = ctypes.CDLL("/usr/local/lib/libSDL2.dylib")
                            except OSError:
                                pass
                    
                    if sdl2:
                        # SDL 창 포인터를 정수로 변환
                        ptr_int = self._get_sdl_window_pointer()
                        if ptr_int:
                            window_ptr = ctypes.c_void_p(ptr_int)
                            
                            # SDL_SetWindowFullscreen(window, SDL_WINDOW_FULLSCREEN_DESKTOP)
                            # SDL_WINDOW_FULLSCREEN_DESKTOP = 0x00001001
                            sdl2.SDL_SetWindowFullscreen.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                            sdl2.SDL_SetWindowFullscreen.restype = ctypes.c_int
                            
                            result = sdl2.SDL_SetWindowFullscreen(window_ptr, 0x00001001)
                            
                            if result == 0:
                                self.logger.info("테두리 없는 전체 화면 모드 활성화 완료 (ctypes)")
                                return
                            else:
                                self.logger.warning(f"SDL_SetWindowFullscreen 반환값: {result}")
                                
                                # 폴백: 테두리 없는 창 + 창 크기/위치 설정
                                try:
                                    sdl2.SDL_SetWindowBordered.argtypes = [ctypes.c_void_p, ctypes.c_int]
                                    sdl2.SDL_SetWindowBordered(window_ptr, 0)  # SDL_FALSE
                                    
                                    sdl2.SDL_SetWindowSize.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
                                    sdl2.SDL_SetWindowSize(window_ptr, self.pixel_width, self.pixel_height)
                                    
                                    sdl2.SDL_SetWindowPosition.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
                                    sdl2.SDL_SetWindowPosition(window_ptr, 0, 0)
                                    
                                    self.logger.info(f"테두리 없는 전체 창 모드 활성화 완료 ({self.pixel_width}x{self.pixel_height})")
                                    return
                                except Exception as e:
                                    self.logger.warning(f"폴백 모드 실패: {e}")
                    else:
                        self.logger.warning("SDL2 라이브러리를 로드할 수 없습니다")
                except Exception as e:
                    self.logger.warning(f"ctypes SDL2 호출 실패: {e}")
            
            # Windows 또는 위 방법 실패 시: tcod의 내부 ffi와 lib 사용
            try:
                from tcod._libtcod import ffi, lib
                
                # SDL_SetWindowFullscreen 시도
                # SDL_WINDOW_FULLSCREEN_DESKTOP = 0x1001
                result = lib.SDL_SetWindowFullscreen(window_p, 0x1001)
                
                if result == 0:
                    self.logger.info("테두리 없는 전체 화면 모드 활성화 완료")
                    return
                else:
                    error = ffi.string(lib.SDL_GetError()).decode('utf-8', errors='ignore')
                    self.logger.warning(f"SDL_SetWindowFullscreen 실패: {error}")
                    
            except ImportError:
                self.logger.info("tcod._libtcod를 가져올 수 없습니다. 대체 방법 시도...")
            except Exception as e:
                self.logger.warning(f"SDL_SetWindowFullscreen 실패: {e}")
            
            # 최종 폴백: SDL_SetWindowBordered + SDL_SetWindowSize + SDL_SetWindowPosition
            try:
                from tcod._libtcod import lib
                
                # 테두리 제거
                lib.SDL_SetWindowBordered(window_p, 0)  # SDL_FALSE = 0
                
                # 창 크기를 화면 전체로
                lib.SDL_SetWindowSize(window_p, self.pixel_width, self.pixel_height)
                
                # 위치를 (0, 0)으로
                lib.SDL_SetWindowPosition(window_p, 0, 0)
                
                self.logger.info(f"테두리 없는 전체 창 모드 활성화 완료 ({self.pixel_width}x{self.pixel_height})")
                return
                
            except ImportError:
                self.logger.warning("tcod._libtcod를 가져올 수 없습니다")
            except Exception as e:
                self.logger.warning(f"폴백 모드 실패: {e}")
                    
        except Exception as e:
            self.logger.warning(f"전체 화면 모드 설정 실패: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def _set_borderless_mode(self) -> None:
        """테두리 없는 창 모드 설정 (SDL_SetWindowBordered)"""
        if not self.context:
            return
        
        try:
            import ctypes
            
            if sys.platform == "win32":
                try:
                    sdl2 = ctypes.CDLL("SDL2.dll")
                except OSError:
                    import tcod
                    tcod_path = Path(tcod.__file__).parent
                    sdl2_path = tcod_path / "SDL2.dll"
                    if sdl2_path.exists():
                        sdl2 = ctypes.CDLL(str(sdl2_path))
                    else:
                        return
                
                window_p = self._get_sdl_window_pointer()
                if window_p:
                    window_ptr = ctypes.c_void_p(window_p if isinstance(window_p, int) else int(window_p))
                    
                    # SDL_SetWindowBordered(window, SDL_FALSE)
                    sdl2.SDL_SetWindowBordered.argtypes = [ctypes.c_void_p, ctypes.c_int]
                    sdl2.SDL_SetWindowBordered(window_ptr, 0)  # SDL_FALSE = 0
                    
                    # 창 크기와 위치 설정
                    sdl2.SDL_SetWindowSize(window_ptr, self.pixel_width, self.pixel_height)
                    sdl2.SDL_SetWindowPosition(window_ptr, 0, 0)
                    
                    self.logger.info("테두리 없는 창 모드 활성화 완료")
                    
        except Exception as e:
            self.logger.warning(f"테두리 없는 창 모드 설정 실패: {e}")

    def _set_initial_window_size(self) -> None:
        """초기 창 크기를 설정된 pixel_width x pixel_height로 설정 (기본 1920x1080)"""
        if not self.context:
            return
        
        try:
            # SDL 창 포인터 가져오기
            window_p = self._get_sdl_window_pointer()
            
            # 방법 1: ctypes로 직접 SDL2 호출 (더 안정적)
            try:
                import ctypes
                
                # SDL2 라이브러리 로드
                if sys.platform == "win32":
                    try:
                        sdl2 = ctypes.CDLL("SDL2.dll")
                    except OSError:
                        # tcod 패키지 내부의 SDL2 찾기
                        import tcod
                        tcod_path = Path(tcod.__file__).parent
                        sdl2_path = tcod_path / "SDL2.dll"
                        if sdl2_path.exists():
                            sdl2 = ctypes.CDLL(str(sdl2_path))
                        else:
                            raise OSError("SDL2.dll not found")
                    
                    if window_p:
                        window_ptr = ctypes.c_void_p(window_p if isinstance(window_p, int) else int(window_p))
                        
                        # 창 크기 설정
                        sdl2.SDL_SetWindowSize(window_ptr, self.pixel_width, self.pixel_height)
                        self._last_window_size = (self.pixel_width, self.pixel_height)
                        self.logger.info(f"초기 창 크기 설정: {self.pixel_width}x{self.pixel_height}")
                        
                        # 테두리 없는 전체 창이면 창 위치를 (0, 0)으로 설정
                        if self.borderless_fullscreen:
                            sdl2.SDL_SetWindowPosition(window_ptr, 0, 0)
                            self.logger.info("테두리 없는 전체 창: 위치 (0, 0) 설정")
                        return
                        
            except Exception as e:
                self.logger.debug(f"ctypes SDL2 호출 실패: {e}")
            
            # 방법 2: tcod.lib 사용 (폴백)
            if window_p:
                import tcod.lib
                
                # 창 크기 설정
                if hasattr(tcod.lib, 'SDL_SetWindowSize'):
                    tcod.lib.SDL_SetWindowSize(window_p, self.pixel_width, self.pixel_height)
                    self._last_window_size = (self.pixel_width, self.pixel_height)
                    self.logger.info(f"초기 창 크기 설정 (tcod.lib): {self.pixel_width}x{self.pixel_height}")
                
                # 테두리 없는 전체 창이면 창 위치를 (0, 0)으로 설정
                if self.borderless_fullscreen and hasattr(tcod.lib, 'SDL_SetWindowPosition'):
                    tcod.lib.SDL_SetWindowPosition(window_p, 0, 0)
                    self.logger.info("테두리 없는 전체 창: 위치 (0, 0) 설정")
                
        except (AttributeError, ImportError, Exception) as e:
            self.logger.debug(f"초기 창 크기 설정 실패: {e}")

    def close(self) -> None:
        """TCOD 종료"""
        if self.context:
            self.context.close()
        self.logger.info("TCOD 종료")


# ── 렌더링 백엔드 선택 ──
# "pygame": pygame-ce 렌더러 (Cogmind급 비주얼)
# "raylib": raylib 렌더러 (Phase 1)
# "tcod":   기존 tcod 렌더러
_BACKEND = "pygame"
_USE_PYGAME = True  # 하위 호환

# 전역 인스턴스
_display: Optional[TCODDisplay] = None


def get_display():
    """전역 디스플레이 인스턴스

    config.yaml의 display.backend 설정에 따라 백엔드 선택.
    "raylib" → RaylibDisplay, "pygame" → PygameDisplay, "tcod" → TCODDisplay.
    세 클래스 모두 동일한 공개 API를 제공.
    """
    global _display
    if _display is None:
        try:
            from src.core.config import get_config
            backend = get_config().get("display.backend", _BACKEND)
        except Exception:
            backend = _BACKEND

        if backend == "raylib":
            from src.ui.raylib_backend.raylib_display import RaylibDisplay
            _display = RaylibDisplay()
        elif backend == "pygame" or _USE_PYGAME:
            from src.ui.pygame_backend.pygame_display import PygameDisplay
            _display = PygameDisplay()
        else:
            _display = TCODDisplay()
    return _display


def render_space_background(
    console: tcod.console.Console, 
    width: int, 
    height: int,
    context: str = "default",
    floor: int = 1,
    dungeon: Optional[Any] = None,
    combat_position: Optional[Tuple[int, int]] = None
) -> None:
    """
    바이옴/상황별 그라데이션 배경 렌더링
    
    Args:
        console: 렌더링할 콘솔
        width: 콘솔 너비
        height: 콘솔 높이
        context: 상황 ("town", "dungeon", "combat", "menu", "default")
        floor: 던전 층 번호 (바이옴 계산용)
    """
    # 바이옴별 그라데이션 색상 정의 (상단 → 하단)
    # BGM 테마에 맞춰 조정 + 전체적으로 어둡고 부드러운 색조
    biome_gradients = {
        # biome_0: forest (숲) - 짙은 초록 (1층 초록 숲)
        0: {
            "top": (5, 12, 8),         # 깊은 초록
            "bottom": (10, 22, 15)     # 어두운 숲 초록
        },
        # biome_1: 
        1: {
            "top": (5, 12, 8),         # 깊은 초록
            "bottom": (10, 22, 15)     # 어두운 숲 초록
        },
        # biome_2: devillands (악마의 땅) - 어두운 빨강/검정
        2: {
            "top": (20, 5, 5),         # 어두운 핏빛
            "bottom": (30, 8, 8)       # 짙은 빨강
        },
        # biome_3: badlands (황무지) - 회갈색
        3: {
            "top": (12, 10, 8),        # 어두운 갈색
            "bottom": (22, 18, 12)     # 황무지 갈색
        },
        # biome_4: desert (사막) - 어두운 모래색
        4: {
            "top": (18, 15, 10),       # 어두운 황토색
            "bottom": (28, 22, 15)     # 사막 모래색
        },
        # biome_5: frostlands (서리의 땅) - 차가운 청록
        5: {
            "top": (8, 12, 15),        # 깊은 청록
            "bottom": (15, 22, 28)     # 얼음 청록
        },
        # biome_6: highlands (고원) - 회색/녹색
        6: {
            "top": (10, 12, 10),       # 어두운 회녹색
            "bottom": (18, 20, 18)     # 고원 녹회색
        },
        # biome_7: icelands (얼음의 땅) - 차가운 파랑/흰색
        7: {
            "top": (10, 15, 20),       # 깊은 한랭색
            "bottom": (18, 25, 32)     # 얼음 파랑
        },
        # biome_8: warlands (전쟁터) - 어두운 주황/회색
        8: {
            "top": (20, 12, 8),        # 어두운 전쟁 주황
            "bottom": (28, 18, 12)     # 황폐한 주황갈색
        },
        # biome_9: caves (동굴) - 어두운 회색 버전 (10층)
        9: {
            "top": (12, 12, 16),       # 어두운 회색
            "bottom": (20, 18, 22)     # 조금 더 밝은 회색
        }
    }
    
    # 상황별 색상 (더 부드럽게 조정)
    context_gradients = {
        "town": {  # 마을 - 어두운 핑크 그라데이션
            "top": (25, 12, 18),       # 어두운 핑크
            "bottom": (45, 20, 30)     # 조금 더 밝은 핑크
        },
        "combat": {  # 전투 - 기본 검정/진한 남색
            "top": (5, 5, 10),
            "bottom": (10, 10, 20)
        },
        "menu": {  # 메뉴 - 우주 테마 (부드러운 파랑)
            "top": (8, 8, 15),
            "bottom": (15, 12, 25)
        },
        "default": {  # 기본
            "top": (8, 8, 15),
            "bottom": (15, 12, 22)
        }
    }
    
    # 상황에 따라 그라데이션 선택
    if context == "dungeon":
        # 던전: 바이옴 인덱스 계산 (층별)
        biome_index = (floor - 1) % 10
        gradient = biome_gradients.get(biome_index, biome_gradients[0])
    elif context in context_gradients:
        gradient = context_gradients[context]
    else:
        gradient = context_gradients["default"]
    
    # 전투 컨텍스트일 때 필드 효과에 따라 색상 변경
    if context == "combat" and dungeon and combat_position:
        effects = []
        # 환경 효과 관리자 확인 (두 가지 속성명 모두 지원)
        effect_manager = None
        if hasattr(dungeon, 'environmental_effect_manager'):
            effect_manager = dungeon.environmental_effect_manager
        elif hasattr(dungeon, 'environment_effect_manager'):
            effect_manager = dungeon.environment_effect_manager
        
        if effect_manager:
            effects = effect_manager.get_effects_at_tile(combat_position[0], combat_position[1])
        
        # 가장 강한 효과의 색상으로 배경 변경
        if effects:
            effect = effects[0]
            overlay_color = effect.color_overlay
            
            # 오버레이 색상을 배경 그라데이션에 혼합
            # 기존 그라데이션에 효과 색상을 30% 혼합
            top_color_base = gradient["top"]
            bottom_color_base = gradient["bottom"]
            
            # 오버레이 색상을 약간 어둡게 조정 (배경용)
            overlay_r, overlay_g, overlay_b = overlay_color
            overlay_dark = (
                max(5, overlay_r // 4),
                max(5, overlay_g // 4),
                max(5, overlay_b // 4)
            )
            
            # 혼합 (70% 기본색 + 30% 효과색)
            top_color = (
                int(top_color_base[0] * 0.7 + overlay_dark[0] * 0.3),
                int(top_color_base[1] * 0.7 + overlay_dark[1] * 0.3),
                int(top_color_base[2] * 0.7 + overlay_dark[2] * 0.3)
            )
            bottom_color = (
                int(bottom_color_base[0] * 0.5 + overlay_dark[0] * 0.5),
                int(bottom_color_base[1] * 0.5 + overlay_dark[1] * 0.5),
                int(bottom_color_base[2] * 0.5 + overlay_dark[2] * 0.5)
            )
        else:
            top_color = gradient["top"]
            bottom_color = gradient["bottom"]
    else:
        top_color = gradient["top"]
        bottom_color = gradient["bottom"]
    
    # 실제 콘솔 크기 확인 (안전성을 위해)
    # console 속성 사용 (가장 안전한 방법)
    try:
        actual_console_width = console.width
        actual_console_height = console.height
    except (AttributeError, TypeError):
        # 속성을 가져올 수 없으면 전달된 값 사용
        actual_console_width = width
        actual_console_height = height
    
    # 전달된 크기와 실제 콘솔 크기 중 작은 값 사용 (안전성)
    # 범위를 넘지 않도록 확실히 제한
    actual_width = min(width, actual_console_width)
    actual_height = min(height, actual_console_height)
    
    # 추가 안전성: range를 직접 제한
    actual_width = max(0, min(actual_width, actual_console_width))
    actual_height = max(0, min(actual_height, actual_console_height))
    
    # 그라데이션 렌더링
    # draw_rect를 사용하여 안전하게 렌더링 (범위 체크 자동)
    if actual_height > 0 and actual_width > 0:
        for y in range(actual_height):
            # 범위 체크 (이중 체크)
            if y >= actual_console_height:
                break
            
            # 선형 보간 (0.0 ~ 1.0)
            ratio = y / max(1, actual_height - 1)
            
            # RGB 보간
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
            
            # 클램핑
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            # 배경색 설정 - draw_rect 사용 (범위 자동 체크)
            bg_color = (r, g, b)
            try:
                # 한 줄씩 그리기 (draw_rect가 내부적으로 범위 체크)
                # draw_width도 한 번 더 체크
                draw_width = min(actual_width, actual_console_width - 0)  # x는 0부터 시작
                if draw_width > 0 and y < actual_console_height:
                    console.draw_rect(0, y, draw_width, 1, ord(' '), bg=bg_color)
            except (IndexError, ValueError, TypeError, AttributeError):
                # 범위를 벗어나면 해당 줄 건너뛰기
                continue
