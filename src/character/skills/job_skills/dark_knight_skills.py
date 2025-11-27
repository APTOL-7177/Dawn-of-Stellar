"""Dark Knight Skills - 암흑기사 (충전 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_dark_knight_skills():
    """암흑기사 10개 스킬 생성 (충전 시스템)"""
    skills = []

    # ============================================================
    # BUILDERS (충전 쌓기)
    # ============================================================

    # 1. 기본 BRV: 충전 강타
    charge_strike = Skill("dk_charge_strike", "충전 강타", "적의 BRV를 공격하면서 충전을 쌓는 기본 공격. 충전에 따라 위력이 증가합니다.")
    charge_strike.effects = [
        DamageEffect(DamageType.BRV, 0.8, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.01}),  # 충전 1%당 +1% 데미지
        GimmickEffect(GimmickOperation.ADD, "charge_gauge", 3, max_value=100)  # 15 → 3 (1/5)
    ]
    charge_strike.costs = []  # 기본 공격은 MP 소모 없음
    charge_strike.sfx = ("combat", "attack_physical")
    charge_strike.metadata = {"basic_attack": True, "charge_gain": 3, "builder": True}  # 15 → 3 (1/5)
    skills.append(charge_strike)

    # 2. 기본 HP: 분쇄 타격
    crushing_blow = Skill("dk_crushing_blow", "분쇄 타격", "적의 HP를 직접 공격하면서 충전을 쌓는 강력한 타격. 충전에 따라 위력이 크게 증가합니다.")
    crushing_blow.effects = [
        DamageEffect(DamageType.HP, 0.5, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.015}),  # 충전 1%당 +1.5% 데미지
        GimmickEffect(GimmickOperation.ADD, "charge_gauge", 2, max_value=100)  # 10 → 2 (1/5)
    ]
    crushing_blow.costs = []  # 기본 공격은 MP 소모 없음
    crushing_blow.sfx = ("combat", "attack_physical")
    crushing_blow.metadata = {"basic_attack": True, "charge_gain": 2, "builder": True}  # 10 → 2 (1/5)
    skills.append(crushing_blow)

    # 3. 방어 태세
    defensive_stance = Skill("dk_defensive_stance", "방어 태세", "방어력 증가 + 피격 시 충전 2배")
    defensive_stance.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "charge_gauge", 1, max_value=100)  # 기본 충전 +1 (5 → 1, 1/5)
    ]
    defensive_stance.costs = [MPCost(6)]  # MP 8 → 6
    defensive_stance.target_type = "self"
    defensive_stance.sfx = ("skill", "protect")
    defensive_stance.metadata = {
        "defensive": True,
        "charge_gain": 1,  # 5 → 1 (1/5)
        "on_hit_charge_multiplier": 2.0,  # 피격 시 충전 2배 (기믹 업데이터에서 처리)
        "builder": True
    }
    skills.append(defensive_stance)

    # 4. 반격 태세
    counter_stance = Skill("dk_counter_stance", "반격 태세", "회피율 증가 + 회피 시 반격 및 충전")
    counter_stance.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.ADD, "charge_gauge", 1, max_value=100)  # 기본 충전 +1 (5 → 1, 1/5)
    ]
    counter_stance.costs = [MPCost(8)]  # MP 10 → 8
    counter_stance.target_type = "self"
    counter_stance.sfx = ("skill", "protect")
    counter_stance.metadata = {
        "counter": True,
        "charge_gain": 1,  # 5 → 1 (1/5)
        "on_evade_counter": True,  # 회피 시 반격 (기믹 업데이터에서 처리)
        "on_evade_charge": 4,  # 회피 시 충전 +4 (20 → 4, 1/5)
        "builder": True
    }
    skills.append(counter_stance)

    # ============================================================
    # SPENDERS (충전 사용 - 한방딜, 캐스트 타임 있음)
    # ============================================================

    # 5. 강타
    power_strike = Skill("dk_power_strike", "강타", "충전 30 소모 (충전 30: 1.6배 → 100: 3.6배)")
    power_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 1.0, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.02}),  # 충전 1%당 +2% 데미지
        GimmickEffect(GimmickOperation.CONSUME, "charge_gauge", 30)
    ]
    power_strike.costs = [MPCost(3), StackCost("charge_gauge", 30)]
    power_strike.cast_time = 0.3  # ATB 30% 캐스트 타임
    power_strike.sfx = ("combat", "damage_high")
    power_strike.metadata = {
        "charge_cost": 30,
        "spender": True,
        "cast_time": 0.3
    }
    skills.append(power_strike)

    # 6. 심연의 폭발
    abyssal_burst = Skill("dk_abyssal_burst", "심연의 폭발", "충전 50 소모 (충전 50: 1.8배 → 100: 2.8배)")
    abyssal_burst.effects = [
        DamageEffect(DamageType.BRV_HP, 0.8, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.02}),  # 충전 1%당 +2% 데미지
        GimmickEffect(GimmickOperation.CONSUME, "charge_gauge", 50)
    ]
    abyssal_burst.costs = [MPCost(5), StackCost("charge_gauge", 50)]
    abyssal_burst.cast_time = 0.5  # ATB 50% 캐스트 타임
    abyssal_burst.target_type = "all_enemies"
    abyssal_burst.is_aoe = True
    abyssal_burst.sfx = ("skill", "cast_complete")
    abyssal_burst.metadata = {
        "charge_cost": 50,
        "spender": True,
        "cast_time": 0.5,
        "aoe": True,
        "stun_chance": 0.3  # 30% 기절 확률
    }
    skills.append(abyssal_burst)

    # 7. 처형
    execution = Skill("dk_execution", "처형", "충전 100 소모 (충전 100: 5.5배, 적 체력 비례 추가 데미지)")
    execution.effects = [
        DamageEffect(DamageType.BRV_HP, 1.5, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.04}),  # 충전 1%당 +4% 데미지
        GimmickEffect(GimmickOperation.SET, "charge_gauge", 0)  # 충전 완전 소모
    ]
    execution.costs = [MPCost(7), StackCost("charge_gauge", 100)]
    execution.cast_time = 1.0  # ATB 100% 캐스트 타임 (매우 긴 시전)
    execution.sfx = ("skill", "ultima")
    execution.metadata = {
        "charge_cost": 100,
        "spender": True,
        "cast_time": 1.0,
        "execute": True,  # 적 체력이 낮을수록 추가 데미지
        "low_hp_bonus": 2.0  # 적 HP 30% 이하일 때 데미지 2배
    }
    skills.append(execution)

    # ============================================================
    # SPECIAL - 패링 기술
    # ============================================================

    # 8. 복수의 패링 (원래 dark_slash)
    vengeful_parry = Skill("dk_vengeful_parry", "복수의 패링", "캐스트 중 피격 시 카운터 (MP 8)")
    vengeful_parry.effects = [
        DamageEffect(DamageType.BRV_HP, 1.0),  # 기본 피해 (캐스트 완료 시) 1.5 → 1.0
        GimmickEffect(GimmickOperation.ADD, "charge_gauge", 1, max_value=100)  # 충전 1 (5 → 1, 1/5)
    ]
    vengeful_parry.costs = [MPCost(8)]  # MP 15 → 8
    vengeful_parry.cast_time = 0.7  # ATB 70% 캐스트 타임 (긴 시전)
    vengeful_parry.sfx = ("combat", "attack_physical")
    vengeful_parry.metadata = {
        "parry": True,  # 패링 기술
        "parry_damage_multiplier": 2.5,  # 패링 성공 시 데미지 3배 → 2.5배
        "parry_charge_gain": 5,  # 패링 성공 시 충전 5 (25 → 5, 1/5)
        "cast_time": 0.7,
        "interruptible": True,  # 중단 가능
        "counter_on_interrupt": True  # 캐스트 중 피격 시 카운터
    }
    skills.append(vengeful_parry)

    # ============================================================
    # UTILITY
    # ============================================================

    # 9. 어둠의 재생
    dark_regeneration = Skill("dk_dark_regeneration", "어둠의 재생", "충전 20 소모하여 HP/BRV 회복")
    dark_regeneration.effects = [
        HealEffect(stat_scaling='max_attack', multiplier=1.5, percentage=0.3),  # 공격력 기반 회복 + 30% 추가
        GimmickEffect(GimmickOperation.CONSUME, "charge_gauge", 20)
    ]
    dark_regeneration.costs = [MPCost(10), StackCost("charge_gauge", 20)]
    dark_regeneration.target_type = "self"
    dark_regeneration.sfx = ("character", "hp_heal")
    dark_regeneration.metadata = {
        "charge_cost": 20,
        "heal": True,
        "brv_restore": True  # BRV도 회복
    }
    skills.append(dark_regeneration)

    # 10. 궁극기: 불굴의 힘
    ultimate = Skill("dk_ultimate", "불굴의 힘", "모든 충전 소모. 막강한 피해 + 생존 버프")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.03}),
        DamageEffect(DamageType.HP, 5.0, gimmick_bonus={"field": "charge_gauge", "multiplier": 0.04}),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=5),
        GimmickEffect(GimmickOperation.SET, "charge_gauge", 0)  # 충전 완전 소모
    ]
    ultimate.costs = [MPCost(40)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.target_type = "single_enemy"
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "charge_consume_all": True,
        "last_stand": True  # 사망 위기 시 충전 100 소모하여 생존 (특성으로 처리)
    }
    skills.append(ultimate)

    return skills

def register_dark_knight_skills(sm):
    skills = create_dark_knight_skills()
    for s in skills:
        sm.register_skill(s)

    # 팀워크 스킬: 피의 계약
    teamwork = TeamworkSkill(
        "dark_knight_teamwork",
        "피의 계약",
        "아군 전체 현재 HP의 25% 흡수 → 자신 BRV로 변환 (MAX BRV의 150%) + 다음 공격 데미지 1.8배 + 어둠 게이지 +50",
        gauge_cost=200
    )
    teamwork.effects = [
        # 아군 전체 HP 25% 흡수 → 자신 BRV로 변환 (커스텀 효과로 구현 필요)
        # 일단 임시로 자신 공격력 버프 + 어둠 게이지 증가
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=1),  # 다음 공격 데미지 1.8배 (기본 1.0 + 0.8)
        GimmickEffect(GimmickOperation.ADD, "dark_power", 50)  # 어둠 게이지 +50
    ]
    teamwork.target_type = "self"
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True, "custom_hp_drain": True}
    skills.append(teamwork)
    return skills
