"""
타일 시스템

던전 맵의 타일 타입 및 속성
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any


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
    ANVIL = "anvil"  # 모루 (수리)

    # ── RPG 오픈월드 자연 지형 ──
    GRASS = "grass"              # 초원/풀밭
    TALL_GRASS = "tall_grass"    # 키 큰 풀 (랜덤 인카운터)
    SAND = "sand"                # 모래/사막
    WATER = "water"              # 물 (이동 불가)
    SHALLOW_WATER = "shallow_water"  # 얕은 물 (이동 가능, 감속)
    MOUNTAIN = "mountain"        # 산/절벽 (이동 불가)
    SNOW = "snow"                # 눈 지형
    DEEP_FOREST = "deep_forest"  # 울창한 숲
    SWAMP = "swamp"              # 늪지
    PATH = "path"                # 길/도로
    BRIDGE = "bridge"            # 다리
    TOWN = "town"                # 마을/정착지
    CAVE_ENTRANCE = "cave_entrance"  # 동굴 입구 (서브 던전)
    NPC = "npc"                  # NPC 위치
    SIGNPOST = "signpost"        # 이정표
    CAMPFIRE = "campfire"        # 모닥불 (세이브/회복 포인트)
    REGION_GATE = "region_gate"  # 지역 경계 표지

    # ── RPG 마을 건물 ──
    KITCHEN = "kitchen"              # 주방 (요리)
    BLACKSMITH = "blacksmith"        # 대장간 (장비 강화)
    ALCHEMY_LAB = "alchemy_lab"      # 연금술 실험실 (포션/폭탄)
    STORAGE_BUILDING = "storage_building"  # 창고 (아이템 보관)
    QUEST_BOARD = "quest_board"      # 퀘스트 게시판
    INN = "inn"                      # 여관 (휴식/회복)
    GUILD_HALL = "guild_hall"        # 모험가 길드
    FOUNTAIN = "fountain"            # 분수대 (HP/MP 회복)

    # ── RPG 오픈월드 장식 지형 ──
    FLOWER = "flower"                # 꽃 (장식)
    ROCK = "rock"                    # 바위/자갈 (장식)
    DEAD_TREE = "dead_tree"          # 마른 나무 (장식)
    MUSHROOM = "mushroom"            # 버섯 (장식)
    CACTUS = "cactus"                # 선인장 (사막 장식)
    RUINS = "ruins"                  # 폐허 (전쟁터 장식)
    STAR_MOSS = "star_moss"          # 별이끼 (별빛왕좌 장식)
    SCORCHED_EARTH = "scorched_earth"  # 그을린 땅 (전쟁터 주 지형)
    CRYSTAL_GRASS = "crystal_grass"  # 수정 풀밭 (별빛왕좌 주 지형)

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
    used: bool = False  # 1회성 기믹 사용 여부 (모루 등)

    # NPC 관련
    npc_id: Optional[str] = None  # 마을 NPC 고유 ID (town_npcs.yaml 참조)

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

        # BOSS_ROOM 타일 표시 제거 (요청에 따라)
        # elif self.tile_type == TileType.BOSS_ROOM:
        #     self.walkable = True
        #     self.transparent = True
        #     self.char = "B"
        #     self.fg_color = (255, 50, 50)

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

        elif self.tile_type == TileType.ANVIL:
            self.walkable = True
            self.transparent = True
            self.char = "T"  # 망치 모양이나 유사한 것
            self.fg_color = (100, 100, 120)  # 강철색

        # ── RPG 오픈월드 자연 지형 ──
        elif self.tile_type == TileType.GRASS:
            self.walkable = True
            self.transparent = True
            self.char = "."
            self.fg_color = (50, 160, 50)

        elif self.tile_type == TileType.TALL_GRASS:
            self.walkable = True
            self.transparent = True
            self.char = ","
            self.fg_color = (30, 130, 30)

        elif self.tile_type == TileType.SAND:
            self.walkable = True
            self.transparent = True
            self.char = "~"
            self.fg_color = (210, 190, 120)

        elif self.tile_type == TileType.WATER:
            self.walkable = False
            self.transparent = True
            self.char = "≈"
            self.fg_color = (30, 80, 200)

        elif self.tile_type == TileType.SHALLOW_WATER:
            self.walkable = True
            self.transparent = True
            self.char = "~"
            self.fg_color = (80, 140, 220)

        elif self.tile_type == TileType.MOUNTAIN:
            self.walkable = False
            self.transparent = False
            self.char = "▲"
            self.fg_color = (120, 100, 80)

        elif self.tile_type == TileType.SNOW:
            self.walkable = True
            self.transparent = True
            self.char = "."
            self.fg_color = (220, 230, 255)

        elif self.tile_type == TileType.DEEP_FOREST:
            self.walkable = True
            self.transparent = False
            self.char = "♣"
            self.fg_color = (20, 100, 20)

        elif self.tile_type == TileType.SWAMP:
            self.walkable = True
            self.transparent = True
            self.char = "~"
            self.fg_color = (80, 110, 50)

        elif self.tile_type == TileType.PATH:
            self.walkable = True
            self.transparent = True
            self.char = "·"
            self.fg_color = (180, 150, 100)

        elif self.tile_type == TileType.BRIDGE:
            self.walkable = True
            self.transparent = True
            self.char = "="
            self.fg_color = (160, 120, 60)

        elif self.tile_type == TileType.TOWN:
            self.walkable = True
            self.transparent = True
            self.char = "■"
            self.fg_color = (200, 180, 100)

        elif self.tile_type == TileType.CAVE_ENTRANCE:
            self.walkable = True
            self.transparent = True
            self.char = "O"
            self.fg_color = (100, 80, 60)

        elif self.tile_type == TileType.NPC:
            self.walkable = True
            self.transparent = True
            self.char = "@"
            self.fg_color = (255, 200, 50)

        elif self.tile_type == TileType.SIGNPOST:
            self.walkable = True
            self.transparent = True
            self.char = "!"
            self.fg_color = (180, 140, 80)

        elif self.tile_type == TileType.CAMPFIRE:
            self.walkable = True
            self.transparent = True
            self.char = "*"
            self.fg_color = (255, 150, 30)

        elif self.tile_type == TileType.REGION_GATE:
            self.walkable = True
            self.transparent = True
            self.char = "◆"
            self.fg_color = (200, 200, 255)

        # ── RPG 마을 건물 ──
        elif self.tile_type == TileType.KITCHEN:
            self.walkable = True
            self.transparent = True
            self.char = "K"
            self.fg_color = (255, 200, 100)

        elif self.tile_type == TileType.BLACKSMITH:
            self.walkable = True
            self.transparent = True
            self.char = "B"
            self.fg_color = (180, 100, 50)

        elif self.tile_type == TileType.ALCHEMY_LAB:
            self.walkable = True
            self.transparent = True
            self.char = "A"
            self.fg_color = (150, 100, 255)

        elif self.tile_type == TileType.STORAGE_BUILDING:
            self.walkable = True
            self.transparent = True
            self.char = "S"
            self.fg_color = (139, 69, 19)

        elif self.tile_type == TileType.QUEST_BOARD:
            self.walkable = True
            self.transparent = True
            self.char = "Q"
            self.fg_color = (255, 215, 0)

        elif self.tile_type == TileType.INN:
            self.walkable = True
            self.transparent = True
            self.char = "I"
            self.fg_color = (200, 150, 200)

        elif self.tile_type == TileType.GUILD_HALL:
            self.walkable = True
            self.transparent = True
            self.char = "G"
            self.fg_color = (200, 50, 50)

        elif self.tile_type == TileType.FOUNTAIN:
            self.walkable = True
            self.transparent = True
            self.char = "F"
            self.fg_color = (100, 200, 255)

        # ── RPG 오픈월드 장식 지형 ──
        elif self.tile_type == TileType.FLOWER:
            self.walkable = True
            self.transparent = True
            self.char = '"'
            self.fg_color = (255, 200, 100)

        elif self.tile_type == TileType.ROCK:
            self.walkable = True
            self.transparent = True
            self.char = "o"
            self.fg_color = (140, 130, 110)

        elif self.tile_type == TileType.DEAD_TREE:
            self.walkable = True
            self.transparent = True
            self.char = "+"
            self.fg_color = (100, 70, 40)

        elif self.tile_type == TileType.MUSHROOM:
            self.walkable = True
            self.transparent = True
            self.char = ","
            self.fg_color = (180, 100, 200)

        elif self.tile_type == TileType.CACTUS:
            self.walkable = True
            self.transparent = True
            self.char = "Y"
            self.fg_color = (80, 160, 50)

        elif self.tile_type == TileType.RUINS:
            self.walkable = True
            self.transparent = True
            self.char = "n"
            self.fg_color = (130, 110, 90)

        elif self.tile_type == TileType.STAR_MOSS:
            self.walkable = True
            self.transparent = True
            self.char = "`"
            self.fg_color = (180, 160, 255)

        elif self.tile_type == TileType.SCORCHED_EARTH:
            self.walkable = True
            self.transparent = True
            self.char = "."
            self.fg_color = (120, 80, 50)

        elif self.tile_type == TileType.CRYSTAL_GRASS:
            self.walkable = True
            self.transparent = True
            self.char = ","
            self.fg_color = (150, 140, 255)

    def unlock(self):
        """문 잠금 해제"""
        if self.locked:
            self.locked = False
            self.walkable = True
            if self.tile_type == TileType.LOCKED_DOOR:
                self.tile_type = TileType.DOOR
                self.char = "+"

    def mark_harvested(self):
        """채집 후 시각 상태 변경 (RPG 오픈월드 자연 타일용)"""
        self.harvested = True
        self.fg_color = (80, 80, 80)  # 어두운 회색
        self.char = "."  # 빈 바닥으로 변경

    def restore_harvested_visual(self):
        """harvested 상태의 시각 복원 (청크 재생성/로드 시 호출)"""
        if self.harvested:
            self.fg_color = (80, 80, 80)
            self.char = "."

# ── 타일 정보 사전 (이름, 설명) ──────────────────────────────────────────
TILE_INFO: Dict[TileType, Tuple[str, str]] = {
    TileType.VOID: ("빈 공간", "아무것도 없는 공간"),
    TileType.FLOOR: ("바닥", "이동 가능한 바닥"),
    TileType.WALL: ("벽", "통과할 수 없는 벽"),
    TileType.DOOR: ("문", "열려있는 문"),
    TileType.LOCKED_DOOR: ("잠긴 문", "열쇠가 필요합니다"),
    TileType.STAIRS_UP: ("올라가는 계단", "위층으로 이동"),
    TileType.STAIRS_DOWN: ("내려가는 계단", "아래층으로 이동"),
    TileType.CHEST: ("보물상자", "열어서 아이템 획득"),
    TileType.TRAP: ("함정", "밟으면 피해를 받습니다"),
    TileType.TELEPORTER: ("텔레포터", "다른 장소로 이동"),
    TileType.LAVA: ("용암", "밟으면 화상 피해"),
    TileType.HEALING_SPRING: ("치유의 샘", "HP를 회복합니다"),
    TileType.BOSS_ROOM: ("보스룸", "강력한 적이 기다리고 있다"),
    TileType.KEY: ("열쇠", "잠긴 문을 열 수 있다"),
    TileType.PUZZLE: ("퍼즐", "풀면 보상을 얻을 수 있다"),
    TileType.SHOP: ("상점", "아이템을 사고팔 수 있다"),
    TileType.ITEM: ("아이템", "떨어진 아이템"),
    TileType.DROPPED_ITEM: ("드롭 아이템", "누군가 떨어뜨린 아이템"),
    TileType.GOLD: ("골드", "떨어진 골드"),
    TileType.INGREDIENT: ("식재료", "채집할 수 있는 식재료"),
    TileType.SWITCH: ("스위치", "작동시키면 무언가 변한다"),
    TileType.PRESSURE_PLATE: ("압력판", "밟으면 작동한다"),
    TileType.LEVER: ("레버", "당기면 무언가 변한다"),
    TileType.ALTAR: ("제단", "기도하면 버프를 받는다"),
    TileType.SHRINE: ("신전", "회복과 보상을 받을 수 있다"),
    TileType.PORTAL: ("포털", "다른 장소로 이동"),
    TileType.SPIKE_TRAP: ("가시 함정", "밟으면 가시에 찔린다"),
    TileType.POISON_GAS: ("독가스", "독 피해를 받습니다"),
    TileType.ICE_FLOOR: ("얼음 바닥", "미끄러질 수 있다"),
    TileType.FIRE_TRAP: ("화염 함정", "밟으면 화염 피해"),
    TileType.SECRET_DOOR: ("비밀 문", "숨겨진 통로"),
    TileType.BUTTON: ("버튼", "누르면 무언가 작동한다"),
    TileType.PEDESTAL: ("받침대", "아이템을 올려놓을 수 있다"),
    TileType.CRYSTAL: ("크리스탈", "MP를 회복합니다"),
    TileType.MANA_WELL: ("마나 샘", "MP를 회복합니다"),
    TileType.TREASURE_MAP: ("보물 지도", "보물의 위치를 알 수 있다"),
    TileType.RIDDLE_STONE: ("수수께끼 돌", "수수께끼를 풀어보자"),
    TileType.MAGIC_CIRCLE: ("마법진", "마법의 힘이 느껴진다"),
    TileType.SACRIFICE_ALTAR: ("희생 제단", "무언가를 바칠 수 있다"),
    TileType.ANVIL: ("모루", "장비를 수리할 수 있다"),
    # RPG 오픈월드
    TileType.GRASS: ("초원", "풀이 무성한 들판"),
    TileType.TALL_GRASS: ("키 큰 풀", "적이 숨어있을 수 있다"),
    TileType.SAND: ("모래", "건조한 사막 지형"),
    TileType.WATER: ("물", "깊은 물이라 건널 수 없다"),
    TileType.SHALLOW_WATER: ("얕은 물", "건널 수 있지만 느리다"),
    TileType.MOUNTAIN: ("산", "높은 절벽이라 지나갈 수 없다"),
    TileType.SNOW: ("눈", "눈으로 뒤덮인 대지"),
    TileType.DEEP_FOREST: ("울창한 숲", "빽빽한 나무 사이로 빛이 들지 않는다"),
    TileType.SWAMP: ("늪지", "발이 빠지는 습지"),
    TileType.PATH: ("길", "정비된 도로"),
    TileType.BRIDGE: ("다리", "물 위에 놓인 다리"),
    TileType.TOWN: ("마을", "마을 바닥"),
    TileType.CAVE_ENTRANCE: ("동굴 입구", "서브 던전으로 들어갈 수 있다"),
    TileType.NPC: ("NPC", "말을 걸 수 있다"),
    TileType.SIGNPOST: ("이정표", "방향을 알려주는 표지판"),
    TileType.CAMPFIRE: ("모닥불", "세이브 및 회복 포인트"),
    TileType.REGION_GATE: ("지역 경계", "다른 지역으로의 경계"),
    # RPG 마을 건물
    TileType.KITCHEN: ("주방", "요리와 식사를 할 수 있다"),
    TileType.BLACKSMITH: ("대장간", "장비를 강화할 수 있다"),
    TileType.ALCHEMY_LAB: ("연금술 실험실", "포션과 폭탄을 제작할 수 있다"),
    TileType.STORAGE_BUILDING: ("창고", "아이템을 보관할 수 있다"),
    TileType.QUEST_BOARD: ("퀘스트 게시판", "의뢰를 확인할 수 있다"),
    TileType.INN: ("여관", "휴식을 취하고 HP/MP를 회복한다"),
    TileType.GUILD_HALL: ("모험가 길드", "정보를 얻을 수 있다"),
    TileType.FOUNTAIN: ("분수대", "마을의 중심, HP/MP를 회복한다"),
    # RPG 장식 지형
    TileType.FLOWER: ("꽃", "들판에 피어난 야생화"),
    TileType.ROCK: ("바위", "땅에 박힌 바위"),
    TileType.DEAD_TREE: ("마른 나무", "생명력을 잃은 고목"),
    TileType.MUSHROOM: ("버섯", "축축한 곳에 자란 버섯"),
    TileType.CACTUS: ("선인장", "사막에서 자라는 선인장"),
    TileType.RUINS: ("폐허", "전쟁의 흔적이 남은 잔해"),
    TileType.STAR_MOSS: ("별이끼", "은은하게 빛나는 이끼"),
    TileType.SCORCHED_EARTH: ("그을린 땅", "전화에 탄 대지"),
    TileType.CRYSTAL_GRASS: ("수정 풀밭", "수정 가루가 빛나는 풀"),
}


def get_tile_info(tile_type: TileType) -> Tuple[str, str]:
    """타일 타입의 (이름, 설명) 반환. 미등록 타입은 기본값 반환."""
    return TILE_INFO.get(tile_type, (tile_type.value, ""))
