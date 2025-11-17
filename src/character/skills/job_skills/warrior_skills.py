"""Warrior Skills - 전사 스킬 (6단계 스탠스 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_warrior_skills():
    """전사 10개 스킬 생성 (6-stance system)"""

    skills = []

    # 1. 기본 BRV: 강타
    power_strike = Skill("warrior_power_strike", "강타", "현재 스탠스 유지")
    power_strike.effects = [
        DamageEffect(DamageType.BRV, 1.6)
    ]
    power_strike.costs = []  # 기본 공격은 MP 소모 없음
    power_strike.sfx = "618"
    power_strike.metadata = {"basic_attack": True}
    skills.append(power_strike)

    # 2. 기본 HP: 방패 강타
    shield_bash = Skill("warrior_shield_bash", "방패 강타", "HP 공격")
    shield_bash.effects = [
        DamageEffect(DamageType.HP, 1.1)
    ]
    shield_bash.costs = []  # 기본 공격은 MP 소모 없음
    shield_bash.sfx = "625"
    shield_bash.metadata = {"basic_attack": True}
    skills.append(shield_bash)

    # 3. 공격 자세
    attack_stance = Skill("warrior_attack_stance", "공격 자세", "공격력 상승 자세")
    attack_stance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 1)  # 1=attack
    ]
    attack_stance.costs = [MPCost(4)]
    attack_stance.target_type = "self"
    # attack_stance.cooldown = 2  # 쿨다운 시스템 제거됨
    attack_stance.sfx = "632"
    attack_stance.metadata = {"stance": "attack", "buff": True}
    skills.append(attack_stance)

    # 4. 방어 자세
    defensive_stance = Skill("warrior_defensive_stance", "방어 자세", "방어력 상승 자세")
    defensive_stance.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 2)  # 2=defense
    ]
    defensive_stance.costs = [MPCost(4)]
    defensive_stance.target_type = "self"
    # defensive_stance.cooldown = 2  # 쿨다운 시스템 제거됨
    defensive_stance.sfx = "639"
    defensive_stance.metadata = {"stance": "defense", "buff": True}
    skills.append(defensive_stance)

    # 5. 광전사 자세
    berserker_rage = Skill("warrior_berserker_rage", "광전사 자세", "극한의 공격력")
    berserker_rage.effects = [
        DamageEffect(DamageType.BRV, 2.0),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 4)  # 4=berserker
    ]
    berserker_rage.costs = [MPCost(8)]
    berserker_rage.target_type = "self"
    # berserker_rage.cooldown = 3  # 쿨다운 시스템 제거됨
    berserker_rage.sfx = "646"
    berserker_rage.metadata = {"stance": "berserker", "buff": True, "damage": True}
    skills.append(berserker_rage)

    # 6. 수호자 자세
    guardian_stance = Skill("warrior_guardian_stance", "수호자 자세", "절대 방어")
    guardian_stance.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 5)  # 5=guardian
    ]
    guardian_stance.costs = [MPCost(8)]
    guardian_stance.target_type = "self"
    # guardian_stance.cooldown = 3  # 쿨다운 시스템 제거됨
    guardian_stance.sfx = "653"
    guardian_stance.metadata = {"stance": "guardian", "buff": True}
    skills.append(guardian_stance)

    # 7. 속도 자세
    speed_stance = Skill("warrior_speed_stance", "속도 자세", "속도 및 ATB 상승")
    speed_stance.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.SET, "current_stance", 6)  # 6=speed
    ]
    speed_stance.costs = [MPCost(6)]
    speed_stance.target_type = "self"
    # speed_stance.cooldown = 2  # 쿨다운 시스템 제거됨
    speed_stance.sfx = "660"
    speed_stance.metadata = {"stance": "speed", "buff": True}
    skills.append(speed_stance)

    # 8. 전쟁의 함성
    war_cry = Skill("warrior_war_cry", "전쟁의 함성", "적 약화 + 파티 강화")
    war_cry.effects = [
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=3),
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3)
    ]
    war_cry.costs = [MPCost(12)]
    # war_cry.cooldown = 4  # 쿨다운 시스템 제거됨
    war_cry.is_aoe = True
    war_cry.sfx = "667"
    war_cry.metadata = {"buff": True, "debuff": True, "aoe": True}
    skills.append(war_cry)

    # 9. 격노의 일격 (NEW - 10번째 스킬)
    furious_strike = Skill("warrior_furious_strike", "격노의 일격", "스탠스 기반 강력한 공격")
    furious_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 2.6),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.SET, "current_stance", 1)  # 1=attack
    ]
    furious_strike.costs = [MPCost(18)]
    # furious_strike.cooldown = 5  # 쿨다운 시스템 제거됨
    furious_strike.sfx = "674"
    furious_strike.metadata = {"stance_based": True, "high_damage": True}
    skills.append(furious_strike)

    # 10. 궁극기: 완전체 각성
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
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = "681"
    ultimate.metadata = {"ultimate": True, "all_stance_fusion": True, "party_buff": True}
    skills.append(ultimate)

    return skills

def register_warrior_skills(skill_manager):
    """전사 스킬 등록"""
    skills = create_warrior_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
