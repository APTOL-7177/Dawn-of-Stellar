"""
경험치 및 레벨업 시스템

전투 보상으로 경험치를 획득하고 레벨업
"""

from typing import List, Dict, Any
import math
import random

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.COMBAT)


class ExperienceSystem:
    """경험치 시스템"""

    # 레벨별 필요 경험치 (지수 곡선)
    @staticmethod
    def experience_for_level(level: int) -> int:
        """
        특정 레벨에 도달하기 위해 필요한 총 경험치

        Args:
            level: 목표 레벨

        Returns:
            필요한 총 경험치
        """
        if level <= 1:
            return 0

        # 공식: 100 * (level - 1)^1.5
        # Lv 2: 100, Lv 3: 283, Lv 4: 520, Lv 5: 800, Lv 10: 2700, Lv 20: 8285
        return int(100 * math.pow(level - 1, 1.5))

    @staticmethod
    def experience_to_next_level(current_level: int, current_exp: int) -> int:
        """
        다음 레벨까지 필요한 경험치

        Args:
            current_level: 현재 레벨
            current_exp: 현재 경험치

        Returns:
            다음 레벨까지 필요한 경험치
        """
        total_needed = ExperienceSystem.experience_for_level(current_level + 1)
        return total_needed - current_exp

    @staticmethod
    def calculate_enemy_experience(enemy_level: int, enemy_count: int = 1) -> int:
        """
        적을 처치했을 때 얻는 경험치

        Args:
            enemy_level: 적의 레벨
            enemy_count: 적의 수

        Returns:
            획득 경험치
        """
        # 기본 경험치: 적 레벨에 비례하여 증가 (레벨^1.3 * 50, 2배 증가)
        # Lv1: 50, Lv2: 96, Lv3: 148, Lv5: 270, Lv10: 998, Lv20: 2924
        base_exp = int(math.pow(enemy_level, 1.3) * 50)

        # 다수의 적: 각 적마다 90%씩 경험치 (무한 파밍 방지)
        total_exp = 0
        for i in range(enemy_count):
            total_exp += int(base_exp * math.pow(0.9, i))

        # 난이도 보정
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()
        if difficulty_system:
            exp_mult = difficulty_system.get_exp_multiplier()
            total_exp = int(total_exp * exp_mult)

        return max(1, total_exp)

    @staticmethod
    def calculate_boss_experience(boss_level: int) -> int:
        """
        보스를 처치했을 때 얻는 경험치 (일반 적의 3배)

        Args:
            boss_level: 보스 레벨

        Returns:
            획득 경험치
        """
        # 난이도 배율은 calculate_enemy_experience에서 이미 적용되므로
        # 여기서는 3배만 적용
        base_exp = int(math.pow(boss_level, 1.3) * 25)

        # 난이도 보정
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()
        if difficulty_system:
            exp_mult = difficulty_system.get_exp_multiplier()
            base_exp = int(base_exp * exp_mult)

        return max(1, base_exp * 3)

    @staticmethod
    def add_experience_to_character(character: Any, exp_amount: int) -> List[Dict[str, Any]]:
        """
        캐릭터에게 경험치 추가 및 레벨업 처리

        Args:
            character: 캐릭터 객체
            exp_amount: 획득 경험치

        Returns:
            레벨업 정보 리스트 [{level: 새_레벨, stat_gains: {...}}]
        """
        # 경험치 속성 추가 (없으면)
        if not hasattr(character, 'experience'):
            character.experience = 0

        old_exp = character.experience
        character.experience += exp_amount

        logger.info(f"{character.name}: +{exp_amount} EXP (총 {character.experience})")

        # 레벨업 체크
        level_ups = []
        while True:
            next_level_exp = ExperienceSystem.experience_for_level(character.level + 1)

            if character.experience >= next_level_exp:
                # 레벨업!
                old_stats = {
                    "hp": character.max_hp,
                    "mp": character.max_mp,
                    "strength": character.strength,
                    "defense": character.defense,
                    "magic": character.magic,
                    "spirit": character.spirit,
                    "speed": character.speed,
                    "luck": character.luck
                }

                character.level_up()

                # 스탯 증가량 계산
                stat_gains = {
                    "hp": character.max_hp - old_stats["hp"],
                    "mp": character.max_mp - old_stats["mp"],
                    "strength": character.strength - old_stats["strength"],
                    "defense": character.defense - old_stats["defense"],
                    "magic": character.magic - old_stats["magic"],
                    "spirit": character.spirit - old_stats["spirit"],
                    "speed": character.speed - old_stats["speed"],
                    "luck": character.luck - old_stats["luck"]
                }

                level_ups.append({
                    "level": character.level,
                    "stat_gains": stat_gains
                })

                logger.info(f"🎉 {character.name} 레벨업! Lv.{character.level}")
            else:
                break

        return level_ups


class RewardCalculator:
    """전투 보상 계산"""

    @staticmethod
    def calculate_combat_rewards(
        enemies: List[Any],
        floor_number: int,
        is_boss_fight: bool = False
    ) -> Dict[str, Any]:
        """
        전투 보상 계산

        Args:
            enemies: 처치한 적 리스트
            floor_number: 현재 층수
            is_boss_fight: 보스전 여부

        Returns:
            {
                "experience": 경험치,
                "gold": 골드,
                "items": 아이템 리스트
            }
        """
        # 경험치 계산
        total_exp = 0
        for enemy in enemies:
            enemy_level = getattr(enemy, 'level', floor_number)

            if is_boss_fight:
                total_exp += ExperienceSystem.calculate_boss_experience(enemy_level)
            else:
                total_exp += ExperienceSystem.calculate_enemy_experience(enemy_level, 1)

        # 골드 계산 (2배 증가)
        # 기본 골드: 적 레벨 * 20 ~ 40 (기존 10-20에서 2배)
        import random
        total_gold = 0
        for enemy in enemies:
            enemy_level = getattr(enemy, 'level', floor_number)
            enemy_gold = random.randint(enemy_level * 20, enemy_level * 40)
            if is_boss_fight:
                enemy_gold *= 5  # 보스는 5배
            total_gold += enemy_gold

        # 아이템 드롭
        # 일반 적: 20% 확률, 보스: 100% 확률
        items = []

        if is_boss_fight:
            # 보스는 무조건 2~3개 드롭
            drop_count = random.randint(2, 3)
            for _ in range(drop_count):
                items.append(RewardCalculator._generate_drop(floor_number, is_boss=True))
            # 보스는 추가로 전투용 소비 아이템 0~1개 드롭
            if random.random() < 0.5:  # 50% 확률
                items.append(RewardCalculator._generate_combat_consumable_drop())
            # 보스도 식재료 드롭 (49% 확률, 30% 감소)
            for enemy in enemies:
                if random.random() < 0.49:  # 49% 확률 (70% * 0.7)
                    ingredient = RewardCalculator._generate_ingredient_drop(enemy)
                    if ingredient:
                        items.append(ingredient)
        else:
            # 일반 적: 각 적마다 20% 확률
            for enemy in enemies:
                if random.random() < 0.2:  # 20%
                    enemy_level = getattr(enemy, 'level', floor_number)
                    items.append(RewardCalculator._generate_drop(enemy_level))
                # 일반 적도 5% 확률로 전투용 소비 아이템 드롭
                if random.random() < 0.05:  # 5%
                    items.append(RewardCalculator._generate_combat_consumable_drop())
                
                # 적 타입에 따른 식재료 드롭 (14% 확률, 보스는 제외, 30% 감소)
                if random.random() < 0.14:  # 14% (20% * 0.7)
                    ingredient = RewardCalculator._generate_ingredient_drop(enemy)
                    if ingredient:
                        items.append(ingredient)

        # 골드 획득량 50% 감소
        total_gold = int(total_gold * 0.5)
        
        # 경험치 획득량 30% 감소 후 추가로 2/3으로 감소 (전체적으로 약 46% 수준)
        total_exp = int(total_exp * 0.7 * (2/3))

        return {
            "experience": total_exp,
            "gold": total_gold,
            "items": items
        }

    @staticmethod
    def _generate_drop(level: int, is_boss: bool = False) -> Any:
        """
        아이템 드롭 생성

        Args:
            level: 적 레벨
            is_boss: 보스 드롭 여부

        Returns:
            드롭 아이템
        """
        from src.equipment.item_system import ItemGenerator

        # 보스는 높은 등급 확률 증가
        if is_boss:
            return ItemGenerator.create_random_drop(level, boss_drop=True)
        else:
            return ItemGenerator.create_random_drop(level)

    @staticmethod
    def _generate_consumable_drop() -> Any:
        """
        소비 아이템 드롭 생성 (HP/MP 포션)

        Returns:
            소비 아이템
        """
        from src.equipment.item_system import ItemGenerator
        import random

        # HP/MP 포션 랜덤 선택
        consumable_choices = ["health_potion", "mana_potion"]
        chosen_consumable = random.choice(consumable_choices)
        return ItemGenerator.create_consumable(chosen_consumable)
    
    @staticmethod
    def _generate_combat_consumable_drop() -> Any:
        """
        전투용 소비 아이템 드롭 생성 (공격/수비 아이템)

        Returns:
            전투용 소비 아이템
        """
        from src.equipment.item_system import ItemGenerator
        import random

        # 전투용 아이템 랜덤 선택
        combat_consumables = [
            # 공격적 아이템
            "fire_bomb", "ice_bomb", "poison_bomb", "thunder_grenade",
            "acid_flask", "debuff_attack", "debuff_defense", "debuff_speed",
            "break_brv", "smoke_bomb",
            # 수비적 아이템
            "barrier_crystal", "haste_crystal", "power_tonic", "defense_elixir",
            "regen_crystal", "mp_regen_crystal", "status_cleanse", "revive_crystal"
        ]
        chosen_consumable = random.choice(combat_consumables)
        return ItemGenerator.create_consumable(chosen_consumable)

    @staticmethod
    def _generate_ingredient_drop(enemy: Any) -> Any:
        """
        적 타입에 따른 식재료 드롭 생성

        Args:
            enemy: 처치한 적

        Returns:
            식재료 아이템 또는 None
        """
        from src.gathering.ingredient import IngredientDatabase
        
        # 적 ID 가져오기 (보스는 base_enemy_id 사용)
        enemy_id = getattr(enemy, 'enemy_id', '')
        if enemy_id.startswith('boss_'):
            enemy_id = enemy_id[5:]  # "boss_" 제거
        
        # 적 타입별 식재료 매핑
        ingredient_mapping = {
            # 고기 계열
            "goblin": ["monster_meat"],
            "orc": ["monster_meat", "monster_meat"],
            "ogre": ["monster_meat", "beast_meat"],
            "wolf": ["beast_meat"],
            "troll": ["beast_meat", "monster_meat"],
            
            # 드래곤 계열
            "dragon": ["dragon_meat"],
            "wyvern": ["beast_meat", "dragon_meat"],
            
            # 슬라임 계열
            "slime": ["blue_mushroom", "red_mushroom", "alchemical_catalyst"],
            
            # 생선 계열
            "kraken": ["fish"],
            "siren": ["fish"],
            
            # 언데드 계열 (식재료 드롭 안함)
            "skeleton": [],
            "zombie": [],
            "ghoul": [],
            "banshee": [],
            "death_knight": [],
            "mummy": [],
            "wraith": [],
            "lich": [],
            "vampire": [],
            
            # 엘리멘탈 계열
            "fire_spirit": ["magic_herb", "spice", "fire_essence"],
            "ice_spirit": ["ice", "ice_essence"],
            "thunder_spirit": ["magic_herb", "lightning_essence"],
            "earth_spirit": ["potato", "carrot"],
            
            # 새 계열
            "harpy": ["berry"],
            "griffin": ["beast_meat"],
            
            # 식물 계열
            "treant": ["carrot", "potato", "berry"],
            "thorn_bush": ["berry"],
            
            # 특수
            "mimic": ["magic_herb", "spice"],
            "nightmare": [],
        }
        
        # 매핑에서 식재료 선택
        possible_ingredients = ingredient_mapping.get(enemy_id, ["monster_meat"])  # 기본값: monster_meat
        
        if not possible_ingredients:
            return None  # 드롭 안함
        
        ingredient_id = random.choice(possible_ingredients)
        return IngredientDatabase.get_ingredient(ingredient_id)


def distribute_party_experience(party: List[Any], total_exp: int) -> Dict[Any, List[Dict[str, Any]]]:
    """
    파티 전체에 경험치 분배

    Args:
        party: 파티 멤버 리스트
        total_exp: 총 획득 경험치

    Returns:
        {캐릭터: [레벨업_정보]} 딕셔너리
    """
    # 생존한 멤버만 경험치 획득
    alive_members = [char for char in party if getattr(char, 'is_alive', True)]

    if not alive_members:
        return {}

    # 경험치는 균등 분배
    exp_per_member = total_exp // len(alive_members)

    level_up_info = {}
    for character in alive_members:
        level_ups = ExperienceSystem.add_experience_to_character(character, exp_per_member)
        if level_ups:
            level_up_info[character] = level_ups

    return level_up_info
