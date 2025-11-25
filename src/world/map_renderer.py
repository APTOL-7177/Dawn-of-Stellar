"""
맵 렌더러

던전 맵을 화면에 표시
"""

import tcod

from src.world.dungeon_generator import DungeonMap
from src.world.tile import TileType


class MapRenderer:
    """맵 렌더러"""

    def __init__(self, map_x: int = 0, map_y: int = 5):
        """
        Args:
            map_x: 맵 표시 시작 X 좌표
            map_y: 맵 표시 시작 Y 좌표
        """
        self.map_x = map_x
        self.map_y = map_y

    def render(
        self,
        console: tcod.console.Console,
        dungeon: DungeonMap,
        camera_x: int = 0,
        camera_y: int = 0,
        view_width: int = 80,
        view_height: int = 45
    ):
        """
        맵 렌더링

        Args:
            console: TCOD 콘솔
            dungeon: 던전 맵
            camera_x: 카메라 X 위치 (맵 좌표)
            camera_y: 카메라 Y 위치 (맵 좌표)
            view_width: 표시 너비
            view_height: 표시 높이
        """
        # 표시 범위 계산
        start_x = max(0, camera_x)
        start_y = max(0, camera_y)
        end_x = min(dungeon.width, camera_x + view_width)
        end_y = min(dungeon.height, camera_y + view_height)

        # 타일 렌더링
        for map_y in range(start_y, end_y):
            for map_x in range(start_x, end_x):
                tile = dungeon.get_tile(map_x, map_y)

                # 화면 좌표 계산
                screen_x = self.map_x + (map_x - camera_x)
                screen_y = self.map_y + (map_y - camera_y)

                # 범위 체크
                if not (0 <= screen_x < console.width and 0 <= screen_y < console.height):
                    continue

                # 탐험되지 않은 타일은 표시 안 함
                if not tile.explored:
                    continue

                # 마을 건물 표시 (우선순위 높음)
                # building_symbol이 있으면 사용, 없으면 타일의 char와 fg_color를 사용 (이미 건물 심볼로 설정됨)
                if hasattr(tile, 'building_symbol') and tile.building_symbol:
                    char = tile.building_symbol
                    fg = getattr(tile, 'building_color', tile.fg_color)
                    bg = (0, 0, 0)
                # 타일의 char가 건물 심볼인 경우 (K, B, A, S, Q, $, I, G, F)
                elif tile.char in ['K', 'B', 'A', 'S', 'Q', '$', 'I', 'G', 'F'] and hasattr(dungeon, 'is_town') and dungeon.is_town:
                    char = tile.char
                    fg = tile.fg_color
                    bg = (0, 0, 0)
                # 마을 장식 제거 (더 이상 사용하지 않음)
                # elif hasattr(tile, 'decoration_char') and tile.decoration_char: 제거됨
                # 함정은 작동하기 전까지 숨김 (일반 바닥처럼 표시)
                elif tile.tile_type in [TileType.TRAP, TileType.SPIKE_TRAP, TileType.FIRE_TRAP, TileType.POISON_GAS]:
                    # 함정은 일반 바닥처럼 표시
                    char = "."
                    fg = (100, 100, 100)
                    bg = (0, 0, 0)
                # 퍼즐은 해결되면 일반 바닥처럼 표시
                elif tile.tile_type == TileType.PUZZLE and getattr(tile, 'puzzle_solved', False):
                    char = "."
                    fg = (100, 100, 100)
                    bg = (0, 0, 0)
                else:
                    # 타일 표시
                    char = tile.char
                    fg = tile.fg_color
                    bg = tile.bg_color

                # 탐험됐지만 현재 보이지 않는 경우 어둡게
                if not tile.visible:
                    fg = tuple(c // 4 for c in fg)
                    bg = tuple(c // 4 for c in bg)

                # 환경 효과 색상 오버레이 적용 (마을이 아닌 경우만)
                if hasattr(dungeon, 'environment_effect_manager') and not (hasattr(dungeon, 'is_town') and dungeon.is_town):
                    effects = dungeon.environment_effect_manager.get_effects_at_tile(map_x, map_y)
                    if effects:
                        # 가장 강한 효과의 색상 사용 (첫 번째 효과)
                        effect = effects[0]
                        overlay_color = effect.color_overlay
                        
                        # 색상 블렌딩 (50% 오버레이)
                        fg = tuple(
                            int(fg[i] * 0.5 + overlay_color[i] * 0.5)
                            for i in range(3)
                        )
                        # 배경색도 약간 블렌딩
                        bg = tuple(
                            int(bg[i] * 0.7 + overlay_color[i] * 0.3)
                            for i in range(3)
                        )

                console.print(screen_x, screen_y, char, fg=fg, bg=bg)

    def render_minimap(
        self,
        console: tcod.console.Console,
        dungeon: DungeonMap,
        minimap_x: int,
        minimap_y: int,
        minimap_width: int = 20,
        minimap_height: int = 15,
        player_pos: tuple = None,
        enemies: list = None
    ):
        """
        미니맵 렌더링

        Args:
            console: TCOD 콘솔
            dungeon: 던전 맵
            minimap_x: 미니맵 X 위치
            minimap_y: 미니맵 Y 위치
            minimap_width: 미니맵 너비
            minimap_height: 미니맵 높이
            player_pos: 플레이어 위치 (x, y) 튜플
            enemies: 적 리스트
        """
        # 스케일 계산
        scale_x = dungeon.width / minimap_width
        scale_y = dungeon.height / minimap_height

        # 테두리
        console.draw_frame(
            minimap_x - 1,
            minimap_y - 1,
            minimap_width + 2,
            minimap_height + 2,
            "[미니맵]",
            fg=(200, 200, 200)
        )

        # 범례 표시
        legend_y = minimap_y + minimap_height + 1
        console.print(minimap_x, legend_y, "@=나 E=적 S=계단", fg=(180, 180, 180))

        # 적 위치를 미니맵 좌표로 변환 (보스와 일반 적 구분)
        enemy_minimap_positions = set()
        boss_minimap_positions = set()
        if enemies:
            for enemy in enemies:
                enemy_mx = int(enemy.x / scale_x)
                enemy_my = int(enemy.y / scale_y)
                if 0 <= enemy_mx < minimap_width and 0 <= enemy_my < minimap_height:
                    if getattr(enemy, 'is_boss', False):
                        boss_minimap_positions.add((enemy_mx, enemy_my))
                    else:
                        enemy_minimap_positions.add((enemy_mx, enemy_my))

        # 플레이어 위치를 미니맵 좌표로 변환
        player_mx, player_my = None, None
        if player_pos:
            player_mx = int(player_pos[0] / scale_x)
            player_my = int(player_pos[1] / scale_y)

        # 미니맵 렌더링
        for my in range(minimap_height):
            for mx in range(minimap_width):
                # 맵 좌표로 변환
                map_x = int(mx * scale_x)
                map_y = int(my * scale_y)

                tile = dungeon.get_tile(map_x, map_y)

                # 간단한 표현
                char = " "
                fg = (50, 50, 50)

                # 플레이어 위치 (최우선)
                if player_mx == mx and player_my == my:
                    char = "@"
                    fg = (0, 255, 0)  # 초록색
                # 계단 표시 (플레이어보다 낮지만 중요)
                elif tile.tile_type == TileType.STAIRS_DOWN:
                    char = ">"
                    fg = (255, 255, 0)  # 노란색 (더 눈에 띄게)
                elif tile.tile_type == TileType.STAIRS_UP:
                    char = "<"
                    fg = (255, 255, 0)  # 노란색 (더 눈에 띄게)
                # 보스 위치 표시 제거 (요청에 따라)
                # elif (mx, my) in boss_minimap_positions:
                #     char = "B"
                #     fg = (255, 0, 0)  # 선명한 빨간색
                # 일반 적 위치
                elif (mx, my) in enemy_minimap_positions:
                    char = "E"
                    fg = (255, 150, 50)  # 주황색
                # 타일 타입
                elif tile.tile_type == TileType.FLOOR:
                    char = "."
                    fg = (100, 100, 100)
                elif tile.tile_type == TileType.WALL:
                    char = "#"
                    fg = (80, 80, 80)
                # BOSS_ROOM 타일 표시 제거 (요청에 따라)
                # elif tile.tile_type == TileType.BOSS_ROOM:
                #     char = "B"
                #     fg = (255, 50, 50)
                elif tile.tile_type == TileType.CHEST:
                    char = "C"
                    fg = (255, 215, 0)  # 금색

                console.print(minimap_x + mx, minimap_y + my, char, fg=fg)
