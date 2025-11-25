"""
월드 탐험 UI

플레이어가 던전을 돌아다니는 화면
"""

from typing import List, Optional, Tuple
import tcod
import time

from src.world.exploration import ExplorationSystem, ExplorationEvent, ExplorationResult
from src.world.map_renderer import MapRenderer
from src.world.field_skills import FieldSkillManager
from src.world.tile import TileType
from src.ui.input_handler import InputHandler, GameAction
from src.ui.gauge_renderer import GaugeRenderer
from src.ui.tcod_display import render_space_background
from src.ui.field_skill_ui import FieldSkillUI
from src.core.logger import get_logger, Loggers
from src.audio.audio_manager import play_bgm


logger = get_logger(Loggers.UI)


class WorldUI:
    """월드 탐험 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        exploration: ExplorationSystem,
        inventory=None,
        party=None,
        network_manager=None,
        local_player_id=None,
        on_update=None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.exploration = exploration
        self.inventory = inventory
        self.party = party
        self.map_renderer = MapRenderer(map_x=0, map_y=5)
        self.gauge_renderer = GaugeRenderer()
        self.network_manager = network_manager
        if self.network_manager is None:
            from src.core.logger import get_logger
            logger = get_logger("world_ui")
            logger.debug("WorldUI initialized with network_manager=None")
        else:
            from src.core.logger import get_logger
            logger = get_logger("world_ui")
            logger.debug(f"WorldUI initialized with network_manager={network_manager}")  # 멀티플레이: 네트워크 관리자
        self.local_player_id = local_player_id  # 멀티플레이: 로컬 플레이어 ID
        self.on_update = on_update  # 업데이트 콜백

        # 필드 스킬 매니저 및 UI 초기화
        self.field_skill_manager = FieldSkillManager(exploration)
        self.field_skill_ui = FieldSkillUI(screen_width, screen_height, self.field_skill_manager)
        
        # 초기화 로그
        logger.info(f"WorldUI 초기화 - inventory: {inventory is not None}, party: {party is not None}, party members: {len(party) if party else 0}")

        # 메시지 로그
        self.messages: List[str] = []
        self.max_messages = 5

        # 상태
        self.quit_requested = False
        self.combat_requested = False
        self.combat_enemies = None  # 전투에 참여할 적들 (맵에서 제거용)
        self.combat_num_enemies = 0  # 실제 전투 적 수
        self.combat_participants = None  # 멀티플레이: 전투 참여자
        self.combat_position = None  # 멀티플레이: 전투 시작 위치
        self.floor_change_requested = None  # "up" or "down"

        # 종료 확인
        self.quit_confirm_mode = False
        self.quit_confirm_yes = False  # True: 예, False: 아니오
        
        # 멀티플레이 이동 쿨타임 (초당 4회 = 0.25초 간격)
        self.last_move_time = 0.0
        self.move_cooldown = 0.25  # 0.25초 = 초당 4회 이동
        
        # 채팅 입력 상태
        self.chat_input_active = False
        self.chat_input_text = ""
        self.chat_input_max_length = 60
        
        # 분수대 사용 여부 (마을 방문마다 리셋)
        self.fountain_used = False
        self.was_in_town = False  # 이전 프레임의 마을 상태 추적

    def add_message(self, text: str):
        """메시지 추가"""
        self.messages.append(text)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        logger.debug(f"메시지: {text}")

    def handle_input(self, action: GameAction, console=None, context=None, key_event=None) -> bool:
        # 마을 입장 시 분수대 사용 플래그 리셋
        is_in_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
        if is_in_town and not self.was_in_town:
            # 마을에 새로 입장한 경우
            self.fountain_used = False
            logger.debug("[분수대] 마을 입장 - 분수대 사용 플래그 리셋")
        self.was_in_town = is_in_town
        """
        입력 처리

        Returns:
            True면 종료
        """
        # Debug: handle_input 호출

        # 채팅 입력 모드
        if self.chat_input_active:
            if isinstance(key_event, tcod.event.KeyDown):
                if key_event.sym == tcod.event.KeySym.RETURN:
                    # Enter: 메시지 전송
                    if self.chat_input_text.strip() and self.network_manager and self.local_player_id:
                        self._send_chat_message(self.chat_input_text.strip())
                        self.chat_input_text = ""
                    self.chat_input_active = False
                    return False
                elif key_event.sym == tcod.event.KeySym.ESCAPE:
                    # ESC: 취소
                    self.chat_input_text = ""
                    self.chat_input_active = False
                    return False
                elif key_event.sym == tcod.event.KeySym.BACKSPACE:
                    # Backspace: 삭제
                    if self.chat_input_text:
                        self.chat_input_text = self.chat_input_text[:-1]
                elif len(self.chat_input_text) < self.chat_input_max_length:
                    # 문자 입력
                    if 32 <= key_event.sym <= 126:  # ASCII 문자 범위
                        char = chr(key_event.sym)
                        self.chat_input_text += char
            return False

        # 필드 스킬 UI 입력 처리
        if self.field_skill_ui.is_active:
            done, msg = self.field_skill_ui.handle_input(action)
            if done:
                if msg:
                    self.add_message(msg)
            return False

        # T 키로 채팅 입력 시작 (멀티플레이어일 때만)
        if isinstance(key_event, tcod.event.KeyDown):
            # 필드 스킬 UI (F 키) - 마을에서는 사용 불가
            if key_event.sym == tcod.event.KeySym.f:
                # 마을인지 확인
                is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
                if is_town:
                    self.add_message("마을에서는 필드스킬을 사용할 수 없습니다.")
                    return False
                if self.party:
                    self.field_skill_ui.show(self.party)
                    return False

            if key_event.sym == tcod.event.KeySym.t:
                is_multiplayer = (
                    self.network_manager is not None or
                    (hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer) or
                    (hasattr(self.exploration, 'session') and self.exploration.session is not None)
                )
                if is_multiplayer:
                    self.chat_input_active = True
                    self.chat_input_text = ""
                    return False
        
        # 봇 관련 코드 제거됨

        # 종료 확인 모드
        if self.quit_confirm_mode:
            if action == GameAction.MOVE_LEFT:
                self.quit_confirm_yes = True
            elif action == GameAction.MOVE_RIGHT:
                self.quit_confirm_yes = False
            elif action == GameAction.CONFIRM:
                if self.quit_confirm_yes:
                    # 종료 확인
                    self.quit_requested = True
                    return True
                else:
                    # 취소
                    self.quit_confirm_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.quit_confirm_mode = False
            return False

        if action == GameAction.QUIT or action == GameAction.ESCAPE:
            # 종료 확인 대화상자 표시
            self.quit_confirm_mode = True
            self.quit_confirm_yes = False
            return False

        # 메뉴 열기 (M키)
        if action == GameAction.MENU:
            # Debug: 메뉴 열기
            if self.inventory is not None and self.party is not None and console is not None and context is not None:
                from src.ui.game_menu import open_game_menu, MenuOption
                # Debug: 게임 메뉴
                result = open_game_menu(console, context, self.inventory, self.party, self.exploration)
                if result == MenuOption.QUIT:
                    self.quit_requested = True
                    return True
                elif result == MenuOption.LOAD_GAME:
                    # 게임을 불러온 경우 탐험 종료하고 main.py에서 처리하도록
                    self.quit_requested = True
                    return True
                return False
            else:
                logger.warning(f"메뉴를 열 수 없음 - inventory={self.inventory is not None}, party={self.party is not None}, console={console is not None}, context={context is not None}")

        # 인벤토리 열기 (I키)
        if action == GameAction.OPEN_INVENTORY:
            # Debug: 인벤토리 열기
            if self.inventory is not None and self.party is not None and console is not None and context is not None:
                from src.ui.inventory_ui import open_inventory
                # Debug: 인벤토리 시도
                # on_update 콜백 전달
                open_inventory(console, context, self.inventory, self.party, self.exploration, on_update=self.on_update)
                return False
            else:
                logger.warning(f"인벤토리를 열 수 없음 - inventory={self.inventory is not None}, party={self.party is not None}, console={console is not None}, context={context is not None}")

        # 이동
        dx, dy = 0, 0

        if action == GameAction.MOVE_UP:
            dy = -1
        elif action == GameAction.MOVE_DOWN:
            dy = 1
        elif action == GameAction.MOVE_LEFT:
            dx = -1
        elif action == GameAction.MOVE_RIGHT:
            dx = 1

        if dx != 0 or dy != 0:
            # 멀티플레이: 이동 쿨타임 체크 (초당 4회 제한)
            import time
            current_time = time.time()
            # 멀티플레이 모드 확인 (엄격한 확인)
            is_multiplayer = False
            try:
                from src.multiplayer.game_mode import get_game_mode_manager
                game_mode_manager = get_game_mode_manager()
                
                # game_mode_manager가 없으면 싱글플레이
                if not game_mode_manager:
                    is_multiplayer = False
                else:
                    # game_mode_manager가 명시적으로 True를 반환하고
                    game_mode_is_multiplayer = game_mode_manager.is_multiplayer()
                    
                    # exploration도 멀티플레이로 설정되어 있어야 함
                    exploration_is_multiplayer = getattr(self.exploration, 'is_multiplayer', False)
                    
                    # 둘 다 True여야만 멀티플레이로 확정
                    is_multiplayer = bool(game_mode_is_multiplayer) and bool(exploration_is_multiplayer)
                    
                    # 디버그 로그
                    if game_mode_is_multiplayer or exploration_is_multiplayer:
                        logger.debug(
                            f"멀티플레이 모드 확인: "
                            f"game_mode={game_mode_is_multiplayer}, "
                            f"exploration={exploration_is_multiplayer}, "
                            f"최종={is_multiplayer}"
                        )
            except Exception as e:
                # game_mode_manager가 없거나 오류가 있으면 싱글플레이로 간주
                logger.debug(f"game_mode_manager 확인 실패: {e}, 싱글플레이로 간주")
                is_multiplayer = False
            
            # 멀티플레이 모드에서만 로컬 플레이어 ID 확인
            if is_multiplayer:
                # 로컬 플레이어 ID 확인
                local_player_id = None
                if hasattr(self.exploration, 'local_player_id'):
                    local_player_id = self.exploration.local_player_id
                elif self.local_player_id:
                    local_player_id = self.local_player_id
                elif hasattr(self.exploration, 'session') and self.exploration.session:
                    local_player_id = getattr(self.exploration.session, 'local_player_id', None)
                
                # 로컬 플레이어 ID가 없으면 이동 불가 (멀티플레이 모드에서만)
                if not local_player_id:
                    logger.error(
                        f"멀티플레이 모드에서 로컬 플레이어 ID가 없어 이동할 수 없습니다. "
                        f"(exploration.is_multiplayer={getattr(self.exploration, 'is_multiplayer', None)}, "
                        f"session={getattr(self.exploration, 'session', None)})"
                    )
                    return False
                
                # 세션에 로컬 플레이어가 있는지 확인
                if hasattr(self.exploration, 'session') and self.exploration.session:
                    if local_player_id not in self.exploration.session.players:
                        logger.warning(f"로컬 플레이어 {local_player_id}가 세션에 없어 이동할 수 없습니다")
                        return False
                
                # 쿨타임 체크
                if current_time - self.last_move_time < self.move_cooldown:
                    # 쿨타임 중이면 이동 무시
                    return False
                # 쿨타임 통과 시 이동 시간 업데이트
                self.last_move_time = current_time
            
            result = self.exploration.move_player(dx, dy)
            if result is None:
                # Debug: 이동 결과 None
                # None인 경우 기본 결과 생성
                from src.world.exploration import ExplorationResult, ExplorationEvent
                result = ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NONE,
                    message=""
                )
            else:
                # Debug: 이동 결과 이벤트
                pass
            
            self._handle_exploration_result(result, console, context)
            # 전투가 트리거되면 즉시 루프 탈출
            if self.combat_requested:
                # Debug: 전투 요청
                return True

        # 채집 또는 계단 이동 (Z키/엔터키)
        elif action == GameAction.CONFIRM:
            # 먼저 채집 오브젝트 찾기
            nearby_harvestables = self._find_all_nearby_harvestables()
            if nearby_harvestables:
                # 채집 오브젝트가 있으면 일괄 채집 실행
                if console is not None and context is not None and self.inventory is not None:
                    from src.ui.gathering_ui import harvest_object

                    harvest_count = 0
                    for harvestable in nearby_harvestables:
                        # 채집 실행 (멀티플레이어 동기화를 위해 exploration 전달)
                        success = harvest_object(console, context, harvestable, self.inventory, exploration=self.exploration)
                        if success:
                            harvest_count += 1
                            logger.info(f"채집 성공: {harvestable.object_type.display_name}")

                    if harvest_count > 0:
                        # 메시지는 harvest_object 내부에서 출력되거나 시스템 메시지로 처리됨
                        pass
                    return False
                else:
                    logger.warning("채집 불가: console, context, inventory가 필요합니다")
                    return False
            
            # 채집 오브젝트가 없으면 계단 이동 체크
            tile = self.exploration.dungeon.get_tile(
                self.exploration.player.x,
                self.exploration.player.y
            )

            if tile:
                from src.world.tile import TileType
                from src.audio import play_sfx
                if tile.tile_type == TileType.STAIRS_DOWN:
                    play_sfx("world", "stairs_down")

                    # 마을인지 확인
                    is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town

                    if is_town:
                        # 마을에서 던전으로 나가는 경우
                        # 멀티플레이: 모든 플레이어 준비 확인
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'session') and self.exploration.session:
                                session = self.exploration.session
                                local_player_id = None
                                if hasattr(self.exploration, 'local_player_id'):
                                    local_player_id = self.exploration.local_player_id

                                # 로컬 플레이어 준비 상태 설정
                                if local_player_id:
                                    session.set_floor_ready(local_player_id, True)

                                # 모든 플레이어 준비 확인
                                if session.is_all_ready_for_floor_change():
                                    self.floor_change_requested = "floor_down"
                                    self.add_message("모든 플레이어가 준비되었습니다. 던전으로 이동합니다...")
                                    session.reset_floor_ready()  # 준비 상태 초기화
                                    return True
                                else:
                                    ready_count = len(session.floor_ready_players)
                                    total_count = len(session.players)
                                    self.add_message(f"던전으로 이동 대기 중... ({ready_count}/{total_count} 준비)")
                                    return False

                        # 싱글플레이: 즉시 이동
                        self.floor_change_requested = "floor_down"
                        self.add_message("던전으로 이동합니다...")
                        return True
                    else:
                        # 던전에서 아래층으로 이동하는 경우
                        # 멀티플레이: 모든 플레이어 준비 확인
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'session') and self.exploration.session:
                                session = self.exploration.session
                                local_player_id = None
                                if hasattr(self.exploration, 'local_player_id'):
                                    local_player_id = self.exploration.local_player_id

                                # 로컬 플레이어 준비 상태 설정
                                if local_player_id:
                                    session.set_floor_ready(local_player_id, True)

                                # 모든 플레이어 준비 확인
                                if session.is_all_ready_for_floor_change():
                                    self.floor_change_requested = "floor_down"
                                    self.add_message("모든 플레이어가 준비되었습니다. 아래층으로 내려갑니다...")
                                    session.reset_floor_ready()  # 준비 상태 초기화
                                    return True
                                else:
                                    ready_count = len(session.floor_ready_players)
                                    total_count = len(session.players)
                                    self.add_message(f"다음 층으로 이동 대기 중... ({ready_count}/{total_count} 준비)")
                                    return False

                        # 싱글플레이: 즉시 이동
                        self.floor_change_requested = "floor_down"
                        self.add_message("아래층으로 내려갑니다...")
                        return True
            return False

        # 상호작용 (E키 또는 Z키)
        elif action == GameAction.INTERACT or action == GameAction.CONFIRM:
            logger.debug(f"상호작용 입력: {action}")
            # 우선순위 1: 요리솥
            nearby_cooking_pot = self._find_nearby_cooking_pot()
            if nearby_cooking_pot:
                logger.info(f"요리솥 발견 및 사용 시도: 위치 ({nearby_cooking_pot.x}, {nearby_cooking_pot.y})")
                if console is not None and context is not None and self.inventory is not None:
                    from src.ui.cooking_ui import open_cooking_pot

                    # 요리 UI 열기
                    logger.info("요리솥 발견! 요리 UI 열기")
                    # 요리솥에서 요리할 때는 보너스 적용
                    open_cooking_pot(console, context, self.inventory, is_cooking_pot=True)
                    return False
                else:
                    logger.warning("요리솥 사용 실패: 필요한 컴포넌트 없음 (console, context, inventory)")
                    self.add_message("요리솥을 사용할 수 없습니다.")
                    return False
            else:
                logger.debug("요리솥 없음 - 다른 상호작용으로 진행")

            # 우선순위 2: 채집 오브젝트 (일괄 채집)
            nearby_harvestables = self._find_all_nearby_harvestables()
            if nearby_harvestables:
                # 채집 오브젝트가 있으면 일괄 채집 실행
                if console is not None and context is not None and self.inventory is not None:
                    from src.ui.gathering_ui import harvest_object
                    
                    harvest_count = 0
                    for harvestable in nearby_harvestables:
                        # 채집 실행 (멀티플레이어 동기화를 위해 exploration 전달)
                        success = harvest_object(console, context, harvestable, self.inventory, exploration=self.exploration)
                        if success:
                            harvest_count += 1
                            logger.info(f"채집 성공: {harvestable.object_type.display_name}")
                    
                    if harvest_count > 0:
                        # 메시지는 harvest_object 내부에서 출력되거나 시스템 메시지로 처리됨
                        pass
                    return False
                else:
                    logger.warning("채집 불가: console, context, inventory가 필요합니다")
                return False

            # E키를 눌렀지만 주변에 아무것도 없을 때
            if action == GameAction.INTERACT:
                # 마을인지 확인
                is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
                
                if is_town:
                    # 마을에서 건물과 상호작용
                    from src.town.town_map import TownInteractionHandler
                    # town_map은 dungeon 객체에 있거나 exploration 객체에 직접 설정됨
                    town_map = getattr(self.exploration, 'town_map', None) or getattr(self.exploration.dungeon, 'town_map', None)
                    town_manager = getattr(self.exploration, 'town_manager', None)
                    if town_manager is None:
                        # exploration에 town_manager가 없으면 전역 town_manager 사용
                        from src.town.town_manager import get_town_manager
                        town_manager = get_town_manager()
                        # exploration에도 설정하여 저장 시 일관성 유지
                        self.exploration.town_manager = town_manager
                        logger.info(f"[DEBUG] world_ui: 전역 town_manager 사용 및 exploration에 설정 (id: {id(town_manager)}, storage: {len(town_manager.get_storage_inventory())}개, building: {building.building_type if hasattr(building, 'building_type') else 'unknown'})")
                    else:
                        logger.info(f"[DEBUG] world_ui: 기존 exploration.town_manager 사용 (id: {id(town_manager)}, storage: {len(town_manager.get_storage_inventory())}개, building: {building.building_type if hasattr(building, 'building_type') else 'unknown'})")
                    
                    if not town_map:
                        # town_map이 없으면 dungeon에서 가져오기 시도
                        if hasattr(self.exploration.dungeon, 'town_map'):
                            town_map = self.exploration.dungeon.town_map
                    
                    if town_map and town_manager:
                        # 현재 위치의 건물 확인
                        player_x = self.exploration.player.x
                        player_y = self.exploration.player.y
                        player_tile = self.exploration.dungeon.get_tile(player_x, player_y)
                        
                        building = None
                        
                        # 방법 1: 타일의 building 속성 사용 (우선순위 높음)
                        if player_tile and hasattr(player_tile, 'building') and player_tile.building:
                            building = player_tile.building
                            logger.debug(f"[상호작용] 타일의 building 속성에서 건물 찾음: {building.name} at ({player_x}, {player_y})")
                        
                        # 방법 2: town_map에서 직접 건물 찾기
                        if not building:
                            building = town_map.get_building_at(player_x, player_y)
                            if building:
                                logger.debug(f"[상호작용] town_map.get_building_at에서 건물 찾음: {building.name} at ({player_x}, {player_y})")
                        
                        # 방법 3: 타일의 char가 건물 심볼인 경우 town_map에서 찾기
                        if not building and player_tile and player_tile.char in ['K', 'B', 'A', 'S', 'Q', '$', 'I', 'G', 'F']:
                            logger.debug(f"[상호작용] 타일 char가 건물 심볼 ({player_tile.char}), town_map.buildings에서 찾기 시도 (총 {len(town_map.buildings)}개 건물)")
                            # 모든 건물을 순회하며 위치 확인
                            for b in town_map.buildings:
                                logger.debug(f"  건물 체크: {b.name} at ({b.x}, {b.y}) vs 플레이어 ({player_x}, {player_y})")
                                if b.x == player_x and b.y == player_y:
                                    building = b
                                    logger.debug(f"[상호작용] town_map.buildings에서 건물 찾음: {building.name}")
                                    break
                        
                        if building:
                            # 건물과 상호작용
                            result = TownInteractionHandler.interact_with_building(
                                building, 
                                self.exploration.player, 
                                town_manager
                            )
                            logger.info(f"[상호작용 성공] {building.name} (위치: {player_x}, {player_y}) - {result.get('message', '')}")
                            self.add_message(result.get('message', f"{building.name}에 입장했습니다."))
                            # TODO: 건물별 UI 열기 (주방, 대장간 등)
                            return False
                        else:
                            # 건물이 없는 위치에서 상호작용 시도
                            tile_char = player_tile.char if player_tile else 'None'
                            logger.warning(f"[상호작용 실패] 위치 ({player_x}, {player_y})에 건물이 없습니다. (타일 char: {tile_char}, town_map.buildings 개수: {len(town_map.buildings)})")
                            # 건물 목록 로그
                            if town_map.buildings:
                                for b in town_map.buildings:
                                    logger.warning(f"  건물: {b.name} at ({b.x}, {b.y})")
                            self.add_message("주변에 상호작용할 건물이 없습니다.")
                            return True
                    else:
                        logger.warning(f"town_map={town_map is not None}, town_manager={town_manager is not None}")
                        if not town_map:
                            logger.error("town_map을 찾을 수 없습니다.")
                        if not town_manager:
                            logger.error("town_manager를 찾을 수 없습니다.")
                
                # 현재 위치의 타일 확인 (모루 등)
                player_tile = self.exploration.dungeon.get_tile(self.exploration.player.x, self.exploration.player.y)
                if player_tile:
                    if player_tile.tile_type == TileType.ANVIL:
                        from src.ui.anvil_ui import open_anvil_ui
                        # 인벤토리는 player 객체의 inventory 속성이 아니라 별도 관리될 수 있으므로 확인
                        # ExplorationSystem.player는 Character 객체임. Character는 inventory 속성을 가지지 않을 수 있음 (장착 equipment만 가짐)
                        # 하지만 여기서는 src.equipment.inventory.Inventory 객체가 필요함.
                        # main.py 등에서 주입된 전역 인벤토리 객체를 찾아야 함.
                        # WorldUI는 inventory 참조를 가지고 있지 않음.
                        # 그러나 GoldShopUI 호출 시에는 inventory를 넘겨줌.
                        # WorldUI 생성자나 초기화 시점에 inventory를 저장하도록 하거나, 
                        # Character 객체에 연결된 파티 인벤토리를 찾아야 함.
                        
                        # 임시 방편: ExplorationSystem에 inventory 참조가 있다면 사용
                        # 또는 Character 객체에 inventory 참조가 있다면 사용
                        
                        inventory = None
                        if hasattr(self.exploration.player, 'inventory'):
                            inventory = self.exploration.player.inventory
                        elif hasattr(self, 'inventory'):
                            inventory = self.inventory
                            
                        # WorldUI가 inventory를 가지고 있지 않다면... 문제.
                        # 일단 open_anvil_ui 호출. inventory가 None이면 안됨.
                        
                        # WorldUI는 inventory 속성을 가지고 있지 않음.
                        # 하지만, 게임 구조상 Player 객체가 Inventory를 가지고 있거나,
                        # WorldUI를 생성할 때 Inventory를 넘겨받아야 함.
                        # 현재 구조에서는 main.py에서 WorldUI를 생성할 때 inventory를 넘기지 않음.
                        # 그러나 Character 클래스는 equipment만 가지고 있고 inventory는 가지고 있지 않음 (Inventory 클래스가 party 리스트를 가짐)
                        
                        # 해결책: 전역 인벤토리에 접근하거나, WorldUI에 inventory 주입 필요.
                        # 여기서는 Character 객체에 임시로 inventory 속성이 있다고 가정하거나 (봇의 경우 있음),
                        # main.py 구조를 볼 수 없으니 가장 안전한 방법인 '전역 인벤토리' 접근 시도.
                        # 하지만 전역 변수는 지양됨.
                        
                        # 코드 분석 결과: src/ui/inventory_ui.py 등을 보면 inventory 객체를 인자로 받음.
                        # WorldUI는 inventory를 모르므로, 상호작용 시점에 inventory를 어떻게든 구해야 함.
                        
                        # 유일한 방법: Character 객체가 inventory를 참조하고 있다고 가정.
                        # character.inventory가 존재할 수 있음
                        
                        # inventory가 None이 아닌지 확인한 후 open_anvil_ui 호출
                        if inventory is not None:
                            open_anvil_ui(console, context, inventory, player_tile)
                            return True
                        else:
                            # 인벤토리를 찾을 수 없으면 메시지 출력
                            self.add_message("인벤토리를 열 수 없습니다.")
                            return True

                self.add_message("주변에 상호작용할 것이 없습니다.")

        return False

    def _handle_exploration_result(self, result: ExplorationResult, console=None, context=None):
        """탐험 결과 처리"""
        # Debug: 탐험 결과

        # 마을 건물 상호작용 처리 (적과 조우와 동일한 방식)
        if result.event == ExplorationEvent.BUILDING_INTERACTION:
            logger.info(f"[건물 상호작용] 이벤트 수신 - result.data={result.data}, console={console is not None}, context={context is not None}, console_type={type(console)}, context_type={type(context)}")
            if result.data:
                building = result.data.get("building")
                logger.info(f"[건물 상호작용] building 객체 확인 - building={building}, building is not None={building is not None}")
                if building is not None and console is not None and context is not None:
                    # 마을에서 건물과 상호작용
                    from src.town.town_map import TownInteractionHandler, BuildingType
                    town_manager = getattr(self.exploration, 'town_manager', None)
                    if town_manager is None:
                        # exploration에 town_manager가 없으면 전역 town_manager 사용
                        from src.town.town_manager import get_town_manager
                        town_manager = get_town_manager()
                        # exploration에도 설정하여 저장 시 일관성 유지
                        self.exploration.town_manager = town_manager
                        logger.info(f"[DEBUG] world_ui: 전역 town_manager 사용 및 exploration에 설정 (id: {id(town_manager)}, storage: {len(town_manager.get_storage_inventory())}개, building: {building.building_type if hasattr(building, 'building_type') else 'unknown'})")
                    else:
                        logger.info(f"[DEBUG] world_ui: 기존 exploration.town_manager 사용 (id: {id(town_manager)}, storage: {len(town_manager.get_storage_inventory())}개, building: {building.building_type if hasattr(building, 'building_type') else 'unknown'})")
                    
                    if town_manager:
                        # 건물과 상호작용
                        interaction_result = TownInteractionHandler.interact_with_building(
                            building, 
                            self.exploration.player, 
                            town_manager
                        )
                        logger.info(f"[건물 상호작용] {building.name} - {interaction_result.get('message', '')}")
                        logger.info(f"[건물 상호작용] 디버그 - console={console is not None}, context={context is not None}, inventory={self.inventory is not None}, building_type={building.building_type}")
                        
                        # 건물별 실제 UI 열기
                        try:
                            # console과 context가 None이면 UI를 열 수 없음
                            if console is None or context is None:
                                logger.warning(f"[건물 상호작용] console 또는 context가 없습니다. console={console is not None}, context={context is not None}")
                                self.add_message(interaction_result.get('message', f"{building.name}에 입장했습니다."))
                                # UI를 열 수 없지만 메시지는 표시했으므로 계속 진행
                            
                            # 건물 타입별 UI 열기
                            if building.building_type == BuildingType.KITCHEN:
                                # 주방: 요리 UI 열기
                                if self.inventory is not None:
                                    from src.ui.cooking_ui import open_cooking_pot
                                    logger.info(f"[건물 상호작용] 주방 UI 열기 (inventory type: {type(self.inventory)})")
                                    # 주방에서는 요리솥 보너스 적용
                                    open_cooking_pot(console, context, self.inventory, is_cooking_pot=True)
                                else:
                                    logger.warning(f"[건물 상호작용] 인벤토리가 없어 주방을 열 수 없습니다. inventory={self.inventory}")
                                    self.add_message("인벤토리가 없어 주방을 사용할 수 없습니다.")
                            elif building.building_type == BuildingType.BLACKSMITH:
                                # 대장간: 골드 상점 열기 (장비 수리/재련)
                                if self.inventory is not None:
                                    from src.ui.gold_shop_ui import open_gold_shop
                                    # 마을에서 대장간을 열 때는 현재 층수 또는 최대 도달 층수 사용
                                    current_floor = self.exploration.floor_number if hasattr(self.exploration, 'floor_number') else 1
                                    max_floor = self.exploration.game_stats.get("max_floor_reached", current_floor) if hasattr(self.exploration, 'game_stats') else current_floor
                                    floor_level = max(current_floor, max_floor)
                                    logger.info(f"[건물 상호작용] 대장간 UI 열기 (현재 층: {current_floor}, 최대 층: {max_floor}, 사용 층수: {floor_level})")
                                    open_gold_shop(console, context, self.inventory, floor_level, shop_type="blacksmith")
                                else:
                                    logger.warning(f"[건물 상호작용] 인벤토리가 없어 대장간을 열 수 없습니다. inventory={self.inventory}")
                                    self.add_message("인벤토리가 없어 대장간을 사용할 수 없습니다.")
                            elif building.building_type == BuildingType.SHOP:
                                # 상점: 골드 상점 열기
                                logger.info(f"[건물 상호작용] 잡화점 - inventory 체크 직전: inventory={self.inventory}, is not None={self.inventory is not None}, type={type(self.inventory)}")
                                if self.inventory is not None:
                                    from src.ui.gold_shop_ui import open_gold_shop
                                    # 마을에서 잡화점을 열 때는 현재 층수 또는 최대 도달 층수 사용
                                    current_floor = self.exploration.floor_number if hasattr(self.exploration, 'floor_number') else 1
                                    max_floor = self.exploration.game_stats.get("max_floor_reached", current_floor) if hasattr(self.exploration, 'game_stats') else current_floor
                                    floor_level = max(current_floor, max_floor)
                                    logger.info(f"[건물 상호작용] 잡화점 UI 열기 (현재 층: {current_floor}, 최대 층: {max_floor}, 사용 층수: {floor_level})")
                                    try:
                                        open_gold_shop(console, context, self.inventory, floor_level, shop_type="shop")
                                        logger.info(f"[건물 상호작용] 잡화점 UI 열기 성공")
                                    except Exception as ui_error:
                                        logger.error(f"[건물 상호작용] 잡화점 UI 열기 오류: {ui_error}", exc_info=True)
                                        self.add_message(f"상점을 열 수 없습니다: {ui_error}")
                                else:
                                    logger.warning(f"[건물 상호작용] 인벤토리가 없어 잡화점을 열 수 없습니다. inventory={self.inventory}, is not None={self.inventory is not None}")
                                    self.add_message("인벤토리가 없어 잡화점을 사용할 수 없습니다.")
                            elif building.building_type == BuildingType.INN:
                                # 여관: 휴식 메뉴 열기
                                # party는 self.party 또는 exploration.player.party에서 가져오기
                                party_for_rest = self.party
                                if not party_for_rest and hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'party'):
                                    party_for_rest = self.exploration.player.party
                                
                                logger.info(f"[건물 상호작용] 여관 체크 - inventory={self.inventory is not None}, party={party_for_rest is not None}, inventory type={type(self.inventory) if self.inventory is not None else None}, party type={type(party_for_rest) if party_for_rest is not None else None}")
                                
                                if self.inventory is not None and party_for_rest is not None:
                                    from src.ui.rest_ui import open_inn_menu
                                    logger.info(f"[건물 상호작용] 여관 UI 열기")
                                    
                                    # max_floor_reached 가져오기
                                    max_floor = 1
                                    if hasattr(self.exploration, 'game_stats') and 'max_floor_reached' in self.exploration.game_stats:
                                        max_floor = self.exploration.game_stats['max_floor_reached']
                                    elif hasattr(self.exploration, 'floor_number'):
                                        max_floor = self.exploration.floor_number
                                    
                                    open_inn_menu(console, context, party_for_rest, self.inventory, max_floor)
                                else:
                                    logger.warning(f"[건물 상호작용] 여관을 열 수 없습니다. inventory={self.inventory is not None}, party={party_for_rest is not None}")
                                    self.add_message("파티 정보가 없어 여관을 사용할 수 없습니다.")
                            elif building.building_type == BuildingType.ALCHEMY_LAB:
                                # 연금술 실험실: 연금술 UI 열기
                                if self.inventory is not None:
                                    from src.ui.alchemy_ui import open_alchemy_lab
                                    floor_level = self.exploration.floor_number if hasattr(self.exploration, 'floor_number') else 1
                                    
                                    # 파티 정보 가져오기
                                    party_for_alchemy = self.party
                                    if not party_for_alchemy and hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'party'):
                                        party_for_alchemy = self.exploration.player.party
                                    
                                    logger.info(f"[건물 상호작용] 연금술 실험실 UI 열기 (층수: {floor_level})")
                                    try:
                                        open_alchemy_lab(console, context, self.inventory, floor_level, party=party_for_alchemy)
                                        logger.info(f"[건물 상호작용] 연금술 실험실 UI 열기 성공")
                                    except Exception as ui_error:
                                        logger.error(f"[건물 상호작용] 연금술 실험실 UI 열기 오류: {ui_error}", exc_info=True)
                                        self.add_message(f"연금술 실험실을 열 수 없습니다: {ui_error}")
                                else:
                                    logger.warning(f"[건물 상호작용] 인벤토리가 없어 연금술 실험실을 열 수 없습니다.")
                                    self.add_message("인벤토리가 없어 연금술 실험실을 사용할 수 없습니다.")
                            elif building.building_type == BuildingType.QUEST_BOARD:
                                # 퀘스트 게시판: 퀘스트 UI 열기
                                from src.quest.quest_manager import get_quest_manager
                                quest_manager = get_quest_manager()
                                
                                # 플레이어 레벨 가져오기
                                player_level = 1
                                if hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'party'):
                                    if self.exploration.player.party:
                                        first_member = self.exploration.player.party[0]
                                        if hasattr(first_member, 'level'):
                                            player_level = first_member.level
                                elif hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'level'):
                                    player_level = self.exploration.player.level
                                
                                logger.info(f"[건물 상호작용] 퀘스트 게시판 UI 열기 (플레이어 레벨: {player_level})")
                                try:
                                    from src.ui.quest_board_ui import open_quest_board
                                    open_quest_board(console, context, quest_manager, player_level)
                                    logger.info(f"[건물 상호작용] 퀘스트 게시판 UI 열기 성공")
                                except Exception as ui_error:
                                    logger.error(f"[건물 상호작용] 퀘스트 게시판 UI 열기 오류: {ui_error}", exc_info=True)
                                    self.add_message(f"퀘스트 게시판을 열 수 없습니다: {ui_error}")
                            elif building.building_type == BuildingType.STORAGE:
                                # 창고: 창고 UI 열기
                                if self.inventory is not None and town_manager is not None:
                                    # 마을 창고 우선 확인
                                    if hasattr(town_manager, 'get_storage_inventory'):
                                        storage_inventory = town_manager.get_storage_inventory()
                                        logger.info(f"[건물 상호작용] 마을 창고 UI 열기 (보관 아이템: {len(storage_inventory)}개)")
                                    elif hasattr(town_manager, 'get_hub_storage'):
                                        # 하위 호환성
                                        storage_inventory = town_manager.get_hub_storage()
                                        logger.info(f"[건물 상호작용] 창고 UI 열기 (보관 아이템: {len(storage_inventory)}개)")
                                    else:
                                        storage_inventory = []
                                        logger.warning("[건물 상호작용] 창고 저장소 메서드를 찾을 수 없습니다")

                                    try:
                                        from src.ui.storage_ui import open_storage
                                        # StorageUI가 알아서 적절한 저장소를 사용할 것이므로 None 전달
                                        open_storage(console, context, self.inventory, None, town_manager)
                                        logger.info(f"[건물 상호작용] 창고 UI 열기 성공")
                                    except Exception as ui_error:
                                        logger.error(f"[건물 상호작용] 창고 UI 열기 오류: {ui_error}", exc_info=True)
                                        self.add_message(f"창고를 열 수 없습니다: {ui_error}")
                                else:
                                    logger.warning(f"[건물 상호작용] 인벤토리 또는 town_manager가 없어 창고를 열 수 없습니다.")
                                    self.add_message("창고를 사용할 수 없습니다.")
                            elif building.building_type == BuildingType.GUILD_HALL:
                                # 모험가 길드: 정보 UI 열기 (간단한 메시지 박스)
                                from src.ui.game_menu import show_message
                                guild_message = interaction_result.get('message', '모험가 길드에 오신 것을 환영합니다!')
                                logger.info(f"[건물 상호작용] 모험가 길드")
                                show_message(console, context, guild_message)
                            elif building.building_type == BuildingType.FOUNTAIN:
                                # 분수대: 파티 전체 HP/MP 20% 회복 (부활 포함)
                                # 마을 방문마다 1번만 사용 가능
                                from src.ui.game_menu import show_message
                                from src.audio import play_sfx
                                
                                if self.fountain_used:
                                    # 이미 사용한 경우
                                    show_message(console, context, "분수대의 힘이 이미 소진되었습니다.\n다음 마을 방문 시 다시 사용할 수 있습니다.")
                                    logger.info("[건물 상호작용] 분수대 - 이미 사용됨")
                                else:
                                    # 파티 정보 가져오기
                                    party_to_heal = self.party
                                    if not party_to_heal and hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'party'):
                                        party_to_heal = self.exploration.player.party
                                    
                                    if party_to_heal:
                                        recovered_count = 0
                                        for member in party_to_heal:
                                            # HP 20% 회복 (최소 1)
                                            heal_amount = max(1, int(member.max_hp * 0.2))
                                            member.heal(heal_amount, can_revive=True)
                                            
                                            # MP 20% 회복 (최소 1)
                                            mp_amount = max(1, int(member.max_mp * 0.2))
                                            member.restore_mp(mp_amount)
                                            
                                            recovered_count += 1
                                        
                                        # 사용 플래그 설정
                                        self.fountain_used = True
                                        play_sfx("ui", "heal")
                                        logger.info(f"[건물 상호작용] 분수대 - 파티원 {recovered_count}명 회복 완료 (사용 플래그 설정)")
                                        show_message(console, context, "분수대의 신비한 힘으로 파티원의 HP와 MP가 회복되었습니다.\n(HP/MP 20% 회복, 부활 포함)")
                                    else:
                                        logger.warning("[건물 상호작용] 분수대 - 파티 정보 없음")
                                        show_message(console, context, "분수대의 맑은 물이 흐르고 있습니다.")
                            else:
                                # 기타 건물은 메시지만 표시
                                from src.ui.game_menu import show_message
                                message = interaction_result.get('message', f"{building.name}에 입장했습니다.")
                                show_message(console, context, message)
                        except Exception as e:
                            logger.error(f"[건물 상호작용] UI 열기 오류: {e}", exc_info=True)
                            self.add_message(f"{building.name} 상호작용 중 오류가 발생했습니다: {e}")
                    else:
                        logger.warning("town_manager를 찾을 수 없습니다.")
                        self.add_message(f"{building.name}에 입장했습니다.")
            return
        
        # NPC 상호작용은 대화 창으로 처리 (로그에 표시하지 않음)
        if result.event == ExplorationEvent.NPC_INTERACTION:
            if console and context and result.data:
                # 기존 화면 먼저 렌더링 (대화 창 위에 표시하기 위해)
                if hasattr(self, 'render'):
                    self.render(console)
                    context.present(console)
                
                from src.ui.npc_dialog_ui import show_npc_dialog, NPCChoice
                
                npc_subtype = result.data.get("npc_subtype", result.data.get("npc_type", "unknown"))
                npc_name = self._get_npc_name(npc_subtype)
                
                # 이미 상호작용한 NPC는 메시지만 표시
                if result.data.get("already_interacted", False):
                    show_npc_dialog(console, context, npc_name, result.message)
                else:
                    # 선택지가 있는 NPC 처리
                    choices = self._get_npc_choices(result, npc_subtype, console, context)
                    if choices:
                        choice_index = show_npc_dialog(console, context, npc_name, result.message, choices)
                        # 선택지 콜백은 show_npc_dialog 내부에서 처리됨
                    else:
                        # 선택지 없이 대화만 표시
                        show_npc_dialog(console, context, npc_name, result.message)
            return

        if result.message:
            self.add_message(result.message)

        if result.event == ExplorationEvent.COMBAT:
            # Debug: 전투 이벤트 감지
            self.combat_requested = True
            # 전투에 참여할 적들 저장
            if result.data:
                if "num_enemies" in result.data:
                    self.combat_num_enemies = result.data["num_enemies"]
                    # Debug: 전투 적 수
                if "enemies" in result.data:
                    self.combat_enemies = result.data["enemies"]
                    # Debug: 맵 적 엔티티
                # 멀티플레이: 참여자 정보 저장
                if "participants" in result.data:
                    self.combat_participants = result.data["participants"]
                    logger.info(f"멀티플레이 전투 참여자: {len(self.combat_participants)}명")
                # 멀티플레이: 전투 위치 저장
                if hasattr(self.exploration, 'player'):
                    self.combat_position = (self.exploration.player.x, self.exploration.player.y)

        elif result.event == ExplorationEvent.TRAP_TRIGGERED:
            # 함정 데미지는 exploration 시스템에서 이미 적용됨
            # 추가 UI 처리 없음
            logger.debug("함정 발동 - 데미지 적용됨")

        elif result.event == ExplorationEvent.HEAL:
            # 회복은 exploration 시스템에서 이미 적용됨
            # 추가 UI 처리 없음
            logger.debug("회복 이벤트 - HP 회복됨")

        elif result.event == ExplorationEvent.TELEPORT:
            self.add_message(f"위치: ({self.exploration.player.x}, {self.exploration.player.y})")

    def _find_all_nearby_harvestables(self):
        """
        플레이어 주변의 모든 채집 가능한 오브젝트 찾기
        (요리솥은 제외)

        Returns:
            채집 가능한 HarvestableObject 리스트
        """
        from src.gathering.harvestable import HarvestableType

        player_x = self.exploration.player.x
        player_y = self.exploration.player.y

        # 인접 범위 (맨하탄 거리 1~2칸)
        max_distance = 2
        
        found_harvestables = []

        for harvestable in self.exploration.dungeon.harvestables:
            # 요리솥은 채집이 아니라 요리 UI를 열어야 함
            if harvestable.object_type == HarvestableType.COOKING_POT:
                continue

            # 맨하탄 거리 계산
            dx = abs(harvestable.x - player_x)
            dy = abs(harvestable.y - player_y)
            
            # 대각선 거리도 포함하여 정확한 인접 체크 (체비쇼프 거리)
            chebyshev_distance = max(dx, dy)

            # 범위 내이면 추가
            if chebyshev_distance <= max_distance:
                # 이미 이 플레이어가 채집한 오브젝트는 제외
                player_id = None
                if hasattr(self.exploration, 'local_player_id'):
                    player_id = self.exploration.local_player_id
                if not harvestable.can_harvest(player_id):
                    continue
                    
                found_harvestables.append(harvestable)

        return found_harvestables

    def _find_nearby_harvestable(self):
        """
        플레이어 주변의 채집 가능한 오브젝트 찾기
        (요리솥은 제외 - 별도 상호작용 필요)

        Returns:
            가장 가까운 HarvestableObject 또는 None
        """
        from src.gathering.harvestable import HarvestableType

        player_x = self.exploration.player.x
        player_y = self.exploration.player.y

        # 인접 범위 (맨하탄 거리 1~2칸)
        max_distance = 2

        closest_harvestable = None
        closest_distance = max_distance + 1

        for harvestable in self.exploration.dungeon.harvestables:
            # 요리솥은 채집이 아니라 요리 UI를 열어야 함
            if harvestable.object_type == HarvestableType.COOKING_POT:
                continue

            # 맨하탄 거리 계산
            dx = abs(harvestable.x - player_x)
            dy = abs(harvestable.y - player_y)
            
            # 대각선 거리도 포함하여 정확한 인접 체크 (체비쇼프 거리)
            # 맨하탄 거리(dx+dy) 대신 max(dx, dy)를 사용하여 대각선도 거리 1로 처리
            chebyshev_distance = max(dx, dy)

            # 범위 내이고 더 가까우면 선택
            if chebyshev_distance <= max_distance and chebyshev_distance < closest_distance:
                # 이미 이 플레이어가 채집한 오브젝트는 제외 (멀티플레이: 개인 보상)
                # 중요: 거리 조건 먼저 체크 후 채집 가능 여부 확인 (최적화)
                player_id = None
                if hasattr(self.exploration, 'local_player_id'):
                    player_id = self.exploration.local_player_id
                if not harvestable.can_harvest(player_id):
                    continue
                    
                closest_harvestable = harvestable
                closest_distance = chebyshev_distance

        return closest_harvestable

    def _find_nearby_cooking_pot(self):
        """
        플레이어 주변의 요리솥 찾기

        Returns:
            가장 가까운 요리솥 HarvestableObject 또는 None
        """
        from src.gathering.harvestable import HarvestableType

        player_x = self.exploration.player.x
        player_y = self.exploration.player.y

        # 인접 범위 (맨하탄 거리 1~2칸)
        max_distance = 2

        logger.debug(f"요리솥 찾기 시작 - 플레이어 위치: ({player_x}, {player_y}), 채집 오브젝트 수: {len(self.exploration.dungeon.harvestables)}")

        for harvestable in self.exploration.dungeon.harvestables:
            # 요리솥만 찾기
            if harvestable.object_type != HarvestableType.COOKING_POT:
                continue

            # 맨하탄 거리 계산
            dx = abs(harvestable.x - player_x)
            dy = abs(harvestable.y - player_y)

            # 대각선 포함 거리 (체비쇼프 거리)
            chebyshev_distance = max(dx, dy)

            logger.debug(f"요리솥 발견: 위치 ({harvestable.x}, {harvestable.y}), 거리: {chebyshev_distance}")

            # 범위 내이면 반환
            if chebyshev_distance <= max_distance:
                logger.info(f"요리솥 사용 가능: 위치 ({harvestable.x}, {harvestable.y}), 거리: {chebyshev_distance}")
                return harvestable

        logger.debug("주변에 사용 가능한 요리솥 없음")
        return None

    def render(self, console: tcod.console.Console):
        """렌더링"""
        # 바이옴별 배경 (던전 층에 따라 다름)
        render_space_background(
            console, 
            self.screen_width, 
            self.screen_height,
            context="dungeon",
            floor=self.exploration.floor_number
        )

        # 제목 - 마을인 경우 "마을"로 표시, 그 외는 층수로 표시
        is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
        if is_town:
            floor_label = "던전 탐험 - 마을"
        else:
            floor_label = f"던전 탐험 - {self.exploration.floor_number}층"
        console.print(
            self.screen_width // 2 - 15,
            1,
            floor_label,
            fg=(255, 255, 100)
        )

        # 맵 렌더링 (플레이어 중심)
        player = self.exploration.player
        self.map_renderer.render(
            console,
            self.exploration.dungeon,
            camera_x=max(0, player.x - 40),
            camera_y=max(0, player.y - 20),
            view_width=self.screen_width,
            view_height=35
        )

        # 적 위치 표시
        camera_x = max(0, player.x - 40)
        camera_y = max(0, player.y - 20)
        for enemy in self.exploration.enemies:
            # 타일의 탐험 및 시야 상태 확인
            tile = self.exploration.dungeon.get_tile(enemy.x, enemy.y)
            if tile and not tile.explored:
                continue  # 탐험하지 않은 영역의 적은 표시하지 않음
            if tile and not tile.visible:
                continue  # 벽 너머의 적은 표시하지 않음
            
            enemy_screen_x = enemy.x - camera_x
            enemy_screen_y = 5 + (enemy.y - camera_y)
            if 0 <= enemy_screen_x < self.screen_width and 0 <= enemy_screen_y < 40:
                # 적 색상: 보스는 선명한 빨강, 일반 적은 주황색
                enemy_color = (255, 0, 0) if enemy.is_boss else (255, 150, 50)
                console.print(enemy_screen_x, enemy_screen_y, "E", fg=enemy_color)

        # 파밍 오브젝트 위치 표시 (채집 가능한 오브젝트)
        for harvestable in self.exploration.dungeon.harvestables:
            # 타일의 탐험 및 시야 상태 확인
            tile = self.exploration.dungeon.get_tile(harvestable.x, harvestable.y)
            if tile and not tile.explored:
                continue  # 탐험하지 않은 영역의 오브젝트는 표시하지 않음
            if tile and not tile.visible:
                continue  # 벽 너머의 오브젝트는 표시하지 않음
            
            harv_screen_x = harvestable.x - camera_x
            harv_screen_y = 5 + (harvestable.y - camera_y)
            if 0 <= harv_screen_x < self.screen_width and 0 <= harv_screen_y < 40:
                # 채집 오브젝트 표시
                console.print(harv_screen_x, harv_screen_y, harvestable.char, fg=harvestable.color)

        # 플레이어 위치 표시 (적 위에 덮어씀)
        # 멀티플레이: 모든 파티 멤버 렌더링 (플레이어별 색상)
        # 멀티플레이 모드 확인 (여러 방법으로 확인)
        is_multiplayer = False
        if hasattr(self.exploration, 'is_multiplayer'):
            is_multiplayer = self.exploration.is_multiplayer
        elif hasattr(self.exploration, 'session') and self.exploration.session:
            is_multiplayer = True
        else:
            # game_mode_manager로 확인 (가장 확실한 방법)
            from src.multiplayer.game_mode import get_game_mode_manager
            game_mode_manager = get_game_mode_manager()
            if game_mode_manager:
                is_multiplayer = game_mode_manager.is_multiplayer()
        
        if is_multiplayer:
            # 멀티플레이: 모든 플레이어 위치 렌더링 (시야와 관계없이 항상 표시)
            # session.players에서 모든 플레이어 위치 가져오기
            all_players = []
            if hasattr(self.exploration, 'session') and self.exploration.session:
                # session.players에서 모든 플레이어 가져오기
                for player_id, mp_player in self.exploration.session.players.items():
                    if hasattr(mp_player, 'x') and hasattr(mp_player, 'y'):
                        all_players.append({
                            'player_id': player_id,
                            'x': mp_player.x,
                            'y': mp_player.y
                        })
            
            # player_positions도 확인 (백업)
            if hasattr(self.exploration, 'player_positions') and self.exploration.player_positions:
                for player_id, (pos_x, pos_y) in self.exploration.player_positions.items():
                    # 이미 추가된 플레이어는 건너뛰기
                    if not any(p['player_id'] == player_id for p in all_players):
                        all_players.append({
                            'player_id': player_id,
                            'x': pos_x,
                            'y': pos_y
                        })
            
            # 로컬 플레이어도 추가 (party에서 가져오기)
            local_player_id = None
            if hasattr(self.exploration, 'local_player_id'):
                local_player_id = self.exploration.local_player_id
            elif hasattr(self.exploration, 'session') and self.exploration.session:
                local_player_id = getattr(self.exploration.session, 'local_player_id', None)
            
            for member in self.exploration.player.party:
                member_player_id = getattr(member, 'player_id', None)
                # 이미 추가된 플레이어는 건너뛰기
                if not any(p['player_id'] == member_player_id for p in all_players) if member_player_id else True:
                    all_players.append({
                        'player_id': member_player_id,
                        'x': getattr(member, 'x', player.x),
                        'y': getattr(member, 'y', player.y)
                    })
            
            # 모든 플레이어 위치 렌더링 (시야 체크 없이 항상 표시)
            for player_data in all_players:
                player_x = player_data['x']
                player_y = player_data['y']
                player_id = player_data['player_id']
                
                screen_x = player_x - camera_x
                screen_y = 5 + (player_y - camera_y)
                
                # 화면 범위 내에만 렌더링 (시야 체크 없이)
                if 0 <= screen_x < self.screen_width and 0 <= screen_y < 40:
                    # 죽은 플레이어 체크 (session 참조)
                    is_dead = False
                    if hasattr(self.exploration, 'session') and self.exploration.session:
                        if player_id in self.exploration.session.players:
                            p = self.exploration.session.players[player_id]
                            # 파티 전멸 여부 확인
                            # (Player 객체 구조에 따라 다름, 여기서는 간단히 가정)
                            # 만약 Player 객체에 is_alive 속성이 없으면 생존으로 간주
                            if hasattr(p, 'is_party_alive'):
                                # is_party_alive가 메서드인지 속성인지 확인
                                if callable(p.is_party_alive):
                                    if not p.is_party_alive():
                                        is_dead = True
                                else:
                                    if not p.is_party_alive:
                                        is_dead = True
                    
                    # 플레이어 ID 기반 색상 할당
                    player_color = self._get_player_color(player_id)
                    char = "@"
                    
                    if is_dead:
                        player_color = (100, 100, 100) # 회색 (유령)
                        char = "@" # 유령 아이콘 대신 @ 사용 (회색)
                    
                    console.print(screen_x, screen_y, char, fg=player_color)
        else:
            # 싱글플레이: 기본 플레이어 위치 렌더링
            screen_x = player.x - camera_x
            screen_y = 5 + (player.y - camera_y)
            if 0 <= screen_x < self.screen_width and 0 <= screen_y < 40:
                console.print(screen_x, screen_y, "@", fg=(255, 255, 100))

        # 파티 상태 (우측 상단)
        self._render_party_status(console)

        # 메시지 로그 (하단)
        self._render_messages(console)

        # 조작법 (최하단, 로그 패널 밖)
        help_text = "방향키: 이동  Z: 계단 이용  M: 메뉴  I: 인벤토리  ESC: 종료"
        is_multiplayer = (
            self.network_manager is not None or
            (hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer) or
            (hasattr(self.exploration, 'session') and self.exploration.session is not None)
        )
        if is_multiplayer:
            help_text += "  T: 채팅"
        
        # 조작 가이드를 최하단에 배치 (로그 패널 아래)
        console.print(
            2,
            self.screen_height - 2,
            help_text,
            fg=(180, 180, 180)
        )

        # 필드 스킬 UI
        if self.field_skill_ui.is_active:
            self.field_skill_ui.render(console)

        # 채팅 입력창
        if self.chat_input_active:
            self._render_chat_input(console)

        # 종료 확인 대화상자
        if self.quit_confirm_mode:
            self._render_quit_confirm(console)

    def _render_party_status(self, console: tcod.console.Console):
        """파티 상태 렌더링 (전투 UI와 동일한 스타일)"""
        from src.ui.gauge_renderer import get_animation_manager
        
        x = self.screen_width - 30
        y = 3

        console.print(x, y, "[파티 상태]", fg=(100, 255, 100))

        for i, member in enumerate(self.exploration.player.party[:4]):
            # 아군 사이 간격: 3줄 (이름 1줄 + HP 1줄 + MP 1줄 + 여백 1줄 = 4줄씩)
            my = y + 2 + i * 4

            # 이름
            # Character 객체는 name을, PartyMember 객체는 character_name을 사용
            member_name = getattr(member, 'name', getattr(member, 'character_name', 'Unknown'))
            console.print(x, my, f"{i+1}. {member_name[:10]}", fg=(255, 255, 255))

            # HP/MP 값 가져오기
            # Character 객체는 current_hp/max_hp를, PartyMember 객체는 stats를 사용
            current_hp = getattr(member, 'current_hp', None)
            max_hp = getattr(member, 'max_hp', None)
            current_mp = getattr(member, 'current_mp', None)
            max_mp = getattr(member, 'max_mp', None)
            
            if current_hp is None or max_hp is None:
                # PartyMember 객체인 경우 stats에서 가져오기
                stats = getattr(member, 'stats', {})
                current_hp = stats.get('hp', 100)
                max_hp = stats.get('max_hp', 100)
            
            if current_mp is None or max_mp is None:
                stats = getattr(member, 'stats', {})
                current_mp = stats.get('mp', 50)
                max_mp = stats.get('max_mp', 50)
            
            wound_damage = getattr(member, 'wound_damage', 0)
            entity_id = f"field_ally_{i}_{member_name}"
            
            # HP 게이지 (전투 UI와 동일 - 애니메이션 + 상처 표시 + 숫자)
            console.print(x, my + 1, "HP:", fg=(200, 200, 200))
            self.gauge_renderer.render_animated_hp_bar(
                console, x + 4, my + 1, 15,
                current_hp, max_hp, entity_id,
                wound_damage=wound_damage, show_numbers=True
            )
            
            # MP 게이지 (전투 UI와 동일 - 애니메이션 + 숫자)
            console.print(x, my + 2, "MP:", fg=(200, 200, 200))
            self.gauge_renderer.render_animated_mp_bar(
                console, x + 4, my + 2, 15,
                current_mp, max_mp, entity_id,
                show_numbers=True
            )

        # 인벤토리 정보 (파티 상태 아래로 이동)
        inv_y = y + 2 + 4 * min(4, len(self.exploration.player.party)) + 1
        console.print(x, inv_y, "[소지품]", fg=(200, 200, 255))
        console.print(x + 2, inv_y + 1, f"열쇠: {len(self.exploration.player.keys)}개", fg=(255, 215, 0))
        # 실제 인벤토리 객체의 아이템 수 표시 (slots 사용)
        item_count = len(self.inventory.slots) if self.inventory and hasattr(self.inventory, 'slots') else 0
        console.print(x + 2, inv_y + 2, f"아이템: {item_count}개", fg=(200, 200, 200))

    def _render_messages(self, console: tcod.console.Console):
        """메시지 로그 - 별도 패널로 표시"""
        # 로그 패널 설정 (좌측 하단에 별도 창으로 표시)
        log_panel_width = min(60, self.screen_width // 2)
        log_panel_height = 8
        log_panel_x = 2
        log_panel_y = self.screen_height - log_panel_height - 3  # 조작 가이드 위에 배치
        
        # 로그 패널 테두리
        console.draw_frame(
            log_panel_x - 1,
            log_panel_y - 1,
            log_panel_width + 2,
            log_panel_height + 2,
            "[로그]",
            fg=(150, 150, 150),
            bg=(0, 0, 0)
        )
        
        # 로그 메시지 표시
        visible_messages = self.messages[-self.max_messages:]
        for i, msg in enumerate(visible_messages):
            # 메시지가 패널 너비를 초과하면 자르기
            if len(msg) > log_panel_width - 2:
                msg = msg[:log_panel_width - 5] + "..."
            console.print(
                log_panel_x, 
                log_panel_y + i, 
                msg, 
                fg=(200, 200, 200)
            )

    def _render_quit_confirm(self, console: tcod.console.Console):
        """종료 확인 대화상자"""
        box_width = 50
        box_height = 10
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 박스
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "게임 종료",
            fg=(255, 100, 100),
            bg=(0, 0, 0)
        )

        # 메시지
        msg = "정말로 게임을 종료하시겠습니까?"
        console.print(
            box_x + (box_width - len(msg)) // 2,
            box_y + 3,
            msg,
            fg=(255, 255, 255)
        )

        msg2 = "저장하지 않은 진행 상황은 잃게 됩니다!"
        console.print(
            box_x + (box_width - len(msg2)) // 2,
            box_y + 5,
            msg2,
            fg=(255, 200, 100)
        )

        # 버튼
        y = box_y + 7
        yes_color = (255, 255, 100) if self.quit_confirm_yes else (180, 180, 180)
        no_color = (255, 255, 100) if not self.quit_confirm_yes else (180, 180, 180)

        console.print(
            box_x + 12, y,
            "[ 예 ]" if self.quit_confirm_yes else "  예  ",
            fg=yes_color
        )

        console.print(
            box_x + 28, y,
            "[아니오]" if not self.quit_confirm_yes else " 아니오 ",
            fg=no_color
        )

        # 도움말
        console.print(
            box_x + (box_width - 30) // 2,
            box_y + box_height - 1,
            "← →: 선택  Z: 확인  X: 취소",
            fg=(150, 150, 150)
        )

    def _render_chat_input(self, console: tcod.console.Console):
        """채팅 입력창 렌더링"""
        box_width = min(70, self.screen_width - 10)
        box_height = 5
        box_x = (self.screen_width - box_width) // 2
        box_y = self.screen_height - box_height - 5
        
        # 배경 박스
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "채팅",
            fg=(100, 200, 255),
            bg=(0, 0, 0)
        )
        
        # 입력 텍스트 표시 (커서 포함)
        input_text = self.chat_input_text + "_"
        display_text = input_text[-box_width + 6:] if len(input_text) > box_width - 6 else input_text
        console.print(
            box_x + 2,
            box_y + 2,
            display_text,
            fg=(255, 255, 255)
        )
        
        # 안내 텍스트
        console.print(
            box_x + 2,
            box_y + box_height - 2,
            "Enter: 전송  ESC: 취소",
            fg=(150, 150, 150)
        )
    
    def _send_chat_message(self, message: str):
        """채팅 메시지 전송"""
        if not self.network_manager or not self.local_player_id:
            return
        
        try:
            from src.multiplayer.protocol import MessageBuilder
            import asyncio
            
            chat_msg = MessageBuilder.chat_message(self.local_player_id, message)
            
            # 비동기 전송
            if self.network_manager.is_host:
                # 호스트: 브로드캐스트
                if hasattr(self.network_manager, '_server_event_loop') and self.network_manager._server_event_loop:
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.broadcast(chat_msg),
                        self.network_manager._server_event_loop
                    )
                else:
                    logger.warning("서버 이벤트 루프를 찾을 수 없습니다. 채팅 메시지 전송 스킵")
            else:
                # 클라이언트: 호스트에게 전송
                if hasattr(self.network_manager, '_client_event_loop') and self.network_manager._client_event_loop:
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.send(chat_msg),
                        self.network_manager._client_event_loop
                    )
                else:
                    logger.warning("클라이언트 이벤트 루프를 찾을 수 없습니다. 채팅 메시지 전송 스킵")
        except Exception as e:
            logger.error(f"채팅 메시지 전송 실패: {e}", exc_info=True)

    def _get_player_color(self, player_id: Optional[str] = None) -> Tuple[int, int, int]:
        """
        플레이어 ID 기반 색상 할당
        
        Args:
            player_id: 플레이어 ID (None이면 첫 번째 플레이어 색상)
        
        Returns:
            RGB 튜플 색상
        """
        # 플레이어별 색상 팔레트 (구분하기 쉬운 색상들)
        color_palette = [
            (255, 100, 100),  # 빨간색
            (100, 255, 100),  # 초록색
            (100, 100, 255),  # 파란색
            (255, 255, 100),  # 노란색
            (255, 100, 255),  # 마젠타
            (100, 255, 255),  # 시안
            (255, 150, 100),  # 주황색
            (200, 100, 255),  # 보라색
        ]
        
        if player_id is None:
            # player_id가 없으면 첫 번째 색상 사용
            return color_palette[0]
        
        # player_id를 기반으로 색상 선택 (해시 사용)
        # 같은 player_id는 항상 같은 색상을 가짐
        hash_value = hash(player_id)
        color_index = abs(hash_value) % len(color_palette)
        return color_palette[color_index]

    def _get_npc_name(self, npc_subtype: str) -> str:
        """NPC 서브타입에 따른 이름 반환"""
        npc_names = {
            "time_researcher": "시공 연구자",
            "timeline_survivor": "타임라인 생존자",
            "space_explorer": "우주 탐험가",
            "merchant": "상인",
            "refugee": "난민",
            "time_thief": "시공 도둑",
            "distortion_entity": "왜곡된 존재",
            "betrayer": "배신자",
            "mysterious_merchant": "신비한 상인",
            "time_mage": "시공 마법사",
            "future_self": "미래의 자신",
            "corrupted_survivor": "오염된 생존자",
            "ancient_guardian": "고대 수호자",
            "void_wanderer": "공허 방랑자",
            "helpful": "친절한 방랑자",
            "harmful": "의심스러운 존재",
            "neutral": "무명의 여행자"
        }
        return npc_names.get(npc_subtype, "NPC")
    
    def _get_npc_choices(self, result: ExplorationResult, npc_subtype: str, console, context) -> Optional[List]:
        """NPC 서브타입에 따른 선택지 반환"""
        from src.ui.npc_dialog_ui import NPCChoice
        
        choices = []
        
        # 시공 연구자: 도움 종류 선택
        if npc_subtype == "time_researcher":
            def choose_heal():
                heal_amount = 80 + self.exploration.floor_number * 15
                for member in self.exploration.player.party:
                    if hasattr(member, 'heal'):
                        member.heal(heal_amount)
                from src.ui.npc_dialog_ui import show_npc_dialog
                show_npc_dialog(
                    console, context,
                    self._get_npc_name(npc_subtype),
                    f"치유 물약을 받았습니다!\n파티가 {heal_amount} HP 회복했습니다!"
                )
            
            def choose_item():
                from src.equipment.item_system import ItemGenerator
                item = ItemGenerator.create_random_drop(self.exploration.floor_number + 2)
                if self.inventory and self.inventory.add_item(item):
                    from src.ui.npc_dialog_ui import show_npc_dialog
                    show_npc_dialog(
                        console, context,
                        self._get_npc_name(npc_subtype),
                        f"{item.name}을(를) 획득했습니다!"
                    )
            
            def choose_mp():
                mp_amount = 30 + self.exploration.floor_number * 5
                for member in self.exploration.player.party:
                    if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                        member.current_mp = min(member.max_mp, member.current_mp + mp_amount)
                from src.ui.npc_dialog_ui import show_npc_dialog
                show_npc_dialog(
                    console, context,
                    self._get_npc_name(npc_subtype),
                    f"마나 회복제를 받았습니다!\n파티가 {mp_amount} MP 회복했습니다!"
                )
            
            choices = [
                NPCChoice("치유 물약 받기", choose_heal),
                NPCChoice("장비 받기", choose_item),
                NPCChoice("마나 회복제 받기", choose_mp)
            ]
        
        # 상인: 구매/판매
        elif npc_subtype in ["merchant", "mysterious_merchant"]:
            def choose_buy():
                from src.ui.shop_ui import open_shop
                open_shop(console, context, self.inventory)
            
            def choose_sell():
                # TODO: 판매 모드 구현
                from src.ui.npc_dialog_ui import show_npc_dialog
                show_npc_dialog(
                    console, context,
                    self._get_npc_name(npc_subtype),
                    "판매 기능은 아직 구현되지 않았습니다."
                )
            
            choices = [
                NPCChoice("구매하기", choose_buy),
                NPCChoice("판매하기", choose_sell),
                NPCChoice("떠나기", None)
            ]
        
        # 배신자: 신뢰하기/거절
        elif npc_subtype == "betrayer":
            def choose_trust():
                # 배신: 데미지 받음
                damage = 100 + self.exploration.floor_number * 20
                for member in self.exploration.player.party:
                    if hasattr(member, 'take_damage'):
                        member.take_damage(damage)
                from src.ui.npc_dialog_ui import show_npc_dialog
                show_npc_dialog(
                    console, context,
                    self._get_npc_name(npc_subtype),
                    f"배신당했습니다!\n파티가 {damage} 데미지를 입었습니다!"
                )
            
            def choose_refuse():
                from src.ui.npc_dialog_ui import show_npc_dialog
                show_npc_dialog(
                    console, context,
                    self._get_npc_name(npc_subtype),
                    "신중한 선택이었습니다.\nNPC가 떠났습니다."
                )
            
            choices = [
                NPCChoice("신뢰하기", choose_trust),
                NPCChoice("거절하기", choose_refuse)
            ]
        
        return choices if choices else None


def run_exploration(
    console: tcod.console.Console,
    context: tcod.context.Context,
    exploration: ExplorationSystem,
    inventory=None,
    party=None,
    play_bgm_on_start: bool = True,
    network_manager=None,
    local_player_id=None
) -> str:
    """
    탐험 실행

    Args:
        play_bgm_on_start: 탐험 시작 시 BGM 재생 여부 (기본 True, 전투 후 복귀 시 False)

    Returns:
        "quit", "combat", "floor_up", "floor_down"
    """
    ui = WorldUI(console.width, console.height, exploration, inventory, party, network_manager, local_player_id)
    handler = InputHandler()

    logger.info(f"탐험 시작: {exploration.floor_number}층")

    # 채팅 메시지 수신 핸들러 등록 (멀티플레이어일 때만)
    if network_manager:
        from src.multiplayer.protocol import MessageType
        host_disconnected = {"value": False}
        
        def handle_chat_message(msg, sender_id):
            """채팅 메시지 수신 핸들러"""
            try:
                player_id = msg.player_id
                message = msg.data.get("message", "")
                
                # 플레이어 이름 가져오기
                player_name = "플레이어"
                if hasattr(exploration, 'session') and exploration.session:
                    if player_id in exploration.session.players:
                        player_name = exploration.session.players[player_id].player_name
                
                # 채팅 메시지 표시
                chat_text = f"[{player_name}]: {message}"
                ui.add_message(chat_text)
                logger.info(f"채팅 메시지 수신: {chat_text}")
            except Exception as e:
                logger.error(f"채팅 메시지 핸들러 오류: {e}", exc_info=True)
        
        def handle_player_left(msg, sender_id):
            """플레이어 나감 핸들러"""
            try:
                player_id = msg.data.get("player_id") or msg.player_id
                if player_id and hasattr(exploration, 'session') and exploration.session:
                    if player_id in exploration.session.players:
                        removed_player = exploration.session.players[player_id]
                        is_host_player = removed_player.is_host
                        player_name = getattr(removed_player, 'player_name', f"플레이어 {player_id}")
                        exploration.session.remove_player(player_id)
                        logger.info(f"플레이어 나감: {player_name} ({player_id})")
                        
                        # 알림 메시지 추가
                        if is_host_player:
                            ui.add_message(f"⚠ 호스트({player_name})가 나갔습니다!")
                            host_disconnected["value"] = True
                        else:
                            ui.add_message(f"⚠ {player_name}이(가) 나갔습니다!")
            except Exception as e:
                logger.error(f"플레이어 나감 핸들러 오류: {e}", exc_info=True)
        
        network_manager.register_handler(MessageType.CHAT_MESSAGE, handle_chat_message)
        network_manager.register_handler(MessageType.PLAYER_LEFT, handle_player_left)
        logger.info("채팅 메시지 및 플레이어 나감 핸들러 등록 완료")

    # 봇 관련 코드 제거됨

    # 남은 이벤트 제거 (불러오기 등에서 남은 키 입력 방지)
    tcod.event.get()

    # BGM 재생 (매 층마다 바뀜, 전투 후 복귀 시에는 재생하지 않음)
    if play_bgm_on_start:
        # 마을인 경우 마을 BGM 재생
        if hasattr(exploration, 'is_town') and exploration.is_town:
            logger.info("마을 BGM 재생: town.ogg")
            # town.ogg 파일 직접 재생
            from src.audio.audio_manager import get_audio_manager
            audio_manager = get_audio_manager()
            # config.yaml에 "town" 트랙이 정의되어 있으면 사용, 없으면 직접 파일명 사용
            if audio_manager.config.get("audio.bgm.tracks.town"):
                play_bgm("town", loop=True, fade_in=True)
            else:
                # 직접 파일명 사용
                audio_manager.play_bgm_file("town.ogg", loop=True, fade_in=True)
        else:
            # 던전인 경우 바이옴별 BGM 재생
            floor = exploration.floor_number
            # 바이옴 계산 (매 층마다 변경: 10개 바이옴 순환)
            biome_index = (floor - 1) % 10
            biome_track = f"biome_{biome_index}"
            
            logger.info(f"층 {floor} -> 바이옴 {biome_index}, BGM: {biome_track}")
            play_bgm(biome_track)

    # 업데이트 콜백 함수 정의
    def update_game_state():
        """게임 상태 업데이트 (백그라운드)"""
        # 핫 리로드 체크 (개발 모드일 때만)
        try:
            from src.core.config import get_config
            config = get_config()
            if config.development_mode:
                from src.core.hot_reload import check_and_reload
                reloaded = check_and_reload()
                if reloaded:
                    logger.info(f"📦 [탐험] 재로드된 모듈: {', '.join(reloaded)}")
        except Exception:
            pass  # 핫 리로드 오류는 무시
        
        # 멀티플레이: 시간 기반 적 이동 업데이트 (2초마다)
        current_time = time.time()
        
        # 적 이동 업데이트 (호스트만)
        if hasattr(exploration, 'is_multiplayer') and exploration.is_multiplayer:
            if hasattr(exploration, 'enemy_sync') and exploration.enemy_sync:
                # last_enemy_update를 exploration에 저장하여 유지
                if not hasattr(exploration, '_last_enemy_update'):
                    exploration._last_enemy_update = 0.0
                
                if current_time - exploration._last_enemy_update >= 2.0:
                    if exploration.is_host and hasattr(exploration, '_move_all_enemies'):
                        exploration._move_all_enemies()
                    exploration._last_enemy_update = current_time
            
            # 봇 관련 코드 제거됨
        
        # 환경 효과 업데이트 (플레이어가 같은 타일에 머물러 있을 때도 적용)
        try:
            effect_message = exploration.update_environmental_effects()
            if effect_message and hasattr(ui, 'add_message'):
                ui.add_message(effect_message)
        except Exception as e:
            logger.warning(f"환경 효과 업데이트 오류: {e}")

    # WorldUI에 업데이트 콜백 설정
    ui.on_update = update_game_state

    while True:
        # 메인 루프에서도 업데이트 실행
        update_game_state()
        
        # ... (기존 코드) ...
        
        # 렌더링
        ui.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait(timeout=0.05):
            action = handler.dispatch(event)
            key_event = event if isinstance(event, tcod.event.KeyDown) else None

            if action or key_event:
                # Debug: 액션 수신
                done = ui.handle_input(action, console, context, key_event)
                # Debug: handle_input 반환
                if done:
                    # Debug: 루프 탈출
                    break
            else:
                # action이 None인 경우 (키 입력 없음)
                # 다음 이벤트 처리로 넘어감
                continue
        
        # 입력 처리 후 즉시 상태 체크 (전투 요청 확인)
        if ui.combat_requested:
            # 전투 데이터 반환: (적 수, 맵 적 엔티티, 참여자, 위치)
            combat_data = {
                "num_enemies": ui.combat_num_enemies,
                "enemies": ui.combat_enemies,
                "participants": getattr(ui, 'combat_participants', None),
                "position": getattr(ui, 'combat_position', None)
            }
            return ("combat", combat_data)


            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return ("quit", None)

        # 호스트 나감 체크 (멀티플레이어)
        if network_manager and 'host_disconnected' in locals() and host_disconnected.get("value", False):
            logger.warning("호스트가 나갔습니다. 메인 메뉴로 돌아갑니다.")
            # 연결 종료
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(network_manager.disconnect())
                else:
                    loop.run_until_complete(network_manager.disconnect())
            except Exception as e:
                logger.error(f"연결 종료 오류: {e}", exc_info=True)
            return ("quit", None)
        
        # 상태 체크
        # Debug: 상태 체크
        if ui.quit_requested:
            return ("quit", None)
        elif ui.combat_requested:
            # Debug: 전투 반환
            # 전투 데이터 반환: (적 수, 맵 적 엔티티, 참여자, 위치)
            combat_data = {
                "num_enemies": ui.combat_num_enemies,
                "enemies": ui.combat_enemies,
                "participants": getattr(ui, 'combat_participants', None),
                "position": getattr(ui, 'combat_position', None)
            }
            return ("combat", combat_data)
        elif ui.floor_change_requested:
            return (ui.floor_change_requested, None)
