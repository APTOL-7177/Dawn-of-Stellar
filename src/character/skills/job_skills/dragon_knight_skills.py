"""Dragon Knight Skills - 용기사 스킬 (화염/용의 힘 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.taunt_effect import TauntEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_dragon_knight_skills():
    """용기사 10개 스킬 생성 (화염/용의 힘 시스템)"""

    skills = []

    # 1. 기본 BRV: 화염 베기
    flame_slash = Skill("dragon_knight_flame_slash", "화염 베기", "용의 힘 스택 획득")
    flame_slash.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "dragon_power", 1, max_value=5)
    ]
    flame_slash.costs = []  # 기본 공격은 MP 소모 없음
    flame_slash.sfx = ("skill", "fire")  # 화염 베기
    flame_slash.metadata = {"dragon_power_gain": 1}
    skills.append(flame_slash)

    # 2. 기본 HP: 용의 돌진
    dragon_dive = Skill("dragon_knight_dragon_dive", "용의 돌진", "용의 힘 소비 공격")
    dragon_dive.effects = [
        DamageEffect(DamageType.HP, 1.1, gimmick_bonus={"field": "dragon_power", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "dragon_power", 1)
    ]
    dragon_dive.costs = []  # 기본 공격은 MP 소모 없음
    dragon_dive.sfx = ("combat", "damage_high")  # 용의 돌진
    dragon_dive.metadata = {"dragon_power_cost": 1, "dragon_scaling": True}
    skills.append(dragon_dive)

    # 3. 화염 숨결
    fire_breath = Skill("dragon_knight_fire_breath", "화염 숨결", "광역 화염 피해")
    fire_breath.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "dragon_power", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.ADD, "dragon_power", 1, max_value=5)
    ]
    fire_breath.costs = []
    # fire_breath.cooldown = 2  # 쿨다운 시스템 제거됨
    fire_breath.target_type = "all_enemies"
    fire_breath.is_aoe = True
    fire_breath.sfx = ("skill", "fire3")  # 화염 숨결
    fire_breath.metadata = {"dragon_scaling": True, "dragon_power_gain": 1, "aoe": True}
    skills.append(fire_breath)

    # 4. 작열 강타
    burning_strike = Skill("dragon_knight_burning_strike", "작열 강타", "용의 힘 2스택 소비")
    burning_strike.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        DamageEffect(DamageType.HP, 1.3, gimmick_bonus={"field": "dragon_power", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "dragon_power", 2)
    ]
    burning_strike.costs = [MPCost(5), StackCost("dragon_power", 2)]
    # burning_strike.cooldown = 3  # 쿨다운 시스템 제거됨
    burning_strike.sfx = ("combat", "critical")  # 작열 강타
    burning_strike.metadata = {"dragon_power_cost": 2, "dragon_scaling": True}
    skills.append(burning_strike)

    # 5. 용의 분노
    dragon_rage = Skill("dragon_knight_dragon_rage", "용의 분노", "용표 1개 획득 + 버프")
    dragon_rage.effects = [
        GimmickEffect(GimmickOperation.ADD, "dragon_marks", 1, max_value=3),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4)
    ]
    dragon_rage.costs = [MPCost(6)]
    dragon_rage.target_type = "self"
    # dragon_rage.cooldown = 5  # 쿨다운 시스템 제거됨
    dragon_rage.sfx = ("character", "status_buff")  # 용의 분노
    dragon_rage.metadata = {"dragon_mark_gain": 1, "buff": True}
    skills.append(dragon_rage)

    # 6. 용의 비늘
    dragon_scales = Skill("dragon_knight_dragon_scales", "용의 비늘", "방어 태세")
    dragon_scales.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.ADD, "dragon_power", 2, max_value=5)
    ]
    dragon_scales.costs = [MPCost(3)]
    dragon_scales.target_type = "self"
    # dragon_scales.cooldown = 3  # 쿨다운 시스템 제거됨
    dragon_scales.sfx = ("skill", "protect")  # 용의 비늘
    dragon_scales.metadata = {"buff": True, "dragon_power_gain": 2}
    skills.append(dragon_scales)

    # 7. 지옥불 폭발
    inferno_burst = Skill("dragon_knight_inferno_burst", "지옥불 폭발", "용의 힘 3스택 소비 광역 폭발")
    inferno_burst.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "dragon_power", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "dragon_power", 3)
    ]
    inferno_burst.costs = [MPCost(7), StackCost("dragon_power", 3)]
    # inferno_burst.cooldown = 4  # 쿨다운 시스템 제거됨
    inferno_burst.target_type = "all_enemies"
    inferno_burst.is_aoe = True
    inferno_burst.sfx = ("skill", "flare")  # 지옥불 폭발
    inferno_burst.metadata = {"dragon_power_cost": 3, "dragon_scaling": True, "aoe": True}
    skills.append(inferno_burst)

    # 8. 용의 날개
    dragon_wings = Skill("dragon_knight_dragon_wings", "용의 날개", "용의 힘 4스택 소비 대공격")
    dragon_wings.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "dragon_power", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 1.5),
        GimmickEffect(GimmickOperation.CONSUME, "dragon_power", 4)
    ]
    dragon_wings.costs = [MPCost(9), StackCost("dragon_power", 4)]
    # dragon_wings.cooldown = 6  # 쿨다운 시스템 제거됨
    dragon_wings.sfx = ("combat", "damage_high")  # 용의 날개
    dragon_wings.metadata = {"dragon_power_cost": 4, "dragon_scaling": True}
    skills.append(dragon_wings)

    # 9. 용의 포효 (NEW - 10번째 스킬로 만들기 위해 추가)
    dragon_roar = Skill("dragon_knight_dragon_roar", "용의 포효", "용의 힘 회복 + 파티 버프")
    dragon_roar.effects = [
        GimmickEffect(GimmickOperation.ADD, "dragon_power", 3, max_value=5),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4, is_party_wide=True)
    ]
    dragon_roar.costs = [MPCost(7)]
    dragon_roar.target_type = "party"
    # dragon_roar.cooldown = 5  # 쿨다운 시스템 제거됨
    dragon_roar.sfx = ("skill", "roar")  # 용의 포효
    dragon_roar.metadata = {"dragon_power_gain": 3, "buff": True, "party_wide": True}
    skills.append(dragon_roar)

    # 10. 용의 각인 (용표 1개 소비 - 강력한 단일 공격)
    dragon_mark_strike = Skill("dragon_knight_dragon_mark_strike", "용의 각인", "용표 1개 소비하여 강력한 일격")
    dragon_mark_strike.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "dragon_power", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 2.0, gimmick_bonus={"field": "dragon_power", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.CONSUME, "dragon_marks", 1)
    ]
    dragon_mark_strike.costs = [MPCost(8), StackCost("dragon_marks", 1)]
    dragon_mark_strike.sfx = ("combat", "critical")  # 용의 각인
    dragon_mark_strike.metadata = {"dragon_mark_cost": 1, "dragon_scaling": True, "high_damage": True}
    skills.append(dragon_mark_strike)

    # 11. 용의 폭풍 (용표 2개 소비 - 광역 공격)
    dragon_storm = Skill("dragon_knight_dragon_storm", "용의 폭풍", "용표 2개 소비하여 광역 화염 폭풍")
    dragon_storm.effects = [
        DamageEffect(DamageType.BRV, 2.2, gimmick_bonus={"field": "dragon_power", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 1.8, gimmick_bonus={"field": "dragon_power", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "dragon_marks", 2)
    ]
    dragon_storm.costs = [MPCost(12), StackCost("dragon_marks", 2)]
    dragon_storm.target_type = "all_enemies"
    dragon_storm.is_aoe = True
    dragon_storm.sfx = ("skill", "flare")  # 용의 폭풍
    dragon_storm.metadata = {"dragon_mark_cost": 2, "dragon_scaling": True, "aoe": True}
    skills.append(dragon_storm)

    # 12. 궁극기: 진 드래곤 (용표 3개 소비 - 드래곤 변신)
    ultimate = Skill("dragon_knight_ultimate", "진 드래곤", "용표 3개로 용으로 변신하여 파멸의 불길")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "dragon_power", "multiplier": 0.4}),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "dragon_power", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 3.0, gimmick_bonus={"field": "dragon_power", "multiplier": 0.6}),
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=6),
        BuffEffect(BuffType.CRITICAL_UP, 0.6, duration=6),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=6),
        GimmickEffect(GimmickOperation.ADD, "dragon_marks", 1, max_value=3),  # 용표 1개 획득
        GimmickEffect(GimmickOperation.CONSUME, "dragon_marks", 3)  # 용표 소비
    ]
    ultimate.costs = [MPCost(25), StackCost("dragon_marks", 3)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 20  # 궁극기 쿨타임 20턴
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "dragon_transform": True, "dragon_mark_cost": 3, "dragon_mark_gain": 1, "dragon_scaling": True, "aoe": True, "buff": True}
    skills.append(ultimate)

    return skills

def register_dragon_knight_skills(skill_manager):
    """용기사 스킬 등록"""
    skills = create_dragon_knight_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 드래곤의 포효
\n    return [s.skill_id for s in skills]\n