"""Dimensionist Skills - 차원술사 스킬 (차원 굴절 시스템)"""
from src.character.skills.skill import Skill
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
        "기본 BRV 공격. 굴절량의 2%만큼 추가 데미지"
    )
    refraction_strike.effects = [
        DamageEffect(
            DamageType.BRV,
            multiplier=1.5,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.02}
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
        "기본 HP 공격. 굴절량의 1%만큼 추가 데미지"
    )
    refraction_release.effects = [
        DamageEffect(
            DamageType.HP,
            multiplier=1.2,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.01}
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
        "굴절량의 75%만큼 HP 회복 및 굴절량 75% 감소"
    )
    dimension_regression.effects = [
        HealEffect(
            fixed_amount=0,
            percentage=0,
            metadata={"refraction_heal": True, "refraction_rate": 0.75}
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
    dimension_regression.sfx = ("character", "heal")
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
        "굴절량의 25%를 소모하여 적 전체에게 소모량의 2.5배 고정 피해"
    )

    # 고정 피해 효과 (스케일링: refraction_stacks × 0.25 × 2.5 = refraction_stacks × 0.625)
    # 하지만 굴절량 소모를 먼저 해야 하므로, 메타데이터로 처리
    dimension_explosion.effects = [
        # 실제 고정 피해는 custom_execute에서 처리
        GimmickEffect(
            GimmickOperation.MULTIPLY,
            "refraction_stacks",
            0.75,  # 25% 소모 = 75%만 남김
            min_value=0
        )
    ]
    dimension_explosion.costs = [MPCost(10)]
    dimension_explosion.target_type = "all_enemies"
    dimension_explosion.is_aoe = True
    dimension_explosion.cooldown = 4
    dimension_explosion.sfx = ("skill", "explosion")
    dimension_explosion.metadata = {
        "refraction_consumption": 0.25,
        "fixed_damage_multiplier": 2.5,
        "custom_damage": True  # 커스텀 데미지 처리 플래그
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
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=3),
        BuffEffect(BuffType.MAGIC_UP, 0.6, duration=3)
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
        "굴절량에 비례한 강력한 전체 공격"
    )
    dimension_scatter.effects = [
        DamageEffect(
            DamageType.BRV_HP,
            multiplier=2.0,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.015}
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
        "최대 HP의 30%만큼 자해하여 동일량을 굴절량으로 전환 (2배 효율)"
    )
    refraction_conversion.effects = [
        # 자해 및 굴절 획득은 메타데이터로 처리
    ]
    refraction_conversion.costs = [MPCost(5)]
    refraction_conversion.target_type = "self"
    refraction_conversion.sfx = ("combat", "critical")
    refraction_conversion.metadata = {
        "self_damage_hp_percent": 0.30,
        "refraction_gain_multiplier": 2.0,
        "custom_effect": True
    }

    # ========================================
    # 8. 차원 보호막 (아군 버프)
    # ========================================
    dimension_barrier = Skill(
        "dimensionist_dimension_barrier",
        "차원 보호막",
        "최대 HP의 25%만큼 굴절량 소모, 아군 전체 피해 경감 +40% (2턴)"
    )
    dimension_barrier.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=2),
        BuffEffect(BuffType.SPIRIT_UP, 0.3, duration=2),
        # 피해 경감 버프는 메타데이터로 처리
    ]
    dimension_barrier.costs = [MPCost(10)]
    dimension_barrier.target_type = "all_allies"
    dimension_barrier.is_aoe = True
    dimension_barrier.sfx = ("character", "status_buff")
    dimension_barrier.metadata = {
        "refraction_cost_hp_percent": 0.25,
        "damage_reduction": 0.40,
        "requires_refraction_check": True
    }

    # ========================================
    # 9. 차원 역류 (고위험 고보상)
    # ========================================
    dimension_backflow = Skill(
        "dimensionist_dimension_backflow",
        "차원 역류",
        "굴절량의 50%를 즉시 HP 고정 피해로 받고, 극강의 단일 공격"
    )
    dimension_backflow.effects = [
        DamageEffect(
            DamageType.BRV_HP,
            multiplier=4.0,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.04}
        ),
        DamageEffect(
            DamageType.HP,
            multiplier=3.5,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.03}
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
        "모든 굴절량을 해방하여 차원을 붕괴시킴"
    )
    ultimate.effects = [
        DamageEffect(
            DamageType.BRV,
            multiplier=5.0,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.05}
        ),
        DamageEffect(
            DamageType.HP,
            multiplier=4.5,
            stat_type="magical",
            gimmick_bonus={"field": "refraction_stacks", "multiplier": 0.04}
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
        ultimate
    ]

def register_dimensionist_skills(skill_manager):
    """차원술사 스킬 등록"""
    skills = create_dimensionist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
