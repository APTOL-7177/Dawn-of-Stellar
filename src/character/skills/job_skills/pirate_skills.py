"""Pirate Skills - 해적 (럼주 & 보물 시스템)

럼주를 마시면 랜덤 효과 발동 (도박!)
적 처치 시 보물 획득, 강력한 일회용 효과

"인생은 도박이야, 럼주나 마셔"
"""
import random
from typing import Any, Optional, Dict, List
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.base import SkillEffect, EffectType, EffectResult
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("pirate_skills")

# ============================================================
# 보물 종류 정의 (18종)
# ============================================================
TREASURE_TYPES = {
    # === Tier C: 기본 보물 (Weight: 20-30) ===
    "gold_pouch": {
        "name": "금화 주머니",
        "tier": "C",
        "effect": "brv_boost",
        "value": 0.5,  # BRV +50%
        "description": "즉시 BRV +50%",
        "weight": 30
    },
    "pirate_pistol": {
        "name": "해적 권총",
        "tier": "C",
        "effect": "bonus_attack",
        "value": 1.5,  # 추가 공격 1.5배
        "description": "현재 BRV의 150% HP 피해",
        "weight": 25
    },
    "cursed_coin": {
        "name": "저주받은 동전",
        "tier": "C",
        "effect": "enemy_debuff",
        "value": 0.3,  # 30% 감소
        "description": "적 전체 공/방 -30% (3턴)",
        "weight": 20
    },
    "lucky_dice": {
        "name": "행운의 주사위",
        "tier": "C",
        "effect": "gamble",
        "value": 2.0,  # 2배 or 0.5배
        "description": "다음 스킬 피해 2배 or 0.5배",
        "weight": 22
    },
    "black_pearl": {
        "name": "검은 진주",
        "tier": "C",
        "effect": "ultimate_charge",
        "value": 50,  # 게이지 +50
        "description": "팀워크 게이지 +50",
        "weight": 20
    },
    
    # === Tier B: 중급 보물 (Weight: 13-18) ===
    "pirate_flag": {
        "name": "해적 깃발",
        "tier": "B",
        "effect": "team_buff_atk",
        "value": 0.3,  # 공격력 +30%
        "duration": 3,
        "description": "아군 전체 공격력 +30% (3턴)",
        "weight": 15
    },
    "compass": {
        "name": "나침반",
        "tier": "B",
        "effect": "gauge_boost",
        "teamwork": 40,
        "atb": 600,
        "description": "팀워크 게이지 +40, ATB +600",
        "weight": 16
    },
    "rum_barrel": {
        "name": "럼주 배럴",
        "tier": "B",
        "effect": "positive_rum",
        "duration_bonus": 1,
        "description": "긍정 럼주 효과 즉시 발동 + 지속 +1턴",
        "weight": 14
    },
    "parrot_charm": {
        "name": "앵무새 부적",
        "tier": "B",
        "effect": "free_skill",
        "description": "다음 스킬 MP 0 + 쿨다운 초기화",
        "weight": 13
    },
    "treasure_map": {
        "name": "보물 지도",
        "tier": "B",
        "effect": "treasure_boost",
        "uses": 3,
        "description": "다음 3전투 보물 획득 100%",
        "weight": 17
    },
    "mermaid_scale": {
        "name": "인어 비늘",
        "tier": "B",
        "effect": "heal_and_evade",
        "heal_percent": 0.3,
        "evasion_bonus": 0.2,
        "duration": 2,
        "description": "아군 전체 HP/MP 30% 회복 + 회피 +20% (2턴)",
        "weight": 18
    },
    
    # === Tier A: 고급 보물 (Weight: 8-12) ===
    "poison_vial": {
        "name": "독약 병",
        "tier": "A",
        "effect": "deadly_poison",
        "damage_percent": 0.1,  # 매턴 최대HP 10%
        "def_down": 0.4,  # 방어력 -40%
        "duration": 5,
        "description": "적 전체 맹독 5턴 (매턴 최대HP 10% + 방어 -40%)",
        "weight": 8
    },
    "cannonball": {
        "name": "대포알",
        "tier": "A",
        "effect": "heavy_damage",
        "value": 2.0,  # BRV의 200%
        "description": "단일 적에게 현재 BRV의 200% HP 피해",
        "weight": 10
    },
    "sea_serpent_fang": {
        "name": "바다뱀 독니",
        "tier": "A",
        "effect": "instant_death",
        "death_chance": 0.3,  # 30% 즉사
        "damage_fallback": 0.3,  # 실패 시 HP 30%
        "description": "단일 적 30% 즉사 또는 HP 30% 고정 피해",
        "weight": 9
    },
    "storm_bottle": {
        "name": "폭풍의 병",
        "tier": "A",
        "effect": "aoe_debuff",
        "brv_down": 0.5,  # BRV -50%
        "speed_down": 0.3,  # 속도 -30%
        "duration": 3,
        "description": "적 전체 BRV -50% + 속도 -30% (3턴)",
        "weight": 11
    },
    
    # === Tier S: 희귀 보물 (Weight: 3-6) ===
    "kraken_eye": {
        "name": "크라켄의 눈",
        "tier": "S",
        "effect": "brv_steal",
        "enemy_brv_zero": True,
        "self_brv_boost": 0.8,  # +80%
        "description": "적 전체 BRV 0 + 자신 BRV +80%",
        "weight": 3
    },
    "poseidon_trident": {
        "name": "포세이돈의 삼지창",
        "tier": "S",
        "effect": "ultimate_strike",
        "value": 3.0,  # BRV의 300%
        "stun_duration": 2,
        "description": "단일 적 BRV 300% HP 피해 + 기절 2턴",
        "weight": 4
    },
    "phoenix_feather": {
        "name": "불사조 깃털",
        "tier": "S",
        "effect": "resurrection",
        "heal_percent": 0.5,  # HP 50% 회복
        "revive_duration": 3,  # 부활 버프 3턴
        "description": "아군 전체 HP 50% 회복 + 부활 버프 (3턴)",
        "weight": 5
    }
}


# ============================================================
# 럼주 효과 정의 (24종)
# ============================================================
RUM_EFFECTS = {
    # === 긍정 효과 Tier S (14개) ===
    "jackpot": {
        "name": "★ 대박 ★",
        "positive": True,
        "tier": "S",
        "attack_multiplier": 3.0,
        "critical_chance": 1.0,
        "duration": 2,
        "description": "공격력 3배 + 100% 크리티컬 (2턴)"
    },
    "invincible_drunk": {
        "name": "★ 무적 취권 ★",
        "positive": True,
        "tier": "S",
        "evasion_modifier": 1.0,
        "counter_attack": True,
        "duration": 2,
        "description": "회피 +100%, 회피 시 반격 (2턴)"
    },
    "liquid_courage": {
        "name": "★ 액체 용기 ★",
        "positive": True,
        "tier": "A",
        "damage_reduction": 0.5,
        "hp_regen": 0.1,
        "duration": 3,
        "description": "피해 50% 감소 + 매턴 HP 10% 회복 (3턴)"
    },
    "sea_kings_blessing": {
        "name": "★ 바다왕의 축복 ★",
        " positive": True,
        "tier": "S",
        "all_stats_up": 0.3,  # 모든 스탯 +30%
        "duration": 3,
        "description": "모든 스탯 +30% (3턴)"
    },
    "golden_rush": {
        "name": "★ 황금 러시 ★",
        "positive": True,
        "tier": "A",
        "brv_multiplier": 2.0,  # BRV 획득 2배
        "treasure_chance": 1.0,  # 보물 획득률 100%
        "duration": 2,
        "description": "BRV 획득 2배, 보물 확정 드랍 (2턴)"
    },
    "double_shot": {
        "name": "★ 더블 샷 ★",
        "positive": True,
        "tier": "S",
        "extra_action": True,  # 추가 행동
        "duration": 1,
        "description": "즉시 추가 행동 1회!"
    },
    "iron_liver": {
        "name": "★ 강철 간 ★",
        "positive": True,
        "tier": "A",
        "status_immunity": True,  # 상태이상 면역
        "hp_regen": 0.2,
        "duration": 4,
        "description": "상태이상 면역 + 매턴 HP 20% 회복 (4턴)"
    },
    "pirates_luck": {
        "name": "★ 해적의 행운 ★",
        "positive": True,
        "tier": "A",
        "critical_damage": 2.0,  # 크리티컬 데미지 2배
        "luck_modifier": 0.5,  # 행운 +50%
        "duration": 3,
        "description": "크리티컬 데미지 2배, 행운 +50% (3턴)"
    },
    "rum_overdrive": {
        "name": "★ 럼 오버드라이브 ★",
        "positive": True,
        "tier": "S",
        "atb_gain": 1000,  # 즉시 ATB +1000
        "speed_modifier": 0.8,  # 속도 +80%
        "duration": 3,
        "description": "즉시 ATB +1000 + 속도 +80% (3턴)"
    },
    "captains_authority": {
        "name": "★ 선장의 위엄 ★",
        "positive": True,
        "tier": "A",
        "party_atk_up": 0.25,  # 파티 전체 공격력 +25%
        "party_def_up": 0.25,  # 파티 전체 방어력 +25%
        "duration": 3,
        "description": "파티 전체 공/방 +25% (3턴)"
    },
    "ocean_blessing": {
        "name": "★ 대양의 축복 ★",
        "positive": True,
        "tier": "A",
        "hp_mp_regen": 0.15,  # 매턴 HP/MP 15% 회복
        "brv_regen": 0.2,  # BRV 리젠 20%
        "duration": 4,
        "description": "매턴 HP/MP/BRV 회복 (4턴)"
    },
    "perfect_aim": {
        "name": "★ 완벽한 조준 ★",
        "positive":  True,
        "tier": "A",
        "accuracy_modifier": 1.0,  # 명중 +100% (확정 명중)
        "critical_chance": 0.5,  # 크리티컬 +50%
        "duration": 3,
        "description": "확정 명중 + 크리티컬 +50% (3턴)"
    },
    "phoenix_rum": {
        "name": "★ 불사조 럼 ★",
        "positive": True,
        "tier": "S",
        "auto_revive": True,  # 자동 부활 1회
        "revive_hp": 0.5,  # 부활 시 HP 50%
        "duration": 5,
        "description": "전투불능 시 자동 부활 1회 (5턴)"
    },
    "treasure_hunter": {
        "name": "★ 보물 사냥꾼 ★",
        "positive": True,
        "tier": "A",
        "treasure_chance": 0.8,  # 보물 확률 +80%
        "gold_bonus": 2.0,  # 골드 2배
        "duration": 3,
        "description": "보물 확률 +80%, 골드 2배 (3턴)"
    },
    
    # === 부정 효과 Tier D (6개) ===
    "tipsy": {
        "name": "✗ 비틀거림 ✗",
        "positive": False,
        "tier": "D",
        "accuracy_modifier": -0.6,  # 명중 -60%
        "evasion_modifier": 0.8,  # 회피 +80%
        "duration": 3,
        "description": "명중 -60%, 회피 +80% (3턴)"
    },
    "fire_blood": {
        "name": "✗ 피가 끓는다 ✗",
        "positive": False,
        "tier": "D",
        "self_damage": 0.15,  # 매턴 15% 자해
        "attack_multiplier": 2.5,  # 공격력 +150%
        "speed_modifier": 0.5,  # 속도 +50%
        "duration": 3,
        "description": "매턴 자해 15%, 공격력 +150%, 속도 +50% (3턴)"
    },
    "blackout": {
        "name": "✗ 블랙아웃 ✗",
        "positive": False,
        "tier": "D",
        "stun": True,
        "stun_duration": 2,  # 2턴 기절
        "triple_action_next": True,  # 이후 3회 행동
        "duration": 2,
        "description": "2턴 기절, 이후 3회 연속 행동!"
    },
    "berserker_rage": {
        "name": "✗ 광란의 도취 ✗",
        "positive": False,
        "tier": "D",
        "attack_multiplier": 2.0,
        "defense_modifier": -0.5,  # 방어 -50%
        "auto_attack": True,  # 자동 공격 (제어 불가)
        "duration": 3,
        "description": "공격력 2배, 방어 -50%, 제어 불가 (3턴)"
    },
    "hangover": {
        "name": "✗ 숙취 ✗",
        "positive": False,
        "tier": "D",
        "speed_modifier": -0.5,  # 속도 -50%
        "accuracy_modifier": -0.3,  # 명중 -30%
        "mp_drain": 0.1,  # 매턴 MP 10% 감소
        "duration": 4,
        "description": "속도 -50%, 명중 -30%, 매턴 MP -10% (4턴)"
    },
    "broken_bottle": {
        "name": "✗ 병 깨짐 ✗",
        "positive": False,
        "tier": "D",
        "brv_to_zero": True,  # BRV 0으로
        "next_attack_triple": True,  # 다음 공격 3배
        "duration": 1,
        "description": "BRV 0! 다음 공격 3배 피해!"
    },
    
    # === 중립 효과 Tier C (4개) ===
    "roulette": {
        "name": "◆ 럼 룰렛 ◆",
        "positive": None,
        "tier": "C",
        "random_stat": True,  # 랜덤 스탯 +100%
        "duration": 2,
        "description": "랜덤 스탯 하나 +100% (2턴)"
    },
    "gambler": {
        "name": "◆ 도박사의 각성 ◆",
        "positive": None,
        "tier": "C",
        "all_damage_random": True,  # 모든 피해 50%~200%
        "critical_guarantee": True,  # 크리티컬 확정
        "duration": 3,
        "description": "크리티컬 확정, 피해 50~200% 랜덤 (3턴)"
    },
    "swap": {
        "name": "◆ 스왑 럼 ◆",
        "positive": None,
        "tier": "C",
        "swap_hp_mp": True,  # HP/MP 교환
        "duration": 1,
        "description": "현재 HP와 MP 교환!"
    },
    "mirror": {
        "name": "◆ 거울 효과 ◆",
        "positive": None,
        "tier": "C",
        "reflect_damage": True,  # 받은 피해 50% 반사
        "damage_taken_up": 0.5,  # 받는 피해 +50%
        "duration": 3,
        "description": "받은 피해 50% 반사, 받는 피해 +50% (3턴)"
    }
}


def get_random_treasure():
    """가중치 기반 랜덤 보물 획득"""
    total_weight = sum(t["weight"] for t in TREASURE_TYPES.values())
    roll = random.randint(1, total_weight)
    
    current = 0
    for tid, treasure in TREASURE_TYPES.items():
        current += treasure["weight"]
        if roll <= current:
            return tid, treasure
    
    return "gold_pouch", TREASURE_TYPES["gold_pouch"]


def get_random_rum_effect(positive_chance=0.5):
    """럼주 효과 랜덤 선택"""
    effects = list(RUM_EFFECTS.items())
    
    # 긍정/부정 가중치 적용
    if random.random() < positive_chance:
        # 긍정 효과 우선
        positive_effects = [(k, v) for k, v in effects if v.get("positive", False)]
        if positive_effects:
            return random.choice(positive_effects)
    
    return random.choice(effects)


class RumEffect(SkillEffect):
    """럼주 랜덤 효과"""
    def __init__(self, positive_chance=0.5):
        super().__init__(EffectType.GIMMICK)
        self.positive_chance = positive_chance

    def execute(self, user, target, context) -> EffectResult:
        """럼주 효과 실행"""
        import random
        from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
        
        # 1. 랜덤 효과 선택
        effect_id, effect_data = get_random_rum_effect(self.positive_chance)
        
        # 2. 효과 적용
        duration = effect_data.get("duration", 2)
        results = []
        combat_manager = context.get('combat_manager') if context else None
        
        # === 효과 매핑 및 실행 ===
        
        # (1) 공격력 (Attack Multiplier)
        if "attack_multiplier" in effect_data:
            val = effect_data["attack_multiplier"]
            buff_val = val - 1.0
            if buff_val > 0:
                results.append(BuffEffect(BuffType.ATTACK_UP, value=buff_val, duration=duration, target="self").execute(user, user, context))
        
        # (2) 크리티컬 확률
        if "critical_chance" in effect_data:
            val = effect_data["critical_chance"]
            results.append(BuffEffect(BuffType.CRITICAL_UP, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (3) 회피율
        if "evasion_modifier" in effect_data:
            val = effect_data["evasion_modifier"]
            results.append(BuffEffect(BuffType.EVASION_UP, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (4) 피해 감소
        if "damage_reduction" in effect_data:
            val = effect_data["damage_reduction"]
            results.append(BuffEffect(BuffType.DEFENSE_UP, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (5) HP 재생
        if "hp_regen" in effect_data:
            val = effect_data["hp_regen"]
            results.append(BuffEffect(BuffType.HP_REGEN, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (6) 모든 스탯  증가
        if "all_stats_up" in effect_data:
            val = effect_data["all_stats_up"]
            for b_type in [BuffType.ATTACK_UP, BuffType.DEFENSE_UP, BuffType.MAGIC_UP, BuffType.SPIRIT_UP, BuffType.SPEED_UP, BuffType.LUCK]:
                results.append(BuffEffect(b_type, value=val, duration=duration, target="self").execute(user, user, context))
                
        # (7) BRV 획득 배율
        if "brv_multiplier" in effect_data:
            val = effect_data["brv_multiplier"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="brv_gain", value=val, duration=duration, target="self").execute(user, user, context))
            
        # (8) 보물 획득 확률
        if "treasure_chance" in effect_data:
            val = effect_data["treasure_chance"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="treasure_drop", value=val, duration=duration, target="self").execute(user, user, context))
            
        # (9) 추가 행동
        if "extra_action" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="extra_action", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (10) 상태이상 면역
        if "status_immunity" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="status_immunity", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (11) 크리티컬 데미지
        if "critical_damage" in effect_data:
            val = effect_data["critical_damage"]
            buff_val = val - 1.0
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="critical_damage", value=buff_val, duration=duration, target="self").execute(user, user, context))
            
        # (12) 행운
        if "luck_modifier" in effect_data:
            val = effect_data["luck_modifier"]
            results.append(BuffEffect(BuffType.LUCK, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (13) 명중률
        if "accuracy_modifier" in effect_data:
            val = effect_data["accuracy_modifier"]
            if val < 0:
                results.append(BuffEffect(BuffType.ACCURACY_DOWN, value=abs(val), duration=duration, target="self").execute(user, user, context))
            else:
                results.append(BuffEffect(BuffType.ACCURACY_UP, value=val, duration=duration, target="self").execute(user, user, context))

        # (14) 자해 (Self Damage)
        if "self_damage" in effect_data:
            val = effect_data["self_damage"]
            results.append(StatusEffect(StatusType.BURN, value=val, duration=duration).execute(user, user, context))
            
        # (15) 속도
        if "speed_modifier" in effect_data:
            val = effect_data["speed_modifier"]
            if val > 0:
                results.append(BuffEffect(BuffType.SPEED_UP, value=val, duration=duration, target="self").execute(user, user, context))
            else:
                results.append(BuffEffect(BuffType.SPEED_DOWN, value=abs(val), duration=duration, target="self").execute(user, user, context))
                
        # (16) 기절
        if "stun" in effect_data:
            stun_dur = effect_data.get("stun_duration", 1)
            results.append(StatusEffect(StatusType.STUN, duration=stun_dur).execute(user, user, context))
            
        # (17) 다음 턴 3회 행동
        if "triple_action_next" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="triple_action_next", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (18) 방어력
        if "defense_modifier" in effect_data:
            val = effect_data["defense_modifier"]
            if val < 0:
                results.append(BuffEffect(BuffType.DEFENSE_DOWN, value=abs(val), duration=duration, target="self").execute(user, user, context))
            else:
                results.append(BuffEffect(BuffType.DEFENSE_UP, value=val, duration=duration, target="self").execute(user, user, context))
                
        # (19) 자동 공격
        if "auto_attack" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="auto_attack", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (20) 반격
        if "counter_attack" in effect_data:
            results.append(BuffEffect(BuffType.COUNTER, value=1, duration=duration, target="self").execute(user, user, context))
        
        # === 새로 추가된 효과들 ===
        
        # (21) ATB 게이지 증가
        if "atb_gain" in effect_data:
            user.atb_gauge = min(2000, user.atb_gauge + effect_data["atb_gain"])
        
        # (22) 파티 공격력 증가
        if "party_atk_up" in effect_data and combat_manager:
            val = effect_data["party_atk_up"]
            if hasattr(combat_manager, 'allies'):
                for ally in combat_manager.allies:
                    if hasattr(ally, 'status_manager'):
                        buff = CombatStatusEffect("선장의 위엄: 공격", StatusType.BUFF, duration=duration)
                        buff.stat_changes = {"physical_attack": val, "magic_attack": val}
                        ally.status_manager.add_status(buff)
        
        # (23) 파티 방어력 증가
        if "party_def_up" in effect_data and combat_manager:
            val = effect_data["party_def_up"]
            if hasattr(combat_manager, 'allies'):
                for ally in combat_manager.allies:
                    if hasattr(ally, 'status_manager'):
                        buff = CombatStatusEffect("선장의 위엄: 방어", StatusType.BUFF, duration=duration)
                        buff.stat_changes = {"physical_defense": val, "magic_defense": val}
                        ally.status_manager.add_status(buff)
        
        # (24) HP/MP 재생 (복합)
        if "hp_mp_regen" in effect_data:
            val = effect_data["hp_mp_regen"]
            results.append(BuffEffect(BuffType.HP_REGEN, value=val, duration=duration, target="self").execute(user, user, context))
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="mp_regen", value=val, duration=duration, target="self").execute(user, user, context))
        
        # (25) BRV 재생
        if "brv_regen" in effect_data:
            val = effect_data["brv_regen"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="brv_regen", value=val, duration=duration, target="self").execute(user, user, context))
        
        # (26) 자동 부활
        if "auto_revive" in effect_data:
            revive_hp = effect_data.get("revive_hp", 0.5)
            if hasattr(user, 'status_manager'):
                revive_buff = CombatStatusEffect("불사조 럼", StatusType.BUFF, duration=duration)
                revive_buff.metadata = {"auto_revive": True, "revive_hp": revive_hp}
                user.status_manager.add_status(revive_buff)
        
        # (27) 골드 보너스
        if "gold_bonus" in effect_data:
            val = effect_data["gold_bonus"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="gold_bonus", value=val, duration=duration, target="self").execute(user, user, context))
        
        # (28) MP 드레인
        if "mp_drain" in effect_data:
            val = effect_data["mp_drain"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="mp_drain", value=val, duration=duration, target="self").execute(user, user, context))
        
        # (29) BRV를 0으로
        if "brv_to_zero" in effect_data:
            user.current_brv = 0
        
        # (30) 다음 공격 3배
        if "next_attack_triple" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="next_attack_triple", value=3.0, duration=1, target="self").execute(user, user, context))
        
        # (31) 랜덤 스탯 +100%
        if "random_stat" in effect_data:
            stat_types = [BuffType.ATTACK_UP, BuffType.DEFENSE_UP, BuffType.MAGIC_UP, BuffType.SPEED_UP, BuffType.EVASION_UP, BuffType.CRITICAL_UP]
            chosen_stat = random.choice(stat_types)
            results.append(BuffEffect(chosen_stat, value=1.0, duration=duration, target="self").execute(user, user, context))
        
        # (32) 크리티컬 확정
        if "critical_guarantee" in effect_data:
            results.append(BuffEffect(BuffType.CRITICAL_UP, value=10.0, duration=duration, target="self").execute(user, user, context))
        
        # (33) 모든 피해 랜덤화
        if "all_damage_random" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="damage_random", value=1, duration=duration, target="self").execute(user, user, context))
        
        # (34) HP/MP 교환
        if "swap_hp_mp" in effect_data:
            temp_hp = user.current_hp
            user.current_hp = min(user.max_hp, user.current_mp)
            user.current_mp = min(user.max_mp, temp_hp)
        
        # (35) 피해 반사
        if "reflect_damage" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="reflect_damage", value=0.5, duration=duration, target="self").execute(user, user, context))
        
        # (36) 받는 피해 증가
        if "damage_taken_up" in effect_data:
            val = effect_data["damage_taken_up"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="damage_taken_up", value=val, duration=duration, target="self").execute(user, user, context))

        # 결과 메시지 조합
        effect_name = effect_data["name"]
        desc = effect_data["description"]
        
        final_msg = f"🍺 럼주 효과: {effect_name}!\n({desc})"
        
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            message=final_msg,
            gimmick_changes={"rum_effect": effect_id}
        )



def create_pirate_skills():
    """해적 11개 스킬 생성 (럼주 & 보물 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 커틀러스 베기 (기본 BRV)
    # ============================================================
    cutlass_slash = Skill(
        "pirate_cutlass_slash",
        "커틀러스 베기",
        "해적의 상징 커틀러스로 베어낸다. 보물 보유 시 추가 피해."
    )
    cutlass_slash.effects = [
        DamageEffect(DamageType.BRV, 1.6, gimmick_bonus={"field": "treasure_count", "multiplier": 0.15}),
    ]
    cutlass_slash.costs = []
    cutlass_slash.sfx = ("combat", "attack_physical")
    cutlass_slash.metadata = {"basic_attack": True, "treasure_scaling": True}
    skills.append(cutlass_slash)
    
    # ============================================================
    # 2. 권총 사격 (기본 HP + 보물 확률)
    # ============================================================
    pistol_shot = Skill(
        "pirate_pistol_shot",
        "권총 사격",
        "해적 권총으로 저격. 적 처치 시 60% 확률로 보물 획득."
    )
    pistol_shot.effects = [
        DamageEffect(DamageType.HP, 1.0),
    ]
    pistol_shot.costs = []
    pistol_shot.sfx = ("skill", "gun_shot")
    pistol_shot.metadata = {"basic_attack": True, "treasure_drop_chance": 0.6, "ranged": True}
    skills.append(pistol_shot)
    
    # ============================================================
    # 3. 럼주 마시기 (핵심 - 랜덤 효과)
    # ============================================================
    drink_rum = Skill(
        "pirate_drink_rum",
        "럼주 마시기",
        "럼주를 마시고 운명을 시험한다! 랜덤 효과 발동."
    )
    drink_rum.effects = [
        # 기본 HP 회복
        HealEffect(HealType.HP, percentage=0.15),
        # 럼주 효과 적용
        RumEffect(positive_chance=0.5)
    ]
    drink_rum.costs = [MPCost(4)]
    drink_rum.target_type = "self"
    drink_rum.sfx = ("character", "drink")
    drink_rum.metadata = {
        "rum_skill": True,
        "random_effect": True,
        "effects": list(RUM_EFFECTS.keys())
    }
    skills.append(drink_rum)
    
    # ============================================================
    # 4. 럼주 나눠주기 (파티 버프)
    # ============================================================
    share_rum = Skill(
        "pirate_share_rum",
        "럼주 나눠주기",
        "동료들에게 럼주를 돌린다. 파티 전원 랜덤 버프."
    )
    share_rum.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3, is_party_wide=True),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=3, is_party_wide=True),
    ]
    share_rum.costs = [MPCost(7)]
    share_rum.target_type = "all_allies"
    share_rum.sfx = ("character", "status_buff")
    share_rum.metadata = {"rum_skill": True, "party_buff": True}
    skills.append(share_rum)
    
    # ============================================================
    # 5. 럼주 뿌리기 (적 디버프 + 화염)
    # ============================================================
    rum_splash = Skill(
        "pirate_rum_splash",
        "럼주 뿌리기",
        "럼주를 뿌리고 불을 붙인다! 전체 화상 + 속도 감소."
    )
    rum_splash.effects = [
        DamageEffect(DamageType.BRV, 1.4),
        StatusEffect(StatusType.BURN, 3, 0.08),  # 3턴 화상
        BuffEffect(BuffType.SPEED_DOWN, 0.3, duration=2),
    ]
    rum_splash.costs = [MPCost(6)]
    rum_splash.target_type = "all_enemies"
    rum_splash.is_aoe = True
    rum_splash.sfx = ("skill", "fire_explosion")
    rum_splash.metadata = {"rum_skill": True, "aoe": True, "debuff": True}
    skills.append(rum_splash)
    
    # ============================================================
    # 6. 약탈 (보물 훔치기)
    # ============================================================
    plunder = Skill(
        "pirate_plunder",
        "약탈",
        "적을 공격하고 보물을 훔친다! 80% 확률로 보물 획득."
    )
    plunder.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8),
    ]
    plunder.costs = [MPCost(6)]
    plunder.sfx = ("item", "get_item")
    plunder.metadata = {"treasure_skill": True, "treasure_steal_chance": 0.8}
    skills.append(plunder)
    
    # ============================================================
    # 7. 보물 사용 (보유 보물 효과)
    # ============================================================
    use_treasure = Skill(
        "pirate_use_treasure",
        "보물 사용",
        "보유한 보물 중 하나를 사용한다. 강력한 일회용 효과!"
    )
    use_treasure.effects = [
        TreasureUseEffect()  # 보물 사용 효과 적용
    ]
    use_treasure.costs = [MPCost(4)]
    use_treasure.sfx = ("item", "use_item")
    use_treasure.metadata = {
        "treasure_skill": True,
        "consume_treasure": True,
        "treasure_effects": TREASURE_TYPES
    }
    skills.append(use_treasure)
    
    # ============================================================
    # 8. 보물 폭탄 (보물 소비 → 전체 피해)
    # ============================================================
    treasure_bomb = Skill(
        "pirate_treasure_bomb",
        "보물 폭탄",
        "보물을 모두 던져 폭발시킨다! 보물당 피해 증가."
    )
    treasure_bomb.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "treasure_count", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "treasure_count", "multiplier": 0.4}),
    ]
    treasure_bomb.costs = [MPCost(14)]
    treasure_bomb.target_type = "all_enemies"
    treasure_bomb.is_aoe = True
    treasure_bomb.sfx = ("skill", "explosion")
    treasure_bomb.metadata = {
        "treasure_skill": True,
        "consume_all_treasure": True,
        "aoe": True,
        "damage_per_treasure": 0.5
    }
    skills.append(treasure_bomb)
    
    # ============================================================
    # 9. 함포 일제사격 (전체 HP 공격)
    # ============================================================
    cannon_barrage = Skill(
        "pirate_cannon_barrage",
        "함포 일제사격",
        "해적선의 함포를 일제히 발사한다! 전체 대상 강력한 HP 공격."
    )
    cannon_barrage.effects = [
        DamageEffect(DamageType.BRV, 2.2),
        DamageEffect(DamageType.HP, 1.6),
    ]
    cannon_barrage.costs = [MPCost(16)]
    cannon_barrage.target_type = "all_enemies"
    cannon_barrage.is_aoe = True
    cannon_barrage.sfx = ("skill", "cannon")
    cannon_barrage.metadata = {"aoe": True, "ship_attack": True}
    skills.append(cannon_barrage)
    
    # ============================================================
    # 10. 해적기 게양 (파티 버프)
    # ============================================================
    raise_flag = Skill(
        "pirate_raise_flag",
        "해적기 게양",
        "해적 깃발을 올린다! 파티 공격력 UP + 약탈 확률 증가."
    )
    raise_flag.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.35, duration=4, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=4, is_party_wide=True),
    ]
    raise_flag.costs = [MPCost(12)]
    raise_flag.target_type = "all_allies"
    raise_flag.sfx = ("character", "status_buff")
    raise_flag.metadata = {
        "party_buff": True,
        "pirate_flag": True,
        "treasure_drop_bonus": 0.2
    }
    skills.append(raise_flag)
    
    # ============================================================
    # 11. 궁극기: 해적왕의 유산
    # ============================================================
    ultimate = Skill(
        "pirate_ultimate",
        "해적왕의 유산",
        "전설의 해적왕이 남긴 보물을 개방한다! 모든 보물 효과 + 럼주 대박 확정."
    )
    ultimate.effects = [
        # 강력한 전체 공격
        DamageEffect(DamageType.BRV, 3.0),
        DamageEffect(DamageType.BRV, 3.0),
        DamageEffect(DamageType.HP, 2.5),
        # 확정 대박 버프
        BuffEffect(BuffType.ATTACK_UP, 1.0, duration=4, target="self"),  # 공격력 2배
        BuffEffect(BuffType.CRITICAL_UP, 0.5, duration=4, target="self"),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=4, target="self"),
    ]
    ultimate.costs = [MPCost(35)]
    ultimate.is_ultimate = True
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aoe": True,
        "all_treasure_effect": True,
        "guaranteed_jackpot": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크 스킬: 약탈 함대
    # ============================================================
    teamwork = TeamworkSkill(
        "pirate_teamwork",
        "약탈 함대",
        "해적 함대가 총공격! 전체 적에게 피해 + 보물 3개 확정 획득.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 2.8),
        DamageEffect(DamageType.HP, 2.0),
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "guaranteed_treasure": 3,
        "aoe": True
    }
    skills.append(teamwork)
    
    return skills


# ============================================================
# 보물 사용 효과 (TreasureUseEffect)
# ============================================================
class TreasureUseEffect(SkillEffect):
    """보물 사용 효과 - pirate_use_treasure 스킬에서 사용"""
    
    def __init__(self):
        super().__init__(EffectType.GIMMICK)
    
    def execute(self, user: Any, target: Any, context: Optional[dict] = None) -> EffectResult:
        """보물 효과 실행"""
        import random
        from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
        
        # 보물 하나 소비
        if not hasattr(user, 'treasure_inventory') or not user.treasure_inventory:
            return EffectResult(success=False, message="보물이 없습니다!")
        
        # 첫 번째 보물 사용
        treasure_id = user.treasure_inventory.pop(0)
        treasure_data = TREASURE_TYPES.get(treasure_id)
        
        if not treasure_data:
            return EffectResult(success=False, message="알 수 없는 보물입니다!")
        
        treasure_name = treasure_data["name"]
        effect_type = treasure_data["effect"]
        messages = [f"📦 {treasure_name}을(를) 사용!"]
        
        # 컨텍스트에서 combat_manager 가져오기
        combat_manager = context.get('combat_manager') if context else None
        
        # ===== 효과 적용 =====
        
        # Tier C: 기본 보물
        if effect_type == "brv_boost":
            brv_gain = int(user.current_brv * treasure_data["value"])
            user.current_brv += brv_gain
            messages.append(f"💎 BRV +{brv_gain}!")
        
        elif effect_type == "bonus_attack":
            if target and hasattr(target, 'current_hp'):
                damage = int(user.current_brv * treasure_data["value"])
                target.current_hp = max(0, target.current_hp - damage)
                messages.append(f"🔫 {target.name}에게 {damage} HP 피해!")
        
        elif effect_type == "enemy_debuff":
            if combat_manager and hasattr(combat_manager, 'enemies'):
                duration = treasure_data.get("duration", 3)
                for enemy in combat_manager.enemies:
                    if hasattr(enemy, 'status_manager'):
                        atk_debuff = CombatStatusEffect("저주: 공격력", StatusType.DEBUFF, duration=duration)
                        atk_debuff.stat_changes = {"physical_attack": -treasure_data["value"], "magic_attack": -treasure_data["value"]}
                        enemy.status_manager.add_status(atk_debuff)
                        def_debuff = CombatStatusEffect("저주: 방어력", StatusType.DEBUFF, duration=duration)
                        def_debuff.stat_changes = {"physical_defense": -treasure_data["value"], "magic_defense": -treasure_data["value"]}
                        enemy.status_manager.add_status(def_debuff)
                messages.append(f"💀 적 전체 공/방 -{int(treasure_data['value']*100)}% ({duration}턴)!")
        
        elif effect_type == "gamble":
            multiplier = treasure_data["value"] if random.random() < 0.5 else (1.0 / treasure_data["value"])
            user.lucky_dice_active = True
            user.lucky_dice_multiplier = multiplier
            result_text = "대박!" if multiplier > 1 else "꽝..."
            messages.append(f"🎲 {result_text} 다음 스킬 피해 {multiplier:.1f}배!")
        
        elif effect_type == "ultimate_charge":
            if combat_manager and hasattr(combat_manager, 'teamwork_gauge'):
                combat_manager.teamwork_gauge = min(
                    combat_manager.max_teamwork_gauge,
                    combat_manager.teamwork_gauge + treasure_data["value"]
                )
                messages.append(f"⚡ 팀워크 게이지 +{treasure_data['value']}!")
        
        # Tier B: 중급 보물
        elif effect_type == "team_buff_atk":
            if combat_manager and hasattr(combat_manager, 'allies'):
                duration = treasure_data.get("duration", 3)
                for ally in combat_manager.allies:
                    if hasattr(ally, 'status_manager'):
                        buff = CombatStatusEffect("해적 깃발", StatusType.BUFF, duration=duration)
                        buff.stat_changes = {"physical_attack": treasure_data["value"], "magic_attack": treasure_data["value"]}
                        ally.status_manager.add_status(buff)
                messages.append(f"🏴 아군 전체 공격력 +{int(treasure_data['value']*100)}% ({duration}턴)!")
        
        elif effect_type == "gauge_boost":
            if combat_manager and hasattr(combat_manager, 'teamwork_gauge'):
                combat_manager.teamwork_gauge = min(
                    combat_manager.max_teamwork_gauge,
                    combat_manager.teamwork_gauge + treasure_data["teamwork"]
                )
            user.atb_gauge = min(2000, user.atb_gauge + treasure_data["atb"])
            messages.append(f"🧭 팀워크 +{treasure_data['teamwork']}, ATB +{treasure_data['atb']}!")
        
        elif effect_type == "positive_rum":
            positive_effects = [k for k, v in RUM_EFFECTS.items() if v.get("positive", False)]
            if positive_effects:
                selected = random.choice(positive_effects)
                effect_data = RUM_EFFECTS[selected]
                user.current_rum_effect = selected
                user.rum_effect_duration = effect_data["duration"] + treasure_data.get("duration_bonus", 0)
                messages.append(f"🍺 {effect_data['name']} 발동!")
        
        elif effect_type == "free_skill":
            user.free_skill_active = True
            messages.append("🦜 다음 스킬 MP 소모 0!")
        
        elif effect_type == "treasure_boost":
            user.treasure_map_uses = treasure_data.get("uses", 3)
            messages.append(f"🗺️ 다음 {user.treasure_map_uses}전투 보물 확정!")
        
        elif effect_type == "heal_and_evade":
            if combat_manager and hasattr(combat_manager, 'allies'):
                heal_percent = treasure_data["heal_percent"]
                duration = treasure_data.get("duration", 2)
                for ally in combat_manager.allies:
                    hp_heal = int(ally.max_hp * heal_percent)
                    mp_heal = int(ally.max_mp * heal_percent)
                    ally.current_hp = min(ally.max_hp, ally.current_hp + hp_heal)
                    ally.current_mp = min(ally.max_mp, ally.current_mp + mp_heal)
                    if hasattr(ally, 'status_manager'):
                        buff = CombatStatusEffect("인어의 축복", StatusType.BUFF, duration=duration)
                        buff.stat_changes = {"evasion": treasure_data["evasion_bonus"]}
                        ally.status_manager.add_status(buff)
                messages.append(f"🧜 전체 HP/MP 30% 회복 + 회피 +20% ({duration}턴)!")
        
        # Tier A: 고급 보물
        elif effect_type == "deadly_poison":
            if combat_manager and hasattr(combat_manager, 'enemies'):
                duration = treasure_data["duration"]
                for enemy in combat_manager.enemies:
                    if hasattr(enemy, 'status_manager'):
                        poison = CombatStatusEffect("치명적인 독", StatusType.POISON, duration=duration)
                        poison.metadata = {"damage_percent": treasure_data["damage_percent"]}
                        enemy.status_manager.add_status(poison)
                        def_debuff = CombatStatusEffect("독: 방어력 감소", StatusType.DEBUFF, duration=duration)
                        def_debuff.stat_changes = {"physical_defense": -treasure_data["def_down"], "magic_defense": -treasure_data["def_down"]}
                        enemy.status_manager.add_status(def_debuff)
                messages.append(f"☠️ 적 전체 맹독 ({duration}턴, 매턴 10% + 방어 -40%)!")
        
        elif effect_type == "heavy_damage":
            if target and hasattr(target, 'current_hp'):
                damage = int(user.current_brv * treasure_data["value"])
                target.current_hp = max(0, target.current_hp - damage)
                user.current_brv = 0  # BRV 소모
                messages.append(f"💣 {target.name}에게 {damage} HP 피해!")
        
        elif effect_type == "instant_death":
            if target and hasattr(target, 'current_hp'):
                if random.random() < treasure_data["death_chance"]:
                    target.current_hp = 0
                    messages.append(f"💀 {target.name} 즉사!")
                else:
                    damage = int(target.max_hp * treasure_data["damage_fallback"])
                    target.current_hp = max(0, target.current_hp - damage)
                    messages.append(f"🐍 {target.name}에게 {damage} HP 고정 피해!")
        
        elif effect_type == "aoe_debuff":
            if combat_manager and hasattr(combat_manager, 'enemies'):
                duration = treasure_data["duration"]
                for enemy in combat_manager.enemies:
                    enemy.current_brv = int(enemy.current_brv * (1 - treasure_data["brv_down"]))
                    if hasattr(enemy, 'status_manager'):
                        speed_debuff = CombatStatusEffect("폭풍", StatusType.DEBUFF, duration=duration)
                        speed_debuff.stat_changes = {"speed": -treasure_data["speed_down"]}
                        enemy.status_manager.add_status(speed_debuff)
                messages.append(f"🌪️ 적 전체 BRV -50% + 속도 -30% ({duration}턴)!")
        
        # Tier S: 희귀 보물
        elif effect_type == "brv_steal":
            if combat_manager and hasattr(combat_manager, 'enemies'):
                for enemy in combat_manager.enemies:
                    enemy.current_brv = 0
                user.current_brv = int(user.current_brv * (1 + treasure_data["self_brv_boost"]))
                messages.append("👁️ 적 전체 BRV 0! 자신 BRV +80%!")
        
        elif effect_type == "ultimate_strike":
            if target and hasattr(target, 'current_hp'):
                damage = int(user.current_brv * treasure_data["value"])
                target.current_hp = max(0, target.current_hp - damage)
                user.current_brv = 0
                if hasattr(target, 'status_manager'):
                    stun = CombatStatusEffect("기절", StatusType.STUN, duration=treasure_data["stun_duration"])
                    target.status_manager.add_status(stun)
                messages.append(f"🔱 {target.name}에게 {damage} HP 피해 + 기절 {treasure_data['stun_duration']}턴!")
        
        elif effect_type == "resurrection":
            if combat_manager and hasattr(combat_manager, 'allies'):
                heal_percent = treasure_data["heal_percent"]
                duration = treasure_data["revive_duration"]
                for ally in combat_manager.allies:
                    hp_heal = int(ally.max_hp * heal_percent)
                    ally.current_hp = min(ally.max_hp, ally.current_hp + hp_heal)
                    if hasattr(ally, 'status_manager'):
                        revive_buff = CombatStatusEffect("불사조의 가호", StatusType.BUFF, duration=duration)
                        revive_buff.metadata = {"revive_on_death": True}
                        ally.status_manager.add_status(revive_buff)
                messages.append(f"🔥 전체 HP 50% 회복 + 부활 버프 ({duration}턴)!")
        
        else:
            messages.append(f"✨ {treasure_data['description']}")
        
        return EffectResult(success=True, message=" ".join(messages))


def register_pirate_skills(skill_manager):
    """해적 스킬 등록"""
    skills = create_pirate_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"해적 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
