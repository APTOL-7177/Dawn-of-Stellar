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
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger


logger = get_logger("gathering_ui")


def harvest_object(
    console: tcod.console.Console,
    context: tcod.context.Context,
    harvestable: HarvestableObject,
    inventory: Inventory
) -> bool:
    """
    채집 오브젝트 수확

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        harvestable: 채집 오브젝트
        inventory: 인벤토리

    Returns:
        채집 성공 여부
    """
    if harvestable.harvested:
        show_message(console, context, "이미 채집한 곳입니다.", Colors.GRAY)
        return False

    # 채집 실행
    results = harvestable.harvest()

    if not results:
        show_message(console, context, "채집할 것이 없습니다.", Colors.GRAY)
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

    # 메시지 표시
    show_multi_line_message(console, context, message_lines, Colors.UI_TEXT_SELECTED)

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

    handler = InputHandler()

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

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action == GameAction.CONFIRM:
                return True
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                return False

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return False


def show_message(
    console: tcod.console.Console,
    context: tcod.context.Context,
    message: str,
    color: tuple = Colors.UI_TEXT
):
    """
    단일 메시지 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        message: 메시지
        color: 색상
    """
    show_multi_line_message(console, context, [message], color)


def show_multi_line_message(
    console: tcod.console.Console,
    context: tcod.context.Context,
    messages: list,
    color: tuple = Colors.UI_TEXT
):
    """
    여러 줄 메시지 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        messages: 메시지 리스트
        color: 색상
    """
    # 박스 크기
    max_width = max(len(msg) for msg in messages)
    box_width = max_width + 10
    box_height = len(messages) + 6
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2

    handler = InputHandler()

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

        # 입력 대기
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action in [GameAction.CONFIRM, GameAction.CANCEL, GameAction.ESCAPE]:
                return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
