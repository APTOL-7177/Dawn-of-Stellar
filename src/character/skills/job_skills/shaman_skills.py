"""Shaman Skills - 무당 스킬 (저주 변환 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_shaman_skills():
    """무당 9개 스킬 생성"""

    # 1. 기본 BRV: 저주 걸기
    curse = Skill("shaman_curse", "저주 걸기", "저주 스택 획득")
    curse.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 1, max_value=8)
    ]
    curse.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 저주 폭발
    curse_burst = Skill("shaman_curse_burst", "저주 폭발", "저주 소비 공격")
    curse_burst.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 1)
    ]
    curse_burst.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 역병
    plague = Skill("shaman_plague", "역병", "저주 2스택 획득, 광역 디버프")
    plague.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=3),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 2, max_value=8)
    ]
    plague.costs = [MPCost(7)]
    plague.cooldown = 2
    plague.is_aoe = True

    # 4. 저주 전이
    curse_transfer = Skill("shaman_curse_transfer", "저주 전이", "저주 2스택 소비, 광역 공격")
    curse_transfer.effects = [
        DamageEffect(DamageType.BRV_HP, 1.7, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 2)
    ]
    curse_transfer.costs = [MPCost(8), StackCost("curse_stacks", 2)]
    curse_transfer.cooldown = 3
    curse_transfer.is_aoe = True

    # 5. 저주 축적
    curse_accumulate = Skill("shaman_curse_accumulate", "저주 축적", "저주 최대 회복")
    curse_accumulate.effects = [
        GimmickEffect(GimmickOperation.SET, "curse_stacks", 8),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=3)
    ]
    curse_accumulate.costs = [MPCost(9)]
    curse_accumulate.target_type = "self"
    curse_accumulate.cooldown = 4

    # 6. 사술
    dark_magic = Skill("shaman_dark_magic", "사술", "저주 3스택 소비, 강력한 디버프")
    dark_magic.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.3}, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.SPEED_DOWN, 0.3, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 3)
    ]
    dark_magic.costs = [MPCost(11), StackCost("curse_stacks", 3)]
    dark_magic.cooldown = 4

    # 7. 영혼 흡수
    soul_drain = Skill("shaman_soul_drain", "영혼 흡수", "저주 4스택 소비, 흡혈 공격")
    soul_drain.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.35}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 4)
    ]
    soul_drain.costs = [MPCost(12), StackCost("curse_stacks", 4)]
    soul_drain.cooldown = 5

    # 8. 저주의 낙인
    curse_mark = Skill("shaman_curse_mark", "저주의 낙인", "저주 6스택 소비, 절대 저주")
    curse_mark.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.8, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.5, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.5, duration=5),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 6)
    ]
    curse_mark.costs = [MPCost(15), StackCost("curse_stacks", 6)]
    curse_mark.cooldown = 6

    # 9. 궁극기: 대저주
    ultimate = Skill("shaman_ultimate", "대저주", "모든 저주를 폭발시켜 파멸")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.8, gimmick_bonus={"field": "curse_stacks", "multiplier": 0.5}, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.6, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "curse_stacks", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("curse_stacks", 1)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    ultimate.cooldown = 10

    return [curse, curse_burst, plague, curse_transfer, curse_accumulate,
            dark_magic, soul_drain, curse_mark, ultimate]

def register_shaman_skills(skill_manager):
    """무당 스킬 등록"""
    skills = create_shaman_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
