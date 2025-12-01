"""
채집 상호작용 UI

던전 탐험 중 채집 포인트와 상호작용
"""

import tcod.console
import tcod.event
from typing import Optional, Dict

from src.gathering.harvestable import HarvestableObject
from src.gathering.ingredient import IngredientDatabase
from src.equipment.inventory import Inventory
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("gathering_ui")

# AI 스펙테이터 모드 플래그 (전역)
_is_ai_spectate_mode = False

def set_ai_spectate_mode(is_ai: bool):
    """AI 스펙테이터 모드 설정"""
    global _is_ai_spectate_mode
    _is_ai_spectate_mode = is_ai

def is_ai_spectate_mode() -> bool:
    """현재 AI 스펙테이터 모드 여부"""
    global _is_ai_spectate_mode
    return _is_ai_spectate_mode


def harvest_object(
    console: tcod.console.Console,
    context: tcod.context.Context,
    harvestable: HarvestableObject,
    inventory: Inventory,
    exploration=None
) -> bool:
    """
    채집 오브젝트 수확

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        harvestable: 채집 오브젝트
        inventory: 인벤토리
        exploration: 탐험 시스템 (멀티플레이어 동기화용)

    Returns:
        채집 성공 여부
    """
    # 멀티플레이: 플레이어 ID 가져오기
    player_id = None
    if exploration and hasattr(exploration, 'local_player_id'):
        player_id = exploration.local_player_id

    # AI 스펙테이터 모드인지 확인 (전역 플래그 + 객체 감지)
    is_ai_mode = (is_ai_spectate_mode() or
                  (exploration is not None and
                   ('AI' in str(type(exploration).__name__) or
                    hasattr(exploration, 'is_ai_spectate_mode'))))

    # 채집 가능 여부 확인 (플레이어별)
    if not harvestable.can_harvest(player_id):
        show_message(console, context, "이미 채집한 곳입니다.", Colors.GRAY, auto_dismiss=is_ai_mode)
        return False

    # 채집 SFX
    from src.audio import play_sfx
    play_sfx("world", "gathering")

    # 채집 실행 (멀티플레이에서는 개인보상이므로 플레이어별로 독립적으로 채집 가능)
    results = harvestable.harvest(player_id)

    if not results:
        show_message(console, context, "채집할 것이 없습니다.", Colors.GRAY, auto_dismiss=is_ai_mode)
        return False

    # 채집 결과 메시지
    message_lines = [
        f"{harvestable.object_type.display_name}에서 재료를 채집했습니다!",
        ""
    ]

    # 인벤토리에 추가
    added_items = []
    failed_items = []

    for ingredient_id, quantity in results.items():
        ingredient = IngredientDatabase.get_ingredient(ingredient_id)
        if ingredient:
            # 수량만큼 추가 시도
            for _ in range(quantity):
                if inventory.add_item(ingredient):
                    added_items.append(ingredient.name)
                else:
                    failed_items.append(ingredient.name)
                    logger.warning(f"인벤토리 가득 참! {ingredient.name} 추가 실패")

    # 성공한 아이템 표시
    if added_items:
        # 중복 제거 및 개수 계산
        item_counts = {}
        for item_name in added_items:
            item_counts[item_name] = item_counts.get(item_name, 0) + 1

        message_lines.append("획득:")
        for item_name, count in item_counts.items():
            message_lines.append(f"  {item_name} x{count}")

    # 실패한 아이템 표시
    if failed_items:
        message_lines.append("")
        message_lines.append("인벤토리 가득 참! 획득 실패:")
        # 중복 제거 및 개수 계산
        item_counts = {}
        for item_name in failed_items:
            item_counts[item_name] = item_counts.get(item_name, 0) + 1
        for item_name, count in item_counts.items():
            message_lines.append(f"  {item_name} x{count}")

    # 메시지 표시 (AI 모드면 자동으로 진행)
    show_multi_line_message(console, context, message_lines, Colors.UI_TEXT_SELECTED, auto_dismiss=is_ai_mode)

    logger.info(f"채집 완료: {harvestable.object_type.display_name}")
    return True


def show_gathering_prompt(
    console: tcod.console.Console,
    context: tcod.context.Context,
    harvestable: HarvestableObject
) -> bool:
    """
    채집 확인 프롬프트

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        harvestable: 채집 오브젝트

    Returns:
        채집 여부 (True/False)
    """
    if harvestable.harvested:
        return False

    # 프롬프트 메시지
    message = f"{harvestable.object_type.display_name}을(를) 채집하시겠습니까?"
    sub_message = "Z: 채집  X: 취소"

    # 박스 크기
    box_width = max(len(message), len(sub_message)) + 10
    box_height = 8
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2


    while True:
        # 배경 그리기
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "채집",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 메시지
        console.print(
            box_x + (box_width - len(message)) // 2,
            box_y + 3,
            message,
            fg=Colors.UI_TEXT
        )

        console.print(
            box_x + (box_width - len(sub_message)) // 2,
            box_y + 5,
            sub_message,
            fg=Colors.GRAY
        )

        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass

        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                keyboard_processed = True
                if action == GameAction.CONFIRM:
                    return True
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    play_sfx("ui", "cursor_cancel")
                    return False

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return False

        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action == GameAction.CONFIRM:
                return True
            elif gamepad_action == GameAction.CANCEL or gamepad_action == GameAction.ESCAPE:
                play_sfx("ui", "cursor_cancel")
                return False

        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)


def show_message(
    console: tcod.console.Console,
    context: tcod.context.Context,
    message: str,
    color: tuple = Colors.UI_TEXT,
    auto_dismiss: bool = False
):
    """
    단일 메시지 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        message: 메시지
        color: 색상
        auto_dismiss: AI 모드일 때 자동으로 진행
    """
    show_multi_line_message(console, context, [message], color, auto_dismiss=auto_dismiss)


def show_multi_line_message(
    console: tcod.console.Console,
    context: tcod.context.Context,
    messages: list,
    color: tuple = Colors.UI_TEXT,
    auto_dismiss: bool = False
):
    """
    여러 줄 메시지 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        messages: 메시지 리스트
        color: 색상
        auto_dismiss: AI 모드일 때 자동으로 진행 (입력 대기 없음)
    """
    # auto_dismiss가 True면 메시지를 표시하지 않고 바로 반환
    if auto_dismiss:
        return

    import time
    import pygame
    
    # 이벤트 큐 비우기 + 딜레이 + 다시 비우기
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()
    
    # 딜레이 후 다시 이벤트 큐 비우기
    time.sleep(0.2)
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()

    # 박스 크기
    max_width = max(len(msg) for msg in messages)
    box_width = max_width + 10
    box_height = len(messages) + 6
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2
    
    # 입력 허용 시작 시간 (1초 후부터 입력 허용)
    start_time = time.time()
    input_delay = 1.0

    while True:
        # 배경 그리기
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "알림",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 메시지 출력
        y = box_y + 2
        for msg in messages:
            console.print(
                box_x + 2,
                y,
                msg,
                fg=color
            )
            y += 1

        # 확인 안내
        confirm_msg = "Z: 확인"
        console.print(
            box_x + (box_width - len(confirm_msg)) // 2,
            box_y + box_height - 2,
            confirm_msg,
            fg=Colors.GRAY
        )

        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            pygame.event.pump()
        except:
            pass

        # 입력 허용 시간 체크
        can_accept_input = (time.time() - start_time) >= input_delay

        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            if can_accept_input:
                action = unified_input_handler.process_tcod_event(event)

                if action:
                    keyboard_processed = True
                    if action in [GameAction.CONFIRM, GameAction.CANCEL, GameAction.ESCAPE]:
                        if action != GameAction.CONFIRM:
                            play_sfx("ui", "cursor_cancel")
                        return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return

        # 게임패드 입력 처리
        if can_accept_input and not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action in [GameAction.CONFIRM, GameAction.CANCEL, GameAction.ESCAPE]:
                if gamepad_action != GameAction.CONFIRM:
                    play_sfx("ui", "cursor_cancel")
                return

        # CPU 사용률 낮추기
        time.sleep(0.01)
