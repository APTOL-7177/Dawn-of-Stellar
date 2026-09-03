"""
월드 탐험 UI

플레이어가 던전을 돌아다니는 화면
"""

from typing import List, Optional, Tuple
import os
import tcod
import time
import pygame

# ExplorationEvent를 먼저 import하여 지역 변수 충돌 방지
from src.world.exploration import ExplorationEvent, ExplorationResult, ExplorationSystem
from src.world.map_renderer import MapRenderer
from src.world.field_skills import FieldSkillManager
from src.world.tile import TileType, get_tile_info
from src.ui.input_handler import InputHandler, GameAction, unified_input_handler, iter_game_input, poll_game_input
from src.ui.gauge_renderer import GaugeRenderer
from src.ui.tcod_display import render_space_background
from src.ui.field_skill_ui import FieldSkillUI
from src.ui.ui_renderer import draw_styled_box, DynamicSeparator
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerEvent, PointerEventKind
from src.ui.visual_tokens import rgb
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
        
        # 인벤토리에 파티 설정 (무게 계산 보너스 적용)
        if inventory is not None and party is not None:
            inventory.party = party
        
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
        logger.info(f"WorldUI 초기화 - inventory: {inventory is not None}, party: {party is not None}, party members: {len(party) if party else 0}, inventory.party: {len(inventory.party) if inventory and inventory.party else 0}")

        # 메시지 로그
        self.messages: List[str] = []
        self.max_messages = 20  # 로그 패널이 커졌으므로 더 많은 메시지 표시
        self.log_scroll_offset = 0

        # 상태
        self.quit_requested = False
        self.combat_requested = False
        self.combat_enemies = None  # 전투에 참여할 적들 (맵에서 제거용)
        self.combat_num_enemies = 0  # 실제 전투 적 수
        self.combat_participants = None  # 멀티플레이: 전투 참여자
        self.combat_position = None  # 멀티플레이: 전투 시작 위치
        self.floor_change_requested = None  # "up" or "down"
        self.main_menu_requested = False  # 메인 메뉴로 돌아가기 요청

        # 종료 확인
        self.quit_confirm_mode = False
        self.quit_confirm_yes = False  # True: 예, False: 아니오
        
        # 이동 쿨타임 (플레이어: 0.2초 = 초당 5회, 적: 0.5초 = 초당 2회)
        # 플레이어가 적보다 2.5배 빠르게 움직임
        self.last_move_time = 0.0
        self.move_cooldown = 0.1  # 0.1초 = 초당 10회 이동 (2배 빨라짐)
        
        # 채팅 입력 상태
        self.chat_input_active = False
        self.chat_input_text = ""
        self.chat_input_max_length = 60

        # 마우스 호버 타일 정보
        self.mouse_screen_x = 0
        self.mouse_screen_y = 0
        self.mouse_hover_active = False  # 마우스가 맵 영역 위에 있는지
        self.pointer_hover_world_cell: Optional[Tuple[int, int]] = None
        self.pointer_hover_detail: Optional[str] = None
        self.pointer_destination: Optional[Tuple[int, int]] = None
        
        # 분수대 사용 여부 (마을 방문마다 리셋)
        self.fountain_used = False
        self.was_in_town = False  # 이전 프레임의 마을 상태 추적

        # 미니맵 토글 (RPG 오픈월드 전용)
        self.show_minimap = False

        # 마우스 호버 툴팁 (보통/평온 난이도에서만 활성)
        self._mouse_sx = 0
        self._mouse_sy = 0
        self._tooltip_enabled = False
        try:
            from src.core.config import get_config
            cfg = get_config()
            if cfg:
                self._tooltip_enabled = cfg.difficulty in ("평온", "보통")
        except Exception:
            pass

        # 화면 전환 후 CONFIRM 입력 방지 쿨다운
        self._confirm_cooldown_until = 0.0

        # 마법진 사용 확인
        self.magic_circle_confirm_mode = False
        self.magic_circle_confirm_yes = True
        self.magic_circle_tile = None

        # 릴리 대사 타이머
        self._lily_idle_check_time = time.time()
        self._lily_random_check_time = time.time()

        # ── Raylib 월드 렌더러 (백엔드가 raylib일 때만) ──────────────
        self._world_renderer = None
        self._raylib_context = None
        self._field_pending_gauges = []  # 게이지 오버레이 큐 (툴팁 보호용 지연 등록)
        try:
            from src.core.config import get_config
            if get_config().get("display.backend", "pygame") == "raylib":
                from src.ui.raylib_backend.world_renderer import WorldRenderer
                from src.ui.tcod_display import get_display
                display = get_display()
                ctx = getattr(display, 'context', None) or getattr(display, '_context', None)
                if ctx is not None:
                    tw = getattr(ctx, 'tile_width', 16)
                    th = getattr(ctx, 'tile_height', 16)
                    self._world_renderer = WorldRenderer(
                        tile_w=tw,
                        tile_h=th,
                        view_cols=self.screen_width,
                        view_rows=self.screen_height - 5,
                    )
                    self._raylib_context = ctx
                    logger.info("Raylib WorldRenderer 초기화 완료")
        except Exception as e:
            logger.debug(f"WorldRenderer 초기화 스킵: {e}")

    def add_message(self, text: str, color=None):
        """메시지 추가 (color는 호환성용 - 탐험 로그에서는 미사용)"""
        self.messages.append(text)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        logger.debug(f"메시지: {text}")

    def flush_pending_loot_messages(self):
        """인벤토리에 저장된 아이템 획득 대기 메시지를 로그에 표시"""
        if self.inventory and hasattr(self.inventory, 'pending_loot_messages'):
            for msg in self.inventory.pending_loot_messages:
                self.add_message(msg)
            self.inventory.pending_loot_messages.clear()

    def handle_pointer_event(self, event: PointerEvent, console=None, context=None) -> PointerDispatchResult:
        self._mouse_sx, self._mouse_sy = event.position.tile
        self.mouse_screen_x, self.mouse_screen_y = event.position.tile

        match event.kind:
            case PointerEventKind.HOVER:
                tooltip = self._update_pointer_hover_detail(event.position.tile)
                return PointerDispatchResult(event=event, tooltip=tooltip)
            case PointerEventKind.WHEEL:
                action = self._handle_pointer_wheel(event)
                return PointerDispatchResult(event=event, action=action)
            case PointerEventKind.CLICK:
                if event.button is PointerButton.RIGHT:
                    self._close_pointer_overlay()
                    return PointerDispatchResult(event=event, action=GameAction.CANCEL)
                if event.button is not PointerButton.LEFT:
                    return PointerDispatchResult(event=event)
                action = self._handle_pointer_left_click(event.position.tile, console, context)
                return PointerDispatchResult(event=event, action=action)
            case PointerEventKind.DRAG_START | PointerEventKind.DRAG_MOVE | PointerEventKind.DRAG_END:
                return PointerDispatchResult(event=event, hovered_region_id="map")
            case unreachable:
                raise AssertionError(f"unreachable pointer event kind: {unreachable!r}")

    def _handle_pointer_wheel(self, event: PointerEvent) -> Optional[GameAction]:
        if event.wheel_delta == 0:
            return None
        if not self._is_log_cell(event.position.tile):
            return None
        action = GameAction.PAGE_UP if event.wheel_delta > 0 else GameAction.PAGE_DOWN
        max_scroll = max(0, len(self.messages) - self._world_log_visible_lines())
        if action is GameAction.PAGE_UP:
            self.log_scroll_offset = min(self.log_scroll_offset + 3, max_scroll)
        else:
            self.log_scroll_offset = max(0, self.log_scroll_offset - 3)
        return action

    def _handle_pointer_left_click(self, tile: Tuple[int, int], console, context) -> Optional[GameAction]:
        world_cell = self._world_cell_from_screen_cell(tile)
        if world_cell is None:
            return None
        self.pointer_destination = world_cell
        action = self._action_towards_world_cell(world_cell)
        if action is not None:
            self.handle_input(action, console, context)
        return action or GameAction.CONFIRM

    def _close_pointer_overlay(self) -> None:
        if getattr(self, "field_skill_ui", None) and self.field_skill_ui.is_active:
            self.field_skill_ui.is_active = False
        if getattr(self, "show_minimap", False):
            self.show_minimap = False
        if getattr(self, "quit_confirm_mode", False):
            self.quit_confirm_mode = False
        if getattr(self, "magic_circle_confirm_mode", False):
            self.magic_circle_confirm_mode = False
            self.magic_circle_tile = None
        if getattr(self, "chat_input_active", False):
            self.chat_input_active = False
            self.chat_input_text = ""

    def _update_pointer_hover_detail(self, tile: Tuple[int, int]) -> Optional[str]:
        world_cell = self._world_cell_from_screen_cell(tile)
        self.pointer_hover_world_cell = world_cell
        self.mouse_hover_active = world_cell is not None
        if world_cell is None:
            self.pointer_hover_detail = None
            return None

        world_x, world_y = world_cell
        tile_info = self._tile_detail_at(world_x, world_y)
        enemy = self._enemy_at(world_x, world_y)
        detail = tile_info if enemy is None else f"{tile_info} | {getattr(enemy, 'name', '???')}"
        self.pointer_hover_detail = detail
        return detail

    def _tile_detail_at(self, world_x: int, world_y: int) -> str:
        dungeon = self.exploration.dungeon
        tile = dungeon.get_tile(world_x, world_y)
        if tile is None:
            return f"타일 ({world_x}, {world_y})"
        try:
            tile_name, tile_desc = get_tile_info(tile.tile_type)
        except (KeyError, TypeError, AttributeError):
            tile_name = getattr(tile.tile_type, "value", str(tile.tile_type))
            tile_desc = ""
        suffix = f" - {tile_desc}" if tile_desc else ""
        return f"{tile_name} ({world_x}, {world_y}){suffix}"

    def _enemy_at(self, world_x: int, world_y: int):
        for enemy in getattr(self.exploration, "enemies", []):
            if getattr(enemy, "x", None) == world_x and getattr(enemy, "y", None) == world_y:
                return enemy
        return None

    def _world_cell_from_screen_cell(self, tile: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        screen_x, screen_y = tile
        if screen_x < 0 or screen_y < 5 or screen_y >= 40 or screen_x >= self.screen_width:
            return None
        camera_x, camera_y = self._current_camera_cell()
        world_x = camera_x + screen_x
        world_y = camera_y + screen_y - 5
        dungeon = self.exploration.dungeon
        if world_x < 0 or world_y < 0 or world_x >= dungeon.width or world_y >= dungeon.height:
            return None
        return (world_x, world_y)

    def _current_camera_cell(self) -> Tuple[int, int]:
        camera_x = getattr(self, "_camera_x", None)
        camera_y = getattr(self, "_camera_y", None)
        if camera_x is not None and camera_y is not None:
            return int(camera_x), int(camera_y)
        player = self.exploration.player
        return max(0, player.x - 40), max(0, player.y - 20)

    def _action_towards_world_cell(self, world_cell: Tuple[int, int]) -> Optional[GameAction]:
        player = self.exploration.player
        dx = world_cell[0] - player.x
        dy = world_cell[1] - player.y
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
        direction_actions = {
            (0, -1): GameAction.MOVE_UP,
            (0, 1): GameAction.MOVE_DOWN,
            (-1, 0): GameAction.MOVE_LEFT,
            (1, 0): GameAction.MOVE_RIGHT,
            (-1, -1): GameAction.MOVE_UP_LEFT,
            (1, -1): GameAction.MOVE_UP_RIGHT,
            (-1, 1): GameAction.MOVE_DOWN_LEFT,
            (1, 1): GameAction.MOVE_DOWN_RIGHT,
        }
        return direction_actions.get((step_x, step_y))

    def _is_log_cell(self, tile: Tuple[int, int]) -> bool:
        screen_x, screen_y = tile
        party_x = self.screen_width - 30
        log_panel_x = 2
        log_panel_width = party_x - log_panel_x - 4
        log_panel_y = self.screen_height - self._world_log_visible_lines() - 4
        return log_panel_x - 1 <= screen_x <= log_panel_x + log_panel_width and log_panel_y - 1 <= screen_y <= log_panel_y + self._world_log_visible_lines()

    def _world_log_visible_lines(self) -> int:
        party = getattr(getattr(self.exploration, "player", None), "party", []) or []
        party_count = min(4, len(party))
        total_height = 2 + (party_count * 4) + 4
        return max(1, (total_height // 2) - 1)

    def handle_input(self, action: GameAction, console=None, context=None, key_event=None) -> bool:
        # 대기 중인 아이템 획득 메시지 표시
        self.flush_pending_loot_messages()

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
                # GameAction.CONFIRM (A버튼) 또는 Enter 키로 전송
                if key_event.sym == tcod.event.KeySym.RETURN or action == GameAction.CONFIRM:
                    # Enter: 메시지 전송
                    if self.chat_input_text.strip() and self.network_manager and self.local_player_id:
                        self._send_chat_message(self.chat_input_text.strip())
                        self.chat_input_text = ""
                    self.chat_input_active = False
                    return False
                # GameAction.CANCEL (B버튼) 또는 ESC 키로 취소
                elif key_event.sym == tcod.event.KeySym.ESCAPE or action == GameAction.CANCEL:
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

        # 필드 스킬 및 채팅 입력 (GameAction 사용)
        # 필드 스킬 (F 키 / L-Trigger)
        # 스폰 위치 텔레포트 (R 키 / 게임패드 R3)
        if action == GameAction.TELEPORT_TO_SPAWN:
            try:
                # RPG 오픈월드에서는 사용 불가
                is_rpg_world = (
                    (hasattr(self.exploration, 'rpg_progress')) or
                    (hasattr(self.exploration, 'is_rpg_sub_dungeon') and self.exploration.is_rpg_sub_dungeon) or
                    (self.exploration.dungeon.width > 300 or self.exploration.dungeon.height > 300)
                )
                if is_rpg_world:
                    self.add_message("RPG 모드에서는 스폰 텔레포트를 사용할 수 없습니다.")
                    return False

                result = self.exploration.teleport_to_spawn()
                if result.success:
                    self.add_message(result.message, (0, 255, 200))
                    # 멀티플레이: 위치 동기화
                    if self.network_manager and hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        try:
                            from src.multiplayer.protocol import MessageBuilder
                            import asyncio
                            player_id = getattr(self.exploration, 'local_player_id', None) or self.local_player_id
                            if player_id:
                                move_message = MessageBuilder.player_move(
                                    player_id=player_id,
                                    x=self.exploration.player.x,
                                    y=self.exploration.player.y,
                                    timestamp=time.time()
                                )
                                self.network_manager.broadcast_sync(move_message)
                                logger.info(f"멀티플레이 스폰 텔레포트 동기화: {player_id} -> ({self.exploration.player.x}, {self.exploration.player.y})")
                        except Exception as sync_e:
                            logger.error(f"스폰 텔레포트 동기화 실패: {sync_e}")
                else:
                    self.add_message(result.message, (255, 200, 100))
            except Exception as e:
                logger.error(f"스폰 텔레포트 처리 중 오류: {e}")
                self.add_message("텔레포트 오류가 발생했습니다.")
            return False

        if action == GameAction.FIELD_SKILL:
            try:
                # 마을인지 확인
                is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
                if is_town:
                    self.add_message("마을에서는 필드스킬을 사용할 수 없습니다.")
                    return False
                if self.party:
                    self.field_skill_ui.show(self.party)
                    return False
            except Exception as e:
                logger.error(f"필드 스킬 처리 중 오류: {e}")
                self.add_message("필드 스킬 UI 오류가 발생했습니다.")
                return False

        # 채팅 (T 키)
        if action == GameAction.CHAT:
            is_multiplayer = (
                self.network_manager is not None or
                (hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer) or
                (hasattr(self.exploration, 'session') and self.exploration.session is not None)
            )
            if is_multiplayer:
                self.chat_input_active = True
                self.chat_input_text = ""
                return False
            else:
                # 싱글플레이어: 릴리 대화 (RPG 모드 - 마을/필드 어디서든)
                if hasattr(self.exploration, 'lily_dialogue') and hasattr(self.exploration, 'rpg_progress'):
                    self._open_lily_conversation(console, context)
                    return False
        
        # 봇 관련 코드 제거됨

        # 미니맵 토글 (Tab 키 / OPEN_MAP)
        if action == GameAction.OPEN_MAP:
            self.show_minimap = not self.show_minimap
            return False

        # 미니맵이 열려있을 때 X키(CANCEL/ESCAPE)로 닫기
        if self.show_minimap and action in (GameAction.CANCEL, GameAction.ESCAPE):
            self.show_minimap = False
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
            self.quit_confirm_yes = False
            return False

        # 마법진 확인 모드
        if self.magic_circle_confirm_mode:
            if action == GameAction.MOVE_LEFT:
                self.magic_circle_confirm_yes = True
            elif action == GameAction.MOVE_RIGHT:
                self.magic_circle_confirm_yes = False
            elif action == GameAction.CONFIRM:
                if self.magic_circle_confirm_yes:
                    # 마법진 사용
                    if self.magic_circle_tile:
                        result = self.exploration.activate_magic_circle(self.magic_circle_tile)
                        self._handle_exploration_result(result, console, context)
                # 모드 종료 (사용했든 취소했든)
                self.magic_circle_confirm_mode = False
                self.magic_circle_tile = None
                return False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.magic_circle_confirm_mode = False
                self.magic_circle_tile = None
                return False
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
                elif result == MenuOption.MAIN_MENU:
                    # 메인 메뉴로 돌아가기
                    self.quit_requested = True
                    self.main_menu_requested = True
                    return True
                elif result == MenuOption.WORLD_MAP:
                    # 월드맵(미니맵) 토글
                    self.show_minimap = not self.show_minimap
                    return False
                elif result == MenuOption.TELEPORT_TO_SPAWN:
                    # 스폰 위치로 텔레포트
                    tp_result = self.exploration.teleport_to_spawn()
                    if tp_result.success:
                        self.add_message(tp_result.message, (0, 255, 200))
                        # 멀티플레이: 위치 동기화
                        if self.network_manager and hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            try:
                                from src.multiplayer.protocol import MessageBuilder
                                player_id = getattr(self.exploration, 'local_player_id', None) or self.local_player_id
                                if player_id:
                                    move_message = MessageBuilder.player_move(
                                        player_id=player_id,
                                        x=self.exploration.player.x,
                                        y=self.exploration.player.y,
                                        timestamp=time.time()
                                    )
                                    self.network_manager.broadcast_sync(move_message)
                            except Exception as sync_e:
                                logger.error(f"스폰 텔레포트 동기화 실패: {sync_e}")
                    else:
                        self.add_message(tp_result.message, (255, 200, 100))
                    return False
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
            
            # 쿨타임 체크 (싱글/멀티 모두)
            if current_time - self.last_move_time < self.move_cooldown:
                # 쿨타임 중이면 이동 무시
                return False
            # 쿨타임 통과 시 이동 시간 업데이트
            self.last_move_time = current_time

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

            result = self.exploration.move_player(dx, dy)
            if result is None:
                # Debug: 이동 결과 None
                # None인 경우 기본 결과 생성
                result = ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NONE,
                    message=""
                )
            else:
                # Debug: 이동 결과 이벤트
                pass
            # 효과 타일 첫 진입 설명 메시지 표시
            if hasattr(self.exploration, '_pending_tile_messages') and self.exploration._pending_tile_messages:
                for msg in self.exploration._pending_tile_messages:
                    self.add_message(msg, (180, 220, 255))
                self.exploration._pending_tile_messages.clear()

            # 이동 성공 시 요리솥 자동 열기 체크 제거 (사용자가 명시적으로 상호작용해야 함)
            # 주석 처리: 자동 열기는 사용자 경험을 해침

            # 랜덤 이벤트 진단: 200스텝마다 게임 내 메시지 표시
            _re_count = getattr(self.exploration, '_re_move_count', 0)
            if _re_count > 0 and _re_count % 200 == 0:
                try:
                    from src.world.random_events import get_random_event_manager
                    _mgr = get_random_event_manager()
                    self.add_message(
                        f"[진단] 이동 {_re_count}회, 이벤트체크 steps={_mgr._steps_since_event}, "
                        f"events={len(_mgr._dungeon_events)}+{len(_mgr._region_events)}, "
                        f"is_town={getattr(self.exploration, 'is_town', '?')}",
                        (100, 100, 100)
                    )
                except Exception:
                    pass

            self._handle_exploration_result(result, console, context)
            # 전투가 트리거되면 메인 루프의 상태 체크에서 처리하도록 False 반환
            if self.combat_requested:
                # Debug: 전투 요청 (run_exploration의 메인 루프에서 처리)
                return False

        # 채집 또는 계단 이동 (Z키/엔터키)
        elif action == GameAction.CONFIRM:
            # 화면 전환 직후 CONFIRM 쿨다운 체크 (Z키 잔류 입력 방지)
            import time as _time
            if _time.time() < self._confirm_cooldown_until:
                return False

            # 우선순위 0: 플레이어가 계단 위에 서 있으면 즉시 계단 이동 (채집보다 우선)
            current_tile = self.exploration.dungeon.get_tile(
                self.exploration.player.x,
                self.exploration.player.y
            )
            if current_tile and current_tile.tile_type == TileType.STAIRS_DOWN:
                from src.audio import play_sfx
                play_sfx("world", "stairs_down")
                is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
                if is_town:
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'session') and self.exploration.session:
                            session = self.exploration.session
                            local_player_id = None
                            if hasattr(self.exploration, 'local_player_id'):
                                local_player_id = self.exploration.local_player_id
                            if local_player_id:
                                session.set_floor_ready(local_player_id, True)
                                if self.network_manager:
                                    from src.multiplayer.protocol import MessageBuilder
                                    import asyncio
                                    try:
                                        ready_msg = MessageBuilder.floor_ready(
                                            player_id=local_player_id,
                                            ready=True,
                                            ready_players=list(session.floor_ready_players),
                                            total_players=len(session.players)
                                        )
                                        server_loop = getattr(self.network_manager, '_server_event_loop', None)
                                        client_loop = getattr(self.network_manager, '_client_event_loop', None)
                                        event_loop = server_loop or client_loop
                                        if event_loop and event_loop.is_running():
                                            asyncio.run_coroutine_threadsafe(
                                                self.network_manager.broadcast(ready_msg),
                                                event_loop
                                            )
                                        else:
                                            self.network_manager.broadcast_sync(ready_msg)
                                    except Exception as e:
                                        logger.error(f"층 이동 준비 상태 브로드캐스트 실패: {e}")
                            if session.is_all_ready_for_floor_change():
                                self.floor_change_requested = "floor_down"
                                self.add_message("모든 플레이어가 준비되었습니다. 던전으로 이동합니다...")
                                session.reset_floor_ready()
                                return True
                            else:
                                ready_count = len(session.floor_ready_players)
                                total_count = len(session.players)
                                self.add_message(f"던전으로 이동 대기 중... ({ready_count}/{total_count} 준비)")
                                return False
                    self.floor_change_requested = "floor_down"
                    self.add_message("던전으로 이동합니다...")
                    return True
                else:
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'session') and self.exploration.session:
                            session = self.exploration.session
                            local_player_id = None
                            if hasattr(self.exploration, 'local_player_id'):
                                local_player_id = self.exploration.local_player_id
                            if local_player_id:
                                session.set_floor_ready(local_player_id, True)
                                if self.network_manager:
                                    from src.multiplayer.protocol import MessageBuilder
                                    import asyncio
                                    try:
                                        ready_msg = MessageBuilder.floor_ready(
                                            player_id=local_player_id,
                                            ready=True,
                                            ready_players=list(session.floor_ready_players),
                                            total_players=len(session.players)
                                        )
                                        server_loop = getattr(self.network_manager, '_server_event_loop', None)
                                        client_loop = getattr(self.network_manager, '_client_event_loop', None)
                                        event_loop = server_loop or client_loop
                                        if event_loop and event_loop.is_running():
                                            asyncio.run_coroutine_threadsafe(
                                                self.network_manager.broadcast(ready_msg),
                                                event_loop
                                            )
                                        else:
                                            self.network_manager.broadcast_sync(ready_msg)
                                    except Exception as e:
                                        logger.error(f"층 이동 준비 상태 브로드캐스트 실패: {e}")
                            if session.is_all_ready_for_floor_change():
                                self.floor_change_requested = "floor_down"
                                self.add_message("모든 플레이어가 준비되었습니다. 아래층으로 내려갑니다...")
                                session.reset_floor_ready()
                                return True
                            else:
                                ready_count = len(session.floor_ready_players)
                                total_count = len(session.players)
                                self.add_message(f"다음 층으로 이동 대기 중... ({ready_count}/{total_count} 준비)")
                                return False
                    self.floor_change_requested = "floor_down"
                    self.add_message("아래층으로 내려갑니다...")
                    next_floor = self.exploration.floor_number + 1
                    try:
                        from src.quest.quest_manager import get_quest_manager
                        quest_manager = get_quest_manager()
                        quest_manager.update_progress("floor_reached", f"floor_{next_floor}")
                    except Exception:
                        pass
                    return True

            # 우선순위 1: 요리솥 상호작용
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

            # 우선순위 2: 채집 오브젝트 찾기
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

            # 우선순위 3: RPG 오픈월드 타일 상호작용 (Z키)
            if self._handle_rpg_tile_interact(console, context):
                return False

            # 우선순위 4: 계단 이동 체크
            tile = self.exploration.dungeon.get_tile(
                self.exploration.player.x,
                self.exploration.player.y
            )

            if tile:
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
                                    
                                    # 준비 상태 브로드캐스트 (호스트/클라이언트 모두)
                                    if self.network_manager:
                                        from src.multiplayer.protocol import MessageBuilder
                                        import asyncio
                                        try:
                                            ready_msg = MessageBuilder.floor_ready(
                                                player_id=local_player_id,
                                                ready=True,
                                                ready_players=list(session.floor_ready_players),
                                                total_players=len(session.players)
                                            )
                                            # 비동기 브로드캐스트
                                            server_loop = getattr(self.network_manager, '_server_event_loop', None)
                                            client_loop = getattr(self.network_manager, '_client_event_loop', None)
                                            event_loop = server_loop or client_loop
                                            if event_loop and event_loop.is_running():
                                                asyncio.run_coroutine_threadsafe(
                                                    self.network_manager.broadcast(ready_msg),
                                                    event_loop
                                                )
                                            else:
                                                self.network_manager.broadcast_sync(ready_msg)
                                            logger.debug(f"층 이동 준비 상태 브로드캐스트: {local_player_id}")
                                        except Exception as e:
                                            logger.error(f"층 이동 준비 상태 브로드캐스트 실패: {e}")

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
                                    
                                    # 준비 상태 브로드캐스트 (호스트/클라이언트 모두)
                                    if self.network_manager:
                                        from src.multiplayer.protocol import MessageBuilder
                                        import asyncio
                                        try:
                                            ready_msg = MessageBuilder.floor_ready(
                                                player_id=local_player_id,
                                                ready=True,
                                                ready_players=list(session.floor_ready_players),
                                                total_players=len(session.players)
                                            )
                                            # 비동기 브로드캐스트
                                            server_loop = getattr(self.network_manager, '_server_event_loop', None)
                                            client_loop = getattr(self.network_manager, '_client_event_loop', None)
                                            event_loop = server_loop or client_loop
                                            if event_loop and event_loop.is_running():
                                                asyncio.run_coroutine_threadsafe(
                                                    self.network_manager.broadcast(ready_msg),
                                                    event_loop
                                                )
                                            else:
                                                self.network_manager.broadcast_sync(ready_msg)
                                            logger.debug(f"층 이동 준비 상태 브로드캐스트: {local_player_id}")
                                        except Exception as e:
                                            logger.error(f"층 이동 준비 상태 브로드캐스트 실패: {e}")

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
                        
                        # 퀘스트 진행도 업데이트 (층 도달 퀘스트)
                        next_floor = self.exploration.floor_number + 1
                        try:
                            from src.quest.quest_manager import get_quest_manager
                            quest_manager = get_quest_manager()
                            quest_manager.update_progress("floor_reached", f"floor_{next_floor}")
                            logger.info(f"[퀘스트] 층 도달 진행도 업데이트: floor_{next_floor}")
                        except Exception as e:
                            logger.warning(f"[퀘스트] 층 도달 진행도 업데이트 실패: {e}")
                        
                        return True
            return False

        # 상호작용 (E키)
        elif action == GameAction.INTERACT:
            logger.debug(f"상호작용 입력: {action}")
            # 우선순위 1: 요리솥 (CONFIRM과 동일하지만 E키로도 사용 가능)
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
                    # 항상 싱글톤 town_manager 사용
                    from src.town.town_manager import get_town_manager
                    town_manager = get_town_manager()
                    # exploration에도 설정하여 저장 시 일관성 유지
                    self.exploration.town_manager = town_manager
                    
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
                            # 건물별 UI 열기는 아래 _handle_rpg_tile_interact로 폴스루
                        else:
                            # 건물이 없는 위치에서 상호작용 시도
                            tile_char = player_tile.char if player_tile else 'None'
                            logger.warning(f"[상호작용 실패] 위치 ({player_x}, {player_y})에 건물이 없습니다. (타일 char: {tile_char}, town_map.buildings 개수: {len(town_map.buildings)})")
                            # 건물 목록 로그
                            if town_map.buildings:
                                for b in town_map.buildings:
                                    logger.warning(f"  건물: {b.name} at ({b.x}, {b.y})")
                            # 타일 기반 핸들러로 폴스루
                    else:
                        logger.warning(f"town_map={town_map is not None}, town_manager={town_manager is not None}")
                        if not town_map:
                            logger.error("town_map을 찾을 수 없습니다.")
                        if not town_manager:
                            logger.error("town_manager를 찾을 수 없습니다.")
                
                # RPG 오픈월드 타일 상호작용 (is_town이 아니어도 동작)
                if self._handle_rpg_tile_interact(console, context):
                    return False

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
                building_type_str = result.data.get("building_type", "")
                logger.info(f"[건물 상호작용] building 객체 확인 - building={building}, building_type_str={building_type_str}")

                # building 객체가 없지만 building_type 문자열이 있는 경우 (RPG 오픈월드)
                # 타일 타입 기반으로 직접 UI 열기
                if building is None and building_type_str and console is not None and context is not None:
                    self._handle_building_type_ui(console, context, building_type_str)

                elif building is not None and console is not None and context is not None:
                    # 마을에서 건물과 상호작용
                    from src.town.town_map import TownInteractionHandler, BuildingType
                    # 항상 싱글톤 town_manager 사용
                    from src.town.town_manager import get_town_manager
                    town_manager = get_town_manager()
                    # exploration에도 설정하여 저장 시 일관성 유지
                    self.exploration.town_manager = town_manager
                    
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
                                    # player 객체 가져오기
                                    player_obj = getattr(self.exploration, 'player', None)
                                    open_quest_board(console, context, quest_manager, player_level, player=player_obj, current_floor=self.exploration.floor_number, inventory=self.inventory)
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
                                # 모험가 길드: 퀘스트 게시판 + 파티 상태 + 업적
                                logger.info(f"[건물 상호작용] 모험가 길드")
                                self._open_town_guild_hall(console, context)
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
        
        if result.message:
            self.add_message(result.message)

        if result.event == ExplorationEvent.COMBAT:
            # Debug: 전투 이벤트 감지
            self.combat_requested = True
            # 전투에 참여할 적들 저장
            if result.data:
                if "num_enemies" in result.data:
                    self.combat_num_enemies = result.data["num_enemies"]
                if "enemies" in result.data:
                    self.combat_enemies = result.data["enemies"]
                # 보스/레벨 정보 저장 (RPG 모드 전투 정확성 향상)
                self.combat_is_boss = result.data.get("is_boss", False)
                self.combat_enemy_level = result.data.get("enemy_level", None)
                # 멀티플레이: 참여자 정보 저장
                if "participants" in result.data:
                    self.combat_participants = result.data["participants"]
                    logger.info(f"멀티플레이 전투 참여자: {len(self.combat_participants)}명")
                # 멀티플레이: 동기화 데이터 저장
                if "synced_enemies" in result.data:
                    self.combat_synced_enemies = result.data["synced_enemies"]
                if "combined_party" in result.data:
                    self.combat_combined_party = result.data["combined_party"]
                if "local_party_ids" in result.data:
                    self.combat_local_party_ids = result.data["local_party_ids"]
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

        # 마법진 발견 처리
        elif result.event == ExplorationEvent.MAGIC_CIRCLE_FOUND:
            if result.data and 'tile' in result.data:
                self.magic_circle_confirm_mode = True
                self.magic_circle_confirm_yes = True
                self.magic_circle_tile = result.data['tile']
                self.add_message(result.message)
            return

        # 보물상자/아이템 발견 처리 - LootUI 표시
        elif result.event == ExplorationEvent.CHEST_FOUND or result.event == ExplorationEvent.ITEM_FOUND:
            logger.info(f"[WorldUI] 보물상자/아이템 이벤트 감지: {result.event}")
            if console is not None and context is not None and result.data and 'items' in result.data:
                items = result.data.get('items', [])
                tile = result.data.get('tile')
                
                logger.info(f"[WorldUI] 아이템 정보: {len(items)}개, 타일 정보: {tile is not None}, 인벤토리: {self.inventory is not None}")
                
                if items and self.inventory is not None:
                    from src.ui.loot_ui import show_loot_screen
                    from src.audio import play_sfx
                    
                    # 메시지 표시
                    self.add_message(result.message)
                    
                    # 기존 화면 렌더링
                    self.render(console, render_ctx=context)
                    context.present(console)

                    # LootUI 표시 (멀티플레이: exploration 전달하여 전투 감지 가능)
                    logger.info("LootUI 표시 시도...")
                    show_loot_screen(console, context, items, self.inventory, exploration=self.exploration)
                    logger.info("LootUI 종료됨")

                    # 획득 아이템 로그 표시 (pending_loot_messages에서 자동 처리)
                    self.flush_pending_loot_messages()
                    
                    # LootUI 닫은 후 타일 정리
                    if tile:
                        logger.info(f"[WorldUI] 타일 정리: ({tile.x}, {tile.y}) {tile.tile_type} -> FLOOR")
                        tile.tile_type = TileType.FLOOR
                        tile.loot_id = None
                        
                        # 멀티플레이: 타일 변경 동기화 (호스트가 브로드캐스트)
                        if self.network_manager and getattr(self.network_manager, 'is_host', False):
                            from src.multiplayer.protocol import MessageBuilder
                            import asyncio
                            try:
                                # ITEM_PICKED_UP 메시지를 사용하여 타일 제거 동기화
                                msg = MessageBuilder.item_picked_up(tile.x, tile.y)
                                server_loop = getattr(self.network_manager, '_server_event_loop', None)
                                if server_loop and server_loop.is_running():
                                    asyncio.run_coroutine_threadsafe(
                                        self.network_manager.broadcast(msg),
                                        server_loop
                                    )
                                    logger.info(f"멀티플레이: 보물상자/아이템 획득 브로드캐스트 완료 ({tile.x}, {tile.y})")
                                else:
                                    self.network_manager.broadcast_sync(msg)
                            except Exception as e:
                                logger.error(f"보물상자 획득 브로드캐스트 실패: {e}")
                        
                    # 아이템 획득 SFX
                    play_sfx("item", "get_item")
                else:
                    if not items:
                        logger.warning("[WorldUI] 아이템 리스트가 비어있습니다.")
                    if self.inventory is None:
                        logger.warning("[WorldUI] 인벤토리가 없습니다.")
                    
                    # 인벤토리가 없거나 아이템이 없더라도 타일은 정리 (무한 루프 방지)
                    if tile:
                        logger.info(f"[WorldUI] 아이템/인벤토리 없음으로 인한 타일 강제 정리: ({tile.x}, {tile.y})")
                        tile.tile_type = TileType.FLOOR
                        tile.loot_id = None
                        
                        # 멀티플레이 동기화 (강제 정리 시에도)
                        if self.network_manager and getattr(self.network_manager, 'is_host', False):
                            from src.multiplayer.protocol import MessageBuilder
                            try:
                                msg = MessageBuilder.item_picked_up(tile.x, tile.y)
                                self.network_manager.broadcast_sync(msg)
                            except: pass
            else:
                logger.warning(f"[WorldUI] 이벤트 데이터가 부족합니다: console={console is not None}, context={context is not None}, data={result.data is not None}")
            return

        elif result.event == ExplorationEvent.RANDOM_EVENT:
            # 랜덤 이벤트 처리
            if result.data and "random_event" in result.data:
                random_event = result.data["random_event"]
                self.add_message(f"[이벤트] {random_event.name}", (255, 215, 0))
                try:
                    from src.ui.random_event_ui import RandomEventUI
                    party_jobs = []
                    if hasattr(self.exploration.player, 'party') and self.exploration.player.party:
                        party_jobs = [getattr(c, 'character_class', '') for c in self.exploration.player.party]
                    event_ui = RandomEventUI()
                    inventory = getattr(self.exploration, 'inventory', None)
                    event_ui.open(random_event, party_jobs, inventory)
                    if console is not None and context is not None:
                        # 이벤트 UI 루프
                        while event_ui.is_active:
                            event_ui.render(console)
                            context.present(console)
                            for action, event in iter_game_input():
                                if action == GameAction.QUIT:
                                    event_ui.is_active = False
                                    break
                                elif action:
                                    event_ui.handle_input(action)
                        # 결과 처리
                        choice_idx = event_ui.get_selected_choice()
                        if choice_idx >= 0:
                            from src.world.random_events import get_random_event_manager
                            # 스케일링용 층수/레벨 계산
                            _evt_floor = getattr(getattr(self.exploration, 'dungeon', None), 'floor', 1) or 1
                            _evt_level = 1
                            _evt_party = getattr(getattr(self.exploration, 'player', None), 'party', None)
                            if _evt_party:
                                _lvls = [getattr(m, 'level', 1) for m in _evt_party]
                                if _lvls:
                                    _evt_level = max(1, sum(_lvls) // len(_lvls))
                            outcome = get_random_event_manager().resolve_choice(
                                random_event, choice_idx, party_jobs, inventory,
                                floor=_evt_floor, level=_evt_level,
                            )
                            if outcome.message:
                                self.add_message(outcome.message, (200, 200, 200))
                            # 골드 처리 (양수=획득, 음수=차감)
                            if outcome.gold != 0 and inventory is not None:
                                inventory.gold = max(0, inventory.gold + outcome.gold)
                                if outcome.gold > 0:
                                    self.add_message(f"  골드 +{outcome.gold}", (255, 215, 0))
                                else:
                                    self.add_message(f"  골드 {outcome.gold}", (200, 150, 50))
                            if outcome.exp > 0:
                                self.add_message(f"  경험치 +{outcome.exp}", (100, 200, 255))
                            # 아이템 획득
                            if outcome.items and inventory is not None:
                                for item_id in outcome.items:
                                    try:
                                        from src.equipment.item_system import (
                                            ItemGenerator, CONSUMABLE_TEMPLATES,
                                            WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES
                                        )
                                        item = None
                                        if item_id in CONSUMABLE_TEMPLATES:
                                            item = ItemGenerator.create_consumable(item_id)
                                        elif item_id in WEAPON_TEMPLATES:
                                            item = ItemGenerator.create_weapon(item_id)
                                        elif item_id in ARMOR_TEMPLATES:
                                            item = ItemGenerator.create_armor(item_id)
                                        elif item_id in ACCESSORY_TEMPLATES:
                                            item = ItemGenerator.create_accessory(item_id)
                                        else:
                                            # 템플릿에 없는 이벤트 아이템 → 파티 레벨 기반 실제 장비/포션으로 대체
                                            avg_level = 1
                                            if hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'party'):
                                                levels = [getattr(m, 'level', 1) for m in (self.exploration.player.party or [])]
                                                if levels:
                                                    avg_level = max(1, sum(levels) // len(levels))
                                            item = ItemGenerator.create_random_drop(
                                                level=avg_level, boss_drop=False,
                                                floor_number=getattr(self.exploration.dungeon, 'floor', 1)
                                            )
                                        if item:
                                            inventory.add_item(item)
                                            self.add_message(f"  아이템 획득: {item.name}", (150, 255, 150))
                                        else:
                                            self.add_message(f"  아이템 획득 실패", (200, 150, 150))
                                    except Exception:
                                        self.add_message(f"  아이템 획득 실패", (200, 150, 150))
                            # 데미지 처리
                            if (outcome.damage > 0 or outcome.damage_percent > 0) and party:
                                for member in party:
                                    if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                                        dmg = outcome.damage
                                        if outcome.damage_percent > 0:
                                            dmg += int(member.max_hp * outcome.damage_percent / 100)
                                        if dmg > 0:
                                            member.current_hp = max(1, member.current_hp - dmg)
                                if outcome.damage_percent > 0:
                                    self.add_message(f"  파티 HP -{outcome.damage_percent}%!", (255, 100, 100))
                                elif outcome.damage > 0:
                                    self.add_message(f"  파티 HP -{outcome.damage}!", (255, 100, 100))
                            # 회복 처리
                            if (outcome.heal > 0 or outcome.heal_percent > 0) and party:
                                for member in party:
                                    if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                                        amount = outcome.heal
                                        if outcome.heal_percent > 0:
                                            amount += int(member.max_hp * outcome.heal_percent / 100)
                                        if amount > 0:
                                            member.current_hp = min(member.max_hp, member.current_hp + amount)
                                if outcome.heal_percent > 0:
                                    self.add_message(f"  파티 HP +{outcome.heal_percent}% 회복!", (100, 255, 100))
                                elif outcome.heal > 0:
                                    self.add_message(f"  파티 HP +{outcome.heal} 회복!", (100, 255, 100))
                            # 호감도 변화
                            if outcome.affinity_gain != 0:
                                if hasattr(self, 'exploration') and hasattr(self.exploration, 'rpg_progress'):
                                    progress = self.exploration.rpg_progress
                                    if hasattr(progress, 'lily_affinity'):
                                        progress.lily_affinity = max(0, progress.lily_affinity + outcome.affinity_gain)
                                if outcome.affinity_gain > 0:
                                    self.add_message(f"  호감도 +{outcome.affinity_gain}", (255, 180, 200))
                                else:
                                    self.add_message(f"  호감도 {outcome.affinity_gain}", (180, 100, 100))
                except Exception as e:
                    import traceback
                    logger.error(f"[랜덤이벤트 진단] UI 처리 실패: {e}\n{traceback.format_exc()}")
                    self.add_message(f"{random_event.description}", (200, 200, 200))


        elif result.event == ExplorationEvent.TELEPORTER_FOUND:
            # 텔레포터 선택 메뉴 표시
            if console is not None and context is not None and result.data:
                from src.ui.cursor_menu import show_teleporter_choice_menu
                choice = show_teleporter_choice_menu(console, context)

                if choice is True:
                    # 텔레포트 실행
                    target = result.data.get("target")
                    tile = result.data.get("tile")
                    if target and tile:
                        from src.audio import play_sfx
                        play_sfx("world", "teleport")
                        self.exploration.player.x, self.exploration.player.y = target
                        self.exploration.update_fov()
                        self.add_message("🌀 텔레포트!")
                        self.add_message(f"위치: ({self.exploration.player.x}, {self.exploration.player.y})")
                        logger.info(f"텔레포트 실행: {target}")
                    else:
                        self.add_message("텔레포트 대상이 잘못되었습니다.")
                elif choice is False:
                    # 취소
                    self.add_message("텔레포트를 취소했습니다.")
                # choice가 None이면 메뉴가 취소됨 (아무 메시지도 표시하지 않음)

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

    def _handle_rpg_tile_interact(self, console, context) -> bool:
        """RPG 오픈월드 타일 상호작용 처리. 처리했으면 True 반환."""
        if self.exploration.dungeon.width <= 300 and self.exploration.dungeon.height <= 300:
            return False

        player_tile = self.exploration.dungeon.get_tile(
            self.exploration.player.x, self.exploration.player.y
        )
        if not player_tile:
            return False

        tt = player_tile.tile_type

        if tt == TileType.NPC:
            try:
                from src.rpg_mode.town_npc_manager import get_town_npc_manager
                from src.ui.npc_dialog_ui import run_npc_dialog, NPCChoice
                from src.quest.quest_manager import get_quest_manager
                npc_mgr = get_town_npc_manager()
                npc_id = getattr(player_tile, 'npc_id', None)
                npc = npc_mgr.get_npc(npc_id) if npc_id else None

                if npc and console and context:
                    # 현재 챕터 확인 (세이브 파일에서 직접 읽기)
                    current_chapter = ""
                    try:
                        import json
                        save_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "saves", "rpg_save.json"
                        )
                        if os.path.exists(save_path):
                            with open(save_path, "r", encoding="utf-8") as f:
                                save_data = json.load(f)
                            rpg_prog = save_data.get("rpg_progress", {})
                            ch_num = rpg_prog.get("current_chapter", 0)
                            if ch_num > 0:
                                current_chapter = f"rpg_ch{ch_num}"
                    except Exception:
                        pass

                    dialog_lines = npc_mgr.get_npc_dialog_lines(npc_id, current_chapter)
                    display_name = npc_mgr.get_npc_display_name(npc_id)

                    # ── 퀘스트 선택지 생성 ──
                    choices = []
                    try:
                        qm = get_quest_manager()
                        npc_region = npc_mgr.get_npc_region(npc_id)
                        npc_quest_types = {
                            "investigate", "explore", "fetch", "collect",
                            "delivery", "escort", "rescue", "puzzle",
                        }
                        for quest in qm.active_quests:
                            if (quest.quest_subtype in npc_quest_types
                                    and quest.region == npc_region
                                    and not quest.is_complete):
                                def _make_cb(qid=quest.quest_id):
                                    def _cb():
                                        _advance_npc_quest(qm, qid, self)
                                    return _cb
                                choices.append(NPCChoice(
                                    text=f"[퀘스트] {quest.name} 진행",
                                    callback=_make_cb(),
                                ))
                    except Exception:
                        pass

                    run_npc_dialog(
                        console, context,
                        npc_name=display_name,
                        dialog_lines=dialog_lines,
                        npc_id=npc_id,
                        choices=choices if choices else None,
                    )
                    self.add_message(f"{npc.name}: 대화를 나눴습니다.")
                elif npc:
                    # console/context 없으면 메시지로 대체
                    self.add_message(f"{npc.name} ({npc.role}): \"{npc.greeting or '...'}\"")
                else:
                    self.add_message("NPC: \"이 차원에 온 것을 환영합니다, 여행자여.\"")
            except Exception as e:
                self.add_message("NPC: \"이 차원에 온 것을 환영합니다, 여행자여.\"")
            return True
        elif tt == TileType.CAMPFIRE:
            if self.party:
                for m in self.party:
                    m.current_hp = m.max_hp
                    m.current_mp = m.max_mp
            self.add_message("캠프파이어에서 휴식했습니다. HP/MP 회복!")
            return True
        elif tt == TileType.HEALING_SPRING:
            if self.party:
                for m in self.party:
                    m.current_hp = m.max_hp
                    m.current_mp = m.max_mp
                    m.wound = 0
            self.add_message("치유의 샘에서 모든 상처가 회복되었습니다!")
            return True
        elif tt == TileType.SHOP:
            if self.inventory and console and context:
                from src.ui.gold_shop_ui import open_gold_shop
                floor_level = getattr(self.exploration, 'floor_number', 1)
                open_gold_shop(console, context, self.inventory, floor_level, shop_type="shop")
            else:
                self.add_message("상점을 이용할 수 없습니다.")
            return True
        elif tt == TileType.KITCHEN:
            if self.inventory and console and context:
                from src.ui.cooking_ui import open_cooking_pot
                open_cooking_pot(console, context, self.inventory, is_cooking_pot=True)
            else:
                self.add_message("주방을 이용할 수 없습니다.")
            _check_facility_quest_progress("kitchen", self)
            return True
        elif tt == TileType.BLACKSMITH:
            if self.inventory and console and context:
                from src.ui.gold_shop_ui import open_gold_shop
                floor_level = getattr(self.exploration, 'floor_number', 1)
                open_gold_shop(console, context, self.inventory, floor_level, shop_type="blacksmith")
            else:
                self.add_message("대장간을 이용할 수 없습니다.")
            _check_facility_quest_progress("blacksmith", self)
            return True
        elif tt == TileType.ALCHEMY_LAB:
            if self.inventory and console and context:
                from src.ui.alchemy_ui import open_alchemy_lab
                floor_level = getattr(self.exploration, 'floor_number', 1)
                open_alchemy_lab(console, context, self.inventory, floor_level, party=self.party)
            else:
                self.add_message("연금술 작업대를 이용할 수 없습니다.")
            _check_facility_quest_progress("alchemy_lab", self)
            return True
        elif tt == TileType.QUEST_BOARD:
            if console and context:
                from src.ui.quest_board_ui import open_quest_board
                player_level = self.party[0].level if self.party else 1
                open_quest_board(console, context, player_level=player_level,
                                 player=self.party[0] if self.party else None,
                                 inventory=self.inventory)
            else:
                self.add_message("퀘스트 게시판을 이용할 수 없습니다.")
            return True
        elif tt == TileType.STORAGE_BUILDING:
            if self.inventory and console and context:
                from src.ui.storage_ui import open_storage
                from src.town.town_manager import get_town_manager
                town_mgr = get_town_manager()
                open_storage(console, context, self.inventory, None, town_mgr)
            else:
                self.add_message("창고를 이용할 수 없습니다.")
            return True
        elif tt == TileType.INN:
            if self.party:
                for m in self.party:
                    m.current_hp = m.max_hp
                    m.current_mp = m.max_mp
                    m.wound = 0
            self.add_message("여관에서 충분히 쉬었습니다. 컨디션 완전 회복!")
            return True
        elif tt == TileType.GUILD_HALL:
            if console and context:
                self._open_guild_hall_ui(console, context)
            else:
                self.add_message("모험가 길드입니다.")
            return True
        elif tt == TileType.CAVE_ENTRANCE:
            if console and context:
                self._enter_sub_dungeon(console, context)
            else:
                self.add_message("동굴 입구를 발견했습니다.")
            _check_area_quest_progress("cave_entrance", self)
            return True
        elif tt == TileType.SIGNPOST:
            self._show_signpost_info()
            _check_area_quest_progress("signpost", self)
            return True
        elif tt == TileType.FOUNTAIN:
            self.add_message("마을 중앙의 분수대입니다.")
            return True

        # ── RPG 오픈월드 자연 타일 채집 ──
        from src.gathering.tile_gathering import can_harvest_tile_at, harvest_tile, get_tile_harvest_name

        px, py = self.exploration.player.x, self.exploration.player.y
        if can_harvest_tile_at(px, py, tt):
            tile = self.exploration.dungeon.get_tile(px, py)
            if tile and tile.harvested:
                self.add_message("이미 채집한 곳입니다.")
                return True

            if console and context:
                tile_name = get_tile_harvest_name(tt)
                from src.ui.gathering_ui import show_gathering_prompt_simple
                if not show_gathering_prompt_simple(console, context, tile_name):
                    return True  # 취소

            # 지역 판별
            from src.rpg_mode.rpg_world_generator import _get_region_for_point
            from src.rpg_mode.rpg_world_config import RPG_WORLD_WIDTH, RPG_WORLD_HEIGHT
            region_id = _get_region_for_point(
                px, py,
                RPG_WORLD_WIDTH, RPG_WORLD_HEIGHT
            )

            # 채집 실행
            results = harvest_tile(tile, region_id)

            # 타임스탬프 기록 (리젠용)
            if hasattr(self.exploration.dungeon, 'harvest_timestamps'):
                self.exploration.dungeon.record_harvest(px, py)

            # 인벤토리에 추가 + 결과 메시지
            if results and self.inventory:
                from src.gathering.ingredient import IngredientDatabase
                added = []
                failed = 0
                total_items = 0
                for ingredient_id, qty in results.items():
                    ingredient = IngredientDatabase.get_ingredient(ingredient_id)
                    if ingredient:
                        total_items += qty
                        # 일괄 추가 시도
                        if hasattr(self.inventory, 'add_item'):
                            for _ in range(qty):
                                if self.inventory.add_item(ingredient):
                                    added.append(ingredient.name)
                                else:
                                    failed += 1

                if added:
                    counts = {}
                    for name in added:
                        counts[name] = counts.get(name, 0) + 1
                    msg_parts = [f"{n} x{c}" for n, c in counts.items()]
                    msg = f"채집 완료! {', '.join(msg_parts)}"
                    if failed > 0:
                        msg += f" (무게 초과로 {failed}개 버림)"
                    self.add_message(msg)
                elif total_items > 0:
                    cur_w = getattr(self.inventory, 'current_weight', 0)
                    max_w = getattr(self.inventory, 'max_weight', 0)
                    self.add_message(f"인벤토리가 가득 찼습니다. ({cur_w:.1f}/{max_w:.1f}kg)")
                else:
                    self.add_message("인벤토리가 가득 찼습니다.")
            else:
                self.add_message("채집할 것이 없었습니다.")

            return True

        return False

    def _handle_building_type_ui(self, console, context, building_type_str: str):
        """building_type 문자열 기반으로 건물 UI 열기 (RPG 오픈월드용 폴백)"""
        logger.info(f"[건물 상호작용 폴백] building_type={building_type_str}")
        if building_type_str == "kitchen" or building_type_str == "cooking_pot":
            if self.inventory is not None:
                from src.ui.cooking_ui import open_cooking_pot
                open_cooking_pot(console, context, self.inventory, is_cooking_pot=True)
            else:
                self.add_message("인벤토리가 없어 주방을 사용할 수 없습니다.")
        elif building_type_str == "shop":
            if self.inventory is not None:
                from src.ui.gold_shop_ui import open_gold_shop
                floor_level = getattr(self.exploration, 'floor_number', 1)
                open_gold_shop(console, context, self.inventory, floor_level, shop_type="shop")
            else:
                self.add_message("인벤토리가 없어 상점을 사용할 수 없습니다.")
        elif building_type_str == "blacksmith":
            if self.inventory is not None:
                from src.ui.gold_shop_ui import open_gold_shop
                floor_level = getattr(self.exploration, 'floor_number', 1)
                open_gold_shop(console, context, self.inventory, floor_level, shop_type="blacksmith")
            else:
                self.add_message("인벤토리가 없어 대장간을 사용할 수 없습니다.")
        elif building_type_str == "alchemy_lab":
            if self.inventory is not None:
                from src.ui.alchemy_ui import open_alchemy_lab
                floor_level = getattr(self.exploration, 'floor_number', 1)
                open_alchemy_lab(console, context, self.inventory, floor_level, party=self.party)
            else:
                self.add_message("인벤토리가 없어 연금술 작업대를 사용할 수 없습니다.")
        elif building_type_str == "storage_building":
            if self.inventory is not None:
                from src.ui.storage_ui import open_storage
                from src.town.town_manager import get_town_manager
                town_mgr = get_town_manager()
                open_storage(console, context, self.inventory, None, town_mgr)
            else:
                self.add_message("인벤토리가 없어 창고를 사용할 수 없습니다.")
        elif building_type_str == "quest_board":
            from src.ui.quest_board_ui import open_quest_board
            player_level = self.party[0].level if self.party else 1
            open_quest_board(console, context, player_level=player_level,
                             player=self.party[0] if self.party else None,
                             inventory=self.inventory)
        elif building_type_str == "inn":
            if self.party:
                for m in self.party:
                    m.current_hp = m.max_hp
                    m.current_mp = m.max_mp
                    m.wound = 0
            self.add_message("여관에서 충분히 쉬었습니다. 컨디션 완전 회복!")
        elif building_type_str == "guild_hall":
            self._open_guild_hall_ui(console, context)
        elif building_type_str == "cave_entrance":
            self._enter_sub_dungeon(console, context)
        else:
            self.add_message(f"건물({building_type_str})에 도착했습니다.")

    def _show_signpost_info(self):
        """SIGNPOST 타일에서 이정표 정보 표시"""
        from src.rpg_mode.rpg_world_generator import _get_region_for_point, get_dungeon_entrance_map
        from src.rpg_mode.rpg_world_config import REGION_MAP

        dungeon = self.exploration.dungeon
        px = self.exploration.player.x
        py = self.exploration.player.y
        w, h = dungeon.width, dungeon.height

        region_id = _get_region_for_point(px, py, w, h)
        region = REGION_MAP.get(region_id)

        # 인접 타일에 CAVE_ENTRANCE가 있는지 확인
        adjacent_cave = None
        seed = getattr(dungeon, '_world_seed', 0)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            adj_tile = dungeon.get_tile(px + dx, py + dy)
            if adj_tile and adj_tile.tile_type == TileType.CAVE_ENTRANCE and seed:
                entrance_map = get_dungeon_entrance_map(seed, w, h)
                match = entrance_map.get((px + dx, py + dy))
                if match:
                    _, sub = match
                    if sub.is_boss_dungeon and region and region.boss_level:
                        level = region.boss_level
                    else:
                        level = region.level_min + sub.enemy_level_bonus if region else sub.enemy_level_bonus
                    boss_tag = " [BOSS]" if sub.is_boss_dungeon else ""
                    self.add_message(f"[이정표] {sub.name} (Lv.{level}){boss_tag} - {sub.description}")
                    adjacent_cave = True
                break

        if not adjacent_cave and region:
            self.add_message(f"[이정표] {region.name} (Lv.{region.level_min}~{region.level_max})")
            if region.town_name:
                self.add_message(f"  마을: {region.town_name}")

    def _enter_sub_dungeon(self, console, context):
        """CAVE_ENTRANCE 타일에서 서브 던전 진입 처리"""
        from src.rpg_mode.rpg_world_generator import get_dungeon_entrance_map, _get_region_for_point
        from src.rpg_mode.rpg_world_config import REGION_MAP
        from src.world.dungeon_generator import DungeonGenerator
        from src.ui.combat_ui import run_combat
        from src.combat.combat_manager import CombatState
        from src.world.enemy_generator import EnemyGenerator

        dungeon = self.exploration.dungeon
        seed = getattr(dungeon, '_world_seed', 0)
        if not seed:
            self.add_message("동굴 입구를 발견했습니다.")
            return

        px = self.exploration.player.x
        py = self.exploration.player.y
        w, h = dungeon.width, dungeon.height

        entrance_map = get_dungeon_entrance_map(seed, w, h)
        match = entrance_map.get((px, py))
        if not match:
            self.add_message("이 동굴은 무너져서 진입할 수 없습니다.")
            return

        region, sub = match
        if sub.is_boss_dungeon and region.boss_level:
            level = region.boss_level
        else:
            level = region.level_min + sub.enemy_level_bonus
        boss_tag = " [BOSS]" if sub.is_boss_dungeon else ""
        label = f"{sub.name} (Lv.{level}){boss_tag}"

        # 진입 확인 UI
        from src.ui.cursor_menu import CursorMenu, MenuItem
        confirm_items = [
            MenuItem(text=f"{label} 에 진입한다", description=sub.description, value=True),
            MenuItem(text="떠난다", description="동굴을 떠납니다", value=False),
        ]
        menu = CursorMenu(
            title="동굴 입구",
            items=confirm_items,
            x=console.width // 2 - 22,
            y=console.height // 2 - 4,
            width=44,
        )

        # 입력 큐 비우기
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        confirmed = False
        while True:
            console.clear()
            menu.render(console)
            context.present(console)
            try:
                pygame.event.pump()
            except Exception:
                pass

            def _process(action):
                if action == GameAction.CONFIRM:
                    sel = menu.get_selected_item()
                    if sel and sel.value is not None:
                        return sel.value
                elif action == GameAction.CANCEL:
                    return False
                elif action == GameAction.MOVE_UP:
                    menu.move_cursor_up()
                elif action == GameAction.MOVE_DOWN:
                    menu.move_cursor_down()
                return None

            done = False
            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                if action:
                    r = _process(action)
                    if r is not None:
                        confirmed = r
                        done = True
                        break
                if isinstance(event, tcod.event.Quit):
                    raise SystemExit()
            if not done:
                ga = unified_input_handler.get_action()
                if ga:
                    r = _process(ga)
                    if r is not None:
                        confirmed = r
                        done = True
            if done:
                break
            time.sleep(0.016)

        if not confirmed:
            self.add_message("동굴을 떠났습니다.")
            return

        # 서브 던전 생성 및 탐험
        self.add_message(f"{sub.name}에 진입합니다...")
        dungeon_seed = hash(sub.dungeon_id) & 0x7FFFFFFF
        gen = DungeonGenerator(width=sub.width, height=sub.height)
        sub_map = gen.generate(floor_number=level, seed=dungeon_seed)

        sub_exploration = ExplorationSystem(
            sub_map, self.party, floor_number=level, inventory=self.inventory,
        )
        sub_exploration.is_rpg_sub_dungeon = True

        # 서브 던전 탐험 루프
        while True:
            result = run_exploration(
                console, context, sub_exploration,
                inventory=self.inventory, party=self.party,
                play_bgm_on_start=True,
            )

            result_type = result[0] if isinstance(result, tuple) else result

            if result_type == "combat":
                # 전투에 참여한 맵 적 엔티티 기억
                combat_data = result[1] if isinstance(result, tuple) and len(result) > 1 else {}
                map_enemies = combat_data.get("enemies", []) if combat_data else []

                enemies = EnemyGenerator.generate_enemies(
                    floor_number=max(1, level),
                )
                combat_result = run_combat(
                    console=console, context=context,
                    party=self.party, enemies=enemies,
                    inventory=self.inventory,
                )
                state = combat_result[0] if isinstance(combat_result, tuple) else combat_result

                # 전투 후 맵에서 적 엔티티 제거 (승리/도주 모두)
                if hasattr(sub_exploration, 'enemies') and map_enemies:
                    for me in map_enemies:
                        if me in sub_exploration.enemies:
                            sub_exploration.enemies.remove(me)
                # 충돌 상태 초기화
                sub_exploration.collision_enemy = None

                if state == CombatState.VICTORY:
                    # 보상 계산 및 표시
                    try:
                        from src.combat.experience_system import (
                            RewardCalculator, distribute_party_experience,
                        )
                        from src.ui.reward_ui import show_reward_screen

                        rewards = RewardCalculator.calculate_combat_rewards(
                            enemies, level, is_boss_fight=sub.is_boss_dungeon,
                        )
                        level_up_info = distribute_party_experience(
                            self.party, rewards["experience"],
                        )
                        show_reward_screen(
                            console, context, rewards, level_up_info,
                            inventory=self.inventory,
                        )
                        if self.inventory:
                            self.inventory.add_gold(rewards.get("gold", 0))
                    except Exception as e:
                        logger.warning(f"서브 던전 보상 처리 오류: {e}")

                    self.add_message("전투 승리!")
                    continue  # 서브 던전 탐험 계속
                elif state == CombatState.DEFEAT:
                    self.add_message("전투에서 패배했습니다... 동굴 밖으로 이동합니다.")
                    break
                else:
                    # FLED - 서브 던전 탐험 계속
                    continue
            else:
                # "quit", "main_menu", "floor_up", "floor_down" 등 → 서브 던전 탈출
                break

        # 서브 던전 클리어 메시지 (보스 던전인 경우)
        if sub.is_boss_dungeon and result_type != "combat":
            self.add_message(f"보스 던전 [{sub.name}]을 탐험했습니다!")

        self.add_message("월드맵으로 돌아왔습니다.")
        # 탐험 BGM 복구
        try:
            play_bgm("exploration")
        except Exception:
            pass

    def _open_town_guild_hall(self, console, context):
        """일반 마을 모험가 길드 메뉴 (퀘스트 게시판 + 파티 상태 + 업적)"""
        from src.ui.cursor_menu import CursorMenu, MenuItem
        from src.ui.game_menu import show_message
        from src.audio import play_sfx
        import time
        import pygame

        menu_items = [
            MenuItem("퀘스트 게시판", value="quest_board"),
            MenuItem("파티 상태", value="party_status"),
            MenuItem("업적/도전과제", value="achievements"),
            MenuItem("나가기", value="exit"),
        ]

        guild_menu = CursorMenu(
            title="모험가 길드",
            items=menu_items,
            x=10,
            y=5,
            width=console.width - 20
        )

        # 입력 큐 비우기
        for _ in tcod.event.get():
            pass
        try:
            pygame.event.pump()
            pygame.event.clear()
        except Exception:
            pass
        unified_input_handler.clear_input_state()
        time.sleep(0.05)
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        while True:
            console.clear()
            render_space_background(console, console.width, console.height)
            # 길드 헤더
            header = "=== 모험가 길드 ==="
            console.print((console.width - len(header)) // 2, 2, header, fg=(255, 80, 80))
            console.print(12, 4, "환영합니다, 모험가여!", fg=(200, 200, 200))
            guild_menu.render(console)
            # 안내
            console.print(2, console.height - 2, "↑↓: 선택  Z: 확인  X: 닫기", fg=(150, 150, 150))
            context.present(console)

            try:
                pygame.event.pump()
            except Exception:
                pass

            action = None
            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                if isinstance(event, tcod.event.Quit):
                    return
                if action:
                    break

            if not action:
                action = unified_input_handler.get_action()

            if not action:
                time.sleep(0.01)
                continue

            result = guild_menu.handle_input(action)
            if result == "exit" or action == GameAction.ESCAPE or action == GameAction.MENU:
                play_sfx("ui", "cursor_cancel")
                break
            elif result == "quest_board":
                play_sfx("ui", "confirm")
                try:
                    from src.ui.quest_board_ui import open_quest_board
                    from src.quest.quest_manager import get_quest_manager
                    quest_manager = get_quest_manager()
                    player_level = getattr(self.party[0], 'level', 1) if self.party else 1
                    current_floor = getattr(self, 'current_floor', 0)
                    open_quest_board(
                        console, context,
                        quest_manager=quest_manager,
                        player_level=player_level,
                        player=self.party[0] if self.party else None,
                        current_floor=current_floor,
                        inventory=self.inventory
                    )
                except Exception as e:
                    logger.error(f"퀘스트 게시판 열기 오류: {e}")
                    show_message(console, context, f"퀘스트 게시판을 열 수 없습니다: {e}")
            elif result == "party_status":
                play_sfx("ui", "confirm")
                self._show_town_guild_party_status(console, context)
            elif result == "achievements":
                play_sfx("ui", "confirm")
                try:
                    from src.ui.guild_hall_ui import GuildHallUI
                    from src.achievement.achievement_manager import AchievementManager
                    import __main__
                    achievement_manager = getattr(__main__, 'global_achievement_manager', None)
                    if not achievement_manager:
                        achievement_manager = AchievementManager()
                    guild_ui = GuildHallUI()
                    guild_ui.set_achievement_manager(achievement_manager)
                    guild_ui.run(console, context)
                except Exception as e:
                    logger.error(f"업적 UI 열기 오류: {e}")
                    show_message(console, context, "업적 시스템에 접근할 수 없습니다.")

            # 길드 메뉴로 돌아갈 때 입력 초기화
            for _ in tcod.event.get():
                pass
            try:
                pygame.event.pump()
                pygame.event.clear()
            except Exception:
                pass
            unified_input_handler.clear_input_state()

    def _show_town_guild_party_status(self, console, context):
        """일반 마을 길드 - 파티 상태 표시"""
        from src.ui.game_menu import show_message
        import time
        import pygame

        if not self.party:
            show_message(console, context, "파티가 비어 있습니다.")
            return

        # 입력 초기화
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        while True:
            console.clear()
            render_space_background(console, console.width, console.height)

            header = "=== 파티 상태 ==="
            console.print((console.width - len(header)) // 2, 2, header, fg=(100, 200, 255))

            y = 5
            for i, member in enumerate(self.party):
                name = getattr(member, 'name', f'멤버 {i+1}')
                job = getattr(member, 'job_name', getattr(member, 'character_class', '???'))
                level = getattr(member, 'level', 1)
                hp = getattr(member, 'current_hp', 0)
                max_hp = getattr(member, 'max_hp', 1)
                mp = getattr(member, 'current_mp', 0)
                max_mp = getattr(member, 'max_mp', 1)
                alive = hp > 0

                # 이름 + 직업
                name_color = (255, 255, 255) if alive else (100, 100, 100)
                console.print(5, y, f"{name} (Lv.{level} {job})", fg=name_color)
                y += 1

                # HP 바
                hp_ratio = hp / max_hp if max_hp > 0 else 0
                hp_color = rgb("status.hp_high") if hp_ratio > 0.5 else rgb("status.hp_mid") if hp_ratio > 0.2 else rgb("status.hp_low")
                console.print(7, y, f"HP: {hp}/{max_hp}", fg=hp_color)
                # HP 바 그래프
                bar_width = 20
                filled = int(bar_width * hp_ratio)
                bar_str = "█" * filled + "░" * (bar_width - filled)
                console.print(25, y, bar_str, fg=hp_color)
                y += 1

                # MP 바
                mp_ratio = mp / max_mp if max_mp > 0 else 0
                console.print(7, y, f"MP: {mp}/{max_mp}", fg=(100, 150, 255))
                filled_mp = int(bar_width * mp_ratio)
                bar_str_mp = "█" * filled_mp + "░" * (bar_width - filled_mp)
                console.print(25, y, bar_str_mp, fg=(100, 150, 255))
                y += 1

                # 상태
                if not alive:
                    console.print(7, y, "상태: 전투불능", fg=rgb("threat.critical"))
                else:
                    console.print(7, y, "상태: 정상", fg=(100, 255, 100))
                y += 2

            console.print(2, console.height - 2, "X: 돌아가기", fg=(150, 150, 150))
            context.present(console)

            try:
                pygame.event.pump()
            except Exception:
                pass

            action = None
            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                if isinstance(event, tcod.event.Quit):
                    return
                if action:
                    break
            if not action:
                action = unified_input_handler.get_action()

            if action in (GameAction.ESCAPE, GameAction.MENU, GameAction.CANCEL):
                return

            time.sleep(0.01)

    def _open_guild_hall_ui(self, console, context):
        """GUILD_HALL 타일에서 길드 홀 UI 표시"""
        from src.ui.cursor_menu import CursorMenu, MenuItem
        from src.rpg_mode.rpg_world_generator import _get_region_for_point, get_dungeon_entrance_map
        from src.rpg_mode.rpg_world_config import REGION_MAP, REGIONS

        dungeon = self.exploration.dungeon
        w, h = dungeon.width, dungeon.height
        px = self.exploration.player.x
        py = self.exploration.player.y
        region_id = _get_region_for_point(px, py, w, h)
        region = REGION_MAP.get(region_id)

        while True:
            items = [
                MenuItem(text="퀘스트 게시판", description="의뢰를 확인하고 수락합니다", value="quest"),
                MenuItem(text="파티 상태", description="파티원의 상태를 확인합니다", value="party"),
                MenuItem(text="지역 던전 정보", description="이 지역의 던전 목록을 봅니다", value="dungeon_info"),
                MenuItem(text="나가기", description="길드를 나갑니다", value="exit"),
            ]
            menu = CursorMenu(
                title="모험가 길드",
                items=items,
                x=console.width // 2 - 22,
                y=console.height // 2 - 6,
                width=44,
            )

            for _ in tcod.event.get():
                pass
            unified_input_handler.clear_input_state()

            choice = None
            while choice is None:
                console.clear()
                menu.render(console)
                context.present(console)
                try:
                    pygame.event.pump()
                except Exception:
                    pass

                def _proc(action):
                    if action == GameAction.CONFIRM:
                        sel = menu.get_selected_item()
                        if sel and sel.value is not None:
                            return sel.value
                    elif action == GameAction.CANCEL:
                        return "exit"
                    elif action == GameAction.MOVE_UP:
                        menu.move_cursor_up()
                    elif action == GameAction.MOVE_DOWN:
                        menu.move_cursor_down()
                    return None

                for event in tcod.event.get():
                    action = unified_input_handler.process_tcod_event(event)
                    if action:
                        r = _proc(action)
                        if r is not None:
                            choice = r
                            break
                    if isinstance(event, tcod.event.Quit):
                        raise SystemExit()
                if choice is None:
                    ga = unified_input_handler.get_action()
                    if ga:
                        r = _proc(ga)
                        if r is not None:
                            choice = r
                time.sleep(0.016)

            if choice == "exit":
                self.add_message("길드를 나왔습니다.")
                return
            elif choice == "quest":
                from src.ui.quest_board_ui import open_quest_board
                player_level = self.party[0].level if self.party else 1
                open_quest_board(
                    console, context, player_level=player_level,
                    player=self.party[0] if self.party else None,
                    inventory=self.inventory,
                )
            elif choice == "party":
                self._show_guild_party_status(console, context)
            elif choice == "dungeon_info":
                self._show_guild_dungeon_info(console, context, region)

    def _show_guild_party_status(self, console, context):
        """길드에서 파티 상태 표시"""
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        while True:
            console.clear()
            console.print(2, 1, "[ 파티 상태 ]", fg=(255, 220, 100))
            console.print(2, 2, "-" * 40, fg=(100, 100, 100))

            if self.party:
                for i, member in enumerate(self.party):
                    y = 4 + i * 3
                    name = getattr(member, 'name', '???')
                    job = getattr(member, 'job_name', getattr(member, 'job', '???'))
                    lv = getattr(member, 'level', 1)
                    hp = getattr(member, 'current_hp', 0)
                    max_hp = getattr(member, 'max_hp', 1)
                    mp = getattr(member, 'current_mp', 0)
                    max_mp = getattr(member, 'max_mp', 1)

                    console.print(3, y, f"{name} [{job}] Lv.{lv}", fg=(220, 220, 255))
                    hp_ratio = hp / max(max_hp, 1)
                    hp_color = (100, 255, 100) if hp_ratio > 0.5 else (255, 255, 100) if hp_ratio > 0.25 else (255, 100, 100)
                    console.print(5, y + 1, f"HP {hp}/{max_hp}  MP {mp}/{max_mp}", fg=hp_color)
            else:
                console.print(3, 4, "파티원이 없습니다.", fg=(180, 180, 180))

            console.print(2, console.height - 2, "X: 돌아가기", fg=(180, 180, 180))
            context.present(console)

            try:
                pygame.event.pump()
            except Exception:
                pass

            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                if action in (GameAction.CANCEL, GameAction.CONFIRM):
                    return
                if isinstance(event, tcod.event.Quit):
                    raise SystemExit()
            ga = unified_input_handler.get_action()
            if ga in (GameAction.CANCEL, GameAction.CONFIRM):
                return
            time.sleep(0.016)

    def _show_guild_dungeon_info(self, console, context, region):
        """길드에서 지역 던전 정보 표시"""
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        while True:
            console.clear()
            region_name = region.name if region else "알 수 없는 지역"
            console.print(2, 1, f"[ {region_name} - 던전 정보 ]", fg=(255, 220, 100))
            console.print(2, 2, "-" * 44, fg=(100, 100, 100))

            if region and region.sub_dungeons:
                for i, sub in enumerate(region.sub_dungeons):
                    y = 4 + i * 3
                    if sub.is_boss_dungeon and region.boss_level:
                        level = region.boss_level
                    else:
                        level = region.level_min + sub.enemy_level_bonus
                    tags = []
                    if sub.is_boss_dungeon:
                        tags.append("BOSS")
                    if sub.is_hidden:
                        tags.append("HIDDEN")
                    tag_str = f" [{'/'.join(tags)}]" if tags else ""
                    name_color = (255, 100, 100) if sub.is_boss_dungeon else (200, 200, 255)
                    console.print(3, y, f"{sub.name}{tag_str}", fg=name_color)
                    console.print(5, y + 1, f"Lv.{level}  {sub.description}", fg=(180, 180, 180))
            else:
                console.print(3, 4, "이 지역에는 알려진 던전이 없습니다.", fg=(180, 180, 180))

            console.print(2, console.height - 2, "X: 돌아가기", fg=(180, 180, 180))
            context.present(console)

            try:
                pygame.event.pump()
            except Exception:
                pass

            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                if action in (GameAction.CANCEL, GameAction.CONFIRM):
                    return
                if isinstance(event, tcod.event.Quit):
                    raise SystemExit()
            ga = unified_input_handler.get_action()
            if ga in (GameAction.CANCEL, GameAction.CONFIRM):
                return
            time.sleep(0.016)

    def _find_nearby_cooking_pot(self):
        """
        플레이어 주변의 요리솥 찾기

        Returns:
            가장 가까운 요리솥 HarvestableObject 또는 None
        """
        from src.gathering.harvestable import HarvestableType

        player_x = self.exploration.player.x
        player_y = self.exploration.player.y

        # 인접 범위 (플레이어와 완전히 겹쳐야 함)
        max_distance = 0

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

    def _open_lily_conversation(self, console, context):
        """마을에서 릴리와 대화 (T키)"""
        try:
            from src.ui.npc_dialog_ui import run_npc_dialog
            from src.ui.cursor_menu import CursorMenu

            lily_mgr = self.exploration.lily_dialogue
            progress = self.exploration.rpg_progress

            conversations = lily_mgr.get_town_conversations(
                progress.current_chapter,
                progress.lily_affinity,
                progress.lily_conversations_seen
            )

            if not conversations:
                self.add_message("릴리: \"지금은 특별히 할 얘기가 없어...\"")
                return

            # 대화 주제 메뉴
            menu_items = []
            for conv in conversations:
                title = conv.get("title", "???")
                is_new = conv.get("is_new", False)
                prefix = "★ " if is_new else "  "
                menu_items.append(f"{prefix}{title}")

            menu = CursorMenu(
                title="릴리와 대화",
                items=menu_items,
                width=30,
            )

            selected = menu.run(console, context)
            if selected is None or selected < 0 or selected >= len(conversations):
                return

            conv = conversations[selected]
            conv_id = conv.get("id", "")
            lines_data = conv.get("lines", [])
            affinity_change = conv.get("affinity_change", 0)

            # 대화 표시
            dialog_lines = []
            for line_entry in lines_data:
                dialog_lines.append(line_entry.get("text", ""))

            if dialog_lines:
                speaker = lines_data[0].get("speaker", "릴리") if lines_data else "릴리"
                run_npc_dialog(
                    console, context,
                    npc_name=speaker,
                    dialog_lines=dialog_lines,
                )

            # 친밀도 변화 + 본 대화 기록
            progress.lily_affinity += affinity_change
            progress.lily_conversations_seen.add(conv_id)

            if affinity_change > 0:
                self.add_message(f"릴리와의 유대가 깊어졌다. (친밀도 +{affinity_change})")

        except Exception as e:
            logger.warning(f"릴리 대화 실패: {e}")

    def render(self, console: tcod.console.Console, render_ctx=None):
        """렌더링

        Args:
            console: 렌더링할 tcod 콘솔
            render_ctx: 렌더링 컨텍스트 (pixel overlay 등록용, RaylibContext 등)
        """
        # 마을인지 확인하여 컨텍스트 설정
        is_town = hasattr(self.exploration, 'is_town') and self.exploration.is_town
        bg_context = "town" if is_town else "dungeon"

        # 배경 렌더링 (마을: 핑크 그라데이션, 던전: 바이옴별 배경)
        render_space_background(
            console,
            self.screen_width,
            self.screen_height,
            context=bg_context,
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

        # 릴리 대사 시스템 목표 HUD
        if hasattr(self.exploration, 'objective_tracker'):
            obj = self.exploration.objective_tracker
            if hasattr(obj, 'current') and obj.current:
                obj_text = obj.current.main_text
                if obj.current.sub_text:
                    obj_text += f" - {obj.current.sub_text}"
                console.print(
                    2, 2,
                    f"[Ch.{obj.current.chapter_number}] {obj.current.chapter_title}",
                    fg=(200, 200, 255)
                )
                console.print(
                    2, 3,
                    f"▶ {obj_text}",
                    fg=(255, 255, 200)
                )

        # 실제 시간 기반 밤/낮 표시 (RPG 모드 한정)
        if hasattr(self.exploration, 'time_label'):
            time_label = self.exploration.time_label
            is_night = getattr(self.exploration, 'is_night', False)
            time_color = (100, 100, 200) if is_night else (255, 220, 100)
            time_icon = "☾" if is_night else "☀"
            console.print(
                self.screen_width - 10, 1,
                f"{time_icon} {time_label}",
                fg=time_color
            )

        # 맵 렌더링 (플레이어 중심)
        player = self.exploration.player

        # 동적 조명: 플레이어 위치 업데이트 + 프레임 갱신
        self.map_renderer.lighting.set_player_position(player.x, player.y)
        self.map_renderer.lighting.update(1.0 / 60.0)

        self.map_renderer.render(
            console,
            self.exploration.dungeon,
            camera_x=max(0, player.x - 40),
            camera_y=max(0, player.y - 20),
            view_width=self.screen_width,
            view_height=35
        )

        # ── Raylib 월드 렌더러 오버레이 (타일셋/FOV/엔티티/미니맵) ──
        if self._world_renderer is not None and self._raylib_context is not None:
            wr = self._world_renderer
            dungeon = self.exploration.dungeon

            # setup (최초 1회 또는 맵 변경 시)
            dw = getattr(dungeon, 'width', 0)
            dh = getattr(dungeon, 'height', 0)
            if getattr(wr, 'map_width', 0) != dw or getattr(wr, 'map_height', 0) != dh:
                wr.setup(dw, dh)

            # 엔티티 목록: 적 + NPC
            entities = list(self.exploration.enemies)
            if hasattr(self.exploration, 'npcs'):
                entities.extend(self.exploration.npcs)

            # FOV 데이터
            fov_visible = getattr(self.exploration, 'fov_visible', None)
            fov_explored = getattr(dungeon, 'explored', None)
            tiles = getattr(dungeon, 'tiles', None)

            def _pixel_cb(dt, _wr=wr, _tiles=tiles,
                          _fov_v=fov_visible, _fov_e=fov_explored,
                          _ents=entities, _px=player.x, _py=player.y):
                _wr.update(dt, _px, _py)
                _wr.draw_map(_tiles, _fov_v, _fov_e, _ents, (_px, _py))

            self._raylib_context.add_pixel_overlay(_pixel_cb)

        # 적 위치 표시
        camera_x = max(0, player.x - 40)
        camera_y = max(0, player.y - 20)
        self._camera_x = camera_x
        self._camera_y = camera_y

        # 현재 시야 반경 계산 (FOV 시스템과 동일하게)
        vision_radius = self.exploration.fov_system.default_radius
        if hasattr(self.exploration, 'player') and hasattr(self.exploration.player, 'fov_radius'):
            vision_radius = self.exploration.player.fov_radius

        for enemy in self.exploration.enemies:
            # 타일의 탐험 상태 확인
            tile = self.exploration.dungeon.get_tile(enemy.x, enemy.y)
            if tile and not tile.explored:
                continue  # 탐험하지 않은 영역의 적은 표시하지 않음

            # 실시간 시야 체크: 플레이어와의 거리 계산
            dx = abs(enemy.x - player.x)
            dy = abs(enemy.y - player.y)
            distance = max(dx, dy)  # Chebyshev distance (대각선 포함)

            # 시야 범위 내에 있는지 체크
            if distance > vision_radius:
                continue  # 시야 밖의 적은 표시하지 않음

            enemy_screen_x = enemy.x - camera_x
            enemy_screen_y = 5 + (enemy.y - camera_y)
            if 0 <= enemy_screen_x < self.screen_width and 0 <= enemy_screen_y < 40:
                # 적 색상 결정
                if hasattr(enemy, 'enemy_id') and enemy.enemy_id == "invisible_enemy":
                    # 투명한 적: 파란색, 깜빡임 효과
                    enemy_color = (0, 100, 255)  # 파란색
                    # 30초마다 깜빡임 (나타났다 사라졌다 함)
                    current_time = time.time()
                    should_display = (int(current_time / 30) % 2) == 0
                    if not should_display:
                        continue  # 표시하지 않음 (깜빡임 효과)
                else:
                    # 일반 적 색상: 보스는 선명한 빨강, 일반 적은 주황색
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
                        player_color = rgb("state.disabled") # 유령
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

        # RPG 나침반 HUD (오픈월드 전용)
        is_large_map = (self.exploration.dungeon.width > 300 or
                        self.exploration.dungeon.height > 300)
        if is_large_map:
            self._render_navigation_compass(console)

        # 메시지 로그 (하단)
        self._render_messages(console)

        # RPG 미니맵 오버레이 (메시지 위에 표시)
        if is_large_map:
            self._render_minimap(console)

        # 조작법 (최하단, 로그 패널 밖) - 컬러 키 가이드
        is_multiplayer = (
            self.network_manager is not None or
            (hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer) or
            (hasattr(self.exploration, 'session') and self.exploration.session is not None)
        )
        nearby_cooking_pot = self._find_nearby_cooking_pot()

        # 키 항목 목록: (키 텍스트, 설명 텍스트)
        if is_large_map:
            key_items = [
                ("←↑↓→", "이동"),
                ("Z", "확인/상호작용"),
                ("X", "취소"),
                ("M", "메뉴"),
                ("I", "인벤토리"),
                ("X", "월드맵"),
                ("T", "릴리"),
            ]
        else:
            key_items = [
                ("←↑↓→", "이동"),
                ("Z", "계단/상호작용"),
                ("X", "취소"),
                ("M", "메뉴"),
                ("I", "인벤토리"),
                ("ESC", "종료"),
            ]

        if is_multiplayer:
            # T 키 항목이 이미 있으면 채팅으로 교체, 없으면 추가
            existing_keys = [k for k, _ in key_items]
            if "T" in existing_keys:
                key_items = [(k, "채팅" if k == "T" else d) for k, d in key_items]
            else:
                key_items.append(("T", "채팅"))

        if nearby_cooking_pot:
            key_items.append(("Z/E", "요리솥 사용"))

        # 한 줄로 렌더링 (key=노란색, 설명=회색, 구분자=어두운 회색)
        KEY_COLOR = rgb("accent.amber")
        DESC_COLOR = rgb("text.secondary")
        SEP_COLOR = rgb("line.subtle")

        render_x = 2
        render_y = self.screen_height - 2

        for idx, (key_str, desc_str) in enumerate(key_items):
            if idx > 0:
                console.print(render_x, render_y, "  ", fg=SEP_COLOR)
                render_x += 2
            console.print(render_x, render_y, key_str, fg=KEY_COLOR)
            render_x += len(key_str)
            console.print(render_x, render_y, ":", fg=SEP_COLOR)
            render_x += 1
            console.print(render_x, render_y, desc_str, fg=DESC_COLOR)
            render_x += len(desc_str)

        # 마우스 호버 타일 툴팁
        if self._tooltip_enabled:
            self._render_hover_tooltip(console, camera_x, camera_y)

        # 마우스 호버 타일 정보 오버레이
        if self.mouse_hover_active:
            self._render_tile_hover_info(console)

        # 게이지 pixel overlay 등록 (툴팁 렌더링 후 → 툴팁이 게이지 위에 표시됨)
        self._register_field_gauge_overlay(console, render_ctx)

        # 필드 스킬 UI
        if self.field_skill_ui.is_active:
            self.field_skill_ui.render(console)

        # 채팅 입력창
        if self.chat_input_active:
            self._render_chat_input(console)

        # 종료 확인 대화상자
        if self.quit_confirm_mode:
            self._render_quit_confirm(console)
        elif self.magic_circle_confirm_mode:
            self._render_magic_circle_confirm(console)

    def update_mouse_position(self, pixel_x: int, pixel_y: int, tile_width: int = 1, tile_height: int = 1):
        """마우스 위치 업데이트 (픽셀 → 타일 좌표 변환)

        pygame 이벤트 루프에서 호출. tile_width/tile_height는 한 타일의 픽셀 크기.
        tcod context가 변환을 처리하는 경우 타일 좌표를 직접 전달.
        """
        if tile_width > 1:
            self._mouse_sx = pixel_x // tile_width
            self._mouse_sy = pixel_y // tile_height
        else:
            self._mouse_sx = pixel_x
            self._mouse_sy = pixel_y

    def _render_hover_tooltip(
        self,
        console: tcod.console.Console,
        camera_x: int,
        camera_y: int,
    ):
        """마우스 호버 위치의 타일/적 정보를 툴팁으로 표시"""
        sx = self._mouse_sx
        sy = self._mouse_sy

        # 화면 범위 밖이면 무시
        if sx < 0 or sy < 5 or sx >= self.screen_width or sy >= self.screen_height:
            return

        # 화면 좌표 → 맵 좌표 역변환 (map_renderer: screen = map_x_offset + (map - camera))
        map_x = camera_x + (sx - 0)   # map_x_offset = 0
        map_y = camera_y + (sy - 5)   # map_y_offset = 5

        dungeon = self.exploration.dungeon
        if map_x < 0 or map_y < 0 or map_x >= dungeon.width or map_y >= dungeon.height:
            return

        tile = dungeon.get_tile(map_x, map_y)
        if tile is None:
            return

        # 탐험 안 된 타일, VOID 는 툴팁 표시 안 함
        if not tile.explored:
            return
        if tile.tile_type == TileType.VOID:
            return

        # 타일 정보 취득
        tile_name, tile_desc = get_tile_info(tile.tile_type)

        # 해당 좌표에 적이 있는지 확인
        enemy_at = None
        for enemy in self.exploration.enemies:
            if enemy.x == map_x and enemy.y == map_y:
                # 시야 내에 있는 적만 표시
                if tile.visible:
                    enemy_at = enemy
                break

        self._draw_tile_tooltip(console, tile, tile_name, tile_desc, enemy_at, sx, sy)

    def _draw_tile_tooltip(
        self,
        console: tcod.console.Console,
        tile,
        tile_name: str,
        tile_desc: str,
        enemy,
        sx: int,
        sy: int,
    ):
        """타일 툴팁 박스를 콘솔에 렌더링"""
        # 색상 상수 (combat_tooltip 스타일)
        BG = rgb("state.tooltip")
        BORDER = rgb("line.strong")

        # 내용 조립: (텍스트, 색상) 리스트
        lines: list = []
        lines.append((f" {tile_name}", tile.fg_color))
        lines.append((f" {tile_desc}", (160, 160, 180)))

        # 부가 정보
        if tile.trap_damage > 0:
            lines.append((f" 피해: {tile.trap_damage}", (255, 100, 100)))
        if tile.locked:
            lines.append((" [잠김]", (200, 150, 50)))

        # 적 정보
        if enemy is not None:
            enemy_name = getattr(enemy, "name", "???")
            enemy_lv = getattr(enemy, "level", 1)
            is_boss = getattr(enemy, "is_boss", False)
            color = (255, 80, 80) if is_boss else (255, 180, 80)
            prefix = "BOSS " if is_boss else ""
            lines.append(("", (0, 0, 0)))  # 빈 줄
            lines.append((f" {prefix}{enemy_name} Lv.{enemy_lv}", color))

        # 폭/높이 계산
        tooltip_w = 22
        tooltip_h = len(lines) + 2  # 테두리 상하

        # 콘솔 크기
        try:
            cw = getattr(console, "width", self.screen_width)
            ch = getattr(console, "height", self.screen_height)
        except Exception:
            cw, ch = self.screen_width, self.screen_height
        sw = min(self.screen_width, cw)
        sh = min(self.screen_height, ch)

        # 위치: 마우스 우측 2칸
        tx = sx + 2
        ty = sy

        # 화면 밖 보정
        if tx + tooltip_w >= sw:
            tx = sx - tooltip_w - 1
        if tx < 0:
            tx = 0
        if ty + tooltip_h >= sh:
            ty = sh - tooltip_h - 1
        if ty < 0:
            ty = 0

        # 배경 채우기
        for dy in range(tooltip_h):
            for dx in range(tooltip_w):
                cx, cy = tx + dx, ty + dy
                if 0 <= cx < sw and 0 <= cy < sh:
                    console.rgb["ch"][cy, cx] = ord(" ")
                    console.rgb["bg"][cy, cx] = BG

        # 테두리
        self._draw_tooltip_border(console, tx, ty, tooltip_w, tooltip_h, sw, sh, BORDER, BG)

        # 내용
        for i, (text, color) in enumerate(lines):
            cy = ty + 1 + i
            if 0 <= cy < sh and text:
                max_len = max(0, sw - tx - 2)
                clipped = text[: tooltip_w - 2]
                if max_len > 0:
                    console.print(tx + 1, cy, clipped[:max_len], fg=color, bg=BG)

    def _render_tile_hover_info(self, console: tcod.console.Console):
        """마우스 호버 타일의 환경 효과 오버레이 표시"""
        sx = getattr(self, '_mouse_sx', -1)
        sy = getattr(self, '_mouse_sy', -1)
        if sx < 0 or sy < 5 or sx >= self.screen_width or sy >= self.screen_height:
            return

        # 카메라 좌표 계산
        camera_x = getattr(self, '_camera_x', 0)
        camera_y = getattr(self, '_camera_y', 0)
        map_x = camera_x + sx
        map_y = camera_y + (sy - 5)

        dungeon = getattr(self.exploration, 'dungeon', None)
        if not dungeon:
            return
        if map_x < 0 or map_y < 0 or map_x >= dungeon.width or map_y >= dungeon.height:
            return

        tile = dungeon.get_tile(map_x, map_y)
        if not tile or not tile.explored or not tile.visible:
            return

        # 환경 효과 매니저에서 해당 타일의 효과 확인
        effect_manager = getattr(dungeon, 'environmental_effect_manager', None)
        if not effect_manager:
            return

        active_effects = getattr(effect_manager, 'active_effects', {})
        tile_effects = []
        for effect_type, effect in active_effects.items():
            affected = getattr(effect, 'affected_tiles', None)
            if affected is None:
                continue
            if (map_x, map_y) in affected:
                tile_effects.append(effect)

        if not tile_effects:
            return

        # 오버레이 박스 렌더링
        lines = []
        for eff in tile_effects:
            color = getattr(eff, 'color_overlay', (180, 180, 180))
            lines.append((f" {eff.name}", color))
            desc = getattr(eff, 'description', '')
            if desc:
                lines.append((f"  {desc}", (160, 160, 180)))

        if not lines:
            return

        tooltip_w = max(len(text) + 3 for text, _ in lines)
        tooltip_w = max(tooltip_w, 18)
        tooltip_w = min(tooltip_w, 35)
        tooltip_h = len(lines) + 2

        cw = getattr(console, 'width', self.screen_width)
        ch = getattr(console, 'height', self.screen_height)
        sw = min(self.screen_width, cw)
        sh = min(self.screen_height, ch)

        # 마우스 좌하단에 표시
        tx = sx + 2
        ty = sy + 1
        if tx + tooltip_w >= sw:
            tx = sx - tooltip_w - 1
        if tx < 0:
            tx = 0
        if ty + tooltip_h >= sh:
            ty = sy - tooltip_h
        if ty < 0:
            ty = 0

        BG = rgb("state.tooltip")
        BORDER = rgb("line.strong")

        # 배경
        for dy in range(tooltip_h):
            for dx in range(tooltip_w):
                cx, cy = tx + dx, ty + dy
                if 0 <= cx < sw and 0 <= cy < sh:
                    console.rgb["ch"][cy, cx] = ord(" ")
                    console.rgb["bg"][cy, cx] = BG

        self._draw_tooltip_border(console, tx, ty, tooltip_w, tooltip_h, sw, sh, BORDER, BG)

        for i, (text, color) in enumerate(lines):
            cy = ty + 1 + i
            if 0 <= cy < sh and text:
                clipped = text[:tooltip_w - 2]
                console.print(tx + 1, cy, clipped, fg=color, bg=BG)

    @staticmethod
    def _draw_tooltip_border(console, x, y, w, h, sw, sh, border_color, bg_color):
        """단순 박스 테두리 그리기"""
        # 상단
        if 0 <= y < sh:
            for dx in range(w):
                cx = x + dx
                if 0 <= cx < sw:
                    ch = ord("┌") if dx == 0 else (ord("┐") if dx == w - 1 else ord("─"))
                    console.rgb["ch"][y, cx] = ch
                    console.rgb["fg"][y, cx] = border_color
                    console.rgb["bg"][y, cx] = bg_color
        # 하단
        by = y + h - 1
        if 0 <= by < sh:
            for dx in range(w):
                cx = x + dx
                if 0 <= cx < sw:
                    ch = ord("└") if dx == 0 else (ord("┘") if dx == w - 1 else ord("─"))
                    console.rgb["ch"][by, cx] = ch
                    console.rgb["fg"][by, cx] = border_color
                    console.rgb["bg"][by, cx] = bg_color
        # 좌우
        for dy in range(1, h - 1):
            cy = y + dy
            if 0 <= cy < sh:
                if 0 <= x < sw:
                    console.rgb["ch"][cy, x] = ord("│")
                    console.rgb["fg"][cy, x] = border_color
                    console.rgb["bg"][cy, x] = bg_color
                rx = x + w - 1
                if 0 <= rx < sw:
                    console.rgb["ch"][cy, rx] = ord("│")
                    console.rgb["fg"][cy, rx] = border_color
                    console.rgb["bg"][cy, rx] = bg_color

    def _render_party_status(self, console: tcod.console.Console):
        """파티 상태 렌더링 (전투 UI와 동일한 스타일) - 화면 맨 밑에 배치"""
        self._field_pending_gauges = []

        x = self.screen_width - 30

        # 파티 멤버 수에 따른 높이 계산 (멤버당 4줄 + 소지품 4줄 + 여백)
        party_count = min(4, len(self.exploration.player.party))
        total_height = 2 + (party_count * 4) + 4  # 제목(1줄) + 멤버들 + 소지품(3줄) + 여백
        y = self.screen_height - total_height - 3  # 조작법 공간(3줄) 확보

        console.print(x, y, "[파티 상태]", fg=(100, 255, 100))

        for i, member in enumerate(self.exploration.player.party[:4]):
            # 아군 사이 간격: 3줄 (이름 1줄 + HP 1줄 + MP 1줄 + 여백 1줄 = 4줄씩)
            my = y + 2 + i * 4

            # 이름 + 직업명
            # Character 객체는 name을, PartyMember 객체는 character_name을 사용
            member_name = getattr(member, 'name', getattr(member, 'character_name', 'Unknown'))
            job_name = getattr(member, 'job_name', '')

            # 이름과 직업명을 함께 표시 (직업명이 있으면)
            if job_name:
                display_text = f"{i+1}. {member_name[:8]} ({job_name[:8]})"
            else:
                display_text = f"{i+1}. {member_name[:10]}"

            console.print(x, my, display_text, fg=(255, 200, 100))

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
            
            wound_damage = getattr(member, 'wound', 0)  # Character 클래스의 wound 속성
            entity_id = f"field_ally_{i}_{member_name}"

            # 디버그: 모든 아군의 wound 값 로깅 (DEBUG 레벨로만 출력)
            from src.core.logger import get_logger
            logger = get_logger("world_ui")
            if wound_damage > 0:  # 상처가 있는 경우만 로깅
                logger.debug(f"[아군 상처] {member_name}: wound={wound_damage}")

            # HP 게이지 (스무스 pixel overlay) — 전투 UI와 동일: 현재값만 게이지 내부
            console.print(x, my + 1, "HP:", fg=(200, 200, 200))
            hp_ratio = current_hp / max(max_hp, 1)
            # 콘솔 폴백 (HP) — 전투 UI와 동일 색상 테이블
            console.draw_rect(x + 4, my + 1, 15, 1, ord(" "), bg=(15, 55, 15))
            _hp_filled = max(0, int(15 * max(0.0, min(1.0, hp_ratio))))
            if _hp_filled > 0:
                _hc = (50, 220, 50) if hp_ratio > 0.6 else ((220, 220, 50) if hp_ratio > 0.3 else (220, 50, 50))
                console.draw_rect(x + 4, my + 1, _hp_filled, 1, ord(" "), bg=_hc)
            wound_r = wound_damage / (max_hp + wound_damage) if wound_damage > 0 and max_hp > 0 else 0.0
            self._field_pending_gauges.append((x + 4, my + 1, 15, hp_ratio, "hp", wound_r, f"{current_hp}"))

            # MP 게이지 (스무스 pixel overlay) — 전투 UI와 동일: 현재값만 게이지 내부
            console.print(x, my + 2, "MP:", fg=(200, 200, 200))
            mp_ratio = current_mp / max(max_mp, 1)
            # 콘솔 폴백 (MP) — 전투 UI와 동일 색상
            console.draw_rect(x + 4, my + 2, 15, 1, ord(" "), bg=(25, 38, 65))
            _mp_filled = max(0, int(15 * max(0.0, min(1.0, mp_ratio))))
            if _mp_filled > 0:
                console.draw_rect(x + 4, my + 2, _mp_filled, 1, ord(" "), bg=(100, 150, 255))
            self._field_pending_gauges.append((x + 4, my + 2, 15, mp_ratio, "mp", 0.0, f"{current_mp}"))

        # 인벤토리 정보 (파티 상태 아래로 이동)
        inv_y = y + 2 + 4 * min(4, len(self.exploration.player.party)) + 1
        console.print(x, inv_y, "[소지품]", fg=(200, 200, 255))
        console.print(x + 2, inv_y + 1, f"열쇠: {len(self.exploration.player.keys)}개", fg=(255, 215, 0))

        # 아이템 무게 정보 표시 (현재/최대)
        if self.inventory and hasattr(self.inventory, 'current_weight') and hasattr(self.inventory, 'max_weight'):
            current_weight = self.inventory.current_weight
            max_weight = self.inventory.max_weight
            # 무게가 90% 이상이면 빨간색으로 경고
            weight_color = (255, 100, 100) if current_weight >= max_weight * 0.9 else (200, 200, 200)
            console.print(x + 2, inv_y + 2, f"아이템: ({current_weight:.1f}/{max_weight:.1f}kg)", fg=weight_color)
        else:
            # 인벤토리가 없거나 속성이 없는 경우 기존 방식 사용
            item_count = len(self.inventory.slots) if self.inventory and hasattr(self.inventory, 'slots') else 0
            console.print(x + 2, inv_y + 2, f"아이템: {item_count}개", fg=(200, 200, 200))

        # 게이지 오버레이는 메인 렌더에서 툴팁 렌더링 후에 등록 (툴팁 가림 방지)

    def _register_field_gauge_overlay(self, console, render_ctx=None) -> None:
        """필드 게이지 pixel overlay 등록 — 툴팁 영역을 게이지 위에 재렌더링

        Args:
            console: tcod 콘솔 (툴팁 보호용)
            render_ctx: present()를 호출하는 렌더링 컨텍스트 (game_menu/inventory 패턴)
        """
        # render_ctx 우선, 없으면 self._raylib_context 폴백
        ctx = None
        if render_ctx and hasattr(render_ctx, 'add_pixel_overlay'):
            ctx = render_ctx
        elif self._raylib_context and hasattr(self._raylib_context, 'add_pixel_overlay'):
            ctx = self._raylib_context
        if not ctx or not self._field_pending_gauges:
            return
        _g = list(self._field_pending_gauges)
        self._field_pending_gauges.clear()
        tw = getattr(ctx, 'tile_width', 10)
        th = getattr(ctx, 'tile_height', 13)
        # 툴팁 보호: 콘솔 참조를 캡처해서 오버레이 내부에서 재렌더링
        _console_ref = console
        _tooltip_bg = (15, 15, 30)  # world_ui 툴팁 배경색
        _fr = getattr(ctx, 'font_renderer', None)  # BDF 폰트 렌더러

        def _field_overlay(dt, _gg=_g, _tw=tw, _th=th,
                           _con=_console_ref, _tbg=_tooltip_bg, _ctx=ctx,
                           _font=_fr):
            from src.ui.raylib_backend.smooth_gauge import draw_smooth_gauge
            # 1) 게이지 그리기 — 튜플: (gx, gy, gw, ratio, kind_or_color, wound, [text])
            for entry in _gg:
                gx, gy, gw, r, ci, wound = entry[:6]
                txt = entry[6] if len(entry) > 6 else ""
                if isinstance(ci, str):
                    draw_smooth_gauge(gx * _tw, gy * _th, gw * _tw, _th, r, kind=ci, wound_ratio=wound, text=txt, font_renderer=_font)
                else:
                    draw_smooth_gauge(gx * _tw, gy * _th, gw * _tw, _th, r, custom_color=ci, wound_ratio=wound, text=txt, font_renderer=_font)
            # 2) 툴팁 영역 재렌더링 (게이지 위에 다시 그림)
            try:
                import numpy as np
                bg_arr = _con.bg  # shape: (H, W, 3)
                mask = ((bg_arr[:, :, 0] == _tbg[0]) &
                        (bg_arr[:, :, 1] == _tbg[1]) &
                        (bg_arr[:, :, 2] == _tbg[2]))
                ys, xs = np.where(mask)
                if len(ys) == 0:
                    return
                fr = getattr(_ctx, 'font_renderer', None)
                if not fr or not getattr(fr, 'is_loaded', False):
                    return
                y_min, y_max = int(ys.min()), int(ys.max())
                x_min, x_max = int(xs.min()), int(xs.max())
                for cy in range(y_min, y_max + 1):
                    for cx in range(x_min, x_max + 1):
                        if mask[cy, cx]:
                            ch = int(_con.ch[cy, cx])
                            fg = (int(_con.fg[cy, cx, 0]),
                                  int(_con.fg[cy, cx, 1]),
                                  int(_con.fg[cy, cx, 2]))
                            fr.render_cell(cx * _tw, cy * _th, ch, fg, _tbg)
            except Exception:
                pass

        ctx.add_pixel_overlay(_field_overlay)

    def _render_navigation_compass(self, console: tcod.console.Console):
        """RPG 오픈월드 나침반 HUD - 가장 가까운 마을 방향/거리 + 현재 지역명"""
        if not hasattr(self.exploration, 'nav_spawn_points'):
            return
        spawn_points = self.exploration.nav_spawn_points
        if not spawn_points:
            return

        player = self.exploration.player
        px, py = player.x, player.y

        # 현재 지역명 표시 (플레이어 위치 기반 실시간 판정)
        region_names = {
            "forgotten_forest": "잊혀진 숲",
            "twilight_desert": "황혼 사막",
            "abyss_cavern": "심연 동굴",
            "storm_plateau": "폭풍 고원",
            "eternal_glacier": "영원의 빙하",
            "war_lands": "전쟁의 땅",
            "starlight_throne": "별빛의 왕좌",
        }
        current_region_id = getattr(self.exploration, 'nav_current_region', None)
        # RPG 오픈월드: 플레이어 좌표로 실시간 지역 판정
        if hasattr(self.exploration, 'dungeon') and self.exploration.dungeon:
            dw = self.exploration.dungeon.width
            dh = self.exploration.dungeon.height
            if dw > 300 or dh > 300:
                try:
                    from src.rpg_mode.rpg_world_generator import _get_region_for_point
                    new_region_id = _get_region_for_point(px, py, dw, dh)
                    # 지역 변경 감지 → BGM 변경
                    if new_region_id != current_region_id:
                        region_bgm = {
                            "forgotten_forest": "forest",
                            "twilight_desert": "desert",
                            "abyss_cavern": "caves",
                            "storm_plateau": "highlands",
                            "eternal_glacier": "frostlands",
                            "war_lands": "warlands",
                            "starlight_throne": "worldmap",
                        }
                        bgm_track = region_bgm.get(new_region_id)
                        if bgm_track:
                            try:
                                from src.audio import play_bgm
                                play_bgm(bgm_track)
                            except Exception:
                                pass
                    current_region_id = new_region_id
                    self.exploration.nav_current_region = current_region_id
                except Exception:
                    pass
        region_name = region_names.get(current_region_id, "알 수 없는 지역")
        console.print(
            self.screen_width // 2 - len(region_name) - 1, 0,
            f"< {region_name} >",
            fg=(180, 220, 255)
        )

        # 가장 가까운 마을 찾기
        nearest_id = None
        nearest_dist = float('inf')
        nearest_x, nearest_y = 0, 0
        for rid, (tx, ty) in spawn_points.items():
            dist = ((px - tx) ** 2 + (py - ty) ** 2) ** 0.5
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_id = rid
                nearest_x, nearest_y = tx, ty

        if nearest_id is None:
            return

        # 방향 화살표 계산
        dx = nearest_x - px
        dy = nearest_y - py
        dist_int = int(nearest_dist)

        if dist_int < 15:
            # 마을 근처면 "마을 근처" 표시
            compass_text = "★ 마을 근처"
            compass_color = (100, 255, 150)
        else:
            # 방향 화살표
            import math
            angle = math.atan2(-dy, dx)  # y축 반전 (화면 좌표)
            # 8방향 매핑
            arrows = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"]
            idx = int((angle + math.pi) / (math.pi / 4) + 0.5) % 8
            # 인덱스 보정: atan2 0=오른쪽, 반시계방향
            arrow = arrows[idx]

            town_name_map = {
                "forgotten_forest": "실바나",
                "twilight_desert": "사막 마을",
                "abyss_cavern": "동굴 마을",
                "storm_plateau": "고원 마을",
                "eternal_glacier": "빙하 마을",
                "war_lands": "전장 마을",
                "starlight_throne": "왕좌 마을",
            }
            town_name = town_name_map.get(nearest_id, "마을")

            if dist_int > 500:
                dist_text = f"{dist_int // 100}00+"
            else:
                dist_text = str(dist_int)
            compass_text = f"{arrow} {town_name} ({dist_text}m)"
            # 거리에 따라 색상 변화
            if dist_int > 300:
                compass_color = (255, 150, 100)  # 멀면 주황
            elif dist_int > 100:
                compass_color = (255, 255, 150)  # 중간이면 노랑
            else:
                compass_color = (150, 255, 150)  # 가까우면 초록

        # 우측 상단 근처에 표시 (시간 표시 아래)
        console.print(
            self.screen_width - len(compass_text) - 2, 2,
            compass_text,
            fg=compass_color
        )

    def _render_minimap(self, console: tcod.console.Console):
        """RPG 오픈월드 미니맵 오버레이"""
        if not self.show_minimap:
            return
        if not hasattr(self.exploration, 'nav_spawn_points'):
            return

        spawn_points = self.exploration.nav_spawn_points
        player = self.exploration.player
        map_w = self.exploration.dungeon.width
        map_h = self.exploration.dungeon.height

        # 미니맵 크기 (화면 중앙에 표시)
        mini_w = 40
        mini_h = 22
        mini_x = (self.screen_width - mini_w) // 2
        mini_y = (self.screen_height - mini_h) // 2

        # 배경 프레임 — semantic 토큰 (패널/보더)
        console.draw_frame(
            mini_x, mini_y, mini_w, mini_h,
            title=" 월드 맵 [N: 닫기] ",
            fg=rgb("line.default"),
            bg=rgb("surface.panel"),
        )

        # 지역 색상
        region_colors = {
            "forgotten_forest": (50, 150, 50),
            "twilight_desert": (200, 180, 80),
            "abyss_cavern": (100, 60, 150),
            "storm_plateau": (80, 180, 80),
            "eternal_glacier": (150, 200, 255),
            "war_lands": (200, 80, 50),
            "starlight_throne": (200, 180, 255),
        }
        region_icons = {
            "forgotten_forest": "♣",
            "twilight_desert": "☼",
            "abyss_cavern": "▼",
            "storm_plateau": "≡",
            "eternal_glacier": "❄",
            "war_lands": "⚔",
            "starlight_throne": "★",
        }
        region_labels = {
            "forgotten_forest": "잊혀진 숲",
            "twilight_desert": "황혼 사막",
            "abyss_cavern": "심연 동굴",
            "storm_plateau": "폭풍 고원",
            "eternal_glacier": "영원의 빙하",
            "war_lands": "전쟁의 땅",
            "starlight_throne": "별빛의 왕좌",
        }

        # 내부 영역
        inner_x = mini_x + 1
        inner_y = mini_y + 1
        inner_w = mini_w - 2
        inner_h = mini_h - 2

        # 각 마을 위치를 미니맵 좌표로 변환하여 표시
        current_region = getattr(self.exploration, 'nav_current_region', None)
        for rid, (tx, ty) in spawn_points.items():
            # 맵 좌표 → 미니맵 좌표
            mx = inner_x + int(tx / max(1, map_w) * (inner_w - 1))
            my = inner_y + int(ty / max(1, map_h) * (inner_h - 1))
            mx = max(inner_x, min(inner_x + inner_w - 1, mx))
            my = max(inner_y, min(inner_y + inner_h - 1, my))

            color = region_colors.get(rid, (150, 150, 150))
            icon = region_icons.get(rid, "?")
            label = region_labels.get(rid, rid)

            # 현재 지역은 밝게 표시
            if rid == current_region:
                color = (min(255, color[0] + 80), min(255, color[1] + 80), min(255, color[2] + 80))

            console.print(mx, my, icon, fg=color)
            # 라벨 (아이콘 옆)
            label_x = mx + 2
            if label_x + len(label) > inner_x + inner_w:
                label_x = mx - len(label) - 1
            if inner_x <= label_x and label_x + len(label) <= inner_x + inner_w:
                console.print(label_x, my, label, fg=color)

        # 플레이어 위치
        pmx = inner_x + int(player.x / max(1, map_w) * (inner_w - 1))
        pmy = inner_y + int(player.y / max(1, map_h) * (inner_h - 1))
        pmx = max(inner_x, min(inner_x + inner_w - 1, pmx))
        pmy = max(inner_y, min(inner_y + inner_h - 1, pmy))
        # 깜빡임 효과
        import time
        blink = int(time.time() * 3) % 2 == 0
        if blink:
            console.print(pmx, pmy, "@", fg=(255, 255, 100))
        else:
            console.print(pmx, pmy, "@", fg=(255, 200, 50))

        # 하단 범례
        legend_y = mini_y + mini_h - 2
        console.print(inner_x, legend_y, "@ 현재 위치", fg=(255, 255, 100))

    def _render_messages(self, console: tcod.console.Console):
        """메시지 로그 - 파티 상태창 왼쪽에 크게 표시"""
        # 파티 상태창 위치 계산 (파티 상태창과 동일한 계산)
        party_count = min(4, len(self.exploration.player.party))
        total_height = 2 + (party_count * 4) + 4  # 제목(1줄) + 멤버들 + 소지품(3줄) + 여백
        party_y = self.screen_height - total_height - 3  # 조작법 공간(3줄) 확보

        # 로그 패널 설정 (파티 상태창 왼쪽에 넓게 배치)
        party_x = self.screen_width - 30  # 파티 상태창 시작 위치
        log_panel_x = 2
        log_panel_width = party_x - log_panel_x - 4  # 파티 상태창 왼쪽까지 (여백 4칸)
        log_panel_height = total_height // 2  # 파티 상태창 높이의 절반
        log_panel_y = self.screen_height - log_panel_height - 3  # 하단에 배치 (조작법 공간 확보)

        # 로그 패널 테두리
        draw_styled_box(
            console,
            log_panel_x - 1,
            log_panel_y - 1,
            log_panel_width + 2,
            log_panel_height + 2,
            title="로그",
            fg=rgb("line.default"),
            bg=rgb("surface.panel")
        )

        # 로그 메시지 표시 (아래에서 위로 최신 메시지부터)
        max_lines = log_panel_height - 1  # 테두리 제외
        max_scroll = max(0, len(self.messages) - max_lines)
        self.log_scroll_offset = max(0, min(self.log_scroll_offset, max_scroll))
        start_idx = max(0, len(self.messages) - max_lines - self.log_scroll_offset)
        end_idx = len(self.messages) - self.log_scroll_offset
        visible_messages = self.messages[start_idx:end_idx]

        for i, msg in enumerate(visible_messages):
            # 메시지가 패널 너비를 초과하면 자르기
            if len(msg) > log_panel_width - 2:
                msg = msg[:log_panel_width - 5] + "..."
            # 릴리 대사 색상 구분
            if msg.startswith('릴리:'):
                msg_color = (255, 200, 255)
            else:
                msg_color = rgb("text.secondary")
            console.print(
                log_panel_x,
                log_panel_y + i,
                msg,
                fg=msg_color
            )
        if len(self.messages) > max_lines:
            if self.log_scroll_offset < max_scroll:
                console.print(log_panel_x + log_panel_width - 1, log_panel_y + max_lines - 1, "▼", fg=rgb("accent.cyan"))
            if self.log_scroll_offset > 0:
                console.print(log_panel_x + log_panel_width - 1, log_panel_y, "▲", fg=rgb("accent.cyan"))

    def _render_quit_confirm(self, console: tcod.console.Console):
        """종료 확인 대화상자"""
        box_width = 50
        box_height = 10
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 박스
        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title="게임 종료",
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

    def _render_magic_circle_confirm(self, console: tcod.console.Console):
        """마법진 사용 확인 대화상자"""
        box_width = 50
        box_height = 10
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 박스
        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title="마법진 발견",
            fg=(100, 200, 255),
            bg=(0, 0, 0)
        )

        # 메시지
        msg = "마법진을 사용하시겠습니까?"
        console.print(
            box_x + (box_width - len(msg)) // 2,
            box_y + 3,
            msg,
            fg=(255, 255, 255)
        )

        msg2 = "(랜덤 효과: 텔레포트, 회복, 버프 등)"
        console.print(
            box_x + (box_width - len(msg2)) // 2,
            box_y + 5,
            msg2,
            fg=(200, 200, 255)
        )

        # 버튼
        y = box_y + 7
        yes_color = (255, 255, 100) if self.magic_circle_confirm_yes else (180, 180, 180)
        no_color = (255, 255, 100) if not self.magic_circle_confirm_yes else (180, 180, 180)

        console.print(
            box_x + 12, y,
            "[ 예 ]" if self.magic_circle_confirm_yes else "  예  ",
            fg=yes_color
        )

        console.print(
            box_x + 28, y,
            "[아니오]" if not self.magic_circle_confirm_yes else " 아니오 ",
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
        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title="채팅",
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


def run_exploration(
    console: tcod.console.Console,
    context: tcod.context.Context,
    exploration: ExplorationSystem,
    inventory=None,
    party=None,
    play_bgm_on_start: bool = True,
    network_manager=None,
    local_player_id=None,
) -> tuple:
    """
    탐험 실행

    Args:
        play_bgm_on_start: 탐험 시작 시 BGM 재생 여부 (기본 True, 전투 후 복귀 시 False)

    Returns:
        "quit", "combat", "floor_up", "floor_down"
    """
    ui = WorldUI(console.width, console.height, exploration, inventory, party, network_manager, local_player_id)
    handler = InputHandler()

    # RPG 모드 초기 안내 메시지
    if hasattr(exploration, 'initial_messages') and exploration.initial_messages:
        for msg in exploration.initial_messages:
            ui.add_message(msg)
        exploration.initial_messages = []  # 한 번만 표시

    # 릴리 대사 타이머 초기화
    lily_check_timer = time.time()

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
    unified_input_handler.clear_input_state()

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

    # ===== 20/30층 스토리 보스 강제 조우 체크 =====
    # 마을이 아니고, 20층 또는 30층에 처음 진입했을 때 즉시 보스 전투 트리거
    if not (hasattr(exploration, 'is_town') and exploration.is_town):
        floor = exploration.floor_number
        
        # 스토리 보스 전투 트리거 플래그 확인
        if not hasattr(exploration, 'story_boss_triggered'):
            exploration.story_boss_triggered = False
        
        # 20층: 세피로스, 30층: 아벨 카인
        if floor in [20, 30] and not exploration.story_boss_triggered:
            from src.story.story_system import get_story_system
            story_system = get_story_system()
            
            # 20층은 sephiroth_defeated, 30층은 cain_defeated 체크
            should_trigger_boss = False
            boss_type = None
            
            if floor == 20 and not story_system.sephiroth_defeated:
                should_trigger_boss = True
                boss_type = "sephiroth"
                logger.info("[스토리 보스] 20층 진입 - 세피로스와 강제 조우!")
            elif floor == 30 and not getattr(story_system, 'cain_defeated', False):
                should_trigger_boss = True
                boss_type = "cain"
                logger.info("[스토리 보스] 30층 진입 - 아벨 카인과 강제 조우!")
            
            if should_trigger_boss:
                # 플래그 설정 (중복 트리거 방지)
                exploration.story_boss_triggered = True
                
                # 스토리 보스 전투 데이터 반환
                return ("story_boss_combat", {
                    "floor": floor,
                    "boss_type": boss_type,
                    "participants": party or (exploration.player.party if hasattr(exploration, 'player') else None)
                })

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
        
        # 시간 기반 적 이동 업데이트 (싱글/멀티 모두)
        # 적과 플레이어가 독립적으로 시간 기반으로 움직임
        import time
        current_time = time.time()

        # 적 이동 업데이트
        if hasattr(exploration, '_move_all_enemies'):
            # 멀티플레이 클라이언트 여부 판별
            _is_mp_client = (hasattr(exploration, 'is_multiplayer') and exploration.is_multiplayer
                             and hasattr(exploration, 'is_host') and not exploration.is_host)

            # 시간 기반 이동 - 각 적이 자신의 move_interval에 따라 이동
            exploration._move_all_enemies()

            # 멀티플레이 클라이언트: 적 충돌은 호스트에서만 처리 (독자 전투 방지)
            if _is_mp_client:
                if hasattr(exploration, 'collision_enemy') and exploration.collision_enemy:
                    logger.info(f"[전투 스킵] 멀티플레이 클라이언트 - collision_enemy 초기화: {getattr(exploration.collision_enemy, 'name', 'Unknown')}")
                exploration.collision_enemy = None

            # 시간 기반 이동 중 적과 플레이어가 충돌했는지 확인
            if hasattr(exploration, 'collision_enemy') and exploration.collision_enemy:

                collided_enemy = exploration.collision_enemy

                # 도망 쿨다운 체크 (이중 안전장치)
                import time
                enemy_id = id(collided_enemy)
                if hasattr(exploration, 'fled_enemies') and enemy_id in exploration.fled_enemies:
                    fled_time = exploration.fled_enemies[enemy_id]
                    if time.time() - fled_time <= 5.0:
                        logger.debug(f"[전투 스킵] {collided_enemy.name} 도망 쿨다운 중 - 전투 무시")
                        exploration.collision_enemy = None  # 충돌 초기화
                        return

                logger.info(f"[전투 트리거] 시간 기반 이동 중 충돌: {collided_enemy.name}")

                # 전투 트리거: 충돌한 적과 주변 적들 수집
                combat_enemies = [collided_enemy]
                combat_range = 3  # 3칸 범위 내의 적들 포함
                for other_enemy in exploration.enemies:
                    if other_enemy == collided_enemy:
                        continue
                    distance = abs(other_enemy.x - collided_enemy.x) + abs(other_enemy.y - collided_enemy.y)
                    if distance <= combat_range:
                        combat_enemies.append(other_enemy)

                # UI에서 전투 트리거
                ui.combat_requested = True
                # exploration.py의 _trigger_combat_with_enemy와 동일한 로직 적용
                # 주변 적 수에 따라 전투 적 수 결정 (2-4마리)
                nearby_count = len(combat_enemies)
                if nearby_count == 1:
                    import random
                    # 1마리 조우: 2~4마리 전투 (기본값)
                    num_enemies = random.randint(2, 4)
                elif nearby_count == 2:
                    import random
                    # 2마리 조우: 3~4마리 전투
                    num_enemies = random.randint(3, 4)
                else:
                    # 3마리 이상 조우: 4마리 전투 (최대)
                    num_enemies = 4
                
                ui.combat_num_enemies = num_enemies
                ui.combat_enemies = combat_enemies
                ui.combat_is_boss = False  # 필드 충돌은 보스전 아님
                ui.combat_enemy_level = getattr(collided_enemy, 'level', None)
                if hasattr(exploration, 'player'):
                    ui.combat_position = (exploration.player.x, exploration.player.y)
                
                # 멀티플레이: 전투 참여자 수집 (주변 플레이어들)
                if hasattr(exploration, '_get_nearby_participants') and ui.combat_position:
                    ui.combat_participants = exploration._get_nearby_participants(ui.combat_position)
                    logger.info(f"멀티플레이 충돌 전투 참여자 수집: {len(ui.combat_participants)}명")
                else:
                    # 싱글플레이 또는 메서드 없는 경우 현재 파티 사용
                    ui.combat_participants = ui.party

                # 전투 진입 후 collision_enemy 반드시 리셋 (미리셋 시 매 프레임 전투 반복 트리거)
                exploration.collision_enemy = None

        # 환경 효과 업데이트 (플레이어가 같은 타일에 머물러 있을 때도 적용)
        try:
            effect_message = exploration.update_environmental_effects()
            if effect_message and hasattr(ui, 'add_message'):
                ui.add_message(effect_message)
        except Exception as e:
            logger.warning(f"환경 효과 업데이트 오류: {e}")

    # WorldUI에 업데이트 콜백 설정
    ui.on_update = update_game_state

    # 메인 루프 진입 직전: 초기화 중 쌓인 이벤트 2차 플러시 + CONFIRM 쿨다운
    # (BGM 로딩 등 초기화 작업 중 SDL 이벤트가 새로 쌓일 수 있으므로)
    tcod.event.get()
    pygame.event.clear()
    import time as _time
    ui._confirm_cooldown_until = _time.time() + 0.5

    while True:
        # 메인 루프에서도 업데이트 실행
        update_game_state()

        # pygame 이벤트 처리 (게임패드 입력을 위해) - 더 자주 호출
        pygame.event.pump()  # pygame 이벤트 큐 업데이트
        # print("🔄 pygame.event.pump() 호출됨", end='\r')  # 디버깅용 (필요시 활성화)


        # 마우스 셀 좌표 업데이트 (호버 툴팁용)
        if ui._tooltip_enabled:
            try:
                mx, my = pygame.mouse.get_pos()
                if hasattr(context, 'pixel_to_cell'):
                    cell_x, cell_y = context.pixel_to_cell(mx, my)
                else:
                    tile_w = getattr(context, 'tile_width', 10)
                    tile_h = getattr(context, 'tile_height', 13)
                    cell_x, cell_y = mx // tile_w, my // tile_h
                ui._mouse_sx = cell_x
                ui._mouse_sy = cell_y
            except Exception:
                pass

        # 릴리 대기 대사 체크
        if hasattr(exploration, 'lily_dialogue') and hasattr(exploration, 'rpg_progress'):
            now = time.time()
            if now - lily_check_timer > 10.0:  # 10초마다 체크
                lily_check_timer = now
                ch = exploration.rpg_progress.current_chapter
                aff = exploration.rpg_progress.lily_affinity
                spoke = False

                idle_line = exploration.lily_dialogue.check_idle_line(ch, aff)
                if idle_line:
                    ui.add_message(f'릴리: "{idle_line}"')
                    spoke = True

                # idle이 나왔으면 random은 스킵 (동시 출력 방지)
                if not spoke:
                    random_line = exploration.lily_dialogue.check_random_chat(ch, aff)
                    if random_line:
                        ui.add_message(f'릴리: "{random_line}"')
                        spoke = True

                # 밤 탐험 대사 (RPG 모드, 실제 시간 기반) - 다른 대사 없을 때만
                if not spoke and getattr(exploration, 'is_night', False):
                    from datetime import datetime
                    cur_hour = datetime.now().hour
                    exploration.is_night = (cur_hour >= 19 or cur_hour < 6)
                    if exploration.is_night:
                        night_line = exploration.lily_dialogue.get_night_line(ch, aff)
                        if night_line:
                            ui.add_message(f'릴리: "{night_line}"')

        # 렌더링
        ui.render(console, render_ctx=context)
        context.present(console)

        # 입력 처리
        action = None
        key_event = None

        # 게임패드 입력 우선 확인
        # print("🔍 게임패드 입력 확인 시작", end='\r')  # 디버깅용 (필요시 활성화)
        action = unified_input_handler.get_action()
        # if action:
        #     print(f"✅ 게임패드 액션 감지: {action}")  # 디버깅용 (필요시 활성화)

        # tcod 이벤트 처리 (키보드/마우스) - 게임패드 입력이 없을 때만
        if not action:
            # print("⌨️ 키보드 입력 확인 시작", end='\r')  # 디버깅용 (필요시 활성화)
            # tcod 이벤트는 non-blocking으로 변경
            events = tcod.event.get()  # wait 대신 get 사용
            for event in events:
                pointer_event = unified_input_handler.process_pointer_event(event)
                if pointer_event is not None:
                    pointer_result = ui.handle_pointer_event(pointer_event, console, context)
                    if pointer_result.action is not None:
                        break
                    continue
                result = unified_input_handler.process_tcod_event(event)
                if isinstance(event, tcod.event.KeyDown):
                    key_event = event
                if result:
                    action = result
                    break  # 액션 발견 시 즉시 중단 (마우스 이벤트가 덮어쓰는 것 방지)

        if action or key_event:
            # Debug: 액션 수신
            done = ui.handle_input(action, console, context, key_event)
            # Debug: handle_input 반환
            if done:
                # Debug: 루프 탈출
                break
        
        # 멀티플레이 클라이언트: DUNGEON_DATA 수신 체크 (매 프레임, 입력 여부 무관)
        # network_manager에 직접 플래그가 저장됨 (session 없이도 작동)
        if network_manager and not getattr(network_manager, 'is_host', True):
            dungeon_received = getattr(network_manager, 'dungeon_data_received', False)
            if dungeon_received:
                logger.info(f"✅ DUNGEON_DATA 플래그 감지! floor={getattr(network_manager, 'pending_floor_number', None)}")
                try:
                    from src.persistence.save_system import deserialize_dungeon
                    pending_data = getattr(network_manager, 'pending_dungeon_data', None)
                    pending_floor = getattr(network_manager, 'pending_floor_number', 1)
                    
                    logger.info(f"📦 pending_data 존재: {pending_data is not None}, 타입: {type(pending_data).__name__ if pending_data else 'None'}")
                    
                    if pending_data:
                        # deserialize_dungeon은 (dungeon, enemies) 튜플 반환
                        new_dungeon, new_enemies = deserialize_dungeon(pending_data)
                        
                        # exploration 업데이트
                        exploration.dungeon = new_dungeon
                        exploration.enemies = new_enemies
                        exploration.floor_number = pending_floor
                        exploration.is_town = False  # 던전이므로 마을 플래그 해제
                        
                        # 시작 위치 설정
                        if "player_start_x" in pending_data and "player_start_y" in pending_data:
                            exploration.player.x = pending_data["player_start_x"]
                            exploration.player.y = pending_data["player_start_y"]
                            logger.info(f"📍 클라이언트 스폰 위치 설정 (Host Sync): ({exploration.player.x}, {exploration.player.y})")
                        elif new_dungeon.rooms:
                            # fallback: 첫 번째 방 중앙
                            first_room = new_dungeon.rooms[0]
                            exploration.player.x = first_room.x + first_room.width // 2
                            exploration.player.y = first_room.y + first_room.height // 2
                            logger.info(f"📍 클라이언트 스폰 위치 설정 (Room 0 fallback): ({exploration.player.x}, {exploration.player.y}) Rooms: {len(new_dungeon.rooms)}")
                        elif new_dungeon.stairs_down:
                            exploration.player.x = new_dungeon.stairs_down[0]
                            exploration.player.y = new_dungeon.stairs_down[1]
                            logger.warning(f"⚠️ 클라이언트 스폰 위치 설정 (Stairs fallback): ({exploration.player.x}, {exploration.player.y}) Rooms Empty!")
                        else:
                            logger.error("❌ 클라이언트 스폰 위치 설정 실패: 방도 없고 계단도 없음!")
                        
                        # 세션의 플레이어 위치도 업데이트 (중요: 멀티플레이 이동/렌더링 동기화)
                        if hasattr(exploration, 'session') and exploration.session and hasattr(exploration, 'local_player_id'):
                            local_id = exploration.local_player_id
                            if local_id in exploration.session.players:
                                exploration.session.players[local_id].x = exploration.player.x
                                exploration.session.players[local_id].y = exploration.player.y
                                
                                # player_positions도 업데이트
                                if hasattr(exploration, 'player_positions'):
                                    exploration.player_positions[local_id] = (exploration.player.x, exploration.player.y)

                                # 새 층 좌표계 기준으로 이동 인가 기준점 재설정
                                # (미재인가 시 첫 이동이 rejection rollback 무한 루프 유발)
                                reauth = getattr(exploration, '_reauthorize_player_position', None)
                                if callable(reauth):
                                    reauth(local_id)
                                    logger.info(f"📍 클라이언트 위치 재인가: ({exploration.player.x}, {exploration.player.y})")

                                # 이동 타임스탬프 기준점도 새 층 시점으로 리셋
                                # (이전 층 타임스탬프가 남으면 새 층 첫 이동이 stale 거부됨)
                                local_player = exploration.session.players[local_id]
                                if hasattr(local_player, 'last_movement_timestamp'):
                                    local_player.last_movement_timestamp = 0.0

                                logger.info(f"📍 클라이언트 세션 위치 업데이트: ({exploration.player.x}, {exploration.player.y})")

                        # FOV 업데이트
                        if hasattr(exploration, 'update_fov'):
                            exploration.update_fov()
                        
                        ui.add_message(f"던전 {pending_floor}층으로 이동했습니다!")
                        logger.info(f"클라이언트 던전 업데이트 완료: {pending_floor}층")
                    
                    # 플래그 초기화
                    network_manager.dungeon_data_received = False
                    network_manager.pending_dungeon_data = None
                except Exception as e:
                    logger.error(f"클라이언트 던전 업데이트 실패: {e}", exc_info=True)

        # 멀티플레이 호스트: 탐험 중 파티 상태 동기화 (0.5초 간격)
        if hasattr(exploration, 'sync_exploration_party_state'):
            exploration.sync_exploration_party_state()

        # 멀티플레이 클라이언트: 대기 중인 전투 즉시 진입 (매 프레임 폴링)
        # _pending_client_combat은 move_player 호출 없이도 즉시 처리되어야 한다.
        if not ui.combat_requested and hasattr(exploration, 'get_pending_combat'):
            pending_combat = exploration.get_pending_combat()
            if pending_combat is not None:
                logger.info("get_pending_combat: 대기 전투 감지 → 전투 진입")
                ui._handle_exploration_result(pending_combat, console, context)

        # 멀티플레이에서 session이 있는 경우 추가 체크 (호스트 측)
        session = None
        if network_manager and hasattr(network_manager, 'session'):
            session = network_manager.session
        elif hasattr(exploration, 'session') and exploration.session:
            session = exploration.session
        
        # 멀티플레이 자동 층 이동: 계단 위에 있으면 자동으로 준비 상태 + 모든 준비 시 이동
        if network_manager and session:
            is_multiplayer = hasattr(exploration, 'is_multiplayer') and exploration.is_multiplayer
            is_host = getattr(network_manager, 'is_host', False)
            
            if is_multiplayer:
                tile = exploration.dungeon.get_tile(exploration.player.x, exploration.player.y)
                if tile and tile.tile_type == TileType.STAIRS_DOWN:
                    local_player_id = getattr(exploration, 'local_player_id', None)
                    
                    # 자동으로 준비 상태 설정
                    if local_player_id and local_player_id not in session.floor_ready_players:
                        session.set_floor_ready(local_player_id, True)
                        ui.add_message("계단 위 - 대기 중...")
                        logger.info(f"계단 위 - 자동 준비: {local_player_id}")
                        
                        # 준비 상태 브로드캐스트
                        from src.multiplayer.protocol import MessageBuilder
                        import asyncio
                        try:
                            ready_msg = MessageBuilder.floor_ready(
                                player_id=local_player_id,
                                ready=True,
                                ready_players=list(session.floor_ready_players),
                                total_players=len(session.players)
                            )
                            server_loop = getattr(network_manager, '_server_event_loop', None)
                            client_loop = getattr(network_manager, '_client_event_loop', None)
                            event_loop = server_loop or client_loop
                            if event_loop and event_loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    network_manager.broadcast(ready_msg),
                                    event_loop
                                )
                            logger.debug("층 이동 준비 상태 브로드캐스트")
                        except Exception as e:
                            logger.error(f"준비 상태 브로드캐스트 실패: {e}")
                    
                    # 호스트: 모든 플레이어 준비 완료 시 자동 층 이동 트리거
                    if is_host and session.is_all_ready_for_floor_change():
                        ui.floor_change_requested = "floor_down"
                        ui.add_message("모든 플레이어 준비 완료! 이동합니다...")
                        session.reset_floor_ready()
                        logger.info("호스트: 자동 층 변경 트리거")
                        break  # 루프 탈출 → main.py에서 층 변경 처리
        
        
        # 입력 처리 후 즉시 상태 체크 (전투 요청 확인)
        if ui.combat_requested:
            # 선제공격 보너스 가져오기
            preemptive = getattr(exploration, 'preemptive_bonus', 0.0)
            # 전투 데이터 반환: (적 수, 맵 적 엔티티, 참여자, 위치, 선제공격)
            combat_data = {
                "num_enemies": ui.combat_num_enemies,
                "enemies": ui.combat_enemies,
                "is_boss": getattr(ui, 'combat_is_boss', False),
                "enemy_level": getattr(ui, 'combat_enemy_level', None),
                "participants": getattr(ui, 'combat_participants', None),
                "position": getattr(ui, 'combat_position', None),
                "preemptive_bonus": preemptive,
                # 멀티플레이 동기화 데이터
                "synced_enemies": getattr(ui, 'combat_synced_enemies', None),
                "combined_party": getattr(ui, 'combat_combined_party', None),
                "local_party_ids": getattr(ui, 'combat_local_party_ids', None),
            }
            # 선제공격 보너스 소비 (1회성)
            if hasattr(exploration, 'preemptive_bonus'):
                exploration.preemptive_bonus = 0.0
            return ("combat", combat_data)

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

    # 루프 탈출 후 상태 체크 (break로 나온 경우)
    logger.debug(f"탐험 루프 탈출: quit={ui.quit_requested}, combat={ui.combat_requested}, floor={ui.floor_change_requested}")
    
    if ui.floor_change_requested:
        return (ui.floor_change_requested, None)
    elif ui.combat_requested:
        preemptive = getattr(exploration, 'preemptive_bonus', 0.0)
        combat_data = {
            "num_enemies": ui.combat_num_enemies,
            "enemies": ui.combat_enemies,
            "is_boss": getattr(ui, 'combat_is_boss', False),
            "enemy_level": getattr(ui, 'combat_enemy_level', None),
            "participants": getattr(ui, 'combat_participants', None),
            "position": getattr(ui, 'combat_position', None),
            "preemptive_bonus": preemptive,
            # 멀티플레이 동기화 데이터
            "synced_enemies": getattr(ui, 'combat_synced_enemies', None),
            "combined_party": getattr(ui, 'combat_combined_party', None),
            "local_party_ids": getattr(ui, 'combat_local_party_ids', None),
        }
        if hasattr(exploration, 'preemptive_bonus'):
            exploration.preemptive_bonus = 0.0
        return ("combat", combat_data)
    elif ui.main_menu_requested:
        return ("main_menu", None)
    elif ui.quit_requested:
        return ("quit", None)

    # 기본값 반환 (예외 상황 대비)
    return ("quit", None)


# ── 퀘스트 진행 헬퍼 함수 (모듈 수준) ──

def _advance_npc_quest(qm, quest_id: str, world_ui):
    """NPC 대화를 통한 퀘스트 목표 진행"""
    try:
        for quest in qm.active_quests:
            if quest.quest_id == quest_id and not quest.is_complete:
                # 미완료 목표 중 첫 번째를 진행
                for i, obj in enumerate(quest.objectives):
                    if not obj.is_complete:
                        qm.complete_rpg_objective(quest_id, i, 1)
                        if obj.is_complete:
                            world_ui.add_message(f"[퀘스트] {obj.description} (완료!)")
                        else:
                            world_ui.add_message(f"[퀘스트] {obj.description} ({obj.progress_text})")
                        break
                if quest.all_objectives_complete:
                    world_ui.add_message(f"[퀘스트 완료] {quest.name} - 퀘스트 보드에서 보상을 수령하세요!")
                break
    except Exception:
        pass


def _check_facility_quest_progress(facility_type: str, world_ui):
    """시설 이용 시 관련 퀘스트 자동 진행 (주방/대장간/연금술)"""
    try:
        from src.quest.quest_manager import get_quest_manager
        qm = get_quest_manager()
        facility_to_subtype = {
            "kitchen": "cooking",
            "blacksmith": "craft",
            "alchemy_lab": "alchemy",
        }
        target_subtype = facility_to_subtype.get(facility_type, "")
        if not target_subtype:
            return
        for quest in qm.active_quests:
            if quest.quest_subtype == target_subtype and not quest.is_complete:
                for i, obj in enumerate(quest.objectives):
                    if not obj.is_complete:
                        qm.complete_rpg_objective(quest.quest_id, i, 1)
                        if obj.is_complete:
                            world_ui.add_message(f"[퀘스트] {obj.description} (완료!)")
                        else:
                            world_ui.add_message(f"[퀘스트] {obj.description} ({obj.progress_text})")
                        break
                if quest.all_objectives_complete:
                    world_ui.add_message(f"[퀘스트 완료] {quest.name} - 퀘스트 보드에서 보상을 수령하세요!")
    except Exception:
        pass


def _check_area_quest_progress(area_type: str, world_ui):
    """지역 타일(동굴/이정표) 상호작용 시 관련 퀘스트 자동 진행"""
    try:
        from src.quest.quest_manager import get_quest_manager
        qm = get_quest_manager()
        area_to_subtypes = {
            "cave_entrance": ["explore", "rescue", "investigate"],
            "signpost": ["explore", "investigate", "puzzle"],
        }
        target_subtypes = area_to_subtypes.get(area_type, [])
        if not target_subtypes:
            return
        for quest in qm.active_quests:
            if quest.quest_subtype in target_subtypes and not quest.is_complete:
                for i, obj in enumerate(quest.objectives):
                    if not obj.is_complete:
                        qm.complete_rpg_objective(quest.quest_id, i, 1)
                        if obj.is_complete:
                            world_ui.add_message(f"[퀘스트] {obj.description} (완료!)")
                        else:
                            world_ui.add_message(f"[퀘스트] {obj.description} ({obj.progress_text})")
                        break
                if quest.all_objectives_complete:
                    world_ui.add_message(f"[퀘스트 완료] {quest.name} - 퀘스트 보드에서 보상을 수령하세요!")
    except Exception:
        pass
