"""
수량 선택 UI

아이템 보관/출고 시 수량을 선택하는 UI
"""

import tcod.console
import tcod.event
from typing import Optional

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.audio import play_sfx


def select_quantity(
    console: tcod.console.Console,
    context: tcod.context.Context,
    item_name: str,
    max_quantity: int
) -> Optional[int]:
    """
    수량 선택 UI
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        item_name: 아이템 이름
        max_quantity: 최대 수량
        
    Returns:
        선택된 수량, 취소 시 None
    """
    selected_quantity = 1
    handler = InputHandler()
    
    while True:
        render_space_background(console, console.width, console.height)
        
        # 제목
        title = f"=== {item_name} 수량 선택 ==="
        console.print((console.width - len(title)) // 2, 10, title, fg=(255, 215, 0))
        
        # 현재 수량 표시
        quantity_text = f"수량: {selected_quantity} / {max_quantity}"
        console.print((console.width - len(quantity_text)) // 2, 13, quantity_text, fg=(255, 255, 255))
        
        # 게이지
        bar_width = 30
        filled = int((selected_quantity / max_quantity) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        console.print((console.width - bar_width) // 2, 15, bar, fg=(100, 200, 100))
        
        # 도움말
        help_lines = [
            "←→: 수량 조절 (1개씩)",
            "Shift+←→: 수량 조절 (10개씩)",
            "Z: 확인  X: 취소"
        ]
        y = 18
        for line in help_lines:
            console.print((console.width - len(line)) // 2, y, line, fg=Colors.GRAY)
            y += 1
        
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.KeyDown):
                shift_pressed = event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT)
                step = 10 if shift_pressed else 1
                
                if event.sym == tcod.event.KeySym.LEFT:
                    selected_quantity = max(1, selected_quantity - step)
                    play_sfx("ui", "cursor_move")
                elif event.sym == tcod.event.KeySym.RIGHT:
                    selected_quantity = min(max_quantity, selected_quantity + step)
                    play_sfx("ui", "cursor_move")
                elif event.sym == tcod.event.KeySym.z:
                    play_sfx("ui", "confirm")
                    return selected_quantity
                elif event.sym == tcod.event.KeySym.x or event.sym == tcod.event.KeySym.ESCAPE:
                    play_sfx("ui", "cursor_cancel")
                    return None
            
            if isinstance(event, tcod.event.Quit):
                return None
