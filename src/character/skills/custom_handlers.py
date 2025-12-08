"""YAML custom handler dispatcher.

스킬 YAML의 `type: custom` 효과를 처리한다.
핵심 리메이크 직업(성기사/검투사/해커/신관/도적/정령술사) 기믹 연동을 우선 지원한다.
"""
from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List

from src.character.gimmick_updater import GimmickUpdater
from src.character.skills.effects.base import EffectResult, EffectType
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
from src.core.event_bus import event_bus, Events
from src.core.logger import get_logger

logger = get_logger("custom_handler")

# 단순 스텁 처리할 커스텀 핸들러 목록 (경고 없이 성공 처리)
STUB_HANDLERS = {
    "consume_afterimage",
    "afterimage_scaling",
    "summon_phantom",
    "electrocution",
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
    "revive",
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
}

def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    return [value]


def _resolve_targets(target: Any, context: Dict[str, Any]) -> List[Any]:
    targets = _as_list(target)
    if not targets:
        # all_enemies/all_allies 컨텍스트에서 가져오기 (AOE)
        for key in ("all_enemies", "all_allies", "enemies"):
            if key in (context or {}):
                targets = _as_list(context.get(key))
                break
    return targets


def _is_buff_status(effect) -> bool:
    st = getattr(effect, "status_type", None)
    if not st:
        return False
    buff_base = {
        StatusType.BUFF,
        StatusType.BLESSING,
        StatusType.GUARDIAN,
        StatusType.HASTE,
        StatusType.REGENERATION,
        StatusType.MP_REGEN,
        StatusType.INVINCIBLE,
        StatusType.REFLECT,
        StatusType.SHIELD,
        StatusType.BARRIER,
        StatusType.MAGIC_BARRIER,
        StatusType.MANA_SHIELD,
        StatusType.HOLY_SHIELD,
        StatusType.BOOST_ALL_STATS,
        StatusType.HOLY_BLESSING,
    }
    try:
        if st in buff_base:
            return True
        name = st.name if hasattr(st, "name") else str(st)
        if name.startswith("BOOST"):
            return True
    except Exception:
        return False
    return False


def _is_debuff_status(effect) -> bool:
    st = getattr(effect, "status_type", None)
    if not st:
        return False
    debuff_base = {
        StatusType.DEBUFF,
        StatusType.DOT,
        StatusType.CC,
        StatusType.REDUCE_ATK,
        StatusType.REDUCE_DEF,
        StatusType.REDUCE_SPD,
        StatusType.REDUCE_ACCURACY,
        StatusType.REDUCE_EVASION,
        StatusType.REDUCE_ALL_STATS,
        StatusType.REDUCE_MAGIC_ATK,
        StatusType.REDUCE_MAGIC_DEF,
        StatusType.VULNERABLE,
        StatusType.EXPOSED,
        StatusType.WEAKNESS,
        StatusType.WEAKEN,
        StatusType.WEAKNESS_EXPOSURE,
        StatusType.HOLY_WEAKNESS,
        StatusType.POISON,
        StatusType.BURN,
        StatusType.BLEED,
        StatusType.CORROSION,
        StatusType.DISEASE,
        StatusType.NECROSIS,
        StatusType.CHILL,
        StatusType.SHOCK,
        StatusType.STUN,
        StatusType.SLEEP,
        StatusType.SILENCE,
        StatusType.BLIND,
        StatusType.PARALYZE,
        StatusType.FREEZE,
        StatusType.SLOW,
        StatusType.MADNESS,
        StatusType.TAUNT,
    }
    try:
        if st in debuff_base:
            return True
        name = st.name if hasattr(st, "name") else str(st)
        if name.startswith("REDUCE"):
            return True
    except Exception:
        return False
    return False


def _int_arg(args: Dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        if key in args and args[key] is not None:
            try:
                return int(args[key])
            except (ValueError, TypeError):
                continue
    return default


def _apply_bonus_damage_from_skill(user, target, context, multiplier: float) -> None:
    """스킬 내 데미지 이펙트 기준으로 추가 피해를 적용한다."""
    if multiplier <= 1.0:
        return
    skill = (context or {}).get("skill")
    if not skill:
        return
    bonus_mult = max(0.0, multiplier - 1.0)
    for effect in getattr(skill, "effects", []):
        if not isinstance(effect, DamageEffect):
            continue
        bonus_effect = DamageEffect(
            damage_type=effect.damage_type,
            multiplier=effect.multiplier * bonus_mult,
            stat_type=getattr(effect, "stat_type", "physical"),
            gimmick_bonus=None,
            hp_scaling=getattr(effect, "hp_scaling", False),
        )
        # 속성/대상 지정 그대로 유지
        if hasattr(effect, "element"):
            bonus_effect.element = getattr(effect, "element")
        if hasattr(effect, "target_override"):
            bonus_effect.target_override = getattr(effect, "target_override")
        try:
            bonus_effect.execute(user, target, context)
        except Exception as exc:  # 안전하게 로그만 남김
            logger.warning("[custom_handler] 추가 피해 적용 실패: %s", exc)


def execute_custom_handler(handler_name: str, args: Dict[str, Any], user, target, context=None) -> EffectResult:
    context = context or {}
    name = (handler_name or "").lower()
    args = args or {}
    targets = _resolve_targets(target, context)

    if name in STUB_HANDLERS:
        return EffectResult(effect_type=EffectType.GIMMICK, success=True)

    try:
        # === 팔라딘/검투사 지원 ===
        if name in {"reroll_crowd_demand", "adjust_expectation"}:
            if getattr(user, "gimmick_type", None) == "crowd_cheer":
                GimmickUpdater.fail_demand(user)
                GimmickUpdater.generate_crowd_demand(user)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="관중 요구 재설정")
        if name == "select_oath":
            oath_id = args.get("oath") or args.get("id") or context.get("selected_oath") or context.get("selected_choice")
            if not oath_id and context.get("skill"):
                try:
                    skill_meta = getattr(context["skill"], "metadata", {}) or {}
                    oath_id = skill_meta.get("_selected_choice")
                except Exception:
                    pass
            if not oath_id:
                oaths = getattr(user, "oaths", {})
                oath_id = next(iter(oaths.keys()), None)
            if oath_id:
                GimmickUpdater.select_oath(user, oath_id)
                oath_name = getattr(user, "oaths", {}).get(oath_id, {}).get("name", oath_id)
                return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"서약 선택: {oath_name}")
            return EffectResult(effect_type=EffectType.GIMMICK, success=False, message="서약 선택 실패")

        # === 정령술사 지원 ===
        if name == "summon_spirit":
            spirit = args.get("spirit") or args.get("spirit_type")
            if spirit:
                GimmickUpdater.summon_spirit(user, str(spirit))
            return EffectResult(effect_type=EffectType.GIMMICK, success=bool(spirit))
        if name == "summon_random_spirits":
            spirits = ["fire", "water", "wind", "earth"]
            count = _int_arg(args, "count", default=2)
            random.shuffle(spirits)
            for spirit in spirits[:count]:
                GimmickUpdater.summon_spirit(user, spirit)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="정령 무작위 소환")
        if name in {"spirit_release", "consume_all_spirits"}:
            released = GimmickUpdater.release_all_spirits(user)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"정령 해방 {released}")
        if name == "spirit_swap":
            GimmickUpdater.swap_spirit_slots(user)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="정령 교대")

        # === 해커 지원 ===
        if name in {"add_intrusion", "add_intrusion_all"}:
            amount = _int_arg(args, "value", "amount", "gain", default=0)
            if not targets and context.get("all_enemies"):
                targets = _as_list(context.get("all_enemies"))
            for t in targets:
                GimmickUpdater.add_intrusion(user, t, amount)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"침투 +{amount}")
        if name == "set_all_intrusion":
            value = _int_arg(args, "value", "amount", default=100)
            if not targets and context.get("all_enemies"):
                targets = _as_list(context.get("all_enemies"))
            for t in targets:
                t.intrusion_gauge = min(100, value)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="침투 설정")
        if name == "reset_intrusion":
            for t in targets:
                GimmickUpdater.reset_intrusion(t)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="침투 초기화")
        if name == "spread_intrusion":
            amount = _int_arg(args, "value", "amount", "gain", default=0)
            spread_targets = _as_list(context.get("all_enemies")) if context else []
            main = target if isinstance(target, (list, tuple)) else target
            for t in spread_targets:
                if main and t is main:
                    continue
                GimmickUpdater.add_intrusion(user, t, amount)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="침투 확산")
        if name == "copy_random_buff":
            if not targets:
                return EffectResult(effect_type=EffectType.GIMMICK, success=True)
            target_obj = targets[0]
            if not hasattr(target_obj, "status_manager") or not hasattr(user, "status_manager"):
                return EffectResult(effect_type=EffectType.GIMMICK, success=True)
            buffs = [e for e in getattr(target_obj.status_manager, "status_effects", []) if _is_buff_status(e)]
            if not buffs:
                return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="복사할 버프 없음")
            src = random.choice(buffs)
            # 효과 복제
            cloned = CombatStatusEffect(
                name=src.name,
                status_type=src.status_type,
                duration=src.duration,
                intensity=getattr(src, "intensity", 1.0),
                stack_count=getattr(src, "stack_count", 1),
                max_stacks=getattr(src, "max_stacks", 1),
                is_stackable=getattr(src, "is_stackable", False),
                source_id=getattr(user, "name", None),
                metadata=dict(getattr(src, "metadata", {}) or {}),
            )
            user.status_manager.add_status(cloned, allow_refresh=True)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"{cloned.name} 복사")
        if name == "copy_enemy_skill":
            # 대상 스킬 중 1개를 기록하여 이번 전투에서 사용 가능하도록 표시 (간소화)
            selected_skill = None
            if targets:
                tgt = targets[0]
                skill_ids = getattr(tgt, "skill_ids", []) or []
                if skill_ids:
                    selected_skill = random.choice(skill_ids)
            if selected_skill:
                copied = getattr(user, "copied_skills", [])
                if selected_skill not in copied:
                    copied = list(copied) + [selected_skill]
                user.copied_skills = copied
                # 실제 사용 가능하도록 skill_ids에도 추가
                if hasattr(user, "skill_ids"):
                    if selected_skill not in user.skill_ids:
                        user.skill_ids.append(selected_skill)
                else:
                    user.skill_ids = [selected_skill]
                return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"스킬 복사: {selected_skill}")
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="복사할 스킬 없음")
        if name == "cleanse":
            # 상태이상 제거 스텁
            if targets:
                for t in targets:
                    if hasattr(t, "status_manager"):
                        t.status_manager.status_effects.clear()
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="정화")
        if name == "revive":
            if targets:
                for t in targets:
                    if hasattr(t, "is_alive"):
                        t.is_alive = True
                        t.current_hp = getattr(t, "max_hp", getattr(t, "current_hp", 0))
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="부활")
        if name == "double_debuff_duration":
            for t in targets:
                if not hasattr(t, "status_manager"):
                    continue
                for eff in getattr(t.status_manager, "status_effects", []):
                    if _is_debuff_status(eff):
                        eff.duration = max(eff.duration * 2, eff.duration + 1)
                        if hasattr(eff, "max_duration"):
                            eff.max_duration = max(eff.max_duration, eff.duration)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="디버프 지속 연장")
        if name == "refraction_to_shield":
            convert_percent = float(args.get("convert_percent", args.get("percent", 0.0)) or 0.0)
            duration = int(args.get("duration", 5))
            targets_list = targets or [user]
            total_converted = 0
            for t in targets_list:
                if not hasattr(user, "refraction_stacks"):
                    continue
                current = getattr(user, "refraction_stacks", 0)
                convert_amount = int(current * convert_percent)
                if convert_amount <= 0:
                    continue
                user.refraction_stacks = max(0, current - convert_amount)
                total_converted += convert_amount
                if hasattr(t, "status_manager"):
                    shield = CombatStatusEffect(
                        name="Refraction Shield",
                        status_type=StatusType.SHIELD,
                        duration=duration,
                        intensity=convert_amount,
                        source_id=getattr(user, "name", None),
                        metadata={"shield_hp": convert_amount},
                    )
                    t.status_manager.add_status(shield, allow_refresh=True)
            msg = f"굴절 보호막 {total_converted}" if total_converted else "굴절 부족"
            return EffectResult(effect_type=EffectType.GIMMICK, success=total_converted > 0, message=msg)

        # === 도적 지원 ===
        if name in {"add_mockery", "add_mockery_all"}:
            amount = _int_arg(args, "value", "amount", "gain", default=0)
            if not targets and context.get("all_enemies"):
                targets = _as_list(context.get("all_enemies"))
            for t in targets:
                GimmickUpdater.add_mockery(user, t, amount)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"농락 +{amount}")
        if name == "set_all_mockery":
            value = _int_arg(args, "value", "amount", default=0)
            if not targets and context.get("all_enemies"):
                targets = _as_list(context.get("all_enemies"))
            for t in targets:
                t.mockery_gauge = min(getattr(user, "max_mockery", 10), value)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="농락 설정")
        if name == "steal_from_enemy":
            tgt = targets[0] if targets else None
            if not tgt:
                return EffectResult(effect_type=EffectType.GIMMICK, success=False, message="대상 없음")

            chances = args.get("steal_chances", {}) or {}
            gold_chance = float(chances.get("gold", 0.0))
            potion_chance = float(chances.get("potion", 0.0))
            buff_chance = float(chances.get("buff", 0.0))

            roll = random.random()
            success_type = None
            if roll < gold_chance:
                success_type = "gold"
            elif roll < gold_chance + potion_chance:
                success_type = "potion"
            elif roll < gold_chance + potion_chance + buff_chance:
                success_type = "buff"

            success = success_type is not None
            mockery_gain = int(args.get("mockery_success" if success else "mockery_fail", 0) or 0)
            if mockery_gain:
                GimmickUpdater.add_mockery(user, tgt, mockery_gain)

            msg = "훔치기 실패"
            if success:
                msg = f"훔치기 성공 ({success_type})"

            try:
                GimmickUpdater._push_ui_log(user, f"[도적] {msg}")
            except Exception:
                logger.debug("UI 로그 실패", exc_info=True)

            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=msg)
        if name == "reset_mockery":
            for t in targets:
                GimmickUpdater.reset_mockery(t)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="농락 초기화")
        if name == "add_mockery_with_stealth":
            base = _int_arg(args, "base", default=_int_arg(args, "value", default=0))
            stealth_val = _int_arg(args, "stealth", default=base)
            amount = stealth_val if getattr(user, "stealth_active", False) else base
            for t in targets:
                GimmickUpdater.add_mockery(user, t, amount)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=f"농락 +{amount}")
        if name in {"enter_stealth", "stealth"}:
            setattr(user, "stealth_active", True)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="은신 돌입")
        if name == "remove_stealth":
            setattr(user, "stealth_active", False)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="은신 해제")
        if name == "backstab_stealth_check":
            if getattr(user, "stealth_active", False):
                skill = context.get("skill")
                meta = getattr(skill, "metadata", {}) if skill else {}
                # 은신 해제 + 농락 보너스
                mockery_gain = meta.get("mockery_on_stealth", args.get("mockery", 0))
                if mockery_gain:
                    for t in targets:
                        GimmickUpdater.add_mockery(user, t, int(mockery_gain))
                setattr(user, "stealth_active", False)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True)
        if name in {"try_execute_with_mockery", "try_execute"}:
            skill = context.get("skill")
            meta = getattr(skill, "metadata", {}) if skill else {}
            base_threshold = float(args.get("threshold") or meta.get("execute_threshold") or 0.0)
            if name == "try_execute_with_mockery":
                mockery_boost = meta.get("execute_threshold_mockery7")
                if targets and getattr(targets[0], "mockery_gauge", 0) >= 7 and mockery_boost:
                    base_threshold = float(mockery_boost)
            executed = False
            for t in targets:
                max_hp = getattr(t, "max_hp", 1) or 1
                if max_hp > 0 and getattr(t, "current_hp", max_hp) <= max_hp * base_threshold:
                    t.current_hp = 0
                    setattr(t, "is_alive", False)
                    executed = True
                    if meta.get("mockery_on_execute"):
                        GimmickUpdater.add_mockery(user, t, int(meta.get("mockery_on_execute", 0)))
                    event_bus.publish(Events.CHARACTER_DEATH, {"character": t, "attacker": user})
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="처형" if executed else "처형 실패")
        if name == "poison_damage_bonus":
            stacks = getattr(target, "poison_stacks", getattr(target, "poison_stage", 0)) or 0
            if stacks <= 0:
                return EffectResult(effect_type=EffectType.GIMMICK, success=True)
            skill = context.get("skill")
            meta = getattr(skill, "metadata", {}) if skill else {}
            bonus = float(meta.get("poison_bonus_damage", args.get("multiplier", args.get("bonus", 0))))
            if bonus <= 0:
                return EffectResult(effect_type=EffectType.GIMMICK, success=True)
            bonus *= max(1, stacks)
            bonus_effect = DamageEffect(
                damage_type=DamageType.HP,
                multiplier=bonus,
                stat_type="physical",
            )
            if skill:
                # 가능한 경우 원본 속성 사용
                for eff in getattr(skill, "effects", []):
                    if isinstance(eff, DamageEffect):
                        if hasattr(eff, "element"):
                            bonus_effect.element = getattr(eff, "element")
                        break
            bonus_effect.execute(user, target, context)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="독 보너스 피해")
        if name == "add_poison_stack":
            inc = _int_arg(args, "value", "amount", default=1)
            max_stack = 3
            for t in targets:
                current = getattr(t, "poison_stacks", 0)
                t.poison_stacks = min(max_stack, current + inc)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="독 중첩")
        if name == "add_mockery_all":
            amount = _int_arg(args, "value", "amount", default=0)
            all_targets = targets or _as_list(context.get("all_enemies"))
            for t in all_targets:
                GimmickUpdater.add_mockery(user, t, amount)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True, message="농락 전체 적용")
        if name == "mock_enemy":
            # 농락 게이지 증가만 처리
            amount = _int_arg(args, "value", "amount", default=1)
            for t in targets:
                GimmickUpdater.add_mockery(user, t, amount)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True)
        if name == "humiliate":
            # 농락 초기화 + 추가 보너스 정도만 처리
            for t in targets:
                GimmickUpdater.reset_mockery(t)
            return EffectResult(effect_type=EffectType.GIMMICK, success=True)

        # === 기타 ===
        if name == "steal_from_enemy":
            logger.debug("[custom_handler] steal_from_enemy 호출 - 구현 보류")
            return EffectResult(effect_type=EffectType.GIMMICK, success=True)
        if name == "grand_finale_choice":
            logger.debug("[custom_handler] grand_finale_choice 호출 - 구현 보류")
            return EffectResult(effect_type=EffectType.GIMMICK, success=True)

        logger.warning("[custom_handler] 미지원 핸들러: %s", name)
        return EffectResult(effect_type=EffectType.GIMMICK, success=True)

    except Exception as exc:
        logger.warning("[custom_handler] 처리 실패 (%s): %s", name, exc)
        return EffectResult(effect_type=EffectType.GIMMICK, success=False, message=str(exc))
