"""Battle Mage Skills - 배틀메이지 스킬 (룬 공명 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_battle_mage_skills():
    """배틀메이지 10개 스킬 생성 (룬 공명 시스템)"""

    # 1. 기본 BRV: 룬 새기기 (룬 획득)
    carve_rune = Skill("battle_mage_carve_rune", "룬 새기기", "적에게 룬을 새겨 룬 획득")
    carve_rune.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="hybrid")
    ]
    carve_rune.costs = []  # 기본 공격은 MP 소모 없음
    carve_rune.metadata = {"basic_attack": True, "rune_gain": True, "random_rune": True}

    # 2. 기본 HP: 룬 폭발 (보유 룬 소모하여 강력한 공격)
    rune_burst = Skill("battle_mage_rune_burst", "룬 폭발", "보유한 룬을 폭발시켜 강력한 피해")
    rune_burst.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="hybrid",
                    gimmick_bonus={"field": "total_runes", "multiplier": 0.2}),  # 룬 1개당 +20% 피해
        # 모든 룬 1개씩 소모
        GimmickEffect(GimmickOperation.CONSUME, "rune_fire", 1),
        GimmickEffect(GimmickOperation.CONSUME, "rune_ice", 1),
        GimmickEffect(GimmickOperation.CONSUME, "rune_lightning", 1),
        GimmickEffect(GimmickOperation.CONSUME, "rune_earth", 1),
        GimmickEffect(GimmickOperation.CONSUME, "rune_arcane", 1)
    ]
    rune_burst.costs = []  # 기본 공격은 MP 소모 없음
    rune_burst.metadata = {"basic_attack": True, "consumes_runes": True}

    # 3. 화염 룬 각인 (물리 공격력 +15% 버프)
    fire_rune = Skill("battle_mage_fire_rune", "화염 룬",
                     "화염 룬 각인, 물리 공격력 +15%")
    fire_rune.effects = [
        GimmickEffect(GimmickOperation.ADD, "rune_fire", 1, max_value=3),
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=99)  # 룬 보유 동안 지속
    ]
    fire_rune.costs = [MPCost(4)]  # 다른 룬들과 동일한 MP 비용
    fire_rune.target_type = "self"
    fire_rune.metadata = {"rune_type": "fire"}

    # 4. 냉기 룬 각인 (마법 공격력 +15% 버프)
    ice_rune = Skill("battle_mage_ice_rune", "냉기 룬",
                    "냉기 룬 각인, 마법 공격력 +15%")
    ice_rune.effects = [
        GimmickEffect(GimmickOperation.ADD, "rune_ice", 1, max_value=3),
        BuffEffect(BuffType.MAGIC_UP, 0.15, duration=99)
    ]
    ice_rune.costs = [MPCost(4)]
    ice_rune.target_type = "self"
    ice_rune.metadata = {"rune_type": "ice"}

    # 5. 번개 룬 각인 (속도 +20% 버프)
    lightning_rune = Skill("battle_mage_lightning_rune", "번개 룬",
                          "번개 룬 각인, 속도 +20%")
    lightning_rune.effects = [
        GimmickEffect(GimmickOperation.ADD, "rune_lightning", 1, max_value=3),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=99)
    ]
    lightning_rune.costs = [MPCost(4)]
    lightning_rune.target_type = "self"
    lightning_rune.metadata = {"rune_type": "lightning"}

    # 6. 대지 룬 각인 (방어력 +20% 버프)
    earth_rune = Skill("battle_mage_earth_rune", "대지 룬",
                      "대지 룬 각인, 방어력 +20%")
    earth_rune.effects = [
        GimmickEffect(GimmickOperation.ADD, "rune_earth", 1, max_value=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=99)
    ]
    earth_rune.costs = [MPCost(4)]
    earth_rune.target_type = "self"
    earth_rune.metadata = {"rune_type": "earth"}

    # 7. 비전 룬 각인 (MP 회복 버프)
    arcane_rune = Skill("battle_mage_arcane_rune", "비전 룬",
                       "비전 룬 각인, MP 회복 +5/턴")
    arcane_rune.effects = [
        GimmickEffect(GimmickOperation.ADD, "rune_arcane", 1, max_value=3),
        BuffEffect(BuffType.MP_REGEN, 5, duration=99)
    ]
    arcane_rune.costs = [MPCost(4)]
    arcane_rune.target_type = "self"
    arcane_rune.metadata = {"rune_type": "arcane"}

    # 8. 룬 폭발 (보유 룬 개수에 비례한 대미지, 모든 룬 소모)
    rune_explosion = Skill("battle_mage_rune_explosion", "룬 폭발",
                          "모든 룬을 폭발시켜 강력한 피해")
    rune_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="hybrid",
                    gimmick_bonus={"field": "total_runes", "multiplier": 0.3}),  # 룬 1개당 +30% 피해
        GimmickEffect(GimmickOperation.SET, "rune_fire", 0),
        GimmickEffect(GimmickOperation.SET, "rune_ice", 0),
        GimmickEffect(GimmickOperation.SET, "rune_lightning", 0),
        GimmickEffect(GimmickOperation.SET, "rune_earth", 0),
        GimmickEffect(GimmickOperation.SET, "rune_arcane", 0)
    ]
    rune_explosion.costs = [MPCost(12)]
    # rune_explosion.cooldown = 4  # 쿨다운 시스템 제거됨
    rune_explosion.metadata = {"consumes_all_runes": True}

    # 9. 원소 융합 (3가지 이상 다른 룬 보유 시 사용 가능, 강력한 융합 공격)
    elemental_fusion = Skill("battle_mage_elemental_fusion", "원소 융합",
                            "3가지 이상 룬 필요, 원소 융합 공격")
    elemental_fusion.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="hybrid"),
        DamageEffect(DamageType.HP, 2.0, stat_type="hybrid"),
        # 각 룬 타입별로 1개씩 소모
        GimmickEffect(GimmickOperation.CONSUME, "rune_fire", 1),
        GimmickEffect(GimmickOperation.CONSUME, "rune_ice", 1),
        GimmickEffect(GimmickOperation.CONSUME, "rune_lightning", 1)
    ]
    elemental_fusion.costs = [MPCost(15)]
    # elemental_fusion.cooldown = 5  # 쿨다운 시스템 제거됨
    elemental_fusion.target_type = "single_enemy"
    elemental_fusion.metadata = {"requires_different_runes": 3}

    # 10. 궁극기: 원소 대재앙 (모든 룬을 융합하여 극한의 피해)
    ultimate = Skill("battle_mage_ultimate", "원소 대재앙",
                    "5가지 모든 원소를 융합한 궁극 마법")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.5, stat_type="hybrid",
                    gimmick_bonus={"field": "total_runes", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 3.0, stat_type="hybrid",
                    gimmick_bonus={"field": "total_runes", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.SET, "rune_fire", 0),
        GimmickEffect(GimmickOperation.SET, "rune_ice", 0),
        GimmickEffect(GimmickOperation.SET, "rune_lightning", 0),
        GimmickEffect(GimmickOperation.SET, "rune_earth", 0),
        GimmickEffect(GimmickOperation.SET, "rune_arcane", 0)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.metadata = {"ultimate": True, "elemental_cataclysm": True}

    return [carve_rune, rune_burst, fire_rune, ice_rune, lightning_rune,
            earth_rune, arcane_rune, rune_explosion, elemental_fusion, ultimate]

def register_battle_mage_skills(skill_manager):
    """배틀메이지 스킬 등록"""
    skills = create_battle_mage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
