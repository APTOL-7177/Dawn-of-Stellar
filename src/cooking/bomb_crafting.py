"""
폭탄 제작 시스템 (Bomb Crafting System)

폭발물 재료를 사용하여 다양한 폭탄을 제작하는 시스템
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.core.logger import get_logger

logger = get_logger("alchemy")


class BombType(Enum):
    """폭탄 타입"""
    FIRE = "fire"             # 화염 폭탄
    ICE = "ice"               # 냉기 폭탄
    LIGHTNING = "lightning"   # 번개 폭탄
    POISON = "poison"         # 독 폭탄
    SMOKE = "smoke"           # 연막탄
    STUN = "stun"             # 기절 폭탄
    FRAGMENTATION = "fragmentation"  # 파편 폭탄
    ACID = "acid"             # 산성 폭탄


@dataclass
class BombRecipe:
    """폭탄 레시피"""
    bomb_id: str
    name: str
    description: str
    bomb_type: BombType
    ingredients: Dict[str, int]  # {ingredient_id: count}
    damage: int                  # 기본 데미지
    aoe_range: int = 1           # 범위 (1 = 단일, 2+ = AOE)
    special_effect: Dict[str, Any] = None  # 특수 효과
    difficulty: int = 1          # 난이도 (1-5)


class BombDatabase:
    """폭탄 데이터베이스"""
    
    RECIPES = {
        # === 기본 폭탄 (Basic Bombs) ===
        "fire_bomb": BombRecipe(
            bomb_id="fire_bomb",
            name="화염 폭탄",
            description="폭발과 함께 화염을 퍼뜨린다. 데미지 80, 화상 3턴.",
            bomb_type=BombType.FIRE,
            ingredients={"bomb_casing": 1, "gunpowder": 2, "fuse": 1, "fire_essence": 1},
            damage=80,
            aoe_range=2,
            special_effect={"burn_damage": 15, "burn_duration": 3},
            difficulty=2
        ),
        
        "ice_bomb": BombRecipe(
            bomb_id="ice_bomb",
            name="냉기 폭탄",
            description="폭발과 함께 냉기를 퍼뜨린다. 데미지 70, 둔화 3턴.",
            bomb_type=BombType.ICE,
            ingredients={"bomb_casing": 1, "gunpowder": 2, "fuse": 1, "ice_essence": 1},
            damage=70,
            aoe_range=2,
            special_effect={"slow_percent": 30, "slow_duration": 3},
            difficulty=2
        ),
        
        "thunder_grenade": BombRecipe(
            bomb_id="thunder_grenade",
            name="번개 수류탄",
            description="폭발과 함께 전기 충격을 준다. 데미지 90, 마비 2턴.",
            bomb_type=BombType.LIGHTNING,
            ingredients={"bomb_casing": 1, "gunpowder": 2, "fuse": 1, "lightning_essence": 1},
            damage=90,
            aoe_range=2,
            special_effect={"stun_chance": 50, "stun_duration": 2},
            difficulty=2
        ),
        
        # === 상태이상 폭탄 (Status Effect Bombs) ===
        "poison_bomb": BombRecipe(
            bomb_id="poison_bomb",
            name="독 폭탄",
            description="독가스를 퍼뜨린다. 데미지 40, 맹독 5턴.",
            bomb_type=BombType.POISON,
            ingredients={"bomb_casing": 1, "gunpowder": 1, "fuse": 1, "red_mushroom": 3},
            damage=40,
            aoe_range=3,
            special_effect={"poison_damage": 20, "poison_duration": 5},
            difficulty=3
        ),
        
        "smoke_bomb": BombRecipe(
            bomb_id="smoke_bomb",
            name="연막탄",
            description="연막을 퍼뜨려 시야를 차단한다. 명중률 -50%, 3턴.",
            bomb_type=BombType.SMOKE,
            ingredients={"bomb_casing": 1, "gunpowder": 1, "fuse": 1, "wood": 2},
            damage=10,
            aoe_range=3,
            special_effect={"accuracy_reduction": 50, "duration": 3},
            difficulty=1
        ),
        
        "acid_flask": BombRecipe(
            bomb_id="acid_flask",
            name="산성 플라스크",
            description="강산을 퍼뜨린다. 데미지 60, 방어력 -30%, 4턴.",
            bomb_type=BombType.ACID,
            ingredients={"glass_vial": 2, "alchemical_catalyst": 2, "slime_jelly": 3},
            damage=60,
            aoe_range=1,
            special_effect={"defense_reduction": 30, "duration": 4},
            difficulty=3
        ),
        
        # === 고급 폭탄 (Advanced Bombs) ===
        "fragmentation_grenade": BombRecipe(
            bomb_id="fragmentation_grenade",
            name="파편 수류탄",
            description="금속 파편을 사방으로 뿌린다. 데미지 120, 광범위.",
            bomb_type=BombType.FRAGMENTATION,
            ingredients={"bomb_casing": 2, "gunpowder": 3, "fuse": 1, "metal_scrap": 5},
            damage=120,
            aoe_range=3,
            difficulty=3
        ),
        
        "stun_grenade": BombRecipe(
            bomb_id="stun_grenade",
            name="섬광탄",
            description="강렬한 빛과 소리로 기절시킨다. 데미지 30, 기절 100%, 2턴.",
            bomb_type=BombType.STUN,
            ingredients={"bomb_casing": 1, "gunpowder": 2, "fuse": 1, "lightning_essence": 1, "salt": 2},
            damage=30,
            aoe_range=2,
            special_effect={"stun_chance": 100, "stun_duration": 2},
            difficulty=4
        ),
        
        "explosive_crystal_bomb": BombRecipe(
            bomb_id="explosive_crystal_bomb",
            name="폭발 결정 폭탄",
            description="불안정한 결정의 힘을 해방한다. 데미지 200, 초광범위.",
            bomb_type=BombType.FIRE,
            ingredients={"bomb_casing": 2, "gunpowder": 5, "fuse": 2, "explosive_crystal": 2},
            damage=200,
            aoe_range=4,
            special_effect={"burn_damage": 30, "burn_duration": 5},
            difficulty=5
        ),
        
        # === 특수 폭탄 (Special Bombs) ===
        "napalm_bomb": BombRecipe(
            bomb_id="napalm_bomb",
            name="네이팜 폭탄",
            description="끈적한 화염을 퍼뜨린다. 데미지 100, 강력한 화상 7턴.",
            bomb_type=BombType.FIRE,
            ingredients={"bomb_casing": 2, "gunpowder": 3, "fuse": 1, "fire_essence": 2, "honey": 2},
            damage=100,
            aoe_range=3,
            special_effect={"burn_damage": 25, "burn_duration": 7},
            difficulty=4
        ),
        
        "cryo_grenade": BombRecipe(
            bomb_id="cryo_grenade",
            name="극저온 수류탄",
            description="주변을 얼려버린다. 데미지 80, 동결 2턴.",
            bomb_type=BombType.ICE,
            ingredients={"bomb_casing": 1, "gunpowder": 2, "fuse": 1, "ice_essence": 2, "ice": 3},
            damage=80,
            aoe_range=2,
            special_effect={"freeze_chance": 60, "freeze_duration": 2},
            difficulty=4
        ),
        
        "emp_grenade": BombRecipe(
            bomb_id="emp_grenade",
            name="EMP 수류탄",
            description="전자기 펄스를 방출한다. 데미지 50, MP 소실 100.",
            bomb_type=BombType.LIGHTNING,
            ingredients={"bomb_casing": 1, "gunpowder": 2, "fuse": 1, "lightning_essence": 2, "metal_scrap": 3},
            damage=50,
            aoe_range=3,
            special_effect={"mp_drain": 100},
            difficulty=4
        ),
        
        # === 전설 폭탄 (Legendary Bombs) - 새 재료 사용 ===
        "dragons_fury": BombRecipe(
            bomb_id="dragons_fury",
            name="용의 분노",
            description="드래곤의 힘이 담긴 폭탄. 데미지 250, 극대 화상 10턴.",
            bomb_type=BombType.FIRE,
            ingredients={"bomb_casing": 3, "gunpowder": 5, "fuse": 2, "fire_essence": 3, "dragon_bone": 1, "sulfur": 2},
            damage=250,
            aoe_range=4,
            special_effect={"burn_damage": 40, "burn_duration": 10},
            difficulty=5
        ),

        "absolute_zero": BombRecipe(
            bomb_id="absolute_zero",
            name="절대영도",
            description="모든 것을 얼려버린다. 데미지 200, 동결 100%, 3턴.",
            bomb_type=BombType.ICE,
            ingredients={"bomb_casing": 2, "gunpowder": 4, "fuse": 2, "ice_essence": 4, "crystal_shard": 2},
            damage=200,
            aoe_range=3,
            special_effect={"freeze_chance": 100, "freeze_duration": 3},
            difficulty=5
        ),

        "thunder_storm": BombRecipe(
            bomb_id="thunder_storm",
            name="뇌우 폭탄",
            description="번개 폭풍을 일으킨다. 데미지 180, 광범위 마비.",
            bomb_type=BombType.LIGHTNING,
            ingredients={"bomb_casing": 2, "gunpowder": 4, "fuse": 2, "lightning_essence": 3, "crystal_shard": 1, "metal_scrap": 5},
            damage=180,
            aoe_range=4,
            special_effect={"stun_chance": 80, "stun_duration": 3},
            difficulty=5
        ),

        "void_grenade": BombRecipe(
            bomb_id="void_grenade",
            name="공허 수류탄",
            description="공허의 힘을 방출한다. 데미지 150, 모든 버프 제거 + 약화.",
            bomb_type=BombType.POISON,
            ingredients={"bomb_casing": 2, "gunpowder": 3, "fuse": 1, "void_lotus": 2, "dark_essence": 2, "cursed_relic": 1},
            damage=150,
            aoe_range=3,
            special_effect={"dispel_buffs": True, "weakness": 30, "duration": 5},
            difficulty=5
        ),

        "mithril_shrapnel": BombRecipe(
            bomb_id="mithril_shrapnel",
            name="미스릴 파편탄",
            description="미스릴 파편이 사방으로 튄다. 데미지 200, 방어력 무시 50%.",
            bomb_type=BombType.FRAGMENTATION,
            ingredients={"bomb_casing": 2, "gunpowder": 4, "fuse": 2, "mithril_ore": 2, "metal_scrap": 5},
            damage=200,
            aoe_range=4,
            special_effect={"armor_penetration": 50},
            difficulty=5
        ),

        "cursed_explosive": BombRecipe(
            bomb_id="cursed_explosive",
            name="저주받은 폭발물",
            description="저주의 힘이 담긴 폭탄. 데미지 220, 저주 3턴 (모든 능력치 -30%).",
            bomb_type=BombType.POISON,
            ingredients={"bomb_casing": 2, "gunpowder": 4, "fuse": 2, "cursed_relic": 2, "demon_horn": 1, "dark_essence": 2},
            damage=220,
            aoe_range=3,
            special_effect={"curse": {"all_stats_percent": -30, "duration": 3}},
            difficulty=5
        ),

        "holy_grenade": BombRecipe(
            bomb_id="holy_grenade",
            name="성스러운 수류탄",
            description="언데드와 악마에게 치명적. 데미지 300 (언데드/악마), 정화 효과.",
            bomb_type=BombType.STUN,
            ingredients={"bomb_casing": 1, "gunpowder": 3, "fuse": 1, "light_essence": 3, "sunblossom": 2},
            damage=150,
            aoe_range=3,
            special_effect={"undead_demon_damage": 300, "cleanse_area": True},
            difficulty=5
        ),

        "stardust_bomb": BombRecipe(
            bomb_id="stardust_bomb",
            name="별가루 폭탄",
            description="별의 힘이 폭발한다. 데미지 350, 모든 원소 효과.",
            bomb_type=BombType.FIRE,
            ingredients={"bomb_casing": 3, "explosive_crystal": 3, "fuse": 2, "stardust": 2, "fire_essence": 1, "ice_essence": 1, "lightning_essence": 1},
            damage=350,
            aoe_range=5,
            special_effect={"burn_damage": 30, "freeze_chance": 40, "stun_chance": 40, "duration": 5},
            difficulty=5
        ),
    }
    
    @classmethod
    def get_recipe(cls, bomb_id: str) -> Optional[BombRecipe]:
        """레시피 가져오기"""
        return cls.RECIPES.get(bomb_id)
    
    @classmethod
    def get_all_recipes(cls) -> List[BombRecipe]:
        """모든 레시피 가져오기"""
        return list(cls.RECIPES.values())


class BombCrafter:
    """폭탄 제작자"""
    
    @staticmethod
    def can_craft(recipe: BombRecipe, inventory: Dict[str, int]) -> bool:
        """
        제작 가능 여부 확인
        
        Args:
            recipe: 폭탄 레시피
            inventory: 플레이어 인벤토리 {item_id: count}
            
        Returns:
            제작 가능 여부
        """
        for ingredient_id, required_count in recipe.ingredients.items():
            if inventory.get(ingredient_id, 0) < required_count:
                return False
        return True
    
    @staticmethod
    def craft_bomb(recipe: BombRecipe, player: Any) -> bool:
        """
        폭탄 제작
        
        Args:
            recipe: 폭탄 레시피
            player: 플레이어 객체
            
        Returns:
            성공 여부
        """
        # 재료 확인
        if not BombCrafter.can_craft(recipe, player.inventory):
            logger.warning(f"재료 부족: {recipe.name}")
            return False
        
        # 재료 소모
        for ingredient_id, count in recipe.ingredients.items():
            player.remove_item(ingredient_id, count)
        
        # 폭탄 생성 (ItemGenerator 사용)
        from src.equipment.item_system import ItemGenerator
        bomb = ItemGenerator.create_consumable(recipe.bomb_id)
        
        # 인벤토리에 추가
        player.add_item(bomb)
        
        logger.info(f"폭탄 제작 성공: {recipe.name}")
        return True
