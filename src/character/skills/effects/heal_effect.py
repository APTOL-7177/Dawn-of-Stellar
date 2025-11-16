"""Heal Effect - 회복 효과"""
from enum import Enum
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class HealType(Enum):
    HP = "hp"
    MP = "mp"
    BRV = "brv"  # BRV 회복

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
            # context에서 party_members를 가져오거나, combat_manager에서 가져오기
            if context and 'party_members' in context:
                targets = context['party_members']
            elif context and 'combat_manager' in context:
                # combat_manager가 있으면 allies를 사용
                combat_manager = context['combat_manager']
                if hasattr(combat_manager, 'allies'):
                    # user가 allies에 속하면 allies를, enemies에 속하면 enemies를 사용
                    if hasattr(combat_manager, 'allies') and user in combat_manager.allies:
                        targets = [a for a in combat_manager.allies if getattr(a, 'is_alive', True)]
                    elif hasattr(combat_manager, 'enemies') and user in combat_manager.enemies:
                        targets = [e for e in combat_manager.enemies if getattr(e, 'is_alive', True)]
                    else:
                        targets = [target] if not isinstance(target, list) else target
                else:
                    targets = [target] if not isinstance(target, list) else target
            else:
                targets = [target] if not isinstance(target, list) else target
        else:
            targets = target if isinstance(target, list) else [target]

        total_heal = 0
        healed_count = 0

        for t in targets:
            # 죽은 대상은 스킵 (부활 스킬이 아닌 경우)
            if not getattr(t, 'is_alive', True):
                continue

            heal_amount = self._calculate_heal_amount(user, t)

            # 회복 적용
            if self.heal_type == HealType.HP:
                if hasattr(t, 'heal'):
                    actual_heal = t.heal(heal_amount)
                elif hasattr(t, 'current_hp') and hasattr(t, 'max_hp'):
                    actual_heal = min(heal_amount, t.max_hp - t.current_hp)
                    t.current_hp += actual_heal
                else:
                    actual_heal = heal_amount
            elif self.heal_type == HealType.MP:
                if hasattr(t, 'restore_mp'):
                    actual_heal = t.restore_mp(heal_amount)
                elif hasattr(t, 'current_mp') and hasattr(t, 'max_mp'):
                    actual_heal = min(heal_amount, t.max_mp - t.current_mp)
                    t.current_mp += actual_heal
                else:
                    actual_heal = heal_amount
            elif self.heal_type == HealType.BRV:
                # BRV 회복
                if hasattr(t, 'current_brv') and hasattr(t, 'max_brv'):
                    actual_heal = min(heal_amount, t.max_brv - t.current_brv)
                    t.current_brv += actual_heal
                else:
                    actual_heal = heal_amount
            else:
                actual_heal = heal_amount

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
        """
        회복량 계산 (스탯 기반)

        우선순위:
        1. 스탯 스케일링 (stat_scaling + multiplier) - 주 회복량
        2. 고정 기본량 (base_amount)
        3. 비율 회복 (percentage) - 추가 회복량

        Args:
            user: 시전자
            target: 대상

        Returns:
            계산된 회복량
        """
        amount = 0

        # 1. 스탯 기반 회복 (주 회복량)
        if self.stat_scaling:
            stat_value = 0

            # stat_scaling 이름에 따라 스탯 값 가져오기
            if self.stat_scaling == 'strength':
                stat_value = getattr(user, 'physical_attack', 0)
            elif self.stat_scaling == 'magic':
                stat_value = getattr(user, 'magic_attack', 0)
            elif hasattr(user, self.stat_scaling):
                stat_value = getattr(user, self.stat_scaling, 0)

            # 스탯 * 배율로 회복량 계산
            if stat_value > 0 and self.multiplier > 0:
                amount = int(stat_value * self.multiplier)

        # 2. 고정 기본량 추가
        if self.base_amount > 0:
            amount += self.base_amount

        # 3. 비율 회복 추가 (대상의 최대 HP/MP/BRV 기준)
        if self.percentage > 0:
            if self.heal_type == HealType.HP:
                if hasattr(target, 'max_hp'):
                    amount += int(target.max_hp * self.percentage)
            elif self.heal_type == HealType.MP:
                if hasattr(target, 'max_mp'):
                    amount += int(target.max_mp * self.percentage)
            elif self.heal_type == HealType.BRV:
                if hasattr(target, 'max_brv'):
                    amount += int(target.max_brv * self.percentage)

        # 최소 회복량 보장
        return max(1, amount)
