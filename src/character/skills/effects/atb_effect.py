"""ATB Effect - ATB 게이지를 직접 조작하는 효과"""
from typing import Any, Dict, Optional
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger
from src.combat.atb_system import get_atb_system

class ATBEffect(SkillEffect):
    """ATB 게이지를 직접 조작하는 효과"""

    def __init__(self, atb_change: int, is_percentage: bool = False, target_allies: bool = False):
        """
        Args:
            atb_change: ATB 변경량 (양수=증가, 음수=감소)
            is_percentage: True면 최대 ATB(2000)의 %로 계산
            target_allies: True면 아군 대상, False면 적 대상
        """
        super().__init__(EffectType.ATB)
        self.atb_change = atb_change
        self.is_percentage = is_percentage
        self.target_allies = target_allies
        self.logger = get_logger("atb_effect")

    def execute(self, user: Any, target: Any, context: Optional[Dict[str, Any]] = None) -> EffectResult:
        """ATB 효과 실행"""
        context = context or {}
        result = EffectResult(effect_type=self.effect_type, success=True)

        # ATB 시스템 가져오기
        atb_system = get_atb_system()
        
        # ATB 게이지 가져오기
        gauge = atb_system.get_gauge(target)
        if not gauge:
            result.success = False
            result.message = f"{target.name}은(는) ATB를 가지고 있지 않음"
            self.logger.warning(f"[ATB_EFFECT] {target.name}에게 ATB 속성이 없음")
            return result

        # ATB 변경량 계산
        if self.is_percentage:
            # 퍼센트로 계산 (atb_change가 100이면 ATB 최대치의 100% = max_gauge)
            max_gauge = gauge.max_gauge
            change = int(max_gauge * (self.atb_change / 100))
        else:
            change = self.atb_change

        # ATB 적용
        old_atb = gauge.current
        
        if change > 0:
            # 증가: increase() 메서드 사용 (최대치 제한 자동 적용, 캐스팅 중에는 증가 안 함)
            gauge.increase(float(change))
        elif change < 0:
            # 감소: 직접 current 수정 (디버프는 캐스팅 중에도 적용)
            # change가 음수이므로 current + change = current - |change|
            gauge.current = max(0, gauge.current + change)
        # change == 0인 경우는 변경 없음
        
        new_atb = gauge.current
        actual_change = new_atb - old_atb

        result.success = True
        result.message = f"{target.name}의 ATB {'+' if actual_change > 0 else ''}{actual_change} ({old_atb} → {new_atb})"

        self.logger.debug(f"[ATB_EFFECT] {target.name}: {old_atb} → {new_atb} (변경: {actual_change})")

        return result
