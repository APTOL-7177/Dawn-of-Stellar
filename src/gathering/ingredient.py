"""
재료 시스템

채집 가능한 재료 아이템
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from src.equipment.item_system import Item, ItemType, ItemRarity


class IngredientCategory(Enum):
    """재료 카테고리"""
    MEAT = "meat"           # 고기
    VEGETABLE = "vegetable" # 채소
    FRUIT = "fruit"         # 과일
    MUSHROOM = "mushroom"   # 버섯
    FISH = "fish"           # 생선
    EGG = "egg"             # 달걀
    DAIRY = "dairy"         # 유제품 (우유, 치즈 등)
    GRAIN = "grain"         # 곡물 (밀, 쌀 등)
    SPICE = "spice"         # 향신료
    SWEETENER = "sweetener" # 감미료 (꿀, 설탕 등)
    FILLER = "filler"       # 필러 (나뭇가지, 얼음 등)

    @property
    def display_name(self) -> str:
        """표시 이름"""
        names = {
            IngredientCategory.MEAT: "고기",
            IngredientCategory.VEGETABLE: "채소",
            IngredientCategory.FRUIT: "과일",
            IngredientCategory.MUSHROOM: "버섯",
            IngredientCategory.FISH: "생선",
            IngredientCategory.EGG: "달걀",
            IngredientCategory.DAIRY: "유제품",
            IngredientCategory.GRAIN: "곡물",
            IngredientCategory.SPICE: "향신료",
            IngredientCategory.SWEETENER: "감미료",
            IngredientCategory.FILLER: "필러"
        }
        return names.get(self, "???")


@dataclass
class Ingredient(Item):
    """
    재료 아이템

    돈스타브 스타일:
    - 카테고리: 고기, 채소 등
    - 가치(value): 레시피 계산에 사용
    - 신선도: 시간에 따라 감소 (선택적)
    """
    category: IngredientCategory = IngredientCategory.FILLER
    food_value: float = 1.0  # 요리 가치 (레시피 계산용)

    # 신선도 (0.0 ~ 1.0)
    freshness: float = 1.0
    spoil_time: int = 0  # 부패 시간 (턴 단위, 0 = 부패하지 않음)

    # 생으로 먹을 수 있는지
    edible_raw: bool = False
    raw_hp_restore: int = 0
    raw_mp_restore: int = 0

    def spoil(self, turns: int = 1):
        """
        부패 진행

        Args:
            turns: 경과 턴 수
        """
        if self.spoil_time > 0:
            self.freshness = max(0.0, self.freshness - (turns / self.spoil_time))

    def is_spoiled(self) -> bool:
        """부패 여부"""
        return self.freshness <= 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "item_type": self.item_type.value,
            "rarity": self.rarity.value,
            "weight": self.weight,
            "sell_price": self.sell_price,
            "category": self.category.value,
            "food_value": self.food_value,
            "freshness": self.freshness,
            "spoil_time": self.spoil_time,
            "edible_raw": self.edible_raw,
            "raw_hp_restore": self.raw_hp_restore,
            "raw_mp_restore": self.raw_mp_restore
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ingredient":
        """딕셔너리에서 복원"""
        return cls(
            item_id=data["item_id"],
            name=data["name"],
            description=data["description"],
            item_type=ItemType(data.get("item_type", "material")),
            rarity=ItemRarity(data.get("rarity", "common")),
            weight=data.get("weight", 0.5),
            sell_price=data.get("sell_price", 10),
            category=IngredientCategory(data["category"]),
            food_value=data.get("food_value", 1.0),
            freshness=data.get("freshness", 1.0),
            spoil_time=data.get("spoil_time", 0),
            edible_raw=data.get("edible_raw", False),
            raw_hp_restore=data.get("raw_hp_restore", 0),
            raw_mp_restore=data.get("raw_mp_restore", 0)
        )


class IngredientDatabase:
    """재료 데이터베이스"""

    # 재료 정의
    INGREDIENTS = {
        # === 고기 ===
        "monster_meat": Ingredient(
            item_id="monster_meat",
            name="몬스터 고기",
            description="몬스터에게서 얻은 고기. 날것으로 먹으면 위험하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=5,
            category=IngredientCategory.MEAT,
            food_value=1.0,
            spoil_time=100,
            edible_raw=True,
            raw_hp_restore=5,
            raw_mp_restore=0
        ),

        "beast_meat": Ingredient(
            item_id="beast_meat",
            name="야수 고기",
            description="야수에게서 얻은 질 좋은 고기.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.8,
            sell_price=15,
            category=IngredientCategory.MEAT,
            food_value=2.0,
            spoil_time=80,
            edible_raw=True,
            raw_hp_restore=10,
            raw_mp_restore=0
        ),

        "dragon_meat": Ingredient(
            item_id="dragon_meat",
            name="드래곤 고기",
            description="드래곤의 고기. 마력이 깃들어 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=1.2,
            sell_price=50,
            category=IngredientCategory.MEAT,
            food_value=3.0,
            spoil_time=120,
            edible_raw=True,
            raw_hp_restore=20,
            raw_mp_restore=10
        ),

        # === 채소 ===
        "carrot": Ingredient(
            item_id="carrot",
            name="당근",
            description="신선한 당근.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=3,
            category=IngredientCategory.VEGETABLE,
            food_value=1.0,
            spoil_time=150,
            edible_raw=True,
            raw_hp_restore=3,
            raw_mp_restore=0
        ),

        "potato": Ingredient(
            item_id="potato",
            name="감자",
            description="평범한 감자.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.3,
            sell_price=3,
            category=IngredientCategory.VEGETABLE,
            food_value=1.0,
            spoil_time=200,
            edible_raw=True,
            raw_hp_restore=5,
            raw_mp_restore=0
        ),

        "magic_herb": Ingredient(
            item_id="magic_herb",
            name="마법 허브",
            description="마력이 담긴 허브. 요리에 넣으면 MP 회복 효과가 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.1,
            sell_price=20,
            category=IngredientCategory.VEGETABLE,
            food_value=1.5,
            spoil_time=100,
            edible_raw=True,
            raw_hp_restore=0,
            raw_mp_restore=10
        ),

        # === 과일 ===
        "berry": Ingredient(
            item_id="berry",
            name="베리",
            description="달콤한 베리.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=5,
            category=IngredientCategory.FRUIT,
            food_value=0.5,
            spoil_time=80,
            edible_raw=True,
            raw_hp_restore=5,
            raw_mp_restore=0
        ),

        "apple": Ingredient(
            item_id="apple",
            name="사과",
            description="빨갛고 아삭한 사과.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=5,
            category=IngredientCategory.FRUIT,
            food_value=1.0,
            spoil_time=120,
            edible_raw=True,
            raw_hp_restore=8,
            raw_mp_restore=0
        ),

        # === 버섯 ===
        "red_mushroom": Ingredient(
            item_id="red_mushroom",
            name="붉은 버섯",
            description="독이 있어 보이는 붉은 버섯.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=10,
            category=IngredientCategory.MUSHROOM,
            food_value=0.5,
            spoil_time=200,
            edible_raw=False,  # 날것 먹으면 위험
            raw_hp_restore=-10,
            raw_mp_restore=0
        ),

        "blue_mushroom": Ingredient(
            item_id="blue_mushroom",
            name="푸른 버섯",
            description="마력이 담긴 푸른 버섯.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.1,
            sell_price=15,
            category=IngredientCategory.MUSHROOM,
            food_value=1.0,
            spoil_time=200,
            edible_raw=True,
            raw_hp_restore=0,
            raw_mp_restore=15
        ),

        # === 생선 ===
        "fish": Ingredient(
            item_id="fish",
            name="물고기",
            description="신선한 물고기.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=10,
            category=IngredientCategory.FISH,
            food_value=1.0,
            spoil_time=60,
            edible_raw=True,
            raw_hp_restore=8,
            raw_mp_restore=0
        ),

        # === 향신료 ===
        "spice": Ingredient(
            item_id="spice",
            name="향신료",
            description="요리의 풍미를 높여주는 향신료.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.05,
            sell_price=20,
            category=IngredientCategory.SPICE,
            food_value=0.5,
            spoil_time=0,  # 부패하지 않음
            edible_raw=False,
            raw_hp_restore=0,
            raw_mp_restore=0
        ),

        # === 감미료 ===
        "honey": Ingredient(
            item_id="honey",
            name="꿀",
            description="달콤한 꿀.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.3,
            sell_price=15,
            category=IngredientCategory.SWEETENER,
            food_value=1.0,
            spoil_time=0,  # 부패하지 않음
            edible_raw=True,
            raw_hp_restore=10,
            raw_mp_restore=0
        ),

        # === 필러 (요리 실패 방지용) ===
        "ice": Ingredient(
            item_id="ice",
            name="얼음",
            description="차가운 얼음. 요리 재료로 쓸 수 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=2,
            category=IngredientCategory.FILLER,
            food_value=0.5,
            spoil_time=50,
            edible_raw=True,
            raw_hp_restore=0,
            raw_mp_restore=5
        ),

        "stick": Ingredient(
            item_id="stick",
            name="나뭇가지",
            description="마른 나뭇가지. 연료나 요리 재료로 쓸 수 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=1,
            category=IngredientCategory.FILLER,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False,
            raw_hp_restore=0,
            raw_mp_restore=0
        ),
    }

    @classmethod
    def get_ingredient(cls, ingredient_id: str) -> Optional[Ingredient]:
        """재료 가져오기"""
        template = cls.INGREDIENTS.get(ingredient_id)
        if template:
            # 복사본 반환 (신선도 등이 개별적으로 관리되도록)
            return Ingredient(
                item_id=template.item_id,
                name=template.name,
                description=template.description,
                item_type=ItemType.MATERIAL,
                rarity=template.rarity,
                weight=template.weight,
                sell_price=template.sell_price,
                category=template.category,
                food_value=template.food_value,
                freshness=template.freshness,
                spoil_time=template.spoil_time,
                edible_raw=template.edible_raw,
                raw_hp_restore=template.raw_hp_restore,
                raw_mp_restore=template.raw_mp_restore
            )
        return None

    @classmethod
    def get_all_ingredient_ids(cls) -> list:
        """모든 재료 ID 목록"""
        return list(cls.INGREDIENTS.keys())
