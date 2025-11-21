"""
고급 AI 봇 테스트 스크립트

실제 게임 파일을 사용하여 고급 AI 봇의 모든 기능을 테스트합니다.
- 자동 직업/특성/패시브 선택
- 자동 전투
- 명령 시스템
- 탐험 AI
"""

import sys
import os
import time
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.ai_bot_advanced import AdvancedBotManager, AdvancedAIBot, BotBehavior
from src.multiplayer.protocol import MessageType, MessageBuilder
from src.core.logger import get_logger
from src.core.config import initialize_config
from uuid import uuid4

logger = get_logger("test.advanced_bot")


async def test_bot_party_setup():
    """봇의 파티 설정 기능 테스트"""
    logger.info("=== 봇 파티 설정 테스트 ===")
    
    # 세션 생성
    session = MultiplayerSession(max_players=4)
    host_id = str(uuid4())[:8]
    session.host_id = host_id
    session.local_player_id = host_id
    
    # 호스트 네트워크 매니저 생성
    network_manager = HostNetworkManager(
        port=8765,
        session=session
    )
    network_manager.player_id = host_id
    
    try:
        # 서버 시작
        await network_manager.start_server()
        logger.info(f"호스트 서버 시작: 포트 {network_manager.port}")
        
        # 봇 관리자 생성
        bot_manager = AdvancedBotManager(
            network_manager=network_manager,
            session=session,
            auto_fill=True,
            min_players=2
        )
        
        # 봇 추가 (다양한 행동 패턴)
        bot1 = bot_manager.add_bot(
            bot_id=str(uuid4())[:8],
            bot_name="탐험가 봇",
            behavior=BotBehavior.EXPLORER,
            is_host=False
        )
        bot2 = bot_manager.add_bot(
            bot_id=str(uuid4())[:8],
            bot_name="공격적 봇",
            behavior=BotBehavior.AGGRESSIVE,
            is_host=False
        )
        bot3 = bot_manager.add_bot(
            bot_id=str(uuid4())[:8],
            bot_name="서포터 봇",
            behavior=BotBehavior.SUPPORT,
            is_host=False
        )
        
        # 봇들을 세션에 추가
        from src.multiplayer.player import MultiplayerPlayer
        for bot in bot_manager.get_all_bots():
            player = MultiplayerPlayer(
                player_id=bot.bot_id,
                player_name=bot.bot_name,
                x=0,
                y=0,
                party=[],
                is_host=False
            )
            session.add_player(player)
        
        # 봇 시작
        bot_manager.start_all()
        logger.info(f"{len(bot_manager.get_all_bots())}개의 봇 시작됨")
        
        # 봇의 자동 직업 선택 테스트
        logger.info("\n=== 자동 직업 선택 테스트 ===")
        available_jobs = ["warrior", "knight", "archer", "cleric", "rogue", "archmage"]
        selected_by_others = set()
        
        for bot in bot_manager.get_all_bots():
            selected_job = bot.auto_select_job(available_jobs, selected_by_others)
            if selected_job:
                logger.info(f"{bot.bot_name}: {selected_job} 선택")
                selected_by_others.add(selected_job)
        
        # 봇의 자동 특성 선택 테스트
        logger.info("\n=== 자동 특성 선택 테스트 ===")
        for bot in bot_manager.get_all_bots():
            if selected_by_others:
                job_id = list(selected_by_others)[0]  # 첫 번째 선택된 직업 사용
                traits = bot.auto_select_traits(job_id)
                logger.info(f"{bot.bot_name}: {job_id} 특성 {len(traits)}개 선택")
        
        # 봇의 자동 패시브 선택 테스트 (호스트만)
        logger.info("\n=== 자동 패시브 선택 테스트 ===")
        host_bot = bot_manager.add_bot(
            bot_id=host_id,
            bot_name="호스트 봇",
            behavior=BotBehavior.EXPLORER,
            is_host=True
        )
        if host_bot.is_host:
            passives = host_bot.auto_select_passives(max_cost=10)
            logger.info(f"{host_bot.bot_name}: 패시브 {len(passives)}개 선택")
        
        # 난이도 자동 선택 테스트
        logger.info("\n=== 난이도 자동 선택 테스트 ===")
        difficulty = bot_manager.auto_select_difficulty()
        logger.info(f"자동 선택된 난이도: {difficulty}")
        
        logger.info("\n[SUCCESS] 파티 설정 테스트 완료")
        
    except Exception as e:
        logger.error(f"파티 설정 테스트 오류: {e}", exc_info=True)
    finally:
        if hasattr(network_manager, 'stop_server'):
            await network_manager.stop_server()
        elif hasattr(network_manager, 'server') and network_manager.server:
            network_manager.server.close()
            await network_manager.server.wait_closed()
        logger.info("호스트 서버 종료")


async def test_bot_combat():
    """봇의 전투 기능 테스트"""
    logger.info("\n=== 봇 전투 테스트 ===")
    
    # 간단한 전투 시뮬레이션
    from src.character.character import Character
    from src.combat.combat_manager import CombatManager
    
    # 테스트 캐릭터 생성
    ally1 = Character("봇 캐릭터 1", "warrior", level=5)
    ally2 = Character("봇 캐릭터 2", "cleric", level=5)
    enemy1 = Character("적 1", "warrior", level=3)
    enemy1.is_enemy = True
    enemy2 = Character("적 2", "rogue", level=3)
    enemy2.is_enemy = True
    
    # 전투 관리자 생성
    combat_manager = CombatManager()
    combat_manager.start_combat([ally1, ally2], [enemy1, enemy2])
    
    # 봇 생성 (테스트용)
    session = MultiplayerSession(max_players=4)
    network_manager = HostNetworkManager(port=8767, session=session)
    network_manager.player_id = "test"
    bot = AdvancedAIBot(
        bot_id="test_bot",
        bot_name="전투 테스트 봇",
        network_manager=network_manager,
        session=session,
        behavior=BotBehavior.AGGRESSIVE
    )
    bot.set_combat_manager(combat_manager)
    
    # 봇의 자동 전투 액션 테스트
    logger.info("봇 자동 전투 액션 테스트:")
    for i in range(3):
        action = bot.auto_combat_action(
            actor=ally1,
            allies=[ally1, ally2],
            enemies=[enemy1, enemy2]
        )
        if action:
            logger.info(f"턴 {i+1}: {action.get('type', 'unknown')} - 대상: {getattr(action.get('target'), 'name', 'None')}")
        else:
            logger.info(f"턴 {i+1}: 액션 없음")
    
    logger.info("[SUCCESS] 전투 테스트 완료")


async def test_bot_commands():
    """봇의 명령 시스템 테스트"""
    logger.info("\n=== 봇 명령 시스템 테스트 ===")
    
    session = MultiplayerSession(max_players=4)
    network_manager = HostNetworkManager(port=8768, session=session)
    network_manager.player_id = "test"
    bot = AdvancedAIBot(
        bot_id="test_bot",
        bot_name="명령 테스트 봇",
        network_manager=network_manager,
        session=session,
        behavior=BotBehavior.EXPLORER
    )
    
    # 숫자 키 명령 테스트
    command_keys = ['1', '2', '3', '4', '5', '6', '7']
    logger.info("숫자 키 명령 테스트:")
    for key in command_keys:
        result = bot.handle_command_key(key)
        if result:
            logger.info(f"키 {key}: 명령 처리됨")
        else:
            logger.info(f"키 {key}: 명령 없음")
    
    logger.info("[SUCCESS] 명령 시스템 테스트 완료")


async def test_bot_exploration():
    """봇의 탐험 AI 테스트"""
    logger.info("\n=== 봇 탐험 AI 테스트 ===")
    
    session = MultiplayerSession(max_players=4)
    network_manager = HostNetworkManager(port=8769, session=session)
    network_manager.player_id = "test"
    bot = AdvancedAIBot(
        bot_id="test_bot",
        bot_name="탐험 테스트 봇",
        network_manager=network_manager,
        session=session,
        behavior=BotBehavior.EXPLORER
    )
    
    # 초기 위치 설정
    bot.current_x = 10
    bot.current_y = 10
    
    # 탐험 이동 테스트
    logger.info("탐험 이동 테스트 (10회):")
    for i in range(10):
        action = bot._decide_action()
        if action and action.get("type") == "move":
            logger.info(f"이동 {i+1}: ({action.get('x')}, {action.get('y')})")
            bot.current_x = action.get('x', bot.current_x)
            bot.current_y = action.get('y', bot.current_y)
    
    logger.info("[SUCCESS] 탐험 AI 테스트 완료")


async def test_bot_auto_fill():
    """봇 자동 채우기 테스트"""
    logger.info("\n=== 봇 자동 채우기 테스트 ===")
    
    session = MultiplayerSession(max_players=4)
    host_id = str(uuid4())[:8]
    session.host_id = host_id
    session.local_player_id = host_id
    
    network_manager = HostNetworkManager(
        port=8766,
        session=session
    )
    network_manager.player_id = host_id
    
    try:
        await network_manager.start_server()
        logger.info(f"호스트 서버 시작: 포트 {network_manager.port}")
        
        # 봇 관리자 생성 (자동 채우기 활성화)
        bot_manager = AdvancedBotManager(
            network_manager=network_manager,
            session=session,
            auto_fill=True,
            min_players=2
        )
        
        # 세션에 플레이어 추가 (1명만)
        from src.multiplayer.player import MultiplayerPlayer
        player = MultiplayerPlayer(
            player_id=host_id,
            player_name="호스트",
            x=0,
            y=0,
            party=[],
            is_host=True
        )
        session.add_player(player)
        
        logger.info(f"현재 플레이어 수: {len(session.players)}")
        logger.info(f"최소 플레이어 수: {bot_manager.min_players}")
        
        # 자동 채우기 체크 (수동으로 시뮬레이션)
        current_time = time.time()
        bot_manager.update(current_time)
        
        logger.info(f"자동 채우기 후 플레이어 수: {len(session.players)}")
        logger.info(f"봇 수: {len(bot_manager.bots)}")
        
        logger.info("[SUCCESS] 자동 채우기 테스트 완료")
        
    except Exception as e:
        logger.error(f"자동 채우기 테스트 오류: {e}", exc_info=True)
    finally:
        if hasattr(network_manager, 'stop_server'):
            await network_manager.stop_server()
        elif hasattr(network_manager, 'server') and network_manager.server:
            network_manager.server.close()
            await network_manager.server.wait_closed()


async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="고급 AI 봇 테스트")
    parser.add_argument(
        "--test",
        choices=["all", "party", "combat", "commands", "exploration", "autofill"],
        default="all",
        help="실행할 테스트"
    )
    
    args = parser.parse_args()
    
    # 설정 초기화
    initialize_config()
    
    try:
        if args.test == "all" or args.test == "party":
            await test_bot_party_setup()
            await asyncio.sleep(1)
        
        if args.test == "all" or args.test == "combat":
            await test_bot_combat()
            await asyncio.sleep(1)
        
        if args.test == "all" or args.test == "commands":
            await test_bot_commands()
            await asyncio.sleep(1)
        
        if args.test == "all" or args.test == "exploration":
            await test_bot_exploration()
            await asyncio.sleep(1)
        
        if args.test == "all" or args.test == "autofill":
            await test_bot_auto_fill()
        
        logger.info("\n" + "="*60)
        logger.info("[SUCCESS] 모든 테스트 완료!")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\n테스트 중단됨")
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

