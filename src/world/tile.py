"""
타일 시스템

던전 맵의 타일 타입 및 속성
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, Any


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
    DROPPED_ITEM = "dropped_item"  # 플레이어가 드롭한 아이템
    GOLD = "gold"  # 떨어진 골드
    INGREDIENT = "ingredient"  # 채집 가능한 식재료
    SWITCH = "switch"  # 스위치
    PRESSURE_PLATE = "pressure_plate"  # 압력판
    LEVER = "lever"  # 레버
    NPC = "npc"  # NPC
    ALTAR = "altar"  # 제단 (버프/회복)
    SHRINE = "shrine"  # 신전 (회복/보상)
    PORTAL = "portal"  # 포털 (텔레포트)
    SPIKE_TRAP = "spike_trap"  # 가시 함정
    POISON_GAS = "poison_gas"  # 독가스
    ICE_FLOOR = "ice_floor"  # 얼음 바닥 (미끄러움)
    FIRE_TRAP = "fire_trap"  # 화염 함정
    SECRET_DOOR = "secret_door"  # 비밀 문
    BUTTON = "button"  # 버튼
    PEDESTAL = "pedestal"  # 받침대 (아이템 올려놓기)
    CRYSTAL = "crystal"  # 크리스탈 (MP 회복)
    MANA_WELL = "mana_well"  # 마나 샘
    TREASURE_MAP = "treasure_map"  # 보물 지도
    RIDDLE_STONE = "riddle_stone"  # 수수께끼 돌
    MAGIC_CIRCLE = "magic_circle"  # 마법진
    SACRIFICE_ALTAR = "sacrifice_altar"  # 희생 제단


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
    ingredient_id: Optional[str] = None  # 식재료 ID
    harvested: bool = False  # 수확 여부
    dropped_item: Optional[Any] = None  # 드롭된 아이템 객체
    gold_amount: int = 0  # 드롭된 골드 양
    dropped_by_player_id: Optional[str] = None  # 드롭한 플레이어 ID (봇이 자신이 드롭한 아이템을 줍지 않도록)
    puzzle_type: Optional[str] = None  # 퍼즐 타입
    puzzle_solved: bool = False  # 퍼즐 해결 여부
    switch_active: bool = False  # 스위치 활성화 여부
    switch_target: Optional[str] = None  # 스위치가 제어하는 대상
    npc_id: Optional[str] = None  # NPC ID
    npc_type: Optional[str] = None  # NPC 타입 (helpful/harmful/neutral/complex)
    npc_subtype: Optional[str] = None  # NPC 서브타입 (스토리별 분류)
    npc_interacted: bool = False  # NPC와 상호작용했는지 여부

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
            self.char = "D"
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
            self.char = "C"
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
            self.char = "T"
            self.fg_color = (150, 100, 255)

        elif self.tile_type == TileType.LAVA:
            self.walkable = True
            self.transparent = True
            self.char = "L"
            self.fg_color = (255, 69, 0)
            self.trap_damage = 20

        elif self.tile_type == TileType.HEALING_SPRING:
            self.walkable = True
            self.transparent = True
            self.char = "H"
            self.fg_color = (100, 255, 255)

        elif self.tile_type == TileType.BOSS_ROOM:
            self.walkable = True
            self.transparent = True
            self.char = "B"
            self.fg_color = (255, 50, 50)

        elif self.tile_type == TileType.KEY:
            self.walkable = True
            self.transparent = True
            self.char = "K"
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

        elif self.tile_type == TileType.DROPPED_ITEM:
            self.walkable = True
            self.transparent = True
            self.char = "%"
            self.fg_color = (255, 200, 100)

        elif self.tile_type == TileType.GOLD:
            self.walkable = True
            self.transparent = True
            self.char = "$"
            self.fg_color = (255, 215, 0)

        elif self.tile_type == TileType.INGREDIENT:
            self.walkable = True
            self.transparent = True
            self.char = "*" if not self.harvested else "."
            self.fg_color = (100, 255, 100) if not self.harvested else (100, 100, 100)

        elif self.tile_type == TileType.SWITCH:
            self.walkable = True
            self.transparent = True
            self.char = "S" if self.switch_active else "s"
            self.fg_color = (100, 255, 100) if self.switch_active else (150, 150, 150)

        elif self.tile_type == TileType.PRESSURE_PLATE:
            self.walkable = True
            self.transparent = True
            self.char = "P" if self.switch_active else "p"
            self.fg_color = (100, 255, 100) if self.switch_active else (200, 200, 200)

        elif self.tile_type == TileType.LEVER:
            self.walkable = True
            self.transparent = True
            self.char = "L" if self.switch_active else "l"
            self.fg_color = (255, 200, 100) if self.switch_active else (150, 150, 150)

        elif self.tile_type == TileType.NPC:
            self.walkable = True
            self.transparent = True
            self.char = "@"
            # NPC는 흰색 고정
            self.fg_color = (255, 255, 255)

        elif self.tile_type == TileType.ALTAR:
            self.walkable = True
            self.transparent = True
            self.char = "A"
            self.fg_color = (200, 150, 255)

        elif self.tile_type == TileType.SHRINE:
            self.walkable = True
            self.transparent = True
            self.char = "S"
            self.fg_color = (255, 255, 200)

        elif self.tile_type == TileType.PORTAL:
            self.walkable = True
            self.transparent = True
            self.char = "O"
            self.fg_color = (150, 150, 255)

        elif self.tile_type == TileType.SPIKE_TRAP:
            self.walkable = True
            self.transparent = True
            self.char = "^"
            self.fg_color = (200, 50, 50)
            self.trap_damage = 15

        elif self.tile_type == TileType.POISON_GAS:
            self.walkable = True
            self.transparent = True
            self.char = "G"
            self.fg_color = (100, 200, 100)
            self.trap_damage = 8

        elif self.tile_type == TileType.ICE_FLOOR:
            self.walkable = True
            self.transparent = True
            self.char = "I"
            self.fg_color = (200, 200, 255)

        elif self.tile_type == TileType.FIRE_TRAP:
            self.walkable = True
            self.transparent = True
            self.char = "F"
            self.fg_color = (255, 100, 0)
            self.trap_damage = 25

        elif self.tile_type == TileType.SECRET_DOOR:
            self.walkable = False
            self.transparent = False
            self.char = "#"
            self.fg_color = (150, 150, 150)

        elif self.tile_type == TileType.BUTTON:
            self.walkable = True
            self.transparent = True
            self.char = "B" if self.switch_active else "b"
            self.fg_color = (255, 200, 100) if self.switch_active else (150, 150, 150)

        elif self.tile_type == TileType.PEDESTAL:
            self.walkable = True
            self.transparent = True
            self.char = "P"
            self.fg_color = (200, 200, 200)

        elif self.tile_type == TileType.CRYSTAL:
            self.walkable = True
            self.transparent = True
            self.char = "C"
            self.fg_color = (150, 200, 255)

        elif self.tile_type == TileType.MANA_WELL:
            self.walkable = True
            self.transparent = True
            self.char = "M"
            self.fg_color = (100, 150, 255)

        elif self.tile_type == TileType.TREASURE_MAP:
            self.walkable = True
            self.transparent = True
            self.char = "M"
            self.fg_color = (255, 200, 100)

        elif self.tile_type == TileType.RIDDLE_STONE:
            self.walkable = True
            self.transparent = True
            self.char = "R"
            self.fg_color = (200, 200, 150)

        elif self.tile_type == TileType.MAGIC_CIRCLE:
            self.walkable = True
            self.transparent = True
            self.char = "C"
            self.fg_color = (255, 150, 255)

        elif self.tile_type == TileType.SACRIFICE_ALTAR:
            self.walkable = True
            self.transparent = True
            self.char = "A"
            self.fg_color = (200, 50, 50)

    def unlock(self):
        """문 잠금 해제"""
        if self.locked:
            self.locked = False
            self.walkable = True
            if self.tile_type == TileType.LOCKED_DOOR:
                self.tile_type = TileType.DOOR
                self.char = "+"
