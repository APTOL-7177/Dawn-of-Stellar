"""Berserker Skills - 광전사 스킬 (HP 소비 + 분노 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.effects.lifesteal_effect import LifestealEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.hp_cost import HPCost
from src.character.skills.costs.stack_cost import StackCost

def create_berserker_skills():
    """광전사 9개 스킬 생성"""
    
    # 1. 기본 BRV: 광란의 일격
    frenzy_strike = Skill("berserker_frenzy_strike", "광란의 일격", "HP 소비하여 강력한 BRV 공격, 분노 축적")
    frenzy_strike.effects = [
        DamageEffect(DamageType.BRV, 1.8),  # 강력한 배율
        GimmickEffect(GimmickOperation.ADD, "rage_stacks", 1, max_value=10)
    ]
    frenzy_strike.costs = []  # 기본 공격은 MP 소모 없음
    
    # 2. 기본 HP: 피의 섬광
    blood_flash = Skill("berserker_blood_flash", "피의 섬광", "HP 소비 HP 공격, 흡혈 회복")
    blood_flash.effects = [
        DamageEffect(DamageType.HP, 1.2),
        LifestealEffect(lifesteal_percent=0.5, low_hp_bonus=True)  # 50% 흡혈
    ]
    blood_flash.costs = []  # 기본 공격은 MP 소모 없음
    
    # 3. 피의 갑옷
    blood_armor = Skill("berserker_blood_armor", "피의 갑옷", "HP 소비하여 강력한 보호막 생성 (150%)")
    blood_armor.effects = [
        ShieldEffect(base_amount=0, hp_consumed_multiplier=1.5),  # 소비 HP의 150%
        GimmickEffect(GimmickOperation.ADD, "rage_stacks", 2, max_value=10)
    ]
    blood_armor.costs = [MPCost(5), HPCost(percentage=0.2)]  # HP 20% 소비
    blood_armor.target_type = "self"
    blood_armor.cooldown = 3
    
    # 4. 흡혈 강타
    vampiric_strike = Skill("berserker_vampiric_strike", "흡혈 강타", "보호막 소비 강력한 HP 공격과 대량 흡혈")
    vampiric_strike.effects = [
        DamageEffect(DamageType.HP, 1.5, gimmick_bonus={"field": "shield_amount", "multiplier": 0.001}),
        LifestealEffect(lifesteal_percent=0.8, low_hp_bonus=True),  # 80% 흡혈
        GimmickEffect(GimmickOperation.SET, "shield_amount", 0)  # 보호막 전부 소비
    ]
    vampiric_strike.costs = [MPCost(6)]
    vampiric_strike.cooldown = 2
    
    # 5. 광폭화
    rampage = Skill("berserker_rampage", "광폭화", "HP 소비하여 분노 대량 축적")
    rampage.effects = [
        DamageEffect(DamageType.BRV, 1.0),
        GimmickEffect(GimmickOperation.ADD, "rage_stacks", 5, max_value=10)
    ]
    rampage.costs = [MPCost(5), HPCost(amount=30)]
    rampage.cooldown = 4
    
    # 6. 전쟁의 함성
    war_cry = Skill("berserker_war_cry", "전쟁의 함성", "HP 낮을수록 강력한 광역 공격, 분노 소비")
    war_cry.effects = [
        DamageEffect(DamageType.BRV, 2.0, hp_scaling=True),  # HP 낮을수록 강력
        GimmickEffect(GimmickOperation.CONSUME, "rage_stacks", 3)
    ]
    war_cry.costs = [MPCost(8), StackCost("rage_stacks", 3)]
    war_cry.target_type = "all_enemies"
    war_cry.cooldown = 3
    
    # 7. 생명력 흡수
    life_drain = Skill("berserker_life_drain", "생명력 흡수", "HP 회복 및 분노 축적")
    life_drain.effects = [
        HealEffect(HealType.HP, percentage=0.2),  # 최대 HP의 20% 회복
        GimmickEffect(GimmickOperation.ADD, "rage_stacks", 2, max_value=10)
    ]
    life_drain.costs = [MPCost(6)]
    life_drain.target_type = "self"
    life_drain.cooldown = 5
    
    # 8. 피의 폭발
    blood_explosion = Skill("berserker_blood_explosion", "피의 폭발", "보호막 폭발시켜 광역 데미지")
    blood_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "shield_amount", "multiplier": 0.002}),
        GimmickEffect(GimmickOperation.SET, "shield_amount", 0)
    ]
    blood_explosion.costs = [MPCost(9)]
    blood_explosion.target_type = "all_enemies"
    blood_explosion.cooldown = 4
    
    # 9. 궁극기: 피의 광란
    blood_frenzy = Skill("berserker_ultimate", "피의 광란", "HP를 1로 만들고 압도적 공격")
    blood_frenzy.effects = [
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "rage_stacks", "multiplier": 0.3}),
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "rage_stacks", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 3.0),
        LifestealEffect(lifesteal_percent=1.0, low_hp_bonus=False),  # 100% 흡혈
        GimmickEffect(GimmickOperation.SET, "rage_stacks", 0)
    ]
    blood_frenzy.costs = [MPCost(25), HPCost(percentage=0.99)]  # HP 99% 소비
    blood_frenzy.is_ultimate = True
    blood_frenzy.cooldown = 10
    
    return [frenzy_strike, blood_flash, blood_armor, vampiric_strike, rampage,
            war_cry, life_drain, blood_explosion, blood_frenzy]

def register_berserker_skills(skill_manager):
    """광전사 스킬 등록"""
    skills = create_berserker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
