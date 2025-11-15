"""
직업별 기본 공격 프로필 조회 스크립트

사용법:
  python scripts/show_job_profiles.py              # 전체 직업 목록
  python scripts/show_job_profiles.py warrior      # 특정 직업 상세
  python scripts/show_job_profiles.py --type physical  # 타입별 필터
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.character.basic_attacks import JOB_ATTACK_PROFILES, get_attack_profile


def show_all_jobs():
    """전체 직업 목록 표시"""
    print("=" * 80)
    print("직업별 기본 공격 프로필 목록")
    print("=" * 80)
    print()

    # 타입별로 분류
    job_types = {
        "물리 딜러": [],
        "마법 딜러": [],
        "하이브리드": [],
        "지원형": [],
        "특수형": []
    }

    for job_id in sorted(JOB_ATTACK_PROFILES.keys()):
        profile = get_attack_profile(job_id, "brv_attack")
        damage_type = profile.get("damage_type", "physical")
        multiplier = profile.get("base_multiplier", 1.0)

        # 타입 분류
        if damage_type == "physical":
            if multiplier >= 1.3:
                job_types["물리 딜러"].append(job_id)
            elif multiplier >= 1.0:
                job_types["물리 딜러"].append(job_id)
            else:
                job_types["지원형"].append(job_id)
        elif damage_type == "magic":
            if multiplier >= 1.2:
                job_types["마법 딜러"].append(job_id)
            elif multiplier >= 1.0:
                job_types["마법 딜러"].append(job_id)
            else:
                job_types["지원형"].append(job_id)
        elif damage_type == "hybrid":
            job_types["하이브리드"].append(job_id)
        else:
            job_types["특수형"].append(job_id)

    for type_name, jobs in job_types.items():
        if not jobs:
            continue

        print(f"[{type_name}] ({len(jobs)}개)")
        for job_id in jobs:
            brv_profile = get_attack_profile(job_id, "brv_attack")
            hp_profile = get_attack_profile(job_id, "hp_attack")

            print(f"  {job_id:20s} - BRV: {brv_profile['base_multiplier']:.2f}x | "
                  f"HP: {hp_profile['base_multiplier']:.2f}x | "
                  f"크리: {'O' if brv_profile['can_critical'] else 'X'}")
        print()


def show_job_detail(job_id: str):
    """특정 직업 상세 정보 표시"""
    if job_id not in JOB_ATTACK_PROFILES:
        print(f"오류: '{job_id}' 직업을 찾을 수 없습니다.")
        print(f"사용 가능한 직업: {', '.join(sorted(JOB_ATTACK_PROFILES.keys()))}")
        return

    print("=" * 80)
    print(f"직업 상세 정보: {job_id}")
    print("=" * 80)
    print()

    # BRV 공격
    brv_profile = get_attack_profile(job_id, "brv_attack")
    print("[BRV 공격]")
    print(f"  이름: {brv_profile['name']}")
    print(f"  설명: {brv_profile.get('description', '설명 없음')}")
    print(f"  타입: {brv_profile['damage_type']}")
    print(f"  기본 스탯: {brv_profile['stat_base']}")
    print(f"  기본 배율: {brv_profile['base_multiplier']:.2f}x")
    print(f"  크리티컬 가능: {'예' if brv_profile['can_critical'] else '아니오'}")

    if brv_profile.get('critical_bonus'):
        print(f"  크리티컬 보너스: +{brv_profile['critical_bonus']*100:.0f}%")
    if brv_profile.get('critical_multiplier'):
        print(f"  크리티컬 배율: {brv_profile['critical_multiplier']:.1f}x")
    if brv_profile.get('ignore_defense'):
        print(f"  방어력 무시: {brv_profile['ignore_defense']*100:.0f}%")

    # 추가 효과
    effects = []
    if brv_profile.get('lifesteal'):
        effects.append(f"흡혈 {brv_profile['lifesteal']*100:.0f}%")
    if brv_profile.get('poison_chance'):
        effects.append(f"독 {brv_profile['poison_chance']*100:.0f}%")
    if brv_profile.get('slow_chance'):
        effects.append(f"슬로우 {brv_profile['slow_chance']*100:.0f}%")
    if brv_profile.get('element'):
        effects.append(f"속성: {brv_profile['element']}")

    if effects:
        print(f"  추가 효과: {', '.join(effects)}")

    print()

    # HP 공격
    hp_profile = get_attack_profile(job_id, "hp_attack")
    print("[HP 공격]")
    print(f"  이름: {hp_profile['name']}")
    print(f"  설명: {hp_profile.get('description', '설명 없음')}")
    print(f"  타입: {hp_profile['damage_type']}")
    print(f"  기본 스탯: {hp_profile['stat_base']}")
    print(f"  기본 배율: {hp_profile['base_multiplier']:.2f}x")
    print(f"  크리티컬 가능: {'예' if hp_profile['can_critical'] else '아니오'}")

    if hp_profile.get('critical_bonus'):
        print(f"  크리티컬 보너스: +{hp_profile['critical_bonus']*100:.0f}%")
    if hp_profile.get('critical_multiplier'):
        print(f"  크리티컬 배율: {hp_profile['critical_multiplier']:.1f}x")
    if hp_profile.get('break_bonus'):
        print(f"  BREAK 보너스: +{hp_profile['break_bonus']*100:.0f}%")

    # 추가 효과
    effects = []
    if hp_profile.get('lifesteal'):
        effects.append(f"흡혈 {hp_profile['lifesteal']*100:.0f}%")
    if hp_profile.get('splash_damage'):
        effects.append(f"광역 {hp_profile['splash_damage']*100:.0f}%")
    if hp_profile.get('dot_damage'):
        effects.append(f"지속 {hp_profile['dot_damage']*100:.0f}%")
    if hp_profile.get('element'):
        effects.append(f"속성: {hp_profile['element']}")

    if effects:
        print(f"  추가 효과: {', '.join(effects)}")

    print()


def show_stats():
    """통계 정보 표시"""
    print("=" * 80)
    print("직업 프로필 통계")
    print("=" * 80)
    print()

    total = len(JOB_ATTACK_PROFILES)
    print(f"총 직업 수: {total}개")
    print()

    # 타입별 통계
    damage_types = {"physical": 0, "magic": 0, "hybrid": 0}
    can_crit_brv = 0
    can_crit_hp = 0

    for job_id in JOB_ATTACK_PROFILES:
        brv_profile = get_attack_profile(job_id, "brv_attack")
        hp_profile = get_attack_profile(job_id, "hp_attack")

        damage_type = brv_profile.get("damage_type", "physical")
        if damage_type in damage_types:
            damage_types[damage_type] += 1

        if brv_profile.get("can_critical"):
            can_crit_brv += 1
        if hp_profile.get("can_critical"):
            can_crit_hp += 1

    print("[데미지 타입 분포]")
    print(f"  물리형: {damage_types['physical']}개")
    print(f"  마법형: {damage_types['magic']}개")
    print(f"  하이브리드: {damage_types['hybrid']}개")
    print()

    print("[크리티컬 가능]")
    print(f"  BRV 공격: {can_crit_brv}/{total}개 ({can_crit_brv/total*100:.1f}%)")
    print(f"  HP 공격: {can_crit_hp}/{total}개 ({can_crit_hp/total*100:.1f}%)")
    print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 인자 없음 - 전체 목록
        show_all_jobs()
        print()
        show_stats()
    elif sys.argv[1] == "--stats":
        # 통계
        show_stats()
    else:
        # 특정 직업 상세
        show_job_detail(sys.argv[1])
