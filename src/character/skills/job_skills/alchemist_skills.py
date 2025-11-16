"""Alchemist Skills - 연금술사 스킬 (포션/폭탄 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_alchemist_skills():
    """연금술사 10개 스킬 생성 (포션/폭탄 시스템)"""

    skills = []

    # 1. 기본 BRV: 포션 투척
    throw_potion = Skill("alchemist_throw_potion", "포션 투척", "포션을 던져 공격, 재료 획득")
    throw_potion.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 1, max_value=10)
    ]
    throw_potion.costs = []  # 기본 공격은 MP 소모 없음
    throw_potion.sfx = "338"  # FFVII potion throw sound
    throw_potion.metadata = {"potion_gain": 1}
    skills.append(throw_potion)

    # 2. 기본 HP: 폭발 포션
    explosive_potion = Skill("alchemist_explosive", "폭발 포션", "포션 소비 폭발")
    explosive_potion.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "potion_stock", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 1)
    ]
    explosive_potion.costs = []  # 기본 공격은 MP 소모 없음
    explosive_potion.sfx = "344"  # FFVII explosion sound
    explosive_potion.metadata = {"potion_cost": 1, "potion_scaling": True}
    skills.append(explosive_potion)

    # 3. 회복 포션
    healing_potion = Skill("alchemist_heal_potion", "회복 포션", "강력한 회복")
    healing_potion.effects = [
        HealEffect(HealType.HP, percentage=0.4),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 2)
    ]
    healing_potion.costs = [MPCost(6), StackCost("potion_stock", 2)]
    healing_potion.target_type = "ally"
    healing_potion.sfx = "352"  # FFVII healing sound
    healing_potion.cooldown = 2
    healing_potion.metadata = {"potion_cost": 2, "healing": True}
    skills.append(healing_potion)

    # 4. 버프 포션
    buff_potion = Skill("alchemist_buff_potion", "버프 포션", "모든 능력치 상승")
    buff_potion.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.3, duration=4),
        BuffEffect(BuffType.MAGIC_UP, 0.3, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 3)
    ]
    buff_potion.costs = [MPCost(10), StackCost("potion_stock", 3)]
    buff_potion.target_type = "ally"
    buff_potion.sfx = "362"  # FFVII buff sound
    buff_potion.cooldown = 4
    buff_potion.metadata = {"potion_cost": 3, "buff": True}
    skills.append(buff_potion)

    # 5. 독 폭탄
    poison_bomb = Skill("alchemist_poison_bomb", "독 폭탄", "지속 피해 폭탄")
    poison_bomb.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="magical"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                    damage_stat="magic", damage_multiplier=0.15),  # 독 DoT: 마법 공격력의 15%
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 1, max_value=10)
    ]
    poison_bomb.costs = [MPCost(12)]
    poison_bomb.sfx = "376"  # FFVII poison sound
    poison_bomb.cooldown = 3
    poison_bomb.metadata = {"potion_gain": 1, "poison": True}
    skills.append(poison_bomb)

    # 6. 재료 수집
    gather_materials = Skill("alchemist_gather", "재료 수집", "포션 재료 대량 수집")
    gather_materials.effects = [
        GimmickEffect(GimmickOperation.ADD, "potion_stock", 5, max_value=10),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=3)  # 방어 태세
    ]
    gather_materials.costs = [MPCost(8)]
    gather_materials.target_type = "self"
    gather_materials.sfx = "404"  # FFVII gather sound
    gather_materials.cooldown = 4
    gather_materials.metadata = {"potion_gain": 5}
    skills.append(gather_materials)

    # 7. 마나 포션
    mana_potion = Skill("alchemist_mana_potion", "마나 포션", "MP 대량 회복")
    mana_potion.effects = [
        HealEffect(HealType.MP, base_amount=50),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 2)
    ]
    mana_potion.costs = [MPCost(4), StackCost("potion_stock", 2)]
    mana_potion.target_type = "ally"
    mana_potion.sfx = "423"  # FFVII mana sound
    mana_potion.cooldown = 5
    mana_potion.metadata = {"potion_cost": 2, "mp_recovery": True}
    skills.append(mana_potion)

    # 8. 폭발 연쇄
    chain_explosion = Skill("alchemist_chain", "폭발 연쇄", "연쇄 폭발")
    chain_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "potion_stock", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 4)
    ]
    chain_explosion.costs = [MPCost(18), StackCost("potion_stock", 4)]
    chain_explosion.sfx = "438"  # FFVII chain explosion sound
    chain_explosion.cooldown = 5
    chain_explosion.metadata = {"potion_cost": 4, "potion_scaling": True, "chain": True}
    chain_explosion.is_aoe = True
    skills.append(chain_explosion)

    # 9. 산성 플라스크 (NEW - 10번째 스킬)
    acid_flask = Skill("alchemist_acid_flask", "산성 플라스크", "방어력 감소 + 피해")
    acid_flask.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.5, duration=4),
        BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "potion_stock", 3)
    ]
    acid_flask.costs = [MPCost(15), StackCost("potion_stock", 3)]
    acid_flask.sfx = "467"  # FFVII acid sound
    acid_flask.cooldown = 4
    acid_flask.metadata = {"potion_cost": 3, "debuff": True}
    skills.append(acid_flask)

    # 10. 궁극기: 현자의 물약
    ultimate = Skill("alchemist_ultimate", "현자의 물약", "완벽한 물약으로 파티 강화")
    ultimate.effects = [
        HealEffect(HealType.HP, percentage=0.5, is_party_wide=True),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=5),
        GimmickEffect(GimmickOperation.SET, "potion_stock", 10)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.target_type = "party"
    ultimate.is_aoe = True
    ultimate.sfx = "696"  # FFVII ultimate alchemy sound
    ultimate.cooldown = 8
    ultimate.metadata = {"ultimate": True, "party_support": True, "potion_refill": True}
    skills.append(ultimate)

    return skills

def register_alchemist_skills(skill_manager):
    """연금술사 스킬 등록"""
    skills = create_alchemist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
