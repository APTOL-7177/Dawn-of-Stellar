"""Time Mage Skills - 시간술사 스킬 (시간 조작 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_time_mage_skills():
    """시간술사 9개 스킬 생성"""

    # 1. 기본 BRV: 시간 가속
    time_accel = Skill("time_mage_time_accel", "시간 가속", "시간 포인트 획득")
    time_accel.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "time_points", 1, max_value=6)
    ]
    time_accel.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 시간 충격
    time_shock = Skill("time_mage_time_shock", "시간 충격", "시간 포인트 소비 공격")
    time_shock.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "time_points", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "time_points", 1)
    ]
    time_shock.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 헤이스트
    haste = Skill("time_mage_haste", "헤이스트", "아군 속도 대폭 상승")
    haste.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.6, duration=4),
        GimmickEffect(GimmickOperation.ADD, "time_points", 1, max_value=6)
    ]
    haste.costs = [MPCost(8)]
    haste.target_type = "ally"
    haste.cooldown = 3

    # 4. 슬로우
    slow = Skill("time_mage_slow", "슬로우", "적 속도 감소")
    slow.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.4, duration=4),
        GimmickEffect(GimmickOperation.ADD, "time_points", 1, max_value=6)
    ]
    slow.costs = [MPCost(6)]
    slow.cooldown = 2

    # 5. 시간 역행
    time_rewind = Skill("time_mage_time_rewind", "시간 역행", "시간 2포인트 소비, 회복")
    time_rewind.effects = [
        GimmickEffect(GimmickOperation.CONSUME, "time_points", 2),
        BuffEffect(BuffType.REGEN, 0.3, duration=3)
    ]
    time_rewind.costs = [MPCost(9), StackCost("time_points", 2)]
    time_rewind.target_type = "ally"
    time_rewind.cooldown = 4

    # 6. 시간 정지
    time_stop = Skill("time_mage_time_stop", "시간 정지", "시간 3포인트 소비, 적 스턴")
    time_stop.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "time_points", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "time_points", 3)
    ]
    time_stop.costs = [MPCost(11), StackCost("time_points", 3)]
    time_stop.cooldown = 5

    # 7. 미래 예지
    future_sight = Skill("time_mage_future_sight", "미래 예지", "시간 4포인트 소비, 회피 상승")
    future_sight.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.7, duration=3),
        BuffEffect(BuffType.ACCURACY_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "time_points", 4)
    ]
    future_sight.costs = [MPCost(10), StackCost("time_points", 4)]
    future_sight.target_type = "self"
    future_sight.cooldown = 5

    # 8. 시간 왜곡
    time_warp = Skill("time_mage_time_warp", "시간 왜곡", "시간 5포인트 소비, 차원 왜곡 공격")
    time_warp.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "time_points", "multiplier": 0.5}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "time_points", 5)
    ]
    time_warp.costs = [MPCost(15), StackCost("time_points", 5)]
    time_warp.cooldown = 6
    time_warp.is_aoe = True

    # 9. 궁극기: 시간의 지배자
    ultimate = Skill("time_mage_ultimate", "시간의 지배자", "모든 시간을 지배")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "time_points", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "time_points", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.5, gimmick_bonus={"field": "time_points", "multiplier": 0.6}, stat_type="magical"),
        BuffEffect(BuffType.SPEED_UP, 0.8, duration=5),
        GimmickEffect(GimmickOperation.SET, "time_points", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("time_points", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10

    return [time_accel, time_shock, haste, slow, time_rewind,
            time_stop, future_sight, time_warp, ultimate]

def register_time_mage_skills(skill_manager):
    """시간술사 스킬 등록"""
    skills = create_time_mage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
