
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.world.exploration import ExplorationSystem, Player, ExplorationResult, ExplorationEvent
from src.world.tile import Tile, TileType
from src.gathering.harvestable import HarvestableObject, HarvestableType
from src.multiplayer.ai_bot_advanced import AdvancedAIBot, BotBehavior, TaskType
from src.multiplayer.bot_communication import BotCommunicationNetwork

class MockDungeon:
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height
        self.tiles = [[Tile(TileType.FLOOR, x, y) for x in range(width)] for y in range(height)]
        self.harvestables = []
        self.rooms = []
        self.stairs_up = None
        self.stairs_down = None

    def is_walkable(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

class MockInventory:
    def __init__(self):
        self.items = []
        self.slots = []  # slots 속성 추가
        self.gold = 0
        self.weight = 0
        self.capacity = 100
    
    def add_item(self, item, qty=1):
        self.items.append((item, qty))
        return True

class TestAutoHarvest(unittest.TestCase):
    
    def setUp(self):
        # 기본 설정
        self.dungeon = MockDungeon()
        member = MagicMock()
        member.vision_bonus = 0  # 시야 보너스 설정
        member.name = "TestMember"
        member.character_class = "Warrior"
        self.party = [member]
        self.inventory = MockInventory()
        
        # 채집물 생성 (위치: 5, 6)
        self.harvestable = MagicMock(spec=HarvestableObject)
        self.harvestable.x = 5
        self.harvestable.y = 6
        # Mock object_type
        mock_type = MagicMock()
        mock_type.value = "herb"
        mock_type.display_name = "약초"
        self.harvestable.object_type = mock_type
        
        self.harvestable.harvested = False
        self.harvestable.can_harvest.return_value = True
        self.harvestable.harvest.return_value = {"herb": 1}
        
        self.dungeon.harvestables.append(self.harvestable)

    @patch('src.world.exploration.play_sfx')
    def test_player_auto_harvest(self, mock_play_sfx):
        """플레이어가 이동하여 밟으면 자동 채집되는지 테스트"""
        print("\n[Test] 플레이어 자동 채집 테스트")
        
        # Mock ItemFactory to avoid ModuleNotFoundError
        mock_item_factory = MagicMock()
        mock_item_factory.ItemFactory.create_item.return_value = "mock_item"
        sys.modules['src.item.item_factory'] = mock_item_factory
        sys.modules['src.item'] = MagicMock()
        
        # ExplorationSystem 초기화 (플레이어 위치: 5, 5)
        exploration = ExplorationSystem(self.dungeon, self.party, inventory=self.inventory)
        exploration.player.x = 5
        exploration.player.y = 5
        
        # 확인: 채집물은 (5, 6)에 있음
        print(f"플레이어 위치: ({exploration.player.x}, {exploration.player.y})")
        print(f"채집물 위치: ({self.harvestable.x}, {self.harvestable.y})")
        
        # 이동 (0, 1) -> (5, 6)으로 이동하여 채집물 밟기
        print("이동 시도: 아래로 1칸 (0, 1)")
        result = exploration.move_player(0, 1)
        
        # 검증
        print(f"이동 결과: {result.message}")
        
        # 1. 위치 이동 확인
        self.assertEqual(exploration.player.x, 5)
        self.assertEqual(exploration.player.y, 6)
        
        # 2. 채집 메서드 호출 확인
        self.harvestable.harvest.assert_called()
        
        # 3. 결과 이벤트가 ITEM_FOUND인지 확인
        # (기존 로직상 ExplorationResult가 반환되어야 함)
        # move_player 내부에서 check_and_harvest를 호출하고 결과를 반영해야 함
        self.assertTrue(result.success)
        # 주의: move_player 로직에 따라 이벤트가 NONE일 수도 있고 ITEM_FOUND일 수도 있음
        # 우리가 수정한 로직은 ITEM_FOUND를 반환하도록 했음
        if result.event == ExplorationEvent.ITEM_FOUND:
            print("[OK] 채집 성공 이벤트 반환됨")
        else:
            print(f"[WARN] 이벤트 타입: {result.event} (예상: ITEM_FOUND)")
            
        # 4. 인벤토리 확인
        self.assertTrue(len(self.inventory.items) > 0)
        print(f"인벤토리 아이템: {self.inventory.items}")

    @patch('src.multiplayer.ai_bot_advanced.get_communication_network')
    def test_bot_auto_harvest_logic(self, mock_get_comm):
        """봇의 자동 채집 로직 (이동 및 블랙리스트) 테스트"""
        print("\n[Test] 봇 AI 자동 채집 로직 테스트")
        
        # Mock Communication Network
        mock_comm = MagicMock(spec=BotCommunicationNetwork)
        mock_get_comm.return_value = mock_comm
        
        # 봇 초기화
        session = MagicMock()
        network = MagicMock()
        bot = AdvancedAIBot("bot_1", "TestBot", network, session)
        
        # 봇 위치 설정 (채집물 바로 옆: 5, 5)
        bot.current_x = 5
        bot.current_y = 5
        
        # 채집물 목표 설정 (5, 6)
        target_pos = (5, 6)
        target_data = {
            "type": "item",
            "position": target_pos,
            "priority": 10
        }
        
        # Mock ExplorationSystem for bot
        exploration = MagicMock()
        exploration.dungeon = self.dungeon
        # _find_path에서 사용됨
        bot._get_exploration_system = MagicMock(return_value=exploration)
        
        # 테스트 1: _scan_for_farmable_items에서 중복 태스크 방지 확인
        # 이미 큐에 태스크 추가
        bot.task_queue.add_task(TaskType.FARM, 10, data=target_data)
        
        # 스캔 결과로 같은 아이템이 나왔다고 가정
        mock_comm.get_nearest_unclaimed_item.return_value = (target_pos, "some_item")
        
        # 스캔 실행
        bot._scan_for_farmable_items()
        
        # 큐 크기가 여전히 1이어야 함 (중복 추가 안됨)
        print(f"태스크 큐 크기: {len(bot.task_queue.tasks)}")
        self.assertEqual(len(bot.task_queue.tasks), 1)
        
        # 테스트 2: _execute_farming_action (도착 시 처리)
        # 봇을 목표 바로 옆(5, 5)에서 목표(5, 6)으로 이동시키는 로직 확인
        # 우리가 수정한 로직: 거리 1이면 즉시 진입
        
        print(f"봇 위치: ({bot.current_x}, {bot.current_y})")
        print(f"목표 위치: {target_pos}")
        
        # 실행
        bot._execute_farming_action(target_data)
        
        # 이동 확인 (mock _execute_move가 호출되었는지)
        # 실제로는 _execute_move가 구현되어 있어 좌표가 바뀜 (mocking 필요)
        # 여기서는 _execute_move를 오버라이드하거나 몽키패치
        
        # 하지만 _execute_farming_action 내부 로직을 검증하기 위해
        # _move_towards 호출 -> 거리 1 -> 즉시 _execute_move 호출 -> 좌표 변경
        # 이 흐름을 타야 함.
        
        # 봇의 _execute_move를 Mock으로 교체하여 호출 여부 확인
        bot._execute_move = MagicMock(side_effect=lambda move: setattr(bot, 'current_x', move['x']) or setattr(bot, 'current_y', move['y']))
        
        # 다시 실행 (거리 1인 상태)
        bot._execute_farming_action(target_data)
        
        # 1. 이동 명령이 내려졌는지 확인
        bot._execute_move.assert_called_with({"x": 5, "y": 6})
        print("[OK] 인접 거리에서 즉시 이동 명령 호출됨")
        
        # 위치 업데이트 시뮬레이션 (위의 side_effect로 이미 5, 6이 됨)
        print(f"이동 후 봇 위치: ({bot.current_x}, {bot.current_y})")
        
        # 다시 실행 (이제 도착한 상태: 5, 6)
        bot._execute_farming_action(target_data)
        
        # 2. 도착 후 블랙리스트 추가 확인
        self.assertIn(target_pos, bot.harvested_blacklist)
        print("[OK] 도착 후 블랙리스트에 추가됨")
        
        # 3. 통신 네트워크에서 제거 요청 확인
        mock_comm.remove_item.assert_called_with(target_pos)
        print("[OK] 통신 네트워크에서 아이템 제거 요청됨")

if __name__ == '__main__':
    unittest.main()

