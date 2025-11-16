"""
튜토리얼 전용 던전 - 작고 간단한 맵
"""

from typing import List, Tuple
from src.world.dungeon_generator import DungeonMap
from src.world.tile import Tile, TileType


class TutorialDungeon:
    """튜토리얼 전용 작은 던전"""

    @staticmethod
    def create_movement_tutorial() -> DungeonMap:
        """이동 튜토리얼용 던전 (작은 방)"""
        width, height = 20, 15
        dungeon = DungeonMap(width, height)

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 작은 방 만들기 (중앙)
        room_x1, room_y1 = 5, 5
        room_x2, room_y2 = 15, 10

        for y in range(room_y1, room_y2):
            for x in range(room_x1, room_x2):
                dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 시작 위치 저장
        start_x, start_y = 7, 7

        # 목표 지점 (출구)
        exit_x, exit_y = 13, 7
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        # 시작/출구 위치를 속성으로 저장
        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)

        return dungeon

    @staticmethod
    def create_combat_tutorial() -> DungeonMap:
        """전투 튜토리얼용 던전 (적 배치)"""
        width, height = 25, 18
        dungeon = DungeonMap(width, height)

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 전투 방 (더 넓게)
        room_x1, room_y1 = 5, 5
        room_x2, room_y2 = 20, 13

        for y in range(room_y1, room_y2):
            for x in range(room_x1, room_x2):
                dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 시작 위치
        start_x, start_y = 7, 9

        # 출구 (전투 후 사용)
        exit_x, exit_y = 18, 13
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)

        return dungeon

    @staticmethod
    def create_skill_tutorial() -> DungeonMap:
        """스킬 튜토리얼용 던전"""
        width, height = 30, 20
        dungeon = DungeonMap(width, height)

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 큰 전투 방
        room_x1, room_y1 = 5, 5
        room_x2, room_y2 = 25, 15

        for y in range(room_y1, room_y2):
            for x in range(room_x1, room_x2):
                dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 시작 위치
        start_x, start_y = 10, 10

        # 보물 상자 (스킬 연습용)
        dungeon.tiles[10][20] = Tile(TileType.CHEST, 20, 10)

        # 출구
        exit_x, exit_y = 22, 14
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)

        return dungeon
