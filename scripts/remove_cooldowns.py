#!/usr/bin/env python3
"""스킬 파일에서 쿨다운 설정을 제거하는 스크립트"""
import re
from pathlib import Path

def remove_cooldown_lines(file_path):
    """파일에서 .cooldown = X 라인을 주석 처리"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # .cooldown = X 패턴 찾기 (들여쓰기 포함)
    pattern = r'^(\s*)(\w+\.cooldown\s*=\s*\d+)$'

    # 주석 처리
    modified_content = re.sub(
        pattern,
        r'\1# \2  # 쿨다운 시스템 제거됨',
        content,
        flags=re.MULTILINE
    )

    if content != modified_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        return True
    return False

def main():
    """메인 함수"""
    base_path = Path(__file__).parent.parent / "src" / "character" / "skills" / "job_skills"

    if not base_path.exists():
        print(f"경로를 찾을 수 없습니다: {base_path}")
        return

    modified_files = []
    for skill_file in base_path.glob("*_skills.py"):
        if remove_cooldown_lines(skill_file):
            modified_files.append(skill_file.name)
            print(f"✓ {skill_file.name}")

    print(f"\n총 {len(modified_files)}개 파일 수정 완료")

if __name__ == "__main__":
    main()
