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
                            actual_port = network_manager.port  # 실제 사용된 포트
                            logger.info(f"호스트 서버 시작됨: ws://0.0.0.0:{actual_port}")
                            logger.info(f"로컬 네트워크 접속 주소: ws://{local_ip}:{actual_port}")
                            logger.info(f"같은 네트워크의 플레이어들은 이 주소로 연결하세요: {local_ip}:{actual_port}")
                            logger.info("참고: 외부 네트워크에서 접속하려면 공인 IP와 포트 포워딩이 필요합니다")
                            
                            # 서버 루프는 별도 스레드에서 실행 (게임 루프와 병렬)
                            import threading
                            def run_server_loop():
                                try:
                                    asyncio.set_event_loop(server_loop)
                                    # 이벤트 루프 참조를 네트워크 매니저에 저장
                                    network_manager._server_event_loop = server_loop
                                    server_loop.run_forever()
                                except Exception as e:
                                    logger.error(f"서버 루프 오류: {e}", exc_info=True)
                                finally:
                                    server_loop.close()
                            
                            server_thread = threading.Thread(target=run_server_loop, daemon=True)
                            server_thread.start()
                            # 서버 스레드가 시작되고 이벤트 루프가 저장될 때까지 약간 대기
                            import time
                            time.sleep(0.2)
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
                            # 호스트가 로비를 취소하면 서버 종료 (클라이언트들이 연결 해제 감지)
                            if network_manager and server_loop:
                                try:
                                    logger.info("호스트 서버 종료 중... (로비 취소)")
                                    if not server_loop.is_closed():
                                        async def stop_server_async():
                                            try:
                                                await network_manager.stop_server()
                                            except Exception as e:
                                                logger.error(f"서버 중지 중 오류: {e}", exc_info=True)
                                        
                                        if server_loop.is_running():
                                            asyncio.run_coroutine_threadsafe(
                                                stop_server_async(),
                                                server_loop
                                            )
                                            import time
                                            time.sleep(0.5)
                                    logger.info("호스트 서버 종료 완료 (로비 취소)")
                                except Exception as e:
                                    logger.error(f"서버 종료 중 오류: {e}", exc_info=True)
                            continue
                        
                        if not lobby_result.get("completed"):
                            continue
                        
                        player_count = lobby_result.get("player_count", 1)
                        local_allocation = lobby_result.get("local_allocation", 4)
                        
                        logger.info(f"로비 완료: {player_count}명 참여, 호스트 캐릭터 할당: {local_allocation}명")
                        
                        # 모든 클라이언트에게 로비 완료 알림 (파티 설정 시작)
                        from src.multiplayer.protocol import MessageBuilder, MessageType
                        import asyncio
                        try:
                            lobby_complete_msg = MessageBuilder.lobby_complete(player_count)
                            # 비동기로 브로드캐스트 (서버 스레드의 이벤트 루프 사용)
                            server_loop = getattr(network_manager, '_server_event_loop', None)
                            if server_loop and server_loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    network_manager.broadcast(lobby_complete_msg),
                                    server_loop
                                )
                                logger.info("로비 완료 메시지 브로드캐스트 완료")
                            else:
                                logger.warning("서버 이벤트 루프를 찾을 수 없습니다. 메시지 브로드캐스트 스킵")
                        except Exception as e:
                            logger.warning(f"로비 완료 메시지 브로드캐스트 실패: {e}", exc_info=True)
                        
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
                        
                        # 패시브 선택 (호스트만)
                        from src.ui.passive_selection import run_passive_selection
                        passive_selection = run_passive_selection(display.console, display.context)
                        
                        if not passive_selection:
                            logger.info("패시브 선택 취소")
                            continue
                        
                        # 패시브 객체 리스트를 ID 리스트로 변환
                        selected_passives = [passive.id for passive in passive_selection.passives] if passive_selection else []
                        
                        # 난이도 선택
                        from src.core.difficulty import DifficultySystem, DifficultyLevel, set_difficulty_system
                        difficulty_system = DifficultySystem(config)
                        
                        # 일반 호스트: UI로 선택
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
                        
                        # 게임 통계 초기화 (마을에서 시작하므로 max_floor_reached는 0)
                        game_stats = {
                            "enemies_defeated": 0,
                            "max_floor_reached": 0,
                            "total_gold_earned": 0,
                            "total_exp_earned": 0,
                            "save_slot": None,
                            "next_dungeon_floor": 1  # 다음 던전 번호 (0->1->0->2->0->3...)
                        }
                        
                        # 게임 시작은 마을(floor 0)에서 시작
                        from src.world.dungeon_generator import DungeonGenerator
                        from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                        
                        floor_number = 0
                        
                        # 각 플레이어마다 자신의 마을 맵 생성 (멀티플레이)
                        from src.town.town_map import TownMap, create_town_dungeon_map
                        from src.town.town_manager import TownManager
                        
                        # 로컬 플레이어의 마을 맵 생성 (각 플레이어는 자신의 마을을 가짐)
                        town_map = TownMap()  # 전역 인스턴스 대신 새 인스턴스 생성
                        town_manager = TownManager()
                        dungeon = create_town_dungeon_map(town_map)
                        
                        logger.info(f"마을 맵 생성 완료 (멀티플레이, 플레이어 {local_player_id})")
                        
                        # PartyMember를 Character 객체로 변환 (특성/패시브 정보 포함)
                        from src.character.character import Character
                        from src.persistence.meta_progress import get_meta_progress
                        character_party = []
                        for idx, member in enumerate(party_members):
                            char = Character(
                                name=member.character_name,
                                character_class=member.job_id,
                                level=1
                            )
                            # 경험치 초기화
                            char.experience = 0
                            
                            # 멀티플레이: 캐릭터에 플레이어 ID 할당
                            # PartyMember에 player_id가 있으면 사용, 없으면 local_player_id 사용
                            if hasattr(member, 'player_id') and member.player_id:
                                char.player_id = member.player_id
                            else:
                                # 로컬 플레이어의 캐릭터에 할당
                                char.player_id = local_player_id
                            logger.debug(f"{member.character_name}에 player_id 할당: {char.player_id}")
                            
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
                        
                        # 파티 강화 업그레이드 적용 (HP/MP 증가)
                        host_meta = get_meta_progress()  # 호스트의 메타 진행
                        from src.character.upgrade_applier import UpgradeApplier
                        UpgradeApplier.apply_to_characters(character_party, meta_progress=host_meta, is_host=True)
                        logger.info("파티 강화 업그레이드 적용 완료")
                        
                        # 시작 장비 지급 (대장간 레벨에 따라 등급 결정)
                        UpgradeApplier.give_starting_equipment(character_party, meta_progress=host_meta, is_host=True)
                        logger.info("시작 장비 지급 완료")
                        
                        # 특성/패시브/업그레이드 적용 후 HP/MP를 최대값으로 보정 (게임 시작 시)
                        for char in character_party:
                            char.current_hp = char.max_hp
                            char.current_mp = char.max_mp
                            char.is_alive = True
                            logger.debug(f"{char.name} HP/MP 초기화: HP={char.current_hp}/{char.max_hp}, MP={char.current_mp}/{char.max_mp}")
                        
                        # 로컬 플레이어의 파티를 Character 객체 리스트로 업데이트 (전투 참여자 수집용)
                        local_player.party = character_party
                        
                        # 다른 플레이어의 파티도 Character 객체로 변환
                        for player_id, mp_player in session.players.items():
                            # 로컬 플레이어는 이미 처리했으므로 건너뛰기
                            if player_id == local_player_id:
                                continue
                            
                            # 다른 플레이어의 파티가 PartyMember 리스트인 경우 Character로 변환
                            if hasattr(mp_player, 'party') and mp_player.party:
                                other_character_party = []
                                for member in mp_player.party:
                                    # 이미 Character 객체인 경우 건너뛰기
                                    from src.character.character import Character
                                    if isinstance(member, Character):
                                        other_character_party.append(member)
                                        continue
                                    
                                    # PartyMember를 Character로 변환
                                    if hasattr(member, 'character_name') and hasattr(member, 'job_id'):
                                        char = Character(
                                            name=member.character_name,
                                            character_class=member.job_id,
                                            level=1
                                        )
                                        char.experience = 0
                                        
                                        # 플레이어 ID 할당
                                        if hasattr(member, 'player_id') and member.player_id:
                                            char.player_id = member.player_id
                                        else:
                                            char.player_id = player_id
                                        
                                        # 특성 적용
                                        if hasattr(member, 'selected_traits') and member.selected_traits:
                                            for trait_id in member.selected_traits:
                                                char.activate_trait(trait_id)
                                        
                                        # 패시브 적용
                                        if selected_passives:
                                            for passive_id in selected_passives:
                                                char.activate_trait(passive_id)
                                        
                                        # 업그레이드 적용
                                        UpgradeApplier.apply_to_characters([char], meta_progress=host_meta, is_host=False)
                                        
                                        # HP/MP 초기화
                                        char.current_hp = char.max_hp
                                        char.current_mp = char.max_mp
                                        char.is_alive = True
                                        
                                        logger.debug(f"{char.name} HP/MP 초기화: HP={char.current_hp}/{char.max_hp}, MP={char.current_mp}/{char.max_mp}")
                                        
                                        other_character_party.append(char)
                                
                                # 변환된 Character 리스트로 업데이트
                                if other_character_party:
                                    mp_player.party = other_character_party
                                    logger.info(f"플레이어 {mp_player.player_name}의 파티를 Character 객체로 변환 완료: {len(other_character_party)}명")
                        
                        # 탐험 시스템 생성 (멀티플레이) - Character 객체 리스트 전달
                        exploration = MultiplayerExplorationSystem(
                            dungeon=dungeon,
                            party=character_party,  # PartyMember가 아닌 Character 객체 리스트
                            floor_number=floor_number,
                            inventory=inventory,
                            game_stats=game_stats,
                            session=session,
                            network_manager=network_manager,
                            local_player_id=local_player_id
                        )
                        
                        # 마을 플레이어 스폰 위치 설정
                        spawn_x, spawn_y = town_map.player_spawn
                        exploration.player.x = spawn_x
                        exploration.player.y = spawn_y
                        
                        # 마을 표시 플래그 추가
                        exploration.is_town = True
                        exploration.town_map = town_map
                        exploration.town_manager = town_manager
                        
                        # 네트워크 매니저에 현재 게임 상태 저장 (클라이언트 연결 시 전송용)
                        network_manager.current_floor = floor_number
                        network_manager.current_dungeon = dungeon
                        network_manager.current_exploration = exploration
                        
                        # 세션에 exploration 저장
                        session.exploration = exploration
                        
                        # 플레이어 초기 위치 설정 (모든 플레이어)
                        # exploration._initialize_player_positions()가 이미 호출되었으므로
                        # 모든 플레이어의 위치를 수집
                        player_positions = {}
                        for player_id, mp_player in session.players.items():
                            if hasattr(mp_player, 'x') and hasattr(mp_player, 'y'):
                                player_positions[player_id] = (int(mp_player.x), int(mp_player.y))
                                logger.info(f"플레이어 {mp_player.player_name} 초기 위치: ({mp_player.x}, {mp_player.y})")
                        
                        # 모든 클라이언트에게 게임 시작 메시지 브로드캐스트
                        from src.multiplayer.protocol import MessageBuilder, MessageType
                        from src.persistence.save_system import serialize_dungeon
                        import asyncio
                        try:
                            dungeon_seed = session.generate_dungeon_seed_for_floor(floor_number)
                            enemies = exploration.enemies if exploration else []
                            dungeon_data = serialize_dungeon(dungeon, enemies=enemies)
                            
                            game_start_msg = MessageBuilder.game_start(
                                dungeon_data=dungeon_data,
                                floor_number=floor_number,
                                dungeon_seed=dungeon_seed,
                                difficulty=difficulty_result.value if hasattr(difficulty_result, 'value') else str(difficulty_result),
                                passives=selected_passives,  # 패시브 정보 포함
                                player_positions=player_positions  # 모든 플레이어의 초기 위치 포함
                            )
                            
                            # 비동기 브로드캐스트
                            server_loop = getattr(network_manager, '_server_event_loop', None)
                            if server_loop and server_loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    network_manager.broadcast(game_start_msg),
                                    server_loop
                                )
                                logger.info(f"게임 시작 메시지 브로드캐스트 완료 (플레이어 위치 {len(player_positions)}개 포함)")
                            else:
                                logger.warning("서버 이벤트 루프를 찾을 수 없습니다. 게임 시작 메시지 브로드캐스트 스킵")
                        except Exception as e:
                            logger.error(f"게임 시작 메시지 브로드캐스트 실패: {e}", exc_info=True)
                        
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
                        
                        # 게임 루프에서 사용할 파티 변수 저장 (층 변경 시 재사용)
                        # character_party는 게임 루프 시작 전에 정의되어 있어야 함
                        
                        play_dungeon_bgm = True
                        
                        # 호스트 채팅 메시지 핸들러 등록 (클라이언트로부터 받은 메시지를 모든 클라이언트에게 브로드캐스트)
                        from src.multiplayer.protocol import MessageType
                        def handle_host_chat_message(msg, sender_id):
                            """호스트 채팅 메시지 핸들러: 클라이언트로부터 받은 메시지를 모든 클라이언트에게 브로드캐스트"""
                            if sender_id and sender_id != local_player_id:
                                # 클라이언트로부터 받은 메시지인 경우만 브로드캐스트
                                try:
                                    import asyncio
                                    if hasattr(network_manager, '_server_event_loop') and network_manager._server_event_loop:
                                        asyncio.run_coroutine_threadsafe(
                                            network_manager.broadcast(msg),
                                            network_manager._server_event_loop
                                        )
                                        logger.debug(f"채팅 메시지 브로드캐스트: {msg.player_id}")
                                except Exception as e:
                                    logger.error(f"채팅 메시지 브로드캐스트 실패: {e}", exc_info=True)
                        
                        network_manager.register_handler(MessageType.CHAT_MESSAGE, handle_host_chat_message)
                        
                        # 멀티플레이 게임 루프
                        while True:
                            result, data = run_exploration(
                                display.console,
                                display.context,
                                exploration,
                                inventory,
                                character_party,  # PartyMember가 아닌 Character 객체 리스트
                                play_bgm_on_start=play_dungeon_bgm,
                                network_manager=network_manager,
                                local_player_id=local_player_id
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
                                    combat_party = data.get("participants", character_party)
                                    combat_position = data.get("position", (local_player.x, local_player.y))
                                else:
                                    num_enemies = 0
                                    map_enemies = []
                                    combat_party = character_party
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
                                    combat_position=combat_position,
                                    local_player_id=local_player_id
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
                                    
                                    # 전투 후 복귀 시 필드 BGM 재생
                                    play_dungeon_bgm = True
                                elif combat_result == CombatState.DEFEAT:
                                    # 전투 참여 파티원만 죽었는지, 모든 플레이어의 모든 캐릭터가 죽었는지 확인
                                    is_game_over = False
                                    if session:
                                        all_players_dead = True
                                        for player_id, player in session.players.items():
                                            if hasattr(player, 'party') and player.party:
                                                has_alive = False
                                                for char in player.party:
                                                    if hasattr(char, 'is_alive') and char.is_alive:
                                                        has_alive = True
                                                        break
                                                    elif hasattr(char, 'current_hp') and char.current_hp > 0:
                                                        has_alive = True
                                                        break
                                                if has_alive:
                                                    all_players_dead = False
                                                    break
                                        is_game_over = all_players_dead
                                    
                                    if is_game_over:
                                        logger.info("❌ 패배... 게임 오버")
                                        from src.ui.game_result_ui import show_game_result
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
                                    else:
                                        logger.info("❌ 패배... 맵으로 복귀")
                                        # 전투 패배 후 복귀 시 필드 BGM 재생
                                        play_dungeon_bgm = True
                                        continue
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
                                
                                # 멀티플레이 모드 유지 확인 (층 변경 후에도 멀티플레이 상태 유지)
                                if hasattr(exploration, 'is_multiplayer'):
                                    # MultiplayerExplorationSystem인 경우 is_multiplayer는 이미 True로 설정되어 있음
                                    # 하지만 확실하게 하기 위해 재확인
                                    if session:
                                        exploration.is_multiplayer = True
                                    else:
                                        from src.multiplayer.game_mode import get_game_mode_manager
                                        game_mode_manager = get_game_mode_manager()
                                        if game_mode_manager:
                                            exploration.is_multiplayer = game_mode_manager.is_multiplayer()
                                
                                # FOV 업데이트 (층 변경 후 필수)
                                if hasattr(exploration, 'update_fov'):
                                    exploration.update_fov()
                                
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
                        client_loop = None
                        try:
                            client_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(client_loop)
                            client_loop.run_until_complete(network_manager.connect(local_player_id, player_name))
                            logger.info("호스트 연결 성공!")
                            
                            # 클라이언트 이벤트 루프를 별도 스레드에서 실행 (메시지 수신 루프가 계속 실행되도록)
                            import threading
                            def run_client_loop():
                                try:
                                    asyncio.set_event_loop(client_loop)
                                    # 이벤트 루프 참조를 네트워크 매니저에 저장
                                    network_manager._client_event_loop = client_loop
                                    client_loop.run_forever()
                                except Exception as e:
                                    logger.error(f"클라이언트 루프 오류: {e}", exc_info=True)
                                finally:
                                    if not client_loop.is_closed():
                                        client_loop.close()
                            
                            client_thread = threading.Thread(target=run_client_loop, daemon=True)
                            client_thread.start()
                            # 클라이언트 스레드가 시작될 때까지 약간 대기
                            import time
                            time.sleep(0.1)
                            logger.info("클라이언트 메시지 수신 루프 시작")
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
                            if client_loop and not client_loop.is_closed():
                                client_loop.close()
                            continue
                        
                        # 세션 정보 대기 (호스트로부터 세션 정보 수신)
                        logger.info("세션 정보 대기 중...")
                        
                        # 세션 정보 수신 대기 (최대 10초)
                        # 메시지 수신 루프는 별도 스레드에서 실행 중
                        timeout = 10.0
                        start_time = time.time()
                        while time.time() - start_time < timeout:
                            # 세션 시드만 받으면 게임 시작 전 연결로 처리 가능 (던전 데이터는 나중에 받을 수 있음)
                            if session_data["session_seed"] is not None:
                                logger.info("세션 시드 수신 확인!")
                                break
                            # 메시지 처리를 위해 짧게 대기 (별도 스레드에서 실행 중이므로 대기만)
                            import time as time_module
                            time_module.sleep(0.05)
                        
                        # 세션 정보 확인
                        if session_data["session_seed"] is None:
                            logger.error("세션 시드를 받지 못했습니다")
                            raise Exception("세션 시드 수신 실패")
                        
                        if session_data["dungeon_data"] is None:
                            logger.warning("던전 데이터를 받지 못했습니다. 게임 시작 전 클라이언트 연결일 수 있습니다.")
                            # 게임이 시작되지 않은 경우, 로비로 이동하여 대기
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
                            
                            # 멀티플레이 로비로 이동하여 호스트가 게임을 시작할 때까지 대기
                            from src.ui.multiplayer_lobby import show_multiplayer_lobby, get_character_allocation
                            from src.multiplayer.game_mode import get_game_mode_manager, MultiplayerMode
                            game_mode_manager = get_game_mode_manager()
                            
                            # 플레이어 수 확인 (세션의 플레이어 수 또는 session_data의 플레이어 목록 크기)
                            player_count = len(session.players)
                            # 세션에 플레이어가 1명만 있으면 (클라이언트만) 최소 2명으로 설정 (호스트 포함)
                            if player_count < 2:
                                # session_data["players"]에 호스트가 포함되어 있을 수 있음
                                if session_data.get("players"):
                                    player_count = len(session_data["players"])
                                else:
                                    # 플레이어가 1명이면 최소 2명으로 설정 (호스트 포함 예상)
                                    player_count = 2
                            
                            # 플레이어 수는 최소 2명, 최대 4명
                            player_count = max(2, min(4, player_count))
                            
                            game_mode_manager.set_multiplayer(
                                player_count=player_count,
                                is_host=False,
                                session_id=session.session_id
                            )
                            game_mode_manager.local_player_id = local_player_id
                            game_mode_manager.is_host = False
                            
                            # 던전 데이터 수신 핸들러 등록 (게임 시작 대기)
                            # 로비에서 던전 데이터를 받으면 자동으로 완료되도록 설정
                            def handle_dungeon_data_for_lobby(msg, sender_id):
                                session_data["dungeon_data"] = msg.data.get("dungeon")
                                session_data["floor_number"] = msg.data.get("floor_number")
                                session_data["dungeon_seed"] = msg.data.get("seed")
                                logger.info(f"던전 데이터 수신: {session_data['floor_number']}층 (로비에서 대기 중)")
                            
                            # 플레이어 목록 업데이트 핸들러 (로비에서 플레이어 추가/제거 감지)
                            def handle_player_list_for_lobby(msg, sender_id):
                                players_list = msg.data.get("players", [])
                                session_data["players"] = players_list
                                
                                # 세션에 플레이어 추가/업데이트
                                for player_data in players_list:
                                    player_id = player_data.get("player_id")
                                    if not player_id:
                                        continue
                                    
                                    # 이미 세션에 있는 플레이어는 업데이트
                                    if player_id in session.players:
                                        existing_player = session.players[player_id]
                                        existing_player.player_name = player_data.get("player_name", existing_player.player_name)
                                        existing_player.x = player_data.get("x", existing_player.x)
                                        existing_player.y = player_data.get("y", existing_player.y)
                                        existing_player.is_host = player_data.get("is_host", False)
                                    else:
                                        # 새 플레이어 추가 (로컬 플레이어 제외)
                                        if player_id != local_player_id:
                                            from src.multiplayer.player import MultiplayerPlayer
                                            new_player = MultiplayerPlayer(
                                                player_id=player_id,
                                                player_name=player_data.get("player_name", "플레이어"),
                                                x=player_data.get("x", 0),
                                                y=player_data.get("y", 0),
                                                party=[],
                                                is_host=player_data.get("is_host", False)
                                            )
                                            session.add_player(new_player)
                                            logger.info(f"로비에서 플레이어 추가: {new_player.player_name} ({player_id})")
                                
                                logger.info(f"플레이어 목록 업데이트: {len(session.players)}명")
                            
                            # 로비 완료 핸들러 (호스트가 파티 설정으로 넘어갈 때)
                            import threading
                            lobby_complete_lock = threading.Lock()
                            lobby_complete_received = {"value": False}
                            def handle_lobby_complete(msg, sender_id):
                                try:
                                    with lobby_complete_lock:
                                        lobby_complete_received["value"] = True
                                    player_count = msg.data.get("player_count", 2)
                                    logger.info(f"로비 완료 메시지 수신: 파티 설정 시작 (플레이어 {player_count}명)")
                                except Exception as e:
                                    logger.error(f"로비 완료 핸들러 오류: {e}", exc_info=True)
                            
                            # 플레이어 나감 핸들러 (호스트 포함)
                            host_disconnected_lock = threading.Lock()
                            host_disconnected = {"value": False}
                            def handle_player_left(msg, sender_id):
                                try:
                                    player_id = msg.data.get("player_id") or msg.player_id
                                    if player_id:
                                        # 세션에서 플레이어 제거
                                        with host_disconnected_lock:
                                            if player_id in session.players:
                                                removed_player = session.players[player_id]
                                                is_host_player = removed_player.is_host
                                                session.remove_player(player_id)
                                                logger.info(f"로비에서 플레이어 제거: {removed_player.player_name} ({player_id})")
                                                
                                                # 호스트가 나갔으면 플래그 설정
                                                if is_host_player:
                                                    host_disconnected["value"] = True
                                                    logger.warning("호스트가 로비를 나갔습니다!")
                                except Exception as e:
                                    logger.error(f"플레이어 나감 핸들러 오류: {e}", exc_info=True)
                            
                            # 게임 시작 핸들러 (호스트가 패시브/난이도 선택 완료 후)
                            game_started = {"value": False}
                            def handle_game_start(msg, sender_id):
                                try:
                                    dungeon_data = msg.data.get("dungeon")
                                    floor_number = msg.data.get("floor_number", 1)
                                    dungeon_seed = msg.data.get("seed")
                                    difficulty_str = msg.data.get("difficulty", "normal")
                                    passives = msg.data.get("passives", [])  # 패시브 정보 받기
                                    player_positions = msg.data.get("player_positions", {})  # 플레이어 초기 위치 받기
                                    
                                    if dungeon_data:
                                        session_data["dungeon_data"] = dungeon_data
                                        session_data["floor_number"] = floor_number
                                        session_data["dungeon_seed"] = dungeon_seed
                                        session_data["difficulty"] = difficulty_str
                                        session_data["player_positions"] = player_positions  # 초기 위치 저장
                                        if passives:
                                            session_data["local_selected_passives"] = passives
                                            logger.info(f"게임 시작 메시지에서 패시브 수신: {passives}")
                                        if player_positions:
                                            logger.info(f"게임 시작 메시지에서 플레이어 초기 위치 수신: {len(player_positions)}개")
                                        game_started["value"] = True
                                        logger.info(f"게임 시작 메시지 수신: {floor_number}층, 난이도={difficulty_str}")
                                    else:
                                        logger.warning("게임 시작 메시지에 던전 데이터가 없습니다")
                                except Exception as e:
                                    logger.error(f"게임 시작 핸들러 오류: {e}", exc_info=True)
                            
                            network_manager.register_handler(MessageType.DUNGEON_DATA, handle_dungeon_data_for_lobby)
                            network_manager.register_handler(MessageType.PLAYER_JOINED, handle_player_list_for_lobby)
                            network_manager.register_handler(MessageType.LOBBY_COMPLETE, handle_lobby_complete)
                            network_manager.register_handler(MessageType.PLAYER_LEFT, handle_player_left)
                            network_manager.register_handler(MessageType.GAME_START, handle_game_start)
                            
                            # 로비에 던전 데이터 확인용 딕셔너리 전달
                            # 로비 내부에서 던전 데이터를 받았는지 확인하고 자동 완료
                            lobby_result = show_multiplayer_lobby(
                                display.console,
                                display.context,
                                session=session,
                                network_manager=network_manager,
                                local_player_id=local_player_id,
                                is_host=False,
                                dungeon_data_check=session_data,  # 던전 데이터 확인용 딕셔너리 전달
                                lobby_complete_check=lobby_complete_received  # 로비 완료 확인용
                            )
                            
                            # 호스트 연결이 끊어졌거나 호스트가 나갔으면 메인 메뉴로 돌아가기
                            if lobby_result and (lobby_result.get("host_disconnected") or host_disconnected.get("value", False)):
                                logger.warning("호스트가 나갔습니다. 메인 메뉴로 돌아갑니다.")
                                # 연결 종료
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(network_manager.disconnect())
                                    loop.close()
                                except Exception as e:
                                    logger.error(f"연결 종료 오류: {e}", exc_info=True)
                                
                                # 메시지 표시
                                from src.ui.npc_dialog_ui import show_npc_dialog
                                show_npc_dialog(
                                    display.console,
                                    display.context,
                                    "연결 종료",
                                    "호스트가 게임을 나갔습니다.\n\n메인 메뉴로 돌아갑니다."
                                )
                                continue  # 메인 메뉴로 돌아가기
                            
                            if lobby_result and lobby_result.get("completed"):
                                # 로비 완료 메시지를 받았는지 확인 (파티 설정으로 이동)
                                if lobby_complete_received.get("value", False):
                                    logger.info("로비 완료! 파티 설정으로 이동")
                                    # 파티 설정으로 이동 (호스트와 동기화)
                                    player_count = len(session.players)
                                    local_allocation = get_character_allocation(player_count, False)
                                    
                                    from src.ui.multiplayer_party_setup import run_multiplayer_party_setup
                                    party_result = run_multiplayer_party_setup(
                                        display.console,
                                        display.context,
                                        session=session,
                                        network_manager=network_manager,
                                        local_player_id=local_player_id,
                                        character_allocation=local_allocation,
                                        is_host=False
                                    )
                                    
                                    if not party_result:
                                        logger.info("파티 설정 취소")
                                        try:
                                            client_loop = getattr(network_manager, '_client_event_loop', None)
                                            if client_loop and not client_loop.is_closed():
                                                asyncio.run_coroutine_threadsafe(
                                                    network_manager.disconnect(),
                                                    client_loop
                                                )
                                        except Exception:
                                            pass
                                        continue
                                    
                                    party_members, selected_passives = party_result
                                    
                                    if not party_members:
                                        logger.info("파티 멤버 없음")
                                        try:
                                            client_loop = getattr(network_manager, '_client_event_loop', None)
                                            if client_loop and not client_loop.is_closed():
                                                asyncio.run_coroutine_threadsafe(
                                                    network_manager.disconnect(),
                                                    client_loop
                                                )
                                        except Exception:
                                            pass
                                        continue
                                    
                                    # 로컬 플레이어의 파티 설정
                                    local_player.party = party_members
                                    
                                    # session의 local_player에도 파티 정보 저장
                                    if session and local_player_id in session.players:
                                        session.players[local_player_id].party = party_members
                                        logger.info(f"session.players[{local_player_id}].party에 저장: {len(party_members)}명")
                                    
                                    # 파티 정보를 session_data에 저장 (게임 시작 로직에서 사용)
                                    session_data["local_party_members"] = party_members
                                    session_data["local_selected_passives"] = selected_passives
                                    logger.info(f"파티 정보를 session_data에 저장: {len(party_members)}명, session_data keys: {list(session_data.keys())}")
                                    
                                    # 호스트가 게임을 시작할 때까지 대기 (게임 시작 메시지 수신)
                                    logger.info("파티 설정 완료! 호스트가 게임을 시작할 때까지 대기...")
                                    timeout = 300.0  # 최대 5분 대기
                                    start_time = time.time()
                                    
                                    while time.time() - start_time < timeout:
                                        if game_started.get("value", False):
                                            logger.info("게임 시작 메시지 수신! 게임을 시작합니다.")
                                            # 게임 시작 메시지를 받았으므로, session_data에 던전 데이터가 설정되어 있음
                                            # 아래의 게임 시작 로직으로 진행하기 위해 break
                                            break
                                        
                                        # 짧게 대기 (백그라운드에서 메시지 수신 중)
                                        time.sleep(0.1)
                                    
                                    if not game_started.get("value", False):
                                        logger.error("게임 시작 타임아웃: 호스트가 게임을 시작하지 않았습니다")
                                        try:
                                            client_loop = getattr(network_manager, '_client_event_loop', None)
                                            if client_loop and not client_loop.is_closed():
                                                asyncio.run_coroutine_threadsafe(
                                                    network_manager.disconnect(),
                                                    client_loop
                                                )
                                        except Exception:
                                            pass
                                        continue
                                    
                                    # 게임 시작 메시지를 받았으므로, session_data에 던전 데이터가 있음
                                    # 아래 게임 시작 로직으로 진행
                                    logger.info("=== 게임 시작 로직 진입 ===")
                                    logger.info("게임 시작 로직으로 진행 - 파티 정보 확인")
                                    # 파티 정보가 session_data에 있는지 확인
                                    if "local_party_members" in session_data:
                                        logger.info(f"session_data에 파티 정보 있음: {len(session_data['local_party_members'])}명")
                                    else:
                                        logger.warning("session_data에 파티 정보 없음!")
                                    
                                    # local_player의 파티 정보 확인
                                    if local_player and local_player.party:
                                        logger.info(f"local_player.party 있음: {len(local_player.party)}명")
                                    else:
                                        logger.warning("local_player.party 없음!")
                                    
                                    # 던전 데이터 역직렬화 및 게임 시작
                                    # (session과 local_player는 이미 위에서 생성됨)
                                    logger.info("로비 완료! 던전 데이터 역직렬화 및 게임 시작")
                                    
                                    # 던전 데이터가 없는 경우 (게임 시작 후 연결)
                                    # 세션 생성 (호스트로부터 받은 정보로 초기화)
                                    logger.info("던전 데이터 체크 시작")
                                    if session_data["dungeon_data"] is None:
                                        logger.error("던전 데이터가 없습니다!")
                                        try:
                                            client_loop = getattr(network_manager, '_client_event_loop', None)
                                            if client_loop and not client_loop.is_closed():
                                                asyncio.run_coroutine_threadsafe(
                                                    network_manager.disconnect(),
                                                    client_loop
                                                )
                                        except Exception:
                                            pass
                                        continue
                                    
                                    logger.info("던전 데이터 있음, 파티 정보 확인 시작")
                                    # session_data에 파티 정보가 있는지 먼저 확인 (멀티플레이 파티 설정에서 설정됨)
                                    saved_party = session_data.get("local_party_members", [])
                                    logger.info(f"게임 시작 로직 - session_data 파티 정보 확인: {len(saved_party)}명, session_data keys: {list(session_data.keys())}")
                                    
                                    # session에서도 파티 정보 확인 (백업)
                                    if not saved_party and 'session' in locals() and session and local_player_id in session.players:
                                        session_player = session.players[local_player_id]
                                        if session_player.party and len(session_player.party) > 0:
                                            saved_party = session_player.party
                                            logger.info(f"session에서 파티 정보 가져옴: {len(saved_party)}명")
                                            # session_data에도 저장
                                            session_data["local_party_members"] = saved_party
                                    
                                    # local_player의 파티 정보 확인 및 설정
                                    if not local_player.party or len(local_player.party) == 0:
                                        if saved_party:
                                            local_player.party = saved_party
                                            logger.info(f"local_player.party에 파티 정보 설정: {len(saved_party)}명")
                                    
                                    # 파티 설정 확인 (멀티플레이 클라이언트는 이미 파티 설정 완료)
                                    # session_data에 파티 정보가 있으면 무조건 사용 (멀티플레이 파티 설정에서 설정됨)
                                    if saved_party:
                                        local_player.party = saved_party
                                        logger.info(f"session_data에서 파티 정보 사용: {len(saved_party)}명")
                                    
                                    # local_player.party가 이미 설정되어 있는지 확인
                                    logger.info(f"파티 설정 확인 - local_player.party: {len(local_player.party) if local_player.party else 0}명")
                                    if not local_player.party or len(local_player.party) == 0:
                                        logger.error("파티 정보가 없습니다! 싱글플레이 파티 설정을 호출하지 않습니다.")
                                        try:
                                            client_loop = getattr(network_manager, '_client_event_loop', None)
                                            if client_loop and not client_loop.is_closed():
                                                asyncio.run_coroutine_threadsafe(
                                                    network_manager.disconnect(),
                                                    client_loop
                                                )
                                        except Exception:
                                            pass
                                        continue
                                    
                                    # 파티 정보가 있으면 게임 시작 로직으로 진행
                                    party_members_raw = local_player.party
                                    selected_passives = session_data.get("local_selected_passives", [])
                                    logger.info(f"게임 시작 - 파티 멤버: {len(party_members_raw)}명")
                                    
                                    # PartyMember를 Character 객체로 변환 (호스트와 동일)
                                    from src.ui.party_setup import PartyMember
                                    from src.character.character import Character
                                    party_members = []
                                    for member in party_members_raw:
                                        # 이미 Character 객체인 경우 그대로 사용
                                        if not isinstance(member, PartyMember):
                                            party_members.append(member)
                                            continue
                                        
                                        # PartyMember를 Character로 변환
                                        char = Character(
                                            name=member.character_name,
                                            character_class=member.job_id,
                                            level=1
                                        )
                                        char.experience = 0
                                        
                                        # 멀티플레이: 캐릭터에 플레이어 ID 할당
                                        if hasattr(member, 'player_id') and member.player_id:
                                            char.player_id = member.player_id
                                        else:
                                            char.player_id = local_player_id
                                        
                                        # 파티 구성에서 선택된 특성 적용
                                        if member.selected_traits:
                                            for trait_id in member.selected_traits:
                                                char.activate_trait(trait_id)
                                        
                                        party_members.append(char)
                                    
                                    # 선택된 패시브를 모든 캐릭터에 적용
                                    if selected_passives:
                                        logger.info(f"클라이언트 패시브 적용 시작: {selected_passives}")
                                        for passive_id in selected_passives:
                                            for char in party_members:
                                                if char.activate_trait(passive_id):
                                                    logger.debug(f"{char.name}에 패시브 추가: {passive_id}")
                                                else:
                                                    logger.warning(f"{char.name}에 패시브 추가 실패: {passive_id}")
                                        logger.info(f"클라이언트 패시브 적용 완료: {', '.join(selected_passives)}")
                                    else:
                                        logger.warning("클라이언트: 선택된 패시브가 없습니다!")
                                    
                                    logger.info(f"파티 변환 완료: {len(party_members)}명 (Character 객체)")
                                    
                                    # 게임 시작 로직 실행
                                    logger.info("게임 시작 로직 실행 시작")
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
                                    
                                    # 플레이어 초기 위치 설정 (호스트로부터 받은 위치 사용)
                                    player_positions = session_data.get("player_positions", {})
                                    if player_positions:
                                        logger.info(f"호스트로부터 받은 플레이어 초기 위치: {len(player_positions)}개")
                                        # 모든 플레이어의 위치 설정
                                        for player_id, pos_data in player_positions.items():
                                            if player_id in session.players:
                                                mp_player = session.players[player_id]
                                                if isinstance(pos_data, dict):
                                                    pos_x = pos_data.get("x", 0)
                                                    pos_y = pos_data.get("y", 0)
                                                else:
                                                    # 튜플 형식인 경우
                                                    pos_x, pos_y = pos_data
                                                
                                                # 이동 가능한 위치인지 확인
                                                if dungeon.is_walkable(pos_x, pos_y):
                                                    mp_player.x = pos_x
                                                    mp_player.y = pos_y
                                                    logger.info(f"플레이어 {mp_player.player_name} 초기 위치 설정: ({pos_x}, {pos_y})")
                                                else:
                                                    # 이동 불가능한 위치면 근처에서 찾기
                                                    logger.warning(f"플레이어 {mp_player.player_name} 초기 위치 ({pos_x}, {pos_y})가 이동 불가능합니다. 근처 위치 찾는 중...")
                                                    import random
                                                    found = False
                                                    for _ in range(30):
                                                        offset_x = random.randint(-3, 3)
                                                        offset_y = random.randint(-3, 3)
                                                        test_x = max(0, min(dungeon.width - 1, pos_x + offset_x))
                                                        test_y = max(0, min(dungeon.height - 1, pos_y + offset_y))
                                                        if dungeon.is_walkable(test_x, test_y):
                                                            mp_player.x = test_x
                                                            mp_player.y = test_y
                                                            found = True
                                                            logger.info(f"플레이어 {mp_player.player_name} 초기 위치 조정: ({test_x}, {test_y})")
                                                            break
                                                    if not found:
                                                        # 기본 위치 사용
                                                        if dungeon.rooms:
                                                            first_room = dungeon.rooms[0]
                                                            mp_player.x = first_room.x + 2
                                                            mp_player.y = first_room.y + 2
                                                            logger.warning(f"플레이어 {mp_player.player_name} 기본 위치 사용: ({mp_player.x}, {mp_player.y})")
                                        
                                        # 로컬 플레이어 위치 설정
                                        if local_player_id in session.players:
                                            mp_player = session.players[local_player_id]
                                            local_player.x = mp_player.x
                                            local_player.y = mp_player.y
                                            exploration.player.x = mp_player.x
                                            exploration.player.y = mp_player.y
                                            logger.info(f"로컬 플레이어 초기 위치: ({mp_player.x}, {mp_player.y})")
                                    else:
                                        # 호스트로부터 위치를 받지 못한 경우 (기존 로직)
                                        logger.warning("호스트로부터 플레이어 초기 위치를 받지 못했습니다. 기본 위치 사용")
                                        if local_player_id in session.players:
                                            mp_player = session.players[local_player_id]
                                            if not hasattr(mp_player, 'x') or mp_player.x == 0:
                                                import random
                                                spawn_x, spawn_y = 5, 5
                                                if dungeon.rooms:
                                                    first_room = dungeon.rooms[0]
                                                    for _ in range(20):
                                                        test_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                                                        test_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                                                        if dungeon.is_walkable(test_x, test_y):
                                                            spawn_x, spawn_y = test_x, test_y
                                                            break
                                                mp_player.x = spawn_x
                                                mp_player.y = spawn_y
                                                local_player.x = spawn_x
                                                local_player.y = spawn_y
                                                exploration.player.x = spawn_x
                                                exploration.player.y = spawn_y
                                                logger.info(f"클라이언트 플레이어 초기 위치 설정: ({spawn_x}, {spawn_y})")
                                                logger.info(f"플레이어 위치 수정: ({spawn_x}, {spawn_y})")
                                            
                                            local_player.x = mp_player.x
                                            local_player.y = mp_player.y
                                            exploration.player.x = mp_player.x
                                            exploration.player.y = mp_player.y
                                            logger.info(f"클라이언트 플레이어 위치 동기화: ({mp_player.x}, {mp_player.y})")
                                    
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
                                                play_bgm_on_start=play_dungeon_bgm,
                                                network_manager=network_manager,
                                                local_player_id=local_player_id
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
                                                    combat_position=combat_position,
                                                    local_player_id=local_player_id
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
                                                    
                                                    # 전투 후 복귀 시 필드 BGM 재생
                                                    from src.audio import play_bgm
                                                    if hasattr(exploration, 'is_town') and exploration.is_town:
                                                        # 마을인 경우 마을 BGM 재생
                                                        play_bgm("town", loop=True, fade_in=True)
                                                    else:
                                                        # 던전인 경우 바이옴별 BGM 재생
                                                        floor = exploration.floor_number
                                                        biome_index = (floor - 1) % 10
                                                        biome_track = f"biome_{biome_index}"
                                                        play_bgm(biome_track)
                                                    play_dungeon_bgm = True
                                                elif combat_result == CombatState.DEFEAT:
                                                    # 전투 참여 파티원만 죽었는지, 모든 플레이어의 모든 캐릭터가 죽었는지 확인
                                                    is_game_over = False
                                                    if session:
                                                        all_players_dead = True
                                                        for player_id, player in session.players.items():
                                                            if hasattr(player, 'party') and player.party:
                                                                has_alive = False
                                                                for char in player.party:
                                                                    if hasattr(char, 'is_alive') and char.is_alive:
                                                                        has_alive = True
                                                                        break
                                                                    elif hasattr(char, 'current_hp') and char.current_hp > 0:
                                                                        has_alive = True
                                                                        break
                                                                if has_alive:
                                                                    all_players_dead = False
                                                                    break
                                                        is_game_over = all_players_dead
                                                    
                                                    if is_game_over:
                                                        logger.info("❌ 패배... 게임 오버")
                                                        from src.ui.game_result_ui import show_game_result
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
                                                    else:
                                                        logger.info("❌ 패배... 맵으로 복귀")
                                                        # 전투 패배 후 복귀 시 필드 BGM 재생
                                                        from src.audio import play_bgm
                                                        if hasattr(exploration, 'is_town') and exploration.is_town:
                                                            # 마을인 경우 마을 BGM 재생
                                                            play_bgm("town", loop=True, fade_in=True)
                                                        else:
                                                            # 던전인 경우 바이옴별 BGM 재생
                                                            floor = exploration.floor_number
                                                            biome_index = (floor - 1) % 10
                                                            biome_track = f"biome_{biome_index}"
                                                            play_bgm(biome_track)
                                                        play_dungeon_bgm = True
                                                        continue
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
                                                
                                                # 멀티플레이 모드 유지 확인 (층 변경 후에도 멀티플레이 상태 유지)
                                                if hasattr(exploration, 'is_multiplayer'):
                                                    # MultiplayerExplorationSystem인 경우 is_multiplayer는 이미 True로 설정되어 있음
                                                    # 하지만 확실하게 하기 위해 재확인
                                                    if session:
                                                        exploration.is_multiplayer = True
                                                    else:
                                                        from src.multiplayer.game_mode import get_game_mode_manager
                                                        game_mode_manager = get_game_mode_manager()
                                                        if game_mode_manager:
                                                            exploration.is_multiplayer = game_mode_manager.is_multiplayer()
                                                
                                                # FOV 업데이트 (층 변경 후 필수)
                                                if hasattr(exploration, 'update_fov'):
                                                    exploration.update_fov()
                                                play_dungeon_bgm = True
                                                continue
                                    except Exception as e:
                                        logger.error(f"게임 루프 오류: {e}", exc_info=True)
                                        break
                                    
                                    # 게임 루프 종료 후 연결 종료
                                    logger.info("클라이언트 게임 루프 종료 - 연결 종료")
                                    try:
                                        client_loop = getattr(network_manager, '_client_event_loop', None)
                                        if client_loop and not client_loop.is_closed():
                                            asyncio.run_coroutine_threadsafe(
                                                network_manager.disconnect(),
                                                client_loop
                                            )
                                    except Exception as e:
                                        logger.error(f"연결 종료 중 오류: {e}", exc_info=True)
                                    
                                    logger.info("클라이언트 세션 종료")
                                
                                # 던전 데이터를 받았는지 확인 (게임 시작 후 연결)
                                elif session_data["dungeon_data"] is not None:
                                    logger.info("던전 데이터 수신 완료! 게임 진행 가능")
                                    # 던전 데이터를 받았으면 아래의 게임 시작 로직으로 진행
                                    # (이제 session과 local_player가 이미 생성되어 있으므로, 던전 데이터만 역직렬화하면 됨)
                                else:
                                    logger.warning("로비에서 나갔지만 던전 데이터나 로비 완료 메시지가 없음")
                                    try:
                                        client_loop = getattr(network_manager, '_client_event_loop', None)
                                        if client_loop and not client_loop.is_closed():
                                            asyncio.run_coroutine_threadsafe(
                                                network_manager.disconnect(),
                                                client_loop
                                            )
                                    except Exception:
                                        pass
                                    continue
                            else:
                                # 로비에서 취소됨
                                logger.info("로비에서 취소됨")
                                try:
                                    client_loop = getattr(network_manager, '_client_event_loop', None)
                                    if client_loop and not client_loop.is_closed():
                                        asyncio.run_coroutine_threadsafe(
                                            network_manager.disconnect(),
                                            client_loop
                                        )
                                except Exception:
                                    pass
                                continue
                        
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
                    
                    # 멀티플레이 세이브 여부 확인 및 처리
                    is_multiplayer_load = loaded_state.get("is_multiplayer", False)
                    session = None
                    network_manager = None
                    local_player_id = None
                    local_player = None
                    assignments = None
                    
                    if is_multiplayer_load:
                        # 멀티플레이 세이브: 무조건 호스트 모드로 진행 (호스트만 저장 가능)
                        logger.info(f"멀티플레이 세이브 불러오기 감지: is_multiplayer={is_multiplayer_load} (호스트 모드로 진행)")
                        
                        # 호스트 모드로 강제 설정 (멀티플레이 게임을 불러올 때는 호스트만 저장할 수 있으므로)
                        mode = "host"
                        
                        # 멀티플레이 세션 설정 (호스트/조인)
                        from src.multiplayer.game_mode import get_game_mode_manager
                        from src.multiplayer.session import MultiplayerSession
                        from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
                        from src.multiplayer.player import MultiplayerPlayer
                        from uuid import uuid4
                        import asyncio
                        
                        game_mode_manager = get_game_mode_manager()
                        
                        # 멀티플레이 게임을 불러올 때는 무조건 호스트 모드 (호스트만 저장 가능)
                        # 호스트 모드 설정
                        logger.info("멀티플레이 세이브: 호스트 모드로 재개 (호스트만 저장 가능)")
                        local_player_id = str(uuid4())[:8]
                        session = MultiplayerSession(max_players=4)
                        session.host_id = local_player_id
                        game_mode_manager.local_player_id = local_player_id
                        game_mode_manager.is_host = True
                        
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
                        
                        network_manager = HostNetworkManager(port=0, session=session)  # 포트 자동 할당
                        network_manager.player_id = local_player_id
                        
                        # 서버 시작
                        server_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(server_loop)
                        server_task = server_loop.create_task(network_manager.start_server())
                        server_loop.run_until_complete(asyncio.sleep(0.5))
                        
                        logger.info(f"멀티플레이 세션 재개 (호스트): {session.session_id}")
                        logger.info(f"로컬 네트워크 접속 주소: ws://{network_manager.local_ip}:{network_manager.port}")
                        
                        # 주석: 조인 모드는 멀티플레이 게임을 불러올 때 사용하지 않음 (호스트만 저장 가능)
                        # elif mode == "join":
                        #     # 조인 모드
                        #     host_address = multiplayer_result.get("host_address")
                        #     port = multiplayer_result.get("port", 5000)
                        #     
                        #     if not host_address:
                        #         logger.error("호스트 주소가 없습니다")
                        #         continue
                        #     
                        #     logger.info(f"멀티플레이 세이브: 조인 모드로 재개 - {host_address}:{port}")
                        #     local_player_id = str(uuid4())[:8]
                        #     network_manager = ClientNetworkManager(host_address, port)
                        #     network_manager.player_id = local_player_id
                        #     game_mode_manager.local_player_id = local_player_id
                        #     game_mode_manager.is_host = False
                        #     
                        #     # 연결 대기
                        #     try:
                        #         loop = asyncio.new_event_loop()
                        #         asyncio.set_event_loop(loop)
                        #         loop.run_until_complete(network_manager.connect())
                        #         
                        #         # 세션 데이터 수신 대기
                        #         import time
                        #         timeout = 5.0
                        #         start_time = time.time()
                        #         while not hasattr(network_manager, 'session') or network_manager.session is None:
                        #             if time.time() - start_time > timeout:
                        #                 logger.error("세션 데이터 수신 타임아웃")
                        #                 break
                        #             loop.run_until_complete(asyncio.sleep(0.1))
                        #         
                        #         if hasattr(network_manager, 'session') and network_manager.session:
                        #             session = network_manager.session
                        #             local_player = session.get_player(local_player_id)
                        #             logger.info(f"멀티플레이 세션 재개 (조인): {session.session_id}")
                        #         else:
                        #             logger.error("세션 데이터 수신 실패")
                        #             continue
                        #     except Exception as e:
                        #         logger.error(f"조인 실패: {e}", exc_info=True)
                        #         continue
                        
                        # 멀티플레이 세션 설정 완료 후 플레이어 재할당 UI 표시
                        if session and local_player_id:
                            logger.info(f"멀티플레이 세션 설정 완료: session={session.session_id}, local_player_id={local_player_id}")
                            from src.ui.multiplayer_character_reassignment_ui import show_character_reassignment
                            
                            # 현재 접속한 플레이어 목록 생성
                            current_players = []
                            if hasattr(session, 'players') and session.players:
                                logger.info(f"세션 플레이어 수: {len(session.players)}")
                                for pid, player in session.players.items():
                                    if player:
                                        current_players.append({
                                            "player_id": pid,
                                            "player_name": getattr(player, 'player_name', '플레이어')
                                        })
                                        logger.debug(f"플레이어 추가: {pid} ({getattr(player, 'player_name', '플레이어')})")
                            
                            # 플레이어가 없으면 로컬 플레이어만 추가 (호스트만 있는 경우)
                            if not current_players and local_player:
                                logger.info(f"플레이어 목록이 비어있음 - 로컬 플레이어 추가: {local_player_id}")
                                current_players.append({
                                    "player_id": local_player_id,
                                    "player_name": getattr(local_player, 'player_name', '호스트')
                                })
                            
                            logger.info(f"재할당 UI 표시 준비: {len(current_players)}명 플레이어, {len(loaded_state.get('party', []))}명 캐릭터")
                            
                            # 재할당 UI 표시 (파티 복원 전에 표시)
                            if current_players:
                                assignments = show_character_reassignment(
                                    display.console,
                                    display.context,
                                    loaded_state.get("party", []),  # 불러온 캐릭터 정보 (player_id 포함)
                                    current_players
                                )
                                
                                if assignments:
                                    logger.info(f"플레이어 재할당 완료: {len(assignments)}명 플레이어에게 할당")
                            
                            # 봇 할당 UI 제거됨
                                    continue
                            else:
                                logger.error("재할당할 플레이어가 없습니다 - 세션 설정 문제 가능성")
                                # 플레이어가 없어도 계속 진행 (싱글플레이처럼)
                                assignments = {}
                        else:
                            logger.warning(f"멀티플레이 세션 설정 실패: session={session is not None}, local_player_id={local_player_id is not None}")
                            assignments = {}
                    
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

                    # 파티 복원 (player_id 포함, 멀티플레이 재할당 적용)
                    try:
                        loaded_party_data = loaded_state.get("party", [])
                        
                        # 멀티플레이: 재할당 결과를 먼저 적용한 후 파티 복원
                        if is_multiplayer_load and assignments:
                            # 재할당 결과를 불러온 파티 데이터에 적용
                            for player_id, character_indices in assignments.items():
                                for char_idx in character_indices:
                                    if char_idx < len(loaded_party_data):
                                        loaded_party_data[char_idx]["player_id"] = player_id
                                        logger.debug(
                                            f"캐릭터 데이터 재할당: {loaded_party_data[char_idx].get('name', 'Unknown')} -> "
                                            f"플레이어 {player_id}"
                                        )
                        
                        # 파티 복원
                        party = [deserialize_party_member(member_data) for member_data in loaded_party_data]
                        logger.info(f"파티 복원 완료: {len(party)}명 (멀티플레이: {is_multiplayer_load})")
                        
                        # 멀티플레이: 재할당된 player_id 확인
                        if is_multiplayer_load:
                            for char in party:
                                if hasattr(char, 'player_id') and char.player_id:
                                    logger.debug(f"{char.name}의 player_id: {char.player_id}")
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

                    # 게임 통계 초기화 (불러온 게임용)
                    game_stats = {
                        "enemies_defeated": loaded_state.get("enemies_defeated", 0),
                        "max_floor_reached": loaded_state.get("max_floor_reached", floor_number),
                        "total_gold_earned": loaded_state.get("total_gold_earned", 0),
                        "total_exp_earned": loaded_state.get("total_exp_earned", 0),
                        "save_slot": loaded_state.get("save_slot", None)
                    }

                    # 탐험 시스템 초기화 (멀티플레이/싱글플레이 구분)
                    if is_multiplayer_load and session and network_manager and local_player_id:
                        # 멀티플레이 탐험 시스템
                        from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                        exploration = MultiplayerExplorationSystem(
                            dungeon=dungeon,
                            party=party,  # Character 객체 리스트
                            floor_number=floor_number,
                            inventory=inventory,
                            game_stats=game_stats,  # 게임 통계 전달
                            session=session,
                            network_manager=network_manager,
                            local_player_id=local_player_id
                        )
                        exploration.player.x = player_pos["x"]
                        exploration.player.y = player_pos["y"]
                        
                        # 로컬 플레이어 위치 설정
                        if local_player:
                            local_player.x = player_pos["x"]
                            local_player.y = player_pos["y"]
                            local_player.party = party  # 로컬 플레이어의 파티 설정
                        
                        logger.info(f"멀티플레이 탐험 시스템 생성 완료 (is_multiplayer={exploration.is_multiplayer})")
                        
                        # 세션에 exploration 설정
                        if session:
                            session.exploration = exploration
                            logger.info("세션에 탐험 시스템 설정 완료")
                    else:
                        # 싱글플레이 탐험 시스템
                        exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                        exploration.player.x = player_pos["x"]
                        exploration.player.y = player_pos["y"]
                        logger.info("싱글플레이 탐험 시스템 생성 완료")

                    # 적 복원
                    exploration.enemies = enemies
                    
                    # 키 복원
                    exploration.player_keys = loaded_state.get("keys", [])
                    
                    # BGM 제어 플래그 (첫 탐험 시작 및 층 변경 시에만 재생)
                    play_dungeon_bgm = True

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
                            
                            # 파티 설정 (싱글플레이 또는 멀티플레이)
                            # 멀티플레이: 전투 데이터에서 참여자 가져오기
                            if is_multiplayer and data and isinstance(data, dict):
                                if "participants" in data:
                                    combat_party = data["participants"]  # 참여자로 교체
                                else:
                                    # participants가 없으면 exploration.player.party 사용
                                    if hasattr(exploration, 'player') and hasattr(exploration.player, 'party'):
                                        combat_party = exploration.player.party
                                    else:
                                        combat_party = []
                                if "position" in data:
                                    combat_position = data["position"]
                            else:
                                # 싱글플레이: exploration의 player.party 사용 (가장 확실한 방법)
                                if hasattr(exploration, 'player') and hasattr(exploration.player, 'party'):
                                    combat_party = exploration.player.party
                                else:
                                    # player.party가 없으면 상위 스코프의 party 변수 사용 시도
                                    try:
                                        # 상위 스코프에서 party 변수 확인
                                        combat_party = party if 'party' in locals() and party is not None else []
                                    except NameError:
                                        combat_party = []
                                
                                if not combat_party or combat_party is None:
                                    logger.error("싱글플레이 전투: 파티를 찾을 수 없습니다. 빈 리스트 사용")
                                    combat_party = []
                            
                            # 파티가 None이거나 빈 리스트이면 오류
                            if combat_party is None:
                                logger.error("싱글플레이 전투: 파티가 None입니다. exploration.player.party 사용 시도")
                                if hasattr(exploration, 'player') and hasattr(exploration.player, 'party'):
                                    combat_party = exploration.player.party or []
                                else:
                                    logger.error("exploration.player.party도 없습니다. 빈 리스트 사용")
                                    combat_party = []
                            
                            # 파티를 전투용 변수에 할당 (None 체크)
                            party = combat_party if combat_party is not None else []
                            
                            combat_result = run_combat(
                                display.console,
                                display.context,
                                party,
                                enemies,
                                inventory=inventory,
                                session=session_for_combat,
                                network_manager=network_manager_for_combat,
                                combat_position=combat_position,
                                local_player_id=local_player_id
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

                                # 전투 후 복귀 시 필드 BGM 재생
                                from src.audio import play_bgm
                                if hasattr(exploration, 'is_town') and exploration.is_town:
                                    # 마을인 경우 마을 BGM 재생
                                    play_bgm("town", loop=True, fade_in=True)
                                else:
                                    # 던전인 경우 바이옴별 BGM 재생
                                    floor = exploration.floor_number
                                    biome_index = (floor - 1) % 10
                                    biome_track = f"biome_{biome_index}"
                                    play_bgm(biome_track)
                                play_dungeon_bgm = True
                                continue
                            elif combat_result == CombatState.DEFEAT:
                                # 전투 참여 파티원만 죽었는지, 모든 플레이어의 모든 캐릭터가 죽었는지 확인
                                is_game_over = getattr(combat_manager, 'is_game_over', False)
                                
                                if is_game_over:
                                    # 모든 플레이어의 모든 캐릭터가 죽었으면 게임오버
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
                                    # 전투 참여 파티원만 죽었으면 패배 (맵으로 복귀)
                                    logger.info("❌ 패배... 맵으로 복귀")
                                    
                                    # 전투 패배 후 복귀 시 필드 BGM 재생
                                    from src.audio import play_bgm
                                    if hasattr(exploration, 'is_town') and exploration.is_town:
                                        # 마을인 경우 마을 BGM 재생
                                        play_bgm("town", loop=True, fade_in=True)
                                    else:
                                        # 던전인 경우 바이옴별 BGM 재생
                                        floor = exploration.floor_number
                                        biome_index = (floor - 1) % 10
                                        biome_track = f"biome_{biome_index}"
                                        play_bgm(biome_track)
                                    play_dungeon_bgm = True
                                    continue
                            else:
                                logger.info("🏃 도망쳤다")
                                # 도망 후 복귀 시 필드 BGM 재생
                                from src.audio import play_bgm
                                if hasattr(exploration, 'is_town') and exploration.is_town:
                                    # 마을인 경우 마을 BGM 재생
                                    play_bgm("town", loop=True, fade_in=True)
                                else:
                                    # 던전인 경우 바이옴별 BGM 재생
                                    floor = exploration.floor_number
                                    biome_index = (floor - 1) % 10
                                    biome_track = f"biome_{biome_index}"
                                    play_bgm(biome_track)
                                play_dungeon_bgm = True
                                continue

                        elif result == "floor_down":
                            # 마을(0층)에서 나가면 다음 던전으로 이동
                            if floor_number == 0:
                                # 마을 상태 저장
                                floors_dungeons[floor_number] = {
                                    "dungeon": exploration.dungeon,
                                    "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                    "player_x": exploration.player.x,
                                    "player_y": exploration.player.y
                                }
                                
                                # 다음 던전 번호로 이동
                                next_dungeon_floor = game_stats.get("next_dungeon_floor", 1)
                                floor_number = next_dungeon_floor
                                exploration.game_stats["max_floor_reached"] = max(exploration.game_stats["max_floor_reached"], floor_number)
                                logger.info(f"⬇ 마을에서 던전 {floor_number}층으로 이동 (멀티플레이)")
                                
                                # 던전 생성 (기존 던전이 있으면 재사용, 없으면 생성)
                                if floor_number in floors_dungeons:
                                    floor_data = floors_dungeons[floor_number]
                                    dungeon = floor_data["dungeon"]
                                    if isinstance(dungeon, tuple):
                                        dungeon, saved_enemies = dungeon
                                    else:
                                        saved_enemies = floor_data["enemies"]
                                    saved_x = floor_data["player_x"]
                                    saved_y = floor_data["player_y"]
                                    logger.info(f"기존 {floor_number}층 던전 재사용 (적 {len(saved_enemies)}마리)")
                                else:
                                    from src.world.dungeon_generator import DungeonGenerator
                                    dungeon_seed = session.generate_dungeon_seed_for_floor(floor_number)
                                    dungeon_gen = DungeonGenerator(width=80, height=50)
                                    dungeon = dungeon_gen.generate(floor_number, seed=dungeon_seed)
                                    saved_enemies = []
                                    saved_x = None
                                    saved_y = None
                                    logger.info(f"새 {floor_number}층 던전 생성 (시드: {dungeon_seed})")
                                
                                # 기존 파티 가져오기 (exploration.player.party 사용)
                                current_party = None
                                if hasattr(exploration, 'player') and hasattr(exploration.player, 'party'):
                                    current_party = exploration.player.party
                                elif hasattr(exploration, 'party'):
                                    current_party = exploration.party
                                
                                if not current_party:
                                    # 파티를 찾을 수 없으면 스코프에서 가져오기 시도
                                    logger.warning("파티를 찾을 수 없습니다. 스코프에서 가져오기 시도")
                                    if 'party_members' in locals() and party_members:
                                        current_party = party_members
                                    else:
                                        logger.error("파티를 찾을 수 없습니다. exploration.player.party 확인 필요")
                                        current_party = []
                                
                                from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                                exploration = MultiplayerExplorationSystem(
                                    dungeon=dungeon,
                                    party=current_party,  # 기존 파티 재사용
                                    floor_number=floor_number,
                                    inventory=inventory,
                                    game_stats=game_stats,
                                    session=session,
                                    network_manager=network_manager,
                                    local_player_id=local_player_id
                                )
                                if saved_enemies:
                                    exploration.enemies = saved_enemies
                                if saved_x is not None and saved_y is not None:
                                    exploration.player.x = saved_x
                                    exploration.player.y = saved_y
                                
                                # 마을 플래그 제거
                                if hasattr(exploration, 'is_town'):
                                    delattr(exploration, 'is_town')
                                
                                # network_manager 업데이트 (멀티플레이어 모드에서만)
                                if network_manager:
                                    network_manager.current_floor = floor_number
                                    network_manager.current_dungeon = dungeon
                                    network_manager.current_exploration = exploration
                                # 싱글플레이 모드에서는 network_manager가 None이므로 업데이트 건너뜀
                                play_dungeon_bgm = True
                                continue
                            else:
                                # 던전에서 내려가는 계단을 밟으면 마을로 복귀하고 다음 던전 번호 증가
                                # 현재 층 상태 저장
                                floors_dungeons[floor_number] = {
                                    "dungeon": exploration.dungeon,
                                    "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                    "player_x": exploration.player.x,
                                    "player_y": exploration.player.y
                                }
                                
                                # 기존 파티 가져오기 (exploration.player.party 사용)
                                current_party = None
                                if hasattr(exploration, 'player') and hasattr(exploration.player, 'party'):
                                    current_party = exploration.player.party
                                elif hasattr(exploration, 'party'):
                                    current_party = exploration.party
                                
                                if not current_party:
                                    # 파티를 찾을 수 없으면 스코프에서 가져오기 시도
                                    logger.warning("파티를 찾을 수 없습니다. 스코프에서 가져오기 시도")
                                    if 'party_members' in locals() and party_members:
                                        current_party = party_members
                                    else:
                                        logger.error("파티를 찾을 수 없습니다. exploration.player.party 확인 필요")
                                        current_party = []
                                
                                # 기존 network_manager 가져오기 (스코프에서 가져오기)
                                # 멀티플레이어 모드에서만 network_manager가 필요함
                                current_network_manager = network_manager
                                if not current_network_manager:
                                    # exploration에서 가져오기 시도
                                    current_network_manager = getattr(exploration, 'network_manager', None) if hasattr(exploration, 'network_manager') else None
                                
                                # network_manager가 None이어도 게임 계속 진행 (싱글플레이 모드 지원)
                                # 멀티플레이어 모드에서만 network_manager 업데이트
                                if not current_network_manager:
                                    logger.warning("network_manager가 None입니다. 싱글플레이 모드이거나 멀티플레이어 연결이 끊어진 상태입니다.")
                                
                                # 마을로 복귀
                                floor_number = 0
                                # 다음 던전 번호 증가
                                current_dungeon = game_stats.get("next_dungeon_floor", 1)
                                game_stats["next_dungeon_floor"] = current_dungeon + 1
                                logger.info(f"던전 클리어! 마을로 복귀. 다음 던전: {game_stats['next_dungeon_floor']}층 (멀티플레이)")
                                
                                # 마을 맵 재사용
                                if floor_number in floors_dungeons:
                                    floor_data = floors_dungeons[floor_number]
                                    dungeon = floor_data["dungeon"]
                                    if isinstance(dungeon, tuple):
                                        dungeon, saved_enemies = dungeon
                                    else:
                                        saved_enemies = floor_data.get("enemies", [])
                                    saved_x = floor_data.get("player_x")
                                    saved_y = floor_data.get("player_y")
                                    logger.info(f"기존 마을 맵 재사용")
                                else:
                                    # 각 플레이어마다 자신의 마을 맵 생성 (멀티플레이)
                                    from src.town.town_map import TownMap, create_town_dungeon_map
                                    from src.town.town_manager import TownManager
                                    # 로컬 플레이어의 마을 맵 생성 (각 플레이어는 자신의 마을을 가짐)
                                    town_map_local = TownMap()  # 전역 인스턴스 대신 새 인스턴스 생성
                                    town_manager_local = TownManager()
                                    dungeon = create_town_dungeon_map(town_map_local)
                                    saved_enemies = []
                                    saved_x = None
                                    saved_y = None
                                    logger.info(f"새 마을 맵 생성 (멀티플레이, 플레이어 {local_player_id})")
                                
                                from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                                exploration = MultiplayerExplorationSystem(
                                    dungeon=dungeon,
                                    party=current_party,  # 기존 파티 재사용
                                    floor_number=floor_number,
                                    inventory=inventory,
                                    game_stats=game_stats,
                                    session=session,
                                    network_manager=network_manager,
                                    local_player_id=local_player_id
                                )
                                # 마을 플레이어 스폰 위치 설정
                                if saved_x is not None and saved_y is not None:
                                    exploration.player.x = saved_x
                                    exploration.player.y = saved_y
                                else:
                                    # 로컬 플레이어의 마을 맵 사용
                                    if 'town_map_local' not in locals():
                                        from src.town.town_map import TownMap
                                        town_map_local = TownMap()
                                    spawn_x, spawn_y = town_map_local.player_spawn
                                    exploration.player.x = spawn_x
                                    exploration.player.y = spawn_y
                                
                                # 마을 표시 플래그 추가
                                if 'town_map_local' not in locals():
                                    from src.town.town_map import TownMap
                                    from src.town.town_manager import TownManager
                                    town_map_local = TownMap()
                                    town_manager_local = TownManager()
                                exploration.is_town = True
                                exploration.town_map = town_map_local
                                exploration.town_manager = town_manager_local
                                
                                # 마을에서는 적 제거
                                exploration.enemies = []
                                
                                # network_manager 업데이트 (멀티플레이어 모드에서만)
                                if current_network_manager:
                                    current_network_manager.current_floor = floor_number
                                    current_network_manager.current_dungeon = dungeon
                                    current_network_manager.current_exploration = exploration
                                # 싱글플레이 모드에서는 network_manager가 None이므로 업데이트 건너뜀
                                
                                # 마을 BGM 재생을 위해 플래그 설정
                                play_dungeon_bgm = True
                                continue
                        elif result == "floor_up":
                            if floor_number == 1:
                                # 던전 1층에서 위로 올라가면 마을(0층)로 복귀
                                # 현재 층 상태 저장
                                floors_dungeons[floor_number] = {
                                    "dungeon": exploration.dungeon,
                                    "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                    "player_x": exploration.player.x,
                                    "player_y": exploration.player.y
                                }
                                
                                # 마을로 복귀
                                floor_number = 0
                                logger.info(f"⬆ 던전에서 마을로 복귀 (멀티플레이)")
                                
                                # 마을 맵 재사용
                                if floor_number in floors_dungeons:
                                    floor_data = floors_dungeons[floor_number]
                                    dungeon = floor_data["dungeon"]
                                    if isinstance(dungeon, tuple):
                                        dungeon, saved_enemies = dungeon
                                    else:
                                        saved_enemies = floor_data.get("enemies", [])
                                    saved_x = floor_data.get("player_x")
                                    saved_y = floor_data.get("player_y")
                                    logger.info(f"기존 마을 맵 재사용")
                                else:
                                    # 각 플레이어마다 자신의 마을 맵 생성 (멀티플레이)
                                    from src.town.town_map import TownMap, create_town_dungeon_map
                                    from src.town.town_manager import TownManager
                                    # 로컬 플레이어의 마을 맵 생성 (각 플레이어는 자신의 마을을 가짐)
                                    town_map_local = TownMap()  # 전역 인스턴스 대신 새 인스턴스 생성
                                    town_manager_local = TownManager()
                                    dungeon = create_town_dungeon_map(town_map_local)
                                    saved_enemies = []
                                    saved_x = None
                                    saved_y = None
                                    logger.info(f"새 마을 맵 생성 (멀티플레이, 플레이어 {local_player_id})")
                                
                                # 기존 파티 가져오기 (exploration.player.party 사용)
                                current_party = None
                                if hasattr(exploration, 'player') and hasattr(exploration.player, 'party'):
                                    current_party = exploration.player.party
                                elif hasattr(exploration, 'party'):
                                    current_party = exploration.party
                                
                                if not current_party:
                                    # 파티를 찾을 수 없으면 스코프에서 가져오기 시도
                                    logger.warning("파티를 찾을 수 없습니다. 스코프에서 가져오기 시도")
                                    if 'party_members' in locals() and party_members:
                                        current_party = party_members
                                    else:
                                        logger.error("파티를 찾을 수 없습니다. exploration.player.party 확인 필요")
                                        current_party = []
                                
                                # 기존 network_manager 가져오기 (스코프에서 가져오기)
                                # 멀티플레이어 모드에서만 network_manager가 필요함
                                current_network_manager = network_manager
                                if not current_network_manager:
                                    # exploration에서 가져오기 시도
                                    current_network_manager = getattr(exploration, 'network_manager', None) if hasattr(exploration, 'network_manager') else None
                                
                                # network_manager가 None이어도 게임 계속 진행 (싱글플레이 모드 지원)
                                if not current_network_manager:
                                    logger.warning("network_manager가 None입니다. 싱글플레이 모드이거나 멀티플레이어 연결이 끊어진 상태입니다.")
                                
                                from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
                                exploration = MultiplayerExplorationSystem(
                                    dungeon=dungeon,
                                    party=current_party,  # 기존 파티 재사용
                                    floor_number=floor_number,
                                    inventory=inventory,
                                    game_stats=game_stats,
                                    session=session,
                                    network_manager=current_network_manager,  # 기존 network_manager 재사용
                                    local_player_id=local_player_id
                                )
                                # 마을 플레이어 스폰 위치 설정
                                if saved_x is not None and saved_y is not None:
                                    exploration.player.x = saved_x
                                    exploration.player.y = saved_y
                                else:
                                    # 로컬 플레이어의 마을 맵 사용
                                    if 'town_map_local' not in locals():
                                        from src.town.town_map import TownMap
                                        town_map_local = TownMap()
                                    spawn_x, spawn_y = town_map_local.player_spawn
                                    exploration.player.x = spawn_x
                                    exploration.player.y = spawn_y
                                
                                # 마을 표시 플래그 추가
                                if 'town_map_local' not in locals():
                                    from src.town.town_map import TownMap
                                    from src.town.town_manager import TownManager
                                    town_map_local = TownMap()
                                    town_manager_local = TownManager()
                                exploration.is_town = True
                                exploration.town_map = town_map_local
                                exploration.town_manager = town_manager_local
                                
                                # network_manager 업데이트 (멀티플레이어 모드에서만)
                                if current_network_manager:
                                    current_network_manager.current_floor = floor_number
                                    current_network_manager.current_dungeon = dungeon
                                    current_network_manager.current_exploration = exploration
                                # 싱글플레이 모드에서는 network_manager가 None이므로 업데이트 건너뜀
                                
                                play_dungeon_bgm = True
                                continue
                            elif floor_number > 1:
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
                    
                    # 시작 장비 지급 (대장간 레벨에 따라 등급 결정)
                    UpgradeApplier.give_starting_equipment(character_party, meta_progress=host_meta, is_host=is_host)
                    logger.info("시작 장비 지급 완료")

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

                    # 게임 시작은 마을(floor 0)에서 시작
                    floor_number = 0

                    # 게임 통계 초기화
                    game_stats = {
                        "enemies_defeated": 0,
                        "max_floor_reached": 0,
                        "total_gold_earned": 0,
                        "total_exp_earned": 0,
                        "save_slot": None,
                        "next_dungeon_floor": 1  # 다음 던전 번호 (0->1->0->2->0->3...)
                    }

                    # 마을 맵 생성 및 던전 맵으로 변환
                    from src.town.town_map import get_town_map, create_town_dungeon_map
                    from src.town.town_manager import TownManager
                    from src.town.floor_transition import get_floor_transition_manager
                    
                    # 마을 관련 객체 전역 저장 (층 이동 시 재사용)
                    town_map = get_town_map()
                    town_manager = TownManager()
                    dungeon = create_town_dungeon_map(town_map)
                    
                    # 탐험 시스템 초기화 (마을)
                    exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                    # 마을 플레이어 스폰 위치 설정
                    spawn_x, spawn_y = town_map.player_spawn
                    exploration.player.x = spawn_x
                    exploration.player.y = spawn_y
                    
                    # 마을 표시 플래그 추가
                    exploration.is_town = True
                    exploration.town_map = town_map
                    exploration.town_manager = town_manager
                    
                    # FloorTransitionManager 초기화
                    floor_transition = get_floor_transition_manager("single_player")
                    floor_transition.current_floor = 0

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
                    
                    # 싱글플레이 모드: local_player_id는 None
                    local_player_id = None

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
                                        combat_position=combat_position,
                                        local_player_id=local_player_id
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

                                        # 전투 후 복귀 시 필드 BGM 재생
                                        from src.audio import play_bgm
                                        if hasattr(exploration, 'is_town') and exploration.is_town:
                                            # 마을인 경우 마을 BGM 재생
                                            play_bgm("town", loop=True, fade_in=True)
                                        else:
                                            # 던전인 경우 바이옴별 BGM 재생
                                            floor = exploration.floor_number
                                            biome_index = (floor - 1) % 10
                                            biome_track = f"biome_{biome_index}"
                                            play_bgm(biome_track)
                                        play_dungeon_bgm = True
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
                                        # 도망 후 복귀 시 필드 BGM 재생
                                        from src.audio import play_bgm
                                        if hasattr(exploration, 'is_town') and exploration.is_town:
                                            # 마을인 경우 마을 BGM 재생
                                            play_bgm("town", loop=True, fade_in=True)
                                        else:
                                            # 던전인 경우 바이옴별 BGM 재생
                                            floor = exploration.floor_number
                                            biome_index = (floor - 1) % 10
                                            biome_track = f"biome_{biome_index}"
                                            play_bgm(biome_track)
                                        play_dungeon_bgm = True
                                        continue

                                elif result == "floor_down":
                                    # 마을(0층)에서 나가면 다음 던전으로 이동
                                    if floor_number == 0:
                                        # 마을 상태 저장
                                        floors_dungeons[floor_number] = {
                                            "dungeon": exploration.dungeon,
                                            "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                            "player_x": exploration.player.x,
                                            "player_y": exploration.player.y
                                        }
                                        
                                        # 다음 던전 번호로 이동
                                        next_dungeon_floor = game_stats.get("next_dungeon_floor", 1)
                                        floor_number = next_dungeon_floor
                                        exploration.game_stats["max_floor_reached"] = max(exploration.game_stats["max_floor_reached"], floor_number)
                                        logger.info(f"⬇ 마을에서 던전 {floor_number}층으로 이동")
                                        
                                        # 던전 생성 (기존 던전이 있으면 재사용, 없으면 생성)
                                        if floor_number in floors_dungeons:
                                            floor_data = floors_dungeons[floor_number]
                                            dungeon = floor_data["dungeon"]
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
                                        if saved_enemies:
                                            exploration.enemies = saved_enemies
                                        if saved_x is not None and saved_y is not None:
                                            exploration.player.x = saved_x
                                            exploration.player.y = saved_y
                                        
                                        # 마을 플래그 제거
                                        if hasattr(exploration, 'is_town'):
                                            delattr(exploration, 'is_town')
                                        
                                        play_dungeon_bgm = True
                                        continue
                                    else:
                                        # 던전에서 내려가는 계단을 밟으면 마을로 복귀하고 다음 던전 번호 증가
                                        # 현재 층 상태 저장
                                        floors_dungeons[floor_number] = {
                                            "dungeon": exploration.dungeon,
                                            "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                            "player_x": exploration.player.x,
                                            "player_y": exploration.player.y
                                        }
                                        
                                        # 마을로 복귀
                                        floor_number = 0
                                        # 다음 던전 번호 증가
                                        current_dungeon = game_stats.get("next_dungeon_floor", 1)
                                        game_stats["next_dungeon_floor"] = current_dungeon + 1
                                        logger.info(f"던전 클리어! 마을로 복귀. 다음 던전: {game_stats['next_dungeon_floor']}층")
                                        
                                        # 마을 맵 재사용
                                        if floor_number in floors_dungeons:
                                            floor_data = floors_dungeons[floor_number]
                                            dungeon = floor_data["dungeon"]
                                            if isinstance(dungeon, tuple):
                                                dungeon, saved_enemies = dungeon
                                            else:
                                                saved_enemies = floor_data.get("enemies", [])
                                            saved_x = floor_data.get("player_x")
                                            saved_y = floor_data.get("player_y")
                                            logger.info(f"기존 마을 맵 재사용")
                                        else:
                                            # 마을 맵 생성
                                            from src.town.town_map import get_town_map, create_town_dungeon_map
                                            from src.town.town_manager import TownManager
                                            town_map_local = get_town_map()
                                            town_manager_local = TownManager()
                                            dungeon = create_town_dungeon_map(town_map_local)
                                            saved_enemies = []
                                            saved_x = None
                                            saved_y = None
                                            logger.info(f"새 마을 맵 생성")
                                        
                                        exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                        # 마을 플레이어 스폰 위치 설정
                                        if saved_x is not None and saved_y is not None:
                                            exploration.player.x = saved_x
                                            exploration.player.y = saved_y
                                        else:
                                            # town_map이 없으면 가져오기
                                            if 'town_map' not in locals():
                                                from src.town.town_map import get_town_map
                                                town_map = get_town_map()
                                            spawn_x, spawn_y = town_map.player_spawn
                                            exploration.player.x = spawn_x
                                            exploration.player.y = spawn_y
                                        
                                        # 마을 표시 플래그 추가
                                        exploration.is_town = True
                                        exploration.town_map = town_map
                                        exploration.town_manager = town_manager
                                        
                                        play_dungeon_bgm = True
                                        continue
                                        
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
                                    if floor_number == 1:
                                        # 던전 1층에서 위로 올라가면 마을(0층)로 복귀
                                        # 현재 층 상태 저장
                                        floors_dungeons[floor_number] = {
                                            "dungeon": exploration.dungeon,
                                            "enemies": exploration.enemies.copy() if hasattr(exploration, 'enemies') else [],
                                            "player_x": exploration.player.x,
                                            "player_y": exploration.player.y
                                        }
                                        
                                        # 마을로 복귀
                                        floor_number = 0
                                        logger.info(f"⬆ 던전에서 마을로 복귀")
                                        
                                        # 마을 맵 재사용
                                        if floor_number in floors_dungeons:
                                            floor_data = floors_dungeons[floor_number]
                                            dungeon = floor_data["dungeon"]
                                            if isinstance(dungeon, tuple):
                                                dungeon, saved_enemies = dungeon
                                            else:
                                                saved_enemies = floor_data.get("enemies", [])
                                            saved_x = floor_data.get("player_x")
                                            saved_y = floor_data.get("player_y")
                                            logger.info(f"기존 마을 맵 재사용")
                                        else:
                                            # 마을 맵 생성
                                            from src.town.town_map import get_town_map, create_town_dungeon_map
                                            from src.town.town_manager import TownManager
                                            town_map_local = get_town_map()
                                            town_manager_local = TownManager()
                                            dungeon = create_town_dungeon_map(town_map_local)
                                            saved_enemies = []
                                            saved_x = None
                                            saved_y = None
                                            logger.info(f"새 마을 맵 생성")
                                        
                                        exploration = ExplorationSystem(dungeon, party, floor_number, inventory, game_stats)
                                        # 마을 플레이어 스폰 위치 설정
                                        if saved_x is not None and saved_y is not None:
                                            exploration.player.x = saved_x
                                            exploration.player.y = saved_y
                                        else:
                                            # 마을 맵 스폰 위치 사용
                                            town_map_local = get_town_map()
                                            spawn_x, spawn_y = town_map_local.player_spawn
                                            exploration.player.x = spawn_x
                                            exploration.player.y = spawn_y
                                        
                                        # 마을 표시 플래그 추가
                                        from src.town.town_map import get_town_map
                                        from src.town.town_manager import TownManager
                                        exploration.is_town = True
                                        exploration.town_map = get_town_map()
                                        exploration.town_manager = TownManager()
                                        
                                        play_dungeon_bgm = True
                                        continue
                                    elif floor_number > 1:
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
