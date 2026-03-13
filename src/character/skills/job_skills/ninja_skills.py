"""Ninja Skills - 닌자 (인법 연쇄 시스템)

속성 인술을 연결하여 강력한 연쇄 인법을 발동하는 쾌속의 닌자.
물리와 마법의 조화, 4대 속성을 자유자재로 다루며 아군을 지원한다.

"바람보다 빠르게, 불꽃보다 뜨겁게."
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("ninja_skills")


def create_ninja_skills():
    """닌자 스킬 생성 (인법 연쇄 시스템)"""

    skills = []

    # ── 기본기 (2개: BRV / HP) ──────────────────────────────────

    # 1-1. 수리검 투척 (기본 BRV)
    shuriken = Skill(
        "ninja_shuriken",
        "수리검 투척",
        "수리검으로 BRV 피해를 준다. 마지막 사용 속성의 인(印) +1."
    )
    shuriken.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
    ]
    shuriken.costs = []
    shuriken.sfx = ("combat", "attack_physical")
    shuriken.metadata = {
        "basic_attack": True,
        "ninpo_seal": True,
        "seal_type": "last_used",
        "seal_add": 1
    }
    skills.append(shuriken)

    # 1-2. 쾌속 수리검 (기본 HP)
    shuriken_hp = Skill(
        "ninja_shuriken_hp",
        "쾌속 수리검",
        "급소를 노려 HP 피해를 준다. 마지막 사용 속성의 인(印) +1."
    )
    shuriken_hp.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="physical"),
    ]
    shuriken_hp.costs = []
    shuriken_hp.sfx = ("combat", "attack_physical")
    shuriken_hp.metadata = {
        "basic_attack": True,
        "ninpo_seal": True,
        "seal_type": "last_used",
        "seal_add": 1
    }
    skills.append(shuriken_hp)

    # ── 속성 인술 (4개) ──────────────────────────────────

    # 2. 화둔 - 호염진
    fire_ninjutsu = Skill(
        "ninja_fire_ninjutsu",
        "화둔 - 호염진",
        "[화속성] 화염 인술로 적을 불태운다. 화(火) 인 +1. 25% 화상."
    )
    fire_ninjutsu.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic", element="fire"),
        DamageEffect(DamageType.HP, 1.2, stat_type="magic"),
        StatusEffect(StatusType.BURN, duration=2, value=0.08, chance=0.25),
    ]
    fire_ninjutsu.costs = [MPCost(2)]
    fire_ninjutsu.sfx = ("combat", "attack_magic")
    fire_ninjutsu.metadata = {
        "ninpo_seal": True,
        "seal_type": "fire",
        "seal_add": 1,
        "element": "fire"
    }
    skills.append(fire_ninjutsu)

    # 3. 수둔 - 빙하진
    ice_ninjutsu = Skill(
        "ninja_ice_ninjutsu",
        "수둔 - 빙하진",
        "[빙속성] 냉기 인술로 적을 얼린다. 빙(氷) 인 +1. 25% 감속."
    )
    ice_ninjutsu.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic", element="ice"),
        DamageEffect(DamageType.HP, 1.2, stat_type="magic"),
        BuffEffect(BuffType.SPEED_DOWN, 0.20, duration=2),
    ]
    ice_ninjutsu.costs = [MPCost(2)]
    ice_ninjutsu.sfx = ("combat", "attack_magic")
    ice_ninjutsu.metadata = {
        "ninpo_seal": True,
        "seal_type": "ice",
        "seal_add": 1,
        "element": "ice"
    }
    skills.append(ice_ninjutsu)

    # 4. 뇌둔 - 자전진
    thunder_ninjutsu = Skill(
        "ninja_thunder_ninjutsu",
        "뇌둔 - 자전진",
        "[뇌속성] 번개 인술로 적을 감전시킨다. 뇌(雷) 인 +1. 25% 감전."
    )
    thunder_ninjutsu.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magic", element="thunder"),
        DamageEffect(DamageType.HP, 1.2, stat_type="magic"),
        StatusEffect(StatusType.SHOCK, duration=2, value=0.05, chance=0.25),
    ]
    thunder_ninjutsu.costs = [MPCost(2)]
    thunder_ninjutsu.sfx = ("combat", "attack_magic")
    thunder_ninjutsu.metadata = {
        "ninpo_seal": True,
        "seal_type": "thunder",
        "seal_add": 1,
        "element": "thunder"
    }
    skills.append(thunder_ninjutsu)

    # 5. 풍둔 - 열풍진
    wind_ninjutsu = Skill(
        "ninja_wind_ninjutsu",
        "풍둔 - 열풍진",
        "[풍속성] 바람 인술로 적을 벤다. 풍(風) 인 +1. 자신 ATB +10%."
    )
    wind_ninjutsu.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="hybrid", element="wind"),
        DamageEffect(DamageType.HP, 1.2, stat_type="hybrid"),
    ]
    wind_ninjutsu.costs = [MPCost(1)]
    wind_ninjutsu.sfx = ("combat", "attack_magic")
    wind_ninjutsu.metadata = {
        "ninpo_seal": True,
        "seal_type": "wind",
        "seal_add": 1,
        "element": "wind",
        "atb_boost": 0.10
    }
    skills.append(wind_ninjutsu)

    # ── 서포트 (3개) ──────────────────────────────────

    # 6. 속성부여 - 인첩
    elemental_edge = Skill(
        "ninja_elemental_edge",
        "속성부여 - 인첩",
        "아군에게 속성의 힘을 부여한다. 공격력 +15% (3턴). 인 +1."
    )
    elemental_edge.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=3),
    ]
    elemental_edge.costs = [MPCost(10)]
    elemental_edge.target_type = "single_ally"
    elemental_edge.sfx = ("skill", "buff")
    elemental_edge.metadata = {
        "buff_skill": True,
        "element_enchant": True,
        "ninpo_seal": True,
        "seal_type": "last_used",
        "seal_add": 1
    }
    skills.append(elemental_edge)

    # 7. 분신술
    shadow_clone = Skill(
        "ninja_shadow_clone",
        "분신술",
        "분신으로 아군 전체 회피 +25% (3턴). 자신 추가 +15%. 풍 인 +1."
    )
    shadow_clone.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.25, duration=3, is_party_wide=True),
        BuffEffect(BuffType.EVASION_UP, 0.15, duration=3, target="self"),
    ]
    shadow_clone.costs = [MPCost(14)]
    shadow_clone.target_type = "all_allies"
    shadow_clone.is_aoe = True
    shadow_clone.sfx = ("skill", "buff")
    shadow_clone.metadata = {
        "buff_skill": True,
        "ninpo_seal": True,
        "seal_type": "wind",
        "seal_add": 1
    }
    skills.append(shadow_clone)

    # 8. 연막탄
    smoke_bomb = Skill(
        "ninja_smoke_bomb",
        "연막탄",
        "적 전체 명중 -30%, 속도 -10% (2턴). 풍 인 +1."
    )
    smoke_bomb.effects = [
        BuffEffect(BuffType.ACCURACY_DOWN, 0.30, duration=2),
        BuffEffect(BuffType.SPEED_DOWN, 0.10, duration=2),
    ]
    smoke_bomb.costs = [MPCost(11)]
    smoke_bomb.target_type = "all_enemies"
    smoke_bomb.is_aoe = True
    smoke_bomb.sfx = ("character", "status_debuff")
    smoke_bomb.metadata = {
        "debuff": True,
        "ninpo_seal": True,
        "seal_type": "wind",
        "seal_add": 1
    }
    skills.append(smoke_bomb)

    # 9. 신속지원
    haste_support = Skill(
        "ninja_haste_support",
        "신속지원",
        "아군 1인 ATB +35%, 속도 +20% (3턴). 풍 인 +1."
    )
    haste_support.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.20, duration=3),
    ]
    haste_support.costs = [MPCost(12)]
    haste_support.target_type = "single_ally"
    haste_support.sfx = ("skill", "haste")
    haste_support.metadata = {
        "buff_skill": True,
        "atb_boost": 0.35,
        "ninpo_seal": True,
        "seal_type": "wind",
        "seal_add": 1
    }
    skills.append(haste_support)

    # ── 인법 연쇄 (2개) ──────────────────────────────────

    # 10. 인법연쇄 - 해인 (인 소비 폭발)
    seal_burst = Skill(
        "ninja_seal_burst",
        "인법연쇄 - 해인",
        "축적한 인(印)을 해방! 2인: 1.8배, 3인: 2.5배 광역, 4인: 3.5배 전속성 광역."
    )
    seal_burst.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 2.0, stat_type="magic"),
    ]
    seal_burst.costs = []
    seal_burst.sfx = ("skill", "limit_break")
    seal_burst.metadata = {
        "ninpo_burst": True,
        "requires_seals": 2,
        "seal_consume_all": True,
        "damage_per_seal": {
            2: {"multiplier": 2.2, "aoe": False},
            3: {"multiplier": 3.0, "aoe": True, "ignore_resist": True},
            4: {"multiplier": 4.0, "aoe": True, "all_elements": True}
        }
    }
    skills.append(seal_burst)

    # 11. 속성연사 (다단 속성 공격)
    elemental_barrage = Skill(
        "ninja_elemental_barrage",
        "속성연사",
        "속성 수리검 4연타! 랜덤 속성 0.5배×4 + HP. 인 최대 2개 축적."
    )
    elemental_barrage.effects = [
        DamageEffect(DamageType.BRV, 0.6, stat_type="hybrid", element="fire"),
        DamageEffect(DamageType.BRV, 0.6, stat_type="hybrid", element="ice"),
        DamageEffect(DamageType.BRV, 0.6, stat_type="hybrid", element="thunder"),
        DamageEffect(DamageType.BRV, 0.6, stat_type="hybrid", element="wind"),
        DamageEffect(DamageType.HP, 2.0, stat_type="hybrid"),
    ]
    elemental_barrage.costs = [MPCost(14)]
    elemental_barrage.sfx = ("combat", "attack_physical")
    elemental_barrage.metadata = {
        "multi_hit": True,
        "hit_count": 4,
        "ninpo_seal": True,
        "seal_type": "random",
        "seal_add": 2
    }
    skills.append(elemental_barrage)

    # ── 궁극기 (1개) ──────────────────────────────────

    # 12. 궁극기: 만화경 인법 - 삼라만상
    ultimate = Skill(
        "ninja_ultimate",
        "만화경 인법 - 삼라만상",
        "[궁극기] 사대 속성 동시 해방! 전속성 4.0배 광역 + 속성 내성 -30% + 아군 ATB +25%."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 4.5, stat_type="magic", element="all"),
        DamageEffect(DamageType.HP, 1.5, stat_type="magic"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.30, duration=3),
        BuffEffect(BuffType.SPEED_UP, 0.25, duration=3, is_party_wide=True),
    ]
    ultimate.costs = [MPCost(40)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aoe": True,
        "all_elements": True,
        "ninpo_seal_fill": 4,
        "ninpo_seal_consume_all": True,
        "element_resist_reduction": 0.30,
        "party_atb_boost": 0.25
    }
    skills.append(ultimate)

    # ── 팀워크 (1개) ──────────────────────────────────

    # 13. 인법결계: 사속호법
    teamwork = TeamworkSkill(
        "ninja_teamwork",
        "인법결계: 사속호법",
        "인(印)을 소모하지 않고 결계를 펼쳐 아군을 강화!\n"
        "화인: 전체 공/마 +20%, 빙인: 전체 방/마방 +20%\n"
        "뇌인: 전체 속도 +20%, 풍인: 전체 ATB +300\n"
        "보호막: 인 수 × 마법력 × 0.25",
        gauge_cost=100
    )
    teamwork.effects = []  # 커스텀 처리 (gimmick_updater에서 인 상태 기반)
    teamwork.target_type = "all_allies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "ninpo_barrier": True,
        "buff_duration": 3,
        "shield_magic_coeff": 0.25,
    }
    skills.append(teamwork)

    return skills


def register_ninja_skills(skill_manager):
    """닌자 스킬 등록"""
    skills = create_ninja_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    logger.info(f"닌자 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
