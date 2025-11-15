"""Archmage Skills - 아크메이지 스킬 (원소 조합 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_archmage_skills():
    """아크메이지 9개 스킬 생성"""

    # 1. 기본 BRV: 화염구
    fireball = Skill("archmage_fireball", "화염구", "화염 원소 획득")
    fireball.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "fire_element", 1, max_value=5)
    ]
    fireball.costs = []  # 기본 공격은 MP 소모 없음
    fireball.sfx = ("skill", "fire")

    # 2. 기본 HP: 번개 화살
    lightning_bolt = Skill("archmage_lightning_bolt", "번개 화살", "번개 원소 획득")
    lightning_bolt.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "lightning_element", 1, max_value=5)
    ]
    lightning_bolt.costs = []  # 기본 공격은 MP 소모 없음
    lightning_bolt.sfx = ("skill", "bolt")

    # 3. 빙결 폭풍
    ice_storm = Skill("archmage_ice_storm", "빙결 폭풍", "빙결 원소 획득 광역 공격")
    ice_storm.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "ice_element", 1, max_value=5)
    ]
    ice_storm.costs = [MPCost(8)]
    ice_storm.cooldown = 2
    ice_storm.is_aoe = True
    ice_storm.cast_time = 0.3  # ATB 30% 캐스팅
    ice_storm.sfx = ("skill", "ice")

    # 4. 화염+번개 융합
    flame_lightning = Skill("archmage_flame_lightning", "화염뇌", "화염+번개 소비 융합 공격")
    flame_lightning.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.0,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.2}, stat_type="magical")
    ]
    flame_lightning.costs = [MPCost(9), StackCost("fire_element", 1), StackCost("lightning_element", 1)]
    flame_lightning.cooldown = 3
    flame_lightning.cast_time = 0.25  # ATB 25% 캐스팅
    flame_lightning.sfx = ("skill", "bolt2")

    # 5. 빙결+번개 융합
    ice_lightning = Skill("archmage_ice_lightning", "빙결뇌", "빙결+번개 소비 융합 공격")
    ice_lightning.effects = [
        DamageEffect(DamageType.BRV, 2.2,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.2,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.25}, stat_type="magical")
    ]
    ice_lightning.costs = [MPCost(9), StackCost("ice_element", 1), StackCost("lightning_element", 1)]
    ice_lightning.cooldown = 3
    ice_lightning.cast_time = 0.25  # ATB 25% 캐스팅
    ice_lightning.sfx = ("skill", "ice3")

    # 6. 화염+빙결 융합
    flame_ice = Skill("archmage_flame_ice", "염빙", "화염+빙결 소비 융합 공격")
    flame_ice.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.2,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.3}, stat_type="magical")
    ]
    flame_ice.costs = [MPCost(9), StackCost("fire_element", 1), StackCost("ice_element", 1)]
    flame_ice.cooldown = 3
    flame_ice.cast_time = 0.25  # ATB 25% 캐스팅
    flame_ice.sfx = ("skill", "fire2")

    # 7. 메테오
    meteor = Skill("archmage_meteor", "메테오", "3원소 소비 대마법")
    meteor.effects = [
        DamageEffect(DamageType.BRV, 2.5,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.5,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.0,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.3}, stat_type="magical")
    ]
    meteor.costs = [MPCost(15), StackCost("fire_element", 1), StackCost("ice_element", 1), StackCost("lightning_element", 1)]
    meteor.cooldown = 5
    meteor.is_aoe = True
    meteor.cast_time = 0.5  # ATB 50% 캐스팅 (강력한 마법)
    meteor.sfx = ("skill", "fire3")

    # 8. 비전 미사일
    arcane_missile = Skill("archmage_arcane_missile", "비전 미사일", "모든 원소 스택 소비")
    arcane_missile.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.BRV_HP, 1.0,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.BRV_HP, 1.0,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.25}, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "fire_element", 0),
        GimmickEffect(GimmickOperation.SET, "ice_element", 0),
        GimmickEffect(GimmickOperation.SET, "lightning_element", 0)
    ]
    arcane_missile.costs = [MPCost(18)]
    arcane_missile.cooldown = 6
    arcane_missile.cast_time = 0.6  # ATB 60% 캐스팅
    arcane_missile.sfx = ("skill", "bolt3")

    # 9. 궁극기: 원소 대폭발
    ultimate = Skill("archmage_ultimate", "원소 대폭발", "모든 원소를 폭발시켜 파멸")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "fire_element", 0),
        GimmickEffect(GimmickOperation.SET, "ice_element", 0),
        GimmickEffect(GimmickOperation.SET, "lightning_element", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.is_aoe = True
    ultimate.cooldown = 10
    ultimate.cast_time = 1.0  # ATB 100% 캐스팅 (궁극기는 한 턴 전체 필요)
    ultimate.sfx = ("skill", "ultima")

    return [fireball, lightning_bolt, ice_storm, flame_lightning, ice_lightning,
            flame_ice, meteor, arcane_missile, ultimate]

def register_archmage_skills(skill_manager):
    """아크메이지 스킬 등록"""
    skills = create_archmage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
