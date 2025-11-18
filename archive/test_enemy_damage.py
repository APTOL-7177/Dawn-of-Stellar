#!/usr/bin/env python3
"""
적 데미지 테스트 스크립트

적들의 BRV 공격과 HP 공격 피해량을 테스트합니다.
"""

import sys
sys.path.insert(0, '/home/user/Dos')

from src.core.config import initialize_config
from src.world.enemy_generator import ENEMY_TEMPLATES, SimpleEnemy
from src.character.character import Character
from src.combat.damage_calculator import DamageCalculator
from src.combat.brave_system import BraveSystem

def test_enemy_damage():
    """적의 피해량 테스트"""

    # 설정 초기화
    initialize_config()

    # 테스트용 플레이어 캐릭터 생성 (전사, 레벨 1)
    player = Character("테스트 전사", "warrior")

    print("=" * 80)
    print("적 데미지 테스트")
    print("=" * 80)
    print(f"\n플레이어: {player.name} (Lv.{player.level})")
    print(f"HP: {player.max_hp}, 방어력: {player.defense}, 마법방어: {player.spirit}")
    print(f"max_brv: {player.max_brv}, current_brv: {player.current_brv}\n")

    # 데미지 계산기 초기화
    damage_calc = DamageCalculator()
    brave_system = BraveSystem()

    # 테스트할 적 목록
    test_enemies = [
        ("slime", "슬라임"),
        ("goblin", "고블린"),
        ("orc", "오크"),
        ("dark_mage", "다크 메이지"),
        ("demon", "악마"),
        ("dragon", "드래곤"),
        ("boss_chimera", "키메라 (보스)"),
        ("sephiroth", "세피로스"),
    ]

    print("-" * 80)
    print(f"{'적 이름':<15} {'Lv1 BRV':<10} {'Lv1 HP':<10} {'스탯':<20} {'평균 BRV 데미지':<15}")
    print("-" * 80)

    for enemy_id, enemy_name in test_enemies:
        template = ENEMY_TEMPLATES[enemy_id]
        enemy = SimpleEnemy(template, level_modifier=1.0)

        # BRV 데미지 계산 (회피 무시, 여러 번 계산하여 평균)
        total_brv_dmg = 0
        num_samples = 10
        for _ in range(num_samples):
            brv_dmg_result = damage_calc.calculate_brv_damage(
                attacker=enemy,
                defender=player,
                skill_multiplier=1.5,  # 일반적인 적 스킬 배율
                ignore_evasion=True  # 회피 무시
            )
            total_brv_dmg += brv_dmg_result.final_damage

        avg_brv_damage = total_brv_dmg // num_samples

        # HP 데미지 계산 (적의 current_brv로)
        # HP 공격은 현재 BRV를 소비해서 데미지를 입힘
        hp_damage = int(enemy.current_brv * 0.25)  # HP 공격은 BRV의 1/4 데미지

        stats_str = f"ATK{enemy.physical_attack}/DEF{enemy.physical_defense}"
        print(f"{enemy_name:<15} {enemy.current_brv:<10} {hp_damage:<10} {stats_str:<20} {avg_brv_damage:<15}")

    print("-" * 80)
    print("\n설명:")
    print("- Lv1 BRV: 전투 시작 시 적의 초기 BRV")
    print("- Lv1 HP: 적이 HP 공격 시 입히는 예상 데미지 (초기 BRV의 1/4)")
    print("- 스탯: 적의 공격력/방어력")
    print("- 평균 BRV 데미지: 적이 BRV 스킬로 공격 시 플레이어가 받는 평균 데미지")
    print("  (스킬 배율 1.5, 회피 무시, 10회 평균)")
    print("\n참고:")
    print("- 적의 스킬 배율: 일반 1.5~1.8, 강력 2.0~2.5, 궁극기 2.5~3.0")
    print("- BRV 공격은 플레이어의 BRV를 깎고 적의 BRV를 올립니다")
    print("- HP 공격은 적의 현재 BRV를 소비하여 플레이어 HP에 직접 데미지")
    print("- 플레이어 방어력: " + str(player.defense) + ", 마법방어: " + str(player.spirit))
    print("=" * 80)

if __name__ == "__main__":
    test_enemy_damage()
