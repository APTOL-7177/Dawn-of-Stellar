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
    DAMAGE_REDUCTION = "damage_reduction"    # 받는 피해 감소
    MP_COST_REDUCTION = "mp_cost_reduction"  # MP 소모 감소
    HP_REGEN = "hp_regen"                    # HP 회복
    MP_REGEN = "mp_regen"                    # MP 회복
    CRITICAL_BONUS = "critical_bonus"        # 크리티컬 확률 증가
    CRITICAL_DAMAGE = "critical_damage"      # 크리티컬 데미지 증가
    BREAK_BONUS = "break_bonus"              # 브레이크 보너스 증가
    ATB_BOOST = "atb_boost"                  # ATB 게이지 증가
    COUNTER = "counter"                      # 반격
    REVIVE = "revive"                        # 부활
    LIFESTEAL = "lifesteal"                  # 생명력 흡수
    MANA_LEECH = "mana_leech"                # 마력 흡수
    ON_KILL = "on_kill"                      # 적 처치 시 효과
    STATUS_RESIST = "status_resist"          # 상태 저항
    DOUBLE_ATTACK = "double_attack"          # 이중 공격
    DOUBLE_CAST = "double_cast"              # 이중 시전
    RETALIATION = "retaliation"              # 보복 (피해 받을 때 공격력 증가)
    HP_SCALING_ATTACK = "hp_scaling_attack"  # HP에 따른 공격력 증가
    GUARDIAN = "guardian"                    # 수호 (아군 피해 대신 받기)
    PERIODIC_BUFF = "periodic_buff"          # 주기적 버프
    LAST_STAND = "last_stand"                # 최후의 일격
    KILL_BONUS = "kill_bonus"                # 처치 보너스
    STATUS_CLEANSE = "status_cleanse"        # 상태 해제
    COOLDOWN_REDUCTION = "cooldown_reduction" # 쿨타임 감소
    DEFEND_BOOST = "defend_boost"            # 방어 보너스
    ALL_STATS_MULTIPLIER = "all_stats_multiplier"  # 모든 스탯 배율


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
                    target_stat="speed"  # 전투 행동 속도 (ATB에 영향)
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
            "luck_boost": [
                TraitEffect(
                    trait_id="luck_boost",
                    effect_type=TraitEffectType.STAT_FLAT,
                    value=10,
                    target_stat="luck"
                )
            ],
            "quick_step": [
                TraitEffect(
                    trait_id="quick_step",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="max_brv"
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
            "battle_heal": [
                TraitEffect(
                    trait_id="battle_heal",
                    effect_type=TraitEffectType.ON_KILL,
                    value=0.10,
                    metadata={"heal_type": "hp"}
                )
            ],
            "battle_mp": [
                TraitEffect(
                    trait_id="battle_mp",
                    effect_type=TraitEffectType.ON_KILL,
                    value=0.05,
                    metadata={"heal_type": "mp"}
                )
            ],
            "damage_reduction": [
                TraitEffect(
                    trait_id="damage_reduction",
                    effect_type=TraitEffectType.DAMAGE_REDUCTION,
                    value=0.10
                )
            ],
            "status_resist": [
                TraitEffect(
                    trait_id="status_resist",
                    effect_type=TraitEffectType.STATUS_RESIST,
                    value=0.15
                )
            ],

            # 코스트 4 패시브
            "first_strike": [
                TraitEffect(
                    trait_id="first_strike",
                    effect_type=TraitEffectType.ATB_BOOST,
                    value=0.50,  # 50% = 0.50
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
                    effect_type=TraitEffectType.DEFEND_BOOST,
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
            "critical_master": [
                TraitEffect(
                    trait_id="critical_master",
                    effect_type=TraitEffectType.CRITICAL_DAMAGE,
                    value=1.50
                )
            ],
            "double_hit": [
                TraitEffect(
                    trait_id="double_hit",
                    effect_type=TraitEffectType.DOUBLE_ATTACK,
                    value=0.25,
                    condition="normal_attack"
                )
            ],
            "lifesteal": [
                TraitEffect(
                    trait_id="lifesteal",
                    effect_type=TraitEffectType.LIFESTEAL,
                    value=0.10
                )
            ],
            "mana_leech": [
                TraitEffect(
                    trait_id="mana_leech",
                    effect_type=TraitEffectType.MANA_LEECH,
                    value=0.05
                )
            ],
            "retaliation": [
                TraitEffect(
                    trait_id="retaliation",
                    effect_type=TraitEffectType.RETALIATION,
                    value=0.05,
                    metadata={"max_stacks": 3}
                )
            ],
            "berserker_rage": [
                TraitEffect(
                    trait_id="berserker_rage",
                    effect_type=TraitEffectType.HP_SCALING_ATTACK,
                    value=0.50,
                    metadata={"max_bonus": 0.50}
                )
            ],
            "guardian_angel": [
                TraitEffect(
                    trait_id="guardian_angel",
                    effect_type=TraitEffectType.GUARDIAN,
                    value=0.20,  # 발동 확률 (20%)
                    condition="ally_damaged",
                    metadata={"protection_ratio": 1.0}  # 보호받을 피해 비율 (100% = 전체 피해 대신 받기)
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
                    effect_type=TraitEffectType.DOUBLE_CAST,
                    value=0.10,
                    condition="skill_cast"
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
                    effect_type=TraitEffectType.DAMAGE_REDUCTION,
                    value=0.20,
                    condition="hp_above_50"
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
                    effect_type=TraitEffectType.PERIODIC_BUFF,
                    value=0.30,
                    condition="turn_count_5",
                    metadata={"interval": 5, "duration": 2}
                )
            ],
            "time_master": [
                TraitEffect(
                    trait_id="time_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.25,
                    target_stat="speed"
                ),
                TraitEffect(
                    trait_id="time_master",
                    effect_type=TraitEffectType.COOLDOWN_REDUCTION,
                    value=0.10
                )
            ],
            "perfect_form": [
                TraitEffect(
                    trait_id="perfect_form",
                    effect_type=TraitEffectType.ALL_STATS_MULTIPLIER,
                    value=1.15
                )
            ],
            "unbreakable": [
                TraitEffect(
                    trait_id="unbreakable",
                    effect_type=TraitEffectType.LAST_STAND,
                    value=1.0,
                    condition="on_death",
                    metadata={"once_per_battle": True}
                )
            ],
            "master_counter": [
                TraitEffect(
                    trait_id="master_counter",
                    effect_type=TraitEffectType.COUNTER,
                    value=0.30,
                    condition="on_hit",
                    metadata={"damage_multiplier": 2.0}
                )
            ],
            "bloodthirst": [
                TraitEffect(
                    trait_id="bloodthirst",
                    effect_type=TraitEffectType.KILL_BONUS,
                    value=0.10,
                    metadata={"max_stacks": 3}
                )
            ],
            "eternal_flame": [
                TraitEffect(
                    trait_id="eternal_flame",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.10,
                    condition="turn_start"
                ),
                TraitEffect(
                    trait_id="eternal_flame",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=0.10,
                    condition="turn_start"
                ),
                TraitEffect(
                    trait_id="eternal_flame",
                    effect_type=TraitEffectType.STATUS_CLEANSE,
                    value=1.0,
                    condition="turn_start"
                )
            ],
        }

        # 직업별 특성 정의
        job_traits = {
            # === WARRIOR (전사) ===
            "adaptive_combat": [
                TraitEffect(
                    trait_id="adaptive_combat",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    condition="stance_changed",
                    target_stat="next_attack",
                    metadata={"description": "전투 중 자세 변경 시 다음 공격 위력 30% 증가"}
                )
            ],
            "battlefield_master": [
                TraitEffect(
                    trait_id="battlefield_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.05,
                    condition="same_stance_per_turn",
                    metadata={"max_stacks": 7, "max_bonus": 1.35, "description": "같은 자세 유지 시 턴마다 능력치 누적 증가 (최대 35%)"}
                )
            ],
            "indomitable_will": [
                TraitEffect(
                    trait_id="indomitable_will",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.08,
                    condition="turn_start",
                    metadata={"description": "모든 자세에서 매 턴 HP 8% 회복"}
                )
            ],
            "combat_instinct": [
                TraitEffect(
                    trait_id="combat_instinct",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=1.0,
                    condition="stance_change_skill",
                    metadata={"description": "자세 변경 스킬 MP 소모 없음"}
                )
            ],
            "complete_mastery": [
                TraitEffect(
                    trait_id="complete_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="all_stats_in_stance",
                    metadata={"description": "6가지 자세 완전 숙달로 모든 자세에서 특화 보너스 획득"}
                )
            ],

            # === SNIPER (저격수) ===
            "last_bullet": [
                TraitEffect(
                    trait_id="last_bullet",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.50,
                    condition="last_bullet",
                    metadata={"description": "마지막 탄환 크리티컬 확률 +50%"}
                ),
                TraitEffect(
                    trait_id="last_bullet",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    condition="last_bullet",
                    metadata={"description": "마지막 탄환 데미지 +30%"}
                )
            ],
            "quick_hands": [
                TraitEffect(
                    trait_id="quick_hands",
                    effect_type=TraitEffectType.ATB_BOOST,
                    value=1000,
                    condition="reload_skill",
                    metadata={"max_uses": 2, "description": "재장전 시 턴을 소모하지 않음 (전투당 2회)"}
                )
            ],
            "bullet_conservation": [
                TraitEffect(
                    trait_id="bullet_conservation",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.30,
                    target_stat="bullet_save_chance",
                    metadata={"description": "30% 확률로 탄환 소모하지 않음"}
                )
            ],
            "precision_aim": [
                TraitEffect(
                    trait_id="precision_aim",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,
                    condition="special_bullet",
                    metadata={"description": "특수 탄환 사용 시 효과 +50%"}
                )
            ],
            "headshot_master": [
                TraitEffect(
                    trait_id="headshot_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.05,
                    condition="on_critical",
                    target_stat="instant_kill_chance",
                    metadata={"description": "크리티컬 시 즉사 확률 5% (보스 제외)"}
                )
            ],

            # === SPELLBLADE (마검사) ===
            "magic_blade_unity": [
                TraitEffect(
                    trait_id="magic_blade_unity",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.50,
                    target_stat="physical_with_magic",
                    metadata={"description": "물리 공격에 마법 데미지 추가 (마력의 50%)"}
                )
            ],
            "dual_element": [
                TraitEffect(
                    trait_id="dual_element",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="use_higher_damage",
                    metadata={"description": "공격 시 물리/마법 중 높은 쪽으로 계산"}
                )
            ],
            "spellblade_art": [
                TraitEffect(
                    trait_id="spellblade_art",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,
                    condition="on_critical",
                    metadata={"description": "크리티컬 시 물리+마법 동시 발동 (데미지 150%씩)"}
                )
            ],
            "arcane_edge": [
                TraitEffect(
                    trait_id="arcane_edge",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.60,
                    condition="after_magic_cast",
                    target_stat="physical",
                    metadata={"description": "마법 시전 후 다음 물리 공격 데미지 +60%"}
                )
            ],
            "combat_casting": [
                TraitEffect(
                    trait_id="combat_casting",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,
                    target_stat="cast_time",
                    metadata={"description": "마법 시전 시간 -50%"}
                )
            ],

            # === ALCHEMIST (연금술사) ===
            "potion_mastery": [
                TraitEffect(
                    trait_id="potion_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    target_stat="potion_effect",
                    metadata={"description": "모든 포션 효과 +50%"}
                ),
                TraitEffect(
                    trait_id="potion_mastery",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=1.0,
                    condition="using_potion",
                    metadata={"description": "포션 사용 시 MP 소모 없음"}
                )
            ],
            "transmutation": [
                TraitEffect(
                    trait_id="transmutation",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="item_conversion",
                    metadata={"description": "아이템을 다른 아이템으로 변환 가능"}
                )
            ],
            "chemical_weapon": [
                TraitEffect(
                    trait_id="chemical_weapon",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="on_attack",
                    target_stat="random_debuff",
                    metadata={"description": "공격 시 랜덤 상태이상 부여 (독, 화상, 둔화)"}
                )
            ],
            "emergency_elixir": [
                TraitEffect(
                    trait_id="emergency_elixir",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.50,
                    condition="hp_below_30",
                    metadata={"max_uses": 1, "description": "HP 30% 이하 시 자동으로 HP 50% 회복 (전투당 1회)"}
                )
            ],
            "philosopher_stone": [
                TraitEffect(
                    trait_id="philosopher_stone",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.05,
                    condition="turn_end",
                    target_stat="potion_generation",
                    metadata={"description": "턴 종료 시 5% 확률로 랜덤 포션 생성"}
                )
            ],

            # === ARCHER (궁수) ===
            "support_fire_master": [
                TraitEffect(
                    trait_id="support_fire_master",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.20,
                    condition="support_fire_combo_min",
                    metadata={"threshold": 2, "description": "연속 지원 사격 2회 이상 시 데미지 +20%"}
                )
            ],
            "perfect_support": [
                TraitEffect(
                    trait_id="perfect_support",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=2.00,
                    condition="support_fire_combo_min",
                    metadata={"threshold": 7, "description": "연속 지원 사격 7회 이상 시 데미지 +100%"}
                ),
                TraitEffect(
                    trait_id="perfect_support",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=1.0,
                    condition="support_fire_combo_min",
                    metadata={"threshold": 7, "description": "확정 크리티컬"}
                )
            ],
            "tactical_marksman": [
                TraitEffect(
                    trait_id="tactical_marksman",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.10,
                    target_stat="accuracy_per_marked_ally",
                    metadata={"max_bonus": 1.30, "description": "마킹된 아군 수에 비례하여 명중률 +10% (최대 +30%)"}
                )
            ],
            "combo_breaker_penalty": [
                TraitEffect(
                    trait_id="combo_breaker_penalty",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.0,
                    condition="combo_break",
                    target_stat="reset_combo",
                    metadata={"description": "직접 공격, 피격, 3턴 지원 없음 시 콤보 초기화"}
                )
            ],
            "overwatch": [
                TraitEffect(
                    trait_id="overwatch",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="marked_allies_min",
                    target_stat="evasion",
                    metadata={"threshold": 3, "description": "마킹된 아군 3명 이상 시 회피율 +20%"}
                ),
                TraitEffect(
                    trait_id="overwatch",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    condition="marked_allies_min",
                    target_stat="speed",
                    metadata={"threshold": 3, "description": "속도 +15%"}
                )
            ],

            # === ARCHMAGE (대마법사) ===
            "mana_mastery": [
                TraitEffect(
                    trait_id="mana_mastery",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=0.30,
                    condition="magic_skill",
                    metadata={"description": "모든 마법 스킬 MP 소모 30% 감소"}
                )
            ],
            "arcane_knowledge": [
                TraitEffect(
                    trait_id="arcane_knowledge",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    target_stat="magic_attack",
                    metadata={"description": "마법 공격력 20% 증가"}
                )
            ],
            "elemental_fury": [
                TraitEffect(
                    trait_id="elemental_fury",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.10,
                    condition="consecutive_magic",
                    metadata={"max_stacks": 5, "max_bonus": 1.50, "description": "연속 마법 시전 시 위력 누적 (최대 50%)"}
                )
            ],
            "spell_weaving": [
                TraitEffect(
                    trait_id="spell_weaving",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.75,
                    target_stat="cast_time",
                    metadata={"description": "마법 시전 시간 25% 감소"}
                )
            ],
            "arcane_supremacy": [
                TraitEffect(
                    trait_id="arcane_supremacy",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.20,
                    condition="mp_above_70",
                    metadata={"description": "MP 70% 이상일 때 크리티컬 확률 20% 증가"}
                )
            ],

            # === ASSASSIN (암살자) ===
            "stealth_state_bonus": [
                TraitEffect(
                    trait_id="stealth_state_bonus",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.80,
                    condition="stealth_active",
                    target_stat="evasion",
                    metadata={"description": "은신 상태일 때 회피율 +80%"}
                ),
                TraitEffect(
                    trait_id="stealth_state_bonus",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=1.0,
                    condition="stealth_active",
                    metadata={"description": "다음 공격 크리티컬 확정"}
                )
            ],
            "stealth_speed_penalty": [
                TraitEffect(
                    trait_id="stealth_speed_penalty",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,
                    condition="stealth_active",
                    target_stat="speed",
                    metadata={"description": "은신 상태일 때 이동 속도 -50%"}
                )
            ],
            "exposed_normal": [
                TraitEffect(
                    trait_id="exposed_normal",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="exposed_state",
                    target_stat="all_stats",
                    metadata={"description": "노출 상태일 때 모든 능력치 정상, 3턴 후 은신 가능"}
                )
            ],
            "attack_breaks_stealth": [
                TraitEffect(
                    trait_id="attack_breaks_stealth",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.0,
                    condition="attack_skill",
                    target_stat="break_stealth",
                    metadata={"description": "공격 스킬 사용 시 은신 상태 해제"}
                )
            ],
            "shadow_master": [
                TraitEffect(
                    trait_id="shadow_master",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=2.50,
                    condition="stealth_first_attack",
                    metadata={"description": "은신 중 첫 공격 데미지 +150%"}
                )
            ],

            # === BARD (음유시인) ===
            "battle_song": [
                TraitEffect(
                    trait_id="battle_song",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.12,
                    target_stat="party_attack",
                    metadata={"description": "파티원 전체 공격력 +12%"}
                ),
                TraitEffect(
                    trait_id="battle_song",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.10,
                    target_stat="party_speed",
                    metadata={"description": "파티원 전체 속도 +10%"}
                )
            ],
            "inspirational_melody": [
                TraitEffect(
                    trait_id="inspirational_melody",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.15,
                    target_stat="party_critical",
                    metadata={"description": "파티원의 크리티컬 확률 +15%"}
                )
            ],
            "requiem": [
                TraitEffect(
                    trait_id="requiem",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.90,
                    target_stat="enemy_attack",
                    metadata={"description": "적 전체의 공격력 -10%"}
                ),
                TraitEffect(
                    trait_id="requiem",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.85,
                    target_stat="enemy_accuracy",
                    metadata={"description": "적 전체의 명중률 -15%"}
                )
            ],
            "harmony": [
                TraitEffect(
                    trait_id="harmony",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    condition="party_alive_min_2",
                    target_stat="all_effects",
                    metadata={"description": "파티원 2명 이상 생존 시 모든 효과 +50%"}
                )
            ],
            "encore": [
                TraitEffect(
                    trait_id="encore",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.20,
                    condition="buff_skill",
                    target_stat="mp_refund",
                    metadata={"description": "버프 스킬 사용 시 20% 확률로 MP 환불"}
                )
            ],

            # === BATTLE_MAGE (전투마법사) ===
            "rune_mastery": [
                TraitEffect(
                    trait_id="rune_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.0,
                    condition="same_rune_3",
                    target_stat="rune_effect",
                    metadata={"description": "같은 종류 룬 3개 보유 시 해당 룬 효과 2배"}
                )
            ],
            "hybrid_strike": [
                TraitEffect(
                    trait_id="hybrid_strike",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.30,
                    target_stat="physical_with_magic_bonus",
                    metadata={"description": "모든 물리 공격에 마법 공격력 30% 추가"}
                ),
                TraitEffect(
                    trait_id="hybrid_strike",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.30,
                    target_stat="magic_with_physical_bonus",
                    metadata={"description": "마법 공격에 물리 공격력 30% 추가"}
                )
            ],
            "rune_combination": [
                TraitEffect(
                    trait_id="rune_combination",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="different_runes_2",
                    target_stat="attack",
                    metadata={"description": "서로 다른 룬 2개 이상 보유 시 조합 보너스 (공격력 +20%)"}
                )
            ],
            "arcane_flow": [
                TraitEffect(
                    trait_id="arcane_flow",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.15,
                    condition="rune_use",
                    target_stat="rune_save_chance",
                    metadata={"description": "룬 사용 시 15% 확률로 룬 소모 없음"}
                )
            ],
            "elemental_harmony": [
                TraitEffect(
                    trait_id="elemental_harmony",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="all_5_runes",
                    target_stat="all_stats",
                    metadata={"description": "5가지 룬을 모두 보유 시 모든 능력치 +30%"}
                )
            ],

            # === BERSERKER (버서커) ===
            "madness_threshold": [
                TraitEffect(
                    trait_id="madness_threshold",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="madness_calculation",
                    metadata={"description": "HP 낮을수록 광기↑ (광기 = (1-HP비율)*100)"}
                )
            ],
            "berserker_mode": [
                TraitEffect(
                    trait_id="berserker_mode",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.60,
                    condition="madness_safe",
                    target_stat="attack",
                    metadata={"description": "광기 30-70 시 공격력 +60%"}
                ),
                TraitEffect(
                    trait_id="berserker_mode",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="madness_safe",
                    target_stat="speed",
                    metadata={"description": "속도 +30%"}
                )
            ],
            "danger_zone": [
                TraitEffect(
                    trait_id="danger_zone",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.00,
                    condition="madness_danger",
                    target_stat="attack",
                    metadata={"description": "광기 71-99 시 공격력 +100%"}
                ),
                TraitEffect(
                    trait_id="danger_zone",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.30,
                    condition="madness_danger",
                    metadata={"description": "크리티컬 +30%"}
                ),
                TraitEffect(
                    trait_id="danger_zone",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,
                    condition="madness_danger",
                    target_stat="damage_taken",
                    metadata={"description": "받는 피해 +50%"}
                )
            ],
            "rampage_state": [
                TraitEffect(
                    trait_id="rampage_state",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=3.00,
                    condition="madness_100",
                    target_stat="attack",
                    metadata={"description": "광기 100 시 3턴간 통제 불가, 공격력 +200%, 무작위 공격"}
                )
            ],
            "pain_tolerance": [
                TraitEffect(
                    trait_id="pain_tolerance",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.80,
                    condition="hp_below_30",
                    target_stat="damage_taken",
                    metadata={"description": "HP 30% 이하 시 받는 피해 -20%"}
                )
            ],

            # === BREAKER (브레이커) ===
            "brv_crusher": [
                TraitEffect(
                    trait_id="brv_crusher",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.40,
                    target_stat="brv_attack",
                    metadata={"description": "BRV 공격 시 추가 피해 +40%"}
                )
            ],
            "break_master": [
                TraitEffect(
                    trait_id="break_master",
                    effect_type=TraitEffectType.BREAK_BONUS,
                    value=2.0,
                    metadata={"description": "BREAK 발동 시 보너스 데미지 2배"}
                )
            ],
            "shield_breaker": [
                TraitEffect(
                    trait_id="shield_breaker",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.40,
                    target_stat="shield_penetration",
                    metadata={"description": "보호막 무시 40%"}
                )
            ],
            "ruthless_breaker": [
                TraitEffect(
                    trait_id="ruthless_breaker",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.80,
                    condition="target_broken",
                    metadata={"description": "BREAK 상태의 적 공격 시 추가 데미지 +80%"}
                ),
                TraitEffect(
                    trait_id="ruthless_breaker",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="target_broken",
                    target_stat="stun_duration",
                    metadata={"description": "스턴 기간 +1턴"}
                )
            ],
            "momentum_crush": [
                TraitEffect(
                    trait_id="momentum_crush",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.60,
                    condition="after_break",
                    target_stat="brv_attack",
                    metadata={"duration": 3, "description": "BREAK 발동 시 다음 BRV 공격 위력 +60% (3턴)"}
                )
            ],

            # === CLERIC (클레릭) ===
            "healing_power": [
                TraitEffect(
                    trait_id="healing_power",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.40,
                    target_stat="healing",
                    metadata={"description": "모든 회복 효과 +40%"}
                )
            ],
            "faith_shield": [
                TraitEffect(
                    trait_id="faith_shield",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="on_heal",
                    target_stat="grant_shield",
                    metadata={"description": "아군 치유 시 대상에게 보호막 부여"}
                )
            ],
            "divine_grace": [
                TraitEffect(
                    trait_id="divine_grace",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.70,
                    condition="mp_above_50",
                    target_stat="heal_cast_time",
                    metadata={"description": "MP 50% 이상일 때 회복 스킬 시전 시간 -30%"}
                )
            ],
            "resurrection_master": [
                TraitEffect(
                    trait_id="resurrection_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="resurrection_success",
                    metadata={"description": "부활 스킬 성공률 100%"}
                ),
                TraitEffect(
                    trait_id="resurrection_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,
                    target_stat="resurrection_hp",
                    metadata={"description": "부활 대상 HP 50% 회복"}
                )
            ],
            "prayer_blessing": [
                TraitEffect(
                    trait_id="prayer_blessing",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.05,
                    condition="turn_start",
                    target_stat="party_hp",
                    metadata={"description": "매 턴 아군 전체 HP 5% 회복"}
                )
            ],

            # === DARK_KNIGHT (다크나이트) ===
            "lifesteal": [
                TraitEffect(
                    trait_id="lifesteal",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.25,
                    target_stat="lifesteal",
                    metadata={"description": "물리 데미지의 25% HP 회복"}
                )
            ],
            "dark_pact": [
                TraitEffect(
                    trait_id="dark_pact",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=3.0,
                    condition="hp_consumed",
                    target_stat="attack_per_hp",
                    metadata={"description": "자신의 HP를 소모하여 공격력 증가 (HP 10% = 공격력 +30%)"}
                )
            ],
            "blood_rage": [
                TraitEffect(
                    trait_id="blood_rage",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.25,
                    condition="hp_below_50",
                    target_stat="attack_speed",
                    metadata={"description": "HP 50% 이하일 때 공격 속도 +25%"}
                )
            ],
            "undying_will": [
                TraitEffect(
                    trait_id="undying_will",
                    effect_type=TraitEffectType.REVIVE,
                    value=0.30,
                    condition="on_death",
                    metadata={"max_uses": 1, "description": "전투 중 1회, 치명상 시 HP 30%로 생존"}
                )
            ],
            "cursed_blade": [
                TraitEffect(
                    trait_id="cursed_blade",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.15,
                    condition="on_attack",
                    target_stat="bleed_chance",
                    metadata={"description": "공격 시 15% 확률로 적에게 출혈 부여 (턴당 BRV 감소)"}
                )
            ],

            # === DIMENSIONIST (차원술사) ===
            "gauge_per_turn": [
                TraitEffect(
                    trait_id="gauge_per_turn",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=10.0,
                    condition="turn_start",
                    target_stat="distortion_gauge",
                    metadata={"description": "매 턴 시작 시 확률 왜곡 게이지 +10"}
                )
            ],
            "critical_charge": [
                TraitEffect(
                    trait_id="critical_charge",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=20.0,
                    condition="on_critical",
                    target_stat="distortion_gauge",
                    metadata={"description": "크리티컬 공격 시 확률 왜곡 게이지 +20"}
                )
            ],
            "luck_amplifier": [
                TraitEffect(
                    trait_id="luck_amplifier",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.1,
                    target_stat="gauge_per_luck",
                    metadata={"description": "행운 스탯에 비례하여 게이지 추가 획득 (행운 10당 +1)"}
                )
            ],
            "probability_master": [
                TraitEffect(
                    trait_id="probability_master",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.30,
                    condition="distortion_gauge_min",
                    metadata={"threshold": 50, "description": "게이지 50+ 시 크리티컬 확률 +30%"}
                ),
                TraitEffect(
                    trait_id="probability_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="distortion_gauge_min",
                    target_stat="evasion",
                    metadata={"threshold": 50, "description": "회피율 +20%"}
                )
            ],
            "dimensional_instability": [
                TraitEffect(
                    trait_id="dimensional_instability",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.50,
                    condition="distortion_gauge_min",
                    metadata={"threshold": 80, "description": "게이지 80+ 시 모든 공격 크리티컬 확률 +50%"}
                ),
                TraitEffect(
                    trait_id="dimensional_instability",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    condition="distortion_gauge_min",
                    target_stat="damage_taken",
                    metadata={"threshold": 80, "description": "받는 데미지 +30%"}
                )
            ],

            # === DRAGON_KNIGHT (용기사) ===
            "dragon_breath": [
                TraitEffect(
                    trait_id="dragon_breath",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.35,
                    target_stat="fire_damage",
                    metadata={"description": "화염 속성 데미지 +35%"}
                ),
                TraitEffect(
                    trait_id="dragon_breath",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    target_stat="fire_resistance",
                    metadata={"description": "화염 저항 +50%"}
                )
            ],
            "burning_rage": [
                TraitEffect(
                    trait_id="burning_rage",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,
                    condition="on_attack",
                    target_stat="burn_chance",
                    metadata={"duration": 3, "description": "공격 시 50% 확률로 화상 부여 (3턴간 BRV 감소)"}
                )
            ],
            "dragon_scales": [
                TraitEffect(
                    trait_id="dragon_scales",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.80,
                    condition="hp_above_70",
                    target_stat="physical_damage_taken",
                    metadata={"description": "HP 70% 이상일 때 물리 데미지 -20%"}
                )
            ],
            "flame_wings": [
                TraitEffect(
                    trait_id="flame_wings",
                    effect_type=TraitEffectType.COUNTER,
                    value=1.0,
                    condition="on_dodge",
                    target_stat="fire_counter",
                    metadata={"description": "회피 성공 시 반격으로 화염 피해"}
                )
            ],
            "inferno": [
                TraitEffect(
                    trait_id="inferno",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.30,
                    condition="target_burning",
                    metadata={"description": "화상 상태의 적 공격 시 데미지 +30%"}
                )
            ],

            # === DRUID (드루이드) ===
            "shapeshifting": [
                TraitEffect(
                    trait_id="shapeshifting",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="animal_form",
                    metadata={"description": "전투 중 동물 형태 전환 가능 (곰: 방어, 표범: 속도, 독수리: 회피)"}
                )
            ],
            "natures_blessing": [
                TraitEffect(
                    trait_id="natures_blessing",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.03,
                    condition="turn_start",
                    metadata={"description": "턴당 HP 3% 자동 회복"}
                )
            ],
            "plant_control": [
                TraitEffect(
                    trait_id="plant_control",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.40,
                    target_stat="root_chance",
                    metadata={"duration": 2, "description": "적을 속박하여 2턴간 행동 불가 (성공률 40%)"}
                )
            ],
            "natural_balance": [
                TraitEffect(
                    trait_id="natural_balance",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.25,
                    target_stat="form_bonus",
                    condition="in_animal_form",
                    metadata={"description": "변신 상태에 따라 능력치 보너스 (곰: 방어력 +25%, 표범: 공격력 +25%, 독수리: 속도 +25%)"}
                )
            ],
            "wild_instinct": [
                TraitEffect(
                    trait_id="wild_instinct",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="hp_below_50",
                    target_stat="all_stats",
                    metadata={"description": "HP 50% 이하 시 모든 스탯 +20%"}
                )
            ],

            # === ELEMENTALIST (정령술사) ===
            "fire_spirit_power": [
                TraitEffect(
                    trait_id="fire_spirit_power",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="spirit_fire_active",
                    target_stat="magic_attack",
                    metadata={"description": "화염 정령 소환 시 마법 공격력 +20%"}
                )
            ],
            "water_spirit_regeneration": [
                TraitEffect(
                    trait_id="water_spirit_regeneration",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=5.0,
                    condition="spirit_water_active",
                    metadata={"description": "물 정령 소환 시 MP 회복 +5/턴"}
                ),
                TraitEffect(
                    trait_id="water_spirit_regeneration",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="spirit_water_active",
                    target_stat="healing",
                    metadata={"description": "힐 +30%"}
                )
            ],
            "wind_spirit_swiftness": [
                TraitEffect(
                    trait_id="wind_spirit_swiftness",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="spirit_wind_active",
                    target_stat="speed",
                    metadata={"description": "바람 정령 소환 시 속도 +30%"}
                ),
                TraitEffect(
                    trait_id="wind_spirit_swiftness",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    condition="spirit_wind_active",
                    target_stat="evasion",
                    metadata={"description": "회피 +15%"}
                )
            ],
            "earth_spirit_defense": [
                TraitEffect(
                    trait_id="earth_spirit_defense",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="spirit_earth_active",
                    target_stat="defense",
                    metadata={"description": "대지 정령 소환 시 방어력 +30%"}
                ),
                TraitEffect(
                    trait_id="earth_spirit_defense",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=3.0,
                    condition="spirit_earth_active",
                    metadata={"description": "HP 회복 +3/턴"}
                )
            ],
            "dual_spirit_mastery": [
                TraitEffect(
                    trait_id="dual_spirit_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    condition="spirit_count_min",
                    target_stat="all_stats",
                    metadata={"threshold": 2, "description": "2마리 정령 소환 시 모든 능력치 +15%"}
                ),
                TraitEffect(
                    trait_id="dual_spirit_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="spirit_count_min",
                    target_stat="fusion_skill_unlock",
                    metadata={"threshold": 2, "description": "융합 스킬 해금"}
                )
            ],

            # === ENGINEER (기계공학자) ===
            "heat_efficiency": [
                TraitEffect(
                    trait_id="heat_efficiency",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    condition="heat_optimal",
                    target_stat="all_stats",
                    metadata={"heat_range": "50-79", "description": "최적 구간(50-79) 유지 시 모든 스탯 +15%"}
                )
            ],
            "dangerous_combat": [
                TraitEffect(
                    trait_id="dangerous_combat",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.20,
                    condition="heat_danger",
                    metadata={"heat_range": "80-99", "description": "위험 구간(80-99) 유지 시 크리티컬 확률 +20%"}
                )
            ],
            "overheat_prevention": [
                TraitEffect(
                    trait_id="overheat_prevention",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=-15.0,
                    condition="heat_95",
                    target_stat="heat_reduction",
                    metadata={"max_uses": 2, "description": "열이 95 도달 시 자동으로 -15 (전투당 2회)"}
                )
            ],
            "auto_cooling": [
                TraitEffect(
                    trait_id="auto_cooling",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=-5.0,
                    condition="turn_end",
                    target_stat="heat_reduction",
                    metadata={"description": "매 턴 종료 시 열 -5 (항상 발동)"}
                )
            ],
            "precision_engineering": [
                TraitEffect(
                    trait_id="precision_engineering",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=0.30,
                    condition="heat_optimal",
                    metadata={"description": "최적 구간에서 스킬 시전 시 MP 소모 -30%"}
                )
            ],

            # === GLADIATOR (검투사) ===
            "crowd_favorite": [
                TraitEffect(
                    trait_id="crowd_favorite",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="cheer_min",
                    target_stat="attack",
                    metadata={"threshold": 50, "description": "환호 50+ 시 공격력 +30%"}
                ),
                TraitEffect(
                    trait_id="crowd_favorite",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.20,
                    condition="cheer_min",
                    metadata={"threshold": 50, "description": "크리티컬 +20%"}
                )
            ],
            "spectacular_fighter": [
                TraitEffect(
                    trait_id="spectacular_fighter",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.60,
                    condition="cheer_min",
                    target_stat="attack",
                    metadata={"threshold": 80, "description": "환호 80+ 시 공격력 +60%"}
                ),
                TraitEffect(
                    trait_id="spectacular_fighter",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.40,
                    condition="cheer_min",
                    metadata={"threshold": 80, "description": "크리티컬 +40%"}
                ),
                TraitEffect(
                    trait_id="spectacular_fighter",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="cheer_min",
                    target_stat="aoe_attacks",
                    metadata={"threshold": 80, "description": "모든 공격 광역화"}
                )
            ],
            "gladiator_glory": [
                TraitEffect(
                    trait_id="gladiator_glory",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="cheer_100",
                    target_stat="invincible",
                    metadata={"duration": 3, "description": "환호 100 도달 시 무적 3턴 발동"}
                )
            ],
            "showmanship": [
                TraitEffect(
                    trait_id="showmanship",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=10.0,
                    condition="on_critical",
                    target_stat="cheer_gain",
                    metadata={"description": "크리티컬 공격 시 환호 +10"}
                )
            ],
            "crowd_reaction": [
                TraitEffect(
                    trait_id="crowd_reaction",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=20.0,
                    condition="on_kill",
                    target_stat="cheer_gain",
                    metadata={"description": "적 처치 시 환호 +20"}
                ),
                TraitEffect(
                    trait_id="crowd_reaction",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=-10.0,
                    condition="on_hit",
                    target_stat="cheer_loss",
                    metadata={"description": "피격 시 환호 -10"}
                )
            ],

            # === HACKER (해커) ===
            "multithread_master": [
                TraitEffect(
                    trait_id="multithread_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="all_stats_per_program",
                    metadata={"description": "동시 실행 프로그램 수에 비례하여 모든 능력치 +15% (프로그램당)"}
                )
            ],
            "cpu_optimization": [
                TraitEffect(
                    trait_id="cpu_optimization",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=2.0,
                    target_stat="program_cost",
                    metadata={"description": "프로그램 유지 비용 -2 MP/턴 (5→3)"}
                )
            ],
            "overclocking": [
                TraitEffect(
                    trait_id="overclocking",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.40,
                    condition="programs_3",
                    target_stat="speed",
                    metadata={"description": "프로그램 3개 동시 실행 시 속도 +40%"}
                ),
                TraitEffect(
                    trait_id="overclocking",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.20,
                    condition="programs_3",
                    metadata={"description": "크리티컬 +20%"}
                )
            ],
            "kernel_panic": [
                TraitEffect(
                    trait_id="kernel_panic",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=10.0,
                    condition="enemy_program_end",
                    metadata={"description": "적 프로그램 종료 시 MP 10 회복"}
                )
            ],
            "zero_day_exploit": [
                TraitEffect(
                    trait_id="zero_day_exploit",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    condition="all_programs_active",
                    target_stat="attack",
                    metadata={"description": "모든 프로그램 동시 실행 시 공격력 +50%"}
                )
            ],

            # === KNIGHT (기사) ===
            "glory_vow": [
                TraitEffect(
                    trait_id="glory_vow",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="party_attack",
                    metadata={"description": "파티원 전체 공격력 +15%"}
                ),
                TraitEffect(
                    trait_id="glory_vow",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="party_defense",
                    metadata={"description": "파티원 전체 방어력 +15%"}
                )
            ],
            "honor_guard": [
                TraitEffect(
                    trait_id="honor_guard",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.80,
                    condition="protecting_ally",
                    target_stat="damage_taken",
                    metadata={"description": "파티원 대신 데미지를 받을 수 있음 (데미지 -20%)"}
                )
            ],
            "chivalry": [
                TraitEffect(
                    trait_id="chivalry",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.25,
                    condition="hp_above_80",
                    target_stat="party_buff_effect",
                    metadata={"description": "HP 80% 이상 유지 시 파티 전체 버프 효과 +25%"}
                )
            ],
            "leadership": [
                TraitEffect(
                    trait_id="leadership",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.08,
                    target_stat="stats_per_ally",
                    metadata={"description": "파티원이 많을수록 스탯 증가 (1명당 +8%)"}
                )
            ],
            "heroic_sacrifice": [
                TraitEffect(
                    trait_id="heroic_sacrifice",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="protecting_ally",
                    target_stat="brv_gain",
                    metadata={"description": "파티원 보호 시 자신의 BRV가 상승"}
                )
            ],

            # === MONK (무승) ===
            "yin_yang_balance": [
                TraitEffect(
                    trait_id="yin_yang_balance",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.05,
                    condition="yin_yang_balanced",
                    metadata={"description": "음양 균형 상태(40-60)에서 HP 5% 회복/턴"}
                ),
                TraitEffect(
                    trait_id="yin_yang_balance",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=0.05,
                    condition="yin_yang_balanced",
                    metadata={"description": "MP 5% 회복/턴"}
                )
            ],
            "yang_mastery": [
                TraitEffect(
                    trait_id="yang_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="yang_state",
                    target_stat="physical_attack",
                    metadata={"description": "양 상태(80+)에서 물리 공격력 +30%"}
                ),
                TraitEffect(
                    trait_id="yang_mastery",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.20,
                    condition="yang_state",
                    metadata={"description": "크리티컬 +20%"}
                )
            ],
            "yin_mastery": [
                TraitEffect(
                    trait_id="yin_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="yin_state",
                    target_stat="magic_attack",
                    metadata={"description": "음 상태(20-)에서 마법 공격력 +30%"}
                ),
                TraitEffect(
                    trait_id="yin_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="yin_state",
                    target_stat="defense",
                    metadata={"description": "방어력 +20%"}
                )
            ],
            "ki_flow": [
                TraitEffect(
                    trait_id="ki_flow",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=5.0,
                    condition="turn_start",
                    target_stat="yin_yang_balance_shift",
                    metadata={"description": "매 턴 음양 게이지가 균형(50)으로 5씩 이동"}
                )
            ],
            "enlightenment": [
                TraitEffect(
                    trait_id="enlightenment",
                    effect_type=TraitEffectType.MP_COST_REDUCTION,
                    value=0.50,
                    condition="yin_yang_perfect",
                    metadata={"description": "정확히 50에서 스킬 사용 시 MP 소모 50% 감소"}
                )
            ],

            # === NECROMANCER (네크로맨서) ===
            "undead_commander": [
                TraitEffect(
                    trait_id="undead_commander",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    condition="undead_min_3",
                    target_stat="undead_power",
                    metadata={"description": "언데드 3마리 이상 보유 시 모든 언데드 능력 +50%"}
                )
            ],
            "death_harvest": [
                TraitEffect(
                    trait_id="death_harvest",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="on_kill",
                    target_stat="corpse_gain",
                    metadata={"description": "적 처치 시 시체 자동 획득 (스켈레톤 소환 재료)"}
                )
            ],
            "necromantic_power": [
                TraitEffect(
                    trait_id="necromantic_power",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.10,
                    target_stat="magic_attack_per_undead",
                    metadata={"description": "언데드 1마리당 마법 공격력 +10%"}
                )
            ],
            "undead_sacrifice": [
                TraitEffect(
                    trait_id="undead_sacrifice",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=20.0,
                    condition="undead_destroyed",
                    metadata={"description": "언데드 파괴 시 MP 20 회복"}
                )
            ],
            "legion_master": [
                TraitEffect(
                    trait_id="legion_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="all_undead_types",
                    target_stat="all_stats",
                    metadata={"description": "각 언데드 타입 1마리씩 보유 시 모든 능력치 +20%"}
                )
            ],

            # === PALADIN (성기사) ===
            "divine_protection": [
                TraitEffect(
                    trait_id="divine_protection",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.30,
                    target_stat="party_critical_nullify",
                    metadata={"description": "파티원이 치명타를 받을 때 30% 확률로 무효화"}
                )
            ],
            "holy_aura": [
                TraitEffect(
                    trait_id="holy_aura",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.15,
                    target_stat="party_defense",
                    metadata={"description": "주변 아군의 방어력 +15%"}
                ),
                TraitEffect(
                    trait_id="holy_aura",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.80,
                    target_stat="undead_enemy_debuff",
                    metadata={"description": "언데드 적 약화"}
                )
            ],
            "martyr_spirit": [
                TraitEffect(
                    trait_id="martyr_spirit",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.70,
                    condition="protecting_ally",
                    target_stat="damage_taken",
                    metadata={"description": "아군 대신 데미지를 받을 수 있음 (데미지 -30%)"}
                )
            ],
            "healing_light": [
                TraitEffect(
                    trait_id="healing_light",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.35,
                    target_stat="healing",
                    metadata={"description": "HP 회복 효과 35% 증가"}
                )
            ],
            "righteous_fury": [
                TraitEffect(
                    trait_id="righteous_fury",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.40,
                    condition="ally_ko",
                    target_stat="attack",
                    metadata={"description": "아군이 전투불능 시 공격력 40% 증가"}
                )
            ],

            # === PHILOSOPHER (철학자) ===
            "power_mastery": [
                TraitEffect(
                    trait_id="power_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.60,
                    condition="choice_power_min",
                    target_stat="physical_attack",
                    metadata={"threshold": 5, "description": "힘 선택 5회 이상 시 물리 공격력 +60%"}
                ),
                TraitEffect(
                    trait_id="power_mastery",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.30,
                    condition="choice_power_min",
                    metadata={"threshold": 5, "description": "크리티컬 +30%"}
                )
            ],
            "wisdom_mastery": [
                TraitEffect(
                    trait_id="wisdom_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.60,
                    condition="choice_wisdom_min",
                    target_stat="magic_attack",
                    metadata={"threshold": 5, "description": "지혜 선택 5회 이상 시 마법 공격력 +60%"}
                ),
                TraitEffect(
                    trait_id="wisdom_mastery",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=5.0,
                    condition="choice_wisdom_min",
                    metadata={"threshold": 5, "description": "MP 회복 +5/턴"}
                )
            ],
            "sacrifice_mastery": [
                TraitEffect(
                    trait_id="sacrifice_mastery",
                    effect_type=TraitEffectType.REVIVE,
                    value=1.0,
                    condition="choice_sacrifice_min",
                    metadata={"threshold": 5, "max_uses": 1, "description": "희생 선택 5회 이상 시 아군 사망 시 자동 부활 (1회)"}
                )
            ],
            "truth_mastery": [
                TraitEffect(
                    trait_id="truth_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.0,
                    condition="choice_truth_min",
                    target_stat="enemy_debuff",
                    metadata={"threshold": 5, "description": "진실 선택 5회 이상 시 적 디버프 효과 2배"}
                )
            ],
            "balanced_philosophy": [
                TraitEffect(
                    trait_id="balanced_philosophy",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.20,
                    condition="choices_balanced",
                    target_stat="all_stats",
                    metadata={"description": "모든 선택 카운트가 균형(차이 2 이하)일 때 모든 스탯 +20%"}
                )
            ],

            # === PIRATE (해적) ===
            "treasure_hunter": [
                TraitEffect(
                    trait_id="treasure_hunter",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    target_stat="gold_gain",
                    metadata={"description": "골드 획득 +50%"}
                ),
                TraitEffect(
                    trait_id="treasure_hunter",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.40,
                    target_stat="item_drop",
                    metadata={"description": "아이템 드랍률 +40%"}
                )
            ],
            "lucky_strike": [
                TraitEffect(
                    trait_id="lucky_strike",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.01,
                    target_stat="critical_per_luck",
                    metadata={"description": "행운 수치만큼 크리티컬 확률 증가 (1행운 = 1%)"}
                )
            ],
            "greed": [
                TraitEffect(
                    trait_id="greed",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.02,
                    target_stat="stats_per_1000gold",
                    metadata={"description": "골드 보유량이 많을수록 스탯 증가 (70골드당 +2%, 최대 +50%)"}
                )
            ],
            "pirate_fortune": [
                TraitEffect(
                    trait_id="pirate_fortune",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.15,
                    condition="combat_victory",
                    target_stat="extra_chest",
                    metadata={"description": "전투 승리 시 15% 확률로 추가 보물 상자"}
                )
            ],
            "dirty_fighting": [
                TraitEffect(
                    trait_id="dirty_fighting",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.20,
                    condition="on_attack",
                    target_stat="random_debuff",
                    metadata={"description": "공격 시 20% 확률로 적 디버프 (랜덤)"}
                )
            ],

            # === PRIEST (사제) ===
            "divine_miracle": [
                TraitEffect(
                    trait_id="divine_miracle",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.10,
                    condition="turn_start",
                    target_stat="miracle_chance",
                    metadata={"description": "턴 시작 시 10% 확률로 랜덤 긍정 효과 (부활, 완전회복, 무적 등)"}
                )
            ],
            "healing_mastery": [
                TraitEffect(
                    trait_id="healing_mastery",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    target_stat="healing",
                    metadata={"description": "모든 회복 효과 +50%"}
                )
            ],
            "blessing": [
                TraitEffect(
                    trait_id="blessing",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.20,
                    target_stat="party_critical_resist",
                    metadata={"description": "파티 전체 크리티컬 받을 확률 -80%"}
                )
            ],
            "holy_protection": [
                TraitEffect(
                    trait_id="holy_protection",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="status_immunity",
                    metadata={"description": "상태이상 면역, 저주 무효"}
                )
            ],
            "resurrection": [
                TraitEffect(
                    trait_id="resurrection",
                    effect_type=TraitEffectType.REVIVE,
                    value=0.50,
                    condition="ally_ko",
                    metadata={"max_uses": 1, "description": "전투 중 1회, 전투불능 파티원 HP 50%로 부활"}
                )
            ],

            # === ROGUE (도적) ===
            "shadow_step": [
                TraitEffect(
                    trait_id="shadow_step",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.50,
                    condition="after_dodge",
                    metadata={"description": "회피 성공 시 다음 공격 치명타 확률 50% 증가"}
                )
            ],
            "assassinate": [
                TraitEffect(
                    trait_id="assassinate",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.15,
                    condition="target_hp_below_30",
                    target_stat="instant_kill",
                    metadata={"description": "HP 30% 이하 적 공격 시 즉사 확률 15%"}
                )
            ],
            "swift_strikes": [
                TraitEffect(
                    trait_id="swift_strikes",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    target_stat="attack_speed",
                    metadata={"description": "공격 속도 30% 증가"}
                ),
                TraitEffect(
                    trait_id="swift_strikes",
                    effect_type=TraitEffectType.ATB_BOOST,
                    value=1.30,
                    metadata={"description": "ATB 회복 빠름"}
                )
            ],
            "evasion_master": [
                TraitEffect(
                    trait_id="evasion_master",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.25,
                    target_stat="evasion",
                    metadata={"description": "회피율 +25%"}
                )
            ],
            "critical_finesse": [
                TraitEffect(
                    trait_id="critical_finesse",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,
                    condition="on_critical",
                    metadata={"description": "크리티컬 데미지 50% 증가"}
                )
            ],

            # === SAMURAI (사무라이) ===
            "bushido": [
                TraitEffect(
                    trait_id="bushido",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="debuff_immunity",
                    metadata={"description": "모든 디버프 무효, 정신 상태이상 면역"}
                )
            ],
            "honor_vow": [
                TraitEffect(
                    trait_id="honor_vow",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.25,
                    condition="one_vs_one",
                    target_stat="all_stats",
                    metadata={"description": "1:1 전투 시 모든 스탯 +25%"}
                )
            ],
            "meditation": [
                TraitEffect(
                    trait_id="meditation",
                    effect_type=TraitEffectType.HP_REGEN,
                    value=0.10,
                    condition="defending",
                    metadata={"description": "방어 태세 시 HP 10% 회복"}
                ),
                TraitEffect(
                    trait_id="meditation",
                    effect_type=TraitEffectType.MP_REGEN,
                    value=0.10,
                    condition="defending",
                    metadata={"description": "MP 10% 회복"}
                )
            ],
            "iaijutsu": [
                TraitEffect(
                    trait_id="iaijutsu",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=1.0,
                    condition="first_strike",
                    metadata={"description": "선제 공격 시 크리티컬 확정"}
                ),
                TraitEffect(
                    trait_id="iaijutsu",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=2.0,
                    condition="first_strike",
                    metadata={"description": "데미지 2배"}
                )
            ],
            "iron_will": [
                TraitEffect(
                    trait_id="iron_will",
                    effect_type=TraitEffectType.REVIVE,
                    value=0.01,
                    condition="on_death",
                    metadata={"max_uses": 1, "description": "HP 1로 생존 효과 (전투당 1회)"}
                )
            ],

            # === SHAMAN (샤먼) ===
            "spirit_sight": [
                TraitEffect(
                    trait_id="spirit_sight",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.0,
                    target_stat="vision_range",
                    metadata={"description": "시야 범위 2배, 숨겨진 함정/보물 자동 발견"}
                )
            ],
            "ancestral_protection": [
                TraitEffect(
                    trait_id="ancestral_protection",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.50,
                    target_stat="critical_resist",
                    metadata={"description": "치명타 받을 확률 -50%"}
                ),
                TraitEffect(
                    trait_id="ancestral_protection",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="instant_death_immunity",
                    metadata={"description": "즉사 공격 무효"}
                )
            ],
            "spirit_communion": [
                TraitEffect(
                    trait_id="spirit_communion",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="combat_start",
                    target_stat="enemy_weakness_reveal",
                    metadata={"description": "전투 시작 시 적의 약점 정보 획득"}
                )
            ],
            "fortune_telling": [
                TraitEffect(
                    trait_id="fortune_telling",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.10,
                    target_stat="predict_and_dodge",
                    metadata={"description": "10% 확률로 적의 다음 행동 예측 및 회피"}
                )
            ],
            "spirit_guide": [
                TraitEffect(
                    trait_id="spirit_guide",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    target_stat="minimap_reveal_all",
                    metadata={"description": "미니맵에 모든 적/아이템/출구 표시"}
                )
            ],

            # === SWORD_SAINT (검성) ===
            "sword_energy": [
                TraitEffect(
                    trait_id="sword_energy",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.30,
                    target_stat="sword_wave",
                    metadata={"description": "물리 공격 시 검기로 추가 피해 (공격력의 30%)"}
                )
            ],
            "rapid_slash": [
                TraitEffect(
                    trait_id="rapid_slash",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=0.25,
                    condition="on_attack",
                    target_stat="extra_attack",
                    metadata={"description": "공격 시 25% 확률로 즉시 추가 공격"}
                )
            ],
            "blade_master": [
                TraitEffect(
                    trait_id="blade_master",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.25,
                    condition="sword_equipped",
                    metadata={"description": "검 장착 시 크리티컬 확률 +25%"}
                ),
                TraitEffect(
                    trait_id="blade_master",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.50,
                    condition="sword_equipped_critical",
                    metadata={"description": "크리티컬 데미지 +50%"}
                )
            ],
            "focus_strike": [
                TraitEffect(
                    trait_id="focus_strike",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=1.40,
                    condition="single_target",
                    metadata={"description": "단일 대상 공격 시 데미지 +40%"}
                )
            ],
            "counter_blade": [
                TraitEffect(
                    trait_id="counter_blade",
                    effect_type=TraitEffectType.COUNTER,
                    value=0.15,
                    condition="on_hit",
                    metadata={"description": "피격 시 15% 확률로 즉시 반격"}
                )
            ],

            # === TIME_MAGE (시간마법사) ===
            "time_balancer": [
                TraitEffect(
                    trait_id="time_balancer",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.40,
                    condition="timeline_0",
                    target_stat="all_stats",
                    metadata={"description": "타임라인 0(현재)에서 모든 스탯 +40%"}
                )
            ],
            "past_wisdom": [
                TraitEffect(
                    trait_id="past_wisdom",
                    effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                    value=0.70,
                    condition="timeline_past",
                    target_stat="damage_taken",
                    metadata={"description": "타임라인 -2 이하에서 받는 피해 -30%"}
                )
            ],
            "future_insight": [
                TraitEffect(
                    trait_id="future_insight",
                    effect_type=TraitEffectType.CRITICAL_BONUS,
                    value=0.30,
                    condition="timeline_future",
                    metadata={"description": "타임라인 +2 이상에서 크리티컬 확률 +30%"}
                )
            ],
            "time_perception": [
                TraitEffect(
                    trait_id="time_perception",
                    effect_type=TraitEffectType.ATB_BOOST,
                    value=1.0,
                    condition="timeline_near_0",
                    metadata={"description": "타임라인이 0에 가까울수록 ATB 회복 속도 증가"}
                )
            ],
            "time_correction": [
                TraitEffect(
                    trait_id="time_correction",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="turn_count_3",
                    target_stat="timeline_reset",
                    metadata={"description": "3턴마다 자동으로 타임라인 0으로 이동"}
                )
            ],

            # === VAMPIRE (뱀파이어) ===
            "satisfied_state": [
                TraitEffect(
                    trait_id="satisfied_state",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.0,
                    condition="thirst_satisfied",
                    target_stat="all_stats",
                    metadata={"description": "갈증 0-30일 때 정상 상태 (기본 능력치)"}
                )
            ],
            "thirsty_state": [
                TraitEffect(
                    trait_id="thirsty_state",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.30,
                    condition="thirst_normal",
                    target_stat="attack",
                    metadata={"description": "갈증 31-60일 때 공격력 +30%"}
                ),
                TraitEffect(
                    trait_id="thirsty_state",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.0,
                    condition="thirst_normal",
                    target_stat="lifesteal",
                    metadata={"description": "흡혈 효과 2배"}
                )
            ],
            "extreme_thirst": [
                TraitEffect(
                    trait_id="extreme_thirst",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.70,
                    condition="thirst_starving",
                    target_stat="attack",
                    metadata={"description": "갈증 61-90일 때 공격력 +70%"}
                ),
                TraitEffect(
                    trait_id="extreme_thirst",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=3.0,
                    condition="thirst_starving",
                    target_stat="lifesteal",
                    metadata={"description": "흡혈 3배"}
                ),
                TraitEffect(
                    trait_id="extreme_thirst",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=1.50,
                    condition="thirst_starving",
                    target_stat="speed",
                    metadata={"description": "속도 +50%"}
                )
            ],
            "blood_frenzy_state": [
                TraitEffect(
                    trait_id="blood_frenzy_state",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=2.0,
                    condition="thirst_max",
                    target_stat="attack",
                    metadata={"description": "갈증 91-100일 때 통제 불가, 아군도 공격 (공격력 +100%)"}
                )
            ],
            "eternal_thirst": [
                TraitEffect(
                    trait_id="eternal_thirst",
                    effect_type=TraitEffectType.STAT_MULTIPLIER,
                    value=10.0,
                    condition="turn_start",
                    target_stat="thirst_gain",
                    metadata={"description": "매 턴 갈증 +10 자동 증가"}
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
                    # all_stats_per_program은 모든 스탯에 적용 (프로그램 수에 비례)
                    if effect.target_stat == "all_stats_per_program":
                        # 해커의 활성 프로그램 수 계산
                        program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
                        active_programs = sum(1 for field in program_fields if getattr(character, field, 0) > 0)
                        if active_programs > 0:
                            # 프로그램당 보너스 적용 (value는 프로그램당 배율)
                            program_bonus = effect.value ** active_programs  # 1.15^프로그램수
                            final_value *= program_bonus
                            self.logger.debug(
                                f"[{trait_id}] {stat_name} 프로그램 보너스 적용: 프로그램 {active_programs}개 × {effect.value} → x{program_bonus:.3f} → {final_value}"
                            )
                    # all_stats는 모든 스탯에 적용
                    elif effect.target_stat == "all_stats":
                        # 모든 스탯에 보너스 적용
                        if effect.effect_type == TraitEffectType.STAT_MULTIPLIER:
                            final_value *= effect.value
                            self.logger.debug(
                                f"[{trait_id}] {stat_name} 전체 스탯 보너스 적용: x{effect.value} → {final_value}"
                            )
                        elif effect.effect_type == TraitEffectType.STAT_FLAT:
                            final_value += effect.value
                            self.logger.debug(
                                f"[{trait_id}] {stat_name} 전체 스탯 고정값 보너스 적용: +{effect.value} → {final_value}"
                            )
                    # ALL_STATS_MULTIPLIER 타입은 모든 스탯에 적용
                    elif effect.effect_type == TraitEffectType.ALL_STATS_MULTIPLIER:
                        final_value *= effect.value
                        self.logger.debug(
                            f"[{trait_id}] {stat_name} 모든 스탯 배율 적용: x{effect.value} → {final_value}"
                        )
                    # all_stats_in_stance는 모든 스탯에 적용 (전사 특성)
                    elif effect.target_stat == "all_stats_in_stance":
                        # 모든 스탯에 보너스 적용
                        if effect.effect_type == TraitEffectType.STAT_MULTIPLIER:
                            final_value *= effect.value
                            self.logger.debug(
                                f"[{trait_id}] {stat_name} 자세 전체 스탯 보너스 적용: x{effect.value} → {final_value}"
                            )
                    # stats_per_1000gold는 골드 보유량에 비례한 스탯 증가 (해적 탐욕 특성)
                    elif effect.target_stat == "stats_per_1000gold":
                        # 골드 보유량 가져오기
                        gold_amount = 0
                        
                        # 1. character에 inventory 속성이 있는 경우
                        if hasattr(character, 'inventory') and hasattr(character.inventory, 'gold'):
                            gold_amount = character.inventory.gold
                        # 2. character에 직접 gold 속성이 있는 경우
                        elif hasattr(character, 'gold'):
                            gold_amount = character.gold
                        # 3. 파티에서 골드 가져오기 시도
                        elif hasattr(character, 'party') and character.party:
                            for member in character.party:
                                if hasattr(member, 'inventory') and hasattr(member.inventory, 'gold'):
                                    gold_amount = member.inventory.gold
                                    break
                        # 4. 전역 게임 상태에서 골드 가져오기 시도
                        else:
                            try:
                                # main.py의 전역 변수에서 골드 가져오기
                                import main
                                if hasattr(main, 'inventory') and hasattr(main.inventory, 'gold'):
                                    gold_amount = main.inventory.gold
                            except:
                                pass
                        
                        # 70골드당 +2% (기존: 250골드당 +2%)
                        gold_units = gold_amount // 70
                        bonus_multiplier = 1.0 + (gold_units * 0.02)  # 70골드당 +2%
                        
                        # 최대값 50%로 제한
                        max_multiplier = 1.50  # 최대 +50%
                        bonus_multiplier = min(bonus_multiplier, max_multiplier)
                        
                        if bonus_multiplier > 1.0:
                            final_value *= bonus_multiplier
                            self.logger.debug(
                                f"[{trait_id}] {stat_name} 골드 보너스 적용: {gold_amount}골드 ({gold_units}×70) → x{bonus_multiplier:.3f} → {final_value}"
                            )
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

        # 최대 75% 감소로 제한
        reduction_rate = min(0.75, reduction_rate)

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

    def calculate_damage_reduction(self, character: Any, is_defending: bool = False) -> float:
        """
        특성에 의한 피해 감소율 계산
        
        Args:
            character: 캐릭터
            is_defending: 방어 중인지 여부
        
        Returns:
            총 피해 감소율 (0.0 = 0%, 0.5 = 50%)
        """
        if not hasattr(character, 'active_traits'):
            return 0.0
        
        total_reduction = 0.0
        
        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)
            
            for effect in effects:
                # DAMAGE_REDUCTION: 일반 피해 감소 (조건 확인)
                if effect.effect_type == TraitEffectType.DAMAGE_REDUCTION:
                    if self._check_condition(character, effect.condition or "", {}):
                        total_reduction += effect.value
                        self.logger.debug(f"[{trait_id}] 피해 감소: +{effect.value * 100:.0f}%")
                
                # DEFEND_BOOST: 방어 중일 때만 피해 감소
                elif effect.effect_type == TraitEffectType.DEFEND_BOOST:
                    if is_defending:
                        condition_met = not effect.condition or self._check_condition(
                            character, effect.condition, {}
                        )
                        if condition_met:
                            total_reduction += effect.value
                            self.logger.debug(f"[{trait_id}] 방어 보너스 피해 감소: +{effect.value * 100:.0f}%")
        
        # 최대 90%까지 감소 가능
        return min(total_reduction, 0.90)

    def calculate_lifesteal(self, character: Any) -> float:
        """
        특성에 의한 생명력 흡수율 계산

        Args:
            character: 캐릭터

        Returns:
            생명력 흡수율 (0.10 = 10%)
        """
        if not hasattr(character, 'active_traits'):
            return 0.0

        lifesteal_rate = 0.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type == TraitEffectType.LIFESTEAL:
                    if self._check_condition(character, effect.condition or "", {}):
                        lifesteal_rate += effect.value
                        self.logger.debug(f"[{trait_id}] 생명력 흡수: +{effect.value * 100:.0f}%")

        return lifesteal_rate

    def calculate_mana_leech(self, character: Any) -> float:
        """
        특성에 의한 마력 흡수율 계산

        Args:
            character: 캐릭터

        Returns:
            마력 흡수율 (0.05 = 5%)
        """
        if not hasattr(character, 'active_traits'):
            return 0.0

        mana_leech_rate = 0.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type == TraitEffectType.MANA_LEECH:
                    if self._check_condition(character, effect.condition or "", {}):
                        mana_leech_rate += effect.value
                        self.logger.debug(f"[{trait_id}] 마력 흡수: +{effect.value * 100:.0f}%")

        return mana_leech_rate

    def calculate_critical_damage(self, character: Any) -> float:
        """
        특성에 의한 크리티컬 데미지 배율 계산

        Args:
            character: 캐릭터

        Returns:
            크리티컬 데미지 배율 (1.0 = 100%, 1.5 = 150%)
        """
        if not hasattr(character, 'active_traits'):
            return 1.0

        critical_damage_mult = 1.0

        for trait_data in character.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type == TraitEffectType.CRITICAL_DAMAGE:
                    if self._check_condition(character, effect.condition or "", {}):
                        # 배율은 곱셈 (1.0 + (value - 1.0))
                        critical_damage_mult *= effect.value
                        self.logger.debug(f"[{trait_id}] 크리티컬 데미지 배율: {effect.value:.2f}x")

        return critical_damage_mult

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
                        )

    def apply_on_kill_effects(self, attacker: Any, defender: Any):
        """
        처치 시 특성 효과 적용 (kill_bonus 등)

        Args:
            attacker: 공격자 (처치한 캐릭터)
            defender: 방어자 (처치된 캐릭터)
        """
        if not hasattr(attacker, 'active_traits'):
            return

        for trait_data in attacker.active_traits:
            trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
            effects = self.get_trait_effects(trait_id)

            for effect in effects:
                if effect.effect_type == TraitEffectType.KILL_BONUS:
                    # 처치 보너스 적용 (예: 공격력 증가, HP 회복 등)
                    # metadata에 구체적인 효과 정의
                    if not effect.metadata:
                        continue
                        
                    # HP 회복
                    if "hp_regen" in effect.metadata:
                        regen = effect.metadata["hp_regen"]
                        heal_amount = int(attacker.max_hp * regen)
                        if hasattr(attacker, 'heal'):
                            actual = attacker.heal(heal_amount)
                            self.logger.info(f"[{trait_id}] 처치 보너스: HP 회복 +{actual}")

                    # BRV 회복
                    if "brv_regen" in effect.metadata:
                        regen = effect.metadata["brv_regen"]
                        brv_amount = int(attacker.max_brv * regen)
                        if hasattr(attacker, 'current_brv'):
                            attacker.current_brv = min(attacker.current_brv + brv_amount, attacker.max_brv)
                            self.logger.info(f"[{trait_id}] 처치 보너스: BRV 회복 +{brv_amount}")

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
            # 스탠스 변경 스킬인지 확인 (metadata에 "stance" 키가 있는지 확인)
            skill = context.get("skill")
            if skill and hasattr(skill, 'metadata'):
                return "stance" in skill.metadata
            return False

        # 전투 시작
        elif condition == "combat_start":
            return context.get("combat_start", False)

        # 스킬 시전
        elif condition == "skill_cast":
            return context.get("is_skill", False)

        # 방어 중
        elif condition == "defending":
            # context에서 직접 확인하거나 캐릭터 상태 확인
            if context.get("is_defending", False):
                return True
            # 캐릭터가 방어 상태인지 확인
            if hasattr(character, 'status_manager'):
                from src.combat.status_effects import StatusType
                if hasattr(character.status_manager, 'has_status'):
                    return character.status_manager.has_status(StatusType.GUARDIAN) or \
                           character.status_manager.has_status(StatusType.SHIELD)
            return False

        # 피격 시
        elif condition == "on_hit":
            return context.get("on_hit", False)
        
        # 일반 공격
        elif condition == "normal_attack":
            return context.get("is_normal_attack", False)
        
        # 아군 피해 받음
        elif condition == "ally_damaged":
            return context.get("ally_damaged", False)
        
        # 턴 카운트 조건
        elif condition.startswith("turn_count_"):
            turn_num = int(condition.split("_")[-1])
            current_turn = context.get("turn_count", 0)
            return current_turn % turn_num == 0
        
        # 사망 시
        elif condition == "on_death":
            if hasattr(character, 'current_hp'):
                return character.current_hp <= 0
            return context.get("is_dead", False) or context.get("on_death", False)
        
        # 적 처치 시
        elif condition == "on_kill":
            return context.get("killed_enemy", False)

        # === 새로운 기믹 시스템 조건들 ===

        # 확률 왜곡 게이지 조건 (차원술사)
        elif condition == "distortion_gauge_min":
            threshold = context.get("threshold", 50)
            if hasattr(character, 'distortion_gauge'):
                return character.distortion_gauge >= threshold
            return False

        # 군중 환호 조건 (글래디에이터)
        elif condition == "cheer_min":
            threshold = context.get("threshold", 50)
            if hasattr(character, 'cheer'):
                return character.cheer >= threshold
            return False

        # 갈증 구간 조건 (뱀파이어)
        elif condition == "thirst_satisfied":
            if hasattr(character, 'thirst') and hasattr(character, 'satisfied_max'):
                return character.thirst <= character.satisfied_max
            return False

        elif condition == "thirst_normal":
            if hasattr(character, 'thirst'):
                normal_min = getattr(character, 'normal_min', 30)
                normal_max = getattr(character, 'normal_max', 69)
                return normal_min <= character.thirst <= normal_max
            return False

        elif condition == "thirst_starving":
            if hasattr(character, 'thirst'):
                starving_min = getattr(character, 'starving_min', 70)
                return character.thirst >= starving_min
            return False

        # 광기 구간 조건 (버서커)
        elif condition == "madness_safe":
            if hasattr(character, 'madness') and hasattr(character, 'safe_max'):
                return character.madness <= character.safe_max
            return False

        elif condition == "madness_danger":
            if hasattr(character, 'madness') and hasattr(character, 'danger_min'):
                return character.madness >= character.danger_min
            return False

        # 은신 상태 조건 (암살자)
        elif condition == "stealth_active":
            if hasattr(character, 'stealth_active'):
                return character.stealth_active == True
            return False

        # 정령 활성화 조건 (정령술사)
        elif condition == "spirit_fire_active":
            if hasattr(character, 'spirit_fire'):
                return character.spirit_fire > 0
            return False

        elif condition == "spirit_water_active":
            if hasattr(character, 'spirit_water'):
                return character.spirit_water > 0
            return False

        elif condition == "spirit_wind_active":
            if hasattr(character, 'spirit_wind'):
                return character.spirit_wind > 0
            return False

        elif condition == "spirit_earth_active":
            if hasattr(character, 'spirit_earth'):
                return character.spirit_earth > 0
            return False

        elif condition == "spirit_count_min":
            threshold = context.get("threshold", 2)
            if hasattr(character, 'spirit_fire'):
                count = sum([
                    getattr(character, 'spirit_fire', 0),
                    getattr(character, 'spirit_water', 0),
                    getattr(character, 'spirit_wind', 0),
                    getattr(character, 'spirit_earth', 0)
                ])
                return count >= threshold
            return False

        # 선택 누적 조건 (철학자)
        elif condition == "choice_power_min":
            threshold = context.get("threshold", 5)
            if hasattr(character, 'choice_power'):
                return character.choice_power >= threshold
            return False

        elif condition == "choice_wisdom_min":
            threshold = context.get("threshold", 5)
            if hasattr(character, 'choice_wisdom'):
                return character.choice_wisdom >= threshold
            return False

        elif condition == "choice_sacrifice_min":
            threshold = context.get("threshold", 5)
            if hasattr(character, 'choice_sacrifice'):
                return character.choice_sacrifice >= threshold
            return False

        elif condition == "choice_truth_min":
            threshold = context.get("threshold", 5)
            if hasattr(character, 'choice_truth'):
                return character.choice_truth >= threshold
            return False

        elif condition == "choices_balanced":
            # 모든 선택 카운트의 차이가 2 이하인지 체크
            if hasattr(character, 'choice_power'):
                choices = [
                    getattr(character, 'choice_power', 0),
                    getattr(character, 'choice_wisdom', 0),
                    getattr(character, 'choice_sacrifice', 0),
                    getattr(character, 'choice_survival', 0),
                    getattr(character, 'choice_truth', 0),
                    getattr(character, 'choice_lie', 0),
                    getattr(character, 'choice_order', 0),
                    getattr(character, 'choice_chaos', 0)
                ]
                if max(choices) - min(choices) <= 2:
                    return True
            return False

        # 지원사격 콤보 조건 (궁수)
        elif condition == "support_fire_combo_min":
            threshold = context.get("threshold", 2)
            if hasattr(character, 'support_fire_combo'):
                return character.support_fire_combo >= threshold
            return False

        elif condition == "marked_allies_min":
            threshold = context.get("threshold", 3)
            if hasattr(character, 'marked_allies'):
                return len(character.marked_allies) >= threshold
            return False

        # 해커 프로그램 조건
        elif condition == "programs_3":
            # 프로그램 3개 이상 활성화 확인
            program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
            active_count = sum(1 for field in program_fields if getattr(character, field, 0) > 0)
            return active_count >= 3

        elif condition == "all_programs_active":
            # 모든 프로그램 활성화 확인 (최대 스레드 수, 기본 3개)
            max_threads = getattr(character, 'max_threads', 3)
            program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
            active_count = sum(1 for field in program_fields if getattr(character, field, 0) > 0)
            return active_count >= max_threads

        elif condition == "enemy_program_end":
            # 적 프로그램 종료 이벤트 확인 (context에서 확인)
            return context.get("enemy_program_ended", False)

        # 엔지니어 열 관리 조건
        elif condition == "heat_optimal":
            # 최적 구간 (50-79)
            if hasattr(character, 'heat'):
                optimal_min = getattr(character, 'optimal_min', 50)
                optimal_max = getattr(character, 'optimal_max', 79)
                return optimal_min <= character.heat <= optimal_max
            return False

        # 음양사 기 조건
        elif condition == "yin_yang_perfect":
            # 정확히 50 (balance_center)
            if hasattr(character, 'ki_gauge'):
                balance_center = getattr(character, 'balance_center', 50)
                return character.ki_gauge == balance_center
            return False

        # 마법 스킬 조건
        elif condition == "magic_skill":
            # context에서 스킬 정보 확인
            skill = context.get("skill") if context else None
            if skill:
                # stat_type이 "magical"이거나 damage_type이 "magic"인 경우
                stat_type = getattr(skill, 'stat_type', None)
                damage_type = getattr(skill, 'damage_type', None)
                return stat_type == "magical" or damage_type == "magic"
            return False

        # 포션 사용 조건
        elif condition == "using_potion":
            # context에서 아이템 사용 정보 확인
            return context.get("using_potion", False) if context else False

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
