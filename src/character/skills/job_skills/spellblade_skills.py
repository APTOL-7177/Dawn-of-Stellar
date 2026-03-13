"""Spellblade Skills - 블레이드 서킷 루프 리메이크"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("spellblade_skills")


def create_spellblade_skills():
    """마검사 스킬 생성 (블레이드 서킷 루프)"""

    skills = []

    # 1. Arc Slash — 기본 BRV (Steel Line 충전)
    arc_slash = Skill(
        "spellblade_arc_slash",
        "아크 슬래시",
        "빠른 검격으로 Steel Line을 충전하고 서킷을 시작한다."
    )
    arc_slash.effects = [
        DamageEffect(DamageType.BRV, 1.55, stat_type="physical")
    ]
    arc_slash.costs = []
    arc_slash.sfx = ("skill", "slash")
    arc_slash.metadata = {
        "basic_attack": True,
        "circuit_channel": "steel",
        "circuit_charge": 14,
        "lock_turns": 1,
        "resonance_step": True,
        "arc_spark_bonus": 0.55
    }
    skills.append(arc_slash)

    # 2. Mana Pierce — 기본 HP (Mana Line 충전, 마법 관통)
    mana_pierce = Skill(
        "spellblade_mana_pierce",
        "마나 피어스",
        "[번개 속성] 마력을 실은 찌르기로 Mana Line을 채우고 HP 피해를 준다."
    )
    mana_pierce.effects = [
        DamageEffect(DamageType.HP, 0.81, stat_type="magical", element="lightning",
                     conditional_bonus={"condition": "stealth", "multiplier": 1.2})
    ]
    mana_pierce.costs = []
    mana_pierce.sfx = ("skill", "elemental")
    mana_pierce.metadata = {
        "basic_attack": True,
        "circuit_channel": "mana",
        "circuit_charge": 14,
        "lock_turns": 1,
        "resonance_step": True,
        "arc_spark_bonus": 0.55
    }
    skills.append(mana_pierce)

    # 3. Flux Step — 회피/전환 보조
    flux_step = Skill(
        "spellblade_flux_step",
        "플럭스 스텝",
        "다음 스킬을 반대 채널로 자동 변환하고 이동/회피를 강화한다."
    )
    flux_step.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.25, duration=2, target="self"),
        BuffEffect(BuffType.EVASION_UP, 0.25, duration=2, target="self"),
        GimmickEffect(GimmickOperation.SET, "circuit_flux_ready", 1)
    ]
    flux_step.costs = [MPCost(6)]
    flux_step.target_type = "self"
    flux_step.sfx = ("skill", "haste")
    flux_step.metadata = {
        "circuit_flux": True,
        "lock_turns": 0
    }
    skills.append(flux_step)

    # 4. Circuit Brand — 표식 디버프, 시그넷 가속
    circuit_brand = Skill(
        "spellblade_circuit_brand",
        "서킷 브랜드",
        "대상에 회로 분쇄 표식을 남겨 양 채널 피해를 증폭하고 시그넷을 준비한다."
    )
    circuit_brand.effects = [
        DamageEffect(DamageType.BRV, 1.1, stat_type="physical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.18, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, 0.18, duration=3),
        StatusEffect(StatusType.SILENCE, duration=1, value=1.0, chance=0.4),
        GimmickEffect(GimmickOperation.SET, "circuit_brand", 1, apply_to_target=True)
    ]
    circuit_brand.costs = [MPCost(8)]
    circuit_brand.sfx = ("skill", "magic_cast")
    circuit_brand.metadata = {
        "circuit_channel": "steel",
        "circuit_charge": 10,
        "lock_turns": 1,
        "brand_skill": True
    }
    skills.append(circuit_brand)

    # 5. Mirror Edge: Overload — 시그넷 소비 하이브리드
    mirror_edge = Skill(
        "spellblade_mirror_edge_overload",
        "미러 엣지: 오버로드",
        "[화염 속성] Resonance Sigil을 소모해 물리/마법 동시 폭발과 방깎을 적용한다."
    )
    mirror_edge.effects = [
        DamageEffect(DamageType.BRV_HP, 1.9, stat_type="physical"),
        DamageEffect(DamageType.BRV_HP, 0.94, stat_type="magical", element="fire"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.12, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, 0.12, duration=3)
    ]
    mirror_edge.costs = [MPCost(12)]
    mirror_edge.sfx = ("skill", "flare")
    mirror_edge.metadata = {
        "circuit_channel": "hybrid",
        "circuit_charge": 10,
        "lock_turns": 1,
        "resonance_step": False,
        "consumes_sigils": True,
        "max_sigils": 3,
        "sigil_damage_bonus": 0.35,
        "def_shred_per_sigil": 0.08,
        "grant_party_buff": 0.08
    }
    skills.append(mirror_edge)

    # 6. Duality Collapse — 궁극기, 두 채널 동시 방전
    ultimate = Skill(
        "spellblade_duality_collapse",
        "이중 붕괴",
        "[번개 속성] 두 채널을 동시에 방전해 광역 하이브리드 폭발을 일으킨다."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.2, stat_type="physical"),
        DamageEffect(DamageType.HP, 1.82, stat_type="magical", element="lightning"),
        StatusEffect(StatusType.STUN, duration=1, value=1.0, chance=0.35),
        GimmickEffect(GimmickOperation.SET, "steel_line", 0),
        GimmickEffect(GimmickOperation.SET, "mana_line", 0)
    ]
    ultimate.costs = [MPCost(24)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "circuit_channel": "hybrid",
        "lock_turns": 0,
        "grant_sigils": 3,
        "reset_circuit": True
    }
    skills.append(ultimate)

    # 팀워크: Mirror Sync
    teamwork = TeamworkSkill(
        "spellblade_teamwork",
        "미러 싱크",
        "파티에 Blade Circuit 버프를 부여하고 즉시 Arc Spark를 발동한다.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="physical"),
        DamageEffect(DamageType.HP, 0.91, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_UP, 0.22, duration=3, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.22, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "resonance_sigil", 3)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "circuit_channel": "hybrid",
        "arc_spark_bonus": 0.6
    }
    skills.append(teamwork)

    # 7. 스틸 리플 — 광역 BRV, Steel 충전
    steel_ripple = Skill(
        "spellblade_steel_ripple",
        "스틸 리플",
        "회전 베기로 주변을 쓸어 Steel Line을 채운다."
    )
    steel_ripple.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="physical"),
    ]
    steel_ripple.target_type = "all_enemies"
    steel_ripple.is_aoe = True
    steel_ripple.costs = [MPCost(8)]
    steel_ripple.sfx = ("skill", "slash2")
    steel_ripple.metadata = {
        "aoe": True,
        "circuit_channel": "steel",
        "circuit_charge": 16,
        "lock_turns": 1,
        "resonance_step": True
    }
    skills.append(steel_ripple)

    # 8. 위상 단절 — 단일 고위력, Mana 라인 특화
    phase_sever = Skill(
        "spellblade_phase_sever",
        "위상 단절",
        "[빙결 속성] 마나 블레이드를 찔러 차단선을 그어 큰 피해를 준다."
    )
    phase_sever.effects = [
        DamageEffect(DamageType.BRV_HP, 1.43, stat_type="magical", element="ice",
                     conditional_bonus={"condition": "stealth", "multiplier": 1.2})
    ]
    phase_sever.costs = [MPCost(10)]
    phase_sever.sfx = ("skill", "magic_cast")
    phase_sever.metadata = {
        "circuit_channel": "mana",
        "circuit_charge": 18,
        "lock_turns": 1,
        "resonance_step": True,
        "arc_spark_bonus": 0.7
    }
    skills.append(phase_sever)

    # 9. 듀얼 레조넌스 — 파티 버프/시그넷 생성
    dual_resonance = Skill(
        "spellblade_dual_resonance",
        "듀얼 레조넌스",
        "두 채널을 공진시켜 파티에 물리/마법 버프와 시그넷을 부여한다."
    )
    dual_resonance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.18, duration=3, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.18, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "resonance_sigil", 1, max_value=3)
    ]
    dual_resonance.costs = [MPCost(10)]
    dual_resonance.target_type = "party"
    dual_resonance.is_aoe = True
    dual_resonance.sfx = ("skill", "cast_complete")
    dual_resonance.metadata = {
        "circuit_channel": "hybrid",
        "lock_turns": 0
    }
    skills.append(dual_resonance)

    # 10. 아크 다이브 — 돌진/하이브리드 일격
    arc_dive = Skill(
        "spellblade_arc_dive",
        "아크 다이브",
        "돌진하며 검과 마력을 함께 주입해 강력한 일격을 꽂는다."
    )
    arc_dive.effects = [
        DamageEffect(DamageType.BRV, 1.7, stat_type="physical"),
        DamageEffect(DamageType.HP, 0.85, stat_type="magical")
    ]
    arc_dive.costs = [MPCost(11)]
    arc_dive.sfx = ("combat", "sword4")
    arc_dive.metadata = {
        "circuit_channel": "hybrid",
        "circuit_charge": 12,
        "lock_turns": 1,
        "resonance_step": True
    }
    skills.append(arc_dive)

    # 11. 서킷 시프트 ? 봉인 해제 + 게이지 보정
    circuit_shift = Skill(
        "spellblade_circuit_shift",
        "서킷 시프트",
        "채널 봉인을 해제하고 두 라인을 소폭 충전하며 속도를 높인다."
    )
    circuit_shift.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=2, target="self"),
        GimmickEffect(GimmickOperation.SET, "steel_lock", 0),
        GimmickEffect(GimmickOperation.SET, "mana_lock", 0),
        GimmickEffect(GimmickOperation.ADD, "steel_line", 10, max_value=100),
        GimmickEffect(GimmickOperation.ADD, "mana_line", 10, max_value=100),
        GimmickEffect(GimmickOperation.ADD, "resonance_sigil", 1, max_value=3)
    ]
    circuit_shift.costs = [MPCost(9)]
    circuit_shift.target_type = "self"
    circuit_shift.sfx = ("skill", "switch")
    circuit_shift.metadata = {
        "circuit_channel": "hybrid",
        "circuit_charge": 0,
        "lock_turns": 0
    }
    skills.append(circuit_shift)

    # 12. 스파크 리바운드 ? 역극성 찌르기
    spark_rebound = Skill(
        "spellblade_spark_rebound",
        "스파크 리바운드",
        "[번개 속성] 역극성 마나를 주입해 반발 피해를 주고 시그넷을 끌어당긴다."
    )
    spark_rebound.effects = [
        DamageEffect(DamageType.HP, 1.04, stat_type="magical", element="lightning"),
        GimmickEffect(GimmickOperation.ADD, "resonance_sigil", 1, max_value=3)
    ]
    spark_rebound.costs = [MPCost(9)]
    spark_rebound.sfx = ("skill", "bolt")
    spark_rebound.metadata = {
        "circuit_channel": "mana",
        "circuit_charge": 12,
        "lock_turns": 1,
        "resonance_step": True,
        "arc_spark_bonus": 0.8
    }
    skills.append(spark_rebound)

    # 13. 레조넌트 클리브 ? 시그넷 증폭 일격
    resonant_cleave = Skill(
        "spellblade_resonant_cleave",
        "레조넌트 클리브",
        "시그넷을 태워 공명 일격을 가해 방어를 절단한다."
    )
    resonant_cleave.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.1, duration=2)
    ]
    resonant_cleave.costs = [MPCost(12)]
    resonant_cleave.sfx = ("combat", "damage_high")
    resonant_cleave.metadata = {
        "circuit_channel": "steel",
        "circuit_charge": 15,
        "lock_turns": 1,
        "consumes_sigils": True,
        "max_sigils": 2,
        "sigil_damage_bonus": 0.3,
        "def_shred_per_sigil": 0.05
    }
    skills.append(resonant_cleave)

    # 14. 미러 스톰 ? 하이브리드 소용돌이
    mirror_storm = Skill(
        "spellblade_mirror_storm",
        "미러 스톰",
        "[바람 속성] 검과 마법을 교차 회전시켜 주변을 휩쓴다."
    )
    mirror_storm.effects = [
        DamageEffect(DamageType.BRV, 1.45, stat_type="physical"),
        DamageEffect(DamageType.HP, 0.75, stat_type="magical", element="wind")
    ]
    mirror_storm.target_type = "all_enemies"
    mirror_storm.is_aoe = True
    mirror_storm.costs = [MPCost(12)]
    mirror_storm.sfx = ("skill", "explosion")
    mirror_storm.metadata = {
        "circuit_channel": "hybrid",
        "circuit_charge": 12,
        "lock_turns": 1,
        "resonance_step": True
    }
    skills.append(mirror_storm)

    return skills


def register_spellblade_skills(skill_manager):
    """마검사 스킬 등록"""
    skills = create_spellblade_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    logger.info(f"마검사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
