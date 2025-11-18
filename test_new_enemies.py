#!/usr/bin/env python3
"""
새로운 적 시스템 테스트

30개의 새로운 적과 70개의 새로운 스킬이 정상적으로 작동하는지 테스트합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.world.enemy_generator import ENEMY_TEMPLATES, EnemyGenerator
from src.combat.enemy_skills import EnemySkillDatabase


def test_new_enemy_templates():
    """새로운 적 템플릿이 제대로 추가되었는지 테스트"""
    print("=" * 60)
    print("1. 적 템플릿 테스트")
    print("=" * 60)

    new_enemies = [
        # 언데드
        "zombie", "ghoul", "banshee", "death_knight", "mummy",
        # 엘리멘탈
        "fire_elemental", "ice_elemental", "thunder_elemental",
        "earth_elemental", "wind_elemental", "dark_elemental",
        # 야수/몬스터
        "bear", "spider", "scorpion", "basilisk", "cerberus", "hydra",
        # 드래곤
        "fire_dragon", "ice_dragon", "poison_dragon", "elder_dragon",
        # 악마
        "imp", "succubus", "balrog", "archfiend",
        # 기계/골렘
        "iron_golem", "crystal_golem", "ancient_automaton",
        # 특수
        "mimic", "nightmare"
    ]

    total = len(new_enemies)
    success = 0
    failed = []

    for enemy_id in new_enemies:
        if enemy_id in ENEMY_TEMPLATES:
            template = ENEMY_TEMPLATES[enemy_id]
            print(f"✓ {template.name} ({enemy_id}): HP={template.hp}, 공격={template.physical_attack}")
            success += 1
        else:
            print(f"✗ {enemy_id}: 템플릿 없음")
            failed.append(enemy_id)

    print(f"\n총 {total}개 중 {success}개 성공")
    if failed:
        print(f"실패: {', '.join(failed)}")

    return len(failed) == 0


def test_enemy_skills():
    """새로운 적 스킬이 제대로 추가되었는지 테스트"""
    print("\n" + "=" * 60)
    print("2. 적 스킬 테스트")
    print("=" * 60)

    # 스킬 데이터베이스 초기화
    EnemySkillDatabase.initialize()

    total_skills = len(EnemySkillDatabase.SKILLS)
    print(f"총 스킬 수: {total_skills}개")

    # 새 스킬 몇 개 샘플 테스트
    sample_skills = [
        "infected_strike", "flame_burst", "bear_roar",
        "fire_breath", "charm", "steel_fist",
        "nightmare_vision"
    ]

    success = 0
    for skill_id in sample_skills:
        skill = EnemySkillDatabase.get_skill(skill_id)
        if skill:
            print(f"✓ {skill.name} ({skill_id}): 배율={skill.damage_multiplier}, 쿨다운={skill.cooldown}")
            success += 1
        else:
            print(f"✗ {skill_id}: 스킬 없음")

    print(f"\n샘플 {len(sample_skills)}개 중 {success}개 성공")

    return success == len(sample_skills)


def test_enemy_skill_mapping():
    """적에게 스킬이 제대로 매핑되는지 테스트"""
    print("\n" + "=" * 60)
    print("3. 적-스킬 매핑 테스트")
    print("=" * 60)

    # 스킬 데이터베이스 초기화
    EnemySkillDatabase.initialize()

    test_enemies = [
        "zombie", "fire_elemental", "bear", "fire_dragon",
        "succubus", "iron_golem", "mimic", "nightmare"
    ]

    success = 0
    for enemy_id in test_enemies:
        skills = EnemySkillDatabase.get_skills_for_enemy_type(enemy_id)
        if skills:
            skill_names = [s.name for s in skills]
            print(f"✓ {enemy_id}: {len(skills)}개 스킬 - {', '.join(skill_names)}")
            success += 1
        else:
            print(f"✗ {enemy_id}: 스킬 없음")

    print(f"\n테스트 {len(test_enemies)}개 중 {success}개 성공")

    return success == len(test_enemies)


def test_enemy_generation():
    """적 생성이 제대로 되는지 테스트"""
    print("\n" + "=" * 60)
    print("4. 적 생성 테스트")
    print("=" * 60)

    # 각 층마다 적 생성 테스트
    test_floors = [1, 3, 6, 9, 12, 15]

    all_success = True
    for floor in test_floors:
        try:
            enemies = EnemyGenerator.generate_enemies(floor, num_enemies=2)
            enemy_info = [f"{e.name}(Lv{e.level})" for e in enemies]
            print(f"✓ {floor}층: {', '.join(enemy_info)}")

            # 스킬 확인
            for enemy in enemies:
                if hasattr(enemy, 'skills') and enemy.skills:
                    skill_names = [s.name for s in enemy.skills[:3]]  # 처음 3개만
                    print(f"  - {enemy.name} 스킬: {', '.join(skill_names)}")
        except Exception as e:
            print(f"✗ {floor}층: 오류 - {e}")
            all_success = False

    return all_success


def test_tier_distribution():
    """층수별 적 티어 분포 테스트"""
    print("\n" + "=" * 60)
    print("5. 층수별 적 티어 분포")
    print("=" * 60)

    for floor in [1, 3, 6, 9, 12, 15, 18]:
        suitable = EnemyGenerator.get_suitable_enemies_for_floor(floor)
        print(f"{floor}층: {len(suitable)}종류 - {', '.join(suitable[:10])}{'...' if len(suitable) > 10 else ''}")

    return True


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("Dawn of Stellar - 새로운 적 시스템 테스트")
    print("=" * 60)
    print(f"기존 적: 17종")
    print(f"새 적: 30종")
    print(f"총 적: 47종")
    print(f"기존 스킬: ~40개")
    print(f"새 스킬: ~70개")
    print(f"총 스킬: ~110개")
    print("=" * 60 + "\n")

    results = []

    # 테스트 실행
    results.append(("적 템플릿", test_new_enemy_templates()))
    results.append(("적 스킬", test_enemy_skills()))
    results.append(("스킬 매핑", test_enemy_skill_mapping()))
    results.append(("적 생성", test_enemy_generation()))
    results.append(("티어 분포", test_tier_distribution()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n모든 테스트 통과! 🎉")
        print("\n새로운 적들:")
        print("  🧟 언데드: 좀비, 구울, 밴시, 죽음의 기사, 미라")
        print("  ⚡ 엘리멘탈: 불/얼음/번개/대지/바람/어둠의 정령")
        print("  🐺 야수: 곰, 거미, 전갈, 바실리스크, 케르베로스, 히드라")
        print("  🐉 드래곤: 화염룡, 빙룡, 독룡, 고룡")
        print("  😈 악마: 임프, 서큐버스, 발록, 대악마")
        print("  🤖 기계: 강철 골렘, 수정 골렘, 고대 자동인형")
        print("  👹 특수: 미믹, 나이트메어")
        return 0
    else:
        print("\n일부 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
