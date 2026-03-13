"""Dimensionist Skills - 차원술사 스킬 (차원 굴절 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.fixed_damage_effect import FixedDamageEffect
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_dimensionist_skills():
    """차원술사 10개 스킬 생성 (차원 굴절 시스템)"""

    # ========================================
    # 1. 굴절 타격 (기본 BRV)
    # ========================================
    refraction_strike = Skill(
        "dimensionist_refraction_strike",
        "굴절 타격",
        "기본 BRV 공격. 굴절량의 70%만큼 추가 데미지"
    )
    refraction_strike.effects = [
        DamageEffect(
            DamageType.BRV,
            multiplier=1.125,
            stat_type="magical"
        )
    ]
    refraction_strike.costs = []
    refraction_strike.target_type = "enemy"
    refraction_strike.sfx = ("skill", "cast_start")
    refraction_strike.metadata = {"refraction_scaling": True}

    # ========================================
    # 2. 굴절 방출 (기본 HP)
    # ========================================
    refraction_release = Skill(
        "dimensionist_refraction_release",
        "굴절 방출",
        "기본 HP 공격. 굴절량의 60%만큼 추가 데미지"
    )
    refraction_release.effects = [
        DamageEffect(
            DamageType.HP,
            multiplier=0.9,
            stat_type="magical"
        )
    ]
    refraction_release.costs = []
    refraction_release.target_type = "enemy"
    refraction_release.sfx = ("skill", "cast_complete")
    refraction_release.metadata = {"refraction_scaling": True}

    # ========================================
    # 3. 차원 회귀 (자가 회복)
    # ========================================
    dimension_regression = Skill(
        "dimensionist_dimension_regression",
        "차원 회귀",
        "굴절량의 150%만큼 HP 회복 및 굴절량 75% 감소"
    )
    dimension_regression.effects = [
        HealEffect(
            fixed_amount=0,
            percentage=0,
            metadata={"refraction_heal": True, "refraction_rate": 1.5}
        ),
        GimmickEffect(
            GimmickOperation.MULTIPLY,
            "refraction_stacks",
            0.25,  # 75% 감소 = 25%만 남김
            min_value=0
        )
    ]
    dimension_regression.costs = [MPCost(8)]
    dimension_regression.target_type = "self"
    dimension_regression.cooldown = 3
    dimension_regression.sfx = ("skill", "cast_complete")
    dimension_regression.metadata = {
        "self_heal": True,
        "refraction_consumption": 0.75
    }

    # ========================================
    # 4. 차원 폭발 (전체 고정 피해)
    # ========================================
    dimension_explosion = Skill(
        "dimensionist_dimension_explosion",
        "차원 폭발",
        "[바람 속성] 굴절량의 20%를 소모하여 적 전체에게 마법력 기반 피해 + 소모량의 8.0배 고정 피해"
    )

    # 마법력 기반 피해 + 고정 피해 효과 (굴절 보너스 완화)
    dimension_explosion.effects = [
        # 마법력 기반 피해 (굴절 보너스 없이 고정 계수만 적용)
        DamageEffect(
            DamageType.BRV,
            multiplier=0.6,
            stat_type="magical",
            element="wind"
        ),
        # 굴절량 소모 (20% → 80% 남김)
        GimmickEffect(
            GimmickOperation.MULTIPLY,
            "refraction_stacks",
            0.8,  # 20% 소모 = 80%만 남김
            min_value=0
        )
    ]
    dimension_explosion.costs = [MPCost(12)]  # MP 소모 증가
    dimension_explosion.target_type = "all_enemies"
    dimension_explosion.is_aoe = True
    dimension_explosion.cooldown = 5  # 쿨다운 증가
    dimension_explosion.sfx = ("skill", "explosion")
    dimension_explosion.metadata = {
        "refraction_consumption": 0.20,  # 소모율 감소 (20%)
        "fixed_damage_multiplier": 8.0,  # 고정 피해 배율
        "custom_damage": True,
        "magic_scaling": True
    }

    # ========================================
    # 5. 굴절 강화 (버프)
    # ========================================
    refraction_enhance = Skill(
        "dimensionist_refraction_enhance",
        "굴절 강화",
        "최대 HP의 20%만큼 굴절량 소모, 공격력/마법력 +60% (3턴)"
    )
    refraction_enhance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=3, target="self"),
        BuffEffect(BuffType.MAGIC_UP, 0.6, duration=3, target="self")
    ]
    refraction_enhance.costs = [MPCost(6)]
    refraction_enhance.target_type = "self"
    refraction_enhance.sfx = ("character", "status_buff")
    refraction_enhance.metadata = {
        "refraction_cost_hp_percent": 0.20,
        "requires_refraction_check": True
    }

    # ========================================
    # 6. 차원 분산 (AOE BRV+HP)
    # ========================================
    dimension_scatter = Skill(
        "dimensionist_dimension_scatter",
        "차원 분산",
        "[바람 속성] 굴절량에 비례한 강력한 전체 공격"
    )
    dimension_scatter.effects = [
        DamageEffect(
            DamageType.BRV_HP,
            multiplier=1.5,
            stat_type="magical",
            element="wind"
        )
    ]
    dimension_scatter.costs = [MPCost(12)]
    dimension_scatter.target_type = "all_enemies"
    dimension_scatter.is_aoe = True
    dimension_scatter.sfx = ("skill", "cast_complete")
    dimension_scatter.metadata = {
        "refraction_cost_hp_percent": 0.15,
        "refraction_scaling": True,
        "requires_refraction_check": True
    }

    # ========================================
    # 7. 굴절 전환 (피해→굴절)
    # ========================================
    refraction_conversion = Skill(
        "dimensionist_refraction_conversion",
        "굴절 전환",
        "HP를 굴절량으로 전환. 소모한 HP의 350% 획득. HP가 낮을수록 효율 증가 (50%에서 최대 1.5배)"
    )
    refraction_conversion.effects = [
        # 자해 및 굴절 획득은 메타데이터로 처리
    ]
    refraction_conversion.costs = [MPCost(5)]
    refraction_conversion.target_type = "self"
    refraction_conversion.sfx = ("combat", "critical")
    refraction_conversion.metadata = {
        "self_damage_hp_percent": 0.25,
        "refraction_gain_multiplier": 3.5,  # 기본 3.5배 (350%)
        "custom_effect": True,
        "low_hp_efficiency_bonus": True,  # HP가 낮을수록 효율 증가
        "max_efficiency_at_hp_percent": 0.5,  # 50% HP에서 최대 효율
        "max_efficiency_multiplier": 1.5  # 최대 1.5배 효율
    }

    # ========================================
    # 8. 차원 보호막 (아군 버프)
    # ========================================
    dimension_barrier = Skill(
        "dimensionist_dimension_barrier",
        "차원 보호막",
        "최대 HP의 25%만큼 굴절량 소모, 아군 전체 피해 경감 +40% (2턴). 경감된 피해는 차원술사의 굴절량으로 전환"
    )
    dimension_barrier.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=2, target="self"),
        BuffEffect(BuffType.SPIRIT_UP, 0.3, duration=2, target="self"),
        # 피해 경감 버프는 메타데이터로 처리
    ]
    dimension_barrier.costs = [MPCost(10)]
    dimension_barrier.target_type = "all_allies"
    dimension_barrier.is_aoe = True
    dimension_barrier.sfx = ("character", "status_buff")
    dimension_barrier.metadata = {
        "refraction_cost_hp_percent": 0.25,
        "damage_reduction": 0.40,
        "requires_refraction_check": True,
        "redirect_reduced_to_refraction": True  # 경감된 피해를 차원술사 굴절량으로 전환
    }

    # ========================================
    # 9. 차원 역류 (고위험 고보상)
    # ========================================
    dimension_backflow = Skill(
        "dimensionist_dimension_backflow",
        "차원 역류",
        "[바람 속성] 굴절량의 50%를 즉시 HP 고정 피해로 받고, 극강의 단일 공격"
    )
    dimension_backflow.effects = [
        DamageEffect(
            DamageType.BRV_HP,
            multiplier=3.0,
            stat_type="magical",
            element="wind"
        ),
        DamageEffect(
            DamageType.HP,
            multiplier=2.625,
            stat_type="magical",
            element="wind"
        )
    ]
    dimension_backflow.costs = [MPCost(15)]
    dimension_backflow.target_type = "enemy"
    dimension_backflow.cooldown = 5
    dimension_backflow.sfx = ("skill", "limit_break")
    dimension_backflow.metadata = {
        "self_damage_refraction_percent": 0.50,
        "high_risk_high_reward": True
    }

    # ========================================
    # 10. 궁극기: 차원 붕괴
    # ========================================
    ultimate = Skill(
        "dimensionist_ultimate",
        "차원 붕괴",
        "[바람 속성] 모든 굴절량을 해방하여 차원을 붕괴시킴"
    )
    ultimate.effects = [
        DamageEffect(
            DamageType.BRV,
            multiplier=3.75,
            stat_type="magical",
            element="wind"
        ),
        DamageEffect(
            DamageType.HP,
            multiplier=3.2,
            stat_type="magical",
            element="wind"
        ),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.5, duration=3),
        BuffEffect(BuffType.SPIRIT_DOWN, 0.5, duration=3),
        # 굴절량 전부 소모 및 회복은 메타데이터로 처리
    ]
    ultimate.costs = [MPCost(35)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "refraction_scaling": True,
        "consume_all_refraction": True,
        "self_heal_refraction_percent": 0.30
    }

    # ========================================
    # 11. 굴절 증폭기 (Refraction Amplifier) - 방어형 스킬
    # ========================================
    refraction_amplifier = Skill(
        "dimensionist_refraction_amplifier",
        "굴절 증폭기",
        "차원 굴절 경감률 +15% (최대 100%), 현재 굴절량의 30%를 보호막으로 변환 (5턴)"
    )
    refraction_amplifier.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.30, duration=2),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.30, duration=2)
    ]
    refraction_amplifier.costs = [MPCost(5)]
    refraction_amplifier.target_type = "self"
    refraction_amplifier.cooldown = 0
    refraction_amplifier.sfx = ("skill", "protect")
    refraction_amplifier.metadata = {
        "tank_skill": True,
        "refraction_reduction_bonus": 0.15,
        "refraction_to_shield_percent": 0.30,
        "skill_category": "defense"
    }

    # ========================================
    # 12. 시간 고정 (Temporal Brace) - 방어형 스킬
    # ========================================
    temporal_brace = Skill(
        "dimensionist_temporal_brace",
        "시간 고정",
        "방어력/마법방어력 +40%, 지연 피해 1회 면역 (면역 발동 시 MP 10 소모)"
    )
    temporal_brace.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.40, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.40, duration=3)
    ]
    temporal_brace.costs = [MPCost(10)]
    temporal_brace.target_type = "self"
    temporal_brace.sfx = ("skill", "shell")
    temporal_brace.metadata = {
        "tank_skill": True,
        "delayed_damage_immunity_charges": 1,
        "immunity_mp_cost": 10,
        "skill_category": "defense"
    }

    return [
        refraction_strike,
        refraction_release,
        dimension_regression,
        dimension_explosion,
        refraction_enhance,
        dimension_scatter,
        refraction_conversion,
        dimension_barrier,
        dimension_backflow,
        ultimate,
        refraction_amplifier,
        temporal_brace
    ]

def register_dimensionist_skills(skill_manager):
    """차원술사 스킬 등록"""
    skills = create_dimensionist_skills()
    
    # 팀워크 스킬: 시공간 파열
    teamwork = TeamworkSkill(
        "dimensionist_teamwork",
        "시공간 파열",
        "축적된 차원 굴절의 50%를 방출하여 전체 적에게 고정 피해 + 나머지 굴절 완전 제거",
        gauge_cost=225)
    teamwork.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.55, duration=3, is_party_wide=True),
        BuffEffect(BuffType.SPEED_DOWN, 0.6, duration=2, is_party_wide=True)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "buff": True, "dimension": True}
    skills.append(teamwork)

    for skill in skills:
        skill_manager.register_skill(skill)

    return [s.skill_id for s in skills]
