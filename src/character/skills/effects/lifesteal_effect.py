"""Lifesteal Effect - 흡혈 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class LifestealEffect(SkillEffect):
    """흡혈 효과 - 가한 데미지의 일부를 회복"""
    def __init__(self, lifesteal_percent=0.3, low_hp_bonus=True):
        super().__init__(EffectType.HEAL)
        self.lifesteal_percent = lifesteal_percent
        self.low_hp_bonus = low_hp_bonus
    
    def execute(self, user, target, context):
        """흡혈 실행 - context에서 데미지 정보 가져오기"""
        # 이전 효과에서 가한 데미지 확인
        damage_dealt = context.get('last_damage', 0)
        
        if damage_dealt <= 0:
            return EffectResult(
                effect_type=EffectType.HEAL,
                success=False,
                message="흡혈 실패 (데미지 없음)"
            )
        
        # 흡혈량 계산
        lifesteal_amount = int(damage_dealt * self.lifesteal_percent)
        
        # HP가 낮을수록 흡혈 증가
        if self.low_hp_bonus:
            hp_percent = user.current_hp / user.max_hp
            if hp_percent < 0.3:
                lifesteal_amount = int(lifesteal_amount * 2.0)
            elif hp_percent < 0.5:
                lifesteal_amount = int(lifesteal_amount * 1.5)

        # 특성 보너스 적용
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()
        
        # 추가 흡혈율 (flat addition)
        # Note: calculate_lifesteal returns a rate (e.g. 0.10) to be added to base rate?
        # Or does it return a percentage of max HP?
        # Based on TraitEffectType.LIFESTEAL description "생명력 흡수율 (0.10 = 10%)", it seems to be a rate.
        # But here we are calculating amount based on damage.
        # So we should add the rate to the base percent.
        
        bonus_rate = trait_manager.calculate_lifesteal(user)
        if bonus_rate > 0:
            # Add bonus rate to the base amount calculation
            # lifesteal_amount was calculated with self.lifesteal_percent
            # We add damage_dealt * bonus_rate
            lifesteal_amount += int(damage_dealt * bonus_rate)

        # 흡혈 배율 (multiplier)
        multiplier = trait_manager.calculate_lifesteal_multiplier(user)
        if multiplier != 1.0:
            lifesteal_amount = int(lifesteal_amount * multiplier)
        
        # 회복 적용
        actual_heal = user.heal(lifesteal_amount)
        
        # Vitality Overflow: 최대 체력 시 초과 회복량을 BRV로 전환
        # Check if user has 'vitality_overflow' trait
        has_overflow = False
        if hasattr(user, 'active_traits') and 'vitality_overflow' in user.active_traits:
            has_overflow = True
        elif hasattr(user, 'system_traits') and 'vitality_overflow' in user.system_traits:
            has_overflow = True
            
        if has_overflow:
            # Calculate overheal
            overheal = lifesteal_amount - actual_heal
            if overheal > 0:
                # Convert overheal to BRV (100% efficiency? or 50%? Let's do 100% as per trait desc "전환")
                # But BRV usually has a cap (Max BRV).
                if hasattr(user, 'current_brv') and hasattr(user, 'max_brv'):
                    old_brv = user.current_brv
                    user.current_brv = min(user.current_brv + overheal, user.max_brv)
                    brv_gain = user.current_brv - old_brv
                    if brv_gain > 0:
                        return EffectResult(
                            effect_type=EffectType.HEAL,
                            success=True,
                            heal_amount=actual_heal,
                            message=f"흡혈 회복 {actual_heal}, BRV 전환 +{brv_gain}"
                        )

        return EffectResult(
            effect_type=EffectType.HEAL,
            success=True,
            heal_amount=actual_heal,
            message=f"흡혈 회복 {actual_heal}"
        )
