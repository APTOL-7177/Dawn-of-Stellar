"""
채집 가능한 오브젝트

던전에 배치되는 채집 포인트
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
import random

from src.gathering.ingredient import IngredientDatabase


class HarvestableType(Enum):
    """채집 오브젝트 타입"""
    BERRY_BUSH = "berry_bush"       # 베리 덤불
    MUSHROOM_PATCH = "mushroom_patch"  # 버섯 패치
    HERB_PLANT = "herb_plant"       # 허브 식물
    TREE = "tree"                   # 나무 (나뭇가지, 과일)
    ROCK = "rock"                   # 바위 (광물)
    WATER = "water"                 # 물 (물고기, 얼음)
    CARCASS = "carcass"             # 시체 (고기)
    COOKING_POT = "cooking_pot"     # 요리솥

    @property
    def display_name(self) -> str:
        """표시 이름"""
        names = {
            HarvestableType.BERRY_BUSH: "베리 덤불",
            HarvestableType.MUSHROOM_PATCH: "버섯 패치",
            HarvestableType.HERB_PLANT: "허브 식물",
            HarvestableType.TREE: "나무",
            HarvestableType.ROCK: "바위",
            HarvestableType.WATER: "물가",
            HarvestableType.CARCASS: "시체",
            HarvestableType.COOKING_POT: "요리솥"
        }
        return names.get(self, "???")

    @property
    def symbol(self) -> str:
        """맵 심볼"""
        symbols = {
            HarvestableType.BERRY_BUSH: "♣",
            HarvestableType.MUSHROOM_PATCH: "♠",
            HarvestableType.HERB_PLANT: "♦",
            HarvestableType.TREE: "♣",
            HarvestableType.ROCK: "◙",
            HarvestableType.WATER: "≈",
            HarvestableType.CARCASS: "☠",
            HarvestableType.COOKING_POT: "Ω"
        }
        return symbols.get(self, "?")


@dataclass
class HarvestableObject:
    """
    채집 가능한 오브젝트

    던전 맵에 배치되며, 플레이어가 채집할 수 있음
    멀티플레이에서는 개인 보상이므로 각 플레이어가 독립적으로 채집 가능
    """
    object_type: HarvestableType
    x: int
    y: int
    harvested: bool = False  # 싱글플레이 호환성을 위해 유지 (deprecated)
    harvested_by: Set[str] = field(default_factory=set)  # 채집한 플레이어 ID 집합 (멀티플레이용)

    # 획득 가능한 재료 (ingredient_id, 최소 개수, 최대 개수)
    loot_table: List[Tuple[str, int, int]] = None

    def __post_init__(self):
        """기본 루트 테이블 설정"""
        if self.loot_table is None:
            self.loot_table = self._get_default_loot_table()

    def _get_default_loot_table(self) -> List[Tuple[str, int, int]]:
        """타입별 기본 루트 테이블 (드롭률 대폭 증가)"""
        loot_tables = {
            HarvestableType.BERRY_BUSH: [
                ("berry", 3, 6),
                ("tomato", 1, 2),
                ("star_fruit", 0, 1), # 희귀: 별모양 과일
            ],
            HarvestableType.MUSHROOM_PATCH: [
                ("red_mushroom", 2, 4),
                ("blue_mushroom", 1, 2),
                ("ginger", 0, 2),
                ("truffle", 0, 1), # 희귀: 송로버섯
            ],
            HarvestableType.HERB_PLANT: [
                ("carrot", 2, 4),
                ("potato", 1, 3),
                ("onion", 1, 3),
                ("magic_herb", 0, 2),
                ("tea_leaf", 0, 2),
                ("flour", 0, 2),
                ("rice", 0, 2),
                ("sugar", 0, 2),
                ("spice", 0, 1),
                ("mandrake", 0, 1), # 희귀: 만드라고라
            ],
            HarvestableType.TREE: [
                ("stick", 2, 5),
                ("apple", 1, 3),
                ("egg", 0, 2),
                ("berry", 1, 2),
                ("golden_apple", 0, 1), # 전설: 황금 사과
            ],
            HarvestableType.ROCK: [
                ("ice", 2, 4),
                ("salt", 1, 3),
                ("dragon_scale", 0, 1), # 전설: 용의 비늘 (광맥에서 발견?)
            ],
            HarvestableType.WATER: [
                ("fish", 2, 5),
                ("shellfish", 1, 3),
                ("water", 2, 5),
                ("ice", 1, 2),
                ("slime_jelly", 0, 2), # 물가에 슬라임?
            ],
            HarvestableType.CARCASS: [
                ("monster_meat", 2, 4),
                ("beast_meat", 1, 2),
                ("milk", 0, 2),
                ("dragon_meat", 0, 1),
                ("phoenix_feather", 0, 1), # 전설: 불사조 깃털
            ],
            HarvestableType.COOKING_POT: [
                # 요리솥은 채집 대상이 아니라 상호작용 오브젝트
            ],
        }
        return loot_tables.get(self.object_type, [])

    def harvest(self, player_id: str = None) -> Dict[str, int]:
        """
        채집 실행

        Args:
            player_id: 플레이어 ID (멀티플레이용, None이면 싱글플레이)

        Returns:
            획득한 재료 딕셔너리 {ingredient_id: quantity}
        """
        # 멀티플레이: 플레이어별 채집 상태 확인
        if player_id:
            if player_id in self.harvested_by:
                return {}  # 이미 이 플레이어가 채집함
            self.harvested_by.add(player_id)
        else:
            # 싱글플레이: 기존 로직 (하위 호환성)
            if self.harvested:
                return {}
            self.harvested = True

        results = {}

        for ingredient_id, min_qty, max_qty in self.loot_table:
            qty = random.randint(min_qty, max_qty)
            
            # 식재료 드롭률 50% 감소 (0.5배)
            # 0개가 나올 수 있음 (의도된 사항)
            qty = int(qty * 0.5)

            if qty > 0:
                results[ingredient_id] = results.get(ingredient_id, 0) + qty
        
        # 봇 전용: 채집 결과가 비어있으면 최소 1개 보장 (무한 시도 방지용)
        # (봇 ID는 보통 'bot_'으로 시작한다고 가정)
        if player_id and player_id.startswith('bot_') and not results:
            # 기본 재료라도 하나 줌
            default_item = self.loot_table[0][0] if self.loot_table else "stick"
            results[default_item] = 1

        return results

    def harvest_by_bot(self, bot_id: str) -> Dict[str, int]:
        """
        봇 전용 채집 (간소화된 프로세스)
        
        Args:
            bot_id: 봇 ID
            
        Returns:
            획득한 재료
        """
        # 거리 체크나 기타 검증 없이 즉시 채집 (AI 로직에서 이미 확인했다고 가정)
        return self.harvest(bot_id)

    def can_harvest(self, player_id: str = None) -> bool:
        """
        채집 가능 여부
        
        Args:
            player_id: 플레이어 ID (멀티플레이용, None이면 싱글플레이)
        
        Returns:
            채집 가능 여부
        """
        if player_id:
            # 멀티플레이: 이 플레이어가 채집했는지 확인
            return player_id not in self.harvested_by
        else:
            # 싱글플레이: 기존 로직
            return not self.harvested

    @property
    def char(self) -> str:
        """맵에 표시될 문자 심볼"""
        return self.object_type.symbol

    @property
    def color(self) -> tuple:
        """오브젝트 색상 (RGB)"""
        colors = {
            HarvestableType.BERRY_BUSH: (255, 100, 100),      # 빨간색
            HarvestableType.MUSHROOM_PATCH: (200, 100, 255),  # 보라색
            HarvestableType.HERB_PLANT: (100, 255, 100),      # 초록색
            HarvestableType.TREE: (139, 69, 19),              # 갈색
            HarvestableType.ROCK: (150, 150, 150),            # 회색
            HarvestableType.WATER: (100, 150, 255),           # 파란색
            HarvestableType.CARCASS: (200, 50, 50),           # 어두운 빨강
            HarvestableType.COOKING_POT: (255, 200, 0)        # 주황색
        }
        return colors.get(self.object_type, (255, 255, 255))


class HarvestableGenerator:
    """채집 오브젝트 생성기"""

    @staticmethod
    def generate_for_floor(floor_number: int, count: int = 5) -> List[HarvestableObject]:
        """
        층별 채집 오브젝트 생성

        Args:
            floor_number: 던전 층
            count: 생성할 개수

        Returns:
            채집 오브젝트 리스트
        """
        objects = []

        # 층에 따른 타입 가중치
        if floor_number <= 3:
            # 초반: 베리, 허브, 나무 위주
            types_weights = [
                (HarvestableType.BERRY_BUSH, 30),
                (HarvestableType.HERB_PLANT, 25),
                (HarvestableType.TREE, 20),
                (HarvestableType.MUSHROOM_PATCH, 15),
                (HarvestableType.WATER, 10),
            ]
        elif floor_number <= 7:
            # 중반: 다양한 타입
            types_weights = [
                (HarvestableType.MUSHROOM_PATCH, 25),
                (HarvestableType.HERB_PLANT, 20),
                (HarvestableType.WATER, 20),
                (HarvestableType.CARCASS, 15),
                (HarvestableType.BERRY_BUSH, 10),
                (HarvestableType.TREE, 10),
            ]
        else:
            # 후반: 고급 재료 위주
            types_weights = [
                (HarvestableType.CARCASS, 30),
                (HarvestableType.MUSHROOM_PATCH, 25),
                (HarvestableType.WATER, 20),
                (HarvestableType.ROCK, 15),
                (HarvestableType.HERB_PLANT, 10),
            ]

        # 가중치 기반 랜덤 선택
        types = [t for t, w in types_weights]
        weights = [w for t, w in types_weights]

        for _ in range(count):
            obj_type = random.choices(types, weights=weights)[0]
            # 위치는 나중에 던전 생성 시 배치
            obj = HarvestableObject(
                object_type=obj_type,
                x=0,
                y=0
            )
            objects.append(obj)

        return objects
