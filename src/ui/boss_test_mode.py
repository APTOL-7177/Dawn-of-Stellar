"""
보스 테스트 모드

--test-boss 플래그로 실행 시 바로 보스 전투 시작
"""

import tcod
from typing import Any, TYPE_CHECKING

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

    # === 1. 테스트 파티 생성 (레벨 20 또는 30, 풀장비) ===
    party_level = boss_floor

    # 4명의 다양한 직업 파티
    if boss_floor == 20:
        job_names = ["warrior", "archer", "magician", "monk"]
        display_names = ["전사", "궁수", "마법사", "몽크"]
    else:  # 30층
        job_names = ["illusionist", "berserker", "vampire", "time_mage"]
        display_names = ["환술사", "버서커", "뱀파이어", "시간술사"]

    party_members = []
    for i, (job_name, display_name) in enumerate(zip(job_names, display_names)):
        char = Character(f"테스터{i+1}", job_name)

        # 레벨 설정
        for _ in range(party_level - 1):
            char.level_up()

        # 풀장비 지급 (레벨에 맞는 최고급 장비)
        _equip_best_gear(char, party_level, logger)

        # HP/MP 완전 회복
        char.current_hp = char.max_hp
        char.current_mp = char.max_mp

        party_members.append(char)
        logger.info(f"파티원 생성: {display_name} (Lv.{party_level})")

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
    combat_manager = CombatManager()

    # 화면 크기 가져오기
    screen_width = console.width
    screen_height = console.height

    combat_ui = CombatUI(screen_width, screen_height, combat_manager)

    # 파티 설정
    combat_manager.party = party

    # 전투 시작
    combat_manager.start_combat(party_members, enemies)

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
            "speed": level * 2,
            "luck": level
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
            "defense": level * 5,
            "spirit": level * 5,
            "hp": level * 20,
            "mp": level * 10
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
            "strength": level * 3,
            "magic": level * 3,
            "defense": level * 3,
            "spirit": level * 3,
            "speed": level * 3,
            "luck": level * 2
        },
        level_requirement=level,
        sell_price=level * 1000
    )
    character.equip_item("accessory", accessory)

    logger.debug(f"{character.name} 장비 완료: 무기+방어구+장신구")
