"""
보스 테스트 모드

--test-boss 플래그로 실행 시 바로 보스 전투 시작
커스텀 파티 구성 지원 (트레이닝 모드와 동일한 방식)
"""

import tcod
from typing import Any, TYPE_CHECKING, Optional
from src.ui.input_handler import unified_input_handler, GameAction
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerEvent, PointerEventKind

if TYPE_CHECKING:
    from src.character.character import Character


def run_boss_test(console: tcod.console.Console, context: Any, boss_floor: int, logger: Any) -> str:
    """
    보스 테스트 모드 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        boss_floor: 보스 층수 (20=세피로스, 30=카인)
        logger: 로거

    Returns:
        결과 문자열
    """
    from src.character.character import Character
    from src.character.party import Party
    from src.equipment.item_system import Equipment, EquipSlot, ItemRarity
    from src.world.enemy_generator import EnemyGenerator
    from src.combat.combat_manager import CombatManager, CombatState
    from src.ui.combat_ui import CombatUI

    logger.info(f"보스 테스트 모드 시작: {boss_floor}층")

    # === 0. 파티 구성 모드 선택 ===
    party_mode = _select_party_mode(console, context, logger)
    if party_mode is None:
        return "cancel"

    # === 1. 파티 생성 ===
    party_level = boss_floor
    selected_passives = []

    if party_mode == "default":
        # 기본 파티 (기존 방식)
        if boss_floor == 20:
            job_names = ["warrior", "archer", "magician", "monk"]
            display_names = ["전사", "궁수", "마법사", "몽크"]
        else:  # 30층
            job_names = ["illusionist", "berserker", "vampire", "time_mage"]
            display_names = ["환술사", "버서커", "흡혈귀", "시간술사"]

        party_members = []
        for i, (job_name, display_name) in enumerate(zip(job_names, display_names)):
            char = Character(f"테스터{i+1}", job_name)

            # 레벨 설정
            for _ in range(party_level - 1):
                char.level_up()

            # 풀장비 지급
            _equip_best_gear(char, party_level, logger)

            # HP/MP 완전 회복
            char.current_hp = char.max_hp
            char.current_mp = char.max_mp

            party_members.append(char)
            logger.info(f"파티원 생성: {display_name} (Lv.{party_level})")

    else:
        # 커스텀 파티 (트레이닝 모드 방식)
        # 레벨 선택
        level_input = _input_level(console, context, logger, boss_floor)
        if level_input is None:
            return "cancel"
        party_level = level_input

        # 직업 선택 (4명)
        party_jobs = []
        picked_jobs: list[str] = []
        for i in range(4):
            job_pick = _select_job(
                console,
                context,
                logger,
                title=f"파티 {i+1}번 직업 선택 (보스: {boss_floor}층)",
                excluded_jobs=set(picked_jobs)
            )
            if job_pick is None:
                return "cancel"
            party_jobs.append(job_pick)
            picked_jobs.append(job_pick)

        # 캐릭터 생성 및 레벨 설정
        from src.character.character_loader import get_all_job_names
        job_names_map = get_all_job_names()

        party_members = []
        for idx, job_id in enumerate(party_jobs):
            display_name = job_names_map.get(job_id, job_id)
            member = Character(display_name, job_id)
            for _ in range(party_level - 1):
                member.level_up()
            party_members.append(member)

        logger.info(f"커스텀 파티 생성: {len(party_members)}명 (Lv.{party_level})")

        # 특성 선택
        from src.ui.trait_selection import run_trait_selection

        trait_results = run_trait_selection(console, context, party_members)
        if trait_results is None:
            logger.info("특성 선택 취소됨")
            return "cancel"

        # 특성 적용
        if trait_results and len(trait_results) > 0:
            for member, traits in zip(party_members, trait_results):
                member.selected_traits = traits.selected_traits
                for trait in traits.selected_traits:
                    tid = trait.id if hasattr(trait, 'id') else str(trait)
                    member.activate_trait(tid)
                logger.info(f"{member.name} 특성 적용: {len(member.selected_traits)}개")

        # 패시브 선택
        from src.ui.passive_selection import run_passive_selection

        passive_result = run_passive_selection(console, context)
        if passive_result is None:
            logger.info("패시브 선택 취소됨")
            return "cancel"

        # 패시브 적용
        if passive_result and passive_result.passives:
            selected_passives = passive_result.passives
            logger.info(f"패시브 선택: {len(selected_passives)}개")

        # 장비 지급 및 회복
        for member in party_members:
            _equip_best_gear(member, party_level, logger)
            member.current_hp = member.max_hp
            member.current_mp = member.max_mp

    party = Party(party_members)

    # === 2. 보스 생성 ===
    boss = EnemyGenerator.generate_boss(boss_floor, is_floor_boss=True)
    minions = EnemyGenerator.generate_enemies(boss_floor, 3, boss_battle=True)  # 보스전 잡몹 1.4배 강화
    enemies = [boss] + minions

    boss_name = "세피로스" if boss_floor == 20 else "닥터 아벨 카인"
    logger.info(f"보스 생성: {boss_name} (Lv.{boss_floor})")

    # === 3. 보스 조우 스토리 재생 ===
    if boss_floor == 20:
        from src.story.story_system import get_story_system
        from src.ui.npc_dialog_ui import render_story_sequence
        story_system = get_story_system()
        encounter_story = story_system.get_sephiroth_encounter_story()
        render_story_sequence(console, context, encounter_story, logger)
    elif boss_floor == 30:
        from src.story.story_system import get_story_system
        from src.ui.npc_dialog_ui import render_story_sequence
        story_system = get_story_system()
        encounter_story = story_system.get_cain_encounter_story()
        render_story_sequence(console, context, encounter_story, logger)

    # === 4. 전투 시작 ===
    from src.combat.combat_manager import set_combat_manager
    combat_manager = CombatManager()
    set_combat_manager(combat_manager)  # 전역 참조 설정

    # 화면 크기 가져오기
    screen_width = console.width
    screen_height = console.height

    combat_ui = CombatUI(screen_width, screen_height, combat_manager)

    # 파티 설정
    combat_manager.party = party

    # AffinityManager 설정 (연계스킬/체인어빌리티용) — 테스트모드: 호감도 최대
    try:
        from src.character.affinity import AffinityManager
        affinity_mgr = AffinityManager()
        # 보스 테스트 모드에서는 모든 파티원 간 호감도를 DEEP_BOND(500+) 레벨로 설정
        party_jobs = [c.job_id for c in party_members if hasattr(c, 'job_id')]
        for i, job_a in enumerate(party_jobs):
            for job_b in party_jobs[i+1:]:
                affinity_mgr.add_points(job_a, job_b, 600)  # DEEP_BOND 기준 500 이상
        combat_manager.affinity_manager = affinity_mgr
    except Exception as e:
        logger.warning(f"AffinityManager 설정 실패: {e}")

    # 전투 시작
    combat_manager.start_combat(party_members, enemies)

    # 팀워크 게이지 600 (체인어빌리티 테스트용) — start_combat 이후에 설정해야 덮어써지지 않음
    combat_manager.party.teamwork_gauge = 600

    # 패시브 적용 (커스텀 파티인 경우)
    if selected_passives:
        for passive in selected_passives:
            for member in party_members:
                member.activate_trait(passive.id)
            logger.debug(f"패시브 적용: {passive.name}")

    # 전투 루프
    from src.ui.input_handler import unified_input_handler
    import pygame
    import time

    logger.info("보스 전투 시작!")
    logger.info(f"초기 전투 상태: {combat_manager.state}")
    logger.info("⚡ 전투 속도: 2배 (60fps 고정)")

    # 60fps 프레임 제한 설정
    TARGET_FPS = 60
    FRAME_TIME = 1.0 / TARGET_FPS  # 0.01666... 초
    GAME_SPEED = 2.0  # 전투 속도 2배

    loop_count = 0
    last_frame_time = time.perf_counter()

    while combat_manager.state not in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
        loop_count += 1
        if loop_count % 100 == 0:
            logger.debug(f"전투 루프 {loop_count}회, 상태: {combat_manager.state}")

        # 프레임 시작 시간
        frame_start = time.perf_counter()

        # pygame 이벤트 처리 (게임패드 입력을 위해) - 더 자주 호출
        try:
            pygame.event.pump()  # pygame 이벤트 큐 업데이트
        except:
            pass

        # UI 업데이트 (게임 속도 2배)
        combat_ui.update(delta_time=GAME_SPEED)

        # 렌더링
        combat_ui.render(console)
        context.present(console)

        # 입력 처리
        action = None

        # 게임패드 입력 우선 확인
        action = unified_input_handler.get_action()

        # tcod 이벤트 처리 (키보드/마우스) - 게임패드 입력이 없을 때만
        if not action:
            # tcod 이벤트는 non-blocking으로 변경
            events = tcod.event.get()  # wait 대신 get 사용
            for event in events:
                # 윈도우 닫기
                if isinstance(event, tcod.event.Quit):
                    logger.info("전투 중단 (윈도우 닫기)")
                    return "quit"

                action = unified_input_handler.process_tcod_event(event)
                if action:
                    break

        if action:
            if combat_ui.handle_input(action):
                break

        # 60fps 유지를 위한 프레임 제한
        frame_end = time.perf_counter()
        frame_duration = frame_end - frame_start
        sleep_time = FRAME_TIME - frame_duration

        if sleep_time > 0:
            time.sleep(sleep_time)

        last_frame_time = time.perf_counter()

    # === 5. 전투 결과 ===
    logger.info(f"전투 종료! 총 루프 횟수: {loop_count}, 최종 상태: {combat_manager.state}")

    if combat_manager.state == CombatState.VICTORY:
        logger.info(f"🎉 보스 테스트 성공! {boss_name} 격파!")

        # 승리 스토리 재생
        if hasattr(combat_manager, 'victory_story') and combat_manager.victory_story:
            from src.ui.npc_dialog_ui import render_story_sequence
            render_story_sequence(console, context, combat_manager.victory_story, logger)

        return "victory"
    elif combat_manager.state == CombatState.DEFEAT:
        logger.info(f"💀 보스 테스트 실패... {boss_name}에게 패배")

        # 패배 스토리 재생
        if boss_floor == 20:
            from src.story.story_system import get_story_system
            from src.ui.npc_dialog_ui import render_story_sequence
            story_system = get_story_system()
            defeat_story = story_system.get_sephiroth_timeout_story()
            render_story_sequence(console, context, defeat_story, logger)
        elif boss_floor == 30:
            from src.story.story_system import get_story_system
            from src.ui.npc_dialog_ui import render_story_sequence
            story_system = get_story_system()
            defeat_story = story_system.get_cain_timeout_story()
            render_story_sequence(console, context, defeat_story, logger)

        return "defeat"
    else:
        logger.warning(f"⚠️ 예상치 못한 전투 상태: {combat_manager.state}")
        logger.warning(f"  - 파티 생존자: {sum(1 for m in party_members if m.is_alive)}/{len(party_members)}")
        logger.warning(f"  - 적 생존자: {sum(1 for e in enemies if e.is_alive)}/{len(enemies)}")
        return "unknown"


def _equip_best_gear(character: "Character", level: int, logger: Any) -> None:
    """
    캐릭터에게 최고급 장비 지급

    Args:
        character: 캐릭터
        level: 레벨
        logger: 로거
    """
    from src.equipment.item_system import Equipment, EquipSlot, ItemRarity, ItemType

    # 무기
    weapon = Equipment(
        item_id=f"test_weapon_{level}",
        name=f"{character.job_name} 전설급 무기",
        description="테스트용 최강 무기",
        item_type=ItemType.WEAPON,
        equip_slot=EquipSlot.WEAPON,
        rarity=ItemRarity.LEGENDARY,
        base_stats={
            "strength": level * 5,
            "magic": level * 5,
        },
        level_requirement=level,
        sell_price=level * 1000
    )
    character.equip_item("weapon", weapon)

    # 방어구
    armor = Equipment(
        item_id=f"test_armor_{level}",
        name=f"{character.job_name} 전설급 갑옷",
        description="테스트용 최강 방어구",
        item_type=ItemType.ARMOR,
        equip_slot=EquipSlot.ARMOR,
        rarity=ItemRarity.LEGENDARY,
        base_stats={
            "defense": level * 2,
            "spirit": level * 2,
            "hp": level * 5,
            "mp": level * 2
        },
        level_requirement=level,
        sell_price=level * 1000
    )
    character.equip_item("armor", armor)

    # 장신구
    accessory = Equipment(
        item_id=f"test_accessory_{level}",
        name=f"{character.job_name} 전설급 장신구",
        description="테스트용 최강 장신구",
        item_type=ItemType.ACCESSORY,
        equip_slot=EquipSlot.ACCESSORY,
        rarity=ItemRarity.LEGENDARY,
        base_stats={
            "strength": level * 1,
            "magic": level * 1,
            "defense": level * 1,
            "spirit": level * 1,
            "speed": level * 1,
            "luck": level * 1
        },
        level_requirement=level,
        sell_price=level * 1000
    )
    character.equip_item("accessory", accessory)

    logger.debug(f"{character.name} 장비 완료: 무기+방어구+장신구")


def _make_party_mode_menu(screen_width: int, screen_height: int):
    from src.ui.cursor_menu import CursorMenu, MenuItem

    return CursorMenu(
        title="보스 테스트 - 파티 구성 모드",
        items=[
            MenuItem(
                "기본 파티 (프리셋)",
                action=lambda: "default",
                description="미리 정해진 직업 조합으로 빠르게 테스트"
            ),
            MenuItem(
                "직접 파티 구성 (커스텀)",
                action=lambda: "custom",
                description="트레이닝 모드처럼 직접 직업/특성/패시브 선택"
            ),
        ],
        x=screen_width // 2 - 22,
        y=screen_height // 2 - 6,
        width=45,
        show_description=True
    )


def _boss_menu_pointer_result(menu, event: PointerEvent) -> PointerDispatchResult:
    result = menu.handle_pointer_event(event)
    if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
        return PointerDispatchResult(event=event, action=GameAction.CANCEL, value=None, tooltip=result.tooltip)
    return result


def _select_party_mode(
    console: tcod.console.Console, context: Any, logger: Any
) -> Optional[str]:
    """
    파티 구성 모드 선택 UI

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        logger: 로거

    Returns:
        "default" (기본 파티) 또는 "custom" (직접 선택), 취소 시 None
    """
    import tcod.event
    import time

    menu = _make_party_mode_menu(console.width, console.height)

    last_gamepad_check = 0
    gamepad_check_interval = 0.016

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        console.clear()
        menu.render(console)
        context.present(console)

        current_time = time.time()
        if current_time - last_gamepad_check >= gamepad_check_interval:
            gamepad_action = unified_input_handler.gamepad_handler.get_action()
            if gamepad_action == GameAction.ESCAPE:
                return None
            elif gamepad_action == GameAction.MOVE_UP:
                menu.move_cursor_up()
            elif gamepad_action == GameAction.MOVE_DOWN:
                menu.move_cursor_down()
            elif gamepad_action == GameAction.CONFIRM:
                return menu.execute_selected()
            last_gamepad_check = current_time

        for event in tcod.event.get():
            context.convert_event(event)
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event:
                pointer_result = _boss_menu_pointer_result(menu, pointer_event)
                if pointer_result.action is GameAction.CANCEL:
                    return None
                if pointer_result.value is not None:
                    return str(pointer_result.value)

            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.UP:
                    menu.move_cursor_up()
                elif event.sym == tcod.event.KeySym.DOWN:
                    menu.move_cursor_down()
                elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
                    return menu.execute_selected()
                elif event.sym == tcod.event.KeySym.ESCAPE:
                    return None
            elif isinstance(event, tcod.event.Quit):
                return None

        time.sleep(0.001)


def _select_job(
    console: tcod.console.Console,
    context: Any,
    logger: Any,
    title: Optional[str] = None,
    excluded_jobs: Optional[set] = None
) -> Optional[str]:
    """
    직업 선택 UI

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        logger: 로거
        title: 화면 타이틀
        excluded_jobs: 제외할 직업 ID 목록

    Returns:
        선택한 직업 ID (취소 시 None)
    """
    from src.ui.cursor_menu import CursorMenu, MenuItem
    from src.character.character_loader import get_all_job_names, load_character_data
    import time

    # 모든 직업 가져오기
    all_jobs = get_all_job_names()

    # 메뉴 아이템 생성
    menu_items = []
    excluded_jobs = excluded_jobs or set()
    for job_id, display_name in all_jobs.items():
        if job_id in excluded_jobs:
            continue
        job_data = load_character_data(display_name) or {}
        desc = job_data.get("description", "")
        slogan = job_data.get("slogan", "")
        full_desc = f"{desc} {(' - ' + slogan) if slogan else ''}".strip()
        menu_items.append(
            MenuItem(
                text=display_name,
                action=lambda j=job_id: j,
                description=full_desc or f"{display_name} 직업으로 보스전 테스트"
            )
        )

    # 메뉴 생성
    menu = CursorMenu(
        title=title or "직업 선택",
        items=menu_items,
        x=console.width // 2 - 20,
        y=console.height // 2 - 15,
        width=40,
        show_description=True
    )

    last_gamepad_check = 0
    gamepad_check_interval = 0.016

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        console.clear()

        # 타이틀
        title_text = title or "=== 보스 테스트 - 직업 선택 ==="
        console.print(
            (console.width - len(title_text)) // 2,
            5,
            title_text,
            fg=(255, 255, 0)
        )

        # 메뉴 렌더링
        menu.render(console)
        context.present(console)

        # 입력 처리
        current_time = time.time()
        if current_time - last_gamepad_check >= gamepad_check_interval:
            gamepad_action = unified_input_handler.gamepad_handler.get_action()
            if gamepad_action:
                if gamepad_action == GameAction.MOVE_UP:
                    menu.move_cursor_up()
                elif gamepad_action == GameAction.MOVE_DOWN:
                    menu.move_cursor_down()
                elif gamepad_action == GameAction.CONFIRM:
                    selected_job = menu.execute_selected()
                    if selected_job:
                        logger.info(f"직업 선택: {selected_job}")
                        return selected_job
                elif gamepad_action == GameAction.ESCAPE or gamepad_action == GameAction.CANCEL:
                    return None
            last_gamepad_check = current_time

        for event in tcod.event.get():
            context.convert_event(event)
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event:
                pointer_result = _boss_menu_pointer_result(menu, pointer_event)
                if pointer_result.action is GameAction.CANCEL:
                    return None
                if pointer_result.value:
                    selected_job = str(pointer_result.value)
                    logger.info(f"직업 선택: {selected_job}")
                    return selected_job

            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.UP:
                    menu.move_cursor_up()
                elif event.sym == tcod.event.KeySym.DOWN:
                    menu.move_cursor_down()
                elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
                    selected_job = menu.execute_selected()
                    if selected_job:
                        logger.info(f"직업 선택: {selected_job}")
                        return selected_job
                elif event.sym == tcod.event.KeySym.ESCAPE:
                    return None
            elif isinstance(event, tcod.event.Quit):
                return None

        time.sleep(0.001)


def _input_level(
    console: tcod.console.Console, context: Any, logger: Any, default_level: int
) -> Optional[int]:
    """
    레벨 입력 UI

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        logger: 로거
        default_level: 기본 레벨 (보스 층수)

    Returns:
        입력한 레벨 (취소 시 None)
    """
    import tcod.event
    import time

    level_str = str(default_level)  # 기본값 설정

    last_gamepad_check = 0
    gamepad_check_interval = 0.016

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        # 게임패드 입력 체크
        current_time = time.time()
        if current_time - last_gamepad_check >= gamepad_check_interval:
            gamepad_action = unified_input_handler.gamepad_handler.get_action()

            if gamepad_action == GameAction.ESCAPE or gamepad_action == GameAction.CANCEL:
                return None
            elif gamepad_action == GameAction.CONFIRM:
                if level_str:
                    try:
                        level = int(level_str)
                        if 1 <= level <= 30:
                            logger.info(f"레벨 입력: {level}")
                            return level
                        else:
                            logger.warning("레벨은 1-30 사이여야 합니다")
                    except ValueError:
                        logger.warning("올바른 숫자를 입력하세요")

            last_gamepad_check = current_time

        # 키보드 이벤트 처리
        events = list(tcod.event.get())
        for event in events:
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.RETURN or event.sym == tcod.event.KeySym.KP_ENTER:
                    if level_str:
                        try:
                            level = int(level_str)
                            if 1 <= level <= 30:
                                logger.info(f"레벨 입력: {level}")
                                return level
                            else:
                                logger.warning("레벨은 1-30 사이여야 합니다")
                        except ValueError:
                            logger.warning("올바른 숫자를 입력하세요")

                elif event.sym == tcod.event.KeySym.BACKSPACE:
                    if level_str:
                        level_str = level_str[:-1]

                elif event.sym == tcod.event.KeySym.ESCAPE:
                    return None

                else:
                    # 숫자 입력 (0-9)
                    digit_map = {
                        tcod.event.KeySym.N0: '0', tcod.event.KeySym.N1: '1',
                        tcod.event.KeySym.N2: '2', tcod.event.KeySym.N3: '3',
                        tcod.event.KeySym.N4: '4', tcod.event.KeySym.N5: '5',
                        tcod.event.KeySym.N6: '6', tcod.event.KeySym.N7: '7',
                        tcod.event.KeySym.N8: '8', tcod.event.KeySym.N9: '9',
                        # 키패드 숫자
                        tcod.event.KeySym.KP_0: '0', tcod.event.KeySym.KP_1: '1',
                        tcod.event.KeySym.KP_2: '2', tcod.event.KeySym.KP_3: '3',
                        tcod.event.KeySym.KP_4: '4', tcod.event.KeySym.KP_5: '5',
                        tcod.event.KeySym.KP_6: '6', tcod.event.KeySym.KP_7: '7',
                        tcod.event.KeySym.KP_8: '8', tcod.event.KeySym.KP_9: '9',
                    }
                    if event.sym in digit_map and len(level_str) < 2:
                        level_str += digit_map[event.sym]
            elif isinstance(event, tcod.event.Quit):
                return None

        # 화면 그리기
        console.clear()
        title = "=== 보스 테스트 - 레벨 입력 ==="
        console.print(
            (console.width - len(title)) // 2,
            console.height // 2 - 5,
            title,
            fg=(255, 255, 0)
        )
        desc = f"캐릭터 레벨을 입력하세요 (1-30, 기본: {default_level})"
        console.print(
            (console.width - len(desc)) // 2,
            console.height // 2 - 2,
            desc,
            fg=(200, 200, 200)
        )
        input_text = f"레벨: {level_str}_"
        console.print(
            (console.width - len(input_text)) // 2,
            console.height // 2,
            input_text,
            fg=(255, 255, 255)
        )
        controls = "[Enter] 확인  [Backspace] 지우기  [Esc] 취소"
        console.print(
            (console.width - len(controls)) // 2,
            console.height // 2 + 3,
            controls,
            fg=(150, 150, 150)
        )
        context.present(console)

        time.sleep(0.001)
