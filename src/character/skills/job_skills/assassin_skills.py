"""Assassin Skills - 암살자 스킬 (은신/크리티컬 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_assassin_skills():
    """암살자 9개 스킬 생성"""

    # 1. 기본 BRV: 그림자 베기
    shadow_slash = Skill("assassin_shadow_slash", "그림자 베기", "은신 포인트 획득")
    shadow_slash.effects = [
        DamageEffect(DamageType.BRV, 1.4),
        GimmickEffect(GimmickOperation.ADD, "stealth_points", 1, max_value=5)
    ]
    shadow_slash.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 암살
    assassinate = Skill("assassin_assassinate", "암살", "은신 포인트로 치명타 증가")
    assassinate.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "stealth_points", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "stealth_points", 1)
    ]
    assassinate.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 배후 습격
    backstab = Skill("assassin_backstab", "배후 습격", "강력한 배후 공격")
    backstab.effects = [
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "stealth_points", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.ADD, "stealth_points", 1, max_value=5)
    ]
    backstab.costs = [MPCost(6)]
    backstab.cooldown = 2

    # 4. 은신
    vanish = Skill("assassin_vanish", "은신", "완전 은신 상태 진입")
    vanish.effects = [
        GimmickEffect(GimmickOperation.SET, "stealth_points", 5),
        BuffEffect(BuffType.EVASION_UP, 0.5, duration=3)
    ]
    vanish.costs = [MPCost(8)]
    vanish.target_type = "self"
    vanish.cooldown = 4

    # 5. 독침
    poison_dart = Skill("assassin_poison_dart", "독침", "은신 2스택 소비, 독 데미지")
    poison_dart.effects = [
        DamageEffect(DamageType.BRV_HP, 1.6, gimmick_bonus={"field": "stealth_points", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "stealth_points", 2)
    ]
    poison_dart.costs = [MPCost(9), StackCost("stealth_points", 2)]
    poison_dart.cooldown = 3

    # 6. 연속 베기
    rapid_stab = Skill("assassin_rapid_stab", "연속 베기", "빠른 3연속 공격")
    rapid_stab.effects = [
        DamageEffect(DamageType.BRV, 0.9),
        DamageEffect(DamageType.BRV, 0.9),
        DamageEffect(DamageType.BRV, 0.9),
        GimmickEffect(GimmickOperation.ADD, "stealth_points", 2, max_value=5)
    ]
    rapid_stab.costs = [MPCost(7)]
    rapid_stab.cast_time = 0.7
    rapid_stab.cooldown = 2

    # 7. 죽음의 표식
    death_mark = Skill("assassin_death_mark", "죽음의 표식", "은신 3스택 소비, 표식 부여")
    death_mark.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "stealth_points", "multiplier": 0.4}),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "stealth_points", 3)
    ]
    death_mark.costs = [MPCost(10), StackCost("stealth_points", 3)]
    death_mark.cooldown = 4

    # 8. 목 베기
    throat_cut = Skill("assassin_throat_cut", "목 베기", "은신 4스택 소비, 침묵 + 출혈")
    throat_cut.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "stealth_points", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.CONSUME, "stealth_points", 4)
    ]
    throat_cut.costs = [MPCost(12), StackCost("stealth_points", 4)]
    throat_cut.cooldown = 5

    # 9. 궁극기: 완벽한 암살
    ultimate = Skill("assassin_ultimate", "완벽한 암살", "모든 은신 포인트로 완벽한 일격")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "stealth_points", "multiplier": 0.4}),
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "stealth_points", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 2.5, gimmick_bonus={"field": "stealth_points", "multiplier": 0.6}),
        GimmickEffect(GimmickOperation.SET, "stealth_points", 0)
    ]
    ultimate.costs = [MPCost(20), StackCost("stealth_points", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10

    return [shadow_slash, assassinate, backstab, vanish, poison_dart,
            rapid_stab, death_mark, throat_cut, ultimate]

def register_assassin_skills(skill_manager):
    """암살자 스킬 등록"""
    skills = create_assassin_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
