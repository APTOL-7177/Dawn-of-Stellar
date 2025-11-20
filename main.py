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

        # 핫 리로드 시스템 초기화 (개발 모드일 때만)
        hot_reload_enabled = config.development_mode or args.dev
        if hot_reload_enabled:
            try:
                from src.core.hot_reload import start_hot_reload
                start_hot_reload(enabled=True)
                logger.info("🔥 핫 리로드 활성화됨 - 코드 변경 시 자동 반영")
            except Exception as e:
                logger.warning(f"핫 리로드 초기화 실패: {e}")
                logger.info("핫 리로드 없이 계속 실행합니다")
                hot_reload_enabled = False
        else:
            hot_reload_enabled = False

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

        # 게임 모드 관리자 초기화
        from src.multiplayer.game_mode import get_game_mode_manager, GameMode
        game_mode_manager = get_game_mode_manager()
        game_mode_manager.set_single_player()  # 기본값: 싱글플레이

        # 메타 진행 시스템 로드
        from src.persistence.meta_progress import get_meta_progress, save_meta_progress
        meta_progress = get_meta_progress()

        # 인트로 스토리 표시 (항상 표시)
        from src.ui.intro_story import show_intro_story
        logger.info("인트로 스토리 시작")
        show_intro_story(display.console, display.context)
        logger.info("인트로 스토리 완료")

        # 인트로 후 튜토리얼 시작 여부 묻기 (최초 1회)
        if not meta_progress.tutorial_offered:
            from src.tutorial.tutorial_integration import TutorialIntegration

            # 튜토리얼 통합 시스템 초기화
            tutorial_integration = TutorialIntegration(display.console, display.context)

            # 튜토리얼 시작 여부 묻기
            if tutorial_integration._ask_start_tutorial():
                logger.info("사용자가 튜토리얼 시작 선택")

                # 튜토리얼 인트로 표시
                tutorial_integration.show_tutorial_intro()

                # 플레이 가능한 튜토리얼 실행
                from src.tutorial.tutorial_playable import run_playable_tutorial
                tutorial_completed = run_playable_tutorial(display.console, display.context)

                if tutorial_completed:
                    logger.info("튜토리얼 완료")
                else:
                    logger.info("튜토리얼 중단")
            else:
                logger.info("사용자가 튜토리얼 건너뛰기 선택")

            meta_progress.tutorial_offered = True
            save_meta_progress()
            logger.info("튜토리얼 권장 상태 저장 완료")

        # 메인 게임 루프
        while True:
            # 핫 리로드 체크 (개발 모드일 때만)
            if hot_reload_enabled:
                try:
                    from src.core.hot_reload import check_and_reload
                    reloaded = check_and_reload()
                    if reloaded:
                        logger.info(f"📦 재로드된 모듈: {', '.join(reloaded)}")
                except Exception as e:
                    logger.debug(f"핫 리로드 체크 중 오류 (무시): {e}")
            
            # 메인 메뉴 실행
            menu_result = run_main_menu(display.console, display.context)
            logger.info(f"메인 메뉴 결과: {menu_result.value}")

            if menu_result == MenuResult.QUIT:
                break
            elif menu_result == MenuResult.MULTIPLAYER:
                # 멀티플레이 메뉴
                logger.info("멀티플레이 모드 선택")
                from src.ui.multiplayer_menu import show_multiplayer_menu
                multiplayer_result = show_multiplayer_menu(display.console, display.context)
                
                if multiplayer_result:
                    # 멀티플레이 세션 시작
                    logger.info(f"멀티플레이 세션 시작: {multiplayer_result}")
                    mode = multiplayer_result.get("mode")
                    
                    if mode == "host":
                        # 호스트 게임 시작
                        logger.info("호스트 모드: 게임 세션 생성 중...")
                        
                        # 멀티플레이 모드 설정
                        from src.multiplayer.game_mode import get_game_mode_manager, MultiplayerMode
                        game_mode_manager = get_game_mode_manager()
                        game_mode_manager.set_multiplayer(
                            player_count=4,  # 최대 4인
                            is_host=True,
                            session_id=None
                        )
                        
                        # 세션 생성
                        from src.multiplayer.session import MultiplayerSession
                        from src.multiplayer.network import HostNetworkManager
                        from uuid import uuid4
                        
                        local_player_id = str(uuid4())[:8]
                        session = MultiplayerSession(max_players=4)
                        session.host_id = local_player_id
                        game_mode_manager.local_player_id = local_player_id
                        game_mode_manager.is_host = True
                        
                        # 로컬 플레이어 추가
                        from src.multiplayer.player import MultiplayerPlayer
                        local_player = MultiplayerPlayer(
                            player_id=local_player_id,
                            player_name="호스트",
                            x=0,
                            y=0,
                            party=[],
                            is_host=True
                        )
                        session.add_player(local_player)
                        session.local_player_id = local_player_id
                        
                        # 네트워크 매니저 생성 및 서버 시작
                        network_manager = HostNetworkManager(port=5000, session=session)
                        network_manager.player_id = local_player_id
                        
                        # 비동기 서버 시작
                        import asyncio
                        server_loop = None
                        server_task = None
                        try:
                            server_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(server_loop)
                            
                            # 서버 시작 (백그라운드 태스크)
                            server_task = server_loop.create_task(network_manager.start_server())
                            
                            # 서버 시작 대기 (약간의 지연)
                            server_loop.run_until_complete(asyncio.sleep(0.5))
                            
                            logger.info(f"멀티플레이 세션 생성 완료: {session.session_id}")
                            # 로컬 네트워크 IP 주소 가져오기
                            local_ip = network_manager.local_ip
                            logger.info(f"호스트 서버 시작됨: ws://0.0.0.0:5000")
                            logger.info(f"로컬 네트워크 접속 주소: ws://{local_ip}:5000")
                            logger.info(f"같은 네트워크의 플레이어들은 이 주소로 연결하세요: {local_ip}:5000")
                            logger.info("참고: 외부 네트워크에서 접속하려면 공인 IP와 포트 포워딩이 필요합니다")
                            
                            # 서버 루프는 별도 스레드에서 실행 (게임 루프와 병렬)
                            import threading
                            def run_server_loop():
                                try:
                                    asyncio.set_event_loop(server_loop)
                                    server_loop.run_forever()
                                except Exception as e:
                                    logger.error(f"서버 루프 오류: {e}", exc_info=True)
                                finally:
                                    server_loop.close()
                            
                            server_thread = threading.Thread(target=run_server_loop, daemon=True)
                            server_thread.start()
                            logger.info("서버 백그라운드 스레드 시작")
                            
                        except Exception as e:
                            logger.error(f"서버 시작 실패: {e}", exc_info=True)
                            logger.warning("서버 없이 로컬 모드로 계속 진행합니다")
                            server_loop = None
                            server_task = None
                        
                        # 멀티플레이 로비 화면 (인원 모집)
                        from src.ui.multiplayer_lobby import show_multiplayer_lobby
                        lobby_result = show_multiplayer_lobby(
                            display.console,
                            display.context,
                            session,
                            network_manager,
                            local_player_id,
                            is_host=True
                        )
                        
                        if not lobby_result or lobby_result.get("cancelled"):
                            logger.info("로비 취소")
                            continue
                        
                        if not lobby_result.get("completed"):
                            continue
                        
                        player_count = lobby_result.get("player_count", 1)
                        local_allocation = lobby_result.get("local_allocation", 4)
                        
                        logger.info(f"로비 완료: {player_count}명 참여, 호스트 캐릭터 할당: {local_allocation}명")
                        
                        # 멀티플레이 파티 설정 (각 플레이어가 자신의 캐릭터 선택)
                        from src.ui.multiplayer_party_setup import run_multiplayer_party_setup
                        party_result = run_multiplayer_party_setup(
                            display.console,
                            display.context,
                            session=session,
                            network_manager=network_manager,
                            local_player_id=local_player_id,
                            character_allocation=local_allocation,
                            is_host=True
                        )
                        
                        if not party_result:
                            logger.info("파티 설정 취소")
                            continue
                        
                        party_members, selected_passives = party_result
                        
                        if not party_members:
                            logger.info("파티 멤버 없음")
                            continue
                        
                        # 로컬 플레이어의 파티 설정
                        local_player.party = party_members
                        
                        # 난이도 선택
                        from src.core.difficulty import DifficultySystem, DifficultyLevel, set_difficulty_system
                        difficulty_system = DifficultySystem(config)
                        
                        from src.ui.difficulty_selection_ui import show_difficulty_selection
                        difficulty_result = show_difficulty_selection(display.console, display.context, difficulty_system)
                        
                        if not difficulty_result:
                            continue
                        
                        difficulty_system.set_difficulty(difficulty_result)
                        set_difficulty_system(difficulty_system)
                        
                        # 인벤토리 생성 (멀티플레이: 호스트 기준)
                        from src.equipment.inventory import Inventory
                        from src.character.upgrade_applier import UpgradeApplier
                        from src.persistence.meta_progress import get_meta_progress
                        host_meta = get_meta_progress()  # 호스트의 메타 진행
                        inventory_weight_bonus = UpgradeApplier.get_inventory_weight_bonus(meta_progress=host_meta, is_host=True)
                        base_weight = 5.0 + (inventory_weight_bonus / 2.5)  # 인벤토리 확장 보너스 적용
                        inventory = Inventory(base_weight=base_weight, party=party_members)
                        
                        # 게임 통계 초기화
                        game_stats = {
                            "enemies_defeated": 0,
                            "max_floor_reached": 1,
                            "total_gold_earned": 0,
                            "total_exp_earned": 0,
                            "save_slot": None
                        }
                        
                        # 던전 생성 (시드 기반)
                        from src.world.dungeon_generator import DungeonGenerator
                        from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                        
                        floor_number = 1
                        dungeon_seed = session.generate_dungeon_seed_for_floor(floor_number)
                        generator = DungeonGenerator()
                        dungeon = generator.generate(floor_number, seed=dungeon_seed)
                        
                        logger.info(f"던전 생성 완료: {floor_number}층 (시드: {dungeon_seed})")
                        
                        # 탐험 시스템 생성 (멀티플레이)
                        exploration = MultiplayerExplorationSystem(
                            dungeon=dungeon,
                            party=party_members,
                            floor_number=floor_number,
                            inventory=inventory,
                            game_stats=game_stats,
                            session=session,
                            network_manager=network_manager,
                            local_player_id=local_player_id
                        )
                        
                        # 네트워크 매니저에 현재 게임 상태 저장 (클라이언트 연결 시 전송용)
                        network_manager.current_floor = floor_number
                        network_manager.current_dungeon = dungeon
                        network_manager.current_exploration = exploration
                        
                        # 플레이어 초기 위치 설정
                        if dungeon.rooms:
                            first_room = dungeon.rooms[0]
                            import random
                            spawn_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                            spawn_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                            local_player.x = spawn_x
                            local_player.y = spawn_y
                            exploration.player.x = spawn_x
                            exploration.player.y = spawn_y
                        
                        # 탐험 루프 시작
                        from src.ui.world_ui import run_exploration
                        from src.ui.combat_ui import run_combat, CombatState
                        from src.combat.experience_system import RewardCalculator, distribute_party_experience
                        from src.ui.reward_ui import show_reward_screen
                        from src.world.enemy_generator import EnemyGenerator
                        
                        floors_dungeons = {}
                        floors_dungeons[floor_number] = {
                            "dungeon": dungeon,
                            "enemies": exploration.enemies,
                            "player_x": local_player.x,
                            "player_y": local_player.y
                        }
                        
                        play_dungeon_bgm = True
                        
                        # 멀티플레이 게임 루프
                        while True:
                            result, data = run_exploration(
                                display.console,
                                display.context,
                                exploration,
                                inventory,
                                party_members,
                                play_bgm_on_start=play_dungeon_bgm
                            )
                            
                            logger.info(f"탐험 결과: {result}")
                            
                            if result == "quit":
                                logger.info("게임 종료")
                                break
                            elif result == "combat":
                                # 전투 처리 (멀티플레이 지원)
                                logger.info("⚔ 전투 시작!")
                                
                                if data and isinstance(data, dict):
                                    num_enemies = data.get("num_enemies", 0)
                                    map_enemies = data.get("enemies", [])
                                    combat_party = data.get("participants", party_members)
                                    combat_position = data.get("position", (local_player.x, local_player.y))
                                else:
                                    num_enemies = 0
                                    map_enemies = []
                                    combat_party = party_members
                                    combat_position = (local_player.x, local_player.y)
                                
                                if num_enemies > 0:
                                    enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
                                else:
                                    enemies = EnemyGenerator.generate_enemies(floor_number)
                                
                                is_boss_fight = any(e.is_boss for e in map_enemies) if map_enemies else False
                                if is_boss_fight and map_enemies:
                                    boss_entity = next((e for e in map_enemies if e.is_boss), None)
                                    if boss_entity:
                                        boss = EnemyGenerator.generate_boss(floor_number)
                                        if enemies:
                                            enemies[0] = boss
                                        else:
                                            enemies.append(boss)
                                
                                # 멀티플레이 전투 실행
                                combat_result = run_combat(
                                    display.console,
                                    display.context,
                                    combat_party,
                                    enemies,
                                    inventory=inventory,
                                    session=session,
                                    network_manager=network_manager,
                                    combat_position=combat_position
                                )
                                
                                if combat_result == CombatState.VICTORY:
                                    # 보상 처리
                                    if map_enemies:
                                        exploration.game_stats["enemies_defeated"] += len(map_enemies)
                                        for enemy_entity in map_enemies:
                                            if enemy_entity in exploration.enemies:
                                                exploration.enemies.remove(enemy_entity)
                                    
                                    rewards = RewardCalculator.calculate_combat_rewards(
                                        enemies,
                                        floor_number,
                                        is_boss_fight=is_boss_fight
                                    )
                                    
                                    # 파티 강화 업그레이드 적용 (경험치/골드 부스트)
                                    from src.character.upgrade_applier import UpgradeApplier
                                    from src.multiplayer.game_mode import get_game_mode_manager
                                    game_mode_manager = get_game_mode_manager()
                                    is_host = not game_mode_manager.is_multiplayer() or game_mode_manager.is_host
                                    
                                    # 멀티플레이: 호스트의 메타 진행 사용
                                    # 싱글플레이: 플레이어의 메타 진행 사용
                                    host_meta = get_meta_progress() if is_host else None
                                    exp_multiplier = UpgradeApplier.get_experience_multiplier(meta_progress=host_meta, is_host=is_host)
                                    gold_multiplier = UpgradeApplier.get_gold_multiplier(meta_progress=host_meta, is_host=is_host)
                                    
                                    # 경험치/골드 보너스 적용
                                    if exp_multiplier > 1.0:
                                        old_exp = rewards["experience"]
                                        rewards["experience"] = int(rewards["experience"] * exp_multiplier)
                                        logger.debug(f"경험치 업그레이드 적용: {old_exp} -> {rewards['experience']} (+{int((exp_multiplier - 1.0) * 100)}%)")
                                    
                                    if gold_multiplier > 1.0:
                                        old_gold = rewards["gold"]
                                        rewards["gold"] = int(rewards["gold"] * gold_multiplier)
                                        logger.debug(f"골드 업그레이드 적용: {old_gold} -> {rewards['gold']} (+{int((gold_multiplier - 1.0) * 100)}%)")
                                    
                                    # 멀티플레이: 경험치 분배
                                    from src.multiplayer.config import MultiplayerConfig
                                    if MultiplayerConfig.exp_divide_by_participants:
                                        participating_count = len(combat_party)
                                        if participating_count > 0:
                                            rewards["experience"] = rewards["experience"] // participating_count
                                    
                                    level_up_info = distribute_party_experience(combat_party, rewards["experience"])
                                    
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
                                    
                                    from src.audio import play_bgm
                                    floor = exploration.floor_number
                                    biome_index = (floor - 1) // 5
                                    biome_index = biome_index % 10
                                    biome_track = f"biome_{biome_index}"
                                    play_bgm(biome_track, loop=True, fade_in=True)
                                    play_dungeon_bgm = False
                                elif combat_result == CombatState.DEFEAT:
                                    logger.info("❌ 패배... 게임 오버")
                                    from src.ui.game_result_ui import show_game_result
                                    # 멀티플레이어 여부 확인 (클라이언트 모드)
                                    is_multiplayer = True  # 클라이언트 모드이므로 멀티플레이
                                    show_game_result(
                                        display.console,
                                        display.context,
                                        is_victory=False,
                                        max_floor=exploration.game_stats["max_floor_reached"],
                                        enemies_defeated=exploration.game_stats["enemies_defeated"],
                                        total_gold=exploration.game_stats["total_gold_earned"],
                                        total_exp=exploration.game_stats["total_exp_earned"],
                                        save_slot=None,
                                        is_multiplayer=is_multiplayer
                                    )
                                    break
                            elif result == "floor_up" or result == "floor_down":
                                # 층 이동 처리 (멀티플레이)
                                if result == "floor_up":
                                    floor_number += 1
                                else:
                                    floor_number = max(1, floor_number - 1)
                                
                                if floor_number not in floors_dungeons:
                                    # 던전 생성
                                    dungeon_seed = session.generate_dungeon_seed_for_floor(floor_number)
                                    from src.world.dungeon_generator import DungeonGenerator
                                    floor_generator = DungeonGenerator(width=80, height=50)
                                    new_dungeon = floor_generator.generate(floor_number, seed=dungeon_seed)
                                    
                                    # 탐험 시스템 임시 생성 (적 스폰용)
                                    from src.world.exploration import ExplorationSystem
                                    temp_exploration = ExplorationSystem(
                                        new_dungeon,
                                        party_members,
                                        floor_number,
                                        inventory,
                                        exploration.game_stats
                                    )
                                    # 탐험 시스템이 자동으로 _spawn_enemies() 호출
                                    new_enemies = temp_exploration.enemies
                                    
                                    # 시작 위치 결정
                                    if new_dungeon.stairs_down:
                                        player_x = new_dungeon.stairs_down[0]
                                        player_y = new_dungeon.stairs_down[1]
                                    elif new_dungeon.rooms:
                                        first_room = new_dungeon.rooms[0]
                                        import random
                                        player_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                                        player_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                                    else:
                                        player_x = 5
                                        player_y = 5
                                    
                                    floors_dungeons[floor_number] = {
                                        "dungeon": new_dungeon,
                                        "enemies": new_enemies,
                                        "player_x": player_x,
                                        "player_y": player_y
                                    }
                                
                                floor_data = floors_dungeons[floor_number]
                                exploration.dungeon = floor_data["dungeon"]
                                exploration.floor_number = floor_number
                                exploration.enemies = floor_data["enemies"]
                                local_player.x = floor_data["player_x"]
                                local_player.y = floor_data["player_y"]
                                exploration.player.x = local_player.x
                                exploration.player.y = local_player.y
                                exploration.game_stats["max_floor_reached"] = max(
                                    exploration.game_stats["max_floor_reached"],
                                    floor_number
                                )
                                
                                # 네트워크 매니저에 현재 층 정보 업데이트 (새로 연결된 클라이언트에게 전송용)
                                if network_manager:
                                    network_manager.current_floor = floor_number
                                    network_manager.current_dungeon = floor_data["dungeon"]
                                    network_manager.current_exploration = exploration
                                
                                play_dungeon_bgm = True
                        
                        logger.info("멀티플레이 세션 종료")
                        
                        # 서버 종료
                        if network_manager and server_loop:
                            try:
                                logger.info("호스트 서버 종료 중...")
                                # 서버 루프가 실행 중이면 서버 중지
                                if not server_loop.is_closed():
                                    # 비동기 서버 중지 함수 실행
                                    async def stop_server_async():
                                        try:
                                            await network_manager.stop_server()
                                        except Exception as e:
                                            logger.error(f"서버 중지 중 오류: {e}", exc_info=True)
                                    
                                    # 서버 종료 태스크 추가
                                    if server_loop.is_running():
                                        server_loop.call_soon_threadsafe(
                                            lambda: asyncio.run_coroutine_threadsafe(
                                                stop_server_async(),
                                                server_loop
                                            )
                                        )
                                        # 서버 종료 대기
                                        import time
                                        time.sleep(0.5)
                                logger.info("호스트 서버 종료 완료")
                            except Exception as e:
                                logger.error(f"서버 종료 중 오류: {e}", exc_info=True)
                        
                    elif mode == "client":
                        # 클라이언트 게임 참가
                        logger.info("클라이언트 모드: 게임 참가")
                        
                        host_address = multiplayer_result.get("host_address", "localhost")
                        port = multiplayer_result.get("port", 5000)
                        
                        logger.info(f"호스트에 연결 시도: {host_address}:{port}")
                        
                        # 멀티플레이 모드 설정
                        from src.multiplayer.game_mode import get_game_mode_manager, MultiplayerMode
                        game_mode_manager = get_game_mode_manager()
                        game_mode_manager.set_multiplayer(
                            player_count=4,  # 최대 4인
                            is_host=False,
                            session_id=None
                        )
                        
                        # 클라이언트 네트워크 매니저 생성
                        from src.multiplayer.network import ClientNetworkManager
                        from uuid import uuid4
                        import asyncio
                        
                        local_player_id = str(uuid4())[:8]
                        network_manager = ClientNetworkManager(host_address, port)
                        network_manager.player_id = local_player_id
                        game_mode_manager.local_player_id = local_player_id
                        game_mode_manager.is_host = False
                        
                        # 플레이어 이름 입력 (간단하게 "클라이언트"로 설정, 향후 UI 추가 가능)
                        player_name = f"플레이어{local_player_id[:4]}"
                        
                        # 세션 정보 수신을 위한 변수들 (메시지 핸들러 등록 전에 준비)
                        from src.multiplayer.session import MultiplayerSession
                        from src.multiplayer.player import MultiplayerPlayer
                        from src.multiplayer.protocol import MessageType
                        import time
                        
                        session_data = {
                            "session_id": None,
                            "session_seed": None,
                            "dungeon_data": None,
                            "floor_number": None,
                            "dungeon_seed": None,
                            "players": []
                        }
                        
                        # 세션 정보 수신 핸들러 등록 (연결 전에 등록)
                        def handle_session_seed(msg, sender_id):
                            session_data["session_seed"] = msg.data.get("seed")
                            session_data["session_id"] = msg.data.get("session_id")
                            logger.info(f"세션 시드 수신: {session_data['session_seed']}")
                        
                        def handle_dungeon_data(msg, sender_id):
                            session_data["dungeon_data"] = msg.data.get("dungeon")
                            session_data["floor_number"] = msg.data.get("floor_number")
                            session_data["dungeon_seed"] = msg.data.get("seed")
                            logger.info(f"던전 데이터 수신: {session_data['floor_number']}층")
                        
                        def handle_player_list(msg, sender_id):
                            session_data["players"] = msg.data.get("players", [])
                            logger.info(f"플레이어 목록 수신: {len(session_data['players'])}명")
                        
                        network_manager.register_handler(MessageType.SESSION_SEED, handle_session_seed)
                        network_manager.register_handler(MessageType.DUNGEON_DATA, handle_dungeon_data)
                        network_manager.register_handler(MessageType.PLAYER_JOINED, handle_player_list)
                        
                        # 비동기 연결 시도
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(network_manager.connect(local_player_id, player_name))
                            logger.info("호스트 연결 성공!")
                        except Exception as e:
                            logger.error(f"호스트 연결 실패: {e}", exc_info=True)
                            # 연결 실패 메시지 표시
                            from src.ui.npc_dialog_ui import show_npc_dialog
                            show_npc_dialog(
                                display.console,
                                display.context,
                                "연결 실패",
                                f"호스트({host_address}:{port})에 연결할 수 없습니다.\n\n"
                                f"오류: {str(e)}\n\n"
                                f"호스트가 게임을 시작했는지 확인해주세요."
                            )
                            loop.close()
                            continue
                        
                        # 세션 정보 대기 (호스트로부터 세션 정보 수신)
                        logger.info("세션 정보 대기 중...")
                        
                        # 세션 정보 수신 대기 (최대 10초)
                        # 메시지 수신 루프는 이미 백그라운드에서 실행 중
                        timeout = 10.0
                        start_time = time.time()
                        while time.time() - start_time < timeout:
                            # 세션 시드와 던전 데이터가 모두 수신되었는지 확인
                            if session_data["session_seed"] is not None and session_data["dungeon_data"] is not None:
                                break
                            # 메시지 처리를 위해 짧게 대기 (비동기 루프는 이미 실행 중)
                            try:
                                # 이미 실행 중인 루프인 경우, 단순히 시간 대기
                                loop.call_soon_threadsafe(lambda: None)
                            except:
                                pass
                            import time as time_module
                            time_module.sleep(0.1)
                        
                        # 세션 정보 확인
                        if session_data["session_seed"] is None:
                            logger.error("세션 시드를 받지 못했습니다")
                            raise Exception("세션 시드 수신 실패")
                        
                        if session_data["dungeon_data"] is None:
                            logger.warning("던전 데이터를 받지 못했습니다. 게임 시작 전 클라이언트 연결일 수 있습니다.")
                            # 게임이 시작되지 않은 경우, 기본 세션만 생성
                            session = MultiplayerSession(max_players=4, host_id=None)
                            session.session_seed = session_data["session_seed"]
                            if session_data["session_id"]:
                                session.session_id = session_data["session_id"]
                            session.local_player_id = local_player_id
                            
                            local_player = MultiplayerPlayer(
                                player_id=local_player_id,
                                player_name=player_name,
                                x=0,
                                y=0,
                                party=[],
                                is_host=False
                            )
                            session.add_player(local_player)
                            
                            # 기존 플레이어 추가
                            for player_data in session_data["players"]:
                                if player_data["player_id"] != local_player_id:
                                    existing_player = MultiplayerPlayer(
                                        player_id=player_data["player_id"],
                                        player_name=player_data["player_name"],
                                        x=player_data.get("x", 0),
                                        y=player_data.get("y", 0),
                                        party=[],
                                        is_host=player_data.get("is_host", False)
                                    )
                                    session.add_player(existing_player)
                            
                            logger.info("클라이언트 세션 준비 완료 (게임 시작 전)")
                            logger.warning("게임이 시작되면 던전 데이터를 수신할 수 있습니다")
                            # 여기서 게임을 시작할 수 없으므로, 임시 세션만 생성
                            continue
                        
                        # 세션 생성 (호스트로부터 받은 정보로 초기화)
                        session = MultiplayerSession(max_players=4, host_id=None)
                        session.session_seed = session_data["session_seed"]
                        if session_data["session_id"]:
                            session.session_id = session_data["session_id"]
                        session.local_player_id = local_player_id
                        
                        # 로컬 플레이어 추가
                        local_player = MultiplayerPlayer(
                            player_id=local_player_id,
                            player_name=player_name,
                            x=0,
                            y=0,
                            party=[],
                            is_host=False
                        )
                        session.add_player(local_player)
                        
                        # 기존 플레이어 추가
                        for player_data in session_data["players"]:
                            if player_data["player_id"] != local_player_id:
                                existing_player = MultiplayerPlayer(
                                    player_id=player_data["player_id"],
                                    player_name=player_data["player_name"],
                                    x=player_data.get("x", 0),
                                    y=player_data.get("y", 0),
                                    party=[],
                                    is_host=player_data.get("is_host", False)
                                )
                                session.add_player(existing_player)
                        
                        logger.info("클라이언트 세션 준비 완료")
                        
                        # 파티 설정 (멀티플레이용 - 클라이언트도 필요)
                        from src.ui.party_setup import run_party_setup
                        party_result = run_party_setup(display.console, display.context)
                        
                        if not party_result:
                            logger.info("파티 설정 취소")
                            try:
                                loop.run_until_complete(network_manager.disconnect())
                            except Exception:
                                pass
                            loop.close()
                            continue
                        
                        party_members, selected_passives = party_result
                        
                        if not party_members:
                            logger.info("파티 멤버 없음")
                            try:
                                loop.run_until_complete(network_manager.disconnect())
                            except Exception:
                                pass
                            loop.close()
                            continue
                        
                        # 로컬 플레이어의 파티 설정
                        local_player.party = party_members
                        
                        # 인벤토리 생성 (호스트와 동기화 예정)
                        from src.equipment.inventory import Inventory
                        inventory = Inventory(party=party_members)
                        
                        # 게임 통계 초기화
                        game_stats = {
                            "enemies_defeated": 0,
                            "max_floor_reached": 1,
                            "total_gold_earned": 0,
                            "total_exp_earned": 0,
                            "save_slot": None
                        }
                        
                        # 던전 데이터로 던전 복원
                        from src.persistence.save_system import deserialize_dungeon
                        from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                        
                        floor_number = session_data["floor_number"] or 1
                        dungeon, enemies_list = deserialize_dungeon(session_data["dungeon_data"])
                        
                        logger.info(f"던전 복원 완료: {floor_number}층 (시드: {session_data['dungeon_seed']})")
                        
                        # 탐험 시스템 생성 (멀티플레이 클라이언트)
                        exploration = MultiplayerExplorationSystem(
                            dungeon=dungeon,
                            party=party_members,
                            floor_number=floor_number,
                            inventory=inventory,
                            game_stats=game_stats,
                            session=session,
                            network_manager=network_manager,
                            local_player_id=local_player_id
                        )
                        
                        # 수신된 적 목록으로 던전 적 설정
                        if enemies_list:
                            exploration.enemies = enemies_list
                        
                        # 플레이어 초기 위치 설정
                        # 기존 플레이어가 있으면 그 위치를 참고, 없으면 첫 방에서 스폰
                        if session_data["players"]:
                            # 다른 플레이어 위치를 참고하여 안전한 위치에 스폰
                            existing_positions = [(p.get("x", 0), p.get("y", 0)) for p in session_data["players"] if p.get("player_id") != local_player_id]
                            if existing_positions and dungeon.rooms:
                                # 다른 플레이어들이 있는 방 근처에 스폰
                                import random
                                room = random.choice(dungeon.rooms)
                                spawn_x = room.x + random.randint(2, max(2, room.width - 3))
                                spawn_y = room.y + random.randint(2, max(2, room.height - 3))
                            elif dungeon.rooms:
                                first_room = dungeon.rooms[0]
                                import random
                                spawn_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                                spawn_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                            else:
                                spawn_x = 5
                                spawn_y = 5
                        elif dungeon.rooms:
                            first_room = dungeon.rooms[0]
                            import random
                            spawn_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                            spawn_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                        else:
                            spawn_x = 5
                            spawn_y = 5
                        
                        local_player.x = spawn_x
                        local_player.y = spawn_y
                        exploration.player.x = spawn_x
                        exploration.player.y = spawn_y
                        
                        logger.info(f"클라이언트 플레이어 초기 위치: ({spawn_x}, {spawn_y})")
                        
                        # 기존 플레이어들의 위치 동기화
                        for player_data in session_data["players"]:
                            if player_data["player_id"] != local_player_id:
                                player = session.get_player(player_data["player_id"])
                                if player:
                                    player.x = player_data.get("x", 0)
                                    player.y = player_data.get("y", 0)
                        
                        # 탐험 루프 시작
                        from src.ui.world_ui import run_exploration
                        from src.ui.combat_ui import run_combat, CombatState
                        from src.combat.experience_system import RewardCalculator, distribute_party_experience
                        from src.ui.reward_ui import show_reward_screen
                        from src.world.enemy_generator import EnemyGenerator
                        
                        floors_dungeons = {}
                        floors_dungeons[floor_number] = {
                            "dungeon": dungeon,
                            "enemies": exploration.enemies,
                            "player_x": local_player.x,
                            "player_y": local_player.y
                        }
                        
                        play_dungeon_bgm = True
                        
                        try:
                            # 클라이언트 게임 루프 (호스트와 동일)
                            while True:
                                result, data = run_exploration(
                                    display.console,
                                    display.context,
                                    exploration,
                                    inventory,
                                    party_members,
                                    play_bgm_on_start=play_dungeon_bgm
                                )
                                
                                logger.info(f"탐험 결과: {result}")
                                
                                if result == "quit":
                                    logger.info("게임 종료")
                                    break
                                elif result == "combat":
                                    # 전투 처리 (멀티플레이 지원)
                                    logger.info("⚔ 전투 시작!")
                                    
                                    if data and isinstance(data, dict):
                                        num_enemies = data.get("num_enemies", 0)
                                        map_enemies = data.get("enemies", [])
                                        combat_party = data.get("participants", party_members)
                                        combat_position = data.get("position", (local_player.x, local_player.y))
                                    else:
                                        num_enemies = 0
                                        map_enemies = []
                                        combat_party = party_members
                                        combat_position = (local_player.x, local_player.y)
                                    
                                    if num_enemies > 0:
                                        enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
                                    else:
                                        enemies = EnemyGenerator.generate_enemies(floor_number)
                                    
                                    is_boss_fight = any(e.is_boss for e in map_enemies) if map_enemies else False
                                    if is_boss_fight and map_enemies:
                                        boss_entity = next((e for e in map_enemies if e.is_boss), None)
                                        if boss_entity:
                                            boss = EnemyGenerator.generate_boss(floor_number)
                                            if enemies:
                                                enemies[0] = boss
                                            else:
                                                enemies.append(boss)
                                    
                                    # 멀티플레이 전투 실행
                                    combat_result = run_combat(
                                        display.console,
                                        display.context,
                                        combat_party,
                                        enemies,
                                        inventory=inventory,
                                        session=session,
                                        network_manager=network_manager,
                                        combat_position=combat_position
                                    )
                                    
                                    if combat_result == CombatState.VICTORY:
                                        # 보상 처리
                                        if map_enemies:
                                            exploration.game_stats["enemies_defeated"] += len(map_enemies)
                                            for enemy_entity in map_enemies:
                                                if enemy_entity in exploration.enemies:
                                                    exploration.enemies.remove(enemy_entity)
                                        
                                        rewards = RewardCalculator.calculate_combat_rewards(
                                            enemies,
                                            floor_number,
                                            is_boss_fight=is_boss_fight
                                        )
                                        
                                        # 파티 강화 업그레이드 적용 (경험치/골드 부스트)
                                        from src.character.upgrade_applier import UpgradeApplier
                                        from src.multiplayer.game_mode import get_game_mode_manager
                                        from src.persistence.meta_progress import get_meta_progress
                                        game_mode_manager = get_game_mode_manager()
                                        is_host = not game_mode_manager.is_multiplayer() or game_mode_manager.is_host
                                        
                                        # 멀티플레이: 호스트의 메타 진행 사용
                                        # 싱글플레이: 플레이어의 메타 진행 사용
                                        host_meta = get_meta_progress() if is_host else None
                                        exp_multiplier = UpgradeApplier.get_experience_multiplier(meta_progress=host_meta, is_host=is_host)
                                        gold_multiplier = UpgradeApplier.get_gold_multiplier(meta_progress=host_meta, is_host=is_host)
                                        
                                        # 경험치/골드 보너스 적용
                                        if exp_multiplier > 1.0:
                                            old_exp = rewards["experience"]
                                            rewards["experience"] = int(rewards["experience"] * exp_multiplier)
                                            logger.debug(f"경험치 업그레이드 적용: {old_exp} -> {rewards['experience']} (+{int((exp_multiplier - 1.0) * 100)}%)")
                                        
                                        if gold_multiplier > 1.0:
                                            old_gold = rewards["gold"]
                                            rewards["gold"] = int(rewards["gold"] * gold_multiplier)
                                            logger.debug(f"골드 업그레이드 적용: {old_gold} -> {rewards['gold']} (+{int((gold_multiplier - 1.0) * 100)}%)")
                                        
                                        # 멀티플레이: 경험치 분배
                                        from src.multiplayer.config import MultiplayerConfig
                                        if MultiplayerConfig.exp_divide_by_participants:
                                            participating_count = len(combat_party)
                                            if participating_count > 0:
                                                rewards["experience"] = rewards["experience"] // participating_count
                                        
                                        level_up_info = distribute_party_experience(combat_party, rewards["experience"])
                                        
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
                                        
                                        from src.audio import play_bgm
                                        floor = exploration.floor_number
                                        biome_index = (floor - 1) // 5
                                        biome_index = biome_index % 10
                                        biome_track = f"biome_{biome_index}"
                                        play_bgm(biome_track, loop=True, fade_in=True)
                                        play_dungeon_bgm = False
                                    elif combat_result == CombatState.DEFEAT:
                                        logger.info("❌ 패배... 게임 오버")
                                        from src.ui.game_result_ui import show_game_result
                                        # 멀티플레이어 여부 확인
                                        is_multiplayer = hasattr(exploration, 'session') or (hasattr(exploration, 'is_multiplayer') and exploration.is_multiplayer)
                                        show_game_result(
                                            display.console,
                                            display.context,
                                            is_victory=False,
                                            max_floor=exploration.game_stats["max_floor_reached"],
                                            enemies_defeated=exploration.game_stats["enemies_defeated"],
                                            total_gold=exploration.game_stats["total_gold_earned"],
                                            total_exp=exploration.game_stats["total_exp_earned"],
                                            save_slot=None,
                                            is_multiplayer=is_multiplayer
                                        )
                                        break
                                elif result == "floor_up" or result == "floor_down":
                                    # 층 이동 처리 (멀티플레이)
                                    if result == "floor_up":
                                        floor_number += 1
                                    else:
                                        floor_number = max(1, floor_number - 1)
                                    
                                    if floor_number not in floors_dungeons:
                                        # 던전 생성 (실제로는 호스트로부터 받아야 함)
                                        dungeon_seed = session.generate_dungeon_seed_for_floor(floor_number)
                                        from src.world.dungeon_generator import DungeonGenerator
                                        floor_generator = DungeonGenerator(width=80, height=50)
                                        new_dungeon = floor_generator.generate(floor_number, seed=dungeon_seed)
                                        
                                        from src.world.exploration import ExplorationSystem
                                        temp_exploration = ExplorationSystem(
                                            new_dungeon,
                                            party_members,
                                            floor_number,
                                            inventory,
                                            exploration.game_stats
                                        )
                                        new_enemies = temp_exploration.enemies
                                        
                                        if new_dungeon.stairs_down:
                                            player_x = new_dungeon.stairs_down[0]
                                            player_y = new_dungeon.stairs_down[1]
                                        elif new_dungeon.rooms:
                                            first_room = new_dungeon.rooms[0]
                                            import random
                                            player_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                                            player_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                                        else:
                                            player_x = 5
                                            player_y = 5
                                        
                                        floors_dungeons[floor_number] = {
                                            "dungeon": new_dungeon,
                                            "enemies": new_enemies,
                                            "player_x": player_x,
                                            "player_y": player_y
                                        }
                                    
                                    floor_data = floors_dungeons[floor_number]
                                    exploration.dungeon = floor_data["dungeon"]
                                    exploration.floor_number = floor_number
                                    exploration.enemies = floor_data["enemies"]
                                    local_player.x = floor_data["player_x"]
                                    local_player.y = floor_data["player_y"]
                                    if hasattr(exploration, 'player'):
                                        exploration.player.x = local_player.x
                                        exploration.player.y = local_player.y
                                    exploration.game_stats["max_floor_reached"] = max(
                                        exploration.game_stats["max_floor_reached"],
                                        floor_number
                                    )
                                    play_dungeon_bgm = True
                                    continue
                        finally:
                            # 연결 종료
                            try:
                                loop.run_until_complete(network_manager.disconnect())
                            except Exception as e:
                                logger.error(f"연결 종료 중 오류: {e}", exc_info=True)
                            finally:
                                loop.close()
                        
                        logger.info("클라이언트 세션 종료")
                        
                    continue
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

                    # 난이도 시스템 복원
                    from src.core.difficulty import DifficultySystem, DifficultyLevel, set_difficulty_system

                    difficulty_system = DifficultySystem(config)
                    difficulty_str = loaded_state.get("difficulty", "보통")

                    # 문자열을 DifficultyLevel로 변환
                    for level in DifficultyLevel:
                        if level.value == difficulty_str:
                            difficulty_system.set_difficulty(level)
                            break

                    set_difficulty_system(difficulty_system)
                    logger.info(f"난이도 시스템 복원: {difficulty_str}")

                    # 파티 복원
                    try:
                        party = [deserialize_party_member(member_data) for member_data in loaded_state.get("party", [])]
                        logger.info(f"파티 복원 완료: {len(party)}명")
                    except Exception as e:
                        logger.error(f"파티 복원 실패: {e}", exc_info=True)
                        logger.error(f"파티 데이터: {loaded_state.get('party', [])}")
                        raise

                    # 던전 복원 (적 포함)
                    dungeon, enemies = deserialize_dungeon(loaded_state["dungeon"])
                    floor_number = loaded_state.get("floor_number", 1)

                    # 디버그: 채집 오브젝트 복원 확인
                    harvestables_count = len(dungeon.harvestables) if hasattr(dungeon, 'harvestables') else 0
                    logger.warning(f"[LOAD] 던전 복원 후 채집 오브젝트: {harvestables_count}개")
                    if hasattr(dungeon, 'harvestables') and dungeon.harvestables:
                        for i, h in enumerate(dungeon.harvestables[:3]):
                            logger.warning(f"[LOAD]   {i+1}. {h.object_type.value} at ({h.x}, {h.y}), harvested={h.harvested}")

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

                    # 적 복원
                    exploration.enemies = enemies
                    
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

                    # 층별 던전 상태 저장 딕셔너리 (층 이동 시 재사용)
                    floors_dungeons = {}
                    # 현재 층 던전 저장
                    floors_dungeons[floor_number] = {
                        "dungeon": dungeon,
                        "enemies": enemies,
                        "player_x": player_pos["x"],
                        "player_y": player_pos["y"]
                    }
                    
                    # 저장된 모든 층의 던전 상태 복원 (있는 경우)
                    if "floors" in loaded_state:
                        for floor_num, floor_data in loaded_state["floors"].items():
                            if floor_num != floor_number:  # 현재 층은 이미 복원됨
                                floor_dungeon, floor_enemies = deserialize_dungeon(floor_data)
                                floors_dungeons[int(floor_num)] = {
                                    "dungeon": floor_dungeon,
                                    "enemies": floor_enemies,
                                    "player_x": floor_data.get("player_position", {}).get("x", 0),
                                    "player_y": floor_data.get("player_position", {}).get("y", 0)
                                }

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

                            # 맵 엔티티에서 보스 정보 확인
                            is_boss_fight = any(e.is_boss for e in map_enemies) if map_enemies else False
                            
                            if num_enemies > 0:
                                enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
                                logger.info(f"적 {len(enemies)}명 생성: {[e.name for e in enemies]}")
                            else:
                                enemies = EnemyGenerator.generate_enemies(floor_number)
                                logger.info(f"적 {len(enemies)}명 생성(기본값)")
                            
                            # 보스가 포함된 경우 보스 추가/교체
                            if is_boss_fight and map_enemies:
                                # 보스 엔티티 찾기
                                boss_entity = next((e for e in map_enemies if e.is_boss), None)
                                if boss_entity:
                                    from src.world.enemy_generator import EnemyGenerator
                                    boss = EnemyGenerator.generate_boss(floor_number)
                                    # 보스를 적 리스트의 첫 번째에 추가 (또는 교체)
                                    if enemies:
                                        enemies[0] = boss
                                    else:
                                        enemies.append(boss)
                                    logger.info(f"보스 추가: {boss.name} (enemy_id: {boss.enemy_id})")

                            # 멀티플레이 모드 확인
                            game_mode_manager = get_game_mode_manager()
                            is_multiplayer = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False
                            
                            # 멀티플레이: 전투 데이터에서 참여자 및 위치 정보 가져오기
                            session_for_combat = None
                            network_manager_for_combat = None
                            combat_position = None
                            
                            if is_multiplayer and data and isinstance(data, dict):
                                if "participants" in data:
                                    party = data["participants"]  # 참여자로 교체
                                if "position" in data:
                                    combat_position = data["position"]
                                # 세션 및 네트워크 매니저 가져오기 (TODO: 실제 세션에서 가져오기)
                                # 현재는 싱글플레이 모드로 처리
                                pass
                            
                            combat_result = run_combat(
                                display.console,
                                display.context,
                                party,
                                enemies,
                                inventory=inventory,
                                session=session_for_combat,
                                network_manager=network_manager_for_combat,
                                combat_position=combat_position
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
                                    is_boss_fight=is_boss_fight
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

                                # 전투 후 던전 BGM 재생 (바이옴별 BGM)
                                from src.audio import play_bgm
                                floor = exploration.floor_number
                                # 바이옴 계산 (5층마다 변경: 1-5층=바이옴0, 6-10층=바이옴1, ...)
                                biome_index = (floor - 1) // 5
                                biome_index = biome_index % 10  # 10개 바이옴 순환
                                biome_track = f"biome_{biome_index}"
                                play_bgm(biome_track, loop=True, fade_in=True)
                                logger.info(f"던전 BGM 재생 (층수: {floor}, 바이옴: {biome_index}, BGM: {biome_track})")
                                play_dungeon_bgm = False
                                continue
                            elif combat_result == CombatState.DEFEAT:
                                logger.info("❌ 패배... 게임 오버")

                                # 게임 정산 (패배)
                                from src.ui.game_result_ui import show_game_result
                                # 불러온 게임 상태에서 멀티플레이어 여부 확인
                                is_multiplayer = loaded_state.get("is_multiplayer", False) if loaded_state else False
                                save_slot_info = exploration.game_stats.get("save_slot", None)
                                if save_slot_info is None:
                                    save_slot_info = {"is_multiplayer": is_multiplayer}
                                elif isinstance(save_slot_info, dict):
                                    save_slot_info["is_multiplayer"] = is_multiplayer
                                show_game_result(
                                    display.console,
                                    display.context,
                                    is_victory=False,
                                    max_floor=exploration.game_stats["max_floor_reached"],
                                    enemies_defeated=exploration.game_stats["enemies_defeated"],
                                    total_gold=exploration.game_stats["total_gold_earned"],
                                    total_exp=exploration.game_stats["total_exp_earned"],
                                    save_slot=save_slot_info,
                                    is_multiplayer=is_multiplayer
                                )
                                break
                            else:
                                logger.info("🏃 도망쳤다")
                                # 도망 후 던전 BGM 재생 (바이옴별 BGM)
                                from src.audio import play_bgm
                                floor = exploration.floor_number
                                # 바이옴 계산 (5층마다 변경: 1-5층=바이옴0, 6-10층=바이옴1, ...)
                                biome_index = (floor - 1) // 5
                                biome_index = biome_index % 10  # 10개 바이옴 순환
                                biome_track = f"biome_{biome_index}"
                                play_bgm(biome_track, loop=True, fade_in=True)
                                logger.info(f"던전 BGM 재생 (층수: {floor}, 바이옴: {biome_index}, BGM: {biome_track})")
                                play_dungeon_bgm = False
                                continue

                        elif result == "floor_down":
                            # 현재 층 상태 저장
                            floors_dungeons[floor_number] = {
                                "dungeon": exploration.dungeon,
                                "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                "player_x": exploration.player.x,
                                "player_y": exploration.player.y
                            }
                            
                            floor_number += 1
                            exploration.game_stats["max_floor_reached"] = max(exploration.game_stats["max_floor_reached"], floor_number)
                            logger.info(f"⬇ 다음 층: {floor_number}층 (최대: {exploration.game_stats['max_floor_reached']}층)")
                            
                            # 기존 던전이 있으면 재사용, 없으면 생성
                            if floor_number in floors_dungeons:
                                floor_data = floors_dungeons[floor_number]
                                dungeon = floor_data["dungeon"]
                                # dungeon이 튜플인 경우 언패킹 (하위 호환성)
                                if isinstance(dungeon, tuple):
                                    dungeon, saved_enemies = dungeon
                                else:
                                    saved_enemies = floor_data["enemies"]
                                saved_x = floor_data["player_x"]
                                saved_y = floor_data["player_y"]
                                logger.info(f"기존 {floor_number}층 던전 재사용 (적 {len(saved_enemies)}마리)")
                            else:
                                from src.world.dungeon_generator import DungeonGenerator
                                dungeon_gen = DungeonGenerator(width=80, height=50)
                                dungeon = dungeon_gen.generate(floor_number)
                                saved_enemies = []
                                saved_x = None
                                saved_y = None
                                logger.info(f"새 {floor_number}층 던전 생성")
                            
                            exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                            # 기존 던전이면 저장된 적 사용, 새 던전이면 _spawn_enemies()로 생성된 적 사용
                            if saved_enemies:
                                exploration.enemies = saved_enemies
                            # 새 던전인 경우 _spawn_enemies()가 이미 호출되어 적이 생성됨
                            if saved_x is not None and saved_y is not None:
                                exploration.player.x = saved_x
                                exploration.player.y = saved_y
                            # 층 변경 시 BGM 재생
                            play_dungeon_bgm = True
                            continue
                        elif result == "floor_up":
                            if floor_number > 1:
                                # 현재 층 상태 저장
                                floors_dungeons[floor_number] = {
                                    "dungeon": exploration.dungeon,
                                    "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                    "player_x": exploration.player.x,
                                    "player_y": exploration.player.y
                                }
                                
                                floor_number -= 1
                                logger.info(f"⬆ 이전 층: {floor_number}층")
                                
                                # 기존 던전이 있으면 재사용, 없으면 생성
                                if floor_number in floors_dungeons:
                                    floor_data = floors_dungeons[floor_number]
                                    dungeon = floor_data["dungeon"]
                                    # dungeon이 튜플인 경우 언패킹 (하위 호환성)
                                    if isinstance(dungeon, tuple):
                                        dungeon, saved_enemies = dungeon
                                    else:
                                        saved_enemies = floor_data["enemies"]
                                    saved_x = floor_data["player_x"]
                                    saved_y = floor_data["player_y"]
                                    logger.info(f"기존 {floor_number}층 던전 재사용 (적 {len(saved_enemies)}마리)")
                                else:
                                    from src.world.dungeon_generator import DungeonGenerator
                                    dungeon_gen = DungeonGenerator(width=80, height=50)
                                    dungeon = dungeon_gen.generate(floor_number)
                                    saved_enemies = []
                                    saved_x = None
                                    saved_y = None
                                    logger.info(f"새 {floor_number}층 던전 생성")
                                
                                exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                # 기존 던전이면 저장된 적 사용, 새 던전이면 _spawn_enemies()로 생성된 적 사용
                                if saved_enemies:
                                    exploration.enemies = saved_enemies
                                # 새 던전인 경우 _spawn_enemies()가 이미 호출되어 적이 생성됨
                                if saved_x is not None and saved_y is not None:
                                    exploration.player.x = saved_x
                                    exploration.player.y = saved_y
                                # 층 변경 시 BGM 재생
                                play_dungeon_bgm = True
                                continue
                            else:
                                logger.info("🎉 던전 탈출 성공!")

                                # 게임 정산 (승리)
                                from src.ui.game_result_ui import show_game_result
                                # 불러온 게임 상태에서 멀티플레이어 여부 확인
                                is_multiplayer = loaded_state.get("is_multiplayer", False) if loaded_state else False
                                save_slot_info = exploration.game_stats.get("save_slot", None)
                                if save_slot_info is None:
                                    save_slot_info = {"is_multiplayer": is_multiplayer}
                                elif isinstance(save_slot_info, dict):
                                    save_slot_info["is_multiplayer"] = is_multiplayer
                                show_game_result(
                                    display.console,
                                    display.context,
                                    is_victory=True,
                                    max_floor=exploration.game_stats["max_floor_reached"],
                                    enemies_defeated=exploration.game_stats["enemies_defeated"],
                                    total_gold=exploration.game_stats["total_gold_earned"],
                                    total_exp=exploration.game_stats["total_exp_earned"],
                                    save_slot=save_slot_info,
                                    is_multiplayer=is_multiplayer
                                )
                                break
                else:
                    logger.info("게임 불러오기 취소")
                    continue

            elif menu_result == MenuResult.NEW_GAME:
                logger.info("새 게임 시작 - 파티 구성")

                # 파티 구성
                from src.ui.party_setup import run_party_setup
                result = run_party_setup(display.console, display.context)
                
                if result is None:
                    continue
                
                party_members, selected_passives = result

                if party_members:
                    logger.info(f"파티 구성 완료: {len(party_members)}명")
                    for i, member in enumerate(party_members):
                        logger.info(
                            f"  {i+1}. {member.character_name} ({member.job_name})"
                        )

                    # 난이도 선택 (파티 구성 완료 후)
                    from src.core.difficulty import DifficultySystem, set_difficulty_system
                    from src.ui.difficulty_selection_ui import show_difficulty_selection

                    difficulty_system = DifficultySystem(config)
                    selected_difficulty = show_difficulty_selection(
                        display.console,
                        display.context,
                        difficulty_system
                    )

                    if selected_difficulty:
                        difficulty_system.set_difficulty(selected_difficulty)
                        set_difficulty_system(difficulty_system)
                        logger.info(f"난이도 선택: {selected_difficulty.value}")
                    else:
                        logger.info("난이도 선택 취소 - 메인 메뉴로")
                        continue

                    # PartyMember를 Character 객체로 변환 (특성/패시브 정보 포함)
                    from src.character.character import Character
                    character_party = []
                    for member in party_members:
                        char = Character(
                            name=member.character_name,
                            character_class=member.job_id,
                            level=1
                        )
                        # 경험치 초기화
                        char.experience = 0
                        
                        # 파티 구성에서 선택된 특성 적용
                        if member.selected_traits:
                            for trait_id in member.selected_traits:
                                if char.activate_trait(trait_id):
                                    logger.debug(f"{member.character_name}에 특성 추가: {trait_id}")
                        
                        character_party.append(char)
                    
                    # 선택된 패시브를 모든 캐릭터에 적용 (파티 전체 공통)
                    if selected_passives:
                        for passive_id in selected_passives:
                            for char in character_party:
                                if char.activate_trait(passive_id):
                                    logger.debug(f"{char.name}에 패시브 추가: {passive_id}")
                        logger.info(f"패시브 적용 완료: {', '.join(selected_passives)}")
                    
                    # 선택된 특성/패시브 로그
                    logger.info("선택된 특성/패시브:")
                    for i, member in enumerate(party_members):
                        char = character_party[i]
                        traits_str = ", ".join(member.selected_traits) if member.selected_traits else "없음"
                        logger.info(f"  {member.character_name} ({member.job_name}): 특성={traits_str}")
                    logger.info(f"  파티 전체 패시브: {', '.join(selected_passives) if selected_passives else '없음'}")

                    # 이제 character_party를 사용
                    party = character_party
                    logger.info("파티 멤버를 Character 객체로 변환 완료")
                    
                    # 파티 강화 업그레이드 적용 (HP/MP 증가)
                    from src.character.upgrade_applier import UpgradeApplier
                    from src.multiplayer.game_mode import get_game_mode_manager
                    game_mode_manager = get_game_mode_manager()
                    is_host = not game_mode_manager.is_multiplayer() or game_mode_manager.is_host
                    
                    # 멀티플레이: 호스트의 메타 진행 사용
                    # 싱글플레이: 플레이어의 메타 진행 사용
                    host_meta = get_meta_progress() if is_host else None
                    UpgradeApplier.apply_to_characters(character_party, meta_progress=host_meta, is_host=is_host)
                    logger.info("파티 강화 업그레이드 적용 완료")

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

                    # 인벤토리 생성 (무게 기반 - 파티 스탯에 연동, 1/10로 조정됨)
                    # 파티 강화 업그레이드 적용 (인벤토리 확장)
                    from src.character.upgrade_applier import UpgradeApplier
                    inventory_weight_bonus = UpgradeApplier.get_inventory_weight_bonus(meta_progress=host_meta, is_host=is_host)
                    base_weight = 5.0 + (inventory_weight_bonus / 2.5)  # 인벤토리 확장 보너스 적용
                    inventory = Inventory(base_weight=base_weight, party=party)
                    inventory.add_gold(200)  # 시작 골드
                    logger.info(f"인벤토리 생성 완료: {inventory.max_weight}kg 가능 (업그레이드 보너스: +{inventory_weight_bonus}kg)")

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

                    # 층별 던전 상태 저장 딕셔너리 (층 이동 시 재사용)
                    floors_dungeons = {}
                    floors_dungeons[floor_number] = {
                        "dungeon": dungeon,
                        "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                        "player_x": exploration.player.x,
                        "player_y": exploration.player.y
                    }

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

                                    # 맵 엔티티에서 보스 정보 확인
                                    is_boss_fight = any(e.is_boss for e in map_enemies) if map_enemies else False
                                    
                                    # 적 생성
                                    if num_enemies > 0:
                                        enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
                                        logger.info(f"적 {len(enemies)}명 생성: {[e.name for e in enemies]}")
                                    else:
                                        # fallback: 랜덤 생성
                                        enemies = EnemyGenerator.generate_enemies(floor_number)
                                        logger.info(f"적 {len(enemies)}명 생성(기본값)")
                                    
                                    # 보스가 포함된 경우 보스 추가/교체
                                    if is_boss_fight and map_enemies:
                                        # 보스 엔티티 찾기
                                        boss_entity = next((e for e in map_enemies if e.is_boss), None)
                                        if boss_entity:
                                            from src.world.enemy_generator import EnemyGenerator
                                            boss = EnemyGenerator.generate_boss(floor_number)
                                            # 보스를 적 리스트의 첫 번째에 추가 (또는 교체)
                                            if enemies:
                                                enemies[0] = boss
                                            else:
                                                enemies.append(boss)
                                            logger.info(f"보스 추가: {boss.name} (enemy_id: {boss.enemy_id})")

                                    # 전투 실행
                                    # 멀티플레이: 근처 참여자만 선택
                                    from src.multiplayer.game_mode import get_game_mode_manager
                                    game_mode_manager = get_game_mode_manager()
                                    
                                    combat_party = party
                                    if game_mode_manager and game_mode_manager.is_multiplayer():
                                        # 멀티플레이 모드: 전투 결과에서 참여자 정보 가져오기
                                        if data and isinstance(data, dict) and "participants" in data:
                                            combat_party = data["participants"]
                                            logger.info(f"멀티플레이 전투: 참여자 {len(combat_party)}명")
                                        else:
                                            # 참여자 정보가 없으면 기본 파티 사용
                                            logger.warning("멀티플레이 전투: 참여자 정보 없음, 기본 파티 사용")
                                    
                                    # 멀티플레이: 전투 데이터에서 참여자 및 위치 정보 가져오기
                                    session_for_combat = None
                                    network_manager_for_combat = None
                                    combat_position = None
                                    
                                    if game_mode_manager and game_mode_manager.is_multiplayer():
                                        if data and isinstance(data, dict):
                                            if "participants" in data:
                                                combat_party = data["participants"]
                                                logger.info(f"멀티플레이 전투: 참여자 {len(combat_party)}명")
                                            else:
                                                combat_party = party
                                                logger.warning("멀티플레이 전투: 참여자 정보 없음, 기본 파티 사용")
                                            if "position" in data:
                                                combat_position = data["position"]
                                        else:
                                            combat_party = party
                                        # TODO: 실제 세션과 네트워크 매니저 가져오기
                                        # 현재는 싱글플레이 모드로 처리
                                    else:
                                        combat_party = party
                                    
                                    combat_result = run_combat(
                                        display.console,
                                        display.context,
                                        combat_party,
                                        enemies,
                                        inventory=inventory,
                                        session=session_for_combat,
                                        network_manager=network_manager_for_combat,
                                        combat_position=combat_position
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
                                            is_boss_fight=is_boss_fight
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

                                        # 전투 후 던전 BGM 재생 (바이옴별 BGM)
                                        from src.audio import play_bgm
                                        floor = exploration.floor_number
                                        # 바이옴 계산 (5층마다 변경: 1-5층=바이옴0, 6-10층=바이옴1, ...)
                                        biome_index = (floor - 1) // 5
                                        biome_index = biome_index % 10  # 10개 바이옴 순환
                                        biome_track = f"biome_{biome_index}"
                                        play_bgm(biome_track, loop=True, fade_in=True)
                                        logger.info(f"던전 BGM 재생 (층수: {floor}, 바이옴: {biome_index}, BGM: {biome_track})")
                                        play_dungeon_bgm = False
                                        continue  # 탐험 계속
                                    elif combat_result == CombatState.DEFEAT:
                                        logger.info("❌ 패배... 게임 오버")

                                        # 게임 정산
                                        from src.ui.game_result_ui import show_game_result
                                        # 싱글플레이 게임이므로 is_multiplayer=False
                                        save_slot_info = exploration.game_stats.get("save_slot", None)
                                        if save_slot_info is None:
                                            save_slot_info = {"is_multiplayer": False}
                                        elif isinstance(save_slot_info, dict):
                                            save_slot_info["is_multiplayer"] = False
                                        show_game_result(
                                            display.console,
                                            display.context,
                                            is_victory=False,
                                            max_floor=exploration.game_stats["max_floor_reached"],
                                            enemies_defeated=exploration.game_stats["enemies_defeated"],
                                            total_gold=exploration.game_stats["total_gold_earned"],
                                            total_exp=exploration.game_stats["total_exp_earned"],
                                            save_slot=save_slot_info,
                                            is_multiplayer=False
                                        )
                                        break
                                    else:
                                        logger.info("🏃 도망쳤다")
                                        # 도망 후 던전 BGM 재생 (바이옴별 BGM)
                                        from src.audio import play_bgm
                                        floor = exploration.floor_number
                                        # 바이옴 계산 (5층마다 변경: 1-5층=바이옴0, 6-10층=바이옴1, ...)
                                        biome_index = (floor - 1) // 5
                                        biome_index = biome_index % 10  # 10개 바이옴 순환
                                        biome_track = f"biome_{biome_index}"
                                        play_bgm(biome_track, loop=True, fade_in=True)
                                        logger.info(f"던전 BGM 재생 (층수: {floor}, 바이옴: {biome_index}, BGM: {biome_track})")
                                        play_dungeon_bgm = False
                                        continue

                                elif result == "floor_down":
                                    # 현재 층 상태 저장
                                    floors_dungeons[floor_number] = {
                                        "dungeon": exploration.dungeon,
                                        "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                        "player_x": exploration.player.x,
                                        "player_y": exploration.player.y
                                    }
                                    
                                    floor_number += 1
                                    exploration.game_stats["max_floor_reached"] = max(exploration.game_stats["max_floor_reached"], floor_number)
                                    logger.info(f"⬇ 다음 층: {floor_number}층 (최대: {exploration.game_stats['max_floor_reached']}층)")
                                    
                                    # 기존 던전이 있으면 재사용, 없으면 생성
                                    if floor_number in floors_dungeons:
                                        floor_data = floors_dungeons[floor_number]
                                        dungeon = floor_data["dungeon"]
                                        # dungeon이 튜플인 경우 언패킹 (하위 호환성)
                                        if isinstance(dungeon, tuple):
                                            dungeon, saved_enemies = dungeon
                                        else:
                                            saved_enemies = floor_data["enemies"]
                                        saved_x = floor_data["player_x"]
                                        saved_y = floor_data["player_y"]
                                        logger.info(f"기존 {floor_number}층 던전 재사용 (적 {len(saved_enemies)}마리)")
                                    else:
                                        dungeon = dungeon_gen.generate(floor_number)
                                        saved_enemies = []
                                        saved_x = None
                                        saved_y = None
                                        logger.info(f"새 {floor_number}층 던전 생성")
                                    
                                    exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                    # 기존 던전이면 저장된 적 사용, 새 던전이면 _spawn_enemies()로 생성된 적 사용
                                    if saved_enemies:
                                        exploration.enemies = saved_enemies
                                    # 새 던전인 경우 _spawn_enemies()가 이미 호출되어 적이 생성됨
                                    if saved_x is not None and saved_y is not None:
                                        exploration.player.x = saved_x
                                        exploration.player.y = saved_y
                                    # 층 변경 시 BGM 재생
                                    play_dungeon_bgm = True
                                    continue
                                elif result == "floor_up":
                                    if floor_number > 1:
                                        # 현재 층 상태 저장
                                        floors_dungeons[floor_number] = {
                                            "dungeon": exploration.dungeon,
                                            "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                            "player_x": exploration.player.x,
                                            "player_y": exploration.player.y
                                        }
                                        
                                        floor_number -= 1
                                        logger.info(f"⬆ 이전 층: {floor_number}층")
                                        
                                        # 기존 던전이 있으면 재사용, 없으면 생성
                                        if floor_number in floors_dungeons:
                                            floor_data = floors_dungeons[floor_number]
                                            dungeon = floor_data["dungeon"]
                                            # dungeon이 튜플인 경우 언패킹 (하위 호환성)
                                            if isinstance(dungeon, tuple):
                                                dungeon, saved_enemies = dungeon
                                            else:
                                                saved_enemies = floor_data["enemies"]
                                            saved_x = floor_data["player_x"]
                                            saved_y = floor_data["player_y"]
                                            logger.info(f"기존 {floor_number}층 던전 재사용 (적 {len(saved_enemies)}마리)")
                                        else:
                                            dungeon = dungeon_gen.generate(floor_number)
                                            saved_enemies = []
                                            saved_x = None
                                            saved_y = None
                                            logger.info(f"새 {floor_number}층 던전 생성")
                                        
                                        exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                        # 기존 던전이면 저장된 적 사용, 새 던전이면 _spawn_enemies()로 생성된 적 사용
                                        if saved_enemies:
                                            exploration.enemies = saved_enemies
                                        # 새 던전인 경우 _spawn_enemies()가 이미 호출되어 적이 생성됨
                                        if saved_x is not None and saved_y is not None:
                                            exploration.player.x = saved_x
                                            exploration.player.y = saved_y
                                        # 층 변경 시 BGM 재생
                                        play_dungeon_bgm = True
                                        continue
                                    else:
                                        logger.info("🎉 던전 탈출 성공!")
                                        # 게임 정산 (승리)
                                        from src.ui.game_result_ui import show_game_result
                                        # 싱글플레이 게임이므로 is_multiplayer=False
                                        save_slot_info = exploration.game_stats.get("save_slot", None)
                                        if save_slot_info is None:
                                            save_slot_info = {"is_multiplayer": False}
                                        elif isinstance(save_slot_info, dict):
                                            save_slot_info["is_multiplayer"] = False
                                        show_game_result(
                                            display.console,
                                            display.context,
                                            is_victory=True,
                                            max_floor=exploration.game_stats["max_floor_reached"],
                                            enemies_defeated=exploration.game_stats["enemies_defeated"],
                                            total_gold=exploration.game_stats["total_gold_earned"],
                                            total_exp=exploration.game_stats["total_exp_earned"],
                                            save_slot=save_slot_info,
                                            is_multiplayer=False
                                        )
                                        break
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
        # 핫 리로드 중지
        if hot_reload_enabled:
            try:
                from src.core.hot_reload import stop_hot_reload
                stop_hot_reload()
            except Exception as e:
                logger.debug(f"핫 리로드 중지 중 오류 (무시): {e}")
        
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
