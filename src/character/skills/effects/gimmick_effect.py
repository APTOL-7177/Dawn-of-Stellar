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
    AUTO_STANCE = "auto_stance"  # 전사: 상황에 맞는 자세로 자동 전환

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
        elif self.operation == GimmickOperation.AUTO_STANCE:
            return self._auto_stance(user, context)

        # apply_to_target이 True면 target에 적용, False면 user에 적용
        entity = target if self.apply_to_target else user

        if entity is None:
            return EffectResult(effect_type=EffectType.GIMMICK, success=False, message="대상이 없습니다")

        # 기본 operation 처리
        old_value = getattr(entity, self.field, 0)
        
        # current_stance 필드의 경우 문자열을 정수로 변환
        if self.field == "current_stance" and isinstance(old_value, str):
            stance_id_to_index = {
                "balanced": 0,
                "attack": 1,
                "defense": 2,
                "berserker": 4,
                "guardian": 5,
                "speed": 6
            }
            old_value = stance_id_to_index.get(old_value, 0)
        
        new_value = old_value

        if self.operation == GimmickOperation.ADD:
            # 타입 체크
            if isinstance(old_value, (int, float)) and isinstance(self.value, (int, float)):
                new_value = old_value + self.value
            else:
                new_value = old_value
        elif self.operation == GimmickOperation.SET:
            new_value = self.value
        elif self.operation == GimmickOperation.CONSUME:
            # 타입 체크
            if isinstance(old_value, (int, float)) and isinstance(self.value, (int, float)):
                new_value = old_value - self.value
            else:
                new_value = old_value

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
        
        # gimmick_changes 계산 (타입 안전하게)
        if isinstance(new_value, (int, float)) and isinstance(old_value, (int, float)):
            change_value = new_value - old_value
        else:
            change_value = 0
        
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={self.field: change_value},
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
    
    def _auto_stance(self, user, context) -> EffectResult:
        """상황에 맞는 자세로 자동 전환 (전사)"""
        if not hasattr(user, 'gimmick_type') or user.gimmick_type != "stance_system":
            return EffectResult(effect_type=EffectType.GIMMICK, success=False, message="스탠스 시스템이 없습니다")
        
        # 현재 상태 확인
        current_hp_ratio = getattr(user, 'current_hp', 0) / max(getattr(user, 'max_hp', 1), 1)
        current_mp_ratio = getattr(user, 'current_mp', 0) / max(getattr(user, 'max_mp', 1), 1)
        
        # 적 정보 확인 (context에서 가져오기)
        enemies = context.get('enemies', [])
        allies = context.get('allies', [])
        
        # 상황 판단 로직
        selected_stance = 0  # 기본: 중립
        
        # 1. HP가 30% 이하이면 수호자 자세 (재생)
        if current_hp_ratio <= 0.3:
            selected_stance = 5  # guardian
        # 2. MP가 부족하면 중립 자세 (효과 없음)
        elif current_mp_ratio <= 0.2:
            selected_stance = 0  # balanced
        # 3. 적이 많거나 강하면 방어 자세
        elif len(enemies) >= 3 or (enemies and any(getattr(e, 'current_hp', 0) > getattr(user, 'max_hp', 0) * 1.5 for e in enemies)):
            selected_stance = 2  # defense
        # 4. 아군이 위험하면 수호자 자세
        elif allies and any(getattr(a, 'current_hp', 0) / max(getattr(a, 'max_hp', 1), 1) <= 0.3 for a in allies if a != user):
            selected_stance = 5  # guardian
        # 5. HP가 충분하고(50% 이상) 적이 강하면 광전사 자세 (극한 공격)
        elif current_hp_ratio >= 0.5 and enemies and any(getattr(e, 'current_hp', 0) > getattr(user, 'max_hp', 0) * 1.2 for e in enemies):
            selected_stance = 4  # berserker
        # 6. 적이 약하거나 적이 적으면 공격 자세
        elif len(enemies) <= 1 or (enemies and all(getattr(e, 'current_hp', 0) < getattr(user, 'max_hp', 0) * 0.8 for e in enemies)):
            selected_stance = 1  # attack
        # 7. 아군이 공격 준비가 안 되어 있거나 적이 빠르면 속도 자세
        elif (allies and any(not hasattr(a, 'atb_value') or getattr(a, 'atb_value', 0) < 30 for a in allies if a != user)) or \
             (enemies and any(hasattr(e, 'speed') and getattr(e, 'speed', 0) > getattr(user, 'speed', 0) * 1.2 for e in enemies)):
            selected_stance = 6  # speed
        # 8. 그 외에는 중립 자세
        else:
            selected_stance = 0  # balanced
        
        # 스탠스 이름 매핑
        stance_names = {
            0: "중립",
            1: "공격",
            2: "방어",
            4: "광전사",
            5: "수호자",
            6: "신속"
        }
        
        old_stance = getattr(user, 'current_stance', 0)
        user.current_stance = selected_stance
        
        # 스탠스 효과 재적용
        from src.character.gimmick_updater import GimmickUpdater
        GimmickUpdater._apply_stance_effects(user)
        
        stance_name = stance_names.get(selected_stance, "알 수 없음")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={"current_stance": selected_stance - (old_stance if isinstance(old_stance, int) else 0)},
            message=f"적응형 전환: {stance_name} 자세"
        )
