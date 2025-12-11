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
    # 1. 성스러운 일격 (기본 BRV + 신앙)
    # ============================================================
    holy_smite = Skill(
        "priest_holy_smite",
        "성스러운 일격",
        "[신성 속성] 신성한 빛으로 공격. 신앙 +5."
    )
    holy_smite.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical", element="holy"),
        GimmickEffect(GimmickOperation.ADD, "faith", 5, max_value=100)
    ]
    holy_smite.costs = []
    holy_smite.sfx = ("skill", "magic_cast")
    holy_smite.metadata = {
        "basic_attack": True,
        "element": "holy",
        "oracle_action": "damage_evil",
        "faith_empowered": True
    }
    skills.append(holy_smite)
    
    # ============================================================
    # 2. 신성 심판 (기본 HP + 신앙 비례)
    # ============================================================
    divine_judgment = Skill(
        "priest_divine_judgment",
        "신성 심판",
        "[신성 속성] 신앙 비례 HP 피해. 신앙 +3."
    )
    divine_judgment.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magical", element="holy",
                    gimmick_bonus={"field": "faith", "multiplier": 0.01}),
        GimmickEffect(GimmickOperation.ADD, "faith", 3, max_value=100)
    ]
    divine_judgment.costs = []
    divine_judgment.sfx = ("skill", "cast_complete")
    divine_judgment.metadata = {
        "basic_attack": True,
        "element": "holy",
        "oracle_action": "damage_evil",
        "scaling": "신앙당 +1%",
        "faith_empowered": True
    }
    skills.append(divine_judgment)
    
    # ============================================================
    # 3. 빛의 속박 (CC + 신앙)
    # ============================================================
    light_bind = Skill(
        "priest_light_bind",
        "빛의 속박",
        "[신성 속성] 빛으로 적을 속박. 속도 -40% + 신앙 +8."
    )
    light_bind.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical", element="holy"),
        BuffEffect(BuffType.SPEED_DOWN, 0.40, duration=2),
        GimmickEffect(GimmickOperation.ADD, "faith", 8, max_value=100)
    ]
    light_bind.costs = [MPCost(6)]
    light_bind.sfx = ("character", "status_debuff")
    light_bind.metadata = {
        "cc": True,
        "element": "holy",
        "oracle_action": "damage_evil",
        "faith_empowered": True
    }
    skills.append(light_bind)
    
    # ============================================================
    # 3.5. 부활 (아군 부활 + HP 회복)
    # ============================================================
    resurrection = Skill(
        "priest_resurrection",
        "부활",
        "아군 1명을 HP 40% 상태로 부활시킴 + 신앙 +20."
    )
    resurrection.effects = [
        HealEffect(HealType.HP, percentage=0.4, metadata={'revival': True}),
        GimmickEffect(GimmickOperation.ADD, "faith", 20, max_value=100)
    ]
    resurrection.costs = [MPCost(20)]
    resurrection.target_type = "ally"
    resurrection.sfx = ("character", "revive")
    resurrection.metadata = {
        "healing": True,
        "revival": True,
        "oracle_action": "heal_ally",
        "faith_empowered": True
    }
    skills.append(resurrection)
    
    # ============================================================
    # 4. 신성한 치유 (단일 힐 + 신앙 강화)
    # ============================================================
    holy_heal = Skill(
        "priest_holy_heal",
        "축복의 치유",
        "마법력 × 1.125 HP 회복 + 신앙 +12.\n신앙 100이면 마법력 × 2.625 회복 + 신앙 소모."
    )
    holy_heal.effects = [
        HealEffect(HealType.HP, base_amount=0, multiplier=1.125, stat_scaling="magic"),
        GimmickEffect(GimmickOperation.ADD, "faith", 12, max_value=100)
    ]
    holy_heal.costs = [MPCost(8)]
    holy_heal.target_type = "ally"
    holy_heal.sfx = ("character", "hp_heal")
    holy_heal.metadata = {
        "healing": True,
        "oracle_action": "heal_ally",
        "faith_empowered": True,
        "faith_multiplier": 2.625
    }
    skills.append(holy_heal)
    
    # ============================================================
    # 5. 신성 보호 (파티 방어 버프)
    # ============================================================
    divine_protection = Skill(
        "priest_divine_protection",
        "신성 보호",
        "신의 보호. 파티 방어/마방 +40% (4턴) + 신앙 +10.\n신앙 100이면 방어/마방 +80% (6턴) + 신앙 소모."
    )
    divine_protection.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.40, duration=4, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.40, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "faith", 10, max_value=100)
    ]
    divine_protection.costs = [MPCost(9)]
    divine_protection.target_type = "party"
    divine_protection.is_aoe = True
    divine_protection.sfx = ("character", "status_buff")
    divine_protection.metadata = {
        "party_buff": True,
        "oracle_action": "buff_ally",
        "faith_empowered": True
    }
    skills.append(divine_protection)
    
    # ============================================================
    # 6. 심판의 빛 (광역 공격)
    # ============================================================
    judgment_light = Skill(
        "priest_judgment_light",
        "심판의 빛",
        "[신성 속성] 심판의 빛! 전체 피해 + 신앙 +15."
    )
    judgment_light.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="magical", element="holy"),
        DamageEffect(DamageType.HP, 1.2, stat_type="magical", element="holy"),
        GimmickEffect(GimmickOperation.ADD, "faith", 15, max_value=100)
    ]
    judgment_light.costs = [MPCost(10)]
    judgment_light.target_type = "all_enemies"
    judgment_light.is_aoe = True
    judgment_light.sfx = ("skill", "cast_complete")
    judgment_light.metadata = {
        "aoe": True,
        "element": "holy",
        "oracle_action": "damage_evil",
        "faith_empowered": True
    }
    skills.append(judgment_light)
    
    # ============================================================
    # 7. 신성 광선 (신앙 소비 공격)
    # ============================================================
    holy_beam = Skill(
        "priest_holy_beam",
        "신성 광선",
        "[신성 속성] 신앙 30 소비. 강력한 신성 광선."
    )
    holy_beam.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magical", element="holy",
                    gimmick_bonus={"field": "faith", "multiplier": 0.015}),
        GimmickEffect(GimmickOperation.CONSUME, "faith", 30)
    ]
    holy_beam.costs = [MPCost(12), StackCost("faith", 30)]
    holy_beam.sfx = ("skill", "magic_cast")
    holy_beam.metadata = {
        "element": "holy",
        "scaling": "신앙당 +1.5%",
        "oracle_action": "damage_evil",
        "faith_empowered": True
    }
    skills.append(holy_beam)
    
    # ============================================================
    # 8. 신의 분노 (광역 심판)
    # ============================================================
    divine_wrath = Skill(
        "priest_divine_wrath",
        "신의 분노",
        "[신성 속성] 신의 분노! 전체 피해 + 신앙 40 소비."
    )
    divine_wrath.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magical", element="holy",
                    gimmick_bonus={"field": "faith", "multiplier": 0.012}),
        DamageEffect(DamageType.HP, 1.8, stat_type="magical", element="holy"),
        GimmickEffect(GimmickOperation.CONSUME, "faith", 40)
    ]
    divine_wrath.costs = [MPCost(14), StackCost("faith", 40)]
    divine_wrath.target_type = "all_enemies"
    divine_wrath.is_aoe = True
    divine_wrath.sfx = ("skill", "cast_complete")
    divine_wrath.metadata = {
        "aoe": True,
        "element": "holy",
        "oracle_action": "damage_evil",
        "faith_empowered": True
    }
    skills.append(divine_wrath)
    
    # ============================================================
    # 9. 신의 은총 (파티 힐 + 버프)
    # ============================================================
    divine_grace = Skill(
        "priest_divine_grace",
        "신의 은총",
        "파티 치유. 마법력 × 0.5625 HP 회복 + 재생 + 신앙 +18."
    )
    divine_grace.effects = [
        HealEffect(HealType.HP, base_amount=0, multiplier=0.5625, is_party_wide=True, stat_scaling="magic"),
        BuffEffect(BuffType.REGEN, 0.08, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "faith", 18, max_value=100)
    ]
    divine_grace.costs = [MPCost(15)]
    divine_grace.target_type = "party"
    divine_grace.is_aoe = True
    divine_grace.sfx = ("character", "hp_heal")
    divine_grace.metadata = {
        "regen": True,
        "oracle_action": "heal_ally",
        "faith_empowered": True
    }
    skills.append(divine_grace)
    
    # ============================================================
    # 10. 궁극기: 천상의 심판
    # ============================================================
    ultimate = Skill(
        "priest_ultimate",
        "천상의 심판",
        "[신성 속성] 천상의 빛! 전체 극대 피해 + 파티 마법력 × 1.5 HP 회복 + 공격력/마법력 +40%."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="magical", element="holy"),
        DamageEffect(DamageType.HP, 3.5, stat_type="magical", element="holy"),
        HealEffect(HealType.HP, base_amount=0, multiplier=1.5, is_party_wide=True, stat_scaling="magic"),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=5, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "faith", 50)
    ]
    ultimate.costs = [MPCost(35)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aoe": True,
        "element": "holy",
        "oracle_action": "damage_evil"
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 신의 기적
    # ============================================================
    teamwork = TeamworkSkill(
        "priest_teamwork",
        "신의 기적",
        "기적 발동! 파티 마법력 × 1.25 HP 회복 + 방어 버프 + 신앙 +50.",
        gauge_cost=175
    )
    teamwork.effects = [
        HealEffect(HealType.HP, base_amount=0, multiplier=1.25, is_party_wide=True, stat_scaling="magic"),
        BuffEffect(BuffType.DEFENSE_UP, 0.25, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "faith", 50, max_value=100)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "miracle": True,
        "oracle_action": "heal_ally"
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
