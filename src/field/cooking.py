"""
Cooking System - 요리 시스템

재료로 음식을 만드는 시스템
"""

import random
from typing import Dict, Any, Optional, List
from enum import Enum
from src.core.event_bus import event_bus
from src.core.config import get_config
from src.core.logger import get_logger
from src.character.stats import Stats


class CookingQuality(Enum):
    """요리 품질"""
    POOR = "poor"
    NORMAL = "normal"
    GOOD = "good"
    EXCELLENT = "excellent"


class Recipe:
    """요리 레시피"""

    def __init__(
        self,
        recipe_id: str,
        name: str,
        ingredients: Dict[str, int],  # {재료ID: 개수}
        effects: Dict[str, Any],
        difficulty: int = 1
    ) -> None:
        self.recipe_id = recipe_id
        self.name = name
        self.ingredients = ingredients
        self.effects = effects
        self.difficulty = difficulty


class CookingSystem:
    """요리 시스템"""

    def __init__(self) -> None:
        self.logger = get_logger("cooking")
        self.config = get_config()

        # 설정 로드
        self.enabled = self.config.get("field_systems.cooking.enabled", True)
        self.mp_cost = self.config.get("field_systems.cooking.mp_cost", 15)
        self.failure_chance = self.config.get("field_systems.cooking.failure_chance", 0.1)
        self.stat_bonus = self.config.get("field_systems.cooking.stat_bonus", "dexterity")

        # 품질 배율
        self.quality_multipliers = {
            CookingQuality.POOR: 0.5,
            CookingQuality.NORMAL: 1.0,
            CookingQuality.GOOD: 1.5,
            CookingQuality.EXCELLENT: 2.0
        }

        # 레시피 데이터베이스
        self.recipes: Dict[str, Recipe] = {}
        self._load_recipes()

    def _load_recipes(self) -> None:
        """레시피 데이터 로드"""
        # 기본 레시피 데이터 (향후 YAML로 확장 가능)
        default_recipes = [
            # === 초급 요리 (난이도 1-2) ===
            Recipe(
                "herb_soup",
                "약초 수프",
                {"herb": 2},
                {"hp_heal": 30, "mp_heal": 10},
                difficulty=1
            ),
            Recipe(
                "mushroom_stew",
                "버섯 스튜",
                {"mushroom": 3},
                {"hp_heal": 50, "brv_heal": 20},
                difficulty=1
            ),
            Recipe(
                "berry_juice",
                "베리 주스",
                {"wild_berry": 4},
                {"mp_heal": 40, "brv_heal": 15},
                difficulty=1
            ),
            Recipe(
                "grilled_fish",
                "생선 구이",
                {"fish": 1, "herb": 1},
                {"hp_heal": 60, "buff": "defense_up"},
                difficulty=2
            ),
            Recipe(
                "roasted_meat",
                "고기 구이",
                {"meat": 1, "wild_berry": 1},
                {"hp_heal": 70, "buff": "strength_up"},
                difficulty=2
            ),
            Recipe(
                "vegetable_salad",
                "야채 샐러드",
                {"vegetable": 3, "herb": 1},
                {"hp_heal": 45, "mp_heal": 25},
                difficulty=1
            ),
            Recipe(
                "honey_bread",
                "꿀빵",
                {"flour": 2, "honey": 1},
                {"brv_heal": 40, "hp_heal": 30},
                difficulty=2
            ),

            # === 중급 요리 (난이도 3-4) ===
            Recipe(
                "seafood_soup",
                "해물 수프",
                {"fish": 2, "shellfish": 1, "herb": 2},
                {"hp_heal": 100, "mp_heal": 50, "buff": "magic_up"},
                difficulty=3
            ),
            Recipe(
                "meat_stew",
                "고기 스튜",
                {"meat": 2, "vegetable": 2, "mushroom": 1},
                {"hp_heal": 120, "brv_heal": 40, "buff": "vitality_up"},
                difficulty=3
            ),
            Recipe(
                "mushroom_risotto",
                "버섯 리조또",
                {"mushroom": 3, "flour": 2, "herb": 1},
                {"hp_heal": 90, "mp_heal": 70},
                difficulty=3
            ),
            Recipe(
                "fruit_tart",
                "과일 타르트",
                {"wild_berry": 3, "flour": 2, "honey": 1},
                {"mp_heal": 80, "buff": "speed_up"},
                difficulty=3
            ),
            Recipe(
                "special_dish",
                "특제 요리",
                {"herb": 1, "mushroom": 2, "flower": 1},
                {"hp_heal": 100, "mp_heal": 50, "buff": "strength_up"},
                difficulty=4
            ),
            Recipe(
                "elven_bread",
                "엘프의 빵",
                {"flour": 3, "honey": 2, "moonflower": 1},
                {"hp_heal": 150, "mp_heal": 100, "brv_heal": 50},
                difficulty=4
            ),
            Recipe(
                "dragon_curry",
                "드래곤 카레",
                {"meat": 3, "vegetable": 2, "spice": 2},
                {"hp_heal": 180, "buff": "all_stats_up"},
                difficulty=4
            ),

            # === 고급 요리 (난이도 5-6) ===
            Recipe(
                "phoenix_soup",
                "불사조 수프",
                {"phoenix_feather": 1, "herb": 3, "moonflower": 2},
                {"hp_heal": 250, "mp_heal": 150, "buff": "regen"},
                difficulty=5
            ),
            Recipe(
                "crystal_cake",
                "크리스탈 케이크",
                {"crystal_sugar": 2, "flour": 3, "wild_berry": 4, "honey": 2},
                {"mp_heal": 200, "buff": "magic_boost"},
                difficulty=5
            ),
            Recipe(
                "royal_feast",
                "왕실 연회 요리",
                {"meat": 3, "fish": 2, "vegetable": 3, "spice": 2, "honey": 1},
                {"hp_heal": 300, "mp_heal": 200, "brv_heal": 100, "buff": "royal_blessing"},
                difficulty=6
            ),
            Recipe(
                "mana_potion_deluxe",
                "고급 마나 포션",
                {"mana_herb": 3, "crystal_water": 2, "moonflower": 1},
                {"mp_heal": 250, "buff": "mp_regen"},
                difficulty=5
            ),
            Recipe(
                "starlight_wine",
                "별빛 와인",
                {"star_fruit": 3, "moonflower": 2, "crystal_water": 1},
                {"hp_heal": 200, "mp_heal": 200, "buff": "luck_up"},
                difficulty=6
            ),

            # === 특수 요리 (난이도 7+) ===
            Recipe(
                "ambrosia",
                "신의 음식",
                {"phoenix_feather": 2, "star_fruit": 3, "crystal_sugar": 2, "moonflower": 3, "mana_herb": 2},
                {"hp_heal": 500, "mp_heal": 500, "brv_heal": 200, "buff": "divine_blessing"},
                difficulty=8
            ),
            Recipe(
                "elixir_supreme",
                "최상급 엘릭서",
                {"phoenix_feather": 1, "dragon_scale": 1, "mana_herb": 4, "crystal_water": 3},
                {"hp_heal": 999, "mp_heal": 999, "buff": "full_recovery"},
                difficulty=9
            ),

            # === 한국 전통 요리 (난이도 2-4) ===
            Recipe(
                "kimchi_stew",
                "김치찌개",
                {"vegetable": 2, "meat": 1, "spice": 1},
                {"hp_heal": 80, "brv_heal": 30, "buff": "strength_up"},
                difficulty=2
            ),
            Recipe(
                "bibimbap",
                "비빔밥",
                {"vegetable": 3, "meat": 1, "herb": 1},
                {"hp_heal": 100, "mp_heal": 40, "brv_heal": 35},
                difficulty=3
            ),
            Recipe(
                "samgyetang",
                "삼계탕",
                {"meat": 2, "herb": 3, "wild_ginseng": 1},
                {"hp_heal": 150, "mp_heal": 80, "buff": "vitality_up"},
                difficulty=4
            ),
            Recipe(
                "bulgogi",
                "불고기",
                {"meat": 3, "vegetable": 1, "spice": 1},
                {"hp_heal": 120, "buff": "attack_up"},
                difficulty=3
            ),
            Recipe(
                "tteokbokki",
                "떡볶이",
                {"flour": 2, "vegetable": 1, "spice": 2},
                {"hp_heal": 70, "brv_heal": 40},
                difficulty=2
            ),

            # === 일본 요리 (난이도 2-4) ===
            Recipe(
                "sushi",
                "초밥",
                {"fish": 3, "seaweed": 1},
                {"hp_heal": 90, "mp_heal": 45},
                difficulty=3
            ),
            Recipe(
                "ramen",
                "라멘",
                {"flour": 2, "meat": 1, "vegetable": 2},
                {"hp_heal": 110, "brv_heal": 50},
                difficulty=3
            ),
            Recipe(
                "tempura",
                "튀김",
                {"fish": 1, "vegetable": 2, "flour": 1},
                {"hp_heal": 75, "buff": "speed_up"},
                difficulty=2
            ),
            Recipe(
                "takoyaki",
                "타코야키",
                {"shellfish": 2, "flour": 2, "vegetable": 1},
                {"hp_heal": 65, "brv_heal": 30},
                difficulty=2
            ),

            # === 서양 요리 (난이도 3-5) ===
            Recipe(
                "steak",
                "스테이크",
                {"meat": 3, "vegetable": 1, "spice": 1},
                {"hp_heal": 140, "buff": "strength_up"},
                difficulty=4
            ),
            Recipe(
                "pasta",
                "파스타",
                {"flour": 3, "vegetable": 2, "spice": 1},
                {"hp_heal": 95, "mp_heal": 55},
                difficulty=3
            ),
            Recipe(
                "pizza",
                "피자",
                {"flour": 3, "meat": 2, "vegetable": 1},
                {"hp_heal": 130, "brv_heal": 60},
                difficulty=4
            ),
            Recipe(
                "soup_de_poisson",
                "프렌치 피시 수프",
                {"fish": 3, "vegetable": 2, "herb": 2, "spice": 1},
                {"hp_heal": 160, "mp_heal": 90, "buff": "magic_up"},
                difficulty=5
            ),

            # === 중국 요리 (난이도 2-4) ===
            Recipe(
                "mapo_tofu",
                "마파두부",
                {"vegetable": 3, "meat": 1, "spice": 2},
                {"hp_heal": 85, "brv_heal": 35, "buff": "attack_up"},
                difficulty=3
            ),
            Recipe(
                "fried_rice",
                "볶음밥",
                {"flour": 2, "meat": 1, "vegetable": 2},
                {"hp_heal": 80, "brv_heal": 45},
                difficulty=2
            ),
            Recipe(
                "sweet_sour_pork",
                "탕수육",
                {"meat": 3, "vegetable": 1, "flour": 1, "honey": 1},
                {"hp_heal": 125, "buff": "defense_up"},
                difficulty=4
            ),
            Recipe(
                "dim_sum",
                "딤섬",
                {"flour": 2, "meat": 1, "vegetable": 1, "shellfish": 1},
                {"hp_heal": 100, "mp_heal": 50},
                difficulty=3
            ),

            # === 디저트 (난이도 2-5) ===
            Recipe(
                "apple_pie",
                "사과 파이",
                {"wild_berry": 3, "flour": 2, "honey": 1},
                {"mp_heal": 70, "brv_heal": 40},
                difficulty=3
            ),
            Recipe(
                "cheesecake",
                "치즈케이크",
                {"flour": 2, "honey": 2, "wild_berry": 1},
                {"mp_heal": 90, "buff": "mp_regen"},
                difficulty=4
            ),
            Recipe(
                "ice_cream",
                "아이스크림",
                {"wild_berry": 2, "honey": 1, "crystal_water": 1},
                {"hp_heal": 50, "mp_heal": 60, "brv_heal": 50},
                difficulty=2
            ),
            Recipe(
                "chocolate_cake",
                "초콜릿 케이크",
                {"flour": 3, "honey": 2, "wild_berry": 1},
                {"mp_heal": 100, "brv_heal": 60},
                difficulty=4
            ),
            Recipe(
                "pudding",
                "푸딩",
                {"honey": 2, "wild_berry": 1},
                {"mp_heal": 65, "brv_heal": 35},
                difficulty=2
            ),

            # === 음료 (난이도 1-4) ===
            Recipe(
                "herbal_tea",
                "허브차",
                {"herb": 3, "honey": 1},
                {"mp_heal": 50, "brv_heal": 30},
                difficulty=1
            ),
            Recipe(
                "energy_drink",
                "에너지 드링크",
                {"wild_berry": 2, "herb": 1, "honey": 1},
                {"brv_heal": 70, "buff": "haste"},
                difficulty=2
            ),
            Recipe(
                "mana_coffee",
                "마나 커피",
                {"mana_herb": 2, "crystal_water": 1},
                {"mp_heal": 120, "buff": "magic_up"},
                difficulty=3
            ),
            Recipe(
                "healing_potion",
                "힐링 포션",
                {"herb": 3, "moonflower": 1, "crystal_water": 1},
                {"hp_heal": 180, "buff": "regen"},
                difficulty=4
            ),

            # === 특별 요리 (난이도 5-8) ===
            Recipe(
                "dragon_meat_bbq",
                "드래곤 고기 바비큐",
                {"dragon_scale": 1, "meat": 2, "spice": 3},
                {"hp_heal": 250, "buff": "dragon_power"},
                difficulty=6
            ),
            Recipe(
                "immortal_peach",
                "불로장생 복숭아",
                {"star_fruit": 2, "moonflower": 2, "honey": 2},
                {"hp_heal": 300, "mp_heal": 300, "buff": "immortality"},
                difficulty=7
            ),
            Recipe(
                "mermaid_soup",
                "인어 수프",
                {"fish": 3, "shellfish": 2, "seaweed": 3, "crystal_water": 2},
                {"hp_heal": 220, "mp_heal": 180, "buff": "water_blessing"},
                difficulty=6
            ),
            Recipe(
                "phoenix_omelette",
                "불사조 오믈렛",
                {"phoenix_feather": 1, "herb": 2, "spice": 1},
                {"hp_heal": 280, "buff": "resurrection"},
                difficulty=7
            ),
            Recipe(
                "celestial_banquet",
                "천상의 연회",
                {"phoenix_feather": 1, "dragon_scale": 1, "star_fruit": 2, "mana_herb": 3, "crystal_sugar": 2},
                {"hp_heal": 500, "mp_heal": 500, "brv_heal": 300, "buff": "ultimate_power"},
                difficulty=9
            ),
        ]

        for recipe in default_recipes:
            self.recipes[recipe.recipe_id] = recipe

    def can_cook(self, character: Any, recipe_id: str, inventory: Dict[str, int]) -> bool:
        """
        요리 가능 여부

        Args:
            character: 캐릭터
            recipe_id: 레시피 ID
            inventory: 인벤토리 {"아이템ID": 개수}

        Returns:
            요리 가능 여부
        """
        if not self.enabled:
            return False

        # MP 확인
        current_mp = getattr(character, 'current_mp', 0)
        if current_mp < self.mp_cost:
            return False

        # 레시피 존재 확인
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return False

        # 재료 확인
        for ingredient, required_amount in recipe.ingredients.items():
            if inventory.get(ingredient, 0) < required_amount:
                return False

        return True

    def cook(
        self,
        character: Any,
        recipe_id: str,
        inventory: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        요리 실행

        Args:
            character: 캐릭터
            recipe_id: 레시피 ID
            inventory: 인벤토리

        Returns:
            요리 결과
        """
        if not self.can_cook(character, recipe_id, inventory):
            return {"success": False, "quality": None, "item": None}

        recipe = self.recipes[recipe_id]

        # MP 소비
        if hasattr(character, 'current_mp'):
            character.current_mp -= self.mp_cost

        # 재료 소비
        for ingredient, amount in recipe.ingredients.items():
            inventory[ingredient] -= amount

        # 실패 판정
        if random.random() < self.failure_chance:
            self.logger.info(f"요리 실패: {character.name} - {recipe.name}")
            event_bus.publish("cooking.failed", {
                "character": character,
                "recipe": recipe
            })
            return {"success": False, "quality": None, "item": None}

        # 품질 결정
        quality = self._determine_quality(character, recipe)

        # 음식 아이템 생성
        item = self._create_food_item(recipe, quality)

        result = {
            "success": True,
            "quality": quality,
            "item": item
        }

        self.logger.info(
            f"요리 성공: {character.name}",
            {
                "recipe": recipe.name,
                "quality": quality.value
            }
        )

        event_bus.publish("cooking.completed", {
            "character": character,
            "result": result
        })

        return result

    def _determine_quality(self, character: Any, recipe: Recipe) -> CookingQuality:
        """품질 결정"""
        stat_value = getattr(character, self.stat_bonus, 0)
        quality_roll = random.random() + (stat_value - recipe.difficulty) * 0.05

        if quality_roll >= 0.9:
            return CookingQuality.EXCELLENT
        elif quality_roll >= 0.7:
            return CookingQuality.GOOD
        elif quality_roll >= 0.4:
            return CookingQuality.NORMAL
        else:
            return CookingQuality.POOR

    def _create_food_item(self, recipe: Recipe, quality: CookingQuality) -> Dict[str, Any]:
        """음식 아이템 생성"""
        multiplier = self.quality_multipliers[quality]

        effects = {}
        for effect_name, effect_value in recipe.effects.items():
            if isinstance(effect_value, (int, float)):
                effects[effect_name] = int(effect_value * multiplier)
            else:
                effects[effect_name] = effect_value

        # 최고 품질일 때 추가 효과
        if quality == CookingQuality.EXCELLENT:
            effects["duration"] = effects.get("duration", 0) + 2

        return {
            "name": f"{recipe.name} ({quality.value})",
            "recipe_id": recipe.recipe_id,
            "quality": quality.value,
            "effects": effects
        }

    def add_recipe(self, recipe: Recipe) -> None:
        """레시피 추가 (동적 확장)"""
        self.recipes[recipe.recipe_id] = recipe

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """레시피 조회"""
        return self.recipes.get(recipe_id)

    def get_all_recipes(self) -> Dict[str, Recipe]:
        """모든 레시피"""
        return self.recipes.copy()


# 전역 인스턴스
cooking_system = CookingSystem()
