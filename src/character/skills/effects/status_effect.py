"""Status Effect - 상태 이상 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType


class StatusType:
    """상태 이상 타입"""
    # 디버프
    POISON = "poison"
    BURN = "burn"
    FREEZE = "freeze"
    STUN = "stun"
    SLEEP = "sleep"
    SILENCE = "silence"
    BLIND = "blind"
    SLOW = "slow"
    CURSE = "curse"
    WEAKEN = "weaken"
    DEFENSE_DOWN = "defense_down"
    ATTACK_DOWN = "attack_down"

    # 팀워크 스킬용 특수 상태
    STEALTH = "stealth"  # 은신
    HP_RECOVERY_BLOCK = "hp_recovery_block"  # HP 회복 불가
    CURSE_MARK = "curse_mark"  # 저주 낙인

    # 특수 마크
    RUNE = "rune"  # 룬 각인
    MARK = "mark"  # 표식
    DOOM = "doom"  # 죽음의 선고

    # 버프
    HASTE = "haste"
    REGEN = "regen"
    BARRIER = "barrier"
    BLESSING = "blessing"
    STRENGTHEN = "strengthen"
    DEFENSE_UP = "defense_up"
    ATTACK_UP = "attack_up"


class StatusEffectData:
    """상태 효과 데이터"""
    def __init__(self, name: str, duration: int, value: float = 0):
        self.name = name
        self.duration = duration  # 남은 턴 수
        self.value = value  # 효과 강도 (선택적)


class StatusEffect(SkillEffect):
    """상태 이상 효과"""
    def __init__(
        self,
        status_type: str,
        duration: int = 3,
        value: float = 0,
        stackable: bool = False,
        remove: bool = False,
        damage_stat: str = None,
        damage_multiplier: float = 0,
        cannot_resist: bool = False
    ):
        super().__init__(EffectType.BUFF)  # 기존 BUFF 타입 재사용
        self.status_type = status_type
        self.duration = duration
        self.value = value
        self.stackable = stackable  # 스택 가능 여부
        self.remove = remove  # True면 상태 제거
        self.damage_stat = damage_stat  # DoT 데미지 계산에 사용할 스탯
        self.damage_multiplier = damage_multiplier  # DoT 데미지 배율
        self.cannot_resist = cannot_resist  # 저항 불가 여부

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """상태 이상 적용 또는 제거"""
        targets = target if isinstance(target, list) else [target]

        affected_count = 0
        for t in targets:
            if self.remove:
                if self._remove_status(t):
                    affected_count += 1
            else:
                # user를 전달하여 스탯 기반 DoT 계산
                if self._apply_status(t, user):
                    affected_count += 1

        status_name = self.status_type.replace('_', ' ').title()
        if self.remove:
            message = f"{status_name} 제거!"
        else:
            message = f"{status_name} 적용! ({self.duration}턴)"

        return EffectResult(
            effect_type=EffectType.BUFF,
            success=affected_count > 0,
            message=message
        )

    def _apply_status(self, target, user=None):
        """개별 상태 이상 적용"""
        # StatusManager가 있으면 사용 (신규 시스템)
        if hasattr(target, 'status_manager'):
            from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType

            # status_type 문자열을 StatusType Enum으로 변환
            status_type_map = {
                'poison': StatusType.POISON,
                'burn': StatusType.BURN,
                'bleed': StatusType.BLEED,
                'corrode': StatusType.CORROSION,
                'corrosion': StatusType.CORROSION,
                'disease': StatusType.DISEASE,
                'necrosis': StatusType.NECROSIS,
                'chill': StatusType.CHILL,
                'shock': StatusType.SHOCK,
                'stun': StatusType.STUN,
                'sleep': StatusType.SLEEP,
                'silence': StatusType.SILENCE,
                'blind': StatusType.BLIND,
                'paralyze': StatusType.PARALYZE,
                'freeze': StatusType.FREEZE,
                'slow': StatusType.SLOW,
                'haste': StatusType.HASTE,
                'regen': StatusType.REGENERATION,
                'regeneration': StatusType.REGENERATION,
                'stealth': StatusType.STEALTH,
                'hp_recovery_block': StatusType.HP_RECOVERY_BLOCK,
                'curse_mark': StatusType.CURSE_MARK,
            }

            status_enum = status_type_map.get(self.status_type.lower())
            if not status_enum:
                # 알 수 없는 상태면 레거시 시스템 사용
                return self._apply_status_legacy(target)

            # DoT의 경우 base_damage 계산 (스탯 기반)
            base_damage = 0
            if self.damage_stat and self.damage_multiplier and user:
                # user의 스탯 가져오기
                stat_value = 0
                if self.damage_stat == 'magic':
                    stat_value = getattr(user, 'magic_attack', 0)
                elif self.damage_stat == 'strength':
                    stat_value = getattr(user, 'physical_attack', 0)
                elif hasattr(user, self.damage_stat):
                    stat_value = getattr(user, self.damage_stat, 0)

                # base_damage = 스탯 * 배율
                base_damage = int(stat_value * self.damage_multiplier)

            # 강력한 상태이상은 최대 2턴으로 제한
            duration = self.duration
            if status_enum in [StatusType.STUN, StatusType.SLEEP, StatusType.FREEZE,
                              StatusType.PARALYZE, StatusType.PETRIFY, StatusType.TIME_STOP,
                              StatusType.SILENCE]:
                duration = min(duration, 2)  # 최대 2턴
            
            # StatusEffect 객체 생성
            status_effect = CombatStatusEffect(
                name=self.status_type.replace('_', ' ').title(),
                status_type=status_enum,
                duration=duration,
                intensity=self.value if self.value > 0 else 1.0,
                is_stackable=self.stackable,
                max_stacks=5 if self.stackable else 1,
                source_id=getattr(user, 'name', None) if user else None,
                metadata={"base_damage": base_damage} if base_damage > 0 else {}
            )

            # StatusManager에 추가
            target.status_manager.add_status(status_effect, allow_refresh=True)
            return True

        # 레거시 시스템 사용
        return self._apply_status_legacy(target)

    def _apply_status_legacy(self, target):
        """레거시 상태 효과 시스템"""
        # status_effects가 리스트인 경우
        if not hasattr(target, 'status_effects'):
            target.status_effects = []

        # 이미 같은 상태가 있는지 확인
        if isinstance(target.status_effects, list):
            # 스택 불가능하면 기존 상태 제거
            if not self.stackable:
                target.status_effects = [e for e in target.status_effects
                                        if not (hasattr(e, 'name') and e.name == self.status_type)]

            # 새 상태 추가
            status_data = StatusEffectData(self.status_type, self.duration, self.value)
            target.status_effects.append(status_data)

        # 딕셔너리인 경우
        elif isinstance(target.status_effects, dict):
            if self.stackable and self.status_type in target.status_effects:
                # 스택 가능하면 턴 수 갱신
                target.status_effects[self.status_type] = max(
                    target.status_effects[self.status_type],
                    self.duration
                )
            else:
                target.status_effects[self.status_type] = self.duration

        return True

    def _remove_status(self, target):
        """개별 상태 이상 제거"""
        if not hasattr(target, 'status_effects'):
            return False

        removed = False

        # 리스트인 경우
        if isinstance(target.status_effects, list):
            original_len = len(target.status_effects)
            target.status_effects = [e for e in target.status_effects
                                    if not (hasattr(e, 'name') and e.name == self.status_type)]
            removed = len(target.status_effects) < original_len

        # 딕셔너리인 경우
        elif isinstance(target.status_effects, dict):
            if self.status_type in target.status_effects:
                del target.status_effects[self.status_type]
                removed = True

        return removed
