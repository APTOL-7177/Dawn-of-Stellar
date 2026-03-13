"""Cleric Skills - 성직자 스킬 (치유/부활 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_cleric_skills():
    """성직자 10개 스킬 생성 (치유/부활 시스템)"""

    skills = []

    # 1. 기본 BRV: 치유의 기도
    pray = Skill("cleric_pray", "기도", "[신성 속성] 신앙 포인트 획득")
    pray.effects = [
        DamageEffect(DamageType.BRV, 0.85, stat_type="magical", element="holy"),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 1, max_value=8)
    ]
    pray.costs = []
    pray.sfx = ("skill", "cast_start")
    pray.metadata = {"element": "holy", "faith_gain": 1}
    skills.append(pray)

    # 2. 기본 HP: 성스러운 일격
    holy_attack = Skill("cleric_holy_attack", "성스러운 일격", "[신성 속성] 신앙 포인트 소비 공격")
    holy_attack.effects = [
        DamageEffect(DamageType.HP, 0.59, stat_type="magical", element="holy", gimmick_bonus={"field": "faith_points", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 1)
    ]
    holy_attack.costs = []
    holy_attack.sfx = ("skill", "cast_complete")
    holy_attack.metadata = {"element": "holy", "faith_cost": 1, "faith_scaling": True}
    skills.append(holy_attack)

    # 3. 치유의 기원
    heal = Skill("cleric_heal", "치유의 기원", "신앙 1포인트 소비, 단일 치유")
    heal.effects = [
        HealEffect(HealType.HP, stat_scaling="magic", multiplier=1.25),  # 마법력 기반 단일 치유
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 1)
    ]
    heal.costs = []
    heal.target_type = "ally"
    heal.cast_time = 0.7  # 강력한 치유는 긴 시전시간 필요
    # heal.cooldown = 1  # 쿨다운 시스템 제거됨
    heal.sfx = ("character", "hp_heal")  # 치유
    heal.metadata = {"faith_cost": 1, "healing": True}
    skills.append(heal)

    # 4. 상급 치유의 기도
    greater_heal = Skill("cleric_greater_heal", "상급 치유의 기도", "신앙 2포인트 소비, 강력한 치유")
    greater_heal.effects = [
        HealEffect(HealType.HP, stat_scaling="magic", multiplier=1.9),  # 마법력 기반 강력 치유
        BuffEffect(BuffType.REGEN, 0.18, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 2)
    ]
    greater_heal.costs = [MPCost(5), StackCost("faith_points", 2)]
    greater_heal.target_type = "ally"
    greater_heal.cast_time = 0.85
    # greater_heal.cooldown = 2  # 쿨다운 시스템 제거됨
    greater_heal.sfx = ("character", "hp_heal_high")  # 대치유
    greater_heal.metadata = {"faith_cost": 2, "healing": True, "regen": True}
    skills.append(greater_heal)

    # 5. 치유의 찬가
    mass_heal = Skill("cleric_mass_heal", "치유의 찬가", "신앙 3포인트 소비, 파티 치유")
    mass_heal.effects = [
        HealEffect(HealType.HP, stat_scaling="magic", multiplier=1.05, is_party_wide=True),  # 마법력 기반 파티 치유
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 3)
    ]
    mass_heal.costs = [MPCost(6), StackCost("faith_points", 3)]
    mass_heal.target_type = "party"
    mass_heal.cast_time = 0.95
    # mass_heal.cooldown = 4  # 쿨다운 시스템 제거됨
    mass_heal.sfx = ("character", "hp_heal_max")  # 집단 치유
    mass_heal.metadata = {"faith_cost": 3, "healing": True, "party_wide": True}
    skills.append(mass_heal)

    # 6. 은총의 기도
    faith_blessing = Skill("cleric_faith_blessing", "은총의 기도", "신앙 최대 회복")
    faith_blessing.effects = [
        GimmickEffect(GimmickOperation.SET, "faith_points", 8),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4),
        BuffEffect(BuffType.REGEN, 0.22, duration=4)
    ]
    faith_blessing.costs = [MPCost(6)]
    faith_blessing.target_type = "self"
    # faith_blessing.cooldown = 5  # 쿨다운 시스템 제거됨
    faith_blessing.sfx = ("character", "status_buff")  # 신앙의 축복
    faith_blessing.metadata = {"faith_max": True, "buff": True}
    skills.append(faith_blessing)

    # 7. 성역의 보호막
    holy_barrier = Skill("cleric_holy_barrier", "성역의 보호막", "신앙 4포인트 소비, 파티 보호")
    holy_barrier.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=4),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.5, duration=4),
        BuffEffect(BuffType.REGEN, 0.28, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 4)
    ]
    holy_barrier.costs = [MPCost(7), StackCost("faith_points", 4)]
    holy_barrier.target_type = "party"
    # holy_barrier.cooldown = 5  # 쿨다운 시스템 제거됨
    holy_barrier.sfx = ("skill", "protect")  # 신성한 보호막
    holy_barrier.metadata = {"faith_cost": 4, "buff": True, "party_wide": True}
    skills.append(holy_barrier)

    # 8. 소생의 기도
    resurrect = Skill("cleric_resurrect", "소생의 기도", "신앙 6포인트 소비, 동료 부활")
    resurrect.effects = [
        HealEffect(HealType.HP, stat_scaling="magic", multiplier=1.6),  # 마법력 기반 부활 회복
        BuffEffect(BuffType.REGEN, 0.35, duration=5),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 6)
    ]
    resurrect.costs = [MPCost(12), StackCost("faith_points", 6)]
    resurrect.target_type = "ally"
    resurrect.cast_time = 1.0
    # resurrect.cooldown = 8  # 쿨다운 시스템 제거됨
    resurrect.sfx = ("character", "revive")  # 부활
    resurrect.metadata = {"faith_cost": 6, "revival": True, "healing": True}
    skills.append(resurrect)

    # 9. 이단 심판 (NEW - 10번째 스킬로 만들기 위해 추가)
    holy_judgment = Skill("cleric_holy_judgment", "이단 심판", "[신성 속성] 신앙 5포인트 소비 대규모 신성 공격")
    holy_judgment.effects = [
        DamageEffect(DamageType.BRV_HP, 1.62, stat_type="magical", element="holy", gimmick_bonus={"field": "faith_points", "multiplier": 0.4}),
        BuffEffect(BuffType.ATTACK_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "faith_points", 5)
    ]
    holy_judgment.costs = [MPCost(10), StackCost("faith_points", 5)]
    holy_judgment.target_type = "all_enemies"
    holy_judgment.is_aoe = True
    holy_judgment.sfx = ("skill", "cast_complete")
    holy_judgment.metadata = {"element": "holy", "faith_cost": 5, "faith_scaling": True, "debuff": True, "aoe": True}
    skills.append(holy_judgment)

    # 10. 궁극기: 천상의 은총
    ultimate = Skill("cleric_ultimate", "천상의 은총", "[신성 속성] 모든 신앙으로 완전한 치유")
    ultimate.effects = [
        HealEffect(HealType.HP, stat_scaling="magic", multiplier=1.35, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5, is_party_wide=True),
        BuffEffect(BuffType.REGEN, 0.42, duration=5, is_party_wide=True),
        DamageEffect(DamageType.HP, 1.62, stat_type="magical", element="holy", gimmick_bonus={"field": "faith_points", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.SET, "faith_points", 0)
    ]
    ultimate.costs = [MPCost(30), StackCost("faith_points", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "party"
    ultimate.is_aoe = True
    ultimate.cast_time = 1.0
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {"ultimate": True, "element": "holy", "faith_consume_all": True, "healing": True, "party_wide": True, "buff": True}
    skills.append(ultimate)

    # 팀워크 스킬: 기적의 기도
    teamwork = TeamworkSkill(
        "cleric_teamwork",
        "치유의 기도",
        "파티 전체 마법력 기반 HP 회복 + 신앙 +1",
        gauge_cost=75)
    teamwork.effects = [
        HealEffect(HealType.HP, stat_scaling="magic", multiplier=1.15, is_party_wide=True),  # 마법력 기반 광역 치유
        GimmickEffect(GimmickOperation.ADD, "faith_points", 1, max_value=8),  # 신앙 +1
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.cast_time = 0  # 즉시 발동
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "healing": True, "cleanse": True}
    skills.append(teamwork)

    return skills

def register_cleric_skills(skill_manager):
    """성직자 스킬 등록"""
    skills = create_cleric_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 치유의 기도
    return [s.skill_id for s in skills]
