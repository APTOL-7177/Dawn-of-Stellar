"""Archer Skills - 궁수 스킬 (조준 포인트 + 지원사격)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.support_fire_effect import SupportFireEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_archer_skills():
    """궁수 9개 스킬 생성"""
    
    # 1. 기본 BRV: 삼연사
    triple_shot = Skill("archer_triple_shot", "삼연사", "3회 연속 사격, 조준 포인트 획득")
    triple_shot.effects = [
        DamageEffect(DamageType.BRV, 0.6),  # 약한 대신 3회
        DamageEffect(DamageType.BRV, 0.6),
        DamageEffect(DamageType.BRV, 0.6),
        GimmickEffect(GimmickOperation.ADD, "aim_points", 1, max_value=5)
    ]
    triple_shot.costs = []  # 기본 공격은 MP 소모 없음
    
    # 2. 기본 HP: 정밀 사격
    precision_shot = Skill("archer_precision_shot", "정밀 사격", "조준 포인트로 강화된 HP 공격")
    precision_shot.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "aim_points", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.CONSUME, "aim_points", 1)
    ]
    precision_shot.costs = []  # 기본 공격은 MP 소모 없음
    
    # 3. 지원 사격
    support_fire = Skill("archer_support_fire", "지원 사격", "아군 행동 시 조준 포인트 소비 자동 사격")
    support_fire.effects = [
        SupportFireEffect(max_points=3, damage_per_point=20),
        BuffEffect(BuffType.ATTACK_UP, multiplier=1.15, duration=3)
    ]
    support_fire.costs = [MPCost(6)]
    support_fire.target_type = "self"
    support_fire.cooldown = 4
    
    # 4. 관통 사격
    piercing_arrow = Skill("archer_piercing_arrow", "관통 사격", "조준 포인트로 관통 공격")
    piercing_arrow.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "aim_points", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.ADD, "aim_points", 1, max_value=5)
    ]
    piercing_arrow.costs = [MPCost(6)]
    piercing_arrow.target_type = "all_enemies"
    piercing_arrow.cooldown = 2
    
    # 5. 집중
    focus = Skill("archer_focus", "집중", "조준 포인트 대량 축적")
    focus.effects = [
        GimmickEffect(GimmickOperation.ADD, "aim_points", 3, max_value=5),
        BuffEffect(BuffType.CRITICAL_UP, multiplier=1.5, duration=2)
    ]
    focus.costs = [MPCost(5)]
    focus.target_type = "self"
    focus.cooldown = 3
    
    # 6. 연속 화살
    rapid_arrows = Skill("archer_rapid_arrows", "연속 화살", "빠른 연속 사격")
    rapid_arrows.effects = [
        DamageEffect(DamageType.BRV, 1.0),
        DamageEffect(DamageType.BRV, 1.0),
        DamageEffect(DamageType.HP, 1.0),
        GimmickEffect(GimmickOperation.ADD, "aim_points", 2, max_value=5)
    ]
    rapid_arrows.costs = [MPCost(8)]
    rapid_arrows.cast_time = 0.8
    rapid_arrows.cooldown = 3
    
    # 7. 명중 강화
    accuracy_up = Skill("archer_accuracy_up", "명중 강화", "명중률과 조준 포인트 증가")
    accuracy_up.effects = [
        GimmickEffect(GimmickOperation.ADD, "aim_points", 2, max_value=5),
        BuffEffect(BuffType.ACCURACY_UP, multiplier=1.3, duration=4)
    ]
    accuracy_up.costs = [MPCost(4)]
    accuracy_up.target_type = "self"
    accuracy_up.cooldown = 4
    
    # 8. 헤드샷
    headshot = Skill("archer_headshot", "헤드샷", "조준 포인트 소비, 크리티컬 확정 HP 공격")
    headshot.effects = [
        DamageEffect(DamageType.HP, 2.0, gimmick_bonus={"field": "aim_points", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "aim_points", 3)
    ]
    headshot.costs = [MPCost(10), StackCost("aim_points", 3)]
    headshot.cooldown = 5
    
    # 9. 궁극기: 천공 사격
    heaven_piercer = Skill("archer_ultimate", "천공 사격", "모든 조준 포인트로 절대 명중 일격")
    heaven_piercer.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "aim_points", "multiplier": 0.5}),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "aim_points", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 2.5),
        GimmickEffect(GimmickOperation.SET, "aim_points", 0)
    ]
    heaven_piercer.costs = [MPCost(20), StackCost("aim_points", 1)]
    heaven_piercer.is_ultimate = True
    heaven_piercer.cooldown = 10
    
    return [triple_shot, precision_shot, support_fire, piercing_arrow, focus,
            rapid_arrows, accuracy_up, headshot, heaven_piercer]

def register_archer_skills(skill_manager):
    """궁수 스킬 등록"""
    skills = create_archer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
