"""Temporal Heal Effect - 시간 기반 회복 이펙트

대상의 과거 HP 상태를 기록해 두었다가, 스킬 사용 시 그 시점으로 HP를 복원한다.
HP 기록은 캐릭터 인스턴스에 _hp_history 속성으로 저장되며,
전투 턴마다 갱신될 수 있도록 설계되어 있다.

YAML 형식:
  - type: temporal_heal
    method: restore_past_hp
    turns_back: 2
    max_heal_percent: 0.4
"""
from collections import deque

from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("temporal_heal_effect")

# HP 히스토리 최대 보존 턴 수 (메모리 절약)
_MAX_HISTORY = 10


def record_hp_snapshot(character) -> None:
    """캐릭터의 현재 HP를 HP 히스토리에 기록한다.

    이 함수는 전투 매니저의 _on_turn_end 등에서 호출되어야 하지만,
    temporal_heal 이펙트가 자체적으로 폴백 처리하므로 선택적이다.

    Args:
        character: HP를 기록할 캐릭터 객체
    """
    if not hasattr(character, '_hp_history'):
        character._hp_history = deque(maxlen=_MAX_HISTORY)
    current_hp = getattr(character, 'current_hp', 0)
    character._hp_history.append(current_hp)
    logger.debug(f"[HP스냅샷] {getattr(character, 'name', '?')} HP 기록: {current_hp}")


class TemporalHealEffect(SkillEffect):
    """시간 회복 이펙트 - 대상의 과거 HP를 기준으로 회복량을 계산한다.

    turns_back 턴 이전의 HP 스냅샷이 있으면 그 시점 HP와 현재 HP의 차이를
    회복한다. 단, max_heal_percent로 최대 회복량을 제한한다.

    스냅샷이 없는 경우에는 max_heal_percent를 현재 최대 HP에 적용한 고정 회복을 수행한다.
    """

    def __init__(self, method: str = "restore_past_hp", turns_back: int = 2, max_heal_percent: float = 0.4):
        """
        Args:
            method: 회복 방식 (현재는 "restore_past_hp"만 지원)
            turns_back: 몇 턴 전 HP로 복원할지
            max_heal_percent: 최대 HP 대비 최대 회복 비율 (0.0~1.0)
        """
        super().__init__(EffectType.HEAL)
        self.method = method
        self.turns_back = max(1, turns_back)
        self.max_heal_percent = max(0.0, min(1.0, max_heal_percent))

    def execute(self, user, target, context):
        """시간 회복 실행"""
        result = EffectResult(effect_type=EffectType.HEAL, success=True)

        targets = target if isinstance(target, list) else [target]
        total_heal = 0

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue

            heal_amount = self._calculate_heal(t)
            if heal_amount <= 0:
                continue

            # HP 회복 적용
            if hasattr(t, 'heal'):
                try:
                    actual = t.heal(heal_amount, source_character=user, is_self_skill=(user == t))
                except TypeError:
                    actual = t.heal(heal_amount)
            elif hasattr(t, 'current_hp') and hasattr(t, 'max_hp'):
                actual = min(heal_amount, t.max_hp - t.current_hp)
                t.current_hp = min(t.max_hp, t.current_hp + actual)
            else:
                actual = heal_amount

            total_heal += actual
            logger.info(
                f"[시간회복] {getattr(t, 'name', '?')} HP +{actual} "
                f"({self.turns_back}턴 전 기준, 최대 {self.max_heal_percent*100:.0f}%)"
            )

        result.heal_amount = total_heal
        result.message = f"시간 회복 +{total_heal} ({self.turns_back}턴 전 기준)"
        return result

    def _calculate_heal(self, target) -> int:
        """대상의 HP 히스토리를 참조해 회복량을 계산한다.

        Args:
            target: 회복 대상

        Returns:
            계산된 회복량 (max_heal_percent 제한 적용)
        """
        max_hp = getattr(target, 'max_hp', 0)
        current_hp = getattr(target, 'current_hp', 0)
        max_heal = int(max_hp * self.max_heal_percent)

        # HP 히스토리가 있으면 turns_back 이전 기록 사용
        history = getattr(target, '_hp_history', None)
        if history and len(history) >= 1:
            # deque의 오른쪽 끝이 최신, turns_back만큼 이전 인덱스 참조
            idx = max(0, len(history) - self.turns_back)
            past_hp = list(history)[idx]
            raw_heal = past_hp - current_hp
            if raw_heal <= 0:
                # 과거보다 HP가 높거나 같으면 회복 필요 없음
                return 0
            return min(raw_heal, max_heal)

        # 스냅샷이 없으면 max_heal_percent 고정 회복 (폴백)
        logger.debug(f"[시간회복] {getattr(target, 'name', '?')} HP 기록 없음 → 고정 회복 적용")
        return min(max_heal, max(0, max_hp - current_hp))
