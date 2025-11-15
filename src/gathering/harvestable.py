"""
채집 가능한 오브젝트

던전에 배치되는 채집 포인트
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Tuple
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
    """
    object_type: HarvestableType
    x: int
    y: int
    harvested: bool = False

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
                ("berry", 3, 6),  # 2-4 → 3-6
            ],
            HarvestableType.MUSHROOM_PATCH: [
                ("red_mushroom", 2, 4),  # 1-2 → 2-4
                ("blue_mushroom", 1, 2),  # 0-1 → 1-2 (확률적 → 확정)
            ],
            HarvestableType.HERB_PLANT: [
                ("carrot", 2, 4),  # 1-2 → 2-4
                ("potato", 1, 3),  # 0-2 → 1-3
                ("magic_herb", 0, 2),  # 0-1 → 0-2
            ],
            HarvestableType.TREE: [
                ("stick", 2, 5),  # 1-3 → 2-5
                ("apple", 1, 3),  # 0-2 → 1-3
                ("berry", 1, 2),  # 0-1 → 1-2
            ],
            HarvestableType.ROCK: [
                ("ice", 2, 4),  # 1-2 → 2-4
            ],
            HarvestableType.WATER: [
                ("fish", 2, 5),  # 1-3 → 2-5
                ("ice", 1, 2),  # 0-1 → 1-2
            ],
            HarvestableType.CARCASS: [
                ("monster_meat", 2, 4),  # 1-2 → 2-4
                ("beast_meat", 1, 2),  # 0-1 → 1-2 (확정)
                ("dragon_meat", 0, 1),  # 추가: 희귀 드롭
            ],
            HarvestableType.COOKING_POT: [
                # 요리솥은 채집 대상이 아니라 상호작용 오브젝트
            ],
        }
        return loot_tables.get(self.object_type, [])

    def harvest(self) -> Dict[str, int]:
        """
        채집 실행

        Returns:
            획득한 재료 딕셔너리 {ingredient_id: quantity}
        """
        if self.harvested:
            return {}

        self.harvested = True
        results = {}

        for ingredient_id, min_qty, max_qty in self.loot_table:
            qty = random.randint(min_qty, max_qty)
            if qty > 0:
                results[ingredient_id] = results.get(ingredient_id, 0) + qty

        return results

    def can_harvest(self) -> bool:
        """채집 가능 여부"""
        return not self.harvested


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
