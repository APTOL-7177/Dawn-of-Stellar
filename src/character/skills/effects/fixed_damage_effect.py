"""Fixed Damage Effect - 고정 피해 효과 (방어력 무시)"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("fixed_damage")

class FixedDamageEffect(SkillEffect):
    """고정 피해 효과 (방어력 무시)

    차원술사의 차원 폭발 등에 사용되는 고정 피해 효과.
    방어력을 무시하고 직접 HP를 감소시킵니다.
    """

    def __init__(self, base_damage=0, scaling_field=None, scaling_multiplier=1.0, target_all=False):
        """고정 피해 효과 초기화

        Args:
            base_damage: 기본 고정 피해량
            scaling_field: 스케일링 필드 (예: "refraction_stacks")
            scaling_multiplier: 스케일링 배율 (예: 0.25 = 25%)
            target_all: 전체 대상 여부
        """
        super().__init__(EffectType.DAMAGE)
        self.base_damage = base_damage
        self.scaling_field = scaling_field
        self.scaling_multiplier = scaling_multiplier
        self.target_all = target_all

    def can_execute(self, user, target, context) -> bool:
        """실행 가능 여부 체크"""
        # 스케일링 필드가 있는 경우, 해당 값이 0보다 커야 함
        if self.scaling_field:
            field_value = getattr(user, self.scaling_field, 0)
            if field_value <= 0 and self.base_damage <= 0:
                return False
        return True

    def execute(self, user, target, context) -> EffectResult:
        """고정 피해 실행

        Args:
            user: 스킬 사용자
            target: 대상 (단일 또는 리스트)
            context: 컨텍스트

        Returns:
            EffectResult
        """
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        # 타겟 리스트 처리
        targets = target if isinstance(target, list) else [target]

        for single_target in targets:
            if not single_target.is_alive:
                continue

            single_result = self._execute_single(user, single_target, context)
            result.merge(single_result)

        return result

    def _execute_single(self, user, target, context):
        """단일 타겟 고정 피해"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        # 기본 피해량
        damage = self.base_damage

        # 스케일링 필드가 있으면 계산
        if self.scaling_field:
            field_value = getattr(user, self.scaling_field, 0)
            scaling_damage = int(field_value * self.scaling_multiplier)
            damage += scaling_damage

            logger.debug(
                f"[고정 피해 스케일링] {user.name}: "
                f"{self.scaling_field}({field_value}) × {self.scaling_multiplier} = {scaling_damage}"
            )

        # 고정 피해 증폭 특성 확인 (차원술사)
        if hasattr(user, 'active_traits'):
            has_amplification = any(
                (t if isinstance(t, str) else t.get('id')) == 'fixed_damage_amplification'
                for t in user.active_traits
            )
            if has_amplification:
                damage = int(damage * 1.5)  # 고정 피해 +50%
                logger.debug(f"[고정 피해 증폭] {user.name}: {damage} (+50%)")

        # 최소 피해 1
        damage = max(1, damage)

        # 고정 피해 적용 (방어력 무시)
        if hasattr(target, 'take_fixed_damage'):
            # take_fixed_damage 메서드가 있으면 사용
            actual_damage = target.take_fixed_damage(damage)
        else:
            # 없으면 직접 HP 감소
            actual_damage = min(damage, target.current_hp)
            target.current_hp = max(0, target.current_hp - damage)

        result.hp_damage = actual_damage
        result.damage_dealt = actual_damage
        result.message = f"고정 피해 {actual_damage}!"

        logger.info(f"{user.name} → {target.name} 고정 피해: {actual_damage}")

        # 컨텍스트에 저장
        if context is not None:
            context['last_damage'] = actual_damage

        return result
