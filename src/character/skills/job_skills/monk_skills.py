"""Monk Skills - 몽크 스킬 (음양 기 흐름 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_monk_skills():
    """몽크 10개 스킬 생성 (음양 기 흐름 시스템)"""

    # 1. 기본 BRV: 장타격 (균형 유지)
    palm_strike = Skill("monk_palm_strike", "장타격", "기본 공격, 음양 균형 유지")
    palm_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical")
    ]
    palm_strike.costs = []  # 기본 공격은 MP 소모 없음
    palm_strike.metadata = {}

    # 2. 기본 HP: 기공파 (균형 유지)
    energy_blast = Skill("monk_energy_blast", "기공파", "내공을 실은 강타")
    energy_blast.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="physical")
    ]
    energy_blast.costs = []  # 기본 공격은 MP 소모 없음
    energy_blast.metadata = {}

    # 3. 음극 장 (음으로 이동, 마법 피해)
    yin_strike = Skill("monk_yin_strike", "음극 장",
                      "음의 기를 모아 마법 피해, 음 -15")
    yin_strike.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magical",
                    conditional_bonus={"condition": "in_yin_state", "multiplier": 1.3}),
        GimmickEffect(GimmickOperation.ADD, "ki_gauge", -15, min_value=0, max_value=100)
    ]
    yin_strike.costs = []
    yin_strike.metadata = {"ki_shift": -15, "element": "yin"}

    # 4. 양극 권 (양으로 이동, 물리 피해)
    yang_strike = Skill("monk_yang_strike", "양극 권",
                       "양의 기를 폭발시켜 물리 피해, 양 +15")
    yang_strike.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical",
                    conditional_bonus={"condition": "in_yang_state", "multiplier": 1.3}),
        GimmickEffect(GimmickOperation.ADD, "ki_gauge", 15, min_value=0, max_value=100)
    ]
    yang_strike.costs = [MPCost(5)]
    yang_strike.metadata = {"ki_shift": 15, "element": "yang"}

    # 5. 태극 회복 (균형으로 복귀, 회복)
    balance_restoration = Skill("monk_balance_restoration", "태극 회복",
                               "음양을 균형으로 되돌려 HP 25% 회복")
    balance_restoration.effects = [
        GimmickEffect(GimmickOperation.SET, "ki_gauge", 50),
        HealEffect(percentage=0.25)
    ]
    balance_restoration.costs = [MPCost(7)]
    balance_restoration.target_type = "self"
    balance_restoration.metadata = {"ki_shift": "reset", "heal": True}

    # 6. 극음공 (음 극단 상태에서 강력한 마법 공격)
    yin_extreme = Skill("monk_yin_extreme", "극음공",
                       "음극(20-)에서만 발동, 강력한 마법 공격, 음 -10")
    yin_extreme.effects = [
        DamageEffect(DamageType.BRV_HP, 3.5, stat_type="magical",
                    conditional_bonus={"condition": "in_yin_state", "multiplier": 1.0}),
        GimmickEffect(GimmickOperation.ADD, "ki_gauge", -10, min_value=0, max_value=100)
    ]
    yin_extreme.costs = [MPCost(9)]
    # yin_extreme.cooldown = 3  # 쿨다운 시스템 제거됨
    yin_extreme.metadata = {"requires_yin": True, "ki_shift": -10}

    # 7. 극양공 (양 극단 상태에서 강력한 물리 공격)
    yang_extreme = Skill("monk_yang_extreme", "극양공",
                        "양극(80+)에서만 발동, 강력한 물리 공격, 양 +10")
    yang_extreme.effects = [
        DamageEffect(DamageType.BRV_HP, 4.0, stat_type="physical",
                    conditional_bonus={"condition": "in_yang_state", "multiplier": 1.0}),
        GimmickEffect(GimmickOperation.ADD, "ki_gauge", 10, min_value=0, max_value=100)
    ]
    yang_extreme.costs = [MPCost(9)]
    # yang_extreme.cooldown = 3  # 쿨다운 시스템 제거됨
    yang_extreme.metadata = {"requires_yang": True, "ki_shift": 10}

    # 8. 태극 유전 (3턴간 자동 균형 이동 강화)
    taichi_flow = Skill("monk_taichi_flow", "태극 유전",
                       "3턴간 자동 균형 이동 +10 (기 흐름 강화)")
    taichi_flow.effects = [
        BuffEffect(BuffType.CUSTOM, 1.0, duration=3, custom_stat="ki_flow_enhanced")
    ]
    taichi_flow.costs = [MPCost(7)]
    taichi_flow.target_type = "self"
    # taichi_flow.cooldown = 4  # 쿨다운 시스템 제거됨
    taichi_flow.metadata = {"buff": "enhanced_ki_flow"}

    # 9. 깨달음 (정확히 50에서만 사용 가능, 강력한 버프)
    enlightenment = Skill("monk_enlightenment", "깨달음",
                         "균형(50)에서만 발동, 3턴간 모든 능력치 +40%")
    enlightenment.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.4, duration=3)
    ]
    enlightenment.costs = [MPCost(10)]
    enlightenment.target_type = "self"
    # enlightenment.cooldown = 5  # 쿨다운 시스템 제거됨
    enlightenment.metadata = {"requires_balance": True, "ki_exact": 50}

    # 10. 궁극기: 태극천지파 (음양을 모두 활용한 궁극기)
    taichi_ultimate = Skill("monk_taichi_ultimate", "태극천지파",
                           "음양의 힘을 모두 방출, 균형(50)으로 복귀")
    taichi_ultimate.effects = [
        # 현재 기 게이지 값에 비례한 피해
        DamageEffect(DamageType.BRV, 3.0, stat_type="physical",
                    gimmick_bonus={"field": "ki_gauge", "multiplier": 0.01}),  # 기 1당 +1% 피해
        DamageEffect(DamageType.HP, 2.5, stat_type="magical",
                    gimmick_bonus={"field": "ki_gauge", "multiplier": -0.01, "invert": True}),  # 100-기 값만큼 피해
        GimmickEffect(GimmickOperation.SET, "ki_gauge", 50)  # 균형으로 복귀
    ]
    taichi_ultimate.costs = [MPCost(30)]
    taichi_ultimate.is_ultimate = True
    # taichi_ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    taichi_ultimate.target_type = "single_enemy"
    taichi_ultimate.metadata = {"ultimate": True, "ki_reset": True}

    return [palm_strike, energy_blast, yin_strike, yang_strike,
            balance_restoration, yin_extreme, yang_extreme, taichi_flow,
            enlightenment, taichi_ultimate]

def register_monk_skills(skill_manager):
    """몽크 스킬 등록"""
    skills = create_monk_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
