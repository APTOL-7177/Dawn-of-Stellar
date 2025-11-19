"""
NPC 대화 UI

NPC와의 대화 및 선택지 처리
"""

import tcod.console
import tcod.event
from typing import Optional, List, Dict, Any, Callable

from src.ui.input_handler import InputHandler, GameAction
from src.ui.tcod_display import Colors
from src.core.logger import get_logger

logger = get_logger("npc_dialog")


class NPCChoice:
    """NPC 선택지"""
    def __init__(self, text: str, callback: Callable[[], Any] = None):
        self.text = text
        self.callback = callback


def show_npc_dialog(
    console: tcod.console.Console,
    context: tcod.context.Context,
    npc_name: str,
    dialog_text: str,
    choices: Optional[List[NPCChoice]] = None
) -> Optional[int]:
    """
    NPC 대화 창 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        npc_name: NPC 이름
        dialog_text: 대화 텍스트 (여러 줄 가능, \n으로 구분)
        choices: 선택지 리스트 (None이면 확인만 가능)
    
    Returns:
        선택된 선택지 인덱스 (None이면 취소)
    """
    handler = InputHandler()
    
    # 대화 텍스트를 줄 단위로 분리
    dialog_lines = dialog_text.split('\n')
    
    # 선택지가 있으면 선택 모드, 없으면 확인만 가능
    has_choices = choices and len(choices) > 0
    selected_index = 0 if has_choices else None
    
    # 박스 크기 계산
    max_line_width = max(len(line) for line in dialog_lines) if dialog_lines else 0
    if has_choices:
        max_choice_width = max(len(choice.text) for choice in choices)
        max_line_width = max(max_line_width, max_choice_width)
    
    box_width = min(max_line_width + 10, console.width - 20)
    box_height = len(dialog_lines) + 6
    if has_choices:
        box_height += len(choices) + 1
    
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2
    
    while True:
        # 기존 화면은 이미 렌더링되어 있다고 가정
        # 대화 상자만 오버레이
        
        # 반투명 배경 (TCOD는 직접 투명도 지원하지 않으므로 어두운 배경)
        for dy in range(box_height):
            for dx in range(box_width):
                console.print(box_x + dx, box_y + dy, " ", bg=(20, 20, 20))
        
        # 대화 상자
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            npc_name,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )
        
        # 대화 텍스트 출력
        y = box_y + 2
        for line in dialog_lines:
            # 긴 줄 자동 줄바꿈
            if len(line) > box_width - 4:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 > box_width - 4:
                        if current_line:
                            console.print(box_x + 2, y, current_line[:box_width - 4], fg=Colors.UI_TEXT)
                            y += 1
                        current_line = word
                    else:
                        current_line += (" " if current_line else "") + word
                if current_line:
                    console.print(box_x + 2, y, current_line[:box_width - 4], fg=Colors.UI_TEXT)
                    y += 1
            else:
                console.print(box_x + 2, y, line, fg=Colors.UI_TEXT)
                y += 1
        
        # 선택지 출력
        if has_choices:
            y += 1
            for i, choice in enumerate(choices):
                if i == selected_index:
                    prefix = "> "
                    fg_color = Colors.UI_TEXT_SELECTED
                else:
                    prefix = "  "
                    fg_color = Colors.UI_TEXT
                
                console.print(box_x + 4, y, f"{prefix}{choice.text}", fg=fg_color)
                y += 1
        
        # 안내 메시지
        help_y = box_y + box_height - 2
        if has_choices:
            help_text = "↑↓: 선택  Z: 확인  X: 취소"
        else:
            help_text = "Z: 확인  X: 취소"
        
        console.print(
            box_x + (box_width - len(help_text)) // 2,
            help_y,
            help_text,
            fg=Colors.GRAY
        )
        
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)
            
            if has_choices:
                if action == GameAction.MOVE_UP:
                    selected_index = max(0, selected_index - 1)
                elif action == GameAction.MOVE_DOWN:
                    selected_index = min(len(choices) - 1, selected_index + 1)
                elif action == GameAction.CONFIRM:
                    # 선택된 선택지의 콜백 실행
                    if choices[selected_index].callback:
                        try:
                            choices[selected_index].callback()
                        except Exception as e:
                            logger.error(f"NPC 선택지 콜백 실행 오류: {e}")
                    return selected_index
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    return None
            else:
                if action == GameAction.CONFIRM:
                    return 0
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    return None
            
            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None

