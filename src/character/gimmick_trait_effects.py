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
        # === 브레이커 (Breaker) - SCATTER 시스템 ===
        # ============================================================
        "engine_overclock": [
            TraitEffect(
                trait_id="engine_overclock",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.23,
                condition="scatter_mode",
                metadata={"description": "SCATTER 시 기본 피해 계수 150%→185%로 증가"}
            )
        ],
        "hydraulic_piston": [
            TraitEffect(
                trait_id="hydraulic_piston",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.45,
                metadata={"gimmick_field": "scatter_speed_reduction", "description": "SCATTER 시 속도 감소율 30%→45%"}
            )
        ],
        "chemical_resonance": [
            TraitEffect(
                trait_id="chemical_resonance",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.12,
                condition="scatter_hit",
                metadata={"description": "SCATTER 시 각 타격 시 추가 물리 데미지 8%→12%"}
            )
        ],
        "steam_siphon": [
            TraitEffect(
                trait_id="steam_siphon",
                effect_type=TraitEffectType.LIFESTEAL,
                value=0.4,
                condition="scatter_activate",
                metadata={"description": "SCATTER 발동 시 공격력의 40% HP 회복"}
            )
        ],
        "infinite_loop": [
            TraitEffect(
                trait_id="infinite_loop",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.2,
                metadata={"gimmick_field": "scatter_gauge", "multiplier": True, "description": "파쇄 게이지 획득 +20%"}
            ),
            TraitEffect(
                trait_id="infinite_loop",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=1.2,
                metadata={"gimmick_field": "scatter_gauge_max", "description": "파쇄 게이지 최대치 +20%"}
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
        "fire_spirit_fury": [
            TraitEffect(
                trait_id="fire_spirit_fury",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.2,
                target_stat="physical_attack",
                condition="spirit_fire_active",
                metadata={"description": "화염 정령 시 공격력 +20%"}
            ),
            TraitEffect(
                trait_id="fire_spirit_fury",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.3,
                condition="spirit_fire_active",
                metadata={"gimmick_field": "burn_chance", "description": "화상 확률 30%"}
            )
        ],
        "water_spirit_blessing": [
            TraitEffect(
                trait_id="water_spirit_blessing",
                effect_type=TraitEffectType.MP_REGEN,
                value=5,
                condition="spirit_water_active",
                metadata={"per_turn": True, "description": "물 정령 시 MP +5/턴"}
            ),
            TraitEffect(
                trait_id="water_spirit_blessing",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.3,
                condition="spirit_water_active",
                metadata={"description": "물 정령 시 힐 +30%"}
            )
        ],
        "wind_spirit_grace": [
            TraitEffect(
                trait_id="wind_spirit_grace",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="speed",
                condition="spirit_wind_active",
                metadata={"description": "바람 정령 시 속도 +30%"}
            ),
            TraitEffect(
                trait_id="wind_spirit_grace",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.15,
                target_stat="evasion",
                condition="spirit_wind_active",
                metadata={"description": "바람 정령 시 회피 +15%"}
            )
        ],
        "earth_spirit_protection": [
            TraitEffect(
                trait_id="earth_spirit_protection",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="physical_defense",
                condition="spirit_earth_active",
                metadata={"description": "대지 정령 시 방어력 +30%"}
            ),
            TraitEffect(
                trait_id="earth_spirit_protection",
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
        "challenger": [
            TraitEffect(
                trait_id="challenger",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.5,
                condition="boss_fight",
                metadata={"gimmick_field": "cheer", "multiplier": True, "description": "보스전에서 환호 획득량 +50%"}
            )
        ],
        "showstopper": [
            TraitEffect(
                trait_id="showstopper",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.5,
                metadata={"gimmick_field": "cheer_decay_reduction", "description": "전투 중 환호 감소율 50% 감소"}
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
        # === 사제 (Priest) - 신앙/점복 시스템 ===
        # ============================================================
        "divine_favor": [
            TraitEffect(
                trait_id="divine_favor",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=5,
                condition="divination_success",
                metadata={"gimmick_field": "faith_points", "description": "점복 성공 시 신앙 +5 추가"}
            )
        ],
        "holy_fervor": [
            TraitEffect(
                trait_id="holy_fervor",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.25,
                condition="faith_min_50",
                metadata={"gimmick_field": "faith_points", "threshold": 50, "description": "신앙 50+ 시 크리 +25%"}
            )
        ],
        "blessed_touch": [
            TraitEffect(
                trait_id="blessed_touch",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.1,
                metadata={"description": "디버프 해제 시 회복 +10%"}
            )
        ],
        "oracle_mastery": [
            TraitEffect(
                trait_id="oracle_mastery",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=-1,
                metadata={"gimmick_field": "divination_threshold", "description": "점복 성공 보너스 임계값 -1"}
            )
        ],
        "divine_intervention": [
            TraitEffect(
                trait_id="divine_intervention",
                effect_type=TraitEffectType.SURVIVE_FATAL,
                value=1,
                condition="faith_min_75",
                metadata={"gimmick_field": "faith_points", "threshold": 75, "description": "신앙 75+ 시 아군 사망 방지 1회"}
            )
        ],

        # ============================================================
        # === 도적 (Rogue) - 맹독 & 속도 시스템 ===
        # ============================================================
        "venom_master": [
            TraitEffect(
                trait_id="venom_master",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                metadata={"gimmick_field": "venom_stacks", "flat_bonus": True,
                         "description": "독 중첩 시 추가 +1"}
            ),
            TraitEffect(
                trait_id="venom_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.3,
                condition="poison_dot",
                metadata={"description": "독 피해 +30%"}
            )
        ],
        "gale_runner": [
            TraitEffect(
                trait_id="gale_runner",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.15,
                target_stat="speed",
                metadata={"description": "속도 +15%"}
            ),
            TraitEffect(
                trait_id="gale_runner",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0.20,
                condition="on_evade",
                metadata={"gimmick_field": "atb_bonus", "description": "회피 성공 시 ATB +20%"}
            )
        ],
        "killer_instinct": [
            TraitEffect(
                trait_id="killer_instinct",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.40,
                condition="target_venom_min_4",
                metadata={"description": "독 4중첩 이상 적에게 크리 확률 +40%"}
            )
        ],
        "venom_dance": [
            TraitEffect(
                trait_id="venom_dance",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1,
                condition="on_evade",
                metadata={"gimmick_field": "venom_stacks", "target": "attacker",
                         "description": "회피 성공 시 공격자에게 독 중첩 +1"}
            )
        ],
        "plague_burst": [
            TraitEffect(
                trait_id="plague_burst",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0.5,
                condition="on_poisoned_enemy_death",
                metadata={"gimmick_field": "venom_stacks", "aoe": True,
                         "description": "독에 걸린 적 사망 시 남은 독 피해 50%를 전체 광역"}
            )
        ],

        # ============================================================
        # === 마검사 (Spellblade) - 블레이드 서킷 ===
        # ============================================================
        "circuit_overdrive": [
            TraitEffect(
                trait_id="circuit_overdrive",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.2,
                metadata={"gimmick_field": "steel_line", "multiplier": True, "description": "Steel Line 획득량 +20%"}
            ),
            TraitEffect(
                trait_id="circuit_overdrive",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.2,
                metadata={"gimmick_field": "mana_line", "multiplier": True, "description": "Mana Line 획득량 +20%"}
            )
        ],
        "resonance_loop": [
            TraitEffect(
                trait_id="resonance_loop",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1,
                metadata={"gimmick_field": "resonance_sigil", "description": "패턴 성공 시 시그넷 추가"}
            )
        ],
        "mirror_specialist": [
            TraitEffect(
                trait_id="mirror_specialist",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1,
                metadata={"gimmick_field": "mirror_edge_def_shred", "description": "미러 엣지 방깎 보너스"}
            )
        ],
        "feedback_spark": [
            TraitEffect(
                trait_id="feedback_spark",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1,
                metadata={"gimmick_field": "arc_spark_bonus", "description": "Arc Spark 피해/MP 회복 보너스"}
            )
        ],
        "balanced_blade": [
            TraitEffect(
                trait_id="balanced_blade",
                effect_type=TraitEffectType.ALL_STATS_MULTIPLIER,
                value=1.15,
                metadata={"description": "양 채널 50+ 시 피해 +15%"}
            )
        ],

        # ============================================================
        # === 주술사 (Shaman) - 오버로드 시스템 ===
        # ============================================================
        "spirit_vision": [
            TraitEffect(
                trait_id="spirit_vision",
                effect_type=TraitEffectType.PASSIVE,
                value=1.5,
                metadata={"field_bonus": "detection", "description": "시야 +50%, 자원/적 탐지 확률 +100%"}
            )
        ],
        "overload_master": [
            TraitEffect(
                trait_id="overload_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.2,
                condition="overload_skill",
                metadata={"description": "오버로드 스킬 효과 +20%"}
            ),
            TraitEffect(
                trait_id="overload_master",
                effect_type=TraitEffectType.MP_COST_REDUCTION,
                value=0.1,
                condition="overload_skill",
                metadata={"description": "오버로드 스킬 MP 소모 -10%"}
            )
        ],
        "desperate_power": [
            TraitEffect(
                trait_id="desperate_power",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.3,
                condition="mp_below_50",
                metadata={"description": "MP 20~49% 시 오버로드 효과 +30%"}
            ),
            TraitEffect(
                trait_id="desperate_power",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.15,
                condition="mp_below_50",
                metadata={"description": "MP 20~49% 시 크리티컬 +15%"}
            )
        ],
        "spirit_resonance": [
            TraitEffect(
                trait_id="spirit_resonance",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.4,
                target_stat="magic_attack",
                condition="overload_min_3",
                metadata={"gimmick_field": "overload_stacks", "threshold": 3, "description": "오버로드 3+ 시 공격 +40%"}
            ),
            TraitEffect(
                trait_id="spirit_resonance",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.25,
                target_stat="speed",
                condition="overload_min_3",
                metadata={"description": "오버로드 3+ 시 속도 +25%"}
            )
        ],
        "toggle_efficiency": [
            TraitEffect(
                trait_id="toggle_efficiency",
                effect_type=TraitEffectType.MP_REGEN,
                value=0.5,
                condition="toggle_active",
                metadata={"description": "토글 스킬 활성 시 MP 회복량 +50%"}
            )
        ],

        # ============================================================
        # === 사무라이 (Samurai) - 검심 시스템 ===
        # ============================================================
        "kenshin_growth": [
            # 관찰 스택에 따른 반격 효과는 gimmick_updater에서 처리
            TraitEffect(
                trait_id="kenshin_growth",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1.0,
                metadata={"gimmick_field": "kenshin_counter", "description": "관찰 스택에 따라 반격 강화"}
            )
        ],
        "meditation": [
            TraitEffect(
                trait_id="meditation",
                effect_type=TraitEffectType.HP_REGEN,
                value=0.10,  # 5% → 10%로 증가
                condition="parrying_hit",
                metadata={"description": "패링 중 피격 시 HP 10% 회복"}
            ),
            TraitEffect(
                trait_id="meditation",
                effect_type=TraitEffectType.MP_REGEN,
                value=0.10,  # 5% → 10%로 증가
                condition="parrying_hit",
                metadata={"description": "패링 중 피격 시 MP 10% 회복"}
            )
        ],
        "iaijutsu": [
            TraitEffect(
                trait_id="iaijutsu",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=1.0,  # 100% 확정 크리티컬
                condition="first_strike",
                metadata={"description": "선제 공격 시 크리티컬 확정"}
            ),
            TraitEffect(
                trait_id="iaijutsu",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=2.0,
                condition="first_strike",
                metadata={"description": "선제 공격 시 피해 2배"}
            )
        ],
        "brv_absorb_master": [
            TraitEffect(
                trait_id="brv_absorb_master",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.1,
                metadata={"gimmick_field": "brv_steal_bonus", "description": "BRV 흡수 +10%"}
            )
        ],
        "iron_will": [
            TraitEffect(
                trait_id="iron_will",
                effect_type=TraitEffectType.SURVIVE_FATAL,
                value=1,
                metadata={"once_per_battle": True, "description": "HP 1로 생존 (전투당 1회)"}
            )
        ],

        # ============================================================
        # === 궁수 (Archer) - 원거리 지원사격 시스템 ===
        # ============================================================
        "support_fire_master": [
            TraitEffect(
                trait_id="support_fire_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.2,
                condition="support_fire_min_2",
                metadata={"gimmick_field": "support_fire_count", "threshold": 2, "description": "지원사격 2회+ 시 데미지 +20%"}
            )
        ],
        "perfect_support": [
            TraitEffect(
                trait_id="perfect_support",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=2.0,
                condition="support_fire_min_7",
                metadata={"gimmick_field": "support_fire_count", "threshold": 7, "description": "지원사격 7회+ 시 데미지 +100%"}
            ),
            TraitEffect(
                trait_id="perfect_support",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=1.0,
                condition="support_fire_min_7",
                metadata={"description": "지원사격 7회+ 시 확정 크리티컬"}
            )
        ],
        "tactical_marksman": [
            TraitEffect(
                trait_id="tactical_marksman",
                effect_type=TraitEffectType.STAT_FLAT,
                value=10,
                target_stat="accuracy",
                condition="marked_target",
                metadata={"max_stacks": 3, "description": "마킹 대상 공격 시 명중률 +10% (최대 +30%)"}
            )
        ],
        "combo_momentum": [
            TraitEffect(
                trait_id="combo_momentum",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.03,
                metadata={"gimmick_field": "support_fire_count", "description": "지원사격 횟수당 명중/크리 +3%"}
            )
        ],
        "overwatch": [
            TraitEffect(
                trait_id="overwatch",
                effect_type=TraitEffectType.STAT_FLAT,
                value=20,
                target_stat="evasion",
                condition="marked_allies_min_3",
                metadata={"description": "마킹 아군 3명+ 시 회피율 +20%"}
            ),
            TraitEffect(
                trait_id="overwatch",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.15,
                target_stat="speed",
                condition="marked_allies_min_3",
                metadata={"description": "마킹 아군 3명+ 시 속도 +15%"}
            )
        ],

        # ============================================================
        # === 대마법사 (Archmage) - 원소 마스터리 시스템 ===
        # ============================================================
        "elemental_affinity": [
            TraitEffect(
                trait_id="elemental_affinity",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                metadata={"gimmick_field": "element_stacks", "description": "기본 스킬 시 원소 2개 획득 (+1 추가)"}
            )
        ],
        "fusion_mastery": [
            TraitEffect(
                trait_id="fusion_mastery",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.3,
                condition="fusion_skill",
                metadata={"description": "2원소 융합 스킬 데미지 +30%"}
            ),
            TraitEffect(
                trait_id="fusion_mastery",
                effect_type=TraitEffectType.MP_COST_REDUCTION,
                value=0.25,
                condition="fusion_skill",
                metadata={"description": "2원소 융합 스킬 MP -25%"}
            )
        ],
        "elemental_resonance": [
            TraitEffect(
                trait_id="elemental_resonance",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.2,
                condition="element_min_3",
                metadata={"gimmick_field": "element_stacks", "threshold": 3, "description": "같은 원소 3개+ 시 해당 원소 데미지 +20%"}
            )
        ],
        "balance_power": [
            TraitEffect(
                trait_id="balance_power",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.25,
                condition="balanced_elements",
                metadata={"description": "화염/빙결 균형 시 반대 속성 크리 +25%"}
            ),
            TraitEffect(
                trait_id="balance_power",
                effect_type=TraitEffectType.CRITICAL_DAMAGE,
                value=1.5,
                condition="balanced_elements",
                metadata={"description": "화염/빙결 균형 시 크리 데미지 +50%"}
            )
        ],
        "elemental_explosion": [
            TraitEffect(
                trait_id="elemental_explosion",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0,
                condition="element_5_types",
                metadata={"description": "5원소 보유 시 특수 변형 발동 (화염=광역, 빙결=ATB초기화, 뇌전=연타)"}
            )
        ],

        # ============================================================
        # === 어쌔신 (Assassin) - 은신 시스템 ===
        # ============================================================
        "stealth_state_bonus": [
            TraitEffect(
                trait_id="stealth_state_bonus",
                effect_type=TraitEffectType.STAT_FLAT,
                value=80,
                target_stat="evasion",
                condition="stealth_active",
                metadata={"description": "은신 상태에서 회피율 +80%"}
            )
        ],
        "shadow_mobility": [
            TraitEffect(
                trait_id="shadow_mobility",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.25,
                condition="stealth_break",
                metadata={"description": "은신 해제 시 데미지 +25%"}
            ),
            TraitEffect(
                trait_id="shadow_mobility",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=1.0,
                condition="evasion_in_stealth",
                metadata={"description": "은신 중 회피 성공 시 은신 유지"}
            )
        ],
        "quick_restealth": [
            TraitEffect(
                trait_id="quick_restealth",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=-1,
                metadata={"gimmick_field": "restealth_cooldown", "description": "은신 재진입 쿨다운 3→2턴"}
            ),
            TraitEffect(
                trait_id="quick_restealth",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="stealth_first_attack",
                metadata={"description": "은신 후 첫 공격 데미지 +50%"}
            )
        ],
        "shadow_mastery": [
            TraitEffect(
                trait_id="shadow_mastery",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=30,
                condition="stealth_observe",
                metadata={"gimmick_field": "stealth_bonus", "description": "은신 중 관찰 시 보너스 +30 자동 충전"}
            )
        ],
        "shadow_master": [
            TraitEffect(
                trait_id="shadow_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=2.5,
                condition="stealth_first_attack",
                metadata={"description": "은신 후 첫 공격 데미지 +150%"}
            )
        ],

        # ============================================================
        # === 배틀메이지 (Battle Mage) - 룬/공명 시스템 ===
        # ============================================================
        "resonance_expert": [
            TraitEffect(
                trait_id="resonance_expert",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.25,
                metadata={"gimmick_field": "resonance_gauge", "multiplier": True, "description": "공명 게이지 획득량 +25%"}
            ),
            TraitEffect(
                trait_id="resonance_expert",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=2,
                condition="resonance_100",
                metadata={"gimmick_field": "burst_duration", "description": "공명 100 시 자동 방출 +2초"}
            )
        ],
        "chain_ignition": [
            TraitEffect(
                trait_id="chain_ignition",
                effect_type=TraitEffectType.PASSIVE,
                value=0.15,
                metadata={"ignition_chance_bonus": 0.15, "spread_bonus": 0.1, "description": "점화 확률 +15%, 확산 +10%"}
            )
        ],
        "rune_archivist": [
            TraitEffect(
                trait_id="rune_archivist",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=1,
                metadata={"gimmick_field": "active_rune_slots", "description": "활성 룬 슬롯 +1"}
            ),
            TraitEffect(
                trait_id="rune_archivist",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=2,
                metadata={"gimmick_field": "rune_max_per_slot", "description": "룬 칸 최대치 +2"}
            )
        ],
        "catalyst_engineer": [
            TraitEffect(
                trait_id="catalyst_engineer",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.03,
                target_stat="speed",
                condition="catalyst_success",
                metadata={"per_rune": True, "duration": 2, "description": "촉매 변환 시 룬당 속도 +3% (2턴)"}
            )
        ],
        "arcane_conductor": [
            TraitEffect(
                trait_id="arcane_conductor",
                effect_type=TraitEffectType.MP_REGEN,
                value=8,
                condition="rune_execute",
                metadata={"description": "룬 인/아웃 실행 시 MP 8 회복"}
            )
        ],

        # ============================================================
        # === 버서커 (Berserker) - 분노 시스템 ===
        # ============================================================
        "rage_control": [
            TraitEffect(
                trait_id="rage_control",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.5,
                metadata={"gimmick_field": "rage_decay_reduction", "description": "분노 자연 감소율 -50%"}
            )
        ],
        "bloodlust": [
            TraitEffect(
                trait_id="bloodlust",
                effect_type=TraitEffectType.HP_REGEN,
                value=0.15,
                condition="on_kill",
                metadata={"description": "적 처치 시 HP 15% 회복"}
            ),
            TraitEffect(
                trait_id="bloodlust",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=20,
                condition="on_kill",
                metadata={"gimmick_field": "rage", "description": "적 처치 시 분노 20 충전"}
            )
        ],
        "last_stand": [
            TraitEffect(
                trait_id="last_stand",
                effect_type=TraitEffectType.SURVIVE_FATAL,
                value=1,
                condition="hp_below_15",
                metadata={"once_per_battle": True, "description": "HP 15% 이하 치명상 면역 1회"}
            ),
            TraitEffect(
                trait_id="last_stand",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=50,
                condition="hp_below_15",
                metadata={"gimmick_field": "rage", "description": "HP 15% 이하 시 분노 50 충전"}
            )
        ],
        "berserker_rush": [
            TraitEffect(
                trait_id="berserker_rush",
                effect_type=TraitEffectType.EXTRA_ACTION,
                value=1,
                condition="rage_min_50",
                metadata={"rage_cost": 50, "once_per_turn": True, "damage_penalty": 0.3,
                         "description": "분노 50 소모 추가 행동 (데미지 -30%)"}
            )
        ],
        "pain_to_power": [
            TraitEffect(
                trait_id="pain_to_power",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.05,
                condition="on_damaged",
                metadata={"gimmick_field": "pain_stacks", "max_stacks": 10,
                         "description": "피격 시 '고통' +1, 스택당 데미지 +5% (최대 +50%)"}
            )
        ],

        # ============================================================
        # === 성직자 (Cleric) - 신앙/치유 시스템 ===
        # ============================================================
        "healing_power": [
            TraitEffect(
                trait_id="healing_power",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.4,
                metadata={"description": "모든 회복 효과 +40%"}
            )
        ],
        "faith_shield": [
            TraitEffect(
                trait_id="faith_shield",
                effect_type=TraitEffectType.PASSIVE,
                value=0.4,
                condition="on_heal",
                metadata={"shield_ratio": 0.4, "description": "아군 치유 시 회복량의 40% 보호막 부여"}
            )
        ],
        "divine_grace": [
            TraitEffect(
                trait_id="divine_grace",
                effect_type=TraitEffectType.COOLDOWN_REDUCTION,
                value=0.6,
                condition="mp_above_50",
                metadata={"description": "MP 50%+ 시 회복 스킬 캐스팅 -60%"}
            )
        ],
        "resurrection_master": [
            TraitEffect(
                trait_id="resurrection_master",
                effect_type=TraitEffectType.PASSIVE,
                value=0.25,
                condition="on_heal",
                metadata={"brv_bonus_ratio": 0.25, "description": "아군 치유 시 회복량의 25% BRV 추가"}
            )
        ],
        "prayer_blessing": [
            TraitEffect(
                trait_id="prayer_blessing",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.05,
                condition="turn_start",
                metadata={"stat": "hp_regen", "description": "매 턴 아군 전체 HP 5% 회복"}
            )
        ],

        # ============================================================
        # === 암흑기사 (Dark Knight) - 암흑 충전 시스템 ===
        # ============================================================
        "perfect_strike": [
            TraitEffect(
                trait_id="perfect_strike",
                effect_type=TraitEffectType.EXECUTE,
                value=0.15,
                condition="charge_100",
                metadata={"boss_damage_bonus": 0.5, "description": "충전 100%에서 15% 즉사, 보스 50% 추가피해"}
            )
        ],
        "charge_acceleration": [
            TraitEffect(
                trait_id="charge_acceleration",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.5,
                metadata={"gimmick_field": "dark_charge", "multiplier": True, "description": "충전 속도 50% 향상"}
            )
        ],
        "survival_instinct": [
            TraitEffect(
                trait_id="survival_instinct",
                effect_type=TraitEffectType.HP_SCALING_ATTACK,
                value=0.5,
                metadata={"inverse": True, "description": "HP 낮을수록 데미지 상승 (최대 +50%)"}
            ),
            TraitEffect(
                trait_id="survival_instinct",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=1.3,
                metadata={"description": "받는 회복 효과 +30%"}
            )
        ],
        "explosive_power": [
            TraitEffect(
                trait_id="explosive_power",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0,
                condition="charge_min_75",
                metadata={"gimmick_field": "dark_charge", "threshold": 75, "aoe_explosion": True,
                         "description": "충전 75%+ 스킬 시 소모 충전량 비례 AOE 폭발"}
            )
        ],
        "overflowing_darkness": [
            TraitEffect(
                trait_id="overflowing_darkness",
                effect_type=TraitEffectType.PASSIVE,
                value=0.1,
                condition="turn_start_charge_50",
                metadata={"gimmick_field": "dark_charge", "threshold": 50, "brv_regen": True,
                         "description": "매 턴 충전 50%+ 시 BRV 최대치의 10% 회복"}
            )
        ],

        # ============================================================
        # === 차원술사 (Dimensionist) - 차원 시스템 ===
        # ============================================================
        "dimensional_stabilization": [
            TraitEffect(
                trait_id="dimensional_stabilization",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.5,
                metadata={"gimmick_field": "dimensional_penalty_reduction", "description": "차원 불안정 페널티 반감 (15%→7.5%)"}
            )
        ],
        "self_healing_mastery": [
            TraitEffect(
                trait_id="self_healing_mastery",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=2.0,
                condition="self_heal",
                metadata={"description": "자가 치유 스킬 회복량 200% 증폭"}
            ),
            TraitEffect(
                trait_id="self_healing_mastery",
                effect_type=TraitEffectType.HEAL_BONUS,
                value=0.2,
                condition="external_heal",
                metadata={"description": "외부 회복 80% 감소"}
            )
        ],
        "fixed_damage_amplification": [
            TraitEffect(
                trait_id="fixed_damage_amplification",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="fixed_damage_skill",
                metadata={"description": "고정 데미지 스킬 +50%"}
            )
        ],
        "double_refraction": [
            TraitEffect(
                trait_id="double_refraction",
                effect_type=TraitEffectType.DAMAGE_REDUCTION,
                value=0.5,
                metadata={"description": "받는 모든 피해 50% 추가 감소"}
            )
        ],
        "quantum_entanglement": [
            TraitEffect(
                trait_id="quantum_entanglement",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1.0,
                metadata={
                    "ally_damage_absorb": 0.30,
                    "ally_attack_amp_ratio": 0.08,
                    "refraction_decay_on_amp": 0.06,
                    "description": "아군 피해 30% 흡수→굴절, 아군 HP 공격 시 굴절 비례 피해 증폭"
                }
            )
        ],

        # ============================================================
        # === 용기사 (Dragon Knight) - 용염 시스템 ===
        # ============================================================
        "dragon_breath": [
            TraitEffect(
                trait_id="dragon_breath",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.35,
                condition="fire_element",
                metadata={"description": "화염 속성 데미지 +35%"}
            ),
            TraitEffect(
                trait_id="dragon_breath",
                effect_type=TraitEffectType.DEBUFF_DURATION,
                value=1,
                condition="fire_dot",
                metadata={"description": "화염 지속 효과 지속시간 +50%"}
            )
        ],
        "burning_rage": [
            TraitEffect(
                trait_id="burning_rage",
                effect_type=TraitEffectType.LIFESTEAL,
                value=0.7,
                condition="target_burning",
                metadata={"description": "화염 상태 적 공격 시 피해의 70% 체력 회복"}
            ),
            TraitEffect(
                trait_id="burning_rage",
                effect_type=TraitEffectType.HP_REGEN,
                value=-0.04,
                condition="turn_start",
                metadata={"description": "매턴 HP/MP 4% 감소 (부작용)"}
            )
        ],
        "dragon_scales": [
            TraitEffect(
                trait_id="dragon_scales",
                effect_type=TraitEffectType.DAMAGE_REDUCTION,
                value=0.85,
                condition="hp_above_95",
                metadata={"description": "HP 95%+ 시 받는 피해 85% 감소"}
            )
        ],
        "flame_wings": [
            TraitEffect(
                trait_id="flame_wings",
                effect_type=TraitEffectType.COUNTER,
                value=1,
                condition="evasion_success",
                metadata={"fire_aoe": True, "description": "회피 성공 시 반경에 화염 피해"}
            )
        ],
        "inferno": [
            TraitEffect(
                trait_id="inferno",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.3,
                condition="target_burning",
                metadata={"description": "이미 연소 중인 적에게 데미지 +30%"}
            )
        ],

        # ============================================================
        # === 기술자 (Engineer) - 터렛/열량 시스템 ===
        # ============================================================
        "turret_reinforcement": [
            TraitEffect(
                trait_id="turret_reinforcement",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.2,
                condition="turret_attack",
                metadata={"description": "터렛 데미지 +20%"}
            ),
            TraitEffect(
                trait_id="turret_reinforcement",
                effect_type=TraitEffectType.PASSIVE,
                value=0.1,
                condition="turret_attack",
                metadata={"status_chance_bonus": 0.1, "description": "터렛 상태이상 확률 +10%"}
            )
        ],
        "turret_shield": [
            TraitEffect(
                trait_id="turret_shield",
                effect_type=TraitEffectType.DAMAGE_REDUCTION,
                value=0.2,
                condition="turret_min_3",
                metadata={"gimmick_field": "turret_count", "threshold": 3, "description": "터렛 3개+ 시 받는 피해 -20%"}
            )
        ],
        "heat_efficiency": [
            TraitEffect(
                trait_id="heat_efficiency",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.3,
                condition="heat_optimal",
                metadata={"heat_range": [50, 79], "description": "열량 적정(50-79) 시 터렛 데미지 +30%"}
            )
        ],
        "overheat_prevention": [
            TraitEffect(
                trait_id="overheat_prevention",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=-30,
                condition="heat_80_plus",
                metadata={"gimmick_field": "heat", "max_uses": 3, "description": "열량 80+ 시 자동 -30 (전투당 3회)"}
            )
        ],
        "double_turret": [
            TraitEffect(
                trait_id="double_turret",
                effect_type=TraitEffectType.PASSIVE,
                value=1.0,
                condition="turret_deploy",
                metadata={"extra_turret": True, "description": "터렛 배치 시 100% 추가 1개 설치"}
            )
        ],

        # ============================================================
        # === 해커 (Hacker) - 침투/RAM 시스템 ===
        # ============================================================
        "parallel_processing": [
            TraitEffect(
                trait_id="parallel_processing",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                condition="turn_start",
                metadata={"gimmick_field": "ram", "description": "매 턴 RAM +1 추가 회복"}
            )
        ],
        "intrusion_expert": [
            TraitEffect(
                trait_id="intrusion_expert",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.2,
                metadata={"gimmick_field": "intrusion", "multiplier": True, "description": "침투 획득량 +20%"}
            )
        ],
        "botnet": [
            TraitEffect(
                trait_id="botnet",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=20,
                condition="hack_success",
                metadata={"gimmick_field": "intrusion", "aoe": True, "description": "해킹 성공 시 주변 적에게 침투 +20 전파"}
            )
        ],
        "zero_day_hunter": [
            TraitEffect(
                trait_id="zero_day_hunter",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=30,
                condition="new_target",
                metadata={"gimmick_field": "intrusion", "description": "새로운 적 공격 시 침투 +30"}
            )
        ],
        "virtualization": [
            TraitEffect(
                trait_id="virtualization",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.5,
                metadata={"gimmick_field": "reboot_hp_penalty_reduction", "description": "리부트 HP 페널티 50% 감소"}
            )
        ],

        # ============================================================
        # === 환술사 (Illusionist) - 환영 시스템 ===
        # ============================================================
        "mirror_image": [
            TraitEffect(
                trait_id="mirror_image",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=2,
                condition="battle_start",
                metadata={"gimmick_field": "phantoms", "description": "전투 시작 시 환영 2개 자동 생성"}
            ),
            TraitEffect(
                trait_id="mirror_image",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.25,
                metadata={"gimmick_field": "phantom_extra_chance", "description": "소환 시 25% 추가 환영"}
            )
        ],
        "mirage_step": [
            TraitEffect(
                trait_id="mirage_step",
                effect_type=TraitEffectType.ATB_BOOST,
                value=0.1,
                condition="evasion_success",
                metadata={"description": "회피 성공 시 ATB +10%"}
            ),
            TraitEffect(
                trait_id="mirage_step",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.2,
                condition="after_evasion",
                metadata={"description": "회피 후 다음 피해 +20%"}
            )
        ],
        "phantom_lord": [
            TraitEffect(
                trait_id="phantom_lord",
                effect_type=TraitEffectType.PASSIVE,
                value=-0.15,
                condition="phantom_min_4",
                metadata={"gimmick_field": "phantoms", "threshold": 4, "enemy_accuracy_debuff": True,
                         "description": "환영 4개 유지 시 적 전체 명중률 -15%"}
            )
        ],
        "shadow_feast": [
            TraitEffect(
                trait_id="shadow_feast",
                effect_type=TraitEffectType.HP_REGEN,
                value=0.05,
                condition="phantom_destroyed",
                metadata={"description": "환영 소멸 시 HP 5% 회복"}
            ),
            TraitEffect(
                trait_id="shadow_feast",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.15,
                condition="phantom_destroyed",
                metadata={"duration": 2, "description": "환영 소멸 후 피해 +15% (2턴)"}
            ),
            TraitEffect(
                trait_id="shadow_feast",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.3,
                condition="phantom_destroyed",
                metadata={"description": "환영 소멸 시 30% 확률 재생성"}
            )
        ],
        "infinite_mirrors": [
            TraitEffect(
                trait_id="infinite_mirrors",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.2,
                metadata={"gimmick_field": "phantoms", "description": "환영 소멸 시 20% 즉시 재생성"}
            ),
            TraitEffect(
                trait_id="infinite_mirrors",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.5,
                condition="hp_below_30",
                metadata={"gimmick_field": "phantoms", "description": "HP 30% 이하 시 재생성 50%"}
            ),
            TraitEffect(
                trait_id="infinite_mirrors",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=1,
                metadata={"gimmick_field": "phantom_hit_resistance", "description": "환영 히트 내성 +1"}
            )
        ],

        # ============================================================
        # === 마술사 (Magician) - 카드 시스템 ===
        # ============================================================
        "sleight_of_hand": [
            TraitEffect(
                trait_id="sleight_of_hand",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=1,
                condition="basic_attack",
                metadata={"gimmick_field": "card_draw", "description": "기본 공격 시 카드 드로우 +1장 (총 2장)"}
            )
        ],
        "card_counter": [
            TraitEffect(
                trait_id="card_counter",
                effect_type=TraitEffectType.PASSIVE,
                value=1,
                metadata={"card_prediction": True, "description": "다음 드로우 카드 확률 향상, 핸드 확인 가능"}
            )
        ],
        "poker_face": [
            TraitEffect(
                trait_id="poker_face",
                effect_type=TraitEffectType.STATUS_RESIST,
                value=1.0,
                condition="mental_status",
                metadata={"description": "정신 상태이상(혼란, 매혹, 유혹) 면역"}
            ),
            TraitEffect(
                trait_id="poker_face",
                effect_type=TraitEffectType.DEBUFF_DURATION,
                value=-1,
                metadata={"description": "받는 디버프 지속시간 -1턴"}
            )
        ],
        "wild_card": [
            TraitEffect(
                trait_id="wild_card",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.5,
                condition="poker_card",
                metadata={"description": "포커 카드 사용 시 스킬 효과 +50%"}
            )
        ],
        "royal_flush_ready": [
            TraitEffect(
                trait_id="royal_flush_ready",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.15,
                condition="winnings_min_5",
                metadata={"gimmick_field": "winnings", "threshold": 5, "description": "승리금 5개+ 시 데미지 +15%"}
            ),
            TraitEffect(
                trait_id="royal_flush_ready",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.1,
                condition="winnings_min_5",
                metadata={"description": "승리금 5개+ 시 크리티컬 +10%"}
            )
        ],

        # ============================================================
        # === 수도승 (Monk) - 기력/음양 시스템 ===
        # ============================================================
        "yin_yang_balance": [
            TraitEffect(
                trait_id="yin_yang_balance",
                effect_type=TraitEffectType.HP_REGEN,
                value=0.05,
                condition="qi_balanced",
                metadata={"qi_range": [40, 60], "description": "기력 균형(40-60)에서 HP 5%/턴 회복"}
            ),
            TraitEffect(
                trait_id="yin_yang_balance",
                effect_type=TraitEffectType.MP_REGEN,
                value=0.05,
                condition="qi_balanced",
                metadata={"description": "기력 균형(40-60)에서 MP 5%/턴 회복"}
            )
        ],
        "yang_mastery": [
            TraitEffect(
                trait_id="yang_mastery",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="physical_attack",
                condition="qi_yang",
                metadata={"qi_threshold": 80, "description": "양(80+)에서 물리 공격력 +30%"}
            ),
            TraitEffect(
                trait_id="yang_mastery",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.2,
                condition="qi_yang",
                metadata={"description": "양(80+)에서 크리티컬 +20%"}
            )
        ],
        "yin_mastery": [
            TraitEffect(
                trait_id="yin_mastery",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.3,
                target_stat="magic_attack",
                condition="qi_yin",
                metadata={"qi_threshold": 20, "description": "음(20-)에서 마법 공격력 +30%"}
            ),
            TraitEffect(
                trait_id="yin_mastery",
                effect_type=TraitEffectType.STAT_MULTIPLIER,
                value=1.2,
                target_stat="defense",
                condition="qi_yin",
                metadata={"description": "음(20-)에서 방어 +20%"}
            )
        ],
        "ki_flow": [
            TraitEffect(
                trait_id="ki_flow",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=5,
                condition="turn_start",
                metadata={"gimmick_field": "qi_auto_balance", "target": 50, "description": "매 턴 기력이 균형(50)으로 5씩 이동"}
            )
        ],
        "enlightenment": [
            TraitEffect(
                trait_id="enlightenment",
                effect_type=TraitEffectType.MP_COST_REDUCTION,
                value=0.5,
                condition="qi_perfect_50",
                metadata={"description": "기력 정확히 50에서 MP 소모 50% 감소"}
            )
        ],

        # ============================================================
        # === 네크로맨서 (Necromancer) - 언데드 소환 시스템 ===
        # ============================================================
        "undead_commander": [
            TraitEffect(
                trait_id="undead_commander",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.5,
                metadata={"gimmick_field": "undead_power_bonus", "description": "언데드 3마리 이상 시 모든 언데드 능력 +50%"}
            )
        ],
        "death_harvest": [
            TraitEffect(
                trait_id="death_harvest",
                effect_type=TraitEffectType.ON_KILL,
                value=1.0,
                metadata={"auto_soul_harvest": True, "description": "적 처치 시 소울 자동 획득 (레이스 소환 가능)"}
            )
        ],
        "necromantic_power": [
            TraitEffect(
                trait_id="necromantic_power",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.1,
                target_stat="magic_attack",
                metadata={"per_unit": "undead", "description": "언데드 1마리당 마법 공격력 +10%"}
            )
        ],
        "undead_sacrifice": [
            TraitEffect(
                trait_id="undead_sacrifice",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=20.0,
                condition="undead_destroyed",
                metadata={"restore": "mp", "description": "언데드 파괴 시 MP 20 회복"}
            )
        ],
        "legion_master": [
            TraitEffect(
                trait_id="legion_master",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.2,
                condition="all_undead_types",
                metadata={"description": "전 언데드 타입 1마리이상 보유 시 모든 능력치 +20%"}
            )
        ],

        # ============================================================
        # === 팔라딘 (Paladin) - 신앙 게이지 시스템 ===
        # ============================================================
        "divine_protection": [
            TraitEffect(
                trait_id="divine_protection",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.3,
                condition="faith_50_plus",
                metadata={"effect": "party_crit_nullify", "description": "신앙 50+ 시 파티 전체 크리티컬 무효화 30%"}
            )
        ],
        "holy_aura": [
            TraitEffect(
                trait_id="holy_aura",
                effect_type=TraitEffectType.PARTY_BUFF,
                value=0.2,
                condition="after_heal",
                target_stat="defense",
                metadata={"description": "치유 시전 후 파티 방어 +20%"}
            )
        ],
        "martyr_spirit": [
            TraitEffect(
                trait_id="martyr_spirit",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=15.0,
                condition="ally_damaged",
                metadata={"gimmick_field": "faith", "description": "아군 피격 감지 - 대신 맞기 시 신앙 +15"}
            )
        ],
        "healing_light": [
            TraitEffect(
                trait_id="healing_light",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=5.0,
                condition="after_heal",
                metadata={"gimmick_field": "faith", "description": "치유 시전 후 신앙 +5 추가"}
            )
        ],
        "righteous_fury": [
            TraitEffect(
                trait_id="righteous_fury",
                effect_type=TraitEffectType.DEFENSE_PENETRATION,
                value=0.5,
                condition="undead_target",
                metadata={"description": "언데드 대상 방어력 50% 관통"}
            )
        ],

        # ============================================================
        # === 필로소퍼 (Philosopher) - 네 갈래 길 시스템 ===
        # ============================================================
        "power_mastery": [
            TraitEffect(
                trait_id="power_mastery",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.6,
                condition="power_path_5_plus",
                target_stat="magic_attack",
                metadata={"crit_bonus": 0.3, "description": "힘 경로 5회 이상 시 마법 공격력 +60%, 크리티컬 +30%"}
            )
        ],
        "wisdom_mastery": [
            TraitEffect(
                trait_id="wisdom_mastery",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.6,
                condition="wisdom_path_5_plus",
                target_stat="magic_attack",
                metadata={"mp_regen": 5, "description": "지혜 경로 5회 이상 시 마법 공격력 +60%, MP 회복 +5/턴"}
            )
        ],
        "sacrifice_mastery": [
            TraitEffect(
                trait_id="sacrifice_mastery",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=1.0,
                condition="sacrifice_path_5_plus",
                metadata={"auto_revive_ally": True, "description": "희생 경로 5회 이상 시 아군 사망 시 자동 부활 (1회)"}
            )
        ],
        "truth_mastery": [
            TraitEffect(
                trait_id="truth_mastery",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=2.0,
                condition="truth_path_5_plus",
                metadata={"debuff_duration_multiplier": True, "description": "진실 경로 5회 이상 시 적 디버프 효과 2배"}
            )
        ],
        "balanced_philosophy": [
            TraitEffect(
                trait_id="balanced_philosophy",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.2,
                condition="all_paths_balanced",
                metadata={"min_diff": 2, "description": "모든 경로 카운트가 균등(최대 2 차이)할 때 모든 스탯 +20%"}
            )
        ],

        # ============================================================
        # === 저격수 (Sniper) - 탄창 관리 시스템 ===
        # ============================================================
        "last_bullet": [
            TraitEffect(
                trait_id="last_bullet",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.5,
                condition="last_magazine_bullet",
                metadata={"crit_bonus": 0.5, "damage_bonus": 0.3, "description": "마지막 탄환 크리 +50%, 데미지 +30%"}
            )
        ],
        "quick_hands": [
            TraitEffect(
                trait_id="quick_hands",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1.0,
                condition="on_reload",
                metadata={"free_turn": True, "max_uses": 2, "description": "재장전 시 턴 소모 안함 (전투당 2회)"}
            )
        ],
        "bullet_conservation": [
            TraitEffect(
                trait_id="bullet_conservation",
                effect_type=TraitEffectType.PASSIVE,
                value=0.3,
                metadata={"save_ammo_chance": True, "description": "30% 확률로 탄환 소모하지 않음"}
            )
        ],
        "precision_aim": [
            TraitEffect(
                trait_id="precision_aim",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.5,
                metadata={"gimmick_field": "special_bullet_effect", "description": "특수 탄환 사용 시 효과 +50%"}
            )
        ],
        "headshot_master": [
            TraitEffect(
                trait_id="headshot_master",
                effect_type=TraitEffectType.EXECUTE,
                value=0.05,
                condition="on_critical",
                metadata={"boss_immune": True, "description": "크리티컬 시 즉사 확률 5% (보스 제외)"}
            )
        ],

        # ============================================================
        # === 검성 (Sword Saint) - 검기 시스템 ===
        # ============================================================
        "sword_energy": [
            TraitEffect(
                trait_id="sword_energy",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.3,
                target_stat="physical_attack",
                metadata={"on_normal_attack": True, "description": "일반 공격 시 검기로 추가 피해 (공격력의 30%)"}
            )
        ],
        "rapid_slash": [
            TraitEffect(
                trait_id="rapid_slash",
                effect_type=TraitEffectType.DOUBLE_ATTACK,
                value=0.25,
                metadata={"description": "일반 공격 시 25% 확률로 추가 공격"}
            )
        ],
        "sword_aura_mastery": [
            TraitEffect(
                trait_id="sword_aura_mastery",
                effect_type=TraitEffectType.GIMMICK_MAX_BONUS,
                value=2.0,
                metadata={"gain_rate_bonus": 1, "description": "검기 최대치 +2, 검기 획득량 +1"}
            )
        ],
        "focus_strike": [
            TraitEffect(
                trait_id="focus_strike",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=0.4,
                condition="full_sword_energy",
                metadata={"gimmick_field": "damage_bonus", "description": "검기 최대 충전 시 데미지 +40%"}
            )
        ],
        "final_strike": [
            TraitEffect(
                trait_id="final_strike",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=0.5,
                condition="hp_below_30",
                metadata={"description": "HP 30% 미만일 때 모든 데미지 +50%"}
            )
        ],

        # ============================================================
        # === 시간술사 (Time Mage) - 가능성 슬롯 시스템 ===
        # ============================================================
        "branch_creator": [
            TraitEffect(
                trait_id="branch_creator",
                effect_type=TraitEffectType.GIMMICK_GAIN_BONUS,
                value=0.15,
                metadata={"luck_scaling": 0.0025, "max_chance": 0.95, "description": "가능성 생성 확률 +15%, 행운 4당 +1% (최대 95%)"}
            )
        ],
        "parallel_resonance": [
            TraitEffect(
                trait_id="parallel_resonance",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.08,
                target_stat="magic_attack",
                metadata={"damage_reduction_per_slot": 0.05, "full_slot_atb": 0.15, "description": "가능성 1개당 마공 +8%, 받는 피해 -5%"}
            )
        ],
        "timeline_interference": [
            TraitEffect(
                trait_id="timeline_interference",
                effect_type=TraitEffectType.GIMMICK_PRESERVE,
                value=0.3,
                metadata={"max_reuse": 2, "description": "가능성 소환 시 30% 확률로 소멸하지 않음 (최대 2회)"}
            )
        ],
        "converging_fates": [
            TraitEffect(
                trait_id="converging_fates",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.4,
                condition="time_storm_3_plus",
                metadata={"apply_time_lock": True, "time_lock_duration": 1, "description": "시간 폭풍 3+ 가능성 해방 시 피해 +40%, 시간 고정 1턴"}
            )
        ],
        "infinite_branches": [
            TraitEffect(
                trait_id="infinite_branches",
                effect_type=TraitEffectType.PASSIVE,
                value=1.0,
                metadata={"start_with_possibility": 1, "low_hp_threshold": 0.3, "low_hp_gen_chance": 1.0, "description": "전투 시작 시 가능성 1개, HP 30% 이하 시 생성 확률 100%"}
            )
        ],

        # ============================================================
        # === 흡혈귀 (Vampire) - 갈증 관리 시스템 ===
        # ============================================================
        "sanguine_arts": [
            TraitEffect(
                trait_id="sanguine_arts",
                effect_type=TraitEffectType.LIFESTEAL,
                value=0.2,
                metadata={"magic_attack_bonus": 0.15, "on_magic_attack": True, "description": "마법 공격 시 20% 흡혈, 마법 공격력 +15%"}
            )
        ],
        "vitality_overflow": [
            TraitEffect(
                trait_id="vitality_overflow",
                effect_type=TraitEffectType.GIMMICK_MODIFIER,
                value=1.0,
                metadata={"gimmick_field": "excess_lifesteal_to_brv", "description": "최대 체력 시 초과 흡혈량을 BRV 회복으로 전환"}
            )
        ],
        "bleeding_heart": [
            TraitEffect(
                trait_id="bleeding_heart",
                effect_type=TraitEffectType.CRITICAL_BONUS,
                value=0.3,
                condition="target_bleeding",
                metadata={"crit_damage_bonus": 0.3, "description": "출혈 상태 적에게 크리 확률 +30%, 크리 데미지 +30%"}
            )
        ],
        "shadow_veil": [
            TraitEffect(
                trait_id="shadow_veil",
                effect_type=TraitEffectType.PASSIVE,
                value=0.15,
                target_stat="evasion",
                metadata={"stealth_on_low_hp": True, "hp_threshold": 0.3, "max_uses": 1, "description": "회피 +15%, HP 30% 미만 시 은신 (전투당 1회)"}
            )
        ],
        "blood_empowerment": [
            TraitEffect(
                trait_id="blood_empowerment",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0.3,
                condition="on_lifesteal",
                metadata={"atk_bonus": 0.2, "speed_bonus": 0.15, "duration": 3, "description": "흡혈 성공 시 30% 확률로 공격 +20%, 속도 +15% 3턴"}
            )
        ],

        # ============================================================
        # === 전사 (Warrior) - 자세 전환 시스템 ===
        # ============================================================
        "adaptive_combat": [
            TraitEffect(
                trait_id="adaptive_combat",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0.3,
                condition="on_stance_change",
                metadata={"damage_reduction": True, "description": "자세 전환 시 받는 피해 30% 감소"}
            )
        ],
        "battlefield_master": [
            TraitEffect(
                trait_id="battlefield_master",
                effect_type=TraitEffectType.GIMMICK_SCALING,
                value=0.35,
                metadata={"per_unit": "stance_uses", "description": "누적 자세 사용 시 해당 능력치 보너스 증가 (최대 35%)"}
            )
        ],
        "indomitable_will": [
            TraitEffect(
                trait_id="indomitable_will",
                effect_type=TraitEffectType.HP_REGEN,
                value=0.08,
                condition="defense_stance",
                metadata={"description": "방어 자세에서 매 턴 HP 8% 회복"}
            )
        ],
        "combat_instinct": [
            TraitEffect(
                trait_id="combat_instinct",
                effect_type=TraitEffectType.MP_COST_REDUCTION,
                value=0.3,
                condition="stance_change_skill",
                metadata={"description": "자세 전환 스킬 MP 소모 감소"}
            )
        ],
        "complete_mastery": [
            TraitEffect(
                trait_id="complete_mastery",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=0.15,
                condition="all_stances_3_plus",
                metadata={"stance_change_bonus": 0.1, "description": "모든 자세 3회 이상 사용 시 모든 자세 보너스 +15%, 전환 보너스 +10%"}
            )
        ],

        # ============================================================
        # === 닌자 (Ninja) - 인법 연쇄 시스템 ===
        # ============================================================
        "ninjutsu_master": [
            TraitEffect(
                trait_id="ninjutsu_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.2,
                condition="elemental_skill",
                metadata={"description": "속성 스킬 피해 +20%"}
            ),
            TraitEffect(
                trait_id="ninjutsu_master",
                effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
                value=1.15,
                condition="weakness_hit",
                metadata={"description": "속성 약점 적중 시 추가 +15%"}
            )
        ],
        "afterimage_step": [
            TraitEffect(
                trait_id="afterimage_step",
                effect_type=TraitEffectType.STAT_PERCENT,
                value=0.1,
                target_stat="speed",
                metadata={"description": "속도 +10%"}
            ),
            TraitEffect(
                trait_id="afterimage_step",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1,
                condition="on_evade",
                metadata={"gimmick_field": "seal_wind", "description": "회피 성공 시 풍(風) 인 1개 자동 축적"}
            )
        ],
        "covert_entry": [
            TraitEffect(
                trait_id="covert_entry",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=1.0,
                condition="battle_start",
                metadata={"stealth": True, "first_critical": True, "description": "전투 첫 턴 은신 상태, 첫 공격 크리티컬 확정"}
            )
        ],
        "smoke_escape": [
            TraitEffect(
                trait_id="smoke_escape",
                effect_type=TraitEffectType.GIMMICK_CONDITIONAL,
                value=1,
                condition="hp_below_30",
                metadata={"auto_evade": 1, "enter_stealth": True, "once_per_battle": True,
                         "description": "HP 30% 이하 시 자동 회피 1회 + 은신 (전투 1회)"}
            )
        ],
        "gale_fury": [
            TraitEffect(
                trait_id="gale_fury",
                effect_type=TraitEffectType.GIMMICK_TRIGGER,
                value=0.95,
                condition="consecutive_3_actions",
                metadata={"atb_bonus": True, "threshold": 3, "description": "연속 3회 행동 시 ATB +95%"}
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
