"""
스토리 모드 탐험 컨트롤러
Dawn of Stellar - 별빛의 여명

스크립트 탐험: 사전설계 맵에서 이동, 상호작용 연습
기존 TutorialDungeon의 맵을 활용
"""

import time
from typing import Optional

import tcod.console
import tcod.event

from src.core.logger import get_logger
from src.audio import play_sfx
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.ui.pointer import PointerButton, PointerEvent, PointerEventKind
from src.ui.visual_tokens import rgb
from src.world.tile import TileType
from src.story_mode.inline_tutorial_overlay import InlineTutorialOverlay, NPC_NAMES

logger = get_logger("story_mode")

# 타일 표시 문자 및 색상 (TileType enum에 맞춤)
TILE_CHARS = {
    TileType.VOID: (" ", (0, 0, 0)),
    TileType.FLOOR: (".", (60, 60, 80)),
    TileType.WALL: ("#", (100, 100, 120)),
    TileType.STAIRS_DOWN: (">", (255, 215, 0)),
    TileType.STAIRS_UP: ("<", (255, 215, 0)),
    TileType.DOOR: ("+", (180, 130, 60)),
    TileType.LOCKED_DOOR: ("+", (255, 80, 80)),
    TileType.TRAP: ("^", (255, 100, 100)),
    TileType.SPIKE_TRAP: ("^", (255, 60, 60)),
    TileType.FIRE_TRAP: ("^", (255, 120, 0)),
    TileType.HEALING_SPRING: ("*", (0, 255, 0)),
    TileType.MANA_WELL: ("~", (0, 150, 255)),
    TileType.CRYSTAL: ("♦", (100, 200, 255)),
    TileType.CHEST: ("$", (255, 215, 0)),
    TileType.KEY: ("!", (255, 255, 0)),
    TileType.BOSS_ROOM: ("B", (255, 0, 0)),
    TileType.SHOP: ("$", (200, 200, 0)),
    TileType.TELEPORTER: ("O", (200, 100, 255)),
    TileType.PORTAL: ("O", (150, 50, 255)),
    TileType.LAVA: ("~", (255, 80, 0)),
    TileType.ICE_FLOOR: ("~", (150, 220, 255)),
    TileType.INGREDIENT: ("*", (100, 255, 100)),
    TileType.MAGIC_CIRCLE: ("◎", (200, 150, 255)),
    TileType.SECRET_DOOR: ("+", (80, 80, 80)),
    TileType.ALTAR: ("†", (255, 215, 100)),
    TileType.SHRINE: ("†", (200, 200, 255)),
    TileType.ANVIL: ("T", (180, 180, 180)),
}

PLAYER_CHAR = "@"
PLAYER_COLOR = (255, 255, 255)


def _screen_to_map_tile(console: tcod.console.Console, dungeon, tile: tuple[int, int]) -> tuple[int, int] | None:
    map_offset_x = (console.width - dungeon.width) // 2
    map_offset_y = (console.height - dungeon.height) // 2 - 2
    tx = tile[0] - map_offset_x
    ty = tile[1] - map_offset_y
    if 0 <= tx < dungeon.width and 0 <= ty < dungeon.height:
        return tx, ty
    return None


def _exploration_pointer_step(event: PointerEvent, console: tcod.console.Console, dungeon, px: int, py: int) -> tuple[int, int, str | None, bool]:
    map_tile = _screen_to_map_tile(console, dungeon, event.position.tile)
    if map_tile is None:
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            return 0, 0, None, True
        return 0, 0, None, False
    tx, ty = map_tile
    tile = dungeon.tiles[ty][tx]
    tooltip = f"{TILE_CHARS.get(tile.tile_type, ('?',))[0]} {tile.tile_type.name}: 목표/오브젝트 위치를 확인합니다"
    if event.kind is PointerEventKind.HOVER:
        return 0, 0, tooltip, False
    if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
        return 0, 0, None, True
    if event.kind is PointerEventKind.CLICK and event.button is PointerButton.LEFT:
        dx = max(-1, min(1, tx - px))
        dy = max(-1, min(1, ty - py))
        return dx, dy, tooltip, False
    return 0, 0, None, False


class StoryExplorationController:
    """
    스토리 모드 탐험 컨트롤러

    사전 설계된 작은 맵에서 이동/상호작용 연습
    """

    def __init__(
        self,
        console: tcod.console.Console,
        context: tcod.context.Context,
        overlay: InlineTutorialOverlay,
    ):
        self.console = console
        self.context = context
        self.overlay = overlay
        self._pointer_tooltip: str | None = None

    def run_scripted_exploration(
        self,
        chapter_id: str,
        dungeon_type: str = "movement_tutorial",
    ) -> str:
        """
        스크립트 탐험 실행

        Returns:
            "completed", "quit"
        """
        # TutorialDungeon에서 맵 생성
        from src.tutorial.tutorial_dungeon import TutorialDungeon

        markers = []
        if dungeon_type == "prologue_awakening":
            dungeon, markers = TutorialDungeon.create_prologue_awakening()
        elif dungeon_type == "combat_training_arena":
            dungeon, markers = TutorialDungeon.create_combat_training_arena()
        elif dungeon_type == "dungeon_basics":
            dungeon, markers = TutorialDungeon.create_dungeon_basics()
        elif dungeon_type == "story_dungeon":
            dungeon, markers = TutorialDungeon.create_story_dungeon()
        elif dungeon_type == "story_combat_arena":
            dungeon, markers = TutorialDungeon.create_story_combat_arena()
        elif dungeon_type == "movement_tutorial":
            dungeon = TutorialDungeon.create_movement_tutorial()
        elif dungeon_type == "combat_tutorial":
            dungeon = TutorialDungeon.create_combat_tutorial()
        elif dungeon_type == "skill_tutorial":
            dungeon = TutorialDungeon.create_skill_tutorial()
        else:
            dungeon = TutorialDungeon.create_movement_tutorial()

        # 마커 저장
        if markers:
            dungeon.story_markers = markers

        # 시작 위치
        px, py = getattr(dungeon, "start_pos", (7, 7))
        exit_pos = getattr(dungeon, "exit_pos", None)
        stairs_down = getattr(dungeon, "stairs_down", None)

        # 힌트 표시
        self.overlay.show_hint(
            "방향키로 이동하세요. 계단(>)에 도착하면 완료!",
            speaker="selena",
            position="bottom",
        )

        step_count = 0
        hint_shown_interact = False

        # 입력 큐 비우기
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        while True:
            # 렌더링
            self._render_map(dungeon, px, py)
            self.overlay.render(self.console)
            self.context.present(self.console)

            # 입력 처리
            try:
                import pygame
                pygame.event.pump()
            except Exception:
                pass

            dx, dy = 0, 0
            keyboard_processed = False

            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                pointer_event = unified_input_handler.process_pointer_event(event)
                if pointer_event is not None:
                    pdx, pdy, tooltip, cancel = _exploration_pointer_step(pointer_event, self.console, dungeon, px, py)
                    if tooltip is not None:
                        self._pointer_tooltip = tooltip
                    if cancel:
                        return "quit"
                    if pdx != 0 or pdy != 0:
                        dx, dy = pdx, pdy
                if action:
                    keyboard_processed = True

                if action == GameAction.MOVE_UP:
                    dy = -1
                elif action == GameAction.MOVE_DOWN:
                    dy = 1
                elif action == GameAction.MOVE_LEFT:
                    dx = -1
                elif action == GameAction.MOVE_RIGHT:
                    dx = 1
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    return "quit"

                if isinstance(event, tcod.event.Quit):
                    return "quit"

            if not keyboard_processed:
                gamepad_action = unified_input_handler.get_action()
                if gamepad_action:
                    if gamepad_action == GameAction.MOVE_UP:
                        dy = -1
                    elif gamepad_action == GameAction.MOVE_DOWN:
                        dy = 1
                    elif gamepad_action == GameAction.MOVE_LEFT:
                        dx = -1
                    elif gamepad_action == GameAction.MOVE_RIGHT:
                        dx = 1
                    elif gamepad_action == GameAction.CANCEL:
                        return "quit"

            # 이동 처리
            if dx != 0 or dy != 0:
                nx, ny = px + dx, py + dy
                if (
                    0 <= nx < dungeon.width
                    and 0 <= ny < dungeon.height
                    and dungeon.tiles[ny][nx].walkable
                ):
                    px, py = nx, ny
                    step_count += 1
                    play_sfx("world", "footstep")

                    # 계단 도착 체크
                    tile = dungeon.tiles[py][px]
                    if tile.tile_type in (TileType.STAIRS_DOWN, TileType.STAIRS_UP):
                        self.overlay.show_hint(
                            "계단에 도착했습니다! 탐험 완료!",
                            speaker="selena",
                            position="center",
                        )
                        self._render_map(dungeon, px, py)
                        self.overlay.render(self.console)
                        self.context.present(self.console)
                        play_sfx("world", "stairs")
                        time.sleep(1.5)
                        return "completed"

                    # 단계별 힌트
                    if step_count == 3 and not hint_shown_interact:
                        self.overlay.show_hint(
                            "잘 하고 있어요! 계속 이동해서 계단(>)을 찾으세요.",
                            speaker="selena",
                        )
                        hint_shown_interact = True

                else:
                    # 벽 충돌
                    play_sfx("ui", "cursor_error")

            time.sleep(0.016)

    def _render_map(self, dungeon, px: int, py: int):
        """맵 렌더링"""
        self.console.clear()
        w, h = self.console.width, self.console.height

        # 배경
        for y in range(h):
            for x in range(w):
                self.console.rgb[y, x] = (ord(" "), (5, 5, 10), (5, 5, 10))

        # 맵 오프셋 (중앙 정렬)
        map_offset_x = (w - dungeon.width) // 2
        map_offset_y = (h - dungeon.height) // 2 - 2

        # 타일 렌더링
        for ty in range(dungeon.height):
            for tx in range(dungeon.width):
                tile = dungeon.tiles[ty][tx]
                char, color = TILE_CHARS.get(
                    tile.tile_type, ("?", (100, 100, 100))
                )
                sx = map_offset_x + tx
                sy = map_offset_y + ty
                if 0 <= sx < w and 0 <= sy < h:
                    self.console.print(sx, sy, char, fg=color)

        # 마커 렌더링 (NPC, 적, 힐 등)
        for marker in getattr(dungeon, "story_markers", []):
            mx = map_offset_x + marker.x
            my = map_offset_y + marker.y
            if 0 <= mx < w and 0 <= my < h:
                if marker.marker_type == "npc":
                    self.console.print(mx, my, "N", fg=(0, 200, 255))
                elif marker.marker_type in ("enemy", "enemy_spawn"):
                    self.console.print(mx, my, "E", fg=(255, 100, 100))
                elif marker.marker_type == "heal":
                    self.console.print(mx, my, "*", fg=(0, 255, 0))
                elif marker.marker_type == "chest":
                    self.console.print(mx, my, "$", fg=(255, 215, 0))
                elif marker.marker_type == "trap":
                    self.console.print(mx, my, "^", fg=(255, 100, 100))

        # 플레이어
        sx = map_offset_x + px
        sy = map_offset_y + py
        if 0 <= sx < w and 0 <= sy < h:
            self.console.print(sx, sy, PLAYER_CHAR, fg=PLAYER_COLOR)

        # 상단 정보
        self.console.print(2, 1, "탐험 모드", fg=(255, 215, 0))
        self.console.print(
            2, 2, "방향키: 이동  X: 돌아가기", fg=Colors.GRAY
        )
        if self._pointer_tooltip:
            self.console.print(2, 3, self._pointer_tooltip[:70], fg=rgb("accent.amber"), bg=rgb("state.tooltip"))

        # 타일 범례
        legend_y = h - 8
        self.console.print(2, legend_y, "범례:", fg=Colors.GRAY)
        self.console.print(2, legend_y + 1, "@ 플레이어", fg=PLAYER_COLOR)
        self.console.print(2, legend_y + 2, "> 계단 (출구)", fg=(255, 215, 0))
        self.console.print(2, legend_y + 3, ". 바닥", fg=(60, 60, 80))
        self.console.print(2, legend_y + 4, "# 벽", fg=(100, 100, 120))
