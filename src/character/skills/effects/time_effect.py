"""Time Effect - 시간 시스템 이펙트

time_fracture: 시간 균열 (적 전체 스탯 감소)
time_crossing: 시간 교차 (2개 가능성 동시 발동)
time_storm: 시간 폭풍 (모든 가능성 해방 + ATB 대폭 감소)
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("time_effect")


class TimeFractureEffect(SkillEffect):
    """시간 균열 - 적 전체에 스탯 감소 디버프를 적용한다.

    YAML 형식:
      - type: time_fracture
        target: all_enemies
        effect: all_stats_down  # 전체 스탯 감소
        value: 0.2              # 감소 비율
        duration: 2             # 지속 턴
    """

    def __init__(self, effect: str = "all_stats_down", value: float = 0.2,
                 duration: int = 2, target: str = "all_enemies"):
        super().__init__(EffectType.BUFF)
        self.effect_type_name = effect
        self.value = value
        self.duration = duration
        self.target_type = target

    def execute(self, user, target, context) -> EffectResult:
        # 대상 결정
        if self.target_type == "all_enemies" and context:
            cm = context.get('combat_manager')
            if cm:
                if hasattr(cm, 'enemies') and user in getattr(cm, 'allies', []):
                    targets = [e for e in cm.enemies if getattr(e, 'is_alive', True)]
                elif hasattr(cm, 'allies') and user in getattr(cm, 'enemies', []):
                    targets = [a for a in cm.allies if getattr(a, 'is_alive', True)]
                else:
                    targets = target if isinstance(target, list) else [target]
            else:
                targets = target if isinstance(target, list) else [target]
        else:
            targets = target if isinstance(target, list) else [target]

        affected = 0
        debuff_types = ['attack_down', 'defense_down', 'magic_down',
                        'magic_defense_down', 'speed_down']

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            if not hasattr(t, 'active_buffs'):
                t.active_buffs = {}
            for debuff in debuff_types:
                t.active_buffs[debuff] = {'value': self.value, 'duration': self.duration}
            affected += 1

        logger.info(f"[시간 균열] {affected}명에게 전체 스탯 -{self.value*100:.0f}% ({self.duration}턴)")
        return EffectResult(
            effect_type=EffectType.BUFF,
            success=affected > 0,
            message=f"시간 균열: {affected}명 스탯 -{self.value*100:.0f}% ({self.duration}턴)"
        )


class TimeCrossingEffect(SkillEffect):
    """시간 교차 - 2개 가능성 슬롯을 동시에 발동한다.

    YAML 형식:
      - type: time_crossing
        power_ratio: 0.75  # 교차 발동 시 위력 배율
        slot_count: 2      # 발동할 슬롯 수
        select_slots: true # 슬롯 선택 여부
    """

    def __init__(self, power_ratio: float = 0.75, slot_count: int = 2,
                 select_slots: bool = True):
        super().__init__(EffectType.GIMMICK)
        self.power_ratio = power_ratio
        self.slot_count = slot_count
        self.select_slots = select_slots

    def execute(self, user, target, context) -> EffectResult:
        slots = getattr(user, 'possibility_slots', [])
        if len(slots) < 2:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="가능성 2개 이상 필요")

        # 슬롯 인덱스 결정
        slot_indices = []
        if context:
            selected = context.get('selected_slot_indices')
            if selected and len(selected) >= 2:
                slot_indices = selected[:2]
        if not slot_indices:
            slot_indices = [0, 1] if len(slots) >= 2 else [0]

        from src.character.gimmick_updater import GimmickUpdater
        results = GimmickUpdater.time_crossing(user, slot_indices, context)

        if context is not None:
            context['crossed_skills'] = results
            context['power_multiplier'] = context.get('power_multiplier', 1.0) * self.power_ratio

        skill_names = [r.get('skill_id', '?') for r in results if r.get('success')]
        logger.info(f"[시간 교차] {getattr(user, 'name', '?')} {skill_names} 동시 발동")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"시간 교차: {', '.join(skill_names)}"
        )


class TimeStormEffect(SkillEffect):
    """시간 폭풍 - 모든 가능성을 해방하고 적 전체 ATB를 대폭 감소시킨다.

    YAML 형식:
      - type: time_storm
        power_ratio: 1.2    # 해방 위력 배율
        release_all: true   # 전부 해방
    """

    def __init__(self, power_ratio: float = 1.2, release_all: bool = True):
        super().__init__(EffectType.GIMMICK)
        self.power_ratio = power_ratio
        self.release_all = release_all

    def execute(self, user, target, context) -> EffectResult:
        from src.character.gimmick_updater import GimmickUpdater
        storm_result = GimmickUpdater.time_storm(user, context)

        if not storm_result.get('success'):
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="해방할 가능성 없음")

        released = storm_result.get('released', [])
        slot_count = len(released)
        convergence_bonus = storm_result.get('convergence_bonus', False)
        damage_bonus = storm_result.get('total_damage_bonus', 0)

        if context is not None:
            context['released_possibilities'] = released
            context['released_count'] = slot_count
            base_mult = context.get('power_multiplier', 1.0)
            context['power_multiplier'] = base_mult * self.power_ratio
            if convergence_bonus:
                context['power_multiplier'] += damage_bonus

        # 적 전체 ATB 감소
        atb_reduced = 0
        if context:
            cm = context.get('combat_manager')
            if cm:
                enemies = []
                if hasattr(cm, 'enemies') and user in getattr(cm, 'allies', []):
                    enemies = [e for e in cm.enemies if getattr(e, 'is_alive', True)]
                elif hasattr(cm, 'allies') and user in getattr(cm, 'enemies', []):
                    enemies = [a for a in cm.allies if getattr(a, 'is_alive', True)]
                for enemy in enemies:
                    try:
                        from src.character.skills.effects.atb_effect import _apply_atb_change
                        # 슬롯 수에 비례한 ATB 감소 (슬롯당 200)
                        reduction = slot_count * 200
                        _apply_atb_change(enemy, -reduction)
                        atb_reduced += 1
                    except Exception:
                        pass

        msg = f"시간 폭풍: {slot_count}개 가능성 해방"
        if convergence_bonus:
            msg += f" + 수렴 보너스 {damage_bonus*100:.0f}%"
        if atb_reduced > 0:
            msg += f" + {atb_reduced}명 ATB 감소"

        logger.info(f"[시간 폭풍] {getattr(user, 'name', '?')} {msg}")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'possibility_slots': -slot_count},
            message=msg
        )
