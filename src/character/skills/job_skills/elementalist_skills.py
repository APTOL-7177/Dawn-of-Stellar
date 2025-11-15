"""Elementalist Skills - 정령술사 스킬 (정령 소환 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_elementalist_skills():
    """정령술사 9개 스킬 생성"""

    # 1. 기본 BRV: 정령 소환
    spirit_call = Skill("elementalist_spirit_call", "정령 소환", "정령 포인트 획득")
    spirit_call.effects = [
        DamageEffect(DamageType.BRV, 1.3, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "spirit_count", 1, max_value=4)
    ]
    spirit_call.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 정령 공격
    spirit_attack = Skill("elementalist_spirit_attack", "정령 공격", "정령 소비 공격")
    spirit_attack.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "spirit_count", "multiplier": 0.4}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "spirit_count", 1)
    ]
    spirit_attack.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 화염 정령
    fire_spirit = Skill("elementalist_fire_spirit", "화염 정령", "화염 정령 특수 소환")
    fire_spirit.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "spirit_count", 1, max_value=4),
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3)
    ]
    fire_spirit.costs = [MPCost(7)]
    fire_spirit.target_type = "self"
    fire_spirit.cooldown = 2

    # 4. 물 정령
    water_spirit = Skill("elementalist_water_spirit", "물 정령", "물 정령 특수 소환")
    water_spirit.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "spirit_count", 1, max_value=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3)
    ]
    water_spirit.costs = [MPCost(7)]
    water_spirit.target_type = "self"
    water_spirit.cooldown = 2

    # 5. 바람 정령
    wind_spirit = Skill("elementalist_wind_spirit", "바람 정령", "바람 정령 특수 소환")
    wind_spirit.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "spirit_count", 1, max_value=4),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=3)
    ]
    wind_spirit.costs = [MPCost(7)]
    wind_spirit.target_type = "self"
    wind_spirit.cooldown = 2

    # 6. 대지 정령
    earth_spirit = Skill("elementalist_earth_spirit", "대지 정령", "대지 정령 특수 소환")
    earth_spirit.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "spirit_count", 2, max_value=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3)
    ]
    earth_spirit.costs = [MPCost(9)]
    earth_spirit.target_type = "self"
    earth_spirit.cooldown = 3

    # 7. 정령 융합
    spirit_fusion = Skill("elementalist_spirit_fusion", "정령 융합", "정령 2체 융합 공격")
    spirit_fusion.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "spirit_count", "multiplier": 0.5}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "spirit_count", 2)
    ]
    spirit_fusion.costs = [MPCost(10), StackCost("spirit_count", 2)]
    spirit_fusion.cooldown = 3

    # 8. 정령왕 소환
    spirit_king = Skill("elementalist_spirit_king", "정령왕 소환", "정령 3체 소비, 정령왕 공격")
    spirit_king.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "spirit_count", "multiplier": 0.6}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.8, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "spirit_count", 3)
    ]
    spirit_king.costs = [MPCost(14), StackCost("spirit_count", 3)]
    spirit_king.cooldown = 5
    spirit_king.is_aoe = True

    # 9. 궁극기: 정령 대결집
    ultimate = Skill("elementalist_ultimate", "정령 대결집", "모든 정령의 힘을 결집")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "spirit_count", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "spirit_count", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.8, gimmick_bonus={"field": "spirit_count", "multiplier": 0.7}, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=4),
        GimmickEffect(GimmickOperation.SET, "spirit_count", 0)
    ]
    ultimate.costs = [MPCost(22), StackCost("spirit_count", 1)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    ultimate.cooldown = 10

    return [spirit_call, spirit_attack, fire_spirit, water_spirit, wind_spirit,
            earth_spirit, spirit_fusion, spirit_king, ultimate]

def register_elementalist_skills(skill_manager):
    """정령술사 스킬 등록"""
    skills = create_elementalist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
