"""Druid Skills - 드루이드 (자연 변신 시스템)

자연 포인트로 동물 변신!
곰/표범/독수리/늑대 형태로 다양한 전투 스타일

"자연의 모든 모습이 나의 힘"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost
from src.core.logger import get_logger

logger = get_logger("druid_skills")


def create_druid_skills():
    """드루이드 스킬 생성 (자연 변신 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 자연의 힘 (기본 BRV + 자연 포인트)
    # ============================================================
    nature_power = Skill(
        "druid_nature_power",
        "자연의 힘",
        "자연의 에너지로 공격. 자연 포인트 +1."
    )
    nature_power.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magic"),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 1, max_value=5)
    ]
    nature_power.costs = []
    nature_power.sfx = ("skill", "cast_start")
    nature_power.metadata = {
        "basic_attack": True,
        "nature_gain": 1
    }
    skills.append(nature_power)
    
    # ============================================================
    # 2. 가시 덩굴 (기본 HP + 자연 소비)
    # ============================================================
    thorn_vine = Skill(
        "druid_thorn_vine",
        "가시 덩굴",
        "가시 덩굴로 적을 옭아맨다. 자연 -1."
    )
    thorn_vine.effects = [
        DamageEffect(DamageType.HP, 1.1, stat_type="magic",
                    gimmick_bonus={"field": "nature_points", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 1)
    ]
    thorn_vine.costs = []
    thorn_vine.sfx = ("skill", "cast_complete")
    thorn_vine.metadata = {
        "basic_attack": True,
        "nature_cost": 1,
        "scaling": "자연당 +25%"
    }
    skills.append(thorn_vine)
    
    # ============================================================
    # 3. 곰 변신 (탱커 모드)
    # ============================================================
    bear_form = Skill(
        "druid_bear_form",
        "곰 변신",
        "거대한 곰으로 변신! 방어 +50%, 공격 +25% (4턴)."
    )
    bear_form.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magic"),
        BuffEffect(BuffType.DEFENSE_UP, 0.50, duration=4),
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=4),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 1, max_value=5)
    ]
    bear_form.costs = [MPCost(5)]
    bear_form.target_type = "self"
    bear_form.sfx = ("character", "status_buff")
    bear_form.metadata = {
        "form": "bear",
        "tank_mode": True,
        "nature_gain": 1
    }
    skills.append(bear_form)
    
    # ============================================================
    # 4. 표범 변신 (속도 모드)
    # ============================================================
    cat_form = Skill(
        "druid_cat_form",
        "표범 변신",
        "날렵한 표범으로 변신! 속도 +60%, 회피 +35% (4턴)."
    )
    cat_form.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic"),
        BuffEffect(BuffType.SPEED_UP, 0.60, duration=4),
        BuffEffect(BuffType.EVASION_UP, 0.35, duration=4),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 1, max_value=5)
    ]
    cat_form.costs = [MPCost(5)]
    cat_form.target_type = "self"
    cat_form.sfx = ("skill", "haste")
    cat_form.metadata = {
        "form": "panther",
        "speed_mode": True,
        "nature_gain": 1
    }
    skills.append(cat_form)
    
    # ============================================================
    # 5. 치유의 숲 (파티 힐)
    # ============================================================
    healing_forest = Skill(
        "druid_healing_forest",
        "치유의 숲",
        "숲의 치유력. 파티 HP 30% 회복. 자연 -2."
    )
    healing_forest.effects = [
        HealEffect(HealType.HP, percentage=0.30, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 2)
    ]
    healing_forest.costs = [MPCost(8), StackCost("nature_points", 2)]
    healing_forest.target_type = "party"
    healing_forest.sfx = ("character", "hp_heal")
    healing_forest.metadata = {
        "nature_cost": 2,
        "party_heal": "30%"
    }
    skills.append(healing_forest)
    
    # ============================================================
    # 6. 자연의 축복 (자연 충전)
    # ============================================================
    nature_blessing = Skill(
        "druid_nature_blessing",
        "자연의 축복",
        "자연과 교감. 자연 MAX + 재생 버프."
    )
    nature_blessing.effects = [
        GimmickEffect(GimmickOperation.SET, "nature_points", 5),
        BuffEffect(BuffType.REGEN, 0.08, duration=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=4)
    ]
    nature_blessing.costs = [MPCost(7)]
    nature_blessing.target_type = "self"
    nature_blessing.sfx = ("character", "status_buff")
    nature_blessing.metadata = {
        "nature_refill": True,
        "regen": "8%/턴"
    }
    skills.append(nature_blessing)
    
    # ============================================================
    # 7. 독수리 변신 (공중 공격)
    # ============================================================
    eagle_form = Skill(
        "druid_eagle_form",
        "독수리 변신",
        "독수리로 급강하 공격! 자연 -3."
    )
    eagle_form.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="magic",
                    gimmick_bonus={"field": "nature_points", "multiplier": 0.3}),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 3)
    ]
    eagle_form.costs = [MPCost(9), StackCost("nature_points", 3)]
    eagle_form.sfx = ("world", "jump")
    eagle_form.metadata = {
        "form": "eagle",
        "nature_cost": 3,
        "aerial_attack": True
    }
    skills.append(eagle_form)
    
    # ============================================================
    # 8. 늑대 변신 (광역 공격)
    # ============================================================
    wolf_form = Skill(
        "druid_wolf_form",
        "늑대 변신",
        "늑대 무리 소환! 전체 공격. 자연 -4."
    )
    wolf_form.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="magic",
                    gimmick_bonus={"field": "nature_points", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 1.4, stat_type="magic"),
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 4)
    ]
    wolf_form.costs = [MPCost(11), StackCost("nature_points", 4)]
    wolf_form.target_type = "all_enemies"
    wolf_form.is_aoe = True
    wolf_form.sfx = ("combat", "attack_physical")
    wolf_form.metadata = {
        "form": "wolf",
        "nature_cost": 4,
        "aoe": True
    }
    skills.append(wolf_form)
    
    # ============================================================
    # 9. 자연의 분노 (원소 폭발)
    # ============================================================
    natures_wrath = Skill(
        "druid_natures_wrath",
        "자연의 분노",
        "자연의 분노 폭발! 전체 피해 + 디버프. 자연 -5."
    )
    natures_wrath.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magic",
                    gimmick_bonus={"field": "nature_points", "multiplier": 0.35}),
        DamageEffect(DamageType.HP, 1.8, stat_type="magic"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.25, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "nature_points", 5)
    ]
    natures_wrath.costs = [MPCost(13), StackCost("nature_points", 5)]
    natures_wrath.target_type = "all_enemies"
    natures_wrath.is_aoe = True
    natures_wrath.sfx = ("skill", "cast_complete")
    natures_wrath.metadata = {
        "nature_cost": 5,
        "aoe": True,
        "debuff": True
    }
    skills.append(natures_wrath)
    
    # ============================================================
    # 10. 궁극기: 진 변신
    # ============================================================
    ultimate = Skill(
        "druid_ultimate",
        "진 변신",
        "자연과 완전한 합일! 전체 피해 + 올버프 + 자연 MAX."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 2.5, stat_type="magic"),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=5),
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=5),
        GimmickEffect(GimmickOperation.SET, "nature_points", 5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "form": "primal",
        "all_buffs": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 대자연의 축복
    # ============================================================
    teamwork = TeamworkSkill(
        "druid_teamwork",
        "대자연의 축복",
        "자연의 가호! 파티 HP 40% + 자연 +3 + 재생.",
        gauge_cost=150
    )
    teamwork.effects = [
        HealEffect(HealType.HP, percentage=0.40, is_party_wide=True),
        BuffEffect(BuffType.REGEN, 0.10, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "nature_points", 3, max_value=5)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "nature_gain": 3
    }
    skills.append(teamwork)
    
    return skills


def register_druid_skills(skill_manager):
    """드루이드 스킬 등록"""
    skills = create_druid_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"드루이드 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
