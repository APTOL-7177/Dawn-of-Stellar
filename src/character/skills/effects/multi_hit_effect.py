"""Multi Hit Effect - 다단히트 HP 데미지 이펙트

multi_hit_hp_damage: 지정된 횟수만큼 HP 데미지를 반복 적용
random_hp_hits: 랜덤 횟수만큼 HP 데미지 적용
"""
import random

from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("multi_hit_effect")


def _apply_hp_hit(user, target, multiplier: float, context) -> int:
    """단일 HP 히트를 적용하고 실제 데미지를 반환한다.

    BraveSystem.hp_attack을 사용하되, 각 히트마다 BRV를 임시 복원하여
    다단히트가 모두 데미지를 입힐 수 있도록 한다.

    Args:
        user: 공격자
        target: 방어자
        multiplier: 데미지 배율
        context: 전투 컨텍스트

    Returns:
        실제 입힌 HP 데미지
    """
    try:
        from src.combat.brave_system import get_brave_system
        brave = get_brave_system()
        # hp_attack은 user.current_brv를 소모하므로 히트마다 임시 복원
        saved_brv = user.current_brv
        # BRV가 0이면 init_brv 또는 max_brv의 30%를 임시 주입
        if saved_brv <= 0:
            init_brv = getattr(user, 'init_brv', getattr(user, 'max_brv', 100))
            user.current_brv = max(1, int(init_brv * 0.3))

        result = brave.hp_attack(user, target, multiplier)
        hp_damage = result.get('hp_damage', 0)

        # 다단히트는 BRV를 소모하지 않는 것으로 취급 (BRV 복원)
        user.current_brv = saved_brv
        return hp_damage
    except Exception as exc:
        logger.warning(f"[다단히트] hp_attack 실패: {exc}")
        # 폴백: 직접 HP 감소
        if hasattr(target, 'current_hp') and hasattr(user, 'physical_attack'):
            raw = int(user.physical_attack * multiplier)
            dmg = max(1, raw)
            target.current_hp = max(0, target.current_hp - dmg)
            if target.current_hp <= 0 and hasattr(target, 'is_alive'):
                target.is_alive = False
            return dmg
        return 0


class MultiHitHpDamageEffect(SkillEffect):
    """다단히트 HP 데미지 이펙트 - 고정 횟수만큼 HP 데미지를 반복한다.

    YAML 형식:
      - type: multi_hit_hp_damage
        hits: 3
        multiplier: 0.5
    """

    def __init__(self, hits: int, multiplier: float):
        super().__init__(EffectType.DAMAGE)
        self.hits = max(1, hits)          # 히트 횟수 (최소 1)
        self.multiplier = multiplier      # 히트당 데미지 배율

    def execute(self, user, target, context):
        """다단히트 HP 데미지 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        targets = target if isinstance(target, list) else [target]
        total_damage = 0

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue

            hit_damage = 0
            for hit_idx in range(self.hits):
                if not getattr(t, 'is_alive', True):
                    break
                dmg = _apply_hp_hit(user, t, self.multiplier, context)
                hit_damage += dmg
                logger.debug(
                    f"[다단히트] {getattr(user, 'name', '?')} → {getattr(t, 'name', '?')} "
                    f"히트 {hit_idx+1}/{self.hits}: {dmg} 데미지"
                )

            total_damage += hit_damage

        result.hp_damage = total_damage
        result.damage_dealt = total_damage
        result.message = f"{self.hits}히트 HP 데미지 합계: {total_damage}"
        return result


class RandomHpHitsEffect(SkillEffect):
    """랜덤 히트 HP 데미지 이펙트 - min_hits~max_hits 사이 랜덤 횟수만큼 HP 데미지를 반복한다.

    YAML 형식:
      - type: random_hp_hits
        min_hits: 2
        max_hits: 5
        multiplier: 0.3
    """

    def __init__(self, min_hits: int, max_hits: int, multiplier: float):
        super().__init__(EffectType.DAMAGE)
        self.min_hits = max(1, min_hits)
        self.max_hits = max(self.min_hits, max_hits)
        self.multiplier = multiplier

    def execute(self, user, target, context):
        """랜덤 히트 HP 데미지 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        actual_hits = random.randint(self.min_hits, self.max_hits)
        targets = target if isinstance(target, list) else [target]
        total_damage = 0

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue

            hit_damage = 0
            for hit_idx in range(actual_hits):
                if not getattr(t, 'is_alive', True):
                    break
                dmg = _apply_hp_hit(user, t, self.multiplier, context)
                hit_damage += dmg
                logger.debug(
                    f"[랜덤히트] {getattr(user, 'name', '?')} → {getattr(t, 'name', '?')} "
                    f"히트 {hit_idx+1}/{actual_hits}: {dmg} 데미지"
                )

            total_damage += hit_damage

        result.hp_damage = total_damage
        result.damage_dealt = total_damage
        result.message = f"{actual_hits}히트(랜덤) HP 데미지 합계: {total_damage}"
        return result
