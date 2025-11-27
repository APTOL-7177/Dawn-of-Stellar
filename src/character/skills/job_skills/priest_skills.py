"""Priest Skills - 신관 (신성 권능 시스템)

치유와 심판으로 신성력 축적!
신앙으로 기적을, 심판으로 징벌을

"구원할 것인가, 심판할 것인가"
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

logger = get_logger("priest_skills")


def create_priest_skills():
    """신관 스킬 생성 (신성 권능 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 성스러운 일격 (기본 BRV + 심판력)
    # ============================================================
    holy_smite = Skill(
        "priest_holy_smite",
        "성스러운 일격",
        "신성한 빛으로 공격. 심판력 +10."
    )
    holy_smite.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magic"),
        GimmickEffect(GimmickOperation.ADD, "judgment_points", 10, max_value=100)
    ]
    holy_smite.costs = []
    holy_smite.sfx = ("skill", "magic_cast")
    holy_smite.metadata = {
        "basic_attack": True,
        "judgment_gain": 10
    }
    skills.append(holy_smite)
    
    # ============================================================
    # 2. 신성 심판 (기본 HP + 심판력 비례)
    # ============================================================
    divine_judgment = Skill(
        "priest_divine_judgment",
        "신성 심판",
        "심판력 비례 HP 피해. 심판력 -15."
    )
    divine_judgment.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magic",
                    gimmick_bonus={"field": "judgment_points", "multiplier": 0.01}),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 15)
    ]
    divine_judgment.costs = []
    divine_judgment.sfx = ("skill", "cast_complete")
    divine_judgment.metadata = {
        "basic_attack": True,
        "judgment_cost": 15,
        "scaling": "심판력당 +1%"
    }
    skills.append(divine_judgment)
    
    # ============================================================
    # 3. 빛의 속박 (CC + 심판력)
    # ============================================================
    light_bind = Skill(
        "priest_light_bind",
        "빛의 속박",
        "빛으로 적을 속박. 속도 -40% + 심판력 +15."
    )
    light_bind.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic"),
        BuffEffect(BuffType.SPEED_DOWN, 0.40, duration=2),
        GimmickEffect(GimmickOperation.ADD, "judgment_points", 15, max_value=100)
    ]
    light_bind.costs = [MPCost(6)]
    light_bind.sfx = ("character", "status_debuff")
    light_bind.metadata = {
        "cc": True,
        "judgment_gain": 15
    }
    skills.append(light_bind)
    
    # ============================================================
    # 4. 신성한 치유 (단일 힐 + 신앙)
    # ============================================================
    holy_heal = Skill(
        "priest_holy_heal",
        "신성한 치유",
        "신의 은총으로 치유. HP 45% 회복 + 신앙 +10."
    )
    holy_heal.effects = [
        HealEffect(HealType.HP, percentage=0.45),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 10, max_value=100)
    ]
    holy_heal.costs = [MPCost(8)]
    holy_heal.target_type = "ally"
    holy_heal.sfx = ("character", "hp_heal")
    holy_heal.metadata = {
        "healing": True,
        "faith_gain": 10,
        "heal_amount": "45%"
    }
    skills.append(holy_heal)
    
    # ============================================================
    # 5. 신성 보호 (파티 방어 버프)
    # ============================================================
    divine_protection = Skill(
        "priest_divine_protection",
        "신성 보호",
        "신의 보호. 파티 방어 +25% + 신앙 +15."
    )
    divine_protection.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.25, duration=4, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.25, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 15, max_value=100)
    ]
    divine_protection.costs = [MPCost(9)]
    divine_protection.target_type = "party"
    divine_protection.is_aoe = True
    divine_protection.sfx = ("character", "status_buff")
    divine_protection.metadata = {
        "party_buff": True,
        "faith_gain": 15
    }
    skills.append(divine_protection)
    
    # ============================================================
    # 6. 심판의 빛 (광역 공격)
    # ============================================================
    judgment_light = Skill(
        "priest_judgment_light",
        "심판의 빛",
        "심판의 빛! 전체 피해 + 심판력 +20."
    )
    judgment_light.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="magic"),
        DamageEffect(DamageType.HP, 1.2, stat_type="magic"),
        GimmickEffect(GimmickOperation.ADD, "judgment_points", 20, max_value=100)
    ]
    judgment_light.costs = [MPCost(10)]
    judgment_light.target_type = "all_enemies"
    judgment_light.is_aoe = True
    judgment_light.sfx = ("skill", "cast_complete")
    judgment_light.metadata = {
        "aoe": True,
        "judgment_gain": 20
    }
    skills.append(judgment_light)
    
    # ============================================================
    # 7. 신성 광선 (심판력 소비 공격)
    # ============================================================
    holy_beam = Skill(
        "priest_holy_beam",
        "신성 광선",
        "심판력 40 소비. 강력한 신성 광선."
    )
    holy_beam.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magic",
                    gimmick_bonus={"field": "judgment_points", "multiplier": 0.015}),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 40)
    ]
    holy_beam.costs = [MPCost(12), StackCost("judgment_points", 40)]
    holy_beam.sfx = ("skill", "magic_cast")
    holy_beam.metadata = {
        "judgment_cost": 40,
        "scaling": "심판력당 +1.5%"
    }
    skills.append(holy_beam)
    
    # ============================================================
    # 8. 신의 분노 (광역 심판)
    # ============================================================
    divine_wrath = Skill(
        "priest_divine_wrath",
        "신의 분노",
        "신의 분노! 전체 피해 + 심판력 50 소비."
    )
    divine_wrath.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magic",
                    gimmick_bonus={"field": "judgment_points", "multiplier": 0.012}),
        DamageEffect(DamageType.HP, 1.8, stat_type="magic"),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 50)
    ]
    divine_wrath.costs = [MPCost(14), StackCost("judgment_points", 50)]
    divine_wrath.target_type = "all_enemies"
    divine_wrath.is_aoe = True
    divine_wrath.sfx = ("skill", "cast_complete")
    divine_wrath.metadata = {
        "judgment_cost": 50,
        "aoe": True
    }
    skills.append(divine_wrath)
    
    # ============================================================
    # 9. 신의 은총 (파티 힐 + 버프)
    # ============================================================
    divine_grace = Skill(
        "priest_divine_grace",
        "신의 은총",
        "신의 은총! 파티 HP 35% + 재생 + 신앙 +20."
    )
    divine_grace.effects = [
        HealEffect(HealType.HP, percentage=0.35, is_party_wide=True),
        BuffEffect(BuffType.REGEN, 0.08, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 20, max_value=100)
    ]
    divine_grace.costs = [MPCost(15)]
    divine_grace.target_type = "party"
    divine_grace.is_aoe = True
    divine_grace.sfx = ("character", "hp_heal")
    divine_grace.metadata = {
        "party_heal": "35%",
        "regen": True,
        "faith_gain": 20
    }
    skills.append(divine_grace)
    
    # ============================================================
    # 10. 궁극기: 천상의 심판
    # ============================================================
    ultimate = Skill(
        "priest_ultimate",
        "천상의 심판",
        "천상의 빛! 전체 극대 피해 + 파티 완전 회복."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="magic"),
        DamageEffect(DamageType.HP, 3.5, stat_type="magic"),
        HealEffect(HealType.HP, percentage=0.60, is_party_wide=True),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "judgment_points", 50),
        GimmickEffect(GimmickOperation.SET, "faith_points", 50)
    ]
    ultimate.costs = [MPCost(35)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "party_heal": "60%",
        "aoe": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 신의 기적
    # ============================================================
    teamwork = TeamworkSkill(
        "priest_teamwork",
        "신의 기적",
        "기적 발동! 파티 HP 50% + 버프 + 심판력/신앙 +30.",
        gauge_cost=175
    )
    teamwork.effects = [
        HealEffect(HealType.HP, percentage=0.50, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.25, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "judgment_points", 30, max_value=100),
        GimmickEffect(GimmickOperation.ADD, "faith_points", 30, max_value=100)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "miracle": True
    }
    skills.append(teamwork)
    
    return skills


def register_priest_skills(skill_manager):
    """신관 스킬 등록"""
    skills = create_priest_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"신관 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
