"""Spellblade Skills - 마검사 (마력 부여 시스템)

검에 원소 마력을 부여!
화염/빙결/번개로 다양한 속성 공격

"검과 마법, 그 경계를 넘어서"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost
from src.core.logger import get_logger

logger = get_logger("spellblade_skills")


def create_spellblade_skills():
    """마검사 스킬 생성 (마력 부여 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 마검 베기 (기본 BRV + 마나)
    # ============================================================
    magic_slash = Skill(
        "spellblade_magic_slash",
        "마검 베기",
        "마력을 담은 검격. 마나 블레이드 +10."
    )
    magic_slash.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 10, max_value=100)
    ]
    magic_slash.costs = []
    magic_slash.sfx = ("combat", "attack_physical")
    magic_slash.metadata = {
        "basic_attack": True,
        "mana_gain": 10
    }
    skills.append(magic_slash)
    
    # ============================================================
    # 2. 원소 베기 (기본 HP + 마나 비례)
    # ============================================================
    elemental_slash = Skill(
        "spellblade_elemental_slash",
        "원소 베기",
        "마나 비례 HP 피해. 마나 -15."
    )
    elemental_slash.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="physical",
                    gimmick_bonus={"field": "mana_blade", "multiplier": 0.01}),
        GimmickEffect(GimmickOperation.CONSUME, "mana_blade", 15)
    ]
    elemental_slash.costs = []
    elemental_slash.sfx = ("combat", "critical")
    elemental_slash.metadata = {
        "basic_attack": True,
        "mana_cost": 15,
        "scaling": "마나당 +1%"
    }
    skills.append(elemental_slash)
    
    # ============================================================
    # 3. 화염 부여 (화상 공격)
    # ============================================================
    fire_infusion = Skill(
        "spellblade_fire_infusion",
        "화염 부여",
        "검에 화염 부여. 피해 + 화상 3턴. 마나 +15."
    )
    fire_infusion.effects = [
        DamageEffect(DamageType.BRV_HP, 1.9, stat_type="physical"),
        StatusEffect(StatusType.BURN, duration=3, value=1.0,
                    damage_stat="magic", damage_multiplier=0.10),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 15, max_value=100)
    ]
    fire_infusion.costs = [MPCost(7)]
    fire_infusion.sfx = ("skill", "fire_explosion")
    fire_infusion.metadata = {
        "element": "fire",
        "mana_gain": 15,
        "burn": True
    }
    skills.append(fire_infusion)
    
    # ============================================================
    # 4. 빙결 부여 (속도 감소)
    # ============================================================
    ice_infusion = Skill(
        "spellblade_ice_infusion",
        "빙결 부여",
        "검에 냉기 부여. 피해 + 속도 -30%. 마나 +15."
    )
    ice_infusion.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.30, duration=3),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 15, max_value=100)
    ]
    ice_infusion.costs = [MPCost(7)]
    ice_infusion.sfx = ("skill", "magic_cast")
    ice_infusion.metadata = {
        "element": "ice",
        "mana_gain": 15,
        "slow": True
    }
    skills.append(ice_infusion)
    
    # ============================================================
    # 5. 번개 부여 (연쇄 피해)
    # ============================================================
    lightning_infusion = Skill(
        "spellblade_lightning_infusion",
        "번개 부여",
        "검에 전격 부여. 2회 공격 + 마나 +20."
    )
    lightning_infusion.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="physical"),
        DamageEffect(DamageType.BRV_HP, 1.4, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 20, max_value=100)
    ]
    lightning_infusion.costs = [MPCost(8)]
    lightning_infusion.sfx = ("skill", "cast_complete")
    lightning_infusion.metadata = {
        "element": "lightning",
        "mana_gain": 20,
        "multi_hit": 2
    }
    skills.append(lightning_infusion)
    
    # ============================================================
    # 6. 마검 난무 (다단 히트)
    # ============================================================
    magic_blade_dance = Skill(
        "spellblade_magic_blade_dance",
        "마검 난무",
        "마검 연속 공격! 4회 피해 + 마나 +10."
    )
    magic_blade_dance.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        DamageEffect(DamageType.HP, 1.0, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 10, max_value=100)
    ]
    magic_blade_dance.costs = [MPCost(9)]
    magic_blade_dance.sfx = ("combat", "attack_physical")
    magic_blade_dance.metadata = {
        "multi_hit": 4,
        "mana_gain": 10
    }
    skills.append(magic_blade_dance)
    
    # ============================================================
    # 7. 마나 폭발 (마나 소비 공격)
    # ============================================================
    mana_burst = Skill(
        "spellblade_mana_burst",
        "마나 폭발",
        "마나 50 소비. 강력한 마력 폭발."
    )
    mana_burst.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="physical",
                    gimmick_bonus={"field": "mana_blade", "multiplier": 0.012}),
        GimmickEffect(GimmickOperation.CONSUME, "mana_blade", 50)
    ]
    mana_burst.costs = [MPCost(10), StackCost("mana_blade", 50)]
    mana_burst.sfx = ("skill", "cast_complete")
    mana_burst.metadata = {
        "mana_cost": 50,
        "scaling": "마나당 +1.2%"
    }
    skills.append(mana_burst)
    
    # ============================================================
    # 8. 원소 폭풍 (광역 공격)
    # ============================================================
    elemental_storm = Skill(
        "spellblade_elemental_storm",
        "원소 폭풍",
        "3원소 합체! 전체 피해 + 상태이상. 마나 -40."
    )
    elemental_storm.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 1.6, stat_type="physical"),
        StatusEffect(StatusType.BURN, duration=2, value=1.0,
                    damage_stat="magic", damage_multiplier=0.08),
        BuffEffect(BuffType.SPEED_DOWN, 0.20, duration=2),
        GimmickEffect(GimmickOperation.CONSUME, "mana_blade", 40)
    ]
    elemental_storm.costs = [MPCost(12), StackCost("mana_blade", 40)]
    elemental_storm.target_type = "all_enemies"
    elemental_storm.is_aoe = True
    elemental_storm.sfx = ("skill", "fire_explosion")
    elemental_storm.metadata = {
        "mana_cost": 40,
        "aoe": True,
        "all_elements": True
    }
    skills.append(elemental_storm)
    
    # ============================================================
    # 9. 검기 회전 (광역 + 마나 충전)
    # ============================================================
    blade_spin = Skill(
        "spellblade_blade_spin",
        "검기 회전",
        "회전하며 광역 공격. 마나 +25."
    )
    blade_spin.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "mana_blade", 25, max_value=100)
    ]
    blade_spin.costs = [MPCost(8)]
    blade_spin.target_type = "all_enemies"
    blade_spin.is_aoe = True
    blade_spin.sfx = ("combat", "attack_physical")
    blade_spin.metadata = {
        "aoe": True,
        "mana_gain": 25
    }
    skills.append(blade_spin)
    
    # ============================================================
    # 10. 궁극기: 마검 오의
    # ============================================================
    ultimate = Skill(
        "spellblade_ultimate",
        "마검 오의",
        "물리와 마법의 완전한 융합! 전체 극대 피해 + 올버프."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 3.5, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=5),
        GimmickEffect(GimmickOperation.SET, "mana_blade", 100)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aoe": True,
        "mana_full": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 마검 일체
    # ============================================================
    teamwork = TeamworkSkill(
        "spellblade_teamwork",
        "마검 일체",
        "검과 마법이 하나로! 전체 피해 + 마나 MAX + 버프.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="physical"),
        DamageEffect(DamageType.HP, 1.8, stat_type="physical"),
        GimmickEffect(GimmickOperation.SET, "mana_blade", 100),
        BuffEffect(BuffType.ATTACK_UP, 0.30, duration=3)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "mana_full": True
    }
    skills.append(teamwork)
    
    return skills


def register_spellblade_skills(skill_manager):
    """마검사 스킬 등록"""
    skills = create_spellblade_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"마검사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
