"""Engineer Skills - 기계공학자 스킬 (포탑 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_engineer_skills():
    """기계공학자 스킬 생성 (포탑 시스템)"""
    skills = []

    # ============================================================
    # 기본 공격 (열 증가)
    # ============================================================

    # 1. 기본 BRV: 포탑 사격
    turret_shot = Skill("engineer_turret_shot", "포탑 사격", "BRV 피해, 열 +2")
    turret_shot.effects = [
        DamageEffect(DamageType.BRV, 1.4),
        GimmickEffect(GimmickOperation.ADD, "heat", 2, max_value=100)
    ]
    turret_shot.costs = []  # 기본 공격은 MP 소모 없음
    turret_shot.sfx = ("combat", "attack_physical")
    turret_shot.metadata = {"basic_attack": True, "heat_change": 2}
    skills.append(turret_shot)

    # 2. 기본 HP: 로켓 펀치
    rocket_punch = Skill("engineer_rocket_punch", "로켓 펀치", "HP 피해, 열 +5")
    rocket_punch.effects = [
        DamageEffect(DamageType.HP, 1.2),
        GimmickEffect(GimmickOperation.ADD, "heat", 5, max_value=100)
    ]
    rocket_punch.costs = []  # 기본 공격은 MP 소모 없음
    rocket_punch.sfx = ("combat", "damage_high")
    rocket_punch.metadata = {"basic_attack": True, "heat_change": 5}
    skills.append(rocket_punch)

    # ============================================================
    # 포탑 설치 스킬들
    # ============================================================

    # 3. 일반 포탑 설치
    deploy_turret = Skill("engineer_deploy_turret", "일반 포탑 설치", "포탑 +1 (턴당 열 +2, HP 공격 0.3배)")
    deploy_turret.effects = [
        GimmickEffect(GimmickOperation.ADD, "turret_count", 1, max_value=999)
    ]
    deploy_turret.costs = []  # MP 0
    deploy_turret.target_type = "self"
    deploy_turret.sfx = ("skill", "summon")
    deploy_turret.metadata = {
        "turret_type": "normal",
        "turret_damage": 0.3
    }
    skills.append(deploy_turret)

    # 2. 화염 포탑 설치
    deploy_fire_turret = Skill("engineer_deploy_fire_turret", "화염 포탑 설치", "포탑 +1 (HP 1.2배, 30% 화상)")
    deploy_fire_turret.effects = [
        GimmickEffect(GimmickOperation.ADD, "turret_count", 1, max_value=999),
        GimmickEffect(GimmickOperation.ADD, "fire_turret_count", 1, max_value=999)
    ]
    deploy_fire_turret.costs = [MPCost(6)]
    deploy_fire_turret.target_type = "self"
    deploy_fire_turret.sfx = ("skill", "summon")
    deploy_fire_turret.metadata = {
        "turret_type": "fire",
        "turret_damage": 1.2,
        "burn_chance": 0.3
    }
    skills.append(deploy_fire_turret)

    # 3. 빙결 포탑 설치
    deploy_ice_turret = Skill("engineer_deploy_ice_turret", "빙결 포탑 설치", "포탑 +1 (HP 0.8배, 40% 속도 감소)")
    deploy_ice_turret.effects = [
        GimmickEffect(GimmickOperation.ADD, "turret_count", 1, max_value=999),
        GimmickEffect(GimmickOperation.ADD, "ice_turret_count", 1, max_value=999)
    ]
    deploy_ice_turret.costs = [MPCost(7)]
    deploy_ice_turret.target_type = "self"
    deploy_ice_turret.sfx = ("skill", "summon")
    deploy_ice_turret.metadata = {
        "turret_type": "ice",
        "turret_damage": 0.8,
        "slow_chance": 0.4
    }
    skills.append(deploy_ice_turret)

    # 4. 전기 포탑 설치
    deploy_thunder_turret = Skill("engineer_deploy_thunder_turret", "전기 포탑 설치", "포탑 +1 (HP 1.0배, 25% 마비)")
    deploy_thunder_turret.effects = [
        GimmickEffect(GimmickOperation.ADD, "turret_count", 1, max_value=999),
        GimmickEffect(GimmickOperation.ADD, "thunder_turret_count", 1, max_value=999)
    ]
    deploy_thunder_turret.costs = [MPCost(8)]
    deploy_thunder_turret.target_type = "self"
    deploy_thunder_turret.sfx = ("skill", "summon")
    deploy_thunder_turret.metadata = {
        "turret_type": "thunder",
        "turret_damage": 1.0,
        "paralyze_chance": 0.25
    }
    skills.append(deploy_thunder_turret)

    # 5. 폭발 포탑 설치
    deploy_explosive_turret = Skill("engineer_deploy_explosive_turret", "폭발 포탑 설치", "포탑 +1 (HP 1.5배, AOE 공격)")
    deploy_explosive_turret.effects = [
        GimmickEffect(GimmickOperation.ADD, "turret_count", 1, max_value=999),
        GimmickEffect(GimmickOperation.ADD, "explosive_turret_count", 1, max_value=999)
    ]
    deploy_explosive_turret.costs = [MPCost(10)]
    deploy_explosive_turret.target_type = "self"
    deploy_explosive_turret.sfx = ("skill", "summon")
    deploy_explosive_turret.metadata = {
        "turret_type": "explosive",
        "turret_damage": 1.5,
        "aoe": True
    }
    skills.append(deploy_explosive_turret)

    # 6. 치유 포탑 설치
    deploy_heal_turret = Skill("engineer_deploy_heal_turret", "치유 포탑 설치", "포탑 +1 (최저 HP 아군 공격력 30% 회복)")
    deploy_heal_turret.effects = [
        GimmickEffect(GimmickOperation.ADD, "turret_count", 1, max_value=999),
        GimmickEffect(GimmickOperation.ADD, "heal_turret_count", 1, max_value=999)
    ]
    deploy_heal_turret.costs = [MPCost(12)]
    deploy_heal_turret.target_type = "self"
    deploy_heal_turret.sfx = ("skill", "summon")
    deploy_heal_turret.metadata = {
        "turret_type": "heal",
        "heal_percent": 0.1
    }
    skills.append(deploy_heal_turret)

    # ============================================================
    # 냉각 스킬들
    # ============================================================

    # 7. 냉각 벤트
    cooling_vent = Skill("engineer_cooling_vent", "냉각 벤트", "열 -30")
    cooling_vent.effects = [
        GimmickEffect(GimmickOperation.ADD, "heat", -30, min_value=0)
    ]
    cooling_vent.costs = [MPCost(3)]
    cooling_vent.target_type = "self"
    cooling_vent.sfx = ("skill", "cast_complete")
    cooling_vent.metadata = {"heat_change": -30}
    skills.append(cooling_vent)

    # 8. 긴급 냉각
    emergency_cooling = Skill("engineer_emergency_cooling", "긴급 냉각", "열 -50, 포탑 1개 파괴")
    emergency_cooling.effects = [
        GimmickEffect(GimmickOperation.ADD, "heat", -50, min_value=0),
        GimmickEffect(GimmickOperation.ADD, "turret_count", -1, min_value=0)
    ]
    emergency_cooling.costs = [MPCost(5)]
    emergency_cooling.target_type = "self"
    emergency_cooling.sfx = ("skill", "cast_complete")
    emergency_cooling.metadata = {"heat_change": -50, "destroy_turret": 1}
    skills.append(emergency_cooling)

    # 9. 전체 냉각
    full_cooling = Skill("engineer_full_cooling", "전체 냉각", "열 -100, 모든 포탑 파괴")
    full_cooling.effects = [
        GimmickEffect(GimmickOperation.SET, "heat", 0),
        GimmickEffect(GimmickOperation.SET, "turret_count", 0),
        GimmickEffect(GimmickOperation.SET, "fire_turret_count", 0),
        GimmickEffect(GimmickOperation.SET, "ice_turret_count", 0),
        GimmickEffect(GimmickOperation.SET, "thunder_turret_count", 0),
        GimmickEffect(GimmickOperation.SET, "explosive_turret_count", 0),
        GimmickEffect(GimmickOperation.SET, "heal_turret_count", 0)
    ]
    full_cooling.costs = [MPCost(8)]
    full_cooling.target_type = "self"
    full_cooling.sfx = ("skill", "cast_complete")
    full_cooling.metadata = {"heat_change": -100, "destroy_all_turrets": True}
    skills.append(full_cooling)

    # ============================================================
    # 유틸리티 스킬
    # ============================================================

    # 10. 포탑 강화 (버프)
    turret_enhance = Skill("engineer_turret_enhance", "포탑 강화", "3턴간 포탑 데미지 +50%, 열 +10")
    turret_enhance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=3, target="self"),
        GimmickEffect(GimmickOperation.ADD, "heat", 10, max_value=100)
    ]
    turret_enhance.costs = [MPCost(9)]
    turret_enhance.target_type = "self"
    turret_enhance.sfx = ("character", "status_buff")
    turret_enhance.metadata = {"turret_enhance": True, "heat_change": 10}
    skills.append(turret_enhance)

    # 11. 궁극기: 메가 블래스터
    mega_blaster = Skill("engineer_mega_blaster", "메가 블래스터", "포탑 수 × HP 2.0배, 열 +60")
    mega_blaster.effects = [
        DamageEffect(DamageType.HP, 2.0, gimmick_bonus={"field": "turret_count", "multiplier": 1.0}),  # 포탑 1개당 +100% (2배씩 증가)
        GimmickEffect(GimmickOperation.ADD, "heat", 60, max_value=100)
    ]
    mega_blaster.costs = [MPCost(30)]
    mega_blaster.is_ultimate = True
    mega_blaster.cooldown = 15
    mega_blaster.sfx = ("skill", "limit_break")
    mega_blaster.metadata = {"heat_change": 60, "turret_scaling": True}
    skills.append(mega_blaster)

    # 팀워크 스킬
    teamwork = TeamworkSkill(
        "engineer_teamwork",
        "긴급 냉각 시스템",
        "열 -70 + 포탑 공격력 +100% (3턴)",
        gauge_cost=150
    )
    teamwork.effects = [
        GimmickEffect(GimmickOperation.ADD, "heat", -70, min_value=0),
        BuffEffect(BuffType.ATTACK_UP, 1.0, duration=3, target="self")
    ]
    teamwork.target_type = "self"
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "engineer": True}
    skills.append(teamwork)

    return skills

def register_engineer_skills(skill_manager):
    """기계공학자 스킬 등록"""
    skills = create_engineer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
