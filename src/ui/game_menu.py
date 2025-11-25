"""
게임 내 메뉴 시스템

탐험 중 M키로 접근 가능한 메인 메뉴
"""

from enum import Enum
from typing import Optional, List
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.ui.tcod_display import render_space_background
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.UI)


class MenuOption(Enum):
    """메뉴 옵션"""
    PARTY_STATUS = "party_status"
    INVENTORY = "inventory"
    QUEST_LIST = "quest_list"  # 퀘스트 목록
    COOKING = "cooking"  # 요리
    SAVE_GAME = "save"
    LOAD_GAME = "load"
    OPTIONS = "options"
    RETURN = "return"
    QUIT = "quit"


class GameMenu:
    """게임 내 메뉴"""

    def __init__(self, screen_width: int, screen_height: int, exploration=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.exploration = exploration
        self.selected_index = 0
        self.menu_options = [
            ("파티 상태", MenuOption.PARTY_STATUS),
            ("인벤토리", MenuOption.INVENTORY),
            ("퀘스트 목록", MenuOption.QUEST_LIST),
            ("게임 저장", MenuOption.SAVE_GAME),
            ("게임 불러오기", MenuOption.LOAD_GAME),
            ("설정", MenuOption.OPTIONS),
            ("돌아가기", MenuOption.RETURN),
        ]
        
        # 마을에서 저장 비활성화 여부 확인
        self.is_town = False
        if exploration and hasattr(exploration, 'is_town'):
            self.is_town = exploration.is_town

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
            selected_option = self.menu_options[self.selected_index][1]
            
            # 마을에서 저장 옵션 비활성화
            if selected_option == MenuOption.SAVE_GAME and self.is_town:
                from src.audio import play_sfx
                play_sfx("ui", "cursor_cancel")
                return None  # 선택 불가능 (메뉴에서 처리)
            
            return selected_option
        elif action == GameAction.ESCAPE:
            # ESC로 메뉴 닫기
            from src.audio import play_sfx
            play_sfx("ui", "cursor_cancel")
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
        for i, (label, option) in enumerate(self.menu_options):
            y = menu_y + 4 + i
            
            # 마을에서 저장 옵션 비활성화 표시
            is_disabled = (option == MenuOption.SAVE_GAME and self.is_town)
            
            if i == self.selected_index:
                # 선택된 항목
                if is_disabled:
                    console.print(menu_x + 2, y, "►", fg=(150, 150, 150))
                    console.print(menu_x + 4, y, f"{label} (마을에서 불가)", fg=(150, 150, 150))
                else:
                    console.print(menu_x + 2, y, "►", fg=(255, 255, 100))
                    console.print(menu_x + 4, y, label, fg=(255, 255, 100))
            else:
                # 일반 항목
                if is_disabled:
                    console.print(menu_x + 4, y, f"{label} (마을에서 불가)", fg=(100, 100, 100))
                else:
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
    menu = GameMenu(console.width, console.height, exploration=exploration)
    handler = InputHandler()

    logger.info(f"게임 메뉴 열림 (마을: {menu.is_town})")

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
                            open_inventory(console, context, inventory, party, exploration)
                            # 인벤토리에서 돌아온 후 메뉴 계속
                            continue
                        else:
                            show_message(console, context, "인벤토리를 열 수 없습니다.")
                            continue

                    elif result == MenuOption.COOKING:
                        if inventory is not None:
                            from src.ui.cooking_ui import open_cooking_pot
                            # 메뉴에서 요리할 때는 요리솥 보너스 없음
                            open_cooking_pot(console, context, inventory, is_cooking_pot=False)
                            # 요리에서 돌아온 후 메뉴 계속
                            continue
                        else:
                            show_message(console, context, "인벤토리가 없어서 요리를 할 수 없습니다.")
                            continue

                    elif result == MenuOption.QUEST_LIST:
                        # 퀘스트 목록 UI
                        from src.quest.quest_manager import get_quest_manager
                        quest_manager = get_quest_manager()
                        if quest_manager:
                            from src.ui.quest_list_ui import open_quest_list
                            open_quest_list(console, context, quest_manager)
                        else:
                            show_message(console, context, "퀘스트 관리자를 찾을 수 없습니다.")
                        continue

                    elif result == MenuOption.PARTY_STATUS and party:
                        open_party_status_menu(console, context, party, exploration=exploration)
                        # 파티 상태에서 돌아온 후 메뉴 계속
                        continue

                    elif result == MenuOption.SAVE_GAME:
                        if exploration is None:
                            show_message(console, context, "저장할 수 없습니다.")
                            continue
                        
                        # 마을에서는 저장 불가
                        if hasattr(exploration, 'is_town') and exploration.is_town:
                            show_message(console, context, "마을에서는 저장할 수 없습니다.")
                            continue

                        from src.ui.save_load_ui import show_save_screen
                        from src.persistence.save_system import (
                            serialize_party_member, serialize_dungeon, serialize_item
                        )

                        # 게임 상태 직렬화
                        # 디버그: 인벤토리 확인
                        logger.warning(f"[SAVE] 저장 전 인벤토리: {inventory}")
                        logger.warning(f"[SAVE] 인벤토리 골드: {inventory.gold if inventory and hasattr(inventory, 'gold') else 'N/A'}G")

                        # 디버그: 채집 오브젝트 확인
                        harvestables_count = len(exploration.dungeon.harvestables) if hasattr(exploration.dungeon, 'harvestables') else 0
                        logger.warning(f"[SAVE] 저장 전 채집 오브젝트: {harvestables_count}개")
                        if hasattr(exploration.dungeon, 'harvestables') and exploration.dungeon.harvestables:
                            for i, h in enumerate(exploration.dungeon.harvestables[:3]):
                                logger.warning(f"[SAVE]   {i+1}. {h.object_type.value} at ({h.x}, {h.y}), harvested={h.harvested}")

                        # 현재 난이도 가져오기
                        from src.core.difficulty import get_difficulty_system
                        difficulty_system = get_difficulty_system()
                        current_difficulty = "보통"
                        if difficulty_system:
                            current_difficulty = difficulty_system.current_difficulty.value

                        from src.persistence.save_system import serialize_game_state
                        
                        # 인벤토리 아이템 리스트 생성
                        inventory_items = []
                        if inventory and hasattr(inventory, 'slots'):
                            for slot in inventory.slots:
                                if slot.item:
                                    inventory_items.append(slot.item)
                        
                        # 멀티플레이어 여부 확인
                        is_multiplayer = False
                        if hasattr(exploration, 'is_multiplayer'):
                            is_multiplayer = exploration.is_multiplayer
                        elif hasattr(exploration, 'session'):
                            # MultiplayerExplorationSystem인 경우
                            is_multiplayer = True
                        
                        # 멀티플레이: 세션 정보 가져오기
                        session = None
                        if is_multiplayer and hasattr(exploration, 'session'):
                            session = exploration.session
                        
                        game_state = serialize_game_state(
                            party=party if party else [],
                            floor_number=exploration.floor_number,
                            dungeon=exploration.dungeon,
                            player_x=exploration.player.x,
                            player_y=exploration.player.y,
                            inventory=inventory_items,
                            player_keys=exploration.player_keys if hasattr(exploration, 'player_keys') else [],
                            traits=[],  # 특성은 파티 구성 시점에 저장됨
                            passives=[],  # 패시브도 파티 구성 시점에 저장됨
                            difficulty=current_difficulty,
                            exploration=exploration,
                            is_multiplayer=is_multiplayer,
                            session=session
                        )
                        
                        # 게임 통계 추가
                        game_state.update({
                            "enemies_defeated": exploration.game_stats.get("enemies_defeated", 0),
                            "max_floor_reached": exploration.game_stats.get("max_floor_reached", exploration.floor_number),
                            "total_gold_earned": exploration.game_stats.get("total_gold_earned", 0),
                            "total_exp_earned": exploration.game_stats.get("total_exp_earned", 0),
                            "save_slot": exploration.game_stats.get("save_slot", None),
                            "next_dungeon_floor": exploration.game_stats.get("next_dungeon_floor", 1),  # 다음 던전 층 번호 저장
                        })
                        
                        # 인벤토리 정보 추가 (기존 형식 유지)
                        if inventory:
                            game_state["inventory"] = {
                                "gold": inventory.gold if hasattr(inventory, 'gold') else 0,
                                "items": [{"item": serialize_item(slot.item), "quantity": getattr(slot, 'quantity', 1)} for slot in inventory.slots] if hasattr(inventory, 'slots') else [],
                                "cooking_cooldown_turn": inventory.cooking_cooldown_turn if hasattr(inventory, 'cooking_cooldown_turn') else None,
                                "cooking_cooldown_duration": inventory.cooking_cooldown_duration if hasattr(inventory, 'cooking_cooldown_duration') else 0
                            }

                        logger.warning(f"[SAVE] game_state['inventory']: {game_state['inventory']}")

                        success = show_save_screen(console, context, game_state, is_multiplayer=is_multiplayer)
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
    party: List,
    exploration=None
):
    """
    파티 상태 화면 (캐릭터 선택 가능)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party: 파티 멤버 리스트
        exploration: 탐험 상태 (멀티플레이어에서 다른 플레이어 정보 가져오기용)
    """
    from src.ui.gauge_renderer import GaugeRenderer
    gauge_renderer = GaugeRenderer()
    handler = InputHandler()

    logger.info("파티 상태 화면 열림")

    # 멀티플레이어에서 모든 플레이어의 파티 정보 수집
    all_party_members = []
    player_sections = []  # 각 플레이어 섹션의 시작 인덱스
    
    # 로컬 플레이어의 파티
    local_player_name = "나의 파티"
    if exploration and hasattr(exploration, 'session') and exploration.session:
        local_player_id = getattr(exploration.session, 'local_player_id', None)
        if local_player_id and local_player_id in exploration.session.players:
            local_player_name = f"{exploration.session.players[local_player_id].player_name}의 파티"
    
    all_party_members.extend(party)
    player_sections.append((0, len(party), local_player_name))
    
    # 멀티플레이어: 다른 플레이어의 파티 정보 추가
    if exploration and hasattr(exploration, 'session') and exploration.session:
        session = exploration.session
        local_player_id = getattr(session, 'local_player_id', None)
        
        for player_id, mp_player in session.players.items():
            # 로컬 플레이어는 이미 추가했으므로 건너뛰기
            if player_id == local_player_id:
                continue
            
            # 다른 플레이어의 파티 정보가 있는지 확인
            if hasattr(mp_player, 'party') and mp_player.party:
                start_idx = len(all_party_members)
                all_party_members.extend(mp_player.party)
                end_idx = len(all_party_members)
                player_name = getattr(mp_player, 'player_name', f"플레이어 {player_id}")
                player_sections.append((start_idx, end_idx, f"{player_name}의 파티"))
    
    selected_index = 0
    max_index = len(all_party_members) - 1 if all_party_members else 0

    while True:
        render_space_background(console, console.width, console.height)

        # 제목
        title = "=== 파티 상태 ==="
        console.print((console.width - len(title)) // 2, 2, title, fg=(255, 255, 100))

        # 파티원 정보 (간략)
        y = 5
        
        # 플레이어 섹션별로 표시
        current_section_idx = 0
        for section_start, section_end, section_name in player_sections:
            # 섹션 헤더
            section_color = (100, 200, 255)
            console.print(3, y, f"━━━ {section_name} ━━━", fg=section_color)
            y += 1
            
            # 해당 섹션의 파티원들 표시
            for i in range(section_start, section_end):
                if i >= len(all_party_members):
                    break
                
                member = all_party_members[i]
                
                # 선택 커서
                if i == selected_index:
                    console.print(3, y, "►", fg=(255, 255, 100))

                # 이름과 직업
                name_color = (255, 255, 255) if i == selected_index else (200, 200, 200)
                member_name = getattr(member, 'name', getattr(member, 'character_name', 'Unknown'))
                console.print(5, y, f"{i+1}. {member_name}", fg=name_color)
                
                level = getattr(member, 'level', 1)
                console.print(30, y, f"Lv.{level}", fg=name_color)

                if hasattr(member, 'job_name'):
                    console.print(40, y, member.job_name, fg=(150, 200, 255))
                elif hasattr(member, 'character_class'):
                    console.print(40, y, member.character_class, fg=(150, 200, 255))

                y += 1

                # HP
                current_hp = getattr(member, 'current_hp', 0)
                max_hp = getattr(member, 'max_hp', 1)
                if current_hp is not None and max_hp is not None:
                    console.print(7, y, "HP:", fg=(200, 200, 200))
                    gauge_renderer.render_bar(
                        console, 11, y, 15,
                        current_hp, max_hp, show_numbers=True
                    )
                    y += 1

                y += 1  # 다음 파티원과 간격
            
            y += 1  # 섹션 간 간격

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
                selected_index = min(max_index, selected_index + 1)
            elif action == GameAction.CONFIRM:
                # 선택한 캐릭터 상세 정보 표시
                if all_party_members and selected_index < len(all_party_members):
                    show_character_detail(console, context, all_party_members[selected_index])
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
        render_space_background(console, console.width, console.height)

        # 제목
        character_name = getattr(character, 'name', getattr(character, 'character_name', 'Unknown'))
        title = f"=== {character_name} 상세 정보 ==="
        console.print((console.width - len(title)) // 2, 2, title, fg=(255, 255, 100))

        y = 5

        # 기본 정보
        console.print(10, y, f"이름: {character_name}", fg=(255, 255, 255))
        y += 1
        level = getattr(character, 'level', 1)
        console.print(10, y, f"레벨: {level}", fg=(200, 200, 200))
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
