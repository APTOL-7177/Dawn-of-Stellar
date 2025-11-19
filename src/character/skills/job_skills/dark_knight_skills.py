"""Dark Knight Skills - 암흑기사 (어둠 흡수)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.lifesteal_effect import LifestealEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_dark_knight_skills():
    """암흑기사 10개 스킬 생성 (어둠 흡수 시스템)"""
    skills = []

    # 1. 기본 BRV: 어둠 베기
    dark_slash = Skill("dk_dark_slash", "어둠 베기", "어둠 스택 획득")
    dark_slash.effects = [
        DamageEffect(DamageType.BRV, 1.6),
        GimmickEffect(GimmickOperation.ADD, "darkness", 1, max_value=10)
    ]
    dark_slash.costs = []  # 기본 공격은 MP 소모 없음
    dark_slash.sfx = ("combat", "attack_physical")  # 어둠 베기
    dark_slash.metadata = {"darkness_gain": 1}
    skills.append(dark_slash)

    # 2. 기본 HP: 흡혈 강타
    drain = Skill("dk_drain", "흡혈 강타", "어둠 소비 HP공격")
    drain.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "darkness", "multiplier": 0.25}),
        LifestealEffect(0.5),
        GimmickEffect(GimmickOperation.CONSUME, "darkness", 1)
    ]
    drain.costs = []  # 기본 공격은 MP 소모 없음
    drain.sfx = ("character", "hp_heal")  # 흡혈 강타
    drain.metadata = {"darkness_cost": 1, "darkness_scaling": True, "lifesteal": True}
    skills.append(drain)
    
    # 3. 어둠의 오라
    dark_aura = Skill("dk_dark_aura", "어둠의 오라", "지속 피해")
    dark_aura.effects = [
        DamageEffect(DamageType.BRV, 1.0),
        DamageEffect(DamageType.BRV, 1.0),
        DamageEffect(DamageType.BRV, 1.0),
        GimmickEffect(GimmickOperation.ADD, "darkness", 2, max_value=10)
    ]
    dark_aura.costs = []
    # dark_aura.cooldown = 3  # 쿨다운 시스템 제거됨
    dark_aura.sfx = ("character", "status_debuff")  # 어둠의 오라
    dark_aura.metadata = {"multi_hit": 3, "darkness_gain": 2}
    skills.append(dark_aura)

    # 4. 어둠의 보호막
    dark_shield = Skill("dk_dark_shield", "어둠의 보호막", "어둠으로 보호")
    dark_shield.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "darkness", 2)
    ]
    dark_shield.costs = [MPCost(4), StackCost("darkness", 2)]
    dark_shield.target_type = "self"
    # dark_shield.cooldown = 4  # 쿨다운 시스템 제거됨
    dark_shield.sfx = ("skill", "protect")  # 어둠의 보호막
    dark_shield.metadata = {"darkness_cost": 2, "buff": True}
    skills.append(dark_shield)

    # 5. 어둠의 파동
    dark_wave = Skill("dk_dark_wave", "어둠의 파동", "광역 공격")
    dark_wave.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "darkness", "multiplier": 0.3}),
        LifestealEffect(0.4),
        GimmickEffect(GimmickOperation.CONSUME, "darkness", 3)
    ]
    dark_wave.costs = [MPCost(6), StackCost("darkness", 3)]
    # dark_wave.cooldown = 4  # 쿨다운 시스템 제거됨
    dark_wave.is_aoe = True
    dark_wave.sfx = ("skill", "cast_complete")  # 어둠의 파동
    dark_wave.metadata = {"darkness_cost": 3, "darkness_scaling": True, "lifesteal": True, "aoe": True}
    skills.append(dark_wave)

    # 6. 어둠의 검
    dark_blade = Skill("dk_dark_blade", "어둠의 검", "강력한 BRV 공격")
    dark_blade.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "darkness", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.ADD, "darkness", 1, max_value=10)
    ]
    dark_blade.costs = [MPCost(6)]
    # dark_blade.cooldown = 2  # 쿨다운 시스템 제거됨
    dark_blade.sfx = ("combat", "attack_physical")  # 어둠의 검
    dark_blade.metadata = {"darkness_scaling": True, "darkness_gain": 1}
    skills.append(dark_blade)

    # 7. 영혼 포식
    soul_eater = Skill("dk_soul_eater", "영혼 포식", "HP 흡수 공격")
    soul_eater.effects = [
        DamageEffect(DamageType.HP, 1.5, gimmick_bonus={"field": "darkness", "multiplier": 0.3}),
        LifestealEffect(0.6),
        GimmickEffect(GimmickOperation.CONSUME, "darkness", 2)
    ]
    soul_eater.costs = [MPCost(6), StackCost("darkness", 2)]
    # soul_eater.cooldown = 3  # 쿨다운 시스템 제거됨
    soul_eater.sfx = ("character", "hp_heal")  # 영혼 포식
    soul_eater.metadata = {"darkness_cost": 2, "darkness_scaling": True, "lifesteal": True}
    skills.append(soul_eater)

    # 8. 어둠 파쇄
    dark_buster = Skill("dk_dark_buster", "어둠 파쇄", "방어 무시 공격")
    dark_buster.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "darkness", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "darkness", 4)
    ]
    dark_buster.costs = [MPCost(7), StackCost("darkness", 4)]
    # dark_buster.cooldown = 5  # 쿨다운 시스템 제거됨
    dark_buster.sfx = ("combat", "damage_high")  # 어둠 파쇄
    dark_buster.metadata = {"darkness_cost": 4, "darkness_scaling": True}
    skills.append(dark_buster)

    # 9. 어둠 폭발
    dark_explosion = Skill("dk_dark_explosion", "어둠 폭발", "광역 어둠 폭발")
    dark_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "darkness", "multiplier": 0.5}),
        LifestealEffect(0.3),
        GimmickEffect(GimmickOperation.CONSUME, "darkness", 5)
    ]
    dark_explosion.costs = [MPCost(10), StackCost("darkness", 5)]
    dark_explosion.target_type = "all_enemies"
    # dark_explosion.cooldown = 6  # 쿨다운 시스템 제거됨
    dark_explosion.is_aoe = True
    dark_explosion.sfx = ("skill", "ultima")  # 어둠 폭발
    dark_explosion.metadata = {"darkness_cost": 5, "darkness_scaling": True, "lifesteal": True, "aoe": True}
    skills.append(dark_explosion)
    
    # 10. 궁극기: 어둠의 지배자
    ultimate = Skill("dk_ultimate", "어둠의 지배자", "궁극 어둠")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "darkness", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.5),
        LifestealEffect(1.0),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        GimmickEffect(GimmickOperation.SET, "darkness", 0)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "darkness_consume_all": True, "darkness_scaling": True, "lifesteal": True, "aoe": True}
    skills.append(ultimate)

    return skills

def register_dark_knight_skills(sm):
    for s in create_dark_knight_skills():
        sm.register_skill(s)
    return [s.skill_id for s in create_dark_knight_skills()]
