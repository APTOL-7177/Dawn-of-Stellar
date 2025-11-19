"""
요리 레시피 시스템 (돈스타브 스타일)

재료 조합 → 요리 결과 매칭
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum

from src.gathering.ingredient import Ingredient, IngredientCategory


class RecipePriority(Enum):
    """레시피 우선순위 (높을수록 우선)"""
    VERY_HIGH = 100  # 특수 요리
    HIGH = 75        # 고급 요리
    MEDIUM = 50      # 일반 요리
    LOW = 25         # 기본 요리
    FALLBACK = 0     # 폴백 (실패 요리)


@dataclass
class RecipeCondition:
    """레시피 조건"""
    # 카테고리별 최소 요구량
    min_category: Dict[IngredientCategory, float] = field(default_factory=dict)

    # 카테고리별 최대 허용량 (초과하면 레시피 실패)
    max_category: Dict[IngredientCategory, float] = field(default_factory=dict)

    # 특정 재료 필수
    required_ingredients: List[str] = field(default_factory=list)

    # 특정 재료 금지
    banned_ingredients: List[str] = field(default_factory=list)

    # 최소 총 food_value
    min_total_value: float = 0.0

    # 최대 총 food_value
    max_total_value: float = 999.0

    # 커스텀 조건 함수
    custom_check: Optional[Callable[[List[Ingredient]], bool]] = None

    def matches(self, ingredients: List[Ingredient]) -> bool:
        """
        재료가 조건을 만족하는지 확인

        Args:
            ingredients: 재료 리스트 (최대 4개)

        Returns:
            조건 만족 여부
        """
        # 빈 재료는 무시
        ingredients = [ing for ing in ingredients if ing is not None]

        if not ingredients:
            return False

        # 카테고리별 집계
        category_values = {}
        ingredient_ids = set()
        total_value = 0.0

        for ing in ingredients:
            category_values[ing.category] = category_values.get(ing.category, 0.0) + ing.food_value
            ingredient_ids.add(ing.item_id)
            total_value += ing.food_value

        # 최소 카테고리 요구량 확인
        for category, min_val in self.min_category.items():
            if category_values.get(category, 0.0) < min_val:
                return False

        # 최대 카테고리 허용량 확인
        for category, max_val in self.max_category.items():
            if category_values.get(category, 0.0) > max_val:
                return False

        # 필수 재료 확인
        for required_id in self.required_ingredients:
            if required_id not in ingredient_ids:
                return False

        # 금지 재료 확인
        for banned_id in self.banned_ingredients:
            if banned_id in ingredient_ids:
                return False

        # 총 가치 확인
        if total_value < self.min_total_value or total_value > self.max_total_value:
            return False

        # 커스텀 조건
        if self.custom_check and not self.custom_check(ingredients):
            return False

        return True


@dataclass
class CookedFood:
    """요리된 음식"""
    name: str
    description: str

    # 효과
    hp_restore: int = 0
    mp_restore: int = 0
    max_hp_bonus: int = 0  # 일시적 최대 HP 증가
    max_mp_bonus: int = 0  # 일시적 최대 MP 증가

    # 버프 (턴 수)
    buff_duration: int = 0
    buff_type: Optional[str] = None  # "attack", "defense", "speed" 등

    # 디버프 (실패 요리)
    is_poison: bool = False
    poison_damage: int = 0

    # 신선도 (요리된 음식도 부패할 수 있음)
    spoil_time: int = 200

    # 인벤토리 관련
    weight: float = 0.5  # 무게 (kg) - 요리는 일반적으로 가벼움

    def __repr__(self) -> str:
        return f"{self.name} (HP+{self.hp_restore}, MP+{self.mp_restore})"


@dataclass
class Recipe:
    """
    요리 레시피 (돈스타브 스타일)

    조건을 만족하면 특정 요리가 나옴
    """
    recipe_id: str
    result: CookedFood
    condition: RecipeCondition
    priority: RecipePriority = RecipePriority.MEDIUM

    def can_cook(self, ingredients: List[Ingredient]) -> bool:
        """재료로 요리 가능한지"""
        return self.condition.matches(ingredients)


class RecipeDatabase:
    """레시피 데이터베이스"""

    RECIPES = []

    @classmethod
    def initialize(cls):
        """레시피 초기화"""
        if cls.RECIPES:
            return  # 이미 초기화됨

        cls.RECIPES = [
            # === 고급 요리 (우선순위 높음) ===

            # 드래곤 스테이크 (드래곤 고기 필수)
            Recipe(
                recipe_id="dragon_steak",
                result=CookedFood(
                    name="드래곤 스테이크",
                    description="드래곤 고기로 만든 최고급 스테이크. 강력한 힘을 부여한다.",
                    hp_restore=80,
                    mp_restore=50,
                    max_hp_bonus=30,
                    buff_duration=10,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dragon_meat"],
                    min_total_value=3.0
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 허브 스튜 (마법 허브 필수)
            Recipe(
                recipe_id="herb_stew",
                result=CookedFood(
                    name="허브 스튜",
                    description="마법 허브가 들어간 스튜. 마력을 회복시킨다.",
                    hp_restore=40,
                    mp_restore=60,
                    max_mp_bonus=20,
                    buff_duration=5,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 생선 구이 (생선 필수)
            Recipe(
                recipe_id="grilled_fish",
                result=CookedFood(
                    name="생선 구이",
                    description="신선한 생선을 구운 요리.",
                    hp_restore=50,
                    mp_restore=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FISH: 1.0},
                    max_category={IngredientCategory.MEAT: 0.0}  # 고기 들어가면 안됨
                ),
                priority=RecipePriority.HIGH
            ),

            # === 일반 요리 ===

            # 미트볼 (고기 2 + 아무거나 2)
            Recipe(
                recipe_id="meatballs",
                result=CookedFood(
                    name="미트볼",
                    description="고기로 만든 미트볼.",
                    hp_restore=60,
                    mp_restore=0
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0},
                    min_total_value=3.0
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 야채 스튜 (채소 3개 이상)
            Recipe(
                recipe_id="vegetable_stew",
                result=CookedFood(
                    name="야채 스튜",
                    description="다양한 채소로 만든 스튜.",
                    hp_restore=40,
                    mp_restore=20
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 3.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 과일 샐러드 (과일 3개 이상)
            Recipe(
                recipe_id="fruit_salad",
                result=CookedFood(
                    name="과일 샐러드",
                    description="신선한 과일로 만든 샐러드.",
                    hp_restore=30,
                    mp_restore=30
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 3.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 버섯 수프 (버섯 2개 이상)
            Recipe(
                recipe_id="mushroom_soup",
                result=CookedFood(
                    name="버섯 수프",
                    description="버섯으로 만든 수프. 마력이 느껴진다.",
                    hp_restore=20,
                    mp_restore=40
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MUSHROOM: 2.0},
                    max_category={IngredientCategory.MEAT: 1.0}  # 고기 1개까지만
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 꿀 요리 (꿀 필수)
            Recipe(
                recipe_id="honey_ham",
                result=CookedFood(
                    name="꿀 구이",
                    description="꿀로 간을 한 구이 요리.",
                    hp_restore=70,
                    mp_restore=10,
                    max_hp_bonus=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 기본 요리 ===

            # 구운 고기 (고기만)
            Recipe(
                recipe_id="cooked_meat",
                result=CookedFood(
                    name="구운 고기",
                    description="간단하게 구운 고기.",
                    hp_restore=40,
                    mp_restore=0
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 1.0},
                    max_total_value=4.0
                ),
                priority=RecipePriority.LOW
            ),

            # 구운 채소 (채소만)
            Recipe(
                recipe_id="roasted_vegetables",
                result=CookedFood(
                    name="구운 채소",
                    description="간단하게 구운 채소.",
                    hp_restore=30,
                    mp_restore=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.LOW
            ),

            # === HP 회복 특화 요리 ===

            # 스테이크 (고기 2개 이상)
            Recipe(
                recipe_id="steak",
                result=CookedFood(
                    name="스테이크",
                    description="고기로 만든 두툼한 스테이크. HP를 크게 회복시킨다.",
                    hp_restore=90,
                    mp_restore=0,
                    buff_duration=8,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0},
                    max_category={IngredientCategory.MUSHROOM: 0.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 삼계탕 (고기 2 + 채소)
            Recipe(
                recipe_id="samgyetang",
                result=CookedFood(
                    name="삼계탕",
                    description="영양만점 삼계탕. 최대 HP를 증가시킨다.",
                    hp_restore=100,
                    mp_restore=30,
                    max_hp_bonus=40,
                    buff_duration=12
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 1.0},
                    min_total_value=3.0
                ),
                priority=RecipePriority.HIGH
            ),

            # 갈비찜 (고기 3개)
            Recipe(
                recipe_id="galbi_jjim",
                result=CookedFood(
                    name="갈비찜",
                    description="부드러운 갈비찜. HP 회복과 방어력 증가.",
                    hp_restore=110,
                    mp_restore=0,
                    buff_duration=10,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 3.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # === MP 회복 특화 요리 ===

            # 마나 포션 (마법 허브 2개)
            Recipe(
                recipe_id="mana_potion_food",
                result=CookedFood(
                    name="마나 주스",
                    description="마법 허브로 만든 주스. MP를 크게 회복시킨다.",
                    hp_restore=20,
                    mp_restore=80,
                    max_mp_bonus=30,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 버섯 스튜 (버섯 3개)
            Recipe(
                recipe_id="mushroom_stew",
                result=CookedFood(
                    name="버섯 스튜",
                    description="다양한 버섯으로 만든 스튜. 마력이 솟아난다.",
                    hp_restore=30,
                    mp_restore=70,
                    buff_duration=6,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MUSHROOM: 3.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 과일 주스 (과일 3개)
            Recipe(
                recipe_id="fruit_juice",
                result=CookedFood(
                    name="과일 주스",
                    description="신선한 과일로 만든 주스. MP 회복과 최대 MP 증가.",
                    hp_restore=25,
                    mp_restore=60,
                    max_mp_bonus=25,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 3.0},
                    max_category={IngredientCategory.MEAT: 0.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 공격력 버프 특화 요리 ===

            # 불고기 (고기 2 + 향신료)
            Recipe(
                recipe_id="bulgogi",
                result=CookedFood(
                    name="불고기",
                    description="달콤한 양념의 불고기. 공격력이 크게 증가한다.",
                    hp_restore=75,
                    mp_restore=0,
                    buff_duration=12,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 바베큐 (고기 2 + 꿀)
            Recipe(
                recipe_id="barbecue",
                result=CookedFood(
                    name="바베큐",
                    description="꿀로 간을 한 바베큐. 물리 공격력과 HP 회복.",
                    hp_restore=85,
                    mp_restore=10,
                    max_hp_bonus=15,
                    buff_duration=10,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.MEAT: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # === 방어력 버프 특화 요리 ===

            # 영양탕 (고기 1 + 채소 2)
            Recipe(
                recipe_id="nutrient_soup",
                result=CookedFood(
                    name="영양탕",
                    description="다양한 재료로 끓인 영양탕. 방어력과 최대 HP 증가.",
                    hp_restore=70,
                    mp_restore=25,
                    max_hp_bonus=30,
                    buff_duration=12,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 1.0, IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 그라탕 (채소 3개)
            Recipe(
                recipe_id="gratin",
                result=CookedFood(
                    name="그라탕",
                    description="채소로 만든 그라탕. 방어력과 MP 회복.",
                    hp_restore=65,
                    mp_restore=40,
                    buff_duration=10,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 3.0},
                    max_category={IngredientCategory.MEAT: 0.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 속도 버프 특화 요리 ===

            # 에너지 드링크 (과일 2 + 마법 허브)
            Recipe(
                recipe_id="energy_drink",
                result=CookedFood(
                    name="에너지 드링크",
                    description="과일과 허브로 만든 에너지 드링크. 속도가 크게 증가한다.",
                    hp_restore=30,
                    mp_restore=40,
                    buff_duration=15,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 2.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 볶음밥 (곡물 2 + 기타)
            Recipe(
                recipe_id="fried_rice",
                result=CookedFood(
                    name="볶음밥",
                    description="재빠르게 볶은 밥. 속도 증가와 종합 회복.",
                    hp_restore=60,
                    mp_restore=30,
                    buff_duration=10,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0},
                    min_total_value=3.0
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 종합 회복 요리 ===

            # 비빔밥 (곡물 1 + 채소 2 + 고기 1)
            Recipe(
                recipe_id="bibimbap",
                result=CookedFood(
                    name="비빔밥",
                    description="다양한 재료가 들어간 비빔밥. 균형잡힌 회복.",
                    hp_restore=80,
                    mp_restore=45,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 1.0, IngredientCategory.VEGETABLE: 2.0, IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 파스타 (곡물 2 + 채소 1 + 고기 1)
            Recipe(
                recipe_id="pasta",
                result=CookedFood(
                    name="파스타",
                    description="이탈리아식 파스타. HP와 MP를 모두 회복.",
                    hp_restore=85,
                    mp_restore=50,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.VEGETABLE: 1.0, IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 라면 (곡물 2 + 채소 1)
            Recipe(
                recipe_id="ramen",
                result=CookedFood(
                    name="라면",
                    description="든든한 라면. 종합 회복과 최대 HP 증가.",
                    hp_restore=75,
                    mp_restore=35,
                    max_hp_bonus=20,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 특수 효과 요리 ===

            # 초밥 (생선 2 + 곡물 1)
            Recipe(
                recipe_id="sushi",
                result=CookedFood(
                    name="초밥",
                    description="신선한 생선으로 만든 초밥. 최대 HP/MP 증가.",
                    hp_restore=90,
                    mp_restore=55,
                    max_hp_bonus=25,
                    max_mp_bonus=25,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FISH: 2.0, IngredientCategory.GRAIN: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 꿀 케이크 (곡물 2 + 꿀)
            Recipe(
                recipe_id="honey_cake",
                result=CookedFood(
                    name="꿀 케이크",
                    description="달콤한 꿀 케이크. HP/MP 회복과 최대 HP 증가.",
                    hp_restore=60,
                    mp_restore=50,
                    max_hp_bonus=20,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 사과 파이 (과일 2 + 곡물 2)
            Recipe(
                recipe_id="apple_pie",
                result=CookedFood(
                    name="사과 파이",
                    description="달콤한 사과 파이. MP 회복 특화.",
                    hp_restore=45,
                    mp_restore=70,
                    max_mp_bonus=30,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 2.0, IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 간편 요리 ===

            # 구운 생선 (생선 1개)
            Recipe(
                recipe_id="cooked_fish",
                result=CookedFood(
                    name="구운 생선",
                    description="간단하게 구운 생선.",
                    hp_restore=45,
                    mp_restore=15
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FISH: 1.0},
                    max_total_value=2.0
                ),
                priority=RecipePriority.LOW
            ),

            # 과일 샐러드 (과일 2개)
            Recipe(
                recipe_id="fruit_salad_simple",
                result=CookedFood(
                    name="과일 샐러드",
                    description="신선한 과일 샐러드.",
                    hp_restore=35,
                    mp_restore=25
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 2.0},
                    max_total_value=3.0
                ),
                priority=RecipePriority.LOW
            ),

            # 버섯 볶음 (버섯 2개)
            Recipe(
                recipe_id="fried_mushroom",
                result=CookedFood(
                    name="버섯 볶음",
                    description="버섯을 볶은 요리. MP 회복.",
                    hp_restore=25,
                    mp_restore=45
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MUSHROOM: 2.0},
                    max_total_value=3.0
                ),
                priority=RecipePriority.LOW
            ),

            # === 더 많은 HP 회복 특화 요리 ===

            # 로스트 치킨 (고기 2 + 향신료)
            Recipe(
                recipe_id="roast_chicken",
                result=CookedFood(
                    name="로스트 치킨",
                    description="향신료를 넣어 구운 닭고기. HP를 크게 회복시킨다.",
                    hp_restore=95,
                    mp_restore=0,
                    buff_duration=8,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 포터하우스 스테이크 (고기 3 + 향신료)
            Recipe(
                recipe_id="porterhouse_steak",
                result=CookedFood(
                    name="포터하우스 스테이크",
                    description="최고급 부위로 만든 스테이크. 최고의 HP 회복.",
                    hp_restore=120,
                    mp_restore=20,
                    max_hp_bonus=35,
                    buff_duration=12,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 3.0, IngredientCategory.SPICE: 1.0},
                    min_total_value=4.0
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 영양만점 국수 (곡물 2 + 고기 1 + 채소 1)
            Recipe(
                recipe_id="nutrient_noodles",
                result=CookedFood(
                    name="영양만점 국수",
                    description="다양한 재료가 들어간 국수. HP 회복 특화.",
                    hp_restore=85,
                    mp_restore=25,
                    max_hp_bonus=25,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.MEAT: 1.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 찜닭 (고기 2 + 채소 1 + 향신료)
            Recipe(
                recipe_id="braised_chicken",
                result=CookedFood(
                    name="찜닭",
                    description="부드럽게 찐 닭고기. HP 회복과 최대 HP 증가.",
                    hp_restore=90,
                    mp_restore=15,
                    max_hp_bonus=30,
                    buff_duration=10,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # === 더 많은 MP 회복 특화 요리 ===

            # 마법사 파이 (마법 허브 + 과일 2 + 곡물 1)
            Recipe(
                recipe_id="wizard_pie",
                result=CookedFood(
                    name="마법사 파이",
                    description="마법 허브가 들어간 파이. MP를 크게 회복시킨다.",
                    hp_restore=30,
                    mp_restore=90,
                    max_mp_bonus=35,
                    buff_duration=10,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.FRUIT: 2.0, IngredientCategory.GRAIN: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 버섯 라자냐 (버섯 2 + 곡물 2)
            Recipe(
                recipe_id="mushroom_lasagna",
                result=CookedFood(
                    name="버섯 라자냐",
                    description="버섯으로 만든 라자냐. 마력이 솟아난다.",
                    hp_restore=40,
                    mp_restore=80,
                    max_mp_bonus=30,
                    buff_duration=8,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MUSHROOM: 2.0, IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 마나 케이크 (마법 허브 + 곡물 2 + 꿀)
            Recipe(
                recipe_id="mana_cake",
                result=CookedFood(
                    name="마나 케이크",
                    description="마법 허브와 꿀로 만든 케이크. MP 회복 특화.",
                    hp_restore=35,
                    mp_restore=75,
                    max_mp_bonus=40,
                    buff_duration=12,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb", "honey"],
                    min_category={IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 마법 스튜 (마법 허브 + 버섯 2)
            Recipe(
                recipe_id="magic_stew",
                result=CookedFood(
                    name="마법 스튜",
                    description="마법 허브와 버섯으로 만든 스튜. 강력한 MP 회복.",
                    hp_restore=25,
                    mp_restore=85,
                    max_mp_bonus=30,
                    buff_duration=10,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.MUSHROOM: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # === 더 많은 종합 회복 요리 ===

            # 김치찌개 (채소 2 + 고기 1 + 향신료)
            Recipe(
                recipe_id="kimchi_stew",
                result=CookedFood(
                    name="김치찌개",
                    description="매콤한 김치찌개. 종합 회복과 공격력 버프.",
                    hp_restore=75,
                    mp_restore=35,
                    buff_duration=10,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0, IngredientCategory.MEAT: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 된장찌개 (채소 2 + 고기 1)
            Recipe(
                recipe_id="doenjang_stew",
                result=CookedFood(
                    name="된장찌개",
                    description="구수한 된장찌개. 균형잡힌 회복.",
                    hp_restore=70,
                    mp_restore=40,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0, IngredientCategory.MEAT: 1.0},
                    max_category={IngredientCategory.SPICE: 0.5}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 부대찌개 (고기 1 + 채소 1 + 곡물 1)
            Recipe(
                recipe_id="budae_stew",
                result=CookedFood(
                    name="부대찌개",
                    description="다양한 재료가 들어간 부대찌개. 종합 회복.",
                    hp_restore=80,
                    mp_restore=45,
                    max_hp_bonus=15,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 1.0, IngredientCategory.VEGETABLE: 1.0, IngredientCategory.GRAIN: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 잡채 (채소 2 + 고기 1 + 향신료)
            Recipe(
                recipe_id="japchae",
                result=CookedFood(
                    name="잡채",
                    description="당면과 채소로 만든 잡채. 종합 회복과 속도 버프.",
                    hp_restore=70,
                    mp_restore=40,
                    buff_duration=12,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0, IngredientCategory.MEAT: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 해물파전 (해산물 2 + 곡물 1 + 채소 1)
            Recipe(
                recipe_id="seafood_pancake",
                result=CookedFood(
                    name="해물파전",
                    description="신선한 해산물로 만든 파전. 종합 회복.",
                    hp_restore=75,
                    mp_restore=50,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FISH: 2.0, IngredientCategory.GRAIN: 1.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 더 많은 공격력 버프 요리 ===

            # 스파이시 치킨 (고기 2 + 향신료 2)
            Recipe(
                recipe_id="spicy_chicken",
                result=CookedFood(
                    name="스파이시 치킨",
                    description="매운 양념 치킨. 공격력이 크게 증가한다.",
                    hp_restore=80,
                    mp_restore=10,
                    buff_duration=15,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.SPICE: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 스테이크 샐러드 (고기 2 + 채소 1)
            Recipe(
                recipe_id="steak_salad",
                result=CookedFood(
                    name="스테이크 샐러드",
                    description="스테이크와 채소 샐러드. 공격력 버프와 종합 회복.",
                    hp_restore=85,
                    mp_restore=30,
                    buff_duration=10,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 1.0},
                    max_category={IngredientCategory.SPICE: 0.5}
                ),
                priority=RecipePriority.HIGH
            ),

            # === 더 많은 방어력 버프 요리 ===

            # 보양탕 (고기 2 + 채소 2)
            Recipe(
                recipe_id="boyang_tang",
                result=CookedFood(
                    name="보양탕",
                    description="영양가 높은 보양탕. 방어력과 최대 HP 증가.",
                    hp_restore=95,
                    mp_restore=30,
                    max_hp_bonus=40,
                    buff_duration=15,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 2.0},
                    min_total_value=4.0
                ),
                priority=RecipePriority.HIGH
            ),

            # 영양밥 (곡물 2 + 채소 2 + 고기 1)
            Recipe(
                recipe_id="nutrient_rice",
                result=CookedFood(
                    name="영양밥",
                    description="영양가 높은 영양밥. 방어력 버프와 종합 회복.",
                    hp_restore=75,
                    mp_restore=40,
                    max_hp_bonus=25,
                    buff_duration=12,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.VEGETABLE: 2.0, IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 더 많은 속도 버프 요리 ===

            # 샐러드 볼 (채소 3 + 과일 1)
            Recipe(
                recipe_id="salad_bowl",
                result=CookedFood(
                    name="샐러드 볼",
                    description="신선한 샐러드. 속도가 크게 증가한다.",
                    hp_restore=50,
                    mp_restore=50,
                    buff_duration=18,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 3.0, IngredientCategory.FRUIT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 과일 스무디 (과일 3 + 꿀)
            Recipe(
                recipe_id="fruit_smoothie",
                result=CookedFood(
                    name="과일 스무디",
                    description="신선한 과일 스무디. 속도 버프와 MP 회복.",
                    hp_restore=35,
                    mp_restore=55,
                    max_mp_bonus=20,
                    buff_duration=15,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.FRUIT: 3.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 더 많은 특수 효과 요리 ===

            # 피쉬 앤 칩스 (생선 2 + 곡물 1 + 향신료)
            Recipe(
                recipe_id="fish_and_chips",
                result=CookedFood(
                    name="피쉬 앤 칩스",
                    description="영국식 피쉬 앤 칩스. 최대 HP/MP 증가.",
                    hp_restore=85,
                    mp_restore=55,
                    max_hp_bonus=30,
                    max_mp_bonus=25,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FISH: 2.0, IngredientCategory.GRAIN: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 영양 샌드위치 (곡물 1 + 고기 1 + 채소 1)
            Recipe(
                recipe_id="nutrient_sandwich",
                result=CookedFood(
                    name="영양 샌드위치",
                    description="다양한 재료가 들어간 샌드위치. 균형잡힌 회복.",
                    hp_restore=65,
                    mp_restore=45,
                    max_hp_bonus=20,
                    max_mp_bonus=15,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 1.0, IngredientCategory.MEAT: 1.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 디저트/음료 ===

            # 초콜릿 케이크 (곡물 2 + 꿀 + 향신료)
            Recipe(
                recipe_id="chocolate_cake",
                result=CookedFood(
                    name="초콜릿 케이크",
                    description="달콤한 초콜릿 케이크. MP 회복과 최대 MP 증가.",
                    hp_restore=50,
                    mp_restore=65,
                    max_mp_bonus=25,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 베리 케이크 (과일 2 + 곡물 2 + 꿀)
            Recipe(
                recipe_id="berry_cake",
                result=CookedFood(
                    name="베리 케이크",
                    description="신선한 베리 케이크. 종합 회복.",
                    hp_restore=55,
                    mp_restore=60,
                    max_mp_bonus=20,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.FRUIT: 2.0, IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 허브차 (마법 허브 + 채소 1)
            Recipe(
                recipe_id="herb_tea",
                result=CookedFood(
                    name="허브차",
                    description="마법 허브로 끓인 차. MP 회복과 마법 버프.",
                    hp_restore=20,
                    mp_restore=70,
                    max_mp_bonus=20,
                    buff_duration=12,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.VEGETABLE: 1.0},
                    max_total_value=3.0
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 마나 포션 요리 (마법 허브 + 과일 2)
            Recipe(
                recipe_id="mana_potion_cooked",
                result=CookedFood(
                    name="마나 포션 스튜",
                    description="마법 허브와 과일로 만든 스튜. 강력한 MP 회복.",
                    hp_restore=25,
                    mp_restore=95,
                    max_mp_bonus=35,
                    buff_duration=10,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.FRUIT: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # === 더 많은 간편 요리 ===

            # 구운 야수 고기 (야수 고기 1개)
            Recipe(
                recipe_id="cooked_beast_meat",
                result=CookedFood(
                    name="구운 야수 고기",
                    description="야수 고기를 구운 요리.",
                    hp_restore=60,
                    mp_restore=5
                ),
                condition=RecipeCondition(
                    required_ingredients=["beast_meat"],
                    max_total_value=3.0
                ),
                priority=RecipePriority.LOW
            ),

            # 생선초밥 (생선 1 + 곡물 1)
            Recipe(
                recipe_id="sashimi_rice",
                result=CookedFood(
                    name="생선초밥",
                    description="생선과 밥으로 만든 초밥.",
                    hp_restore=55,
                    mp_restore=40
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FISH: 1.0, IngredientCategory.GRAIN: 1.0},
                    max_total_value=3.0
                ),
                priority=RecipePriority.LOW
            ),

            # 채소 볶음 (채소 2)
            Recipe(
                recipe_id="stir_fried_vegetables",
                result=CookedFood(
                    name="채소 볶음",
                    description="간단하게 볶은 채소.",
                    hp_restore=40,
                    mp_restore=20
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0},
                    max_total_value=2.5
                ),
                priority=RecipePriority.LOW
            ),

            # === 추가 HP 회복 요리 ===

            # 치킨 스튜 (고기 2 + 채소 1)
            Recipe(
                recipe_id="chicken_stew",
                result=CookedFood(
                    name="치킨 스튜",
                    description="부드러운 치킨 스튜. HP 회복과 방어력 버프.",
                    hp_restore=88,
                    mp_restore=20,
                    max_hp_bonus=22,
                    buff_duration=9,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 돼지갈비 (고기 2 + 향신료)
            Recipe(
                recipe_id="pork_ribs",
                result=CookedFood(
                    name="돼지갈비",
                    description="양념 갈비. HP 회복과 공격력 버프.",
                    hp_restore=92,
                    mp_restore=5,
                    buff_duration=10,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 추가 MP 회복 요리 ===

            # 마법 파스타 (마법 허브 + 곡물 2)
            Recipe(
                recipe_id="magic_pasta",
                result=CookedFood(
                    name="마법 파스타",
                    description="마법 허브가 들어간 파스타. MP 회복 특화.",
                    hp_restore=35,
                    mp_restore=78,
                    max_mp_bonus=28,
                    buff_duration=9,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["magic_herb"],
                    min_category={IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 버섯 크림 스프 (버섯 2 + 채소 1)
            Recipe(
                recipe_id="mushroom_cream_soup",
                result=CookedFood(
                    name="버섯 크림 스프",
                    description="버섯으로 만든 크림 스프. MP 회복.",
                    hp_restore=32,
                    mp_restore=72,
                    max_mp_bonus=25,
                    buff_duration=8,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MUSHROOM: 2.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 추가 종합 회복 요리 ===

            # 떡볶이 (곡물 2 + 채소 1 + 향신료)
            Recipe(
                recipe_id="tteokbokki",
                result=CookedFood(
                    name="떡볶이",
                    description="매콤달콤한 떡볶이. 종합 회복과 속도 버프.",
                    hp_restore=72,
                    mp_restore=38,
                    buff_duration=10,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.VEGETABLE: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 쌀국수 (곡물 2 + 채소 1 + 고기 1)
            Recipe(
                recipe_id="pho",
                result=CookedFood(
                    name="쌀국수",
                    description="베트남식 쌀국수. 종합 회복.",
                    hp_restore=82,
                    mp_restore=42,
                    max_hp_bonus=18,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.VEGETABLE: 1.0, IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 마파두부 (채소 2 + 고기 1 + 향신료)
            Recipe(
                recipe_id="mapo_tofu",
                result=CookedFood(
                    name="마파두부",
                    description="매콤한 마파두부. 종합 회복과 마법 버프.",
                    hp_restore=68,
                    mp_restore=48,
                    buff_duration=10,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0, IngredientCategory.MEAT: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 탕수육 (고기 2 + 채소 1 + 향신료)
            Recipe(
                recipe_id="sweet_sour_pork",
                result=CookedFood(
                    name="탕수육",
                    description="중국식 탕수육. 종합 회복과 공격력 버프.",
                    hp_restore=88,
                    mp_restore=32,
                    buff_duration=9,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 1.0, IngredientCategory.SPICE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 추가 특수 효과 요리 ===

            # 드래곤 스튜 (드래곤 고기 + 채소 1)
            Recipe(
                recipe_id="dragon_stew",
                result=CookedFood(
                    name="드래곤 스튜",
                    description="드래곤 고기로 만든 스튜. 최고의 효과.",
                    hp_restore=105,
                    mp_restore=60,
                    max_hp_bonus=45,
                    max_mp_bonus=30,
                    buff_duration=15,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dragon_meat"],
                    min_category={IngredientCategory.VEGETABLE: 1.0},
                    min_total_value=3.5
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 골든 파이 (꿀 + 곡물 2 + 과일 1)
            Recipe(
                recipe_id="golden_pie",
                result=CookedFood(
                    name="골든 파이",
                    description="황금빛 파이. 최대 HP/MP 증가.",
                    hp_restore=62,
                    mp_restore=68,
                    max_hp_bonus=30,
                    max_mp_bonus=30,
                    buff_duration=12
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.GRAIN: 2.0, IngredientCategory.FRUIT: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 추가 간편 요리 ===

            # 베리 샐러드 (과일 2)
            Recipe(
                recipe_id="berry_salad",
                result=CookedFood(
                    name="베리 샐러드",
                    description="신선한 베리 샐러드.",
                    hp_restore=32,
                    mp_restore=28
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 2.0},
                    max_total_value=2.5
                ),
                priority=RecipePriority.LOW
            ),

            # 구운 버섯 (버섯 2)
            Recipe(
                recipe_id="grilled_mushroom",
                result=CookedFood(
                    name="구운 버섯",
                    description="간단하게 구운 버섯.",
                    hp_restore=28,
                    mp_restore=42
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.MUSHROOM: 2.0},
                    max_total_value=2.5
                ),
                priority=RecipePriority.LOW
            ),

            # 구운 당근 (채소 2)
            Recipe(
                recipe_id="roasted_carrots",
                result=CookedFood(
                    name="구운 당근",
                    description="구운 당근.",
                    hp_restore=38,
                    mp_restore=15
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.VEGETABLE: 2.0},
                    max_total_value=2.5,
                    max_category={IngredientCategory.MEAT: 0.0}
                ),
                priority=RecipePriority.LOW
            ),

            # === 디저트 추가 ===

            # 스트로베리 쇼트케이크 (과일 2 + 곡물 2)
            Recipe(
                recipe_id="strawberry_cake",
                result=CookedFood(
                    name="스트로베리 쇼트케이크",
                    description="달콤한 스트로베리 케이크. MP 회복.",
                    hp_restore=48,
                    mp_restore=62,
                    max_mp_bonus=22,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    min_category={IngredientCategory.FRUIT: 2.0, IngredientCategory.GRAIN: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 허니 토스트 (곡물 1 + 꿀)
            Recipe(
                recipe_id="honey_toast",
                result=CookedFood(
                    name="허니 토스트",
                    description="달콤한 꿀 토스트. 종합 회복.",
                    hp_restore=52,
                    mp_restore=48,
                    max_hp_bonus=15,
                    buff_duration=8
                ),
                condition=RecipeCondition(
                    required_ingredients=["honey"],
                    min_category={IngredientCategory.GRAIN: 1.0},
                    max_total_value=2.5
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 실패 요리 (독성) ===

            # 독 버섯 요리 (독 버섯 포함)
            Recipe(
                recipe_id="poison_mushroom_dish",
                result=CookedFood(
                    name="독 버섯 요리",
                    description="독성 버섯이 들어간 요리. 위험하다!",
                    hp_restore=20,
                    mp_restore=10,
                    is_poison=True,
                    poison_damage=30
                ),
                condition=RecipeCondition(
                    required_ingredients=["red_mushroom"],
                    min_category={IngredientCategory.MUSHROOM: 2.0}
                ),
                priority=RecipePriority.FALLBACK
            ),

            # 나쁜 고기 요리 (썩은 고기)
            Recipe(
                recipe_id="rotten_meat_dish",
                result=CookedFood(
                    name="썩은 고기 요리",
                    description="상한 고기로 만든 요리...",
                    hp_restore=15,
                    mp_restore=0,
                    is_poison=True,
                    poison_damage=25
                ),
                condition=RecipeCondition(
                    required_ingredients=["monster_meat"],
                    min_category={IngredientCategory.MEAT: 2.0},
                    max_total_value=2.5  # 낮은 가치 = 상한 고기
                ),
                priority=RecipePriority.FALLBACK
            ),

            # === 폴백 요리 ===

            # Wet Goop (조건 불만족)
            Recipe(
                recipe_id="wet_goop",
                result=CookedFood(
                    name="축축한 음식",
                    description="뭔가 잘못된 요리... 먹을 수는 있지만...",
                    hp_restore=10,
                    mp_restore=0,
                    is_poison=False
                ),
                condition=RecipeCondition(
                    min_total_value=0.0  # 항상 만족 (폴백)
                ),
                priority=RecipePriority.FALLBACK
            ),
        ]

        # 우선순위 순으로 정렬
        cls.RECIPES.sort(key=lambda r: r.priority.value, reverse=True)

    @classmethod
    def find_recipe(cls, ingredients: List[Ingredient]) -> Recipe:
        """
        재료로 만들 수 있는 레시피 찾기

        우선순위가 높은 레시피부터 확인하여 첫 번째 매치 반환

        Args:
            ingredients: 재료 리스트 (최대 4개)

        Returns:
            매칭된 레시피 (없으면 폴백 레시피)
        """
        cls.initialize()

        for recipe in cls.RECIPES:
            if recipe.can_cook(ingredients):
                return recipe

        # 폴백 (wet goop)
        return cls.RECIPES[-1]
