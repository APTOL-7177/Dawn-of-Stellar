"""Steal Buff Effect - 버프 훔치기 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType


class StealBuffEffect(SkillEffect):
    """적의 버프를 훔쳐서 자신에게 적용하는 효과"""
    def __init__(self, priority_order=None):
        super().__init__(EffectType.BUFF)
        # 우선순위: 공격력 > 방어력 > 속도
        self.priority_order = priority_order or ["attack_up", "defense_up", "speed_up"]

    def can_execute(self, user, target, context):
        return True, ""

    def execute(self, user, target, context):
        """버프 훔치기 실행"""
        result = EffectResult(effect_type=EffectType.BUFF, success=False)

        # 타겟의 버프 확인 및 훔치기
        stolen_buff = None

        if hasattr(target, 'status_effects') and isinstance(target.status_effects, dict):
            # 우선순위에 따라 버프 찾기
            for buff_type in self.priority_order:
                if buff_type in target.status_effects:
                    stolen_buff = buff_type
                    duration = target.status_effects[buff_type]
                    del target.status_effects[buff_type]
                    break

        elif hasattr(target, 'status_effects') and isinstance(target.status_effects, list):
            # 리스트 타입의 상태 효과
            for i, status in enumerate(target.status_effects):
                if hasattr(status, 'name'):
                    status_name = status.name.lower()
                    if any(priority in status_name for priority in self.priority_order):
                        stolen_buff = status.name
                        target.status_effects.pop(i)
                        duration = getattr(status, 'duration', 3)
                        break

        # 훔친 버프를 자신에게 적용
        if stolen_buff:
            # 자신에게 동일한 버프 적용
            if hasattr(user, 'status_effects'):
                if isinstance(user.status_effects, dict):
                    user.status_effects[stolen_buff] = duration
                elif isinstance(user.status_effects, list):
                    from src.character.skills.effects.status_effect import StatusEffectData
                    buff_data = StatusEffectData(stolen_buff, duration)
                    user.status_effects.append(buff_data)

            result.message = f"{stolen_buff.replace('_', ' ').title()} 버프 훔치기 성공!"
            result.success = True
        else:
            result.message = "훔칠 버프가 없습니다"

        return result
