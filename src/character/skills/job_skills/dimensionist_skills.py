"""Dimensionist Skills - 차원술사 스킬 (확률 왜곡 게이지 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_dimensionist_skills():
    """차원술사 10개 스킬 생성 (확률 왜곡 게이지 시스템)"""

    # 1. 기본 BRV: 확률 왜곡 타격
    distortion_strike = Skill("dimensionist_strike", "확률 왜곡 타격", "기본 공격 (게이지 +15)")
    distortion_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", 15, max_value=100)  # 게이지 +15
    ]
    distortion_strike.costs = []  # 기본 공격은 MP 소모 없음
    distortion_strike.sfx = "338"  # FFVII distortion sound
    distortion_strike.metadata = {"gauge_gain": 15}

    # 2. 기본 HP: 현실 절단
    reality_cut = Skill("dimensionist_reality_cut", "현실 절단", "HP 공격 (게이지 +20)")
    reality_cut.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", 20, max_value=100)  # 게이지 +20
    ]
    reality_cut.costs = []  # 기본 공격은 MP 소모 없음
    reality_cut.sfx = "344"  # FFVII reality sound
    reality_cut.metadata = {"gauge_gain": 20}

    # 3. 크리티컬 왜곡 (게이지 20 소모 - 크리티컬 확률 +50%)
    crit_distortion = Skill("dimensionist_crit_distortion", "크리티컬 왜곡", "게이지 20 소모: 크리티컬 +50% (2턴)")
    crit_distortion.effects = [
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", -20, min_value=0),  # 게이지 -20
        BuffEffect(BuffType.CRITICAL_UP, 0.5, duration=2),
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical")
    ]
    crit_distortion.costs = [MPCost(10)]
    crit_distortion.target_type = "self"
    crit_distortion.sfx = "352"  # FFVII crit sound
    crit_distortion.cooldown = 2
    crit_distortion.metadata = {"distortion_cost": 20, "crit_boost": 0.5}

    # 4. 회피 왜곡 (게이지 30 소모 - 회피율 +80%)
    evasion_distortion = Skill("dimensionist_evasion_distortion", "회피 왜곡", "게이지 30 소모: 회피 +80% (2턴)")
    evasion_distortion.effects = [
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", -30, min_value=0),  # 게이지 -30
        BuffEffect(BuffType.EVASION_UP, 0.8, duration=2),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=2)
    ]
    evasion_distortion.costs = [MPCost(12)]
    evasion_distortion.target_type = "self"
    evasion_distortion.sfx = "362"  # FFVII evasion sound
    evasion_distortion.cooldown = 3
    evasion_distortion.metadata = {"distortion_cost": 30, "evasion_boost": 0.8}

    # 5. 확률 공격 (게이지에 비례한 데미지)
    probability_attack = Skill("dimensionist_probability_attack", "확률 공격", "게이지 비례 강력한 공격")
    probability_attack.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magical",
                    gimmick_bonus={"field": "distortion_gauge", "multiplier": 0.02}),  # 게이지 1당 +2% 피해
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", 10, max_value=100)  # 게이지 +10
    ]
    probability_attack.costs = [MPCost(15)]
    probability_attack.sfx = "376"  # FFVII probability sound
    probability_attack.cooldown = 3
    probability_attack.metadata = {"gauge_scaling": True}

    # 6. 양자 도약 (순간이동 + 회피)
    quantum_leap = Skill("dimensionist_quantum_leap", "양자 도약", "순간이동 공격 + 게이지 획득")
    quantum_leap.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magical"),
        BuffEffect(BuffType.EVASION_UP, 0.5, duration=2),
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", 25, max_value=100)  # 게이지 +25
    ]
    quantum_leap.costs = [MPCost(18)]
    quantum_leap.sfx = "404"  # FFVII quantum sound
    quantum_leap.cooldown = 4
    quantum_leap.metadata = {"teleport": True, "gauge_gain": 25}

    # 7. 시간 되감기 (게이지 50 소모 - 쿨다운 리셋)
    time_rewind = Skill("dimensionist_time_rewind", "시간 되감기", "게이지 50 소모: 쿨다운 리셋 + 재행동")
    time_rewind.effects = [
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", -50, min_value=0),  # 게이지 -50
        # 쿨다운 리셋 효과 (메타데이터로 표시)
        BuffEffect(BuffType.SPEED_UP, 0.8, duration=2),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=2),
        HealEffect(percentage=0.20)  # HP 20% 회복
    ]
    time_rewind.costs = [MPCost(25)]
    time_rewind.target_type = "self"
    time_rewind.sfx = "423"  # FFVII rewind sound
    time_rewind.cooldown = 6
    time_rewind.metadata = {"distortion_cost": 50, "reset_cooldowns": True, "retry": True}

    # 8. 현실 조작 (전장 조작 + 게이지 획득)
    reality_shift = Skill("dimensionist_reality_shift", "현실 조작", "적 디버프 + 게이지 획득")
    reality_shift.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical"),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.5, duration=3, target="all_enemies"),
        BuffEffect(BuffType.EVASION_DOWN, 0.3, duration=3, target="all_enemies"),
        GimmickEffect(GimmickOperation.ADD, "distortion_gauge", 30, max_value=100)  # 게이지 +30
    ]
    reality_shift.costs = [MPCost(20)]
    reality_shift.target_type = "all_enemies"
    reality_shift.is_aoe = True
    reality_shift.sfx = "438"  # FFVII reality shift sound
    reality_shift.cooldown = 5
    reality_shift.metadata = {"gauge_gain": 30}

    # 9. 평행우주 (게이지 100 소모 - 상태 리셋 + 극강 버프)
    parallel_universe = Skill("dimensionist_parallel_universe", "평행우주", "게이지 100 소모: 평행우주의 나와 교체")
    parallel_universe.effects = [
        GimmickEffect(GimmickOperation.SET, "distortion_gauge", 0),  # 게이지 전부 소모
        # 상태 리셋 (모든 디버프 제거, HP/MP 회복)
        HealEffect(percentage=0.50),  # HP 50% 회복
        # 극강 버프 (평행우주의 강화된 나)
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.8, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.6, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.6, duration=5),
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="magical")
    ]
    parallel_universe.costs = [MPCost(30)]
    parallel_universe.target_type = "self"
    parallel_universe.sfx = "467"  # FFVII parallel sound
    parallel_universe.cooldown = 8
    parallel_universe.metadata = {"distortion_cost": 100, "reset_status": True, "alternate_self": True}

    # 10. 궁극기: 차원 붕괴
    ultimate = Skill("dimensionist_ultimate", "차원 붕괴", "모든 게이지 소모하여 극한의 공격")
    ultimate.effects = [
        # 극대 공격 (게이지에 비례)
        DamageEffect(DamageType.BRV, 4.0, stat_type="magical",
                    gimmick_bonus={"field": "distortion_gauge", "multiplier": 0.03}),
        DamageEffect(DamageType.BRV, 3.5, stat_type="magical",
                    gimmick_bonus={"field": "distortion_gauge", "multiplier": 0.03}),
        DamageEffect(DamageType.HP, 5.0, stat_type="magical",
                    gimmick_bonus={"field": "distortion_gauge", "multiplier": 0.02}),
        # 확률 조작 (크리티컬 확정)
        BuffEffect(BuffType.CRITICAL_UP, 1.0, duration=1),
        # 모든 게이지 소모
        GimmickEffect(GimmickOperation.SET, "distortion_gauge", 0)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = "696"  # FFVII ultimate dimension sound
    ultimate.cooldown = 8
    ultimate.metadata = {"ultimate": True, "gauge_scaling": True, "consume_all_gauge": True}

    return [distortion_strike, reality_cut, crit_distortion, evasion_distortion, probability_attack,
            quantum_leap, time_rewind, reality_shift, parallel_universe, ultimate]

def register_dimensionist_skills(skill_manager):
    """차원술사 스킬 등록"""
    skills = create_dimensionist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
