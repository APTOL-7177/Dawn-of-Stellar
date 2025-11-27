"""Pirate Skills - 해적 (럼주 & 보물 시스템)

럼주를 마시면 랜덤 효과 발동 (도박!)
적 처치 시 보물 획득, 강력한 일회용 효과

"인생은 도박이야, 럼주나 마셔"
"""
import random
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
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
    "jackpot": {
        "name": "대박",
        "positive": True,
        "attack_multiplier": 2.0,
        "duration": 3,
        "description": "공격력 2배 (3턴)"
    },
    "tipsy": {
        "name": "취기",
        "positive": False,  # 반반
        "accuracy_modifier": -0.3,
        "evasion_modifier": 0.5,
        "duration": 2,
        "description": "명중 -30%, 회피 +50% (2턴)"
    },
    "fire_blood": {
        "name": "불꽃 피",
        "positive": False,  # 반반
        "self_damage": 0.1,  # 매턴 10% 자해
        "attack_multiplier": 1.8,
        "duration": 3,
        "description": "매턴 자해 10%, 공격력 +80% (3턴)"
    },
    "blackout": {
        "name": "블랙아웃",
        "positive": False,
        "stun": True,
        "double_action_next": True,
        "duration": 1,
        "description": "1턴 기절, 다음 턴 2회 행동"
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
        # 럼주 효과는 execute_skill에서 랜덤 적용
    ]
    drink_rum.costs = [MPCost(8)]
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
    share_rum.costs = [MPCost(12)]
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
    rum_splash.costs = [MPCost(10)]
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
        BuffEffect(BuffType.ATTACK_UP, 1.0, duration=4),  # 공격력 2배
        BuffEffect(BuffType.CRITICAL_UP, 0.5, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=4),
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
