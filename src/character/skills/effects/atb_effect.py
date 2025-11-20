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
        try:
            atb_system = get_atb_system()
        except Exception as e:
            self.logger.error(f"[ATB_EFFECT] ATB 시스템 가져오기 실패: {e}")
            result.success = False
            result.message = "ATB 효과 적용 실패"
            return result
        
        # ATB 게이지 가져오기 (없으면 등록)
        gauge = atb_system.get_gauge(target)
        if not gauge:
            # 전투 중이 아닐 수 있으므로 경고만 하고 실패 반환
            self.logger.warning(f"[ATB_EFFECT] {getattr(target, 'name', 'Unknown')}에게 ATB 게이지가 없음 - 등록 시도")
            try:
                # combat_manager가 있는 경우에만 등록 시도
                combat_manager = context.get('combat_manager')
                if combat_manager and hasattr(combat_manager, 'atb'):
                    atb_system.register_combatant(target)
                    gauge = atb_system.get_gauge(target)
            except Exception as e:
                self.logger.warning(f"[ATB_EFFECT] ATB 등록 시도 실패: {e}")
            
            # 그래도 없으면 실패
            if not gauge:
                result.success = False
                result.message = f"{getattr(target, 'name', 'Unknown')}은(는) ATB를 가지고 있지 않음"
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
            # 증가: 일관성을 위해 캐스팅 중에도 적용 (increase()는 캐스팅 중 차단하므로 직접 수정)
            # 최대치 제한 적용
            gauge.current = min(gauge.current + change, gauge.max_gauge)
        elif change < 0:
            # 감소: 직접 current 수정 (디버프는 캐스팅 중에도 적용)
            # change가 음수이므로 current + change = current - |change|
            gauge.current = max(0, gauge.current + change)
        # change == 0인 경우는 변경 없음
        
        new_atb = gauge.current
        actual_change = new_atb - old_atb

        # 실제로 변경이 있었는지 확인
        target_name = getattr(target, 'name', 'Unknown')
        try:
            if actual_change == 0 and change != 0:
                # 변경이 없었는데 change가 0이 아니면 (이미 최대치/최소치인 경우)
                result.success = False
                if change > 0:
                    result.message = f"{target_name}의 ATB는 이미 최대치입니다"
                else:
                    result.message = f"{target_name}의 ATB는 이미 최소치입니다"
            elif actual_change == 0:
                # change == 0인 경우 (변경 없음)
                result.success = True
                result.message = f"{target_name}의 ATB 변경 없음"
            else:
                # 정상적으로 변경됨
                result.success = True
                result.message = f"{target_name}의 ATB {'+' if actual_change > 0 else ''}{actual_change} ({old_atb} → {new_atb})"

            self.logger.debug(f"[ATB_EFFECT] {target_name}: {old_atb} → {new_atb} (변경: {actual_change})")
        except Exception as e:
            self.logger.error(f"[ATB_EFFECT] 메시지 생성 중 오류: {e}")
            result.success = True  # ATB는 변경되었으므로 성공으로 처리
            result.message = f"ATB {actual_change} 변경"

        return result
