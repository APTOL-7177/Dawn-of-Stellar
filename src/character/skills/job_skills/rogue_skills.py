"""Rogue Skills - 도적 스킬 (아이템/훔치기 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_rogue_skills():
    """도적 9개 스킬"""
    
    skills = []
    
    # 1. 기본 BRV: 기습
    ambush = Skill("rogue_ambush", "기습", "빠른 기습 공격, 아이템 획득")
    ambush.effects = [
        DamageEffect(DamageType.BRV, 1.3),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    ambush.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(ambush)
    
    # 2. 기본 HP: 급소 공격
    vital_strike = Skill("rogue_vital_strike", "급소 공격", "치명타 확정")
    vital_strike.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "stolen_items", "multiplier": 0.15})
    ]
    vital_strike.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(vital_strike)
    
    # 3. 훔치기
    steal = Skill("rogue_steal", "훔치기", "적의 버프/자원 훔치기")
    steal.effects = [
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 3, max_value=10),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=3)
    ]
    steal.costs = [MPCost(6)]
    steal.cooldown = 3
    skills.append(steal)
    
    # 4. 연막탄
    smoke_bomb = Skill("rogue_smoke", "연막탄", "회피 + 아이템 사용")
    smoke_bomb.effects = [
        GimmickEffect(GimmickOperation.SET, "evasion_active", 1),
        BuffEffect(BuffType.EVASION_UP, 0.4, duration=2)
    ]
    smoke_bomb.costs = [MPCost(5)]
    smoke_bomb.target_type = "self"
    smoke_bomb.cooldown = 4
    skills.append(smoke_bomb)
    
    # 5. 아이템 활용
    use_item = Skill("rogue_use_item", "아이템 활용", "훔친 아이템으로 공격")
    use_item.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "stolen_items", "multiplier": 0.25})
    ]
    use_item.costs = [MPCost(8), StackCost("stolen_items", 2)]
    use_item.cooldown = 2
    skills.append(use_item)
    
    # 6. 독 바르기
    poison_blade = Skill("rogue_poison", "독 바르기", "지속 피해")
    poison_blade.effects = [
        DamageEffect(DamageType.BRV, 1.2),
        DamageEffect(DamageType.BRV, 0.8),
        DamageEffect(DamageType.BRV, 0.8),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    poison_blade.costs = [MPCost(7)]
    poison_blade.cooldown = 3
    skills.append(poison_blade)
    
    # 7. 보물 사냥
    treasure_hunt = Skill("rogue_treasure", "보물 사냥", "골드/아이템 대량 획득")
    treasure_hunt.effects = [
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10),
        BuffEffect(BuffType.LUCK, 0.3, duration=4)
    ]
    treasure_hunt.costs = [MPCost(9)]
    treasure_hunt.target_type = "self"
    treasure_hunt.cooldown = 5
    skills.append(treasure_hunt)
    
    # 8. 배신자의 일격
    backstab = Skill("rogue_backstab", "배신자의 일격", "아이템 소비 초강타")
    backstab.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "stolen_items", "multiplier": 0.4})
    ]
    backstab.costs = [MPCost(12), StackCost("stolen_items", 4)]
    backstab.cooldown = 5
    skills.append(backstab)
    
    # 9. 궁극기: 완벽한 강탈
    ultimate = Skill("rogue_ultimate", "완벽한 강탈", "모든 것을 훔치는 궁극기")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "stolen_items", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.0),
        GimmickEffect(GimmickOperation.SET, "stolen_items", 10),
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.4, duration=5)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    skills.append(ultimate)
    
    return skills

def register_rogue_skills(skill_manager):
    skills = create_rogue_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
