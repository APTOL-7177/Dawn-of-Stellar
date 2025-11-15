"""
타일 시스템

던전 맵의 타일 타입 및 속성
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple


class TileType(Enum):
    """타일 타입"""
    VOID = "void"  # 빈 공간
    FLOOR = "floor"  # 바닥 (이동 가능)
    WALL = "wall"  # 벽
    DOOR = "door"  # 문
    LOCKED_DOOR = "locked_door"  # 잠긴 문
    STAIRS_UP = "stairs_up"  # 올라가는 계단
    STAIRS_DOWN = "stairs_down"  # 내려가는 계단

    # 기믹 타일
    CHEST = "chest"  # 보물상자
    TRAP = "trap"  # 함정
    TELEPORTER = "teleporter"  # 텔레포터
    LAVA = "lava"  # 용암 (데미지)
    HEALING_SPRING = "healing_spring"  # 치유의 샘
    BOSS_ROOM = "boss_room"  # 보스룸 입구
    KEY = "key"  # 열쇠
    PUZZLE = "puzzle"  # 퍼즐
    SHOP = "shop"  # 상점
    ITEM = "item"  # 떨어진 아이템/장비


@dataclass
class Tile:
    """타일"""
    tile_type: TileType
    x: int
    y: int

    # 속성
    walkable: bool = True  # 이동 가능
    transparent: bool = True  # 시야 통과
    explored: bool = False  # 탐험됨
    visible: bool = False  # 현재 보임

    # 기믹 관련
    locked: bool = False  # 잠김 (문)
    key_id: Optional[str] = None  # 필요한 열쇠 ID
    trap_damage: int = 0  # 함정 데미지
    teleport_target: Optional[Tuple[int, int]] = None  # 텔레포터 목적지
    loot_id: Optional[str] = None  # 전리품 ID (상자)

    # 시각적
    char: str = "."  # 표시 문자
    fg_color: Tuple[int, int, int] = (255, 255, 255)  # 전경색
    bg_color: Tuple[int, int, int] = (0, 0, 0)  # 배경색

    def __post_init__(self):
        """타일 타입에 따른 기본 속성 설정"""
        if self.tile_type == TileType.VOID:
            self.walkable = False
            self.transparent = False
            self.char = " "
            self.fg_color = (0, 0, 0)

        elif self.tile_type == TileType.FLOOR:
            self.walkable = True
            self.transparent = True
            self.char = "."
            self.fg_color = (100, 100, 100)

        elif self.tile_type == TileType.WALL:
            self.walkable = False
            self.transparent = False
            self.char = "#"
            self.fg_color = (130, 110, 50)

        elif self.tile_type == TileType.DOOR:
            self.walkable = True
            self.transparent = False
            self.char = "+"
            self.fg_color = (139, 69, 19)

        elif self.tile_type == TileType.LOCKED_DOOR:
            self.walkable = False
            self.transparent = False
            self.locked = True
            self.char = "⊞"
            self.fg_color = (200, 150, 50)

        elif self.tile_type == TileType.STAIRS_UP:
            self.walkable = True
            self.transparent = True
            self.char = "<"
            self.fg_color = (255, 255, 255)

        elif self.tile_type == TileType.STAIRS_DOWN:
            self.walkable = True
            self.transparent = True
            self.char = ">"
            self.fg_color = (255, 255, 255)

        elif self.tile_type == TileType.CHEST:
            self.walkable = True
            self.transparent = True
            self.char = "☐"
            self.fg_color = (255, 215, 0)

        elif self.tile_type == TileType.TRAP:
            self.walkable = True
            self.transparent = True
            self.char = "^"
            self.fg_color = (255, 100, 100)
            self.trap_damage = 10

        elif self.tile_type == TileType.TELEPORTER:
            self.walkable = True
            self.transparent = True
            self.char = "⊗"
            self.fg_color = (150, 100, 255)

        elif self.tile_type == TileType.LAVA:
            self.walkable = True
            self.transparent = True
            self.char = "≈"
            self.fg_color = (255, 69, 0)
            self.trap_damage = 20

        elif self.tile_type == TileType.HEALING_SPRING:
            self.walkable = True
            self.transparent = True
            self.char = "♨"
            self.fg_color = (100, 255, 255)

        elif self.tile_type == TileType.BOSS_ROOM:
            self.walkable = True
            self.transparent = True
            self.char = "⚠"
            self.fg_color = (255, 50, 50)

        elif self.tile_type == TileType.KEY:
            self.walkable = True
            self.transparent = True
            self.char = "♀"
            self.fg_color = (255, 215, 0)

        elif self.tile_type == TileType.PUZZLE:
            self.walkable = True
            self.transparent = True
            self.char = "?"
            self.fg_color = (200, 200, 255)

        elif self.tile_type == TileType.SHOP:
            self.walkable = True
            self.transparent = True
            self.char = "$"
            self.fg_color = (255, 215, 0)

        elif self.tile_type == TileType.ITEM:
            self.walkable = True
            self.transparent = True
            self.char = "i"
            self.fg_color = (255, 255, 100)

    def unlock(self):
        """문 잠금 해제"""
        if self.locked:
            self.locked = False
            self.walkable = True
            if self.tile_type == TileType.LOCKED_DOOR:
                self.tile_type = TileType.DOOR
                self.char = "+"
