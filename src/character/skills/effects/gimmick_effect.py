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
    def __init__(self, operation, field, value, max_value=None, min_value=None, apply_to_target=False, **kwargs):
        super().__init__(EffectType.GIMMICK)
        self.operation = operation
        self.field = field
        self.value = value
        self.max_value = max_value
        self.min_value = min_value
        self.apply_to_target = apply_to_target  # True면 target에 적용, False면 user에 적용
        self.extra_params = kwargs  # bullet_type 등 추가 파라미터
    
    def can_execute(self, user, target, context) -> bool:
        # apply_to_target이 True면 target을 확인, False면 user를 확인
        check_entity = target if self.apply_to_target else user
        return check_entity is not None

    def execute(self, user, target, context) -> EffectResult:
        # 특수 operation 처리 (항상 user에 적용)
        if self.operation == GimmickOperation.RELOAD_MAGAZINE:
            return self._reload_magazine(user, context)
        elif self.operation == GimmickOperation.LOAD_BULLETS:
            return self._load_bullets(user, context)

        # apply_to_target이 True면 target에 적용, False면 user에 적용
        entity = target if self.apply_to_target else user

        if entity is None:
            return EffectResult(effect_type=EffectType.GIMMICK, success=False, message="대상이 없습니다")

        # 기본 operation 처리
        old_value = getattr(entity, self.field, 0)
        new_value = old_value

        if self.operation == GimmickOperation.ADD:
            new_value = old_value + self.value
        elif self.operation == GimmickOperation.SET:
            new_value = self.value
        elif self.operation == GimmickOperation.CONSUME:
            new_value = old_value - self.value

        # 최대값 제한
        max_field_name = f"max_{self.field}"
        if hasattr(entity, max_field_name):
            actual_max = getattr(entity, max_field_name)
            new_value = min(new_value, actual_max)
        elif self.max_value is not None:
            new_value = min(new_value, self.max_value)

        # 최소값 제한
        if self.min_value is not None:
            new_value = max(new_value, self.min_value)
        else:
            new_value = max(new_value, 0)

        setattr(entity, self.field, new_value)

        # 해커 멀티스레드 시스템: program_* 변수 변경 시 active_threads 자동 업데이트
        if hasattr(entity, 'gimmick_type') and entity.gimmick_type == "multithread_system":
            if self.field.startswith("program_"):
                program_name = self.field.replace("program_", "")  # "program_virus" -> "virus"

                # active_threads 리스트 초기화 (없으면)
                if not hasattr(entity, 'active_threads'):
                    entity.active_threads = []

                # 정수 타입이면 리스트로 변환 (하위 호환성)
                if isinstance(entity.active_threads, int):
                    entity.active_threads = []

                # 프로그램 활성화 (new_value > 0)
                if new_value > 0 and old_value == 0:
                    if program_name not in entity.active_threads:
                        entity.active_threads.append(program_name)

                # 프로그램 비활성화 (new_value == 0)
                elif new_value == 0 and old_value > 0:
                    if program_name in entity.active_threads:
                        entity.active_threads.remove(program_name)

        entity_name = getattr(entity, 'name', '대상')
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={self.field: new_value - old_value},
            message=f"{entity_name}의 {self.field}: {old_value} -> {new_value}"
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
