"""Gladiator Skills - 검투사 스킬 (군중의 환호 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_gladiator_skills():
    """검투사 10개 스킬 생성 (군중의 환호 시스템)"""

    # 1. 기본 BRV: 투기장 타격
    arena_strike = Skill("gladiator_arena_strike", "투기장 타격", "기본 공격 (환호 +5)")
    arena_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 5, max_value=100)  # 환호 +5
    ]
    arena_strike.costs = []  # 기본 공격은 MP 소모 없음
    arena_strike.sfx = ("combat", "attack_physical")  # 투기장 타격
    arena_strike.metadata = {"cheer_gain": 5}

    # 2. 기본 HP: 명예의 일격
    honor_strike = Skill("gladiator_honor_strike", "명예의 일격", "HP 공격 (환호 +10)")
    honor_strike.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 10, max_value=100)  # 환호 +10
    ]
    honor_strike.costs = []  # 기본 공격은 MP 소모 없음
    honor_strike.sfx = ("combat", "critical")  # 명예의 일격
    honor_strike.metadata = {"cheer_gain": 10}

    # 3. 화려한 공격 (환호 대폭 증가)
    spectacular_attack = Skill("gladiator_spectacular", "화려한 공격", "쇼맨십 공격으로 환호 +20")
    spectacular_attack.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 20, max_value=100)  # 환호 +20
    ]
    spectacular_attack.costs = []
    spectacular_attack.sfx = ("combat", "attack_physical")  # 화려한 공격
    # spectacular_attack.cooldown = 2  # 쿨다운 시스템 제거됨
    spectacular_attack.metadata = {"showmanship": True, "cheer_gain": 20}

    # 4. 군중 도발 (환호에 비례한 공격)
    taunt_crowd = Skill("gladiator_taunt", "군중 도발", "환호에 비례한 강력한 공격")
    taunt_crowd.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="physical",
                    gimmick_bonus={"field": "cheer", "multiplier": 0.02}),  # 환호 1당 +2% 피해
        GimmickEffect(GimmickOperation.ADD, "cheer", 15, max_value=100)
    ]
    taunt_crowd.costs = [MPCost(6)]
    taunt_crowd.sfx = ("character", "status_buff")  # 군중 도발
    # taunt_crowd.cooldown = 3  # 쿨다운 시스템 제거됨
    taunt_crowd.metadata = {"cheer_scaling": True}

    # 5. 위험한 묘기 (고위험 고보상 - 환호 +30, HP 손실)
    risky_stunt = Skill("gladiator_risky_stunt", "위험한 묘기", "HP 20% 희생하여 환호 +30")
    risky_stunt.effects = [
        DamageEffect(DamageType.BRV_HP, 2.8, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 30, max_value=100),  # 환호 +30
        # HP 20% 손실 (self-damage)
    ]
    risky_stunt.costs = [MPCost(7)]
    risky_stunt.sfx = ("combat", "damage_high")  # 위험한 묘기
    # risky_stunt.cooldown = 4  # 쿨다운 시스템 제거됨
    risky_stunt.metadata = {"high_risk": True, "hp_cost_percent": 0.2, "cheer_gain": 30}

    # 6. 영광의 일격 (환호 소비하여 극강 공격)
    glory_strike = Skill("gladiator_glory_strike", "영광의 일격", "환호 30 소비하여 극강 공격")
    glory_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 3.5, stat_type="physical",
                    gimmick_bonus={"field": "cheer", "multiplier": 0.03}),
        GimmickEffect(GimmickOperation.ADD, "cheer", -30, min_value=0)  # 환호 -30
    ]
    glory_strike.costs = [MPCost(9)]
    glory_strike.sfx = ("combat", "critical")  # 영광의 일격
    # glory_strike.cooldown = 4  # 쿨다운 시스템 제거됨
    glory_strike.metadata = {"cheer_cost": 30}

    # 7. 군중 흥분 (환호를 50으로 설정)
    excite_crowd = Skill("gladiator_excite", "군중 흥분", "환호를 50으로 조정 (인기 구간)")
    excite_crowd.effects = [
        GimmickEffect(GimmickOperation.SET, "cheer", 50),  # 환호 50으로 설정
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=3)
    ]
    excite_crowd.costs = [MPCost(6)]
    excite_crowd.target_type = "self"
    excite_crowd.sfx = ("character", "status_buff")  # 군중 흥분
    # excite_crowd.cooldown = 6  # 쿨다운 시스템 제거됨
    excite_crowd.metadata = {"cheer_control": True, "set_cheer": 50}

    # 8. 불굴의 투지 (HP 회복 + 환호 회복)
    indomitable_will = Skill("gladiator_will", "불굴의 투지", "HP 30% 회복 + 환호 +25")
    indomitable_will.effects = [
        HealEffect(percentage=0.45),  # 불굴의 투지
        GimmickEffect(GimmickOperation.ADD, "cheer", 25, max_value=100),  # 환호 +25
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=3)
    ]
    indomitable_will.costs = [MPCost(7)]
    indomitable_will.target_type = "self"
    indomitable_will.sfx = ("character", "hp_heal")  # 불굴의 투지
    # indomitable_will.cooldown = 5  # 쿨다운 시스템 제거됨
    indomitable_will.metadata = {"recovery": True, "cheer_gain": 25}

    # 9. 챔피언의 함성 (아군 지원 + 환호 공유)
    champion_roar = Skill("gladiator_champion_roar", "챔피언의 함성", "아군 전체 버프 (환호 비례)")
    champion_roar.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=4),
        # Bonus based on cheer
        GimmickEffect(GimmickOperation.ADD, "cheer", 10, max_value=100)
    ]
    champion_roar.costs = [MPCost(9)]
    champion_roar.target_type = "party"
    champion_roar.is_aoe = True
    champion_roar.sfx = ("skill", "haste")  # 챔피언의 함성
    # champion_roar.cooldown = 6  # 쿨다운 시스템 제거됨
    champion_roar.metadata = {"party_buff": True}

    # 10. 궁극기: 검투사의 영광 (환호 100으로 폭발)
    ultimate = Skill("gladiator_ultimate", "검투사의 영광", "환호 100 도달, 무적 + 극대 공격")
    ultimate.effects = [
        # 환호를 100으로 설정 (무적 발동)
        GimmickEffect(GimmickOperation.SET, "cheer", 100),
        # 극대 공격
        DamageEffect(DamageType.BRV, 4.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 5.0, stat_type="physical"),
        # 무적 버프 (3턴)
        BuffEffect(BuffType.INVINCIBLE, 1.0, duration=3),
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.6, duration=5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "invincible": True}

    return [arena_strike, honor_strike, spectacular_attack, taunt_crowd, risky_stunt,
            glory_strike, excite_crowd, indomitable_will, champion_roar, ultimate]

def register_gladiator_skills(skill_manager):
    """검투사 스킬 등록"""
    skills = create_gladiator_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
