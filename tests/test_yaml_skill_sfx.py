"""YAML 스킬 SFX 로딩 테스트"""

import pytest
from pathlib import Path
import yaml
from src.character.skills.skill_manager import SkillManager
from src.character.skills.yaml_skill_loader import load_yaml_skills


def test_all_yaml_skills_have_sfx():
    """모든 YAML 스킬이 SFX를 가지고 있는지 확인"""
    skills_dir = Path("data/skills")

    # 모든 YAML 파일 확인
    yaml_files = list(skills_dir.glob("*.yaml"))
    assert len(yaml_files) > 0, "스킬 YAML 파일이 없습니다"

    missing_sfx = []

    for yaml_file in yaml_files:
        with yaml_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # deprecated 스킬은 스킵
        if data.get("metadata", {}).get("state") == "deprecated":
            continue

        # SFX 필드 확인
        if "sfx" not in data:
            missing_sfx.append(yaml_file.name)

    # 결과 출력
    if missing_sfx:
        print(f"\nSFX가 없는 스킬: {len(missing_sfx)}개")
        for filename in missing_sfx[:10]:  # 최대 10개만 출력
            print(f"  - {filename}")
    else:
        print(f"\n모든 스킬에 SFX가 정상적으로 추가되었습니다! (총 {len(yaml_files)}개)")

    assert len(missing_sfx) == 0, f"SFX가 없는 스킬: {missing_sfx}"


def test_yaml_skills_load_correctly():
    """YAML 스킬이 SkillManager에 정상적으로 로드되는지 확인"""
    skill_manager = SkillManager()
    registered_ids = load_yaml_skills(skill_manager)

    assert len(registered_ids) > 0, "등록된 스킬이 없습니다"
    print(f"\n{len(registered_ids)}개 스킬이 정상적으로 로드되었습니다")

    # 샘플 스킬 확인
    sample_skills = [
        "paladin_holy_smite",
        "shaman_spirit_arrow",
        "elementalist_teamwork",
        "knight_bash",
        "hacker_basic_breach",
    ]

    for skill_id in sample_skills:
        skill = skill_manager.get_skill(skill_id)
        if skill:
            assert skill.sfx is not None, f"{skill_id}의 SFX가 None입니다"
            assert isinstance(skill.sfx, tuple), f"{skill_id}의 SFX가 tuple이 아닙니다"
            assert len(skill.sfx) == 2, f"{skill_id}의 SFX 길이가 2가 아닙니다"
            print(f"  ✓ {skill_id}: {skill.sfx}")
        else:
            print(f"  ✗ {skill_id}: 스킬을 찾을 수 없습니다")


def test_sfx_format():
    """SFX 포맷이 올바른지 확인"""
    skills_dir = Path("data/skills")

    invalid_sfx = []

    for yaml_file in skills_dir.glob("*.yaml"):
        with yaml_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sfx = data.get("sfx")
        if sfx:
            # SFX는 [category, name] 형태여야 함
            if not isinstance(sfx, list) or len(sfx) != 2:
                invalid_sfx.append((yaml_file.name, sfx))
            elif not isinstance(sfx[0], str) or not isinstance(sfx[1], str):
                invalid_sfx.append((yaml_file.name, sfx))

    if invalid_sfx:
        print(f"\n잘못된 SFX 포맷: {len(invalid_sfx)}개")
        for filename, sfx in invalid_sfx[:5]:
            print(f"  - {filename}: {sfx}")
    else:
        print(f"\n모든 SFX 포맷이 올바릅니다!")

    assert len(invalid_sfx) == 0, f"잘못된 SFX 포맷: {invalid_sfx}"


if __name__ == "__main__":
    print("=" * 60)
    print("YAML 스킬 SFX 테스트")
    print("=" * 60)

    test_all_yaml_skills_have_sfx()
    test_sfx_format()
    test_yaml_skills_load_correctly()

    print("\n" + "=" * 60)
    print("모든 테스트 통과!")
    print("=" * 60)
