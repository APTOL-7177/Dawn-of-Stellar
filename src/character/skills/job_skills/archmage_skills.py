"""Archmage Skills - 아크메이지 스킬 (원소 조합 시스템 v2.0)

아크메이지 융합 스킬 재설계:
- 폭뢰섬 (화염+번개): 연쇄 폭발 공격
- 극한뇌전 (빙결+번개): 감전 마비 공격
- 상반의 격류 (화염+빙결): 열충격 파쇄 공격

유틸리티 스킬:
- 원소 순환: 원소 변환 시스템
- 원소 과부하: 단일 원소 극대화
- 지연 마법진: 트랩 설치 시스템
- 원소 장막: 보호막 생성
- 원소 낙인: 취약점 부여
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.archmage_effects import (
    ChainDamageEffect,
    ElectrocutionEffect,
    ThermalShockEffect,
    ElementalTransmutationEffect,
    ElementalOverloadEffect,
    ElementalBrandEffect,
    ElementalAegisEffect,
    DelayedGlyphEffect
)
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_archmage_skills():
    """아크메이지 스킬 생성 (원소 조합 시스템 v2.0)"""

    skills = []

    # ========================================
    # 기본 스킬 (원소 획득)
    # ========================================

    # 1. 기본 BRV: 화염구
    fireball = Skill("archmage_fireball", "화염구", "화염 원소 획득")
    fireball.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "fire_element", 1, max_value=5)
    ]
    fireball.costs = []  # 기본 공격은 MP 소모 없음
    fireball.sfx = ("skill", "fire")
    fireball.metadata = {"element": "fire", "element_gain": 1}
    skills.append(fireball)

    # 2. 기본 HP: 번개 화살
    lightning_bolt = Skill("archmage_lightning_bolt", "번개 화살", "번개 원소 획득")
    lightning_bolt.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "lightning_element", 1, max_value=5)
    ]
    lightning_bolt.costs = []
    lightning_bolt.sfx = ("skill", "bolt")
    lightning_bolt.metadata = {"element": "lightning", "element_gain": 1}
    skills.append(lightning_bolt)

    # 3. 빙결 폭풍
    ice_storm = Skill("archmage_ice_storm", "빙결 폭풍", "빙결 원소 획득 광역 공격")
    ice_storm.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "ice_element", 1, max_value=5)
    ]
    ice_storm.costs = []
    ice_storm.target_type = "all_enemies"
    ice_storm.is_aoe = True
    ice_storm.cast_time = 0.3
    ice_storm.sfx = ("skill", "ice")
    ice_storm.metadata = {"element": "ice", "element_gain": 1, "aoe": True}
    skills.append(ice_storm)

    # ========================================
    # 2원소 융합 스킬 (재설계)
    # ========================================

    # 4. 폭뢰섬 (화염+번개) - 연쇄 폭발 공격
    thunderstorm_inferno = Skill(
        "archmage_thunderstorm_inferno",
        "폭뢰섬",
        "화염+번개 융합: 연쇄 폭발! 화염 스택당 연쇄 확률 +20%, 번개 스택만큼 최대 연쇄 횟수"
    )
    thunderstorm_inferno.effects = [
        ChainDamageEffect(
            base_multiplier=1.8,
            chain_chance_per_stack=0.20,
            damage_falloff=[0.70, 0.50, 0.30, 0.20, 0.15],
            stat_type="magical"
        )
    ]
    thunderstorm_inferno.costs = [MPCost(8), StackCost("fire_element", 1), StackCost("lightning_element", 1)]
    thunderstorm_inferno.cast_time = 0.25
    thunderstorm_inferno.sfx = ("skill", "cast_complete")
    thunderstorm_inferno.metadata = {
        "fusion": True,
        "elements": ["fire", "lightning"],
        "element_cost": 2,
        "special": "chain_explosion",
        "multi_hit": 2  # 연쇄 폭발 감각
    }
    skills.append(thunderstorm_inferno)

    # 5. 극한뇌전 (빙결+번개) - 감전 마비 공격
    arctic_tempest = Skill(
        "archmage_arctic_tempest",
        "극한뇌전",
        "빙결+번개 융합: 감전 마비! 번개 스택당 마비 확률 +10%, 빙결 스택당 둔화 -10%"
    )
    arctic_tempest.effects = [
        ElectrocutionEffect(
            base_brv_multiplier=2.2,
            base_hp_multiplier=1.2,
            paralyze_chance_per_stack=0.10,
            atb_slow_per_stack=0.10,
            stat_type="magical"
        )
    ]
    arctic_tempest.costs = [MPCost(8), StackCost("ice_element", 1), StackCost("lightning_element", 1)]
    arctic_tempest.cast_time = 0.25
    arctic_tempest.sfx = ("skill", "cast_complete")
    arctic_tempest.metadata = {
        "fusion": True,
        "elements": ["ice", "lightning"],
        "element_cost": 2,
        "special": "electrocution",
        "multi_hit": 2  # 번개/빙결 이중 타격감
    }
    skills.append(arctic_tempest)

    # 6. 상반의 격류 (화염+빙결) - 열충격 파쇄 공격
    paradox_surge = Skill(
        "archmage_paradox_surge",
        "상반의 격류",
        "화염+빙결 융합: 열충격 파쇄! 스택 차이만큼 추가 데미지, 균형 시 크리티컬 +40%"
    )
    paradox_surge.effects = [
        ThermalShockEffect(
            base_multiplier=2.0,
            diff_bonus_per_stack=0.15,
            balance_crit_bonus=0.40,
            balance_crit_multiplier=2.2,
            stat_type="magical"
        )
    ]
    paradox_surge.costs = [MPCost(8), StackCost("fire_element", 1), StackCost("ice_element", 1)]
    paradox_surge.cast_time = 0.25
    paradox_surge.sfx = ("skill", "cast_complete")
    paradox_surge.metadata = {
        "fusion": True,
        "elements": ["fire", "ice"],
        "element_cost": 2,
        "special": "thermal_shock",
        "multi_hit": 2  # 연속 파쇄 느낌을 위해 2타 처리
    }
    skills.append(paradox_surge)

    # 7. 메테오
    meteor = Skill("archmage_meteor", "메테오", "3원소 각 2개씩 소비 대마법")
    meteor.effects = [
        DamageEffect(DamageType.BRV, 0.5,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.08}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 0.5,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.08}, stat_type="magical"),
        DamageEffect(DamageType.HP, 0.7,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.1}, stat_type="magical")
    ]
    meteor.costs = [MPCost(15), StackCost("fire_element", 2), StackCost("ice_element", 2), StackCost("lightning_element", 2)]
    meteor.target_type = "all_enemies"
    meteor.is_aoe = True
    meteor.cast_time = 0.75  # ATB 75% 캐스팅 (강력한 마법)
    meteor.sfx = ("skill", "ultima")  # 메테오
    meteor.metadata = {
        "fusion": True,
        "elements": ["fire", "ice", "lightning"],
        "element_cost": 6,
        "aoe": True,
        # 떨어지는 유성 타수 표현 (타격감/로그용)
        "multi_hit": 3
    }
    skills.append(meteor)

    # 8. 비전 미사일
    arcane_missile = Skill("archmage_arcane_missile", "비전 미사일", "모든 원소 스택 소비 (최소 9개)")
    arcane_missile.effects = [
        DamageEffect(DamageType.BRV_HP, 1.5,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.BRV_HP, 0.8,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.2}, stat_type="magical"),
        DamageEffect(DamageType.BRV_HP, 0.8,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "fire_element", 0),
        GimmickEffect(GimmickOperation.SET, "ice_element", 0),
        GimmickEffect(GimmickOperation.SET, "lightning_element", 0)
    ]
    arcane_missile.costs = [MPCost(15)]
    arcane_missile.cast_time = 0.6  # ATB 60% 캐스팅
    arcane_missile.sfx = ("combat", "attack_physical")  # 비전 미사일
    arcane_missile.metadata = {"element_consume_all": True, "element_scaling": True, "min_total_stacks": 9}
    skills.append(arcane_missile)

    # ========================================
    # 유틸리티 스킬 (신규)
    # ========================================

    # 9. 원소 순환 (Elemental Transmutation) - 원소 변환
    elemental_transmutation = Skill(
        "archmage_elemental_transmutation",
        "원소 순환",
        "원소 2개 소비 → 다른 원소 3개 생성. 완전 순환 시 모든 원소 +1, 마법 공격력 +20%"
    )
    elemental_transmutation.effects = [
        ElementalTransmutationEffect(consume_amount=2, generate_amount=3)
    ]
    elemental_transmutation.costs = [MPCost(4)]
    elemental_transmutation.target_type = "self"
    elemental_transmutation.sfx = ("skill", "cast_complete")
    elemental_transmutation.metadata = {
        "utility": True,
        "element_transform": True,
        "requires_selection": True  # UI에서 변환할 원소 선택 필요
    }
    skills.append(elemental_transmutation)

    # 10. 원소 과부하 (Elemental Overload) - 단일 원소 극대화
    elemental_overload = Skill(
        "archmage_elemental_overload",
        "원소 과부하",
        "선택한 원소 전체 소비 (최소 3개). 5스택 시 특수 효과 발동"
    )
    elemental_overload.effects = [
        ElementalOverloadEffect(min_stacks=3)
    ]
    elemental_overload.costs = [MPCost(12)]
    elemental_overload.target_type = "all_enemies"  # 화염/빙결은 광역, 번개는 단일
    elemental_overload.is_aoe = True
    elemental_overload.cast_time = 0.5
    elemental_overload.sfx = ("skill", "limit_break")
    elemental_overload.metadata = {
        "utility": True,
        "element_consume": True,
        "requires_selection": True,  # UI에서 원소 선택 필요
        "special_at_5": True
    }
    skills.append(elemental_overload)

    # 11. 지연 마법진 (Delayed Glyph) - 트랩 설치
    delayed_glyph = Skill(
        "archmage_delayed_glyph",
        "지연 마법진",
        "원소 마법진 설치 (최대 3개). 3턴 후 자동 발동 또는 융합 스킬로 기폭"
    )
    delayed_glyph.effects = [
        DelayedGlyphEffect(delay_turns=3)
    ]
    delayed_glyph.costs = [MPCost(3)]
    delayed_glyph.target_type = "self"
    delayed_glyph.sfx = ("skill", "cast_complete")
    delayed_glyph.metadata = {
        "utility": True,
        "trap": True,
        "requires_selection": True,  # UI에서 원소 선택 필요
        "max_glyphs": 3
    }
    skills.append(delayed_glyph)

    # 12. 원소 장막 (Elemental Aegis) - 보호막 생성
    elemental_aegis = Skill(
        "archmage_elemental_aegis",
        "원소 장막",
        "아군 전체 공유 보호막 생성 (최소 7개). HP 피해 1당 보호막 4 소모. 완전 보호 시 1.5배"
    )
    elemental_aegis.effects = [
        ElementalAegisEffect(base_multiplier=4.5, duration=3)
    ]
    elemental_aegis.costs = [MPCost(10)]
    elemental_aegis.target_type = "self"
    elemental_aegis.sfx = ("character", "status_buff")
    elemental_aegis.metadata = {
        "utility": True,
        "defensive": True,
        "shield": True,
        "min_total_stacks": 7
    }
    skills.append(elemental_aegis)

    # 13. 원소 낙인 (Elemental Brand) - 취약점 부여
    elemental_brand = Skill(
        "archmage_elemental_brand",
        "원소 낙인",
        "적에게 3가지 원소 낙인 부여 (5턴). 원소 피해 +40%, 융합 스킬 데미지 +50%"
    )
    elemental_brand.effects = [
        ElementalBrandEffect(vulnerability=0.40, duration=5)
    ]
    elemental_brand.costs = [
        MPCost(8),
        StackCost("fire_element", 1),
        StackCost("ice_element", 1),
        StackCost("lightning_element", 1)
    ]
    elemental_brand.cast_time = 0.2
    elemental_brand.sfx = ("skill", "cast_complete")
    elemental_brand.metadata = {
        "utility": True,
        "debuff": True,
        "element_cost": 3,
        "boss_opener": True
    }
    skills.append(elemental_brand)

    # 14. 원소 폭주 - 모든 원소 획득 + 마법 강화
    elemental_surge = Skill("archmage_elemental_surge", "원소 폭주", "모든 원소 획득 + 마법 강화")
    elemental_surge.effects = [
        GimmickEffect(GimmickOperation.ADD, "fire_element", 2, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "ice_element", 2, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "lightning_element", 2, max_value=5),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=4)
    ]
    elemental_surge.costs = [MPCost(7)]
    elemental_surge.target_type = "self"
    elemental_surge.sfx = ("character", "status_buff")
    elemental_surge.metadata = {"element_gain_all": True, "buff": True}
    skills.append(elemental_surge)

    # ========================================
    # 궁극기 및 팀워크
    # ========================================

    # 15. 궁극기: 원소 대폭발
    ultimate = Skill("archmage_ultimate", "원소 대폭발", "모든 원소를 폭발시켜 파멸")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "fire_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "ice_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0,
                    gimmick_bonus={"field": "lightning_element", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.2, stat_type="magical"),
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
