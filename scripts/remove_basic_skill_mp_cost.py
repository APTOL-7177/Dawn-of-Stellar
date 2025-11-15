#!/usr/bin/env python3
"""기본 공격 스킬(첫 2개)의 MP 코스트 제거"""

import os
import re
from pathlib import Path

def remove_mp_cost_from_basic_skills(file_path):
    """파일의 첫 2개 스킬에서 MP 코스트 제거"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    skill_count = 0
    i = 0

    while i < len(lines) and skill_count < 2:
        line = lines[i]

        # 스킬 정의 시작 (# 1. 기본 BRV: 또는 # 2. 기본 HP:)
        if re.match(r'^\s*# [12]\. 기본 (?:BRV|HP):', line):
            skill_count += 1

            # 다음 줄부터 .costs 라인 찾기
            for j in range(i + 1, min(i + 10, len(lines))):
                if '.costs = [MPCost(' in lines[j]:
                    # 들여쓰기 유지하면서 MP 코스트 제거
                    indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                    var_name = lines[j].strip().split('.')[0]
                    lines[j] = f"{indent}{var_name}.costs = []  # 기본 공격은 MP 소모 없음\n"
                    modified = True
                    print(f"  - Skill #{skill_count}: {var_name} MP cost removed")
                    break

                # 다음 스킬 시작되면 중단
                if re.match(r'^\s*# \d+\.', lines[j]):
                    break

        i += 1

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    return modified

def main():
    skills_dir = Path("/home/user/Dos/src/character/skills/job_skills")
    modified_count = 0

    for skill_file in sorted(skills_dir.glob("*_skills.py")):
        print(f"Processing: {skill_file.name}")
        if remove_mp_cost_from_basic_skills(skill_file):
            modified_count += 1
            print(f"  ✓ Modified")
        else:
            print(f"  ✗ No changes needed")

    print(f"\n총 {modified_count}개 파일 수정 완료")

if __name__ == "__main__":
    main()
