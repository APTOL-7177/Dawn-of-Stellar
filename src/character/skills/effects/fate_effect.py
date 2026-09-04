"""Fate Effect - 운명 시스템 이펙트

fate_copy: 운명 복사 (아군의 마지막 스킬을 가능성 슬롯에 복사)
overwrite_fate: 운명 덮어쓰기 (가능성 슬롯의 스킬을 교체)
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("fate_effect")


class FateCopyEffect(SkillEffect):
    """운명 복사 - 아군의 마지막 사용 스킬을 가능성 슬롯에 복사한다.

    YAML 형식:
      - type: fate_copy
        target: selected_ally      # 대상 선택
        copy_last_skill: true      # 마지막 스킬 복사
        store_as_possibility: true # 가능성으로 저장
        power_ratio: 0.85          # 복사 스킬 위력 배율
    """

    def __init__(self, copy_last_skill: bool = True,
                 store_as_possibility: bool = True, power_ratio: float = 0.85,
                 target: str = "selected_ally"):
        super().__init__(EffectType.GIMMICK)
        self.copy_last_skill = copy_last_skill
        self.store_as_possibility = store_as_possibility
        self.power_ratio = power_ratio
        self.target_type = target

    def execute(self, user, target, context) -> EffectResult:
        targets = target if isinstance(target, list) else [target]

        # 아군 대상 찾기
        ally = None
        for t in targets:
            if t != user and getattr(t, 'is_alive', True):
                ally = t
                break

        # 아군이 없으면 context에서 찾기
        if not ally and context:
            allies = context.get('all_allies', [])
            for a in allies:
                if a != user and getattr(a, 'is_alive', True):
                    ally = a
                    break

        if not ally:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="복사 대상 없음")

        from src.character.gimmick_updater import GimmickUpdater
        copy_result = GimmickUpdater.fate_copy(user, ally, context)

        if copy_result.get('success'):
            skill_id = copy_result['copied_skill']
            original = copy_result.get('original_character', '')
            logger.info(f"[운명 복사] {getattr(user, 'name', '?')} ← {original}: '{skill_id}'")
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=True,
                gimmick_changes={'possibility_slots': 1},
                message=f"운명 복사: {skill_id} (출처: {original})"
            )

        error = copy_result.get('error', '복사 실패')
        return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                            message=f"운명 복사 실패: {error}")


class OverwriteFateEffect(SkillEffect):
    """운명 덮어쓰기 - 가능성 슬롯의 스킬을 다른 스킬로 교체한다.

    YAML 형식:
      - type: overwrite_fate
        select_slot: true              # 슬롯 선택
        select_replacement_skill: true # 교체 스킬 선택
        power_ratio: 0.85             # 교체 스킬 위력 배율
    """

    def __init__(self, select_slot: bool = True,
                 select_replacement_skill: bool = True,
                 power_ratio: float = 0.85):
        super().__init__(EffectType.GIMMICK)
        self.select_slot = select_slot
        self.select_replacement_skill = select_replacement_skill
        self.power_ratio = power_ratio

    def execute(self, user, target, context) -> EffectResult:
        slots = getattr(user, 'possibility_slots', [])
        if not slots:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="덮어쓸 가능성 슬롯 없음")

        # 슬롯 인덱스와 교체 스킬 결정
        slot_index = 0
        new_skill_id = None

        if context:
            slot_index = context.get('selected_slot_index', 0)
            new_skill_id = context.get('selected_skill_id')

        # 교체 스킬이 없으면 user의 스킬 목록에서 랜덤 선택
        if not new_skill_id:
            skill_ids = getattr(user, 'skill_ids', [])
            excluded = ['teamwork', 'infinite_convergence', 'time_storm']
            available = [s for s in skill_ids if s not in excluded]
            if available:
                import random
                new_skill_id = random.choice(available)

        if not new_skill_id:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="교체할 스킬 없음")

        from src.character.gimmick_updater import GimmickUpdater
        result = GimmickUpdater.overwrite_fate(user, slot_index, new_skill_id)

        if result.get('success'):
            old_skill = result['old_skill']
            logger.info(f"[운명 덮어쓰기] {getattr(user, 'name', '?')} '{old_skill}' → '{new_skill_id}'")
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=True,
                message=f"운명 덮어쓰기: {old_skill} → {new_skill_id}"
            )

        error = result.get('error', '덮어쓰기 실패')
        return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                            message=f"운명 덮어쓰기 실패: {error}")
