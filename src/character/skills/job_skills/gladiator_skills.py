"""Gladiator Skills - 검투사 스킬 (처치 보상/패링 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_gladiator_skills():
    """검투사 9개 스킬 생성"""
    
    # 1. 기본 BRV: 투기장 기술
    arena_strike = Skill("gladiator_arena_strike", "투기장 기술", "적 공격, 처치 시 영구 강화")
    arena_strike.effects = [
        DamageEffect(DamageType.BRV, 1.4, gimmick_bonus={"field": "kill_count", "multiplier": 0.1}),
        GimmickEffect(GimmickOperation.ADD, "glory_points", 1, max_value=10)
    ]
    arena_strike.costs = []  # 기본 공격은 MP 소모 없음
    
    # 2. 기본 HP: 명예의 일격
    honor_strike = Skill("gladiator_honor_strike", "명예의 일격", "처치 스택으로 강력한 일격")
    honor_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "kill_count", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.CONSUME, "glory_points", 1)
    ]
    honor_strike.costs = []  # 기본 공격은 MP 소모 없음
    
    # 3. 패링
    parry = Skill("gladiator_parry", "패링", "다음 공격을 반격으로 전환")
    parry.effects = [
        GimmickEffect(GimmickOperation.SET, "parry_active", 1),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=2)
    ]
    parry.costs = [MPCost(6)]
    parry.target_type = "self"
    parry.cooldown = 4
    
    # 4. 처형
    execute = Skill("gladiator_execute", "처형", "영광 포인트 소비, 처형 일격")
    execute.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "glory_points", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.ADD, "kill_count", 1),  # 처치 가정
        GimmickEffect(GimmickOperation.CONSUME, "glory_points", 2)
    ]
    execute.costs = [MPCost(9), StackCost("glory_points", 2)]
    execute.cooldown = 3
    
    # 5. 투사의 기백
    warrior_spirit = Skill("gladiator_spirit", "투사의 기백", "처치 경험으로 힘 강화")
    warrior_spirit.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=4),
        GimmickEffect(GimmickOperation.ADD, "glory_points", 2, max_value=10)
    ]
    warrior_spirit.costs = [MPCost(8)]
    warrior_spirit.target_type = "self"
    warrior_spirit.cooldown = 4
    
    # 6. 피의 갈증
    blood_thirst = Skill("gladiator_blood_thirst", "피의 갈증", "공격 + 처치 시 회복")
    blood_thirst.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "kill_count", "multiplier": 0.15}),
        HealEffect(HealType.HP, percentage=0.2),
        GimmickEffect(GimmickOperation.ADD, "glory_points", 1, max_value=10)
    ]
    blood_thirst.costs = [MPCost(7)]
    blood_thirst.cooldown = 2
    
    # 7. 결투자의 영광
    duel_glory = Skill("gladiator_duel_glory", "결투자의 영광", "영광 포인트로 전투력 폭발")
    duel_glory.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "glory_points", "multiplier": 0.35}),
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "glory_points", 3)
    ]
    duel_glory.costs = [MPCost(11), StackCost("glory_points", 3)]
    duel_glory.cooldown = 5
    
    # 8. 챔피언의 함성
    champion_roar = Skill("gladiator_roar", "챔피언의 함성", "처치 횟수로 아군 고무")
    champion_roar.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.2, duration=4, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.15, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "glory_points", 2, max_value=10)
    ]
    champion_roar.costs = [MPCost(10)]
    champion_roar.target_type = "party"
    champion_roar.cooldown = 6
    
    # 9. 궁극기: 콜로세움의 왕
    ultimate = Skill("gladiator_ultimate", "콜로세움의 왕", "모든 영광으로 최강 일격")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "glory_points", "multiplier": 0.5}),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "kill_count", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 3.5),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.4, duration=5),
        GimmickEffect(GimmickOperation.SET, "glory_points", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    
    return [arena_strike, honor_strike, parry, execute, warrior_spirit,
            blood_thirst, duel_glory, champion_roar, ultimate]

def register_gladiator_skills(skill_manager):
    """검투사 스킬 등록"""
    skills = create_gladiator_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
