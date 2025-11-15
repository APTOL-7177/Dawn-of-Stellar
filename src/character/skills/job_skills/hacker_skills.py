"""Hacker Skills - 해커 스킬 (해킹/디버프 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_hacker_skills():
    """해커 9개 스킬"""
    skills = []
    
    # 1. 기본 BRV: 해킹 시도
    hack_attempt = Skill("hacker_hack", "해킹 시도", "시스템 침투")
    hack_attempt.effects = [
        DamageEffect(DamageType.BRV, 1.3, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "hack_stacks", 1, max_value=10)
    ]
    hack_attempt.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(hack_attempt)
    
    # 2. 기본 HP: 시스템 오버로드
    overload = Skill("hacker_overload", "시스템 오버로드", "해킹 완료 후 폭발")
    overload.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "hack_stacks", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "hack_stacks", 1)
    ]
    overload.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(overload)
    
    # 3. 디버프 설치
    install_debuff = Skill("hacker_debuff", "디버프 설치", "적 약화")
    install_debuff.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "debuff_count", 1, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "hack_stacks", 2, max_value=10)
    ]
    install_debuff.costs = [MPCost(6)]
    install_debuff.cooldown = 2
    skills.append(install_debuff)
    
    # 4. 시스템 교란
    disrupt = Skill("hacker_disrupt", "시스템 교란", "적 능력 감소")
    disrupt.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "hack_stacks", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "hack_stacks", 1, max_value=10)
    ]
    disrupt.costs = [MPCost(7)]
    disrupt.cooldown = 2
    skills.append(disrupt)
    
    # 5. 바이러스 유포
    virus = Skill("hacker_virus", "바이러스 유포", "지속 피해")
    virus.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.0, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.0, stat_type="magical"),
        DamageEffect(DamageType.BRV, 0.8, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "hack_stacks", 2, max_value=10)
    ]
    virus.costs = [MPCost(9)]
    virus.cooldown = 3
    skills.append(virus)
    
    # 6. 백도어
    backdoor = Skill("hacker_backdoor", "백도어", "해킹 축적")
    backdoor.effects = [
        GimmickEffect(GimmickOperation.ADD, "hack_stacks", 5, max_value=10),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=3)
    ]
    backdoor.costs = [MPCost(8)]
    backdoor.target_type = "self"
    backdoor.cooldown = 5
    skills.append(backdoor)
    
    # 7. 시스템 다운
    system_down = Skill("hacker_system_down", "시스템 다운", "강제 종료")
    system_down.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "hack_stacks", "multiplier": 0.35}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "hack_stacks", 3)
    ]
    system_down.costs = [MPCost(11), StackCost("hack_stacks", 3)]
    system_down.cooldown = 4
    skills.append(system_down)
    
    # 8. 루트킷
    rootkit = Skill("hacker_rootkit", "루트킷", "완전 장악")
    rootkit.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "hack_stacks", "multiplier": 0.4}, stat_type="magical"),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "hack_stacks", 5)
    ]
    rootkit.costs = [MPCost(14), StackCost("hack_stacks", 5)]
    rootkit.cooldown = 6
    skills.append(rootkit)
    
    # 9. 궁극기: 제로데이
    ultimate = Skill("hacker_ultimate", "제로데이", "완벽한 해킹")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "hack_stacks", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.5, gimmick_bonus={"field": "debuff_count", "multiplier": 0.6}, stat_type="magical"),
        BuffEffect(BuffType.MAGIC_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "hack_stacks", 10),
        GimmickEffect(GimmickOperation.SET, "debuff_count", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    skills.append(ultimate)
    
    return skills

def register_hacker_skills(skill_manager):
    skills = create_hacker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
