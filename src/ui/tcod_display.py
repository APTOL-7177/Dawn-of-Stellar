"""
TCOD Display - python-tcod 기반 디스플레이 시스템

tcod를 사용한 렌더링 및 UI 관리
"""

import tcod
import tcod.context
import tcod.console
import tcod.event
from typing import Optional, Tuple, Any
from pathlib import Path
import platform
import sys

from src.core.config import get_config
from src.core.logger import get_logger
from src.ui.gauge_tileset import initialize_gauge_tiles


class Colors:
    """색상 정의"""
    # 기본 색상
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    DARK_GRAY = (64, 64, 64)

    # 추가 색상
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    ORANGE = (255, 165, 0)

    # UI 색상
    UI_BG = (20, 20, 30)
    UI_BORDER = (100, 100, 150)
    UI_TEXT = (200, 200, 200)
    UI_TEXT_SELECTED = (255, 255, 100)

    # HP/MP 바
    HP_FULL = (0, 200, 0)
    HP_HALF = (200, 200, 0)
    HP_LOW = (200, 0, 0)
    HP_BG = (100, 0, 0)

    MP_FULL = (0, 100, 200)
    MP_BG = (0, 50, 100)

    # 상처
    WOUND = (150, 50, 50)

    # 맵 색상
    FLOOR = (50, 50, 150)
    WALL = (0, 0, 100)
    PLAYER = (255, 255, 255)
    ENEMY = (255, 0, 0)
    ITEM = (255, 255, 0)


class TCODDisplay:
    """
    TCOD 디스플레이 매니저

    화면 렌더링 및 레이아웃 관리
    """

    def __init__(self) -> None:
        self.logger = get_logger("display")
        self.config = get_config()

        # 화면 크기 (기본값 - 콘솔 크기는 고정)
        self.screen_width = self.config.get("display.screen_width", 80)
        self.screen_height = self.config.get("display.screen_height", 50)
        
        # 현재 디스플레이의 종횡비 가져오기 (창 크기 조정용)
        display_aspect_ratio = self._get_display_aspect_ratio()
        
        if display_aspect_ratio:
            self.logger.info(
                f"콘솔 크기: {self.screen_width}x{self.screen_height}, "
                f"모니터 종횡비: {display_aspect_ratio:.4f} (검은색 띠로 조정)"
            )
        else:
            self.logger.info(
                f"콘솔 크기: {self.screen_width}x{self.screen_height} "
                "(디스플레이 종횡비를 가져올 수 없음)"
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

        self._initialize_tcod()

    def _initialize_tcod(self) -> None:
        """TCOD 초기화"""
        # 한글 지원 TrueType 폰트 로드
        font_size = self.config.get("display.font_size", 32)
        char_spacing_adjust = self.config.get("display.char_spacing_adjust", 2)

        import platform
        import os

        # OS별 시스템 폰트 경로 (한글 지원)
        font_paths = []

        # 프로젝트 루트 경로
        project_root = Path(__file__).parent.parent.parent
        self.logger.info(f"프로젝트 루트: {project_root.absolute()}")

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
                        f"  ✓ 비트맵 폰트 로드 성공: {font_path}\n"
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
                    self.logger.info("  ✓ 게이지 타일셋 초기화 완료")
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
            
            # 디스플레이 종횡비 설정 (창 크기 조정용 - 검은색 띠 생성)
            display_aspect_ratio = self._get_display_aspect_ratio()
            if display_aspect_ratio:
                self._aspect_ratio = display_aspect_ratio
            else:
                # 종횡비를 가져올 수 없으면 콘솔의 종횡비 사용
                self._aspect_ratio = self.screen_width / self.screen_height
            
            # 콘솔 크기와 종횡비 확인
            console_aspect = self.screen_width / self.screen_height
            self.logger.info(
                f"콘솔 크기: {self.screen_width}x{self.screen_height} (고정), "
                f"콘솔 종횡비: {console_aspect:.4f}, "
                f"창 종횡비: {self._aspect_ratio:.4f} (모니터에 맞춤, 검은색 띠 사용)"
            )

            context_kwargs = {
                "columns": self.screen_width,
                "rows": self.screen_height,
                "tileset": self.tileset,
                "title": "Dawn of Stellar - 별빛의 여명",
                "vsync": self.config.get("display.vsync", True),
            }

            if renderer is not None:
                context_kwargs["renderer"] = renderer
                self.logger.info(f"렌더러 사용: {renderer_name}")

            # 콘솔 크기는 고정하고, 창 크기는 모니터 종횡비에 맞춤
            # TCOD는 콘솔을 중앙에 배치하고, 종횡비가 맞지 않으면 검은색 배경으로 띠를 만듦
            try:
                # context 생성
                self.context = tcod.context.new(**context_kwargs)
                
                # 모니터 종횡비에 맞춰 창 크기 조정 (검은색 띠 생성)
                # SDL 종횡비 제약 설정으로 자동으로 띠 생성
                if display_aspect_ratio:
                    self._set_aspect_ratio_constraint(display_aspect_ratio)
                else:
                    # 종횡비를 가져오지 못했어도 콘솔 종횡비로 설정
                    self._set_aspect_ratio_constraint()
                
                self.logger.info(
                    f"창 크기를 모니터 종횡비({self._aspect_ratio:.4f})로 설정 완료. "
                    f"콘솔({self.screen_width}x{self.screen_height})은 중앙에 배치되고 "
                    f"좌우 또는 상하에 검은색 띠가 표시됩니다."
                )
                
            except Exception as e:
                self.logger.warning(f"컨텍스트 생성 중 오류: {e}, 기본 설정 사용")
                try:
                    self.context = tcod.context.new(**context_kwargs)
                except:
                    pass
        else:
            self.context = tcod.context.new_terminal(
                self.screen_width,
                self.screen_height,
                title="Dawn of Stellar - 별빛의 여명",
                vsync=self.config.get("display.vsync", True)
            )

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

            # HP 바
            current_hp = getattr(character, 'current_hp', 100)
            max_hp = getattr(character, 'max_hp', 100)
            self.sidebar_console.print(1, y, "HP:", fg=Colors.UI_TEXT)
            y += 1
            self._render_bar(self.sidebar_console, 1, y, 18, current_hp, max_hp, Colors.HP_FULL, Colors.HP_BG)
            y += 2

            # MP 바
            current_mp = getattr(character, 'current_mp', 50)
            max_mp = getattr(character, 'max_mp', 50)
            self.sidebar_console.print(1, y, "MP:", fg=Colors.UI_TEXT)
            y += 1
            self._render_bar(self.sidebar_console, 1, y, 18, current_mp, max_mp, Colors.MP_FULL, Colors.MP_BG)
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
        bg_color: Tuple[int, int, int]
    ) -> None:
        """
        바(HP/MP) 렌더링

        Args:
            console: 대상 콘솔
            x, y: 위치
            width: 바 너비
            current: 현재 값
            maximum: 최대 값
            fg_color: 전경색
            bg_color: 배경색
        """
        # 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 전경 (현재 값)
        if maximum > 0:
            filled_width = int((current / maximum) * width)
            if filled_width > 0:
                console.draw_rect(x, y, filled_width, 1, ord(" "), bg=fg_color)

        # 텍스트 (숫자)
        text = f"{current}/{maximum}"
        text_x = x + (width - len(text)) // 2
        console.print(text_x, y, text, fg=Colors.WHITE)

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
            # 모니터 종횡비에 맞춰 창 크기 조정 (검은색 띠 유지)
            self._handle_window_resize_events()
            
            # 기본 렌더링 (TCOD가 자동으로 콘솔을 중앙에 배치하고 검은색 띠 생성)
            self.context.present(self.console)
            
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
            return None
        
        try:
            # 방법 1: 직접 속성 접근 (일반적인 방법)
            attr_names = [
                'sdl_window_p', '_sdl_window_p', 'sdl_window',
                'window', '_window', 'sdl_window_ptr'
            ]
            for attr_name in attr_names:
                if hasattr(self.context, attr_name):
                    ptr = getattr(self.context, attr_name)
                    if ptr and ptr != 0:
                        try:
                            return int(ptr) if not isinstance(ptr, int) else ptr
                        except (ValueError, TypeError):
                            continue
            
            # 방법 2: 내부 context 객체 접근 (OpenGL2 렌더러일 수 있음)
            inner_attrs = ['_context', 'context', '_impl', 'impl']
            for inner_attr in inner_attrs:
                if hasattr(self.context, inner_attr):
                    inner = getattr(self.context, inner_attr)
                    if inner:
                        for attr_name in attr_names:
                            if hasattr(inner, attr_name):
                                ptr = getattr(inner, attr_name)
                                if ptr and ptr != 0:
                                    try:
                                        return int(ptr) if not isinstance(ptr, int) else ptr
                                    except (ValueError, TypeError):
                                        continue
            
            # 방법 3: tcod.lib를 통한 접근
            try:
                import tcod.lib
                if hasattr(tcod.lib, 'ffi'):
                    ffi = tcod.lib.ffi
                    # context의 내부 구조 탐색
                    if hasattr(self.context, '__dict__'):
                        # 모든 속성을 순회하며 포인터 찾기
                        for key, value in self.context.__dict__.items():
                            if 'window' in key.lower() or 'sdl' in key.lower():
                                if value and value != 0:
                                    try:
                                        ptr_int = int(value)
                                        if ptr_int > 0:
                                            return ptr_int
                                    except (ValueError, TypeError):
                                        pass
            except:
                pass
            
            # 방법 4: context.sdl_window 속성 직접 확인 (OpenGL2에서도 가능)
            # TCOD는 모든 렌더러에서 SDL 창을 사용하므로, 숨겨진 속성일 수 있음
            try:
                # dir()로 모든 속성 확인
                all_attrs = dir(self.context)
                for attr in all_attrs:
                    if not attr.startswith('__') and ('window' in attr.lower() or 'sdl' in attr.lower()):
                        try:
                            value = getattr(self.context, attr)
                            if value and value != 0:
                                if isinstance(value, int) and value > 1000:  # 합리적인 포인터 값
                                    return value
                                elif hasattr(value, '__int__'):
                                    ptr_int = int(value)
                                    if ptr_int > 1000:
                                        return ptr_int
                        except:
                            continue
            except:
                pass
            
        except Exception as e:
            # 디버그 로그 (너무 많이 출력되지 않도록)
            if not hasattr(self, '_window_pointer_error_logged'):
                self.logger.debug(f"SDL 창 포인터 가져오기 시도 중 오류: {e}")
                self._window_pointer_error_logged = True
        
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

    def close(self) -> None:
        """TCOD 종료"""
        if self.context:
            self.context.close()
        self.logger.info("TCOD 종료")


# 전역 인스턴스
_display: Optional[TCODDisplay] = None


def get_display() -> TCODDisplay:
    """전역 디스플레이 인스턴스"""
    global _display
    if _display is None:
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
        # biome_0: caves (동굴) - 어두운 회색/보라
        0: {
            "top": (8, 8, 15),        # 깊은 회색
            "bottom": (18, 15, 25)     # 어두운 보라
        },
        # biome_1: forest (숲) - 짙은 초록
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
        # biome_9: caves (동굴) - biome_0과 동일
        9: {
            "top": (8, 8, 15),         # 깊은 회색
            "bottom": (18, 15, 25)     # 어두운 보라
        }
    }
    
    # 상황별 색상 (더 부드럽게 조정)
    context_gradients = {
        "town": {  # 마을 - 따뜻하지만 차분한 색
            "top": (20, 15, 10),       # 차분한 갈색
            "bottom": (35, 25, 18)     # 부드러운 황갈색
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

