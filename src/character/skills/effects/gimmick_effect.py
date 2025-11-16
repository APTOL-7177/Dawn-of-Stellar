"""Gimmick Effect"""
from enum import Enum
from typing import Any, Optional
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class GimmickOperation(Enum):
    ADD = "add"
    SET = "set"
    CONSUME = "consume"
    RELOAD_MAGAZINE = "reload_magazine"  # 저격수: 탄창 재장전
    LOAD_BULLETS = "load_bullets"  # 저격수: 특수 탄환 장전

class GimmickEffect(SkillEffect):
    """기믹 효과"""
    def __init__(self, operation, field, value, max_value=None, min_value=None, **kwargs):
        super().__init__(EffectType.GIMMICK)
        self.operation = operation
        self.field = field
        self.value = value
        self.max_value = max_value
        self.min_value = min_value
        self.extra_params = kwargs  # bullet_type 등 추가 파라미터
    
    def can_execute(self, user, target, context) -> bool:
        return hasattr(user, self.field)
    
    def execute(self, user, target, context) -> EffectResult:
        # 특수 operation 처리
        if self.operation == GimmickOperation.RELOAD_MAGAZINE:
            return self._reload_magazine(user, context)
        elif self.operation == GimmickOperation.LOAD_BULLETS:
            return self._load_bullets(user, context)

        # 기본 operation 처리
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

        # 최대값 제한
        max_field_name = f"max_{self.field}"
        if hasattr(user, max_field_name):
            actual_max = getattr(user, max_field_name)
            new_value = min(new_value, actual_max)
        elif self.max_value is not None:
            new_value = min(new_value, self.max_value)

        # 최소값 제한
        if self.min_value is not None:
            new_value = max(new_value, self.min_value)
        else:
            new_value = max(new_value, 0)

        setattr(user, self.field, new_value)

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={self.field: new_value - old_value},
            message=f"{self.field}: {old_value} -> {new_value}"
        )

    def _reload_magazine(self, user, context) -> EffectResult:
        """탄창 재장전 (저격수)"""
        if not hasattr(user, 'magazine'):
            return EffectResult(effect_type=EffectType.GIMMICK, success=False)

        bullet_type = self.extra_params.get('bullet_type', 'normal')
        amount = self.value
        max_mag = getattr(user, 'max_magazine', 6)

        # 탄창 비우고 재장전
        user.magazine = [bullet_type] * min(amount, max_mag)
        user.current_bullet_index = 0

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"탄창 재장전: {amount}발 ({bullet_type})"
        )

    def _load_bullets(self, user, context) -> EffectResult:
        """특수 탄환 장전 (저격수)"""
        if not hasattr(user, 'magazine'):
            return EffectResult(effect_type=EffectType.GIMMICK, success=False)

        bullet_type = self.extra_params.get('bullet_type', 'normal')
        amount = self.value
        max_mag = getattr(user, 'max_magazine', 6)

        # 현재 탄창에 추가
        for _ in range(amount):
            if len(user.magazine) < max_mag:
                user.magazine.append(bullet_type)

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"{bullet_type} {amount}발 장전"
        )
