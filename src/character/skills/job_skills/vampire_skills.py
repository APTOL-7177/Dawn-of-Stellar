"""Vampire Skills - 흡혈귀 스킬 (흡혈/버티기 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.lifesteal_effect import LifestealEffect
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_vampire_skills():
    """흡혈귀 9개 스킬"""
    
    skills = []
    
    # 1. 기본 BRV: 흡혈
    blood_drain = Skill("vampire_drain", "흡혈", "피를 빨아 회복")
    blood_drain.effects = [
        DamageEffect(DamageType.BRV, 1.3),
        LifestealEffect(lifesteal_percent=0.3),
        GimmickEffect(GimmickOperation.ADD, "blood_pool", 1, max_value=10)
    ]
    blood_drain.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(blood_drain)
    
    # 2. 기본 HP: 피의 창
    blood_lance = Skill("vampire_lance", "피의 창", "피를 소비한 공격")
    blood_lance.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "blood_pool", "multiplier": 0.2}),
        LifestealEffect(lifesteal_percent=0.5)
    ]
    blood_lance.costs = [StackCost("blood_pool", 1)]  # blood_pool 1 필요
    skills.append(blood_lance)
    
    # 3. 피의 갑옷
    blood_armor = Skill("vampire_armor", "피의 갑옷", "피로 보호막")
    blood_armor.effects = [
        ShieldEffect(base_amount=0, multiplier=1.5, stat_name="blood_pool")
    ]
    blood_armor.costs = [MPCost(8), StackCost("blood_pool", 3)]
    blood_armor.target_type = "self"
    blood_armor.cooldown = 4
    skills.append(blood_armor)
    
    # 4. 재생
    regeneration = Skill("vampire_regen", "재생", "흡혈귀의 재생력")
    regeneration.effects = [
        HealEffect(HealType.HP, percentage=0.25),
        GimmickEffect(GimmickOperation.ADD, "blood_pool", 2, max_value=10)
    ]
    regeneration.costs = [MPCost(6)]
    regeneration.target_type = "self"
    regeneration.cooldown = 3
    skills.append(regeneration)
    
    # 5. 피의 폭발
    blood_explosion = Skill("vampire_explosion", "피의 폭발", "피 폭발 광역")
    blood_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "blood_pool", "multiplier": 0.3}),
        LifestealEffect(lifesteal_percent=0.4)
    ]
    blood_explosion.costs = [MPCost(9), StackCost("blood_pool", 2)]
    blood_explosion.cooldown = 3
    skills.append(blood_explosion)
    
    # 6. 흡혈 강화
    blood_frenzy = Skill("vampire_frenzy", "흡혈 강화", "흡혈 극대화")
    blood_frenzy.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        GimmickEffect(GimmickOperation.SET, "lifesteal_boost", 2)
    ]
    blood_frenzy.costs = [MPCost(8)]
    blood_frenzy.target_type = "self"
    blood_frenzy.cooldown = 5
    skills.append(blood_frenzy)
    
    # 7. 불사
    immortal = Skill("vampire_immortal", "불사", "일시 무적")
    immortal.effects = [
        ShieldEffect(base_amount=200),
        HealEffect(HealType.HP, percentage=0.3)
    ]
    immortal.costs = [MPCost(12), StackCost("blood_pool", 5)]
    immortal.target_type = "self"
    immortal.cooldown = 7
    skills.append(immortal)
    
    # 8. 피의 지배
    blood_control = Skill("vampire_control", "피의 지배", "피로 적 조종")
    blood_control.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "blood_pool", "multiplier": 0.35}),
        LifestealEffect(lifesteal_percent=0.8)
    ]
    blood_control.costs = [MPCost(14), StackCost("blood_pool", 4)]
    blood_control.cooldown = 6
    skills.append(blood_control)
    
    # 9. 궁극기: 혈족의 군주
    ultimate = Skill("vampire_ultimate", "혈족의 군주", "완전한 흡혈귀화")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5),
        DamageEffect(DamageType.HP, 3.0),
        LifestealEffect(lifesteal_percent=1.5),
        ShieldEffect(base_amount=150),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "blood_pool", 10)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    skills.append(ultimate)
    
    return skills

def register_vampire_skills(skill_manager):
    skills = create_vampire_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
