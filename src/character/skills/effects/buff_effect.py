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
        # target 파라미터 확인 ("self"면 user에게 적용)
        if self.target == "self":
            targets = [user]
        elif self.is_party_wide:
            # 파티 전체 버프: combat_manager에서 allies 가져오기
            if context:
                combat_manager = context.get('combat_manager')
                if combat_manager and hasattr(combat_manager, 'allies'):
                    # user가 allies에 속하면 allies 전체, 아니면 enemies 전체
                    if user in combat_manager.allies:
                        targets = [a for a in combat_manager.allies if getattr(a, 'is_alive', True)]
                    elif hasattr(combat_manager, 'enemies') and user in combat_manager.enemies:
                        targets = [e for e in combat_manager.enemies if getattr(e, 'is_alive', True)]
                    else:
                        targets = context.get('party_members', [target]) if context else [target]
                else:
                    targets = context.get('party_members', [target]) if context else [target]
            else:
                targets = [target] if not isinstance(target, list) else target
        else:
            targets = target if isinstance(target, list) else [target]

        buffed_count = 0
        target_names = []
        for t in targets:
            if self._apply_buff(t, user):
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
    
    def _apply_buff(self, target, user=None):
        """개별 버프 적용"""
        if not hasattr(target, 'active_buffs'):
            target.active_buffs = {}
        
        buff_data = {
            'value': self.value,
            'duration': self.duration
        }
        
        # HP_REGEN과 REGEN의 경우 시전자 스탯 정보 저장 (스탯 기반 계산용)
        # MP_REGEN은 고정값으로 유지
        if (self.buff_type == 'hp_regen' or self.buff_type == 'regen') and user:
            # 시전자의 공격력/마법력 저장
            if hasattr(user, 'stat_manager'):
                from src.character.stats import Stats
                # HP 재생은 물리 공격력 또는 마법 공격력 중 높은 값 사용
                physical_attack = user.stat_manager.get_value(Stats.STRENGTH)
                magic_attack = user.stat_manager.get_value(Stats.MAGIC)
                buff_data['stat_base'] = max(physical_attack, magic_attack)
            else:
                # StatManager가 없는 경우 기본 속성 사용
                physical_attack = getattr(user, 'physical_attack', getattr(user, 'strength', 0))
                magic_attack = getattr(user, 'magic_attack', getattr(user, 'magic', 0))
                buff_data['stat_base'] = max(physical_attack, magic_attack)
        
        target.active_buffs[self.buff_type] = buff_data
        return True
