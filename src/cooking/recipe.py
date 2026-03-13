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
                    item_id=r_data['id'],
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
                    is_poison=effects.get('is_poison', False),
                    poison_damage=effects.get('poison_damage', 0),
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
            
        # YAML 레시피 로드
        cls._load_from_yaml()

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

        # 명시적 wet_goop 폴백 (정렬 순서 의존 제거)
        return Recipe(
            recipe_id="wet_goop",
            result=CookedFood(
                name="축축한 음식",
                description="뭔가 잘못된 요리... 먹을 수는 있지만...",
                item_id="wet_goop",
                hp_restore=5,
                mp_restore=0,
                is_poison=False
            ),
            condition=RecipeCondition(min_total_value=0.0),
            priority=RecipePriority.FALLBACK
        )
