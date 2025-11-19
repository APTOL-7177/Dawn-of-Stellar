"""Protect Effect - 아군 보호 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class ProtectEffect(SkillEffect):
    """아군 보호 효과 (기사가 아군을 보호)"""
    def __init__(self):
        super().__init__(EffectType.GIMMICK)

    def execute(self, user, target, context):
        """보호 관계 설정"""
        # 사용자(기사)가 보호할 대상 설정
        if not hasattr(user, 'protected_allies'):
            user.protected_allies = []
        
        # 이미 보호 중인 대상이면 제거 (중복 방지)
        if target in user.protected_allies:
            user.protected_allies.remove(target)
        
        # 보호 대상 추가
        user.protected_allies.append(target)
        
        # 보호받는 대상에게도 보호자 정보 설정
        if not hasattr(target, 'protected_by'):
            target.protected_by = []
        
        if user not in target.protected_by:
            target.protected_by.append(user)
        
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'protected_ally': target.name},
            message=f"{user.name}이(가) {target.name}을(를) 보호합니다!"
        )

