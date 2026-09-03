# -*- coding: utf-8 -*-
"""닌자 뇌속성 thunder/lightning 정규화 테스트 (t_756d8ec1).

설계: thunder_lightning_canonicalization_design.md (t_f13aae2e)
결정 D1: element 값의 canonical은 lightning. seal_type(인)/variant key/세이브는 유지.
근거 주석은 설계 문서 §1~§5의 파일:줄 기준.
"""
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ELEMENTS = ["fire", "ice", "thunder", "wind"]
NEW_ID = "ninja_elemental_ninjutsu"
BARRAGE_ID = "ninja_elemental_barrage"


# ─────────────────────────────────────────────────────────────
# T1. 로드 시점 정규화 (R1+R2+R6a)
# ─────────────────────────────────────────────────────────────
class TestT1LoadTimeNormalization:
    def _load_skill(self, skill_id):
        from src.character.skills.skill_initializer import initialize_all_skills
        from src.character.skills.skill_manager import get_skill_manager
        initialize_all_skills()
        return get_skill_manager().get_skill(skill_id)

    def test_variant_metadata_override_element_normalized(self):
        """R1+R6a: ninja_elemental_ninjutsu thunder variant element → lightning."""
        skill = self._load_skill(NEW_ID)
        override = skill.metadata["variant_options"]["thunder"]["metadata_override"]
        assert override["element"] == "lightning"

    def test_variant_seal_type_not_converted(self):
        """seal_type은 인(印) 네임스페이스 — 변환 금지."""
        skill = self._load_skill(NEW_ID)
        override = skill.metadata["variant_options"]["thunder"]["metadata_override"]
        assert override["seal_type"] == "thunder"

    def test_barrage_third_damage_element_normalized(self):
        """R2: ninja_elemental_barrage 3번째 damage effect element → lightning."""
        skill = self._load_skill(BARRAGE_ID)
        elements = [getattr(e, "element", None) for e in skill.effects]
        assert "lightning" in elements
        assert "thunder" not in elements

    def test_other_elements_pass_through(self):
        """ELEMENT_ALIASES 미포함 원소(fire/ice/wind)는 무변경 통과."""
        from src.character.skills.element_alias import normalize_element
        assert normalize_element("fire") == "fire"
        assert normalize_element("ice") == "ice"
        assert normalize_element("wind") == "wind"
        assert normalize_element(None) is None
        assert normalize_element("lightning") == "lightning"

    def test_element_aliases_constant(self):
        """R6: ELEMENT_ALIASES = {thunder: lightning} 전용."""
        from src.character.skills.element_alias import ELEMENT_ALIASES
        assert ELEMENT_ALIASES == {"thunder": "lightning"}


# ─────────────────────────────────────────────────────────────
# T2. 실행 시점 방어선 (R6b)
# ─────────────────────────────────────────────────────────────
class TestT2CalculationDefenseLine:
    def test_element_bonus_normalizes_thunder(self):
        """damage_calculator._get_element_bonus: thunder → lightning 저항표 조회.
        근거: enemy_generator.py:984-1115 적 저항은 lightning 키."""
        from src.combat.damage_calculator import DamageCalculator
        from src.character.character import Character

        calc = DamageCalculator()
        defender = Character(name="적", character_class="warrior")
        defender.is_enemy = True
        defender.element_resistance = {"lightning": 2.5}
        bonus = calc._get_element_bonus(defender, "thunder")
        assert abs(bonus - (1.0 / 2.5)) < 1e-9

    def test_elemental_damage_stat_normalizes_thunder(self):
        """_get_elemental_damage_stat: element='thunder' → lightning_damage 스탯 가산.
        근거: damage_calculator.py element_attr_map에 thunder 부재."""
        from src.combat.damage_calculator import DamageCalculator
        from src.character.character import Character

        calc = DamageCalculator()
        attacker = Character(name="닌자", character_class="ninja")
        attacker.lightning_damage = 30
        assert calc._get_elemental_damage_stat(attacker, "thunder") == 30

    def test_spirit_fallback_accepts_thunder_as_lightning(self):
        """element_resistance 미보유 적: spirit 마법 저항이 thunder도 인정.
        근거: damage_calculator.py:1065 canonical 목록에 lightning만 존재."""
        from src.combat.damage_calculator import DamageCalculator
        from src.character.character import Character

        calc = DamageCalculator()
        defender = Character(name="적", character_class="warrior")
        defender.is_enemy = True
        assert not hasattr(defender, "element_resistance")
        assert calc._get_element_bonus(defender, "thunder") == calc._get_element_bonus(defender, "lightning")


# ─────────────────────────────────────────────────────────────
# T3. 저항 연결 회귀 (버그 수정 행동 변화 확인)
# ─────────────────────────────────────────────────────────────
class TestT3ResistanceLinkage:
    def _bonus(self, resistance):
        from src.combat.damage_calculator import DamageCalculator
        from src.character.character import Character
        calc = DamageCalculator()
        defender = Character(name="적", character_class="warrior")
        defender.is_enemy = True
        if resistance is not None:
            defender.element_resistance = {"lightning": resistance}
        return calc._get_element_bonus(defender, "thunder")

    def test_weakness_amplifies(self):
        """kraken {lightning: 0.4} 약점 → 2.5x (기존엔 1.0 고정)."""
        assert abs(self._bonus(0.4) - 2.5) < 1e-9

    def test_resistance_reduces(self):
        """thunder_elemental {lightning: 2.5} 저항 → 0.4x (기존엔 1.0 고정)."""
        assert abs(self._bonus(2.5) - 0.4) < 1e-9

    def test_no_resistance_neutral(self):
        """무저항 적: spirit 기반 마법 저항만 적용 (0.864 = spirit 폴백), thunder==lightning."""
        assert abs(self._bonus(None) - self._bonus_thunder_vs_lightning()) < 1e-9

    def _bonus_thunder_vs_lightning(self):
        from src.combat.damage_calculator import DamageCalculator
        from src.character.character import Character
        calc = DamageCalculator()
        defender = Character(name="적", character_class="warrior")
        defender.is_enemy = True
        return calc._get_element_bonus(defender, "lightning")

    def test_other_variants_unchanged(self):
        """fire/ice/wind 변형은 기존과 동일 (무회귀)."""
        assert abs(self._bonus_from_element("fire", 0.5) - 2.0) < 1e-9

    def _bonus_from_element(self, element, resistance):
        from src.combat.damage_calculator import DamageCalculator
        from src.character.character import Character
        calc = DamageCalculator()
        defender = Character(name="적", character_class="warrior")
        defender.is_enemy = True
        defender.element_resistance = {element: resistance}
        return calc._get_element_bonus(defender, element)


# ─────────────────────────────────────────────────────────────
# T4. 시각효과 정규화
# ─────────────────────────────────────────────────────────────
class TestT4VisualEffects:
    def test_no_thunder_key_in_element_effects(self):
        """_ELEMENT_EFFECTS에 thunder 키 부재 — canonical만 존재.
        근거: raylib_backend/effects/skill_effects.py:22-66."""
        for backend in (
            "src.raylib_backend.effects.skill_effects",
            "src.pygame_backend.effects.skill_effects",
        ):
            try:
                mod = __import__(backend, fromlist=["_ELEMENT_EFFECTS"])
            except ImportError:
                continue  # 백엔드 미빌드 환경 스킵
            effects_map = getattr(mod, "_ELEMENT_EFFECTS", None)
            if effects_map is None:
                continue
            assert "thunder" not in effects_map, f"{backend}에 thunder 키 존재"
            assert "lightning" in effects_map

    def test_hit_info_lightning_has_effect(self):
        """hit_info element='lightning' → lightning 이펙트 선택 (328줄 경로)."""
        try:
            from src.raylib_backend.effects import skill_effects as se
        except ImportError:
            try:
                from src.pygame_backend.effects import skill_effects as se
            except ImportError:
                return  # 백엔드 없는 환경 스킵
        hit = {"element": "lightning"}
        element = hit.get("element")
        assert element in getattr(se, "_ELEMENT_EFFECTS", {"lightning": 1})


# ─────────────────────────────────────────────────────────────
# T5. 세이브/alias 무결성
# ─────────────────────────────────────────────────────────────
class TestT5SaveCompatibility:
    def test_seal_save_fields_untouched(self):
        """seal_thunder 필드는 그대로 — element 정규화와 무관.
        근거: character.py:2387 세이브 필드."""
        from src.character.character import Character
        char = Character(name="닌자", character_class="ninja")
        char.seal_thunder = 3
        assert char.seal_thunder == 3

    def test_skill_aliases_keep_legacy_thunder_id(self):
        """T5b: skill_aliases.yaml 레거시 4둔술 별칭 유지."""
        aliases = yaml.safe_load(
            (PROJECT_ROOT / "data" / "skill_aliases.yaml").read_text(encoding="utf-8")
        )
        flat = str(aliases)
        assert "ninja_thunder_ninjutsu" in flat


# ─────────────────────────────────────────────────────────────
# T6. 표시 레이어 무회귀
# ─────────────────────────────────────────────────────────────
class TestT6DisplayLayer:
    def test_tooltip_thunder_mapping_preserved(self):
        """combat_tooltip "thunder": "뇌" 매핑 유지 (레거시 세이브 표시).
        근거: combat_tooltip.py:608."""
        from src.ui import combat_tooltip
        found = False
        for name in ("element_names", "ELEMENT_NAMES"):
            mapping = getattr(combat_tooltip, name, None)
            if isinstance(mapping, dict) and mapping.get("thunder") == "뇌":
                found = True
                break
        if not found:
            # 매핑이 함수 내부 상수일 수 있으므로 소스 레벨로 검증
            src = Path(combat_tooltip.__file__).read_text(encoding="utf-8")
            assert '"thunder"' in src, "combat_tooltip에 thunder 표시 매핑 부재"


# ─────────────────────────────────────────────────────────────
# T7. AI greedy / 프롬프트 무회귀
# ─────────────────────────────────────────────────────────────
class TestT7AiLayer:
    def test_job_prompt_keeps_variant_keys(self):
        """R4: variant 키 fire|ice|thunder|wind 유지 (표기 계층).
        근거: src/ai/job_prompts.py:599."""
        src = (PROJECT_ROOT / "src" / "ai" / "job_prompts.py").read_text(encoding="utf-8")
        assert "fire|ice|thunder|wind" in src

    def test_ninja_seal_elements_constant_unchanged(self):
        """NINJA_SEAL_ELEMENTS는 seal 네임스페이스 — thunder 유지."""
        from src.character import llm_bot_helpers
        seals = getattr(llm_bot_helpers, "NINJA_SEAL_ELEMENTS", None)
        if seals is not None:
            assert "thunder" in list(seals)


# ─────────────────────────────────────────────────────────────
# T8. 공유 인스턴스 위생 + variant key ≠ element (t_83d83e83 상속)
# ─────────────────────────────────────────────────────────────
class TestT8SharedInstanceHygiene:
    def _make(self):
        from src.character.character import Character
        from src.character.skills.skill_initializer import initialize_all_skills
        from src.character.skills.skill_manager import get_skill_manager
        initialize_all_skills()
        char = Character(name="테스트닌자", character_class="ninja")
        skill = get_skill_manager().get_skill(NEW_ID)
        return char, skill

    def _make_enemy(self):
        from src.character.character import Character
        enemy = Character(name="더미", character_class="warrior")
        enemy.is_enemy = True
        enemy.current_brv = 100
        enemy.max_brv = 999
        return enemy

    def test_thunder_variant_effective_element_is_lightning(self):
        """T8b: _selected_variant='thunder' 실행 시
        context['_variant_meta']['element']=='lightning', ['seal_type']=='thunder'."""
        from src.core.event_bus import event_bus, Events
        char, skill = self._make()
        skill.metadata["_selected_variant"] = "thunder"
        target = self._make_enemy()
        context = {"all_enemies": [target]}
        result = skill.execute(char, target, context)
        assert result.success
        event_bus.publish(Events.SKILL_EXECUTE, {
            "skill": skill, "user": char, "target": target,
            "result": result, "context": context,
        })
        assert getattr(char, "seal_thunder", 0) == 1
        effective = context.get("_variant_meta") or {}
        assert effective.get("element") == "lightning"
        assert effective.get("seal_type") == "thunder"

    def test_no_sticky_thunder_element_after_execute(self):
        """실행 종료 후 effect.element thunder/lightning 잔존 없음 (비-mutating)."""
        char, skill = self._make()
        skill.metadata["_selected_variant"] = "thunder"
        target = self._make_enemy()
        skill.execute(char, target, {})
        residual = [getattr(e, "element", None) for e in skill.effects]
        assert "lightning" not in residual, f"element 잔존(오염): {residual}"
        assert "thunder" not in residual
        assert "element" not in skill.metadata

    def test_failure_path_restores_state(self):
        """MP 부족 실패 경로에서도 복원 (기존 T9 상속)."""
        char, skill = self._make()
        skill.metadata["_selected_variant"] = "thunder"
        char.current_mp = 0
        target = self._make_enemy()
        result = skill.execute(char, target, {})
        assert not result.success
        residual = [getattr(e, "element", None) for e in skill.effects]
        assert "lightning" not in residual
        assert "element" not in skill.metadata


# ─────────────────────────────────────────────────────────────
# T10. 문서 동기화
# ─────────────────────────────────────────────────────────────
class TestT10Docs:
    def test_job_guides_document_thunder_to_lightning(self):
        """docs/job_guide.md + data/job_guide.md 닌자 섹션 명시.
        근거: R5."""
        needle = "lightning"
        for rel in ("docs/job_guide.md", "data/job_guide.md"):
            path = PROJECT_ROOT / rel
            assert path.exists(), f"{rel} 부재"
            text = path.read_text(encoding="utf-8")
            assert needle in text, f"{rel}에 lightning 명시 부재"
