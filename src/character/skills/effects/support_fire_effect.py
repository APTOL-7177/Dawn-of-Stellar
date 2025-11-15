"""Support Fire Effect - 지원사격 효과 (궁수 전용)"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class SupportFireEffect(SkillEffect):
    """지원사격 효과 - 조준 포인트 소비하여 자동 사격"""
    def __init__(self, max_points=3, damage_per_point=20):
        super().__init__(EffectType.GIMMICK)
        self.max_points = max_points
        self.damage_per_point = damage_per_point
    
    def execute(self, user, target, context):
        """지원사격 설정"""
        if not hasattr(user, 'support_fire_active'):
            user.support_fire_active = False
        
        # 지원사격 활성화
        user.support_fire_active = True
        user.support_fire_max_points = self.max_points
        user.support_fire_damage = self.damage_per_point
        
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'support_fire_active': True},
            message=f"지원사격 활성화 (최대 {self.max_points}포인트 소비)"
        )
