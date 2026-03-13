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
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.hp_cost import HPCost
from src.character.skills.costs.stack_cost import StackCost

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
        setattr(effect, "element", data["element"])
    return effect


def _create_heal_effect(data: Dict[str, Any]) -> HealEffect:
    heal_type = HealType.HP if data.get("heal_type", "hp").lower() == "hp" else HealType.MP
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
        set_percent=data.get("set_percent"),
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


# 지원하지만 실제 효과는 스텁 처리할 커스텀 effect 타입들
STUB_EFFECT_TYPES = {
    "consume_afterimage",
    "afterimage_scaling",
    "summon_phantom",
    "generate_possibility",
    "phantom_bonus_debuff",
    "phantom_convergence_bonus",
    "consume_option",
    "glyph",
    "brand",
    "overload",
    "transmutation",
    "fate_copy",
    "on_evade_trigger",
    "phantom_damage_redirect",
    "release_all_possibilities",
    "chain_cast",
    "time_fracture",
    "clear_slots",
    "consume_all_phantoms",
    "multi_hit_hp_damage",
    "consume_gimmick",
    "damage_share",
    "gain_gimmick",
    "consume_phantom",
    "charge_afterimage",
    "phantom_echo_damage",
    "apply_trap",
    "overwrite_fate",
    "thermal_shock",
    "temporal_heal",
    "random_hp_hits",
    "atb_boost",
    "summon_possibility",
    "phantom_priority",
    "phantom_counter",
    "chain_damage",
    "atb_charge",
    "self_atb_cost",
    "time_crossing",
    "time_storm",
    "convergence_bonus",
    "shield_damage",
    "area_damage",
    "electrocution",
}


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
    if data.get("teamwork_gauge") is not None:
        costs.append(StackCost("teamwork_gauge", int(data["teamwork_gauge"])))
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

    for effect_data in data.get("effects", []):
        effect = _create_effect(effect_data)
        if effect:
            skill.effects.append(effect)

    costs = _create_costs(data.get("costs"))
    skill.costs.extend(costs)

    return skill


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
