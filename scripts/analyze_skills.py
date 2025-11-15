#!/usr/bin/env python3
"""
생성된 스킬 데이터 분석 스크립트
"""

import yaml
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).parent.parent
SKILLS_DIR = ROOT_DIR / "data" / "skills"

def analyze_skills():
    """모든 스킬을 분석합니다."""
    skill_files = list(SKILLS_DIR.glob("*.yaml"))

    # 통계 데이터
    total = len(skill_files)
    types = defaultdict(int)
    elements = defaultdict(int)
    stat_bases = defaultdict(int)
    mp_ranges = defaultdict(int)

    for skill_file in skill_files:
        with open(skill_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

            # 타입 통계
            skill_type = data.get('type', 'unknown')
            types[skill_type] += 1

            # MP 통계
            mp_cost = data.get('costs', {}).get('mp', 0)
            if mp_cost < 20:
                mp_ranges['10-19'] += 1
            elif mp_cost < 30:
                mp_ranges['20-29'] += 1
            elif mp_cost < 40:
                mp_ranges['30-39'] += 1
            elif mp_cost < 50:
                mp_ranges['40-49'] += 1
            else:
                mp_ranges['50+'] += 1

            # 효과 분석
            effects = data.get('effects', [])
            for effect in effects:
                element = effect.get('element', 'none')
                if element != 'none':
                    elements[element] += 1

                stat_base = effect.get('stat_base', 'none')
                if stat_base != 'none':
                    stat_bases[stat_base] += 1

    # 결과 출력
    print("="*70)
    print(f"스킬 데이터 분석 보고서")
    print("="*70)
    print(f"\n총 스킬 수: {total}개\n")

    print("-" * 70)
    print("1. 스킬 타입별 분포")
    print("-" * 70)
    for skill_type, count in sorted(types.items(), key=lambda x: -x[1]):
        percentage = (count / total) * 100
        print(f"  {skill_type:20s}: {count:3d}개 ({percentage:5.1f}%)")

    print("\n" + "-" * 70)
    print("2. 원소 속성별 분포")
    print("-" * 70)
    for element, count in sorted(elements.items(), key=lambda x: -x[1]):
        percentage = (count / total) * 100
        print(f"  {element:20s}: {count:3d}개 ({percentage:5.1f}%)")

    print("\n" + "-" * 70)
    print("3. 기본 스탯별 분포")
    print("-" * 70)
    for stat, count in sorted(stat_bases.items(), key=lambda x: -x[1]):
        percentage = (count / total) * 100
        print(f"  {stat:20s}: {count:3d}개 ({percentage:5.1f}%)")

    print("\n" + "-" * 70)
    print("4. MP 소모량 분포")
    print("-" * 70)
    for mp_range, count in sorted(mp_ranges.items()):
        percentage = (count / total) * 100
        print(f"  {mp_range:20s}: {count:3d}개 ({percentage:5.1f}%)")

    print("\n" + "="*70)
    print("분석 완료!")
    print("="*70)

if __name__ == "__main__":
    analyze_skills()
