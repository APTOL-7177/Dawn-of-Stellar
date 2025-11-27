"""Elementalist Skills - 정령술사 (4대 정령 소환 시스템)

화염/물/바람/대지 정령을 소환!
2마리 소환 시 융합 스킬 해금

"하나보다 둘, 둘보다 넷이 강하다"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("elementalist_skills")


def create_elementalist_skills():
    """정령술사 스킬 생성 (4대 정령 소환 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 정령 일격 (기본 BRV)
    # ============================================================
    strike = Skill(
        "elementalist_strike",
        "정령 일격",
        "정령의 힘을 담은 기본 공격."
    )
    strike.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magic"),
    ]
    strike.costs = []
    strike.sfx = ("skill", "magic_cast")
    strike.metadata = {
        "basic_attack": True,
        "elemental": True
    }
    skills.append(strike)
    
    # ============================================================
    # 2. 정령 폭발 (기본 HP)
    # ============================================================
    spirit_burst = Skill(
        "elementalist_spirit_burst",
        "정령 폭발",
        "소환된 정령 수 비례 HP 피해."
    )
    spirit_burst.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magic",
                    gimmick_bonus={"field": "spirit_count", "multiplier": 0.4}),
    ]
    spirit_burst.costs = []
    spirit_burst.sfx = ("skill", "cast_complete")
    spirit_burst.metadata = {
        "basic_attack": True,
        "scaling": "정령당 +40%"
    }
    skills.append(spirit_burst)
    
    # ============================================================
    # 3. 화염 정령 소환
    # ============================================================
    summon_fire = Skill(
        "elementalist_summon_fire",
        "화염 정령 소환",
        "화염 정령 소환! 공격력 +20%, 화상 부여."
    )
    summon_fire.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magic"),
        StatusEffect(StatusType.BURN, duration=3, value=1.0,
                    damage_stat="magic", damage_multiplier=0.10),
        BuffEffect(BuffType.ATTACK_UP, 0.20, duration=5),
        GimmickEffect(GimmickOperation.SET, "spirit_fire", 1)
    ]
    summon_fire.costs = [MPCost(10)]
    summon_fire.sfx = ("skill", "fire_explosion")
    summon_fire.metadata = {
        "spirit": "fire",
        "buff": "공격력 +20%",
        "status": "화상"
    }
    skills.append(summon_fire)
    
    # ============================================================
    # 4. 물 정령 소환
    # ============================================================
    summon_water = Skill(
        "elementalist_summon_water",
        "물 정령 소환",
        "물 정령 소환! MP회복 +5/턴, 힐 +25%."
    )
    summon_water.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic"),
        HealEffect(HealType.HP, percentage=0.15),
        BuffEffect(BuffType.MP_REGEN, 5, duration=5),
        GimmickEffect(GimmickOperation.SET, "spirit_water", 1)
    ]
    summon_water.costs = [MPCost(8)]
    summon_water.target_type = "self"
    summon_water.sfx = ("skill", "magic_cast")
    summon_water.metadata = {
        "spirit": "water",
        "mp_regen": 5,
        "heal_bonus": "25%"
    }
    skills.append(summon_water)
    
    # ============================================================
    # 5. 바람 정령 소환
    # ============================================================
    summon_wind = Skill(
        "elementalist_summon_wind",
        "바람 정령 소환",
        "바람 정령 소환! 속도 +25%, 회피 +15%."
    )
    summon_wind.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magic"),
        BuffEffect(BuffType.SPEED_UP, 0.25, duration=5),
        BuffEffect(BuffType.EVASION_UP, 0.15, duration=5),
        GimmickEffect(GimmickOperation.SET, "spirit_wind", 1)
    ]
    summon_wind.costs = [MPCost(8)]
    summon_wind.target_type = "self"
    summon_wind.sfx = ("skill", "haste")
    summon_wind.metadata = {
        "spirit": "wind",
        "speed_buff": "25%",
        "evasion_buff": "15%"
    }
    skills.append(summon_wind)
    
    # ============================================================
    # 6. 대지 정령 소환
    # ============================================================
    summon_earth = Skill(
        "elementalist_summon_earth",
        "대지 정령 소환",
        "대지 정령 소환! 방어력 +25%, HP회복 +3/턴."
    )
    summon_earth.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic"),
        BuffEffect(BuffType.DEFENSE_UP, 0.25, duration=5),
        BuffEffect(BuffType.HP_REGEN, 3, duration=5),
        GimmickEffect(GimmickOperation.SET, "spirit_earth", 1)
    ]
    summon_earth.costs = [MPCost(8)]
    summon_earth.target_type = "self"
    summon_earth.sfx = ("character", "status_buff")
    summon_earth.metadata = {
        "spirit": "earth",
        "defense_buff": "25%",
        "hp_regen": 3
    }
    skills.append(summon_earth)
    
    # ============================================================
    # 7. 융합: 화염 돌풍 (화염+바람)
    # ============================================================
    fusion_firestorm = Skill(
        "elementalist_fusion_firestorm",
        "화염 돌풍",
        "[융합] 화염+바람 정령. 전체 화염 폭풍."
    )
    fusion_firestorm.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magic"),
        DamageEffect(DamageType.HP, 1.8, stat_type="magic"),
        StatusEffect(StatusType.BURN, duration=3, value=1.0,
                    damage_stat="magic", damage_multiplier=0.12),
    ]
    fusion_firestorm.costs = [MPCost(14)]
    fusion_firestorm.target_type = "all_enemies"
    fusion_firestorm.is_aoe = True
    fusion_firestorm.sfx = ("skill", "fire_explosion")
    fusion_firestorm.metadata = {
        "fusion": True,
        "requires": ["fire", "wind"],
        "aoe": True
    }
    skills.append(fusion_firestorm)
    
    # ============================================================
    # 8. 융합: 진흙 속박 (물+대지)
    # ============================================================
    fusion_mudtrap = Skill(
        "elementalist_fusion_mudtrap",
        "진흙 속박",
        "[융합] 물+대지 정령. 전체 속도/방어 감소."
    )
    fusion_mudtrap.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magic"),
        BuffEffect(BuffType.SPEED_DOWN, 0.30, duration=3),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.20, duration=3),
    ]
    fusion_mudtrap.costs = [MPCost(12)]
    fusion_mudtrap.target_type = "all_enemies"
    fusion_mudtrap.is_aoe = True
    fusion_mudtrap.sfx = ("character", "status_debuff")
    fusion_mudtrap.metadata = {
        "fusion": True,
        "requires": ["water", "earth"],
        "debuff": True
    }
    skills.append(fusion_mudtrap)
    
    # ============================================================
    # 9. 융합: 증기 폭발 (화염+물)
    # ============================================================
    fusion_steam = Skill(
        "elementalist_fusion_steam",
        "증기 폭발",
        "[융합] 화염+물 정령. 강력한 단일 피해."
    )
    fusion_steam.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 2.0, stat_type="magic"),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.25, duration=2),
    ]
    fusion_steam.costs = [MPCost(13)]
    fusion_steam.sfx = ("skill", "cast_complete")
    fusion_steam.metadata = {
        "fusion": True,
        "requires": ["fire", "water"],
        "high_damage": True
    }
    skills.append(fusion_steam)
    
    # ============================================================
    # 10. 궁극기: 4대 정령 융합
    # ============================================================
    ultimate = Skill(
        "elementalist_ultimate",
        "4대 정령 융합",
        "4대 정령 완전 융합! 전체 피해 + 모든 정령 효과."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 3.0, stat_type="magic"),
        StatusEffect(StatusType.BURN, duration=3, value=1.0,
                    damage_stat="magic", damage_multiplier=0.15),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=5),
        GimmickEffect(GimmickOperation.SET, "spirit_fire", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_water", 1),
    ]
    ultimate.costs = [MPCost(35)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "all_spirits": True,
        "aoe": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 정령 합체
    # ============================================================
    teamwork = TeamworkSkill(
        "elementalist_teamwork",
        "정령 합체",
        "모든 정령이 하나로! 전체 피해 + 모든 정령 소환.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 2.0, stat_type="magic"),
        GimmickEffect(GimmickOperation.SET, "spirit_fire", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_water", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_wind", 1),
        GimmickEffect(GimmickOperation.SET, "spirit_earth", 1),
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "summon_all": True
    }
    skills.append(teamwork)
    
    return skills


def register_elementalist_skills(skill_manager):
    """정령술사 스킬 등록"""
    skills = create_elementalist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"정령술사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
