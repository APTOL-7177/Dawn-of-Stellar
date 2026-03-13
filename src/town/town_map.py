"""
타운 허브 맵 시스템 (Town Hub Map)

플레이어가 탐험할 수 있는 마을 허브 맵
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import random

from src.core.logger import get_logger

logger = get_logger("town")


class BuildingType(Enum):
    """건물 타입"""
    KITCHEN = "kitchen"              # 주방
    BLACKSMITH = "blacksmith"        # 대장간
    ALCHEMY_LAB = "alchemy_lab"      # 연금술 실험실
    STORAGE = "storage"              # 창고
    QUEST_BOARD = "quest_board"      # 퀘스트 게시판
    SHOP = "shop"                    # 상점
    INN = "inn"                      # 여관
    GUILD_HALL = "guild_hall"        # 길드 홀
    FOUNTAIN = "fountain"            # 분수대 (장식)


@dataclass
class Building:
    """건물"""
    building_type: BuildingType
    x: int
    y: int
    name: str
    description: str
    accessible: bool = True  # 접근 가능 여부

    @property
    def symbol(self) -> str:
        """맵 심볼"""
        symbols = {
            BuildingType.KITCHEN: "K",
            BuildingType.BLACKSMITH: "B",
            BuildingType.ALCHEMY_LAB: "A",
            BuildingType.STORAGE: "S",
            BuildingType.QUEST_BOARD: "Q",
            BuildingType.SHOP: "$",
            BuildingType.INN: "I",
            BuildingType.GUILD_HALL: "G",
            BuildingType.FOUNTAIN: "F"
        }
        return symbols.get(self.building_type, "?")

    @property
    def color(self) -> tuple:
        """색상 (RGB)"""
        colors = {
            BuildingType.KITCHEN: (255, 200, 100),
            BuildingType.BLACKSMITH: (255, 140, 60),
            BuildingType.ALCHEMY_LAB: (180, 120, 255),
            BuildingType.STORAGE: (180, 130, 70),
            BuildingType.QUEST_BOARD: (255, 215, 0),
            BuildingType.SHOP: (100, 220, 100),
            BuildingType.INN: (220, 160, 220),
            BuildingType.GUILD_HALL: (255, 80, 80),
            BuildingType.FOUNTAIN: (100, 200, 255)
        }
        return colors.get(self.building_type, (255, 255, 255))


class TownMap:
    """타운 맵 - 시각적으로 꾸며진 마을"""

    def __init__(self, width: int = 40, height: int = 25):
        self.width = width
        self.height = height
        self.tiles: List[List[str]] = [["," for _ in range(width)] for _ in range(height)]
        self.buildings: List[Building] = []
        self.player_spawn = (width // 2, height - 3)  # 하단 중앙 스폰

        self._generate_town()

    def _generate_town(self):
        """타운 생성"""
        # 1. 성벽 테두리
        self._create_walls()
        # 2. 도로 네트워크
        self._create_roads()
        # 3. 건물 배치
        self._place_buildings()
        # 4. 건물 주변 벽 (울타리)
        self._add_building_enclosures()
        # 5. 분수대 물 타일
        self._add_fountain_area()
        # 6. 장식 (나무, 꽃)
        self._add_decorations()

    def _create_walls(self):
        """성벽 테두리 생성"""
        # 상단 벽
        for x in range(self.width):
            self.tiles[0][x] = "#"
        # 하단 벽 (출입구 제외)
        for x in range(self.width):
            self.tiles[self.height - 1][x] = "#"
        # 좌측 벽
        for y in range(self.height):
            self.tiles[y][0] = "#"
        # 우측 벽
        for y in range(self.height):
            self.tiles[y][self.width - 1] = "#"

        # 하단 출입구 (중앙 3칸 개방)
        gate_x = self.width // 2
        self.tiles[self.height - 1][gate_x - 1] = "."
        self.tiles[self.height - 1][gate_x] = "."
        self.tiles[self.height - 1][gate_x + 1] = "."

    def _create_roads(self):
        """격자형 도로 생성"""
        # 주요 세로 도로: x=10, 20, 30
        road_cols = [10, 20, 30]
        for x in road_cols:
            if x < self.width:
                for y in range(1, self.height - 1):
                    if self.tiles[y][x] != "#":
                        self.tiles[y][x] = "."

        # 주요 가로 도로: y=6, 13, 20
        road_rows = [6, 13, 20]
        for y in road_rows:
            if y < self.height:
                for x in range(1, self.width - 1):
                    if self.tiles[y][x] != "#":
                        self.tiles[y][x] = "."

        # 하단 출입구로 연결하는 세로 도로
        gate_x = self.width // 2
        for y in range(20, self.height - 1):
            if self.tiles[y][gate_x] != "#":
                self.tiles[y][gate_x] = "."

    def _place_buildings(self):
        """건물 배치 - 격자 도로에 맞춰 배치"""
        placed_types = set()

        # 건물 배치 (40x25 기준 좌표)
        building_placements = [
            # 상단 구역 (y=3~4)
            (BuildingType.KITCHEN, 5, 3, "별빛 주방", "요리와 식사를 할 수 있습니다"),
            (BuildingType.QUEST_BOARD, 15, 3, "퀘스트 게시판", "의뢰를 확인할 수 있습니다"),
            (BuildingType.BLACKSMITH, 25, 3, "대장간", "장비를 강화할 수 있습니다"),
            # 중앙 구역 (y=9~10)
            (BuildingType.ALCHEMY_LAB, 5, 9, "연금술 실험실", "포션과 폭탄을 제작할 수 있습니다"),
            (BuildingType.FOUNTAIN, 20, 10, "중앙 분수대", "마을의 중심입니다"),
            (BuildingType.STORAGE, 35, 9, "창고", "아이템을 보관할 수 있습니다"),
            # 하단 구역 (y=16~17)
            (BuildingType.INN, 5, 16, "여관", "휴식을 취할 수 있습니다"),
            (BuildingType.SHOP, 15, 16, "잡화점", "아이템을 사고팔 수 있습니다"),
            (BuildingType.GUILD_HALL, 25, 16, "모험가 길드", "퀘스트와 정보를 얻을 수 있습니다"),
        ]

        for building_type, bx, by, name, desc in building_placements:
            if building_type in placed_types:
                continue

            # 좌표 범위 체크
            if bx < 1 or bx >= self.width - 1 or by < 1 or by >= self.height - 1:
                logger.warning(f"건물 {name}의 좌표 ({bx}, {by})가 맵 범위를 벗어났습니다.")
                continue

            existing_building = self.get_building_at(bx, by)
            if existing_building:
                continue

            building = Building(
                building_type=building_type,
                x=bx,
                y=by,
                name=name,
                description=desc
            )

            self.buildings.append(building)
            self.tiles[by][bx] = building.symbol
            placed_types.add(building_type)

    def _add_building_enclosures(self):
        """건물 주변에 작은 울타리/벽 배치"""
        for building in self.buildings:
            # 분수대는 울타리 없음
            if building.building_type == BuildingType.FOUNTAIN:
                continue

            bx, by = building.x, building.y
            # 건물 주변 3x3 영역에 울타리 (아래쪽 입구는 열어둠)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = bx + dx, by + dy
                    if 0 < nx < self.width - 1 and 0 < ny < self.height - 1:
                        # 건물 자체, 도로, 다른 건물은 건드리지 않음
                        if self.tiles[ny][nx] == ",":
                            # 가장자리만 울타리 (건물 바로 아래는 입구로 비워둠)
                            if abs(dx) == 1 or abs(dy) == 1:
                                # 건물 아래쪽 (dy==1, dx==0)은 입구
                                if dy == 1 and dx == 0:
                                    self.tiles[ny][nx] = "."  # 도로로 설정 (입구)
                                else:
                                    self.tiles[ny][nx] = "="

    def _add_fountain_area(self):
        """분수대 주변에 물 타일 추가"""
        fountain = None
        for b in self.buildings:
            if b.building_type == BuildingType.FOUNTAIN:
                fountain = b
                break

        if not fountain:
            return

        fx, fy = fountain.x, fountain.y
        # 분수대 주변 십자 형태로 물 배치
        water_offsets = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1),
        ]
        for dx, dy in water_offsets:
            nx, ny = fx + dx, fy + dy
            if 0 < nx < self.width - 1 and 0 < ny < self.height - 1:
                if self.tiles[ny][nx] in [",", " "]:
                    self.tiles[ny][nx] = "~"

    def _add_decorations(self):
        """장식 요소 추가 (나무, 꽃)"""
        building_positions = {(b.x, b.y) for b in self.buildings}

        # 사용 가능한 위치 (잔디만)
        available = []
        for y in range(2, self.height - 2):
            for x in range(2, self.width - 2):
                if self.tiles[y][x] == "," and (x, y) not in building_positions:
                    available.append((x, y))

        if not available:
            return

        # 나무 배치 (벽 근처 우선)
        tree_count = min(25, len(available) // 5)
        # 벽 근처 위치 우선
        wall_adjacent = [
            (x, y) for x, y in available
            if y <= 3 or y >= self.height - 4 or x <= 3 or x >= self.width - 4
        ]
        interior = [(x, y) for x, y in available if (x, y) not in wall_adjacent]

        rng = random.Random(42)  # 고정 시드로 일관된 배치

        tree_positions = set()
        # 벽 근처에 나무 배치
        wall_trees = rng.sample(wall_adjacent, min(tree_count // 2, len(wall_adjacent)))
        for x, y in wall_trees:
            self.tiles[y][x] = "T"
            tree_positions.add((x, y))

        # 내부에도 나무 배치 (건물 울타리와 2칸 이상 떨어진 곳)
        interior_trees = rng.sample(interior, min(tree_count // 2, len(interior)))
        for x, y in interior_trees:
            # 울타리("=")에 인접하지 않은 곳만
            near_enclosure = False
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if self.tiles[ny][nx] == "=":
                            near_enclosure = True
                            break
                if near_enclosure:
                    break
            if not near_enclosure:
                self.tiles[y][x] = "T"
                tree_positions.add((x, y))

        # 꽃 배치 (도로 옆, 건물 근처)
        remaining = [
            (x, y) for x, y in available
            if (x, y) not in tree_positions and self.tiles[y][x] == ","
        ]
        flower_count = min(15, len(remaining) // 4)
        if remaining and flower_count > 0:
            flower_positions = rng.sample(remaining, flower_count)
            for x, y in flower_positions:
                self.tiles[y][x] = "*"

    def get_building_at(self, x: int, y: int) -> Optional[Building]:
        """특정 위치의 건물 가져오기"""
        for building in self.buildings:
            if building.x == x and building.y == y:
                return building
        return None

    def get_tile(self, x: int, y: int) -> str:
        """타일 가져오기"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return "#"  # 벽

    def is_walkable(self, x: int, y: int) -> bool:
        """이동 가능 여부"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False

        tile = self.tiles[y][x]
        # 잔디, 도로, 꽃, 빈공간, 건물 심볼은 이동 가능
        # 벽(#), 울타리(=), 나무(T), 물(~)은 이동 불가
        return tile in [",", ".", "*", " "] or tile in ['K', 'B', 'A', 'S', 'Q', '$', 'I', 'G', 'F']

    def render_ascii(self, player_x: int, player_y: int) -> str:
        """ASCII 렌더링"""
        lines = []
        lines.append("=" * (self.width + 2))

        for y in range(self.height):
            row = "|"
            for x in range(self.width):
                if x == player_x and y == player_y:
                    row += "@"  # 플레이어
                else:
                    row += self.tiles[y][x]
            row += "|"
            lines.append(row)

        lines.append("=" * (self.width + 2))

        # 범례
        lines.append("")
        lines.append("[ 범례 ]")
        lines.append("@ = 플레이어 | . = 도로 | , = 잔디")
        lines.append("K = 주방 | B = 대장간 | A = 연금술실 | S = 창고")
        lines.append("Q = 퀘스트 | $ = 상점 | I = 여관 | G = 길드 | F = 분수")
        lines.append("T = 나무 | ~ = 물 | * = 꽃 | = = 울타리")

        return "\n".join(lines)


class TownInteractionHandler:
    """타운 상호작용 핸들러"""

    @staticmethod
    def interact_with_building(building: Building, player: Any, town_manager: Any) -> Dict[str, Any]:
        """
        건물과 상호작용

        Args:
            building: 건물
            player: 플레이어
            town_manager: TownManager 인스턴스

        Returns:
            상호작용 결과
        """
        if building.building_type == BuildingType.KITCHEN:
            return TownInteractionHandler._interact_kitchen(player, town_manager)

        elif building.building_type == BuildingType.BLACKSMITH:
            return TownInteractionHandler._interact_blacksmith(player, town_manager)

        elif building.building_type == BuildingType.ALCHEMY_LAB:
            return TownInteractionHandler._interact_alchemy(player, town_manager)

        elif building.building_type == BuildingType.STORAGE:
            return TownInteractionHandler._interact_storage(player, town_manager)

        elif building.building_type == BuildingType.QUEST_BOARD:
            return TownInteractionHandler._interact_quest_board(player)

        elif building.building_type == BuildingType.SHOP:
            return TownInteractionHandler._interact_shop(player)

        elif building.building_type == BuildingType.INN:
            return TownInteractionHandler._interact_inn(player)

        elif building.building_type == BuildingType.GUILD_HALL:
            return TownInteractionHandler._interact_guild(player)

        elif building.building_type == BuildingType.FOUNTAIN:
            return TownInteractionHandler._interact_fountain(player)

        return {"message": f"{building.name}에 입장했습니다."}

    @staticmethod
    def _interact_kitchen(player: Any, town_manager: Any) -> Dict[str, Any]:
        """주방 상호작용"""
        from src.town.town_manager import FacilityType
        facility = town_manager.get_facility(FacilityType.KITCHEN)

        return {
            "message": "별빛 주방에 오신 것을 환영합니다!",
            "options": ["요리하기", "시설 업그레이드", "나가기"],
            "facility_level": facility.level if facility else 1
        }

    @staticmethod
    def _interact_blacksmith(player: Any, town_manager: Any) -> Dict[str, Any]:
        """대장간 상호작용"""
        from src.town.town_manager import FacilityType
        facility = town_manager.get_facility(FacilityType.BLACKSMITH)

        return {
            "message": "대장간에 오신 것을 환영합니다!",
            "options": ["장비 수리", "장비 재련", "시설 업그레이드", "나가기"],
            "facility_level": facility.level if facility else 1
        }

    @staticmethod
    def _interact_alchemy(player: Any, town_manager: Any) -> Dict[str, Any]:
        """연금술실 상호작용"""
        from src.town.town_manager import FacilityType
        facility = town_manager.get_facility(FacilityType.ALCHEMY_LAB)

        return {
            "message": "연금술 실험실에 오신 것을 환영합니다!",
            "options": ["포션 제작", "폭탄 제작", "시설 업그레이드", "나가기"],
            "facility_level": facility.level if facility else 1
        }

    @staticmethod
    def _interact_storage(player: Any, town_manager: Any) -> Dict[str, Any]:
        """창고 상호작용"""
        hub_storage = town_manager.get_hub_storage()

        return {
            "message": "창고에 오신 것을 환영합니다!",
            "options": ["보관함 확인", "아이템 찾기", "나가기"],
            "storage_items": hub_storage
        }

    @staticmethod
    def _interact_quest_board(player: Any) -> Dict[str, Any]:
        """퀘스트 게시판 상호작용"""
        from src.quest.quest_manager import get_quest_manager
        quest_manager = get_quest_manager()

        available = quest_manager.get_available_quests()
        active = quest_manager.get_active_quests()

        return {
            "message": "퀘스트 게시판입니다.",
            "available_quests": len(available),
            "active_quests": len(active)
        }

    @staticmethod
    def _interact_shop(player: Any) -> Dict[str, Any]:
        """상점 상호작용"""
        return {
            "message": "잡화점에 오신 것을 환영합니다!",
            "options": ["구매", "판매", "나가기"]
        }

    @staticmethod
    def _interact_inn(player: Any) -> Dict[str, Any]:
        """여관 상호작용 - 파티 전체 회복 + 인플레이션"""
        # 인플레이션: 도달한 최고 층수에 따라 가격 증가 (층당 25%)
        base_cost = 100

        # 최고 도달 층수 가져오기
        max_floor = 1
        if hasattr(player, 'max_floor_reached'):
            max_floor = player.max_floor_reached

        # 인플레이션 배율 적용 (1층=1.0, 층당 +0.25)
        inflation_multiplier = 1.0 + (max_floor - 1) * 0.25
        cost = int(base_cost * inflation_multiplier)

        return {
            "message": "여관에 오신 것을 환영합니다!",
            "options": ["휴식하기 (파티 전체 HP/MP 완전 회복 + 부활)", "나가기"],
            "cost": cost,
            "level_multiplier": inflation_multiplier
        }

    @staticmethod
    def _interact_guild(player: Any) -> Dict[str, Any]:
        """길드 홀 상호작용"""
        return {
            "message": "모험가 길드에 오신 것을 환영합니다!",
            "options": ["정보 확인", "랭킹 보기", "나가기"]
        }

    @staticmethod
    def _interact_fountain(player: Any) -> Dict[str, Any]:
        """분수대 상호작용 (장식)"""
        return {
            "message": "중앙 분수대에 입장했습니다. 마을의 중심입니다."
        }


def create_town_dungeon_map(town_map: 'TownMap') -> Any:
    """
    TownMap을 DungeonMap으로 변환

    Args:
        town_map: TownMap 인스턴스

    Returns:
        DungeonMap 인스턴스
    """
    from src.world.dungeon_generator import DungeonMap
    from src.world.tile import Tile, TileType
    from src.world.dungeon_generator import Rect

    # 던전 맵 생성
    dungeon = DungeonMap(town_map.width, town_map.height)

    # 건물 위치를 딕셔너리로 저장 (렌더링용)
    building_positions = {}
    for building in town_map.buildings:
        building_positions[(building.x, building.y)] = building

    # 타일 색상 매핑
    tile_styles = {
        ",": (TileType.FLOOR, ",", (60, 130, 50), (5, 20, 5)),       # 잔디
        ".": (TileType.FLOOR, ".", (180, 160, 120), (20, 15, 10)),    # 도로
        " ": (TileType.FLOOR, " ", (80, 80, 80), (0, 0, 0)),         # 빈공간
        "#": (TileType.WALL, "#", (140, 130, 110), (40, 35, 30)),     # 성벽
        "=": (TileType.WALL, "=", (120, 110, 80), (30, 25, 15)),      # 울타리
        "T": (TileType.WALL, "T", (34, 160, 34), (10, 30, 10)),       # 나무
        "~": (TileType.WALL, "~", (80, 160, 255), (10, 20, 50)),      # 물 (이동 불가)
        "*": (TileType.FLOOR, "*", (255, 200, 120), (15, 25, 10)),    # 꽃
    }

    # 마을 타일을 던전 타일로 변환
    for y in range(town_map.height):
        for x in range(town_map.width):
            tile_char = town_map.tiles[y][x]

            # 건물 위치인 경우
            if (x, y) in building_positions:
                building = building_positions[(x, y)]
                dungeon.set_tile(x, y, TileType.FLOOR)
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.building_symbol = building.symbol
                    tile.building_color = building.color
                    tile.building = building
                    tile.char = building.symbol
                    tile.fg_color = building.color
                    tile.explored = True
                    tile.visible = True
            elif tile_char in tile_styles:
                tile_type, char, fg, bg = tile_styles[tile_char]
                dungeon.set_tile(x, y, tile_type)
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.char = char
                    tile.fg_color = fg
                    tile.bg_color = bg
            elif tile_char in ['K', 'B', 'A', 'S', 'Q', '$', 'I', 'G', 'F']:
                # 건물 심볼이지만 building_positions에 없는 경우 (안전장치)
                dungeon.set_tile(x, y, TileType.FLOOR)
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.char = tile_char
                    tile.fg_color = (255, 255, 255)
            else:
                # 기타는 FLOOR (잔디 색상)
                dungeon.set_tile(x, y, TileType.FLOOR)
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.char = tile_char
                    tile.fg_color = (60, 130, 50)

    # 물 타일은 이동 불가로 설정 (FLOOR이지만 walkable=False 효과)
    # map_renderer에서는 FLOOR로 표시하되, exploration에서 이동 제한

    # 모든 마을 타일: 탐험됨 + 보임
    for y in range(town_map.height):
        for x in range(town_map.width):
            tile = dungeon.get_tile(x, y)
            if tile:
                tile.explored = True
                tile.visible = True

    # 마을 출입구를 계단으로 설정
    exit_x = town_map.width // 2
    exit_y = town_map.height - 2
    dungeon.set_tile(exit_x, exit_y, TileType.STAIRS_DOWN)
    tile = dungeon.get_tile(exit_x, exit_y)
    if tile:
        tile.explored = True
        tile.visible = True
    dungeon.stairs_down = (exit_x, exit_y)

    # 빈 방 리스트
    dungeon.rooms = []
    for building in town_map.buildings:
        rect = Rect(building.x - 1, building.y - 1, 3, 3)
        dungeon.rooms.append(rect)

    # 마을 표시 플래그
    dungeon.is_town = True
    dungeon.town_map = town_map

    return dungeon


# 전역 인스턴스
_town_map = TownMap()

def get_town_map() -> TownMap:
    return _town_map
