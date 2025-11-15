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

        # ASCII 아트 타이틀 (테두리 제거)
        self.title_art = [
            "",
            "",
            "        ██████╗  █████╗ ██╗    ██╗███╗   ██╗              ",
            "        ██╔══██╗██╔══██╗██║    ██║████╗  ██║              ",
            "        ██║  ██║███████║██║ █╗ ██║██╔██╗ ██║              ",
            "        ██║  ██║██╔══██║██║███╗██║██║╚██╗██║              ",
            "        ██████╔╝██║  ██║╚███╔███╔╝██║ ╚████║              ",
            "        ╚═════╝ ╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═══╝              ",
            "                       Of                                  ",
            "          ▒█▀▀▀█ ▀▀█▀▀ ▒█▀▀▀ ▒█░░░ ▒█░░░ ░█▀▀█ ▒█▀▀█     ",
            "          ░▀▀▀▄▄ ░▒█░░ ▒█▀▀▀ ▒█░░░ ▒█░░░ ▒█▄▄█ ▒█▄▄▀     ",
            "          ▒█▄▄▄█ ░▒█░░ ▒█▄▄▄ ▒█▄▄█ ▒█▄▄█ ▒█░▒█ ▒█░▒█     ",
            "",
            "",
        ]

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
        # 화면에 랜덤하게 별 배치
        self.star_positions = []
        for _ in range(30):  # 30개의 별
            x = random.randint(0, self.screen_width - 1)
            y = random.randint(0, self.screen_height // 2)  # 상단 절반에만
            brightness = random.randint(0, 10)  # 초기 밝기
            self.star_positions.append([x, y, brightness])

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
        menu_y = self.screen_height // 2 + 5  # 공백 추가

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

        # 배경 별 렌더링 (반짝임 효과)
        for star in self.star_positions:
            x, y, brightness = star
            # 밝기 변화 (사인 함수로 부드러운 반짝임)
            phase = (self.animation_frame + brightness * 10) / 20.0
            current_brightness = int(150 + 105 * math.sin(phase))

            # 별 문자와 색상
            star_chars = [".", "*", "✦", "✧", "⋆"]
            star_char = star_chars[brightness % len(star_chars)]
            star_color = (current_brightness, current_brightness, 255)

            console.print(x, y, star_char, fg=star_color)

        # 떨어지는 별똥별 (랜덤 생성)
        if self.animation_frame % 120 == 0 or random.random() < 0.01:  # 가끔 생성
            start_x = random.randint(0, self.screen_width - 1)
            self.shooting_stars.append([start_x, 0, 0])  # [x, y, life]

        # 별똥별 렌더링 및 업데이트
        for shooting_star in self.shooting_stars[:]:
            x, y, life = shooting_star
            # 별똥별 꼬리 렌더링
            trail_length = 3
            for i in range(trail_length):
                trail_y = y - i
                trail_x = x + i
                if 0 <= trail_x < self.screen_width and 0 <= trail_y < self.screen_height:
                    alpha = 255 - (i * 60)
                    console.print(trail_x, trail_y, "·", fg=(alpha, alpha, 255))

            # 별똥별 머리 부분
            if 0 <= x < self.screen_width and 0 <= y < self.screen_height:
                console.print(x, y, "★", fg=(255, 255, 200))

            # 별똥별 이동 (오른쪽 아래로)
            shooting_star[0] += 1
            shooting_star[1] += 1
            shooting_star[2] += 1

            # 화면 밖으로 나가거나 수명 다하면 제거
            if shooting_star[0] >= self.screen_width or shooting_star[1] >= self.screen_height or shooting_star[2] > 30:
                self.shooting_stars.remove(shooting_star)

        # ASCII 아트 타이틀 렌더링 (중앙 상단)
        title_start_y = 5

        # 타이틀 색상 애니메이션 (천천히 변화)
        color_shift = math.sin(self.animation_frame / 30.0) * 30

        # 각 줄마다 그라데이션 색상 적용
        for line_idx, line in enumerate(self.title_art):
            # 줄별로 다른 색상 (그라데이션)
            base_color = self.title_gradient[line_idx % len(self.title_gradient)]

            # 색상에 애니메이션 효과 추가
            r = min(255, max(0, int(base_color[0] + color_shift)))
            g = min(255, max(0, int(base_color[1] + color_shift)))
            b = min(255, max(0, int(base_color[2] + color_shift * 0.5)))
            color = (r, g, b)

            # 중앙 정렬
            title_x = (self.screen_width - len(line)) // 2
            console.print(
                title_x,
                title_start_y + line_idx,
                line,
                fg=color
            )

        # 한글 서브타이틀 (별빛의 여명)
        subtitle_y = title_start_y + len(self.title_art) + 1
        subtitle_x = (self.screen_width - len(self.subtitle)) // 2
        # 서브타이틀도 은은하게 반짝임
        subtitle_brightness = int(200 + 55 * math.sin(self.animation_frame / 25.0))
        console.print(
            subtitle_x,
            subtitle_y,
            self.subtitle,
            fg=(subtitle_brightness, subtitle_brightness, 255)
        )

        # 장식 별 (타이틀 양옆)
        star_y = title_start_y + len(self.title_art) // 2
        star_brightness = int(150 + 105 * math.sin(self.animation_frame / 15.0))
        star_color = (star_brightness, star_brightness, 255)
        console.print(2, star_y, "✧", fg=star_color)
        console.print(self.screen_width - 3, star_y, "✧", fg=star_color)
        console.print(5, star_y - 2, "⋆", fg=star_color)
        console.print(self.screen_width - 6, star_y - 2, "⋆", fg=star_color)

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
