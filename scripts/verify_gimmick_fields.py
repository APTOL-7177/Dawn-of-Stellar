"""기믹 필드명 일치성 검증 스크립트"""
import os
import yaml
import re
from pathlib import Path


def load_yaml_gimmicks():
    """모든 직업의 YAML에서 기믹 정보 추출"""
    gimmicks = {}
    yaml_dir = Path("data/characters")

    for yaml_file in yaml_dir.glob("*.yaml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        class_name = data.get('class_name', yaml_file.stem)
        gimmick = data.get('gimmick', {})

        if gimmick:
            gimmick_type = gimmick.get('type')
            # max_xxx 필드들 추출
            max_fields = {k: v for k, v in gimmick.items() if k.startswith('max_')}

            gimmicks[class_name] = {
                'file': yaml_file.name,
                'type': gimmick_type,
                'max_fields': max_fields
            }

    return gimmicks


def extract_character_init_fields():
    """character.py의 _initialize_gimmick에서 필드명 추출"""
    char_file = Path("src/character/character.py")

    with open(char_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # _initialize_gimmick 함수 찾기
    func_match = re.search(r'def _initialize_gimmick\(self\).*?(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    if not func_match:
        return {}

    func_content = func_match.group(0)

    # 각 gimmick_type 블록 찾기
    gimmick_fields = {}

    # elif/if gimmick_type == "xxx": 패턴 찾기
    type_pattern = r'(?:if|elif)\s+gimmick_type\s*==\s*"([^"]+)":(.*?)(?=\n\s*(?:elif|if|def|$))'

    for match in re.finditer(type_pattern, func_content, re.DOTALL):
        gimmick_type = match.group(1)
        init_code = match.group(2)

        # self.xxx = 형태의 필드 추출
        fields = {}
        field_pattern = r'self\.(\w+)\s*=\s*([^\n]+)'
        for field_match in re.finditer(field_pattern, init_code):
            field_name = field_match.group(1)
            field_value = field_match.group(2).strip()
            fields[field_name] = field_value

        gimmick_fields[gimmick_type] = fields

    return gimmick_fields


def extract_ui_display_fields():
    """combat_ui.py의 _get_gimmick_display에서 필드명 추출"""
    ui_file = Path("src/ui/combat_ui.py")

    with open(ui_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # _get_gimmick_display 함수 찾기
    func_match = re.search(r'def _get_gimmick_display\(self.*?\n(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    if not func_match:
        return {}

    func_content = func_match.group(0)

    # 각 gimmick_type 블록 찾기
    gimmick_fields = {}

    # elif/if gimmick_type == "xxx": 패턴 찾기
    type_pattern = r'(?:if|elif)\s+gimmick_type\s*==\s*"([^"]+)":(.*?)(?=\n\s*(?:elif|if|def|return|$))'

    for match in re.finditer(type_pattern, func_content, re.DOTALL):
        gimmick_type = match.group(1)
        display_code = match.group(2)

        # getattr(character, 'xxx', ...) 형태의 필드 추출
        fields = set()
        field_pattern = r'getattr\(character,\s*["\'](\w+)["\']'
        for field_match in re.finditer(field_pattern, display_code):
            field_name = field_match.group(1)
            fields.add(field_name)

        gimmick_fields[gimmick_type] = list(fields)

    return gimmick_fields


def main():
    import sys
    import io
    # Windows 콘솔 인코딩 문제 해결
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("기믹 필드명 일치성 검증")
    print("=" * 80)

    yaml_gimmicks = load_yaml_gimmicks()
    char_init_fields = extract_character_init_fields()
    ui_display_fields = extract_ui_display_fields()

    print(f"\n총 {len(yaml_gimmicks)}개 직업 YAML 발견")
    print(f"character.py에서 {len(char_init_fields)}개 기믹 타입 발견")
    print(f"combat_ui.py에서 {len(ui_display_fields)}개 기믹 타입 발견")

    # 타입별로 비교
    all_types = set()
    all_types.update(yaml_gimmicks.keys())
    all_types.update(char_init_fields.keys())
    all_types.update(ui_display_fields.keys())

    issues = []

    print("\n" + "=" * 80)
    print("상세 검증 결과")
    print("=" * 80)

    for class_name, info in yaml_gimmicks.items():
        gimmick_type = info['type']
        yaml_file = info['file']
        max_fields = info['max_fields']

        print(f"\n[{class_name}] ({yaml_file})")
        print(f"  Gimmick Type: {gimmick_type}")
        print(f"  YAML Max Fields: {list(max_fields.keys())}")

        # character.py 확인
        if gimmick_type in char_init_fields:
            char_fields = char_init_fields[gimmick_type]
            print(f"  Character Init Fields: {list(char_fields.keys())}")

            # max_ 필드가 일치하는지 확인
            char_max_fields = [k for k in char_fields.keys() if k.startswith('max_')]
            if set(max_fields.keys()) != set(char_max_fields):
                issue = f"  ⚠️  YAML의 max_ 필드와 character.py의 max_ 필드가 불일치"
                print(issue)
                issues.append(f"{class_name}: {issue}")
        else:
            issue = f"  ❌ character.py에 {gimmick_type} 초기화 코드 없음"
            print(issue)
            issues.append(f"{class_name}: {issue}")

        # combat_ui.py 확인
        if gimmick_type in ui_display_fields:
            ui_fields = ui_display_fields[gimmick_type]
            print(f"  UI Display Fields: {ui_fields}")

            # UI에서 사용하는 필드가 character.py에서 초기화되는지 확인
            if gimmick_type in char_init_fields:
                char_field_names = set(char_init_fields[gimmick_type].keys())
                missing_fields = set(ui_fields) - char_field_names

                if missing_fields:
                    issue = f"  ⚠️  UI에서 사용하지만 character.py에서 초기화하지 않는 필드: {missing_fields}"
                    print(issue)
                    issues.append(f"{class_name}: {issue}")
        else:
            issue = f"  ❌ combat_ui.py에 {gimmick_type} 표시 코드 없음"
            print(issue)
            issues.append(f"{class_name}: {issue}")

    # combat_ui.py에만 있는 기믹 타입 찾기
    print("\n" + "=" * 80)
    print("UI에만 존재하는 기믹 타입 (중복 가능성)")
    print("=" * 80)

    ui_only_types = set(ui_display_fields.keys()) - set(char_init_fields.keys())
    if ui_only_types:
        for ui_type in sorted(ui_only_types):
            print(f"  - {ui_type}: {ui_display_fields[ui_type]}")
    else:
        print("  없음")

    # 요약
    print("\n" + "=" * 80)
    print("요약")
    print("=" * 80)

    if issues:
        print(f"\n⚠️  {len(issues)}개의 문제 발견:\n")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ 모든 기믹 필드명이 일치합니다!")


if __name__ == "__main__":
    main()
