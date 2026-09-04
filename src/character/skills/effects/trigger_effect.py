"""Trigger Effect - 상태이상/트리거 시스템 이펙트

on_evade_trigger: 회피 시 트리거 효과 등록
apply_trap: 함정 설치 (적 행동 시 발동)
brand: 낙인 (피격 시 추가 데미지)
electrocution: 감전 (행동 시 피해)
glyph: 글리프 (지연 발동 효과)
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("trigger_effect")


class OnEvadeTriggerEffect(SkillEffect):
    """회피 시 트리거 - 회피 성공 시 추가 효과를 발동하는 버프를 부여한다.

    YAML 형식:
      - type: on_evade_trigger
        effect: summon_phantom  # 발동 효과 (summon_phantom | restore_phantom)
        count: 1                # 효과 수량
        duration: 3             # 지속 턴
    """

    def __init__(self, effect: str = "summon_phantom", count: int = 1,
                 duration: int = 3):
        super().__init__(EffectType.GIMMICK)
        self.trigger_effect = effect
        self.count = count
        self.duration = duration

    def execute(self, user, target, context) -> EffectResult:
        # 캐릭터에 회피 트리거 등록
        if not hasattr(user, 'evade_triggers'):
            user.evade_triggers = []

        user.evade_triggers.append({
            'effect': self.trigger_effect,
            'count': self.count,
            'duration': self.duration,
        })

        logger.info(f"[회피 트리거] {getattr(user, 'name', '?')} 회피 시 {self.trigger_effect} 발동 ({self.duration}턴)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=f"회피 트리거: {self.trigger_effect} ({self.duration}턴)"
        )


class ApplyTrapEffect(SkillEffect):
    """함정 설치 - 적이 행동 시 발동하는 함정을 설치한다.

    YAML 형식:
      - type: apply_trap
        trap_type: mirror_reflect  # 함정 타입
        duration: 2                # 지속 턴
        trigger_chance: 0.3        # 발동 확률
        reflect_ratio: 0.4         # 반사 비율
        damage_type: magic         # 피해 타입
    """

    def __init__(self, trap_type: str = "mirror_reflect", duration: int = 2,
                 trigger_chance: float = 0.3, reflect_ratio: float = 0.4,
                 damage_type: str = "magic"):
        super().__init__(EffectType.GIMMICK)
        self.trap_type = trap_type
        self.duration = duration
        self.trigger_chance = trigger_chance
        self.reflect_ratio = reflect_ratio
        self.damage_type = damage_type

    def execute(self, user, target, context) -> EffectResult:
        targets = target if isinstance(target, list) else [target]
        applied = 0

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            if not hasattr(t, 'active_traps'):
                t.active_traps = []

            t.active_traps.append({
                'trap_type': self.trap_type,
                'duration': self.duration,
                'trigger_chance': self.trigger_chance,
                'reflect_ratio': self.reflect_ratio,
                'damage_type': self.damage_type,
                'source': user,
            })
            applied += 1

        logger.info(f"[함정 설치] {getattr(user, 'name', '?')} {self.trap_type} 설치 ({applied}명)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=applied > 0,
            message=f"함정 설치: {self.trap_type} ({self.duration}턴, {self.trigger_chance*100:.0f}% 발동)"
        )


class BrandEffect(SkillEffect):
    """낙인 - 피격 시 추가 데미지를 받는 낙인을 새긴다.

    YAML 형식:
      - type: brand
        vulnerability: 0.4  # 추가 피해 비율
        duration: 5         # 지속 턴
        brands:             # 원소 낙인 목록
        - fire
        - ice
        - lightning
    """

    def __init__(self, vulnerability: float = 0.4, duration: int = 5,
                 brands: list = None):
        super().__init__(EffectType.BUFF)
        self.vulnerability = vulnerability
        self.duration = duration
        self.brands = brands or []

    def execute(self, user, target, context) -> EffectResult:
        targets = target if isinstance(target, list) else [target]
        applied = 0

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            if not hasattr(t, 'active_brands'):
                t.active_brands = []

            for brand_element in (self.brands or ['generic']):
                t.active_brands.append({
                    'element': brand_element,
                    'vulnerability': self.vulnerability,
                    'duration': self.duration,
                    'source': getattr(user, 'name', None),
                })

            # active_buffs에 취약 디버프 등록 (기존 시스템 호환)
            if not hasattr(t, 'active_buffs'):
                t.active_buffs = {}
            t.active_buffs['vulnerability'] = {
                'value': self.vulnerability,
                'duration': self.duration,
            }
            applied += 1

        brand_str = ', '.join(self.brands) if self.brands else '일반'
        logger.info(f"[낙인] {applied}명에게 {brand_str} 낙인 (취약 +{self.vulnerability*100:.0f}%, {self.duration}턴)")
        return EffectResult(
            effect_type=EffectType.BUFF,
            success=applied > 0,
            message=f"낙인({brand_str}): 취약 +{self.vulnerability*100:.0f}% ({self.duration}턴)"
        )


class ElectrocutionEffect(SkillEffect):
    """감전 - 복합 원소 데미지 (화염+냉기+번개 등).

    YAML 형식:
      - type: electrocution
        element:
        - ice
        - lightning
        brv_multiplier: 2.2  # BRV 데미지 배율
        hp_multiplier: 1.2   # HP 데미지 배율
    """

    def __init__(self, element: list = None, brv_multiplier: float = 1.0,
                 hp_multiplier: float = 1.0):
        super().__init__(EffectType.DAMAGE)
        self.elements = element or []
        self.brv_multiplier = brv_multiplier
        self.hp_multiplier = hp_multiplier

    def execute(self, user, target, context) -> EffectResult:
        import random as rng
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        targets = target if isinstance(target, list) else [target]
        total_damage = 0

        # 마법 공격력 사용
        attack = getattr(user, 'magic_attack', 0) or getattr(user, 'magic', 0)
        if attack == 0 and hasattr(user, 'stat_manager'):
            try:
                from src.character.stats import Stats
                attack = user.stat_manager.get_value(Stats.MAGIC)
            except Exception:
                pass

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            defense = getattr(t, 'magic_defense', 0)

            # BRV 데미지
            brv_raw = max(1, int((attack - defense * 0.5) * self.brv_multiplier))
            brv_dmg = max(1, int(brv_raw * rng.uniform(0.9, 1.1)))
            t.current_brv = max(0, getattr(t, 'current_brv', 0) - brv_dmg)
            user.current_brv = getattr(user, 'current_brv', 0) + brv_dmg

            # HP 데미지
            hp_raw = max(1, int((attack - defense * 0.5) * self.hp_multiplier))
            hp_dmg = max(1, int(hp_raw * rng.uniform(0.9, 1.1)))
            t.current_hp = max(0, t.current_hp - hp_dmg)
            total_damage += brv_dmg + hp_dmg

            if t.current_hp <= 0 and hasattr(t, 'is_alive'):
                t.is_alive = False

        result.brv_damage = total_damage // 2
        result.hp_damage = total_damage - result.brv_damage
        result.damage_dealt = total_damage
        element_str = '+'.join(self.elements) if self.elements else '복합'
        result.message = f"{element_str} 감전: {total_damage} 데미지"
        logger.info(f"[감전] {element_str} → {total_damage} 데미지")
        return result


class GlyphEffect(SkillEffect):
    """글리프 - 지연 발동 효과를 설치한다.

    YAML 형식:
      - type: glyph
        delay_turns: 3   # 발동까지 남은 턴
        max_glyphs: 3    # 최대 글리프 수
    """

    def __init__(self, delay_turns: int = 3, max_glyphs: int = 3):
        super().__init__(EffectType.GIMMICK)
        self.delay_turns = delay_turns
        self.max_glyphs = max_glyphs

    def execute(self, user, target, context) -> EffectResult:
        if not hasattr(user, 'active_glyphs'):
            user.active_glyphs = []

        if len(user.active_glyphs) >= self.max_glyphs:
            return EffectResult(effect_type=EffectType.GIMMICK, success=True,
                                message=f"글리프 최대치 ({self.max_glyphs})")

        # 스킬 정보 저장
        skill = context.get('skill') if context else None
        skill_id = getattr(skill, 'skill_id', None) or getattr(skill, 'id', 'unknown')

        user.active_glyphs.append({
            'skill_id': skill_id,
            'delay_turns': self.delay_turns,
            'source': getattr(user, 'name', None),
        })

        current_count = len(user.active_glyphs)
        logger.info(f"[글리프] {getattr(user, 'name', '?')} 글리프 설치 ({current_count}/{self.max_glyphs}, {self.delay_turns}턴 후 발동)")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'active_glyphs': 1},
            message=f"글리프 설치: {self.delay_turns}턴 후 발동 ({current_count}/{self.max_glyphs})"
        )
