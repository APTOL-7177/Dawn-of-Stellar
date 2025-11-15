"""Cleric Skills - 성직자 스킬 (치유/부활 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_cleric_skills():
    """성직자 9개 스킬 생성"""

    # 1. 기본 BRV: 기도
    pray = Skill("cleric_pray", "기도", "신앙 포인트 획득")
    pray.effects = [
        DamageEffect(DamageType.BRV, 1.3, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 1, max_value=8)
    ]
    pray.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 신성 공격
    holy_attack = Skill("cleric_holy_attack", "신성 공격", "신앙 포인트 소비 공격")
    holy_attack.effects = [
        DamageEffect(DamageType.HP, 0.9, gimmick_bonus={"field": "faith_points", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 1)
    ]
    holy_attack.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 치유
    heal = Skill("cleric_heal", "치유", "신앙 1포인트 소비, 단일 치유")
    heal.effects = [
        HealEffect(HealType.HP, percentage=0.4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 1)
    ]
    heal.costs = [MPCost(6), StackCost("faith_points", 1)]
    heal.target_type = "ally"
    heal.cooldown = 1

    # 4. 대치유
    greater_heal = Skill("cleric_greater_heal", "대치유", "신앙 2포인트 소비, 강력한 치유")
    greater_heal.effects = [
        HealEffect(HealType.HP, percentage=0.6),
        BuffEffect(BuffType.REGEN, 0.2, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 2)
    ]
    greater_heal.costs = [MPCost(8), StackCost("faith_points", 2)]
    greater_heal.target_type = "ally"
    greater_heal.cooldown = 2

    # 5. 집단 치유
    mass_heal = Skill("cleric_mass_heal", "집단 치유", "신앙 3포인트 소비, 파티 치유")
    mass_heal.effects = [
        HealEffect(HealType.HP, percentage=0.35, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 3)
    ]
    mass_heal.costs = [MPCost(10), StackCost("faith_points", 3)]
    mass_heal.target_type = "party"
    mass_heal.cooldown = 4

    # 6. 신앙의 축복
    faith_blessing = Skill("cleric_faith_blessing", "신앙의 축복", "신앙 최대 회복")
    faith_blessing.effects = [
        GimmickEffect(GimmickOperation.SET, "faith_points", 8),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4),
        BuffEffect(BuffType.REGEN, 0.25, duration=4)
    ]
    faith_blessing.costs = [MPCost(9)]
    faith_blessing.target_type = "self"
    faith_blessing.cooldown = 5

    # 7. 신성한 보호막
    holy_barrier = Skill("cleric_holy_barrier", "신성한 보호막", "신앙 4포인트 소비, 파티 보호")
    holy_barrier.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=4),
        BuffEffect(BuffType.REGEN, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 4)
    ]
    holy_barrier.costs = [MPCost(12), StackCost("faith_points", 4)]
    holy_barrier.target_type = "party"
    holy_barrier.cooldown = 5

    # 8. 부활
    resurrect = Skill("cleric_resurrect", "부활", "신앙 6포인트 소비, 동료 부활")
    resurrect.effects = [
        HealEffect(HealType.HP, percentage=0.5),
        BuffEffect(BuffType.REGEN, 0.4, duration=5),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 6)
    ]
    resurrect.costs = [MPCost(18), StackCost("faith_points", 6)]
    resurrect.target_type = "ally"
    resurrect.cooldown = 8

    # 9. 궁극기: 신의 은총
    ultimate = Skill("cleric_ultimate", "신의 은총", "모든 신앙으로 완전한 치유")
    ultimate.effects = [
        HealEffect(HealType.HP, percentage=0.8, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5),
        BuffEffect(BuffType.REGEN, 0.5, duration=5),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "faith_points", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "faith_points", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("faith_points", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10

    return [pray, holy_attack, heal, greater_heal, mass_heal,
            faith_blessing, holy_barrier, resurrect, ultimate]

def register_cleric_skills(skill_manager):
    """성직자 스킬 등록"""
    skills = create_cleric_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
