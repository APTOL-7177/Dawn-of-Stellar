"""Berserker Skills - 광전사 스킬 (광기 역치 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.hp_cost import HPCost

def create_berserker_skills():
    """광전사 10개 스킬 생성 (광기 역치 시스템 - HP↓ → 광기↑)"""

    # 1. 기본 BRV: 베기
    slash = Skill("berserker_slash", "베기", "기본 물리 공격")
    slash.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical")
    ]
    slash.costs = []
    slash.sfx = "slash_heavy.ogg"
    slash.metadata = {}

    # 2. 기본 HP: 강타
    smash = Skill("berserker_smash", "강타", "강력한 HP 공격")
    smash.effects = [
        DamageEffect(DamageType.HP, 1.3, stat_type="physical")
    ]
    smash.costs = []
    smash.sfx = "impact_brutal.ogg"
    smash.metadata = {}

    # 3. 무모한 일격 (HP 소모로 강력한 공격, 광기↑)
    reckless_strike = Skill("berserker_reckless_strike", "무모한 일격",
                           "HP 15% 소모, 광기↑로 강력한 공격")
    reckless_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 2.8, stat_type="physical",
                    conditional_bonus={"condition": "in_berserker_mode", "multiplier": 1.4}),
    ]
    reckless_strike.costs = [MPCost(10), HPCost(percentage=0.15)]
    reckless_strike.sfx = "slash_reckless.ogg"
    # reckless_strike.cooldown = 2  # 쿨다운 시스템 제거됨
    reckless_strike.metadata = {"hp_cost_percent": 0.15}

    # 4. 자해 (HP 20% 감소 → 광기 대폭 증가, 공격력 버프)
    self_harm = Skill("berserker_self_harm", "자해",
                     "HP 20% 감소, 3턴간 공격력 +50%")
    self_harm.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=3)
    ]
    self_harm.costs = [MPCost(8), HPCost(percentage=0.20)]
    self_harm.target_type = "self"
    self_harm.sfx = "blood_splash.ogg"
    # self_harm.cooldown = 4  # 쿨다운 시스템 제거됨
    self_harm.metadata = {"hp_cost_percent": 0.20, "madness_gain": "high"}

    # 5. 전투의 함성 (광역 디버프 + 자신 버프)
    battle_cry = Skill("berserker_battle_cry", "전투의 함성",
                      "적 전체 위축, 자신 속도 +40%")
    battle_cry.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=2),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=3)
    ]
    battle_cry.costs = [MPCost(15)]
    battle_cry.target_type = "all_enemies"
    battle_cry.is_aoe = True
    battle_cry.sfx = "roar_berserker.ogg"
    # battle_cry.cooldown = 3  # 쿨다운 시스템 제거됨
    battle_cry.metadata = {"aoe": True}

    # 6. 피의 분노 (광기에 비례한 공격)
    blood_rage = Skill("berserker_blood_rage", "피의 분노",
                      "광기(HP 손실)에 비례한 강력한 공격")
    blood_rage.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="physical",
                    # HP 손실 비율에 비례 (HP 30%일 때 광기 70 → +140% 피해)
                    gimmick_bonus={"field": "madness", "multiplier": 0.02})
    ]
    blood_rage.costs = [MPCost(18)]
    blood_rage.sfx = "blood_rage.ogg"
    # blood_rage.cooldown = 3  # 쿨다운 시스템 제거됨
    blood_rage.metadata = {"madness_scaling": True}

    # 7. 필사의 공격 (HP 30% 이하일 때 극대 피해)
    desperate_assault = Skill("berserker_desperate_assault", "필사의 공격",
                             "HP 30% 이하 시 극대 피해 (조건부 강화)")
    desperate_assault.effects = [
        DamageEffect(DamageType.BRV_HP, 3.5, stat_type="physical",
                    conditional_bonus={"condition": "hp_below_30", "multiplier": 1.8})
    ]
    desperate_assault.costs = [MPCost(22)]
    desperate_assault.sfx = "slash_desperate.ogg"
    # desperate_assault.cooldown = 4  # 쿨다운 시스템 제거됨
    desperate_assault.metadata = {"requires_low_hp": True}

    # 8. 치유의 포효 (HP 30% 회복 + BRV 50% 회복)
    healing_roar = Skill("berserker_healing_roar", "치유의 포효",
                        "HP 30% 회복 + BRV 50% 회복 (광기↓)")
    healing_roar.effects = [
        HealEffect(percentage=0.30),
        # BRV 회복 효과 추가 필요 (구현 시)
    ]
    healing_roar.costs = [MPCost(20)]
    healing_roar.target_type = "self"
    healing_roar.sfx = "heal_roar.ogg"
    # healing_roar.cooldown = 5  # 쿨다운 시스템 제거됨
    healing_roar.metadata = {"hp_heal": 0.30, "brv_heal": 0.50}

    # 9. 통제된 광기 (HP를 50%로 조정 → 광기 50 유지)
    controlled_fury = Skill("berserker_controlled_fury", "통제된 광기",
                           "HP를 50%로 설정 (광기 최적 구간)")
    controlled_fury.effects = [
        # HP를 최대 HP의 50%로 설정하는 특수 효과
        HealEffect(set_percent=0.50)  # HP를 50%로 설정
    ]
    controlled_fury.costs = [MPCost(25)]
    controlled_fury.target_type = "self"
    controlled_fury.sfx = "controlled_fury.ogg"
    # controlled_fury.cooldown = 6  # 쿨다운 시스템 제거됨
    controlled_fury.metadata = {"hp_set_percent": 0.50, "madness_control": True}

    # 10. 궁극기: 광란의 힘 (HP 1%로 강제 → 광기 100, 폭주)
    ultimate = Skill("berserker_ultimate", "광란의 힘",
                    "HP를 1%로 감소, 광기 100 폭주 상태 진입!")
    ultimate.effects = [
        # HP를 1%로 강제 감소
        DamageEffect(DamageType.BRV, 4.5, stat_type="physical"),
        DamageEffect(DamageType.HP, 4.0, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_UP, 2.0, duration=3),  # 공격력 +200%
        BuffEffect(BuffType.SPEED_UP, 1.0, duration=3)   # 속도 +100%
    ]
    ultimate.costs = [MPCost(30), HPCost(percentage=0.99)]  # HP 99% 소모 (1% 남김)
    ultimate.is_ultimate = True
    ultimate.sfx = "ultimate_berserker.ogg"
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.metadata = {"ultimate": True, "rampage": True, "hp_to_1_percent": True}

    return [slash, smash, reckless_strike, self_harm, battle_cry,
            blood_rage, desperate_assault, healing_roar, controlled_fury, ultimate]

def register_berserker_skills(skill_manager):
    """광전사 스킬 등록"""
    skills = create_berserker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
