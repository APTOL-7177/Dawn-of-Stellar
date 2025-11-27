"""Break Effect - BREAK 강제 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType


class BreakEffect(SkillEffect):
    """BREAK 강제 적용 효과"""
    def __init__(self, force_break: bool = True, brv_gain: int = 0):
        super().__init__(EffectType.DAMAGE)
        self.force_break = force_break  # True: BREAK 강제 적용
        self.brv_gain = brv_gain  # 자신 BRV 추가 획득량

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """BREAK 강제 적용 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        targets = target if isinstance(target, list) else [target]
        affected_count = 0

        for t in targets:
            if self.force_break and hasattr(t, 'current_brv'):
                # BRV를 0으로 만들어 BREAK 상태로 만듦
                t.current_brv = 0
                affected_count += 1

                # BREAK 이벤트 발생 (가능하다면)
                if hasattr(t, 'on_break'):
                    t.on_break()

        # 자신 BRV 추가 획득
        if self.brv_gain > 0 and hasattr(user, 'current_brv') and hasattr(user, 'max_brv'):
            old_brv = user.current_brv
            user.current_brv = min(user.max_brv, user.current_brv + self.brv_gain)
            actual_gain = user.current_brv - old_brv

            result.message = f"적 BREAK 적용! 자신 BRV +{actual_gain}"
        else:
            result.message = f"적 BREAK 적용!"

        result.success = affected_count > 0
        return result
