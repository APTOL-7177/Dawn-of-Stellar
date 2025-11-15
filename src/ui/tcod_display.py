"""
TCOD Display - python-tcod 기반 디스플레이 시스템

tcod를 사용한 렌더링 및 UI 관리
"""

import tcod
import tcod.context
import tcod.console
import tcod.event
from typing import Optional, Tuple
from pathlib import Path

from src.core.config import get_config
from src.core.logger import get_logger


class Colors:
    """색상 정의"""
    # 기본 색상
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    DARK_GRAY = (64, 64, 64)

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

        # 화면 크기
        self.screen_width = self.config.get("display.screen_width", 80)
        self.screen_height = self.config.get("display.screen_height", 50)

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

            context_kwargs = {
                "columns": self.screen_width,
                "rows": self.screen_height,
                "tileset": self.tileset,
                "title": "Dawn of Stellar - 별빛의 여명",
                "vsync": self.config.get("display.vsync", True)
            }

            if renderer is not None:
                context_kwargs["renderer"] = renderer
                self.logger.info(f"렌더러 사용: {renderer_name}")

            self.context = tcod.context.new(**context_kwargs)
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
            self.context.present(self.console)

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
