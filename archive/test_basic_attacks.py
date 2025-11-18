"""
직업별 기본 공격 차별화 시스템 테스트

각 직업의 BRV 공격과 HP 공격이 올바르게 적용되는지 확인
"""

from src.character.character import Character
from src.combat.damage_calculator import DamageCalculator
from src.core.config import initialize_config

# 설정 초기화
initialize_config()


def test_job_attack_profiles():
    """여러 직업의 기본 공격 프로필 테스트"""

    # 테스트할 직업 목록
    test_jobs = [
        "warrior",      # 물리 딜러
        "berserker",    # 크리티컬 특화
        "mage",         # 마법 딜러
        "priest",       # 지원형
        "assassin",     # 속도형
        "archer",       # 원거리
        "monk",         # 격투가
        "vampire",      # 특수형
        "breaker",      # BRV 파괴 특화
    ]

    # 데미지 계산기
    calc = DamageCalculator()

    # 더미 적 생성
    dummy = Character("더미", "warrior", level=10)

    print("=" * 80)
    print("직업별 기본 공격 차별화 시스템 테스트")
    print("=" * 80)
    print()

    for job in test_jobs:
        try:
            # 캐릭터 생성
            char = Character(f"테스트_{job}", job, level=10)

            print(f"[{char.job_name}] ({job})")
            print(f"  스탯: STR={char.strength} MAG={char.magic} DEF={char.defense} SPD={char.speed} LCK={char.luck}")

            # BRV 공격 테스트 (직업 프로필 사용)
            brv_result = calc.calculate_brv_damage(char, dummy, skill_multiplier=1.0, use_job_profile=True)

            print(f"  ├─ BRV 공격: {brv_result.final_damage} 데미지")
            print(f"  │  ├─ 기본: {brv_result.base_damage}")
            print(f"  │  ├─ 배율: {brv_result.multiplier:.2f}x")
            print(f"  │  ├─ 크리티컬: {'예' if brv_result.is_critical else '아니오'}")
            print(f"  │  └─ 상세: {brv_result.details.get('job_profile', False)}")

            # HP 공격 테스트 (BRV 100으로 가정)
            hp_result, wound = calc.calculate_hp_damage(
                char, dummy,
                brv_points=100,
                hp_multiplier=1.0,
                is_break=False,
                use_job_profile=True
            )

            print(f"  └─ HP 공격: {hp_result.final_damage} 데미지 (상처: {wound})")
            print(f"     ├─ 배율: {hp_result.multiplier:.2f}x")
            print(f"     ├─ 크리티컬: {'예' if hp_result.is_critical else '아니오'}")
            print(f"     └─ 상세: {hp_result.details.get('job_profile', False)}")

            print()

        except Exception as e:
            print(f"  [오류] {job}: {e}")
            print()

    print("=" * 80)
    print("테스트 완료")
    print("=" * 80)


def test_critical_differences():
    """크리티컬 특화 직업 테스트"""

    print("\n" + "=" * 80)
    print("크리티컬 특화 직업 비교 테스트")
    print("=" * 80)
    print()

    calc = DamageCalculator()
    dummy = Character("더미", "warrior", level=10)

    # 크리티컬 관련 직업
    crit_jobs = {
        "warrior": "기본형",
        "berserker": "크리티컬 +20%",
        "assassin": "크리티컬 +25%",
        "samurai": "크리티컬 +10%",
        "sniper": "크리티컬 배율 2.5x"
    }

    for job, desc in crit_jobs.items():
        char = Character(f"테스트_{job}", job, level=10)

        # 여러 번 공격하여 크리티컬 확률 확인
        crit_count = 0
        total_damage = 0
        iterations = 100

        for _ in range(iterations):
            result = calc.calculate_brv_damage(char, dummy, skill_multiplier=1.0, use_job_profile=True)
            if result.is_critical:
                crit_count += 1
            total_damage += result.final_damage

        crit_rate = (crit_count / iterations) * 100
        avg_damage = total_damage / iterations

        print(f"[{char.job_name}] - {desc}")
        print(f"  크리티컬 발생률: {crit_rate:.1f}% ({crit_count}/{iterations})")
        print(f"  평균 데미지: {avg_damage:.1f}")
        print()


def test_physical_vs_magical():
    """물리 딜러 vs 마법 딜러 비교"""

    print("\n" + "=" * 80)
    print("물리 딜러 vs 마법 딜러 비교")
    print("=" * 80)
    print()

    calc = DamageCalculator()
    dummy = Character("더미", "warrior", level=10)

    # 물리 딜러
    physical_jobs = ["warrior", "berserker", "gladiator"]
    # 마법 딜러
    magical_jobs = ["mage", "archmage", "elementalist"]

    print("[물리 딜러]")
    for job in physical_jobs:
        char = Character(f"테스트_{job}", job, level=10)
        result = calc.calculate_brv_damage(char, dummy, skill_multiplier=1.0, use_job_profile=True)
        print(f"  {char.job_name:12s}: {result.final_damage:4d} 데미지 (배율: {result.multiplier:.2f}x)")

    print("\n[마법 딜러]")
    for job in magical_jobs:
        char = Character(f"테스트_{job}", job, level=10)
        result = calc.calculate_brv_damage(char, dummy, skill_multiplier=1.0, use_job_profile=True)
        print(f"  {char.job_name:12s}: {result.final_damage:4d} 데미지 (배율: {result.multiplier:.2f}x)")

    print()


def test_support_vs_dps():
    """지원형 vs 딜러형 비교"""

    print("\n" + "=" * 80)
    print("지원형 vs 딜러형 데미지 비교")
    print("=" * 80)
    print()

    calc = DamageCalculator()
    dummy = Character("더미", "warrior", level=10)

    jobs_by_type = {
        "순수 딜러": ["berserker", "gladiator", "assassin"],
        "하이브리드": ["battle_mage", "spellblade", "paladin"],
        "지원형": ["priest", "cleric", "bard"]
    }

    for job_type, jobs in jobs_by_type.items():
        print(f"[{job_type}]")
        for job in jobs:
            char = Character(f"테스트_{job}", job, level=10)
            brv_result = calc.calculate_brv_damage(char, dummy, skill_multiplier=1.0, use_job_profile=True)
            hp_result, _ = calc.calculate_hp_damage(char, dummy, brv_points=100, use_job_profile=True)

            print(f"  {char.job_name:12s}: BRV {brv_result.final_damage:4d} | HP {hp_result.final_damage:4d}")
        print()


if __name__ == "__main__":
    # 모든 테스트 실행
    test_job_attack_profiles()
    test_critical_differences()
    test_physical_vs_magical()
    test_support_vs_dps()
