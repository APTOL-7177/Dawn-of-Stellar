"""Shaman Skills - 무당 스킬 (저주 변환 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_shaman_skills():
    """무당 10개 스킬 생성 (저주 변환 시스템)"""

    skills = []

    # 1. 기본 BRV: 저주 걸기
    curse = Skill("shaman_curse", "저주 걸기", "저주 스택 획득")
    curse.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 1, max_value=8)
    ]
    curse.costs = []  # 기본 공격은 MP 소모 없음
    curse.sfx = ("skill", "cast_start")  # 저주 걸기
    curse.metadata = {"curse_gain": 1}
    skills.append(curse)

    # 2. 기본 HP: 저주 폭발
    curse_burst = Skill("shaman_curse_burst", "저주 폭발", "저주 소비 공격")
    curse_burst.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 1)
    ]
    curse_burst.costs = []  # 기본 공격은 MP 소모 없음
    curse_burst.sfx = ("skill", "cast_complete")  # 저주 폭발
    curse_burst.metadata = {"curse_cost": 1, "curse_scaling": True}
    skills.append(curse_burst)

    # 3. 역병
    plague = Skill("shaman_plague", "역병", "저주 2스택 획득, 광역 디버프")
    plague.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=3),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 2, max_value=8)
    ]
    plague.costs = []
    # plague.cooldown = 2  # 쿨다운 시스템 제거됨
    plague.is_aoe = True
    plague.sfx = ("character", "status_debuff")  # 역병
    plague.metadata = {"curse_gain": 2, "debuff": True, "aoe": True}
    skills.append(plague)

    # 4. 저주 전이
    curse_transfer = Skill("shaman_curse_transfer", "저주 전이", "저주 2스택 소비, 광역 공격")
    curse_transfer.effects = [
        DamageEffect(DamageType.BRV_HP, 1.7, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 2)
    ]
    curse_transfer.costs = [MPCost(3), StackCost("curse_stacks", 2)]
    # curse_transfer.cooldown = 3  # 쿨다운 시스템 제거됨
    curse_transfer.is_aoe = True
    curse_transfer.sfx = ("skill", "cast_complete")  # 저주 전이
    curse_transfer.metadata = {"curse_cost": 2, "curse_scaling": True, "aoe": True}
    skills.append(curse_transfer)

    # 5. 저주 축적
    curse_accumulate = Skill("shaman_curse_accumulate", "저주 축적", "저주 최대 회복")
    curse_accumulate.effects = [
        GimmickEffect(GimmickOperation.SET, "curse_stacks", 8),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=3)
    ]
    curse_accumulate.costs = [MPCost(4)]
    curse_accumulate.target_type = "self"
    # curse_accumulate.cooldown = 4  # 쿨다운 시스템 제거됨
    curse_accumulate.sfx = ("character", "status_buff")  # 저주 축적
    curse_accumulate.metadata = {"curse_refill": True, "buff": True}
    skills.append(curse_accumulate)

    # 6. 사술
    dark_magic = Skill("shaman_dark_magic", "사술", "저주 3스택 소비, 강력한 디버프")
    dark_magic.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.3}, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.SPEED_DOWN, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 3)
    ]
    dark_magic.costs = [MPCost(6), StackCost("curse_stacks", 3)]
    # dark_magic.cooldown = 4  # 쿨다운 시스템 제거됨
    dark_magic.sfx = ("skill", "ultima")  # 사술
    dark_magic.metadata = {"curse_cost": 3, "curse_scaling": True, "debuff": True}
    skills.append(dark_magic)

    # 7. 영혼 흡수
    soul_drain = Skill("shaman_soul_drain", "영혼 흡수", "저주 4스택 소비, 흡혈 공격")
    soul_drain.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.35}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 4)
    ]
    soul_drain.costs = [MPCost(6), StackCost("curse_stacks", 4)]
    # soul_drain.cooldown = 5  # 쿨다운 시스템 제거됨
    soul_drain.sfx = ("character", "hp_heal")  # 영혼 흡수
    soul_drain.metadata = {"curse_cost": 4, "curse_scaling": True, "drain": True}
    skills.append(soul_drain)

    # 8. 저주의 낙인
    curse_mark = Skill("shaman_curse_mark", "저주의 낙인", "저주 6스택 소비, 절대 저주")
    curse_mark.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.8, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.5, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.5, duration=5),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 6)
    ]
    curse_mark.costs = [MPCost(9), StackCost("curse_stacks", 6)]
    # curse_mark.cooldown = 6  # 쿨다운 시스템 제거됨
    curse_mark.sfx = ("character", "status_debuff")  # 저주의 낙인
    curse_mark.metadata = {"curse_cost": 6, "curse_scaling": True, "debuff": True}
    skills.append(curse_mark)

    # 9. 영혼의 악몽 (NEW - 10번째 스킬)
    nightmare = Skill("shaman_nightmare", "영혼의 악몽", "저주 스택 기반 광역 공포")
    nightmare.effects = [
        DamageEffect(DamageType.BRV_HP, 2.3, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.3}, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.5, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 5)
    ]
    nightmare.costs = [MPCost(10), StackCost("curse_stacks", 5)]
    # nightmare.cooldown = 5  # 쿨다운 시스템 제거됨
    nightmare.is_aoe = True
    nightmare.sfx = ("skill", "cast_complete")  # 영혼의 악몽
    nightmare.metadata = {"curse_cost": 5, "curse_scaling": True, "debuff": True, "aoe": True}
    skills.append(nightmare)

    # 10. 궁극기: 대저주
    ultimate = Skill("shaman_ultimate", "대저주", "모든 저주를 폭발시켜 파멸")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.8, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.5}, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.6, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "curse_stacks", 0)
    ]
    ultimate.costs = [MPCost(30), StackCost("curse_stacks", 1)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "curse_dump": True, "debuff": True, "aoe": True}
    skills.append(ultimate)

    return skills

def register_shaman_skills(skill_manager):
    """무당 스킬 등록"""
    skills = create_shaman_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
