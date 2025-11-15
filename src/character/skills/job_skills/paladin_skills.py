"""Paladin Skills - 팔라딘 스킬 (성력/신성 보호 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_paladin_skills():
    """팔라딘 9개 스킬 생성"""
    
    # 1. 기본 BRV: 성스러운 일격
    holy_strike = Skill("paladin_holy_strike", "성스러운 일격", "신성한 힘으로 공격, 성력 획득")
    holy_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    holy_strike.costs = []  # 기본 공격은 MP 소모 없음
    
    # 2. 기본 HP: 신성한 심판
    divine_judgment = Skill("paladin_judgment", "신성한 심판", "성력 소비 심판의 일격")
    divine_judgment.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "holy_power", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 1)
    ]
    divine_judgment.costs = []  # 기본 공격은 MP 소모 없음
    
    # 3. 신성한 보호막
    divine_shield = Skill("paladin_divine_shield", "신성한 보호막", "성력으로 강력한 보호막")
    divine_shield.effects = [
        ShieldEffect(base_amount=50, multiplier=1.0, stat_name="holy_power"),
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 2)
    ]
    divine_shield.costs = [MPCost(8), StackCost("holy_power", 2)]
    divine_shield.target_type = "self"
    divine_shield.cooldown = 4
    
    # 4. 신성화
    consecration = Skill("paladin_consecration", "신성화", "땅을 신성화, 지속 피해")
    consecration.effects = [
        DamageEffect(DamageType.BRV, 1.3),
        DamageEffect(DamageType.BRV, 1.3),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    consecration.costs = [MPCost(6)]
    consecration.cooldown = 3
    
    # 5. 성스러운 빛
    holy_light = Skill("paladin_holy_light", "성스러운 빛", "아군 치유 + 성력")
    holy_light.effects = [
        HealEffect(HealType.HP, percentage=0.35),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    holy_light.costs = [MPCost(8)]
    holy_light.target_type = "ally"
    holy_light.cooldown = 2
    
    # 6. 정의의 망치
    hammer = Skill("paladin_hammer", "정의의 망치", "성력 비례 강타")
    hammer.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "holy_power", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    hammer.costs = [MPCost(9)]
    hammer.cooldown = 3
    
    # 7. 축복
    blessing = Skill("paladin_blessing", "축복", "파티 전체 방어 버프")
    blessing.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4, is_party_wide=True),
        BuffEffect(BuffType.SPIRIT_UP, 0.3, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    blessing.costs = [MPCost(10)]
    blessing.target_type = "party"
    blessing.cooldown = 5
    
    # 8. 복수의 격노
    avenging_wrath = Skill("paladin_wrath", "복수의 격노", "성력 3 소비, 강력한 버프")
    avenging_wrath.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=5),
        ShieldEffect(base_amount=80),
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 3)
    ]
    avenging_wrath.costs = [MPCost(12), StackCost("holy_power", 3)]
    avenging_wrath.target_type = "self"
    avenging_wrath.cooldown = 6
    
    # 9. 궁극기: 신성한 폭풍
    ultimate = Skill("paladin_ultimate", "신성한 폭풍", "성력으로 신성 폭풍 + 파티 힐")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "holy_power", "multiplier": 0.4}),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "holy_power", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 3.0),
        HealEffect(HealType.HP, percentage=0.4, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "holy_power", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    
    return [holy_strike, divine_judgment, divine_shield, consecration, holy_light,
            hammer, blessing, avenging_wrath, ultimate]

def register_paladin_skills(skill_manager):
    """팔라딘 스킬 등록"""
    skills = create_paladin_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
