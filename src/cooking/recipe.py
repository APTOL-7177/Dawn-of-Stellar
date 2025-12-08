"""
요리 레시피 시스템 (돈스타브 스타일)

재료 조합 → 요리 결과 매칭
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum

from src.gathering.ingredient import Ingredient, IngredientCategory
from src.equipment.item_system import ItemType


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

    # 특정 재료 필수 (ID만 확인)
    required_ingredients: List[str] = field(default_factory=list)

    # 특정 재료 필수 (ID와 개수 확인) - YAML 로드용
    required_counts: Dict[str, int] = field(default_factory=dict)

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

        # 카테고리별 집계 & ID별 개수 집계
        category_values = {}
        ingredient_ids = set()
        ingredient_counts = {}
        total_value = 0.0

        for ing in ingredients:
            category_values[ing.category] = category_values.get(ing.category, 0.0) + ing.food_value

            # CookedFood 객체의 경우 item_id가 있으면 그것을, 없으면 name을 사용
            # 다른 객체의 경우 item_id를 사용
            if isinstance(ing, CookedFood):
                ing_id = ing.item_id if ing.item_id else ing.name
                ingredient_ids.add(ing_id)
                ingredient_counts[ing_id] = ingredient_counts.get(ing_id, 0) + 1
            else:
                ingredient_ids.add(ing.item_id)
                ingredient_counts[ing.item_id] = ingredient_counts.get(ing.item_id, 0) + 1

            total_value += ing.food_value

        # 1. 필수 재료 개수 확인 (YAML 레시피용 - 정확한 매칭)
        if self.required_counts:
            # 필수 재료가 있는지 확인
            for item_id, count in self.required_counts.items():
                if ingredient_counts.get(item_id, 0) < count:
                    return False
            
            # 카테고리 조건이 없는 경우에만 정확한 개수 매칭 (Exact Match)
            # 카테고리 조건이 있다면, 필수 재료 외에 다른 재료(카테고리용)가 들어갈 수 있음
            if not self.min_category:
                total_required = sum(self.required_counts.values())
                if len(ingredients) != total_required:
                    return False
                    
            # 필수 재료 조건은 만족했으므로, 계속해서 카테고리 조건 등을 확인
            # (필수 재료도 카테고리 값에 기여함)

        # 2. 기존 로직 (카테고리 기반)

        # 최소 카테고리 요구량 확인
        for category, min_val in self.min_category.items():
            if category_values.get(category, 0.0) < min_val:
                return False

        # 최대 카테고리 허용량 확인
        for category, max_val in self.max_category.items():
            if category_values.get(category, 0.0) > max_val:
                return False

        # 필수 재료 확인 (ID만)
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
    item_id: Optional[str] = None  # 선택적 item_id (없으면 name 사용)

    # 요리솥 보너스 적용 전 원래 값 (중복 보너스 방지용)
    original_hp_restore: Optional[int] = None
    original_mp_restore: Optional[int] = None
    original_buff_duration: Optional[int] = None

    def __post_init__(self):
        """초기화 후 처리"""
        # item_id가 설정되지 않은 경우 name으로 설정
        if self.item_id is None:
            self.item_id = self.name

    # 효과
    hp_restore: int = 0
    mp_restore: int = 0
    max_hp_bonus: int = 0  # 일시적 최대 HP 증가
    max_mp_bonus: int = 0  # 일시적 최대 MP 증가

    # 버프 (턴 수)
    buff_duration: int = 0
    buff_type: Optional[str] = None  # "attack", "defense", "speed" 등

    # 고급 버프 효과
    critical_rate: float = 0.0       # 치명타 확률 증가 (0.0 ~ 1.0)
    cooldown_reduction: float = 0.0  # 쿨타임 감소 (0.0 ~ 1.0)
    elemental_resist: Dict[str, float] = field(default_factory=dict) # 속성 저항 {element: value}
    xp_bonus: float = 0.0            # 경험치 획득량 증가 (0.0 ~ 1.0)
    
    # 상태이상 치료
    cure_status: Optional[str] = None

    # 디버프 (실패 요리)
    is_poison: bool = False
    poison_damage: int = 0

    # 신선도 (요리된 음식도 부패할 수 있음)
    spoil_time: int = 200

    weight: float = 0.5  # 무게 (kg) - 요리는 일반적으로 가벼움
    
    # 재료로 사용될 때의 속성
    category: IngredientCategory = IngredientCategory.PREPARED_DISH
    food_value: float = 1.0
    
    # 아이템 타입 (인벤토리 호환성)
    item_type: ItemType = ItemType.FOOD

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
    def _load_from_yaml(cls):
        """YAML 파일에서 레시피 로드"""
        import yaml
        import os
        from src.core.logger import get_logger
        
        logger = get_logger("recipe_db")
        
        # YAML 파일 경로
        data_path = os.path.join("data", "cooking_recipes.yaml")
        
        if not os.path.exists(data_path):
            logger.warning(f"Recipe file not found: {data_path}")
            return

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                recipes_data = yaml.safe_load(f)
                
            if not recipes_data:
                return

            loaded_count = 0
            for r_data in recipes_data:
                # 효과 파싱
                effects = r_data.get('effects', {})
                
                # 버프 타입 매핑
                buff_type = None
                if 'buff' in effects:
                    buff_str = effects['buff']
                    if 'strength' in buff_str or 'attack' in buff_str:
                        buff_type = "attack"
                    elif 'defense' in buff_str or 'vitality' in buff_str:
                        buff_type = "defense"
                    elif 'speed' in buff_str or 'agility' in buff_str:
                        buff_type = "speed"
                    elif 'magic' in buff_str or 'intelligence' in buff_str:
                        buff_type = "magic"
                    elif 'luck' in buff_str:
                        buff_type = "luck"
                    elif 'accuracy' in buff_str:
                        buff_type = "accuracy"
                    elif 'evasion' in buff_str:
                        buff_type = "evasion"
                
                # 결과 음식 생성
                # 재료로 사용될 때의 속성 파싱
                food_category = IngredientCategory.PREPARED_DISH
                if 'result_category' in r_data:
                    try:
                        food_category = IngredientCategory(r_data['result_category'])
                    except ValueError:
                        pass
                        
                food = CookedFood(
                    name=r_data['name'],
                    description=r_data.get('description', ''),
                    hp_restore=effects.get('hp_heal', 0),
                    mp_restore=effects.get('mp_heal', 0),
                    max_hp_bonus=effects.get('max_hp_bonus', 0),
                    max_mp_bonus=effects.get('max_mp_bonus', 0),
                    buff_duration=effects.get('duration', 0),
                    buff_type=buff_type,
                    critical_rate=effects.get('critical_rate', 0.0),
                    cooldown_reduction=effects.get('cooldown_reduction', 0.0),
                    elemental_resist=effects.get('elemental_resist', {}),
                    xp_bonus=effects.get('xp_bonus', 0.0),
                    cure_status=effects.get('cure_status'),
                    category=food_category,
                    food_value=r_data.get('food_value', 1.0)
                )
                
                # 조건 생성
                condition_args = {}
                
                # 1. 필수 재료 (ID와 개수)
                ingredients_data = r_data.get('ingredients', {})
                required_counts = {}
                
                # 2. 카테고리 요구사항
                min_category = {}
                max_category = {}
                
                for key, value in ingredients_data.items():
                    # 키가 카테고리인지 확인
                    try:
                        category = IngredientCategory(key)
                        # 카테고리라면 min_category에 추가
                        min_category[category] = float(value)
                    except ValueError:
                        # 카테고리가 아니면 특정 아이템 ID로 간주
                        required_counts[key] = int(value)
                
                # 추가 조건들
                if 'max_category' in r_data:
                    for key, value in r_data['max_category'].items():
                        try:
                            category = IngredientCategory(key)
                            max_category[category] = float(value)
                        except ValueError:
                            pass
                            
                condition = RecipeCondition(
                    required_counts=required_counts,
                    min_category=min_category,
                    max_category=max_category,
                    min_total_value=r_data.get('min_total_value', 0.0),
                    max_total_value=r_data.get('max_total_value', 999.0)
                )
                
                # 우선순위 설정
                priority_val = r_data.get('priority', 'MEDIUM')
                priority = getattr(RecipePriority, priority_val, RecipePriority.MEDIUM)
                
                # 난이도가 높으면 우선순위도 높게 설정 (자동)
                difficulty = r_data.get('difficulty', 1)
                if difficulty >= 7:
                    priority = RecipePriority.VERY_HIGH
                elif difficulty >= 5:
                    priority = RecipePriority.HIGH
                
                recipe = Recipe(
                    recipe_id=r_data['id'],
                    result=food,
                    condition=condition,
                    priority=priority
                )
                
                cls.RECIPES.append(recipe)
                loaded_count += 1
                
            logger.info(f"Loaded {loaded_count} recipes from YAML")
            
        except Exception as e:
            logger.error(f"Failed to load recipes from YAML: {e}")

    @classmethod
    def initialize(cls):
        """레시피 초기화"""
        if cls.RECIPES:
            return  # 이미 초기화됨
            
        # 1. YAML 레시피 로드
        cls._load_from_yaml()

        # 2. 기존 하드코딩 레시피 추가 (기존 코드 유지)
        cls.RECIPES.extend([
            # === 고급 요리 (우선순위 높음) ===
            # === 고급 요리 (우선순위 높음) ===

            # 드래곤 스테이크 (드래곤 고기 필수)
            Recipe(
                recipe_id="dragon_steak",
                result=CookedFood(
                    name="드래곤 스테이크",
                    description="드래곤 고기로 만든 최고급 스테이크. 강력한 힘을 부여한다.",
                    hp_restore=120,
                    mp_restore=55,
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
                    hp_restore=70,
                    mp_restore=85,
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
                    hp_restore=70,
                    mp_restore=45
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
                    hp_restore=95,
                    mp_restore=40
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
                    hp_restore=85,
                    mp_restore=55
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
                    hp_restore=50,
                    mp_restore=60
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
                    hp_restore=60,
                    mp_restore=70
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
                    hp_restore=110,
                    mp_restore=45,
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
                    hp_restore=55,
                    mp_restore=15
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
                    hp_restore=40,
                    mp_restore=28
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
                    hp_restore=100,
                    mp_restore=40,
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
                    hp_restore=130,
                    mp_restore=70,
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
                    hp_restore=120,
                    mp_restore=55,
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
                    hp_restore=50,
                    mp_restore=100,
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
                    hp_restore=60,
                    mp_restore=90,
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
                    hp_restore=40,
                    mp_restore=80,
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
                    hp_restore=85,
                    mp_restore=40,
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
                    hp_restore=95,
                    mp_restore=45,
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
                    hp_restore=100,
                    mp_restore=60,
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
                    hp_restore=90,
                    mp_restore=70,
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
                    hp_restore=40,
                    mp_restore=70,
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
                    hp_restore=90,
                    mp_restore=55,
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
                    hp_restore=115,
                    mp_restore=65,
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
                    hp_restore=120,
                    mp_restore=70,
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
                    hp_restore=110,
                    mp_restore=60,
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
                    mp_restore=70,
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
                    hp_restore=70,
                    mp_restore=75,
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
                    hp_restore=60,
                    mp_restore=80,
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
                    hp_restore=50,
                    mp_restore=25
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
                    mp_restore=32
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
                    hp_restore=30,
                    mp_restore=38
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
                    hp_restore=90,
                    mp_restore=40,
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
                    hp_restore=340,
                    mp_restore=200,
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
                    hp_restore=120,
                    mp_restore=60,
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
                    hp_restore=100,
                    mp_restore=50,
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
                    hp_restore=45,
                    mp_restore=100,
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
                    hp_restore=60,
                    mp_restore=90,
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
                    hp_restore=55,
                    mp_restore=100,
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
                    hp_restore=45,
                    mp_restore=100,
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
                    hp_restore=110,
                    mp_restore=60,
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
                    hp_restore=105,
                    mp_restore=65,
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
                    hp_restore=120,
                    mp_restore=70,
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
                    hp_restore=100,
                    mp_restore=65,
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
                    hp_restore=115,
                    mp_restore=75,
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
                    mp_restore=42,
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
                    hp_restore=90,
                    mp_restore=50,
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
                    hp_restore=125,
                    mp_restore=65,
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
                    hp_restore=105,
                    mp_restore=70,
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
                    hp_restore=70,
                    mp_restore=75,
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
                    hp_restore=50,
                    mp_restore=75,
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
                    mp_restore=65,
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
                    hp_restore=100,
                    mp_restore=70,
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
                    hp_restore=70,
                    mp_restore=75,
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
                    hp_restore=75,
                    mp_restore=75,
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
                    hp_restore=30,
                    mp_restore=80,
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
                    hp_restore=50,
                    mp_restore=100,
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
                    hp_restore=65,
                    mp_restore=20
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
                    mp_restore=32
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
                    hp_restore=42,
                    mp_restore=28
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
                    hp_restore=130,
                    mp_restore=60,
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
                    hp_restore=130,
                    mp_restore=50,
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
                    hp_restore=55,
                    mp_restore=90,
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
                    hp_restore=65,
                    mp_restore=75,
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
                    hp_restore=100,
                    mp_restore=60,
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
                    hp_restore=115,
                    mp_restore=65,
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
                    hp_restore=90,
                    mp_restore=70,
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
                    hp_restore=130,
                    mp_restore=60,
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
                    hp_restore=400,
                    mp_restore=250,
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
                    hp_restore=85,
                    mp_restore=80,
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
                    mp_restore=35
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
                    hp_restore=30,
                    mp_restore=40
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
                    mp_restore=25
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
                    hp_restore=70,
                    mp_restore=75,
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
                    hp_restore=75,
                    mp_restore=65,
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

            # ============================================
            # YAML 레시피 추가 (중복 제외)
            # ============================================

            # === 중간 재료 (Intermediate Ingredients) ===

            # 반죽
            Recipe(
                recipe_id="dough",
                result=CookedFood(
                    name="반죽",
                    description="밀가루와 물을 섞어 만든 반죽. 빵이나 면의 재료.",
                    hp_restore=15,
                    mp_restore=10,
                    category=IngredientCategory.GRAIN,
                    food_value=1.0
                ),
                condition=RecipeCondition(
                    required_ingredients=["flour", "water"]
                ),
                priority=RecipePriority.LOW
            ),

            # 버터
            Recipe(
                recipe_id="butter",
                result=CookedFood(
                    name="버터",
                    description="우유를 저어 만든 고소한 버터.",
                    hp_restore=20,
                    mp_restore=15,
                    category=IngredientCategory.VEGETABLE,
                    food_value=1.0
                ),
                condition=RecipeCondition(
                    required_ingredients=["milk", "salt"]
                ),
                priority=RecipePriority.LOW
            ),

            # 치즈
            Recipe(
                recipe_id="cheese",
                result=CookedFood(
                    name="치즈",
                    description="우유를 발효시켜 만든 치즈.",
                    hp_restore=35,
                    mp_restore=22,
                    category=IngredientCategory.VEGETABLE,
                    food_value=1.0
                ),
                condition=RecipeCondition(
                    required_ingredients=["milk"],
                    min_category={IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.LOW
            ),

            # 생크림
            Recipe(
                recipe_id="cream",
                result=CookedFood(
                    name="생크림",
                    description="달콤하고 부드러운 크림.",
                    hp_restore=25,
                    mp_restore=20,
                    category=IngredientCategory.VEGETABLE,
                    food_value=1.0
                ),
                condition=RecipeCondition(
                    required_ingredients=["milk", "sugar"]
                ),
                priority=RecipePriority.LOW
            ),

            # 삶은 달걀
            Recipe(
                recipe_id="boiled_egg",
                result=CookedFood(
                    name="삶은 달걀",
                    description="간단하게 삶은 달걀.",
                    hp_restore=40,
                    mp_restore=18,
                    category=IngredientCategory.MEAT,
                    food_value=1.0
                ),
                condition=RecipeCondition(
                    required_ingredients=["egg", "water"]
                ),
                priority=RecipePriority.LOW
            ),

            # === 초급 요리 (YAML Tier 1) ===

            # 약초 수프
            Recipe(
                recipe_id="herb_soup",
                result=CookedFood(
                    name="약초 수프",
                    description="따뜻하게 데운 약초 물. MP 회복에 좋다.",
                    hp_restore=35,
                    mp_restore=35
                ),
                condition=RecipeCondition(
                    required_ingredients=["herb"],
                    min_category={IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.LOW
            ),

            # 계란 프라이
            Recipe(
                recipe_id="egg_fry",
                result=CookedFood(
                    name="계란 프라이",
                    description="노른자가 살아있는 계란 프라이.",
                    hp_restore=45,
                    mp_restore=18
                ),
                condition=RecipeCondition(
                    required_ingredients=["egg"]
                ),
                priority=RecipePriority.LOW
            ),

            # 토스트
            Recipe(
                recipe_id="toast",
                result=CookedFood(
                    name="토스트",
                    description="바삭하게 구운 식빵.",
                    hp_restore=30,
                    mp_restore=18
                ),
                condition=RecipeCondition(
                    required_ingredients=["bread"]
                ),
                priority=RecipePriority.LOW
            ),

            # 주먹밥
            Recipe(
                recipe_id="rice_ball",
                result=CookedFood(
                    name="주먹밥",
                    description="간단하게 뭉친 주먹밥.",
                    hp_restore=40,
                    mp_restore=20
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "salt"]
                ),
                priority=RecipePriority.LOW
            ),

            # === 중급 요리 (YAML Tier 2) ===

            # 꿀빵
            Recipe(
                recipe_id="honey_bread",
                result=CookedFood(
                    name="꿀빵",
                    description="꿀을 발라 구운 달콤한 빵.",
                    hp_restore=80,
                    mp_restore=60,
                    category=IngredientCategory.GRAIN,
                    food_value=1.0
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "honey"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 진한 야채 스프
            Recipe(
                recipe_id="vegetable_soup_rich",
                result=CookedFood(
                    name="진한 야채 스프",
                    description="버터로 풍미를 더한 야채 스프.",
                    hp_restore=90,
                    mp_restore=65,
                    buff_duration=8,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    required_ingredients=["butter", "milk"],
                    min_category={IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 오므라이스
            Recipe(
                recipe_id="omurice",
                result=CookedFood(
                    name="오므라이스",
                    description="계란으로 감싼 볶음밥.",
                    hp_restore=120,
                    mp_restore=55
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "egg", "tomato_sauce"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 크림 파스타
            Recipe(
                recipe_id="cream_pasta",
                result=CookedFood(
                    name="크림 파스타",
                    description="부드러운 크림 소스 파스타.",
                    hp_restore=110,
                    mp_restore=70,
                    buff_duration=10,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "cream", "milk"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 토마토 파스타
            Recipe(
                recipe_id="tomato_pasta",
                result=CookedFood(
                    name="토마토 파스타",
                    description="새콤한 토마토 소스 파스타.",
                    hp_restore=100,
                    mp_restore=65,
                    buff_duration=8,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "tomato_sauce", "herb"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 밀크티
            Recipe(
                recipe_id="milk_tea",
                result=CookedFood(
                    name="밀크티",
                    description="달콤하고 부드러운 밀크티.",
                    hp_restore=40,
                    mp_restore=75,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["tea_leaf", "milk", "sugar"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 과일 펀치
            Recipe(
                recipe_id="fruit_punch",
                result=CookedFood(
                    name="과일 펀치",
                    description="여러 가지 과일을 섞어 만든 시원한 음료.",
                    hp_restore=50,
                    mp_restore=75
                ),
                condition=RecipeCondition(
                    required_ingredients=["water", "sugar"],
                    min_category={IngredientCategory.FRUIT: 3.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 팬케이크
            Recipe(
                recipe_id="pancakes",
                result=CookedFood(
                    name="팬케이크",
                    description="폭신폭신한 팬케이크.",
                    hp_restore=100,
                    mp_restore=65,
                    buff_duration=10,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "milk", "egg", "honey"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 특제 볶음밥
            Recipe(
                recipe_id="fried_rice_special",
                result=CookedFood(
                    name="특제 볶음밥",
                    description="다양한 재료가 들어간 볶음밥.",
                    hp_restore=120,
                    mp_restore=65,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "egg"],
                    min_category={IngredientCategory.MEAT: 1.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 고급 요리 (YAML Tier 3) ===

            # 콤비네이션 피자
            Recipe(
                recipe_id="pizza",
                result=CookedFood(
                    name="콤비네이션 피자",
                    description="토핑이 가득한 피자. 한 조각만 먹어도 배부르다.",
                    hp_restore=120,
                    mp_restore=65,
                    max_hp_bonus=25,
                    buff_duration=15,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "tomato_sauce", "cheese"],
                    min_category={IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 까르보나라
            Recipe(
                recipe_id="carbonara",
                result=CookedFood(
                    name="까르보나라",
                    description="계란 노른자와 크림으로 맛을 낸 정통 파스타.",
                    hp_restore=110,
                    mp_restore=65,
                    buff_duration=12
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "cream", "egg"],
                    min_category={IngredientCategory.MEAT: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 스테이크 정식
            Recipe(
                recipe_id="steak_dinner",
                result=CookedFood(
                    name="스테이크 정식",
                    description="스테이크와 가니쉬, 와인이 곁들여진 정식.",
                    hp_restore=140,
                    mp_restore=70,
                    max_hp_bonus=30,
                    buff_duration=20,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    required_ingredients=["wine"],
                    min_category={IngredientCategory.MEAT: 2.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 해산물 파에야
            Recipe(
                recipe_id="seafood_paella",
                result=CookedFood(
                    name="해산물 파에야",
                    description="해산물의 풍미가 쌀알에 배어든 요리.",
                    hp_restore=100,
                    mp_restore=80,
                    buff_duration=15,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "fish_stock", "shellfish", "spice"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 궁중 갈비찜
            Recipe(
                recipe_id="beef_stew_royal",
                result=CookedFood(
                    name="궁중 갈비찜",
                    description="최상급 갈비를 육수에 졸여 만든 궁중 요리.",
                    hp_restore=135,
                    mp_restore=65,
                    max_hp_bonus=40,
                    buff_duration=15
                ),
                condition=RecipeCondition(
                    required_ingredients=["meat_stock", "soy_sauce"],
                    min_category={IngredientCategory.MEAT: 3.0, IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 클럽 샌드위치
            Recipe(
                recipe_id="club_sandwich",
                result=CookedFood(
                    name="클럽 샌드위치",
                    description="여러 층으로 쌓아 올린 푸짐한 샌드위치.",
                    hp_restore=85,
                    mp_restore=55,
                    buff_duration=12
                ),
                condition=RecipeCondition(
                    required_ingredients=["toast", "cheese"],
                    min_category={IngredientCategory.MEAT: 1.0, IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 치즈 케이크
            Recipe(
                recipe_id="cheesecake",
                result=CookedFood(
                    name="치즈 케이크",
                    description="진한 치즈의 풍미가 느껴지는 케이크.",
                    hp_restore=65,
                    mp_restore=90,
                    max_mp_bonus=25,
                    buff_duration=15,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["cheese", "cream", "egg", "sugar"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 과일 타르트
            Recipe(
                recipe_id="fruit_tart",
                result=CookedFood(
                    name="과일 타르트",
                    description="상큼한 과일이 올라간 타르트.",
                    hp_restore=55,
                    mp_restore=80,
                    buff_duration=12,
                    buff_type="luck"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "cream"],
                    min_category={IngredientCategory.FRUIT: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 로얄 밀크티
            Recipe(
                recipe_id="royal_milk_tea",
                result=CookedFood(
                    name="로얄 밀크티",
                    description="우유를 듬뿍 넣어 끓인 홍차.",
                    hp_restore=50,
                    mp_restore=75,
                    buff_duration=10,
                    cure_status="silence"
                ),
                condition=RecipeCondition(
                    required_ingredients=["tea_leaf", "honey"],
                    min_category={IngredientCategory.VEGETABLE: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 특급 초밥
            Recipe(
                recipe_id="sushi_premium",
                result=CookedFood(
                    name="특급 초밥",
                    description="엄선된 재료로 만든 초밥.",
                    hp_restore=110,
                    mp_restore=80,
                    max_hp_bonus=20,
                    max_mp_bonus=20,
                    buff_duration=15
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "shellfish"],
                    min_category={IngredientCategory.FISH: 1.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 해산물 파스타
            Recipe(
                recipe_id="seafood_pasta",
                result=CookedFood(
                    name="해산물 파스타",
                    description="신선한 조개가 들어간 파스타.",
                    hp_restore=95,
                    mp_restore=65,
                    buff_duration=15
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "shellfish", "tomato_sauce"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 에그 타르트
            Recipe(
                recipe_id="egg_tart",
                result=CookedFood(
                    name="에그 타르트",
                    description="부드러운 커스터드 크림이 듬뿍.",
                    hp_restore=80,
                    mp_restore=70,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "cream", "sugar"],
                    min_category={IngredientCategory.MEAT: 1.0}  # egg category
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 상태 이상 회복 요리 ===

            # 해독 샐러드
            Recipe(
                recipe_id="antidote_salad",
                result=CookedFood(
                    name="해독 샐러드",
                    description="독소를 배출해주는 샐러드.",
                    hp_restore=70,
                    mp_restore=50,
                    cure_status="poison"
                ),
                condition=RecipeCondition(
                    required_ingredients=["herb"],
                    min_category={IngredientCategory.VEGETABLE: 2.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 맑은 정신 수프
            Recipe(
                recipe_id="clarity_soup",
                result=CookedFood(
                    name="맑은 정신 수프",
                    description="머리를 맑게 해주는 시원한 국물.",
                    hp_restore=50,
                    mp_restore=75,
                    cure_status="confusion"
                ),
                condition=RecipeCondition(
                    required_ingredients=["fish_stock", "mint"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 따뜻한 생강차
            Recipe(
                recipe_id="warm_ginger_tea",
                result=CookedFood(
                    name="따뜻한 생강차",
                    description="몸을 따뜻하게 녹여주는 차.",
                    hp_restore=45,
                    mp_restore=65,
                    cure_status="freeze"
                ),
                condition=RecipeCondition(
                    required_ingredients=["ginger", "honey", "water"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 진저 에일
            Recipe(
                recipe_id="ginger_ale",
                result=CookedFood(
                    name="진저 에일",
                    description="생강으로 만든 시원한 음료.",
                    hp_restore=30,
                    mp_restore=35,
                    buff_duration=10
                ),
                condition=RecipeCondition(
                    required_ingredients=["ginger", "sugar", "water"]
                ),
                priority=RecipePriority.LOW
            ),

            # === 특수 효과 요리 ===

            # 황금 사과 파이 (치명타 증가)
            Recipe(
                recipe_id="golden_apple_pie",
                result=CookedFood(
                    name="황금 사과 파이",
                    description="황금 사과로 만든 전설적인 파이. 치명타율 상승.",
                    hp_restore=320,
                    mp_restore=220,
                    critical_rate=0.20,
                    buff_duration=30,
                    buff_type="luck"
                ),
                condition=RecipeCondition(
                    required_ingredients=["golden_apple", "dough", "honey", "butter"]
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 암살자의 스튜 (치명타 증가)
            Recipe(
                recipe_id="assassins_stew",
                result=CookedFood(
                    name="암살자의 스튜",
                    description="치명적인 일격을 위한 스튜.",
                    hp_restore=80,
                    mp_restore=55,
                    critical_rate=0.15,
                    buff_duration=20
                ),
                condition=RecipeCondition(
                    required_ingredients=["monster_meat", "red_mushroom", "spice"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 시간 왜곡 차 (쿨타임 감소)
            Recipe(
                recipe_id="time_warp_tea",
                result=CookedFood(
                    name="시간 왜곡 차",
                    description="시간의 흐름을 느리게 느끼게 하는 차. 스킬 쿨타임 감소.",
                    hp_restore=40,
                    mp_restore=95,
                    cooldown_reduction=0.20,
                    buff_duration=20,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    required_ingredients=["tea_leaf", "magic_herb", "water"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 신속의 샐러드 (쿨타임 감소)
            Recipe(
                recipe_id="quickstep_salad",
                result=CookedFood(
                    name="신속의 샐러드",
                    description="몸을 가볍게 해주는 샐러드. 쿨타임 감소.",
                    hp_restore=80,
                    mp_restore=65,
                    cooldown_reduction=0.10,
                    buff_duration=15,
                    buff_type="speed"
                ),
                condition=RecipeCondition(
                    required_ingredients=["berry"],
                    min_category={IngredientCategory.VEGETABLE: 3.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 학자의 죽 (경험치 증가)
            Recipe(
                recipe_id="scholars_porridge",
                result=CookedFood(
                    name="학자의 죽",
                    description="머리가 좋아지는 죽. 경험치 획득량 증가.",
                    hp_restore=80,
                    mp_restore=70,
                    xp_bonus=0.20,
                    buff_duration=30
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "water"],
                    min_category={IngredientCategory.FISH: 1.0}
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 지혜의 수프 (경험치 증가)
            Recipe(
                recipe_id="wisdom_soup",
                result=CookedFood(
                    name="지혜의 수프",
                    description="고대의 지혜가 담긴 수프. 깨달음을 얻게 해준다.",
                    hp_restore=300,
                    mp_restore=280,
                    max_mp_bonus=35,
                    xp_bonus=0.50,
                    buff_duration=40
                ),
                condition=RecipeCondition(
                    required_ingredients=["mandrake", "magic_herb", "milk"]
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 화염 저항 칠리 (화염 저항)
            Recipe(
                recipe_id="fireproof_chili",
                result=CookedFood(
                    name="화염 저항 칠리",
                    description="이열치열. 불에 대한 저항력을 높여준다.",
                    hp_restore=95,
                    mp_restore=50,
                    elemental_resist={"fire": 0.50},
                    buff_duration=20,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    required_ingredients=["tomato_sauce", "spice"],
                    min_category={IngredientCategory.MEAT: 2.0}
                ),
                priority=RecipePriority.HIGH
            ),

            # 수호의 아이스크림 (냉기 저항)
            Recipe(
                recipe_id="ice_cream_warding",
                result=CookedFood(
                    name="수호의 아이스크림",
                    description="차가운 기운으로 냉기 저항력을 높여준다.",
                    hp_restore=55,
                    mp_restore=75,
                    elemental_resist={"ice": 0.50},
                    cure_status="burn",
                    buff_duration=20
                ),
                condition=RecipeCondition(
                    required_ingredients=["ice", "cream", "sugar", "berry"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # 송로버섯 리조또
            Recipe(
                recipe_id="truffle_risotto",
                result=CookedFood(
                    name="송로버섯 리조또",
                    description="송로버섯의 깊은 향이 배어있는 고급 리조또.",
                    hp_restore=110,
                    mp_restore=80,
                    buff_duration=25
                ),
                condition=RecipeCondition(
                    required_ingredients=["rice", "truffle", "cream", "cheese"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 별빛 타르트 (마법 강화)
            Recipe(
                recipe_id="star_fruit_tart",
                result=CookedFood(
                    name="별빛 타르트",
                    description="반짝이는 별빛을 담은 타르트. 마력이 증가한다.",
                    hp_restore=55,
                    mp_restore=95,
                    max_mp_bonus=40,
                    buff_duration=20,
                    buff_type="magic"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "cream", "star_fruit"]
                ),
                priority=RecipePriority.HIGH
            ),

            # 슬라임 푸딩
            Recipe(
                recipe_id="slime_pudding",
                result=CookedFood(
                    name="슬라임 푸딩",
                    description="탱글탱글한 슬라임 푸딩. 물리 저항 증가.",
                    hp_restore=80,
                    mp_restore=65,
                    elemental_resist={"physical": 0.10},
                    buff_duration=15,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    required_ingredients=["slime_jelly", "sugar", "milk"]
                ),
                priority=RecipePriority.MEDIUM
            ),

            # === 최상급 요리 (YAML Tier 4) ===

            # 비프 웰링턴
            Recipe(
                recipe_id="beef_wellington",
                result=CookedFood(
                    name="비프 웰링턴",
                    description="스테이크를 페이스트리 반죽으로 감싸 구운 최고의 요리.",
                    hp_restore=420,
                    mp_restore=240,
                    max_hp_bonus=50,
                    buff_duration=30
                ),
                condition=RecipeCondition(
                    required_ingredients=["dough", "mushroom_stew", "butter"],
                    min_category={IngredientCategory.MEAT: 2.0}
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 황제 해산물 플래터
            Recipe(
                recipe_id="seafood_platter_deluxe",
                result=CookedFood(
                    name="황제 해산물 플래터",
                    description="바다의 모든 진미를 모아놓은 플래터.",
                    hp_restore=380,
                    mp_restore=260,
                    max_hp_bonus=30,
                    max_mp_bonus=30,
                    buff_duration=25
                ),
                condition=RecipeCondition(
                    required_ingredients=["grilled_fish", "kraken_tentacle", "butter"]
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 용의 연회
            Recipe(
                recipe_id="dragon_feast",
                result=CookedFood(
                    name="용의 연회",
                    description="용 사냥꾼들만이 즐길 수 있다는 전설의 연회.",
                    hp_restore=480,
                    mp_restore=280,
                    max_hp_bonus=50,
                    max_mp_bonus=40,
                    buff_duration=40,
                    buff_type="attack"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dragon_steak", "dragon_stew", "wine"]
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 용비늘 국 (전 속성 저항)
            Recipe(
                recipe_id="dragon_scale_soup",
                result=CookedFood(
                    name="용비늘 국",
                    description="용의 비늘을 우려낸 국물. 모든 속성 저항이 크게 증가한다.",
                    hp_restore=360,
                    mp_restore=240,
                    elemental_resist={"fire": 0.80, "ice": 0.80, "lightning": 0.80},
                    buff_duration=30,
                    buff_type="defense"
                ),
                condition=RecipeCondition(
                    required_ingredients=["dragon_scale", "water", "spice"]
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 불사조의 눈물 차
            Recipe(
                recipe_id="phoenix_tear_tea",
                result=CookedFood(
                    name="불사조의 눈물 차",
                    description="불사조의 깃털을 우려낸 차. 놀라운 치유력이 있다.",
                    hp_restore=450,
                    mp_restore=300,
                    cure_status="all",
                    buff_duration=30
                ),
                condition=RecipeCondition(
                    required_ingredients=["phoenix_feather", "water", "honey"]
                ),
                priority=RecipePriority.VERY_HIGH
            ),

            # 암브로시아 (신들의 음식)
            Recipe(
                recipe_id="ambrosia",
                result=CookedFood(
                    name="암브로시아",
                    description="신들의 음식. 먹는 순간 불멸에 가까운 힘을 얻는다.",
                    hp_restore=500,
                    mp_restore=300,
                    max_hp_bonus=60,
                    max_mp_bonus=50,
                    cure_status="all",
                    buff_duration=50
                ),
                condition=RecipeCondition(
                    required_ingredients=["fruit_tart", "honey_cake", "royal_milk_tea", "phoenix_feather"]
                ),
                priority=RecipePriority.VERY_HIGH
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
        ])

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
