"""
경험치 및 레벨업 시스템

전투 보상으로 경험치를 획득하고 레벨업
"""

from typing import List, Dict, Any
import math

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
        # 기본 경험치: 적 레벨에 비례하여 증가 (레벨^1.3 * 25)
        # Lv1: 25, Lv2: 48, Lv3: 74, Lv5: 135, Lv10: 499, Lv20: 1462
        base_exp = int(math.pow(enemy_level, 1.3) * 25)

        # 다수의 적: 각 적마다 90%씩 경험치 (무한 파밍 방지)
        total_exp = 0
        for i in range(enemy_count):
            total_exp += int(base_exp * math.pow(0.9, i))

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
        return ExperienceSystem.calculate_enemy_experience(boss_level, 1) * 3

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

        # 골드 계산
        # 기본 골드: 적 레벨 * 10 ~ 20
        import random
        total_gold = 0
        for enemy in enemies:
            enemy_level = getattr(enemy, 'level', floor_number)
            enemy_gold = random.randint(enemy_level * 10, enemy_level * 20)
            if is_boss_fight:
                enemy_gold *= 5  # 보스는 5배
            total_gold += enemy_gold

        # 아이템 드롭
        # 일반 적: 20% 확률, 보스: 100% 확률
        items = []

        if is_boss_fight:
            # 보스는 무조건 2~4개 드롭
            drop_count = random.randint(2, 4)
            for _ in range(drop_count):
                items.append(RewardCalculator._generate_drop(floor_number, is_boss=True))
        else:
            # 일반 적: 각 적마다 20% 확률
            for enemy in enemies:
                if random.random() < 0.2:  # 20%
                    enemy_level = getattr(enemy, 'level', floor_number)
                    items.append(RewardCalculator._generate_drop(enemy_level))

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
    exp_per_member = total_exp

    level_up_info = {}
    for character in alive_members:
        level_ups = ExperienceSystem.add_experience_to_character(character, exp_per_member)
        if level_ups:
            level_up_info[character] = level_ups

    return level_up_info
