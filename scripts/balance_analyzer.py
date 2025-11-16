"""스킬 밸런스 분석 스크립트

33개 직업 × 10개 스킬 = 330개 스킬의 밸런스를 분석합니다.
- MP 소모량 vs 데미지 배율
- 쿨다운 vs 스킬 효과
- 기믹 소모 vs 효과
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.effects.damage_effect import DamageEffect
from src.character.skills.costs.mp_cost import MPCost

def analyze_skill_balance():
    """전체 스킬 밸런스 분석"""

    skill_manager = get_skill_manager()

    # 모든 직업 스킬 등록
    from src.character.skills.job_skills import (
        warrior_skills, archmage_skills, sniper_skills, rogue_skills,
        paladin_skills, berserker_skills, monk_skills, bard_skills,
        necromancer_skills, shaman_skills, philosopher_skills, chronomancer_skills,
        alchemist_skills, vampire_skills, hacker_skills, dark_knight_skills,
        battle_mage_skills, dimensionist_skills, engineer_skills, gladiator_skills,
        mime_skills, machinist_skills, martial_artist_skills, elementalist_skills,
        archer_skills, assassin_skills, sword_saint_skills, pirate_skills,
        dragoon_skills, breaker_skills, samurai_skills, magic_knight_skills, druid_skills
    )

    job_modules = [
        warrior_skills, archmage_skills, sniper_skills, rogue_skills,
        paladin_skills, berserker_skills, monk_skills, bard_skills,
        necromancer_skills, shaman_skills, philosopher_skills, chronomancer_skills,
        alchemist_skills, vampire_skills, hacker_skills, dark_knight_skills,
        battle_mage_skills, dimensionist_skills, engineer_skills, gladiator_skills,
        mime_skills, machinist_skills, martial_artist_skills, elementalist_skills,
        archer_skills, assassin_skills, sword_saint_skills, pirate_skills,
        dragoon_skills, breaker_skills, samurai_skills, magic_knight_skills, druid_skills
    ]

    print("=" * 80)
    print("스킬 밸런스 분석")
    print("=" * 80)

    total_skills = 0
    balance_issues = []

    for module in job_modules:
        job_name = module.__name__.split('.')[-1].replace('_skills', '')

        # 스킬 생성 함수 호출
        if hasattr(module, f'create_{job_name}_skills'):
            create_func = getattr(module, f'create_{job_name}_skills')
            skills = create_func()
        else:
            print(f"⚠️  {job_name}: 스킬 생성 함수 없음")
            continue

        print(f"\n[{job_name.upper()}] - {len(skills)}개 스킬")
        total_skills += len(skills)

        for i, skill in enumerate(skills, 1):
            # MP 비용 추출
            mp_cost = 0
            for cost in skill.costs:
                if isinstance(cost, MPCost):
                    mp_cost = cost.amount
                    break

            # 데미지 효과 추출
            damage_multipliers = []
            for effect in skill.effects:
                if isinstance(effect, DamageEffect):
                    damage_multipliers.append(effect.multiplier)

            max_damage = max(damage_multipliers) if damage_multipliers else 0

            # 밸런스 검증
            # 기본 공격 (1, 2번 스킬)
            if i <= 2:
                if mp_cost > 0:
                    balance_issues.append(f"{job_name} - {skill.name}: 기본 공격인데 MP 소모 {mp_cost}")
            else:
                # 데미지/MP 비율 검증
                if mp_cost > 0 and max_damage > 0:
                    ratio = max_damage / mp_cost
                    # 정상 비율: 0.1~0.3 (MP 10당 데미지 1~3)
                    if ratio < 0.08:
                        balance_issues.append(
                            f"{job_name} - {skill.name}: MP 효율 낮음 (MP {mp_cost}, 데미지 {max_damage}, 비율 {ratio:.2f})"
                        )
                    elif ratio > 0.35:
                        balance_issues.append(
                            f"{job_name} - {skill.name}: MP 효율 높음 (MP {mp_cost}, 데미지 {max_damage}, 비율 {ratio:.2f})"
                        )

            # 궁극기 (10번 스킬)
            if i == 10:
                if not skill.is_ultimate:
                    balance_issues.append(f"{job_name} - {skill.name}: 10번 스킬인데 is_ultimate=False")
                if mp_cost < 25:
                    balance_issues.append(f"{job_name} - {skill.name}: 궁극기인데 MP 소모 {mp_cost} (권장: 30+)")

            print(f"  {i}. {skill.name:25s} MP:{mp_cost:2d} 데미지:{max_damage:.1f} CD:{skill.cooldown}")

    print("\n" + "=" * 80)
    print(f"총 {total_skills}개 스킬 분석 완료")
    print("=" * 80)

    if balance_issues:
        print(f"\n⚠️  {len(balance_issues)}개 밸런스 이슈 발견:\n")
        for issue in balance_issues:
            print(f"  - {issue}")
    else:
        print("\n✅ 밸런스 이슈 없음!")

    print("\n")

if __name__ == "__main__":
    analyze_skill_balance()
