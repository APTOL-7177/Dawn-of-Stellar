"""
직업별 팀워크 스킬 직접 검증

각 직업 파일에 직접 접근하여 팀워크 스킬 존재 여부를 확인합니다.
"""

import os
from pathlib import Path

# 직업 스킬 디렉토리
skills_dir = Path(__file__).parent.parent / "src" / "character" / "skills" / "job_skills"

# 테스트할 파일들
skill_files = sorted([f for f in skills_dir.glob("*_skills.py") if f.name != "__pycache__"])

passed = 0
failed = 0
results = []

print("=" * 70)
print("직업별 팀워크 스킬 파일 검증")
print("=" * 70)

for skill_file in skill_files:
    job_name = skill_file.stem.replace("_skills", "").replace("_", " ").title()

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 체크 사항
        has_teamwork_import = "from src.character.skills.teamwork_skill import TeamworkSkill" in content
        has_teamwork_skill = 'TeamworkSkill(' in content
        has_teamwork_cost = 'gauge_cost=' in content
        has_teamwork_metadata = '"teamwork": True' in content

        if has_teamwork_import and has_teamwork_skill and has_teamwork_cost and has_teamwork_metadata:
            passed += 1
            results.append(("PASS", f"{job_name}: 팀워크 스킬 정의 완료"))
        else:
            failed += 1
            missing = []
            if not has_teamwork_import:
                missing.append("import")
            if not has_teamwork_skill:
                missing.append("TeamworkSkill()")
            if not has_teamwork_cost:
                missing.append("gauge_cost")
            if not has_teamwork_metadata:
                missing.append("metadata")
            results.append(("FAIL", f"{job_name}: {', '.join(missing)} 누락"))

    except Exception as e:
        failed += 1
        results.append(("FAIL", f"{job_name}: {str(e)}"))

# 결과 출력
print()
for status, message in results:
    symbol = "[OK]" if status == "PASS" else "[FAIL]"
    print(f"{symbol} {message}")

print("\n" + "=" * 70)
print(f"총 {passed + failed}개 파일")
print(f"성공: {passed}")
print(f"실패: {failed}")
print("=" * 70)

if failed == 0:
    print("\n[SUCCESS] 모든 직업의 팀워크 스킬 정의 완료!")
    exit(0)
else:
    print(f"\n[FAILED] {failed}개 파일에서 문제 발견")
    exit(1)
