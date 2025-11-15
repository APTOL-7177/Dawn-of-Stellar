"""Sniper Skills - 저격수 스킬 (조준/1발 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_sniper_skills():
    """저격수 9개 스킬"""
    skills = []
    
    # 1. 기본 BRV: 정밀 조준
    precise_aim = Skill("sniper_aim", "정밀 조준", "조준 집중")
    precise_aim.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        GimmickEffect(GimmickOperation.ADD, "focus_stacks", 1, max_value=10)
    ]
    precise_aim.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(precise_aim)
    
    # 2. 기본 HP: 헤드샷
    headshot = Skill("sniper_headshot", "헤드샷", "집중 소비 치명타")
    headshot.effects = [
        DamageEffect(DamageType.HP, 2.0, gimmick_bonus={"field": "focus_stacks", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "focus_stacks", 2)
    ]
    headshot.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(headshot)
    
    # 3. 완벽한 집중
    perfect_focus = Skill("sniper_perfect_focus", "완벽한 집중", "집중 최대화")
    perfect_focus.effects = [
        GimmickEffect(GimmickOperation.ADD, "focus_stacks", 5, max_value=10),
        BuffEffect(BuffType.CRITICAL_UP, 0.5, duration=3)
    ]
    perfect_focus.costs = [MPCost(8)]
    perfect_focus.target_type = "self"
    perfect_focus.cooldown = 5
    skills.append(perfect_focus)
    
    # 4. 관통 사격
    penetrating_shot = Skill("sniper_penetrate", "관통 사격", "방어 무시 사격")
    penetrating_shot.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "focus_stacks", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "focus_stacks", 3)
    ]
    penetrating_shot.costs = [MPCost(10), StackCost("focus_stacks", 3)]
    penetrating_shot.cast_time = 2.5
    penetrating_shot.cooldown = 3
    skills.append(penetrating_shot)
    
    # 5. 저격 자세
    sniper_stance = Skill("sniper_stance", "저격 자세", "완벽한 자세")
    sniper_stance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        BuffEffect(BuffType.ACCURACY_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.ADD, "focus_stacks", 2, max_value=10)
    ]
    sniper_stance.costs = [MPCost(6)]
    sniper_stance.target_type = "self"
    sniper_stance.cooldown = 4
    skills.append(sniper_stance)
    
    # 6. 급소 파악
    weak_spot = Skill("sniper_weak_spot", "급소 파악", "적 약점 간파")
    weak_spot.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "focus_stacks", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.ADD, "focus_stacks", 2, max_value=10)
    ]
    weak_spot.costs = [MPCost(7)]
    weak_spot.cast_time = 1.8
    weak_spot.cooldown = 2
    skills.append(weak_spot)
    
    # 7. 폭발탄
    explosive_round = Skill("sniper_explosive", "폭발탄", "폭발 피해")
    explosive_round.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "focus_stacks", "multiplier": 0.38}),
        GimmickEffect(GimmickOperation.CONSUME, "focus_stacks", 4)
    ]
    explosive_round.costs = [MPCost(12), StackCost("focus_stacks", 4)]
    explosive_round.cast_time = 2.2
    explosive_round.cooldown = 5
    skills.append(explosive_round)
    
    # 8. 최종 조준
    final_aim = Skill("sniper_final_aim", "최종 조준", "절대 명중")
    final_aim.effects = [
        GimmickEffect(GimmickOperation.SET, "focus_stacks", 10),
        BuffEffect(BuffType.CRITICAL_UP, 0.8, duration=2)
    ]
    final_aim.costs = [MPCost(15)]
    final_aim.target_type = "self"
    final_aim.cooldown = 8
    skills.append(final_aim)
    
    # 9. 궁극기: 절대영도
    ultimate = Skill("sniper_ultimate", "절대영도", "완벽한 1발")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "focus_stacks", "multiplier": 0.6}),
        DamageEffect(DamageType.HP, 5.0, gimmick_bonus={"field": "focus_stacks", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.SET, "focus_stacks", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cast_time = 3.0
    ultimate.cooldown = 10
    skills.append(ultimate)
    
    return skills

def register_sniper_skills(skill_manager):
    skills = create_sniper_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
