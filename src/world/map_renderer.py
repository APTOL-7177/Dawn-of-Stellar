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

                # 타일 표시
                char = tile.char
                fg = tile.fg_color
                bg = tile.bg_color

                # 탐험됐지만 현재 보이지 않는 경우 어둡게
                if not tile.visible:
                    fg = tuple(c // 4 for c in fg)
                    bg = tuple(c // 4 for c in bg)

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

        # 적 위치를 미니맵 좌표로 변환 (미리 계산)
        enemy_minimap_positions = set()
        if enemies:
            for enemy in enemies:
                enemy_mx = int(enemy.x / scale_x)
                enemy_my = int(enemy.y / scale_y)
                if 0 <= enemy_mx < minimap_width and 0 <= enemy_my < minimap_height:
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
                # 적 위치
                elif (mx, my) in enemy_minimap_positions:
                    char = "E"
                    fg = (255, 50, 50)  # 빨간색
                # 타일 타입
                elif tile.tile_type == TileType.FLOOR:
                    char = "."
                    fg = (100, 100, 100)
                elif tile.tile_type == TileType.WALL:
                    char = "#"
                    fg = (80, 80, 80)
                elif tile.tile_type in [TileType.STAIRS_UP, TileType.STAIRS_DOWN]:
                    char = "S"
                    fg = (255, 255, 0)  # 노란색 (더 눈에 띄게)
                elif tile.tile_type == TileType.BOSS_ROOM:
                    char = "B"
                    fg = (255, 50, 50)
                elif tile.tile_type == TileType.CHEST:
                    char = "C"
                    fg = (255, 215, 0)  # 금색

                console.print(minimap_x + mx, minimap_y + my, char, fg=fg)
