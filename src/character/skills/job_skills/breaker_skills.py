"""Breaker Skills - 브레이커 (파괴력 축적 시스템)

BRV를 부수고 파괴력을 축적!
파괴력 비례 피해 + 방어 관통

"부서진 것들이 나의 무기가 된다"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost
from src.core.logger import get_logger

logger = get_logger("breaker_skills")


def create_breaker_skills():
    """브레이커 스킬 생성 (파괴력 축적 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 파쇄 타격 (기본 BRV + 파괴력 축적)
    # ============================================================
    crush = Skill(
        "breaker_crush",
        "파쇄 타격",
        "강력한 BRV 공격. 파괴력 +1."
    )
    crush.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "break_power", 1, max_value=10)
    ]
    crush.costs = []
    crush.sfx = ("combat", "attack_physical")
    crush.metadata = {
        "basic_attack": True,
        "break_power_gain": 1,
        "brv_focus": True
    }
    skills.append(crush)
    
    # ============================================================
    # 2. 파괴의 일격 (기본 HP + 파괴력 소비)
    # ============================================================
    break_hit = Skill(
        "breaker_break_hit",
        "파괴의 일격",
        "파괴력 비례 HP 피해. 파괴력 -1."
    )
    break_hit.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="physical",
                    gimmick_bonus={"field": "break_power", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "break_power", 1)
    ]
    break_hit.costs = []
    break_hit.sfx = ("combat", "damage_high")
    break_hit.metadata = {
        "basic_attack": True,
        "break_power_cost": 1,
        "scaling": "파괴력당 +20%"
    }
    skills.append(break_hit)
    
    # ============================================================
    # 3. BRV 집중 (공격 버프 + 파괴력)
    # ============================================================
    brv_focus = Skill(
        "breaker_brv_focus",
        "BRV 집중",
        "파괴에 집중. 공격력 +35% (4턴) + 파괴력 +2."
    )
    brv_focus.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.35, duration=4),
        GimmickEffect(GimmickOperation.ADD, "break_power", 2, max_value=10)
    ]
    brv_focus.costs = [MPCost(4)]
    brv_focus.target_type = "self"
    brv_focus.sfx = ("character", "status_buff")
    brv_focus.metadata = {
        "buff": True,
        "break_power_gain": 2
    }
    skills.append(brv_focus)
    
    # ============================================================
    # 4. 연타 (다중 BRV 히트)
    # ============================================================
    multi = Skill(
        "breaker_multi",
        "연타",
        "3연속 BRV 공격. 파괴력 +2."
    )
    multi.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="physical"),
        DamageEffect(DamageType.BRV, 1.4, stat_type="physical"),
        DamageEffect(DamageType.BRV, 1.4, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "break_power", 2, max_value=10)
    ]
    multi.costs = [MPCost(5)]
    multi.sfx = ("combat", "attack_physical")
    multi.metadata = {
        "multi_hit": 3,
        "break_power_gain": 2
    }
    skills.append(multi)
    
    # ============================================================
    # 5. 파괴 강화 (파괴력 대량 충전)
    # ============================================================
    enhance = Skill(
        "breaker_enhance",
        "파괴 강화",
        "파괴 본능 각성. 파괴력 +5 + 크리 +25%."
    )
    enhance.effects = [
        GimmickEffect(GimmickOperation.ADD, "break_power", 5, max_value=10),
        BuffEffect(BuffType.CRITICAL_UP, 0.25, duration=3)
    ]
    enhance.costs = [MPCost(6)]
    enhance.target_type = "self"
    enhance.sfx = ("skill", "haste")
    enhance.metadata = {
        "break_power_gain": 5,
        "crit_buff": True
    }
    skills.append(enhance)
    
    # ============================================================
    # 6. 대파쇄 (강력 BRV)
    # ============================================================
    mega_crush = Skill(
        "breaker_mega_crush",
        "대파쇄",
        "파괴력 비례 BRV 대피해. 파괴력 +1."
    )
    mega_crush.effects = [
        DamageEffect(DamageType.BRV, 2.8, stat_type="physical",
                    gimmick_bonus={"field": "break_power", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.ADD, "break_power", 1, max_value=10)
    ]
    mega_crush.costs = [MPCost(7)]
    mega_crush.sfx = ("combat", "damage_high")
    mega_crush.metadata = {
        "break_power_gain": 1,
        "scaling": "파괴력당 +25%"
    }
    skills.append(mega_crush)
    
    # ============================================================
    # 7. 파괴 충격파 (광역 BRV)
    # ============================================================
    wave = Skill(
        "breaker_wave",
        "파괴 충격파",
        "충격파로 전체 BRV 공격. 파괴력 -3."
    )
    wave.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical",
                    gimmick_bonus={"field": "break_power", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "break_power", 3)
    ]
    wave.costs = [MPCost(8), StackCost("break_power", 3)]
    wave.target_type = "all_enemies"
    wave.is_aoe = True
    wave.sfx = ("skill", "cast_complete")
    wave.metadata = {
        "break_power_cost": 3,
        "aoe": True
    }
    skills.append(wave)
    
    # ============================================================
    # 8. 완전 파괴 (BRV+HP 콤보)
    # ============================================================
    total = Skill(
        "breaker_total",
        "완전 파괴",
        "완벽한 파괴. BRV+HP 피해. 파괴력 -5."
    )
    total.effects = [
        DamageEffect(DamageType.BRV_HP, 2.4, stat_type="physical",
                    gimmick_bonus={"field": "break_power", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "break_power", 5)
    ]
    total.costs = [MPCost(10), StackCost("break_power", 5)]
    total.sfx = ("combat", "break")
    total.metadata = {
        "break_power_cost": 5,
        "scaling": "파괴력당 +35%"
    }
    skills.append(total)
    
    # ============================================================
    # 9. 파괴의 화신 (파괴력 MAX 충전)
    # ============================================================
    devastation = Skill(
        "breaker_devastation",
        "파괴의 화신",
        "파괴신 강림. 파괴력 MAX + 공/크리 버프."
    )
    devastation.effects = [
        GimmickEffect(GimmickOperation.SET, "break_power", 10),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=4)
    ]
    devastation.costs = [MPCost(12)]
    devastation.target_type = "self"
    devastation.sfx = ("character", "status_buff")
    devastation.metadata = {
        "break_power_max": True,
        "buff": True
    }
    skills.append(devastation)
    
    # ============================================================
    # 10. 궁극기: 절대 파괴
    # ============================================================
    ultimate = Skill(
        "breaker_ultimate",
        "절대 파괴",
        "모든 것을 파괴! 전체 다중 피해 + 파괴력 전소비."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="physical",
                    gimmick_bonus={"field": "break_power", "multiplier": 0.4}),
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical",
                    gimmick_bonus={"field": "break_power", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 3.5, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        GimmickEffect(GimmickOperation.SET, "break_power", 0)
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
        "break_consume_all": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 쉘 브레이크
    # ============================================================
    teamwork = TeamworkSkill(
        "breaker_teamwork",
        "쉘 브레이크",
        "적 방어 완전 파괴! 단일 BRV (4.0x) + BREAK 확정 + 방어 -30%.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 4.0, stat_type="physical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.30, duration=3),
        GimmickEffect(GimmickOperation.ADD, "break_power", 5, max_value=10)
    ]
    teamwork.target_type = "enemy"
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "guaranteed_break": True
    }
    skills.append(teamwork)
    
    return skills


def register_breaker_skills(skill_manager):
    """브레이커 스킬 등록"""
    skills = create_breaker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"브레이커 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
