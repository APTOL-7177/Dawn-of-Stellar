"""Buff Effect - 버프 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class BuffType:
    """버프 타입"""
    # 버프 (증가)
    ATTACK_UP = "attack_up"
    DEFENSE_UP = "defense_up"
    MAGIC_UP = "magic_up"
    MAGIC_DEFENSE_UP = "magic_defense_up"  # 마법 방어력 증가
    SPIRIT_UP = "spirit_up"
    SPEED_UP = "speed_up"
    CRITICAL_UP = "critical_up"
    ACCURACY_UP = "accuracy_up"
    EVASION_UP = "evasion_up"
    LUCK = "luck"  # 행운 증가

    # 디버프 (감소)
    ATTACK_DOWN = "attack_down"
    DEFENSE_DOWN = "defense_down"
    MAGIC_DOWN = "magic_down"
    MAGIC_DEFENSE_DOWN = "magic_defense_down"  # 마법 방어력 감소
    SPIRIT_DOWN = "spirit_down"
    SPEED_DOWN = "speed_down"
    CRITICAL_DOWN = "critical_down"
    ACCURACY_DOWN = "accuracy_down"
    EVASION_DOWN = "evasion_down"

    # 특수 버프
    REGEN = "regen"  # HP 재생
    HP_REGEN = "hp_regen"  # HP 재생 (고정값)
    MP_REGEN = "mp_regen"  # MP 재생 (고정값)
    COUNTER = "counter"  # 반격
    INVINCIBLE = "invincible"  # 무적
    SKILL_SEAL = "skill_seal"  # 스킬 봉인
    CUSTOM = "custom"  # 커스텀 버프 (metadata 사용)

class BuffEffect(SkillEffect):
    """버프 효과"""
    def __init__(self, buff_type: str, value: float = None, duration: int = 3, is_party_wide: bool = False, multiplier: float = None, target: str = None, custom_stat: str = None):
        super().__init__(EffectType.BUFF)
        self.buff_type = buff_type
        # multiplier와 value 중 하나는 반드시 제공되어야 함
        if value is None and multiplier is None:
            raise ValueError("Either 'value' or 'multiplier' must be provided")
        # multiplier가 제공되면 value로 변환 (호환성)
        self.value = value if value is not None else multiplier
        self.duration = duration
        self.is_party_wide = is_party_wide
        self.target = target  # "enemy", "self", "party", "ally", "all_enemies" 등 (현재는 미사용, 향후 사용)
        self.custom_stat = custom_stat  # CUSTOM 버프 타입용

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """버프 적용"""
        # 파티 전체 버프
        if self.is_party_wide:
            targets = context.get('party_members', [target]) if context else [target]
        else:
            targets = target if isinstance(target, list) else [target]

        buffed_count = 0
        target_names = []
        for t in targets:
            if self._apply_buff(t):
                buffed_count += 1
                if hasattr(t, 'name'):
                    target_names.append(t.name)

        # ISSUE-003: 버프 메시지 개선 - 대상 명시
        buff_name = self.buff_type.replace('_', ' ').title()
        value_str = f"+{int(self.value*100)}%" if self.value >= 0 else f"{int(self.value*100)}%"

        if self.is_party_wide:
            message = f"파티 전체에 {buff_name} 적용! ({value_str}, {self.duration}턴)"
        else:
            if target_names:
                target_str = ", ".join(target_names)
                message = f"{target_str}에게 {buff_name} 적용! ({value_str}, {self.duration}턴)"
            else:
                message = f"{buff_name} 적용! ({value_str}, {self.duration}턴)"

        return EffectResult(
            effect_type=EffectType.BUFF,
            success=buffed_count > 0,
            message=message
        )
    
    def _apply_buff(self, target):
        """개별 버프 적용"""
        if not hasattr(target, 'active_buffs'):
            target.active_buffs = {}
        
        target.active_buffs[self.buff_type] = {
            'value': self.value,
            'duration': self.duration
        }
        return True
