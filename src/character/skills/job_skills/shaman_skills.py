"""Shaman Skills - 무당 (저주 축적 시스템)

저주를 모아 강력한 주술 발동!
DoT와 디버프의 달인

"조상의 목소리가 미래를 말해준다"
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

logger = get_logger("shaman_skills")


def create_shaman_skills():
    """무당 스킬 생성 (저주 축적 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 저주 걸기 (기본 BRV + 저주)
    # ============================================================
    curse = Skill(
        "shaman_curse",
        "저주 걸기",
        "저주를 건다. 저주 스택 +1."
    )
    curse.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magic"),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 1, max_value=10)
    ]
    curse.costs = []
    curse.sfx = ("character", "status_debuff")
    curse.metadata = {
        "basic_attack": True,
        "curse_gain": 1
    }
    skills.append(curse)
    
    # ============================================================
    # 2. 저주 폭발 (기본 HP + 저주 비례)
    # ============================================================
    curse_burst = Skill(
        "shaman_curse_burst",
        "저주 폭발",
        "저주 비례 HP 피해. 저주 -1."
    )
    curse_burst.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magic",
                    gimmick_bonus={"field": "curse_stacks", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 1)
    ]
    curse_burst.costs = []
    curse_burst.sfx = ("skill", "cast_complete")
    curse_burst.metadata = {
        "basic_attack": True,
        "curse_cost": 1,
        "scaling": "저주당 +20%"
    }
    skills.append(curse_burst)
    
    # ============================================================
    # 3. 역병 (광역 DoT)
    # ============================================================
    plague = Skill(
        "shaman_plague",
        "역병",
        "역병을 퍼뜨린다. 전체 독 4턴 + 저주 +2."
    )
    plague.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                    damage_stat="magic", damage_multiplier=0.12),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 2, max_value=10)
    ]
    plague.costs = [MPCost(8)]
    plague.target_type = "all_enemies"
    plague.is_aoe = True
    plague.sfx = ("character", "status_debuff")
    plague.metadata = {
        "aoe": True,
        "curse_gain": 2,
        "dot": "마공 12%/턴"
    }
    skills.append(plague)
    
    # ============================================================
    # 4. 저주 전이 (디버프 확산)
    # ============================================================
    curse_transfer = Skill(
        "shaman_curse_transfer",
        "저주 전이",
        "저주를 전이. 공/방 -20% + 저주 +2."
    )
    curse_transfer.effects = [
        DamageEffect(DamageType.BRV_HP, 1.6, stat_type="magic"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.20, duration=3),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.20, duration=3),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 2, max_value=10)
    ]
    curse_transfer.costs = [MPCost(7)]
    curse_transfer.sfx = ("character", "status_debuff")
    curse_transfer.metadata = {
        "debuff": True,
        "curse_gain": 2
    }
    skills.append(curse_transfer)
    
    # ============================================================
    # 5. 저주 축적 (저주 대량 충전)
    # ============================================================
    curse_accumulate = Skill(
        "shaman_curse_accumulate",
        "저주 축적",
        "저주를 모은다. 저주 +4 + 마법 버프."
    )
    curse_accumulate.effects = [
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 4, max_value=10),
        BuffEffect(BuffType.MAGIC_UP, 0.25, duration=3)
    ]
    curse_accumulate.costs = [MPCost(5)]
    curse_accumulate.target_type = "self"
    curse_accumulate.sfx = ("character", "status_buff")
    curse_accumulate.metadata = {
        "curse_gain": 4,
        "buff": True
    }
    skills.append(curse_accumulate)
    
    # ============================================================
    # 6. 어둠의 마법 (강력 단일)
    # ============================================================
    dark_magic = Skill(
        "shaman_dark_magic",
        "어둠의 마법",
        "어둠의 힘! 저주 비례 피해 + 저주 +1."
    )
    dark_magic.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="magic",
                    gimmick_bonus={"field": "curse_stacks", "multiplier": 0.15}),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 1, max_value=10)
    ]
    dark_magic.costs = [MPCost(8)]
    dark_magic.sfx = ("skill", "magic_cast")
    dark_magic.metadata = {
        "curse_scaling": True,
        "curse_gain": 1
    }
    skills.append(dark_magic)
    
    # ============================================================
    # 7. 영혼 흡수 (HP 흡수)
    # ============================================================
    soul_drain = Skill(
        "shaman_soul_drain",
        "영혼 흡수",
        "영혼을 빨아들인다. 피해량 30% HP 흡수 + 저주 +1."
    )
    soul_drain.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="magic"),
        HealEffect(HealType.HP, percentage=0.15),  # 간접 흡혈
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 1, max_value=10)
    ]
    soul_drain.costs = [MPCost(9)]
    soul_drain.sfx = ("skill", "cast_complete")
    soul_drain.metadata = {
        "lifesteal": 0.30,
        "curse_gain": 1
    }
    skills.append(soul_drain)
    
    # ============================================================
    # 8. 저주의 낙인 (저주 소비 공격)
    # ============================================================
    curse_mark = Skill(
        "shaman_curse_mark",
        "저주의 낙인",
        "저주 5 소비. 강력한 저주 폭발."
    )
    curse_mark.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic",
                    gimmick_bonus={"field": "curse_stacks", "multiplier": 0.25}),
        DamageEffect(DamageType.HP, 2.0, stat_type="magic"),
        GimmickEffect(GimmickOperation.CONSUME, "curse_stacks", 5)
    ]
    curse_mark.costs = [MPCost(12), StackCost("curse_stacks", 5)]
    curse_mark.sfx = ("skill", "cast_complete")
    curse_mark.metadata = {
        "curse_cost": 5,
        "scaling": "저주당 +25%"
    }
    skills.append(curse_mark)
    
    # ============================================================
    # 9. 악몽 (수면 + 피해)
    # ============================================================
    nightmare = Skill(
        "shaman_nightmare",
        "악몽",
        "악몽을 심는다. 수면 2턴 + 피해 + 저주 +2."
    )
    nightmare.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magic"),
        StatusEffect(StatusType.SLEEP, duration=2, value=1.0),
        GimmickEffect(GimmickOperation.ADD, "curse_stacks", 2, max_value=10)
    ]
    nightmare.costs = [MPCost(10)]
    nightmare.sfx = ("character", "status_debuff")
    nightmare.metadata = {
        "cc": True,
        "sleep": 2,
        "curse_gain": 2
    }
    skills.append(nightmare)
    
    # ============================================================
    # 10. 궁극기: 대저주
    # ============================================================
    ultimate = Skill(
        "shaman_ultimate",
        "대저주",
        "모든 저주 해방! 전체 극대 피해 + 저주 전소비."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="magic",
                    gimmick_bonus={"field": "curse_stacks", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 3.5, stat_type="magic"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                    damage_stat="magic", damage_multiplier=0.15),
        BuffEffect(BuffType.ATTACK_DOWN, 0.30, duration=4),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.25, duration=4),
        GimmickEffect(GimmickOperation.SET, "curse_stacks", 0)
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
        "curse_consume_all": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크: 조상의 분노
    # ============================================================
    teamwork = TeamworkSkill(
        "shaman_teamwork",
        "조상의 분노",
        "조상령 강림! 전체 피해 + 저주 MAX + 디버프.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 2.2, stat_type="magic"),
        DamageEffect(DamageType.HP, 1.8, stat_type="magic"),
        GimmickEffect(GimmickOperation.SET, "curse_stacks", 10),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.25, duration=3)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "curse_max": True
    }
    skills.append(teamwork)
    
    return skills


def register_shaman_skills(skill_manager):
    """무당 스킬 등록"""
    skills = create_shaman_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"무당 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
