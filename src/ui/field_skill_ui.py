"""
Field Skill UI - 필드 스킬 선택 UI

탐험 모드에서 F키를 눌렀을 때 파티원 중 누구의 스킬을 사용할지 선택하는 팝업
"""

from typing import List, Optional, Tuple
import tcod

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors
from src.world.field_skills import FieldSkillManager
from src.core.logger import get_logger
from src.ui.input_handler import GameAction

logger = get_logger("field_skill_ui")

class FieldSkillUI:
    """필드 스킬 선택 UI"""

    def __init__(self, screen_width: int, screen_height: int, skill_manager: FieldSkillManager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.skill_manager = skill_manager
        self.menu: Optional[CursorMenu] = None
        self.is_active = False

    def show(self, party: List) -> None:
        """UI 표시"""
        self.is_active = True
        self._create_menu(party)

    def hide(self) -> None:
        """UI 숨김"""
        self.is_active = False
        self.menu = None

    def _create_menu(self, party: List) -> None:
        """파티원 선택 메뉴 생성"""
        items = []
        for member in party:
            # 멤버의 직업과 이름 가져오기
            # PartyMember 객체일 수도 있고 Character 객체일 수도 있음
            char_class = getattr(member, 'character_class', getattr(member, 'job_id', 'unknown'))
            name = getattr(member, 'name', 'Unknown')
            current_mp = getattr(member, 'current_mp', 0)
            max_mp = getattr(member, 'max_mp', 100)
            
            # 스킬 정보 가져오기
            skill_info = self.skill_manager.get_skill_info(char_class)
            
            if skill_info:
                skill_name = skill_info['name']
                mp_cost = skill_info['mp']
                desc = skill_info['desc']
                
                # 메뉴 아이템 텍스트
                text = f"[{char_class}] {name} - {skill_name} (MP {mp_cost})"
                
                # MP 부족 시 비활성화
                enabled = current_mp >= mp_cost
                if not enabled:
                    text += " [MP 부족]"
                
                item = MenuItem(
                    text=text,
                    enabled=enabled,
                    description=desc,
                    value=member  # 멤버 객체를 값으로 저장
                )
                items.append(item)
            else:
                # 스킬 없는 직업 (혹은 데이터 누락)
                items.append(MenuItem(
                    text=f"[{char_class}] {name} - 스킬 없음",
                    enabled=False,
                    description="사용 가능한 필드 스킬이 없습니다."
                ))

        # 메뉴 위치 계산 (화면 중앙)
        width = 60
        height = len(items) + 4 # 제목 + 여백
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2

        self.menu = CursorMenu(
            title="필드 스킬 선택 (Field Skill)",
            items=items,
            x=x,
            y=y,
            width=width,
            show_description=True
        )

    def handle_input(self, action: GameAction) -> Tuple[bool, Optional[str]]:
        """
        입력 처리
        
        Returns:
            (UI 종료 여부, 결과 메시지)
        """
        if not self.is_active or not self.menu:
            return False, None

        if action == GameAction.MOVE_UP:
            self.menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.menu.move_cursor_down()
        elif action == GameAction.CANCEL:
            self.hide()
            return True, None # UI 닫힘
        elif action == GameAction.CONFIRM:
            selected = self.menu.get_selected_item()
            if selected and selected.enabled:
                member = selected.value
                success, msg = self.skill_manager.use_skill(member)
                self.hide()
                return True, msg # 스킬 사용 결과 메시지 반환
            
        return False, None

    def render(self, console: tcod.console.Console) -> None:
        """렌더링"""
        if self.is_active and self.menu:
            self.menu.render(console)

