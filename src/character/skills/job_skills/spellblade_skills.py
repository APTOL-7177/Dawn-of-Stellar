"""Spellblade Skills - 마검사 스킬 (원소 주입 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_spellblade_skills():
    """마검사 9개 스킬 생성"""

    # 1. 기본 BRV: 마력 베기
    magic_slash = Skill("spellblade_magic_slash", "마력 베기", "마력 스택 획득")
    magic_slash.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 1, max_value=6)
    ]
    magic_slash.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 원소 베기
    elemental_slash = Skill("spellblade_elemental_slash", "원소 베기", "마력 소비 공격")
    elemental_slash.effects = [
        DamageEffect(DamageType.HP, 1.1, gimmick_bonus={"field": "mana_blade", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "mana_blade", 1)
    ]
    elemental_slash.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 화염 주입
    fire_infusion = Skill("spellblade_fire_infusion", "화염 주입", "마력 2스택 획득 + 화염 버프")
    fire_infusion.effects = [
        DamageEffect(DamageType.BRV, 1.7, stat_type="magical"),  # 마법 주입
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 2, max_value=6)
    ]
    fire_infusion.costs = [MPCost(7)]
    fire_infusion.target_type = "self"
    fire_infusion.cooldown = 2

    # 4. 빙결 주입
    ice_infusion = Skill("spellblade_ice_infusion", "빙결 주입", "마력 2스택 획득 + 빙결 버프")
    ice_infusion.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),  # 마법 주입
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 2, max_value=6)
    ]
    ice_infusion.costs = [MPCost(7)]
    ice_infusion.target_type = "self"
    ice_infusion.cooldown = 2

    # 5. 번개 주입
    lightning_infusion = Skill("spellblade_lightning_infusion", "번개 주입", "마력 2스택 획득 + 번개 버프")
    lightning_infusion.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),  # 마법 주입
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 2, max_value=6)
    ]
    lightning_infusion.costs = [MPCost(7)]
    lightning_infusion.target_type = "self"
    lightning_infusion.cooldown = 2

    # 6. 마검 난무
    magic_blade_dance = Skill("spellblade_magic_blade_dance", "마검 난무", "마력 3스택 소비, 연속 공격")
    magic_blade_dance.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "mana_blade", "multiplier": 0.25}),
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "mana_blade", "multiplier": 0.25}),
        DamageEffect(DamageType.HP, 1.3),
        GimmickEffect(GimmickOperation.CONSUME, "mana_blade", 3)
    ]
    magic_blade_dance.costs = [MPCost(11), StackCost("mana_blade", 3)]
    magic_blade_dance.cooldown = 4

    # 7. 마력 폭발
    mana_burst = Skill("spellblade_mana_burst", "마력 폭발", "마력 최대 회복")
    mana_burst.effects = [
        GimmickEffect(GimmickOperation.SET, "mana_blade", 6),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=4)
    ]
    mana_burst.costs = [MPCost(10)]
    mana_burst.target_type = "self"
    mana_burst.cooldown = 5

    # 8. 원소 폭풍
    elemental_storm = Skill("spellblade_elemental_storm", "원소 폭풍", "마력 5스택 소비, 광역 공격")
    elemental_storm.effects = [
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "mana_blade", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 1.8),
        GimmickEffect(GimmickOperation.CONSUME, "mana_blade", 5)
    ]
    elemental_storm.costs = [MPCost(15), StackCost("mana_blade", 5)]
    elemental_storm.cooldown = 6
    elemental_storm.is_aoe = True

    # 9. 궁극기: 마검 극의
    ultimate = Skill("spellblade_ultimate", "마검 극의", "모든 마력으로 궁극의 마검")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "mana_blade", "multiplier": 0.5}),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "mana_blade", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.0, gimmick_bonus={"field": "mana_blade", "multiplier": 0.6}),
        BuffEffect(BuffType.ATTACK_UP, 0.7, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.7, duration=5),
        GimmickEffect(GimmickOperation.SET, "mana_blade", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("mana_blade", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10

    return [magic_slash, elemental_slash, fire_infusion, ice_infusion, lightning_infusion,
            magic_blade_dance, mana_burst, elemental_storm, ultimate]

def register_spellblade_skills(skill_manager):
    """마검사 스킬 등록"""
    skills = create_spellblade_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
