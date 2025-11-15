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

        # 보호막 추가
        if not hasattr(target, 'shield_amount'):
            target.shield_amount = 0

        old_shield = target.shield_amount
        target.shield_amount += amount

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'shield_amount': amount},
            message=f"보호막 +{amount} (총 {target.shield_amount})"
        )
