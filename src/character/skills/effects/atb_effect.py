"""ATB Effect - ATB 게이지 조작 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType


class AtbEffect(SkillEffect):
    """ATB 게이지 조작 효과"""
    def __init__(self, atb_change: int, is_party_wide: bool = False, target_all_enemies: bool = False):
        super().__init__(EffectType.BUFF)
        self.atb_change = atb_change  # ATB 변경량 (양수: 증가, 음수: 감소)
        self.is_party_wide = is_party_wide
        self.target_all_enemies = target_all_enemies

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """ATB 게이지 조작 실행"""
        result = EffectResult(effect_type=EffectType.BUFF, success=True)

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
            if hasattr(t, 'current_atb') and hasattr(t, 'max_atb'):
                # ATB 변경 적용
                old_atb = t.current_atb
                t.current_atb = max(0, min(t.max_atb, t.current_atb + self.atb_change))
                actual_change = t.current_atb - old_atb
                total_atb_change += actual_change
                affected_count += 1

        if affected_count > 0:
            direction = "증가" if self.atb_change > 0 else "감소"
            message = f"ATB {direction} {abs(total_atb_change)}"
            result.message = message

        return result