"""Pirate Skills - 해적 스킬 (약탈/골드 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_pirate_skills():
    """해적 10개 스킬 생성 (약탈/골드 시스템)"""

    skills = []

    # 1. 기본 BRV: 약탈
    plunder = Skill("pirate_plunder", "약탈", "골드 획득")
    plunder.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "gold", 1, max_value=10)
    ]
    plunder.costs = []  # 기본 공격은 MP 소모 없음
    plunder.sfx = "020"  # 짧은 획득
    plunder.metadata = {"gold_gain": 1}
    skills.append(plunder)

    # 2. 기본 HP: 금화 발사
    coin_shot = Skill("pirate_coin_shot", "금화 발사", "골드 소비 공격")
    coin_shot.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "gold", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "gold", 1)
    ]
    coin_shot.costs = []  # 기본 공격은 MP 소모 없음
    coin_shot.sfx = "014"  # 짧은 총 공격
    coin_shot.metadata = {"gold_cost": 1, "gold_scaling": True}
    skills.append(coin_shot)

    # 3. 보물 사냥
    treasure_hunt = Skill("pirate_treasure_hunt", "보물 사냥", "골드 2개 획득")
    treasure_hunt.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        GimmickEffect(GimmickOperation.ADD, "gold", 2, max_value=10)
    ]
    treasure_hunt.costs = []
    # treasure_hunt.cooldown = 2  # 쿨다운 시스템 제거됨
    treasure_hunt.sfx = "357"  # 짧은 획득
    treasure_hunt.metadata = {"gold_gain": 2}
    skills.append(treasure_hunt)

    # 4. 럼주 마시기
    drink_rum = Skill("pirate_drink_rum", "럼주 마시기", "골드 2개 소비, 버프")
    drink_rum.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "gold", 2)
    ]
    drink_rum.costs = [MPCost(4), StackCost("gold", 2)]
    drink_rum.target_type = "self"
    # drink_rum.cooldown = 3  # 쿨다운 시스템 제거됨
    drink_rum.sfx = "093"  # 짧은 버프
    drink_rum.metadata = {"gold_cost": 2, "buff": True}
    skills.append(drink_rum)

    # 5. 대포 발사
    cannon_fire = Skill("pirate_cannon_fire", "대포 발사", "골드 3개 소비, 광역 공격")
    cannon_fire.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "gold", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.CONSUME, "gold", 3)
    ]
    cannon_fire.costs = [MPCost(6), StackCost("gold", 3)]
    # cannon_fire.cooldown = 3  # 쿨다운 시스템 제거됨
    cannon_fire.is_aoe = True
    cannon_fire.sfx = "019"  # 짧은 폭발
    cannon_fire.metadata = {"gold_cost": 3, "gold_scaling": True, "aoe": True}
    skills.append(cannon_fire)

    # 6. 보물 저장
    store_treasure = Skill("pirate_store_treasure", "보물 저장", "골드 최대 회복")
    store_treasure.effects = [
        GimmickEffect(GimmickOperation.SET, "gold", 10),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3)
    ]
    store_treasure.costs = [MPCost(5)]
    store_treasure.target_type = "self"
    # store_treasure.cooldown = 5  # 쿨다운 시스템 제거됨
    store_treasure.sfx = "093"  # 짧은 버프
    store_treasure.metadata = {"gold_refill": True, "buff": True}
    skills.append(store_treasure)

    # 7. 금화 폭탄
    gold_bomb = Skill("pirate_gold_bomb", "금화 폭탄", "골드 5개 소비, 광역 폭발")
    gold_bomb.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "gold", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 1.5),
        GimmickEffect(GimmickOperation.CONSUME, "gold", 5)
    ]
    gold_bomb.costs = [MPCost(7), StackCost("gold", 5)]
    # gold_bomb.cooldown = 4  # 쿨다운 시스템 제거됨
    gold_bomb.is_aoe = True
    gold_bomb.sfx = "146"  # 짧은 폭발
    gold_bomb.metadata = {"gold_cost": 5, "gold_scaling": True, "aoe": True}
    skills.append(gold_bomb)

    # 8. 해적선 공격
    pirate_ship_attack = Skill("pirate_pirate_ship_attack", "해적선 공격", "골드 7개 소비, 해적선 소환")
    pirate_ship_attack.effects = [
        DamageEffect(DamageType.BRV, 2.8, gimmick_bonus={"field": "gold", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 2.0),
        GimmickEffect(GimmickOperation.CONSUME, "gold", 7)
    ]
    pirate_ship_attack.costs = [MPCost(9), StackCost("gold", 7)]
    # pirate_ship_attack.cooldown = 6  # 쿨다운 시스템 제거됨
    pirate_ship_attack.is_aoe = True
    pirate_ship_attack.sfx = "146"  # 짧은 광역 공격
    pirate_ship_attack.metadata = {"gold_cost": 7, "gold_scaling": True, "aoe": True}
    skills.append(pirate_ship_attack)

    # 9. 검은 수염의 저주 (NEW - 10번째 스킬 전)
    blackbeard_curse = Skill("pirate_blackbeard_curse", "검은 수염의 저주", "골드 8개 소비, 강력한 디버프")
    blackbeard_curse.effects = [
        DamageEffect(DamageType.BRV_HP, 2.6, gimmick_bonus={"field": "gold", "multiplier": 0.45}),
        BuffEffect(BuffType.ATTACK_DOWN, 0.5, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.5, duration=5),
        BuffEffect(BuffType.SPEED_DOWN, 0.3, duration=5),
        GimmickEffect(GimmickOperation.CONSUME, "gold", 8)
    ]
    blackbeard_curse.costs = [MPCost(11), StackCost("gold", 8)]
    # blackbeard_curse.cooldown = 7  # 쿨다운 시스템 제거됨
    blackbeard_curse.is_aoe = True
    blackbeard_curse.sfx = "148"  # 짧은 디버프
    blackbeard_curse.metadata = {"gold_cost": 8, "gold_scaling": True, "debuff": True, "aoe": True}
    skills.append(blackbeard_curse)

    # 10. 궁극기: 보물섬의 전설
    ultimate = Skill("pirate_ultimate", "보물섬의 전설", "모든 골드로 전설의 보물 개방")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "gold", "multiplier": 0.35}),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "gold", "multiplier": 0.35}),
        DamageEffect(DamageType.HP, 3.0, gimmick_bonus={"field": "gold", "multiplier": 0.5}),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "gold", 10)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = "035"  # 짧은 리미트 브레이크
    ultimate.metadata = {"ultimate": True, "gold_scaling": True, "gold_refill": True, "aoe": True}
    skills.append(ultimate)

    return skills

def register_pirate_skills(skill_manager):
    """해적 스킬 등록"""
    skills = create_pirate_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
