"""
고급 AI 봇 시스템 테스트 스크립트
"""

import sys
import os
import time
from unittest.mock import MagicMock

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.multiplayer.ai_bot_advanced import AdvancedAIBot, BotBehavior, BotCommand
from src.multiplayer.bot_tasks import TaskType
from src.multiplayer.network import NetworkManager
from src.multiplayer.session import MultiplayerSession

class MockDungeon:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height
        self.tiles = [[MagicMock() for _ in range(height)] for _ in range(width)]
        self.rooms = []
        self.stairs_down = None
        self.stairs_up = None
        self.harvestables = []
        
    def is_walkable(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height
        
    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[x][y]
        return None

class MockExploration:
    def __init__(self):
        self.dungeon = MockDungeon()
        self.local_player_id = "player1"
        self.enemies = []
        
    def get_enemy_at(self, x, y):
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                return enemy
        return None
        
    def handle_interaction(self, x, y, bot_id):
        print(f"[System] {bot_id} interaction at ({x}, {y})")

class MockHarvestable:
    def __init__(self, x, y, name="TestItem"):
        self.x = x
        self.y = y
        self.object_type = MagicMock()
        self.object_type.display_name = name
        
    def can_harvest(self, bot_id):
        return True
        
    def harvest(self, bot_id):
        print(f"[System] Harvested by {bot_id}")
        return [MagicMock(name="Herb")]

def test_bot_logic():
    print("=== 고급 AI 봇 테스트 시작 ===")
    
    # 1. 봇 초기화
    network_manager = MagicMock(spec=NetworkManager)
    network_manager.is_host = False # Mock에 is_host 속성 추가
    session = MagicMock(spec=MultiplayerSession)
    session.players = {}
    
    bot = AdvancedAIBot("bot1", "Bot-Alpha", network_manager, session)
    
    # Mock Exploration 시스템 주입 (get_exploration_system 메서드 모킹)
    mock_exploration = MockExploration()
    bot._get_exploration_system = MagicMock(return_value=mock_exploration)
    
    # 초기 위치 설정
    bot.current_x = 5
    bot.current_y = 5
    bot.start()
    print(f"1. 봇 시작 위치: ({bot.current_x}, {bot.current_y})")
    
    # 2. 채집 테스트
    print("\n--- 채집 테스트 ---")
    # (5, 7) 위치에 채집물 배치 (2칸 거리)
    harvestable = MockHarvestable(5, 7, "Rare Herb")
    mock_exploration.dungeon.harvestables.append(harvestable) # harvestables에 추가
    
    # 통신 네트워크에 채집물 정보 주입
    bot.communication.share_item_location("system", (5, 7), harvestable)
    
    # 봇 업데이트 (스캔 -> 태스크 생성)
    print(">> Update 1: 스캔 및 태스크 생성")
    bot.update(time.time())
    
    # 태스크 큐 확인
    if bot.task_queue.tasks:
        print(f"   태스크 생성됨: {bot.task_queue.tasks[0]}")
    else:
        print("   태스크 생성 실패!")
        
    # 봇 업데이트 (이동)
    print(">> Update 2: 이동 시작")
    bot.update(time.time() + 0.5)
    print(f"   현재 위치: ({bot.current_x}, {bot.current_y})") # (5, 6) 예상
    
    # 봇 업데이트 (도착 및 채집 시작)
    print(">> Update 3: 도착 및 채집 시도")
    bot.update(time.time() + 1.0)
    print(f"   현재 위치: ({bot.current_x}, {bot.current_y})") # (5, 6) 유지 (거리 1)
    
    # 채집 시퀀스 진행 (Z키 3번)
    print(">> Update 4~6: 채집 시퀀스 진행")
    for i in range(3):
        bot.update(time.time() + 1.5 + (i * 0.6))
        
    # 블랙리스트 확인
    if (5, 7) in bot.harvested_blacklist:
        print("   SUCCESS: 채집물이 블랙리스트에 추가됨")
    else:
        print("   FAIL: 채집물이 블랙리스트에 없음")
        
    # 3. 서성임 방지 테스트 (회피 이동)
    print("\n--- 서성임 방지 테스트 ---")
    print(f"   채집 직후 위치: ({bot.current_x}, {bot.current_y})")
    
    # 추가 업데이트로 이동 확인
    bot.update(time.time() + 5.0)
    print(f"   회피 이동 후 위치: ({bot.current_x}, {bot.current_y})")
    
    if (bot.current_x, bot.current_y) != (5, 6):
        print("   SUCCESS: 봇이 채집 위치를 떠남")
    else:
        print("   FAIL: 봇이 제자리에 있음")

    # 4. 전투 테스트
    print("\n--- 전투 테스트 ---")
    bot.in_combat = True
    print("   전투 모드 활성화")
    
    # 이동 명령 시도
    prev_x, prev_y = bot.current_x, bot.current_y
    bot._execute_move({"x": bot.current_x + 1, "y": bot.current_y})
    
    if bot.current_x == prev_x and bot.current_y == prev_y:
        print("   SUCCESS: 전투 중 이동 차단됨")
    else:
        print(f"   FAIL: 전투 중 이동함 ({prev_x}, {prev_y} -> {bot.current_x}, {bot.current_y})")

    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_bot_logic()
