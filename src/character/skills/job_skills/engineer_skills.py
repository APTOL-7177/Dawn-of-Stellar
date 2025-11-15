"""Engineer Skills - 기계공학자 스킬 (기계 배치 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_engineer_skills():
    """기계공학자 9개 스킬 생성"""

    # 1. 기본 BRV: 기계 부품 조립
    assemble_parts = Skill("engineer_assemble_parts", "기계 부품 조립", "기계 부품 획득")
    assemble_parts.effects = [
        DamageEffect(DamageType.BRV, 1.3),
        GimmickEffect(GimmickOperation.ADD, "machine_parts", 1, max_value=5)
    ]
    assemble_parts.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 기계 공격
    machine_attack = Skill("engineer_machine_attack", "기계 공격", "기계 부품 소비 공격")
    machine_attack.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "machine_parts", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "machine_parts", 1)
    ]
    machine_attack.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 포탑 설치
    turret_deploy = Skill("engineer_turret_deploy", "포탑 설치", "부품 2개 소비, 포탑 배치")
    turret_deploy.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "machine_parts", "multiplier": 0.15}),
        GimmickEffect(GimmickOperation.CONSUME, "machine_parts", 2)
    ]
    turret_deploy.costs = [MPCost(7), StackCost("machine_parts", 2)]
    turret_deploy.cooldown = 2

    # 4. 수리 드론
    repair_drone = Skill("engineer_repair_drone", "수리 드론", "부품 2개 소비, 회복 기계")
    repair_drone.effects = [
        GimmickEffect(GimmickOperation.CONSUME, "machine_parts", 2),
        BuffEffect(BuffType.REGEN, 0.25, duration=4)
    ]
    repair_drone.costs = [MPCost(8), StackCost("machine_parts", 2)]
    repair_drone.target_type = "ally"
    repair_drone.cooldown = 3

    # 5. 방어막 생성기
    shield_generator = Skill("engineer_shield_generator", "방어막 생성기", "부품 3개 소비, 방어막")
    shield_generator.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "machine_parts", 3)
    ]
    shield_generator.costs = [MPCost(9), StackCost("machine_parts", 3)]
    shield_generator.target_type = "ally"
    shield_generator.cooldown = 4

    # 6. 기계 전개
    machine_deploy = Skill("engineer_machine_deploy", "기계 전개", "부품 최대 회복")
    machine_deploy.effects = [
        GimmickEffect(GimmickOperation.SET, "machine_parts", 5),
        BuffEffect(BuffType.ACCURACY_UP, 0.3, duration=3)
    ]
    machine_deploy.costs = [MPCost(10)]
    machine_deploy.target_type = "self"
    machine_deploy.cooldown = 5

    # 7. 폭발 드론
    explosive_drone = Skill("engineer_explosive_drone", "폭발 드론", "부품 4개 소비, 자폭 공격")
    explosive_drone.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "machine_parts", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "machine_parts", 4)
    ]
    explosive_drone.costs = [MPCost(12), StackCost("machine_parts", 4)]
    explosive_drone.cooldown = 4
    explosive_drone.is_aoe = True

    # 8. 거대 로봇
    giant_robot = Skill("engineer_giant_robot", "거대 로봇", "부품 5개 소비, 로봇 소환")
    giant_robot.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "machine_parts", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 1.8),
        GimmickEffect(GimmickOperation.CONSUME, "machine_parts", 5)
    ]
    giant_robot.costs = [MPCost(15), StackCost("machine_parts", 5)]
    giant_robot.cooldown = 6

    # 9. 궁극기: 기계군단
    ultimate = Skill("engineer_ultimate", "기계군단", "모든 기계 총동원")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "machine_parts", "multiplier": 0.3}),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "machine_parts", "multiplier": 0.3}),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "machine_parts", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 2.5),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.SET, "machine_parts", 0)
    ]
    ultimate.costs = [MPCost(22), StackCost("machine_parts", 1)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    ultimate.cooldown = 10

    return [assemble_parts, machine_attack, turret_deploy, repair_drone, shield_generator,
            machine_deploy, explosive_drone, giant_robot, ultimate]

def register_engineer_skills(skill_manager):
    """기계공학자 스킬 등록"""
    skills = create_engineer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
