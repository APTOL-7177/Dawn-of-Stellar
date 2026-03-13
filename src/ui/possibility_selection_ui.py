"""가능성 선택 UI - 시간술사 가능성 슬롯 선택"""
import tcod
import tcod.event
from typing import Optional, List, Dict, Any
from src.core.logger import get_logger
from src.audio.audio_manager import play_sfx
from src.ui.input_handler import unified_input_handler, GameAction
from src.ui.ui_renderer import draw_styled_box, SelectionHighlight

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

        # UI 효과
        self._highlight = SelectionHighlight(
            base_bg=(40, 40, 60), pulse_bg=(60, 60, 100), speed=3.0
        )
        self._last_time = 0.0
    
    def render(self):
        """UI 렌더링"""
        import time as _time

        # dt 계산
        now = _time.monotonic()
        dt = now - self._last_time if self._last_time else 0.016
        self._last_time = now
        self._highlight.update(dt)

        # 더블라인 배경 박스
        draw_styled_box(
            self.console, self.x, self.y, self.width, self.height,
            title="가능성 선택",
            fg=(255, 255, 255),
            bg=(20, 20, 40),
            title_fg=(255, 255, 100),
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
                # 커서 항목 펄스 하이라이트 배경
                highlight_bg = self._highlight.get_bg_color()
                self.console.draw_rect(
                    self.x + 1, y_pos, self.width - 2, 1,
                    ord(" "), bg=highlight_bg
                )
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
    
    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리 (GameAction 기반 - 키보드/게임패드 통합)

        Returns:
            True면 UI 종료
        """
        if action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.cancelled = True
            play_sfx("ui", "cursor_cancel")
            return True

        elif action == GameAction.MOVE_UP:
            self.cursor_index = max(0, self.cursor_index - 1)
            play_sfx("ui", "cursor_move")

        elif action == GameAction.MOVE_DOWN:
            self.cursor_index = min(len(self.slots) - 1, self.cursor_index + 1)
            play_sfx("ui", "cursor_move")

        elif action == GameAction.CONFIRM:
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

        elif action == GameAction.INTERACT:
            # 다중 선택 확정 (TAB/게임패드 Y버튼)
            if self.action == "summon_dual" and len(self.selected_indices) >= 2:
                self.confirmed = True
                play_sfx("ui", "cursor_select")
                return True

        return False

    def handle_number_key(self, key: tcod.event.KeyDown) -> bool:
        """숫자키 직접 선택 (키보드 전용)"""
        if key.sym >= tcod.event.KeySym.N1 and key.sym <= tcod.event.KeySym.N9:
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
    import time
    import pygame
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

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    # 메인 루프 (비블로킹 - 게임패드 폴링 지원)
    while True:
        ui.render()
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            pygame.event.pump()
        except Exception:
            pass

        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            if isinstance(event, tcod.event.KeyDown):
                # 숫자키 직접 선택 (키보드 전용)
                if ui.handle_number_key(event):
                    return ui.get_result()
                # GameAction 변환
                kb_action = unified_input_handler.process_tcod_event(event)
                if kb_action:
                    keyboard_processed = True
                    if ui.handle_input(kb_action):
                        return ui.get_result()
            elif isinstance(event, tcod.event.Quit):
                return None

        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if ui.handle_input(gamepad_action):
                    return ui.get_result()

        # CPU 사용률 방지
        time.sleep(0.016)
