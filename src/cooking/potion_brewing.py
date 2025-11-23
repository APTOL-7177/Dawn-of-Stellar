"""
포션 양조 시스템 (Potion Brewing System)

연금술 재료를 사용하여 다양한 포션을 제작하는 시스템
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.core.logger import get_logger
from src.gathering.ingredient import IngredientDatabase

logger = get_logger("alchemy")


class PotionType(Enum):
    """포션 타입"""
    HEALING = "healing"           # HP 회복
    MANA = "mana"                 # MP 회복
    REJUVENATION = "rejuvenation" # HP+MP 회복
    STRENGTH = "strength"         # 공격력 증가
    DEFENSE = "defense"           # 방어력 증가
    SPEED = "speed"               # 속도 증가
    RESISTANCE = "resistance"     # 상태이상 저항
    CLEANSING = "cleansing"       # 상태이상 제거
    REGENERATION = "regeneration" # 지속 회복
    BERSERK = "berserk"          # 광폭화 (공격↑ 방어↓)
    INVISIBILITY = "invisibility" # 투명화
    LUCK = "luck"                 # 행운 증가


@dataclass
class PotionRecipe:
    """포션 레시피"""
    potion_id: str
    name: str
    description: str
    potion_type: PotionType
    ingredients: Dict[str, int]  # {ingredient_id: count}
    effects: Dict[str, Any]      # 효과 수치
    duration: int = 0            # 지속 시간 (턴), 0 = 즉시
    difficulty: int = 1          # 난이도 (1-5)
    
    
class PotionDatabase:
    """포션 데이터베이스"""
    
    RECIPES = {
        # === 기본 포션 (Basic Potions) ===
        "minor_health_potion": PotionRecipe(
            potion_id="minor_health_potion",
            name="소형 체력 포션",
            description="약한 체력 회복 포션. HP 50 회복.",
            potion_type=PotionType.HEALING,
            ingredients={"glass_vial": 1, "pure_water": 1, "magic_herb": 1},
            effects={"hp_restore": 50},
            difficulty=1
        ),
        
        "health_potion": PotionRecipe(
            potion_id="health_potion",
            name="체력 포션",
            description="중간 체력 회복 포션. HP 150 회복.",
            potion_type=PotionType.HEALING,
            ingredients={"glass_vial": 1, "pure_water": 2, "magic_herb": 2, "honey": 1},
            effects={"hp_restore": 150},
            difficulty=2
        ),
        
        "greater_health_potion": PotionRecipe(
            potion_id="greater_health_potion",
            name="대형 체력 포션",
            description="강력한 체력 회복 포션. HP 300 회복.",
            potion_type=PotionType.HEALING,
            ingredients={"glass_vial": 1, "pure_water": 3, "mana_blossom": 2, "golden_apple": 1},
            effects={"hp_restore": 300},
            difficulty=3
        ),
        
        "minor_mana_potion": PotionRecipe(
            potion_id="minor_mana_potion",
            name="소형 마나 포션",
            description="약한 마나 회복 포션. MP 30 회복.",
            potion_type=PotionType.MANA,
            ingredients={"glass_vial": 1, "pure_water": 1, "blue_mushroom": 1},
            effects={"mp_restore": 30},
            difficulty=1
        ),
        
        "mana_potion": PotionRecipe(
            potion_id="mana_potion",
            name="마나 포션",
            description="중간 마나 회복 포션. MP 80 회복.",
            potion_type=PotionType.MANA,
            ingredients={"glass_vial": 1, "pure_water": 2, "mana_blossom": 1, "blue_mushroom": 1},
            effects={"mp_restore": 80},
            difficulty=2
        ),
        
        "greater_mana_potion": PotionRecipe(
            potion_id="greater_mana_potion",
            name="대형 마나 포션",
            description="강력한 마나 회복 포션. MP 200 회복.",
            potion_type=PotionType.MANA,
            ingredients={"glass_vial": 1, "pure_water": 3, "mana_blossom": 3, "star_fruit": 1},
            effects={"mp_restore": 200},
            difficulty=3
        ),
        
        # === 복합 포션 (Combination Potions) ===
        "rejuvenation_potion": PotionRecipe(
            potion_id="rejuvenation_potion",
            name="회춘 포션",
            description="HP와 MP를 동시에 회복. HP 100, MP 50 회복.",
            potion_type=PotionType.REJUVENATION,
            ingredients={"glass_vial": 1, "pure_water": 2, "magic_herb": 1, "mana_blossom": 1, "honey": 1},
            effects={"hp_restore": 100, "mp_restore": 50},
            difficulty=3
        ),
        
        # === 버프 포션 (Buff Potions) ===
        "strength_potion": PotionRecipe(
            potion_id="strength_potion",
            name="힘의 포션",
            description="공격력을 크게 증가시킨다. 20턴 지속.",
            potion_type=PotionType.STRENGTH,
            ingredients={"glass_vial": 1, "pure_water": 1, "fire_essence": 1, "beast_meat": 2},
            effects={"strength_bonus": 15},
            duration=20,
            difficulty=3
        ),
        
        "defense_potion": PotionRecipe(
            potion_id="defense_potion",
            name="방어의 포션",
            description="방어력을 크게 증가시킨다. 20턴 지속.",
            potion_type=PotionType.DEFENSE,
            ingredients={"glass_vial": 1, "pure_water": 1, "ice_essence": 1, "stone": 2},
            effects={"defense_bonus": 15},
            duration=20,
            difficulty=3
        ),
        
        "speed_potion": PotionRecipe(
            potion_id="speed_potion",
            name="신속의 포션",
            description="속도를 크게 증가시킨다. 15턴 지속.",
            potion_type=PotionType.SPEED,
            ingredients={"glass_vial": 1, "pure_water": 1, "lightning_essence": 1, "berry": 3},
            effects={"speed_bonus": 20},
            duration=15,
            difficulty=3
        ),
        
        # === 특수 포션 (Special Potions) ===
        "regeneration_potion": PotionRecipe(
            potion_id="regeneration_potion",
            name="재생 포션",
            description="매 턴 HP를 회복한다. 10턴 동안 턴당 20 HP 회복.",
            potion_type=PotionType.REGENERATION,
            ingredients={"glass_vial": 1, "pure_water": 2, "mana_blossom": 2, "truffle": 1},
            effects={"regen_per_turn": 20},
            duration=10,
            difficulty=4
        ),
        
        "cleansing_potion": PotionRecipe(
            potion_id="cleansing_potion",
            name="정화 포션",
            description="모든 상태이상을 제거한다.",
            potion_type=PotionType.CLEANSING,
            ingredients={"glass_vial": 1, "pure_water": 3, "magic_herb": 2, "alchemical_catalyst": 1},
            effects={"cleanse_all": True},
            difficulty=3
        ),
        
        "berserk_potion": PotionRecipe(
            potion_id="berserk_potion",
            name="광폭화 포션",
            description="공격력 +30%, 방어력 -20%. 15턴 지속.",
            potion_type=PotionType.BERSERK,
            ingredients={"glass_vial": 1, "pure_water": 1, "fire_essence": 2, "dragon_meat": 1},
            effects={"strength_percent": 30, "defense_percent": -20},
            duration=15,
            difficulty=4
        ),
        
        "resistance_potion": PotionRecipe(
            potion_id="resistance_potion",
            name="저항의 포션",
            description="상태이상 저항 +50%. 20턴 지속.",
            potion_type=PotionType.RESISTANCE,
            ingredients={"glass_vial": 1, "pure_water": 2, "alchemical_catalyst": 2, "mandrake": 1},
            effects={"status_resistance": 50},
            duration=20,
            difficulty=4
        ),
        
        "luck_potion": PotionRecipe(
            potion_id="luck_potion",
            name="행운의 포션",
            description="크리티컬 확률 +15%. 30턴 지속.",
            potion_type=PotionType.LUCK,
            ingredients={"glass_vial": 1, "pure_water": 1, "star_fruit": 1, "golden_apple": 1},
            effects={"crit_rate": 15},
            duration=30,
            difficulty=5
        ),

        # === 고급 포션 (Advanced Potions) - 새 재료 사용 ===
        "elixir_of_life": PotionRecipe(
            potion_id="elixir_of_life",
            name="생명의 영약",
            description="최대 HP를 넘어 회복한다. HP 500 회복, 상처 100 치료.",
            potion_type=PotionType.HEALING,
            ingredients={"glass_vial": 1, "pure_water": 3, "sunblossom": 2, "ancient_root": 1, "light_essence": 1},
            effects={"hp_restore": 500, "wound_cure": 100},
            difficulty=5
        ),

        "ether_draught": PotionRecipe(
            potion_id="ether_draught",
            name="에테르 음료",
            description="마나를 완전히 회복한다. MP 전체 회복.",
            potion_type=PotionType.MANA,
            ingredients={"glass_vial": 1, "pure_water": 2, "ether": 1, "mana_blossom": 3, "crystal_shard": 1},
            effects={"mp_restore_percent": 100},
            difficulty=5
        ),

        "invisibility_potion": PotionRecipe(
            potion_id="invisibility_potion",
            name="투명화 포션",
            description="일시적으로 투명해진다. 5턴 동안 회피율 +80%.",
            potion_type=PotionType.INVISIBILITY,
            ingredients={"glass_vial": 1, "pure_water": 2, "ghost_essence": 2, "moonflower": 1},
            effects={"evasion_bonus": 80},
            duration=5,
            difficulty=5
        ),

        "titans_strength": PotionRecipe(
            potion_id="titans_strength",
            name="거인의 힘",
            description="초인적인 힘을 얻는다. 공격력 +50, 25턴 지속.",
            potion_type=PotionType.STRENGTH,
            ingredients={"glass_vial": 1, "pure_water": 2, "golem_core": 1, "dragon_bone": 1, "fire_essence": 2},
            effects={"strength_bonus": 50},
            duration=25,
            difficulty=5
        ),

        "stone_skin": PotionRecipe(
            potion_id="stone_skin",
            name="석화 피부",
            description="피부가 돌처럼 단단해진다. 방어력 +50, 20턴 지속.",
            potion_type=PotionType.DEFENSE,
            ingredients={"glass_vial": 1, "pure_water": 2, "earth_essence": 2, "obsidian": 2, "golem_core": 1},
            effects={"defense_bonus": 50},
            duration=20,
            difficulty=5
        ),

        "wind_walker": PotionRecipe(
            potion_id="wind_walker",
            name="바람 걷기",
            description="바람처럼 빨라진다. 속도 +40, 회피율 +20%, 15턴 지속.",
            potion_type=PotionType.SPEED,
            ingredients={"glass_vial": 1, "pure_water": 1, "wind_essence": 3, "moonflower": 1},
            effects={"speed_bonus": 40, "evasion_bonus": 20},
            duration=15,
            difficulty=4
        ),

        "vampiric_elixir": PotionRecipe(
            potion_id="vampiric_elixir",
            name="흡혈 영약",
            description="생명력 흡수 능력을 부여한다. 피해의 30%를 HP로 회복, 20턴.",
            potion_type=PotionType.REGENERATION,
            ingredients={"glass_vial": 1, "pure_water": 2, "vampire_fang": 1, "dark_essence": 2},
            effects={"lifesteal_percent": 30},
            duration=20,
            difficulty=5
        ),

        "holy_water": PotionRecipe(
            potion_id="holy_water",
            name="성수",
            description="언데드에게 특효. 상태이상 제거 + HP 100 회복.",
            potion_type=PotionType.CLEANSING,
            ingredients={"glass_vial": 1, "pure_water": 3, "light_essence": 2, "sunblossom": 2},
            effects={"cleanse_all": True, "hp_restore": 100, "undead_damage": 200},
            difficulty=4
        ),

        "cursed_brew": PotionRecipe(
            potion_id="cursed_brew",
            name="저주받은 물약",
            description="모든 능력치 +20%, HP/MP -50%. 위험하지만 강력하다. 15턴.",
            potion_type=PotionType.BERSERK,
            ingredients={"glass_vial": 1, "pure_water": 1, "cursed_relic": 1, "demon_horn": 1, "dark_essence": 2},
            effects={"all_stats_percent": 20, "hp_percent": -50, "mp_percent": -50},
            duration=15,
            difficulty=5
        ),

        "philosophers_elixir": PotionRecipe(
            potion_id="philosophers_elixir",
            name="현자의 영약",
            description="전설의 만능 포션. HP/MP 전체 회복 + 모든 상태이상 제거.",
            potion_type=PotionType.REJUVENATION,
            ingredients={"glass_vial": 1, "pure_water": 3, "philosophers_stone_fragment": 1, "stardust": 1, "ether": 2},
            effects={"hp_restore_percent": 100, "mp_restore_percent": 100, "cleanse_all": True},
            difficulty=5
        ),

        "mana_shield": PotionRecipe(
            potion_id="mana_shield",
            name="마나 보호막",
            description="MP로 데미지를 흡수한다. 피해의 50%를 MP로 대신 받음, 15턴.",
            potion_type=PotionType.DEFENSE,
            ingredients={"glass_vial": 1, "pure_water": 2, "crystal_shard": 2, "ether": 1},
            effects={"mana_shield": 50},
            duration=15,
            difficulty=5
        ),

        "moonlight_brew": PotionRecipe(
            potion_id="moonlight_brew",
            name="달빛 물약",
            description="밤의 힘을 얻는다. 크리티컬 확률 +25%, 크리티컬 데미지 +50%. 20턴.",
            potion_type=PotionType.LUCK,
            ingredients={"glass_vial": 1, "pure_water": 2, "moonflower": 3, "void_lotus": 1, "dark_essence": 1},
            effects={"crit_rate": 25, "crit_damage": 50},
            duration=20,
            difficulty=5
        ),
    }
    
    @classmethod
    def get_recipe(cls, potion_id: str) -> Optional[PotionRecipe]:
        """레시피 가져오기"""
        return cls.RECIPES.get(potion_id)
    
    @classmethod
    def get_all_recipes(cls) -> List[PotionRecipe]:
        """모든 레시피 가져오기"""
        return list(cls.RECIPES.values())


class PotionBrewer:
    """포션 제조기"""
    
    @staticmethod
    def can_brew(recipe: PotionRecipe, inventory: Dict[str, int]) -> bool:
        """
        제조 가능 여부 확인
        
        Args:
            recipe: 포션 레시피
            inventory: 플레이어 인벤토리 {item_id: count}
            
        Returns:
            제조 가능 여부
        """
        for ingredient_id, required_count in recipe.ingredients.items():
            if inventory.get(ingredient_id, 0) < required_count:
                return False
        return True
    
    @staticmethod
    def brew_potion(recipe: PotionRecipe, player: Any) -> bool:
        """
        포션 제조
        
        Args:
            recipe: 포션 레시피
            player: 플레이어 객체
            
        Returns:
            성공 여부
        """
        # 재료 확인
        if not PotionBrewer.can_brew(recipe, player.inventory):
            logger.warning(f"재료 부족: {recipe.name}")
            return False
        
        # 재료 소모
        for ingredient_id, count in recipe.ingredients.items():
            player.remove_item(ingredient_id, count)
        
        # 포션 생성 (ItemGenerator 사용)
        from src.equipment.item_system import ItemGenerator
        potion = ItemGenerator.create_consumable(recipe.potion_id)
        
        # 인벤토리에 추가
        player.add_item(potion)
        
        logger.info(f"포션 제조 성공: {recipe.name}")
        return True
