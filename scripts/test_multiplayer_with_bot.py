"""
멀티플레이어 AI 봇 테스트 스크립트

실제 게임 파일을 사용하여 멀티플레이어 테스트를 수행합니다.
호스트와 클라이언트를 시뮬레이션하고 AI 봇을 추가하여 테스트합니다.
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
from src.multiplayer.ai_bot import BotManager, BotBehavior, AIBot
from src.multiplayer.protocol import MessageType, MessageBuilder
from src.core.logger import get_logger
from uuid import uuid4

logger = get_logger("test.bot")


async def test_host_with_bot():
    """호스트 모드에서 봇 테스트"""
    logger.info("=== 호스트 모드 봇 테스트 시작 ===")
    
    # 세션 생성
    session = MultiplayerSession(max_players=4)
    local_player_id = str(uuid4())[:8]
    session.host_id = local_player_id
    session.local_player_id = local_player_id
    
    # 호스트 네트워크 매니저 생성
    network_manager = HostNetworkManager(
        session=session,
        local_player_id=local_player_id
    )
    
    try:
        # 서버 시작
        await network_manager.start_server(port=8765)
        logger.info("호스트 서버 시작: 포트 8765")
        
        # 봇 관리자 생성
        bot_manager = BotManager(network_manager, session)
        
        # 봇 추가 (다양한 행동 패턴)
        bot1 = bot_manager.add_bot(
            bot_id=str(uuid4())[:8],
            bot_name="탐험가 봇",
            behavior=BotBehavior.EXPLORER
        )
        bot2 = bot_manager.add_bot(
            bot_id=str(uuid4())[:8],
            bot_name="공격적 봇",
            behavior=BotBehavior.AGGRESSIVE
        )
        bot3 = bot_manager.add_bot(
            bot_id=str(uuid4())[:8],
            bot_name="랜덤 봇",
            behavior=BotBehavior.RANDOM
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
        
        # 테스트 실행 (30초)
        start_time = time.time()
        test_duration = 30.0
        
        while time.time() - start_time < test_duration:
            current_time = time.time()
            bot_manager.update(current_time)
            await asyncio.sleep(0.1)
        
        # 봇 중지
        bot_manager.stop_all()
        logger.info("봇 테스트 완료")
        
    except Exception as e:
        logger.error(f"호스트 봇 테스트 오류: {e}", exc_info=True)
    finally:
        await network_manager.disconnect()
        logger.info("호스트 서버 종료")


async def test_client_with_bot():
    """클라이언트 모드에서 봇 테스트"""
    logger.info("=== 클라이언트 모드 봇 테스트 시작 ===")
    
    # 세션 생성
    session = MultiplayerSession(max_players=4)
    local_player_id = str(uuid4())[:8]
    session.local_player_id = local_player_id
    
    # 클라이언트 네트워크 매니저 생성
    network_manager = ClientNetworkManager(
        session=session,
        local_player_id=local_player_id
    )
    
    try:
        # 호스트에 연결
        await network_manager.connect("localhost", 8765)
        logger.info("호스트에 연결됨")
        
        # 봇 관리자 생성
        bot_manager = BotManager(network_manager, session)
        
        # 봇 추가
        bot = bot_manager.add_bot(
            bot_id=local_player_id,
            bot_name="클라이언트 봇",
            behavior=BotBehavior.EXPLORER
        )
        
        # 봇 시작
        bot_manager.start_all()
        
        logger.info("클라이언트 봇 시작됨")
        
        # 테스트 실행 (30초)
        start_time = time.time()
        test_duration = 30.0
        
        while time.time() - start_time < test_duration:
            current_time = time.time()
            bot_manager.update(current_time)
            await asyncio.sleep(0.1)
        
        # 봇 중지
        bot_manager.stop_all()
        logger.info("클라이언트 봇 테스트 완료")
        
    except Exception as e:
        logger.error(f"클라이언트 봇 테스트 오류: {e}", exc_info=True)
    finally:
        await network_manager.disconnect()
        logger.info("클라이언트 연결 종료")


async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="멀티플레이어 AI 봇 테스트")
    parser.add_argument(
        "--mode",
        choices=["host", "client"],
        default="host",
        help="테스트 모드 (host 또는 client)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "host":
        await test_host_with_bot()
    else:
        await test_client_with_bot()


if __name__ == "__main__":
    asyncio.run(main())

