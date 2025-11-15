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

            # === 실패 요리 (폴백) ===

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
