"""
사용하지 않는 YAML 스킬 파일을 archive 폴더로 이동하는 스크립트

Python 스킬 파일에서 참조되지 않는 YAML 스킬 파일들을 찾아 이동합니다.
"""

import re
from pathlib import Path
import shutil

def find_yaml_skills_referenced_in_python():
    """Python 파일들에서 참조되는 YAML 스킬 ID들을 찾습니다"""
    referenced_skills = set()

    # 모든 character YAML 파일에서 skills 리스트 확인
    char_dir = Path('data/characters')
    for char_file in char_dir.glob('*.yaml'):
        with open(char_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # skills: 섹션에서 스킬 ID 추출
            if 'skills:' in content:
                lines = content.split('\n')
                in_skills = False
                for line in lines:
                    if line.strip() == 'skills:':
                        in_skills = True
                        continue
                    if in_skills:
                        if line.startswith('  ') or line.startswith('- '):
                            # 스킬 ID 추출 (- skill_id 형식)
                            match = re.match(r'^\s*-\s*(\w+)', line)
                            if match:
                                skill_id = match.group(1)
                                referenced_skills.add(skill_id)
                        elif not line.strip().startswith('#') and line.strip():
                            # skills 섹션 종료
                            break

    return referenced_skills

def find_all_yaml_skills():
    """data/skills/ 폴더의 모든 YAML 스킬 파일 ID를 찾습니다"""
    skills_dir = Path('data/skills')
    yaml_skills = {}

    for yaml_file in skills_dir.glob('*.yaml'):
        skill_id = yaml_file.stem
        yaml_skills[skill_id] = yaml_file

    return yaml_skills

def main():
    """사용하지 않는 YAML 스킬 파일들을 archive로 이동"""
    print("=== 사용하지 않는 YAML 스킬 찾기 ===\n")

    # 참조되는 스킬 찾기
    referenced = find_yaml_skills_referenced_in_python()
    print(f"캐릭터 파일에서 참조되는 스킬: {len(referenced)}개")

    # 모든 YAML 스킬 찾기
    all_yaml = find_all_yaml_skills()
    print(f"data/skills/의 YAML 스킬: {len(all_yaml)}개\n")

    # 사용하지 않는 스킬 찾기
    unused = set(all_yaml.keys()) - referenced

    if not unused:
        print("사용하지 않는 YAML 스킬이 없습니다!")
        return

    print(f"사용하지 않는 스킬: {len(unused)}개\n")

    # archive 폴더 생성
    archive_dir = Path('archive/skills_unused_yaml')
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 이동
    moved_count = 0
    for skill_id in sorted(unused):
        yaml_file = all_yaml[skill_id]
        target = archive_dir / yaml_file.name

        try:
            shutil.move(str(yaml_file), str(target))
            print(f"[MOVED] {yaml_file.name}")
            moved_count += 1
        except Exception as e:
            print(f"[ERROR] {yaml_file.name}: {e}")

    print(f"\n=== 완료: {moved_count}개 파일 이동 ===")

if __name__ == '__main__':
    main()
