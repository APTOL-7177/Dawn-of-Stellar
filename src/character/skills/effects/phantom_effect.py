"""Phantom Effect - 환술사 환영 시스템 이펙트

summon_phantom: 환영 소환 (phantom_count 증가)
consume_phantom: 환영 소비 (phantom_count 감소, 효과 증폭)
phantom_echo_damage: 환영 에코 데미지 (phantom_count 비례 추가 데미지)
consume_all_phantoms: 모든 환영 소비
phantom_bonus_debuff: 환영 수 비례 디버프 강화
phantom_convergence_bonus: 환영 수렴 보너스
phantom_damage_redirect: 환영 피해 대리 흡수
phantom_priority: 환영 우선 타겟 설정
phantom_counter: 환영 카운터 (피격 시 반격)
"""
import random

from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("phantom_effect")


class SummonPhantomEffect(SkillEffect):
    """환영 소환 - phantom_count를 증가시킨다.

    YAML 형식:
      - type: summon_phantom
        count: 1           # 기본 소환 수 (또는 base_count)
        bonus_count: 1     # 추가 소환 수 (확률 기반)
        bonus_chance: 0.3  # 추가 소환 확률
        fill_to_max: false # true면 최대치까지 채움
        luck_scaling: 0.01 # 행운에 비례한 추가 확률
    """

    def __init__(self, count: int = 1, bonus_count: int = 0,
                 bonus_chance: float = 0.0, fill_to_max: bool = False,
                 luck_scaling: float = 0.0):
        super().__init__(EffectType.GIMMICK)
        self.count = count
        self.bonus_count = bonus_count
        self.bonus_chance = bonus_chance
        self.fill_to_max = fill_to_max
        self.luck_scaling = luck_scaling

    def execute(self, user, target, context) -> EffectResult:
        max_phantoms = getattr(user, 'max_phantoms', 4)
        current = getattr(user, 'phantom_count', 0)

        if self.fill_to_max:
            add_count = max(0, max_phantoms - current)
        else:
            add_count = self.count
            # 추가 소환 확률 계산
            if self.bonus_count > 0 and self.bonus_chance > 0:
                luck = getattr(user, 'luck', 0)
                if hasattr(user, 'stat_manager'):
                    try:
                        from src.character.stats import Stats
                        luck = user.stat_manager.get_value(Stats.LUCK)
                    except Exception:
                        pass
                final_chance = self.bonus_chance + (luck * self.luck_scaling)
                if random.random() < final_chance:
                    add_count += self.bonus_count

        old_count = current
        new_count = min(current + add_count, max_phantoms)
        actual_added = new_count - old_count
        user.phantom_count = new_count

        # phantom_hits 배열 업데이트 (GimmickEffect와 동일 패턴)
        hit_absorb = getattr(user, 'phantom_hit_absorb', 2)
        if hasattr(user, '_has_trait') and user._has_trait('infinite_mirrors'):
            hit_absorb += 1
        if not hasattr(user, 'phantom_hits') or not isinstance(user.phantom_hits, list):
            user.phantom_hits = []
        for _ in range(actual_added):
            if len(user.phantom_hits) < max_phantoms:
                user.phantom_hits.append(hit_absorb)

        logger.info(f"[환영 소환] {getattr(user, 'name', '?')} 환영 +{actual_added} (현재: {new_count}/{max_phantoms})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'phantom_count': actual_added},
            message=f"환영 소환 +{actual_added} (현재: {new_count})"
        )


class ConsumePhantomEffect(SkillEffect):
    """환영 소비 - phantom_count를 감소시키고 context에 소비량을 기록한다.

    YAML 형식:
      - type: consume_phantom
        count: 1  # 소비할 환영 수
    """

    def __init__(self, count: int = 1):
        super().__init__(EffectType.GIMMICK)
        self.count = count

    def execute(self, user, target, context) -> EffectResult:
        current = getattr(user, 'phantom_count', 0)
        consume = min(self.count, current)

        if consume > 0:
            user.phantom_count = max(0, current - consume)
            # phantom_hits 뒤에서부터 제거
            if hasattr(user, 'phantom_hits') and isinstance(user.phantom_hits, list):
                remove_count = min(consume, len(user.phantom_hits))
                user.phantom_hits = user.phantom_hits[:-remove_count] if remove_count > 0 else user.phantom_hits

        # context에 소비량 기록 (후속 이펙트에서 참조)
        if context is not None:
            context['phantoms_consumed'] = context.get('phantoms_consumed', 0) + consume

        logger.info(f"[환영 소비] {getattr(user, 'name', '?')} 환영 -{consume} (잔여: {getattr(user, 'phantom_count', 0)})")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'phantom_count': -consume},
            message=f"환영 소비 -{consume}"
        )


class PhantomEchoDamageEffect(SkillEffect):
    """환영 에코 데미지 - phantom_count에 비례한 추가 데미지를 입힌다.

    YAML 형식:
      - type: phantom_echo_damage
        per_phantom_multiplier: 0.25  # 환영당 데미지 배율
        damage_type: magic           # physical | magic
        stat_base: magic             # strength | magic
    """

    def __init__(self, per_phantom_multiplier: float = 0.25,
                 damage_type: str = "physical", stat_base: str = "physical"):
        super().__init__(EffectType.DAMAGE)
        self.per_phantom_multiplier = per_phantom_multiplier
        self.damage_type = damage_type
        self.stat_base = stat_base

    def execute(self, user, target, context) -> EffectResult:
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        phantom_count = getattr(user, 'phantom_count', 0)
        if phantom_count <= 0:
            result.message = "환영 없음 - 에코 데미지 0"
            return result

        targets = target if isinstance(target, list) else [target]
        total_damage = 0

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue

            # 스탯 기반 데미지 계산
            if self.stat_base in ("magic", "magical"):
                attack = getattr(user, 'magic_attack', 0) or getattr(user, 'magic', 0)
                if attack == 0 and hasattr(user, 'stat_manager'):
                    try:
                        from src.character.stats import Stats
                        attack = user.stat_manager.get_value(Stats.MAGIC)
                    except Exception:
                        pass
                defense = getattr(t, 'magic_defense', 0)
            else:
                attack = getattr(user, 'physical_attack', 0) or getattr(user, 'strength', 0)
                if attack == 0 and hasattr(user, 'stat_manager'):
                    try:
                        from src.character.stats import Stats
                        attack = user.stat_manager.get_value(Stats.STRENGTH)
                    except Exception:
                        pass
                defense = getattr(t, 'physical_defense', 0) or getattr(t, 'defense', 0)

            # 환영당 데미지 = (공격 - 방어) * per_phantom_multiplier
            for _ in range(phantom_count):
                raw = max(1, int((attack - defense * 0.5) * self.per_phantom_multiplier))
                variation = random.uniform(0.9, 1.1)
                dmg = max(1, int(raw * variation))
                t.current_hp = max(0, t.current_hp - dmg)
                total_damage += dmg
                if t.current_hp <= 0 and hasattr(t, 'is_alive'):
                    t.is_alive = False
                    break

        result.hp_damage = total_damage
        result.damage_dealt = total_damage
        result.message = f"환영 에코 {phantom_count}히트 - 총 {total_damage} 데미지"
        logger.info(f"[환영 에코] {getattr(user, 'name', '?')} {phantom_count}히트 → {total_damage} 데미지")
        return result


class ConsumeAllPhantomsEffect(SkillEffect):
    """모든 환영 소비 - phantom_count 전부 사용하고 context에 저장한다.

    YAML 형식:
      - type: consume_all_phantoms
        store_count: true  # context에 소비된 수를 저장
    """

    def __init__(self, store_count: bool = True):
        super().__init__(EffectType.GIMMICK)
        self.store_count = store_count

    def execute(self, user, target, context) -> EffectResult:
        current = getattr(user, 'phantom_count', 0)
        user.phantom_count = 0
        if hasattr(user, 'phantom_hits'):
            user.phantom_hits = []

        if context is not None and self.store_count:
            context['phantoms_consumed'] = current
            # 다단히트에서 사용할 수 있도록 power_multiplier 설정
            context['phantom_count_consumed'] = current

        logger.info(f"[환영 전소비] {getattr(user, 'name', '?')} 환영 {current}개 소비")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'phantom_count': -current},
            message=f"환영 전부 소비: {current}개"
        )


class PhantomBonusDebuffEffect(SkillEffect):
    """환영 수에 비례한 디버프 강화.

    YAML 형식:
      - type: phantom_bonus_debuff
        per_phantom_bonus: 0.05  # 환영당 디버프 강도 증가
        stat: accuracy           # 감소시킬 스탯
        max_bonus: 0.2           # 최대 보너스
    """

    def __init__(self, per_phantom_bonus: float = 0.05, stat: str = "accuracy",
                 max_bonus: float = 1.0):
        super().__init__(EffectType.BUFF)
        self.per_phantom_bonus = per_phantom_bonus
        self.stat = stat
        self.max_bonus = max_bonus

    def execute(self, user, target, context) -> EffectResult:
        phantom_count = getattr(user, 'phantom_count', 0)
        bonus = min(phantom_count * self.per_phantom_bonus, self.max_bonus)

        if bonus <= 0:
            return EffectResult(effect_type=EffectType.BUFF, success=True,
                                message="환영 없음 - 디버프 보너스 없음")

        targets = target if isinstance(target, list) else [target]
        debuff_type = f"{self.stat}_down"

        for t in targets:
            if not hasattr(t, 'active_buffs'):
                t.active_buffs = {}
            t.active_buffs[debuff_type] = {'value': bonus, 'duration': 3}

        logger.info(f"[환영 디버프] {self.stat} -{bonus*100:.0f}% (환영 {phantom_count}개)")
        return EffectResult(
            effect_type=EffectType.BUFF,
            success=True,
            message=f"환영 디버프: {self.stat} -{bonus*100:.0f}%"
        )


class PhantomConvergenceBonusEffect(SkillEffect):
    """환영 수렴 보너스 - 환영이 많을수록 데미지 증가.

    YAML 형식:
      - type: phantom_convergence_bonus
        per_phantom_bonus: 0.25  # 환영당 데미지 배율 증가
        max_bonus: 1.0           # 최대 보너스 배율
    """

    def __init__(self, per_phantom_bonus: float = 0.25, max_bonus: float = 1.0):
        super().__init__(EffectType.GIMMICK)
        self.per_phantom_bonus = per_phantom_bonus
        self.max_bonus = max_bonus

    def execute(self, user, target, context) -> EffectResult:
        phantom_count = getattr(user, 'phantom_count', 0)
        bonus = min(phantom_count * self.per_phantom_bonus, self.max_bonus)

        if context is not None:
            current_mult = context.get('power_multiplier', 1.0)
            context['power_multiplier'] = current_mult + bonus

        logger.info(f"[환영 수렴] 데미지 +{bonus*100:.0f}% (환영 {phantom_count}개)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"환영 수렴 보너스: +{bonus*100:.0f}%"
        )


class PhantomDamageRedirectEffect(SkillEffect):
    """환영 피해 대리 - 환영이 피해를 대신 받는 효과를 부여한다.

    YAML 형식:
      - type: phantom_damage_redirect
        redirect_percent: 0.5   # 대리 흡수 비율
        destroy_on_damage: true # 피해 시 환영 파괴
        duration: 3             # 지속 턴
    """

    def __init__(self, redirect_percent: float = 0.5,
                 destroy_on_damage: bool = True, duration: int = 3):
        super().__init__(EffectType.GIMMICK)
        self.redirect_percent = redirect_percent
        self.destroy_on_damage = destroy_on_damage
        self.duration = duration

    def execute(self, user, target, context) -> EffectResult:
        phantom_count = getattr(user, 'phantom_count', 0)
        if phantom_count <= 0:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="환영 없음 - 피해 대리 불가")

        # 캐릭터에 피해 대리 효과 등록
        user.phantom_redirect = {
            'redirect_percent': self.redirect_percent,
            'destroy_on_damage': self.destroy_on_damage,
            'duration': self.duration,
        }

        logger.info(f"[환영 방패] {getattr(user, 'name', '?')} 피해 {self.redirect_percent*100:.0f}% 대리 ({self.duration}턴)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"환영 방패: 피해 {self.redirect_percent*100:.0f}% 대리 ({self.duration}턴)"
        )


class PhantomPriorityEffect(SkillEffect):
    """환영 우선 타겟 설정 - 적이 환영을 먼저 공격하도록 설정한다.

    YAML 형식:
      - type: phantom_priority
        redirect_chance: 0.7  # 환영으로 리다이렉트 확률
    """

    def __init__(self, redirect_chance: float = 0.7):
        super().__init__(EffectType.GIMMICK)
        self.redirect_chance = redirect_chance

    def execute(self, user, target, context) -> EffectResult:
        phantom_count = getattr(user, 'phantom_count', 0)
        if phantom_count <= 0:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="환영 없음 - 우선 타겟 불가")

        user.phantom_priority = {
            'redirect_chance': self.redirect_chance,
            'active': True,
        }

        logger.info(f"[환영 도발] {getattr(user, 'name', '?')} 환영 우선 타겟 ({self.redirect_chance*100:.0f}%)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"환영 우선 타겟: {self.redirect_chance*100:.0f}% 확률"
        )


class PhantomCounterEffect(SkillEffect):
    """환영 카운터 - 피격 시 환영이 반격하는 효과를 부여한다.

    YAML 형식:
      - type: phantom_counter
        counter_chance: 0.25   # 반격 확률
        counter_damage: 0.5    # 반격 데미지 배율
        stat_base: strength    # 반격 스탯 기준
    """

    def __init__(self, counter_chance: float = 0.25, counter_damage: float = 0.5,
                 stat_base: str = "physical"):
        super().__init__(EffectType.GIMMICK)
        self.counter_chance = counter_chance
        self.counter_damage = counter_damage
        self.stat_base = stat_base

    def execute(self, user, target, context) -> EffectResult:
        phantom_count = getattr(user, 'phantom_count', 0)
        if phantom_count <= 0:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message="환영 없음 - 카운터 불가")

        user.phantom_counter = {
            'counter_chance': self.counter_chance,
            'counter_damage': self.counter_damage,
            'stat_base': self.stat_base,
            'active': True,
        }

        logger.info(f"[환영 반격] {getattr(user, 'name', '?')} 환영 카운터 설정 ({self.counter_chance*100:.0f}%)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"환영 카운터: {self.counter_chance*100:.0f}% 확률, {self.counter_damage}x 데미지"
        )
