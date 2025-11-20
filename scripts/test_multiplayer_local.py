#!/usr/bin/env python3
"""
로컬 멀티플레이 테스트 스크립트

혼자서 멀티플레이를 테스트할 수 있는 간단한 스크립트입니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.multiplayer.test_helper import create_test_session, MultiplayerTestHelper
from src.core.logger import get_logger, Loggers

logger = get_logger(Loggers.SYSTEM)


async def test_multiplayer_with_bots():
    """봇과 함께 멀티플레이 테스트"""
    print("=" * 60)
    print("멀티플레이 테스트 시작 (봇 사용)")
    print("=" * 60)
    
    # 4인 세션 생성 (호스트 1명 + 봇 3명)
    session, helper = create_test_session(player_count=4)
    
    print(f"\n[OK] 세션 생성 완료: {len(session.players)}명")
    print(f"   - 호스트: {session.host_id}")
    print(f"   - 봇: {len(helper.mock_clients)}명")
    
    # 플레이어 목록 출력
    print("\n[INFO] 플레이어 목록:")
    for player_id, player in session.players.items():
        marker = "[HOST]" if player.is_host else "[BOT]"
        print(f"   {marker} {player.player_name} (ID: {player_id[:8]}...)")
        print(f"      위치: ({player.x}, {player.y})")
    
    # 자동 시뮬레이션 시작
    print("\n[START] 자동 시뮬레이션 시작 (5초간)...")
    await helper.start_auto_simulation(interval=1.0)
    
    try:
        # 5초 동안 시뮬레이션 실행
        for i in range(5):
            await asyncio.sleep(1.0)
            
            # 현재 위치 출력
            positions = helper.get_player_positions()
            print(f"\n[TIME] {i+1}초 경과:")
            for player_id, (x, y) in positions.items():
                player = session.players[player_id]
                marker = "[HOST]" if player.is_host else "[BOT]"
                print(f"   {marker} {player.player_name}: ({x}, {y})")
        
        # 최종 위치 출력
        print("\n[OK] 시뮬레이션 완료")
        final_positions = helper.get_player_positions()
        print("\n[FINAL] 최종 위치:")
        for player_id, (x, y) in final_positions.items():
            player = session.players[player_id]
            marker = "[HOST]" if player.is_host else "[BOT]"
            print(f"   {marker} {player.player_name}: ({x}, {y})")
    
    finally:
        # 정리
        await helper.stop_auto_simulation()
        print("\n[STOP] 시뮬레이션 중지됨")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


def main():
    """메인 함수"""
    try:
        asyncio.run(test_multiplayer_with_bots())
    except KeyboardInterrupt:
        print("\n\n[WARN] 테스트 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

