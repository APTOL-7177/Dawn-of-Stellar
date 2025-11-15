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
    def __init__(self, status_type: str, duration: int = 3, value: float = 0, stackable: bool = False, remove: bool = False):
        super().__init__(EffectType.BUFF)  # 기존 BUFF 타입 재사용
        self.status_type = status_type
        self.duration = duration
        self.value = value
        self.stackable = stackable  # 스택 가능 여부
        self.remove = remove  # True면 상태 제거

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
                if self._apply_status(t):
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

    def _apply_status(self, target):
        """개별 상태 이상 적용"""
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
