"""
월드 탐험 UI

플레이어가 던전을 돌아다니는 화면
"""

from typing import List, Optional, Tuple
import tcod

from src.world.exploration import ExplorationSystem, ExplorationEvent, ExplorationResult
from src.world.map_renderer import MapRenderer
from src.ui.input_handler import InputHandler, GameAction
from src.ui.gauge_renderer import GaugeRenderer
from src.ui.tcod_display import render_space_background
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
        local_player_id=None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.exploration = exploration
        self.inventory = inventory
        self.party = party
        self.map_renderer = MapRenderer(map_x=0, map_y=5)
        self.gauge_renderer = GaugeRenderer()
        self.network_manager = network_manager  # 멀티플레이: 네트워크 관리자
        self.local_player_id = local_player_id  # 멀티플레이: 로컬 플레이어 ID

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

    def add_message(self, text: str):
        """메시지 추가"""
        self.messages.append(text)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        logger.debug(f"메시지: {text}")

    def handle_input(self, action: GameAction, console=None, context=None, key_event=None) -> bool:
        """
        입력 처리

        Returns:
            True면 종료
        """
        logger.warning(f"[DEBUG] handle_input 호출됨: action={action}")

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

        # T 키로 채팅 입력 시작 (멀티플레이어일 때만)
        if isinstance(key_event, tcod.event.KeyDown) and key_event.sym == tcod.event.KeySym.t:
            is_multiplayer = (
                self.network_manager is not None or
                (hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer) or
                (hasattr(self.exploration, 'session') and self.exploration.session is not None)
            )
            if is_multiplayer:
                self.chat_input_active = True
                self.chat_input_text = ""
                return False

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
            logger.warning(f"[DEBUG] 메뉴 열기 요청")
            if self.inventory is not None and self.party is not None and console is not None and context is not None:
                from src.ui.game_menu import open_game_menu, MenuOption
                logger.warning("[DEBUG] 게임 메뉴 열기")
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
            logger.warning(f"[DEBUG] 인벤토리 열기 요청")
            if self.inventory is not None and self.party is not None and console is not None and context is not None:
                from src.ui.inventory_ui import open_inventory
                logger.warning("[DEBUG] 인벤토리 열기 시도")
                open_inventory(console, context, self.inventory, self.party, self.exploration)
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
                # 쿨타임 체크
                if current_time - self.last_move_time < self.move_cooldown:
                    # 쿨타임 중이면 이동 무시
                    return False
                # 쿨타임 통과 시 이동 시간 업데이트
                self.last_move_time = current_time
            
            result = self.exploration.move_player(dx, dy)
            if result is None:
                logger.warning(f"[DEBUG] 이동 결과: None (이벤트 없음)")
                # None인 경우 기본 결과 생성
                from src.world.exploration import ExplorationResult, ExplorationEvent
                result = ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NONE,
                    message=""
                )
            else:
                logger.warning(f"[DEBUG] 이동 결과: event={result.event}")
            self._handle_exploration_result(result, console, context)
            # 전투가 트리거되면 즉시 루프 탈출
            if self.combat_requested:
                logger.warning(f"[DEBUG] 전투 요청됨! 루프 탈출")
                return True

        # 상호작용 (E키 또는 Z키)
        elif action == GameAction.INTERACT or action == GameAction.CONFIRM:
            # 우선순위 1: 요리솥
            nearby_cooking_pot = self._find_nearby_cooking_pot()
            if nearby_cooking_pot:
                if console is not None and context is not None and self.inventory is not None:
                    from src.ui.cooking_ui import open_cooking_pot

                    # 요리 UI 열기
                    logger.info("요리솥 발견! 요리 UI 열기")
                    # 요리솥에서 요리할 때는 보너스 적용
                    open_cooking_pot(console, context, self.inventory, is_cooking_pot=True)
                    return False
                else:
                    self.add_message("요리솥을 사용할 수 없습니다.")
                    return False

            # 우선순위 2: 채집 오브젝트
            nearby_harvestable = self._find_nearby_harvestable()
            if nearby_harvestable:
                # 채집 오브젝트가 있으면 채집 실행
                if console is not None and context is not None and self.inventory is not None:
                    from src.ui.gathering_ui import harvest_object, show_gathering_prompt

                    # 채집 확인 프롬프트
                    if show_gathering_prompt(console, context, nearby_harvestable):
                        # 채집 실행 (멀티플레이어 동기화를 위해 exploration 전달)
                        success = harvest_object(console, context, nearby_harvestable, self.inventory, exploration=self.exploration)
                        if success:
                            logger.info(f"채집 성공: {nearby_harvestable.object_type.display_name}")
                        return False
                else:
                    logger.warning("채집 불가: console, context, inventory가 필요합니다")
                return False

            # 우선순위 3: 계단 이동 (Z키만)
            if action == GameAction.CONFIRM:
                tile = self.exploration.dungeon.get_tile(
                    self.exploration.player.x,
                    self.exploration.player.y
                )

                if tile:
                    from src.world.tile import TileType
                    from src.audio import play_sfx
                    if tile.tile_type == TileType.STAIRS_DOWN:
                        play_sfx("world", "stairs_down")
                        self.floor_change_requested = "floor_down"
                        self.add_message("아래층으로 내려갑니다...")
                        return True
                    elif tile.tile_type == TileType.STAIRS_UP:
                        play_sfx("world", "stairs_up")
                        self.floor_change_requested = "floor_up"
                        self.add_message("위층으로 올라갑니다...")
                        return True

            # E키를 눌렀지만 주변에 아무것도 없을 때
            if action == GameAction.INTERACT:
                self.add_message("주변에 상호작용할 것이 없습니다.")

        return False

    def _handle_exploration_result(self, result: ExplorationResult, console=None, context=None):
        """탐험 결과 처리"""
        logger.warning(f"[DEBUG] 탐험 결과: event={result.event}, message={result.message}")

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
            logger.warning(f"[DEBUG] 전투 이벤트 감지! combat_requested를 True로 설정")
            self.combat_requested = True
            # 전투에 참여할 적들 저장
            if result.data:
                if "num_enemies" in result.data:
                    self.combat_num_enemies = result.data["num_enemies"]
                    logger.warning(f"[DEBUG] 전투 적 수: {self.combat_num_enemies}마리")
                if "enemies" in result.data:
                    self.combat_enemies = result.data["enemies"]
                    logger.warning(f"[DEBUG] 맵 적 엔티티: {len(self.combat_enemies)}개")
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

            # 이미 채집한 오브젝트는 제외
            if harvestable.harvested:
                continue

            # 맨하탄 거리 계산
            distance = abs(harvestable.x - player_x) + abs(harvestable.y - player_y)

            # 범위 내이고 더 가까우면 선택
            if distance <= max_distance and distance < closest_distance:
                closest_harvestable = harvestable
                closest_distance = distance

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

        for harvestable in self.exploration.dungeon.harvestables:
            # 요리솥만 찾기
            if harvestable.object_type != HarvestableType.COOKING_POT:
                continue

            # 맨하탄 거리 계산
            distance = abs(harvestable.x - player_x) + abs(harvestable.y - player_y)

            # 범위 내이면 반환
            if distance <= max_distance:
                return harvestable

        return None

    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목
        console.print(
            self.screen_width // 2 - 15,
            1,
            f"던전 탐험 - {self.exploration.floor_number}층",
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
                    # 플레이어 ID 기반 색상 할당
                    player_color = self._get_player_color(player_id)
                    console.print(screen_x, screen_y, "@", fg=player_color)
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

        # 조작법 (하단)
        help_text = "방향키: 이동  Z: 계단 이용  M: 메뉴  I: 인벤토리  ESC: 종료"
        is_multiplayer = (
            self.network_manager is not None or
            (hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer) or
            (hasattr(self.exploration, 'session') and self.exploration.session is not None)
        )
        if is_multiplayer:
            help_text += "  T: 채팅"
        console.print(
            5,
            self.screen_height - 2,
            help_text,
            fg=(180, 180, 180)
        )

        # 채팅 입력창
        if self.chat_input_active:
            self._render_chat_input(console)

        # 종료 확인 대화상자
        if self.quit_confirm_mode:
            self._render_quit_confirm(console)

    def _render_party_status(self, console: tcod.console.Console):
        """파티 상태 렌더링 (간단)"""
        x = self.screen_width - 30
        y = 3

        console.print(x, y, "[파티 상태]", fg=(100, 255, 100))

        for i, member in enumerate(self.exploration.player.party[:4]):
            my = y + 2 + i * 2

            # 이름과 HP 게이지를 한 줄에 표시
            # Character 객체는 name을, PartyMember 객체는 character_name을 사용
            member_name = getattr(member, 'name', getattr(member, 'character_name', 'Unknown'))
            console.print(x, my, f"{i+1}. {member_name[:10]}", fg=(255, 255, 255))

            # HP 게이지 (가로, 간단)
            # Character 객체는 current_hp/max_hp를, PartyMember 객체는 stats를 사용
            current_hp = getattr(member, 'current_hp', None)
            max_hp = getattr(member, 'max_hp', None)
            if current_hp is None or max_hp is None:
                # PartyMember 객체인 경우 stats에서 가져오기
                stats = getattr(member, 'stats', {})
                current_hp = stats.get('hp', 100)
                max_hp = stats.get('max_hp', 100)
            
            console.print(x + 14, my, "HP:", fg=(200, 200, 200))
            self.gauge_renderer.render_bar(
                console, x + 17, my, 10,
                current_hp, max_hp, show_numbers=False
            )

        # 인벤토리 정보
        inv_y = y + 15
        console.print(x, inv_y, "[소지품]", fg=(200, 200, 255))
        console.print(x + 2, inv_y + 1, f"열쇠: {len(self.exploration.player.keys)}개", fg=(255, 215, 0))
        # 실제 인벤토리 객체의 아이템 수 표시 (slots 사용)
        item_count = len(self.inventory.slots) if self.inventory and hasattr(self.inventory, 'slots') else 0
        console.print(x + 2, inv_y + 2, f"아이템: {item_count}개", fg=(200, 200, 200))

    def _render_messages(self, console: tcod.console.Console):
        """메시지 로그"""
        msg_y = 40
        console.print(0, msg_y, "─" * self.screen_width, fg=(100, 100, 100))

        for i, msg in enumerate(self.messages[-self.max_messages:]):
            console.print(2, msg_y + 1 + i, msg, fg=(200, 200, 200))

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
            player_id = msg.player_id
            message = msg.data.get("message", "")
        
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
            
            # 플레이어 이름 가져오기
            player_name = "플레이어"
            if hasattr(exploration, 'session') and exploration.session:
                if player_id in exploration.session.players:
                    player_name = exploration.session.players[player_id].player_name
            
            # 채팅 메시지 표시
            chat_text = f"[{player_name}]: {message}"
            ui.add_message(chat_text)
            logger.info(f"채팅 메시지 수신: {chat_text}")
        
        network_manager.register_handler(MessageType.CHAT_MESSAGE, handle_chat_message)
        network_manager.register_handler(MessageType.PLAYER_LEFT, handle_player_left)
        logger.info("채팅 메시지 및 플레이어 나감 핸들러 등록 완료")

    # 남은 이벤트 제거 (불러오기 등에서 남은 키 입력 방지)
    tcod.event.get()

    # 바이옴별 BGM 재생 (매 층마다 바뀜, 전투 후 복귀 시에는 재생하지 않음)
    if play_bgm_on_start:
        floor = exploration.floor_number
        # 바이옴 계산 (매 층마다 변경: 10개 바이옴 순환)
        biome_index = (floor - 1) % 10
        biome_track = f"biome_{biome_index}"
        
        logger.info(f"층 {floor} -> 바이옴 {biome_index}, BGM: {biome_track}")
        play_bgm(biome_track)

    import time
    last_enemy_update = time.time()
    
    while True:
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
        if hasattr(exploration, 'is_multiplayer') and exploration.is_multiplayer:
            if hasattr(exploration, 'enemy_sync') and exploration.enemy_sync:
                if current_time - last_enemy_update >= 2.0:
                    if exploration.is_host and hasattr(exploration, '_move_all_enemies'):
                        exploration._move_all_enemies()
                    last_enemy_update = current_time
        
        # 렌더링
        ui.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait(timeout=0.05):
            action = handler.dispatch(event)
            key_event = event if isinstance(event, tcod.event.KeyDown) else None

            if action or key_event:
                logger.warning(f"[DEBUG] 액션 수신: {action}")
                done = ui.handle_input(action, console, context, key_event)
                logger.warning(f"[DEBUG] handle_input 반환값: {done}")
                if done:
                    logger.warning(f"[DEBUG] 루프 탈출 - done=True")
                    break
            else:
                # action이 None인 경우 (키 입력 없음)
                # 다음 이벤트 처리로 넘어감
                continue

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
        logger.warning(f"[DEBUG] 상태 체크: quit={ui.quit_requested}, combat={ui.combat_requested}, floor_change={ui.floor_change_requested}")
        if ui.quit_requested:
            return ("quit", None)
        elif ui.combat_requested:
            logger.warning(f"[DEBUG] 전투 반환! 적 {ui.combat_num_enemies}마리 (맵 엔티티: {len(ui.combat_enemies) if ui.combat_enemies else 0}개)")
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
