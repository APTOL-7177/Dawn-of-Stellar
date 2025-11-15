"""
Trait Effects - 특성 효과 시스템

특성(Trait)이 실제 게임플레이에 영향을 주도록 구현
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from src.core.logger import get_logger


class TraitType(Enum):
    """특성 타입"""
    PASSIVE = "passive"  # 항상 적용되는 효과
    TRIGGER = "trigger"  # 특정 조건에서 발동
    COMBAT = "combat"    # 전투 중 특정 시점에 발동


class TraitEffectType(Enum):
    """특성 효과 타입"""
    STAT_MULTIPLIER = "stat_multiplier"      # 스탯 배율 증가
    STAT_FLAT = "stat_flat"                  # 스탯 고정값 증가
    DAMAGE_MULTIPLIER = "damage_multiplier"  # 데미지 배율 증가
    MP_COST_REDUCTION = "mp_cost_reduction"  # MP 소모 감소
    HP_REGEN = "hp_regen"                    # HP 회복
    MP_REGEN = "mp_regen"                    # MP 회복
    CRITICAL_BONUS = "critical_bonus"        # 크리티컬 확률 증가
    BREAK_BONUS = "break_bonus"              # 브레이크 보너스 증가
    ATB_BOOST = "atb_boost"                  # ATB 게이지 증가
    COUNTER = "counter"                      # 반격
    REVIVE = "revive"                        # 부활


@dataclass
class TraitEffect:
    """특성 효과"""
    trait_id: str
    effect_type: TraitEffectType
    value: float
    condition: Optional[str] = None
    target_stat: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TraitEffectManager:
    """
    특성 효과 관리자

    캐릭터의 활성화된 특성들을 관리하고 효과를 적용합니다.
    """

    def __init__(self):
        self.logger = get_logger("trait_effects")

        # 특성별 효과 정의
        self.trait_definitions = self._load_trait_definitions()

    def _load_trait_definitions(self) -> Dict[str, List[TraitEffect]]:
        """특성별 효과 정의 로드"""
        # passives.yaml의 패시브 스킬 정의
        passives = {
            # 코스트 2 패시브
            "hp_boost": [
                TraitEffect(
                    trait_id="hp_boost",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="hp"
                )
            ],
            "mp_boost": [
                TraitEffect(
                    trait_id="mp_boost",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="mp"
                )
            ],
            "speed_boost": [
                TraitEffect(
                    trait_id="speed_boost",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.12,
                    target_stat="speed"
                )
            ],
            "brv_boost": [
                TraitEffect(
                    trait_id="brv_boost",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="init_brv"
                )
            ],
            "accuracy_boost": [
                TraitEffect(
                    trait_id="accuracy_boost",
                    effect_type=TraitEffectType.STAT_FLAT,
                    value=10,
                    target_stat="accuracy"
                )
            ],
            "evasion_boost": [
                TraitEffect(
                    trait_id="evasion_boost",
                    effect_type=TraitEffectType.STAT_FLAT,
                    value=10,
                    target_stat="evasion"
                )
            ],

            # 코스트 3 패시브
            "physical_power": [
                TraitEffect(
                    trait_id="physical_power",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.20,
                    target_stat="physical"
                )
            ],
            "magic_power": [
                TraitEffect(
                    trait_id="magic_power",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.20,
                    target_stat="magic"
                )
            ],
            "physical_guard": [
                TraitEffect(
                    trait_id="physical_guard",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    target_stat="physical_defense"
                )
            ],
            "magic_guard": [
                TraitEffect(
                    trait_id="magic_guard",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    target_stat="magic_defense"
                )
            ],
            "critical_boost": [
                TraitEffect(
                    trait_id="critical_boost",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.15
                )
            ],
            "counter_stance": [
                TraitEffect(
                    trait_id="counter_stance",
                    effect_type=TraitEffectType.COUNTER,
                    value=0.15,
                    condition="on_hit"
                )
            ],
            "auto_regen": [
                TraitEffect(
                    trait_id="auto_regen",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.05,
                    condition="turn_start"
                )
            ],
            "mp_recovery": [
                TraitEffect(
                    trait_id="mp_recovery",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=0.03,
                    condition="turn_start"
                )
            ],

            # 코스트 4 패시브
            "first_strike": [
                TraitEffect(
                    trait_id="first_strike",
                    effect_type=TraitEffectType.ATB_BOOST,
                    value=500,
                    condition="combat_start"
                )
            ],
            "break_master": [
                TraitEffect(
                    trait_id="break_master",
                    effect_type=TraitEffectType.BREAK_BONUS,
                    value=1.5
                )
            ],
            "skill_master": [
                TraitEffect(
                    trait_id="skill_master",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=0.20
                )
            ],
            "hp_danger_boost": [
                TraitEffect(
                    trait_id="hp_danger_boost",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,
                    condition="hp_below_30",
                    target_stat="all_attack"
                )
            ],
            "shield_mastery": [
                TraitEffect(
                    trait_id="shield_mastery",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.50,
                    condition="defending",
                    metadata={"brv_regen": 0.10}
                )
            ],
            "element_mastery": [
                TraitEffect(
                    trait_id="element_mastery",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.25,
                    target_stat="elemental"
                )
            ],

            # 코스트 5 패시브
            "phoenix_blessing": [
                TraitEffect(
                    trait_id="phoenix_blessing",
                    effect_type=TraitEffectType.REVIVE,
                    value=0.5,
                    condition="on_death"
                )
            ],
            "double_cast": [
                TraitEffect(
                    trait_id="double_cast",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.10,
                    condition="skill_cast",
                    metadata={"double_chance": 0.10}
                )
            ],
            "ultimate_power": [
                TraitEffect(
                    trait_id="ultimate_power",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    target_stat="physical"
                ),
                TraitEffect(
                    trait_id="ultimate_power",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    target_stat="magic"
                )
            ],
            "ultimate_defense": [
                TraitEffect(
                    trait_id="ultimate_defense",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    target_stat="physical_defense"
                ),
                TraitEffect(
                    trait_id="ultimate_defense",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    target_stat="magic_defense"
                )
            ],
            "brave_soul": [
                TraitEffect(
                    trait_id="brave_soul",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.80,  # 받는 피해 -20% = 0.80 배율
                    condition="hp_above_50",
                    target_stat="damage_taken"
                ),
                TraitEffect(
                    trait_id="brave_soul",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.20,
                    condition="hp_above_50",
                    target_stat="brv_attack"
                )
            ],
            "tactical_genius": [
                TraitEffect(
                    trait_id="tactical_genius",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.0,
                    condition="turn_count_5",
                    metadata={"buff_duration": 2, "buff_power": 1.30}
                )
            ],
        }

        # 직업별 특성 정의 (전사 예시)
        job_traits = {
            "adaptive_combat": [
                TraitEffect(
                    trait_id="adaptive_combat",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    condition="stance_changed",
                    target_stat="next_attack"
                )
            ],
            "battlefield_master": [
                TraitEffect(
                    trait_id="battlefield_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.05,
                    condition="same_stance_per_turn",
                    metadata={"max_stacks": 7, "max_bonus": 1.35}  # 최대 35% (7턴 * 5%)
                )
            ],
            "indomitable_will": [
                TraitEffect(
                    trait_id="indomitable_will",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.08,
                    condition="turn_start"
                )
            ],
            "combat_instinct": [
                TraitEffect(
                    trait_id="combat_instinct",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=1.0,  # 100% 감소 = MP 소모 없음
                    condition="stance_change_skill"
                )
            ],
            "complete_mastery": [
                TraitEffect(
                    trait_id="complete_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="all_stats_in_stance"
                )
            ],

            # 저격수 특성
            "focus_power": [
                TraitEffect(
                    trait_id="focus_power",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,  # 50% 증가
                    condition="defend_stack",
                    metadata={"max_stacks": 3, "per_stack": 0.50}  # 최대 3스택, 스택당 50%
                )
            ],
            "steady_hands": [
                TraitEffect(
                    trait_id="steady_hands",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=100.0,  # 100% 명중률
                    target_stat="accuracy"
                ),
                TraitEffect(
                    trait_id="steady_hands",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,  # 회피율 -50%
                    target_stat="evasion"
                )
            ],

            # 마검사 특성
            "combat_casting": [
                TraitEffect(
                    trait_id="combat_casting",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,  # 시전 시간 -50%
                    target_stat="cast_time"
                )
            ],

            # 기계공학자 특성
            "emergency_repair": [
                TraitEffect(
                    trait_id="emergency_repair",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.0,  # 장비 효과 2배
                    condition="hp_below_50",
                    target_stat="equipment_bonus"
                )
            ],
        }

        # 통합
        return {**passives, **job_traits}

    def get_trait_effects(self, trait_id: str) -> List[TraitEffect]:
        """특성 ID로 효과 리스트 가져오기"""
        return self.trait_definitions.get(trait_id, [])

    def calculate_stat_bonus(
        self,
        character: Any,
        stat_name: str,
        base_value: float
    ) -> float:
        """
        특성에 의한 스탯 보너스 계산

        Args:
            character: 캐릭터
            stat_name: 스탯 이름
            base_value: 기본 스탯 값

        Returns:
            보너스 적용된 최종 값
        """
        if not hasattr(character, 'active_traits'):
            return base_value

        final_value = base_value

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                # 조건 확인
                if effect.condition and not self._check_condition(character, effect.condition):
                    continue

                # 스탯 타겟 확인
                if effect.target_stat and effect.target_stat != stat_name:
                    continue

                # 효과 적용
                if effect.effect_type == TraitEffectType.STAT_MULTIPLIER:
                    final_value *= effect.value
                    self.logger.debug(
                        f"[{trait_id}] {stat_name} 배율 적용: x{effect.value} → {final_value}"
                    )
                elif effect.effect_type == TraitEffectType.STAT_FLAT:
                    final_value += effect.value
                    self.logger.debug(
                        f"[{trait_id}] {stat_name} 고정값 적용: +{effect.value} → {final_value}"
                    )

        return final_value

    def calculate_damage_multiplier(
        self,
        character: Any,
        damage_type: str = "physical",
        **context
    ) -> float:
        """
        특성에 의한 데미지 배율 계산

        Args:
            character: 캐릭터
            damage_type: 데미지 타입 (physical, magic, brv_attack 등)
            **context: 컨텍스트 정보 (스킬, 대상 등)

        Returns:
            총 데미지 배율 (1.0 = 100%)
        """
        if not hasattr(character, 'active_traits'):
            return 1.0

        total_multiplier = 1.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type != TraitEffectType.DAMAGE_MULTIPLIER:
                    continue

                # 조건 확인
                if effect.condition and not self._check_condition(character, effect.condition, context):
                    continue

                # 타겟 확인
                if effect.target_stat:
                    # 데미지 타입이 맞는지 확인
                    if effect.target_stat == damage_type:
                        total_multiplier *= effect.value
                    elif effect.target_stat == "all_attack":
                        total_multiplier *= effect.value
                    elif effect.target_stat == "elemental" and context.get("is_elemental"):
                        total_multiplier *= effect.value
                    elif effect.target_stat == "next_attack":
                        # 다음 공격에만 적용
                        total_multiplier *= effect.value
                else:
                    # 타겟이 없으면 모든 데미지에 적용
                    total_multiplier *= effect.value

                self.logger.debug(
                    f"[{trait_id}] 데미지 배율 적용: x{effect.value} → 총 x{total_multiplier}"
                )

        return total_multiplier

    def calculate_mp_cost(self, character: Any, base_cost: int, **context) -> int:
        """
        특성에 의한 MP 소모 계산

        Args:
            character: 캐릭터
            base_cost: 기본 MP 소모
            **context: 컨텍스트 (스킬 정보 등)

        Returns:
            최종 MP 소모
        """
        if not hasattr(character, 'active_traits'):
            return base_cost

        reduction_rate = 0.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type != TraitEffectType.MP_COST_REDUCTION:
                    continue

                # 조건 확인
                if effect.condition and not self._check_condition(character, effect.condition, context):
                    continue

                reduction_rate += effect.value
                self.logger.debug(f"[{trait_id}] MP 감소: {effect.value * 100}%")

        # 최대 100% 감소
        reduction_rate = min(1.0, reduction_rate)

        final_cost = int(base_cost * (1.0 - reduction_rate))

        if reduction_rate > 0:
            self.logger.info(
                f"MP 소모 감소: {base_cost} → {final_cost} (-{int(reduction_rate * 100)}%)"
            )

        return max(0, final_cost)

    def calculate_critical_bonus(self, character: Any) -> float:
        """
        특성에 의한 크리티컬 확률 보너스

        Args:
            character: 캐릭터

        Returns:
            크리티컬 확률 보너스 (0.15 = +15%)
        """
        if not hasattr(character, 'active_traits'):
            return 0.0

        bonus = 0.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type == TraitEffectType.CRITICAL_BONUS:
                    bonus += effect.value
                    self.logger.debug(f"[{trait_id}] 크리티컬 보너스: +{effect.value * 100}%")

        return bonus

    def calculate_break_bonus(self, character: Any) -> float:
        """
        특성에 의한 브레이크 보너스 배율

        Args:
            character: 캐릭터

        Returns:
            브레이크 보너스 배율 (1.5 = 150%)
        """
        if not hasattr(character, 'active_traits'):
            return 0.0

        bonus = 0.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type == TraitEffectType.BREAK_BONUS:
                    bonus += effect.value
                    self.logger.debug(f"[{trait_id}] 브레이크 보너스: +{effect.value}")

        return bonus

    def apply_turn_start_effects(self, character: Any):
        """
        턴 시작 시 특성 효과 적용 (HP/MP 회복 등)

        Args:
            character: 캐릭터
        """
        if not hasattr(character, 'active_traits'):
            return

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                # 턴 시작 조건 확인
                if effect.condition != "turn_start":
                    continue

                # HP 회복
                if effect.effect_type == TraitEffectType.HP_REGEN:
                    heal_amount = int(character.max_hp * effect.value)
                    if hasattr(character, 'heal'):
                        actual = character.heal(heal_amount)
                        self.logger.info(
                            f"[{trait_id}] {character.name} HP 회복: {actual} ({effect.value * 100}%)"
                        )

                # MP 회복
                elif effect.effect_type == TraitEffectType.MP_REGEN:
                    mp_amount = int(character.max_mp * effect.value)
                    if hasattr(character, 'restore_mp'):
                        actual = character.restore_mp(mp_amount)
                        self.logger.info(
                            f"[{trait_id}] {character.name} MP 회복: {actual} ({effect.value * 100}%)"
                        )

    def _check_condition(
        self,
        character: Any,
        condition: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        조건 확인

        Args:
            character: 캐릭터
            condition: 조건 문자열
            context: 컨텍스트 정보

        Returns:
            조건 만족 여부
        """
        context = context or {}

        # HP 조건
        if condition == "hp_below_30":
            if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
                return character.current_hp / character.max_hp < 0.30

        elif condition == "hp_below_50":
            if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
                return character.current_hp / character.max_hp < 0.50

        elif condition == "hp_above_50":
            if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
                return character.current_hp / character.max_hp >= 0.50

        # 방어 스택 조건 (저격수 특성)
        elif condition == "defend_stack":
            if hasattr(character, 'defend_stack_count'):
                return character.defend_stack_count > 0
            return False

        # 스탠스 변경
        elif condition == "stance_changed":
            return context.get("stance_changed", False)

        elif condition == "same_stance_per_turn":
            # 전사 특성: 같은 스탠스 유지 시 누적
            # 스탠스 카운터: character.stance_counter (같은 스탠스 유지 턴 수)
            if hasattr(character, 'stance_counter'):
                # 스탠스가 변경되지 않았으면 카운터 증가
                current_stance = getattr(character, 'current_stance', None)
                previous_stance = getattr(character, 'previous_stance', None)

                if current_stance and current_stance == previous_stance:
                    character.stance_counter = getattr(character, 'stance_counter', 0) + 1
                    return True
                else:
                    # 스탠스 변경 시 카운터 리셋
                    character.stance_counter = 1
                    character.previous_stance = current_stance
                    return False
            else:
                # 스탠스 시스템이 없으면 기본 True
                return True

        elif condition == "stance_change_skill":
            # 스탠스 변경 스킬인지 확인
            skill = context.get("skill")
            if skill and hasattr(skill, 'skill_id'):
                return "stance" in skill.skill_id.lower()
            return False

        # 전투 시작
        elif condition == "combat_start":
            return context.get("combat_start", False)

        # 스킬 시전
        elif condition == "skill_cast":
            return context.get("is_skill", False)

        # 방어 중
        elif condition == "defending":
            return context.get("is_defending", False)

        # 피격 시
        elif condition == "on_hit":
            return context.get("on_hit", False)

        # 사망 시
        elif condition == "on_death":
            return context.get("on_death", False)

        # 턴 카운트
        elif condition.startswith("turn_count_"):
            turn_mod = int(condition.split("_")[-1])
            turn_count = context.get("turn_count", 0)
            return turn_count > 0 and turn_count % turn_mod == 0

        # 기본적으로 조건 만족
        return True


# 전역 인스턴스
_trait_effect_manager: Optional[TraitEffectManager] = None


def get_trait_effect_manager() -> TraitEffectManager:
    """전역 특성 효과 관리자 인스턴스"""
    global _trait_effect_manager
    if _trait_effect_manager is None:
        _trait_effect_manager = TraitEffectManager()
    return _trait_effect_manager
