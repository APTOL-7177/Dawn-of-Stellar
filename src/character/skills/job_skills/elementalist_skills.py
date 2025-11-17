"""Elementalist Skills - 정령술사 스킬 (4대 정령 소환)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.costs.mp_cost import MPCost

def create_elementalist_skills():
    """정령술사 10개 스킬 생성 (4대 정령 소환)"""

    # 1. 기본 BRV: 원소 타격
    elemental_strike = Skill("elementalist_strike", "원소 타격", "기본 마법 공격")
    elemental_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical")
    ]
    elemental_strike.costs = []  # 기본 공격은 MP 소모 없음
    elemental_strike.sfx = "338"  # FFVII elemental sound
    elemental_strike.metadata = {}

    # 2. 기본 HP: 정령 폭발
    spirit_burst = Skill("elementalist_spirit_burst", "정령 폭발", "HP 마법 공격")
    spirit_burst.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical")
    ]
    spirit_burst.costs = []  # 기본 공격은 MP 소모 없음
    spirit_burst.sfx = "344"  # FFVII burst sound
    spirit_burst.metadata = {}

    # 3. 화염 정령 소환 (공격력 +20%, 화상)
    summon_fire = Skill("elementalist_summon_fire", "화염 정령 소환", "공격력 +20%, 화상 피해")
    summon_fire.effects = [
        GimmickEffect(GimmickOperation.ADD, "spirit_fire", 1, max_value=1),  # 화염 정령 소환
        BuffEffect(BuffType.ATTACK_UP, 0.2, duration=99),  # 정령 소환 중 지속
        DamageEffect(DamageType.BRV, 1.8, stat_type="magical")
    ]
    summon_fire.costs = [MPCost(12)]
    summon_fire.target_type = "self"
    summon_fire.sfx = "352"  # FFVII fire summon sound
    # summon_fire.cooldown = 3  # 쿨다운 시스템 제거됨
    summon_fire.metadata = {"spirit_type": "fire", "attack_boost": 0.2}

    # 4. 물 정령 소환 (MP 회복 +5/턴, 힐 +30%)
    summon_water = Skill("elementalist_summon_water", "물 정령 소환", "MP 회복 +5/턴, 힐 +30%")
    summon_water.effects = [
        GimmickEffect(GimmickOperation.ADD, "spirit_water", 1, max_value=1),
        BuffEffect(BuffType.MP_REGEN, 5, duration=99),
        HealEffect(percentage=0.15)  # 즉시 HP 15% 회복
    ]
    summon_water.costs = [MPCost(10)]
    summon_water.target_type = "self"
    summon_water.sfx = "362"  # FFVII water summon sound
    # summon_water.cooldown = 3  # 쿨다운 시스템 제거됨
    summon_water.metadata = {"spirit_type": "water", "mp_regen": 5}

    # 5. 바람 정령 소환 (속도 +30%, 회피 +15%)
    summon_wind = Skill("elementalist_summon_wind", "바람 정령 소환", "속도 +30%, 회피 +15%")
    summon_wind.effects = [
        GimmickEffect(GimmickOperation.ADD, "spirit_wind", 1, max_value=1),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=99),
        BuffEffect(BuffType.EVASION_UP, 0.15, duration=99)
    ]
    summon_wind.costs = [MPCost(10)]
    summon_wind.target_type = "self"
    summon_wind.sfx = "376"  # FFVII wind summon sound
    # summon_wind.cooldown = 3  # 쿨다운 시스템 제거됨
    summon_wind.metadata = {"spirit_type": "wind", "speed_boost": 0.3}

    # 6. 대지 정령 소환 (방어력 +30%, HP 회복 +3/턴)
    summon_earth = Skill("elementalist_summon_earth", "대지 정령 소환", "방어력 +30%, HP 회복 +3/턴")
    summon_earth.effects = [
        GimmickEffect(GimmickOperation.ADD, "spirit_earth", 1, max_value=1),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=99),
        BuffEffect(BuffType.HP_REGEN, 3, duration=99)
    ]
    summon_earth.costs = [MPCost(10)]
    summon_earth.target_type = "self"
    summon_earth.sfx = "404"  # FFVII earth summon sound
    # summon_earth.cooldown = 3  # 쿨다운 시스템 제거됨
    summon_earth.metadata = {"spirit_type": "earth", "defense_boost": 0.3}

    # 7. 융합: 화염 돌풍 (화염 + 바람)
    fusion_firestorm = Skill("elementalist_fusion_firestorm", "화염 돌풍", "화염+바람 융합 (광역 화염 공격)")
    fusion_firestorm.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="magical"),
        # 두 정령 소비
        GimmickEffect(GimmickOperation.SET, "spirit_fire", 0),
        GimmickEffect(GimmickOperation.SET, "spirit_wind", 0)
    ]
    fusion_firestorm.costs = [MPCost(18)]
    fusion_firestorm.target_type = "all_enemies"
    fusion_firestorm.is_aoe = True
    fusion_firestorm.sfx = "423"  # FFVII firestorm sound
    # fusion_firestorm.cooldown = 4  # 쿨다운 시스템 제거됨
    fusion_firestorm.metadata = {"fusion": "fire_wind", "requires_both_spirits": True}

    # 8. 융합: 진흙 속박 (물 + 대지)
    fusion_mudtrap = Skill("elementalist_fusion_mudtrap", "진흙 속박", "물+대지 융합 (속도↓ 방어↓)")
    fusion_mudtrap.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.5, duration=4),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        # 두 정령 소비
        GimmickEffect(GimmickOperation.SET, "spirit_water", 0),
        GimmickEffect(GimmickOperation.SET, "spirit_earth", 0)
    ]
    fusion_mudtrap.costs = [MPCost(16)]
    fusion_mudtrap.sfx = "438"  # FFVII mud sound
    # fusion_mudtrap.cooldown = 4  # 쿨다운 시스템 제거됨
    fusion_mudtrap.metadata = {"fusion": "water_earth", "requires_both_spirits": True}

    # 9. 융합: 증기 폭발 (화염 + 물)
    fusion_steam = Skill("elementalist_fusion_steam", "증기 폭발", "화염+물 융합 (마법 피해 + 명중↓)")
    fusion_steam.effects = [
        DamageEffect(DamageType.BRV_HP, 3.2, stat_type="magical"),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.4, duration=3),
        # 두 정령 소비
        GimmickEffect(GimmickOperation.SET, "spirit_fire", 0),
        GimmickEffect(GimmickOperation.SET, "spirit_water", 0)
    ]
    fusion_steam.costs = [MPCost(20)]
    fusion_steam.target_type = "all_enemies"
    fusion_steam.is_aoe = True
    fusion_steam.sfx = "467"  # FFVII steam sound
    # fusion_steam.cooldown = 5  # 쿨다운 시스템 제거됨
    fusion_steam.metadata = {"fusion": "fire_water", "requires_both_spirits": True}

    # 10. 궁극기: 4대 정령 대결집 (모든 정령 즉시 소환 + 극대 공격)
    ultimate = Skill("elementalist_ultimate", "4대 정령 대결집", "모든 정령 소환 + 극대 융합 공격")
    ultimate.effects = [
        # 4대 정령 모두 소환
        GimmickEffect(GimmickOperation.SET, "spirit_fire", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_water", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_wind", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_earth", 1),
        # 극대 공격
        DamageEffect(DamageType.BRV, 4.0, stat_type="magical"),
        DamageEffect(DamageType.HP, 4.5, stat_type="magical"),
        # 모든 정령 버프 적용
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = "696"  # FFVII ultimate summon sound
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.metadata = {"ultimate": True, "summon_all_spirits": True}

    return [elemental_strike, spirit_burst, summon_fire, summon_water, summon_wind,
            summon_earth, fusion_firestorm, fusion_mudtrap, fusion_steam, ultimate]

def register_elementalist_skills(skill_manager):
    """정령술사 스킬 등록"""
    skills = create_elementalist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
