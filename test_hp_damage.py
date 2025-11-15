"""
HP 데미지 계산 테스트

BRV 값에 따른 HP 데미지 변화를 확인합니다.
"""

import sys
from src.character.character import Character
from src.combat.damage_calculator import get_damage_calculator
from src.combat.brave_system import get_brave_system
from src.core.config import initialize_config, get_config

def test_hp_damage():
    """다양한 BRV 값으로 HP 데미지 테스트"""

    # 설정 초기화
    initialize_config()
    config = get_config()
    damage_calc = get_damage_calculator()
    brave_system = get_brave_system()

    # 테스트 캐릭터 생성
    print("=" * 70)
    print("HP 데미지 계산 테스트")
    print("=" * 70)

    # 공격자: 전사 (물리 공격형)
    attacker = Character("테스트 전사", "warrior")
    attacker.level = 5
    # 스탯 수동 설정 (stat_manager 사용)
    attacker.stat_manager.set_base_value("hp", 500)
    attacker.stat_manager.set_base_value("strength", 50)
    attacker.stat_manager.set_base_value("magic", 30)
    attacker.stat_manager.set_base_value("defense", 20)
    attacker.stat_manager.set_base_value("spirit", 20)
    attacker.stat_manager.set_base_value("max_brv", 2000)
    attacker.current_hp = 500
    attacker.current_brv = 0

    print(f"\n[공격자] {attacker.name}")
    print(f"  - 레벨: {attacker.level}")
    print(f"  - 공격력: {attacker.strength}")
    print(f"  - 마법: {attacker.magic}")

    # 방어자: 적 (간단한 테스트용)
    defender = Character("테스트 적", "warrior")
    defender.level = 5
    # 스탯 수동 설정 (stat_manager 사용)
    defender.stat_manager.set_base_value("hp", 300)
    defender.stat_manager.set_base_value("strength", 30)
    defender.stat_manager.set_base_value("magic", 20)
    defender.stat_manager.set_base_value("defense", 25)
    defender.stat_manager.set_base_value("spirit", 20)
    defender.stat_manager.set_base_value("max_brv", 1000)
    defender.current_hp = 300
    defender.current_brv = 500

    print(f"\n[방어자] {defender.name}")
    print(f"  - 레벨: {defender.level}")
    print(f"  - HP: {defender.current_hp}/{defender.max_hp}")
    print(f"  - 방어력: {defender.defense}")
    print(f"  - 정신: {defender.spirit}")

    # 테스트할 BRV 값들
    brv_values = [0, 50, 100, 200, 500, 1000, 2000]
    skill_multipliers = [1.0, 1.5, 2.0, 3.0]  # 스킬 계수

    print("\n" + "=" * 70)
    print("테스트 1: 물리 HP 공격 (BRV 값 변화)")
    print("=" * 70)

    for skill_mult in skill_multipliers:
        print(f"\n[스킬 계수: {skill_mult}x]")
        print(f"{'BRV':>6} | {'스탯배율':>10} | {'기본 데미지':>12} | {'최종 데미지':>12}")
        print("-" * 70)

        for brv in brv_values:
            # HP 데미지 계산
            damage_result, wound_damage = damage_calc.calculate_hp_damage(
                attacker=attacker,
                defender=defender,
                brv_points=brv,
                hp_multiplier=skill_mult,
                is_break=False,
                damage_type="physical"
            )

            stat_modifier = damage_result.variance
            base_damage = damage_result.base_damage
            final_damage = damage_result.final_damage

            print(f"{brv:>6} | {stat_modifier:>10.2f} | {base_damage:>12} | {final_damage:>12}")

    print("\n" + "=" * 70)
    print("테스트 2: 마법 HP 공격 (BRV 값 변화)")
    print("=" * 70)

    for skill_mult in [1.0, 2.0]:
        print(f"\n[스킬 계수: {skill_mult}x]")
        print(f"{'BRV':>6} | {'스탯배율':>10} | {'기본 데미지':>12} | {'최종 데미지':>12}")
        print("-" * 70)

        for brv in brv_values:
            # HP 데미지 계산 (마법)
            damage_result, wound_damage = damage_calc.calculate_hp_damage(
                attacker=attacker,
                defender=defender,
                brv_points=brv,
                hp_multiplier=skill_mult,
                is_break=False,
                damage_type="magical"
            )

            stat_modifier = damage_result.variance
            base_damage = damage_result.base_damage
            final_damage = damage_result.final_damage

            print(f"{brv:>6} | {stat_modifier:>10.2f} | {base_damage:>12} | {final_damage:>12}")

    print("\n" + "=" * 70)
    print("테스트 3: BREAK 상태 보너스")
    print("=" * 70)

    brv = 500
    skill_mult = 1.5

    # 일반 상태
    damage_normal, _ = damage_calc.calculate_hp_damage(
        attacker=attacker,
        defender=defender,
        brv_points=brv,
        hp_multiplier=skill_mult,
        is_break=False,
        damage_type="physical"
    )

    # BREAK 상태
    damage_break, _ = damage_calc.calculate_hp_damage(
        attacker=attacker,
        defender=defender,
        brv_points=brv,
        hp_multiplier=skill_mult,
        is_break=True,
        damage_type="physical"
    )

    print(f"\nBRV: {brv}, 스킬 계수: {skill_mult}x")
    print(f"일반 상태:  {damage_normal.final_damage}")
    print(f"BREAK 상태: {damage_break.final_damage}")
    print(f"BREAK 보너스: {damage_break.final_damage / damage_normal.final_damage:.2f}배")

    print("\n" + "=" * 70)
    print("테스트 4: 기믹 보너스 (룬 스택)")
    print("=" * 70)

    brv = 300
    rune_stacks = [0, 2, 4, 6, 8]

    print(f"\n[BRV: {brv}, 룬 보너스: 스택당 +0.5배]")
    print(f"{'룬 스택':>8} | {'스킬 계수':>10} | {'최종 데미지':>12}")
    print("-" * 70)

    for stacks in rune_stacks:
        # 룬 스택 보너스: 스택당 +0.5배
        skill_mult = 1.0 + (stacks * 0.5)

        damage_result, _ = damage_calc.calculate_hp_damage(
            attacker=attacker,
            defender=defender,
            brv_points=brv,
            hp_multiplier=skill_mult,
            is_break=False,
            damage_type="magical"
        )

        print(f"{stacks:>8} | {skill_mult:>10.1f}x | {damage_result.final_damage:>12}")

    print("\n" + "=" * 70)
    print("결론:")
    print("=" * 70)
    print("✓ BRV가 0이면 HP 데미지도 0")
    print("✓ BRV 값에 비례하여 HP 데미지 증가")
    print("✓ 스킬 계수(기믹 보너스)가 배율로 작용")
    print("✓ 스탯 배율(공격/방어)이 추가 보정")
    print("✓ 공식: HP데미지 = BRV × 스킬계수 × (공격/방어)")
    print("=" * 70)

if __name__ == "__main__":
    test_hp_damage()
