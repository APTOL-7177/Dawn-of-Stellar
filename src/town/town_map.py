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
            BuildingType.BLACKSMITH: (180, 100, 50),
            BuildingType.ALCHEMY_LAB: (150, 100, 255),
            BuildingType.STORAGE: (139, 69, 19),
            BuildingType.QUEST_BOARD: (255, 215, 0),
            BuildingType.SHOP: (100, 200, 100),
            BuildingType.INN: (200, 150, 200),
            BuildingType.GUILD_HALL: (200, 50, 50),
            BuildingType.FOUNTAIN: (100, 200, 255)
        }
        return colors.get(self.building_type, (255, 255, 255))


class TownMap:
    """타운 맵"""
    
    def __init__(self, width: int = 30, height: int = 20):
        self.width = width
        self.height = height
        self.tiles: List[List[str]] = [[" " for _ in range(width)] for _ in range(height)]
        self.buildings: List[Building] = []
        self.player_spawn = (width // 2, height - 2)  # 하단 중앙 스폰
        
        self._generate_town()
    
    def _generate_town(self):
        """타운 생성"""
        # 보도 생성 (가로/세로)
        self._create_roads()
        
        # 건물 배치
        self._place_buildings()
        
        # 장식 요소 제거 (사용자 요청)
        # self._add_decorations()
    
    def _create_roads(self):
        """도로 생성"""
        # 가로 도로 (중앙)
        mid_y = self.height // 2
        for x in range(self.width):
            self.tiles[mid_y][x] = "."
        
        # 세로 도로 (중앙)
        mid_x = self.width // 2
        for y in range(self.height):
            self.tiles[y][mid_x] = "."
        
        # 추가 세로 도로 (좌우)
        for x in [self.width // 4, 3 * self.width // 4]:
            for y in range(self.height):
                self.tiles[y][x] = "."
    
    def _place_buildings(self):
        """건물 배치 - 각 건물 타입은 하나씩만, 고정 위치"""
        # 이미 배치된 건물 타입 추적 (중복 방지)
        placed_types = set()
        
        # 건물 배치 정의: (타입, 고정 x 좌표, 고정 y 좌표, 이름, 설명)
        # 맵 크기에 상관없이 고정 위치 사용 (30x20 기준으로 설계)
        building_placements = [
            # 상단 중앙
            (BuildingType.QUEST_BOARD, 15, 4, "퀘스트 게시판", "의뢰를 확인할 수 있습니다"),
            # 상단 좌우
            (BuildingType.KITCHEN, 7, 6, "별빛 주방", "요리와 식사를 할 수 있습니다"),
            (BuildingType.BLACKSMITH, 22, 6, "대장간", "장비를 강화할 수 있습니다"),
            # 중앙 좌우
            (BuildingType.ALCHEMY_LAB, 7, 12, "연금술 실험실", "포션과 폭탄을 제작할 수 있습니다"),
            (BuildingType.STORAGE, 22, 12, "창고", "아이템을 보관할 수 있습니다"),
            # 중앙
            (BuildingType.FOUNTAIN, 15, 10, "중앙 분수대", "마을의 중심입니다"),
            # 하단
            (BuildingType.SHOP, 15, 14, "잡화점", "아이템을 사고팔 수 있습니다"),
            (BuildingType.INN, 6, 16, "여관", "휴식을 취할 수 있습니다"),
            (BuildingType.GUILD_HALL, 24, 16, "모험가 길드", "정보를 얻을 수 있습니다")
        ]
        
        # 맵 크기에 맞게 좌표 스케일링 (30x20 기준)
        base_width = 30
        base_height = 20
        scale_x = self.width / base_width
        scale_y = self.height / base_height
        
        for building_type, base_x, base_y, name, desc in building_placements:
            # 이미 배치된 건물 타입은 건너뜀 (중복 방지)
            if building_type in placed_types:
                logger.warning(f"건물 타입 {building_type.value}가 이미 배치되어 있습니다. 건너뜁니다.")
                continue
            
            # 스케일링된 좌표 계산 (맵 크기에 따라 조정)
            x = int(base_x * scale_x)
            y = int(base_y * scale_y)
            
            # 좌표 범위 체크
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                logger.warning(f"건물 {name}의 좌표 ({x}, {y})가 맵 범위를 벗어났습니다. 건너뜁니다.")
                continue
            
            # 이미 다른 건물이 있는 위치인지 확인 (도로는 덮어쓸 수 있음)
            # 같은 위치에 건물이 이미 있는지 확인
            existing_building = self.get_building_at(x, y)
            if existing_building:
                logger.warning(f"건물 {name}의 위치 ({x}, {y})에 이미 다른 건물({existing_building.name})이 있습니다. 건너뜁니다.")
                continue
            
            # 타일이 건물 심볼인 경우도 건너뜀 (중복 방지)
            if self.tiles[y][x] not in [" ", "."]:
                # 건물 심볼인 경우
                if self.tiles[y][x] in ['K', 'B', 'A', 'S', 'Q', '$', 'I', 'G', 'F']:
                    logger.warning(f"건물 {name}의 위치 ({x}, {y})에 이미 건물이 있습니다. (타일: {self.tiles[y][x]}) 건너뜁니다.")
                    continue
            
            building = Building(
                building_type=building_type,
                x=x,
                y=y,
                name=name,
                description=desc
            )
            
            self.buildings.append(building)
            self.tiles[y][x] = building.symbol
            placed_types.add(building_type)  # 배치된 타입 기록
    
    def _add_decorations(self):
        """장식 추가 - 건물과 도로 위치를 피해서 배치"""
        # 건물 위치 저장 (중복 배치 방지)
        building_positions = {(building.x, building.y) for building in self.buildings}
        
        # 도로 위치 저장 (도로에는 장식 배치하지 않음)
        road_positions = set()
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == ".":
                    road_positions.add((x, y))
        
        # 사용 가능한 위치만 필터링 (빈 공간만)
        available_positions = []
        for y in range(self.height):
            for x in range(self.width):
                # 건물 위치, 도로 위치, 이미 장식이 있는 위치는 제외
                if (x, y) not in building_positions and (x, y) not in road_positions and self.tiles[y][x] == " ":
                    available_positions.append((x, y))
        
        # 사용 가능한 위치가 없으면 장식 추가 안 함
        if not available_positions:
            logger.warning("장식을 배치할 위치가 없습니다.")
            return
        
        # 장식 배치 (최대 20개, 또는 사용 가능한 위치 수만큼)
        decoration_count = min(20, len(available_positions))
        decoration_positions = random.sample(available_positions, decoration_count)
        
        for x, y in decoration_positions:
            # 각 위치에 하나씩만 장식 배치 (중복 방지)
            if self.tiles[y][x] == " ":
                self.tiles[y][x] = random.choice(["T", "t", "*"])  # T=나무, t=작은나무, *=꽃
                logger.debug(f"장식 배치: ({x}, {y}) = {self.tiles[y][x]}")
    
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
        return tile in [" ", "."]  # 빈 공간, 도로만 이동 가능 (장식 제거)
    
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
        lines.append("@ = 플레이어 | . = 도로")
        lines.append("K = 주방 | B = 대장간 | A = 연금술실 | S = 창고")
        lines.append("Q = 퀘스트 | $ = 상점 | I = 여관 | G = 길드 | F = 분수")
        
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
        # 예: 1층=100G, 5층=200G, 10층=325G
        inflation_multiplier = 1.0 + (max_floor - 1) * 0.25
        cost = int(base_cost * inflation_multiplier)
        
        return {
            "message": "여관에 오신 것을 환영합니다!",
            "options": ["휴식하기 (파티 전체 HP/MP 완전 회복 + 부활)", "나가기"],
            "cost": cost,
            "level_multiplier": inflation_multiplier  # 이름은 유지하되 의미는 인플레이션 배율
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
    
    # 마을 타일을 던전 타일로 변환
    for y in range(town_map.height):
        for x in range(town_map.width):
            tile_char = town_map.tiles[y][x]
            
            # 건물 위치인 경우
            if (x, y) in building_positions:
                building = building_positions[(x, y)]
                # 건물 타일: FLOOR로 설정하고 건물 정보 저장
                # 타일을 먼저 설정한 후 속성 추가
                dungeon.set_tile(x, y, TileType.FLOOR)
                tile = dungeon.get_tile(x, y)
                if tile:
                    # 건물 정보를 타일에 저장 (렌더링용)
                    tile.building_symbol = building.symbol
                    tile.building_color = building.color
                    tile.building = building  # 건물 객체 참조 저장
                    # 건물 문자가 기본 타일 문자보다 우선되도록 설정
                    tile.char = building.symbol
                    tile.fg_color = building.color
                    # 마을 타일은 탐험됨과 보임 상태로 설정 (전체 시야)
                    tile.explored = True
                    tile.visible = True
            elif tile_char == ".":
                # 도로는 FLOOR로 설정하고 도로 표시
                dungeon.set_tile(x, y, TileType.FLOOR)
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.char = "."  # 도로 문자
                    tile.fg_color = (150, 150, 150)  # 도로 색상
            elif tile_char == " ":
                # 빈 공간은 FLOOR
                dungeon.set_tile(x, y, TileType.FLOOR)
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.char = " "  # 빈 공간
                    tile.fg_color = (80, 80, 80)  # 어두운 색상
            elif tile_char == "#":
                # 벽은 WALL
                dungeon.set_tile(x, y, TileType.WALL)
            # 장식 요소 제거 (T, t, * 제거)
            # elif tile_char in ["T", "t", "*"]: 제거됨
            else:
                # 기타는 FLOOR
                dungeon.set_tile(x, y, TileType.FLOOR)
    
    # 마을 출입구를 계단으로 설정 (하단 중앙, 던전으로 나가는 계단)
    exit_x, exit_y = town_map.width // 2, town_map.height - 2
    dungeon.set_tile(exit_x, exit_y, TileType.STAIRS_DOWN)
    dungeon.stairs_down = (exit_x, exit_y)
    
    # 빈 방 리스트 (마을은 방 구조가 없으므로)
    dungeon.rooms = []
    
    # 건물 위치를 "방"으로 간주 (필요 시)
    for building in town_map.buildings:
        # 건물 위치를 간단한 방으로 추가 (시각화용)
        from src.world.dungeon_generator import Rect
        rect = Rect(building.x - 1, building.y - 1, 3, 3)
        dungeon.rooms.append(rect)
    
    # 마을 표시 플래그 추가
    dungeon.is_town = True
    dungeon.town_map = town_map  # 원본 마을 맵 참조 저장
    
    return dungeon


# 전역 인스턴스
_town_map = TownMap()

def get_town_map() -> TownMap:
    return _town_map
