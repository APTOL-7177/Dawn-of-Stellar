"""Vampire Skills - 흡혈귀 스킬 (갈증 관리 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_vampire_skills():
    """흡혈귀 10개 스킬 생성 (갈증 관리 시스템)"""

    # 1. 기본 BRV: 흡혈 물기 (갈증 -5, 소량 감소)
    vampiric_bite = Skill("vampiric_bite", "흡혈 물기", "적을 물어 피를 빨아 갈증 감소")
    vampiric_bite.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "thirst", -5, min_value=0)  # 갈증 -5
    ]
    vampiric_bite.costs = []  # 기본 공격은 MP 소모 없음
    vampiric_bite.sfx = "032"  # FFVII bite/drain sound
    vampiric_bite.metadata = {"thirst_reduction": -5, "lifesteal": 0.2}

    # 2. 기본 HP: 피의 흡수 (갈증 -20, 대량 감소)
    blood_drain = Skill("vampiric_blood_drain", "피의 흡수", "적의 생명력을 빨아들여 갈증 대폭 감소")
    blood_drain.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "thirst", -20, min_value=0)  # 갈증 -20
    ]
    blood_drain.costs = []  # 기본 공격은 MP 소모 없음
    blood_drain.sfx = "048"  # FFVII drain sound
    blood_drain.metadata = {"thirst_reduction": -20, "lifesteal": 0.4}

    # 3. 피의 창 (갈증 구간에 따라 위력 증가)
    blood_lance = Skill("vampire_blood_lance", "피의 창", "갈증에 비례한 강력한 공격")
    blood_lance.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="magical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.02}),  # 갈증 1당 +2% 피해
        GimmickEffect(GimmickOperation.ADD, "thirst", -10, min_value=0)  # 갈증 -10
    ]
    blood_lance.costs = []
    blood_lance.sfx = "108"  # FFVII lance/spear sound
    # blood_lance.cooldown = 2  # 쿨다운 시스템 제거됨
    blood_lance.metadata = {"thirst_scaling": True}

    # 4. 기본 HP: 갈증 폭발 (의도적으로 갈증 증가, 강력한 공격)
    thirst_surge = Skill("vampire_thirst_surge", "갈증 폭발", "갈증을 폭발시켜 강력한 공격")
    thirst_surge.effects = [
        DamageEffect(DamageType.BRV_HP, 2.8, stat_type="physical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.025}),
        GimmickEffect(GimmickOperation.ADD, "thirst", 30, max_value=100)  # 갈증 +30 (위험!)
    ]
    thirst_surge.costs = []  # 기본 공격은 MP 소모 없음
    thirst_surge.sfx = "146"  # FFVII explosion sound
    thirst_surge.metadata = {"basic_attack": True, "thirst_increase": True, "high_risk": True}

    # 5. 박쥐 떼 (광역 공격 + 갈증 감소)
    bat_swarm = Skill("vampire_bat_swarm", "박쥐 떼", "박쥐 떼로 적 전체 공격, 갈증 감소")
    bat_swarm.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "thirst", -15, min_value=0)  # 갈증 -15
    ]
    bat_swarm.costs = []
    bat_swarm.target_type = "all_enemies"
    bat_swarm.is_aoe = True
    bat_swarm.sfx = "182"  # FFVII swarm/flutter sound
    # bat_swarm.cooldown = 4  # 쿨다운 시스템 제거됨
    bat_swarm.metadata = {"aoe": True, "thirst_reduction": -15}

    # 6. 안개 형상 (회피 증가 + 갈증 증가)
    mist_form = Skill("vampire_mist_form", "안개 형상", "안개가 되어 회피 증가, 갈증 상승")
    mist_form.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.6, duration=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "thirst", 10, max_value=100)  # 갈증 +10 (변신 비용)
    ]
    mist_form.costs = [MPCost(4)]
    mist_form.target_type = "self"
    mist_form.sfx = "199"  # FFVII mist/fog sound
    # mist_form.cooldown = 5  # 쿨다운 시스템 제거됨
    mist_form.metadata = {"evasion_buff": True}

    # 7. 피의 광란 준비 (갈증을 극심 구간으로)
    prepare_frenzy = Skill("vampire_prepare_frenzy", "광란 준비", "갈증을 70으로 조정 (극심 구간)")
    prepare_frenzy.effects = [
        GimmickEffect(GimmickOperation.SET, "thirst", 70),  # 갈증을 70으로 설정 (극심 구간)
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3)
    ]
    prepare_frenzy.costs = [MPCost(9)]
    prepare_frenzy.target_type = "self"
    prepare_frenzy.sfx = "217"  # FFVII power-up sound
    # prepare_frenzy.cooldown = 6  # 쿨다운 시스템 제거됨
    prepare_frenzy.metadata = {"thirst_control": True, "optimal_thirst": 70}

    # 8. 생명력 착취 (강력한 HP 흡수, 갈증 대폭 감소)
    life_tap = Skill("vampire_life_tap", "생명력 착취", "적의 생명력을 대량 흡수, 갈증 -30")
    life_tap.effects = [
        DamageEffect(DamageType.HP, 2.5, stat_type="magical"),
        HealEffect(percentage=0.25),  # HP 회복
        GimmickEffect(GimmickOperation.ADD, "thirst", -30, min_value=0)  # 갈증 -30
    ]
    life_tap.costs = [MPCost(9)]
    life_tap.sfx = "261"  # FFVII drain/absorb sound
    # life_tap.cooldown = 4  # 쿨다운 시스템 제거됨
    life_tap.metadata = {"major_drain": True, "thirst_reduction": -30}

    # 9. 만족 상태로 (갈증을 0으로 리셋)
    blood_satiation = Skill("vampire_blood_satiation", "혈액 만족", "갈증을 0으로 리셋 (만족 상태)")
    blood_satiation.effects = [
        GimmickEffect(GimmickOperation.SET, "thirst", 0),  # 갈증 0으로 리셋
        HealEffect(percentage=0.20),  # HP 20% 회복
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=3)
    ]
    blood_satiation.costs = [MPCost(10)]
    blood_satiation.target_type = "self"
    blood_satiation.sfx = "300"  # FFVII restoration sound
    # blood_satiation.cooldown = 7  # 쿨다운 시스템 제거됨
    blood_satiation.metadata = {"thirst_reset": True, "recovery": True}

    # 10. 궁극기: 혈족의 군주 (극한 갈증 활용)
    ultimate = Skill("vampire_ultimate", "혈족의 군주", "극한 갈증으로 압도적인 힘 발휘")
    ultimate.effects = [
        # 현재 갈증에 비례한 극대 피해
        DamageEffect(DamageType.BRV, 3.5, stat_type="physical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.04}),
        DamageEffect(DamageType.HP, 4.0, stat_type="magical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.03}),
        HealEffect(percentage=0.40),  # HP 40% 회복
        BuffEffect(BuffType.ATTACK_UP, 1.0, duration=4),  # 공격력 +100%
        GimmickEffect(GimmickOperation.SET, "thirst", 50)  # 궁극기 후 갈증 50으로 조정
    ]
    ultimate.costs = [MPCost(15)]
    ultimate.is_ultimate = True
    ultimate.sfx = "687"  # FFVII ultimate sound
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.target_type = "single"
    ultimate.metadata = {"ultimate": True, "thirst_scaling_max": True}

    return [vampiric_bite, blood_drain, blood_lance, thirst_surge, bat_swarm,
            mist_form, prepare_frenzy, life_tap, blood_satiation, ultimate]

def register_vampire_skills(skill_manager):
    """흡혈귀 스킬 등록"""
    skills = create_vampire_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
