"""가능성 선택 UI - 시간술사 가능성 슬롯 선택"""
import tcod
import tcod.event
from typing import Optional, List, Dict, Any
from src.core.logger import get_logger
from src.audio.audio_manager import play_sfx

logger = get_logger("possibility_selection_ui")


class PossibilitySelectionUI:
    """가능성 슬롯 선택 UI"""
    
    def __init__(self, console: tcod.console.Console, slots: List[Dict], 
                 action: str = "summon_single", max_select: int = 1):
        """
        Args:
            console: tcod 콘솔
            slots: 가능성 슬롯 목록 [{'skill_id': ..., 'power_ratio': ..., 'skill_name': ...}, ...]
            action: 액션 타입 (summon_single, summon_dual, overwrite_slot)
            max_select: 최대 선택 가능 개수
        """
        self.console = console
        self.slots = slots
        self.action = action
        self.max_select = max_select
        
        self.selected_indices: List[int] = []
        self.cursor_index = 0
        self.cancelled = False
        self.confirmed = False
        
        # UI 크기 및 위치
        self.width = 40
        self.height = min(len(slots) + 6, 15)
        self.x = (console.width - self.width) // 2
        self.y = (console.height - self.height) // 2
    
    def render(self):
        """UI 렌더링"""
        # 배경 박스
        self.console.draw_frame(
            self.x, self.y, self.width, self.height,
            title="가능성 선택",
            clear=True,
            fg=(255, 255, 255),
            bg=(20, 20, 40)
        )
        
        # 설명 텍스트
        action_desc = {
            "summon_single": "발동할 가능성 1개 선택",
            "summon_dual": f"발동할 가능성 2개 선택 ({len(self.selected_indices)}/2)",
            "overwrite_slot": "덮어쓸 슬롯 선택"
        }
        desc = action_desc.get(self.action, "선택")
        self.console.print(self.x + 2, self.y + 1, desc, fg=(200, 200, 200))
        
        # 슬롯 목록
        for i, slot in enumerate(self.slots):
            y_pos = self.y + 3 + i
            
            # 선택 상태 표시
            if i in self.selected_indices:
                prefix = "◆ "
                fg_color = (100, 255, 100)
            elif i == self.cursor_index:
                prefix = "▶ "
                fg_color = (255, 255, 100)
            else:
                prefix = "  "
                fg_color = (200, 200, 200)
            
            skill_name = slot.get('skill_name', slot.get('skill_id', '???'))
            power = int(slot.get('power_ratio', 0.85) * 100)
            
            text = f"{prefix}{i+1}. {skill_name} ({power}%)"
            self.console.print(self.x + 2, y_pos, text, fg=fg_color)
        
        # 하단 안내
        help_y = self.y + self.height - 2
        if self.action == "summon_dual":
            help_text = "Enter: 선택/해제 | Tab: 확정 | Esc: 취소"
        else:
            help_text = "Enter: 확정 | Esc: 취소"
        self.console.print(self.x + 2, help_y, help_text, fg=(150, 150, 150))
    
    def handle_input(self, key: tcod.event.KeyDown) -> bool:
        """
        입력 처리
        
        Returns:
            True면 UI 종료
        """
        if key.sym == tcod.event.KeySym.ESCAPE:
            self.cancelled = True
            play_sfx("ui", "cursor_cancel")
            return True
        
        elif key.sym == tcod.event.KeySym.UP or key.sym == tcod.event.KeySym.w:
            self.cursor_index = max(0, self.cursor_index - 1)
            play_sfx("ui", "cursor_move")
            
        elif key.sym == tcod.event.KeySym.DOWN or key.sym == tcod.event.KeySym.s:
            self.cursor_index = min(len(self.slots) - 1, self.cursor_index + 1)
            play_sfx("ui", "cursor_move")
        
        elif key.sym == tcod.event.KeySym.RETURN or key.sym == tcod.event.KeySym.z:
            if self.action == "summon_dual":
                # 다중 선택 모드
                if self.cursor_index in self.selected_indices:
                    self.selected_indices.remove(self.cursor_index)
                    play_sfx("ui", "cursor_cancel")
                elif len(self.selected_indices) < self.max_select:
                    self.selected_indices.append(self.cursor_index)
                    play_sfx("ui", "cursor_select")
            else:
                # 단일 선택 모드 - 즉시 확정
                self.selected_indices = [self.cursor_index]
                self.confirmed = True
                play_sfx("ui", "cursor_select")
                return True
        
        elif key.sym == tcod.event.KeySym.TAB:
            # 다중 선택 확정
            if self.action == "summon_dual" and len(self.selected_indices) >= 2:
                self.confirmed = True
                play_sfx("ui", "cursor_select")
                return True
        
        # 숫자키로 직접 선택
        elif key.sym >= tcod.event.KeySym.N1 and key.sym <= tcod.event.KeySym.N9:
            num = key.sym - tcod.event.KeySym.N1
            if num < len(self.slots):
                if self.action == "summon_dual":
                    if num in self.selected_indices:
                        self.selected_indices.remove(num)
                    elif len(self.selected_indices) < self.max_select:
                        self.selected_indices.append(num)
                else:
                    self.selected_indices = [num]
                    self.confirmed = True
                    play_sfx("ui", "cursor_select")
                    return True
        
        return False
    
    def get_result(self) -> Optional[List[int]]:
        """선택 결과 반환"""
        if self.cancelled:
            return None
        if self.confirmed:
            return self.selected_indices
        return None


def show_possibility_selection(console: tcod.console.Console, context: tcod.context.Context,
                               character, action: str = "summon_single") -> Optional[List[int]]:
    """
    가능성 선택 UI 표시
    
    Args:
        console: tcod 콘솔
        context: tcod 컨텍스트
        character: 시간술사 캐릭터
        action: 액션 타입
    
    Returns:
        선택된 슬롯 인덱스 리스트 또는 None (취소)
    """
    from src.character.skills.skill_manager import get_skill_manager
    
    slots = getattr(character, 'possibility_slots', [])
    if not slots:
        logger.warning("가능성 슬롯이 비어있습니다")
        return None
    
    # 스킬 이름 추가
    skill_manager = get_skill_manager()
    enriched_slots = []
    for slot in slots:
        skill = skill_manager.get_skill(slot['skill_id'])
        enriched_slot = slot.copy()
        enriched_slot['skill_name'] = skill.name if skill else slot['skill_id']
        enriched_slots.append(enriched_slot)
    
    # 최대 선택 개수
    max_select = 2 if action == "summon_dual" else 1
    
    # UI 생성
    ui = PossibilitySelectionUI(console, enriched_slots, action, max_select)
    
    # 메인 루프
    while True:
        ui.render()
        context.present(console)
        
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.KeyDown):
                if ui.handle_input(event):
                    return ui.get_result()
            elif isinstance(event, tcod.event.Quit):
                return None
