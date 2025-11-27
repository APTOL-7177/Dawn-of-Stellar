"""
모든 직업 스킬 파일의 구문 오류 수정

return [s.skill_id for s in skills, teamwork]  (오류)
→ return skills  (수정)
"""

import os
from pathlib import Path

# 직업 스킬 디렉토리
skills_dir = Path(__file__).parent.parent / "src" / "character" / "skills" / "job_skills"

# 수정할 패턴
old_pattern = "return [s.skill_id for s in skills, teamwork]"
new_pattern = "return skills"

fixed_count = 0
error_count = 0

print("=" * 70)
print("직업 스킬 파일 구문 오류 수정")
print("=" * 70)

for skill_file in sorted(skills_dir.glob("*_skills.py")):
    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if old_pattern in content:
            # 수정
            new_content = content.replace(old_pattern, new_pattern)

            with open(skill_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"[OK] {skill_file.name} 수정됨")
            fixed_count += 1
        else:
            # 이미 수정되었거나 함수가 없음
            pass

    except Exception as e:
        print(f"[FAIL] {skill_file.name}: {str(e)}")
        error_count += 1

print("\n" + "=" * 70)
print(f"수정된 파일: {fixed_count}개")
print(f"오류: {error_count}개")
print("=" * 70)
