"""
게임 내 메뉴 시스템

탐험 중 M키로 접근 가능한 메인 메뉴
"""

from enum import Enum
from typing import Optional, List
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.UI)


class MenuOption(Enum):
    """메뉴 옵션"""
    PARTY_STATUS = "party_status"
    INVENTORY = "inventory"
    SHOP = "shop"  # 골드 상점
    SAVE_GAME = "save"
    LOAD_GAME = "load"
    OPTIONS = "options"
    RETURN = "return"
    QUIT = "quit"


class GameMenu:
    """게임 내 메뉴"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0
        self.menu_options = [
            ("파티 상태", MenuOption.PARTY_STATUS),
            ("인벤토리", MenuOption.INVENTORY),
            ("상점", MenuOption.SHOP),
            ("게임 저장", MenuOption.SAVE_GAME),
            ("게임 불러오기", MenuOption.LOAD_GAME),
            ("설정", MenuOption.OPTIONS),
            ("돌아가기", MenuOption.RETURN),
        ]

    def handle_input(self, action: GameAction) -> Optional[MenuOption]:
        """
        입력 처리

        Returns:
            선택된 메뉴 옵션, 없으면 None
        """
        if action == GameAction.MOVE_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = min(len(self.menu_options) - 1, self.selected_index + 1)
        elif action == GameAction.CONFIRM or action == GameAction.MENU:
            # Enter 또는 M키로 선택
            return self.menu_options[self.selected_index][1]
        elif action == GameAction.ESCAPE:
            # ESC로 메뉴 닫기
            return MenuOption.RETURN

        return None

    def render(self, console: tcod.console.Console):
        """메뉴 렌더링"""
        # 반투명 배경 (어두운 오버레이)
        for y in range(self.screen_height):
            for x in range(self.screen_width):
                console.print(x, y, " ", bg=(0, 0, 0))

        # 메뉴 박스
        menu_width = 40
        menu_height = len(self.menu_options) + 6
        menu_x = (self.screen_width - menu_width) // 2
        menu_y = (self.screen_height - menu_height) // 2

        # 박스 테두리
        self._draw_box(console, menu_x, menu_y, menu_width, menu_height)

        # 제목
        title = "=== 메뉴 ==="
        console.print(
            menu_x + (menu_width - len(title)) // 2,
            menu_y + 2,
            title,
            fg=(255, 255, 100)
        )

        # 메뉴 옵션
        for i, (label, _) in enumerate(self.menu_options):
            y = menu_y + 4 + i
            if i == self.selected_index:
                # 선택된 항목
                console.print(menu_x + 2, y, "►", fg=(255, 255, 100))
                console.print(menu_x + 4, y, label, fg=(255, 255, 100))
            else:
                # 일반 항목
                console.print(menu_x + 4, y, label, fg=(200, 200, 200))

        # 조작법
        help_text = "↑↓: 선택  Enter/M: 확인  ESC: 닫기"
        console.print(
            menu_x + (menu_width - len(help_text)) // 2,
            menu_y + menu_height - 2,
            help_text,
            fg=(150, 150, 150)
        )

    def _draw_box(self, console: tcod.console.Console, x: int, y: int, width: int, height: int):
        """박스 테두리 그리기"""
        # 모서리
        console.print(x, y, "┌", fg=(200, 200, 200))
        console.print(x + width - 1, y, "┐", fg=(200, 200, 200))
        console.print(x, y + height - 1, "└", fg=(200, 200, 200))
        console.print(x + width - 1, y + height - 1, "┘", fg=(200, 200, 200))

        # 가로선
        for i in range(1, width - 1):
            console.print(x + i, y, "─", fg=(200, 200, 200))
            console.print(x + i, y + height - 1, "─", fg=(200, 200, 200))

        # 세로선
        for i in range(1, height - 1):
            console.print(x, y + i, "│", fg=(200, 200, 200))
            console.print(x + width - 1, y + i, "│", fg=(200, 200, 200))

        # 내부 채우기
        for dy in range(1, height - 1):
            for dx in range(1, width - 1):
                console.print(x + dx, y + dy, " ", bg=(20, 20, 40))


def open_game_menu(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory=None,
    party=None,
    exploration=None
) -> MenuOption:
    """
    게임 메뉴 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리 (인벤토리 메뉴용)
        party: 파티 (파티 상태 메뉴용)
        exploration: 탐험 상태 (저장용)

    Returns:
        선택된 메뉴 옵션
    """
    menu = GameMenu(console.width, console.height)
    handler = InputHandler()

    logger.info("게임 메뉴 열림")

    while True:
        # 렌더링
        menu.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                result = menu.handle_input(action)
                if result:
                    logger.info(f"메뉴 선택: {result.value}")

                    # 하위 메뉴로 이동
                    if result == MenuOption.INVENTORY:
                        if inventory is not None and party is not None:
                            from src.ui.inventory_ui import open_inventory
                            open_inventory(console, context, inventory, party)
                            # 인벤토리에서 돌아온 후 메뉴 계속
                            continue
                        else:
                            show_message(console, context, "인벤토리를 열 수 없습니다.")
                            continue

                    elif result == MenuOption.PARTY_STATUS and party:
                        open_party_status_menu(console, context, party)
                        # 파티 상태에서 돌아온 후 메뉴 계속
                        continue

                    elif result == MenuOption.SHOP:
                        if inventory is not None and exploration is not None:
                            from src.ui.gold_shop_ui import open_gold_shop
                            floor_level = exploration.floor_number if hasattr(exploration, 'floor_number') else 1
                            open_gold_shop(console, context, inventory, floor_level)
                            # 상점에서 돌아온 후 메뉴 계속
                            continue
                        else:
                            show_message(console, context, "상점을 열 수 없습니다.")
                            continue

                    elif result == MenuOption.SAVE_GAME:
                        if exploration is None:
                            show_message(console, context, "저장할 수 없습니다.")
                            continue

                        from src.ui.save_load_ui import show_save_screen
                        from src.persistence.save_system import (
                            serialize_party_member, serialize_dungeon, serialize_item
                        )

                        # 게임 상태 직렬화
                        # 디버그: 인벤토리 확인
                        logger.warning(f"[SAVE] 저장 전 인벤토리: {inventory}")
                        logger.warning(f"[SAVE] 인벤토리 골드: {inventory.gold if inventory and hasattr(inventory, 'gold') else 'N/A'}G")

                        game_state = {
                            "party": [serialize_party_member(m) for m in party] if party else [],
                            "floor_number": exploration.floor_number,
                            "dungeon": serialize_dungeon(exploration.dungeon),
                            "player_position": {
                                "x": exploration.player.x,
                                "y": exploration.player.y
                            },
                            "inventory": {
                                "gold": inventory.gold if inventory and hasattr(inventory, 'gold') else 0,
                                "items": [serialize_item(slot.item) for slot in inventory.slots] if inventory and hasattr(inventory, 'slots') else []
                            },
                            "keys": exploration.player_keys if hasattr(exploration, 'player_keys') else [],
                            # 게임 통계 (로그라이크 정산용)
                            "enemies_defeated": exploration.game_stats.get("enemies_defeated", 0),
                            "max_floor_reached": exploration.game_stats.get("max_floor_reached", exploration.floor_number),
                            "total_gold_earned": exploration.game_stats.get("total_gold_earned", 0),
                            "total_exp_earned": exploration.game_stats.get("total_exp_earned", 0),
                            "save_slot": exploration.game_stats.get("save_slot", None),
                        }

                        logger.warning(f"[SAVE] game_state['inventory']: {game_state['inventory']}")

                        success = show_save_screen(console, context, game_state)
                        if success:
                            show_message(console, context, "저장 완료!")
                        continue

                    elif result == MenuOption.LOAD_GAME:
                        from src.ui.save_load_ui import show_load_screen
                        game_state = show_load_screen(console, context)
                        if game_state:
                            # 로드 성공 - 메뉴 닫고 게임 재시작
                            return MenuOption.LOAD_GAME
                        continue

                    elif result == MenuOption.OPTIONS:
                        from src.ui.settings_ui import open_settings
                        open_settings(console, context)
                        # 설정에서 돌아온 후 메뉴 계속
                        continue

                    elif result == MenuOption.RETURN:
                        return result

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return MenuOption.QUIT


def open_party_status_menu(
    console: tcod.console.Console,
    context: tcod.context.Context,
    party: List
):
    """
    파티 상태 화면 (캐릭터 선택 가능)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party: 파티 멤버 리스트
    """
    from src.ui.gauge_renderer import GaugeRenderer
    gauge_renderer = GaugeRenderer()
    handler = InputHandler()

    logger.info("파티 상태 화면 열림")

    selected_index = 0

    while True:
        console.clear()

        # 제목
        title = "=== 파티 상태 ==="
        console.print((console.width - len(title)) // 2, 2, title, fg=(255, 255, 100))

        # 파티원 정보 (간략)
        y = 5
        for i, member in enumerate(party):
            # 선택 커서
            if i == selected_index:
                console.print(3, y, "►", fg=(255, 255, 100))

            # 이름과 직업
            name_color = (255, 255, 255) if i == selected_index else (200, 200, 200)
            console.print(5, y, f"{i+1}. {member.name}", fg=name_color)
            console.print(30, y, f"Lv.{member.level}", fg=name_color)

            if hasattr(member, 'job_name'):
                console.print(40, y, member.job_name, fg=(150, 200, 255))
            elif hasattr(member, 'character_class'):
                console.print(40, y, member.character_class, fg=(150, 200, 255))

            y += 1

            # HP
            if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                console.print(7, y, "HP:", fg=(200, 200, 200))
                gauge_renderer.render_bar(
                    console, 11, y, 15,
                    member.current_hp, member.max_hp, show_numbers=True
                )
                y += 1

            y += 1  # 다음 파티원과 간격

        # 조작법
        console.print(
            5,
            console.height - 3,
            "↑↓: 선택  Enter: 상세 정보  ESC: 돌아가기",
            fg=(180, 180, 180)
        )

        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action == GameAction.MOVE_UP:
                selected_index = max(0, selected_index - 1)
            elif action == GameAction.MOVE_DOWN:
                selected_index = min(len(party) - 1, selected_index + 1)
            elif action == GameAction.CONFIRM:
                # 선택한 캐릭터 상세 정보 표시
                show_character_detail(console, context, party[selected_index])
            elif action == GameAction.ESCAPE or action == GameAction.MENU:
                return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return


def show_character_detail(
    console: tcod.console.Console,
    context: tcod.context.Context,
    character
):
    """
    캐릭터 상세 정보 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        character: 캐릭터 객체
    """
    from src.ui.gauge_renderer import GaugeRenderer
    gauge_renderer = GaugeRenderer()
    handler = InputHandler()

    while True:
        console.clear()

        # 제목
        title = f"=== {character.name} 상세 정보 ==="
        console.print((console.width - len(title)) // 2, 2, title, fg=(255, 255, 100))

        y = 5

        # 기본 정보
        console.print(10, y, f"이름: {character.name}", fg=(255, 255, 255))
        y += 1
        console.print(10, y, f"레벨: {character.level}", fg=(200, 200, 200))
        y += 1

        if hasattr(character, 'job_name'):
            console.print(10, y, f"직업: {character.job_name}", fg=(150, 200, 255))
        elif hasattr(character, 'character_class'):
            console.print(10, y, f"직업: {character.character_class}", fg=(150, 200, 255))
        y += 2

        # HP
        if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
            console.print(10, y, "HP:", fg=(200, 200, 200))
            gauge_renderer.render_bar(
                console, 14, y, 30,
                character.current_hp, character.max_hp, show_numbers=True
            )
            y += 1

        # MP
        if hasattr(character, 'current_mp') and hasattr(character, 'max_mp'):
            console.print(10, y, "MP:", fg=(200, 200, 200))
            gauge_renderer.render_bar(
                console, 14, y, 30,
                character.current_mp, character.max_mp, show_numbers=True,
                color_gradient=False, custom_color=(100, 150, 255)
            )
            y += 2

        # 스탯 상세
        console.print(10, y, "[ 스탯 ]", fg=(255, 200, 100))
        y += 1

        if hasattr(character, 'strength'):
            console.print(12, y, f"STR (힘):      {character.strength:3d}", fg=(255, 180, 180))
            y += 1
            console.print(12, y, f"DEF (방어):    {character.defense:3d}", fg=(180, 180, 255))
            y += 1
            console.print(12, y, f"MAG (마력):    {character.magic:3d}", fg=(200, 150, 255))
            y += 1
            console.print(12, y, f"SPR (정신):    {character.spirit:3d}", fg=(150, 255, 200))
            y += 1
            console.print(12, y, f"SPD (속도):    {character.speed:3d}", fg=(255, 255, 150))
            y += 1
            console.print(12, y, f"LUK (행운):    {character.luck:3d}", fg=(255, 200, 255))
            y += 2

        # 경험치
        if hasattr(character, 'experience') and hasattr(character, 'experience_to_next_level'):
            console.print(10, y, "[ 경험치 ]", fg=(255, 200, 100))
            y += 1
            exp_ratio = character.experience / character.experience_to_next_level if character.experience_to_next_level > 0 else 0
            exp_bar, exp_color = gauge_renderer.render_percentage_bar(
                exp_ratio, width=30, show_percent=False
            )
            console.print(12, y, f"{exp_bar}", fg=(100, 255, 100))
            y += 1
            console.print(12, y, f"{character.experience} / {character.experience_to_next_level} EXP", fg=(150, 255, 150))
            y += 2

        # 장비 정보
        if hasattr(character, 'equipment'):
            console.print(10, y, "[ 장비 ]", fg=(255, 200, 100))
            y += 1
            if character.equipment:
                for slot, item in character.equipment.items():
                    if item:
                        console.print(12, y, f"{slot}: {item.name}", fg=(200, 200, 200))
                        y += 1
            else:
                console.print(12, y, "장비 없음", fg=(150, 150, 150))
                y += 1

        # 조작법
        console.print(
            5,
            console.height - 3,
            "ESC: 돌아가기",
            fg=(180, 180, 180)
        )

        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action == GameAction.ESCAPE or action == GameAction.MENU or action == GameAction.CONFIRM:
                return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return


def show_message(
    console: tcod.console.Console,
    context: tcod.context.Context,
    message: str
):
    """
    간단한 메시지 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        message: 표시할 메시지
    """
    handler = InputHandler()

    # 메시지 박스
    box_width = min(60, len(message) + 4)
    box_height = 7
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2

    while True:
        # 기존 화면 위에 오버레이
        # (기존 화면 내용은 유지)

        # 반투명 배경
        for dy in range(box_height):
            for dx in range(box_width):
                console.print(box_x + dx, box_y + dy, " ", bg=(0, 0, 0))

        # 박스 테두리
        console.print(box_x, box_y, "┌", fg=(200, 200, 200))
        console.print(box_x + box_width - 1, box_y, "┐", fg=(200, 200, 200))
        console.print(box_x, box_y + box_height - 1, "└", fg=(200, 200, 200))
        console.print(box_x + box_width - 1, box_y + box_height - 1, "┘", fg=(200, 200, 200))

        for i in range(1, box_width - 1):
            console.print(box_x + i, box_y, "─", fg=(200, 200, 200))
            console.print(box_x + i, box_y + box_height - 1, "─", fg=(200, 200, 200))

        for i in range(1, box_height - 1):
            console.print(box_x, box_y + i, "│", fg=(200, 200, 200))
            console.print(box_x + box_width - 1, box_y + i, "│", fg=(200, 200, 200))

        # 내부 배경
        for dy in range(1, box_height - 1):
            for dx in range(1, box_width - 1):
                console.print(box_x + dx, box_y + dy, " ", bg=(20, 20, 40))

        # 메시지
        console.print(
            box_x + (box_width - len(message)) // 2,
            box_y + 2,
            message,
            fg=(255, 255, 255)
        )

        # 확인 안내
        help_text = "아무 키나 누르세요..."
        console.print(
            box_x + (box_width - len(help_text)) // 2,
            box_y + 4,
            help_text,
            fg=(150, 150, 150)
        )

        context.present(console)

        # 아무 키나 누르면 닫기
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.KeyDown):
                return
            if isinstance(event, tcod.event.Quit):
                return
