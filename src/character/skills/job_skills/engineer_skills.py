"""Engineer Skills - 기계공학자 스킬 (열 관리 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_engineer_skills():
    """기계공학자 10개 스킬 생성 (열 관리 시스템)"""

    # 1. 기본 BRV: 포탑 사격
    turret_shot = Skill("engineer_turret_shot", "포탑 사격", "기본 공격, 열 +15")
    turret_shot.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "heat", 15, max_value=100)
    ]
    turret_shot.costs = []  # 기본 공격은 MP 소모 없음
    turret_shot.metadata = {"heat_change": 15}

    # 2. 기본 HP: 로켓 펀치
    rocket_punch = Skill("engineer_rocket_punch", "로켓 펀치", "단일 강타, 열 +25")
    rocket_punch.effects = [
        DamageEffect(DamageType.HP, 1.5),
        GimmickEffect(GimmickOperation.ADD, "heat", 25, max_value=100)
    ]
    rocket_punch.costs = []  # 기본 공격은 MP 소모 없음
    rocket_punch.metadata = {"heat_change": 25}

    # 3. 과열 포격 (위험 구간에서 강력함)
    overload_blast = Skill("engineer_overload_blast", "과열 포격",
                          "위험 구간(80+)에서 배율 3.5, 열 +35")
    overload_blast.effects = [
        DamageEffect(DamageType.BRV, 2.5,
                    conditional_bonus={"condition": "danger_zone", "multiplier": 1.4}),
        GimmickEffect(GimmickOperation.ADD, "heat", 35, max_value=100)
    ]
    overload_blast.costs = []
    overload_blast.metadata = {"heat_change": 35, "danger_zone_bonus": True}

    # 4. EMP 폭발 (광역 공격)
    emp_explosion = Skill("engineer_emp_explosion", "EMP 폭발",
                         "광역 공격, 기계 무력화, 열 +40")
    emp_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0),
        GimmickEffect(GimmickOperation.ADD, "heat", 40, max_value=100)
    ]
    emp_explosion.costs = [MPCost(9)]
    emp_explosion.target_type = "all_enemies"
    emp_explosion.is_aoe = True
    emp_explosion.metadata = {"heat_change": 40}

    # 5. 냉각 벤트 (열 감소 + 방어 버프)
    cooling_vent = Skill("engineer_cooling_vent", "냉각 벤트",
                        "열 -30, 방어력 +20% 1턴")
    cooling_vent.effects = [
        GimmickEffect(GimmickOperation.ADD, "heat", -30, min_value=0),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=1)
    ]
    cooling_vent.costs = [MPCost(5)]
    cooling_vent.target_type = "self"
    cooling_vent.metadata = {"heat_change": -30}

    # 6. 오버클럭 모드 (위험 구간 패널티 제거)
    overclock_mode = Skill("engineer_overclock_mode", "오버클럭 모드",
                          "3턴간 위험 구간 패널티 제거, 열 +20")
    overclock_mode.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=3),
        GimmickEffect(GimmickOperation.ADD, "heat", 20, max_value=100)
    ]
    overclock_mode.costs = [MPCost(11)]
    overclock_mode.target_type = "self"
    # overclock_mode.cooldown = 5  # 쿨다운 시스템 제거됨
    overclock_mode.metadata = {"heat_change": 20, "overclock": True}

    # 7. 긴급 수리 (회복 + 열 감소)
    emergency_repair = Skill("engineer_emergency_repair", "긴급 수리",
                            "HP 30% 회복, 열 -40")
    emergency_repair.effects = [
        HealEffect(percentage=0.3),
        GimmickEffect(GimmickOperation.ADD, "heat", -40, min_value=0)
    ]
    emergency_repair.costs = [MPCost(9)]
    emergency_repair.target_type = "self"
    # emergency_repair.cooldown = 4  # 쿨다운 시스템 제거됨
    emergency_repair.metadata = {"heat_change": -40}

    # 8. 보호막 생성기 (방어막 생성)
    shield_generator = Skill("engineer_shield_generator", "보호막 생성기",
                            "3턴간 피해 흡수 방어막, 열 +15")
    shield_generator.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "heat", 15, max_value=100)
    ]
    shield_generator.costs = [MPCost(6)]
    shield_generator.target_type = "self"
    # shield_generator.cooldown = 4  # 쿨다운 시스템 제거됨
    shield_generator.metadata = {"heat_change": 15, "shield": True}

    # 9. 드론 배치 (지원 공격)
    deploy_drone = Skill("engineer_deploy_drone", "드론 배치",
                        "지원 드론 배치, 2턴간 공격력 +25%")
    deploy_drone.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=2),
        GimmickEffect(GimmickOperation.ADD, "heat", 10, max_value=100)
    ]
    deploy_drone.costs = [MPCost(6)]
    deploy_drone.target_type = "self"
    # deploy_drone.cooldown = 3  # 쿨다운 시스템 제거됨
    deploy_drone.metadata = {"heat_change": 10, "drone": True}

    # 10. 궁극기: 메가 블래스터 (현재 열에 비례한 피해)
    mega_blaster = Skill("engineer_mega_blaster", "메가 블래스터",
                        "현재 열에 비례한 대량 피해, 열 +60")
    mega_blaster.effects = [
        DamageEffect(DamageType.BRV, 2.5,
                    gimmick_bonus={"field": "heat", "multiplier": 0.02}),  # 열 1당 +2% 피해
        DamageEffect(DamageType.HP, 2.0,
                    gimmick_bonus={"field": "heat", "multiplier": 0.015}),  # 열 1당 +1.5% 피해
        GimmickEffect(GimmickOperation.ADD, "heat", 60, max_value=100)
    ]
    mega_blaster.costs = [MPCost(15)]
    mega_blaster.is_ultimate = True
    # mega_blaster.cooldown = 8  # 쿨다운 시스템 제거됨
    mega_blaster.metadata = {"heat_change": 60, "heat_scaling": True}

    return [turret_shot, rocket_punch, overload_blast, emp_explosion,
            cooling_vent, overclock_mode, emergency_repair, shield_generator,
            deploy_drone, mega_blaster]

def register_engineer_skills(skill_manager):
    """기계공학자 스킬 등록"""
    skills = create_engineer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
