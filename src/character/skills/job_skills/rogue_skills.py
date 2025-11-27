"""Rogue Skills - 도적 (절도 & 회피 시스템)

적에게서 아이템을 훔쳐라!
회피로 생존, 암살로 마무리

"정정당당? 그건 바보들이나 하는 거지"
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

logger = get_logger("rogue_skills")


def create_rogue_skills():
    """도적 스킬 생성 (절도 & 회피 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 기습 (기본 BRV + 크리티컬)
    # ============================================================
    ambush = Skill(
        "rogue_ambush",
        "기습",
        "빠른 기습 공격. 크리티컬 확률 UP."
    )
    ambush.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="physical"),
        BuffEffect(BuffType.CRITICAL_UP, 0.15, duration=2)
    ]
    ambush.costs = []
    ambush.sfx = ("combat", "attack_physical")
    ambush.metadata = {
        "basic_attack": True,
        "crit_boost": True
    }
    skills.append(ambush)
    
    # ============================================================
    # 2. 급소 찌르기 (기본 HP)
    # ============================================================
    vital_strike = Skill(
        "rogue_vital_strike",
        "급소 찌르기",
        "급소를 노린 HP 공격."
    )
    vital_strike.effects = [
        DamageEffect(DamageType.HP, 1.3, stat_type="physical"),
    ]
    vital_strike.costs = []
    vital_strike.sfx = ("combat", "critical")
    vital_strike.metadata = {
        "basic_attack": True,
        "critical_bonus": 0.3
    }
    skills.append(vital_strike)
    
    # ============================================================
    # 3. 훔치기 (아이템 획득)
    # ============================================================
    steal = Skill(
        "rogue_steal",
        "훔치기",
        "적에게서 아이템 훔치기! 훔친 아이템 +1."
    )
    steal.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    steal.costs = [MPCost(4)]
    steal.sfx = ("item", "get_item")
    steal.metadata = {
        "steal": True,
        "item_gain": 1,
        "steal_chance": 0.7
    }
    skills.append(steal)
    
    # ============================================================
    # 4. 연막탄 (회피 모드)
    # ============================================================
    smoke = Skill(
        "rogue_smoke",
        "연막탄",
        "연막으로 은신. 회피 +50%, 속도 +30% (3턴)."
    )
    smoke.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=3),
        BuffEffect(BuffType.SPEED_UP, 0.30, duration=3),
    ]
    smoke.costs = [MPCost(6)]
    smoke.target_type = "self"
    smoke.sfx = ("skill", "haste")
    smoke.metadata = {
        "stealth": True,
        "evasion_mode": True
    }
    skills.append(smoke)
    
    # ============================================================
    # 5. 훔친 아이템 사용
    # ============================================================
    use_item = Skill(
        "rogue_use_item",
        "아이템 사용",
        "훔친 아이템 사용. HP 25% 회복 또는 버프. (훔친 아이템 -1)"
    )
    use_item.effects = [
        HealEffect(HealType.HP, percentage=0.25),
        BuffEffect(BuffType.ATTACK_UP, 0.20, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "stolen_items", 1)
    ]
    use_item.costs = [StackCost("stolen_items", 1)]
    use_item.target_type = "self"
    use_item.sfx = ("item", "use_item")
    use_item.metadata = {
        "item_cost": 1,
        "random_effect": True
    }
    skills.append(use_item)
    
    # ============================================================
    # 6. 독 바르기 (DoT 공격)
    # ============================================================
    poison = Skill(
        "rogue_poison",
        "독 바르기",
        "무기에 독을 바른다. 4턴 독 피해."
    )
    poison.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                    damage_stat="physical", damage_multiplier=0.10),
    ]
    poison.costs = [MPCost(7)]
    poison.sfx = ("character", "status_debuff")
    poison.metadata = {
        "poison": True,
        "dot": "물공 10%/턴"
    }
    skills.append(poison)
    
    # ============================================================
    # 7. 보물 탐지 (대량 아이템 획득)
    # ============================================================
    treasure = Skill(
        "rogue_treasure",
        "보물 탐지",
        "보물을 찾아낸다! 훔친 아이템 +3."
    )
    treasure.effects = [
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 3, max_value=10),
        BuffEffect(BuffType.LUCK, 0.20, duration=3)
    ]
    treasure.costs = [MPCost(5)]
    treasure.target_type = "self"
    treasure.sfx = ("item", "get_item")
    treasure.metadata = {
        "item_gain": 3,
        "luck_boost": True
    }
    skills.append(treasure)
    
    # ============================================================
    # 8. 백스탭 (후방 공격)
    # ============================================================
    backstab = Skill(
        "rogue_backstab",
        "백스탭",
        "치명적인 후방 공격. 크리 +40% (이번 공격)."
    )
    backstab.effects = [
        DamageEffect(DamageType.BRV_HP, 2.4, stat_type="physical"),
        BuffEffect(BuffType.CRITICAL_UP, 0.40, duration=1),
    ]
    backstab.costs = [MPCost(9)]
    backstab.sfx = ("combat", "critical")
    backstab.metadata = {
        "backstab": True,
        "crit_bonus": 0.40
    }
    skills.append(backstab)
    
    # ============================================================
    # 9. 암살 (처형기)
    # ============================================================
    assassinate = Skill(
        "rogue_assassinate",
        "암살",
        "암살 시도! HP 30% 이하 적 즉사 15% 확률."
    )
    assassinate.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 2.5, stat_type="physical"),
    ]
    assassinate.costs = [MPCost(12)]
    assassinate.sfx = ("combat", "damage_high")
    assassinate.metadata = {
        "execute": True,
        "instant_kill_threshold": 0.30,
        "instant_kill_chance": 0.15
    }
    skills.append(assassinate)
    
    # ============================================================
    # 10. 궁극기: 그림자 습격
    # ============================================================
    ultimate = Skill(
        "rogue_ultimate",
        "그림자 습격",
        "그림자에서 습격! 전체 피해 + 모든 아이템 효과 + 은신."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical"),
        DamageEffect(DamageType.HP, 3.5, stat_type="physical"),
        BuffEffect(BuffType.EVASION_UP, 0.60, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.50, duration=4),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10)
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
        "stealth_after": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 대약탈
    # ============================================================
    teamwork = TeamworkSkill(
        "rogue_teamwork",
        "대약탈",
        "대규모 약탈! 전체 피해 + 훔친 아이템 +5 + 회피 버프.",
        gauge_cost=150
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10),
        BuffEffect(BuffType.EVASION_UP, 0.30, duration=3)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "item_gain": 5
    }
    skills.append(teamwork)
    
    return skills


def register_rogue_skills(skill_manager):
    """도적 스킬 등록"""
    skills = create_rogue_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"도적 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
