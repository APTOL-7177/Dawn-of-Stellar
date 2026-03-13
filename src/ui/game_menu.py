"""
게임 내 메뉴 시스템

탐험 중 M키로 접근 가능한 메인 메뉴
"""

from enum import Enum
from typing import Optional, List
import tcod

from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.ui.tcod_display import render_space_background
from src.ui.ui_renderer import draw_styled_box, SelectionHighlight, MenuScrambleEffect
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.UI)


class MenuOption(Enum):
    """메뉴 옵션"""
    PARTY_STATUS = "party_status"
    INVENTORY = "inventory"
    AFFINITY = "affinity"  # 호감도 열람
    QUEST_LIST = "quest_list"  # 퀘스트 목록
    SAVE_GAME = "save"
    LOAD_GAME = "load"
    OPTIONS = "options"
    MAIN_MENU = "main_menu"  # 메인 메뉴로 돌아가기
    LILY_TALK = "lily_talk"    # RPG 모드: 릴리 대화
    WORLD_MAP = "world_map"    # RPG 모드: 월드맵
    TELEPORT_TO_SPAWN = "teleport_to_spawn"  # 스폰 위치로 텔레포트 (긴급 탈출)
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
            ("호감도", MenuOption.AFFINITY),
            ("퀘스트 목록", MenuOption.QUEST_LIST),
            ("게임 저장", MenuOption.SAVE_GAME),
            ("게임 불러오기", MenuOption.LOAD_GAME),
            ("설정", MenuOption.OPTIONS),
            ("메인 메뉴", MenuOption.MAIN_MENU),
            ("돌아가기", MenuOption.RETURN),
        ]
        
        # RPG 모드 판별
        is_rpg = (exploration
                  and hasattr(exploration, 'lily_dialogue')
                  and hasattr(exploration, 'rpg_progress'))
        is_rpg_sub = (exploration
                      and hasattr(exploration, 'is_rpg_sub_dungeon')
                      and exploration.is_rpg_sub_dungeon)
        is_large_map = (exploration
                        and (exploration.dungeon.width > 300
                             or exploration.dungeon.height > 300)) if exploration else False

        # 로그라이크 전용: 스폰 텔레포트 (RPG 모드 제외)
        if not is_rpg and not is_rpg_sub and not is_large_map:
            # "설정" 앞에 삽입
            idx = next(
                (i for i, (_, opt) in enumerate(self.menu_options)
                 if opt == MenuOption.OPTIONS), len(self.menu_options) - 2
            )
            self.menu_options.insert(idx, ("스폰 위치로 귀환", MenuOption.TELEPORT_TO_SPAWN))

        # RPG 모드 전용 메뉴 (릴리 대화, 월드맵)
        if is_rpg:
            # 퀘스트 목록 뒤에 삽입
            idx = next(
                (i for i, (_, opt) in enumerate(self.menu_options)
                 if opt == MenuOption.QUEST_LIST), 3
            ) + 1
            self.menu_options.insert(idx, ("릴리와 대화", MenuOption.LILY_TALK))
            self.menu_options.insert(idx + 1, ("월드맵", MenuOption.WORLD_MAP))

        # 마을에서 저장 비활성화 여부 확인
        self.is_town = False
        if exploration and hasattr(exploration, 'is_town'):
            self.is_town = exploration.is_town

        # UI 효과
        self._highlight = SelectionHighlight(
            base_bg=(40, 40, 60), pulse_bg=(60, 60, 100), speed=3.0
        )
        self._scramble = MenuScrambleEffect(
            [label for label, _ in self.menu_options],
            duration=0.4, stagger=0.06,
        )
        self._last_time = 0.0

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
        import time as _time

        # dt 계산
        now = _time.monotonic()
        dt = now - self._last_time if self._last_time else 0.016
        self._last_time = now

        # 효과 갱신
        self._highlight.update(dt)
        self._scramble.update(dt)

        # 반투명 배경 (어두운 오버레이)
        for y in range(self.screen_height):
            for x in range(self.screen_width):
                console.print(x, y, " ", bg=(0, 0, 0))

        # 메뉴 박스
        menu_width = 40
        menu_height = len(self.menu_options) + 6
        menu_x = (self.screen_width - menu_width) // 2
        menu_y = (self.screen_height - menu_height) // 2

        # 더블라인 박스 + 타이틀
        draw_styled_box(
            console, menu_x, menu_y, menu_width, menu_height,
            title="메뉴",
            fg=(200, 200, 200),
            bg=(20, 20, 40),
            title_fg=(255, 255, 100),
        )

        # 스크램블 텍스트 가져오기
        display_texts = self._scramble.get_display_texts()

        # 메뉴 옵션
        for i, (label, option) in enumerate(self.menu_options):
            y = menu_y + 4 + i

            # 스크램블 효과 적용 (진행 중이면 스크램블 텍스트 사용)
            display_label = display_texts[i] if i < len(display_texts) else label

            # 마을에서 저장 옵션 비활성화 표시
            is_disabled = (option == MenuOption.SAVE_GAME and self.is_town)

            if i == self.selected_index:
                # 선택된 항목 — 펄스 하이라이트 배경
                highlight_bg = self._highlight.get_bg_color()
                console.draw_rect(menu_x + 1, y, menu_width - 2, 1, ord(" "), bg=highlight_bg)

                if is_disabled:
                    console.print(menu_x + 2, y, "►", fg=(150, 150, 150))
                    console.print(menu_x + 4, y, f"{display_label} (마을에서 불가)", fg=(150, 150, 150))
                else:
                    console.print(menu_x + 2, y, "►", fg=(255, 255, 100))
                    console.print(menu_x + 4, y, display_label, fg=(255, 255, 100))
            else:
                # 일반 항목
                if is_disabled:
                    console.print(menu_x + 4, y, f"{display_label} (마을에서 불가)", fg=(100, 100, 100))
                else:
                    console.print(menu_x + 4, y, display_label, fg=(200, 200, 200))

        # 조작법 (게임패드 연결 시 게임패드 버튼으로 표시)
        from src.ui.input_handler import key_binding_manager
        use_gamepad = unified_input_handler.gamepad_connected

        if use_gamepad:
            move_help = key_binding_manager.get_movement_help(True)
            confirm_key = key_binding_manager.get_action_display("confirm", True)
            cancel_key = key_binding_manager.get_action_display("escape", True)
            help_text = f"{move_help}  {confirm_key}: 확인  {cancel_key}: 닫기"
        else:
            help_text = "↑↓: 선택  Enter/M: 확인  ESC: 닫기"

        console.print(
            menu_x + (menu_width - len(help_text)) // 2,
            menu_y + menu_height - 2,
            help_text,
            fg=(150, 150, 150)
        )


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

    logger.info(f"게임 메뉴 열림 (마을: {menu.is_town})")

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        # 렌더링
        menu.render(console)
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass

        # 입력 처리 (키보드 + 게임패드)
        action = None
        
        # 키보드 입력
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            if action:
                break
        
        # 게임패드 입력 (키보드 입력이 없을 때)
        if not action:
            action = unified_input_handler.get_action()

        if action:
            result = menu.handle_input(action)
            if result:
                logger.info(f"메뉴 선택: {result.value}")

                # 하위 메뉴로 이동
                if result == MenuOption.INVENTORY:
                    if inventory is not None and party is not None:
                        from src.ui.inventory_ui import open_inventory
                        open_inventory(console, context, inventory, party, exploration)
                        continue
                    else:
                        show_message(console, context, "인벤토리를 열 수 없습니다.")
                        continue

                elif result == MenuOption.AFFINITY:
                    if party and len(party) >= 2:
                        try:
                            from src.ui.affinity_ui import AffinityUI
                            from src.character.affinity import AffinityManager
                            # 기존 combat manager의 AffinityManager 사용 (새로 생성하면 0pt)
                            aff_mgr = None
                            try:
                                from src.combat.combat_manager import get_combat_manager
                                cm = get_combat_manager()
                                if cm and cm.affinity_manager:
                                    aff_mgr = cm.affinity_manager
                            except Exception:
                                pass
                            if aff_mgr is None:
                                # combat manager 없으면 캐시된 데이터로 복원
                                aff_mgr = AffinityManager()
                                try:
                                    import src.persistence.save_system as save_module
                                    cached = getattr(save_module, '_last_loaded_affinity_data', None)
                                    if cached:
                                        aff_mgr.from_dict(cached)
                                except Exception:
                                    pass
                            party_jobs = [getattr(m, 'job_id', getattr(m, 'character_class', '')) for m in party]
                            party_names = {getattr(m, 'job_id', getattr(m, 'character_class', '')): getattr(m, 'name', '???') for m in party}
                            aff_ui = AffinityUI(console, context)
                            aff_ui.show(aff_mgr, party_jobs, party_names)
                        except Exception as e:
                            logger.error(f"호감도 UI 오류: {e}")
                            show_message(console, context, "호감도를 표시할 수 없습니다.")
                    else:
                        show_message(console, context, "파티원이 2명 이상이어야 합니다.")
                    continue

                elif result == MenuOption.QUEST_LIST:
                    from src.quest.quest_manager import get_quest_manager
                    quest_manager = get_quest_manager()
                    if quest_manager:
                        from src.ui.quest_list_ui import open_quest_list
                        player_obj = getattr(exploration, 'player', None) if exploration else None
                        open_quest_list(console, context, quest_manager, player=player_obj, inventory=inventory)
                    else:
                        show_message(console, context, "퀘스트 관리자를 찾을 수 없습니다.")
                    continue

                elif result == MenuOption.LILY_TALK:
                    if (exploration
                            and hasattr(exploration, 'lily_dialogue')
                            and hasattr(exploration, 'rpg_progress')):
                        try:
                            from src.ui.npc_dialog_ui import run_npc_dialog
                            from src.ui.cursor_menu import CursorMenu, MenuItem

                            lily_mgr = exploration.lily_dialogue
                            progress = exploration.rpg_progress
                            convos = lily_mgr.get_town_conversations(
                                progress.current_chapter,
                                progress.lily_affinity,
                                progress.lily_conversations_seen,
                            )
                            if not convos:
                                show_message(console, context,
                                             '릴리: "지금은 특별히 할 얘기가 없어..."')
                            else:
                                import time
                                import pygame
                                items = []
                                for c in convos:
                                    pfx = "★ " if c.get("is_new") else "  "
                                    items.append(MenuItem(text=f"{pfx}{c.get('title', '???')}"))
                                lily_cm = CursorMenu(
                                    title="릴리와 대화", items=items, width=30,
                                    x=console.width // 2 - 15,
                                    y=console.height // 2 - len(items) // 2 - 2,
                                )
                                for _ in tcod.event.get():
                                    pass
                                sel = None
                                lily_menu_running = True
                                while lily_menu_running:
                                    console.clear()
                                    lily_cm.render(console)
                                    context.present(console)
                                    try:
                                        pygame.event.pump()
                                    except Exception:
                                        pass
                                    for ev in tcod.event.get():
                                        act = unified_input_handler.process_tcod_event(ev)
                                        if act == GameAction.CONFIRM:
                                            sel = lily_cm.cursor_index
                                            lily_menu_running = False
                                            break
                                        elif act == GameAction.CANCEL:
                                            lily_menu_running = False
                                            break
                                        elif act == GameAction.MOVE_UP:
                                            lily_cm.move_cursor_up()
                                        elif act == GameAction.MOVE_DOWN:
                                            lily_cm.move_cursor_down()
                                        if isinstance(ev, tcod.event.Quit):
                                            raise SystemExit()
                                    gp_act = unified_input_handler.get_action()
                                    if gp_act == GameAction.CONFIRM:
                                        sel = lily_cm.cursor_index
                                        lily_menu_running = False
                                    elif gp_act == GameAction.CANCEL:
                                        lily_menu_running = False
                                    elif gp_act == GameAction.MOVE_UP:
                                        lily_cm.move_cursor_up()
                                    elif gp_act == GameAction.MOVE_DOWN:
                                        lily_cm.move_cursor_down()
                                    time.sleep(0.01)

                                if sel is not None and 0 <= sel < len(convos):
                                    conv = convos[sel]
                                    ld = conv.get("lines", [])
                                    dl = [le.get("text", "") for le in ld]
                                    if dl:
                                        sp = ld[0].get("speaker", "릴리") if ld else "릴리"
                                        run_npc_dialog(console, context,
                                                       npc_name=sp, dialog_lines=dl)
                                    progress.lily_affinity += conv.get("affinity_change", 0)
                                    progress.lily_conversations_seen.add(conv.get("id", ""))
                        except Exception as e:
                            logger.error(f"릴리 대화 메뉴 오류: {e}")
                    continue

                elif result == MenuOption.WORLD_MAP:
                    # 메뉴 닫고 미니맵 토글
                    return result

                elif result == MenuOption.TELEPORT_TO_SPAWN:
                    # 메뉴 닫고 world_ui에서 텔레포트 처리
                    return result

                elif result == MenuOption.PARTY_STATUS and party:
                    open_party_status_menu(console, context, party, exploration=exploration)
                    continue

                elif result == MenuOption.SAVE_GAME:
                    if exploration is None:
                        show_message(console, context, "저장할 수 없습니다.")
                        continue

                    # 마을에서는 저장 불가
                    if hasattr(exploration, 'is_town') and exploration.is_town:
                        show_message(console, context, "마을에서는 저장할 수 없습니다.")
                        continue

                    # RPG 서브 던전에서는 저장 불가 (월드맵에서 자동 저장됨)
                    if getattr(exploration, 'is_rpg_sub_dungeon', False):
                        show_message(console, context, "던전 안에서는 저장할 수 없습니다. 월드맵에서 자동 저장됩니다.")
                        continue

                    from src.ui.save_load_ui import show_save_screen
                    from src.persistence.save_system import (
                        serialize_party_member, serialize_dungeon, serialize_item
                    )

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
                        is_multiplayer = True
                    
                    # 멀티플레이: 세션 정보 가져오기
                    session = None
                    if is_multiplayer and hasattr(exploration, 'session'):
                        session = exploration.session
                    
                    # max_floor_reached 계산
                    max_floor = exploration.game_stats.get("max_floor_reached", exploration.floor_number)
                    max_floor = max(max_floor, exploration.floor_number)

                    # RPG 모드 감지 (대형 맵은 시드로 재생성하므로 던전 직렬화 스킵)
                    is_rpg_mode = (exploration.dungeon.width > 300 or exploration.dungeon.height > 300)

                    if is_rpg_mode:
                        # RPG 모드: rpg_mode_manager의 _auto_save와 동일한 경량 저장
                        from src.persistence.save_system import serialize_party_member as _spm
                        rpg_party_data = [_spm(m) for m in (party if party else [])]
                        rpg_inv_data = []
                        for item in inventory_items:
                            if item:
                                rpg_inv_data.append(serialize_item(item))

                        # RPG 진행 상태 가져오기
                        rpg_progress_dict = {}
                        if hasattr(exploration, 'town_manager') and exploration.town_manager:
                            tm = exploration.town_manager
                            if hasattr(tm, '_rpg_progress'):
                                rpg_progress_dict = tm._rpg_progress

                        game_state = {
                            "party": rpg_party_data,
                            "floor_number": 1,
                            "max_floor_reached": 1,
                            "inventory_items": rpg_inv_data,
                            "rpg_mode": True,
                            "player_x": exploration.player.x,
                            "player_y": exploration.player.y,
                            "world_seed": getattr(exploration.dungeon, '_world_seed', 0),
                            "rpg_progress": rpg_progress_dict,
                            "difficulty": current_difficulty,
                        }
                    else:
                        game_state = serialize_game_state(
                            party=party if party else [],
                            floor_number=exploration.floor_number,
                            dungeon=exploration.dungeon,
                            player_x=exploration.player.x,
                            player_y=exploration.player.y,
                            inventory=inventory_items,
                            player_keys=exploration.player_keys if hasattr(exploration, 'player_keys') else [],
                            traits=[],
                            passives=[],
                            difficulty=current_difficulty,
                            exploration=exploration,
                            is_multiplayer=is_multiplayer,
                            session=session,
                            max_floor_reached=max_floor
                        )

                    # 게임 통계 추가
                    game_state.update({
                        "enemies_defeated": exploration.game_stats.get("enemies_defeated", 0),
                        "total_gold_earned": exploration.game_stats.get("total_gold_earned", 0),
                        "total_exp_earned": exploration.game_stats.get("total_exp_earned", 0),
                        "save_slot": exploration.game_stats.get("save_slot", None),
                        "next_dungeon_floor": exploration.game_stats.get("next_dungeon_floor", 1),
                    })

                    # 인벤토리 정보 추가 (일반 모드만)
                    if not is_rpg_mode and inventory is not None:
                        game_state["inventory"] = {
                            "gold": inventory.gold if hasattr(inventory, 'gold') else 0,
                            "base_weight": inventory.base_weight if hasattr(inventory, 'base_weight') else 50.0,
                            "items": [{"item": serialize_item(slot.item), "quantity": getattr(slot, 'quantity', 1)} for slot in inventory.slots if slot.item] if hasattr(inventory, 'slots') else [],
                            "cooking_cooldown_turn": inventory.cooking_cooldown_turn if hasattr(inventory, 'cooking_cooldown_turn') else None,
                            "cooking_cooldown_duration": inventory.cooking_cooldown_duration if hasattr(inventory, 'cooking_cooldown_duration') else 0
                        }

                    success = show_save_screen(console, context, game_state, is_multiplayer=is_multiplayer)
                    if success:
                        show_message(console, context, "저장 완료!")
                    continue

                elif result == MenuOption.LOAD_GAME:
                    from src.ui.save_load_ui import show_load_screen
                    game_state = show_load_screen(console, context)
                    if game_state:
                        return MenuOption.LOAD_GAME
                    continue

                elif result == MenuOption.OPTIONS:
                    from src.ui.settings_ui import open_settings
                    open_settings(console, context)
                    continue

                elif result == MenuOption.MAIN_MENU:
                    # 메인 메뉴로 돌아가기 전 경고 표시
                    confirmed = show_confirm_dialog(
                        console, context,
                        "메인 메뉴로 돌아가시겠습니까?",
                        "저장하지 않은 진행 상황은 사라집니다."
                    )
                    if confirmed:
                        logger.info("메인 메뉴로 돌아가기 선택됨")
                        return MenuOption.MAIN_MENU
                    continue

                elif result == MenuOption.RETURN:
                    return result

        # 윈도우 닫기
        for quit_event in tcod.event.get():
            if isinstance(quit_event, tcod.event.Quit):
                return MenuOption.QUIT

        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)


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

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

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

                # HP (애니메이션 게이지)
                current_hp = getattr(member, 'current_hp', 0)
                max_hp = getattr(member, 'max_hp', 1)
                if current_hp is not None and max_hp is not None:
                    console.print(7, y, "HP:", fg=(200, 200, 200))
                    hp_member_id = f"party_hp_{i}_{getattr(member, 'id', id(member))}"
                    wound_damage = getattr(member, 'wound', 0)
                    gauge_renderer.render_animated_hp_bar(
                        console, 11, y, 15,
                        current_hp, max_hp, hp_member_id,
                        wound_damage=wound_damage, show_numbers=True
                    )
                    y += 1

                # MP (애니메이션 게이지)
                current_mp = getattr(member, 'current_mp', 0)
                max_mp = getattr(member, 'max_mp', 1)
                if current_mp is not None and max_mp is not None:
                    console.print(7, y, "MP:", fg=(200, 200, 200))
                    mp_member_id = f"party_mp_{i}_{getattr(member, 'id', id(member))}"
                    gauge_renderer.render_animated_mp_bar(
                        console, 11, y, 15,
                        current_mp, max_mp, mp_member_id,
                        show_numbers=True,
                        reserved_mp=getattr(member, "reserved_max_mp", 0)
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

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass

        # 입력 처리 함수
        def process_party_action(action):
            nonlocal selected_index
            if action == GameAction.MOVE_UP:
                selected_index = max(0, selected_index - 1)
            elif action == GameAction.MOVE_DOWN:
                selected_index = min(max_index, selected_index + 1)
            elif action == GameAction.CONFIRM:
                if all_party_members and selected_index < len(all_party_members):
                    show_character_detail(console, context, all_party_members[selected_index])
            elif action == GameAction.ESCAPE or action == GameAction.MENU:
                return True
            return False

        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                keyboard_processed = True
                if process_party_action(action):
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return

        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if process_party_action(gamepad_action):
                    return

        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)


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

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

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

        # HP (애니메이션 게이지 사용)
        if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
            console.print(10, y, "HP:", fg=(200, 200, 200))
            hp_character_id = f"detail_hp_{getattr(character, 'id', id(character))}"
            wound_damage = getattr(character, 'wound', 0)
            gauge_renderer.render_animated_hp_bar(
                console, 14, y, 30,
                character.current_hp, character.max_hp, hp_character_id,
                wound_damage=wound_damage, show_numbers=True
            )
            y += 1

        # MP (애니메이션 게이지 사용)
        if hasattr(character, 'current_mp') and hasattr(character, 'max_mp'):
            console.print(10, y, "MP:", fg=(200, 200, 200))
            mp_character_id = f"detail_mp_{getattr(character, 'id', id(character))}"
            gauge_renderer.render_animated_mp_bar(
                console, 14, y, 30,
                character.current_mp, character.max_mp, mp_character_id,
                show_numbers=True,
                reserved_mp=getattr(character, "reserved_max_mp", 0)
            )
            y += 2

        # 스탯 상세
        console.print(10, y, "[ 스탯 ]", fg=(255, 200, 100))
        y += 1

        if hasattr(character, 'strength'):
            # 기본 스탯 표시
            console.print(12, y, f"STR (공격):    {character.strength:3d}", fg=(255, 180, 180))
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

            # 상세 스탯 계산 및 표시
            console.print(10, y, "[ 상세 정보 ]", fg=(255, 200, 100))
            y += 1

            from src.character.trait_effects import get_trait_effect_manager
            trait_manager = get_trait_effect_manager()

            # 1. 크리티컬 확률
            # 공식: (1 - (100 / (Luck * 2 + 100))) + Base(0.1) + Traits
            luck = character.luck
            luck_bonus = 1.0 - (100.0 / (luck * 2 + 100))
            base_crit = 0.1  # 기본값
            trait_crit = trait_manager.calculate_critical_bonus(character)
            final_crit = min(0.95, luck_bonus + base_crit + trait_crit)
            
            console.print(12, y, f"치명타 확률:   {final_crit*100:5.1f}%", fg=(255, 100, 100))
            y += 1

            # 2. 크리티컬 데미지
            # 공식: Base(1.5) * Traits + Equipment
            base_crit_dmg = 1.5
            trait_crit_dmg = trait_manager.calculate_critical_damage(character)
            equip_crit_dmg = 0.0
            
            # 장비에서 critical_damage 효과 합산
            if hasattr(character, 'equipment') and character.equipment:
                for slot, item in character.equipment.items():
                    if not item:
                        continue
                    # special_effects에서 critical_damage 확인
                    if hasattr(item, 'special_effects'):
                        for effect in item.special_effects:
                            effect_type = getattr(effect, 'effect_type', None)
                            effect_value = getattr(effect, 'value', 0)
                            type_value = getattr(effect_type, 'value', str(effect_type)) if effect_type else ''
                            if type_value == 'critical_damage':
                                equip_crit_dmg += effect_value
            
            final_crit_dmg = base_crit_dmg * trait_crit_dmg + equip_crit_dmg
            
            console.print(12, y, f"치명타 피해:   {final_crit_dmg*100:5.0f}%", fg=(255, 50, 50))
            y += 1

            # 3. 명중률 / 회피율
            accuracy = int(character.stat_manager.get_value("accuracy", use_total=True))
            evasion = int(character.stat_manager.get_value("evasion", use_total=True))
            
            console.print(12, y, f"명중률:        {accuracy:3d}", fg=(150, 255, 255))
            y += 1
            console.print(12, y, f"회피율:        {evasion:3d}", fg=(150, 255, 150))
            y += 2

            # 4. 방어 관통 스탯 (캐릭터 속성 + 장비 효과 합산)
            phys_pen = getattr(character, 'physical_penetration', 0)
            phys_pen_fixed = getattr(character, 'physical_penetration_fixed', 0)
            magic_pen = getattr(character, 'magic_penetration', 0)
            magic_pen_fixed = getattr(character, 'magic_penetration_fixed', 0)
            
            # 장비에서 관통 효과 추가 합산
            if hasattr(character, 'equipment') and character.equipment:
                for slot, item in character.equipment.items():
                    if not item:
                        continue
                    
                    # 1. affixes (ItemAffix) 확인
                    if hasattr(item, 'affixes'):
                        for affix in item.affixes:
                            stat = getattr(affix, 'stat', '')
                            value = getattr(affix, 'value', 0)
                            if stat == 'physical_penetration':
                                phys_pen += value
                            elif stat == 'physical_penetration_fixed':
                                phys_pen_fixed += value
                            elif stat == 'magic_penetration':
                                magic_pen += value
                            elif stat == 'magic_penetration_fixed':
                                magic_pen_fixed += value
                    
                    # 2. special_effects (EquipmentEffect) 확인
                    if hasattr(item, 'special_effects'):
                        for effect in item.special_effects:
                            effect_type = getattr(effect, 'effect_type', None)
                            effect_value = getattr(effect, 'value', 0)
                            # EffectType enum의 value로 비교
                            type_value = getattr(effect_type, 'value', str(effect_type)) if effect_type else ''
                            if type_value == 'physical_penetration':
                                phys_pen += effect_value
                            elif type_value == 'physical_penetration_fixed':
                                phys_pen_fixed += effect_value
                            elif type_value == 'magic_penetration':
                                magic_pen += effect_value
                            elif type_value == 'magic_penetration_fixed':
                                magic_pen_fixed += effect_value

            console.print(10, y, "[ 방어 관통 ]", fg=(255, 200, 100))
            y += 1
            
            # 물리 관통 표시
            pen_text = f"물리 관통:     {phys_pen*100:5.1f}%"
            if phys_pen_fixed > 0:
                pen_text += f" (+{int(phys_pen_fixed)})"
            console.print(12, y, pen_text, fg=(255, 150, 100))
            y += 1
            
            # 마법 관통 표시
            pen_text = f"마법 관통:     {magic_pen*100:5.1f}%"
            if magic_pen_fixed > 0:
                pen_text += f" (+{int(magic_pen_fixed)})"
            console.print(12, y, pen_text, fg=(200, 150, 255))
            y += 2

            # 5. 속성 추가 데미지
            element_map = {
                "fire": ("화염", "fire_damage", (255, 100, 100)),
                "ice": ("빙결", "ice_damage", (100, 100, 255)),
                "lightning": ("번개", "lightning_damage", (255, 255, 100)),
                "earth": ("대지", "earth_damage", (150, 100, 50)),
                "wind": ("바람", "wind_damage", (100, 255, 100)),
                "water": ("물", "water_damage", (100, 150, 255)),
                "holy": ("신성", "holy_damage", (255, 255, 200)),
                "dark": ("암흑", "dark_damage", (100, 50, 100)),
            }

            has_elem_dmg = False
            
            for elem, (name, attr_name, color) in element_map.items():
                bonus = 0
                # 캐릭터 기본 속성
                if hasattr(character, attr_name):
                    bonus += getattr(character, attr_name, 0)
                
                # 장비 속성
                if hasattr(character, 'equipment') and character.equipment:
                    for slot, item in character.equipment.items():
                        if item and hasattr(item, 'effects'):
                            for effect in item.effects:
                                if hasattr(effect, 'effect_type') and hasattr(effect, 'value'):
                                    if effect.effect_type == attr_name:
                                        bonus += int(effect.value)
                
                if bonus > 0:
                    if not has_elem_dmg:
                        console.print(10, y, "[ 속성 강화 ]", fg=(255, 200, 100))
                        y += 1
                        has_elem_dmg = True
                    
                    console.print(12, y, f"{name} 추가 피해: +{bonus}", fg=color)
                    y += 1
            
            if has_elem_dmg:
                y += 1

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
                        # 추가옵션 (접사) 표시
                        if hasattr(item, 'affixes') and item.affixes:
                            for affix in item.affixes:
                                console.print(14, y, f"+ {affix.get_description()}", fg=(255, 200, 100))
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
                if action == GameAction.ESCAPE or action == GameAction.MENU or action == GameAction.CONFIRM:
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return

        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action == GameAction.ESCAPE or gamepad_action == GameAction.MENU or gamepad_action == GameAction.CONFIRM:
                return

        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)


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
    
    # 게임패드/키보드 입력 상태 초기화
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
    
    handler = InputHandler()

    # 메시지 박스 (한글 등 전각 문자의 실제 표시 폭 고려)
    def _display_width(text: str) -> int:
        """문자열의 콘솔 표시 폭 계산 (전각 문자 = 2칸)"""
        w = 0
        for ch in text:
            w += 2 if ord(ch) > 0x7F else 1
        return w

    def _wrap_lines(text: str, max_width: int) -> list:
        """텍스트를 줄바꿈(\n) 및 폭 제한으로 분리"""
        raw_lines = text.split('\n')
        wrapped = []
        for line in raw_lines:
            if _display_width(line) <= max_width:
                wrapped.append(line)
            else:
                words = line.split(' ')
                current = ""
                for word in words:
                    test = current + (" " if current else "") + word
                    if _display_width(test) <= max_width:
                        current = test
                    else:
                        if current:
                            wrapped.append(current)
                        current = word
                if current:
                    wrapped.append(current)
        return wrapped if wrapped else [""]

    help_text = "아무 키나 누르세요..."
    max_inner_width = min(56, console.width - 6)
    msg_lines = _wrap_lines(message, max_inner_width)

    help_w = _display_width(help_text)
    content_w = max(max(_display_width(l) for l in msg_lines), help_w)
    box_width = min(60, content_w + 4)
    # 테두리(2) + 상단여백(1) + 메시지줄 + 간격(1) + 안내(1) + 하단여백(1)
    box_height = len(msg_lines) + 5
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2
    
    # 입력 허용 시작 시간 (1초 후부터 입력 허용)
    start_time = time.time()
    input_delay = 1.0

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

        # 메시지 (멀티라인 지원)
        for i, line in enumerate(msg_lines):
            console.print(
                box_x + (box_width - _display_width(line)) // 2,
                box_y + 2 + i,
                line,
                fg=(255, 255, 255)
            )

        # 확인 안내
        console.print(
            box_x + (box_width - _display_width(help_text)) // 2,
            box_y + box_height - 2,
            help_text,
            fg=(150, 150, 150)
        )

        context.present(console)

        # pygame 이벤트 업데이트 (게임패드용)
        try:
            pygame.event.pump()
        except:
            pass

        # 입력 허용 시간 체크
        can_accept_input = (time.time() - start_time) >= input_delay

        # 아무 키나 누르면 닫기 (키보드)
        for event in tcod.event.get():
            if can_accept_input:
                if isinstance(event, tcod.event.KeyDown):
                    return
            if isinstance(event, tcod.event.Quit):
                return
        
        # 게임패드 입력
        if can_accept_input:
            action = unified_input_handler.get_action()
            if action:
                return
        
        # CPU 절약
        time.sleep(0.01)


def show_confirm_dialog(
    console: tcod.console.Console,
    context: tcod.context.Context,
    title: str,
    message: str
) -> bool:
    """
    확인 다이얼로그 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        title: 제목
        message: 메시지

    Returns:
        True: 확인, False: 취소
    """
    import time
    
    selected = 0  # 0: 예, 1: 아니오

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        # 배경 어둡게
        for y in range(console.height):
            for x in range(console.width):
                console.print(x, y, " ", bg=(0, 0, 0))
        
        # 다이얼로그 박스
        dialog_width = max(len(title), len(message)) + 10
        dialog_height = 9
        dialog_x = (console.width - dialog_width) // 2
        dialog_y = (console.height - dialog_height) // 2
        
        # 박스 테두리
        # 모서리
        console.print(dialog_x, dialog_y, "┌", fg=(255, 200, 100))
        console.print(dialog_x + dialog_width - 1, dialog_y, "┐", fg=(255, 200, 100))
        console.print(dialog_x, dialog_y + dialog_height - 1, "└", fg=(255, 200, 100))
        console.print(dialog_x + dialog_width - 1, dialog_y + dialog_height - 1, "┘", fg=(255, 200, 100))
        
        # 가로선
        for i in range(1, dialog_width - 1):
            console.print(dialog_x + i, dialog_y, "─", fg=(255, 200, 100))
            console.print(dialog_x + i, dialog_y + dialog_height - 1, "─", fg=(255, 200, 100))
        
        # 세로선
        for i in range(1, dialog_height - 1):
            console.print(dialog_x, dialog_y + i, "│", fg=(255, 200, 100))
            console.print(dialog_x + dialog_width - 1, dialog_y + i, "│", fg=(255, 200, 100))
        
        # 내부 채우기
        for dy in range(1, dialog_height - 1):
            for dx in range(1, dialog_width - 1):
                console.print(dialog_x + dx, dialog_y + dy, " ", bg=(30, 20, 40))
        
        # 경고 아이콘과 제목
        console.print(
            dialog_x + (dialog_width - len(title) - 4) // 2,
            dialog_y + 2,
            f"⚠ {title}",
            fg=(255, 200, 100)
        )
        
        # 메시지
        console.print(
            dialog_x + (dialog_width - len(message)) // 2,
            dialog_y + 4,
            message,
            fg=(200, 200, 200)
        )
        
        # 버튼
        yes_text = "예"
        no_text = "아니오"
        button_y = dialog_y + 6
        
        yes_x = dialog_x + dialog_width // 3 - len(yes_text)
        no_x = dialog_x + 2 * dialog_width // 3 - len(no_text)
        
        if selected == 0:
            console.print(yes_x, button_y, f"[ {yes_text} ]", fg=(255, 255, 100))
            console.print(no_x, button_y, f"  {no_text}  ", fg=(150, 150, 150))
        else:
            console.print(yes_x, button_y, f"  {yes_text}  ", fg=(150, 150, 150))
            console.print(no_x, button_y, f"[ {no_text} ]", fg=(255, 255, 100))
        
        context.present(console)
        
        # pygame 이벤트 업데이트
        try:
            import pygame
            pygame.event.pump()
        except:
            pass
        
        # 입력 처리
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            
            if action == GameAction.MOVE_LEFT or action == GameAction.MOVE_RIGHT:
                selected = 1 - selected  # 토글
                from src.audio import play_sfx
                play_sfx("ui", "cursor_move")
            elif action == GameAction.CONFIRM:
                from src.audio import play_sfx
                if selected == 0:
                    play_sfx("ui", "cursor_select")
                    return True
                else:
                    play_sfx("ui", "cursor_cancel")
                    return False
            elif action == GameAction.ESCAPE:
                from src.audio import play_sfx
                play_sfx("ui", "cursor_cancel")
                return False
            
            if isinstance(event, tcod.event.Quit):
                return False
        
        # 게임패드 입력
        gamepad_action = unified_input_handler.get_action()
        if gamepad_action:
            if gamepad_action == GameAction.MOVE_LEFT or gamepad_action == GameAction.MOVE_RIGHT:
                selected = 1 - selected
                from src.audio import play_sfx
                play_sfx("ui", "cursor_move")
            elif gamepad_action == GameAction.CONFIRM:
                from src.audio import play_sfx
                if selected == 0:
                    play_sfx("ui", "cursor_select")
                    return True
                else:
                    play_sfx("ui", "cursor_cancel")
                    return False
            elif gamepad_action == GameAction.ESCAPE:
                from src.audio import play_sfx
                play_sfx("ui", "cursor_cancel")
                return False
        
        time.sleep(0.01)
