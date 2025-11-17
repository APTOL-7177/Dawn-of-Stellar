"""ATB Effect - ATB 게이지를 직접 조작하는 효과"""
from typing import Any, Dict, Optional
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

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

        # ATB 변경량 계산
        if self.is_percentage:
            # 퍼센트로 계산 (atb_change가 100이면 ATB 최대치 2000의 100% = 2000)
            change = int(2000 * (self.atb_change / 100))
        else:
            change = self.atb_change

        # ATB 적용
        if hasattr(target, 'atb'):
            old_atb = target.atb
            target.atb = max(0, min(2000, target.atb + change))
            actual_change = target.atb - old_atb

            result.success = True
            result.message = f"{target.name}의 ATB {'+' if actual_change > 0 else ''}{actual_change} ({old_atb} → {target.atb})"

            self.logger.debug(f"[ATB_EFFECT] {target.name}: {old_atb} → {target.atb} (변경: {actual_change})")
        else:
            result.success = False
            result.message = f"{target.name}은(는) ATB를 가지고 있지 않음"
            self.logger.warning(f"[ATB_EFFECT] {target.name}에게 ATB 속성이 없음")

        return result
