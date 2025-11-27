"""Taunt Effect - 도발 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType


class TauntEffect(SkillEffect):
    """도발 효과 - 적을 자신에게 집중시키는 효과"""
    def __init__(self, duration: int = 2, cannot_resist: bool = False):
        super().__init__(EffectType.BUFF)
        self.duration = duration
        self.cannot_resist = cannot_resist

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """도발 적용"""
        result = EffectResult(effect_type=EffectType.BUFF, success=True)

        # 타겟 결정 - 전체 적을 대상으로 함
        if context and 'combat_manager' in context:
            combat_manager = context['combat_manager']
            if hasattr(combat_manager, 'enemies'):
                targets = combat_manager.enemies
            else:
                targets = target if isinstance(target, list) else [target]
        else:
            targets = target if isinstance(target, list) else [target]

        affected_count = 0
        for t in targets:
            # 도발 상태 적용 (실제로는 상태 매니저에 등록)
            if hasattr(t, 'status_manager'):
                # TODO: 도발 상태 구현
                affected_count += 1
            elif hasattr(t, 'status_effects'):
                # 레거시 시스템
                if not hasattr(t, 'status_effects'):
                    t.status_effects = []
                # 도발 상태 추가
                from src.character.skills.effects.status_effect import StatusEffectData
                taunt_data = StatusEffectData("taunt", self.duration)
                t.status_effects.append(taunt_data)
                affected_count += 1

        result.message = f"도발 적용! ({self.duration}턴)"
        result.success = affected_count > 0
        return result
