"""YAML Skill Loader

YAML 기반 스킬을 SkillManager에 등록한다.
아이콘/색/스크린 이펙트와 같은 UI 필드는 무시한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.core.logger import get_logger
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.status_effect import StatusEffect
from src.character.skills.effects.taunt_effect import TauntEffect
from src.character.skills.effects.protect_effect import ProtectEffect
from src.character.skills.effects.fixed_damage_effect import FixedDamageEffect
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.effects.atb_effect import (
    AtbBoostEffect, AtbChargeEffect, SelfAtbCostEffect, SelfAtbCostPercentEffect
)
from src.character.skills.effects.multi_hit_effect import MultiHitHpDamageEffect, RandomHpHitsEffect
from src.character.skills.effects.chain_effect import ChainCastEffect, ChainDamageEffect
from src.character.skills.effects.temporal_heal_effect import TemporalHealEffect
from src.character.skills.effects.damage_share_effect import DamageShareEffect
from src.character.skills.effects.phantom_effect import (
    SummonPhantomEffect, ConsumePhantomEffect, PhantomEchoDamageEffect,
    ConsumeAllPhantomsEffect, PhantomBonusDebuffEffect, PhantomConvergenceBonusEffect,
    PhantomDamageRedirectEffect, PhantomPriorityEffect, PhantomCounterEffect,
)
from src.character.skills.effects.possibility_effect import (
    GeneratePossibilityEffect, ReleaseAllPossibilitiesEffect,
    SummonPossibilityEffect, ConsumeOptionEffect,
)
from src.character.skills.effects.afterimage_effect import (
    ConsumeAfterimageEffect, AfterimageScalingEffect, ChargeAfterimageEffect,
)
from src.character.skills.effects.time_effect import (
    TimeFractureEffect, TimeCrossingEffect, TimeStormEffect,
)
from src.character.skills.effects.utility_effect import (
    ClearSlotsEffect, GainGimmickEffect, ConsumeGimmickEffect,
    ConvergenceBonusEffect, ShieldDamageEffect, AreaDamageEffect,
)
from src.character.skills.effects.trigger_effect import (
    OnEvadeTriggerEffect, ApplyTrapEffect, BrandEffect,
    ElectrocutionEffect, GlyphEffect,
)
from src.character.skills.effects.element_effect import (
    OverloadEffect, TransmutationEffect, ThermalShockEffect,
)
from src.character.skills.effects.fate_effect import (
    FateCopyEffect, OverwriteFateEffect,
)
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.hp_cost import HPCost
from src.character.skills.costs.stack_cost import StackCost
from src.character.skills.element_alias import normalize_element

logger = get_logger("yaml_skill_loader")
SKILLS_DIR = Path("data/skills")

# SE 파일명 → config 기반 SFX 튜플 매핑 ("se" 카테고리 변환용)
_SE_TO_CONFIG_SFX = {
    "Fire1": ("skill", "fire"), "Fire2": ("skill", "fire2"), "Fire3": ("skill", "fire3"),
    "Ice1": ("skill", "ice"), "Ice2": ("skill", "ice2"), "Ice3": ("skill", "ice3"),
    "Thunder1": ("skill", "bolt"), "Thunder2": ("skill", "lightning"), "Thunder3": ("skill", "bolt3"),
    "Magic1": ("skill", "magic_cast"), "Magic2": ("skill", "cast_complete"),
    "Damage1": ("combat", "damage_low"), "Damage3": ("combat", "attack_physical"),
    "Damage4": ("combat", "multi_hit"), "Damage5": ("combat", "critical"),
    "Slash1": ("skill", "slash"), "Slash2": ("skill", "slash2"),
    "Sword2": ("skill", "sword"), "Sword4": ("combat", "sword4"),
    "Explosion2": ("skill", "explosion"), "Explosion3": ("skill", "flare"),
    "Explosion4": ("skill", "ultima"),
    "Up1": ("character", "status_buff"), "Up2": ("skill", "haste"),
    "Down1": ("character", "status_debuff"), "Down2": ("skill", "slow"),
    "Recovery": ("character", "hp_heal"),
    "Heal1": ("skill", "cure"), "Heal3": ("item", "high_potion"),
    "Heal4": ("skill", "holy"), "Heal5": ("item", "elixir"),
    "Darkness3": ("skill", "dark"),
    "Barrier": ("skill", "barrier"), "Blind": ("skill", "confusion"),
    "Poison": ("skill", "poison"),
    "Water1": ("skill", "water"), "Wind1": ("skill", "wind"), "Earth1": ("skill", "earth"),
    "Blow10": ("skill", "roar"),
    "Gun1": ("skill", "gun_shot"), "Gun2": ("skill", "gun_reload"),
    "Summon": ("skill", "summon"), "Move2": ("skill", "teleport"),
    "Collapse1": ("character", "death"), "Raise1": ("character", "revive"),
    "Absorb1": ("skill", "dark"), "Absorb2": ("skill", "dark"),
    "Attack1": ("combat", "attack_physical"), "Attack2": ("combat", "attack_physical"),
    "Attack3": ("combat", "damage_high"),
    "Bell1": ("skill", "bell"), "Reflection": ("skill", "reflect"),
    "Parry": ("combat", "guard"), "Evasion1": ("combat", "dodge"),
    "Break": ("combat", "break"), "Breath": ("skill", "wind"),
    "Chain": ("combat", "multi_hit"), "Computer": ("skill", "computer"),
    "Laser1": ("skill", "laser"), "Load1": ("skill", "load"),
    "Machine": ("skill", "machine"), "Skill3": ("skill", "skill3"),
    "Sound1": ("skill", "sound1"), "Sound2": ("skill", "sound2"), "Sound3": ("skill", "sound3"),
    "Switch1": ("skill", "switch"), "Switch2": ("skill", "trap"),
    "Taunt": ("character", "taunt"), "Guard": ("combat", "guard"),
    "Dispel": ("skill", "reflect"), "Revive": ("character", "revive"),
    "Charge": ("skill", "load"),
    "Explosion1": ("item", "grenade"),
}


def _infer_sfx(data: dict) -> tuple:
    """스킬 속성 분석 → 적절한 SFX 자동 할당 (다양한 사운드 배분)"""
    skill_id = data.get("id", "")
    effects = data.get("effects", [])
    metadata = data.get("metadata", {})
    skill_type = data.get("type", "")
    target = data.get("target", "single_enemy")
    description = data.get("description", "")

    has_damage = False
    has_heal = False
    has_buff = False
    has_debuff = False
    is_magical = False
    element = None
    status_type = None

    for eff in effects:
        et = (eff.get("type") or "").lower()
        if et in ("damage", "hp_damage"):
            has_damage = True
            element = element or eff.get("element")
            if eff.get("stat_base") == "magic":
                is_magical = True
        elif et == "heal" or et == "mp_restore":
            has_heal = True
        elif et == "buff":
            has_buff = True
        elif et in ("debuff", "status", "status_effect"):
            has_debuff = True
            st = (eff.get("status") or eff.get("status_type") or "").lower()
            if "poison" in st:
                status_type = "poison"
            elif "blind" in st or "confus" in st:
                status_type = "confusion"
            elif "burn" in st or "fire" in st:
                element = element or "fire"
            elif "freeze" in st or "ice" in st:
                element = element or "ice"

    # 결정론적 해시 (같은 스킬은 항상 같은 SFX)
    h = sum(ord(c) for c in skill_id)

    # 원소 기반
    if element:
        el = element.lower()
        elem_map = {
            "fire": [("skill", "fire"), ("skill", "fire2"), ("skill", "fire3")],
            "ice": [("skill", "ice"), ("skill", "ice2"), ("skill", "ice3")],
            "lightning": [("skill", "bolt"), ("skill", "bolt2"), ("skill", "lightning")],
            "thunder": [("skill", "bolt"), ("skill", "bolt2"), ("skill", "bolt3")],
            "dark": [("skill", "dark")],
            "darkness": [("skill", "dark")],
            "holy": [("skill", "holy")],
            "light": [("skill", "holy")],
            "water": [("skill", "water"), ("skill", "rain")],
            "wind": [("skill", "wind")],
            "earth": [("skill", "earth")],
            "poison": [("skill", "poison")],
            "magical": [("skill", "cast_complete"), ("skill", "elemental"), ("skill", "magic_cast")],
        }
        opts = elem_map.get(el)
        if opts:
            return opts[h % len(opts)]

    # 상태이상 특화
    if status_type == "poison":
        return ("skill", "poison")
    if status_type == "confusion":
        return ("skill", "confusion")

    # 궁극기
    if skill_type == "ultimate" or metadata.get("ultimate"):
        return [("skill", "limit_break"), ("skill", "ultima"), ("skill", "flare")][h % 3]

    # 회복 전용
    if has_heal and not has_damage:
        return [("character", "hp_heal"), ("skill", "cure"), ("skill", "holy")][h % 3]

    # 버프 전용
    if has_buff and not has_damage and not has_heal:
        return [("character", "status_buff"), ("skill", "haste"), ("skill", "barrier"), ("skill", "protect")][h % 4]

    # 디버프 전용
    if has_debuff and not has_damage:
        return [("character", "status_debuff"), ("skill", "slow"), ("skill", "confusion")][h % 3]

    # 물리 공격
    if has_damage and not is_magical:
        sid = skill_id.lower()
        if any(kw in sid for kw in ("slash", "cut", "blade", "sword", "saber")):
            return [("skill", "slash"), ("skill", "slash2"), ("skill", "sword"), ("combat", "sword4")][h % 4]
        if any(kw in sid for kw in ("shot", "gun", "bullet", "snipe", "cannon")):
            return [("skill", "gun_shot"), ("combat", "attack_gun"), ("skill", "explosion")][h % 3]
        if any(kw in sid for kw in ("arrow", "bow", "rain")):
            return [("combat", "attack_gun"), ("skill", "gun_shot")][h % 2]
        if any(kw in sid for kw in ("explo", "bomb", "blast", "burst")):
            return [("skill", "explosion"), ("skill", "flare"), ("skill", "cannon")][h % 3]
        if any(kw in sid for kw in ("strike", "bash", "crush", "smash", "hit", "blow")):
            return [("combat", "attack_physical"), ("combat", "critical"), ("combat", "damage_high"), ("combat", "multi_hit")][h % 4]
        if any(kw in sid for kw in ("punch", "kick", "fist", "claw", "bite")):
            return [("combat", "attack_physical"), ("combat", "multi_hit"), ("combat", "damage_high")][h % 3]
        if any(kw in sid for kw in ("lance", "spear", "stab", "pierce", "thrust")):
            return [("combat", "attack_physical"), ("skill", "slash"), ("combat", "damage_high")][h % 3]
        if any(kw in sid for kw in ("drain", "absorb", "steal", "siphon")):
            return [("skill", "dark"), ("combat", "damage_low")][h % 2]
        if target in ("all_enemies", "all"):
            return [("combat", "multi_hit"), ("skill", "explosion"), ("skill", "slash2")][h % 3]
        return [("combat", "attack_physical"), ("skill", "sword"), ("combat", "damage_high"), ("skill", "slash"), ("combat", "multi_hit")][h % 5]

    # 마법 공격
    if has_damage and is_magical:
        if target in ("all_enemies", "all"):
            return [("skill", "elemental"), ("skill", "cast_complete"), ("skill", "explosion")][h % 3]
        return [("skill", "cast_complete"), ("skill", "elemental"), ("skill", "magic_cast")][h % 3]

    # 소환/차원
    sid_lower = skill_id.lower()
    if any(kw in sid_lower for kw in ("summon", "phantom", "spirit")):
        return ("skill", "summon")
    if any(kw in sid_lower for kw in ("dimension", "teleport", "warp", "rift")):
        return ("skill", "teleport")
    if any(kw in sid_lower for kw in ("roar", "cry", "shout", "taunt")):
        return ("skill", "roar")
    if any(kw in sid_lower for kw in ("shield", "guard", "defend", "armor")):
        return ("skill", "barrier")
    if any(kw in sid_lower for kw in ("song", "lullaby", "anthem", "melody")):
        return [("skill", "bell"), ("skill", "sound1"), ("skill", "sound2")][h % 3]

    return ("combat", "attack_physical")


def _load_yaml_file(file_path: Path) -> Dict[str, Any]:
    try:
        with file_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("[YAML SKILL] 파일 읽기 실패: %s (%s)", file_path, exc)
        return {}


def _map_damage_type(value: str) -> DamageType:
    if not value:
        return DamageType.BRV
    value = value.lower()
    if value == "hp":
        return DamageType.HP
    if value in ("brv_hp", "hp_brv", "mixed"):
        return DamageType.BRV_HP
    return DamageType.BRV


def _map_operation(value: str) -> GimmickOperation:
    if not value:
        return GimmickOperation.ADD
    value = value.lower()
    if value in ("set", "assign"):
        return GimmickOperation.SET
    if value in ("reset", "clear"):
        return GimmickOperation.SET
    if value in ("consume", "use", "spend"):
        return GimmickOperation.CONSUME
    if value in ("multiply", "mul", "scale"):
        return GimmickOperation.MULTIPLY
    if value in ("reload_magazine", "reload"):
        return GimmickOperation.RELOAD_MAGAZINE
    if value in ("load_bullets", "load"):
        return GimmickOperation.LOAD_BULLETS
    if value == "auto_stance":
        return GimmickOperation.AUTO_STANCE
    return GimmickOperation.ADD


def _create_damage_effect(data: Dict[str, Any]) -> DamageEffect:
    effect = DamageEffect(
        damage_type=_map_damage_type(data.get("damage_type")),
        multiplier=float(data.get("multiplier", 1.0)),
        gimmick_bonus=data.get("gimmick_bonus"),
        stat_type="magical" if data.get("stat_base") in ("magic", "magical") else data.get("stat_base", "physical"),
        conditional_bonus=data.get("conditional_bonus"),
        hp_scaling=data.get("hp_scaling", False),
    )
    if "element" in data:
        # t_756d8ec1: element 값은 로드 시점에 canonical로 정규화 (thunder→lightning)
        setattr(effect, "element", normalize_element(data["element"]))
    return effect


def _create_heal_effect(data: Dict[str, Any]) -> HealEffect:
    raw_heal_type = data.get("heal_type", data.get("restore_type", "hp")).lower()
    set_percent = data.get("set_percent")

    # heal_type/restore_type: full → HP/MP 전회복 (set_percent=1.0)
    if raw_heal_type == "full":
        # mp_restore 타입이면 MP, 아니면 HP
        effect_type = data.get("type", "heal")
        if effect_type == "mp_restore":
            heal_type = HealType.MP
        else:
            heal_type = HealType.HP
        set_percent = 1.0
    elif raw_heal_type == "mp":
        heal_type = HealType.MP
    elif raw_heal_type == "brv":
        heal_type = HealType.BRV
    else:
        heal_type = HealType.HP

    percentage = data.get("percent")
    if percentage is None:
        percentage = data.get("percentage")
    base_amount = data.get("amount", data.get("base_amount", data.get("value")))
    fixed_amount = data.get("fixed_amount", data.get("flat"))
    return HealEffect(
        heal_type=heal_type,
        base_amount=base_amount or 0,
        percentage=percentage or 0,
        stat_scaling=data.get("stat_scaling"),
        multiplier=data.get("multiplier", 1.0),
        is_party_wide=data.get("is_party_wide", False),
        set_percent=set_percent,
        fixed_amount=fixed_amount,
        metadata=data.get("metadata", {}),
        target_self=data.get("target_self", False),
    )


def _map_buff_type(data: Dict[str, Any]) -> tuple[str, Optional[str]]:
    if data.get("buff_id"):
        return data["buff_id"], data.get("custom_stat")
    if data.get("buff_type"):
        return data["buff_type"], data.get("custom_stat")

    stat = data.get("stat")
    if stat:
        stat_key = str(stat).lower()
        stat_map = {
            "attack": BuffType.ATTACK_UP,
            "physical_attack": BuffType.ATTACK_UP,
            "strength": BuffType.ATTACK_UP,
            "magic": BuffType.MAGIC_UP,
            "magic_attack": BuffType.MAGIC_UP,
            "magic_power": BuffType.MAGIC_UP,
            "defense": BuffType.DEFENSE_UP,
            "physical_defense": BuffType.DEFENSE_UP,
            "magic_defense": BuffType.MAGIC_DEFENSE_UP,
            "resistance": BuffType.MAGIC_DEFENSE_UP,
            "spirit": BuffType.SPIRIT_UP,
            "speed": BuffType.SPEED_UP,
            "critical": BuffType.CRITICAL_UP,
            "accuracy": BuffType.ACCURACY_UP,
            "evasion": BuffType.EVASION_UP,
        }
        mapped = stat_map.get(stat_key)
        if mapped:
            return mapped, None
        return BuffType.CUSTOM, stat

    special = data.get("special")
    if special:
        return str(special), data.get("custom_stat")

    return BuffType.CUSTOM, data.get("custom_stat")


def _create_buff_effect(data: Dict[str, Any]) -> BuffEffect:
    buff_type, custom_stat = _map_buff_type(data)
    value = data.get("value")
    multiplier = data.get("multiplier")
    # 값이 없고 effects만 있는 경우 안전하게 0으로 기본값 설정
    if value is None and multiplier is None:
        value = 0
    return BuffEffect(
        buff_type=buff_type or "custom",
        value=value,
        duration=data.get("duration", 3),
        is_party_wide=data.get("is_party_wide", False),
        multiplier=multiplier,
        target=data.get("target"),
        custom_stat=custom_stat,
    )


def _create_custom_handler_effect(handler_name: str, data: Dict[str, Any]):
    """지정 핸들러를 호출하는 CustomEffect 생성"""
    from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
    from src.character.skills.custom_handlers import execute_custom_handler

    class CustomHandlerEffect(SkillEffect):
        def __init__(self, handler: str, args: Dict[str, Any]):
            super().__init__(EffectType.GIMMICK)
            self.handler_name = handler
            self.args = args

        def execute(self, user, target, context):
            return execute_custom_handler(self.handler_name, self.args, user, target, context)

    args = {k: v for k, v in data.items() if k not in {"type", "handler"}}
    return CustomHandlerEffect(handler_name, args)


# 모든 스텁 이펙트가 구현 완료됨 - 빈 set
STUB_EFFECT_TYPES = set()


def _create_status_effect(data: Dict[str, Any]) -> StatusEffect:
    return StatusEffect(
        status_type=data.get("status_type") or data.get("debuff_id") or "unknown",
        duration=data.get("duration", 3),
        value=data.get("value", 0),
        stackable=data.get("stackable", False),
        remove=data.get("remove", False),
        damage_stat=data.get("damage_stat"),
        damage_multiplier=data.get("damage_multiplier", 0),
        cannot_resist=data.get("cannot_resist", False),
        chance=data.get("chance", 1.0),
        resonance_chance=data.get("resonance_chance"),
        resonance_duration_bonus=data.get("resonance_duration_bonus", 0),
    )


def _create_gimmick_effect(data: Dict[str, Any]) -> GimmickEffect:
    return GimmickEffect(
        operation=_map_operation(data.get("operation")),
        field=data.get("field") or data.get("stat") or data.get("gimmick"),
        value=data.get("value", 0),
        max_value=data.get("max_value"),
        min_value=data.get("min_value"),
        apply_to_target=data.get("apply_to_target", False),
    )


def _create_taunt_effect(data: Dict[str, Any]) -> TauntEffect:
    return TauntEffect(duration=data.get("duration", 2), cannot_resist=data.get("cannot_resist", False))


def _create_protect_effect(data: Dict[str, Any]) -> ProtectEffect:
    return ProtectEffect(
        duration=data.get("duration", 2),
        redirect_ratio=data.get("redirect_ratio", 1.0),
        shield_percent=data.get("shield_percent", 0.0),
        damage_reduction=data.get("damage_reduction", 0.0),
    )


def _create_fixed_damage_effect(data: Dict[str, Any]) -> FixedDamageEffect:
    return FixedDamageEffect(value=data.get("value", 0), target=data.get("target"))


def _create_shield_effect(data: Dict[str, Any]) -> ShieldEffect:
    effect = ShieldEffect(
        base_amount=data.get("base_amount", 0),
        hp_consumed_multiplier=data.get("hp_consumed_multiplier", 0.0),
        multiplier=data.get("multiplier", data.get("stat_multiplier", 0.0)),
        stat_name=data.get("stat_name"),
    )
    # 메타데이터 전달용 필드를 그대로 부착
    for extra_key in ("hp_ratio", "duration", "shield_type", "requires_shield"):
        if extra_key in data:
            setattr(effect, extra_key, data[extra_key])
    return effect


def _create_restore_gimmick_effect(data: Dict[str, Any]) -> GimmickEffect:
    field = data.get("gimmick") or data.get("field") or data.get("stat")
    return GimmickEffect(
        operation=GimmickOperation.ADD,
        field=field,
        value=data.get("amount", data.get("value", 0)),
        max_value=data.get("max_value"),
    )


def _create_conditional_buff_effect(data: Dict[str, Any]):
    """조건부 버프는 커스텀 핸들러로 context에 전달한다."""
    from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

    class ConditionalBuffEffect(SkillEffect):
        def __init__(self, payload: Dict[str, Any]):
            super().__init__(EffectType.BUFF)
            self.payload = payload

        def execute(self, user, target, context):
            if context is None:
                context = {}
            handlers = context.setdefault("custom_handlers", [])
            handlers.append(("conditional_buff", self.payload, target))
            return EffectResult(effect_type=self.effect_type, success=True)

    return ConditionalBuffEffect(data)


def _create_lifesteal_effect(data: Dict[str, Any]):
    """흡혈 효과 생성"""
    from src.character.skills.effects.lifesteal_effect import LifestealEffect
    percent = data.get("percent", 0.3)
    low_hp_bonus = data.get("low_hp_bonus", True)
    return LifestealEffect(lifesteal_percent=percent, low_hp_bonus=low_hp_bonus)


def _create_atb_boost_effect(data: Dict[str, Any]) -> AtbBoostEffect:
    """atb_boost 이펙트 빌더 - 대상 ATB를 고정값만큼 증가"""
    return AtbBoostEffect(
        amount=int(data.get("amount", data.get("value", 500))),
        is_party_wide=data.get("is_party_wide", False),
    )


def _create_atb_charge_effect(data: Dict[str, Any]) -> AtbChargeEffect:
    """atb_charge 이펙트 빌더 - 대상 ATB를 퍼센트만큼 충전"""
    return AtbChargeEffect(percent=float(data.get("percent", data.get("value", 50))))


def _create_self_atb_cost_effect(data: Dict[str, Any]):
    """self_atb_cost 이펙트 빌더 - 시전자 ATB 추가 소비

    amount(고정값) 또는 percent(비율)를 지원한다. time_accel.yaml은
    value: 0.5 (50% 소비) 형태이므로 value를 percent로도 해석한다.
    """
    percent = data.get("percent")
    amount = data.get("amount")
    value = data.get("value")
    if amount is not None:
        return SelfAtbCostEffect(amount=int(amount))
    ratio = float(percent if percent is not None else (value if value is not None else 0))
    if ratio <= 1.0:
        ratio *= 100.0
    return SelfAtbCostPercentEffect(percent=ratio)


def _create_multi_hit_hp_damage_effect(data: Dict[str, Any]) -> MultiHitHpDamageEffect:
    """multi_hit_hp_damage 이펙트 빌더 - 고정 횟수 HP 다단히트"""
    return MultiHitHpDamageEffect(
        hits=int(data.get("hits", 3)),
        multiplier=float(data.get("multiplier", 0.5)),
    )


def _create_random_hp_hits_effect(data: Dict[str, Any]) -> RandomHpHitsEffect:
    """random_hp_hits 이펙트 빌더 - 랜덤 횟수 HP 다단히트"""
    return RandomHpHitsEffect(
        min_hits=int(data.get("min_hits", 2)),
        max_hits=int(data.get("max_hits", 5)),
        multiplier=float(data.get("multiplier", 0.3)),
    )


def _create_chain_cast_effect(data: Dict[str, Any]) -> ChainCastEffect:
    """chain_cast 이펙트 빌더 - 스킬 목록 연속 발동"""
    return ChainCastEffect(skills=data.get("skills", []))


def _create_chain_damage_effect(data: Dict[str, Any]) -> ChainDamageEffect:
    """chain_damage 이펙트 빌더 - 원소 스택 기반 연쇄 폭발"""
    elements = data.get("element", [])
    if isinstance(elements, str):
        elements = [elements]
    return ChainDamageEffect(
        elements=elements,
        multiplier=float(data.get("multiplier", 1.0)),
        chain_chance_per_stack=float(data.get("chain_chance_per_stack", 0.2)),
        damage_falloff=data.get("damage_falloff", [0.7, 0.5, 0.3]),
        stat_base=data.get("stat_base", "magic"),
    )


def _create_temporal_heal_effect(data: Dict[str, Any]) -> TemporalHealEffect:
    """temporal_heal 이펙트 빌더 - 과거 HP 기준 시간 회복"""
    return TemporalHealEffect(
        method=data.get("method", "restore_past_hp"),
        turns_back=int(data.get("turns_back", 2)),
        max_heal_percent=float(data.get("max_heal_percent", 0.4)),
    )


def _create_damage_share_effect(data: Dict[str, Any]) -> DamageShareEffect:
    """damage_share 이펙트 빌더 - 피해 분담 링크 등록"""
    return DamageShareEffect(
        share_percent=float(data.get("share_percent", 0.4)),
        duration=int(data.get("duration", 3)),
        linked_to=data.get("linked_to", "caster"),
    )


EFFECT_BUILDERS = {
    "damage": _create_damage_effect,
    "hp_damage": _create_damage_effect,  # hp_damage를 damage와 동일 처리
    "heal": _create_heal_effect,
    "mp_restore": _create_heal_effect,
    "buff": _create_buff_effect,
    "debuff": _create_status_effect,
    "status": _create_status_effect,
    "status_effect": _create_status_effect,
    "refraction_to_shield": lambda data: _create_custom_handler_effect("refraction_to_shield", data),
    "gimmick": _create_gimmick_effect,
    "cleanse": lambda data: _create_custom_handler_effect("cleanse", data),
    "dispel": lambda data: _create_custom_handler_effect("cleanse", data),
    "revive": lambda data: _create_custom_handler_effect("revive", data),
    "taunt": _create_taunt_effect,
    "protect": _create_protect_effect,
    "fixed_damage": _create_fixed_damage_effect,
    "shield": _create_shield_effect,
    "apply_shield": _create_shield_effect,
    "restore_gimmick": _create_restore_gimmick_effect,
    "conditional_buff": _create_conditional_buff_effect,
    "toggle_buff": lambda data: _create_custom_handler_effect("toggle_buff", data),
    "lifesteal": _create_lifesteal_effect,
    # ── 신규 구현 이펙트 ──
    "atb_boost": _create_atb_boost_effect,
    "atb_charge": _create_atb_charge_effect,
    "self_atb_cost": _create_self_atb_cost_effect,
    "multi_hit_hp_damage": _create_multi_hit_hp_damage_effect,
    "random_hp_hits": _create_random_hp_hits_effect,
    "chain_cast": _create_chain_cast_effect,
    "chain_damage": _create_chain_damage_effect,
    "temporal_heal": _create_temporal_heal_effect,
    "damage_share": _create_damage_share_effect,
    # ── 환술사 환영 시스템 ──
    "summon_phantom": lambda data: SummonPhantomEffect(
        count=int(data.get("count", data.get("base_count", 1))),
        bonus_count=int(data.get("bonus_count", 0)),
        bonus_chance=float(data.get("bonus_chance", 0.0)),
        fill_to_max=bool(data.get("fill_to_max", False)),
        luck_scaling=float(data.get("luck_scaling", 0.0)),
    ),
    "consume_phantom": lambda data: ConsumePhantomEffect(
        count=int(data.get("count", 1)),
    ),
    "phantom_echo_damage": lambda data: PhantomEchoDamageEffect(
        per_phantom_multiplier=float(data.get("per_phantom_multiplier", 0.25)),
        damage_type=data.get("damage_type", "physical"),
        stat_base=data.get("stat_base", "physical"),
    ),
    "consume_all_phantoms": lambda data: ConsumeAllPhantomsEffect(
        store_count=bool(data.get("store_count", True)),
    ),
    "phantom_bonus_debuff": lambda data: PhantomBonusDebuffEffect(
        per_phantom_bonus=float(data.get("per_phantom_bonus", 0.05)),
        stat=data.get("stat", "accuracy"),
        max_bonus=float(data.get("max_bonus", 1.0)),
    ),
    "phantom_convergence_bonus": lambda data: PhantomConvergenceBonusEffect(
        per_phantom_bonus=float(data.get("per_phantom_bonus", 0.25)),
        max_bonus=float(data.get("max_bonus", 1.0)),
    ),
    "phantom_damage_redirect": lambda data: PhantomDamageRedirectEffect(
        redirect_percent=float(data.get("redirect_percent", 0.5)),
        destroy_on_damage=bool(data.get("destroy_on_damage", True)),
        duration=int(data.get("duration", 3)),
    ),
    "phantom_priority": lambda data: PhantomPriorityEffect(
        redirect_chance=float(data.get("redirect_chance", 0.7)),
    ),
    "phantom_counter": lambda data: PhantomCounterEffect(
        counter_chance=float(data.get("counter_chance", 0.25)),
        counter_damage=float(data.get("counter_damage", 0.5)),
        stat_base=data.get("stat_base", "physical"),
    ),
    # ── 차원술사 가능성 시스템 ──
    "generate_possibility": lambda data: GeneratePossibilityEffect(
        chance=float(data.get("chance", 0.7)),
        alternative_skill=data.get("alternative_skill", ""),
    ),
    "release_all_possibilities": lambda data: ReleaseAllPossibilitiesEffect(
        power_ratio=float(data.get("power_ratio", 1.0)),
        sequence=bool(data.get("sequence", True)),
        delay_between=float(data.get("delay_between", 0.3)),
    ),
    "summon_possibility": lambda data: SummonPossibilityEffect(
        power_ratio=float(data.get("power_ratio", 0.85)),
        select_slot=bool(data.get("select_slot", True)),
    ),
    "consume_option": lambda data: ConsumeOptionEffect(
        consume_phantoms=int(data.get("consume_phantoms", 0)),
        bonus_if_consumed=data.get("bonus_if_consumed"),
    ),
    # ── 잔상 시스템 ──
    "consume_afterimage": lambda data: ConsumeAfterimageEffect(
        amount=data.get("amount", 1),
    ),
    "afterimage_scaling": lambda data: AfterimageScalingEffect(
        bonus_per_afterimage=float(data.get("bonus_per_afterimage", 0.01)),
    ),
    "charge_afterimage": lambda data: ChargeAfterimageEffect(
        value=int(data.get("value", 1)),
    ),
    # ── 시간 시스템 ──
    "time_fracture": lambda data: TimeFractureEffect(
        effect=data.get("effect", "all_stats_down"),
        value=float(data.get("value", 0.2)),
        duration=int(data.get("duration", 2)),
        target=data.get("target", "all_enemies"),
    ),
    "time_crossing": lambda data: TimeCrossingEffect(
        power_ratio=float(data.get("power_ratio", 0.75)),
        slot_count=int(data.get("slot_count", 2)),
        select_slots=bool(data.get("select_slots", True)),
    ),
    "time_storm": lambda data: TimeStormEffect(
        power_ratio=float(data.get("power_ratio", 1.2)),
        release_all=bool(data.get("release_all", True)),
    ),
    # ── 유틸리티/슬롯 시스템 ──
    "clear_slots": lambda data: ClearSlotsEffect(
        after_cast=bool(data.get("after_cast", True)),
    ),
    "gain_gimmick": lambda data: GainGimmickEffect(
        gimmick=data.get("gimmick", ""),
        amount=int(data.get("amount", 1)),
    ),
    "consume_gimmick": lambda data: ConsumeGimmickEffect(
        gimmick=data.get("gimmick", ""),
        amount=int(data.get("amount", 1)),
    ),
    "convergence_bonus": lambda data: ConvergenceBonusEffect(
        min_possibilities=int(data.get("min_possibilities", 3)),
        damage_bonus=float(data.get("damage_bonus", 0.5)),
        apply_debuff=data.get("apply_debuff"),
    ),
    "shield_damage": lambda data: ShieldDamageEffect(
        bonus_multiplier=float(data.get("bonus_multiplier", 1.5)),
    ),
    "area_damage": lambda data: AreaDamageEffect(
        splash_ratio=float(data.get("splash_ratio", 0.5)),
    ),
    # ── 상태이상/트리거 시스템 ──
    "on_evade_trigger": lambda data: OnEvadeTriggerEffect(
        effect=data.get("effect", "summon_phantom"),
        count=int(data.get("count", 1)),
        duration=int(data.get("duration", 3)),
    ),
    "apply_trap": lambda data: ApplyTrapEffect(
        trap_type=data.get("trap_type", "mirror_reflect"),
        duration=int(data.get("duration", 2)),
        trigger_chance=float(data.get("trigger_chance", 0.3)),
        reflect_ratio=float(data.get("reflect_ratio", 0.4)),
        damage_type=data.get("damage_type", "magic"),
    ),
    "brand": lambda data: BrandEffect(
        vulnerability=float(data.get("vulnerability", 0.4)),
        duration=int(data.get("duration", 5)),
        brands=data.get("brands"),
    ),
    "electrocution": lambda data: ElectrocutionEffect(
        element=data.get("element"),
        brv_multiplier=float(data.get("brv_multiplier", 1.0)),
        hp_multiplier=float(data.get("hp_multiplier", 1.0)),
    ),
    "glyph": lambda data: GlyphEffect(
        delay_turns=int(data.get("delay_turns", 3)),
        max_glyphs=int(data.get("max_glyphs", 3)),
    ),
    # ── 원소/변환 시스템 ──
    "overload": lambda data: OverloadEffect(
        min_stacks=int(data.get("min_stacks", 3)),
        fire_effect=data.get("fire_effect", "burning"),
        ice_effect=data.get("ice_effect", "frozen_solid"),
        lightning_effect=data.get("lightning_effect", "stun"),
        stat_base=data.get("stat_base", "magic"),
    ),
    "transmutation": lambda data: TransmutationEffect(
        consume_amount=int(data.get("consume_amount", 2)),
        generate_amount=int(data.get("generate_amount", 3)),
        mp_recovery=int(data.get("mp_recovery", 0)),
    ),
    "thermal_shock": lambda data: ThermalShockEffect(
        element=data.get("element"),
        multiplier=float(data.get("multiplier", 2.0)),
        diff_bonus_per_stack=float(data.get("diff_bonus_per_stack", 0.15)),
    ),
    # ── 운명 시스템 ──
    "fate_copy": lambda data: FateCopyEffect(
        copy_last_skill=bool(data.get("copy_last_skill", True)),
        store_as_possibility=bool(data.get("store_as_possibility", True)),
        power_ratio=float(data.get("power_ratio", 0.85)),
        target=data.get("target", "selected_ally"),
    ),
    "overwrite_fate": lambda data: OverwriteFateEffect(
        select_slot=bool(data.get("select_slot", True)),
        select_replacement_skill=bool(data.get("select_replacement_skill", True)),
        power_ratio=float(data.get("power_ratio", 0.85)),
    ),
}

# 스텁 effect 타입을 모두 custom handler로 연결하여 경고 없이 통과
for _stub in STUB_EFFECT_TYPES:
    EFFECT_BUILDERS[_stub] = lambda data, name=_stub: _create_custom_handler_effect(name, data)


def _create_effect(data: Dict[str, Any]):
    effect_type = (data.get("type") or "").lower()
    if not effect_type:
        return None

    builder = EFFECT_BUILDERS.get(effect_type)
    if builder:
        effect = builder(data)
        target_override = data.get("target")
        if target_override:
            setattr(effect, "target_override", target_override)
        return effect

    if effect_type == "custom":
        handler = data.get("handler")
        if not handler:
            logger.warning("[YAML SKILL] custom handler 누락: data=%s", data)
            return None

        from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
        from src.character.skills.custom_handlers import execute_custom_handler

        class CustomEffect(SkillEffect):
            def __init__(self, handler_name: str, args: Dict[str, Any]):
                super().__init__(EffectType.GIMMICK)
                self.handler_name = handler_name
                self.args = args

            def execute(self, user, target, context):
                return execute_custom_handler(self.handler_name, self.args, user, target, context)

        args = {k: v for k, v in data.items() if k not in {"type", "handler"}}
        return CustomEffect(handler, args)

    logger.warning("[YAML SKILL] 지원되지 않는 effect type: %s", effect_type)
    return None


def _create_costs(data: Dict[str, Any]) -> List[Any]:
    costs = []
    if not data:
        return costs
    if data.get("mp") is not None:
        costs.append(MPCost(int(data["mp"])))
    if data.get("hp") is not None:
        costs.append(HPCost(int(data["hp"])))
    # faith 비용 처리 (성기사 기적 스킬용)
    if data.get("faith") is not None:
        costs.append(StackCost("faith", int(data["faith"])))
    # teamwork_gauge는 TeamworkSkill.can_use()에서 파티 게이지로 직접 검증하므로
    # StackCost로 추가하지 않음 (StackCost는 캐릭터 속성을 검사하여 실패함)
    stacks = data.get("stacks")
    if isinstance(stacks, dict):
        for stack_id, amount in stacks.items():
            try:
                costs.append(StackCost(stack_id, int(amount)))
            except Exception as exc:
                logger.warning("[YAML SKILL] stack cost 변환 실패: %s (%s)", stack_id, exc)
    stack_data = data.get("stack")
    if isinstance(stack_data, dict):
        stack_id = stack_data.get("id") or stack_data.get("name")
        amount = stack_data.get("amount", stack_data.get("value", 1))
        if stack_id:
            costs.append(StackCost(stack_id, int(amount)))
    stack_list = data.get("stack_costs")
    if isinstance(stack_list, list):
        for item in stack_list:
            if isinstance(item, dict):
                stack_id = item.get("id") or item.get("name")
                amount = item.get("amount", item.get("value", 1))
                if stack_id:
                    costs.append(StackCost(stack_id, int(amount)))
    return costs


def _create_skill(data: Dict[str, Any]) -> Skill:
    skill_id = data.get("id")
    name = data.get("name", skill_id)
    description = data.get("description", "")
    skill_type = data.get("type", "combat")

    if skill_type == "teamwork" or data.get("metadata", {}).get("teamwork"):
        gauge_cost = data.get("costs", {}).get("teamwork_gauge", 100)
        skill = TeamworkSkill(skill_id, name, description, gauge_cost=gauge_cost)
    else:
        skill = Skill(skill_id, name, description)

    skill.target_type = data.get("target", "single_enemy")
    skill.category = skill_type
    skill.metadata = data.get("metadata", {})
    # RAM 비용이 costs에 정의된 경우 메타데이터로도 전달하여 처리 일관성 확보
    ram_cost = data.get("costs", {}).get("ram")
    if ram_cost is not None:
        try:
            skill.metadata.setdefault("ram_cost", int(ram_cost))
        except Exception:
            pass
    skill.cast_time = data.get("cast_time") or data.get("costs", {}).get("cast_time")
    sfx_field = data.get("sfx")
    if isinstance(sfx_field, (list, tuple)) and len(sfx_field) == 2:
        cat, name = sfx_field[0], sfx_field[1]
        if cat == "se":
            # "se" 카테고리는 config에 없음 → 파일명으로 변환
            skill.sfx = _SE_TO_CONFIG_SFX.get(name) or _infer_sfx(data)
        else:
            skill.sfx = (cat, name)
    else:
        skill.sfx = _infer_sfx(data)
    skill.is_aoe = skill.target_type in {"all_enemies", "all_allies", "party", "all"}
    skill.triggers_chain = bool(data.get("triggers_chain", False))

    # variants 사용 시 일반 효과는 base.effects에, 아니면 effects에 정의됨 (t_082c6a99)
    base_data = data.get("base") or {}
    effects_data = data.get("effects") or (base_data.get("effects") if isinstance(base_data, dict) else None) or []
    for effect_data in effects_data:
        effect = _create_effect(effect_data)
        if effect:
            skill.effects.append(effect)

    # variants 파생 프리미티브 (t_082c6a99): base.effects 뒤에 변형 전용 효과를 append하고
    # 실행 시 선택 변형의 인덱스만 활성화 (_variant_filter 매핑).
    variants = data.get("variants")
    if isinstance(variants, dict) and variants.get("options"):
        _apply_variant_primitive(skill, variants)

    costs = _create_costs(data.get("costs"))
    skill.costs.extend(costs)

    return skill


def _apply_variant_primitive(skill: Skill, variants: Dict[str, Any]) -> None:
    """variants YAML → skill.metadata['variant_options'] + 변형 전용 효과 등록.

    - 각 옵션의 extra_status/extra_buff는 기존 StatusEffect/BuffEffect 빌더를 재사용해
      skill.effects 뒤에 등록하고, metadata['_variant_filter'][element] = [effect_idx...]
      로 실행 시점 필터링 대상을 기록한다.
    - 실행 시점 병합(_selected_variant → metadata_override 주입)은 skill.execute 참조.
    """
    options = variants.get("options") or {}
    default_key = variants.get("default")
    if not default_key or default_key not in options:
        default_key = next(iter(options), None)

    variant_options: Dict[str, Any] = {}
    variant_filter: Dict[str, list] = {}

    for key, opt in options.items():
        if not isinstance(opt, dict):
            continue
        entry: Dict[str, Any] = {"label": opt.get("label", key)}
        meta_override = opt.get("metadata_override")
        if meta_override:
            entry["metadata_override"] = dict(meta_override)
            # t_756d8ec1: element 값만 canonical 정규화 (seal_type 등은 무변경)
            if "element" in entry["metadata_override"]:
                entry["metadata_override"]["element"] = normalize_element(
                    entry["metadata_override"]["element"]
                )
        if opt.get("extra_status"):
            entry["extra_status"] = dict(opt["extra_status"])
        if opt.get("extra_buff"):
            entry["extra_buff"] = dict(opt["extra_buff"])
        if opt.get("extra_atb_boost") is not None:
            entry["extra_atb_boost"] = opt["extra_atb_boost"]
        variant_options[key] = entry

        effect_indices = []
        extra_status = opt.get("extra_status")
        if extra_status:
            status_data = dict(extra_status)
            if "status_id" in status_data and "status_type" not in status_data:
                status_data["status_type"] = status_data.pop("status_id")
            effect = _create_status_effect(status_data)
            skill.effects.append(effect)
            effect_indices.append(len(skill.effects) - 1)
        extra_buff = opt.get("extra_buff")
        if extra_buff:
            buff_data = dict(extra_buff)
            stats = buff_data.pop("stats", None)
            if isinstance(stats, dict) and stats:
                stat_key, stat_value = next(iter(stats.items()))
                buff_data.setdefault("value", stat_value)
                buff_data.setdefault("custom_stat", stat_key)
                buff_data.setdefault("buff_type", "custom")
            effect = _create_buff_effect(buff_data)
            skill.effects.append(effect)
            effect_indices.append(len(skill.effects) - 1)
        extra_atb = opt.get("extra_atb_boost")
        if extra_atb:
            # atb_boost는 metadata 기반(gimmick_updater atb_boost 처리)이므로
            # metadata_override로 주입만 하면 됨 — 별도 effect 없음
            entry.setdefault("metadata_override", {})["atb_boost"] = float(extra_atb)

        if effect_indices:
            variant_filter[key] = effect_indices

    skill.metadata["variant_options"] = variant_options
    skill.metadata["variant_default"] = default_key
    skill.metadata["variant_capable"] = True
    if variant_filter:
        skill.metadata["_variant_filter"] = variant_filter


def load_yaml_skills(skill_manager):
    """data/skills 폴더의 YAML 스킬을 모두 등록한다."""
    if not SKILLS_DIR.exists():
        logger.warning("[YAML SKILL] 디렉터리 없음: %s", SKILLS_DIR)
        return []

    registered_ids = []
    for file_path in sorted(SKILLS_DIR.glob("*.yaml")):
        data = _load_yaml_file(file_path)
        if not data:
            continue

        metadata = data.get("metadata", {})
        if metadata.get("state") == "deprecated":
            logger.info("[YAML SKILL] deprecated 스킬 스킵: %s", file_path.name)
            continue

        try:
            skill = _create_skill(data)
        except Exception as exc:
            logger.error("[YAML SKILL] 변환 실패 (%s): %s", file_path, exc)
            continue

        if skill_manager.get_skill(skill.skill_id):
            logger.warning(f"[YAML SKILL] 중복 ID: {skill.skill_id} ({file_path.name})")
            continue

        skill_manager.register_skill(skill)
        registered_ids.append(skill.skill_id)
        logger.debug("[YAML SKILL] 등록: %s", skill.skill_id)

    logger.info("[YAML SKILL] 등록 완료: %d개", len(registered_ids))
    return registered_ids
