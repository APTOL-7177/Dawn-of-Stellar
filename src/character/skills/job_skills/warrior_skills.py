"""Warrior Skills - 전사 스킬 (6단계 스탠스 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_warrior_skills():
    """전사 9개 스킬 생성 (6-stance system)"""

    # 1. 기본 BRV: 강타
    power_strike = Skill("warrior_power_strike", "강타", "현재 스탠스 유지")
    power_strike.effects = [
        DamageEffect(DamageType.BRV, 1.6)
    ]
    power_strike.costs = []  # 기본 공격은 MP 소모 없음
    power_strike.sfx = ("combat", "attack_physical")

    # 2. 기본 HP: 방패 강타
    shield_bash = Skill("warrior_shield_bash", "방패 강타", "HP 공격")
    shield_bash.effects = [
        DamageEffect(DamageType.HP, 1.1)
    ]
    shield_bash.costs = []  # 기본 공격은 MP 소모 없음
    shield_bash.sfx = ("combat", "attack_physical")

    # 3. 공격 자세
    attack_stance = Skill("warrior_attack_stance", "공격 자세", "공격력 상승 자세")
    attack_stance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 1)  # 1=attack
    ]
    attack_stance.costs = []  # MP 소모 없음 (trait)
    attack_stance.target_type = "self"
    attack_stance.cooldown = 1
    attack_stance.sfx = ("character", "status_buff")

    # 4. 방어 자세
    defensive_stance = Skill("warrior_defensive_stance", "방어 자세", "방어력 상승 자세")
    defensive_stance.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 2)  # 2=defense
    ]
    defensive_stance.costs = []  # MP 소모 없음
    defensive_stance.target_type = "self"
    defensive_stance.cooldown = 1
    defensive_stance.sfx = ("skill", "protect")

    # 5. 광전사 자세
    berserker_rage = Skill("warrior_berserker_rage", "광전사 자세", "극한의 공격력")
    berserker_rage.effects = [
        DamageEffect(DamageType.BRV, 2.0),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 4)  # 4=berserker
    ]
    berserker_rage.costs = []
    berserker_rage.target_type = "self"
    berserker_rage.cooldown = 3
    berserker_rage.sfx = ("skill", "limit_break")

    # 6. 수호자 자세
    guardian_stance = Skill("warrior_guardian_stance", "수호자 자세", "절대 방어")
    guardian_stance.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 5)  # 5=guardian
    ]
    guardian_stance.costs = []
    guardian_stance.target_type = "self"
    guardian_stance.cooldown = 3
    guardian_stance.sfx = ("skill", "shell")

    # 7. 속도 자세
    speed_stance = Skill("warrior_speed_stance", "속도 자세", "속도 및 ATB 상승")
    speed_stance.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 6)  # 6=speed
    ]
    speed_stance.costs = []
    speed_stance.target_type = "self"
    speed_stance.cooldown = 2
    speed_stance.sfx = ("skill", "haste")

    # 8. 전쟁의 함성
    war_cry = Skill("warrior_war_cry", "전쟁의 함성", "적 약화 + 파티 강화")
    war_cry.effects = [
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=3),
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3)
    ]
    war_cry.costs = [MPCost(9)]
    war_cry.cooldown = 4
    war_cry.is_aoe = True
    war_cry.sfx = ("character", "status_buff")

    # 9. 궁극기: 완전체 각성
    ultimate = Skill("warrior_ultimate", "완전체 각성", "모든 스탠스의 힘 융합")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5),
        DamageEffect(DamageType.BRV, 2.5),
        DamageEffect(DamageType.HP, 2.8),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "current_stance", 0)  # 0=balanced
    ]
    ultimate.costs = [MPCost(22)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    ultimate.sfx = ("skill", "limit_break")

    return [power_strike, shield_bash, attack_stance, defensive_stance, berserker_rage,
            guardian_stance, speed_stance, war_cry, ultimate]

def register_warrior_skills(skill_manager):
    """전사 스킬 등록"""
    skills = create_warrior_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
