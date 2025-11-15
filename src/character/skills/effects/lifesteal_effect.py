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
        
        # 회복 적용
        actual_heal = user.heal(lifesteal_amount)
        
        return EffectResult(
            effect_type=EffectType.HEAL,
            success=True,
            heal_amount=actual_heal,
            message=f"흡혈 회복 {actual_heal}"
        )
