"""
난이도 선택 UI

게임 시작 전 난이도 선택
"""

import tcod.console
import tcod.event
from typing import Optional
import math

from src.core.difficulty import DifficultyLevel, DifficultySystem
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("difficulty_ui")


class DifficultySelectionUI:
    """난이도 선택 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        difficulty_system: DifficultySystem
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            difficulty_system: 난이도 시스템
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.difficulty_system = difficulty_system

        # 난이도 목록
        self.difficulties = list(DifficultyLevel)
        self.cursor = 1  # 기본: 보통

        # 상태
        self.closed = False
        self.selected_difficulty: Optional[DifficultyLevel] = None

        # 애니메이션
        self.animation_frame = 0

        logger.info("난이도 선택 UI 열기")

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            닫기 여부
        """
        if action == GameAction.MOVE_UP:
            self.cursor = max(0, self.cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.cursor = min(len(self.difficulties) - 1, self.cursor + 1)
        elif action == GameAction.CONFIRM:
            # 난이도 선택 확정
            self.selected_difficulty = self.difficulties[self.cursor]
            self.difficulty_system.set_difficulty(self.selected_difficulty)
            logger.info(f"난이도 선택: {self.selected_difficulty.value}")
            self.closed = True
            return True
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소 시 기본 난이도 (보통)
            play_sfx("ui", "cursor_cancel")
            self.selected_difficulty = DifficultyLevel.NORMAL
            self.difficulty_system.set_difficulty(self.selected_difficulty)
            self.closed = True
            return True

        return False

    def render(self, console: tcod.console.Console) -> None:
        """
        렌더링

        Args:
            console: 렌더링할 콘솔
        """
        # 배경 클리어
        render_space_background(console, self.screen_width, self.screen_height)

        # 애니메이션 프레임 증가
        self.animation_frame += 1

        # 타이틀
        title = "난이도 선택"
        subtitle = "차원 항해의 난이도를 선택하세요"

        title_x = (self.screen_width - len(title)) // 2
        console.print(
            title_x,
            5,
            title,
            fg=Colors.CYAN
        )

        subtitle_x = (self.screen_width - len(subtitle)) // 2
        console.print(
            subtitle_x,
            7,
            subtitle,
            fg=Colors.GRAY
        )

        # 난이도 목록
        menu_y = 10
        menu_width = 60
        menu_x = (self.screen_width - menu_width) // 2

        # 난이도별 색상
        difficulty_colors = {
            DifficultyLevel.PEACEFUL: (100, 255, 100),  # 녹색 (쉬움)
            DifficultyLevel.NORMAL: (200, 200, 200),    # 회색 (보통)
            DifficultyLevel.CHALLENGE: (255, 200, 100), # 주황 (도전)
            DifficultyLevel.NIGHTMARE: (255, 100, 100), # 빨강 (악몽)
            DifficultyLevel.HELL: (200, 0, 200)         # 보라 (지옥)
        }

        for idx, difficulty in enumerate(self.difficulties):
            y = menu_y + idx * 7

            # 난이도 정보 가져오기
            info = self.difficulty_system.get_difficulty_info(difficulty)

            # 선택된 항목 표시
            is_selected = (idx == self.cursor)

            # 배경 박스
            if is_selected:
                # 선택된 항목 강조 (애니메이션)
                pulse = math.sin(self.animation_frame / 10.0) * 10 + 20
                bg_color = (int(pulse), int(pulse), int(pulse * 2))

                # 박스 그리기 (배경색만 설정) - tcod는 [y, x] 순서 사용
                for dx in range(menu_width):
                    for dy in range(6):
                        console.bg[y + dy, menu_x + dx] = bg_color

            # 난이도 이름
            name_color = difficulty_colors.get(difficulty, Colors.WHITE)
            if is_selected:
                # 선택된 항목은 더 밝게
                name_color = tuple(min(255, c + 50) for c in name_color)

            cursor_str = "▶ " if is_selected else "  "
            console.print(
                menu_x + 2,
                y,
                f"{cursor_str}{info['name']}",
                fg=name_color
            )

            # 설명
            console.print(
                menu_x + 4,
                y + 1,
                info['description'],
                fg=Colors.GRAY
            )

            # 배율 정보
            modifiers_text = (
                f"적 체력: {info['modifiers']['적 체력']}  "
                f"적 공격력: {info['modifiers']['적 공격력']}  "
                f"플레이어 데미지: {info['modifiers']['플레이어 데미지']}"
            )
            console.print(
                menu_x + 4,
                y + 2,
                modifiers_text,
                fg=Colors.YELLOW
            )

            # 보상 정보
            rewards_text = (
                f"경험치: {info['modifiers']['경험치']}  "
                f"드랍률: {info['modifiers']['드랍률']}"
            )
            console.print(
                menu_x + 4,
                y + 3,
                rewards_text,
                fg=Colors.GREEN
            )

        # 조작 안내
        controls = "방향키: 이동  Z: 선택  X: 취소 (기본: 보통)"
        console.print(
            (self.screen_width - len(controls)) // 2,
            self.screen_height - 3,
            controls,
            fg=Colors.GRAY
        )

        # 추가 안내
        notice = "※ 난이도는 세이브 파일별로 저장되며, 게임 중 변경할 수 없습니다"
        console.print(
            (self.screen_width - len(notice)) // 2,
            self.screen_height - 5,
            notice,
            fg=Colors.ORANGE
        )


def show_difficulty_selection(
    console: tcod.console.Console,
    context: tcod.context.Context,
    difficulty_system: DifficultySystem
) -> Optional[DifficultyLevel]:
    """
    난이도 선택 UI 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        difficulty_system: 난이도 시스템

    Returns:
        선택된 난이도 (취소 시 None)
    """
    from src.ui.input_handler import InputHandler
    import time

    ui = DifficultySelectionUI(console.width, console.height, difficulty_system)
    handler = InputHandler()

    # 애니메이션을 위한 시간 관리
    last_time = time.time()
    frame_time = 1.0 / 30.0  # 30 FPS

    while not ui.closed:
        current_time = time.time()
        delta_time = current_time - last_time

        # 프레임 제한 (30 FPS)
        if delta_time >= frame_time:
            last_time = current_time

            # 렌더링
            ui.render(console)
            context.present(console)

        # 입력 처리
        for event in tcod.event.get():
            action = handler.dispatch(event)

            if action:
                if ui.handle_input(action):
                    return ui.selected_difficulty

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return DifficultyLevel.NORMAL  # 기본값

        # CPU 사용률 낮추기
        time.sleep(0.01)

    return ui.selected_difficulty
