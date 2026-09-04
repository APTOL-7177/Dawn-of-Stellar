"""Element Effect - 원소/변환 시스템 이펙트

overload: 과부하 (기믹 게이지 초과 소비로 강력한 효과)
transmutation: 변환 (원소 스택 변환)
thermal_shock: 열충격 (화염+냉기 연속 시 추가 데미지)
"""
import random

from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("element_effect")


class OverloadEffect(SkillEffect):
    """과부하 - 원소 스택을 대량 소비하여 강력한 상태이상을 적용한다.

    YAML 형식:
      - type: overload
        min_stacks: 3             # 최소 필요 스택
        fire_effect: burning      # 화염 과부하 효과
        ice_effect: frozen_solid  # 냉기 과부하 효과
        lightning_effect: stun    # 번개 과부하 효과
        stat_base: magic          # 데미지 스탯 기준
    """

    def __init__(self, min_stacks: int = 3, fire_effect: str = "burning",
                 ice_effect: str = "frozen_solid", lightning_effect: str = "stun",
                 stat_base: str = "magic"):
        super().__init__(EffectType.GIMMICK)
        self.min_stacks = min_stacks
        self.fire_effect = fire_effect
        self.ice_effect = ice_effect
        self.lightning_effect = lightning_effect
        self.stat_base = stat_base

    def execute(self, user, target, context) -> EffectResult:
        targets = target if isinstance(target, list) else [target]
        applied_effects = []

        # 원소 스택 확인 (정령술사/원소술사의 element_stacks 또는 rune 스택)
        element_fields = {
            'fire': ['rune_fire', 'fire_stacks', 'element_fire'],
            'ice': ['rune_ice', 'ice_stacks', 'element_ice'],
            'lightning': ['rune_lightning', 'lightning_stacks', 'element_lightning'],
        }

        effect_map = {
            'fire': self.fire_effect,
            'ice': self.ice_effect,
            'lightning': self.lightning_effect,
        }

        for element, fields in element_fields.items():
            stacks = 0
            used_field = None
            for field in fields:
                val = getattr(user, field, 0)
                if val > 0:
                    stacks = val
                    used_field = field
                    break

            if stacks < self.min_stacks:
                continue

            # 스택 소비
            if used_field:
                setattr(user, used_field, 0)

            # 효과 적용
            effect_name = effect_map.get(element, 'burning')
            for t in targets:
                if not getattr(t, 'is_alive', True):
                    continue
                if hasattr(t, 'status_manager'):
                    try:
                        from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
                        status_map = {
                            'burning': StatusType.BURNING,
                            'frozen_solid': StatusType.FROZEN_SOLID,
                            'stun': StatusType.STUN,
                            'burn': StatusType.BURN,
                            'freeze': StatusType.FREEZE,
                            'shock': StatusType.SHOCK,
                        }
                        st = status_map.get(effect_name, StatusType.BURN)
                        duration = min(2, 1 + stacks // 3)
                        effect = CombatStatusEffect(
                            name=effect_name.replace('_', ' ').title(),
                            status_type=st,
                            duration=duration,
                            intensity=stacks * 0.5,
                            source_id=getattr(user, 'name', None),
                        )
                        t.status_manager.add_status(effect, allow_refresh=True)
                    except Exception:
                        pass

            applied_effects.append(f"{element}({stacks})")

        if applied_effects:
            msg = f"과부하: {', '.join(applied_effects)}"
        else:
            msg = "과부하 조건 불충분"

        logger.info(f"[과부하] {getattr(user, 'name', '?')} {msg}")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=len(applied_effects) > 0,
            message=msg
        )


class TransmutationEffect(SkillEffect):
    """변환 - 원소 스택을 소비하고 다른 원소 스택을 생성한다.

    YAML 형식:
      - type: transmutation
        consume_amount: 2   # 소비할 스택 수
        generate_amount: 3  # 생성할 스택 수
        mp_recovery: 5      # MP 회복량
    """

    def __init__(self, consume_amount: int = 2, generate_amount: int = 3,
                 mp_recovery: int = 0):
        super().__init__(EffectType.GIMMICK)
        self.consume_amount = consume_amount
        self.generate_amount = generate_amount
        self.mp_recovery = mp_recovery

    def execute(self, user, target, context) -> EffectResult:
        # 원소 스택 필드 탐색
        element_fields = ['rune_fire', 'rune_ice', 'rune_lightning', 'rune_earth', 'rune_arcane',
                          'fire_stacks', 'ice_stacks', 'lightning_stacks',
                          'element_fire', 'element_ice', 'element_lightning', 'element_earth']

        # 가장 많은 스택을 가진 원소에서 소비
        best_field = None
        best_value = 0
        for field in element_fields:
            val = getattr(user, field, 0)
            if val > best_value:
                best_value = val
                best_field = field

        consumed = 0
        if best_field and best_value >= self.consume_amount:
            setattr(user, best_field, best_value - self.consume_amount)
            consumed = self.consume_amount

        # 가장 적은 스택의 다른 원소에 생성
        if consumed > 0:
            other_fields = [f for f in element_fields if f != best_field and hasattr(user, f)]
            if other_fields:
                # 가장 적은 스택의 필드 찾기
                min_field = min(other_fields, key=lambda f: getattr(user, f, 0))
                old_val = getattr(user, min_field, 0)
                max_val = getattr(user, f'max_{min_field}', 10)
                new_val = min(old_val + self.generate_amount, max_val)
                setattr(user, min_field, new_val)

        # MP 회복
        mp_restored = 0
        if self.mp_recovery > 0 and consumed > 0:
            old_mp = getattr(user, 'current_mp', 0)
            max_mp = getattr(user, 'max_mp', 100)
            user.current_mp = min(max_mp, old_mp + self.mp_recovery)
            mp_restored = user.current_mp - old_mp

        msg = f"변환: {consumed}스택 소비 → {self.generate_amount}스택 생성"
        if mp_restored > 0:
            msg += f" + MP +{mp_restored}"

        logger.info(f"[변환] {getattr(user, 'name', '?')} {msg}")
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=consumed > 0,
            heal_amount=mp_restored,
            message=msg
        )


class ThermalShockEffect(SkillEffect):
    """열충격 - 화염+냉기 연속 적용 시 추가 데미지.

    YAML 형식:
      - type: thermal_shock
        element:
        - fire
        - ice
        multiplier: 2.0             # 데미지 배율
        diff_bonus_per_stack: 0.15  # 스택 차이에 따른 보너스
    """

    def __init__(self, element: list = None, multiplier: float = 2.0,
                 diff_bonus_per_stack: float = 0.15):
        super().__init__(EffectType.DAMAGE)
        self.elements = element or ['fire', 'ice']
        self.multiplier = multiplier
        self.diff_bonus_per_stack = diff_bonus_per_stack

    def execute(self, user, target, context) -> EffectResult:
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        targets = target if isinstance(target, list) else [target]
        total_damage = 0

        # 화염/냉기 스택 차이 기반 보너스
        fire_stacks = (getattr(user, 'rune_fire', 0) or
                       getattr(user, 'fire_stacks', 0) or
                       getattr(user, 'element_fire', 0))
        ice_stacks = (getattr(user, 'rune_ice', 0) or
                      getattr(user, 'ice_stacks', 0) or
                      getattr(user, 'element_ice', 0))
        diff = abs(fire_stacks - ice_stacks)
        bonus = diff * self.diff_bonus_per_stack

        final_mult = self.multiplier + bonus

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
            raw = max(1, int((attack - defense * 0.5) * final_mult))
            dmg = max(1, int(raw * random.uniform(0.9, 1.1)))
            t.current_hp = max(0, t.current_hp - dmg)
            total_damage += dmg
            if t.current_hp <= 0 and hasattr(t, 'is_alive'):
                t.is_alive = False

        result.hp_damage = total_damage
        result.damage_dealt = total_damage
        result.message = f"열충격: {total_damage} 데미지 (배율 {final_mult:.1f}x)"
        logger.info(f"[열충격] {total_damage} 데미지 (스택 차이 {diff}, 보너스 +{bonus*100:.0f}%)")
        return result
