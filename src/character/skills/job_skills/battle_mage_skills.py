"""Battle Mage Skills - 배틀메이지 스킬 (룬 폭발 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_battle_mage_skills():
    """배틀메이지 9개 스킬"""
    skills = []

    # 1. 기본 BRV: 룬 새기기
    engrave_rune = Skill("bmage_engrave", "룬 새기기", "적에게 룬 각인")
    engrave_rune.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),
        StatusEffect(StatusType.RUNE, duration=99, stackable=True),  # 적에게 룬 마크
        GimmickEffect(GimmickOperation.ADD, "rune_stacks", 1, max_value=8)  # 자신의 룬 스택 증가
    ]
    engrave_rune.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(engrave_rune)
    
    # 2. 기본 HP: 룬 폭발
    rune_burst = Skill("bmage_burst", "룬 폭발", "룬 폭발 공격")
    rune_burst.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "rune_stacks", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "rune_stacks", 1),
        StatusEffect(StatusType.RUNE, remove=True)  # 적의 룬 마크 제거
    ]
    rune_burst.costs = []  # 기본 공격은 MP 소모 없음
    rune_burst.aoe_effect = DamageEffect(DamageType.BRV, 0.3, stat_type="magical")  # 룬 폭발 광역 피해 (약함)
    skills.append(rune_burst)
    
    # 3. 룬 강화
    empower_rune = Skill("bmage_empower", "룬 강화", "룬 위력 강화")
    empower_rune.effects = [
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=4),
        GimmickEffect(GimmickOperation.ADD, "rune_stacks", 2, max_value=8)
    ]
    empower_rune.costs = [MPCost(6)]
    empower_rune.target_type = "self"
    empower_rune.cooldown = 3
    skills.append(empower_rune)
    
    # 4. 연쇄 폭발
    chain_burst = Skill("bmage_chain", "연쇄 폭발", "다중 룬 폭발")
    chain_burst.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "rune_stacks", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "rune_stacks", 2),
        StatusEffect(StatusType.RUNE, remove=True)  # 적의 룬 마크 제거
    ]
    chain_burst.costs = [MPCost(9), StackCost("rune_stacks", 2)]
    chain_burst.cooldown = 2
    chain_burst.aoe_effect = DamageEffect(DamageType.BRV, 0.4, stat_type="magical")  # 룬 폭발 광역 피해
    skills.append(chain_burst)
    
    # 5. 마법검
    magic_blade = Skill("bmage_blade", "마법검", "룬 부여 검격")
    magic_blade.effects = [
        DamageEffect(DamageType.BRV, 1.6, gimmick_bonus={"field": "rune_stacks", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "rune_stacks", 1, max_value=8)
    ]
    magic_blade.costs = [MPCost(8)]
    magic_blade.cooldown = 2
    skills.append(magic_blade)
    
    # 6. 룬 방어
    rune_shield = Skill("bmage_shield", "룬 방어", "룬으로 보호")
    rune_shield.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3),
        BuffEffect(BuffType.SPIRIT_UP, 0.3, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "rune_stacks", 2)
    ]
    rune_shield.costs = [MPCost(7), StackCost("rune_stacks", 2)]
    rune_shield.target_type = "self"
    rune_shield.cooldown = 4
    skills.append(rune_shield)
    
    # 7. 룬 폭풍
    rune_storm = Skill("bmage_storm", "룬 폭풍", "광역 룬 공격")
    rune_storm.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "rune_stacks", "multiplier": 0.35}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "rune_stacks", 3),
        StatusEffect(StatusType.RUNE, remove=True)  # 적의 룬 마크 제거
    ]
    rune_storm.costs = [MPCost(11), StackCost("rune_stacks", 3)]
    rune_storm.cooldown = 4
    rune_storm.aoe_effect = DamageEffect(DamageType.BRV, 0.5, stat_type="magical")  # 룬 폭발 광역 피해
    skills.append(rune_storm)
    
    # 8. 고대 룬
    ancient_rune = Skill("bmage_ancient", "고대 룬", "강력한 고대 룬")
    ancient_rune.effects = [
        GimmickEffect(GimmickOperation.SET, "rune_stacks", 8),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=4)
    ]
    ancient_rune.costs = [MPCost(12)]
    ancient_rune.target_type = "self"
    ancient_rune.cooldown = 6
    skills.append(ancient_rune)
    
    # 9. 궁극기: 룬 대폭발
    ultimate = Skill("bmage_ultimate", "룬 대폭발", "모든 룬 폭발")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "rune_stacks", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "rune_stacks", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.5, stat_type="magical"),
        BuffEffect(BuffType.MAGIC_UP, 0.6, duration=5),
        GimmickEffect(GimmickOperation.SET, "rune_stacks", 0),
        StatusEffect(StatusType.RUNE, remove=True)  # 적의 룬 마크 제거
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    ultimate.aoe_effect = DamageEffect(DamageType.BRV_HP, 1.0, stat_type="magical")  # 룬 대폭발 강력한 광역 피해
    skills.append(ultimate)
    
    return skills

def register_battle_mage_skills(skill_manager):
    skills = create_battle_mage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
