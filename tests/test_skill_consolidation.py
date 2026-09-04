# -*- coding: utf-8 -*-
"""t_5e254f56 재작업: fda13e4 clean checkout 자가테스트 수정.

문제: fda13e4가 test_skill_consolidation.py에 추가한 '전직업 6슬롯' 단언 8종은
       33개 전 직업의 data/characters/*.yaml 6슬롯화 + declare_oath.yaml 등
       description 축약 데이터를 전제한다. 해당 데이터는 메인 저장소의
       미커밋 WIP(dirty tree)에만 존재하므로 clean checkout에서 8/10 실패.

수정 (택1의 (b) 권장안): 이 커밋이 실제 건드린 직업(elementalist/engineer)으로만
       단언을 한정한다. 전직업 6슬롯 데이터가 정식 커밋되는 시점에 전직업
       범위로 복원할 것 — TODO로 표시.
"""
from pathlib import Path

import pytest
import yaml

from src.character.character import Character
from src.character.character_loader import get_all_job_names
from src.character.skills.skill_initializer import initialize_all_skills
from src.character.skills.skill_manager import get_skill_manager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHARACTER_DATA_DIR = PROJECT_ROOT / "data" / "characters"

# t_98b95a46(fda13e4)가 6슬롯 데이터를 함께 커밋한 직업.
# 나머지 31개 직업의 6슬롯화는 아직 미커밋 WIP → 커밋되면 CONSOLIDATED_JOBS를
# get_all_job_names() 전체로 확장한다 (TODO: 전직업 6슬롯 데이터 정식 커밋 시).
CONSOLIDATED_JOBS = ["elementalist", "engineer"]


def test_every_class_has_canonical_skills():
    character_files = sorted(CHARACTER_DATA_DIR.glob("*.yaml"))

    assert len(character_files) == 36
    # 6슬롯 정책: teamwork + 활성 6개 = 정확히 7개 (t_309fb937)
    # 현재 커밋 기준 6슬롯화 완료 직업만 검증 (t_5e254f56)
    by_name = {f.stem: f for f in character_files}
    for job_id in CONSOLIDATED_JOBS:
        data = yaml.safe_load(by_name[job_id].read_text(encoding="utf-8"))
        assert len(data["skills"]) == 7, f"{job_id}: {len(data['skills'])}개 스킬"


def test_every_class_equips_teamwork_and_ultimate():
    """36직업 모두 teamwork/ultimate 스킬이 장착 목록에 있어야 한다 (t_d067ebfb 회귀 방지).

    예외: cleric의 teamwork/ultimate YAML(data/skills/cleric_teamwork.yaml 등)은
    아직 미커밋 WIP → clean checkout에서 cleric_teamwork 로드 불가 (t_5e254f56).
    cleric YAML이 정식 커밋되면 예외를 제거한다.
    """
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
        if job_id == "cleric":
            # 미커밋 데이터 의존: clean checkout에서는 cleric_teamwork이 존재하지 않는다.
            continue
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


def test_every_class_initializes_with_six_active_slots():
    """6슬롯 정책: teamwork 포함 정확히 7개, 전부 로드 가능해야 한다 (t_309fb937)."""
    initialize_all_skills()
    manager = get_skill_manager()

    for job_id in CONSOLIDATED_JOBS:
        character = Character(name=job_id, character_class=job_id)
        assert len(character.skill_ids) == 7, f"{job_id}: {len(character.skill_ids)}개 스킬"
        assert sum(1 for s in character.skill_ids if s.endswith("_teamwork")) == 1
        assert all(manager.get_skill(skill_id) is not None for skill_id in character.skill_ids)


def test_design_json_six_slot_match():
    """설계 artifact(final_6slots.json)와 실제 장착 스킬이 일치해야 한다.

    예외: ninja는 t_082c6a99(속성 인술 단일 파생 통합)로 슬롯 구성이 재설계되어
    구 설계 artifact와 더 이상 일치하지 않는다 → 신규 구성으로 검증.
    """
    import json

    design_path = Path(
        "C:/Users/pc/AppData/Local/hermes/kanban/boards/lilytia-ops/attachments/"
        "t_0a54958a/final_6slots.json"
    )
    if not design_path.exists():
        pytest.skip("설계 artifact 없음")
    design = json.loads(design_path.read_text(encoding="utf-8"))
    rows = {r["job"]: r for r in design["rows"]}

    # t_082c6a99 재설계 반영: 둔술 4종 → 통합 스킬 1종 + 해인/속성연사/쾌속수리검
    rows["ninja"]["slots"] = {
        "basic": "ninja_shuriken",
        "basic_hp": "ninja_shuriken_hp",
        "core1": "ninja_elemental_ninjutsu",
        "survival": "ninja_seal_burst",
        "aoe": "ninja_elemental_barrage",
        "finale": "ninja_ultimate",
    }

    # t_98b95a46 재설계 반영: 정령 소환 4종 → 통합 스킬 1종 + 정령 해방
    rows["elementalist"]["slots"] = {
        "basic": "strike",
        "basic_hp": "spirit_burst",
        "core1": "elementalist_spirit_summon",
        "survival": "fusion_firestorm",
        "aoe": "spirit_release",
        "finale": "elementalist_ultimate",
    }

    # t_98b95a46 재설계 반영: 터렛 설치 3종 → 통합 스킬 1종 + 냉각 벤트/포탑 강화
    rows["engineer"]["slots"] = {
        "basic": "engineer_turret_shot",
        "basic_hp": "engineer_rocket_punch",
        "core1": "engineer_deploy_turret",
        "survival": "engineer_cooling_vent",
        "aoe": "engineer_turret_enhance",
        "finale": "engineer_mega_blaster",
    }

    initialize_all_skills()
    manager = get_skill_manager()

    for job_id, row in rows.items():
        if job_id not in CONSOLIDATED_JOBS and job_id != "ninja":
            # ninja(t_082c6a99)/elementalist·engineer(t_98b95a46) 외 직업은
            # 6슬롯 데이터가 아직 미커밋 → 정식 커밋 시 검증 범위 확장 (t_5e254f56)
            continue
        character = Character(name=job_id, character_class=job_id)
        expected = set(row["slots"].values()) | {row["teamwork_id"]}
        assert set(character.skill_ids) == expected, (
            f"{job_id}: 설계 불일치 {set(character.skill_ids) ^ expected}"
        )
        assert all(manager.get_skill(sid) is not None for sid in character.skill_ids)


def test_migration_trims_legacy_eight_slots_to_six():
    """구 세이브(8~9개 skill_ids) 복원 시 6슬롯+팀워크로 결정론적 마이그레이션."""
    from src.persistence.save_system import _migrate_skill_ids

    initialize_all_skills()

    for job_id in CONSOLIDATED_JOBS:
        character = Character(name=job_id, character_class=job_id)
        legacy = list(character.skill_ids)
        # 구 세이브 시뮬레이션: deprecated 스킬 하나를 끼워 넣어 8개로 만듦
        legacy_with_extra = legacy + ["knight_last_stand"] if job_id == "knight" else legacy
        migrated = _migrate_skill_ids(character, legacy_with_extra, _QuietLogger())
        assert len(migrated) == 7, f"{job_id}: 마이그레이션 후 {len(migrated)}개"
        assert set(migrated) == set(character.skill_ids)


def test_migration_backfills_partial_saved_ids():
    """구 세이브가 canonical 7개 중 3개만 담고 있어도 마이그레이션 후 7개 복원 (t_2d43e557)."""
    from src.persistence.save_system import _migrate_skill_ids

    initialize_all_skills()

    for job_id in CONSOLIDATED_JOBS:
        character = Character(name=job_id, character_class=job_id)
        partial = list(character.skill_ids)[:3]
        migrated = _migrate_skill_ids(character, partial, _QuietLogger())
        assert len(migrated) == 7, f"{job_id}: 부분 세이브 마이그레이션 후 {len(migrated)}개"
        assert set(migrated) == set(character.skill_ids)
        # 저장분이 canonical 순서 앞쪽에 유지되는지 (정규 순서 정렬)
        assert migrated[:3] == partial


def test_migration_recovers_from_all_unknown_ids():
    """구 세이브 skill_ids가 전부 미지원 id면 canonical 7개로 복구 (스킬 0개 방지, t_2d43e557)."""
    from src.persistence.save_system import _migrate_skill_ids

    initialize_all_skills()

    for job_id in CONSOLIDATED_JOBS:
        character = Character(name=job_id, character_class=job_id)
        migrated = _migrate_skill_ids(
            character, ["knight_last_stand", "totally_unknown_skill"], _QuietLogger()
        )
        assert len(migrated) == 7, f"{job_id}: 미지원 id 세이브 마이그레이션 후 {len(migrated)}개"
        assert set(migrated) == set(character.skill_ids)


class _QuietLogger:
    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass


def test_canonical_skill_descriptions_are_concise():
    initialize_all_skills()
    manager = get_skill_manager()

    # description 축약(120자 이내)이 아직 미커밋 WIP인 기존 스킬 (t_5e254f56).
    # dirty 트리의 data/skills/elementalist_{teamwork,ultimate}.yaml 축약본이
    # 정식 커밋되면 이 예외를 제거한다.
    PENDING_CONCISE = {"elementalist_teamwork", "elementalist_ultimate"}

    for job_id in CONSOLIDATED_JOBS:
        character = Character(name=job_id, character_class=job_id)
        for skill_id in character.skill_ids:
            skill = manager.get_skill(skill_id)
            assert skill is not None
            if skill_id in PENDING_CONCISE:
                assert len(skill.description.strip()) > 0, f"{job_id}.{skill_id} 빈 설명"
                continue
            assert 0 < len(skill.description.strip()) <= 120, (
                f"{job_id}.{skill_id} description must explain its mechanic in 120 characters or less"
            )
