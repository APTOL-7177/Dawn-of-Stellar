"""
Main Menu - 메인 메뉴

게임 시작 시 표시되는 메인 메뉴
"""

import tcod.console
import tcod.event
from typing import Optional
from enum import Enum

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction
from src.core.logger import get_logger
from src.audio import play_bgm


class MenuResult(Enum):
    """메뉴 결과"""
    NEW_GAME = "new_game"
    CONTINUE = "continue"
    SHOP = "shop"
    SETTINGS = "settings"
    QUIT = "quit"
    NONE = "none"


class MainMenu:
    """
    메인 메뉴

    - 새 게임
    - 계속하기
    - 상점
    - 설정
    - 종료
    """

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("main_menu")

        # 메뉴 결과
        self.result: MenuResult = MenuResult.NONE

        # 큰 글씨 폰트 (4x5 픽셀 - 더 작고 세련된 스타일)
        self.big_font = {
            'D': [
                [1,1,1,0],
                [1,0,0,1],
                [1,0,0,1],
                [1,0,0,1],
                [1,1,1,0]
            ],
            'A': [
                [0,1,1,0],
                [1,0,0,1],
                [1,1,1,1],
                [1,0,0,1],
                [1,0,0,1]
            ],
            'W': [
                [1,0,0,1],
                [1,0,0,1],
                [1,0,1,1],
                [1,1,0,1],
                [1,0,0,1]
            ],
            'N': [
                [1,0,0,1],
                [1,1,0,1],
                [1,0,1,1],
                [1,0,0,1],
                [1,0,0,1]
            ],
            'S': [
                [0,1,1,1],
                [1,0,0,0],
                [0,1,1,0],
                [0,0,0,1],
                [1,1,1,0]
            ],
            'T': [
                [1,1,1,1],
                [0,1,1,0],
                [0,1,1,0],
                [0,1,1,0],
                [0,1,1,0]
            ],
            'E': [
                [1,1,1,1],
                [1,0,0,0],
                [1,1,1,0],
                [1,0,0,0],
                [1,1,1,1]
            ],
            'L': [
                [1,0,0,0],
                [1,0,0,0],
                [1,0,0,0],
                [1,0,0,0],
                [1,1,1,1]
            ],
            'R': [
                [1,1,1,0],
                [1,0,0,1],
                [1,1,1,0],
                [1,0,1,0],
                [1,0,0,1]
            ],
        }

        # 작은 글씨 폰트 (3x3 픽셀 - OF용)
        self.small_font = {
            'O': [
                [1,1,1],
                [1,0,1],
                [1,1,1]
            ],
            'F': [
                [1,1,1],
                [1,1,0],
                [1,0,0]
            ],
        }

        # 한글 서브타이틀
        self.subtitle = "별빛의 여명"

        # 애니메이션 관련
        self.animation_frame = 0
        self.star_positions = []  # 반짝이는 별 위치
        self.shooting_stars = []  # 떨어지는 별똥별
        self._generate_stars()

        # 타이틀 색상 (별빛 그라데이션)
        self.title_gradient = [
            (100, 150, 255),   # 파란 별빛
            (150, 180, 255),   # 밝은 파랑
            (200, 220, 255),   # 하얀 별빛
            (255, 240, 200),   # 따뜻한 빛
            (255, 255, 150),   # 노란 빛
        ]

    def _generate_stars(self):
        """배경 별 생성"""
        import random
        # 화면에 랜덤하게 별 배치 (줄임)
        self.star_positions = []
        for _ in range(15):  # 15개로 줄임
            x = random.randint(0, self.screen_width - 1)
            y = random.randint(0, self.screen_height - 1)
            brightness = random.randint(0, 10)  # 초기 밝기
            speed = random.uniform(0.5, 2.0)  # 반짝임 속도
            self.star_positions.append([x, y, brightness, speed])

        # 메뉴 아이템 생성
        # 저장 파일이 있는지 확인
        from src.persistence.save_system import SaveSystem
        save_system = SaveSystem()
        has_saves = len(save_system.list_saves()) > 0

        menu_items = [
            MenuItem(
                text="새 게임",
                action=self._new_game,
                description="새로운 모험을 시작합니다"
            ),
            MenuItem(
                text="계속하기",
                action=self._continue_game,
                enabled=has_saves,
                description="저장된 게임을 불러옵니다"
            ),
            MenuItem(
                text="상점",
                action=self._open_shop,
                description="별빛의 파편으로 직업과 패시브를 구매합니다"
            ),
            MenuItem(
                text="설정",
                action=self._open_settings,
                description="게임 설정을 변경합니다"
            ),
            MenuItem(
                text="종료",
                action=self._quit_game,
                description="게임을 종료합니다"
            ),
        ]

        # 커서 메뉴 생성 (중앙 하단 배치)
        menu_width = 40
        menu_x = (self.screen_width - menu_width) // 2
        menu_y = self.screen_height // 2 + 2  # 타이틀이 작아져서 간격 조정

        self.menu = CursorMenu(
            title="",
            items=menu_items,
            x=menu_x,
            y=menu_y,
            width=menu_width,
            show_description=True
        )

    def _new_game(self) -> None:
        """새 게임 시작"""
        self.logger.info("새 게임 선택")
        self.result = MenuResult.NEW_GAME

    def _continue_game(self) -> None:
        """게임 계속하기"""
        self.logger.info("계속하기 선택")
        self.result = MenuResult.CONTINUE

    def _open_shop(self) -> None:
        """상점 열기"""
        self.logger.info("상점 선택")
        self.result = MenuResult.SHOP

    def _open_settings(self) -> None:
        """설정 열기"""
        self.logger.info("설정 선택")
        self.result = MenuResult.SETTINGS

    def _quit_game(self) -> None:
        """게임 종료"""
        self.logger.info("종료 선택")
        self.result = MenuResult.QUIT

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            메뉴가 종료되었으면 True
        """
        if action == GameAction.MOVE_UP:
            self.menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            self.menu.execute_selected()
            return self.result != MenuResult.NONE
        elif action == GameAction.ESCAPE or action == GameAction.QUIT:
            self.result = MenuResult.QUIT
            return True

        return False

    def render(self, console: tcod.console.Console) -> None:
        """
        메인 메뉴 렌더링

        Args:
            console: 렌더링할 콘솔
        """
        import math
        import random

        # 배경 클리어
        console.clear()

        # 애니메이션 프레임 증가
        self.animation_frame += 1

        # 배경에 어두운 그라데이션 (우주 느낌)
        for y in range(self.screen_height):
            gradient_intensity = max(0, int(10 + (y / self.screen_height) * 20))
            r = max(0, gradient_intensity // 3)
            g = max(0, gradient_intensity // 4)
            b = max(0, gradient_intensity)
            for x in range(self.screen_width):
                console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))

        # 배경 별 렌더링 (은은한 반짝임만)
        for star in self.star_positions:
            x, y, brightness, speed = star
            # 밝기 변화 (사인 함수로 부드러운 반짝임)
            phase = (self.animation_frame + brightness * 10) / (20.0 / speed)
            current_brightness = max(0, min(255, int(120 + 135 * math.sin(phase))))

            # 은은한 별 (한 가지 스타일)
            star_color = (current_brightness, current_brightness, 255)

            if 0 <= x < self.screen_width and 0 <= y < self.screen_height:
                console.print(x, y, "·", fg=star_color)

        # 화면 테두리 장식 (코너 장식)
        corner_brightness = max(0, min(255, int(150 + 105 * math.sin(self.animation_frame / 20.0))))
        corner_color = (corner_brightness, corner_brightness, 255)

        # 좌상단
        console.print(0, 0, "╔", fg=corner_color)
        console.print(1, 0, "═", fg=corner_color)
        console.print(2, 0, "═", fg=corner_color)
        console.print(0, 1, "║", fg=corner_color)

        # 우상단
        console.print(self.screen_width - 1, 0, "╗", fg=corner_color)
        console.print(self.screen_width - 2, 0, "═", fg=corner_color)
        console.print(self.screen_width - 3, 0, "═", fg=corner_color)
        console.print(self.screen_width - 1, 1, "║", fg=corner_color)

        # 좌하단
        console.print(0, self.screen_height - 1, "╚", fg=corner_color)
        console.print(1, self.screen_height - 1, "═", fg=corner_color)
        console.print(2, self.screen_height - 1, "═", fg=corner_color)
        console.print(0, self.screen_height - 2, "║", fg=corner_color)

        # 우하단
        console.print(self.screen_width - 1, self.screen_height - 1, "╝", fg=corner_color)
        console.print(self.screen_width - 2, self.screen_height - 1, "═", fg=corner_color)
        console.print(self.screen_width - 3, self.screen_height - 1, "═", fg=corner_color)
        console.print(self.screen_width - 1, self.screen_height - 2, "║", fg=corner_color)

        # 박스 렌더링 타이틀 (중앙 상단, 3줄로 구성)
        title_start_y = 6

        # 타이틀 색상 애니메이션 (천천히 변화 + 물결 효과)
        color_shift = math.sin(self.animation_frame / 30.0) * 30
        wave_offset = math.sin(self.animation_frame / 15.0) * 2  # 물결 효과

        # 메인 타이틀 색상 (파란색 계열 - 더 밝게)
        main_color_base = (140, 200, 255)
        main_r = min(255, max(0, int(main_color_base[0] + color_shift)))
        main_g = min(255, max(0, int(main_color_base[1] + color_shift)))
        main_b = min(255, max(0, int(main_color_base[2] + color_shift * 0.5)))
        main_color = (main_r, main_g, main_b)

        # "OF" 색상 (은은한 노란색)
        of_color_base = (255, 220, 150)
        of_r = min(255, max(0, int(of_color_base[0] + color_shift * 0.3)))
        of_g = min(255, max(0, int(of_color_base[1] + color_shift * 0.3)))
        of_b = min(255, max(0, int(of_color_base[2] + color_shift * 0.2)))
        of_color = (of_r, of_g, of_b)

        # 그림자 색상
        shadow_color = (20, 30, 50)

        # 렌더링 헬퍼 함수
        def render_text(text, font_dict, y_offset, char_width, char_height, color, use_glow=False):
            letter_spacing = 1
            total_width = (char_width + letter_spacing) * len(text) - letter_spacing
            start_x = (self.screen_width - total_width) // 2

            current_x = start_x
            for char in text:
                if char in font_dict:
                    char_pixels = font_dict[char]

                    # 픽셀 단위로 렌더링
                    for y, row in enumerate(char_pixels):
                        for x, pixel in enumerate(row):
                            if pixel == 1:
                                px = current_x + x
                                py = title_start_y + y_offset + y

                                # 그림자 효과
                                if px + 1 < self.screen_width and py + 1 < self.screen_height:
                                    ch, fg, _ = console.rgb[py + 1, px + 1]
                                    console.rgb[py + 1, px + 1] = (ch, fg, shadow_color)

                                # 글로우 효과 (선택적)
                                if use_glow:
                                    glow_color = (
                                        max(0, color[0] - 80),
                                        max(0, color[1] - 80),
                                        max(0, color[2] - 80)
                                    )
                                    # 주변 픽셀에 글로우
                                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                                        gx, gy = px + dx, py + dy
                                        if 0 <= gx < self.screen_width and 0 <= gy < self.screen_height:
                                            ch, fg, current_bg = console.rgb[gy, gx]
                                            # 이미 그려진 부분이 아니면 글로우 적용
                                            if not (current_bg[0] > 100 or current_bg[1] > 100 or current_bg[2] > 100):
                                                console.rgb[gy, gx] = (ch, fg, glow_color)

                                # 메인 블록
                                if px < self.screen_width and py < self.screen_height:
                                    ch, fg, _ = console.rgb[py, px]
                                    console.rgb[py, px] = (ch, fg, color)

                    # 다음 글자 위치로 이동
                    current_x += char_width + letter_spacing

        # 1줄: "DAWN" (큰 글씨)
        render_text("DAWN", self.big_font, 0, 4, 5, main_color, use_glow=True)

        # 2줄: "OF" (작은 글씨)
        render_text("OF", self.small_font, 7, 3, 3, of_color, use_glow=False)

        # 3줄: "STELLAR" (큰 글씨)
        render_text("STELLAR", self.big_font, 11, 4, 5, main_color, use_glow=True)

        # 타이틀 주변 빛 확산 효과
        title_center_y = title_start_y + 8
        title_center_x = self.screen_width // 2

        # 빛 확산 라인 (좌우)
        glow_length = int(8 + 3 * math.sin(self.animation_frame / 25.0))
        glow_brightness = max(0, min(255, int(80 + 50 * math.sin(self.animation_frame / 20.0))))

        for i in range(1, glow_length):
            alpha = max(0, int(glow_brightness * (1 - i / glow_length)))
            glow_color = (alpha, alpha, 255)

            # 왼쪽
            if title_center_x - 25 - i >= 0:
                console.print(title_center_x - 25 - i, title_center_y, "─", fg=glow_color)
            # 오른쪽
            if title_center_x + 25 + i < self.screen_width:
                console.print(title_center_x + 25 + i, title_center_y, "─", fg=glow_color)

        # 한글 서브타이틀 (별빛의 여명)
        subtitle_y = title_start_y + 18  # 타이틀 전체 높이 + 2줄 간격
        subtitle_x = (self.screen_width - len(self.subtitle)) // 2
        # 서브타이틀도 은은하게 반짝임
        subtitle_brightness = max(0, min(255, int(200 + 55 * math.sin(self.animation_frame / 25.0))))
        console.print(
            subtitle_x,
            subtitle_y,
            self.subtitle,
            fg=(subtitle_brightness, subtitle_brightness, 255)
        )

        # 장식 별 (타이틀 위아래만 - 더 은은하게)
        star_brightness = max(0, min(255, int(150 + 105 * math.sin(self.animation_frame / 15.0))))
        star_color = (star_brightness, star_brightness, 255)

        # 위아래 별 (펄스 애니메이션)
        top_brightness = max(0, min(255, int(180 + 75 * math.sin(self.animation_frame / 12.0))))
        bottom_brightness = max(0, min(255, int(180 + 75 * math.sin(self.animation_frame / 12.0 + math.pi))))

        # 위쪽 별 3개
        console.print(self.screen_width // 2 - 2, title_start_y - 1, "✦", fg=(top_brightness, top_brightness, 255))
        console.print(self.screen_width // 2, title_start_y - 1, "✦", fg=(top_brightness, top_brightness, 255))
        console.print(self.screen_width // 2 + 2, title_start_y - 1, "✦", fg=(top_brightness, top_brightness, 255))

        # 아래쪽 별 3개
        console.print(self.screen_width // 2 - 2, title_start_y + 17, "✦", fg=(bottom_brightness, bottom_brightness, 255))
        console.print(self.screen_width // 2, title_start_y + 17, "✦", fg=(bottom_brightness, bottom_brightness, 255))
        console.print(self.screen_width // 2 + 2, title_start_y + 17, "✦", fg=(bottom_brightness, bottom_brightness, 255))

        # 메뉴 프레임 효과
        menu_y_start = self.screen_height // 2 + 1
        menu_y_end = menu_y_start + 10
        menu_x_start = (self.screen_width - 40) // 2 - 2
        menu_x_end = menu_x_start + 44

        frame_brightness = max(0, min(255, int(100 + 50 * math.sin(self.animation_frame / 30.0))))
        frame_color = (frame_brightness, frame_brightness, 200)

        # 프레임 라인 (상하좌우)
        for x in range(menu_x_start, menu_x_end):
            if x >= 0 and x < self.screen_width:
                console.print(x, menu_y_start - 1, "─", fg=frame_color)
                console.print(x, menu_y_end, "─", fg=frame_color)

        for y in range(menu_y_start, menu_y_end):
            if y >= 0 and y < self.screen_height:
                console.print(menu_x_start - 1, y, "│", fg=frame_color)
                console.print(menu_x_end, y, "│", fg=frame_color)

        # 프레임 코너
        console.print(menu_x_start - 1, menu_y_start - 1, "┌", fg=frame_color)
        console.print(menu_x_end, menu_y_start - 1, "┐", fg=frame_color)
        console.print(menu_x_start - 1, menu_y_end, "└", fg=frame_color)
        console.print(menu_x_end, menu_y_end, "┘", fg=frame_color)

        # 버전 정보
        version = "v5.0.0"
        console.print(
            self.screen_width - len(version) - 2,
            self.screen_height - 2,
            version,
            fg=Colors.GRAY
        )

        # 조작 안내
        controls = "방향키: 이동  Z: 선택  X: 취소"
        console.print(
            2,
            self.screen_height - 2,
            controls,
            fg=Colors.GRAY
        )

        # 메뉴 렌더링
        self.menu.render(console)

    def reset(self) -> None:
        """메뉴 상태 초기화"""
        self.result = MenuResult.NONE


def run_main_menu(console: tcod.console.Console, context: tcod.context.Context) -> MenuResult:
    """
    메인 메뉴 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        메뉴 선택 결과
    """
    from src.ui.input_handler import InputHandler
    import time

    # 메인 메뉴 BGM 재생
    play_bgm("main_menu")

    menu = MainMenu(console.width, console.height)
    handler = InputHandler()

    # 애니메이션을 위한 시간 관리
    last_time = time.time()
    frame_time = 1.0 / 30.0  # 30 FPS

    while True:
        current_time = time.time()
        delta_time = current_time - last_time

        # 프레임 제한 (30 FPS)
        if delta_time >= frame_time:
            last_time = current_time

            # 렌더링 (매 프레임마다 애니메이션 업데이트)
            menu.render(console)
            context.present(console)

        # 입력 처리 (논블로킹)
        for event in tcod.event.get():
            action = handler.dispatch(event)

            if action:
                if menu.handle_input(action):
                    return menu.result

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return MenuResult.QUIT

        # CPU 사용률 낮추기
        time.sleep(0.01)
