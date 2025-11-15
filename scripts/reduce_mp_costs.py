#!/usr/bin/env python3
"""모든 스킬의 MP 코스트를 1/4로 감소"""

import os
import re
from pathlib import Path

def reduce_mp_costs(file_path):
    """파일의 모든 MPCost 값을 1/4로 감소"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    def replace_mp_cost(match):
        nonlocal modified
        mp_value = int(match.group(1))
        new_value = max(1, round(mp_value / 4))  # 최소 1, 반올림
        modified = True
        return f"MPCost({new_value})"

    # MPCost(숫자) 패턴 찾아서 1/4로 변경
    new_content = re.sub(r'MPCost\((\d+)\)', replace_mp_cost, content)

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    return modified

def main():
    skills_dir = Path("/home/user/Dos/src/character/skills/job_skills")
    modified_count = 0

    for skill_file in sorted(skills_dir.glob("*_skills.py")):
        print(f"Processing: {skill_file.name}")
        if reduce_mp_costs(skill_file):
            modified_count += 1
            print(f"  ✓ Modified")
        else:
            print(f"  ✗ No changes needed")

    print(f"\n총 {modified_count}개 파일 수정 완료")

if __name__ == "__main__":
    main()
