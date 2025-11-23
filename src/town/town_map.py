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
        
        # 장식 요소
        self._add_decorations()
    
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
        """건물 배치"""
        building_placements = [
            # (타입, x비율, y비율, 이름, 설명)
            (BuildingType.QUEST_BOARD, 0.5, 0.2, "퀘스트 게시판", "의뢰를 확인할 수 있습니다"),
            (BuildingType.KITCHEN, 0.25, 0.3, "별빛 주방", "요리와 식사를 할 수 있습니다"),
            (BuildingType.BLACKSMITH, 0.75, 0.3, "대장간", "장비를 강화할 수 있습니다"),
            (BuildingType.ALCHEMY_LAB, 0.25, 0.6, "연금술 실험실", "포션과 폭탄을 제작할 수 있습니다"),
            (BuildingType.STORAGE, 0.75, 0.6, "창고", "아이템을 보관할 수 있습니다"),
            (BuildingType.SHOP, 0.5, 0.7, "잡화점", "아이템을 사고팔 수 있습니다"),
            (BuildingType.INN, 0.2, 0.8, "여관", "휴식을 취할 수 있습니다"),
            (BuildingType.GUILD_HALL, 0.8, 0.8, "모험가 길드", "정보를 얻을 수 있습니다"),
            (BuildingType.FOUNTAIN, 0.5, 0.5, "중앙 분수대", "마을의 중심입니다")
        ]
        
        for building_type, x_ratio, y_ratio, name, desc in building_placements:
            x = int(self.width * x_ratio)
            y = int(self.height * y_ratio)
            
            building = Building(
                building_type=building_type,
                x=x,
                y=y,
                name=name,
                description=desc
            )
            
            self.buildings.append(building)
            self.tiles[y][x] = building.symbol
    
    def _add_decorations(self):
        """장식 추가"""
        # 나무와 잔디 추가 (랜덤)
        for _ in range(20):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            
            if self.tiles[y][x] == " ":
                self.tiles[y][x] = random.choice(["T", "t", "*"])  # T=나무, t=작은나무, *=꽃
    
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
        return tile in [" ", ".", "T", "t", "*"]  # 빈 공간, 도로, 장식은 이동 가능
    
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
        # 인플레이션: 플레이어 레벨에 따라 가격 증가
        base_cost = 150
        level_multiplier = 1 + (player.level // 5) * 0.5  # 5레벨마다 50% 증가
        cost = int(base_cost * level_multiplier)
        
        return {
            "message": "여관에 오신 것을 환영합니다!",
            "options": ["휴식하기 (파티 전체 HP/MP 완전 회복 + 부활)", "나가기"],
            "cost": cost,
            "level_multiplier": level_multiplier
        }
    
    @staticmethod
    def _interact_guild(player: Any) -> Dict[str, Any]:
        """길드 홀 상호작용"""
        return {
            "message": "모험가 길드에 오신 것을 환영합니다!",
            "options": ["정보 확인", "랭킹 보기", "나가기"]
        }


# 전역 인스턴스
_town_map = TownMap()

def get_town_map() -> TownMap:
    return _town_map
