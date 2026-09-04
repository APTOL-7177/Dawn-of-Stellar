"""Utility Effect - 유틸리티/슬롯 시스템 이펙트

clear_slots: 기믹 슬롯 초기화
gain_gimmick: 기믹 게이지 획득
consume_gimmick: 기믹 게이지 소비
convergence_bonus: 수렴 보너스 (스택 비례 데미지 증가)
shield_damage: 쉴드 대상 추가 데미지
area_damage: 범위 데미지 (AOE)
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("utility_effect")


class ClearSlotsEffect(SkillEffect):
    """기믹 슬롯 초기화 - 가능성 슬롯을 모두 비운다.

    YAML 형식:
      - type: clear_slots
        after_cast: true  # 시전 후 슬롯 초기화
    """

    def __init__(self, after_cast: bool = True):
        super().__init__(EffectType.GIMMICK)
        self.after_cast = after_cast

    def execute(self, user, target, context) -> EffectResult:
        old_count = len(getattr(user, 'possibility_slots', []))
        user.possibility_slots = []

        logger.info(f"[슬롯 초기화] {getattr(user, 'name', '?')} 가능성 슬롯 {old_count}개 초기화")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'possibility_slots': -old_count},
            message=f"가능성 슬롯 초기화 ({old_count}개 제거)"
        )


class GainGimmickEffect(SkillEffect):
    """기믹 게이지 획득 - 지정된 기믹 필드를 증가시킨다.

    YAML 형식:
      - type: gain_gimmick
        gimmick: duty    # 기믹 필드명
        amount: 1        # 증가량
    """

    def __init__(self, gimmick: str = "", amount: int = 1):
        super().__init__(EffectType.GIMMICK)
        self.gimmick = gimmick
        self.amount = amount

    def execute(self, user, target, context) -> EffectResult:
        if not self.gimmick:
            return EffectResult(effect_type=EffectType.GIMMICK, success=False,
                                message="기믹 필드 미지정")

        old_value = getattr(user, self.gimmick, 0)
        max_field = f"max_{self.gimmick}"
        max_value = getattr(user, max_field, None)

        new_value = old_value + self.amount
        if max_value is not None and isinstance(max_value, (int, float)):
            new_value = min(new_value, max_value)

        setattr(user, self.gimmick, new_value)
        actual_gain = new_value - old_value

        logger.info(f"[기믹 획득] {getattr(user, 'name', '?')} {self.gimmick} +{actual_gain} (현재: {new_value})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={self.gimmick: actual_gain},
            message=f"{self.gimmick} +{actual_gain} (현재: {new_value})"
        )


class ConsumeGimmickEffect(SkillEffect):
    """기믹 게이지 소비 - 지정된 기믹 필드를 감소시킨다.

    YAML 형식:
      - type: consume_gimmick
        gimmick: fury     # 기믹 필드명
        amount: 10        # 소비량
    """

    def __init__(self, gimmick: str = "", amount: int = 1):
        super().__init__(EffectType.GIMMICK)
        self.gimmick = gimmick
        self.amount = amount

    def execute(self, user, target, context) -> EffectResult:
        if not self.gimmick:
            return EffectResult(effect_type=EffectType.GIMMICK, success=False,
                                message="기믹 필드 미지정")

        old_value = getattr(user, self.gimmick, 0)
        consumed = min(self.amount, old_value)
        new_value = max(0, old_value - consumed)
        setattr(user, self.gimmick, new_value)

        if context is not None:
            context['gimmick_consumed'] = consumed

        logger.info(f"[기믹 소비] {getattr(user, 'name', '?')} {self.gimmick} -{consumed} (잔여: {new_value})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={self.gimmick: -consumed},
            message=f"{self.gimmick} -{consumed} (잔여: {new_value})"
        )


class ConvergenceBonusEffect(SkillEffect):
    """수렴 보너스 - 가능성 슬롯 수에 비례한 데미지 증가 및 추가 디버프.

    YAML 형식:
      - type: convergence_bonus
        min_possibilities: 3    # 최소 슬롯 수
        damage_bonus: 0.5       # 데미지 보너스
        apply_debuff:
          type: time_lock
          duration: 1
    """

    def __init__(self, min_possibilities: int = 3, damage_bonus: float = 0.5,
                 apply_debuff: dict = None):
        super().__init__(EffectType.GIMMICK)
        self.min_possibilities = min_possibilities
        self.damage_bonus = damage_bonus
        self.apply_debuff = apply_debuff or {}

    def execute(self, user, target, context) -> EffectResult:
        # 해방된 가능성 수 확인 (context에서 가져옴)
        released_count = 0
        if context:
            released_count = context.get('released_count', 0)
        if released_count <= 0:
            released_count = len(getattr(user, 'possibility_slots', []))

        if released_count < self.min_possibilities:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message=f"수렴 보너스 불충분 ({released_count}/{self.min_possibilities})")

        # 데미지 보너스 적용
        if context is not None:
            current_mult = context.get('power_multiplier', 1.0)
            context['power_multiplier'] = current_mult + self.damage_bonus

        # 디버프 적용
        if self.apply_debuff:
            targets = target if isinstance(target, list) else [target]
            debuff_type = self.apply_debuff.get('type', 'slow')
            duration = self.apply_debuff.get('duration', 1)
            for t in targets:
                if not getattr(t, 'is_alive', True):
                    continue
                if hasattr(t, 'status_manager'):
                    try:
                        from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
                        status_map = {
                            'time_lock': StatusType.STUN,
                            'stun': StatusType.STUN,
                            'slow': StatusType.SLOW,
                            'freeze': StatusType.FREEZE,
                        }
                        st = status_map.get(debuff_type, StatusType.SLOW)
                        effect = CombatStatusEffect(
                            name=debuff_type.replace('_', ' ').title(),
                            status_type=st,
                            duration=min(duration, 2),
                            intensity=1.0,
                            source_id=getattr(user, 'name', None),
                        )
                        t.status_manager.add_status(effect, allow_refresh=True)
                    except Exception:
                        pass

        logger.info(f"[수렴 보너스] 데미지 +{self.damage_bonus*100:.0f}% (가능성 {released_count}개)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"수렴 보너스: +{self.damage_bonus*100:.0f}%"
        )


class ShieldDamageEffect(SkillEffect):
    """쉴드 대상 추가 데미지 - 보호막이 있는 대상에게 추가 피해를 입힌다.

    YAML 형식:
      - type: shield_damage
        bonus_multiplier: 1.5  # 보호막 대상 추가 배율
    """

    def __init__(self, bonus_multiplier: float = 1.5):
        super().__init__(EffectType.GIMMICK)
        self.bonus_multiplier = bonus_multiplier

    def execute(self, user, target, context) -> EffectResult:
        targets = target if isinstance(target, list) else [target]
        applied = False

        for t in targets:
            shield = getattr(t, 'shield_amount', 0)
            if shield > 0 and context is not None:
                current_mult = context.get('power_multiplier', 1.0)
                context['power_multiplier'] = current_mult * self.bonus_multiplier
                applied = True

        msg = f"쉴드 추가 피해 x{self.bonus_multiplier}" if applied else "보호막 없음"
        return EffectResult(effect_type=EffectType.GIMMICK, success=True, message=msg)


class AreaDamageEffect(SkillEffect):
    """범위 데미지 - 주변 적에게 감소된 피해를 입힌다.

    YAML 형식:
      - type: area_damage
        splash_ratio: 0.5  # 주변 대상 피해 비율
    """

    def __init__(self, splash_ratio: float = 0.5):
        super().__init__(EffectType.GIMMICK)
        self.splash_ratio = splash_ratio

    def execute(self, user, target, context) -> EffectResult:
        # context에 스플래시 배율 설정 (DamageEffect에서 참조)
        if context is not None:
            context['splash_ratio'] = self.splash_ratio

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"범위 피해 {self.splash_ratio*100:.0f}%"
        )
