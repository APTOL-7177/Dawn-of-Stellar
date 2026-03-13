"""
skill_effects.py - 스킬별 유니크 이펙트 매핑 + 트리거 엔진

스킬의 원소/타입/직업에 따라 고유 파티클 + 화면 셰이크 + 플래시를 트리거합니다.
다단히트 에스컬레이션, 궁극기 강화, 직업별 바리에이션을 지원합니다.

사용:
    from src.ui.pygame_backend.effects.skill_effects import trigger_skill_effect
    trigger_skill_effect(hit_info, effect_manager)
"""

import random
from typing import Any, Dict, List, Optional, Tuple

from src.core.logger import get_logger

logger = get_logger("effects.skill")


# ── 원소별 이펙트 정의 (기본) ─────────────────────────────────
# 각 원소에 여러 바리에이션을 두어 랜덤 선택
_ELEMENT_EFFECTS: Dict[str, List[Dict[str, Any]]] = {
    "fire": [
        {"particle": "fire", "shake": (6.0, 0.3), "flash": ((255, 80, 30), 0.2)},
        {"particle": "flame_pillar", "shake": (7.0, 0.35), "flash": ((255, 100, 20), 0.2)},
        {"particle": "fire_explosion", "shake": (8.0, 0.3), "flash": ((255, 60, 10), 0.18)},
    ],
    "ice": [
        {"particle": "ice", "shake": (3.0, 0.25), "flash": ((100, 200, 255), 0.2)},
        {"particle": "ice_shatter", "shake": (5.0, 0.3), "flash": ((140, 220, 255), 0.2)},
        {"particle": "frost_ring", "shake": (2.0, 0.2), "flash": ((160, 230, 255), 0.25)},
    ],
    "lightning": [
        {"particle": "lightning", "shake": (10.0, 0.35), "flash": ((255, 255, 100), 0.15)},
        {"particle": "thunder_bolt", "shake": (12.0, 0.3), "flash": ((255, 255, 150), 0.12)},
        {"particle": "chain_lightning", "shake": (8.0, 0.25), "flash": ((200, 200, 255), 0.15)},
    ],
    "water": [
        {"particle": "water", "shake": (3.0, 0.25), "flash": ((50, 100, 255), 0.2)},
        {"particle": "water_torrent", "shake": (4.0, 0.3), "flash": ((30, 80, 255), 0.2)},
        {"particle": "tidal_wave", "shake": (5.0, 0.35), "flash": ((60, 140, 220), 0.25)},
    ],
    "earth": [
        {"particle": "earth", "shake": (6.0, 0.3), "flash": ((150, 100, 50), 0.2)},
        {"particle": "earth_shatter", "shake": (8.0, 0.35), "flash": ((180, 130, 60), 0.2)},
        {"particle": "quake_wave", "shake": (10.0, 0.3), "flash": ((140, 100, 40), 0.18)},
    ],
    "wind": [
        {"particle": "wind", "shake": None, "flash": ((200, 255, 200), 0.15)},
        {"particle": "wind_blade", "shake": (3.0, 0.2), "flash": ((200, 255, 220), 0.12)},
        {"particle": "gale_spiral", "shake": None, "flash": ((220, 255, 240), 0.2)},
    ],
    "holy": [
        {"particle": "holy", "shake": (3.0, 0.2), "flash": ((255, 255, 200), 0.25)},
        {"particle": "holy_pillar", "shake": (4.0, 0.25), "flash": ((255, 240, 150), 0.3)},
        {"particle": "divine_radiance", "shake": (2.0, 0.2), "flash": ((255, 255, 180), 0.3)},
    ],
    "dark": [
        {"particle": "dark", "shake": (6.0, 0.3), "flash": ((80, 0, 120), 0.25)},
        {"particle": "dark_vortex", "shake": (5.0, 0.35), "flash": ((60, 0, 100), 0.3)},
        {"particle": "shadow_claw", "shake": (7.0, 0.25), "flash": ((80, 0, 80), 0.2)},
    ],
    "poison": [
        {"particle": "poison", "shake": None, "flash": ((100, 200, 0), 0.2)},
    ],
}

# ── 직업(기믹) 기본 이펙트 ─────────────────────────────────
# 원소가 없는 물리/마법 공격 시 직업에 따라 선택
_GIMMICK_EFFECTS: Dict[str, Dict[str, Any]] = {
    "sword_aura": {"particle": "sword_aura_slash", "shake": (4.0, 0.2), "flash": ((200, 180, 255), 0.12)},
    "madness_threshold": {"particle": "berserker_frenzy", "shake": (6.0, 0.25), "flash": ((255, 30, 30), 0.15)},
    "stealth_exposure": {"particle": "stealth_strike", "shake": (5.0, 0.2), "flash": ((100, 0, 150), 0.1)},
    "dragon_marks": {"particle": "dragon_breath", "shake": (6.0, 0.3), "flash": ((255, 100, 0), 0.2)},
    "intrusion_system": {"particle": "hack_glitch", "shake": (3.0, 0.2), "flash": ((0, 255, 0), 0.15)},
    "score_composition": {"particle": "music_notes", "shake": None, "flash": ((255, 200, 100), 0.2)},
    "yin_yang_flow": {"particle": "monk_ki_burst", "shake": (4.0, 0.2), "flash": ((255, 220, 100), 0.15)},
    "alchemy_system": {"particle": "alchemy_burst", "shake": (4.0, 0.25), "flash": ((255, 100, 200), 0.2)},
    "rune_resonance": {"particle": "rune_activation", "shake": (3.0, 0.2), "flash": ((150, 100, 255), 0.2)},
    "possibility_slots": {"particle": "time_distortion", "shake": (2.0, 0.3), "flash": ((180, 255, 255), 0.25)},
    "magazine_system": {"particle": "sniper_shot", "shake": (5.0, 0.15), "flash": ((255, 255, 200), 0.1)},
    "phantom_legion": {"particle": "phantom_slash", "shake": (4.0, 0.2), "flash": ((160, 100, 255), 0.15)},
    "dimension_refraction": {"particle": "dimension_rift", "shake": (4.0, 0.25), "flash": ((80, 0, 200), 0.2)},
    "rum_treasure_system": {"particle": "cannon_blast", "shake": (6.0, 0.25), "flash": ((200, 200, 200), 0.15)},
    "charge_system": {"particle": "charge_release", "shake": (5.0, 0.25), "flash": ((200, 50, 50), 0.15)},
    "stance_system": {"particle": "stance_shift", "shake": (3.0, 0.2), "flash": ((100, 200, 255), 0.12)},
    "duty_system": {"particle": "duty_shield", "shake": (3.0, 0.2), "flash": ((220, 200, 255), 0.15)},
    "crowd_cheer": {"particle": "crowd_roar", "shake": (4.0, 0.2), "flash": ((255, 220, 80), 0.15)},
    "shapeshifting_system": {"particle": "druid_nature", "shake": (3.0, 0.2), "flash": ((50, 200, 50), 0.2)},
    "thirst_gauge": {"particle": "vampire_bite", "shake": (4.0, 0.2), "flash": ((180, 0, 0), 0.15)},
    "elemental_spirits": {"particle": "spirit_summon", "shake": (3.0, 0.2), "flash": ((100, 200, 255), 0.2)},
    "undead_legion": {"particle": "necro_drain", "shake": (4.0, 0.25), "flash": ((60, 0, 40), 0.25)},
    "mp_overload_system": {"particle": "magic_burst", "shake": (5.0, 0.25), "flash": ((180, 100, 255), 0.2)},
    "oath_system": {"particle": "holy_pillar", "shake": (3.0, 0.2), "flash": ((255, 240, 150), 0.2)},
    "divinity_system": {"particle": "divine_radiance", "shake": (2.0, 0.2), "flash": ((255, 255, 180), 0.25)},
    "oracle_system": {"particle": "divine_radiance", "shake": (2.0, 0.2), "flash": ((255, 255, 200), 0.25)},
    "dilemma_choice": {"particle": "dilemma_resolve", "shake": (3.0, 0.2), "flash": ((200, 200, 255), 0.2)},
    "venom_system": {"particle": "poison_burst", "shake": (3.0, 0.15), "flash": ((100, 220, 60), 0.12)},
    "break_system": {"particle": "smash_ground", "shake": (6.0, 0.25), "flash": ((200, 180, 150), 0.15)},
    "support_fire": {"particle": "sniper_shot", "shake": (3.0, 0.15), "flash": ((255, 255, 200), 0.1)},
    "trick_deck": {"particle": "magic_burst", "shake": (3.0, 0.2), "flash": ((180, 100, 255), 0.15)},
    "elemental_counter": {"particle": "arcane_pulse", "shake": (4.0, 0.25), "flash": ((120, 80, 255), 0.2)},
    "blade_circuit": {"particle": "slash_wide", "shake": (4.0, 0.2), "flash": ((150, 200, 255), 0.15)},
    "kenshin_system": {"particle": "slash_precise", "shake": (5.0, 0.2), "flash": ((255, 255, 255), 0.1)},
    "heat_management": {"particle": "fire_explosion", "shake": (5.0, 0.25), "flash": ((255, 160, 40), 0.15)},
}

# ── 스킬 special 태그 이펙트 (최고 우선순위) ──────────────
_SPECIAL_SKILL_EFFECTS: Dict[str, Dict[str, Any]] = {
    "chain_explosion": {"particle": "fire_explosion", "shake": (10.0, 0.4), "flash": ((255, 100, 20), 0.2, 200)},
    "electrocution": {"particle": "chain_lightning", "shake": (12.0, 0.35), "flash": ((255, 255, 100), 0.15, 180)},
    "thermal_shock": {"particle": "ice_shatter", "shake": (8.0, 0.3), "flash": ((200, 240, 255), 0.2, 180)},
    "brv_break_focused": {"particle": "smash_ground", "shake": (8.0, 0.3), "flash": ((255, 150, 50), 0.2)},
    "parry_ultimate": {"particle": "slash_precise", "shake": (14.0, 0.4), "flash": ((255, 255, 255), 0.15, 220)},
    "rampage": {"particle": "berserker_frenzy", "shake": (12.0, 0.45), "flash": ((255, 0, 0), 0.2, 200)},
    "dragon_transform": {"particle": "dragon_mark_burst", "shake": (12.0, 0.4), "flash": ((255, 150, 0), 0.25, 200)},
    "multithread_rampage": {"particle": "hack_glitch", "shake": (10.0, 0.35), "flash": ((0, 255, 0), 0.15, 180)},
}

# ── 힐 서브타입 이펙트 ──────────────────────────────────────
_HEAL_EFFECTS: Dict[str, Dict[str, Any]] = {
    "default": {"particle": "heal_skill", "shake": None, "flash": ((100, 255, 150), 0.2)},
    "group": {"particle": "heal_group", "shake": None, "flash": ((100, 255, 180), 0.25)},
    "resurrection": {"particle": "heal_resurrection", "shake": (3.0, 0.2), "flash": ((255, 255, 200), 0.3)},
    "cleanse": {"particle": "heal_cleanse", "shake": None, "flash": ((200, 255, 255), 0.2)},
    "mp_restore": {"particle": "heal_mp_restore", "shake": None, "flash": ((100, 150, 255), 0.2)},
}

# ── 버프 서브타입 이펙트 ──────────────────────────────────────
_BUFF_EFFECTS: Dict[str, Dict[str, Any]] = {
    "default": {"particle": "buff", "shake": None, "flash": ((255, 220, 80), 0.15)},
    "attack": {"particle": "buff_attack", "shake": None, "flash": ((255, 100, 80), 0.15)},
    "defense": {"particle": "buff_defense", "shake": None, "flash": ((100, 200, 255), 0.15)},
    "speed": {"particle": "buff_speed", "shake": None, "flash": ((255, 255, 100), 0.15)},
    "barrier": {"particle": "buff_barrier", "shake": None, "flash": ((200, 220, 255), 0.2)},
    "regen": {"particle": "buff_regen", "shake": None, "flash": ((100, 255, 150), 0.15)},
    "critical": {"particle": "buff_critical", "shake": None, "flash": ((255, 200, 50), 0.15)},
    "haste": {"particle": "buff_haste", "shake": None, "flash": ((255, 255, 150), 0.12)},
    "invincible": {"particle": "buff_invincible", "shake": (2.0, 0.15), "flash": ((255, 255, 255), 0.2, 180)},
}

# ── 디버프 적용 이펙트 (STATUS_APPLIED 이벤트용) ─────────────
_DEBUFF_EFFECTS: Dict[str, Dict[str, Any]] = {
    "poison": {"particle": "debuff_poison", "shake": None, "flash": ((100, 200, 0), 0.15)},
    "burn": {"particle": "debuff_burn", "shake": (2.0, 0.15), "flash": ((255, 80, 0), 0.15)},
    "freeze": {"particle": "debuff_freeze", "shake": (2.0, 0.15), "flash": ((100, 200, 255), 0.2)},
    "stun": {"particle": "debuff_stun", "shake": (3.0, 0.15), "flash": ((255, 255, 100), 0.12)},
    "sleep": {"particle": "debuff_stun", "shake": None, "flash": ((150, 150, 200), 0.2)},
    "silence": {"particle": "debuff_silence", "shake": None, "flash": ((180, 100, 200), 0.15)},
    "blind": {"particle": "debuff_blind", "shake": None, "flash": ((80, 80, 80), 0.2)},
    "slow": {"particle": "debuff_slow", "shake": None, "flash": ((150, 150, 200), 0.15)},
    "shock": {"particle": "debuff_paralyze", "shake": (2.0, 0.12), "flash": ((255, 255, 0), 0.12)},
    "curse": {"particle": "debuff_curse", "shake": None, "flash": ((100, 0, 150), 0.2)},
    "doom": {"particle": "debuff_doom", "shake": (3.0, 0.2), "flash": ((80, 0, 80), 0.25)},
    "weaken": {"particle": "debuff_curse", "shake": None, "flash": ((150, 100, 50), 0.15)},
    "weakness": {"particle": "debuff_curse", "shake": None, "flash": ((150, 100, 50), 0.15)},
    "defense_down": {"particle": "debuff_scatter", "shake": None, "flash": ((200, 150, 50), 0.15)},
    "attack_down": {"particle": "debuff_slow", "shake": None, "flash": ((200, 100, 100), 0.15)},
    "scatter": {"particle": "debuff_scatter", "shake": (2.0, 0.15), "flash": ((200, 200, 100), 0.15)},
    "paralyze": {"particle": "debuff_paralyze", "shake": (2.0, 0.15), "flash": ((255, 255, 0), 0.12)},
    "bleed": {"particle": "debuff_bleed", "shake": (2.0, 0.15), "flash": ((200, 0, 0), 0.15)},
    "confuse": {"particle": "debuff_confuse", "shake": (2.0, 0.15), "flash": ((255, 100, 255), 0.15)},
}

# ── 버프 상태 적용 이펙트 (STATUS_APPLIED 이벤트용) ──────────
_BUFF_STATUS_EFFECTS: Dict[str, Dict[str, Any]] = {
    "haste": {"particle": "buff_haste", "shake": None, "flash": ((255, 255, 150), 0.12)},
    "regen": {"particle": "buff_regen", "shake": None, "flash": ((100, 255, 150), 0.15)},
    "barrier": {"particle": "buff_barrier", "shake": None, "flash": ((200, 220, 255), 0.2)},
    "blessing": {"particle": "buff_invincible", "shake": None, "flash": ((255, 255, 200), 0.2)},
    "strengthen": {"particle": "buff_attack", "shake": None, "flash": ((255, 150, 80), 0.15)},
    "defense_up": {"particle": "buff_defense", "shake": None, "flash": ((100, 200, 255), 0.15)},
    "attack_up": {"particle": "buff_attack", "shake": None, "flash": ((255, 100, 80), 0.15)},
}

# ── 아이템 사용 이펙트 ──────────────────────────────────────
_ITEM_EFFECTS: Dict[str, Dict[str, Any]] = {
    "potion": {"particle": "item_potion", "shake": None, "flash": ((100, 255, 100), 0.15)},
    "hi_potion": {"particle": "item_potion", "shake": None, "flash": ((100, 255, 150), 0.18)},
    "ether": {"particle": "item_ether", "shake": None, "flash": ((100, 150, 255), 0.15)},
    "elixir": {"particle": "item_elixir", "shake": None, "flash": ((255, 255, 200), 0.2)},
    "antidote": {"particle": "item_antidote", "shake": None, "flash": ((200, 255, 200), 0.15)},
    "bomb": {"particle": "item_bomb", "shake": (6.0, 0.3), "flash": ((255, 100, 0), 0.2)},
    "grenade": {"particle": "item_bomb", "shake": (7.0, 0.3), "flash": ((255, 120, 20), 0.2)},
}

# ── 방어/특수 행동 이펙트 ────────────────────────────────────
_DEFEND_EFFECT: Dict[str, Any] = {"particle": "defend_guard", "shake": None, "flash": ((200, 220, 255), 0.15)}
_COUNTER_EFFECT: Dict[str, Any] = {"particle": "counter_attack", "shake": (4.0, 0.2), "flash": ((255, 200, 50), 0.15)}
_DODGE_EFFECT: Dict[str, Any] = {"particle": "dodge_evade", "shake": None, "flash": None}
_ABSORB_EFFECT: Dict[str, Any] = {"particle": "absorb_drain", "shake": None, "flash": ((150, 0, 200), 0.15)}
_REFLECT_EFFECT: Dict[str, Any] = {"particle": "reflect_barrier", "shake": (3.0, 0.15), "flash": ((200, 220, 255), 0.15)}
_PROVOKE_EFFECT: Dict[str, Any] = {"particle": "provoke_taunt", "shake": (3.0, 0.15), "flash": ((255, 50, 50), 0.15)}

# ── 물리/마법 기본 이펙트 (바리에이션) ────────────────────────
_PHYSICAL_EFFECTS: List[Dict[str, Any]] = [
    {"particle": "physical", "shake": (4.0, 0.2), "flash": None},
    {"particle": "slash_wide", "shake": (4.0, 0.2), "flash": None},
    {"particle": "thrust_impact", "shake": (5.0, 0.2), "flash": None},
    {"particle": "slash_precise", "shake": (3.0, 0.15), "flash": None},
]
_MAGICAL_EFFECTS: List[Dict[str, Any]] = [
    {"particle": "magic_burst", "shake": (3.0, 0.2), "flash": ((180, 100, 255), 0.15)},
    {"particle": "magic_beam", "shake": (4.0, 0.2), "flash": ((200, 150, 255), 0.12)},
    {"particle": "arcane_pulse", "shake": (2.0, 0.2), "flash": ((120, 80, 255), 0.15)},
]

# ── 크리티컬/BREAK 강화 ──────────────────────────────────────
_CRITICAL_ENHANCE: Dict[str, Any] = {
    "particle": "critical_burst", "shake": (12.0, 0.4),
    "flash": ((255, 255, 255), 0.15, 200),
}
_BREAK_ENHANCE: Dict[str, Any] = {
    "particle": "break_burst", "shake": (15.0, 0.45),
    "flash": ((255, 50, 50), 0.25, 220),
}

# 검기 추가타 전용
_SWORD_AURA_EFFECT: Dict[str, Any] = {
    "particle": "sword_aura_slash", "shake": (3.0, 0.15),
    "flash": ((200, 180, 255), 0.1),
}

# ── 음/양 기운 매핑 ──────────────────────────────────────────
def _get_monk_effect(hit_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """몽크: 기 게이지 상태에 따라 음/양 이펙트 선택"""
    attacker = hit_info.get('attacker')
    ki = getattr(attacker, 'ki_gauge', 50)
    if ki <= 30:
        return {"particle": "yin_strike", "shake": (3.0, 0.2), "flash": ((60, 60, 200), 0.15)}
    elif ki >= 70:
        return {"particle": "yang_strike", "shake": (5.0, 0.2), "flash": ((255, 200, 50), 0.15)}
    return None  # 중간 상태는 기본 이펙트


def _resolve_heal_subtype(hit_info: Dict[str, Any]) -> Dict[str, Any]:
    """힐 스킬의 서브타입을 판별하여 적절한 이펙트를 반환합니다."""
    skill_id = (hit_info.get("skill_id") or "").lower()

    # 부활
    if any(kw in skill_id for kw in ("resurrect", "revive", "raise", "부활")):
        return _HEAL_EFFECTS["resurrection"]
    # 정화/해제
    if any(kw in skill_id for kw in ("cleanse", "purify", "esuna", "정화", "해제", "cure_status")):
        return _HEAL_EFFECTS["cleanse"]
    # MP 회복
    if any(kw in skill_id for kw in ("mp_", "mana_", "ether", "마나", "mp_restore")):
        return _HEAL_EFFECTS["mp_restore"]
    # 그룹 힐 (키워드 또는 다수 타겟)
    if any(kw in skill_id for kw in ("group", "party", "mass", "all", "area", "전체", "광역")):
        return _HEAL_EFFECTS["group"]
    if hit_info.get("targets_hit", 1) > 1:
        return _HEAL_EFFECTS["group"]

    return _HEAL_EFFECTS["default"]


def _resolve_buff_subtype(hit_info: Dict[str, Any]) -> Dict[str, Any]:
    """버프 스킬의 서브타입을 판별하여 적절한 이펙트를 반환합니다."""
    skill_id = (hit_info.get("skill_id") or "").lower()

    # 무적
    if any(kw in skill_id for kw in ("invincib", "무적", "immortal", "divine_shield")):
        return _BUFF_EFFECTS["invincible"]
    # 배리어/보호막
    if any(kw in skill_id for kw in ("barrier", "shield", "protect", "배리어", "보호", "aegis")):
        return _BUFF_EFFECTS["barrier"]
    # 공격력
    if any(kw in skill_id for kw in ("attack_up", "power_up", "strength", "공격", "empower", "enchant", "sharpen")):
        return _BUFF_EFFECTS["attack"]
    # 방어력
    if any(kw in skill_id for kw in ("defense_up", "iron_", "fortif", "방어력", "harden")):
        return _BUFF_EFFECTS["defense"]
    # 헤이스트/속도
    if any(kw in skill_id for kw in ("haste", "speed", "quick", "가속", "속도", "accel")):
        return _BUFF_EFFECTS["haste"]
    # 리젠
    if any(kw in skill_id for kw in ("regen", "heal_over", "재생", "recovery")):
        return _BUFF_EFFECTS["regen"]
    # 크리티컬/집중
    if any(kw in skill_id for kw in ("critical", "focus", "집중", "크리", "precision")):
        return _BUFF_EFFECTS["critical"]
    # 속도(버프)
    if any(kw in skill_id for kw in ("speed_up", "swift")):
        return _BUFF_EFFECTS["speed"]

    return _BUFF_EFFECTS["default"]


def _resolve_effect(hit_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """hit_info에서 가장 적절한 이펙트 설정을 다층 우선순위로 결정합니다.

    우선순위:
      1. 검기 추가타 (sword_aura_hit)
      2. damage_type == heal → 서브타입 분기
      3. damage_type == buff → 서브타입 분기
      4. skill_special 태그 (최고 특수성)
      5. element (원소 바리에이션 랜덤 선택)
      6. gimmick_type (직업별 기본 이펙트)
      7. stat_type (물리/마법 바리에이션 랜덤 선택)
    """
    damage_type = hit_info.get("damage_type", "brv")
    element = hit_info.get("element")
    stat_type = hit_info.get("stat_type", "physical")
    gimmick_type = hit_info.get("gimmick_type")
    skill_special = hit_info.get("skill_special")
    sword_aura_hit = hit_info.get("sword_aura_hit")
    brv_damage = hit_info.get("brv_damage", 0)
    hp_damage = hit_info.get("hp_damage", 0)

    # 1) 검기 추가타: 전용 이펙트
    if sword_aura_hit:
        return _SWORD_AURA_EFFECT

    # 2) 힐 → 서브타입 분기 (부활/정화/MP회복/그룹힐/기본)
    if damage_type == "heal":
        return _resolve_heal_subtype(hit_info)

    # 3) 버프 → 서브타입 분기 (무적/배리어/공격/방어/속도/리젠/크리/기본)
    if damage_type == "buff":
        return _resolve_buff_subtype(hit_info)

    # 4) 스킬 special 태그 (chain_explosion, rampage 등)
    if skill_special and skill_special in _SPECIAL_SKILL_EFFECTS:
        return _SPECIAL_SKILL_EFFECTS[skill_special]

    # 5) 원소 이펙트 (바리에이션 랜덤 선택)
    if element and element in _ELEMENT_EFFECTS:
        variations = _ELEMENT_EFFECTS[element]
        return random.choice(variations)

    # 6) 몽크 음양 특수 처리
    if gimmick_type == "yin_yang_flow":
        monk_eff = _get_monk_effect(hit_info)
        if monk_eff:
            return monk_eff

    # 7) 직업별 기본 이펙트
    if gimmick_type and gimmick_type in _GIMMICK_EFFECTS:
        return _GIMMICK_EFFECTS[gimmick_type]

    # 8) 데미지가 있으면 물리/마법 바리에이션
    if brv_damage > 0 or hp_damage > 0:
        if stat_type == "magical":
            return random.choice(_MAGICAL_EFFECTS)
        return random.choice(_PHYSICAL_EFFECTS)

    return None


def _scale_effect(
    base: Dict[str, Any],
    hit_info: Dict[str, Any],
) -> Dict[str, Any]:
    """히트 상황에 따라 기본 이펙트를 스케일링합니다.

    - 다단히트: 히트 번호가 올라갈수록 파티클 수 증가, 셰이크 강화
    - HP 공격: BRV 대비 추가 셰이크
    - 높은 피해: 파티클 수 보너스
    - 궁극기: 전반적 강화
    """
    result = dict(base)  # 원본 변경 방지

    # ── 다단히트 에스컬레이션 ──────────────────────────────────
    multi_current = hit_info.get("multi_hit_current")
    multi_total = hit_info.get("multi_hit_total")
    if multi_current and multi_total and multi_total > 1:
        # 히트 번호에 따라 1.0 → 1.5배 스케일링
        hit_ratio = multi_current / multi_total
        escalation = 1.0 + hit_ratio * 0.5
        result["_particle_scale"] = escalation
        # 후반 히트일수록 셰이크 증가
        if result.get("shake"):
            si, sd = result["shake"]
            result["shake"] = (si * (1.0 + hit_ratio * 0.3), sd)

    # ── HP 공격 강화 ──────────────────────────────────────────
    damage_type = hit_info.get("damage_type", "brv")
    if damage_type in ("hp", "brv_hp"):
        # HP 공격은 추가 셰이크
        if result.get("shake"):
            si, sd = result["shake"]
            result["shake"] = (si * 1.3, sd * 1.1)
        elif damage_type == "hp":
            result["shake"] = (5.0, 0.2)

    # ── 높은 피해 보너스 ──────────────────────────────────────
    hp_pct = hit_info.get("hp_percent_of_target", 0)
    if hp_pct > 20:
        # 20% 이상의 HP 피해: 파티클 보너스
        bonus = min(2.0, 1.0 + (hp_pct - 20) / 40)
        prev_scale = result.get("_particle_scale", 1.0)
        result["_particle_scale"] = prev_scale * bonus

    # ── 궁극기 강화 ───────────────────────────────────────────
    if hit_info.get("is_ultimate"):
        prev_scale = result.get("_particle_scale", 1.0)
        result["_particle_scale"] = prev_scale * 1.5
        if result.get("shake"):
            si, sd = result["shake"]
            result["shake"] = (si * 1.4, sd * 1.2)
        if result.get("flash"):
            # 플래시 알파 증가
            flash = result["flash"]
            if len(flash) == 2:
                result["flash"] = (flash[0], flash[1], 200)
            elif len(flash) == 3:
                result["flash"] = (flash[0], flash[1], min(255, int(flash[2] * 1.3)))

    return result


def trigger_skill_effect(
    hit_info: Dict[str, Any],
    effect_manager: Any,
    target_x: float = 0.0,
    target_y: float = 0.0,
) -> None:
    """
    히트 이벤트에 대응하는 스킬 이펙트를 트리거합니다.

    Args:
        hit_info: COMBAT_HIT 이벤트 데이터
        effect_manager: EffectManager 인스턴스
        target_x: 타격 위치 X (픽셀)
        target_y: 타격 위치 Y (픽셀)
    """
    if effect_manager is None:
        return

    base_effect = _resolve_effect(hit_info)
    if base_effect is None:
        return

    # 상황별 스케일링
    effect = _scale_effect(base_effect, hit_info)

    is_critical = hit_info.get("is_critical", False)
    is_break = hit_info.get("is_break", False)
    particle_scale = effect.get("_particle_scale", 1.0)

    # AoE 다단히트: 셰이크/플래시 강도 감소 (과도한 화면 떨림 방지)
    targets_hit = hit_info.get("targets_hit", 1)
    aoe_dampen = 0.4 if targets_hit > 1 else 1.0

    # 1) 파티클 방출
    particle_type = effect.get("particle")
    if particle_type:
        count = None
        if particle_scale != 1.0:
            # 기본 count에 스케일 적용
            from src.ui.pygame_backend.effects.particles import _PRESETS
            preset = _PRESETS.get(particle_type, {})
            base_count = preset.get("count", 12)
            count = max(3, int(base_count * particle_scale))
        try:
            effect_manager.emit_particles(target_x, target_y, particle_type, count)
        except Exception:
            effect_manager.emit_particles(target_x, target_y, "spark")

    # 2) 화면 셰이크
    shake = effect.get("shake")
    if shake:
        intensity, duration = shake
        effect_manager.trigger_shake(intensity * aoe_dampen, duration * aoe_dampen)

    # 3) 화면 플래시
    flash = effect.get("flash")
    if flash:
        if len(flash) == 3:
            color, duration, max_alpha = flash
            effect_manager.trigger_flash(color, duration * aoe_dampen, int(max_alpha * aoe_dampen))
        else:
            color, duration = flash
            effect_manager.trigger_flash(color, duration * aoe_dampen)

    # 4) 크리티컬 강화 (기본 이펙트 위에 추가)
    if is_critical:
        try:
            effect_manager.emit_particles(target_x, target_y, "critical_burst", count=8)
        except Exception:
            pass
        c_shake = _CRITICAL_ENHANCE["shake"]
        effect_manager.trigger_shake(c_shake[0], c_shake[1])
        c_flash = _CRITICAL_ENHANCE["flash"]
        effect_manager.trigger_flash(c_flash[0], c_flash[1], c_flash[2])

    # 5) BREAK 강화
    if is_break:
        try:
            effect_manager.emit_particles(target_x, target_y, "break_burst", count=12)
        except Exception:
            pass
        b_shake = _BREAK_ENHANCE["shake"]
        effect_manager.trigger_shake(b_shake[0], b_shake[1])
        b_flash = _BREAK_ENHANCE["flash"]
        effect_manager.trigger_flash(b_flash[0], b_flash[1], b_flash[2])

    # 6) AOE 범위 링 이펙트 (광역 공격 시 추가)
    targets_hit = hit_info.get("targets_hit", 1)
    if targets_hit > 1:
        try:
            effect_manager.emit_particles(target_x, target_y, "aoe_ring", count=min(int(8 * targets_hit), 24))
        except Exception:
            pass

    logger.debug(
        f"스킬 이펙트: element={hit_info.get('element')}, "
        f"gimmick={hit_info.get('gimmick_type')}, "
        f"special={hit_info.get('skill_special')}, "
        f"critical={is_critical}, break={is_break}, "
        f"ultimate={hit_info.get('is_ultimate')}, "
        f"multi={hit_info.get('multi_hit_current')}/{hit_info.get('multi_hit_total')}, "
        f"preset={particle_type}, scale={particle_scale:.1f}"
    )


def trigger_status_effect(
    status_data: Dict[str, Any],
    effect_manager: Any,
    target_x: float = 0.0,
    target_y: float = 0.0,
) -> None:
    """STATUS_APPLIED 이벤트에 대응하는 상태이상 이펙트를 트리거합니다.

    Args:
        status_data: STATUS_APPLIED 이벤트 데이터 (owner, status, is_new)
        effect_manager: EffectManager 인스턴스
        target_x: 대상 위치 X (픽셀)
        target_y: 대상 위치 Y (픽셀)
    """
    if effect_manager is None:
        return

    status = status_data.get("status")
    if status is None:
        return

    # 갱신(is_new=False)일 때는 이펙트 생략
    if not status_data.get("is_new", True):
        return

    status_type = getattr(status, "status_type", None) or getattr(status, "name", "")

    # 디버프 이펙트
    if status_type in _DEBUFF_EFFECTS:
        effect = _DEBUFF_EFFECTS[status_type]
    # 버프 상태 이펙트
    elif status_type in _BUFF_STATUS_EFFECTS:
        effect = _BUFF_STATUS_EFFECTS[status_type]
    else:
        return  # 매핑되지 않은 상태는 무시

    # 파티클 방출
    particle_type = effect.get("particle")
    if particle_type:
        try:
            effect_manager.emit_particles(target_x, target_y, particle_type)
        except Exception:
            effect_manager.emit_particles(target_x, target_y, "spark")

    # 화면 셰이크
    shake = effect.get("shake")
    if shake:
        intensity, duration = shake
        effect_manager.trigger_shake(intensity, duration)

    # 화면 플래시
    flash = effect.get("flash")
    if flash:
        if len(flash) == 3:
            color, duration, max_alpha = flash
            effect_manager.trigger_flash(color, duration, max_alpha)
        else:
            color, duration = flash
            effect_manager.trigger_flash(color, duration)

    logger.debug(f"상태이상 이펙트: {status_type} → {particle_type}")


def trigger_item_effect(
    item_name: str,
    effect_manager: Any,
    target_x: float = 0.0,
    target_y: float = 0.0,
) -> None:
    """아이템 사용 시 이펙트를 트리거합니다.

    Args:
        item_name: 아이템 이름/ID
        effect_manager: EffectManager 인스턴스
        target_x: 대상 위치 X (픽셀)
        target_y: 대상 위치 Y (픽셀)
    """
    if effect_manager is None:
        return

    name_lower = item_name.lower()
    effect = None

    # 아이템 이름에서 키워드 매칭
    for key, eff in _ITEM_EFFECTS.items():
        if key in name_lower:
            effect = eff
            break

    # 한글 키워드 폴백
    if effect is None:
        if any(kw in name_lower for kw in ("포션", "회복약")):
            effect = _ITEM_EFFECTS["potion"]
        elif any(kw in name_lower for kw in ("에테르", "마나")):
            effect = _ITEM_EFFECTS["ether"]
        elif any(kw in name_lower for kw in ("엘릭서", "만능약")):
            effect = _ITEM_EFFECTS["elixir"]
        elif any(kw in name_lower for kw in ("해독", "독치료")):
            effect = _ITEM_EFFECTS["antidote"]
        elif any(kw in name_lower for kw in ("폭탄", "수류탄", "화염병")):
            effect = _ITEM_EFFECTS["bomb"]

    if effect is None:
        # 기본 아이템 이펙트 (포션 스타일)
        effect = _ITEM_EFFECTS["potion"]

    # 파티클 방출
    particle_type = effect.get("particle")
    if particle_type:
        try:
            effect_manager.emit_particles(target_x, target_y, particle_type)
        except Exception:
            effect_manager.emit_particles(target_x, target_y, "spark")

    # 화면 플래시
    flash = effect.get("flash")
    if flash:
        if len(flash) == 3:
            color, duration, max_alpha = flash
            effect_manager.trigger_flash(color, duration, max_alpha)
        else:
            color, duration = flash
            effect_manager.trigger_flash(color, duration)

    # 화면 셰이크 (폭탄류만)
    shake = effect.get("shake")
    if shake:
        intensity, duration = shake
        effect_manager.trigger_shake(intensity, duration)

    logger.debug(f"아이템 이펙트: {item_name} → {particle_type}")
