"""Shield Effect - 보호막 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class ShieldEffect(SkillEffect):
    """보호막 효과"""
    def __init__(self, base_amount=0, hp_consumed_multiplier=0.0, multiplier=0.0, stat_name=None):
        super().__init__(EffectType.GIMMICK)
        self.base_amount = base_amount
        self.hp_consumed_multiplier = hp_consumed_multiplier
        self.multiplier = multiplier
        self.stat_name = stat_name

    def execute(self, user, target, context):
        """보호막 생성"""
        amount = self.base_amount

        # HP 소비 기반 보호막
        if self.hp_consumed_multiplier > 0 and context and 'hp_consumed' in context:
            hp_consumed = context['hp_consumed']
            amount += int(hp_consumed * self.hp_consumed_multiplier)

        # 스탯/기믹 기반 보호막 (예: holy_power)
        if self.stat_name and hasattr(user, self.stat_name):
            stat_value = getattr(user, self.stat_name, 0)
            amount += int(stat_value * self.multiplier * 10)  # 성력당 보호막 배수

        # 공격력 기반 보호막 (수호의 맹세 등)
        # context에서 'attack_multiplier'가 있으면 공격력의 해당 비율만큼 보호막 추가
        if context and 'attack_multiplier' in context:
            attack_multiplier = context['attack_multiplier']
            # physical_attack 또는 strength 속성 사용
            if hasattr(user, 'physical_attack'):
                attack = user.physical_attack
            elif hasattr(user, 'strength'):
                attack = user.strength
            else:
                attack = 0
            amount += int(attack * attack_multiplier)

        # 보호막 추가 (수호의 맹세는 본인에게 보호막을 두름)
        # context에서 'protect_self'가 True이면 user에게, 아니면 target에게
        shield_target = user if context and context.get('protect_self', False) else target
        
        if not hasattr(shield_target, 'shield_amount'):
            shield_target.shield_amount = 0

        old_shield = shield_target.shield_amount
        
        # 중첩 방지: context에서 'replace_shield'가 True이면 기존 보호막을 덮어씀
        if context and context.get('replace_shield', False):
            shield_target.shield_amount = amount
            message = f"보호막 {amount} (기존 보호막 대체)"
        else:
            shield_target.shield_amount += amount
            message = f"보호막 +{amount} (총 {shield_target.shield_amount})"

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'shield_amount': amount},
            message=message
        )
