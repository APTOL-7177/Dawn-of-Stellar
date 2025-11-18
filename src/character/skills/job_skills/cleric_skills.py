"""Cleric Skills - 성직자 스킬 (치유/부활 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_cleric_skills():
    """성직자 10개 스킬 생성 (치유/부활 시스템)"""

    skills = []

    # 1. 기본 BRV: 기도
    pray = Skill("cleric_pray", "기도", "신앙 포인트 획득")
    pray.effects = [
        DamageEffect(DamageType.BRV, 1.3, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 1, max_value=8)
    ]
    pray.costs = []  # 기본 공격은 MP 소모 없음
    pray.sfx = "543"
    pray.metadata = {"faith_gain": 1}
    skills.append(pray)

    # 2. 기본 HP: 신성 공격
    holy_attack = Skill("cleric_holy_attack", "신성 공격", "신앙 포인트 소비 공격")
    holy_attack.effects = [
        DamageEffect(DamageType.HP, 0.9, gimmick_bonus={"field": "faith_points", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 1)
    ]
    holy_attack.costs = []  # 기본 공격은 MP 소모 없음
    holy_attack.sfx = "548"
    holy_attack.metadata = {"faith_cost": 1, "faith_scaling": True}
    skills.append(holy_attack)

    # 3. 치유
    heal = Skill("cleric_heal", "치유", "신앙 1포인트 소비, 단일 치유")
    heal.effects = [
        HealEffect(HealType.HP, percentage=0.4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 1)
    ]
    heal.costs = []
    heal.target_type = "ally"
    # heal.cooldown = 1  # 쿨다운 시스템 제거됨
    heal.sfx = "558"
    heal.metadata = {"faith_cost": 1, "healing": True}
    skills.append(heal)

    # 4. 대치유
    greater_heal = Skill("cleric_greater_heal", "대치유", "신앙 2포인트 소비, 강력한 치유")
    greater_heal.effects = [
        HealEffect(HealType.HP, percentage=0.6),
        BuffEffect(BuffType.REGEN, 0.2, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 2)
    ]
    greater_heal.costs = [MPCost(5), StackCost("faith_points", 2)]
    greater_heal.target_type = "ally"
    # greater_heal.cooldown = 2  # 쿨다운 시스템 제거됨
    greater_heal.sfx = "568"
    greater_heal.metadata = {"faith_cost": 2, "healing": True, "regen": True}
    skills.append(greater_heal)

    # 5. 집단 치유
    mass_heal = Skill("cleric_mass_heal", "집단 치유", "신앙 3포인트 소비, 파티 치유")
    mass_heal.effects = [
        HealEffect(HealType.HP, percentage=0.35, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 3)
    ]
    mass_heal.costs = [MPCost(6), StackCost("faith_points", 3)]
    mass_heal.target_type = "party"
    # mass_heal.cooldown = 4  # 쿨다운 시스템 제거됨
    mass_heal.sfx = "578"
    mass_heal.metadata = {"faith_cost": 3, "healing": True, "party_wide": True}
    skills.append(mass_heal)

    # 6. 신앙의 축복
    faith_blessing = Skill("cleric_faith_blessing", "신앙의 축복", "신앙 최대 회복")
    faith_blessing.effects = [
        GimmickEffect(GimmickOperation.SET, "faith_points", 8),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4),
        BuffEffect(BuffType.REGEN, 0.25, duration=4)
    ]
    faith_blessing.costs = [MPCost(6)]
    faith_blessing.target_type = "self"
    # faith_blessing.cooldown = 5  # 쿨다운 시스템 제거됨
    faith_blessing.sfx = "588"
    faith_blessing.metadata = {"faith_max": True, "buff": True}
    skills.append(faith_blessing)

    # 7. 신성한 보호막
    holy_barrier = Skill("cleric_holy_barrier", "신성한 보호막", "신앙 4포인트 소비, 파티 보호")
    holy_barrier.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=4),
        BuffEffect(BuffType.REGEN, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 4)
    ]
    holy_barrier.costs = [MPCost(7), StackCost("faith_points", 4)]
    holy_barrier.target_type = "party"
    # holy_barrier.cooldown = 5  # 쿨다운 시스템 제거됨
    holy_barrier.sfx = "598"
    holy_barrier.metadata = {"faith_cost": 4, "buff": True, "party_wide": True}
    skills.append(holy_barrier)

    # 8. 부활
    resurrect = Skill("cleric_resurrect", "부활", "신앙 6포인트 소비, 동료 부활")
    resurrect.effects = [
        HealEffect(HealType.HP, percentage=0.5),
        BuffEffect(BuffType.REGEN, 0.4, duration=5),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 6)
    ]
    resurrect.costs = [MPCost(12), StackCost("faith_points", 6)]
    resurrect.target_type = "ally"
    # resurrect.cooldown = 8  # 쿨다운 시스템 제거됨
    resurrect.sfx = "608"
    resurrect.metadata = {"faith_cost": 6, "revival": True, "healing": True}
    skills.append(resurrect)

    # 9. 성스러운 심판 (NEW - 10번째 스킬로 만들기 위해 추가)
    holy_judgment = Skill("cleric_holy_judgment", "성스러운 심판", "신앙 5포인트 소비 대규모 신성 공격")
    holy_judgment.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "faith_points", "multiplier": 0.4}, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 5)
    ]
    holy_judgment.costs = [MPCost(10), StackCost("faith_points", 5)]
    holy_judgment.is_aoe = True
    # holy_judgment.cooldown = 6  # 쿨다운 시스템 제거됨
    holy_judgment.sfx = "618"
    holy_judgment.metadata = {"faith_cost": 5, "faith_scaling": True, "debuff": True, "aoe": True}
    skills.append(holy_judgment)

    # 10. 궁극기: 신의 은총
    ultimate = Skill("cleric_ultimate", "신의 은총", "모든 신앙으로 완전한 치유")
    ultimate.effects = [
        HealEffect(HealType.HP, percentage=0.8, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5, is_party_wide=True),
        BuffEffect(BuffType.REGEN, 0.5, duration=5, is_party_wide=True),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "faith_points", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "faith_points", 0)
    ]
    ultimate.costs = [MPCost(18), StackCost("faith_points", 1)]
    ultimate.is_ultimate = True
    ultimate.target_type = "party"
    ultimate.is_aoe = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = "628"
    ultimate.metadata = {"ultimate": True, "faith_consume_all": True, "healing": True, "party_wide": True, "buff": True}
    skills.append(ultimate)

    return skills

def register_cleric_skills(skill_manager):
    """성직자 스킬 등록"""
    skills = create_cleric_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
