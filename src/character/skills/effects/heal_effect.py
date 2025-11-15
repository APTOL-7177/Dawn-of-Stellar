"""Heal Effect - 회복 효과"""
from enum import Enum
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class HealType(Enum):
    HP = "hp"
    MP = "mp"

class HealEffect(SkillEffect):
    """회복 효과"""
    def __init__(self, heal_type=HealType.HP, base_amount=0, percentage=0.0, stat_scaling=None, multiplier=1.0, is_party_wide=False):
        super().__init__(EffectType.HEAL)
        self.heal_type = heal_type
        self.base_amount = base_amount
        self.percentage = percentage
        self.stat_scaling = stat_scaling
        self.multiplier = multiplier
        self.is_party_wide = is_party_wide

    def execute(self, user, target, context):
        """회복 실행"""
        # 파티 전체 힐
        if self.is_party_wide:
            targets = context.get('party_members', [target]) if context else [target]
        else:
            targets = target if isinstance(target, list) else [target]

        total_heal = 0
        healed_count = 0

        for t in targets:
            heal_amount = self._calculate_heal_amount(user, t)

            # 회복 적용
            if self.heal_type == HealType.HP:
                actual_heal = t.heal(heal_amount)
            else:
                actual_heal = t.restore_mp(heal_amount)

            total_heal += actual_heal
            healed_count += 1

        if self.is_party_wide:
            message = f"파티 {healed_count}명 {self.heal_type.value.upper()} 회복 {total_heal}"
        else:
            message = f"{self.heal_type.value.upper()} 회복 {total_heal}"

        return EffectResult(
            effect_type=EffectType.HEAL,
            success=True,
            heal_amount=total_heal,
            message=message
        )

    def _calculate_heal_amount(self, user, target):
        """회복량 계산"""
        amount = self.base_amount

        # 스탯 스케일링
        if self.stat_scaling and hasattr(user, self.stat_scaling):
            stat_value = getattr(user, self.stat_scaling, 0)
            amount += int(stat_value * self.multiplier)

        # 비율 회복
        if self.percentage > 0:
            if self.heal_type == HealType.HP:
                amount += int(target.max_hp * self.percentage)
            elif self.heal_type == HealType.MP:
                amount += int(target.max_mp * self.percentage)

        return amount
