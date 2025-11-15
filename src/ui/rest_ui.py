"""
휴식/캠프 UI

플레이어가 던전에서 휴식을 취하고 요리할 수 있음
"""

import tcod.console
import tcod.event
from typing import List, Any, Optional

from src.equipment.inventory import Inventory
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.ui.cooking_ui import open_cooking_pot
from src.core.logger import get_logger


logger = get_logger("rest_ui")


def open_rest_menu(
    console: tcod.console.Console,
    context: tcod.context.Context,
    party: List[Any],
    inventory: Inventory
) -> str:
    """
    휴식 메뉴 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party: 파티 멤버
        inventory: 인벤토리

    Returns:
        선택한 행동 ("rest", "cook", "cancel")
    """
    menu_items = [
        "휴식하기 (HP/MP 회복)",
        "요리하기",
        "취소"
    ]

    cursor = 0
    handler = InputHandler()

    logger.info("휴식 메뉴 열기")

    while True:
        # 화면 지우기
        console.clear()

        # 제목
        title = "⛺ 캠프"
        console.print(
            (console.width - len(title)) // 2,
            5,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 메뉴 아이템
        start_y = 10
        for i, item in enumerate(menu_items):
            is_selected = (i == cursor)
            prefix = "►" if is_selected else " "

            color = Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT

            console.print(
                (console.width - len(item) - 2) // 2,
                start_y + i * 2,
                f"{prefix} {item}",
                fg=color
            )

        # 파티 상태 표시
        party_y = console.height - 10
        console.print(
            5, party_y,
            "파티 상태:",
            fg=Colors.UI_TEXT
        )

        for i, member in enumerate(party):
            name = getattr(member, 'name', 'Unknown')
            hp = getattr(member, 'current_hp', 0)
            max_hp = getattr(member, 'max_hp', 1)
            mp = getattr(member, 'current_mp', 0)
            max_mp = getattr(member, 'max_mp', 1)

            hp_percent = (hp / max_hp * 100) if max_hp > 0 else 0
            hp_color = Colors.UI_TEXT
            if hp_percent < 30:
                hp_color = (255, 100, 100)
            elif hp_percent < 60:
                hp_color = (255, 255, 100)

            console.print(
                7, party_y + 1 + i,
                f"{name}: HP {hp}/{max_hp}  MP {mp}/{max_mp}",
                fg=hp_color
            )

        # 도움말
        help_text = "↑↓: 선택  Z: 확인  X: 취소"
        console.print(
            (console.width - len(help_text)) // 2,
            console.height - 2,
            help_text,
            fg=Colors.GRAY
        )

        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action == GameAction.MOVE_UP:
                cursor = max(0, cursor - 1)
            elif action == GameAction.MOVE_DOWN:
                cursor = min(len(menu_items) - 1, cursor + 1)
            elif action == GameAction.CONFIRM:
                if cursor == 0:
                    # 휴식
                    perform_rest(console, context, party)
                    logger.info("휴식 완료")
                    return "rest"
                elif cursor == 1:
                    # 요리
                    cooked_food = open_cooking_pot(console, context, inventory)
                    if cooked_food:
                        logger.info(f"요리 완료: {cooked_food.name}")
                        # 요리 결과를 인벤토리에 추가 (Consumable 아이템으로 변환)
                        from src.equipment.item_system import Consumable, ItemRarity, ItemType
                        food_item = Consumable(
                            item_id=cooked_food.get('recipe_id', 'food'),
                            name=cooked_food.get('name', '요리'),
                            description=f"요리된 음식: {cooked_food.get('quality', 'normal')}",
                            item_type=ItemType.CONSUMABLE,
                            rarity=ItemRarity.COMMON,
                            effect_type="heal_hp",
                            effect_value=cooked_food.get('effects', {}).get('hp_heal', 50)
                        )
                        try:
                            inventory.add_item(food_item)
                            logger.info(f"인벤토리에 추가: {food_item.name}")
                        except Exception as e:
                            logger.warning(f"인벤토리 추가 실패: {e}")
                    return "cook"
                elif cursor == 2:
                    # 취소
                    logger.info("휴식 취소")
                    return "cancel"
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                logger.info("휴식 취소")
                return "cancel"

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return "cancel"


def perform_rest(
    console: tcod.console.Console,
    context: tcod.context.Context,
    party: List[Any]
):
    """
    휴식 실행 (HP/MP 회복)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party: 파티 멤버
    """
    # 각 멤버 HP/MP 50% 회복
    recovery_messages = ["휴식을 취했습니다.", ""]

    for member in party:
        name = getattr(member, 'name', 'Unknown')

        # HP 회복
        if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
            hp_before = member.current_hp
            recovery_amount = member.max_hp // 2  # 50% 회복
            member.current_hp = min(member.max_hp, member.current_hp + recovery_amount)
            hp_recovered = member.current_hp - hp_before

            if hp_recovered > 0:
                recovery_messages.append(f"{name}: HP +{hp_recovered}")

        # MP 회복
        if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
            mp_before = member.current_mp
            recovery_amount = member.max_mp // 2  # 50% 회복
            member.current_mp = min(member.max_mp, member.current_mp + recovery_amount)
            mp_recovered = member.current_mp - mp_before

            if mp_recovered > 0:
                recovery_messages.append(f"{name}: MP +{mp_recovered}")

    # 메시지 표시
    show_message_box(console, context, recovery_messages)


def show_message_box(
    console: tcod.console.Console,
    context: tcod.context.Context,
    messages: List[str]
):
    """
    메시지 박스 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        messages: 메시지 리스트
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
            "휴식 결과",
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
                fg=Colors.UI_TEXT
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
