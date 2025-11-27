"""Archmage Skills - 아크메이지 스킬 (원소 조합 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_archmage_skills():
    """아크메이지 10개 스킬 생성 (원소 조합 시스템)"""

    skills = []

    # 1. 기본 BRV: 화염구
    fireball = Skill("archmage_fireball", "화염구", "화염 원소 획득")
    fireball.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "fire_element", 1, max_value=5)
    ]
    fireball.costs = []  # 기본 공격은 MP 소모 없음
    fireball.sfx = ("skill", "fire")  # 화염구
    fireball.metadata = {"element": "fire", "element_gain": 1}
    skills.append(fireball)

    # 2. 기본 HP: 번개 화살
    lightning_bolt = Skill("archmage_lightning_bolt", "번개 화살", "번개 원소 획득")
    lightning_bolt.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "lightning_element", 1, max_value=5)
    ]
    lightning_bolt.costs = []  # 기본 공격은 MP 소모 없음
    lightning_bolt.sfx = ("skill", "bolt")  # 번개 화살
    lightning_bolt.metadata = {"element": "lightning", "element_gain": 1}
    skills.append(lightning_bolt)

    # 3. 빙결 폭풍
    ice_storm = Skill("archmage_ice_storm", "빙결 폭풍", "빙결 원소 획득 광역 공격")
    ice_storm.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "ice_element", 1, max_value=5)
    ]
    ice_storm.costs = []
    # ice_storm.cooldown = 2  # 쿨다운 시스템 제거됨
    ice_storm.target_type = "all_enemies"
    ice_storm.is_aoe = True
    ice_storm.cast_time = 0.3  # ATB 30% 캐스팅
    ice_storm.sfx = ("skill", "ice")  # 빙결 폭풍
    ice_storm.metadata = {"element": "ice", "element_gain": 1, "aoe": True}
    skills.append(ice_storm)

    # 4. 화염+번개 융합
    flame_lightning = Skill("archmage_flame_lightning", "화염뇌", "화염+번개 소비 융합 공격")
    flame_lightning.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.0,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.2}, stat_type="magical")
    ]
    flame_lightning.costs = [MPCost(5), StackCost("fire_element", 1), StackCost("lightning_element", 1)]
    # flame_lightning.cooldown = 3  # 쿨다운 시스템 제거됨
    flame_lightning.cast_time = 0.25  # ATB 25% 캐스팅
    flame_lightning.sfx = ("skill", "cast_complete")  # 화염뇌
    flame_lightning.metadata = {"fusion": True, "elements": ["fire", "lightning"], "element_cost": 2}
    skills.append(flame_lightning)

    # 5. 빙결+번개 융합
    ice_lightning = Skill("archmage_ice_lightning", "빙결뇌", "빙결+번개 소비 융합 공격")
    ice_lightning.effects = [
        DamageEffect(DamageType.BRV, 2.2,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.2,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.25}, stat_type="magical")
    ]
    ice_lightning.costs = [MPCost(5), StackCost("ice_element", 1), StackCost("lightning_element", 1)]
    # ice_lightning.cooldown = 3  # 쿨다운 시스템 제거됨
    ice_lightning.cast_time = 0.25  # ATB 25% 캐스팅
    ice_lightning.sfx = ("skill", "cast_complete")  # 빙결뇌
    ice_lightning.metadata = {"fusion": True, "elements": ["ice", "lightning"], "element_cost": 2}
    skills.append(ice_lightning)

    # 6. 화염+빙결 융합
    flame_ice = Skill("archmage_flame_ice", "염빙", "화염+빙결 소비 융합 공격")
    flame_ice.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.2,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.3}, stat_type="magical")
    ]
    flame_ice.costs = [MPCost(5), StackCost("fire_element", 1), StackCost("ice_element", 1)]
    # flame_ice.cooldown = 3  # 쿨다운 시스템 제거됨
    flame_ice.cast_time = 0.25  # ATB 25% 캐스팅
    flame_ice.sfx = ("skill", "cast_complete")  # 염빙
    flame_ice.metadata = {"fusion": True, "elements": ["fire", "ice"], "element_cost": 2}
    skills.append(flame_ice)

    # 7. 메테오
    meteor = Skill("archmage_meteor", "메테오", "3원소 소비 대마법")
    meteor.effects = [
        DamageEffect(DamageType.BRV, 1.0,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.0,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.5,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.3}, stat_type="magical")
    ]
    meteor.costs = [MPCost(12), StackCost("fire_element", 1), StackCost("ice_element", 1), StackCost("lightning_element", 1)]
    # meteor.cooldown = 5  # 쿨다운 시스템 제거됨
    meteor.target_type = "all_enemies"
    meteor.is_aoe = True
    meteor.cast_time = 0.75  # ATB 75% 캐스팅 (강력한 마법)
    meteor.sfx = ("skill", "ultima")  # 메테오
    meteor.metadata = {"fusion": True, "elements": ["fire", "ice", "lightning"], "element_cost": 3, "aoe": True}
    skills.append(meteor)

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
    arcane_missile.costs = [MPCost(11)]
    # arcane_missile.cooldown = 6  # 쿨다운 시스템 제거됨
    arcane_missile.cast_time = 0.6  # ATB 60% 캐스팅
    arcane_missile.sfx = ("combat", "attack_physical")  # 비전 미사일
    arcane_missile.metadata = {"element_consume_all": True, "element_scaling": True}
    skills.append(arcane_missile)

    # 9. 원소 폭주 (NEW - 10번째 스킬로 만들기 위해 추가)
    elemental_surge = Skill("archmage_elemental_surge", "원소 폭주", "모든 원소 획득 + 마법 강화")
    elemental_surge.effects = [
        GimmickEffect(GimmickOperation.ADD, "fire_element", 2, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "ice_element", 2, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "lightning_element", 2, max_value=5),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=4)
    ]
    elemental_surge.costs = [MPCost(7)]
    elemental_surge.target_type = "self"
    # elemental_surge.cooldown = 5  # 쿨다운 시스템 제거됨
    elemental_surge.sfx = ("character", "status_buff")  # 원소 폭주
    elemental_surge.metadata = {"element_gain_all": True, "buff": True}
    skills.append(elemental_surge)

    # 10. 궁극기: 원소 대폭발
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
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.cast_time = 1.0  # ATB 100% 캐스팅 (궁극기는 한 턴 전체 필요)
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "element_consume_all": True, "aoe": True, "element_scaling": True}
    skills.append(ultimate)

    # 팀워크 스킬: 원소 대폭발
    teamwork = TeamworkSkill(
        "archmage_teamwork",
        "원소 수렴",
        "전체 적 무속성 마법 BRV+HP (4.5x) + 적 전체 속성 저항 -40% (3턴)",
        gauge_cost=250)
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 4.5),  # BRV 마법 공격 4.5x
        DamageEffect(DamageType.HP, 1.0),  # HP 변환
        BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, 0.4, duration=3),  # 적 전체 속성 저항 -40%
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "buff": True, "element": True}
    skills.append(teamwork)

    return skills

def register_archmage_skills(skill_manager):
    """아크메이지 스킬 등록"""
    skills = create_archmage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 원소 수렴
    return [s.skill_id for s in skills]