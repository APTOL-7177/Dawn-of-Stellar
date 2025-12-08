"""Protect Effect - 아군 보호 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class ProtectEffect(SkillEffect):
    """아군 보호 효과 (기사가 아군을 보호)"""
    def __init__(self, duration: int = 2, redirect_ratio: float = 1.0, shield_percent: float = 0.0, damage_reduction: float = 0.0):
        super().__init__(EffectType.BUFF)
        self.duration = duration
        self.redirect_ratio = redirect_ratio
        self.shield_percent = shield_percent
        self.damage_reduction = damage_reduction

    def execute(self, user, target, context):
        """보호 관계 설정 - 한 번에 하나의 아군만 보호"""
        # 사용자(기사)가 보호할 대상 설정
        if not hasattr(user, 'protected_allies'):
            user.protected_allies = []

        # 기존 보호 관계 해제 (한 번에 하나의 아군만 보호)
        for old_record in user.protected_allies[:]:
            old_target = old_record['target']
            if old_target != target:
                # 기존 보호 대상에서 사용자 제거
                if hasattr(old_target, 'protected_by'):
                    old_target.protected_by = [p for p in old_target.protected_by if p['protector'] != user]
                # 사용자 보호 목록에서 제거
                user.protected_allies.remove(old_record)

        # 이미 보호 중인 대상이면 제거 (갱신을 위해)
        user.protected_allies = [r for r in user.protected_allies if r['target'] != target]
        if hasattr(target, 'protected_by'):
            target.protected_by = [p for p in target.protected_by if p['protector'] != user]

        # 보호 정보 생성
        protection_info = {
            'protector': user,
            'target': target,
            'duration': self.duration,
            'redirect_ratio': self.redirect_ratio,
            'shield_percent': self.shield_percent,
            'damage_reduction': self.damage_reduction
        }

        # 보호 대상 추가
        user.protected_allies.append(protection_info)

        # 보호받는 대상에게도 보호자 정보 설정
        if not hasattr(target, 'protected_by'):
            target.protected_by = []

        target.protected_by.append(protection_info)
        
        # StatusEffect로 지속 시간 관리 (ProtectionStatus)
        # StatusManager의 cleanup 로직(GUARDIAN)과 연동되어 만료 시 protected_by를 정리함
        from src.combat.status_effects import StatusEffect, StatusType
        
        guardian_status = StatusEffect(
            name="수호",
            status_type=StatusType.GUARDIAN,
            duration=self.duration,
            intensity=1.0,
            metadata={'protector': user}
        )
        
        if hasattr(target, 'status_manager'):
            target.status_manager.add_status(guardian_status)
        
        return EffectResult(
            effect_type=EffectType.BUFF,
            success=True,
            gimmick_changes={'protected_ally': target.name},
            message=f"{user.name}이(가) {target.name}을(를) 보호합니다! (피해 {int(self.damage_reduction*100)}% 감소/대신 받음)"
        )

