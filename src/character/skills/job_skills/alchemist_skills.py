"""Alchemist Skills - 연금술사 (포션 조합 시스템)

재료를 모아 다양한 포션을 제조하고 투척!
회복/버프/폭발/산성 등 상황에 맞는 조합

"완벽한 조합은 천재의 영역, 폭발은 일상"
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

logger = get_logger("alchemist_skills")


def create_alchemist_skills():
    """연금술사 스킬 생성 (포션 조합 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 포션 투척 (기본 BRV + 재료 획득)
    # ============================================================
    throw_potion = Skill(
        "alchemist_throw_potion",
        "포션 투척",
        "실험용 포션을 던져 공격. 재료 +1 획득."
    )
    throw_potion.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic"),
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 1, max_value=10)
    ]
    throw_potion.costs = []
    throw_potion.sfx = ("item", "use_item")
    throw_potion.metadata = {
        "basic_attack": True,
        "potion_gain": 1,
        "description": "기본 공격으로 재료 수집"
    }
    skills.append(throw_potion)
    
    # ============================================================
    # 2. 폭발 포션 (기본 HP + 재료 소비)
    # ============================================================
    explosive = Skill(
        "alchemist_explosive",
        "폭발 포션",
        "불안정한 포션이 폭발! 재료 비례 피해."
    )
    explosive.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magic",
                    gimmick_bonus={"field": "potion_stock", "multiplier": 0.15}),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 1)
    ]
    explosive.costs = []
    explosive.sfx = ("item", "grenade")
    explosive.metadata = {
        "basic_attack": True,
        "potion_cost": 1,
        "scaling": "재료 1개당 +15% 피해"
    }
    skills.append(explosive)
    
    # ============================================================
    # 3. 회복 포션 (HP 회복)
    # ============================================================
    heal_potion = Skill(
        "alchemist_heal_potion",
        "회복 포션",
        "정성껏 조합한 회복약. HP 40% 회복. (재료 2개)"
    )
    heal_potion.effects = [
        HealEffect(HealType.HP, percentage=0.40),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 2)
    ]
    heal_potion.costs = [StackCost("potion_stock", 2)]
    heal_potion.target_type = "ally"
    heal_potion.sfx = ("character", "hp_heal")
    heal_potion.metadata = {
        "potion_cost": 2,
        "healing": True,
        "heal_amount": "40%"
    }
    skills.append(heal_potion)
    
    # ============================================================
    # 4. 버프 포션 (올스탯 버프)
    # ============================================================
    buff_potion = Skill(
        "alchemist_buff_potion",
        "버프 포션",
        "능력 강화약. 공/마/속 +25% (4턴). (재료 3개)"
    )
    buff_potion.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=4),
        BuffEffect(BuffType.MAGIC_UP, 0.25, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 3)
    ]
    buff_potion.costs = [MPCost(6), StackCost("potion_stock", 3)]
    buff_potion.target_type = "ally"
    buff_potion.sfx = ("character", "status_buff")
    buff_potion.metadata = {
        "potion_cost": 3,
        "buff": True,
        "duration": 4
    }
    skills.append(buff_potion)
    
    # ============================================================
    # 5. 독 폭탄 (DoT + 재료 획득)
    # ============================================================
    poison_bomb = Skill(
        "alchemist_poison_bomb",
        "독 폭탄",
        "맹독 폭탄 투척. 4턴 독 + 재료 +1."
    )
    poison_bomb.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magic"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                    damage_stat="magic", damage_multiplier=0.12),
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 1, max_value=10)
    ]
    poison_bomb.costs = [MPCost(7)]
    poison_bomb.sfx = ("character", "status_debuff")
    poison_bomb.metadata = {
        "potion_gain": 1,
        "poison": True,
        "dot_damage": "마공 12%/턴"
    }
    skills.append(poison_bomb)
    
    # ============================================================
    # 6. 재료 수집 (재료 대량 획득)
    # ============================================================
    gather = Skill(
        "alchemist_gather",
        "재료 수집",
        "주변에서 재료를 긁어모은다. 재료 +4."
    )
    gather.effects = [
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 4, max_value=10),
        BuffEffect(BuffType.DEFENSE_UP, 0.15, duration=2)
    ]
    gather.costs = [MPCost(4)]
    gather.target_type = "self"
    gather.sfx = ("item", "get_item")
    gather.metadata = {
        "potion_gain": 4,
        "utility": True,
        "defense_while_gathering": True
    }
    skills.append(gather)
    
    # ============================================================
    # 7. 마나 포션 (MP 회복)
    # ============================================================
    mana_potion = Skill(
        "alchemist_mana_potion",
        "마나 포션",
        "파란 포션으로 MP 25 회복. (재료 2개)"
    )
    mana_potion.effects = [
        HealEffect(HealType.MP, base_amount=25),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 2)
    ]
    mana_potion.costs = [StackCost("potion_stock", 2)]
    mana_potion.target_type = "ally"
    mana_potion.sfx = ("character", "mp_heal")
    mana_potion.metadata = {
        "potion_cost": 2,
        "mp_recovery": 25
    }
    skills.append(mana_potion)
    
    # ============================================================
    # 8. 폭발 연쇄 (광역 폭발)
    # ============================================================
    chain = Skill(
        "alchemist_chain",
        "폭발 연쇄",
        "연쇄 폭발! 전체 피해 + 재료 비례 보너스. (재료 4개)"
    )
    chain.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="magic",
                    gimmick_bonus={"field": "potion_stock", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 4)
    ]
    chain.costs = [MPCost(10), StackCost("potion_stock", 4)]
    chain.target_type = "all_enemies"
    chain.is_aoe = True
    chain.sfx = ("item", "grenade")
    chain.metadata = {
        "potion_cost": 4,
        "aoe": True,
        "scaling": "재료당 +20%"
    }
    skills.append(chain)
    
    # ============================================================
    # 9. 산성 플라스크 (방어 감소)
    # ============================================================
    acid_flask = Skill(
        "alchemist_acid_flask",
        "산성 플라스크",
        "강산 투척! 물/마방 -25% (4턴). (재료 3개)"
    )
    acid_flask.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="magic"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.25, duration=4),
        BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, 0.25, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 3)
    ]
    acid_flask.costs = [MPCost(9), StackCost("potion_stock", 3)]
    acid_flask.sfx = ("character", "status_debuff")
    acid_flask.metadata = {
        "potion_cost": 3,
        "debuff": True,
        "defense_reduction": "25%"
    }
    skills.append(acid_flask)
    
    # ============================================================
    # 10. 궁극기: 현자의 물약
    # ============================================================
    ultimate = Skill(
        "alchemist_ultimate",
        "현자의 물약",
        "전설의 비약! 파티 HP 50% 회복 + 올스탯 버프 + 재료 MAX."
    )
    ultimate.effects = [
        HealEffect(HealType.HP, percentage=0.50, is_party_wide=True),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=5, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=5, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "potion_stock", 10)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "party"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "party_heal": "50%",
        "party_buff": True,
        "potion_refill": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 비약 조합
    # ============================================================
    teamwork = TeamworkSkill(
        "alchemist_teamwork",
        "비약 조합",
        "희귀 비약 즉시 생성! 파티 HP 40% + 공/방 +25% (3턴).",
        gauge_cost=125
    )
    teamwork.effects = [
        HealEffect(HealType.HP, percentage=0.40, is_party_wide=True),
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.25, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 3, max_value=10)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "potion_gain": 3
    }
    skills.append(teamwork)
    
    return skills


def register_alchemist_skills(skill_manager):
    """연금술사 스킬 등록"""
    skills = create_alchemist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"연금술사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
