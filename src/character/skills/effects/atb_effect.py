"""ATB Effect - ATB 게이지 조작 효과

atb_boost: 대상 ATB를 고정값만큼 증가
atb_charge: 대상 ATB를 퍼센트만큼 충전
self_atb_cost: 시전자 ATB를 추가 소비
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("atb_effect")


def _apply_atb_change(target, amount: int) -> int:
    """ATB 시스템 게이지와 캐릭터 atb_gauge 속성을 동시에 변경한다.

    ATBSystem.gauges 딕셔너리를 통해 실제 게이지 객체에 접근하고,
    캐릭터 객체의 atb_gauge 속성(UI 표시용)도 함께 업데이트한다.

    Args:
        target: 대상 캐릭터
        amount: ATB 변경량 (양수=증가, 음수=감소)

    Returns:
        실제로 변경된 ATB 양
    """
    try:
        from src.combat.atb_system import get_atb_system
        atb_sys = get_atb_system()
        gauge = atb_sys.get_gauge(target)
        if gauge:
            old = gauge.current
            threshold = atb_sys.threshold
            max_gauge = atb_sys.max_gauge
            gauge.current = max(0, min(max_gauge, gauge.current + amount))
            return int(gauge.current - old)
    except Exception as exc:
        logger.debug(f"[ATB] ATBSystem 접근 실패: {exc}")

    # 폴백: 캐릭터 속성 직접 조작
    if hasattr(target, 'atb_gauge'):
        max_atb = getattr(target, 'max_atb', 2000)
        old = target.atb_gauge
        target.atb_gauge = max(0, min(max_atb, target.atb_gauge + amount))
        return int(target.atb_gauge - old)
    return 0


class AtbEffect(SkillEffect):
    """ATB 게이지 조작 효과 (고정값 변경)"""
    def __init__(self, atb_change: int, is_party_wide: bool = False, target_all_enemies: bool = False):
        super().__init__(EffectType.BUFF)
        self.atb_change = atb_change  # ATB 변경량 (양수: 증가, 음수: 감소)
        self.is_party_wide = is_party_wide
        self.target_all_enemies = target_all_enemies

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """ATB 게이지 조작 실행"""
        from src.core.logger import get_logger
        logger = get_logger("atb_effect")

        result = EffectResult(effect_type=EffectType.BUFF, success=True)

        logger.debug(f"[AtbEffect] 실행 시작 - user: {user.name if hasattr(user, 'name') else user}, target: {target.name if hasattr(target, 'name') else target}, atb_change: {self.atb_change}")

        # 타겟 결정
        if self.target_all_enemies:
            # context에서 적들을 가져오기
            if context and 'combat_manager' in context:
                combat_manager = context['combat_manager']
                if hasattr(combat_manager, 'enemies'):
                    targets = combat_manager.enemies
                else:
                    targets = [target] if not isinstance(target, list) else target
            else:
                targets = [target] if not isinstance(target, list) else target
        elif self.is_party_wide:
            # context에서 아군들을 가져오기
            if context and 'combat_manager' in context:
                combat_manager = context['combat_manager']
                if hasattr(combat_manager, 'allies'):
                    targets = combat_manager.allies
                else:
                    targets = [target] if not isinstance(target, list) else target
            else:
                targets = [target] if not isinstance(target, list) else target
        else:
            targets = target if isinstance(target, list) else [target]

        affected_count = 0
        total_atb_change = 0

        for t in targets:
            actual_change = _apply_atb_change(t, self.atb_change)
            if actual_change != 0:
                total_atb_change += actual_change
                affected_count += 1
                logger.info(f"[AtbEffect] {getattr(t, 'name', t)} ATB 변경량: {actual_change:+d}")

        if affected_count > 0:
            direction = "증가" if self.atb_change > 0 else "감소"
            message = f"ATB {direction} {abs(total_atb_change)}"
            result.message = message

        return result


class AtbBoostEffect(SkillEffect):
    """ATB 부스트 이펙트 - 대상 ATB를 고정값만큼 즉시 증가시킨다.

    YAML 형식:
      - type: atb_boost
        target: self / single_ally / all_allies
        amount: 500
    """

    def __init__(self, amount: int, is_party_wide: bool = False):
        super().__init__(EffectType.ATB)
        self.amount = amount          # 증가량 (ATBSystem 기준 0~2000)
        self.is_party_wide = is_party_wide

    def execute(self, user, target, context):
        """ATB 부스트 실행"""
        result = EffectResult(effect_type=EffectType.ATB, success=True)

        if self.is_party_wide:
            # 파티 전체 부스트
            if context and 'combat_manager' in context:
                cm = context['combat_manager']
                if hasattr(cm, 'allies') and user in cm.allies:
                    targets = [a for a in cm.allies if getattr(a, 'is_alive', True)]
                elif hasattr(cm, 'enemies') and user in cm.enemies:
                    targets = [e for e in cm.enemies if getattr(e, 'is_alive', True)]
                else:
                    targets = [target] if not isinstance(target, list) else target
            else:
                targets = target if isinstance(target, list) else [target]
        else:
            targets = target if isinstance(target, list) else [target]

        total = 0
        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            actual = _apply_atb_change(t, self.amount)
            total += actual
            logger.info(f"[ATB부스트] {getattr(t, 'name', t)} ATB +{actual}")

        result.message = f"ATB 부스트 +{total}" if total else "ATB 부스트 (변화 없음)"
        return result


class AtbChargeEffect(SkillEffect):
    """ATB 퍼센트 충전 이펙트 - 대상 ATB를 threshold 기준 퍼센트만큼 충전한다.

    YAML 형식:
      - type: atb_charge
        target: self
        percent: 50   # threshold의 50%를 충전
    """

    def __init__(self, percent: float):
        super().__init__(EffectType.ATB)
        # percent는 0~100 범위로 입력받으며 내부적으로 0~1.0으로 변환
        self.percent = percent / 100.0 if percent > 1.0 else percent

    def execute(self, user, target, context):
        """ATB 퍼센트 충전 실행"""
        result = EffectResult(effect_type=EffectType.ATB, success=True)

        targets = target if isinstance(target, list) else [target]
        total = 0

        try:
            from src.combat.atb_system import get_atb_system
            threshold = get_atb_system().threshold
        except Exception:
            threshold = 1000  # 기본 threshold 폴백

        charge_amount = int(threshold * self.percent)

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            actual = _apply_atb_change(t, charge_amount)
            total += actual
            logger.info(f"[ATB충전] {getattr(t, 'name', t)} ATB +{actual} ({self.percent*100:.0f}%)")

        result.message = f"ATB {self.percent*100:.0f}% 충전 (+{total})"
        return result


class SelfAtbCostEffect(SkillEffect):
    """시전자 ATB 추가 소비 이펙트 - 스킬 사용 후 시전자의 ATB를 추가로 소비한다.

    YAML 형식:
      - type: self_atb_cost
        amount: 300   # 추가 소비할 ATB 양
    """

    def __init__(self, amount: int):
        super().__init__(EffectType.ATB)
        self.amount = amount  # 소비량 (양수 값, 내부에서 음수로 적용)

    def execute(self, user, target, context):
        """ATB 추가 소비 실행 (항상 시전자에게 적용)"""
        result = EffectResult(effect_type=EffectType.ATB, success=True)

        actual = _apply_atb_change(user, -self.amount)
        logger.info(f"[ATB소비] {getattr(user, 'name', user)} ATB -{self.amount} (실제: {actual})")
        result.message = f"ATB 추가 소비 -{abs(actual)}"
        return result


class SelfAtbCostPercentEffect(SkillEffect):
    """시전자 ATB 비율 소비 이펙트 - 시전자 ATB의 일정 비율을 추가로 소비한다.

    YAML 형식:
      - type: self_atb_cost
        percent: 50   # 현재 threshold 기준 50% 소비
    """

    def __init__(self, percent: float):
        super().__init__(EffectType.ATB)
        # percent는 0~100 범위로 입력받는다
        self.percent = percent

    def execute(self, user, target, context):
        """ATB 비율 소비 실행 (항상 시전자에게 적용)"""
        result = EffectResult(effect_type=EffectType.ATB, success=True)

        try:
            from src.combat.atb_system import get_atb_system
            threshold = get_atb_system().threshold
        except Exception:
            threshold = 1000  # 기본 threshold 폴백

        cost = int(threshold * self.percent / 100.0)
        actual = _apply_atb_change(user, -cost)
        logger.info(f"[ATB소비] {getattr(user, 'name', user)} ATB -{cost} ({self.percent:.0f}%) (실제: {actual})")
        result.message = f"ATB 추가 소비 -{abs(actual)}"
        return result