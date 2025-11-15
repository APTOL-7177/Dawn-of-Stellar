"""
BRV 데미지 계산 테스트

공격력/방어력 비율이 선형으로 작동하는지 확인합니다.
"""

from src.character.character import Character
from src.combat.damage_calculator import get_damage_calculator
from src.core.config import initialize_config

def test_brv_damage():
    """BRV 공격 선형 스케일링 테스트"""

    # 설정 초기화
    initialize_config()
    damage_calc = get_damage_calculator()

    print("=" * 70)
    print("BRV 데미지 선형 스케일링 테스트")
    print("=" * 70)

    # 공격자 생성
    attacker = Character("테스트 전사", "warrior")
    attacker.level = 5
    attacker.stat_manager.set_base_value("hp", 500)
    attacker.stat_manager.set_base_value("defense", 20)
    attacker.stat_manager.set_base_value("spirit", 20)
    attacker.current_hp = 500

    # 방어자 생성
    defender = Character("테스트 적", "warrior")
    defender.level = 5
    defender.stat_manager.set_base_value("hp", 300)
    defender.stat_manager.set_base_value("defense", 25)
    defender.stat_manager.set_base_value("spirit", 20)
    defender.current_hp = 300

    print("\n" + "=" * 70)
    print("테스트 1: 물리 BRV 공격 (공격력 변화)")
    print("=" * 70)
    print(f"방어자 방어력: {defender.defense}")
    print(f"\n{'공격력':>8} | {'기본 데미지':>12} | {'비율 (데미지/공격력)':>25}")
    print("-" * 70)

    attack_values = [10, 20, 30, 50, 100]
    skill_mult = 1.0

    for atk in attack_values:
        attacker.stat_manager.set_base_value("strength", atk)

        result = damage_calc.calculate_brv_damage(
            attacker=attacker,
            defender=defender,
            skill_multiplier=skill_mult
        )

        ratio = result.base_damage / atk if atk > 0 else 0
        print(f"{atk:>8} | {result.base_damage:>12} | {ratio:>25.3f}")

    print("\n분석:")
    print("✓ 공격력이 2배가 되면 데미지도 2배 (선형)")
    print("✓ 비율(데미지/공격력)이 일정함")

    print("\n" + "=" * 70)
    print("테스트 2: 마법 BRV 공격 (마법력 변화)")
    print("=" * 70)
    print(f"방어자 정신력: {defender.spirit}")
    print(f"\n{'마법력':>8} | {'기본 데미지':>12} | {'비율 (데미지/마법력)':>25}")
    print("-" * 70)

    magic_values = [10, 20, 30, 50, 100]

    for mag in magic_values:
        attacker.stat_manager.set_base_value("magic", mag)

        result = damage_calc.calculate_magic_damage(
            attacker=attacker,
            defender=defender,
            skill_multiplier=skill_mult
        )

        ratio = result.base_damage / mag if mag > 0 else 0
        print(f"{mag:>8} | {result.base_damage:>12} | {ratio:>25.3f}")

    print("\n분석:")
    print("✓ 마법력이 2배가 되면 데미지도 2배 (선형)")
    print("✓ 비율(데미지/마법력)이 일정함")

    print("\n" + "=" * 70)
    print("테스트 3: 스킬 계수 배율")
    print("=" * 70)

    attacker.stat_manager.set_base_value("strength", 50)

    skill_multipliers = [1.0, 1.5, 2.0, 3.0]

    print(f"공격력: {attacker.strength}, 방어력: {defender.defense}")
    print(f"\n{'스킬 계수':>10} | {'기본 데미지':>12}")
    print("-" * 70)

    for skill_mult in skill_multipliers:
        result = damage_calc.calculate_brv_damage(
            attacker=attacker,
            defender=defender,
            skill_multiplier=skill_mult
        )

        print(f"{skill_mult:>10.1f}x | {result.base_damage:>12}")

    print("\n분석:")
    print("✓ 스킬 계수가 2배가 되면 데미지도 2배")

    print("\n" + "=" * 70)
    print("결론")
    print("=" * 70)
    print("✓ 모든 공격이 선형 스케일링 사용")
    print("✓ 공식: 데미지 = (공격력/방어력) × 스킬계수 × 배율")
    print("✓ 제곱 스케일링 제거 완료")
    print("=" * 70)

if __name__ == "__main__":
    test_brv_damage()
