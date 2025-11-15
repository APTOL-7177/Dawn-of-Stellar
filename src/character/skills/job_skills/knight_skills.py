"""Knight Skills - 기사 스킬 (의무/수호 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_knight_skills():
    """기사 9개 스킬"""
    skills = []
    
    # 1. 기본 BRV: 창 돌격
    lance_charge = Skill("knight_lance", "창 돌격", "돌격 공격, 의무 생성")
    lance_charge.effects = [
        DamageEffect(DamageType.BRV, 1.4),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    lance_charge.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(lance_charge)
    
    # 2. 기본 HP: 의무의 일격
    duty_strike = Skill("knight_duty_strike", "의무의 일격", "의무 소비 공격")
    duty_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "duty_stacks", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 1)
    ]
    duty_strike.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(duty_strike)
    
    # 3. 수호의 맹세
    guardian_oath = Skill("knight_oath", "수호의 맹세", "아군 보호")
    guardian_oath.effects = [
        ShieldEffect(base_amount=60),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    guardian_oath.costs = [MPCost(6)]
    guardian_oath.target_type = "ally"
    guardian_oath.cooldown = 3
    skills.append(guardian_oath)
    
    # 4. 기사도
    chivalry = Skill("knight_chivalry", "기사도", "의무로 방어력 증가")
    chivalry.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.35, duration=4),
        BuffEffect(BuffType.SPIRIT_UP, 0.35, duration=4),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    chivalry.costs = [MPCost(8)]
    chivalry.target_type = "self"
    chivalry.cooldown = 4
    skills.append(chivalry)
    
    # 5. 불굴의 의지
    iron_will = Skill("knight_iron_will", "불굴의 의지", "생존 + 의무")
    iron_will.effects = [
        ShieldEffect(base_amount=100),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 2, max_value=5)
    ]
    iron_will.costs = [MPCost(9)]
    iron_will.target_type = "self"
    iron_will.cooldown = 5
    skills.append(iron_will)
    
    # 6. 방패 강타
    shield_bash = Skill("knight_bash", "방패 강타", "방어 + 공격")
    shield_bash.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "duty_stacks", "multiplier": 0.2}),
        ShieldEffect(base_amount=40),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    shield_bash.costs = [MPCost(7)]
    shield_bash.cooldown = 2
    skills.append(shield_bash)
    
    # 7. 최후의 보루
    last_stand = Skill("knight_last_stand", "최후의 보루", "의무 3 소비, 생존")
    last_stand.effects = [
        ShieldEffect(base_amount=150),
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 3)
    ]
    last_stand.costs = [MPCost(12), StackCost("duty_stacks", 3)]
    last_stand.target_type = "self"
    last_stand.cooldown = 6
    skills.append(last_stand)
    
    # 8. 헌신
    devotion = Skill("knight_devotion", "헌신", "파티 전체 보호")
    devotion.effects = [
        ShieldEffect(base_amount=80),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    devotion.costs = [MPCost(11)]
    devotion.target_type = "party"
    devotion.cooldown = 6
    skills.append(devotion)
    
    # 9. 궁극기: 성스러운 돌격
    ultimate = Skill("knight_ultimate", "성스러운 돌격", "모든 의무로 최후 돌격")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "duty_stacks", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.0),
        ShieldEffect(base_amount=200),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "duty_stacks", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    skills.append(ultimate)
    
    return skills

def register_knight_skills(skill_manager):
    skills = create_knight_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
