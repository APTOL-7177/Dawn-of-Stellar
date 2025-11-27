"""
필드스킬 메뉴 UI (인게임 메뉴용)

필드 스킬 관리 및 설정
"""

from enum import Enum
from typing import List, Optional
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.ui.tcod_display import render_space_background, Colors
from src.core.logger import get_logger, Loggers
from src.field.field_skills import FieldSkillManager
from src.character.skill_types import skill_type_registry, SkillCategory


logger = get_logger(Loggers.UI)


class FieldSkillMenuOption(Enum):
    """필드스킬 메뉴 옵션"""
    VIEW_SKILLS = "view_skills"
    BACK = "back"


class FieldSkillMenu:
    """필드스킬 메뉴"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0
        self.skill_manager = FieldSkillManager()
        self.field_skills = self.skill_manager.field_skills

        # 메뉴 옵션들
        self.menu_options = [
            ("필드 스킬 목록 보기", FieldSkillMenuOption.VIEW_SKILLS),
            ("돌아가기", FieldSkillMenuOption.BACK)
        ]

    def render(self, console: tcod.console.Console) -> None:
        """메뉴 렌더링"""
        # 배경 렌더링
        render_space_background(console, self.screen_width, self.screen_height)

        # 타이틀
        title = "필드 스킬 관리"
        title_x = (self.screen_width - len(title)) // 2
        console.print(title_x, 3, title, fg=Colors.CYAN)

        # 메뉴 옵션들
        start_y = 8
        for i, (option_text, _) in enumerate(self.menu_options):
            fg_color = Colors.YELLOW if i == self.selected_index else Colors.WHITE
            console.print(4, start_y + i * 2, f"{i + 1}. {option_text}", fg=fg_color)

        # 선택된 옵션에 대한 설명
        if self.selected_index < len(self.menu_options):
            description_y = start_y + len(self.menu_options) * 2 + 2
            if self.selected_index == 0:  # 필드 스킬 목록 보기
                console.print(4, description_y, "사용 가능한 모든 필드 스킬을 확인하고 설명을 볼 수 있습니다.", fg=Colors.GRAY)
            elif self.selected_index == 1:  # 돌아가기
                console.print(4, description_y, "메뉴로 돌아갑니다.", fg=Colors.GRAY)

        # 필드 스킬 정보 표시 (간단히)
        skills_info_y = description_y + 4
        console.print(4, skills_info_y, f"등록된 필드 스킬: {len(self.field_skills)}개", fg=Colors.GREEN)

        # 몇 개의 스킬 이름 표시
        if self.field_skills:
            skill_list_y = skills_info_y + 2
            max_display = min(5, len(self.field_skills))
            for i in range(max_display):
                skill_type = self.field_skills[i]
                skill_name = getattr(skill_type, 'name', str(skill_type))
                console.print(6, skill_list_y + i, f"• {skill_name}", fg=Colors.LIGHT_BLUE)

            if len(self.field_skills) > max_display:
                console.print(6, skill_list_y + max_display, f"... 외 {len(self.field_skills) - max_display}개", fg=Colors.GRAY)

        # 조작 안내
        controls_y = self.screen_height - 3
        console.print(4, controls_y, "방향키: 이동  Z: 선택  X: 취소", fg=Colors.GRAY)

    def handle_input(self, action: GameAction) -> Optional[FieldSkillMenuOption]:
        """입력 처리"""
        if action == GameAction.MOVE_UP:
            self.selected_index = (self.selected_index - 1) % len(self.menu_options)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = (self.selected_index + 1) % len(self.menu_options)
        elif action == GameAction.CONFIRM:
            return self.menu_options[self.selected_index][1]
        elif action == GameAction.ESCAPE or action == GameAction.QUIT:
            return FieldSkillMenuOption.BACK

        return None


def open_field_skill_menu(console: tcod.console.Console, context: tcod.context.Context) -> None:
    """
    필드스킬 메뉴 열기 (인게임 메뉴용)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
    """
    from src.audio import play_sfx

    logger.info("필드스킬 메뉴 열기")

    # 메뉴 진입 사운드
    play_sfx("ui", "cursor_confirm")

    menu = FieldSkillMenu(console.width, console.height)
    handler = InputHandler()

    while True:
        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)
            if action:
                result = menu.handle_input(action)
                if result == FieldSkillMenuOption.BACK:
                    logger.info("필드스킬 메뉴 닫기")
                    # 메뉴 종료 사운드
                    play_sfx("ui", "cursor_cancel")
                    return
                elif result == FieldSkillMenuOption.VIEW_SKILLS:
                    # 필드 스킬 목록 보기 (아직 구현되지 않음 - TODO)
                    logger.info("필드 스킬 목록 보기 선택")
                    play_sfx("ui", "cursor_confirm")
                    # TODO: 상세 스킬 목록 UI 구현

        # 렌더링
        menu.render(console)
        context.present(console)
