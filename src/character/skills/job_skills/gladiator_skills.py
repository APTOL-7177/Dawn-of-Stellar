"""Gladiator Skills - 검투사 (군중 환호 시스템)

화려한 플레이로 관중을 열광시켜라!
환호가 높을수록 강해지며 100 달성 시 무적

"관중이 열광할수록 나는 강해진다"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("gladiator_skills")


def create_gladiator_skills():
    """검투사 스킬 생성 (군중 환호 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 투기장 타격 (기본 BRV + 환호)
    # ============================================================
    arena_strike = Skill(
        "gladiator_arena_strike",
        "투기장 타격",
        "관중에게 어필하는 공격. 환호 +5."
    )
    arena_strike.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 5, max_value=100)
    ]
    arena_strike.costs = []
    arena_strike.sfx = ("combat", "attack_physical")
    arena_strike.metadata = {
        "basic_attack": True,
        "cheer_gain": 5
    }
    skills.append(arena_strike)
    
    # ============================================================
    # 2. 명예의 일격 (기본 HP + 환호)
    # ============================================================
    honor_strike = Skill(
        "gladiator_honor_strike",
        "명예의 일격",
        "명예로운 마무리. 환호 +10."
    )
    honor_strike.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 10, max_value=100)
    ]
    honor_strike.costs = []
    honor_strike.sfx = ("combat", "critical")
    honor_strike.metadata = {
        "basic_attack": True,
        "cheer_gain": 10
    }
    skills.append(honor_strike)
    
    # ============================================================
    # 3. 화려한 공격 (쇼맨십)
    # ============================================================
    spectacular = Skill(
        "gladiator_spectacular",
        "화려한 공격",
        "화려한 쇼맨십! 환호 +15."
    )
    spectacular.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 15, max_value=100)
    ]
    spectacular.costs = [MPCost(5)]
    spectacular.sfx = ("combat", "attack_physical")
    spectacular.metadata = {
        "showmanship": True,
        "cheer_gain": 15
    }
    skills.append(spectacular)
    
    # ============================================================
    # 4. 군중 도발 (환호 비례 공격)
    # ============================================================
    taunt = Skill(
        "gladiator_taunt",
        "군중 도발",
        "환호 비례 강력한 공격. 환호 +10."
    )
    taunt.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="physical",
                    gimmick_bonus={"field": "cheer", "multiplier": 0.015}),
        GimmickEffect(GimmickOperation.ADD, "cheer", 10, max_value=100)
    ]
    taunt.costs = [MPCost(7)]
    taunt.sfx = ("character", "status_buff")
    taunt.metadata = {
        "cheer_scaling": True,
        "scaling": "환호당 +1.5%"
    }
    skills.append(taunt)
    
    # ============================================================
    # 5. 위험한 묘기 (고위험 고보상)
    # ============================================================
    risky_stunt = Skill(
        "gladiator_risky_stunt",
        "위험한 묘기",
        "위험한 묘기! 환호 +25 (HP 15% 소비)."
    )
    risky_stunt.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 25, max_value=100),
    ]
    risky_stunt.costs = [MPCost(8)]
    risky_stunt.sfx = ("combat", "damage_high")
    risky_stunt.metadata = {
        "high_risk": True,
        "hp_cost_percent": 0.15,
        "cheer_gain": 25
    }
    skills.append(risky_stunt)
    
    # ============================================================
    # 6. 영광의 일격 (환호 소비 공격)
    # ============================================================
    glory_strike = Skill(
        "gladiator_glory_strike",
        "영광의 일격",
        "환호 30 소비, 극강 공격."
    )
    glory_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="physical",
                    gimmick_bonus={"field": "cheer", "multiplier": 0.02}),
        GimmickEffect(GimmickOperation.ADD, "cheer", -30, min_value=0)
    ]
    glory_strike.costs = [MPCost(10)]
    glory_strike.sfx = ("combat", "critical")
    glory_strike.metadata = {
        "cheer_cost": 30,
        "scaling": "환호당 +2%"
    }
    skills.append(glory_strike)
    
    # ============================================================
    # 7. 군중 흥분 (환호 50 세팅)
    # ============================================================
    excite = Skill(
        "gladiator_excite",
        "군중 흥분",
        "관중 열광! 환호 50으로 조정 + 버프."
    )
    excite.effects = [
        GimmickEffect(GimmickOperation.SET, "cheer", 50),
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3),
        BuffEffect(BuffType.CRITICAL_UP, 0.20, duration=3)
    ]
    excite.costs = [MPCost(8)]
    excite.target_type = "self"
    excite.sfx = ("character", "status_buff")
    excite.metadata = {
        "cheer_set": 50,
        "buff": True
    }
    skills.append(excite)
    
    # ============================================================
    # 8. 불굴의 투지 (HP 회복 + 환호)
    # ============================================================
    will = Skill(
        "gladiator_will",
        "불굴의 투지",
        "역전의 의지! HP 35% 회복 + 환호 +20."
    )
    will.effects = [
        HealEffect(HealType.HP, percentage=0.35),
        GimmickEffect(GimmickOperation.ADD, "cheer", 20, max_value=100),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3)
    ]
    will.costs = [MPCost(9)]
    will.target_type = "self"
    will.sfx = ("character", "hp_heal")
    will.metadata = {
        "recovery": True,
        "cheer_gain": 20
    }
    skills.append(will)
    
    # ============================================================
    # 9. 챔피언의 함성 (파티 버프)
    # ============================================================
    champion_roar = Skill(
        "gladiator_champion_roar",
        "챔피언의 함성",
        "챔피언의 함성! 파티 버프 + 환호 +10."
    )
    champion_roar.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=4, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.15, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "cheer", 10, max_value=100)
    ]
    champion_roar.costs = [MPCost(11)]
    champion_roar.target_type = "party"
    champion_roar.is_aoe = True
    champion_roar.sfx = ("skill", "haste")
    champion_roar.metadata = {
        "party_buff": True,
        "cheer_gain": 10
    }
    skills.append(champion_roar)
    
    # ============================================================
    # 10. 궁극기: 검투사의 영광
    # ============================================================
    ultimate = Skill(
        "gladiator_ultimate",
        "검투사의 영광",
        "환호 MAX! 무적 3턴 + 극대 피해."
    )
    ultimate.effects = [
        GimmickEffect(GimmickOperation.SET, "cheer", 100),
        DamageEffect(DamageType.BRV, 3.5, stat_type="physical"),
        DamageEffect(DamageType.HP, 4.0, stat_type="physical"),
        BuffEffect(BuffType.INVINCIBLE, 1.0, duration=3),
        BuffEffect(BuffType.ATTACK_UP, 0.6, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.4, duration=5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "invincible": 3,
        "cheer_max": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 군중의 환호
    # ============================================================
    teamwork = TeamworkSkill(
        "gladiator_teamwork",
        "군중의 환호",
        "관중 폭발! BRV+HP 공격 + 환호 +30 + 방어 버프.",
        gauge_cost=150
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 1.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "cheer", 30, max_value=100),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=2)
    ]
    teamwork.target_type = "enemy"
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "cheer_gain": 30
    }
    skills.append(teamwork)
    
    return skills


def register_gladiator_skills(skill_manager):
    """검투사 스킬 등록"""
    skills = create_gladiator_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"검투사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
