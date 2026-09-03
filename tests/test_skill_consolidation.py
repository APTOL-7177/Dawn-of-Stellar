from pathlib import Path

import yaml

from src.character.character import Character
from src.character.character_loader import get_all_job_names
from src.character.skills.skill_initializer import initialize_all_skills
from src.character.skills.skill_manager import get_skill_manager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHARACTER_DATA_DIR = PROJECT_ROOT / "data" / "characters"


def test_every_class_has_canonical_skills():
    character_files = sorted(CHARACTER_DATA_DIR.glob("*.yaml"))

    assert len(character_files) == 36
    # active 스킬 8개 + teamwork/ultimate 장착 보강으로 8~9개 허용
    assert all(
        len(yaml.safe_load(character_file.read_text(encoding="utf-8"))["skills"]) in (8, 9)
        for character_file in character_files
    )


def test_every_class_equips_teamwork_and_ultimate():
    """36직업 모두 teamwork/ultimate 스킬이 장착 목록에 있어야 한다 (t_d067ebfb 회귀 방지)."""
    from src.character.skills.skill_manager import get_skill_manager

    initialize_all_skills()
    manager = get_skill_manager()

    for job_id in get_all_job_names():
        character = Character(name=job_id, character_class=job_id)
        tw = [sid for sid in character.skill_ids if sid.endswith("_teamwork")]
        ults = []
        for sid in character.skill_ids:
            skill = manager.get_skill(sid)
            if skill and (getattr(skill, "is_ultimate", False) or (getattr(skill, "metadata", {}) or {}).get("ultimate")):
                ults.append(sid)
        assert tw, f"{job_id}: teamwork 스킬 미장착"
        assert ults, f"{job_id}: ultimate 스킬 미장착"


def test_yaml_authority_over_python_redefinitions():
    """YAML 단일 정본: 초기화 후에도 YAML 스킬이 Python 정의로 덮어써지지 않아야 한다."""
    from src.character.skills.yaml_skill_loader import load_yaml_skills
    from src.character.skills.skill_manager import SkillManager

    initialize_all_skills()
    live_manager = get_skill_manager()
    yaml_only_manager = SkillManager()
    yaml_ids = load_yaml_skills(yaml_only_manager)

    mismatches = []
    for sid in yaml_ids:
        live = live_manager._skills.get(sid)
        canonical = yaml_only_manager._skills[sid]
        if (
            live is None
            or type(live) is not type(canonical)
            or live.name != canonical.name
            or len(live.effects) != len(canonical.effects)
            or len(live.costs) != len(canonical.costs)
        ):
            mismatches.append(sid)
    assert not mismatches, f"YAML 정본 재정의 잔존: {mismatches[:10]}"


def test_legacy_aliases_resolve_to_canonical_skills():
    initialize_all_skills()
    manager = get_skill_manager()
    aliases = yaml.safe_load((PROJECT_ROOT / "data" / "skill_aliases.yaml").read_text(encoding="utf-8"))["aliases"]

    for legacy_id, canonical_id in aliases.items():
        assert manager.resolve_skill_id(legacy_id) == canonical_id
        assert manager.get_skill(legacy_id) is manager.get_skill(canonical_id)


def test_every_class_initializes_with_eight_or_nine_loadable_skills():
    initialize_all_skills()
    manager = get_skill_manager()

    for job_id in get_all_job_names():
        character = Character(name=job_id, character_class=job_id)
        assert len(character.skill_ids) in (8, 9)
        assert all(manager.get_skill(skill_id) is not None for skill_id in character.skill_ids)


def test_canonical_skill_descriptions_are_concise():
    initialize_all_skills()
    manager = get_skill_manager()

    for job_id in get_all_job_names():
        character = Character(name=job_id, character_class=job_id)
        for skill_id in character.skill_ids:
            skill = manager.get_skill(skill_id)
            assert skill is not None
            assert 0 < len(skill.description.strip()) <= 120, (
                f"{job_id}.{skill_id} description must explain its mechanic in 120 characters or less"
            )
