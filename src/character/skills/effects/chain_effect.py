"""Chain Effect - 체인 캐스트/데미지 이펙트

chain_cast: 지정된 스킬 목록을 연속 발동 (power_ratio 배율 적용)
chain_damage: 원소 스택 기반 확률적 연쇄 폭발 데미지
"""
import random

from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("chain_effect")


class ChainCastEffect(SkillEffect):
    """체인 캐스트 이펙트 - 지정된 스킬 목록을 연속으로 발동한다.

    YAML 형식:
      - type: chain_cast
        skills:
          - skill_id: time_bolt
            power_ratio: 1.4
          - skill_id: rewind
            target: lowest_hp_ally
            power_ratio: 1.2
    """

    def __init__(self, skills: list):
        """
        Args:
            skills: 연속 발동할 스킬 목록. 각 항목은
                    {'skill_id': str, 'power_ratio': float, 'target': str(optional)} 형식.
        """
        super().__init__(EffectType.GIMMICK)
        self.skills = skills or []

    def execute(self, user, target, context):
        """체인 캐스트 실행 - SkillManager를 통해 각 스킬을 순서대로 발동한다."""
        result = EffectResult(effect_type=EffectType.GIMMICK, success=True)

        if not self.skills:
            result.message = "체인 캐스트: 발동할 스킬 없음"
            return result

        try:
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
        except Exception as exc:
            logger.warning(f"[체인캐스트] SkillManager 접근 실패: {exc}")
            result.success = False
            return result

        cast_names = []
        all_enemies = context.get('all_enemies', []) if context else []
        all_allies = context.get('all_allies', []) if context else []

        for skill_entry in self.skills:
            skill_id = skill_entry.get('skill_id') or skill_entry.get('id')
            if not skill_id:
                continue

            power_ratio = float(skill_entry.get('power_ratio', 1.0))
            target_override = skill_entry.get('target')

            # 타겟 결정
            resolved_target = self._resolve_target(
                target_override, user, target, all_enemies, all_allies
            )

            chain_context = dict(context) if context else {}
            chain_context['power_multiplier'] = power_ratio
            chain_context['skip_cost'] = True  # 체인 발동은 비용 무료

            chain_skill = skill_manager.get_skill(skill_id)
            if chain_skill is None:
                logger.warning(f"[체인캐스트] 스킬 없음: {skill_id}")
                continue

            try:
                skill_manager.execute_skill(skill_id, user, resolved_target, context=chain_context)
                cast_names.append(chain_skill.name)
                logger.info(f"[체인캐스트] {getattr(user, 'name', '?')} → {chain_skill.name} 발동 (배율 {power_ratio})")
            except Exception as exc:
                logger.warning(f"[체인캐스트] 스킬 실행 실패 ({skill_id}): {exc}")

        result.message = "체인 캐스트: " + " → ".join(cast_names) if cast_names else "체인 캐스트 (실패)"
        return result

    def _resolve_target(self, target_hint, user, original_target, all_enemies, all_allies):
        """target_hint 문자열에 따라 적절한 타겟을 결정한다."""
        if not target_hint:
            return original_target

        hint = str(target_hint).lower()

        if hint == "self":
            return user
        if hint in ("all_enemies", "all"):
            return all_enemies
        if hint == "all_allies":
            alive_allies = [a for a in all_allies if getattr(a, 'is_alive', True)]
            return alive_allies
        if hint == "lowest_hp_ally":
            alive_allies = [a for a in all_allies if getattr(a, 'is_alive', True)]
            if alive_allies:
                return min(alive_allies, key=lambda a: getattr(a, 'current_hp', 0))
            return user
        if hint == "highest_hp_enemy":
            alive_enemies = [e for e in all_enemies if getattr(e, 'is_alive', True)]
            if alive_enemies:
                return max(alive_enemies, key=lambda e: getattr(e, 'current_hp', 0))
        if hint == "random_enemy":
            alive_enemies = [e for e in all_enemies if getattr(e, 'is_alive', True)]
            if alive_enemies:
                return random.choice(alive_enemies)

        return original_target


class ChainDamageEffect(SkillEffect):
    """체인 데미지 이펙트 - 원소 스택 기반 확률적 연쇄 폭발 데미지를 입힌다.

    화염/번개 등 원소 스택이 쌓여 있을수록 연쇄 횟수가 늘어난다.
    각 연쇄마다 damage_falloff 배율이 적용되어 데미지가 줄어든다.

    YAML 형식:
      - type: chain_damage
        element: [fire, lightning]
        multiplier: 1.8
        chain_chance_per_stack: 0.2
        damage_falloff: [0.7, 0.5, 0.3, 0.2, 0.15]
        stat_base: magic
    """

    def __init__(
        self,
        elements: list,
        multiplier: float,
        chain_chance_per_stack: float,
        damage_falloff: list,
        stat_base: str = "magic",
    ):
        """
        Args:
            elements: 스택을 참조할 원소 목록 (ex: ['fire', 'lightning'])
            multiplier: 기본 데미지 배율
            chain_chance_per_stack: 스택 1개당 연쇄 추가 확률
            damage_falloff: 연쇄 단계별 데미지 배율 리스트 (1번째 연쇄, 2번째 ...)
            stat_base: 데미지 계산 기준 스탯 ("physical" | "magic")
        """
        super().__init__(EffectType.DAMAGE)
        self.elements = [str(e).lower() for e in (elements or [])]
        self.multiplier = float(multiplier)
        self.chain_chance_per_stack = float(chain_chance_per_stack)
        self.damage_falloff = damage_falloff or [0.7, 0.5, 0.3]
        self.stat_base = stat_base

    def _get_element_stacks(self, user) -> int:
        """시전자가 보유한 관련 원소 스택 합산 수를 반환한다."""
        total = 0
        for elem in self.elements:
            # ex: user.fire_stacks, user.lightning_stacks 또는 user.element_stacks['fire']
            attr_name = f"{elem}_stacks"
            total += getattr(user, attr_name, 0)
            # 딕셔너리 형태도 지원
            elem_dict = getattr(user, 'element_stacks', {})
            if isinstance(elem_dict, dict):
                total += elem_dict.get(elem, 0)
        return total

    def execute(self, user, target, context):
        """체인 데미지 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        targets = target if isinstance(target, list) else [target]
        alive_targets = [t for t in targets if getattr(t, 'is_alive', True)]
        if not alive_targets:
            result.message = "체인 데미지: 유효 타겟 없음"
            return result

        # 원소 스택 기반 최대 연쇄 횟수 및 확률 계산
        stacks = self._get_element_stacks(user)
        base_chance = stacks * self.chain_chance_per_stack
        max_chains = len(self.damage_falloff)

        # 실제 연쇄 횟수 결정 (확률 판정)
        actual_chains = 0
        for _ in range(max_chains):
            if random.random() < base_chance:
                actual_chains += 1
            else:
                break  # 실패하면 더 이상 연쇄하지 않음

        total_damage = 0

        try:
            from src.combat.damage_calculator import get_damage_calculator
            from src.combat.brave_system import get_brave_system
            calc = get_damage_calculator()
            brave = get_brave_system()
        except Exception as exc:
            logger.warning(f"[체인데미지] 시스템 접근 실패: {exc}")
            result.success = False
            return result

        # 각 대상에게 초기 타격 + 연쇄 데미지 적용
        for t in alive_targets:
            # 초기 타격
            try:
                if self.stat_base == "magic":
                    dmg_result = calc.calculate_magic_damage(user, t, self.multiplier)
                else:
                    dmg_result = calc.calculate_brv_damage(user, t, self.multiplier)

                brv_result = brave.brv_attack(user, t, dmg_result.final_damage)
                hit_damage = brv_result.get('brv_stolen', 0)
                total_damage += hit_damage
                logger.debug(f"[체인데미지] 초기 타격: {getattr(t, 'name', '?')} BRV -{hit_damage}")
            except Exception as exc:
                logger.warning(f"[체인데미지] 초기 타격 실패: {exc}")

            # 연쇄 타격
            for chain_idx in range(actual_chains):
                if not getattr(t, 'is_alive', True):
                    break
                falloff = self.damage_falloff[chain_idx] if chain_idx < len(self.damage_falloff) else 0.1
                chain_mult = self.multiplier * falloff

                try:
                    if self.stat_base == "magic":
                        chain_dmg_result = calc.calculate_magic_damage(user, t, chain_mult)
                    else:
                        chain_dmg_result = calc.calculate_brv_damage(user, t, chain_mult)

                    chain_brv = brave.brv_attack(user, t, chain_dmg_result.final_damage)
                    chain_hit = chain_brv.get('brv_stolen', 0)
                    total_damage += chain_hit
                    logger.debug(
                        f"[체인데미지] 연쇄 {chain_idx+1}: {getattr(t, 'name', '?')} BRV -{chain_hit} "
                        f"(배율 {chain_mult:.2f})"
                    )
                except Exception as exc:
                    logger.warning(f"[체인데미지] 연쇄 {chain_idx+1} 실패: {exc}")

        result.brv_damage = total_damage
        result.damage_dealt = total_damage
        result.message = f"체인 폭발 {actual_chains}연쇄! 총 BRV 데미지: {total_damage}"
        return result
