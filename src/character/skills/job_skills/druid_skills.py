"""Druid Skills - 드루이드 스킬 (변신 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_druid_skills():
    """드루이드 9개 스킬 생성"""

    # 1. 기본 BRV: 자연의 힘
    nature_power = Skill("druid_nature_power", "자연의 힘", "자연 포인트 획득")
    nature_power.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 1, max_value=5)
    ]
    nature_power.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 가시 덩굴
    thorn_vine = Skill("druid_thorn_vine", "가시 덩굴", "자연 포인트 소비 공격")
    thorn_vine.effects = [
        DamageEffect(DamageType.HP, 1.1, gimmick_bonus={"field": "nature_points", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 1)
    ]
    thorn_vine.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 곰 변신
    bear_form = Skill("druid_bear_form", "곰 변신", "방어 태세 변신")
    bear_form.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=4),
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 1, max_value=5)
    ]
    bear_form.costs = [MPCost(7)]
    bear_form.target_type = "self"
    bear_form.cooldown = 3

    # 4. 표범 변신
    cat_form = Skill("druid_cat_form", "표범 변신", "속도 태세 변신")
    cat_form.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        BuffEffect(BuffType.SPEED_UP, 0.7, duration=4),
        BuffEffect(BuffType.EVASION_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 1, max_value=5)
    ]
    cat_form.costs = [MPCost(7)]
    cat_form.target_type = "self"
    cat_form.cooldown = 3

    # 5. 치유의 숲
    healing_forest = Skill("druid_healing_forest", "치유의 숲", "자연 2포인트 소비, 회복")
    healing_forest.effects = [
        HealEffect(HealType.HP, percentage=0.3, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 2)
    ]
    healing_forest.costs = [MPCost(9), StackCost("nature_points", 2)]
    healing_forest.target_type = "party"
    healing_forest.cooldown = 4

    # 6. 자연의 축복
    nature_blessing = Skill("druid_nature_blessing", "자연의 축복", "자연 최대 회복")
    nature_blessing.effects = [
        GimmickEffect(GimmickOperation.SET, "nature_points", 5),
        BuffEffect(BuffType.REGEN, 0.3, duration=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4)
    ]
    nature_blessing.costs = [MPCost(10)]
    nature_blessing.target_type = "self"
    nature_blessing.cooldown = 5

    # 7. 독수리 변신
    eagle_form = Skill("druid_eagle_form", "독수리 변신", "자연 3포인트 소비, 공중 공격")
    eagle_form.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "nature_points", "multiplier": 0.4}, stat_type="magical"),
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 3)
    ]
    eagle_form.costs = [MPCost(11), StackCost("nature_points", 3)]
    eagle_form.cooldown = 4

    # 8. 늑대 변신
    wolf_form = Skill("druid_wolf_form", "늑대 변신", "자연 4포인트 소비, 광역 공격")
    wolf_form.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "nature_points", "multiplier": 0.35}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.5, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 4)
    ]
    wolf_form.costs = [MPCost(14), StackCost("nature_points", 4)]
    wolf_form.cooldown = 5
    wolf_form.is_aoe = True

    # 9. 궁극기: 진 변신
    ultimate = Skill("druid_ultimate", "진 변신", "완전한 변신으로 자연과 하나")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "nature_points", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "nature_points", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.8, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "nature_points", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("nature_points", 1)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    ultimate.cooldown = 10

    return [nature_power, thorn_vine, bear_form, cat_form, healing_forest,
            nature_blessing, eagle_form, wolf_form, ultimate]

def register_druid_skills(skill_manager):
    """드루이드 스킬 등록"""
    skills = create_druid_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
