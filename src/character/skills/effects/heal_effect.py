"""Heal Effect - 회복 효과"""
from enum import Enum
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class HealType(Enum):
    HP = "hp"
    MP = "mp"
    BRV = "brv"  # BRV 회복

class HealEffect(SkillEffect):
    """회복 효과"""
    def __init__(self, heal_type=HealType.HP, base_amount=0, percentage=0.0, stat_scaling=None, multiplier=1.0, is_party_wide=False, set_percent=None):
        super().__init__(EffectType.HEAL)
        self.heal_type = heal_type
        self.base_amount = base_amount
        self.percentage = percentage
        self.stat_scaling = stat_scaling
        self.multiplier = multiplier
        self.is_party_wide = is_party_wide
        self.set_percent = set_percent  # HP/MP를 특정 %로 설정 (회복이 아닌 설정)

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

            # set_percent가 설정된 경우 HP/MP를 특정 %로 설정
            if self.set_percent is not None:
                heal_amount = self._calculate_set_amount(t)
            else:
                heal_amount = self._calculate_heal_amount(user, t)

            # 회복 적용
            if self.heal_type == HealType.HP:
                if self.set_percent is not None:
                    # set_percent: HP를 특정 %로 직접 설정
                    if hasattr(t, 'current_hp') and hasattr(t, 'max_hp'):
                        target_hp = int(t.max_hp * self.set_percent)
                        actual_heal = target_hp - t.current_hp
                        t.current_hp = max(1, target_hp)  # 최소 1 HP 보장
                    else:
                        actual_heal = heal_amount
                elif hasattr(t, 'heal'):
                    actual_heal = t.heal(heal_amount)
                elif hasattr(t, 'current_hp') and hasattr(t, 'max_hp'):
                    actual_heal = min(heal_amount, t.max_hp - t.current_hp)
                    t.current_hp += actual_heal
                else:
                    actual_heal = heal_amount
            elif self.heal_type == HealType.MP:
                if self.set_percent is not None:
                    # set_percent: MP를 특정 %로 직접 설정
                    if hasattr(t, 'current_mp') and hasattr(t, 'max_mp'):
                        target_mp = int(t.max_mp * self.set_percent)
                        actual_heal = target_mp - t.current_mp
                        t.current_mp = max(0, target_mp)
                    else:
                        actual_heal = heal_amount
                elif hasattr(t, 'restore_mp'):
                    actual_heal = t.restore_mp(heal_amount)
                elif hasattr(t, 'current_mp') and hasattr(t, 'max_mp'):
                    actual_heal = min(heal_amount, t.max_mp - t.current_mp)
                    t.current_mp += actual_heal
                else:
                    actual_heal = heal_amount
            elif self.heal_type == HealType.BRV:
                if self.set_percent is not None:
                    # set_percent: BRV를 특정 %로 직접 설정
                    if hasattr(t, 'current_brv') and hasattr(t, 'max_brv'):
                        target_brv = int(t.max_brv * self.set_percent)
                        actual_heal = target_brv - t.current_brv
                        t.current_brv = max(0, target_brv)
                    else:
                        actual_heal = heal_amount
                else:
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
                if hasattr(user, 'stat_manager'):
                    from src.character.stats import Stats
                    stat_value = user.stat_manager.get_value(Stats.STRENGTH)
                else:
                    stat_value = getattr(user, 'physical_attack', getattr(user, 'strength', 0))
            elif self.stat_scaling == 'magic':
                if hasattr(user, 'stat_manager'):
                    from src.character.stats import Stats
                    stat_value = user.stat_manager.get_value(Stats.MAGIC)
                else:
                    stat_value = getattr(user, 'magic_attack', getattr(user, 'magic', 0))
            elif self.stat_scaling == 'max_attack':  # 물리/마법 중 높은 값
                if hasattr(user, 'stat_manager'):
                    from src.character.stats import Stats
                    physical = user.stat_manager.get_value(Stats.STRENGTH)
                    magic = user.stat_manager.get_value(Stats.MAGIC)
                    stat_value = max(physical, magic)
                else:
                    physical = getattr(user, 'physical_attack', getattr(user, 'strength', 0))
                    magic = getattr(user, 'magic_attack', getattr(user, 'magic', 0))
                    stat_value = max(physical, magic)
            elif hasattr(user, self.stat_scaling):
                stat_value = getattr(user, self.stat_scaling, 0)

            # 스탯 * 배율로 회복량 계산
            if stat_value > 0 and self.multiplier > 0:
                amount = int(stat_value * self.multiplier)

        # 2. 고정 기본량 추가
        if self.base_amount > 0:
            amount += self.base_amount

        # 3. 비율 회복 추가 (HP는 시전자 스탯 기반, MP/BRV는 대상 최대값 기반)
        if self.percentage > 0:
            if self.heal_type == HealType.HP:
                # HP 회복은 항상 시전자 스탯 기반 (물리/마법 중 높은 값)
                if hasattr(user, 'stat_manager'):
                    from src.character.stats import Stats
                    physical = user.stat_manager.get_value(Stats.STRENGTH)
                    magic = user.stat_manager.get_value(Stats.MAGIC)
                    stat_value = max(physical, magic)
                else:
                    physical = getattr(user, 'physical_attack', getattr(user, 'strength', 0))
                    magic = getattr(user, 'magic_attack', getattr(user, 'magic', 0))
                    stat_value = max(physical, magic)
                # percentage를 배율로 사용 (예: 0.3 = 30%, 0.6 = 60%, 1.1 = 110%)
                amount += int(stat_value * self.percentage)
            elif self.heal_type == HealType.MP:
                if hasattr(target, 'max_mp'):
                    amount += int(target.max_mp * self.percentage)
            elif self.heal_type == HealType.BRV:
                if hasattr(target, 'max_brv'):
                    amount += int(target.max_brv * self.percentage)

        # 회복 보너스는 가산적으로 적용 (+40%, +30%, +30% = 총 +100%)
        heal_bonus_multiplier = 1.0
        
        # 시전자의 healing_power 특성: 모든 회복 효과 +40%
        if hasattr(user, 'active_traits'):
            has_healing_power = any(
                (t if isinstance(t, str) else t.get('id')) == 'healing_power'
                for t in user.active_traits
            )
            if has_healing_power:
                heal_bonus_multiplier += 0.4

            # healing_mastery 특성: 모든 회복 효과 +30%
            has_healing_mastery = any(
                (t if isinstance(t, str) else t.get('id')) == 'healing_mastery'
                for t in user.active_traits
            )
            if has_healing_mastery:
                heal_bonus_multiplier += 0.3

        # 대상의 survival_instinct 특성: 받는 회복 효과 +30%
        if hasattr(target, 'active_traits'):
            has_survival_instinct = any(
                (t if isinstance(t, str) else t.get('id')) == 'survival_instinct'
                for t in target.active_traits
            )
            if has_survival_instinct:
                heal_bonus_multiplier += 0.3
        
        # 가산적 보너스 적용
        if heal_bonus_multiplier > 1.0:
            amount = int(amount * heal_bonus_multiplier)

        # 최소 회복량 보장
        return max(1, amount)

    def _calculate_set_amount(self, target):
        """
        HP/MP를 특정 %로 설정하기 위한 회복량 계산

        Args:
            target: 대상

        Returns:
            현재 HP/MP를 목표 %로 만들기 위한 회복량 (음수일 수 있음)
        """
        if self.heal_type == HealType.HP:
            if hasattr(target, 'max_hp') and hasattr(target, 'current_hp'):
                target_hp = int(target.max_hp * self.set_percent)
                return target_hp - target.current_hp  # 음수면 감소, 양수면 회복
        elif self.heal_type == HealType.MP:
            if hasattr(target, 'max_mp') and hasattr(target, 'current_mp'):
                target_mp = int(target.max_mp * self.set_percent)
                return target_mp - target.current_mp
        elif self.heal_type == HealType.BRV:
            if hasattr(target, 'max_brv') and hasattr(target, 'current_brv'):
                target_brv = int(target.max_brv * self.set_percent)
                return target_brv - target.current_brv

        return 0
