#!/usr/bin/env python3
"""
Dawn of Stellar - 별빛의 여명

메인 엔트리 포인트
"""

import sys
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import initialize_config, get_config
from src.core.logger import get_logger, Loggers
from src.core.event_bus import event_bus


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="Dawn of Stellar - 별빛의 여명"
    )

    parser.add_argument(
        "--dev",
        action="store_true",
        help="개발 모드로 실행 (모든 클래스 잠금 해제)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드로 실행"
    )

    parser.add_argument(
        "--log",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="로그 레벨 설정"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="설정 파일 경로"
    )

    parser.add_argument(
        "--mobile-server",
        action="store_true",
        help="모바일 서버 모드로 실행"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="서버 포트 (모바일 서버 모드)"
    )

    return parser.parse_args()


def main() -> int:
    """
    메인 함수

    Returns:
        종료 코드 (0: 정상, 1: 에러)
    """
    # 명령줄 인자 파싱
    args = parse_arguments()

    try:
        # 설정 초기화
        config = initialize_config(args.config)

        # 명령줄 옵션으로 설정 오버라이드
        if args.dev:
            config.set("development.enabled", True)
            config.set("development.unlock_all_classes", True)

        if args.debug:
            config.set("development.debug_mode", True)

        # 로거 초기화
        logger = get_logger(Loggers.SYSTEM)
        logger.info("=" * 60)
        logger.info("Dawn of Stellar - 별빛의 여명 시작")
        logger.info(f"버전: {config.get('game.version', '5.0.0')}")
        logger.info(f"언어: {config.language}")
        logger.info(f"개발 모드: {config.development_mode}")
        logger.info(f"디버그 모드: {config.debug_mode}")
        logger.info("=" * 60)

        # TCOD 디스플레이 초기화
        from src.ui.tcod_display import get_display
        from src.ui.main_menu import run_main_menu, MenuResult

        display = get_display()
        logger.info("TCOD 디스플레이 초기화 완료")

        # 스킬 시스템 초기화
        from src.character.skills.skill_initializer import initialize_all_skills
        if not initialize_all_skills():
            logger.error("스킬 초기화 실패 - 게임을 종료합니다")
            return 1

        # 장비 효과 시스템 초기화
        from src.equipment.equipment_effects import get_equipment_effect_manager
        effect_manager = get_equipment_effect_manager()
        logger.info("장비 효과 시스템 초기화 완료")

        # 인트로 스토리 표시 (최초 1회)
        intro_shown = False
        if not intro_shown:
            from src.ui.intro_story import show_intro_story
            logger.info("인트로 스토리 시작")
            show_intro_story(display.console, display.context)
            intro_shown = True
            logger.info("인트로 스토리 완료")

        # 메인 게임 루프
        while True:
            # 메인 메뉴 실행
            menu_result = run_main_menu(display.console, display.context)
            logger.info(f"메인 메뉴 결과: {menu_result.value}")

            if menu_result == MenuResult.QUIT:
                break
            elif menu_result == MenuResult.CONTINUE:
                # 게임 불러오기
                logger.info("계속하기 - 저장된 게임 불러오기")
                from src.ui.save_load_ui import show_load_screen
                from src.persistence.save_system import deserialize_dungeon, deserialize_item
                from src.character.character import Character
                from src.equipment.inventory import Inventory

                loaded_state = show_load_screen(display.console, display.context)

                if loaded_state:
                    logger.info("게임 불러오기 성공")
                    # 불러온 데이터로 게임 재개
                    from src.persistence.save_system import (
                        deserialize_party_member,
                        deserialize_dungeon,
                        deserialize_inventory
                    )
                    from src.world.exploration import ExplorationSystem
                    from src.ui.world_ui import run_exploration
                    from src.ui.combat_ui import run_combat, CombatState
                    from src.combat.experience_system import (
                        RewardCalculator,
                        distribute_party_experience
                    )
                    from src.ui.reward_ui import show_reward_screen
                    from src.world.enemy_generator import EnemyGenerator

                    # 파티 복원
                    try:
                        party = [deserialize_party_member(member_data) for member_data in loaded_state.get("party", [])]
                        logger.info(f"파티 복원 완료: {len(party)}명")
                    except Exception as e:
                        logger.error(f"파티 복원 실패: {e}", exc_info=True)
                        logger.error(f"파티 데이터: {loaded_state.get('party', [])}")
                        raise

                    # 던전 복원
                    dungeon = deserialize_dungeon(loaded_state["dungeon"])
                    floor_number = loaded_state.get("floor_number", 1)
                    logger.info(f"던전 복원 완료: {floor_number}층")

                    # 인벤토리 복원 (파티 정보 전달로 최대 무게 계산)
                    inventory_data = loaded_state.get("inventory", {})
                    inventory = deserialize_inventory(inventory_data, party=party)
                    logger.info(f"인벤토리 복원 완료: 골드 {inventory.gold}, 무게 {inventory.current_weight}kg/{inventory.max_weight}kg")

                    # 플레이어 위치 복원
                    player_pos = loaded_state.get("player_position", {"x": 0, "y": 0})

                    # 탐험 시스템 초기화
                    exploration = ExplorationSystem(dungeon, party, floor_number, inventory)
                    exploration.player.x = player_pos["x"]
                    exploration.player.y = player_pos["y"]

                    # 키 복원
                    exploration.player_keys = loaded_state.get("keys", [])

                    # BGM 제어 플래그 (첫 탐험 시작 및 층 변경 시에만 재생)
                    play_dungeon_bgm = True

                    # 게임 통계 초기화 (불러온 게임용)
                    game_stats = {
                        "enemies_defeated": loaded_state.get("enemies_defeated", 0),
                        "max_floor_reached": loaded_state.get("max_floor_reached", floor_number),
                        "total_gold_earned": loaded_state.get("total_gold_earned", 0),
                        "total_exp_earned": loaded_state.get("total_exp_earned", 0),
                        "save_slot": loaded_state.get("save_slot", None)
                    }

                    # 탐험 시스템에 게임 통계 전달
                    exploration.game_stats = game_stats

                    # 탐험 계속 (새 게임과 동일한 루프)
                    while True:
                        result, data = run_exploration(
                            display.console,
                            display.context,
                            exploration,
                            inventory,
                            party,
                            play_bgm_on_start=play_dungeon_bgm
                        )

                        logger.info(f"탐험 결과: {result}")

                        if result == "quit":
                            logger.info("게임 종료")
                            break
                        elif result == "combat":
                            # 전투 처리 (새 게임과 동일)
                            logger.info("⚔ 전투 시작!")

                            # 전투 데이터 처리 (딕셔너리 형식)
                            if data and isinstance(data, dict):
                                num_enemies = data.get("num_enemies", 0)
                                map_enemies = data.get("enemies", [])
                                logger.info(f"전투 데이터: 적 {num_enemies}마리, 맵 엔티티 {len(map_enemies)}개")
                            elif data and isinstance(data, list):
                                # 하위 호환성: 리스트로 받은 경우
                                num_enemies = len(data)
                                map_enemies = data
                                logger.info(f"전투 데이터(레거시): 적 {num_enemies}마리")
                            else:
                                num_enemies = 0
                                map_enemies = []
                                logger.info("전투 데이터 없음")

                            if num_enemies > 0:
                                enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
                                logger.info(f"적 {len(enemies)}명 생성: {[e.name for e in enemies]}")
                            else:
                                enemies = EnemyGenerator.generate_enemies(floor_number)
                                logger.info(f"적 {len(enemies)}명 생성(기본값)")

                            combat_result = run_combat(
                                display.console,
                                display.context,
                                party,
                                enemies
                            )

                            logger.info(f"전투 결과: {combat_result}")

                            if combat_result == CombatState.VICTORY:
                                logger.info("✅ 승리!")

                                # 맵에서 적 엔티티 제거
                                if map_enemies:
                                    exploration.game_stats["enemies_defeated"] += len(map_enemies)
                                    for enemy_entity in map_enemies:
                                        if enemy_entity in exploration.enemies:
                                            exploration.enemies.remove(enemy_entity)
                                    logger.info(f"맵 적 엔티티 {len(map_enemies)}개 제거 (총 격파: {exploration.game_stats['enemies_defeated']}마리)")

                                rewards = RewardCalculator.calculate_combat_rewards(
                                    enemies,
                                    floor_number,
                                    is_boss_fight=False
                                )

                                level_up_info = distribute_party_experience(
                                    party,
                                    rewards["experience"]
                                )

                                # 통계 업데이트
                                exploration.game_stats["total_gold_earned"] += rewards.get("gold", 0)
                                exploration.game_stats["total_exp_earned"] += rewards["experience"]

                                show_reward_screen(
                                    display.console,
                                    display.context,
                                    rewards,
                                    level_up_info
                                )

                                for item in rewards.get("items", []):
                                    if not inventory.add_item(item):
                                        logger.warning(f"인벤토리 가득 참! {item.name} 버려짐")

                                inventory.add_gold(rewards.get("gold", 0))

                                # 별의 파편은 게임 정산 시에만 지급 (로그라이크 방식)

                                # 전투 후 던전 BGM 재생
                                from src.audio import play_bgm
                                play_bgm("dungeon_normal", loop=True, fade_in=True)
                                logger.info("던전 BGM 재생")
                                play_dungeon_bgm = False
                                continue
                            elif combat_result == CombatState.DEFEAT:
                                logger.info("❌ 패배... 게임 오버")

                                # 게임 정산 (패배)
                                from src.ui.game_result_ui import show_game_result
                                show_game_result(
                                    display.console,
                                    display.context,
                                    is_victory=False,
                                    max_floor=exploration.game_stats["max_floor_reached"],
                                    enemies_defeated=exploration.game_stats["enemies_defeated"],
                                    total_gold=exploration.game_stats["total_gold_earned"],
                                    total_exp=exploration.game_stats["total_exp_earned"],
                                    save_slot=exploration.game_stats.get("save_slot", None)
                                )
                                break
                            else:
                                logger.info("🏃 도망쳤다")
                                # 도망 후 던전 BGM 재생
                                from src.audio import play_bgm
                                play_bgm("dungeon_normal", loop=True, fade_in=True)
                                logger.info("던전 BGM 재생")
                                play_dungeon_bgm = False
                                continue

                        elif result == "floor_down":
                            floor_number += 1
                            exploration.game_stats["max_floor_reached"] = max(exploration.game_stats["max_floor_reached"], floor_number)
                            logger.info(f"⬇ 다음 층: {floor_number}층 (최대: {exploration.game_stats['max_floor_reached']}층)")
                            from src.world.dungeon_generator import DungeonGenerator
                            dungeon_gen = DungeonGenerator(width=80, height=50)
                            dungeon = dungeon_gen.generate(floor_number)
                            exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                            # 층 변경 시 BGM 재생
                            play_dungeon_bgm = True
                            continue
                        elif result == "floor_up":
                            if floor_number > 1:
                                floor_number -= 1
                                logger.info(f"⬆ 이전 층: {floor_number}층")
                                from src.world.dungeon_generator import DungeonGenerator
                                dungeon_gen = DungeonGenerator(width=80, height=50)
                                dungeon = dungeon_gen.generate(floor_number)
                                exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                # 층 변경 시 BGM 재생
                                play_dungeon_bgm = True
                                continue
                            else:
                                logger.info("🎉 던전 탈출 성공!")

                                # 게임 정산 (승리)
                                from src.ui.game_result_ui import show_game_result
                                show_game_result(
                                    display.console,
                                    display.context,
                                    is_victory=True,
                                    max_floor=exploration.game_stats["max_floor_reached"],
                                    enemies_defeated=exploration.game_stats["enemies_defeated"],
                                    total_gold=exploration.game_stats["total_gold_earned"],
                                    total_exp=exploration.game_stats["total_exp_earned"],
                                    save_slot=exploration.game_stats.get("save_slot", None)
                                )
                                break
                else:
                    logger.info("게임 불러오기 취소")
                    continue

            elif menu_result == MenuResult.NEW_GAME:
                logger.info("새 게임 시작 - 파티 구성")

                # 파티 구성
                from src.ui.party_setup import run_party_setup
                party = run_party_setup(display.console, display.context)

                if party:
                    logger.info(f"파티 구성 완료: {len(party)}명")
                    for i, member in enumerate(party):
                        logger.info(
                            f"  {i+1}. {member.character_name} ({member.job_name})"
                        )

                    # PartyMember를 Character 객체로 변환
                    from src.character.character import Character
                    character_party = []
                    for member in party:
                        char = Character(
                            name=member.character_name,
                            character_class=member.job_id,
                            level=1
                        )
                        # 경험치 초기화
                        char.experience = 0
                        character_party.append(char)

                    # 이제 character_party를 사용
                    party = character_party
                    logger.info("파티 멤버를 Character 객체로 변환 완료")

                    # 특성 선택
                    from src.ui.trait_selection import run_trait_selection
                    trait_selections = run_trait_selection(
                        display.console,
                        display.context,
                        party
                    )

                    if trait_selections:
                        logger.info(f"특성 선택 완료: {len(trait_selections)}명")
                        for traits in trait_selections:
                            logger.info(
                                f"  {traits.character_name} ({traits.job_name}): "
                                f"{', '.join([t.name for t in traits.selected_traits])}"
                            )

                        # 패시브 선택
                        from src.ui.passive_selection import run_passive_selection
                        passive_selection = run_passive_selection(
                            display.console,
                            display.context
                        )

                        if passive_selection:
                            logger.info(
                                f"패시브 선택 완료: {len(passive_selection.passives)}개, "
                                f"총 코스트 {passive_selection.total_cost}"
                            )
                            for passive in passive_selection.passives:
                                logger.info(
                                    f"  [{passive.cost}] {passive.name}"
                                )

                            # 게임 시작!
                            logger.info("=== 게임 시작! ===")
                            from src.world.dungeon_generator import DungeonGenerator
                            from src.world.exploration import ExplorationSystem
                            from src.world.enemy_generator import EnemyGenerator
                            from src.ui.world_ui import run_exploration
                            from src.ui.combat_ui import run_combat, CombatState
                            from src.combat.experience_system import (
                                RewardCalculator,
                                distribute_party_experience
                            )
                            from src.ui.reward_ui import show_reward_screen
                            from src.equipment.inventory import Inventory

                            # 인벤토리 생성 (무게 기반 - 파티 스탯에 연동)
                            inventory = Inventory(base_weight=50.0, party=party)
                            inventory.add_gold(200)  # 시작 골드
                            logger.info(f"인벤토리 생성 완료: {inventory.max_weight}kg 가능")

                            # 무게 제한 세부 내역 로그
                            breakdown = inventory.weight_breakdown
                            logger.info(
                                f"무게 제한 세부: 기본 {breakdown['base']}kg + "
                                f"파티 {breakdown['party_count']}kg + "
                                f"힘 {breakdown['strength_bonus']}kg + "
                                f"레벨 {breakdown['level_bonus']}kg = "
                                f"총 {inventory.max_weight}kg"
                            )

                            floor_number = 1

                            # 게임 통계 초기화
                            game_stats = {
                                "enemies_defeated": 0,
                                "max_floor_reached": 1,
                                "total_gold_earned": 0,
                                "total_exp_earned": 0,
                                "save_slot": None
                            }

                            # 던전 및 탐험 초기화 (층 변경 시에만 재생성)
                            dungeon_gen = DungeonGenerator(width=80, height=50)
                            dungeon = dungeon_gen.generate(floor_number)
                            exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)

                            # BGM 제어 플래그 (첫 탐험 시작 및 층 변경 시에만 재생)
                            play_dungeon_bgm = True

                            while True:
                                # 탐험 시작 (기존 exploration 객체 재사용)
                                result, data = run_exploration(
                                    display.console,
                                    display.context,
                                    exploration,
                                    inventory,
                                    party,
                                    play_bgm_on_start=play_dungeon_bgm
                                )

                                logger.info(f"탐험 결과: {result}")

                                if result == "quit":
                                    logger.info("게임 종료")
                                    break
                                elif result == "combat":
                                    # 전투 시작!
                                    logger.info("⚔ 전투 시작!")

                                    # 전투 데이터 처리 (딕셔너리 형식)
                                    if data and isinstance(data, dict):
                                        num_enemies = data.get("num_enemies", 0)
                                        map_enemies = data.get("enemies", [])
                                        logger.warning(f"[DEBUG] 전투 데이터: 적 {num_enemies}마리, 맵 엔티티 {len(map_enemies)}개")
                                    else:
                                        # fallback
                                        num_enemies = 0
                                        map_enemies = []
                                        logger.warning("[DEBUG] 전투 데이터 없음 - 랜덤 생성")

                                    # 적 생성
                                    if num_enemies > 0:
                                        enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
                                        logger.info(f"적 {len(enemies)}명 생성: {[e.name for e in enemies]}")
                                    else:
                                        # fallback: 랜덤 생성
                                        enemies = EnemyGenerator.generate_enemies(floor_number)
                                        logger.info(f"적 {len(enemies)}명 생성(기본값)")

                                    # 전투 실행
                                    combat_result = run_combat(
                                        display.console,
                                        display.context,
                                        party,
                                        enemies
                                    )

                                    logger.info(f"전투 결과: {combat_result}")

                                    if combat_result == CombatState.VICTORY:
                                        logger.info("✅ 승리!")

                                        # 필드에서 해당 적들 제거
                                        if map_enemies:
                                            exploration.game_stats["enemies_defeated"] += len(map_enemies)  # 통계 업데이트
                                            for enemy_entity in map_enemies:
                                                if enemy_entity in exploration.enemies:
                                                    exploration.enemies.remove(enemy_entity)
                                            logger.warning(f"[DEBUG] 맵 적 엔티티 {len(map_enemies)}마리 제거됨 (총 격파: {exploration.game_stats['enemies_defeated']}마리)")

                                        # 보상 계산
                                        rewards = RewardCalculator.calculate_combat_rewards(
                                            enemies,
                                            floor_number,
                                            is_boss_fight=False
                                        )

                                        # 경험치 분배
                                        level_up_info = distribute_party_experience(
                                            party,
                                            rewards["experience"]
                                        )

                                        # 통계 업데이트
                                        exploration.game_stats["total_gold_earned"] += rewards.get("gold", 0)
                                        exploration.game_stats["total_exp_earned"] += rewards["experience"]

                                        # 보상 화면 표시
                                        show_reward_screen(
                                            display.console,
                                            display.context,
                                            rewards,
                                            level_up_info
                                        )

                                        # 아이템을 인벤토리에 추가
                                        for item in rewards.get("items", []):
                                            if not inventory.add_item(item):
                                                logger.warning(f"인벤토리 가득 참! {item.name} 버려짐")

                                        # 골드 추가
                                        inventory.add_gold(rewards.get("gold", 0))

                                        # 별의 파편은 게임 정산 시에만 지급 (로그라이크 방식)

                                        # 전투 후 던전 BGM 재생
                                        from src.audio import play_bgm
                                        play_bgm("dungeon_normal", loop=True, fade_in=True)
                                        logger.info("던전 BGM 재생")
                                        play_dungeon_bgm = False
                                        continue  # 탐험 계속
                                    elif combat_result == CombatState.DEFEAT:
                                        logger.info("❌ 패배... 게임 오버")

                                        # 게임 정산
                                        from src.ui.game_result_ui import show_game_result
                                        show_game_result(
                                            display.console,
                                            display.context,
                                            is_victory=False,
                                            max_floor=exploration.game_stats["max_floor_reached"],
                                            enemies_defeated=exploration.game_stats["enemies_defeated"],
                                            total_gold=exploration.game_stats["total_gold_earned"],
                                            total_exp=exploration.game_stats["total_exp_earned"],
                                            save_slot=exploration.game_stats.get("save_slot", None)
                                        )
                                        break
                                    else:
                                        logger.info("🏃 도망쳤다")
                                        # 도망 후 던전 BGM 재생
                                        from src.audio import play_bgm
                                        play_bgm("dungeon_normal", loop=True, fade_in=True)
                                        logger.info("던전 BGM 재생")
                                        play_dungeon_bgm = False
                                        continue

                                elif result == "floor_down":
                                    floor_number += 1
                                    exploration.game_stats["max_floor_reached"] = max(exploration.game_stats["max_floor_reached"], floor_number)
                                    logger.info(f"⬇ 다음 층: {floor_number}층 (최대: {exploration.game_stats['max_floor_reached']}층)")
                                    # 새 던전 생성
                                    dungeon = dungeon_gen.generate(floor_number)
                                    exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                    # 층 변경 시 BGM 재생
                                    play_dungeon_bgm = True
                                    continue
                                elif result == "floor_up":
                                    if floor_number > 1:
                                        floor_number -= 1
                                        logger.info(f"⬆ 이전 층: {floor_number}층")
                                        # 새 던전 생성
                                        dungeon = dungeon_gen.generate(floor_number)
                                        exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                        # 층 변경 시 BGM 재생
                                        play_dungeon_bgm = True
                                        continue
                                    else:
                                        logger.info("🎉 던전 탈출 성공!")

                                        # 게임 정산 (승리)
                                        from src.ui.game_result_ui import show_game_result
                                        show_game_result(
                                            display.console,
                                            display.context,
                                            is_victory=True,
                                            max_floor=exploration.game_stats["max_floor_reached"],
                                            enemies_defeated=exploration.game_stats["enemies_defeated"],
                                            total_gold=exploration.game_stats["total_gold_earned"],
                                            total_exp=exploration.game_stats["total_exp_earned"],
                                            save_slot=exploration.game_stats.get("save_slot", None)
                                        )
                                        break

                            break
                        else:
                            logger.info("패시브 선택 취소 - 메인 메뉴로")
                            continue
                    else:
                        logger.info("특성 선택 취소 - 메인 메뉴로")
                        continue
                else:
                    logger.info("파티 구성 취소 - 메인 메뉴로")
                    continue
            elif menu_result == MenuResult.CONTINUE:
                logger.info("게임 계속하기 (구현 예정)")
                # TODO: 세이브 로드
                break
            elif menu_result == MenuResult.SHOP:
                logger.info("상점 열기")
                from src.ui.shop_ui import open_shop
                # 상점은 골드가 필요하므로 임시로 None 전달 (메인 메뉴에서는 골드가 없음)
                # TODO: 메타 진행용 별빛의 파편 같은 별도 화폐 시스템 구현
                open_shop(display.console, display.context, inventory=None)
                continue
            elif menu_result == MenuResult.SETTINGS:
                logger.info("설정 열기")
                from src.ui.settings_ui import open_settings
                open_settings(display.console, display.context)
                continue

        # 정리
        display.close()

        logger.info("게임 종료")
        return 0

    except Exception as e:
        print(f"\n❌ 에러 발생: {str(e)}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
