"""Possibility Effect - 차원술사 가능성 시스템 이펙트

generate_possibility: 가능성 생성 (possibility_slots에 스킬 추가)
release_all_possibilities: 모든 가능성 해방
summon_possibility: 가능성 소환 (슬롯의 스킬 발동)
consume_option: 옵션 소비 (가능성 1개 소비)
"""
import random

from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("possibility_effect")


class GeneratePossibilityEffect(SkillEffect):
    """가능성 생성 - 스킬 사용 시 alternative_skill을 가능성 슬롯에 저장한다.

    YAML 형식:
      - type: generate_possibility
        chance: 0.7              # 생성 확률
        alternative_skill: slow  # 저장할 대체 스킬 ID
    """

    def __init__(self, chance: float = 0.7, alternative_skill: str = ""):
        super().__init__(EffectType.GIMMICK)
        self.chance = chance
        self.alternative_skill = alternative_skill

    def execute(self, user, target, context) -> EffectResult:
        if not self.alternative_skill:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="대체 스킬 미지정")

        # 가능성 슬롯 확인
        slots = getattr(user, 'possibility_slots', [])
        max_slots = getattr(user, 'max_possibility_slots', 4)
        if len(slots) >= max_slots:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="가능성 슬롯 가득 참")

        # 생성 확률 계산 (특성 보너스 포함)
        final_chance = self.chance
        if hasattr(user, 'active_traits'):
            for trait_data in user.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == "branch_creator":
                    final_chance += 0.15
                    luck = getattr(user, 'luck', 0)
                    if hasattr(user, 'stat_manager'):
                        try:
                            from src.character.stats import Stats
                            luck = user.stat_manager.get_value(Stats.LUCK)
                        except Exception:
                            pass
                    final_chance += luck * 0.0025
                    final_chance = min(final_chance, 0.95)
                    break

        if random.random() >= final_chance:
            logger.debug(f"[가능성] {getattr(user, 'name', '?')} 가능성 생성 실패 (확률: {final_chance*100:.0f}%)")
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="가능성 생성 실패")

        # GimmickUpdater를 통해 가능성 추가
        from src.character.gimmick_updater import GimmickUpdater
        success = GimmickUpdater._add_possibility(user, self.alternative_skill)

        if success:
            logger.info(f"[가능성 생성] {getattr(user, 'name', '?')} '{self.alternative_skill}' 저장됨")
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=True,
                gimmick_changes={'possibility_slots': 1},
                message=f"가능성 생성: {self.alternative_skill}"
            )

        return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                            message="가능성 슬롯 가득 참")


class ReleaseAllPossibilitiesEffect(SkillEffect):
    """모든 가능성 해방 - 저장된 모든 가능성을 소비하고 context에 정보를 기록한다.

    YAML 형식:
      - type: release_all_possibilities
        power_ratio: 1.4   # 해방 시 위력 배율
        sequence: true     # 순차 발동 여부
        delay_between: 0.3 # 발동 간 딜레이
    """

    def __init__(self, power_ratio: float = 1.0, sequence: bool = True,
                 delay_between: float = 0.3):
        super().__init__(EffectType.GIMMICK)
        self.power_ratio = power_ratio
        self.sequence = sequence
        self.delay_between = delay_between

    def execute(self, user, target, context) -> EffectResult:
        from src.character.gimmick_updater import GimmickUpdater
        storm_result = GimmickUpdater.time_storm(user, context)

        if not storm_result.get('success'):
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="해방할 가능성 없음")

        released = storm_result.get('released', [])
        slot_count = len(released)
        convergence_bonus = storm_result.get('convergence_bonus', False)
        total_damage_bonus = storm_result.get('total_damage_bonus', 0)

        # context에 해방 정보 저장 (후속 이펙트에서 사용)
        if context is not None:
            context['released_possibilities'] = released
            context['released_count'] = slot_count
            # power_multiplier에 해방 보너스 적용
            base_mult = context.get('power_multiplier', 1.0)
            context['power_multiplier'] = base_mult * self.power_ratio
            if convergence_bonus:
                context['power_multiplier'] += total_damage_bonus

        logger.info(f"[가능성 해방] {getattr(user, 'name', '?')} {slot_count}개 가능성 해방 (수렴: {convergence_bonus})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'possibility_slots': -slot_count},
            message=f"가능성 {slot_count}개 해방!" + (f" 수렴 보너스 +{total_damage_bonus*100:.0f}%" if convergence_bonus else "")
        )


class SummonPossibilityEffect(SkillEffect):
    """가능성 소환 - 저장된 가능성 슬롯의 스킬을 발동한다.

    YAML 형식:
      - type: summon_possibility
        power_ratio: 0.85   # 소환 시 위력 배율
        select_slot: true    # 슬롯 선택 여부
    """

    def __init__(self, power_ratio: float = 0.85, select_slot: bool = True):
        super().__init__(EffectType.GIMMICK)
        self.power_ratio = power_ratio
        self.select_slot = select_slot

    def execute(self, user, target, context) -> EffectResult:
        slots = getattr(user, 'possibility_slots', [])
        if not slots:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="가능성 슬롯이 비어있음")

        # 슬롯 인덱스 결정 (컨텍스트에서 선택하거나 첫 번째 슬롯)
        slot_index = 0
        if context:
            selected = context.get('selected_slot_index')
            if selected is not None and 0 <= selected < len(slots):
                slot_index = selected

        from src.character.gimmick_updater import GimmickUpdater
        summon_result = GimmickUpdater.summon_possibility(user, slot_index, context)

        if not summon_result.get('success'):
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message=summon_result.get('error', '소환 실패'))

        skill_id = summon_result['skill_id']
        power = summon_result.get('power_ratio', self.power_ratio)

        # context에 소환 정보 저장 (전투 시스템에서 스킬 발동에 사용)
        if context is not None:
            context['summoned_skill_id'] = skill_id
            context['power_multiplier'] = context.get('power_multiplier', 1.0) * power
            context['original_character'] = summon_result.get('original_character')

        logger.info(f"[가능성 소환] {getattr(user, 'name', '?')} '{skill_id}' 발동 (위력: {power})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"가능성 소환: {skill_id} (위력 {power*100:.0f}%)"
        )


class ConsumeOptionEffect(SkillEffect):
    """옵션 소비 - 환영 또는 가능성을 1개 소비하고 보너스를 적용한다.

    YAML 형식:
      - type: consume_option
        consume_phantoms: 1           # 환영 소비 수
        bonus_if_consumed:
          multiplier_bonus: 0.5       # 소비 시 데미지 보너스
          guaranteed_critical: true   # 소비 시 크리티컬 확정
    """

    def __init__(self, consume_phantoms: int = 0,
                 bonus_if_consumed: dict = None):
        super().__init__(EffectType.GIMMICK)
        self.consume_phantoms = consume_phantoms
        self.bonus_if_consumed = bonus_if_consumed or {}

    def execute(self, user, target, context) -> EffectResult:
        consumed = False

        # 환영 소비
        if self.consume_phantoms > 0:
            current = getattr(user, 'phantom_count', 0)
            if current >= self.consume_phantoms:
                user.phantom_count = current - self.consume_phantoms
                # phantom_hits 업데이트
                if hasattr(user, 'phantom_hits') and isinstance(user.phantom_hits, list):
                    remove = min(self.consume_phantoms, len(user.phantom_hits))
                    user.phantom_hits = user.phantom_hits[:-remove] if remove > 0 else user.phantom_hits
                consumed = True

        # 보너스 적용
        if consumed and self.bonus_if_consumed and context is not None:
            mult_bonus = self.bonus_if_consumed.get('multiplier_bonus', 0)
            if mult_bonus:
                current_mult = context.get('power_multiplier', 1.0)
                context['power_multiplier'] = current_mult + mult_bonus
            if self.bonus_if_consumed.get('guaranteed_critical'):
                context['force_critical'] = True

        msg = "옵션 소비 성공" if consumed else "소비할 옵션 없음"
        if consumed and self.bonus_if_consumed:
            msg += f" (보너스 적용)"
        logger.info(f"[옵션 소비] {getattr(user, 'name', '?')} {msg}")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=msg
        )
