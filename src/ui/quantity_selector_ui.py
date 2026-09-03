"""
수량 선택 UI

아이템 보관/출고 시 수량을 선택하는 UI
"""

import tcod.console
import tcod.event
from typing import Optional

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion
from src.ui.visual_tokens import rgb
from src.audio import play_sfx


def quantity_pointer_regions(console_width: int) -> tuple[PointerRegion, ...]:
    bar_width = 30
    bar_x = (console_width - bar_width) // 2
    return (
        PointerRegion("quantity_bar", bar_x, 15, bar_width, 1, tooltip="드래그하거나 휠로 수량을 조절합니다."),
        PointerRegion("confirm", bar_x, 18, 12, 1, command=GameAction.CONFIRM, tooltip="선택한 수량을 확정합니다."),
        PointerRegion("cancel", bar_x + 18, 18, 12, 1, command=GameAction.CANCEL, tooltip="수량 선택을 취소합니다."),
    )


def handle_quantity_pointer_event(
    event: PointerEvent,
    selected_quantity: int,
    max_quantity: int,
    console_width: int,
) -> tuple[int, tuple[str, int | None] | None]:
    dispatcher = PointerDispatcher(quantity_pointer_regions(console_width))
    result = dispatcher.dispatch(event)
    region = dispatcher.region_at(event.position)
    if event.kind is PointerEventKind.WHEEL:
        step = 1 if event.wheel_delta > 0 else -1
        return max(1, min(max_quantity, selected_quantity + step)), None
    if event.kind in (PointerEventKind.DRAG_START, PointerEventKind.DRAG_MOVE, PointerEventKind.DRAG_END) and region:
        relative_x = max(0, min(region.width - 1, event.position.tile[0] - region.x))
        quantity = 1 + int(round((relative_x / max(1, region.width - 1)) * (max_quantity - 1)))
        return max(1, min(max_quantity, quantity)), None
    if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
        return selected_quantity, ("cancel", None)
    if event.kind is PointerEventKind.CLICK and region and region.region_id == "quantity_bar":
        quantity, _result = handle_quantity_pointer_event(
            PointerEventKind.DRAG_MOVE.at(tile=event.position.tile, pixel=event.position.pixel, button=PointerButton.LEFT),
            selected_quantity,
            max_quantity,
            console_width,
        )
        return quantity, None
    if result.action is GameAction.CONFIRM:
        return selected_quantity, ("confirm", selected_quantity)
    if result.action is GameAction.CANCEL:
        return selected_quantity, ("cancel", None)
    return selected_quantity, None


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
    
    # 콘솔 크기 확인 (안전성을 위해)
    try:
        console_width = console.width
        console_height = console.height
    except (AttributeError, TypeError):
        # 기본값 사용
        console_width = 80
        console_height = 50

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        # 배경 클리어 및 단순 배경 렌더링
        console.clear()
        # 어두운 배경색으로 전체 채우기
        bg_color = (10, 10, 20)
        try:
            for y in range(min(console_height, console.height)):
                console.draw_rect(0, y, min(console_width, console.width), 1, ord(' '), bg=bg_color)
        except (IndexError, ValueError, TypeError):
            # 오류 발생 시 단순히 clear만 사용
            pass
        
        # 제목
        title = f"=== {item_name} 수량 선택 ==="
        console.print((console_width - len(title)) // 2, 10, title, fg=(255, 215, 0))
        
        # 현재 수량 표시
        quantity_text = f"수량: {selected_quantity} / {max_quantity}"
        console.print((console_width - len(quantity_text)) // 2, 13, quantity_text, fg=(255, 255, 255))
        
        # 게이지
        bar_width = 30
        filled = int((selected_quantity / max_quantity) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        console.print((console_width - bar_width) // 2, 15, bar, fg=rgb("status.success"))
        
        # 도움말
        help_lines = [
            "←→: 수량 조절 (1개씩)",
            "Shift+←→: 수량 조절 (10개씩)",
            "Z: 확인  X: 취소"
        ]
        y = 18
        for line in help_lines:
            console.print((console_width - len(line)) // 2, y, line, fg=Colors.GRAY)
            y += 1
        
        context.present(console)
        
        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass
        
        # 입력 처리 함수
        def process_action(action):
            nonlocal selected_quantity
            step = 1
            if action == GameAction.MOVE_LEFT:
                selected_quantity = max(1, selected_quantity - step)
                play_sfx("ui", "cursor_move")
            elif action == GameAction.MOVE_RIGHT:
                selected_quantity = min(max_quantity, selected_quantity + step)
                play_sfx("ui", "cursor_move")
            elif action == GameAction.MOVE_UP:
                selected_quantity = min(max_quantity, selected_quantity + 10)
                play_sfx("ui", "cursor_move")
            elif action == GameAction.MOVE_DOWN:
                selected_quantity = max(1, selected_quantity - 10)
                play_sfx("ui", "cursor_move")
            elif action == GameAction.CONFIRM:
                play_sfx("ui", "confirm")
                return ("confirm", selected_quantity)
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                play_sfx("ui", "cursor_cancel")
                return ("cancel", None)
            return None
        
        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                keyboard_processed = True
                result = process_action(action)
                if result:
                    return result[1]

            if hasattr(event, "tile") and hasattr(event, "pixel"):
                pointer_event = unified_input_handler.process_pointer_event(event)
                if pointer_event is not None:
                    selected_quantity, pointer_result = handle_quantity_pointer_event(
                        pointer_event,
                        selected_quantity,
                        max_quantity,
                        console_width,
                    )
                    if pointer_result:
                        return pointer_result[1]

            if isinstance(event, tcod.event.Quit):
                return None
        
        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                result = process_action(gamepad_action)
                if result:
                    return result[1]
        
        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)
