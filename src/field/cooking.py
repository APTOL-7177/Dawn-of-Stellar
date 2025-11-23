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
        import yaml
        import os

        # YAML 파일 경로
        data_path = os.path.join("data", "cooking_recipes.yaml")
        
        try:
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    recipes_data = yaml.safe_load(f)
                    
                if recipes_data:
                    for r_data in recipes_data:
                        recipe = Recipe(
                            recipe_id=r_data['id'],
                            name=r_data['name'],
                            ingredients=r_data['ingredients'],
                            effects=r_data['effects'],
                            difficulty=r_data.get('difficulty', 1)
                        )
                        self.recipes[recipe.recipe_id] = recipe
                    
                    self.logger.info(f"Loaded {len(self.recipes)} recipes from {data_path}")
                else:
                    self.logger.warning(f"No recipes found in {data_path}")
            else:
                self.logger.error(f"Cooking recipes file not found: {data_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to load cooking recipes: {e}")

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
