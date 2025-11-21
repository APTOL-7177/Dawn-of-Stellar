"""
멀티플레이 탐험 시스템

개별 캐릭터 이동 및 동기화를 관리합니다.
"""

from typing import List, Dict, Optional, Tuple, Any
import time

from src.world.exploration import ExplorationSystem, Player, Enemy
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
from src.multiplayer.config import MultiplayerConfig
from src.multiplayer.game_mode import get_game_mode_manager
from src.multiplayer.movement_sync import MovementSyncManager
from src.multiplayer.enemy_sync import EnemySyncManager
from src.multiplayer.combat_join import CombatJoinHandler
from src.core.logger import get_logger


class MultiplayerExplorationSystem(ExplorationSystem):
    """멀티플레이 탐험 시스템"""
    
    def __init__(
        self,
        dungeon,
        party: List[Any],
        floor_number: int = 1,
        inventory=None,
        game_stats=None,
        session: Optional[MultiplayerSession] = None,
        network_manager: Optional[NetworkManager] = None,
        local_player_id: Optional[str] = None
    ):
        """
        초기화
        
        Args:
            dungeon: 던전 맵
            party: 파티 (싱글플레이 호환성을 위해 유지)
            floor_number: 층 번호
            inventory: 인벤토리
            game_stats: 게임 통계
            session: 멀티플레이 세션
            network_manager: 네트워크 관리자
            local_player_id: 로컬 플레이어 ID
        """
        # 부모 클래스 초기화 (싱글플레이용 기본값 사용)
        # 멀티플레이에서는 실제로 Player 객체는 사용하지 않음
        super().__init__(dungeon, party, floor_number, inventory, game_stats)
        
        self.logger = get_logger("multiplayer.exploration")
        self.session = session
        self.network_manager = network_manager
        self.local_player_id = local_player_id
        
        # 멀티플레이 모드 여부 (세션이 있으면 멀티플레이로 간주)
        self.game_mode_manager = get_game_mode_manager()
        if session:
            # 세션이 제공되면 멀티플레이 모드
            self.is_multiplayer = True
            # 호스트 여부는 세션에서 확인
            self.is_host = (session.host_id is not None and 
                           local_player_id is not None and 
                           session.host_id == local_player_id)
        else:
            # 세션이 없으면 싱글플레이 모드
            self.is_multiplayer = self.game_mode_manager.is_multiplayer() if self.game_mode_manager else False
            self.is_host = getattr(self.game_mode_manager, 'is_host', False) if self.game_mode_manager else False
        
        # 플레이어별 위치 추적
        self.player_positions: Dict[str, Tuple[int, int]] = {}
        
        # 위치 동기화 타이머
        self.last_position_sync = 0.0
        self.position_sync_interval = MultiplayerConfig.SYNC_INTERVAL_POSITION
        
        # 적 이동 타이머 (0.65초 간격)
        self.last_enemy_move = 0.0
        self.enemy_move_interval = 0.65  # 멀티플레이: 0.65초 간격
        
        # 이동 동기화 관리자
        self.movement_sync: Optional[MovementSyncManager] = None
        # 적 동기화 관리자
        self.enemy_sync: Optional[EnemySyncManager] = None
        # 전투 합류 관리자
        self.combat_join_handler: Optional[CombatJoinHandler] = None
        
        # 현재 진행 중인 전투 추적 (전투 관리자 참조)
        self.active_combat_manager: Optional[Any] = None
        self.active_combat_id: Optional[str] = None
        self.active_combat_position: Optional[Tuple[int, int]] = None
        
        if self.is_multiplayer and self.session:
            # 세션의 플레이어들을 초기 위치 설정
            self._initialize_player_positions()
            
            # 로컬 플레이어 위치 동기화 및 FOV 초기화
            if self.local_player_id and self.local_player_id in self.session.players:
                mp_player = self.session.players[self.local_player_id]
                if hasattr(mp_player, 'x') and hasattr(mp_player, 'y'):
                    # 이동 가능한 위치인지 확인
                    if (0 <= mp_player.x < self.dungeon.width and 
                        0 <= mp_player.y < self.dungeon.height and
                        self.dungeon.is_walkable(mp_player.x, mp_player.y)):
                        self.player.x = mp_player.x
                        self.player.y = mp_player.y
                    else:
                        # 이동 불가능한 위치면 기본 위치 사용
                        self.logger.warning(
                            f"로컬 플레이어 초기 위치 ({mp_player.x}, {mp_player.y})가 "
                            f"이동 불가능합니다. 기본 위치로 조정합니다."
                        )
                        # _initialize_player_positions에서 올바른 위치로 설정됨
            
            # FOV 초기 업데이트
            self.update_fov()
            
            # 이동 동기화 관리자 초기화
            if network_manager:
                self.movement_sync = MovementSyncManager(
                    session=session,
                    network_manager=network_manager,
                    is_host=self.is_host
                )
                # exploration 참조 전달 (위치 동기화용)
                self.movement_sync.exploration = self
                if local_player_id:
                    self.movement_sync.set_local_player_id(local_player_id)
                
                # 적 동기화 관리자 초기화
                self.enemy_sync = EnemySyncManager(
                    session=session,
                    network_manager=network_manager,
                    is_host=self.is_host,
                    exploration=self  # exploration 참조 전달
                )
                
                # 전투 합류 관리자 초기화
                self.combat_join_handler = CombatJoinHandler(session=session)
                
                # 전투 이벤트 구독 (멀티플레이 모드에서만)
                self._subscribe_to_combat_events()
                
                # 채집물은 개인보상이므로 동기화 제거
                # self._register_harvest_handler()
                
                # 아이템 획득 동기화 핸들러 등록 (드롭된 아이템은 개인보상이므로 제거)
                # self._register_item_pickup_handler()  # 드롭된 아이템은 개인보상
                
                # NPC 위치 동기화 핸들러 등록
                self._register_npc_move_handler()
                
                # 드롭된 아이템/골드 동기화 핸들러 등록
                self._register_drop_handlers()
    
    def _register_harvest_handler(self):
        """채집 동기화 핸들러 등록"""
        if not self.network_manager:
            return
        
        from src.multiplayer.protocol import MessageType
        
        async def handle_harvest(message, sender_id=None):
            """채집 메시지 처리 (다른 플레이어가 채집했을 때)"""
            try:
                x = message.data.get("x")
                y = message.data.get("y")
                object_type_str = message.data.get("object_type")
                
                if x is None or y is None or not object_type_str:
                    self.logger.warning(f"채집 메시지에 필수 데이터가 없습니다: x={x}, y={y}, object_type={object_type_str}")
                    return
                
                # 해당 위치의 harvestable 찾기
                from src.gathering.harvestable import HarvestableType
                try:
                    object_type = HarvestableType(object_type_str)
                except ValueError:
                    self.logger.warning(f"알 수 없는 채집 타입: {object_type_str}")
                    return
                
                # 던전의 harvestable 목록에서 찾기
                found = False
                for harvestable in self.dungeon.harvestables:
                    if (harvestable.x == x and harvestable.y == y and 
                        harvestable.object_type == object_type):
                        found = True
                        # 이미 채집되었는지 확인 (중복 방지)
                        if not harvestable.harvested:
                            harvestable.harvested = True
                            player_name = getattr(self.session.players.get(sender_id), 'player_name', sender_id) if sender_id and self.session and sender_id in self.session.players else sender_id or "알 수 없음"
                            self.logger.info(f"채집 동기화: {player_name}가 ({x}, {y}) {object_type_str} 채집 - harvested=True")
                        else:
                            self.logger.debug(f"채집 동기화: ({x}, {y}) {object_type_str}는 이미 채집됨")
                        break
                
                if not found:
                    self.logger.warning(f"채집 동기화: ({x}, {y}) {object_type_str}를 찾을 수 없음")
            except Exception as e:
                self.logger.error(f"채집 동기화 처리 실패: {e}", exc_info=True)
        
        self.network_manager.register_handler(MessageType.HARVEST, handle_harvest)
        self.logger.debug("채집 동기화 핸들러 등록 완료")
    
    def _register_item_pickup_handler(self):
        """아이템 획득 동기화 핸들러 등록"""
        if not self.network_manager:
            return
        
        from src.multiplayer.protocol import MessageType
        from src.world.tile import TileType
        
        async def handle_item_pickup(message, sender_id=None):
            """아이템 획득 메시지 처리 (다른 플레이어가 아이템을 주웠을 때)"""
            try:
                x = message.data.get("x")
                y = message.data.get("y")
                
                if x is None or y is None:
                    self.logger.warning(f"아이템 획득 메시지에 필수 데이터가 없습니다: x={x}, y={y}")
                    return
                
                # 해당 위치의 타일 찾기
                if 0 <= x < self.dungeon.width and 0 <= y < self.dungeon.height:
                    tile = self.dungeon.get_tile(x, y)
                    if tile and tile.tile_type == TileType.ITEM:
                        # 아이템 타일을 FLOOR로 변경 (아이템 제거)
                        tile.tile_type = TileType.FLOOR
                        tile.loot_id = None
                        player_name = getattr(self.session.players.get(sender_id), 'player_name', sender_id) if sender_id and self.session and sender_id in self.session.players else sender_id or "알 수 없음"
                        self.logger.info(f"아이템 획득 동기화: {player_name}가 ({x}, {y}) 아이템 획득 - 타일 제거")
                    else:
                        self.logger.debug(f"아이템 획득 동기화: ({x}, {y})는 아이템 타일이 아님 (타입: {tile.tile_type if tile else None})")
                else:
                    self.logger.warning(f"아이템 획득 동기화: ({x}, {y})는 맵 범위를 벗어남")
            except Exception as e:
                self.logger.error(f"아이템 획득 동기화 처리 실패: {e}", exc_info=True)
        
        self.network_manager.register_handler(MessageType.ITEM_PICKED_UP, handle_item_pickup)
        self.logger.debug("아이템 획득 동기화 핸들러 등록 완료")
    
    def _register_npc_move_handler(self):
        """NPC 이동 동기화 핸들러 등록"""
        if not self.network_manager:
            return
        
        from src.multiplayer.protocol import MessageType
        from src.world.tile import TileType
        
        async def handle_npc_move(message, sender_id=None):
            """NPC 이동 메시지 처리 (클라이언트)"""
            try:
                npc_positions = message.data.get("npcs", {})
                
                if not npc_positions:
                    return
                
                # 각 NPC 위치 업데이트
                for npc_id, pos_data in npc_positions.items():
                    old_x = pos_data.get("old_x")
                    old_y = pos_data.get("old_y")
                    new_x = pos_data.get("x")
                    new_y = pos_data.get("y")
                    
                    if old_x is None or old_y is None or new_x is None or new_y is None:
                        continue
                    
                    # 기존 위치의 타일 확인
                    if 0 <= old_x < self.dungeon.width and 0 <= old_y < self.dungeon.height:
                        old_tile = self.dungeon.get_tile(old_x, old_y)
                        if old_tile and old_tile.tile_type == TileType.NPC and old_tile.npc_id == npc_id:
                            # 기존 위치를 FLOOR로 변경
                            self.dungeon.set_tile(old_x, old_y, TileType.FLOOR)
                    
                    # 새 위치에 NPC 배치
                    if 0 <= new_x < self.dungeon.width and 0 <= new_y < self.dungeon.height:
                        new_tile = self.dungeon.get_tile(new_x, new_y)
                        if new_tile and new_tile.tile_type != TileType.NPC:
                            # NPC 정보 가져오기 (기존 타일에서)
                            npc_type = pos_data.get("npc_type")
                            npc_subtype = pos_data.get("npc_subtype")
                            npc_interacted = pos_data.get("npc_interacted", False)
                            
                            self.dungeon.set_tile(
                                new_x, new_y,
                                TileType.NPC,
                                npc_id=npc_id,
                                npc_type=npc_type,
                                npc_subtype=npc_subtype,
                                npc_interacted=npc_interacted
                            )
                            self.logger.debug(f"NPC 이동 동기화: {npc_id} ({old_x}, {old_y}) -> ({new_x}, {new_y})")
            except Exception as e:
                self.logger.error(f"NPC 이동 동기화 처리 실패: {e}", exc_info=True)
        
        self.network_manager.register_handler(MessageType.NPC_MOVE, handle_npc_move)
        self.logger.debug("NPC 이동 동기화 핸들러 등록 완료")
    
    def _subscribe_to_combat_events(self):
        """전투 이벤트 구독 (멀티플레이 전투 합류 시스템용)"""
        try:
            from src.core.event_bus import event_bus, Events
            
            # 전투 시작 이벤트 구독
            event_bus.subscribe(Events.COMBAT_START, self._on_combat_start)
            
            # 전투 종료 이벤트 구독
            event_bus.subscribe(Events.COMBAT_END, self._on_combat_end)
            
            self.logger.info("전투 이벤트 구독 완료 (멀티플레이 합류 시스템)")
        except Exception as e:
            self.logger.error(f"전투 이벤트 구독 실패: {e}", exc_info=True)
    
    def _on_combat_start(self, data: Dict[str, Any]):
        """전투 시작 이벤트 처리"""
        try:
            if not self.is_multiplayer or not self.combat_join_handler:
                return
            
            # 전투 관리자 참조 가져오기
            combat_manager = data.get("combat_manager")
            if not combat_manager:
                self.logger.warning("전투 시작 이벤트에 전투 관리자가 없음")
                return
            
            # 전투 ID 생성 (타임스탬프 기반)
            import time
            combat_id = f"combat_{int(time.time() * 1000)}"
            
            # 전투 위치 (플레이어 위치 또는 이벤트 데이터에서 가져오기)
            position = None
            if hasattr(self, 'player') and hasattr(self.player, 'x') and hasattr(self.player, 'y'):
                position = (self.player.x, self.player.y)
            elif hasattr(self, 'player_positions') and self.local_player_id:
                if self.local_player_id in self.player_positions:
                    position = self.player_positions[self.local_player_id]
            elif hasattr(self, 'player_positions') and self.player_positions:
                # 첫 번째 플레이어 위치 사용
                first_position = next(iter(self.player_positions.values()), None)
                if first_position:
                    position = first_position
            
            if not position:
                # 기본 위치
                position = (0, 0)
                self.logger.warning(f"전투 위치를 찾을 수 없어 기본 위치 사용: {position}")
            
            # 전투 등록
            self.register_active_combat(combat_manager, combat_id, position)
            
            self.logger.info(f"전투 시작 이벤트 처리: {combat_id} at {position}")
        except Exception as e:
            self.logger.error(f"전투 시작 이벤트 처리 실패: {e}", exc_info=True)
    
    def _on_combat_end(self, data: Dict[str, Any]):
        """전투 종료 이벤트 처리"""
        try:
            if not self.is_multiplayer or not self.combat_join_handler:
                return
            
            # 활성 전투 해제
            if self.active_combat_id:
                self.unregister_active_combat(self.active_combat_id)
            
            self.logger.info(f"전투 종료 이벤트 처리: {data.get('state', 'unknown')}")
        except Exception as e:
            self.logger.error(f"전투 종료 이벤트 처리 실패: {e}", exc_info=True)
    
    def _get_nearby_participants(self, combat_position: Tuple[int, int]) -> List[Any]:
        """
        전투 시작 시 근처 아군만 참여 (5타일 반경)
        
        Args:
            combat_position: 전투 시작 위치 (x, y)
            
        Returns:
            참여할 캐릭터 리스트
        """
        try:
            if not self.is_multiplayer or not self.session:
                # 싱글플레이: 기본 파티 사용
                if hasattr(self, 'player') and hasattr(self.player, 'party'):
                    return self.player.party or []
                return []
            
            participation_radius = MultiplayerConfig.participation_radius  # 5 타일
            participants = []
            
            # 모든 플레이어 확인
            for player_id, player in self.session.players.items():
                try:
                    if not player:
                        self.logger.debug(f"플레이어 {player_id}: None")
                        continue
                    
                    # 플레이어 위치 확인
                    if not hasattr(player, 'x') or not hasattr(player, 'y'):
                        self.logger.warning(f"플레이어 {player_id}: 위치 속성 없음")
                        continue
                    
                    try:
                        player_x = int(player.x)
                        player_y = int(player.y)
                    except (ValueError, TypeError, AttributeError):
                        self.logger.warning(f"플레이어 {player_id}의 위치를 읽을 수 없음")
                        continue
                    
                    player_position = (player_x, player_y)
                    
                    # 거리 계산 (맨하탄 거리)
                    distance = abs(player_position[0] - combat_position[0]) + abs(player_position[1] - combat_position[1])
                    
                    self.logger.debug(
                        f"플레이어 {player_id} 체크: 위치=({player_x}, {player_y}), "
                        f"전투 위치={combat_position}, 거리={distance}, "
                        f"파티 있음={hasattr(player, 'party')}, 파티 길이={len(player.party) if hasattr(player, 'party') and player.party else 0}"
                    )
                    
                    # 5타일 반경 내에 있는지 확인
                    if distance <= participation_radius:
                        # 플레이어의 파티 캐릭터 추가
                        if hasattr(player, 'party') and player.party:
                            party_count = 0
                            for character in player.party:
                                if character:
                                    is_alive = getattr(character, 'is_alive', True)
                                    if is_alive:
                                        # 플레이어 ID 설정 (나중에 합류 시 추적용)
                                        try:
                                            character.player_id = player_id
                                        except Exception as e:
                                            # 플레이어 ID 설정 실패 시 로깅만 (속성이 없는 경우 등)
                                            self.logger.debug(f"캐릭터 {getattr(character, 'name', 'Unknown')}에 플레이어 ID 설정 실패: {e}")
                                        participants.append(character)
                                        party_count += 1
                            self.logger.info(
                                f"플레이어 {player_id} 전투 참여: {party_count}명 "
                                f"(거리: {distance}타일, 파티 총 {len(player.party)}명)"
                            )
                        else:
                            self.logger.warning(
                                f"플레이어 {player_id}: 파티 없음 또는 비어있음 "
                                f"(hasattr party={hasattr(player, 'party')}, "
                                f"party={player.party if hasattr(player, 'party') else None})"
                            )
                except Exception as e:
                    self.logger.error(f"플레이어 {player_id} 참여자 수집 실패: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"전투 참여자: {len(participants)}명 (반경: {participation_radius}타일, 총 플레이어: {len(self.session.players)}명)")
            
            # 참여자가 없으면 기본 파티 반환 (싱글플레이 호환성)
            if len(participants) == 0:
                self.logger.warning("전투 참여자가 0명입니다. 기본 파티를 사용합니다.")
                if hasattr(self, 'player') and hasattr(self.player, 'party') and self.player.party:
                    self.logger.info(f"기본 파티 사용: {len(self.player.party)}명")
                    return self.player.party
            
            return participants
        except Exception as e:
            self.logger.error(f"근처 참여자 수집 실패: {e}", exc_info=True)
            # 실패 시 기본 파티 반환
            if hasattr(self, 'player') and hasattr(self.player, 'party'):
                return self.player.party or []
            return []
    
    def _trigger_combat_with_enemy(self, enemy: Any) -> 'ExplorationResult':
        """
        적 엔티티와의 전투 (멀티플레이 오버라이드)
        
        근처 아군만 참여하도록 수정
        """
        try:
            # 부모 클래스의 기본 로직 실행
            result = super()._trigger_combat_with_enemy(enemy)
            
            if not self.is_multiplayer:
                # 싱글플레이: 기본 결과 반환
                return result
            
            # 멀티플레이: 근처 참여자만 선택
            combat_position = (enemy.x, enemy.y)
            participants = self._get_nearby_participants(combat_position)
            
            # 참여자 정보를 결과에 추가
            if result.data:
                result.data["participants"] = participants
                result.data["combat_position"] = combat_position
            else:
                result.data = {
                    "participants": participants,
                    "combat_position": combat_position
                }
            
            participant_count = len(participants)
            self.logger.info(
                f"멀티플레이 전투 시작: 참여자 {participant_count}명 "
                f"(반경 {MultiplayerConfig.participation_radius}타일 내)"
            )
            
            return result
        except Exception as e:
            self.logger.error(f"멀티플레이 전투 트리거 실패: {e}", exc_info=True)
            # 실패 시 기본 결과 반환
            return super()._trigger_combat_with_enemy(enemy)
    
    def _initialize_player_positions(self):
        """플레이어 초기 위치 설정"""
        if not self.session or not hasattr(self, 'player'):
            return
        
        # 기본 플레이어 위치를 시작점으로 설정
        start_x, start_y = self.player.x, self.player.y
        
        import random
        for player_id, mp_player in self.session.players.items():
            # 이미 위치가 설정되어 있고 이동 가능한 위치면 그대로 사용
            if hasattr(mp_player, 'x') and hasattr(mp_player, 'y'):
                current_x = int(mp_player.x)
                current_y = int(mp_player.y)
                # 이동 가능한 위치인지 확인
                if (0 <= current_x < self.dungeon.width and 
                    0 <= current_y < self.dungeon.height and
                    self.dungeon.is_walkable(current_x, current_y)):
                    # 이미 올바른 위치에 있으면 그대로 사용
                    self.player_positions[player_id] = (current_x, current_y)
                    self.logger.info(
                        f"플레이어 {mp_player.player_name} 초기 위치 유지: "
                        f"({current_x}, {current_y})"
                    )
                    continue
            
            # 위치가 없거나 이동 불가능한 위치면 새로 찾기
            spawn_x, spawn_y = start_x, start_y
            
            # 첫 방에서 안전한 위치 찾기
            if self.dungeon.rooms:
                first_room = self.dungeon.rooms[0]
                # 방 안에서 이동 가능한 위치 찾기
                found = False
                for _ in range(50):  # 최대 50번 시도
                    test_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
                    test_y = first_room.y + random.randint(2, max(2, first_room.height - 3))
                    if self.dungeon.is_walkable(test_x, test_y):
                        spawn_x, spawn_y = test_x, test_y
                        found = True
                        break
                
                # 방에서 못 찾으면 시작 위치 근처에서 찾기
                if not found:
                    for _ in range(50):
                        offset_x = random.randint(-5, 5)
                        offset_y = random.randint(-5, 5)
                        test_x = start_x + offset_x
                        test_y = start_y + offset_y
                        test_x = max(0, min(self.dungeon.width - 1, test_x))
                        test_y = max(0, min(self.dungeon.height - 1, test_y))
                        if self.dungeon.is_walkable(test_x, test_y):
                            spawn_x, spawn_y = test_x, test_y
                            found = True
                            break
            else:
                # 방이 없으면 시작 위치 근처에서 이동 가능한 위치 찾기
                for _ in range(50):  # 최대 50번 시도
                    offset_x = random.randint(-5, 5)
                    offset_y = random.randint(-5, 5)
                    test_x = start_x + offset_x
                    test_y = start_y + offset_y
                    # 맵 경계 체크
                    test_x = max(0, min(self.dungeon.width - 1, test_x))
                    test_y = max(0, min(self.dungeon.height - 1, test_y))
                    if self.dungeon.is_walkable(test_x, test_y):
                        spawn_x, spawn_y = test_x, test_y
                        break
            
            mp_player.x = spawn_x
            mp_player.y = spawn_y
            
            # 맵 경계 체크 (안전장치)
            mp_player.x = max(0, min(self.dungeon.width - 1, mp_player.x))
            mp_player.y = max(0, min(self.dungeon.height - 1, mp_player.y))
            
            # 최종 확인: 이동 가능한 위치인지
            if not self.dungeon.is_walkable(mp_player.x, mp_player.y):
                # 이동 불가능한 위치면 기본 위치 사용
                self.logger.warning(
                    f"플레이어 {mp_player.player_name}의 초기 위치 ({mp_player.x}, {mp_player.y})가 "
                    f"이동 불가능합니다. 기본 위치로 조정합니다."
                )
                mp_player.x = start_x
                mp_player.y = start_y
            
            self.player_positions[player_id] = (mp_player.x, mp_player.y)
            
            # 로컬 플레이어인 경우 player 객체도 업데이트
            if player_id == self.local_player_id:
                self.player.x = mp_player.x
                self.player.y = mp_player.y
            
            self.logger.info(
                f"플레이어 {mp_player.player_name} 초기 위치: "
                f"({mp_player.x}, {mp_player.y}) (이동 가능: {self.dungeon.is_walkable(mp_player.x, mp_player.y)})"
            )
    
    def update_player_movement(
        self,
        player_id: str,
        dx: int,
        dy: int
    ) -> bool:
        """
        플레이어 이동 업데이트 (멀티플레이)
        
        Args:
            player_id: 플레이어 ID
            dx: X 방향 이동량 (-1, 0, 1)
            dy: Y 방향 이동량 (-1, 0, 1)
            
        Returns:
            이동 성공 여부
        """
        if not self.is_multiplayer or not self.session:
            # 싱글플레이 모드: 기본 처리 사용
            return self._handle_single_player_movement(dx, dy)
        
        if player_id not in self.session.players:
            self.logger.warning(f"플레이어 {player_id}가 세션에 없습니다")
            return False
        
        player = self.session.players[player_id]
        new_x = player.x + dx
        new_y = player.y + dy
        
        # 이동 동기화 관리자를 통한 이동 처리 (쌍방향 동기화)
        if self.movement_sync:
            # 이동 가능 여부 확인
            if not self._can_move_to(new_x, new_y):
                return False
            
            # 위치 업데이트 (로컬 플레이어)
            player.x = new_x
            player.y = new_y
            self.player_positions[player_id] = (new_x, new_y)
            # 로컬 플레이어인 경우 player 객체도 업데이트
            if player_id == self.local_player_id:
                self.player.x = new_x
                self.player.y = new_y
            
            # 모든 플레이어가 직접 브로드캐스트 (호스트/클라이언트 구분 없음)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 실행 중인 루프: 태스크로 실행
                    asyncio.create_task(
                        self.movement_sync.broadcast_move(player_id, new_x, new_y)
                    )
                else:
                    # 실행 중이지 않은 루프: 동기 실행
                    loop.run_until_complete(
                        self.movement_sync.broadcast_move(player_id, new_x, new_y)
                    )
            except RuntimeError:
                # 이벤트 루프가 없는 경우: 새 루프 생성
                try:
                    asyncio.run(
                        self.movement_sync.broadcast_move(player_id, new_x, new_y)
                    )
                except Exception as e:
                    self.logger.error(f"이동 브로드캐스트 실패: {e}", exc_info=True)
            
            return True
        
        # 이동 동기화 관리자가 없는 경우: 기본 처리
        if self.is_host:
            if not self._can_move_to(new_x, new_y):
                return False
            
            # 위치 업데이트
            player.x = new_x
            player.y = new_y
            self.player_positions[player_id] = (new_x, new_y)
            # 로컬 플레이어인 경우 player 객체도 업데이트
            if player_id == self.local_player_id:
                self.player.x = new_x
                self.player.y = new_y
            
            # 모든 클라이언트에게 이동 브로드캐스트
            if self.network_manager:
                from src.multiplayer.protocol import MessageBuilder
                import asyncio
                message = MessageBuilder.player_move(
                    player_id=player_id,
                    x=new_x,
                    y=new_y
                )
                # 이동 동기화는 movement_sync를 통해 처리하므로 여기서는 브로드캐스트하지 않음
                # (movement_sync.broadcast_move에서 호스트는 broadcast, 클라이언트는 send 사용)
                pass
        
        return True
    
    def _can_move_to(self, x: int, y: int) -> bool:
        """
        이동 가능 여부 확인
        
        Args:
            x: 목표 X 좌표
            y: 목표 Y 좌표
            
        Returns:
            이동 가능 여부
        """
        # 맵 경계 체크
        if x < 0 or x >= self.dungeon.width or y < 0 or y >= self.dungeon.height:
            return False
        
        # 이동 가능한 타일인지 확인
        if not self.dungeon.is_walkable(x, y):
            return False
        
        # 다른 플레이어와 겹치는지 확인
        if self.is_multiplayer and self.session:
            for player_id, player in self.session.players.items():
                try:
                    if player_id == self.local_player_id:
                        continue
                    
                    if hasattr(player, 'x') and hasattr(player, 'y'):
                        player_x = int(player.x) if player.x is not None else None
                        player_y = int(player.y) if player.y is not None else None
                        
                        if player_x is not None and player_y is not None:
                            if player_x == x and player_y == y:
                                # 다른 플레이어와 겹침
                                self.logger.debug(f"이동 불가: 다른 플레이어({player_id})가 위치 ({x}, {y})에 있음")
                                return False
                except (ValueError, TypeError, AttributeError) as e:
                    self.logger.warning(f"플레이어 {player_id} 위치 확인 실패: {e}")
                    continue
        
        return True
    
    def move_player(self, dx: int, dy: int):
        """
        플레이어 이동 (멀티플레이 오버라이드)
        
        Args:
            dx: X 방향 이동량
            dy: Y 방향 이동량
            
        Returns:
            ExplorationResult
        """
        if not self.is_multiplayer or not self.session or not self.local_player_id:
            # 싱글플레이 모드: 부모 클래스 로직 사용
            return super().move_player(dx, dy)
        
        # 멀티플레이 모드: update_player_movement 사용
        if self.local_player_id not in self.session.players:
            self.logger.warning(f"로컬 플레이어 {self.local_player_id}가 세션에 없습니다")
            return super().move_player(dx, dy)
        
        # 목적지 위치 계산
        mp_player = self.session.players[self.local_player_id]
        if not hasattr(mp_player, 'x') or not hasattr(mp_player, 'y'):
            from src.world.exploration import ExplorationResult, ExplorationEvent
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="플레이어 위치 정보가 없습니다"
            )
        
        new_x = mp_player.x + dx
        new_y = mp_player.y + dy
        
        # 이동 가능 체크
        from src.world.tile import TileType
        if not self.dungeon.is_walkable(new_x, new_y):
            tile = self.dungeon.get_tile(new_x, new_y)
            if tile and tile.tile_type == TileType.LOCKED_DOOR:
                return self._handle_locked_door(tile)
            from src.world.exploration import ExplorationResult, ExplorationEvent
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이동할 수 없습니다"
            )
        
        # 적과의 충돌 확인 (이동 전에!)
        enemy = self.get_enemy_at(new_x, new_y)
        if enemy:
            self.logger.info(f"적 발견! 전투 트리거 at ({enemy.x}, {enemy.y})")
            # 플레이어는 이동하지 않고 전투만 트리거
            return self._trigger_combat_with_enemy(enemy)
        
        # 이동 업데이트
        success = self.update_player_movement(self.local_player_id, dx, dy)
        
        if not success:
            # 이동 실패
            from src.world.exploration import ExplorationResult, ExplorationEvent
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이동할 수 없습니다"
            )
        
        # 로컬 플레이어 위치도 업데이트 (렌더링 및 FOV 계산용)
        if hasattr(mp_player, 'x') and hasattr(mp_player, 'y'):
            old_x, old_y = self.player.x, self.player.y
            self.player.x = mp_player.x
            self.player.y = mp_player.y
            
            # 위치가 변경되었거나 초기화 후라면 FOV 업데이트
            if old_x != self.player.x or old_y != self.player.y:
                self.update_fov()
            # 항상 FOV 업데이트 (안전장치)
            self.update_fov()
        
        # 타일 이벤트 체크
        tile = self.dungeon.get_tile(self.player.x, self.player.y)
        result = self._check_tile_event(tile) if tile else None
        
        # NPC 이동 (플레이어 이동 후, 멀티플레이에서는 호스트만)
        if self.is_multiplayer:
            if self.is_host:
                self._move_npcs_multiplayer()
        else:
            self._move_npcs()
        
        # 적 움직임 후 플레이어 위치에 적이 있는지 다시 체크 (호스트만)
        if self.is_host:
            enemy_at_player = self.get_enemy_at(self.player.x, self.player.y)
            if enemy_at_player:
                self.logger.info(f"적이 플레이어에게 접근! 전투 시작")
                return self._trigger_combat_with_enemy(enemy_at_player)
        
        if result is None:
            # 기본 결과 반환
            from src.world.exploration import ExplorationResult, ExplorationEvent
            result = ExplorationResult(
                success=True,
                event=ExplorationEvent.NONE,
                message=""
            )
        
        return result
    
    def _handle_single_player_movement(self, dx: int, dy: int) -> bool:
        """
        싱글플레이 이동 처리 (기본 로직)
        
        Args:
            dx: X 방향 이동량
            dy: Y 방향 이동량
            
        Returns:
            이동 성공 여부
        """
        # 부모 클래스의 move_player 호출
        if hasattr(super(), 'move_player'):
            result = super().move_player(dx, dy)
            return result.success if hasattr(result, 'success') else True
        return False
    
    def _move_all_enemies(self):
        """
        모든 적 이동 (부모 클래스 메서드 오버라이드)
        
        멀티플레이에서는 호스트만 실행하고, 0.65초 간격으로 제한됩니다.
        """
        if not self.is_multiplayer:
            # 싱글플레이: 부모 클래스 로직 사용
            super()._move_all_enemies()
            return
        
        # 멀티플레이: 호스트만 실행하고 시간 체크는 상위에서 처리
        if self.is_host:
            current_time = time.time()
            
            # 적 동기화 관리자를 통한 이동 가능 여부 확인
            if self.enemy_sync and self.enemy_sync.can_move_enemies(current_time):
                # 부모 클래스의 적 이동 로직 실행
                super()._move_all_enemies()
                
                # 적 위치 동기화 (비동기로 처리)
                if self.enemy_sync and hasattr(self, 'enemies') and self.enemies:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 이미 실행 중인 루프에서는 create_task 사용
                            task = asyncio.create_task(
                                self.enemy_sync.sync_enemy_positions(self.enemies)
                            )
                            # 태스크가 백그라운드에서 실행되도록 함 (경고 방지)
                            # 태스크는 네트워크 매니저의 이벤트 루프에서 실행됨
                        else:
                            # 실행 중인 루프가 없으면 run_until_complete 사용
                            loop.run_until_complete(
                                self.enemy_sync.sync_enemy_positions(self.enemies)
                            )
                    except RuntimeError as e:
                        # 이벤트 루프가 없으면 나중에 처리 (비동기 함수 호출 불가)
                        self.logger.debug(f"비동기 브로드캐스트 실패 (이벤트 루프 없음): {e}")
                    except Exception as e:
                        # 기타 예외는 로그만 남기고 계속 진행
                        self.logger.debug(f"적 위치 동기화 오류 (무시): {e}")
                
                # 이동 시간 업데이트
                self.enemy_sync.update_move_time(current_time)
                self.last_enemy_move = current_time
    
    async def sync_player_positions(self):
        """
        플레이어 위치 동기화 (주기적으로 호출)
        
        이동 동기화 관리자를 통해 위치를 동기화합니다.
        """
        if not self.is_multiplayer or not self.session:
            return
        
        if self.movement_sync:
            await self.movement_sync.sync_positions()
        
        # 기존 로직 (백업)
        current_time = time.time()
        
        # 동기화 주기 체크
        if current_time - self.last_position_sync < self.position_sync_interval:
            return
        
        self.last_position_sync = current_time
    
    def register_active_combat(self, combat_manager: Any, combat_id: str, position: Tuple[int, int]):
        """
        진행 중인 전투 등록
        
        Args:
            combat_manager: 전투 관리자
            combat_id: 전투 ID
            position: 전투 위치 (x, y)
        """
        self.active_combat_manager = combat_manager
        self.active_combat_id = combat_id
        self.active_combat_position = position
        
        if self.combat_join_handler:
            self.combat_join_handler.register_combat(combat_id, position)
        
        self.logger.info(f"전투 등록: {combat_id} at {position}")
    
    def unregister_active_combat(self, combat_id: str):
        """
        진행 중인 전투 해제
        
        Args:
            combat_id: 전투 ID
        """
        if self.active_combat_id == combat_id:
            self.active_combat_manager = None
            self.active_combat_id = None
            self.active_combat_position = None
        
        if self.combat_join_handler:
            self.combat_join_handler.unregister_combat(combat_id)
        
        self.logger.info(f"전투 해제: {combat_id}")
    
    def _trigger_combat_auto_join_check(self):
        """
        전투 자동 합류 체크 트리거 (비동기 태스크 생성)
        
        move_player는 동기 함수이므로, 비동기 체크를 별도 태스크로 실행합니다.
        """
        if not self.is_multiplayer or not self.combat_join_handler or not self.session:
            return
        
        if not self.active_combat_id or not self.active_combat_position:
            return
        
        # 비동기 태스크로 실행
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 이벤트 루프가 있으면 태스크 생성
                asyncio.create_task(self._check_combat_auto_join())
            else:
                # 이벤트 루프가 없으면 새로 생성하여 실행
                asyncio.run(self._check_combat_auto_join())
        except RuntimeError as e:
            # 이벤트 루프 관련 오류는 무시 (동기 모드일 수 있음)
            self.logger.debug(f"비동기 전투 자동 합류 체크 실패 (이벤트 루프 없음): {e}")
        except Exception as e:
            self.logger.warning(f"전투 자동 합류 체크 실패: {e}")
    
    async def _check_combat_auto_join(self):
        """
        전투 도중 자동 합류 체크 (플레이어 이동 후 호출)
        
        멀티플레이에서 다른 플레이어가 전투 중인 지역에 진입하면 자동으로 전투에 참여합니다.
        """
        if not self.is_multiplayer or not self.combat_join_handler or not self.session:
            return
        
        if not self.active_combat_id or not self.active_combat_position:
            # 진행 중인 전투가 없음
            return
        
        # 현재 시간
        current_time = time.time()
        
        # 모든 플레이어 가져오기
        all_players = {}
        for player_id, player in self.session.players.items():
            if hasattr(player, 'x') and hasattr(player, 'y'):
                all_players[player_id] = player
        
        # 자동 합류 체크
        join_requests = self.combat_join_handler.check_auto_join(current_time, all_players)
        
        # 합류 요청 처리
        for join_request in join_requests:
            player_id = join_request["player_id"]
            player = join_request["player"]
            
            # 이미 전투에 참여 중인지 확인 (전투 관리자의 allies에서 확인)
            if self.active_combat_manager:
                current_participant_ids = set()
                for ally in self.active_combat_manager.allies:
                    # 플레이어 ID 추출
                    ally_player_id = None
                    if hasattr(ally, 'player_id'):
                        ally_player_id = getattr(ally, 'player_id', None)
                    elif hasattr(ally, 'owner') and hasattr(ally.owner, 'player_id'):
                        ally_player_id = getattr(ally.owner, 'player_id', None)
                    
                    if ally_player_id:
                        current_participant_ids.add(ally_player_id)
                
                # 이미 참여 중이면 스킵
                if player_id in current_participant_ids:
                    continue
                
                # 전투에 합류 처리
                await self._add_player_to_combat(player_id, player, join_request["combat_id"])
    
    async def _add_player_to_combat(self, player_id: str, player: Any, combat_id: str):
        """
        플레이어를 전투에 합류시키기
        
        Args:
            player_id: 플레이어 ID
            player: 플레이어 객체
            combat_id: 전투 ID
        """
        try:
            if not player_id or not isinstance(player_id, str):
                self.logger.error(f"잘못된 플레이어 ID: {player_id}")
                return
            
            if not player:
                self.logger.error(f"플레이어 객체가 None: {player_id}")
                return
            
            if not combat_id or not isinstance(combat_id, str):
                self.logger.error(f"잘못된 전투 ID: {combat_id}")
                return
            
            if not self.active_combat_manager:
                self.logger.warning(f"활성 전투 관리자가 없음: {player_id}")
                return
            
            # 플레이어의 파티 가져오기
            if not hasattr(player, 'party'):
                self.logger.warning(f"플레이어 {player_id}에 party 속성이 없음")
                return
            
            if not player.party or not isinstance(player.party, list):
                self.logger.warning(f"플레이어 {player_id}의 파티가 비어있음")
                return
            
            new_allies = []
            
            # 플레이어의 파티 멤버 추가
            for character in player.party:
                try:
                    if not character:
                        continue
                    
                    is_alive = getattr(character, 'is_alive', True)
                    if not is_alive:
                        continue
                    
                    # ATB 시스템에 등록
                    if not hasattr(self.active_combat_manager, 'atb'):
                        self.logger.error("전투 관리자에 ATB 시스템이 없음")
                        continue
                    
                    try:
                        self.active_combat_manager.atb.register_combatant(character)
                    except Exception as e:
                        self.logger.error(f"ATB 등록 실패: {e}", exc_info=True)
                        continue
                    
                    # ATB 게이지 초기화 (0부터 시작 - 설정에 따라)
                    try:
                        gauge = self.active_combat_manager.atb.get_gauge(character)
                        if gauge:
                            gauge.current = MultiplayerConfig.combat_join_atb_initial
                    except Exception as e:
                        self.logger.error(f"ATB 게이지 초기화 실패: {e}", exc_info=True)
                    
                    # BRV 초기화
                    if hasattr(self.active_combat_manager, 'brave'):
                        try:
                            self.active_combat_manager.brave.initialize_brv(character)
                        except Exception as e:
                            self.logger.error(f"BRV 초기화 실패: {e}", exc_info=True)
                    
                    # 플레이어 ID 설정 (합류한 캐릭터에 플레이어 ID 연결)
                    try:
                        character.player_id = player_id
                    except Exception as e:
                        self.logger.warning(f"플레이어 ID 설정 실패: {e}")
                    
                    # 아군 리스트에 추가
                    if hasattr(self.active_combat_manager, 'allies'):
                        try:
                            self.active_combat_manager.allies.append(character)
                            new_allies.append(character)
                        except Exception as e:
                            self.logger.error(f"아군 리스트 추가 실패: {e}", exc_info=True)
                except Exception as e:
                    self.logger.error(f"캐릭터 {getattr(character, 'name', 'Unknown')} 합류 처리 실패: {e}", exc_info=True)
                    continue
            
            if new_allies:
                try:
                    # 합류 표시
                    if self.combat_join_handler:
                        self.combat_join_handler.mark_player_joined(combat_id, player_id)
                    
                    # 네트워크 동기화 (호스트가 모든 클라이언트에게 브로드캐스트)
                    if self.is_host and self.network_manager:
                        try:
                            from src.multiplayer.protocol import MessageBuilder
                            
                            # 캐릭터 ID 수집
                            character_ids = []
                            for c in new_allies:
                                try:
                                    char_id = getattr(c, 'id', None)
                                    if char_id:
                                        character_ids.append(char_id)
                                except Exception:
                                    continue
                            
                            # 전투 상태 수집
                            combat_state = {}
                            if hasattr(self.active_combat_manager, 'allies'):
                                try:
                                    combat_state["allies"] = [getattr(c, 'id', None) for c in self.active_combat_manager.allies if hasattr(c, 'id')]
                                except Exception:
                                    combat_state["allies"] = []
                            
                            if hasattr(self.active_combat_manager, 'enemies'):
                                try:
                                    combat_state["enemies"] = [getattr(e, 'id', None) for e in self.active_combat_manager.enemies if hasattr(e, 'id')]
                                except Exception:
                                    combat_state["enemies"] = []
                            
                            join_message = MessageBuilder.combat_join(
                                player_id=player_id,
                                characters=character_ids,
                                combat_state=combat_state
                            )
                            await self.network_manager.broadcast(join_message)
                        except Exception as e:
                            self.logger.error(f"합류 네트워크 동기화 실패: {e}", exc_info=True)
                    
                    self.logger.info(f"✅ 플레이어 {player_id} 전투 {combat_id}에 자동 합류 ({len(new_allies)}명)")
                except Exception as e:
                    self.logger.error(f"합류 처리 완료 실패: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"플레이어 전투 합류 실패: {e}", exc_info=True)
    
    async def update_enemy_movement(self, current_time: float):
        """
        적 이동 업데이트 (0.65초 간격)
        
        멀티플레이에서는 호스트만 적을 이동시키고, 클라이언트에게 동기화합니다.
        
        Args:
            current_time: 현재 시간
        """
        if not self.is_multiplayer:
            # 싱글플레이: 기존 로직 사용
            return
        
        # 적 동기화 관리자를 통한 이동 처리
        if self.enemy_sync:
            # 이동 가능 여부 확인
            if self.enemy_sync.can_move_enemies(current_time):
                # 호스트만 적 이동 실행
                if self.is_host:
                    # 기존 적 이동 로직 실행 (부모 클래스의 _move_all_enemies 호출)
                    if hasattr(self, '_move_all_enemies'):
                        self._move_all_enemies()
                    
                    # 적 위치 동기화
                    if hasattr(self, 'enemies'):
                        await self.enemy_sync.sync_enemy_positions(self.enemies)
        
        # 기존 타이머 업데이트 (백업)
        if current_time - self.last_enemy_move >= self.enemy_move_interval:
            self.last_enemy_move = current_time
    
    def _move_npcs_multiplayer(self):
        """
        NPC 이동 처리 (멀티플레이 - 호스트만)
        
        NPC 이동 후 동기화 메시지를 클라이언트에게 전송합니다.
        """
        if not self.is_host or not self.is_multiplayer:
            return
        
        from src.world.tile import TileType
        import random
        
        # 던전 전체를 스캔하여 NPC 타일 찾기
        npc_positions = []
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                tile = self.dungeon.get_tile(x, y)
                if tile and tile.tile_type == TileType.NPC:
                    npc_positions.append((x, y, tile))
        
        # 이동한 NPC 정보 수집
        moved_npcs = {}
        
        # 각 NPC를 랜덤하게 이동
        for x, y, npc_tile in npc_positions:
            # NPC는 상호작용하지 않은 경우에만 이동 (상인 등은 제외)
            if npc_tile.npc_interacted:
                continue
            
            # 30% 확률로 이동 (적보다 덜 자주 이동)
            if random.random() < 0.3:
                directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
                random.shuffle(directions)  # 랜덤 순서
                
                for dx, dy in directions:
                    new_x = x + dx
                    new_y = y + dy
                    
                    # 이동 가능한 위치인지 확인
                    if self.dungeon.is_walkable(new_x, new_y):
                        new_tile = self.dungeon.get_tile(new_x, new_y)
                        # 다른 NPC나 적, 플레이어와 겹치지 않도록 체크
                        if (new_tile and new_tile.tile_type != TileType.NPC and
                            not self.get_enemy_at(new_x, new_y) and
                            (new_x, new_y) != (self.player.x, self.player.y)):
                            
                            # 기존 위치를 FLOOR로 변경
                            self.dungeon.set_tile(x, y, TileType.FLOOR)
                            
                            # 새 위치에 NPC 배치
                            self.dungeon.set_tile(
                                new_x, new_y,
                                TileType.NPC,
                                npc_id=npc_tile.npc_id,
                                npc_type=npc_tile.npc_type,
                                npc_subtype=npc_tile.npc_subtype,
                                npc_interacted=npc_tile.npc_interacted
                            )
                            
                            # 이동한 NPC 정보 저장
                            npc_id = npc_tile.npc_id or f"npc_{x}_{y}"
                            moved_npcs[npc_id] = {
                                "x": new_x,
                                "y": new_y,
                                "old_x": x,
                                "old_y": y,
                                "npc_type": npc_tile.npc_type,
                                "npc_subtype": npc_tile.npc_subtype,
                                "npc_interacted": npc_tile.npc_interacted
                            }
                            
                            self.logger.debug(f"NPC 이동: {npc_tile.npc_subtype} ({x}, {y}) -> ({new_x}, {new_y})")
                            break  # 이동 성공하면 중단
        
        # 이동한 NPC가 있으면 동기화 메시지 전송
        if moved_npcs and self.network_manager:
            from src.multiplayer.protocol import MessageBuilder
            import asyncio
            try:
                npc_move_msg = MessageBuilder.npc_move(moved_npcs)
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.network_manager.broadcast(npc_move_msg))
                else:
                    loop.run_until_complete(self.network_manager.broadcast(npc_move_msg))
                self.logger.debug(f"NPC 이동 동기화 메시지 전송: {len(moved_npcs)}개")
            except Exception as e:
                self.logger.error(f"NPC 이동 동기화 메시지 전송 실패: {e}", exc_info=True)
    
    def _register_drop_handlers(self):
        """드롭된 아이템/골드 동기화 핸들러 등록"""
        if not self.network_manager:
            return
        
        from src.multiplayer.protocol import MessageType
        from src.world.tile import TileType
        from src.equipment.item_system import ItemGenerator
        
        async def handle_item_dropped(message, sender_id=None):
            """아이템 드롭 메시지 처리"""
            if self.is_host and sender_id is None:
                return  # 호스트는 자신의 메시지를 처리하지 않음
            
            x = message.data.get("x")
            y = message.data.get("y")
            item_data = message.data.get("item", {})
            
            if x is None or y is None:
                self.logger.warning(f"아이템 드롭 메시지에 필수 데이터가 없습니다: x={x}, y={y}")
                return
            
            # 해당 위치의 타일 찾기
            if 0 <= x < self.dungeon.width and 0 <= y < self.dungeon.height:
                tile = self.dungeon.get_tile(x, y)
                if tile:
                    # 아이템 재생성 (간단한 버전 - 실제로는 더 복잡할 수 있음)
                    # 여기서는 타일만 표시하고, 실제 아이템은 플레이어가 주울 때 생성
                    tile.tile_type = TileType.DROPPED_ITEM
                    # dropped_item은 실제로는 클라이언트가 주울 때 생성되므로 None으로 설정
                    # 또는 아이템 데이터를 저장해두고 나중에 사용
                    self.logger.debug(f"아이템 드롭 동기화: ({x}, {y})")
        
        async def handle_gold_dropped(message, sender_id=None):
            """골드 드롭 메시지 처리"""
            if self.is_host and sender_id is None:
                return  # 호스트는 자신의 메시지를 처리하지 않음
            
            x = message.data.get("x")
            y = message.data.get("y")
            amount = message.data.get("amount", 0)
            
            if x is None or y is None or amount <= 0:
                self.logger.warning(f"골드 드롭 메시지에 필수 데이터가 없습니다: x={x}, y={y}, amount={amount}")
                return
            
            # 해당 위치의 타일 찾기
            if 0 <= x < self.dungeon.width and 0 <= y < self.dungeon.height:
                tile = self.dungeon.get_tile(x, y)
                if tile:
                    tile.tile_type = TileType.GOLD
                    tile.gold_amount = amount
                    self.logger.debug(f"골드 드롭 동기화: ({x}, {y}) {amount}G")
        
        self.network_manager.register_handler(MessageType.ITEM_DROPPED, handle_item_dropped)
        self.network_manager.register_handler(MessageType.GOLD_DROPPED, handle_gold_dropped)
        self.logger.debug("드롭된 아이템/골드 동기화 핸들러 등록 완료")

