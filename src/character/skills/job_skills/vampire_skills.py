"""Vampire Skills - 흡혈귀 스킬 (갈증 관리 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.effects.lifesteal_effect import LifestealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_vampire_skills():
    """흡혈귀 10개 스킬 생성 (갈증 관리 시스템)"""

    # 1. 기본 BRV: 흡혈 물기 (갈증 -5, 소량 감소)
    vampiric_bite = Skill("vampire_vampiric_bite", "흡혈 물기", "적을 물어 피를 빨아 갈증 감소")
    vampiric_bite.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "thirst", -5, min_value=0)  # 갈증 -5
    ]
    vampiric_bite.costs = []  # 기본 공격은 MP 소모 없음
    vampiric_bite.sfx = ("combat", "attack_physical")  # 흡혈 물기
    vampiric_bite.metadata = {"basic_attack": True, "thirst_reduction": -5, "lifesteal": 0.2}

    # 2. 기본 HP: 피의 흡수 (갈증 -20, 대량 감소)
    blood_drain = Skill("vampire_blood_drain", "피의 흡수", "적의 생명력을 빨아들여 갈증 대폭 감소")
    blood_drain.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "thirst", -20, min_value=0)  # 갈증 -20
    ]
    blood_drain.costs = []  # 기본 공격은 MP 소모 없음
    blood_drain.sfx = ("character", "hp_heal")  # 피의 흡수
    blood_drain.metadata = {"basic_attack": True, "thirst_reduction": -20, "lifesteal": 0.75}

    # 3. 피의 창 (갈증에 비례한 강력한 공격, 갈증 증가)
    blood_lance = Skill("vampire_blood_lance", "피의 창", "갈증에 비례한 강력한 공격, 갈증 증가")
    blood_lance.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="magical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.02}),  # 갈증 1당 +2% 피해
        GimmickEffect(GimmickOperation.ADD, "thirst", 15, max_value=100)  # 갈증 +15
    ]
    blood_lance.costs = [MPCost(4)]  # MP 소모 필요
    blood_lance.sfx = ("combat", "damage_high")  # 피의 창
    # blood_lance.cooldown = 2  # 쿨다운 시스템 제거됨
    blood_lance.metadata = {"thirst_scaling": True, "thirst_increase": True}

    # 4. 갈증 폭발 (의도적으로 갈증 증가, 강력한 공격)
    thirst_surge = Skill("vampire_thirst_surge", "갈증 폭발", "갈증을 폭발시켜 강력한 공격")
    thirst_surge.effects = [
        DamageEffect(DamageType.BRV_HP, 2.8, stat_type="physical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.025}),
        GimmickEffect(GimmickOperation.ADD, "thirst", 30, max_value=100)  # 갈증 +30 (위험!)
    ]
    thirst_surge.costs = [MPCost(6)]  # MP 소모 필요
    thirst_surge.sfx = ("skill", "cast_complete")  # 갈증 폭발
    thirst_surge.metadata = {"thirst_increase": True, "high_risk": True}

    # 5. 박쥐 떼 (광역 공격, 갈증 증가)
    bat_swarm = Skill("vampire_bat_swarm", "박쥐 떼", "박쥐 떼로 적 전체 공격, 갈증 증가")
    bat_swarm.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "thirst", 12, max_value=100)  # 갈증 +12
    ]
    bat_swarm.costs = [MPCost(5)]
    bat_swarm.target_type = "all_enemies"
    bat_swarm.is_aoe = True
    bat_swarm.sfx = ("skill", "summon")  # 박쥐 떼
    # bat_swarm.cooldown = 4  # 쿨다운 시스템 제거됨
    bat_swarm.metadata = {"aoe": True, "thirst_increase": True}

    # 6. 안개 형상 (회피 증가 + 갈증 증가)
    mist_form = Skill("vampire_mist_form", "안개 형상", "안개가 되어 회피 증가, 갈증 상승")
    mist_form.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.6, duration=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "thirst", 15, max_value=100)  # 갈증 +15 (변신 비용)
    ]
    mist_form.costs = [MPCost(4)]
    mist_form.target_type = "self"
    mist_form.sfx = ("combat", "dodge")  # 안개 형상
    # mist_form.cooldown = 5  # 쿨다운 시스템 제거됨
    mist_form.metadata = {"evasion_buff": True, "thirst_increase": True}

    # 7. 피의 광란 준비 (갈증 대폭 증가, 공격력 버프)
    prepare_frenzy = Skill("vampire_prepare_frenzy", "광란 준비", "갈증을 대폭 증가시켜 극심 구간으로")
    prepare_frenzy.effects = [
        GimmickEffect(GimmickOperation.ADD, "thirst", 40, max_value=100),  # 갈증 +40 (극심 구간으로)
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3)
    ]
    prepare_frenzy.costs = [MPCost(9)]
    prepare_frenzy.target_type = "self"
    prepare_frenzy.sfx = ("character", "status_buff")  # 광란 준비
    # prepare_frenzy.cooldown = 6  # 쿨다운 시스템 제거됨
    prepare_frenzy.metadata = {"thirst_increase": True, "optimal_thirst": 70}

    # 8. 생명력 착취 (강력한 HP 흡수, 갈증 대폭 감소) - 일부 스킬
    life_tap = Skill("vampire_life_tap", "생명력 착취", "적의 생명력을 대량 흡수, 갈증 -30")
    life_tap.effects = [
        DamageEffect(DamageType.HP, 2.5, stat_type="magical"),
        HealEffect(percentage=0.9),  # 생명력 착취 (흡혈 보너스)
        GimmickEffect(GimmickOperation.ADD, "thirst", -30, min_value=0)  # 갈증 -30
    ]
    life_tap.costs = [MPCost(9)]
    life_tap.sfx = ("character", "hp_heal")  # 생명력 착취
    # life_tap.cooldown = 4  # 쿨다운 시스템 제거됨
    life_tap.metadata = {"major_drain": True, "thirst_reduction": -30}

    # 9. 혈액 만족 (갈증을 0으로 리셋) - 일부 스킬
    blood_satiation = Skill("vampire_blood_satiation", "혈액 만족", "갈증을 0으로 리셋 (만족 상태)")
    blood_satiation.effects = [
        GimmickEffect(GimmickOperation.SET, "thirst", 0),  # 갈증 0으로 리셋
        HealEffect(percentage=0.6),  # 혈액 만족
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=3)
    ]
    blood_satiation.costs = [MPCost(10)]
    blood_satiation.target_type = "self"
    blood_satiation.sfx = ("character", "hp_heal")  # 혈액 만족
    # blood_satiation.cooldown = 7  # 쿨다운 시스템 제거됨
    blood_satiation.metadata = {"thirst_reset": True, "recovery": True}

    # 10. 궁극기: 혈족의 군주 (극한 갈증 활용, 갈증 증가)
    ultimate = Skill("vampire_ultimate", "혈족의 군주", "극한 갈증으로 압도적인 힘 발휘")
    ultimate.effects = [
        # 현재 갈증에 비례한 극대 피해
        DamageEffect(DamageType.BRV, 3.5, stat_type="physical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.04}),
        DamageEffect(DamageType.HP, 4.0, stat_type="magical",
                    gimmick_bonus={"field": "thirst", "multiplier": 0.03}),
        HealEffect(percentage=0.95),  # 궁극기
        BuffEffect(BuffType.ATTACK_UP, 1.0, duration=4),  # 공격력 +100%
        GimmickEffect(GimmickOperation.ADD, "thirst", 20, max_value=100)  # 갈증 +20 (궁극기 사용 비용)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.target_type = "single"
    ultimate.metadata = {"ultimate": True, "thirst_scaling_max": True, "thirst_increase": True}

    skills = [vampiric_bite, blood_drain, blood_lance, thirst_surge, bat_swarm,
            mist_form, prepare_frenzy, life_tap, blood_satiation, ultimate]

    # 팀워크 스킬: 뱀파이어의 물림
    teamwork = TeamworkSkill(
        "vampire_teamwork",
        "피의 향연",
        "단일 대상 BRV+HP (2.5x → HP 변환) + 입힌 HP 데미지의 100% 흡혈 + 갈증 게이지 완전 충족",
        gauge_cost=150)
    teamwork.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=3, is_party_wide=True),  # 공격력 +50%
        GimmickEffect(GimmickOperation.SET, "thirst", 100),  # 갈증 게이지 완전 충족
        # 100% 흡혈 효과 적용
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "buff": True, "vampire": True}
    skills.append(teamwork)

    return skills

def register_vampire_skills(skill_manager):
    """흡혈귀 스킬 등록"""
    skills = create_vampire_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    return [s.skill_id for s in skills]