"""Breaker Skills - 브레이커 스킬 (BRV 파괴 특화)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_breaker_skills():
    """브레이커 9개 스킬"""
    skills = []
    
    # 1. 기본 BRV: 파쇄 타격
    crush_strike = Skill("breaker_crush", "파쇄 타격", "BRV 파괴 공격")
    crush_strike.effects = [
        DamageEffect(DamageType.BRV, 2.0),
        GimmickEffect(GimmickOperation.ADD, "break_power", 1, max_value=10)
    ]
    crush_strike.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(crush_strike)
    
    # 2. 기본 HP: 파괴의 일격
    break_hit = Skill("breaker_break_hit", "파괴의 일격", "BREAK 보너스")
    break_hit.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "break_power", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "break_power", 1)
    ]
    break_hit.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(break_hit)
    
    # 3. BRV 집중
    brv_focus = Skill("breaker_brv_focus", "BRV 집중", "BRV 공격력 증가")
    brv_focus.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.ADD, "break_power", 2, max_value=10)
    ]
    brv_focus.costs = [MPCost(6)]
    brv_focus.target_type = "self"
    brv_focus.cooldown = 3
    skills.append(brv_focus)
    
    # 4. 연타
    multi_strike = Skill("breaker_multi", "연타", "3연속 BRV 공격")
    multi_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        DamageEffect(DamageType.BRV, 1.5),
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "break_power", 2, max_value=10)
    ]
    multi_strike.costs = [MPCost(8)]
    multi_strike.cooldown = 2
    skills.append(multi_strike)
    
    # 5. 파괴 강화
    break_enhance = Skill("breaker_enhance", "파괴 강화", "BREAK 위력 증폭")
    break_enhance.effects = [
        GimmickEffect(GimmickOperation.ADD, "break_power", 5, max_value=10),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=3)
    ]
    break_enhance.costs = [MPCost(9)]
    break_enhance.target_type = "self"
    break_enhance.cooldown = 5
    skills.append(break_enhance)
    
    # 6. 대파쇄
    mega_crush = Skill("breaker_mega_crush", "대파쇄", "초강력 BRV 공격")
    mega_crush.effects = [
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "break_power", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.ADD, "break_power", 1, max_value=10)
    ]
    mega_crush.costs = [MPCost(10)]
    mega_crush.cooldown = 3
    skills.append(mega_crush)
    
    # 7. 파괴 충격파
    break_wave = Skill("breaker_wave", "파괴 충격파", "광역 BRV 공격")
    break_wave.effects = [
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "break_power", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.CONSUME, "break_power", 3)
    ]
    break_wave.costs = [MPCost(11), StackCost("break_power", 3)]
    break_wave.cooldown = 4
    skills.append(break_wave)
    
    # 8. 완전 파괴
    total_break = Skill("breaker_total", "완전 파괴", "절대 BREAK")
    total_break.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "break_power", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "break_power", 5)
    ]
    total_break.costs = [MPCost(14), StackCost("break_power", 5)]
    total_break.cooldown = 6
    skills.append(total_break)
    
    # 9. 궁극기: 절대 파괴
    ultimate = Skill("breaker_ultimate", "절대 파괴", "모든 것을 파괴")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.5, gimmick_bonus={"field": "break_power", "multiplier": 0.5}),
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "break_power", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 4.0),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "break_power", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    skills.append(ultimate)
    
    return skills

def register_breaker_skills(skill_manager):
    skills = create_breaker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
