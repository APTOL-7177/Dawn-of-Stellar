# -*- coding: utf-8 -*-
"""정령술사 4정령 소환 + 엔지니어 터렛 5종 단일 파생 통합 테스트 (t_98b95a46).

설계: elementalist_spirit_summon_design.md (t_df906dd2)
      engineer_turret_variant_design_1.md (t_82b1bff1)
- variants 엔진 확장: costs_override / extra_gimmick / spirit_type 복원키
- D3 requires_unsummoned_spirit 선차단 / D4 summon_spirit 변형 인지
- D6 융합 우선 greedy / D10·E4 세이브 필드 / E1~E3 런타임 정본화
"""
from pathlib import Path

import yaml

import src.character.gimmick_updater  # noqa: F401  # SKILL_EXECUTE 핸들러 등록 보장

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SPIRITS = ["fire", "water", "wind", "earth"]
LEGACY_SUMMONS = [f"summon_{s}_spirit" for s in SPIRITS]
NEW_SUMMON_ID = "elementalist_spirit_summon"
TURRET_TYPES = ["normal", "fire", "ice", "explosive", "heal"]
NEW_TURRET_ID = "engineer_deploy_turret"


def _make_char(character_class: str, name: str):
    from src.character.character import Character
    from src.character.skills.skill_initializer import initialize_all_skills
    initialize_all_skills()
    return Character(name=name, character_class=character_class)


# ─────────────────────────────────────────────────────────────
# T1. YAML 정본 무결성
# ─────────────────────────────────────────────────────────────
class TestT1YamlIntegrity:
    def test_unified_summon_yaml(self):
        path = PROJECT_ROOT / "data" / "skills" / "elementalist_spirit_summon.yaml"
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["id"] == NEW_SUMMON_ID
        assert data["costs"]["mp"] == 10
        opts = data["variants"]["options"]
        assert set(opts.keys()) == set(SPIRITS)
        assert data["variants"]["default"] == "fire"
        assert data["metadata"]["requires_unsummoned_spirit"] is True
        assert data["metadata"]["variant_policy"] == "elementalist_fusion"
        # base.effects는 custom 1개뿐 — 정적 gimmick SET 금지 (설계 §2.4 버그 회피)
        effects = data["base"]["effects"]
        assert len(effects) == 1 and effects[0]["type"] == "custom"

    def test_unified_turret_yaml(self):
        path = PROJECT_ROOT / "data" / "skills" / "engineer_deploy_turret.yaml"
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["id"] == NEW_TURRET_ID
        assert data["costs"]["mp"] == 0
        opts = data["variants"]["options"]
        assert set(opts.keys()) == set(TURRET_TYPES)
        assert data["variants"]["default"] == "normal"
        # thunder 신규 변형 금지
        assert "thunder" not in opts
        # 변형별 비용/기믹
        assert opts["fire"]["costs_override"] == {"mp": 6}
        assert opts["ice"]["costs_override"] == {"mp": 7}
        assert opts["explosive"]["costs_override"] == {"mp": 10}
        assert opts["heal"]["costs_override"] == {"mp": 12}
        assert opts["fire"]["extra_gimmick"][0]["field"] == "fire_turret_count"
        # explosive는 1차 구현 단일 타겟 — aoe 키 제거 (E7 선언-구현 일치)
        assert "aoe" not in opts["explosive"]["metadata_override"]
        # base.effects는 turret_count +1만
        base = data["base"]["effects"]
        assert len(base) == 1 and base[0]["field"] == "turret_count"

    def test_job_yaml_equips(self):
        ele = yaml.safe_load(
            (PROJECT_ROOT / "data" / "characters" / "elementalist.yaml").read_text(encoding="utf-8")
        )
        assert len(ele["skills"]) == 7
        assert "spirit_summon" in ele["skills"]
        for legacy in ("summon_fire_spirit", "summon_water_spirit"):
            assert legacy not in ele["skills"]
        assert "spirit_release" in ele["skills"]

        eng = yaml.safe_load(
            (PROJECT_ROOT / "data" / "characters" / "engineer.yaml").read_text(encoding="utf-8")
        )
        assert len(eng["skills"]) == 7
        assert "deploy_turret" in eng["skills"]
        assert "cooling_vent" in eng["skills"] and "turret_enhance" in eng["skills"]
        for legacy in ("deploy_fire_turret", "deploy_ice_turret"):
            assert legacy not in eng["skills"]

    def test_legacy_yamls_deprecated(self):
        for sid in LEGACY_SUMMONS + [
            "engineer_deploy_fire_turret", "engineer_deploy_ice_turret",
            "engineer_deploy_explosive_turret", "engineer_deploy_heal_turret",
            "engineer_deploy_thunder_turret",
        ]:
            path = PROJECT_ROOT / "data" / "skills" / f"{sid}.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            meta = data.get("metadata") or {}
            assert meta.get("state") == "deprecated", f"{sid}: state: deprecated 누락"

    def test_aliases_registered(self):
        data = yaml.safe_load(
            (PROJECT_ROOT / "data" / "skill_aliases.yaml").read_text(encoding="utf-8")
        )
        aliases = data["aliases"]
        for sid in LEGACY_SUMMONS:
            assert aliases.get(sid) == NEW_SUMMON_ID, sid
        for sid in ["engineer_deploy_fire_turret", "engineer_deploy_ice_turret",
                    "engineer_deploy_explosive_turret", "engineer_deploy_heal_turret",
                    "engineer_deploy_thunder_turret"]:
            assert aliases.get(sid) == NEW_TURRET_ID, sid


# ─────────────────────────────────────────────────────────────
# T2. 정령 변형 실행 + 비용 전 중복 차단
# ─────────────────────────────────────────────────────────────
class TestT2SpiritVariantExecution:
    def test_variant_summon_and_no_mutation(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("elementalist", "테스트정령")
        assert NEW_SUMMON_ID in char.skill_ids
        skill = get_skill_manager().get_skill(NEW_SUMMON_ID)

        skill.metadata["_selected_variant"] = "water"
        result = skill.execute(char, char, {})
        assert result.success
        assert getattr(char, "spirit_water", 0) == 1
        assert char.spirit_slots == ["water"]
        # 비-mutating: 실행 후 metadata 잔존 없음
        assert "spirit_type" not in skill.metadata
        assert "_active_variant" not in skill.metadata
        assert "_variant_cost_override" not in skill.metadata

    def test_duplicate_summon_blocked_before_cost(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("elementalist", "테스트정령2")
        skill = get_skill_manager().get_skill(NEW_SUMMON_ID)

        skill.metadata["_selected_variant"] = "fire"
        assert skill.execute(char, char, {}).success
        mp_before = char.current_mp
        skill.metadata["_selected_variant"] = "fire"
        result = skill.execute(char, char, {})
        assert not result.success
        assert "이미 소환" in result.message
        assert char.current_mp == mp_before  # MP 무차감 (D3)

    def test_auto_replace_oldest(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("elementalist", "테스트정령3")
        skill = get_skill_manager().get_skill(NEW_SUMMON_ID)
        for v in ("fire", "water", "wind"):
            skill.metadata["_selected_variant"] = v
            skill.execute(char, char, {})
        # 3번째 소환 → 가장 오래된 fire 교체
        assert char.spirit_slots == ["water", "wind"]
        assert getattr(char, "spirit_fire", 0) == 0

    def test_all_four_spirits_reachable(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("elementalist", "테스트정령4")
        skill = get_skill_manager().get_skill(NEW_SUMMON_ID)
        summoned = set()
        for v in SPIRITS:
            skill.metadata["_selected_variant"] = v
            result = skill.execute(char, char, {})
            if result.success:
                summoned.add(v)
        assert summoned == set(SPIRITS)  # 통합 전 wind/earth 미장착 → 이제 4정령 도달


# ─────────────────────────────────────────────────────────────
# T4. 세이브 마이그레이션
# ─────────────────────────────────────────────────────────────
class TestT4Migration:
    def test_old_saves_collapse(self):
        from src.persistence.save_system import _migrate_skill_ids
        char = _make_char("elementalist", "마이그정령")
        old = ["teamwork", "strike", *LEGACY_SUMMONS, "spirit_burst",
               "fusion_firestorm", "ultimate"]
        mig = _migrate_skill_ids(char, old, _FakeLogger())
        assert len(mig) == 7
        assert mig.count(NEW_SUMMON_ID) == 1

    def test_engineer_old_saves_collapse(self):
        from src.persistence.save_system import _migrate_skill_ids
        char = _make_char("engineer", "마이그엔지니어")
        old = ["teamwork", "turret_shot", "deploy_fire_turret", "deploy_ice_turret",
               "deploy_turret", "rocket_punch", "mega_blaster"]
        mig = _migrate_skill_ids(char, old, _FakeLogger())
        assert len(mig) == 7
        assert mig.count(NEW_TURRET_ID) == 1
        assert "engineer_cooling_vent" in mig and "engineer_turret_enhance" in mig


class _FakeLogger:
    def info(self, *a):
        pass

    def warning(self, *a):
        pass


# ─────────────────────────────────────────────────────────────
# T5. AI 융합 우선 greedy / T10 엔지니어 greedy
# ─────────────────────────────────────────────────────────────
class TestT5AiGreedy:
    def test_elementalist_fusion_first(self):
        from src.character.llm_bot_helpers import pick_elementalist_variant
        char = _make_char("elementalist", "AI정령")
        assert pick_elementalist_variant(char) == "fire"          # 빈 슬롯 → 첫 융합 첫 requires
        char.spirit_fire = 1
        char.spirit_slots = ["fire"]
        assert pick_elementalist_variant(char) == "wind"          # fusion_firestorm [fire,wind]
        char.spirit_wind = 1
        char.spirit_slots = ["fire", "wind"]
        assert pick_elementalist_variant(char) == "water"         # 완성 → 첫 비활성
        char.spirit_fire = 0
        char.spirit_slots = ["wind"]
        assert pick_elementalist_variant(char) == "fire"          # [wind] → 빠진 쪽

    def test_engineer_greedy(self):
        from src.character.llm_bot_helpers import pick_engineer_variant
        char = _make_char("engineer", "AI엔지니어")
        assert pick_engineer_variant(char) == "normal"            # 포탑 0기 → 무료
        char.turret_count = 1
        assert pick_engineer_variant(None) == "normal"            # 정보 부재 폴백

    def test_apply_variant_actor_dispatch(self):
        from src.character.llm_bot_helpers import apply_variant_to_action_skill
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("elementalist", "AI정령2")
        skill = get_skill_manager().get_skill(NEW_SUMMON_ID)
        selected = apply_variant_to_action_skill(skill, None, actor=char)
        assert selected == "fire"

    def test_ninja_signature_regression(self):
        from src.character.llm_bot_helpers import pick_ninja_variant, apply_variant_to_action_skill
        assert pick_ninja_variant({}) == "fire"
        char = _make_char("ninja", "AI닌자")
        from src.character.skills.skill_manager import get_skill_manager
        skill = get_skill_manager().get_skill("ninja_elemental_ninjutsu")
        selected = apply_variant_to_action_skill(skill, {"fire": 1})
        assert selected == "ice"


# ─────────────────────────────────────────────────────────────
# T6. 엔지니어 변형별 비용·기믹·레지스트리 (T2/T3/T5 엔지니어판)
# ─────────────────────────────────────────────────────────────
class TestT6TurretVariants:
    def test_fire_variant_cost_and_gimmick_and_registry(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("engineer", "테스트엔지니어")
        assert NEW_TURRET_ID in char.skill_ids
        assert any(sid.endswith("_teamwork") for sid in char.skill_ids)
        assert "engineer_mega_blaster" in char.skill_ids  # 궁극기 (meta.ultimate, is_ultimate 플래그 미설정)
        # double_turret 특성이 기본 available_traits에 있어 설치마다 +2가 된다 —
        # 순수 증분만 검증하기 위해 모든 트레이트 목록에서 제외
        for attr in ("active_traits", "available_traits", "traits", "selected_traits"):
            if hasattr(char, attr):
                setattr(char, attr, [
                    t for t in (getattr(char, attr, None) or [])
                    if (t if isinstance(t, str) else t.get("id")) != "double_turret"
                ])
        skill = get_skill_manager().get_skill(NEW_TURRET_ID)

        skill.metadata["_selected_variant"] = "fire"
        result = skill.execute(char, char, {})
        assert result.success
        assert char.fire_turret_count == 1
        assert char.turret_count == 1
        assert char.current_mp == char.max_mp - 9  # 6 × 1.5 = 9
        registry = getattr(char, "turret_damage_registry", {})
        assert registry.get("fire", {}).get("damage") == 0.6
        assert registry.get("fire", {}).get("burn_chance") == 0.2
        # 비-mutating
        assert "_variant_cost_override" not in skill.metadata

    def test_normal_variant_free(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("engineer", "테스트엔지니어2")
        for attr in ("active_traits", "available_traits", "traits", "selected_traits"):
            if hasattr(char, attr):
                setattr(char, attr, [])
        skill = get_skill_manager().get_skill(NEW_TURRET_ID)
        skill.metadata["_selected_variant"] = "normal"
        result = skill.execute(char, char, {})
        assert result.success
        assert char.current_mp == char.max_mp
        assert char.turret_count == 1
        assert getattr(char, "fire_turret_count", 0) == 0

    def test_ice_no_cross_contamination(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("engineer", "테스트엔지니어3")
        for attr in ("active_traits", "available_traits", "traits", "selected_traits"):
            if hasattr(char, attr):
                setattr(char, attr, [])
        skill = get_skill_manager().get_skill(NEW_TURRET_ID)
        skill.metadata["_selected_variant"] = "fire"
        skill.execute(char, char, {})
        skill.metadata["_selected_variant"] = "ice"
        skill.execute(char, char, {})
        assert char.fire_turret_count == 1 and char.ice_turret_count == 1
        registry = getattr(char, "turret_damage_registry", {})
        assert registry.get("fire", {}).get("damage") == 0.6
        assert registry.get("ice", {}).get("damage") == 0.4
        assert registry.get("ice", {}).get("slow_chance") == 0.25


# ─────────────────────────────────────────────────────────────
# T8. 정령/포탑 상태 세이브 필드 (D10/E4)
# ─────────────────────────────────────────────────────────────
class TestT8SaveFields:
    def test_spirit_fields_saved(self):
        char = _make_char("elementalist", "세이브정령")
        state = char._get_gimmick_state()
        for field in ("spirit_fire", "spirit_water", "spirit_wind", "spirit_earth",
                      "spirit_slots", "active_resonance", "resonance_multiplier", "max_spirits"):
            assert field in state, field

    def test_turret_fields_saved(self):
        char = _make_char("engineer", "세이브엔지니어")
        state = char._get_gimmick_state()
        for field in ("turret_count", "fire_turret_count", "ice_turret_count",
                      "thunder_turret_count", "explosive_turret_count", "heal_turret_count",
                      "turret_damage_registry"):
            assert field in state, field


# ─────────────────────────────────────────────────────────────
# T9. 공유 인스턴스 위생 + E5 turret_enhance strength 키
# ─────────────────────────────────────────────────────────────
class TestT9HygieneAndEnhance:
    def test_no_metadata_leak_on_failures(self):
        from src.character.skills.skill_manager import get_skill_manager
        char = _make_char("elementalist", "위생정령")
        char.current_mp = 0  # MP 부족 실패 경로
        skill = get_skill_manager().get_skill(NEW_SUMMON_ID)
        skill.metadata["_selected_variant"] = "wind"
        skill.execute(char, char, {})
        assert "spirit_type" not in skill.metadata
        assert "_variant_cost_override" not in skill.metadata

    def test_turret_enhance_uses_strength_key(self):
        """E5: Stats enum에 attack 없음 → strength 키 정규화 확인."""
        path = PROJECT_ROOT / "data" / "skills" / "engineer_turret_enhance.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        stats = data["effects"][0]["stats"]
        assert "attack" not in stats
        assert "strength" in stats


# ─────────────────────────────────────────────────────────────
# T10b/T10c/T10d. 정령 고유 + 팀워크/궁극기 회귀
# ─────────────────────────────────────────────────────────────
class TestT10Regression:
    def test_teamwork_and_ultimate_equipped(self):
        ele = _make_char("elementalist", "회귀정령")
        eng = _make_char("engineer", "회귀엔지니어")
        assert any(sid.endswith("_teamwork") for sid in ele.skill_ids)
        assert "elementalist_ultimate" in ele.skill_ids
        assert any(sid.endswith("_teamwork") for sid in eng.skill_ids)
        assert "engineer_mega_blaster" in eng.skill_ids

    def test_deprecated_skills_not_registered(self):
        """T10d: 구 id로 get_skill하면 통합 스킬로 resolve (deprecated 파일 미등록)."""
        from src.character.skills.skill_manager import get_skill_manager
        _make_char("elementalist", "정규정령")
        m = get_skill_manager()
        for sid in LEGACY_SUMMONS:
            resolved = m.resolve_skill_id(sid)
            assert resolved == NEW_SUMMON_ID, sid

    def test_job_prompts_updated(self):
        from src.ai.job_prompts import JOB_STRATEGIES
        ele = JOB_STRATEGIES["elementalist"]
        assert "skill_spirit_summon" in ele.priority_actions
        assert "skill_summon_fire" not in ele.priority_actions
        eng = JOB_STRATEGIES["engineer"]
        assert "skill_deploy_turret" in eng.priority_actions
        assert "skill_overclock_mode" not in eng.priority_actions
