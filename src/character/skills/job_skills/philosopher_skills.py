"""Philosopher Skills - 철학자 스킬 (분석/적응 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_philosopher_skills():
    """철학자 9개 스킬 생성"""

    # 1. 기본 BRV: 분석
    analyze = Skill("philosopher_analyze", "분석", "지식 스택 획득")
    analyze.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "knowledge_stacks", 1, max_value=10)
    ]
    analyze.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 논리적 공격
    logic_strike = Skill("philosopher_logic_strike", "논리적 공격", "지식 소비 공격")
    logic_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.15}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "knowledge_stacks", 1)
    ]
    logic_strike.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 통찰력
    insight = Skill("philosopher_insight", "통찰력", "지식 2스택 획득 + 정확도 상승")
    insight.effects = [
        GimmickEffect(GimmickOperation.ADD, "knowledge_stacks", 2, max_value=10),
        BuffEffect(BuffType.ACCURACY_UP, 0.4, duration=3)
    ]
    insight.costs = [MPCost(6)]
    insight.target_type = "self"
    insight.cooldown = 2

    # 4. 패턴 인식
    pattern_recognition = Skill("philosopher_pattern_recognition", "패턴 인식", "지식 2스택 소비, 약점 공격")
    pattern_recognition.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.2}, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "knowledge_stacks", 2)
    ]
    pattern_recognition.costs = [MPCost(8), StackCost("knowledge_stacks", 2)]
    pattern_recognition.cooldown = 3

    # 5. 이론 정립
    theory_establish = Skill("philosopher_theory_establish", "이론 정립", "지식 3스택 소비, 버프")
    theory_establish.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "knowledge_stacks", 3)
    ]
    theory_establish.costs = [MPCost(9), StackCost("knowledge_stacks", 3)]
    theory_establish.target_type = "self"
    theory_establish.cooldown = 4

    # 6. 전략 수립
    strategy_plan = Skill("philosopher_strategy_plan", "전략 수립", "지식 최대 회복")
    strategy_plan.effects = [
        GimmickEffect(GimmickOperation.SET, "knowledge_stacks", 10),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=4)
    ]
    strategy_plan.costs = [MPCost(10)]
    strategy_plan.target_type = "self"
    strategy_plan.cooldown = 5

    # 7. 논리 폭발
    logic_burst = Skill("philosopher_logic_burst", "논리 폭발", "지식 5스택 소비, 광역 공격")
    logic_burst.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "knowledge_stacks", 5)
    ]
    logic_burst.costs = [MPCost(12), StackCost("knowledge_stacks", 5)]
    logic_burst.cooldown = 4
    logic_burst.is_aoe = True

    # 8. 완벽한 분석
    perfect_analysis = Skill("philosopher_perfect_analysis", "완벽한 분석", "지식 7스택 소비, 치명타 확정")
    perfect_analysis.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "knowledge_stacks", 7)
    ]
    perfect_analysis.costs = [MPCost(15), StackCost("knowledge_stacks", 7)]
    perfect_analysis.cooldown = 6

    # 9. 궁극기: 진리 도달
    ultimate = Skill("philosopher_ultimate", "진리 도달", "모든 지식으로 진리 공격")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.0, gimmick_bonus={"field": "knowledge_stacks", "multiplier": 0.35}, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "knowledge_stacks", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("knowledge_stacks", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10

    return [analyze, logic_strike, insight, pattern_recognition, theory_establish,
            strategy_plan, logic_burst, perfect_analysis, ultimate]

def register_philosopher_skills(skill_manager):
    """철학자 스킬 등록"""
    skills = create_philosopher_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
