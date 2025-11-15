"""Gimmick Effect"""
from enum import Enum
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class GimmickOperation(Enum):
    ADD = "add"
    SET = "set"
    CONSUME = "consume"

class GimmickEffect(SkillEffect):
    """기믹 효과"""
    def __init__(self, operation, field, value, max_value=None):
        super().__init__(EffectType.GIMMICK)
        self.operation = operation
        self.field = field
        self.value = value
        self.max_value = max_value
    
    def can_execute(self, user, target, context) -> bool:
        return hasattr(user, self.field)
    
    def execute(self, user, target, context) -> EffectResult:
        if not hasattr(user, self.field):
            return EffectResult(effect_type=EffectType.GIMMICK, success=False)

        old_value = getattr(user, self.field, 0)
        new_value = old_value

        if self.operation == GimmickOperation.ADD:
            new_value = old_value + self.value
        elif self.operation == GimmickOperation.SET:
            new_value = self.value
        elif self.operation == GimmickOperation.CONSUME:
            new_value = old_value - self.value

        # 제한 (캐릭터의 max_{field} 속성을 우선 참조)
        max_field_name = f"max_{self.field}"
        if hasattr(user, max_field_name):
            # 캐릭터에 max_{field} 속성이 있으면 그걸 사용 (최우선)
            actual_max = getattr(user, max_field_name)
            new_value = min(new_value, actual_max)
        elif self.max_value is not None:
            # 스킬에서 지정한 max_value 사용 (fallback)
            new_value = min(new_value, self.max_value)
        new_value = max(new_value, 0)

        setattr(user, self.field, new_value)

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={self.field: new_value - old_value},
            message=f"{self.field}: {old_value} -> {new_value}"
        )
