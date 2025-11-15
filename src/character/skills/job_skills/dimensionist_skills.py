"""Dimensionist Skills - 차원술사 스킬 (차원 이동 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_dimensionist_skills():
    """차원술사 9개 스킬 생성"""

    # 1. 기본 BRV: 차원 균열
    dimension_rift = Skill("dimensionist_dimension_rift", "차원 균열", "차원 포인트 획득")
    dimension_rift.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "dimension_points", 1, max_value=5)
    ]
    dimension_rift.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 차원 절단
    dimension_cut = Skill("dimensionist_dimension_cut", "차원 절단", "차원 포인트 소비 공격")
    dimension_cut.effects = [
        DamageEffect(DamageType.HP, 1.1, gimmick_bonus={"field": "dimension_points", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "dimension_points", 1)
    ]
    dimension_cut.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 차원 이동
    dimension_shift = Skill("dimensionist_dimension_shift", "차원 이동", "회피 상승 + 차원 포인트")
    dimension_shift.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.6, duration=3),
        GimmickEffect(GimmickOperation.ADD, "dimension_points", 2, max_value=5)
    ]
    dimension_shift.costs = [MPCost(7)]
    dimension_shift.target_type = "self"
    dimension_shift.cooldown = 3

    # 4. 차원 문
    dimension_gate = Skill("dimensionist_dimension_gate", "차원 문", "차원 2포인트 소비, 광역 공격")
    dimension_gate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "dimension_points", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "dimension_points", 2)
    ]
    dimension_gate.costs = [MPCost(9), StackCost("dimension_points", 2)]
    dimension_gate.cooldown = 3
    dimension_gate.is_aoe = True

    # 5. 차원 왜곡
    dimension_warp = Skill("dimensionist_dimension_warp", "차원 왜곡", "차원 3포인트 소비, 대공격")
    dimension_warp.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "dimension_points", "multiplier": 0.4}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "dimension_points", 3)
    ]
    dimension_warp.costs = [MPCost(11), StackCost("dimension_points", 3)]
    dimension_warp.cooldown = 4

    # 6. 평행 세계
    parallel_world = Skill("dimensionist_parallel_world", "평행 세계", "차원 최대 회복")
    parallel_world.effects = [
        GimmickEffect(GimmickOperation.SET, "dimension_points", 5),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3)
    ]
    parallel_world.costs = [MPCost(10)]
    parallel_world.target_type = "self"
    parallel_world.cooldown = 5

    # 7. 차원 붕괴
    dimension_collapse = Skill("dimensionist_dimension_collapse", "차원 붕괴", "차원 4포인트 소비, 광역 붕괴")
    dimension_collapse.effects = [
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "dimension_points", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "dimension_points", 4)
    ]
    dimension_collapse.costs = [MPCost(14), StackCost("dimension_points", 4)]
    dimension_collapse.cooldown = 5
    dimension_collapse.is_aoe = True

    # 8. 차원의 지배자
    dimension_master = Skill("dimensionist_dimension_master", "차원의 지배자", "차원 5포인트 소비, 절대 공격")
    dimension_master.effects = [
        DamageEffect(DamageType.BRV_HP, 2.8, gimmick_bonus={"field": "dimension_points", "multiplier": 0.6}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "dimension_points", 5)
    ]
    dimension_master.costs = [MPCost(16), StackCost("dimension_points", 5)]
    dimension_master.cooldown = 6

    # 9. 궁극기: 차원 파괴
    ultimate = Skill("dimensionist_ultimate", "차원 파괴", "모든 차원을 파괴")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "dimension_points", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "dimension_points", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.0, stat_type="magical"),
        BuffEffect(BuffType.EVASION_UP, 0.8, duration=4),
        GimmickEffect(GimmickOperation.SET, "dimension_points", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("dimension_points", 1)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    ultimate.cooldown = 10

    return [dimension_rift, dimension_cut, dimension_shift, dimension_gate, dimension_warp,
            parallel_world, dimension_collapse, dimension_master, ultimate]

def register_dimensionist_skills(skill_manager):
    """차원술사 스킬 등록"""
    skills = create_dimensionist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
