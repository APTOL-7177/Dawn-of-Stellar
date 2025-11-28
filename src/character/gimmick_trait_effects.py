"""
Gimmick Trait Effects - 기믹 연동 특성 효과 시스템

12개 리워크 직업의 특성 효과 정의
"""

from typing import Dict, List, Any, TYPE_CHECKING
from src.character.trait_effects import TraitEffect, TraitEffectType
from src.core.logger import get_logger

if TYPE_CHECKING:
    from src.character.character import Character

logger = get_logger("gimmick_trait_effects")


def get_gimmick_trait_definitions() -> Dict[str, List[TraitEffect]]:
    """12개 리워크 직업의 특성 효과 정의"""
    
    return {
        # ============================================================
        # === 해적 (Pirate) - 럼주 & 보물 시스템 ===
        # ============================================================
        "lucky_drunk": [
            TraitEffect(
                trait_id="lucky_drunk",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.7,
                metadata={"gimmick_field": "rum_positive_chance", "description": "럼주 긍정 효과 확률 70%"}
            )
        ],
        "treasure_hoarder": [
            TraitEffect(
                trait_id="treasure_hoarder",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=5,
                metadata={"gimmick_field": "max_treasure", "description": "보물 최대 5개"}
            ),
            TraitEffect(
                trait_id="treasure_hoarder",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="treasure_stacked",
                metadata={"description": "같은 보물 중첩 시 효과 1.5배"}
            )
        ],
        "sea_dog_instinct": [
            TraitEffect(
                trait_id="sea_dog_instinct",
                effect_type=TraitEffectType.STAT_FLAT,
                value=40,
                target_stat="evasion",
                condition="hp_below_30",
                metadata={"description": "HP 30% 이하 시 회피율 +40%"}
            ),
            TraitEffect(
                trait_id="sea_dog_instinct",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1.0,
                condition="hp_below_30",
                metadata={"gimmick_field": "rum_always_positive", "description": "HP 30% 이하 시 럼주 항상 긍정"}
            )
        ],
        "plunder_master": [
            TraitEffect(
                trait_id="plunder_master",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1.0,
                metadata={"gimmick_field": "treasure_drop_rate", "description": "적 처치 시 100% 보물 획득"}
            ),
            TraitEffect(
                trait_id="plunder_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.3,
                condition="using_treasure",
                metadata={"description": "보물 효과 +30%"}
            )
        ],
        "pirate_kings_fortune": [
            TraitEffect(
                trait_id="pirate_kings_fortune",
                effect_type=TraitEffectType.STAT_FLAT,
                value=15,
                target_stat="luck",
                metadata={"description": "행운 +15%"}
            ),
            TraitEffect(
                trait_id="pirate_kings_fortune",
                effect_type=TraitEffectType.CRITICAL_DAMAGE,
                value=1.25,
                metadata={"description": "크리티컬 데미지 +25%"}
            )
        ],

        # ============================================================
        # === 바드 (Bard) - 악보 작곡 시스템 ===
        # ============================================================
        "perfect_pitch": [
            TraitEffect(
                trait_id="perfect_pitch",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=1.5,
                condition="harmony_complete",
                metadata={"description": "화음 완성 시 효과 +50%"}
            ),
            TraitEffect(
                trait_id="perfect_pitch",
                effect_type=TraitEffectType.DAMAGE_REDUCTION,
                value=0.3,
                condition="discord",
                metadata={"description": "불협화음 페널티 -30%"}
            )
        ],
        "crescendo_master": [
            TraitEffect(
                trait_id="crescendo_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.25,
                condition="notes_min_3",
                metadata={"gimmick_field": "music_notes", "threshold": 3, "description": "음표 3개 이상 시 피해 +25%"}
            )
        ],
        "encore": [
            TraitEffect(
                trait_id="encore",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.25,
                condition="score_complete",
                metadata={"description": "악보 완성 시 25% 확률로 음표 유지"}
            )
        ],
        "party_inspiration": [
            TraitEffect(
                trait_id="party_inspiration",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.15,
                target_stat="critical",
                metadata={"description": "파티 전체 크리티컬 +15%"}
            ),
            TraitEffect(
                trait_id="party_inspiration",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.2,
                target_stat="mp_regen",
                metadata={"description": "파티 전체 MP 회복 +20%"}
            )
        ],
        "battle_hymn": [
            TraitEffect(
                trait_id="battle_hymn",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=2,
                condition="combat_start",
                metadata={"gimmick_field": "start_notes", "description": "전투 시작 시 음표 2개 획득"}
            ),
            TraitEffect(
                trait_id="battle_hymn",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.1,
                target_stat="attack",
                metadata={"description": "파티 공격력 +10%"}
            )
        ],

        # ============================================================
        # === 연금술사 (Alchemist) - 포션 조합 시스템 ===
        # ============================================================
        "potion_mastery": [
            TraitEffect(
                trait_id="potion_mastery",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.4,
                condition="using_potion_skill",
                metadata={"description": "포션 스킬 효과 +40%"}
            ),
            TraitEffect(
                trait_id="potion_mastery",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.2,
                metadata={"gimmick_field": "potion_stock", "description": "재료 소비 시 20% 확률 유지"}
            )
        ],
        "efficient_brewing": [
            TraitEffect(
                trait_id="efficient_brewing",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                metadata={"gimmick_field": "potion_stock", "description": "재료 획득량 +1"}
            ),
            TraitEffect(
                trait_id="efficient_brewing",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=13,
                metadata={"gimmick_field": "max_potion_stock", "description": "최대 재료 13개"}
            )
        ],
        "chemical_expert": [
            TraitEffect(
                trait_id="chemical_expert",
                effect_type=TraitEffectType.DOT_DAMAGE_BONUS,
                value=1.5,
                metadata={"description": "독/화상 피해 +50%"}
            ),
            TraitEffect(
                trait_id="chemical_expert",
                effect_type=TraitEffectType.DEBUFF_DURATION,
                value=1,
                metadata={"description": "디버프 지속시간 +1턴"}
            )
        ],
        "emergency_synthesis": [
            TraitEffect(
                trait_id="emergency_synthesis",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=3,
                condition="hp_below_30",
                metadata={"gimmick_field": "potion_stock", "heal_percent": 0.3, "once_per_battle": True,
                         "description": "HP 30% 이하 시 재료 3개 + HP 30% 회복"}
            )
        ],
        "philosophers_touch": [
            TraitEffect(
                trait_id="philosophers_touch",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=2,
                condition="potion_stock_min_5",
                metadata={"gimmick_field": "potion_stock", "trigger": "turn_end",
                         "description": "재료 5개 이상 시 턴 종료 시 +2"}
            )
        ],

        # ============================================================
        # === 브레이커 (Breaker) - 파괴력 축적 시스템 ===
        # ============================================================
        "destruction_resonance": [
            TraitEffect(
                trait_id="destruction_resonance",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="break_power_min_5",
                metadata={"gimmick_field": "break_power", "threshold": 5, "description": "파괴력 5+ 시 피해 +50%"}
            ),
            TraitEffect(
                trait_id="destruction_resonance",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                condition="break_power_min_5",
                metadata={"gimmick_field": "break_power", "description": "파괴력 5+ 시 획득량 +1"}
            )
        ],
        "armor_shatter": [
            TraitEffect(
                trait_id="armor_shatter",
                effect_type=TraitEffectType.DEFENSE_PENETRATION,
                value=0.03,
                condition="per_break_power",
                metadata={"gimmick_field": "break_power", "max": 0.30, "description": "파괴력당 방어 관통 3% (최대 30%)"}
            )
        ],
        "break_momentum": [
            TraitEffect(
                trait_id="break_momentum",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=3,
                condition="on_break",
                metadata={"gimmick_field": "break_power", "description": "BREAK 시 파괴력 +3"}
            ),
            TraitEffect(
                trait_id="break_momentum",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.8,
                condition="after_break",
                metadata={"duration": 1, "description": "BREAK 후 다음 공격 +80%"}
            )
        ],
        "relentless_crusher": [
            TraitEffect(
                trait_id="relentless_crusher",
                effect_type=TraitEffectType.DEFENSE_PENETRATION,
                value=1.0,
                condition="break_power_max",
                metadata={"gimmick_field": "break_power", "threshold": 10, "description": "파괴력 MAX 시 방어 완전 관통"}
            )
        ],
        "destruction_chain": [
            TraitEffect(
                trait_id="destruction_chain",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=2,
                condition="enemy_brv_zero",
                metadata={"gimmick_field": "break_power", "description": "적 BRV 0 시 파괴력 +2"}
            )
        ],

        # ============================================================
        # === 드루이드 (Druid) - 자연 변신 시스템 ===
        # ============================================================
        "nature_conduit": [
            TraitEffect(
                trait_id="nature_conduit",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                metadata={"gimmick_field": "nature_points", "description": "자연 포인트 획득량 +1"}
            ),
            TraitEffect(
                trait_id="nature_conduit",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=7,
                metadata={"gimmick_field": "max_nature_points", "description": "최대 자연 포인트 7"}
            )
        ],
        "primal_form": [
            TraitEffect(
                trait_id="primal_form",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.4,
                condition="using_transform",
                metadata={"description": "변신 스킬 피해 +40%"}
            ),
            TraitEffect(
                trait_id="primal_form",
                effect_type=TraitEffectType.DEBUFF_DURATION,
                value=2,
                condition="form_buff",
                metadata={"description": "변신 버프 +2턴"}
            )
        ],
        "natures_fury": [
            TraitEffect(
                trait_id="natures_fury",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="nature_points_min_3",
                metadata={"gimmick_field": "nature_points", "threshold": 3, "description": "자연 포인트 3+ 시 피해 +50%"}
            ),
            TraitEffect(
                trait_id="natures_fury",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.3,
                condition="nature_points_min_3",
                metadata={"description": "자연 포인트 3+ 시 힐 +30%"}
            )
        ],
        "wild_surge": [
            TraitEffect(
                trait_id="wild_surge",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0,
                condition="nature_points_max",
                metadata={"gimmick_field": "nature_points", "threshold": 5, "free_cast": True, "damage_mult": 2.0,
                         "description": "자연 포인트 MAX 시 변신 무료 + 피해 2배"}
            )
        ],
        "regeneration_aura": [
            TraitEffect(
                trait_id="regeneration_aura",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.05,
                target_stat="hp_regen",
                condition="in_form",
                metadata={"description": "변신 중 파티 HP 5%/턴 회복"}
            ),
            TraitEffect(
                trait_id="regeneration_aura",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1,
                condition="in_form_turn_start",
                metadata={"gimmick_field": "nature_points", "description": "변신 중 턴 시작 시 자연 포인트 +1"}
            )
        ],

        # ============================================================
        # === 정령술사 (Elementalist) - 4대 정령 시스템 ===
        # ============================================================
        "fire_spirit_power": [
            TraitEffect(
                trait_id="fire_spirit_power",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.2,
                target_stat="physical_attack",
                condition="spirit_fire_active",
                metadata={"description": "화염 정령 시 공격력 +20%"}
            ),
            TraitEffect(
                trait_id="fire_spirit_power",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.3,
                condition="spirit_fire_active",
                metadata={"gimmick_field": "burn_chance", "description": "화상 확률 30%"}
            )
        ],
        "water_spirit_regeneration": [
            TraitEffect(
                trait_id="water_spirit_regeneration",
                effect_type=TraitEffectType.MP_REGEN,
                value=5,
                condition="spirit_water_active",
                metadata={"per_turn": True, "description": "물 정령 시 MP +5/턴"}
            ),
            TraitEffect(
                trait_id="water_spirit_regeneration",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.3,
                condition="spirit_water_active",
                metadata={"description": "물 정령 시 힐 +30%"}
            )
        ],
        "wind_spirit_swiftness": [
            TraitEffect(
                trait_id="wind_spirit_swiftness",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="speed",
                condition="spirit_wind_active",
                metadata={"description": "바람 정령 시 속도 +30%"}
            ),
            TraitEffect(
                trait_id="wind_spirit_swiftness",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.15,
                target_stat="evasion",
                condition="spirit_wind_active",
                metadata={"description": "바람 정령 시 회피 +15%"}
            )
        ],
        "earth_spirit_defense": [
            TraitEffect(
                trait_id="earth_spirit_defense",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="physical_defense",
                condition="spirit_earth_active",
                metadata={"description": "대지 정령 시 방어력 +30%"}
            ),
            TraitEffect(
                trait_id="earth_spirit_defense",
                effect_type=TraitEffectType.HP_REGEN,
                value=3,
                condition="spirit_earth_active",
                metadata={"per_turn": True, "description": "대지 정령 시 HP +3/턴"}
            )
        ],
        "dual_spirit_mastery": [
            TraitEffect(
                trait_id="dual_spirit_mastery",
                effect_type=TraitEffectType.ALL_STATS_MULTIPLIER,
                value=1.15,
                condition="spirits_2",
                metadata={"description": "정령 2마리 시 전체 스탯 +15%"}
            ),
            TraitEffect(
                trait_id="dual_spirit_mastery",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1,
                condition="spirits_2",
                metadata={"gimmick_field": "fusion_unlocked", "description": "정령 2마리 시 융합 스킬 해금"}
            )
        ],

        # ============================================================
        # === 검투사 (Gladiator) - 군중 환호 시스템 ===
        # ============================================================
        "crowd_favorite": [
            TraitEffect(
                trait_id="crowd_favorite",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="physical_attack",
                condition="cheer_min_50",
                metadata={"gimmick_field": "cheer", "threshold": 50, "description": "환호 50+ 시 공격력 +30%"}
            ),
            TraitEffect(
                trait_id="crowd_favorite",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.2,
                condition="cheer_min_50",
                metadata={"description": "환호 50+ 시 크리티컬 +20%"}
            )
        ],
        "spectacular_fighter": [
            TraitEffect(
                trait_id="spectacular_fighter",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.6,
                target_stat="physical_attack",
                condition="cheer_min_80",
                metadata={"gimmick_field": "cheer", "threshold": 80, "description": "환호 80+ 시 공격력 +60%"}
            ),
            TraitEffect(
                trait_id="spectacular_fighter",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.4,
                condition="cheer_min_80",
                metadata={"description": "환호 80+ 시 크리티컬 +40%"}
            ),
            TraitEffect(
                trait_id="spectacular_fighter",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1,
                condition="cheer_min_80",
                metadata={"gimmick_field": "aoe_attacks", "description": "환호 80+ 시 모든 공격 광역화"}
            )
        ],
        "gladiator_glory": [
            TraitEffect(
                trait_id="gladiator_glory",
                effect_type=TraitEffectType.INVINCIBLE_TRIGGER,
                value=3,
                condition="cheer_100",
                metadata={"gimmick_field": "cheer", "threshold": 100, "description": "환호 100 시 무적 3턴"}
            )
        ],
        "showmanship": [
            TraitEffect(
                trait_id="showmanship",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=10,
                condition="on_critical",
                metadata={"gimmick_field": "cheer", "description": "크리티컬 시 환호 +10"}
            )
        ],
        "crowd_reaction": [
            TraitEffect(
                trait_id="crowd_reaction",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=20,
                condition="on_kill",
                metadata={"gimmick_field": "cheer", "description": "적 처치 시 환호 +20"}
            ),
            TraitEffect(
                trait_id="crowd_reaction",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=-10,
                condition="on_damaged",
                metadata={"gimmick_field": "cheer", "description": "피격 시 환호 -10"}
            )
        ],

        # ============================================================
        # === 기사 (Knight) - 의무 시스템 ===
        # ============================================================
        "duty_amplifier": [
            TraitEffect(
                trait_id="duty_amplifier",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.5,
                metadata={"gimmick_field": "duty_stacks", "multiplier": True, "description": "의무 획득량 +50%"}
            ),
            TraitEffect(
                trait_id="duty_amplifier",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="physical_defense",
                condition="duty_min_5",
                metadata={"gimmick_field": "duty_stacks", "threshold": 5, "description": "의무 5+ 시 방어력 +30%"}
            )
        ],
        "oath_keeper": [
            TraitEffect(
                trait_id="oath_keeper",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.03,
                target_stat="defense",
                condition="per_duty",
                metadata={"gimmick_field": "duty_stacks", "max": 0.30, "description": "의무당 파티 방어 +3% (최대 30%)"}
            )
        ],
        "guardian_shield": [
            TraitEffect(
                trait_id="guardian_shield",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=3,
                condition="on_protect",
                metadata={"gimmick_field": "duty_stacks", "description": "아군 보호 시 의무 +3"}
            ),
            TraitEffect(
                trait_id="guardian_shield",
                effect_type=TraitEffectType.DAMAGE_REDUCTION,
                value=0.25,
                condition="protecting",
                metadata={"description": "보호 중 받는 피해 -25%"}
            )
        ],
        "duty_overflow": [
            TraitEffect(
                trait_id="duty_overflow",
                effect_type=TraitEffectType.INVINCIBLE_TRIGGER,
                value=1,
                condition="duty_max",
                metadata={"gimmick_field": "duty_stacks", "threshold": 10, "party_wide": True,
                         "description": "의무 MAX 시 파티 전체 무적 1턴"}
            )
        ],
        "sacrifice_honor": [
            TraitEffect(
                trait_id="sacrifice_honor",
                effect_type=TraitEffectType.SURVIVE_FATAL,
                value=1.0,
                condition="protecting_fatal",
                metadata={"consume_all_duty": True, "party_heal": 0.3,
                         "description": "보호 중 치명상 시 생존 + 파티 HP 30% 회복"}
            )
        ],

        # ============================================================
        # === 신관 (Priest) - 신앙/심판 시스템 ===
        # ============================================================
        "faith_amplifier": [
            TraitEffect(
                trait_id="faith_amplifier",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=5,
                condition="on_heal",
                metadata={"gimmick_field": "faith_points", "description": "힐 시 신앙 +5 추가"}
            ),
            TraitEffect(
                trait_id="faith_amplifier",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.3,
                metadata={"description": "힐 효과 +30%"}
            )
        ],
        "judgment_wrath": [
            TraitEffect(
                trait_id="judgment_wrath",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                target_stat="holy",
                condition="judgment_min_50",
                metadata={"gimmick_field": "judgment_points", "threshold": 50, "description": "심판력 50+ 시 신성 피해 +50%"}
            ),
            TraitEffect(
                trait_id="judgment_wrath",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.25,
                condition="judgment_min_50",
                metadata={"gimmick_field": "judgment_points", "multiplier": True, "description": "심판력 50+ 시 획득량 +25%"}
            )
        ],
        "divine_balance": [
            TraitEffect(
                trait_id="divine_balance",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.4,
                condition="faith_equals_judgment",
                metadata={"description": "신앙=심판 시 모든 스킬 +40%"}
            )
        ],
        "resurrection_prayer": [
            TraitEffect(
                trait_id="resurrection_prayer",
                effect_type=TraitEffectType.AUTO_RESURRECT,
                value=0.6,
                condition="faith_100",
                metadata={"gimmick_field": "faith_points", "threshold": 100,
                         "description": "신앙 100 시 아군 자동 부활 (HP 60%)"}
            )
        ],
        "holy_sanctuary": [
            TraitEffect(
                trait_id="holy_sanctuary",
                effect_type=TraitEffectType.INVINCIBLE_TRIGGER,
                value=3,
                condition="judgment_100",
                metadata={"gimmick_field": "judgment_points", "threshold": 100, "party_wide": True,
                         "cleanse": True, "description": "심판력 100 시 파티 무적 3턴 + 상태해제"}
            )
        ],

        # ============================================================
        # === 도적 (Rogue) - 절도 & 회피 시스템 ===
        # ============================================================
        "master_thief": [
            TraitEffect(
                trait_id="master_thief",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.3,
                metadata={"gimmick_field": "steal_success_bonus", "description": "훔치기 성공률 +30%"}
            ),
            TraitEffect(
                trait_id="master_thief",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="using_stolen_item",
                metadata={"description": "훔친 아이템 효과 +50%"}
            )
        ],
        "treasure_sense": [
            TraitEffect(
                trait_id="treasure_sense",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=2.0,
                condition="stolen_items_min_5",
                metadata={"gimmick_field": "rare_steal_chance", "description": "훔친 아이템 5+ 시 희귀 획득 2배"}
            )
        ],
        "shadow_evasion": [
            TraitEffect(
                trait_id="shadow_evasion",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1,
                condition="on_evade",
                metadata={"gimmick_field": "stolen_items", "description": "회피 시 훔친 아이템 +1"}
            ),
            TraitEffect(
                trait_id="shadow_evasion",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1,
                condition="on_evade",
                metadata={"gimmick_field": "guaranteed_crit", "description": "회피 시 다음 공격 크리티컬 확정"}
            )
        ],
        "quick_fingers": [
            TraitEffect(
                trait_id="quick_fingers",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.5,
                metadata={"gimmick_field": "stolen_items", "description": "아이템 사용 시 50% 확률 유지"}
            )
        ],
        "assassin_instinct": [
            TraitEffect(
                trait_id="assassin_instinct",
                effect_type=TraitEffectType.EXECUTE,
                value=0.2,
                condition="stolen_items_max",
                metadata={"gimmick_field": "stolen_items", "threshold": 10,
                         "description": "훔친 아이템 MAX 시 HP 20% 이하 적 즉사"}
            )
        ],

        # ============================================================
        # === 마검사 (Spellblade) - 마나 블레이드 시스템 ===
        # ============================================================
        "mana_conduit": [
            TraitEffect(
                trait_id="mana_conduit",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.5,
                metadata={"gimmick_field": "mana_blade", "multiplier": True, "description": "마나 획득량 +50%"}
            ),
            TraitEffect(
                trait_id="mana_conduit",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=120,
                metadata={"gimmick_field": "max_mana_blade", "description": "최대 마나 블레이드 120"}
            )
        ],
        "elemental_mastery": [
            TraitEffect(
                trait_id="elemental_mastery",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.4,
                condition="using_enchant",
                metadata={"description": "원소 부여 스킬 피해 +40%"}
            ),
            TraitEffect(
                trait_id="elemental_mastery",
                effect_type=TraitEffectType.DEBUFF_DURATION,
                value=1,
                metadata={"description": "상태이상 지속시간 +1턴"}
            )
        ],
        "blade_resonance": [
            TraitEffect(
                trait_id="blade_resonance",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1,
                condition="mana_blade_min_50",
                metadata={"gimmick_field": "dual_damage", "description": "마나 50+ 시 물리/마법 동시 피해"}
            )
        ],
        "arcane_overflow": [
            TraitEffect(
                trait_id="arcane_overflow",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0,
                condition="mana_blade_100",
                metadata={"gimmick_field": "mana_blade", "threshold": 100, "free_cast": True, "damage_mult": 2.0,
                         "description": "마나 MAX 시 다음 스킬 무료 + 피해 2배"}
            )
        ],
        "spell_chain": [
            TraitEffect(
                trait_id="spell_chain",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=10,
                condition="enchant_chain",
                metadata={"gimmick_field": "mana_blade", "description": "원소 스킬 연속 시 마나 +10"}
            ),
            TraitEffect(
                trait_id="spell_chain",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.15,
                condition="enchant_chain",
                metadata={"stacking": True, "description": "연속 원소 스킬 시 피해 +15% 누적"}
            )
        ],

        # ============================================================
        # === 무당 (Shaman) - 저주 축적 시스템 ===
        # ============================================================
        "curse_amplifier": [
            TraitEffect(
                trait_id="curse_amplifier",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                metadata={"gimmick_field": "curse_stacks", "description": "저주 획득량 +1"}
            ),
            TraitEffect(
                trait_id="curse_amplifier",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.2,
                metadata={"gimmick_field": "curse_stacks", "description": "저주 비례 피해 +20% 추가"}
            )
        ],
        "lingering_curse": [
            TraitEffect(
                trait_id="lingering_curse",
                effect_type=TraitEffectType.DEBUFF_DURATION,
                value=2,
                metadata={"description": "디버프/DoT 지속시간 +2턴"}
            ),
            TraitEffect(
                trait_id="lingering_curse",
                effect_type=TraitEffectType.DOT_DAMAGE_BONUS,
                value=1.3,
                metadata={"description": "DoT 효과 +30%"}
            )
        ],
        "curse_resonance": [
            TraitEffect(
                trait_id="curse_resonance",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.6,
                condition="curse_min_5",
                metadata={"gimmick_field": "curse_stacks", "threshold": 5, "description": "저주 5+ 시 피해 +60%"}
            ),
            TraitEffect(
                trait_id="curse_resonance",
                effect_type=TraitEffectType.STATUS_RESIST,
                value=1.0,
                condition="curse_min_5",
                metadata={"description": "저주 5+ 시 디버프 면역"}
            )
        ],
        "hex_master": [
            TraitEffect(
                trait_id="hex_master",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0,
                condition="curse_max",
                metadata={"gimmick_field": "curse_stacks", "threshold": 10, "curse_explosion": True, "aoe": True,
                         "description": "저주 MAX 시 저주 폭발 자동 발동"}
            )
        ],
        "soul_harvest": [
            TraitEffect(
                trait_id="soul_harvest",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=3,
                condition="on_kill",
                metadata={"gimmick_field": "curse_stacks", "description": "적 처치 시 저주 +3"}
            ),
            TraitEffect(
                trait_id="soul_harvest",
                effect_type=TraitEffectType.HP_REGEN,
                value=0.1,
                condition="on_kill",
                metadata={"description": "적 처치 시 HP 10% 회복"}
            ),
            TraitEffect(
                trait_id="soul_harvest",
                effect_type=TraitEffectType.MP_REGEN,
                value=0.1,
                condition="on_kill",
                metadata={"description": "적 처치 시 MP 10% 회복"}
            )
        ],
    }


def register_gimmick_traits(trait_manager):
    """기믹 특성을 TraitEffectManager에 등록"""
    gimmick_traits = get_gimmick_trait_definitions()
    
    for trait_id, effects in gimmick_traits.items():
        if trait_id not in trait_manager.trait_definitions:
            trait_manager.trait_definitions[trait_id] = effects
            logger.debug(f"기믹 특성 등록: {trait_id}")
        else:
            # 기존 특성에 효과 추가
            trait_manager.trait_definitions[trait_id].extend(effects)
            logger.debug(f"기믹 특성 확장: {trait_id}")
    
    logger.info(f"기믹 특성 {len(gimmick_traits)}개 등록 완료")


# ============================================================
# 기믹 효과 계산 함수들
# ============================================================

def calculate_gimmick_gain_bonus(character: Any, gimmick_field: str) -> float:
    """
    특성에 의한 기믹 스택 획득량 보너스 계산
    
    Args:
        character: 캐릭터
        gimmick_field: 기믹 필드명 (예: 'break_power', 'curse_stacks')
    
    Returns:
        획득량 보너스 (1.0 = 기본, 1.5 = +50%)
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    bonus = 0.0
    multiplier = 1.0
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.GIMMICK_GAIN_BONUS:
                metadata = effect.metadata or {}
                if metadata.get('gimmick_field') == gimmick_field or not metadata.get('gimmick_field'):
                    if metadata.get('multiplier'):
                        multiplier *= (1.0 + effect.value)
                    else:
                        bonus += effect.value
    
    return max(0, bonus) + (multiplier - 1.0) * 1.0  # 고정 보너스 + 배율 보너스


def calculate_gimmick_scaling_damage(character: Any, gimmick_field: str, base_damage: float) -> float:
    """
    기믹 비례 피해 보너스 계산
    
    Args:
        character: 캐릭터
        gimmick_field: 기믹 필드명
        base_damage: 기본 피해량
    
    Returns:
        보너스 적용된 피해량
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    gimmick_value = getattr(character, gimmick_field, 0)
    bonus_multiplier = 1.0
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.GIMMICK_SCALING:
                metadata = effect.metadata or {}
                if metadata.get('gimmick_field') == gimmick_field:
                    # 기믹 스택당 추가 피해
                    bonus_multiplier += effect.value * gimmick_value
    
    return base_damage * bonus_multiplier


def check_gimmick_trigger(character: Any, trigger_type: str, context: Dict = None) -> List[Dict]:
    """
    기믹 트리거 조건 체크 및 발동할 효과 반환
    
    Args:
        character: 캐릭터
        trigger_type: 트리거 타입 (예: 'on_kill', 'turn_end', 'cheer_100')
        context: 컨텍스트 정보
    
    Returns:
        발동할 효과 목록 [{trait_id, effect, metadata}, ...]
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    context = context or {}
    triggered_effects = []
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.GIMMICK_TRIGGER:
                if effect.condition == trigger_type or _check_trigger_condition(character, effect.condition, context):
                    triggered_effects.append({
                        'trait_id': trait_id,
                        'effect': effect,
                        'metadata': effect.metadata or {}
                    })
    
    return triggered_effects


def _check_trigger_condition(character: Any, condition: str, context: Dict) -> bool:
    """트리거 조건 체크"""
    if not condition:
        return True
    
    # 기믹 MAX 조건
    if condition.endswith('_max'):
        field = condition[:-4]  # '_max' 제거
        max_field = f'max_{field}'
        current = getattr(character, field, 0)
        max_val = getattr(character, max_field, 10)
        return current >= max_val
    
    # 기믹 MIN 조건
    if '_min_' in condition:
        parts = condition.split('_min_')
        if len(parts) == 2:
            field = parts[0]
            threshold = int(parts[1])
            return getattr(character, field, 0) >= threshold
    
    # context 기반 조건
    return context.get(condition, False)


def apply_gimmick_effect(character: Any, effect: TraitEffect, context: Dict = None):
    """
    기믹 효과 적용
    
    Args:
        character: 캐릭터
        effect: 특성 효과
        context: 컨텍스트
    """
    metadata = effect.metadata or {}
    gimmick_field = metadata.get('gimmick_field')
    
    if not gimmick_field:
        return
    
    current = getattr(character, gimmick_field, 0)
    max_field = f'max_{gimmick_field}'
    max_val = getattr(character, max_field, 999)
    
    # 값 적용
    if effect.effect_type == TraitEffectType.GIMMICK_TRIGGER:
        # 트리거 효과는 값을 더함
        new_val = min(current + effect.value, max_val)
        setattr(character, gimmick_field, new_val)
        logger.debug(f"기믹 트리거: {gimmick_field} {current} → {new_val}")
    
    elif effect.effect_type == TraitEffectType.GIMMICK_MAX_BONUS:
        # 최대치 증가
        setattr(character, max_field, effect.value)
        logger.debug(f"기믹 최대치: {max_field} = {effect.value}")


def calculate_defense_penetration(character: Any, context: Dict = None) -> float:
    """
    특성에 의한 방어 관통률 계산
    
    Args:
        character: 캐릭터
        context: 컨텍스트
    
    Returns:
        방어 관통률 (0.0 ~ 1.0)
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    context = context or {}
    total_penetration = 0.0
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.DEFENSE_PENETRATION:
                metadata = effect.metadata or {}
                condition = effect.condition or ""
                
                # 조건 체크
                if condition == "per_break_power":
                    # 파괴력당 방어 관통
                    break_power = getattr(character, 'break_power', 0)
                    pen = effect.value * break_power
                    max_pen = metadata.get('max', 0.3)
                    total_penetration += min(pen, max_pen)
                elif condition == "break_power_max":
                    # 파괴력 MAX 시 완전 관통
                    if getattr(character, 'break_power', 0) >= 10:
                        total_penetration = 1.0
                        break
                else:
                    total_penetration += effect.value
    
    return min(total_penetration, 1.0)  # 최대 100%


def calculate_heal_bonus(character: Any, context: Dict = None) -> float:
    """
    특성에 의한 힐 효과 보너스 계산
    
    Args:
        character: 캐릭터
        context: 컨텍스트
    
    Returns:
        힐 배율 (1.0 = 100%)
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    context = context or {}
    multiplier = 1.0
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.HEAL_BONUS:
                if manager._check_condition(character, effect.condition or "", context):
                    multiplier *= effect.value
    
    return multiplier


def calculate_dot_damage_bonus(character: Any) -> float:
    """
    특성에 의한 DoT 피해 보너스 계산
    
    Args:
        character: 캐릭터
    
    Returns:
        DoT 피해 배율 (1.0 = 100%)
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    multiplier = 1.0
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.DOT_DAMAGE_BONUS:
                multiplier *= effect.value
    
    return multiplier


def calculate_debuff_duration_bonus(character: Any) -> int:
    """
    특성에 의한 디버프 지속시간 보너스 계산
    
    Args:
        character: 캐릭터
    
    Returns:
        추가 지속시간 (턴)
    """
    from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
    
    manager = get_trait_effect_manager()
    bonus = 0
    
    all_traits = []
    if hasattr(character, 'active_traits'):
        all_traits.extend(character.active_traits)
    if hasattr(character, 'system_traits'):
        all_traits.extend(character.system_traits)
    
    for trait_data in all_traits:
        trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
        effects = manager.get_trait_effects(trait_id)
        
        for effect in effects:
            if effect.effect_type == TraitEffectType.DEBUFF_DURATION:
                bonus += int(effect.value)
    
    return bonus
