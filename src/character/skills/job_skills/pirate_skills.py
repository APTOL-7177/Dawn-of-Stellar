"""Pirate Skills - 해적 (럼주 & 보물 시스템)

럼주를 마시면 랜덤 효과 발동 (도박!)
적 처치 시 보물 획득, 강력한 일회용 효과

"인생은 도박이야, 럼주나 마셔"
"""
import random
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
# 보물 종류 정의
# ============================================================
TREASURE_TYPES = {
    "gold_pouch": {
        "name": "금화 주머니",
        "effect": "brv_boost",
        "value": 0.5,  # BRV +50%
        "description": "즉시 BRV +50%",
        "weight": 30
    },
    "pirate_pistol": {
        "name": "해적 권총",
        "effect": "bonus_attack",
        "value": 1.5,  # 추가 공격 1.5배
        "description": "추가 원거리 공격",
        "weight": 25
    },
    "cursed_coin": {
        "name": "저주받은 동전",
        "effect": "enemy_debuff",
        "value": 0.3,  # 30% 감소
        "description": "적 전체 공/방 -30%",
        "weight": 20
    },
    "lucky_dice": {
        "name": "행운의 주사위",
        "effect": "gamble",
        "value": 2.0,  # 2배 or 0.5배
        "description": "다음 스킬 2배 or 0.5배",
        "weight": 15
    },
    "black_pearl": {
        "name": "검은 진주",
        "effect": "ultimate_charge",
        "value": 50,  # 게이지 +50
        "description": "팀워크 게이지 +50",
        "weight": 10
    }
}

# ============================================================
# 럼주 효과 정의
# ============================================================
RUM_EFFECTS = {
    # === 긍정 효과 (8개) ===
    "jackpot": {
        "name": "★ 대박 ★",
        "positive": True,
        "attack_multiplier": 3.0,
        "critical_chance": 1.0,
        "duration": 2,
        "description": "공격력 3배 + 100% 크리티컬 (2턴)"
    },
    "invincible_drunk": {
        "name": "★ 무적 취권 ★",
        "positive": True,
        "evasion_modifier": 1.0,
        "counter_attack": True,
        "duration": 2,
        "description": "회피 +100%, 회피 시 반격 (2턴)"
    },
    "liquid_courage": {
        "name": "★ 액체 용기 ★",
        "positive": True,
        "damage_reduction": 0.5,
        "hp_regen": 0.1,
        "duration": 3,
        "description": "피해 50% 감소 + 매턴 HP 10% 회복 (3턴)"
    },
    "sea_kings_blessing": {
        "name": "★ 바다왕의 축복 ★",
        "positive": True,
        "all_stats_up": 0.3,  # 모든 스탯 +30%
        "duration": 3,
        "description": "모든 스탯 +30% (3턴)"
    },
    "golden_rush": {
        "name": "★ 황금 러시 ★",
        "positive": True,
        "brv_multiplier": 2.0,  # BRV 획득 2배
        "treasure_chance": 1.0,  # 보물 획득률 100%
        "duration": 2,
        "description": "BRV 획득 2배, 보물 확정 드랍 (2턴)"
    },
    "double_shot": {
        "name": "★ 더블 샷 ★",
        "positive": True,
        "extra_action": True,  # 추가 행동
        "duration": 1,
        "description": "즉시 추가 행동 1회!"
    },
    "iron_liver": {
        "name": "★ 강철 간 ★",
        "positive": True,
        "status_immunity": True,  # 상태이상 면역
        "hp_regen": 0.2,
        "duration": 4,
        "description": "상태이상 면역 + 매턴 HP 20% 회복 (4턴)"
    },
    "pirates_luck": {
        "name": "★ 해적의 행운 ★",
        "positive": True,
        "critical_damage": 2.0,  # 크리티컬 데미지 2배
        "luck_modifier": 0.5,  # 행운 +50%
        "duration": 3,
        "description": "크리티컬 데미지 2배, 행운 +50% (3턴)"
    },
    # === 부정 효과 (4개) ===
    "tipsy": {
        "name": "✗ 비틀거림 ✗",
        "positive": False,
        "accuracy_modifier": -0.6,  # 명중 -60%
        "evasion_modifier": 0.8,
        "duration": 3,
        "description": "명중 -60%, 회피 +80% (3턴)"
    },
    "fire_blood": {
        "name": "✗ 피가 끓는다 ✗",
        "positive": False,
        "self_damage": 0.15,  # 매턴 15% 자해
        "attack_multiplier": 2.5,  # 공격력 +150%
        "speed_modifier": 0.5,  # 속도 +50%
        "duration": 3,
        "description": "매턴 자해 15%, 공격력 +150%, 속도 +50% (3턴)"
    },
    "blackout": {
        "name": "✗ 블랙아웃 ✗",
        "positive": False,
        "stun": True,
        "stun_duration": 2,  # 2턴 기절
        "triple_action_next": True,  # 이후 3회 행동
        "duration": 2,
        "description": "2턴 기절, 이후 3회 연속 행동!"
    },
    "berserker_rage": {
        "name": "✗ 광란의 도취 ✗",
        "positive": False,
        "attack_multiplier": 2.0,
        "defense_modifier": -0.5,  # 방어 -50%
        "auto_attack": True,  # 자동 공격 (제어 불가)
        "duration": 3,
        "description": "공격력 2배, 방어 -50%, 제어 불가 (3턴)"
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
        # 1. 랜덤 효과 선택
        effect_id, effect_data = get_random_rum_effect(self.positive_chance)
        
        # 2. 효과 적용
        duration = effect_data.get("duration", 2)
        results = []
        
        # 효과 매핑 및 실행
        # (1) 공격력 (Attack Multiplier)
        if "attack_multiplier" in effect_data:
            val = effect_data["attack_multiplier"]
            # 2.0 -> +100% (1.0)
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
            
        # (4) 피해 감소 -> 방어력 증가로 근사
        if "damage_reduction" in effect_data:
            val = effect_data["damage_reduction"]
            results.append(BuffEffect(BuffType.DEFENSE_UP, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (5) HP 재생
        if "hp_regen" in effect_data:
            val = effect_data["hp_regen"]
            results.append(BuffEffect(BuffType.HP_REGEN, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (6) 모든 스탯 증가
        if "all_stats_up" in effect_data:
            val = effect_data["all_stats_up"]
            for b_type in [BuffType.ATTACK_UP, BuffType.DEFENSE_UP, BuffType.MAGIC_UP, BuffType.SPIRIT_UP, BuffType.SPEED_UP, BuffType.LUCK]:
                results.append(BuffEffect(b_type, value=val, duration=duration, target="self").execute(user, user, context))
                
        # (7) BRV 획득 배율 (커스텀)
        if "brv_multiplier" in effect_data:
            val = effect_data["brv_multiplier"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="brv_gain", value=val, duration=duration, target="self").execute(user, user, context))
            
        # (8) 보물 획득 확률 (커스텀)
        if "treasure_chance" in effect_data:
            val = effect_data["treasure_chance"]
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="treasure_drop", value=val, duration=duration, target="self").execute(user, user, context))
            
        # (9) 추가 행동 (커스텀)
        if "extra_action" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="extra_action", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (10) 상태이상 면역 (커스텀)
        if "status_immunity" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="status_immunity", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (11) 크리티컬 데미지 (커스텀)
        if "critical_damage" in effect_data:
            val = effect_data["critical_damage"]
            # 2.0 -> +100%
            buff_val = val - 1.0
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="critical_damage", value=buff_val, duration=duration, target="self").execute(user, user, context))
            
        # (12) 행운
        if "luck_modifier" in effect_data:
            val = effect_data["luck_modifier"]
            results.append(BuffEffect(BuffType.LUCK, value=val, duration=duration, target="self").execute(user, user, context))
            
        # (13) 명중률 (음수면 감소)
        if "accuracy_modifier" in effect_data:
            val = effect_data["accuracy_modifier"]
            if val < 0:
                results.append(BuffEffect(BuffType.ACCURACY_DOWN, value=abs(val), duration=duration, target="self").execute(user, user, context))
            else:
                results.append(BuffEffect(BuffType.ACCURACY_UP, value=val, duration=duration, target="self").execute(user, user, context))

        # (14) 자해 (Self Damage) -> 화상(Burn)으로 처리
        if "self_damage" in effect_data:
            val = effect_data["self_damage"]
            # 화상은 턴당 데미지
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
            
        # (17) 다음 턴 3회 행동 (커스텀)
        if "triple_action_next" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="triple_action_next", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (18) 방어력 (음수면 감소)
        if "defense_modifier" in effect_data:
            val = effect_data["defense_modifier"]
            if val < 0:
                results.append(BuffEffect(BuffType.DEFENSE_DOWN, value=abs(val), duration=duration, target="self").execute(user, user, context))
            else:
                results.append(BuffEffect(BuffType.DEFENSE_UP, value=val, duration=duration, target="self").execute(user, user, context))
                
        # (19) 자동 공격 (커스텀)
        if "auto_attack" in effect_data:
            results.append(BuffEffect(BuffType.CUSTOM, custom_stat="auto_attack", value=1, duration=duration, target="self").execute(user, user, context))
            
        # (20) 반격 (Counter)
        if "counter_attack" in effect_data:
            results.append(BuffEffect(BuffType.COUNTER, value=1, duration=duration, target="self").execute(user, user, context))

        # 결과 메시지 조합
        effect_name = effect_data["name"]
        desc = effect_data["description"]
        
        final_msg = f"럼주 효과 발동: {effect_name}!\n({desc})"
        
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
        # 보물 효과는 execute_skill에서 적용
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


def register_pirate_skills(skill_manager):
    """해적 스킬 등록"""
    skills = create_pirate_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"해적 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
