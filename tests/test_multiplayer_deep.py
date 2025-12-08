
import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import time

from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.combat_sync import CombatSyncManager
from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder
from src.combat.combat_manager import CombatManager, ActionType

class TestMultiplayerDeep(unittest.IsolatedAsyncioTestCase):
    """멀티플레이 심층 테스트 및 버그 수정 검증"""

    async def asyncSetUp(self):
        # 기본 세션 설정
        self.session = MultiplayerSession(max_players=4)
        self.host_player = MultiplayerPlayer("host", "Host Player")
        self.client_player1 = MultiplayerPlayer("client1", "Client 1")
        self.client_player2 = MultiplayerPlayer("client2", "Client 2")
        
        self.session.add_player(self.host_player)
        self.session.add_player(self.client_player1)
        self.session.add_player(self.client_player2)
        
        # 네트워크 관리자 Mock
        self.mock_network = MagicMock(spec=NetworkManager)
        self.mock_network.send = AsyncMock()
        self.mock_network.broadcast = AsyncMock()
        self.mock_network.is_host = True
        
        # 전투 관리자 Mock
        self.mock_combat_manager = MagicMock(spec=CombatManager)
        self.mock_combat_manager.allies = []
        self.mock_combat_manager.enemies = []
        
        # 던전 Mock 설정
        self.dungeon = MagicMock()
        self.dungeon.width = 100
        self.dungeon.height = 100
        self.dungeon.is_walkable.return_value = True
        self.dungeon.is_town = False
        self.dungeon.harvestables = []
        
        # 방 정보 Mock
        room = MagicMock()
        room.x = 10
        room.y = 10
        room.width = 10
        room.height = 10
        room.x1 = 10
        room.x2 = 20
        room.y1 = 10
        room.y2 = 20
        self.dungeon.rooms = [room]
        
        # 계단 위치 설정
        self.dungeon.stairs_up = (11, 11)
        self.dungeon.stairs_down = (18, 18)
        
        # 타일 Mock
        from src.world.tile import TileType
        tile = MagicMock()
        tile.tile_type = TileType.FLOOR
        self.dungeon.get_tile.return_value = tile
        
        # ExplorationSystem 초기화 시 EnemyGenerator를 사용하므로 이를 patch
        with patch('src.world.enemy_generator.EnemyGenerator.generate_boss'), \
             patch('src.world.exploration.ExplorationSystem._spawn_enemies'):
            
            self.exploration = MultiplayerExplorationSystem(
                dungeon=self.dungeon,
                party=[],
                session=self.session,
                network_manager=self.mock_network,
                local_player_id="host"
            )
        
        self.exploration.register_active_combat = MagicMock()
        self.exploration.game_mode_manager = MagicMock()
        
    async def test_host_migration_notification(self):
        """
        검증: 호스트 이탈 시 새로운 호스트 정보가 클라이언트에게 전파되어야 함
        (참고: session.remove_player 자체는 브로드캐스트를 하지 않으므로, 
         이 로직은 NetworkManager 통합 테스트에서 더 정확히 검증 가능하지만,
         여기서는 session 로직이 올바른 리턴값을 주는지 확인)
        """
        # 현재 호스트 확인
        self.assertEqual(self.session.host_id, "host")
        
        # 호스트 제거 (세션 로직)
        success, new_host_id = self.session.remove_player("host")
        
        # 제거 성공 및 새 호스트 ID 반환 확인
        self.assertTrue(success)
        self.assertIsNotNone(new_host_id)
        self.assertNotEqual(new_host_id, "host")
        self.assertIn(new_host_id, ["client1", "client2"])
        
        # 세션 내부 상태 확인
        self.assertEqual(self.session.host_id, new_host_id)
        
    async def test_combat_start_synchronization_fix(self):
        """
        검증: 클라이언트에서 적과 조우 시 직접 전투를 시작하지 않고 호스트에게 요청을 보내야 함
        """
        # 클라이언트 탐험 시스템 설정
        client_network = MagicMock(spec=NetworkManager)
        client_network.is_host = False
        client_network.send = AsyncMock()
        
        with patch('src.world.exploration.ExplorationSystem._spawn_enemies'):
            client_exploration = MultiplayerExplorationSystem(
                dungeon=self.dungeon,
                party=[],
                session=self.session,
                network_manager=client_network,
                local_player_id="client1"
            )
        
        # 적 설정
        enemy = MagicMock()
        enemy.x = 10
        enemy.y = 10
        enemy.id = "enemy1"
        
        # 클라이언트 위치 설정
        self.client_player1.x = 10
        self.client_player1.y = 10
        
        # ExplorationResult Mock
        mock_result = MagicMock()
        
        with patch('src.world.exploration.ExplorationSystem._trigger_combat_with_enemy', return_value=mock_result) as mock_super_trigger:
            # 적과 조우
            client_exploration._trigger_combat_with_enemy(enemy)
            
            # 검증:
            # 1. 부모 클래스의 _trigger_combat_with_enemy는 호출되지 않아야 함 (로컬 전투 시작 방지)
            mock_super_trigger.assert_not_called()
            
            # 2. 호스트에게 메시지를 보내야 함
            client_network.send.assert_called_once()
            
            # 3. 메시지 내용 확인
            args, _ = client_network.send.call_args
            message = args[0]
            self.assertEqual(message.type, MessageType.REQUEST_COMBAT_START)
            self.assertEqual(message.data["enemy_id"], "enemy1")

    async def test_action_timeout_logic(self):
        """
        검증: 액션 요청 시 타임아웃 태스크가 시작되어야 함
        """
        client_network = MagicMock(spec=NetworkManager)
        client_network.is_host = False
        client_network.send = AsyncMock()
        
        sync_manager = CombatSyncManager(
            session=self.session,
            network_manager=client_network,
            is_host=False
        )
        
        # 액터 설정
        actor = MagicMock()
        actor.id = "actor1"
        sync_manager._get_character_id = MagicMock(return_value="actor1")
        sync_manager._set_player_selecting = MagicMock()
        sync_manager._serialize_action = MagicMock(return_value={})
        
        # start_timeout_task 메서드 Mocking (실제 비동기 태스크 생성 여부 확인용)
        with patch.object(sync_manager, '_start_timeout_task') as mock_start_timeout:
            # 액션 요청
            await sync_manager.send_action_request(
                player_id="client1",
                actor=actor,
                action_type=ActionType.BRV_ATTACK
            )
            
            # 검증:
            # 1. 네트워크 전송
            client_network.send.assert_called_once()
            
            # 2. UI 잠금
            sync_manager._set_player_selecting.assert_called_with("client1", True)
            
            # 3. 타임아웃 태스크 시작
            mock_start_timeout.assert_called_once_with("client1")

    async def test_movement_sync_rollback_handler(self):
        """
        검증: 이동 롤백(거절) 메시지를 처리하는 핸들러가 등록되어야 함
        """
        client_network = MagicMock(spec=NetworkManager)
        client_network.is_host = False
        client_network.send = AsyncMock()
        
        with patch('src.world.exploration.ExplorationSystem._spawn_enemies'):
            client_exploration = MultiplayerExplorationSystem(
                dungeon=self.dungeon,
                party=[],
                session=self.session,
                network_manager=client_network,
                local_player_id="client1"
            )
        
        # 등록된 핸들러 목록 확인
        handlers = client_network.register_handler.call_args_list
        registered_types = [args[0] for args, _ in handlers]
        
        # 검증: MOVEMENT_REJECTED 핸들러가 등록되어 있어야 함
        self.assertIn(MessageType.MOVEMENT_REJECTED, registered_types)
        
        # 롤백 로직 테스트
        # MOVEMENT_REJECTED 메시지 수신 시 롤백 함수 호출 확인은
        # NetworkManager의 _handle_message 로직에 의존하므로 
        # 여기서는 핸들러 등록 여부만 확인하거나, 
        # NetworkManager를 통해 메시지를 주입하여 테스트할 수 있음.
        
        # 간단히 rollback_player_position 메서드가 존재하는지 확인
        self.assertTrue(hasattr(client_exploration, 'rollback_player_position'))
