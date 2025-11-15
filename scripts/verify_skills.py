#!/usr/bin/env python3
"""
스킬 데이터 검증 스크립트
모든 캐릭터의 스킬이 제대로 생성되었는지 확인합니다.
"""

import yaml
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).parent.parent
CHARACTERS_DIR = ROOT_DIR / "data" / "characters"
SKILLS_DIR = ROOT_DIR / "data" / "skills"

def verify_skills():
    """스킬 데이터를 검증합니다."""
    character_files = list(CHARACTERS_DIR.glob("*.yaml"))

    total_chars = 0
    total_expected_skills = 0
    total_missing_skills = 0
    missing_by_class = []

    print("="*70)
    print("스킬 데이터 검증 보고서")
    print("="*70)

    for char_file in sorted(character_files):
        with open(char_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            class_name = data.get('class_name', char_file.stem)
            skills = data.get('skills', [])

            total_chars += 1
            total_expected_skills += len(skills)

            missing = []
            for skill_id in skills:
                skill_file = SKILLS_DIR / f"{skill_id}.yaml"
                if not skill_file.exists():
                    missing.append(skill_id)
                    total_missing_skills += 1

            if missing:
                missing_by_class.append((class_name, missing))
                print(f"\n[경고] {class_name} - {len(missing)}개 스킬 누락:")
                for skill in missing:
                    print(f"  - {skill}")
            else:
                print(f"[OK] {class_name} - {len(skills)}개 스킬 모두 존재")

    # 요약
    print("\n" + "="*70)
    print("검증 요약")
    print("="*70)
    print(f"총 캐릭터 수: {total_chars}개")
    print(f"예상 스킬 수: {total_expected_skills}개")
    print(f"누락된 스킬: {total_missing_skills}개")

    if total_missing_skills == 0:
        print("\n모든 스킬이 정상적으로 생성되었습니다!")
    else:
        print(f"\n{len(missing_by_class)}개 직업에서 스킬 누락 발견")

    print("="*70)

    # 스킬 파일 수 확인
    skill_files = list(SKILLS_DIR.glob("*.yaml"))
    print(f"\n실제 생성된 스킬 파일 수: {len(skill_files)}개")

    # 중복 체크 (여러 직업이 같은 스킬을 사용할 수 있음)
    skill_usage = defaultdict(list)
    for char_file in character_files:
        with open(char_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            class_name = data.get('class_name', char_file.stem)
            skills = data.get('skills', [])
            for skill_id in skills:
                skill_usage[skill_id].append(class_name)

    # 공유 스킬 통계
    shared_skills = {k: v for k, v in skill_usage.items() if len(v) > 1}
    if shared_skills:
        print(f"\n여러 직업이 공유하는 스킬: {len(shared_skills)}개")
        for skill_id, classes in sorted(shared_skills.items(), key=lambda x: -len(x[1]))[:5]:
            print(f"  - {skill_id}: {len(classes)}개 직업 ({', '.join(classes[:3])}...)")

    print("="*70)

if __name__ == "__main__":
    verify_skills()
