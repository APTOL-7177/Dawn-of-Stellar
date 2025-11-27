"""Philosopher Skills - 철학자 스킬 (딜레마 선택 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_philosopher_skills():
    """철학자 10개 스킬 생성 (딜레마 선택 시스템)"""

    # 1. 기본 BRV: 철학적 타격
    philosophical_strike = Skill("philosopher_strike", "철학적 타격", "기본 마법 공격")
    philosophical_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical")
    ]
    philosophical_strike.costs = []  # 기본 공격은 MP 소모 없음
    philosophical_strike.sfx = ("skill", "cast_start")  # 철학적 타격
    philosophical_strike.metadata = {}

    # 2. 기본 HP: 진리의 일격
    truth_strike = Skill("philosopher_truth_strike", "진리의 일격", "HP 마법 공격")
    truth_strike.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical")
    ]
    truth_strike.costs = []  # 기본 공격은 MP 소모 없음
    truth_strike.sfx = ("skill", "cast_complete")  # 진리의 일격
    truth_strike.metadata = {}

    # 3. 힘 선택 (공격력 +50%, 3턴)
    choose_power = Skill("philosopher_choose_power", "힘 선택", "물리 공격력 +50% (3턴)")
    choose_power.effects = [
        GimmickEffect(GimmickOperation.ADD, "choice_power", 1, max_value=99),  # 힘 선택 카운트 +1
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=3),
        DamageEffect(DamageType.BRV, 1.8, stat_type="physical")
    ]
    choose_power.costs = []
    choose_power.target_type = "self"
    choose_power.sfx = ("character", "status_buff")  # 힘 선택
    # choose_power.cooldown = 2  # 쿨다운 시스템 제거됨
    choose_power.metadata = {"dilemma": "power_wisdom", "choice": "power"}

    # 4. 지혜 선택 (마법 공격력 +50%, 3턴)
    choose_wisdom = Skill("philosopher_choose_wisdom", "지혜 선택", "마법 공격력 +50% (3턴)")
    choose_wisdom.effects = [
        GimmickEffect(GimmickOperation.ADD, "choice_wisdom", 1, max_value=99),  # 지혜 선택 카운트 +1
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=3),
        DamageEffect(DamageType.BRV, 1.8, stat_type="magical")
    ]
    choose_wisdom.costs = [MPCost(6)]
    choose_wisdom.target_type = "self"
    choose_wisdom.sfx = ("skill", "haste")  # 지혜 선택
    # choose_wisdom.cooldown = 2  # 쿨다운 시스템 제거됨
    choose_wisdom.metadata = {"dilemma": "power_wisdom", "choice": "wisdom"}

    # 5. 희생 선택 (아군 HP 30% 회복)
    choose_sacrifice = Skill("philosopher_choose_sacrifice", "희생 선택", "아군 HP 30% 회복")
    choose_sacrifice.effects = [
        GimmickEffect(GimmickOperation.ADD, "choice_sacrifice", 1, max_value=99),  # 희생 선택 카운트 +1
        HealEffect(percentage=0.44),  # 희생 선택 (0.36 → 0.44 증가)
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=3)
    ]
    choose_sacrifice.costs = [MPCost(7)]
    choose_sacrifice.target_type = "ally"
    choose_sacrifice.sfx = ("character", "hp_heal")  # 희생 선택
    # choose_sacrifice.cooldown = 3  # 쿨다운 시스템 제거됨
    choose_sacrifice.metadata = {"dilemma": "sacrifice_survival", "choice": "sacrifice"}

    # 6. 생존 선택 (자신 HP 30% 회복)
    choose_survival = Skill("philosopher_choose_survival", "생존 선택", "자신 HP 30% 회복")
    choose_survival.effects = [
        GimmickEffect(GimmickOperation.ADD, "choice_survival", 1, max_value=99),  # 생존 선택 카운트 +1
        HealEffect(percentage=0.44),  # 생존 선택 (0.36 → 0.44 증가)
        BuffEffect(BuffType.EVASION_UP, 0.3, duration=3)
    ]
    choose_survival.costs = [MPCost(7)]
    choose_survival.target_type = "self"
    choose_survival.sfx = ("character", "hp_heal")  # 생존 선택
    # choose_survival.cooldown = 3  # 쿨다운 시스템 제거됨
    choose_survival.metadata = {"dilemma": "sacrifice_survival", "choice": "survival"}

    # 7. 진실 선택 (적 디버프 - 방어력↓ 명중↓)
    choose_truth = Skill("philosopher_choose_truth", "진실 선택", "적 방어↓ 명중↓")
    choose_truth.effects = [
        GimmickEffect(GimmickOperation.ADD, "choice_truth", 1, max_value=99),  # 진실 선택 카운트 +1
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.3, duration=4)
    ]
    choose_truth.costs = [MPCost(6)]
    choose_truth.sfx = ("character", "status_debuff")  # 진실 선택
    # choose_truth.cooldown = 3  # 쿨다운 시스템 제거됨
    choose_truth.metadata = {"dilemma": "truth_lie", "choice": "truth"}

    # 8. 거짓 선택 (자신 버프 - 공격↑ 속도↑)
    choose_lie = Skill("philosopher_choose_lie", "거짓 선택", "자신 공격↑ 속도↑")
    choose_lie.effects = [
        GimmickEffect(GimmickOperation.ADD, "choice_lie", 1, max_value=99),  # 거짓 선택 카운트 +1
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=4)
    ]
    choose_lie.costs = [MPCost(6)]
    choose_lie.target_type = "self"
    choose_lie.sfx = ("character", "status_buff")  # 거짓 선택
    # choose_lie.cooldown = 3  # 쿨다운 시스템 제거됨
    choose_lie.metadata = {"dilemma": "truth_lie", "choice": "lie"}

    # 9. 균형의 철학 (모든 선택 초기화, 균형 버프)
    balanced_philosophy = Skill("philosopher_balanced", "균형의 철학", "모든 선택 초기화 + 균형 버프")
    balanced_philosophy.effects = [
        # 모든 선택 초기화
        GimmickEffect(GimmickOperation.SET, "choice_power", 0),
        GimmickEffect(GimmickOperation.SET, "choice_wisdom", 0),
        GimmickEffect(GimmickOperation.SET, "choice_sacrifice", 0),
        GimmickEffect(GimmickOperation.SET, "choice_survival", 0),
        GimmickEffect(GimmickOperation.SET, "choice_truth", 0),
        GimmickEffect(GimmickOperation.SET, "choice_lie", 0),
        # 균형 버프 (모든 스탯 +30%)
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.3, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=5),
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magical")
    ]
    balanced_philosophy.costs = [MPCost(12)]
    balanced_philosophy.target_type = "self"
    balanced_philosophy.sfx = ("skill", "haste")  # 균형의 철학
    # balanced_philosophy.cooldown = 6  # 쿨다운 시스템 제거됨
    balanced_philosophy.metadata = {"reset_choices": True}

    # 10. 궁극기: 철학자의 돌
    ultimate = Skill("philosopher_ultimate", "철학자의 돌", "선택의 결정체, 극한의 공격")
    ultimate.effects = [
        # 극대 공격 (선택 누적에 비례)
        DamageEffect(DamageType.BRV, 3.5, stat_type="magical",
                    gimmick_bonus={"field": "choice_power", "multiplier": 0.05}),
        DamageEffect(DamageType.BRV, 3.5, stat_type="magical",
                    gimmick_bonus={"field": "choice_wisdom", "multiplier": 0.05}),
        DamageEffect(DamageType.HP, 5.0, stat_type="magical"),
        # 모든 선택 효과 동시 발동
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.8, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=5),
        # 선택 누적 유지 (초기화하지 않음)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "choice_scaling": True}

    return [philosophical_strike, truth_strike, choose_power, choose_wisdom, choose_sacrifice,
            choose_survival, choose_truth, choose_lie, balanced_philosophy, ultimate]

def register_philosopher_skills(skill_manager):
    """철학자 스킬 등록"""
    skills = create_philosopher_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 진리의 계시
    teamwork = TeamworkSkill(
        "philosopher_teamwork",
        "진리의 계시",
        "현재까지 선택한 딜레마 경향에 따라 효과 변화 (최고의 강화 기술)",
        gauge_cost=250
    )
    teamwork.effects = [
        # 딜레마 기반 효과 - 임시로 균형 효과로 처리
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.3, duration=3, is_party_wide=True),
        HealEffect(percentage=0.3, is_party_wide=True)
    ]
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True}
    skills.append(teamwork)
    return skills
