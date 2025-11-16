"""Vampire Skills - 흡혈귀 스킬 (혈액 저장고 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.lifesteal_effect import LifestealEffect
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_vampire_skills():
    """흡혈귀 10개 스킬 - 혈액 저장고 시스템"""

    skills = []

    # 1. 기본 BRV 공격: 흡혈 물기 (혈액 획득)
    vampiric_bite = Skill("vampiric_bite", "흡혈 물기", "적을 물어 BRV 데미지와 혈액 획득")
    vampiric_bite.effects = [
        DamageEffect(DamageType.BRV, 1.4),
        LifestealEffect(lifesteal_percent=0.25),
        GimmickEffect(GimmickOperation.ADD, "blood", 10, max_value=100)
    ]
    vampiric_bite.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(vampiric_bite)

    # 2. 기본 HP 공격: 피의 흡수 (혈액 획득)
    blood_drain = Skill("blood_drain", "피의 흡수", "적의 생명력을 흡수하여 HP 데미지와 혈액 획득")
    blood_drain.effects = [
        DamageEffect(DamageType.HP, 1.0),
        LifestealEffect(lifesteal_percent=0.4),
        GimmickEffect(GimmickOperation.ADD, "blood", 15, max_value=100)
    ]
    blood_drain.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(blood_drain)

    # 3. 피의 창 (혈액 소비 강력 공격)
    blood_lance = Skill("blood_lance", "피의 창", "혈액을 창으로 만들어 강력한 관통 공격")
    blood_lance.effects = [
        DamageEffect(DamageType.HP, 1.8, gimmick_bonus={"field": "blood", "multiplier": 0.02}),
        LifestealEffect(lifesteal_percent=0.35),
        GimmickEffect(GimmickOperation.CONSUME, "blood", 20)
    ]
    blood_lance.costs = [MPCost(5), StackCost("blood", 20)]
    blood_lance.cooldown = 2
    skills.append(blood_lance)

    # 4. 박쥐 떼 (광역 BRV 공격, 혈액 획득)
    bat_swarm = Skill("bat_swarm", "박쥐 떼", "수많은 박쥐로 적들을 공격하고 혈액 획득")
    bat_swarm.effects = [
        DamageEffect(DamageType.BRV, 1.2),
        DamageEffect(DamageType.BRV, 1.2),
        LifestealEffect(lifesteal_percent=0.2),
        GimmickEffect(GimmickOperation.ADD, "blood", 25, max_value=100)
    ]
    bat_swarm.costs = [MPCost(8)]
    bat_swarm.target_type = "all_enemies"
    bat_swarm.cooldown = 3
    skills.append(bat_swarm)

    # 5. 피의 보호막 (혈액 소비 방어)
    blood_shield = Skill("blood_shield", "피의 보호막", "혈액으로 강력한 보호막 생성")
    blood_shield.effects = [
        ShieldEffect(base_amount=100, multiplier=0.5, stat_name="blood"),
        GimmickEffect(GimmickOperation.CONSUME, "blood", 30)
    ]
    blood_shield.costs = [MPCost(10), StackCost("blood", 30)]
    blood_shield.target_type = "self"
    blood_shield.cooldown = 4
    skills.append(blood_shield)

    # 6. 안개 형상 (회피 및 방어 증가)
    mist_form = Skill("mist_form", "안개 형상", "안개로 변신하여 회피율과 방어력 증가")
    mist_form.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=3),
        BuffEffect(BuffType.EVASION_UP, 0.4, duration=3),
        HealEffect(HealType.HP, percentage=0.15)
    ]
    mist_form.costs = [MPCost(12)]
    mist_form.target_type = "self"
    mist_form.cooldown = 5
    skills.append(mist_form)

    # 7. 피의 광란 (공격력 증가, 혈액 소비)
    blood_frenzy = Skill("blood_frenzy", "피의 광란", "혈액의 힘으로 광폭화하여 공격력 대폭 증가")
    blood_frenzy.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "blood", 40)
    ]
    blood_frenzy.costs = [MPCost(15), StackCost("blood", 40)]
    blood_frenzy.target_type = "self"
    blood_frenzy.cooldown = 5
    skills.append(blood_frenzy)

    # 8. 생명력 착취 (강력한 HP 흡수)
    life_tap = Skill("life_tap", "생명력 착취", "적의 생명력을 대량으로 빨아들임")
    life_tap.effects = [
        DamageEffect(DamageType.HP, 2.0, gimmick_bonus={"field": "blood", "multiplier": 0.015}),
        LifestealEffect(lifesteal_percent=0.8),
        GimmickEffect(GimmickOperation.CONSUME, "blood", 25)
    ]
    life_tap.costs = [MPCost(18), StackCost("blood", 25)]
    life_tap.cooldown = 4
    skills.append(life_tap)

    # 9. 진홍의 폭발 (광역 강력 공격)
    crimson_nova = Skill("crimson_nova", "진홍의 폭발", "혈액을 폭발시켜 모든 적에게 막대한 피해")
    crimson_nova.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "blood", "multiplier": 0.025}),
        LifestealEffect(lifesteal_percent=0.5),
        GimmickEffect(GimmickOperation.CONSUME, "blood", 50)
    ]
    crimson_nova.costs = [MPCost(22), StackCost("blood", 50)]
    crimson_nova.target_type = "all_enemies"
    crimson_nova.cooldown = 6
    skills.append(crimson_nova)

    # 10. 궁극기: 혈족의 군주
    blood_lord_ultimate = Skill("blood_lord_ultimate", "혈족의 군주", "흡혈귀 진조의 힘을 해방하여 압도적인 공격과 회복")
    blood_lord_ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0),
        DamageEffect(DamageType.HP, 4.0, gimmick_bonus={"field": "blood", "multiplier": 0.03}),
        LifestealEffect(lifesteal_percent=1.2),
        ShieldEffect(base_amount=200),
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        HealEffect(HealType.HP, percentage=0.4),
        GimmickEffect(GimmickOperation.SET, "blood", 100)
    ]
    blood_lord_ultimate.costs = [MPCost(30)]
    blood_lord_ultimate.is_ultimate = True
    blood_lord_ultimate.cooldown = 10
    skills.append(blood_lord_ultimate)

    return skills

def register_vampire_skills(skill_manager):
    skills = create_vampire_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
