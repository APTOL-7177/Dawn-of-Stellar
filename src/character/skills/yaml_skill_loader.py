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
        stat_type=data.get("stat_base", "physical"),
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
        skill.sfx = tuple(sfx_field)
    else:
        skill.sfx = None  # 기본 SFX 미지정 (개별 스킬에 명시 필요)
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
