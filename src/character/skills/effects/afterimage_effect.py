"""Afterimage Effect - 잔상 시스템 이펙트

consume_afterimage: 잔상 소비 (afterimage_count 감소)
afterimage_scaling: 잔상 수에 비례한 스케일링
charge_afterimage: 잔상 충전 (afterimage_count 증가)
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("afterimage_effect")


class ConsumeAfterimageEffect(SkillEffect):
    """잔상 소비 - afterimage_count를 감소시킨다.

    YAML 형식:
      - type: consume_afterimage
        amount: all  # "all" 또는 숫자
    """

    def __init__(self, amount=1):
        super().__init__(EffectType.GIMMICK)
        self.amount = amount  # "all" 또는 int

    def execute(self, user, target, context) -> EffectResult:
        current = getattr(user, 'afterimage_count', 0)

        if self.amount == "all" or self.amount == 0:
            consumed = current
            user.afterimage_count = 0
        else:
            consumed = min(int(self.amount), current)
            user.afterimage_count = max(0, current - consumed)

        # context에 소비량 기록 (후속 이펙트에서 참조)
        if context is not None:
            context['afterimages_consumed'] = context.get('afterimages_consumed', 0) + consumed

        logger.info(f"[잔상 소비] {getattr(user, 'name', '?')} 잔상 -{consumed} (잔여: {getattr(user, 'afterimage_count', 0)})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'afterimage_count': -consumed},
            message=f"잔상 소비 -{consumed}"
        )


class AfterimageScalingEffect(SkillEffect):
    """잔상 스케일링 - 소비된 잔상 수에 비례하여 데미지 배율을 증가시킨다.

    YAML 형식:
      - type: afterimage_scaling
        bonus_per_afterimage: 0.01  # 잔상당 배율 증가
    """

    def __init__(self, bonus_per_afterimage: float = 0.01):
        super().__init__(EffectType.GIMMICK)
        self.bonus_per_afterimage = bonus_per_afterimage

    def execute(self, user, target, context) -> EffectResult:
        # context에서 소비된 잔상 수 가져오기
        consumed = 0
        if context:
            consumed = context.get('afterimages_consumed', 0)

        # 소비된 잔상이 없으면 현재 잔상 수 사용
        if consumed <= 0:
            consumed = getattr(user, 'afterimage_count', 0)

        bonus = consumed * self.bonus_per_afterimage

        if bonus > 0 and context is not None:
            current_mult = context.get('power_multiplier', 1.0)
            context['power_multiplier'] = current_mult + bonus

        logger.info(f"[잔상 스케일링] 데미지 +{bonus*100:.1f}% (잔상 {consumed}개)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"잔상 스케일링: +{bonus*100:.1f}%"
        )


class ChargeAfterimageEffect(SkillEffect):
    """잔상 충전 - afterimage_count를 증가시킨다.

    YAML 형식:
      - type: charge_afterimage
        value: 35  # 충전량
    """

    def __init__(self, value: int = 1):
        super().__init__(EffectType.GIMMICK)
        self.value = value

    def execute(self, user, target, context) -> EffectResult:
        current = getattr(user, 'afterimage_count', 0)
        max_afterimage = getattr(user, 'max_afterimage_count', 100)
        new_value = min(current + self.value, max_afterimage)
        added = new_value - current
        user.afterimage_count = new_value

        logger.info(f"[잔상 충전] {getattr(user, 'name', '?')} 잔상 +{added} (현재: {new_value})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'afterimage_count': added},
            message=f"잔상 충전 +{added} (현재: {new_value})"
        )
