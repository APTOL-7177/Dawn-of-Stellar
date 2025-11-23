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
    PREPARED_DISH = "prepared_dish" # 조리된 음식 (재료로 사용 시)
    CONSTRUCTION = "construction"   # 건설 자재 (나무, 돌, 철 등)
    ALCHEMY = "alchemy"             # 연금술 재료 (포션 제작용)
    EXPLOSIVE = "explosive"         # 폭발물 재료 (폭탄 제작용)

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
            IngredientCategory.FILLER: "필러",
            IngredientCategory.PREPARED_DISH: "요리",
            IngredientCategory.CONSTRUCTION: "건설 자재",
            IngredientCategory.ALCHEMY: "연금술 재료",
            IngredientCategory.EXPLOSIVE: "폭발물 재료"
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
        data = {
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
            "raw_mp_restore": self.raw_mp_restore,
            # Item 클래스 속성 추가
            "max_durability": self.max_durability,
            "current_durability": self.current_durability
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ingredient":
        """딕셔너리에서 복원"""
        ing = cls(
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
        # Item 속성 복원
        ing.max_durability = data.get("max_durability", 100)
        ing.current_durability = data.get("current_durability", 100)
        return ing


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

        # === 곡물 ===
        "flour": Ingredient(
            item_id="flour",
            name="밀가루",
            description="곱게 빻은 밀가루. 반죽의 주재료.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=5,
            category=IngredientCategory.GRAIN,
            food_value=1.0,
            spoil_time=0,
            edible_raw=False
        ),

        "rice": Ingredient(
            item_id="rice",
            name="쌀",
            description="도정한 쌀. 밥을 지을 수 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=5,
            category=IngredientCategory.GRAIN,
            food_value=1.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 유제품 ===
        "milk": Ingredient(
            item_id="milk",
            name="우유",
            description="신선한 우유.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=10,
            category=IngredientCategory.DAIRY,
            food_value=1.0,
            spoil_time=50,
            edible_raw=True,
            raw_hp_restore=5
        ),

        # === 채소 추가 ===
        "tomato": Ingredient(
            item_id="tomato",
            name="토마토",
            description="잘 익은 토마토.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=5,
            category=IngredientCategory.VEGETABLE,
            food_value=1.0,
            spoil_time=100,
            edible_raw=True,
            raw_hp_restore=5
        ),

        "onion": Ingredient(
            item_id="onion",
            name="양파",
            description="매운 맛이 나는 양파.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=5,
            category=IngredientCategory.VEGETABLE,
            food_value=1.0,
            spoil_time=150,
            edible_raw=True,
            raw_hp_restore=2
        ),

        "tea_leaf": Ingredient(
            item_id="tea_leaf",
            name="찻잎",
            description="향긋한 찻잎.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.1,
            sell_price=15,
            category=IngredientCategory.VEGETABLE,
            food_value=0.5,
            spoil_time=0,
            edible_raw=False
        ),

        "ginger": Ingredient(
            item_id="ginger",
            name="생강",
            description="알싸한 맛의 생강.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.1,
            sell_price=15,
            category=IngredientCategory.SPICE,
            food_value=0.5,
            spoil_time=0,
            edible_raw=False
        ),

        # === 달걀 ===
        "egg": Ingredient(
            item_id="egg",
            name="달걀",
            description="신선한 달걀.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=5,
            category=IngredientCategory.EGG,
            food_value=1.0,
            spoil_time=80,
            edible_raw=True,
            raw_hp_restore=5
        ),

        # === 조미료 ===
        "salt": Ingredient(
            item_id="salt",
            name="소금",
            description="짠맛을 내는 소금.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=5,
            category=IngredientCategory.SPICE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "sugar": Ingredient(
            item_id="sugar",
            name="설탕",
            description="단맛을 내는 설탕.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=5,
            category=IngredientCategory.SWEETENER,
            food_value=0.5,
            spoil_time=0,
            edible_raw=True,
            raw_hp_restore=2
        ),

        # === 해산물 ===
        "shellfish": Ingredient(
            item_id="shellfish",
            name="조개",
            description="단단한 껍질의 조개.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.3,
            sell_price=10,
            category=IngredientCategory.FISH,
            food_value=1.0,
            spoil_time=60,
            edible_raw=False
        ),

        # === 물 ===
        "water": Ingredient(
            item_id="water",
            name="물",
            description="깨끗한 물.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=1,
            category=IngredientCategory.FILLER,
            food_value=0.5,
            spoil_time=0,
            edible_raw=True,
            raw_hp_restore=0,
            raw_mp_restore=5
        ),

        # === 희귀 재료 (Rare Ingredients) ===
        "golden_apple": Ingredient(
            item_id="golden_apple",
            name="황금 사과",
            description="황금빛으로 빛나는 사과. 강력한 마력이 느껴진다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.LEGENDARY,
            weight=0.5,
            sell_price=100,
            category=IngredientCategory.FRUIT,
            food_value=5.0,
            spoil_time=0, # 썩지 않음
            edible_raw=True,
            raw_hp_restore=100,
            raw_mp_restore=100
        ),

        "truffle": Ingredient(
            item_id="truffle",
            name="송로버섯",
            description="땅속의 다이아몬드라 불리는 버섯.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.2,
            sell_price=80,
            category=IngredientCategory.MUSHROOM,
            food_value=3.0,
            spoil_time=100,
            edible_raw=True,
            raw_hp_restore=20
        ),

        "star_fruit": Ingredient(
            item_id="star_fruit",
            name="별모양 과일",
            description="별을 닮은 신비한 과일.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.3,
            sell_price=40,
            category=IngredientCategory.FRUIT,
            food_value=2.0,
            spoil_time=80,
            edible_raw=True,
            raw_mp_restore=50
        ),

        "mandrake": Ingredient(
            item_id="mandrake",
            name="만드라고라",
            description="비명을 지르는 뿌리 식물. 약효가 뛰어나다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.5,
            sell_price=60,
            category=IngredientCategory.VEGETABLE,
            food_value=2.0,
            spoil_time=0,
            edible_raw=False # 기절함
        ),

        "slime_jelly": Ingredient(
            item_id="slime_jelly",
            name="슬라임 젤리",
            description="슬라임의 체액. 쫄깃하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=5,
            category=IngredientCategory.MEAT, # 고기 취급?
            food_value=0.5,
            spoil_time=0,
            edible_raw=True,
            raw_hp_restore=5
        ),

        "dragon_scale": Ingredient(
            item_id="dragon_scale",
            name="용의 비늘",
            description="드래곤의 단단한 비늘. 갈아서 약재로 쓴다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.LEGENDARY,
            weight=1.0,
            sell_price=200,
            category=IngredientCategory.SPICE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "phoenix_feather": Ingredient(
            item_id="phoenix_feather",
            name="불사조의 깃털",
            description="영원히 타오르는 깃털.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.LEGENDARY,
            weight=0.1,
            sell_price=300,
            category=IngredientCategory.SPICE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 건설 자재 (Construction Materials) ===
        "wood": Ingredient(
            item_id="wood",
            name="목재",
            description="단단한 나무. 건물을 짓거나 도구를 만들 때 쓰인다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=1.0,
            sell_price=2,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "stone": Ingredient(
            item_id="stone",
            name="석재",
            description="단단한 돌. 건물의 기초가 된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=2.0,
            sell_price=2,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "iron_ore": Ingredient(
            item_id="iron_ore",
            name="철광석",
            description="제련하면 철이 되는 광석. 대장간의 필수 재료.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=3.0,
            sell_price=10,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 연금술 재료 (Alchemy Materials) ===
        "glass_vial": Ingredient(
            item_id="glass_vial",
            name="유리병",
            description="투명한 유리병. 포션을 담는 데 필수적이다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=5,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "alchemical_catalyst": Ingredient(
            item_id="alchemical_catalyst",
            name="연금술 촉매",
            description="마법적 반응을 촉진하는 분말. 슬라임에서 추출한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.1,
            sell_price=15,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "pure_water": Ingredient(
            item_id="pure_water",
            name="정제수",
            description="불순물이 제거된 깨끗한 물. 포션의 기본 용매.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=3,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=True,
            raw_hp_restore=0,
            raw_mp_restore=5
        ),

        "fire_essence": Ingredient(
            item_id="fire_essence",
            name="화염의 정수",
            description="불의 정령에서 추출한 에센스. 폭발물과 포션에 사용한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=30,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "ice_essence": Ingredient(
            item_id="ice_essence",
            name="빙항의 정수",
            description="얼음의 정령에서 추출한 에센스. 냉각 효과를 준다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=30,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "lightning_essence": Ingredient(
            item_id="lightning_essence",
            name="뇌전의 정수",
            description="번개의 정령에서 추출한 에센스. 전기 충격을 부여한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=30,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "mana_blossom": Ingredient(
            item_id="mana_blossom",
            name="마력꽃",
            description="마력이 응축된 신비한 꽃. MP 회복 포션의 핵심 재료.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=40,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=100,
            edible_raw=True,
            raw_hp_restore=0,
            raw_mp_restore=30
        ),

        # === 폭발물 재료 (Explosive Materials) ===
        "gunpowder": Ingredient(
            item_id="gunpowder",
            name="화약",
            description="검은 분말. 폭발성이 강하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.3,
            sell_price=20,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "metal_scrap": Ingredient(
            item_id="metal_scrap",
            name="금속 파편",
            description="부서진 금속 조각. 폭탄 케이싱을 만드는 데 사용한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=5,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "explosive_crystal": Ingredient(
            item_id="explosive_crystal",
            name="폭발 결정",
            description="불안정한 에너지를 품은 결정. 강력한 폭발력을 지녔다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.2,
            sell_price=50,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "fuse": Ingredient(
            item_id="fuse",
            name="도화선",
            description="천천히 타는 심지. 폭탄에 불을 붙이는 데 사용한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=3,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "bomb_casing": Ingredient(
            item_id="bomb_casing",
            name="폭탄 케이싱",
            description="금속으로 만든 폭탄 외피. 내부에 화약을 넣을 수 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=10,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 광물 자원 (Mineral Resources) ===
        "copper_ore": Ingredient(
            item_id="copper_ore",
            name="구리 광석",
            description="구리가 함유된 광석. 제련하면 구리가 된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=2.0,
            sell_price=8,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "silver_ore": Ingredient(
            item_id="silver_ore",
            name="은 광석",
            description="은이 함유된 광석. 귀금속 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=2.5,
            sell_price=25,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "gold_ore": Ingredient(
            item_id="gold_ore",
            name="금 광석",
            description="금이 함유된 광석. 매우 귀하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=3.0,
            sell_price=100,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "mithril_ore": Ingredient(
            item_id="mithril_ore",
            name="미스릴 광석",
            description="전설의 금속 미스릴이 담긴 광석. 가볍고 강하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=1.5,
            sell_price=200,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "obsidian": Ingredient(
            item_id="obsidian",
            name="흑요석",
            description="날카롭고 단단한 화산암. 무기 제작에 탁월하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=2.0,
            sell_price=30,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "crystal_shard": Ingredient(
            item_id="crystal_shard",
            name="수정 파편",
            description="투명하게 빛나는 수정. 마법 물품 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.3,
            sell_price=50,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 몬스터 부위 (Monster Parts) ===
        "ghost_essence": Ingredient(
            item_id="ghost_essence",
            name="유령의 정수",
            description="유령에서 추출한 에테르 정수. 투명화 포션에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=40,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "golem_core": Ingredient(
            item_id="golem_core",
            name="골렘의 핵",
            description="골렘의 동력원. 강력한 마법 에너지를 담고 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=5.0,
            sell_price=150,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "demon_horn": Ingredient(
            item_id="demon_horn",
            name="악마의 뿔",
            description="악마의 뿔. 저주받은 아이템 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=1.0,
            sell_price=80,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "vampire_fang": Ingredient(
            item_id="vampire_fang",
            name="흡혈귀의 송곳니",
            description="뾰족한 송곳니. 생명력 흡수 효과를 부여한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.2,
            sell_price=120,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "dragon_bone": Ingredient(
            item_id="dragon_bone",
            name="용의 뼈",
            description="드래곤의 뼈. 강력한 무기와 방어구 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.LEGENDARY,
            weight=8.0,
            sell_price=500,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 희귀 식물 (Rare Plants) ===
        "moonflower": Ingredient(
            item_id="moonflower",
            name="달빛 꽃",
            description="달빛 아래서만 피는 신비한 꽃. 강력한 마법 효과를 지닌다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=60,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=50,
            edible_raw=False
        ),

        "sunblossom": Ingredient(
            item_id="sunblossom",
            name="태양 꽃",
            description="태양의 기운을 머금은 꽃. 회복 효과가 탁월하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=60,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=50,
            edible_raw=True,
            raw_hp_restore=30
        ),

        "ancient_root": Ingredient(
            item_id="ancient_root",
            name="고대의 뿌리",
            description="수백 년 된 나무의 뿌리. 생명력이 응축되어 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.5,
            sell_price=100,
            category=IngredientCategory.VEGETABLE,
            food_value=3.0,
            spoil_time=0,
            edible_raw=False
        ),

        "void_lotus": Ingredient(
            item_id="void_lotus",
            name="공허의 연꽃",
            description="어둠 속에서 자라는 연꽃. 어둠의 힘을 담고 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.2,
            sell_price=150,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 추가 원소 정수 (Elemental Essences) ===
        "earth_essence": Ingredient(
            item_id="earth_essence",
            name="대지의 정수",
            description="대지 정령에서 추출한 에센스. 방어 효과를 부여한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.1,
            sell_price=30,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "wind_essence": Ingredient(
            item_id="wind_essence",
            name="바람의 정수",
            description="바람 정령에서 추출한 에센스. 속도 증가 효과를 부여한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.RARE,
            weight=0.05,
            sell_price=30,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "light_essence": Ingredient(
            item_id="light_essence",
            name="빛의 정수",
            description="빛의 정령에서 추출한 에센스. 정화와 회복 효과를 준다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.05,
            sell_price=80,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "dark_essence": Ingredient(
            item_id="dark_essence",
            name="어둠의 정수",
            description="어둠의 정령에서 추출한 에센스. 저주와 약화 효과를 부여한다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.05,
            sell_price=80,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 제작 중간재 (Crafting Intermediates) ===
        "oil": Ingredient(
            item_id="oil",
            name="기름",
            description="식물성 기름. 연료나 용매로 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=5,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "wax": Ingredient(
            item_id="wax",
            name="밀랍",
            description="벌집에서 얻은 밀랍. 봉인과 코팅에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.3,
            sell_price=8,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "resin": Ingredient(
            item_id="resin",
            name="수지",
            description="나무에서 나온 끈적한 액체. 접착과 코팅에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.3,
            sell_price=5,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "charcoal": Ingredient(
            item_id="charcoal",
            name="목탄",
            description="나무를 탄화시켜 만든 연료. 제련과 화약 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.2,
            sell_price=3,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "sulfur": Ingredient(
            item_id="sulfur",
            name="유황",
            description="노란 광물. 강력한 폭발물 제작에 필수적이다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.UNCOMMON,
            weight=0.5,
            sell_price=15,
            category=IngredientCategory.EXPLOSIVE,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 희귀 재료 (Rare Materials) ===
        "stardust": Ingredient(
            item_id="stardust",
            name="별가루",
            description="하늘에서 떨어진 별의 가루. 기적의 물약을 만들 수 있다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.LEGENDARY,
            weight=0.01,
            sell_price=500,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "philosophers_stone_fragment": Ingredient(
            item_id="philosophers_stone_fragment",
            name="현자의 돌 파편",
            description="전설의 현자의 돌 파편. 물질 변환의 힘을 지녔다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.LEGENDARY,
            weight=0.1,
            sell_price=1000,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "ether": Ingredient(
            item_id="ether",
            name="에테르",
            description="순수한 마법 에너지가 결정화된 물질.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=0.1,
            sell_price=100,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "cursed_relic": Ingredient(
            item_id="cursed_relic",
            name="저주받은 유물",
            description="불길한 기운이 감도는 고대 유물. 위험하지만 강력하다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.EPIC,
            weight=1.0,
            sell_price=150,
            category=IngredientCategory.ALCHEMY,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        # === 동물 부산물 (Animal Byproducts) ===
        "leather": Ingredient(
            item_id="leather",
            name="가죽",
            description="동물 가죽. 방어구 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.5,
            sell_price=10,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
        ),

        "sinew": Ingredient(
            item_id="sinew",
            name="힘줄",
            description="동물의 힘줄. 활시위나 봉합에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.1,
            sell_price=5,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=100,
            edible_raw=False
        ),

        "bone": Ingredient(
            item_id="bone",
            name="뼈",
            description="동물의 뼈. 도구나 장식품 제작에 사용된다.",
            item_type=ItemType.MATERIAL,
            rarity=ItemRarity.COMMON,
            weight=0.3,
            sell_price=3,
            category=IngredientCategory.CONSTRUCTION,
            food_value=0.0,
            spoil_time=0,
            edible_raw=False
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
