"""
Gimmick 시스템 검증 스크립트

모든 직업의 YAML gimmick 정의와 character.py 초기화, 스킬 사용이 일치하는지 검증합니다.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict


def load_yaml(file_path: str) -> Dict[str, Any]:
    """YAML 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_all_character_yamls(data_dir: str) -> List[str]:
    """모든 캐릭터 YAML 파일 경로 반환"""
    char_dir = Path(data_dir) / "characters"
    return sorted(char_dir.glob("*.yaml"))


def extract_gimmick_from_yaml(yaml_path: str) -> Dict[str, Any]:
    """YAML 파일에서 gimmick 정의 추출"""
    data = load_yaml(yaml_path)
    job_name = Path(yaml_path).stem
    class_name = data.get('class_name', job_name)
    gimmick = data.get('gimmick', None)

    return {
        'job_id': job_name,
        'class_name': class_name,
        'has_gimmick': gimmick is not None,
        'gimmick_type': gimmick.get('type') if gimmick else None,
        'gimmick_data': gimmick
    }


def extract_character_py_gimmicks(character_py_path: str) -> Dict[str, List[str]]:
    """character.py의 _initialize_gimmick()에서 지원하는 gimmick 타입과 필드 추출"""
    with open(character_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # _initialize_gimmick 함수 찾기
    func_match = re.search(r'def _initialize_gimmick\(self\).*?(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    if not func_match:
        return {}

    func_content = func_match.group(0)

    # elif gimmick_type == "xxx": 패턴 찾기
    gimmick_types = {}

    # 각 elif/if 블록 찾기
    type_pattern = r'(?:if|elif)\s+gimmick_type\s*==\s*"([^"]+)":\s*(.*?)(?=\n\s*(?:elif|if|def|$))'

    for match in re.finditer(type_pattern, func_content, re.DOTALL):
        gimmick_type = match.group(1)
        init_code = match.group(2)

        # self.xxx = 형태의 필드 추출
        fields = re.findall(r'self\.(\w+)\s*=', init_code)
        gimmick_types[gimmick_type] = fields

    return gimmick_types


def extract_skill_gimmick_usage(skill_file_path: str) -> Set[str]:
    """스킬 파일에서 사용되는 gimmick 필드 추출"""
    with open(skill_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    gimmick_fields = set()

    # GimmickEffect 사용 패턴 찾기
    # GimmickEffect(GimmickOperation.XXX, "field_name", ...)
    field_pattern1 = r'GimmickEffect\(\s*GimmickOperation\.\w+\s*,\s*["\'](\w+)["\']'

    for match in re.finditer(field_pattern1, content):
        field_name = match.group(1)
        gimmick_fields.add(field_name)

    # GimmickEffect(field="field_name", ...)
    field_pattern2 = r'GimmickEffect\([^)]*field\s*=\s*["\'](\w+)["\']'

    for match in re.finditer(field_pattern2, content):
        field_name = match.group(1)
        gimmick_fields.add(field_name)

    # gimmick_bonus={"field": "field_name", ...}
    field_pattern3 = r'gimmick_bonus\s*=\s*\{[^}]*["\']field["\']\s*:\s*["\'](\w+)["\']'

    for match in re.finditer(field_pattern3, content):
        field_name = match.group(1)
        gimmick_fields.add(field_name)

    # StackCost("field_name", ...)
    field_pattern4 = r'StackCost\(\s*["\'](\w+)["\']'

    for match in re.finditer(field_pattern4, content):
        field_name = match.group(1)
        gimmick_fields.add(field_name)

    # 직접 사용 패턴도 찾기
    # 예: caster.shadow_count += 1
    direct_pattern = r'(?:caster|target|user)\.(\w+(?:_count|_stacks|_power|_energy|_marks|_points|_aura|_bond|stance))'

    for match in re.finditer(direct_pattern, content):
        field_name = match.group(1)
        # 일반적인 스탯 제외
        if field_name not in ['current_hp', 'current_mp', 'current_brv', 'max_hp', 'max_mp']:
            gimmick_fields.add(field_name)

    return gimmick_fields


def analyze_all_jobs(project_root: str) -> Dict[str, Any]:
    """모든 직업 분석"""
    data_dir = os.path.join(project_root, "data")
    src_dir = os.path.join(project_root, "src")

    # 1. YAML에서 gimmick 추출
    yaml_gimmicks = {}
    yaml_files = get_all_character_yamls(data_dir)

    for yaml_path in yaml_files:
        info = extract_gimmick_from_yaml(str(yaml_path))
        yaml_gimmicks[info['job_id']] = info

    # 2. character.py에서 지원하는 gimmick 타입 추출
    character_py_path = os.path.join(src_dir, "character", "character.py")
    supported_gimmick_types = extract_character_py_gimmicks(character_py_path)

    # 3. 스킬 파일에서 사용되는 gimmick 필드 추출
    skill_dir = Path(src_dir) / "character" / "skills" / "job_skills"
    skill_gimmick_usage = {}

    for skill_file in skill_dir.glob("*_skills.py"):
        job_id = skill_file.stem.replace('_skills', '')
        fields = extract_skill_gimmick_usage(str(skill_file))
        if fields:
            skill_gimmick_usage[job_id] = fields

    return {
        'yaml_gimmicks': yaml_gimmicks,
        'supported_types': supported_gimmick_types,
        'skill_usage': skill_gimmick_usage
    }


def find_issues(analysis: Dict[str, Any]) -> Dict[str, List[str]]:
    """불일치 및 문제점 찾기"""
    issues = {
        'missing_yaml_gimmick': [],      # YAML에 gimmick이 없는데 스킬에서 사용
        'missing_character_init': [],     # character.py에 초기화가 없는 gimmick 타입
        'field_mismatch': [],             # 스킬 사용 필드와 character.py 초기화 불일치
        'unused_gimmick': [],             # YAML에 정의되었지만 사용 안 됨
    }

    yaml_gimmicks = analysis['yaml_gimmicks']
    supported_types = analysis['supported_types']
    skill_usage = analysis['skill_usage']

    for job_id, skill_fields in skill_usage.items():
        yaml_info = yaml_gimmicks.get(job_id, {})

        # 1. YAML에 gimmick이 없는데 스킬에서 사용
        if not yaml_info.get('has_gimmick'):
            issues['missing_yaml_gimmick'].append(
                f"{job_id} ({yaml_info.get('class_name', 'N/A')}): "
                f"스킬에서 사용 중인 필드 {skill_fields}"
            )

        # 2. character.py에 초기화가 없는 gimmick 타입
        gimmick_type = yaml_info.get('gimmick_type')
        if gimmick_type and gimmick_type not in supported_types:
            issues['missing_character_init'].append(
                f"{job_id} ({yaml_info.get('class_name', 'N/A')}): "
                f"타입 '{gimmick_type}' 초기화 코드 없음"
            )

        # 3. 필드 불일치
        if gimmick_type and gimmick_type in supported_types:
            initialized_fields = set(supported_types[gimmick_type])
            used_fields = skill_fields

            missing_in_init = used_fields - initialized_fields
            if missing_in_init:
                issues['field_mismatch'].append(
                    f"{job_id} ({yaml_info.get('class_name', 'N/A')}): "
                    f"스킬에서 사용하지만 초기화 안 됨: {missing_in_init}"
                )

    # 4. 사용 안 되는 gimmick
    for job_id, yaml_info in yaml_gimmicks.items():
        if yaml_info.get('has_gimmick') and job_id not in skill_usage:
            issues['unused_gimmick'].append(
                f"{job_id} ({yaml_info.get('class_name', 'N/A')}): "
                f"YAML에 정의되었지만 스킬에서 미사용"
            )

    return issues


def print_report(analysis: Dict[str, Any], issues: Dict[str, List[str]]):
    """분석 결과 출력"""
    print("=" * 80)
    print("Gimmick 시스템 검증 보고서")
    print("=" * 80)
    print()

    # 1. YAML Gimmick 현황
    print("1. YAML Gimmick 정의 현황 (34개 직업)")
    print("-" * 80)

    yaml_gimmicks = analysis['yaml_gimmicks']
    gimmick_count = sum(1 for info in yaml_gimmicks.values() if info['has_gimmick'])
    no_gimmick_count = len(yaml_gimmicks) - gimmick_count

    print(f"- Gimmick 있음: {gimmick_count}개")
    print(f"- Gimmick 없음: {no_gimmick_count}개")
    print()

    # Gimmick 없는 직업 목록
    print("Gimmick 없는 직업:")
    for job_id, info in yaml_gimmicks.items():
        if not info['has_gimmick']:
            print(f"  - {job_id} ({info['class_name']})")
    print()

    # Gimmick 타입별 분류
    print("Gimmick 타입별 분류:")
    type_counts = defaultdict(list)
    for job_id, info in yaml_gimmicks.items():
        if info['has_gimmick']:
            gimmick_type = info['gimmick_type']
            type_counts[gimmick_type].append(f"{job_id} ({info['class_name']})")

    for gimmick_type, jobs in sorted(type_counts.items()):
        print(f"  - {gimmick_type}: {len(jobs)}개")
        for job in jobs:
            print(f"    * {job}")
    print()

    # 2. character.py 지원 현황
    print("2. character.py의 _initialize_gimmick() 지원 타입")
    print("-" * 80)
    supported_types = analysis['supported_types']
    print(f"총 {len(supported_types)}개 타입 지원:")
    for gimmick_type, fields in sorted(supported_types.items()):
        print(f"  - {gimmick_type}: {', '.join(fields)}")
    print()

    # 3. 스킬 사용 현황
    print("3. 스킬에서 Gimmick 사용 현황")
    print("-" * 80)
    skill_usage = analysis['skill_usage']
    print(f"총 {len(skill_usage)}개 직업이 스킬에서 gimmick 사용:")
    for job_id, fields in sorted(skill_usage.items()):
        class_name = yaml_gimmicks.get(job_id, {}).get('class_name', 'N/A')
        print(f"  - {job_id} ({class_name}): {', '.join(sorted(fields))}")
    print()

    # 4. 문제점
    print("4. 발견된 문제점")
    print("=" * 80)

    total_issues = sum(len(v) for v in issues.values())

    if total_issues == 0:
        print("문제 없음! 모든 gimmick이 올바르게 정의되고 사용되고 있습니다.")
    else:
        print(f"총 {total_issues}개 문제 발견:")
        print()

        # 4-1. YAML에 gimmick 없음
        if issues['missing_yaml_gimmick']:
            print(f"4-1. YAML에 gimmick이 없는데 스킬에서 사용 ({len(issues['missing_yaml_gimmick'])}개)")
            print("-" * 80)
            for issue in issues['missing_yaml_gimmick']:
                print(f"  - {issue}")
            print()

        # 4-2. character.py 초기화 없음
        if issues['missing_character_init']:
            print(f"4-2. character.py에 초기화 코드 없음 ({len(issues['missing_character_init'])}개)")
            print("-" * 80)
            for issue in issues['missing_character_init']:
                print(f"  - {issue}")
            print()

        # 4-3. 필드 불일치
        if issues['field_mismatch']:
            print(f"4-3. 스킬 사용 필드와 초기화 불일치 ({len(issues['field_mismatch'])}개)")
            print("-" * 80)
            for issue in issues['field_mismatch']:
                print(f"  - {issue}")
            print()

        # 4-4. 미사용 gimmick
        if issues['unused_gimmick']:
            print(f"4-4. YAML에 정의되었지만 스킬에서 미사용 ({len(issues['unused_gimmick'])}개)")
            print("-" * 80)
            for issue in issues['unused_gimmick']:
                print(f"  - {issue}")
            print()

    print("=" * 80)


def main():
    """메인 함수"""
    # 프로젝트 루트 찾기
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print("Gimmick 시스템 검증 중...")
    print(f"프로젝트 루트: {project_root}")
    print()

    # 분석 실행
    analysis = analyze_all_jobs(str(project_root))

    # 문제점 찾기
    issues = find_issues(analysis)

    # 보고서 출력
    print_report(analysis, issues)


if __name__ == "__main__":
    main()
