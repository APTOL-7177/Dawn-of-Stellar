"""Berserker Skills - 광전사 스킬 (분노 관리 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_berserker_skills():
    """광전사 10개 스킬 생성 (분노 관리 시스템)"""

    # 1. 기본 BRV: 야만적 일격 (분노 생성)
    savage_strike = Skill("berserker_savage_strike", "야만적 일격", "기본 공격, 분노 +8")
    savage_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "rage", 8, max_value=100)
    ]
    savage_strike.costs = []  # 기본 공격은 MP 소모 없음
    savage_strike.metadata = {"rage_change": 8}

    # 2. 기본 HP: 잔혹한 강습 (분노 생성)
    brutal_assault = Skill("berserker_brutal_assault", "잔혹한 강습", "HP 공격, 분노 +12")
    brutal_assault.effects = [
        DamageEffect(DamageType.HP, 1.3),
        GimmickEffect(GimmickOperation.ADD, "rage", 12, max_value=100)
    ]
    brutal_assault.costs = []  # 기본 공격은 MP 소모 없음
    brutal_assault.metadata = {"rage_change": 12}

    # 3. 분노의 일격 (분노에 비례한 데미지)
    rage_strike = Skill("berserker_rage_strike", "분노의 일격",
                       "분노에 비례한 강력한 BRV 공격, 분노 +15")
    rage_strike.effects = [
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "rage", "multiplier": 0.015}),  # 분노 1당 +1.5% 피해
        GimmickEffect(GimmickOperation.ADD, "rage", 15, max_value=100)
    ]
    rage_strike.costs = [MPCost(12)]
    rage_strike.metadata = {"rage_change": 15, "rage_scaling": True}

    # 4. 피의 광기 (분노 소비로 HP 공격)
    blood_frenzy = Skill("berserker_blood_frenzy", "피의 광기",
                        "분노 소비하여 강력한 HP 공격 (분노 -25)")
    blood_frenzy.effects = [
        DamageEffect(DamageType.HP, 2.5,
                    gimmick_bonus={"field": "rage", "multiplier": 0.02}),  # 분노 1당 +2% 피해
        GimmickEffect(GimmickOperation.ADD, "rage", -25, min_value=0)
    ]
    blood_frenzy.costs = [MPCost(15)]
    blood_frenzy.metadata = {"rage_change": -25, "rage_scaling": True}

    # 5. 광전사 모드 (분노 생성 증가 버프)
    berserk_mode = Skill("berserker_berserk_mode", "광전사 모드",
                        "3턴간 공격력 +40%, 분노 획득 +50%")
    berserk_mode.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "rage", 20, max_value=100)
    ]
    berserk_mode.costs = [MPCost(18)]
    berserk_mode.target_type = "self"
    berserk_mode.cooldown = 5
    berserk_mode.metadata = {"rage_change": 20, "berserk_buff": True}

    # 6. 전쟁의 함성 (광역 공격 + 분노 생성)
    warcry = Skill("berserker_warcry", "전쟁의 함성",
                  "광역 BRV 공격, 분노 +20")
    warcry.effects = [
        DamageEffect(DamageType.BRV, 1.8,
                    gimmick_bonus={"field": "rage", "multiplier": 0.01}),  # 분노 1당 +1% 피해
        GimmickEffect(GimmickOperation.ADD, "rage", 20, max_value=100)
    ]
    warcry.costs = [MPCost(16)]
    warcry.target_type = "all_enemies"
    warcry.is_aoe = True
    warcry.metadata = {"rage_change": 20}

    # 7. 분노 폭발 (높은 분노 소비로 폭발적 데미지)
    rage_explosion = Skill("berserker_rage_explosion", "분노 폭발",
                          "분노 50 이상 필요, 분노 전부 소비하여 극대 피해")
    rage_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0,
                    gimmick_bonus={"field": "rage", "multiplier": 0.03}),  # 분노 1당 +3% 피해
        GimmickEffect(GimmickOperation.SET, "rage", 0)  # 분노 전부 소비
    ]
    rage_explosion.costs = [MPCost(22)]
    rage_explosion.cooldown = 4
    rage_explosion.metadata = {"rage_consumed": "all", "min_rage": 50}

    # 8. 진정하기 (분노 감소로 방어 버프)
    calm_down = Skill("berserker_calm_down", "진정하기",
                     "분노 -40, 방어력 +50% 2턴")
    calm_down.effects = [
        GimmickEffect(GimmickOperation.ADD, "rage", -40, min_value=0),
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=2),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.3, duration=2)
    ]
    calm_down.costs = [MPCost(10)]
    calm_down.target_type = "self"
    calm_down.cooldown = 4
    calm_down.metadata = {"rage_change": -40, "defensive": True}

    # 9. 광란 (연속 공격 + 분노 대량 생성)
    rampage = Skill("berserker_rampage", "광란",
                   "3회 연속 공격, 분노 +30")
    rampage.effects = [
        DamageEffect(DamageType.BRV, 1.2,
                    gimmick_bonus={"field": "rage", "multiplier": 0.01}),
        DamageEffect(DamageType.BRV, 1.2,
                    gimmick_bonus={"field": "rage", "multiplier": 0.01}),
        DamageEffect(DamageType.BRV, 1.2,
                    gimmick_bonus={"field": "rage", "multiplier": 0.01}),
        GimmickEffect(GimmickOperation.ADD, "rage", 30, max_value=100)
    ]
    rampage.costs = [MPCost(20)]
    rampage.cooldown = 5
    rampage.metadata = {"rage_change": 30, "multi_hit": 3}

    # 10. 궁극기: 분노의 화신 (최대 분노로 압도적 공격)
    ultimate_fury = Skill("berserker_ultimate_fury", "분노의 화신",
                         "분노 70 이상 필요, 모든 분노를 소비하여 파괴적 공격")
    ultimate_fury.effects = [
        DamageEffect(DamageType.BRV, 3.5,
                    gimmick_bonus={"field": "rage", "multiplier": 0.04}),  # 분노 1당 +4% 피해
        DamageEffect(DamageType.HP, 3.0,
                    gimmick_bonus={"field": "rage", "multiplier": 0.03}),  # 분노 1당 +3% 피해
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=2),  # 공격 후 버프
        GimmickEffect(GimmickOperation.SET, "rage", 0)  # 모든 분노 소비
    ]
    ultimate_fury.costs = [MPCost(30)]
    ultimate_fury.is_ultimate = True
    ultimate_fury.cooldown = 8
    ultimate_fury.metadata = {"rage_consumed": "all", "min_rage": 70, "ultimate": True}

    return [savage_strike, brutal_assault, rage_strike, blood_frenzy, berserk_mode,
            warcry, rage_explosion, calm_down, rampage, ultimate_fury]

def register_berserker_skills(skill_manager):
    """광전사 스킬 등록"""
    skills = create_berserker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
