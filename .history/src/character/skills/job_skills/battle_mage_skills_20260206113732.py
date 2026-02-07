"""Battle Mage Skills - 룬 연쇄 폭발 리메이크"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost


def create_battle_mage_skills():
    """배틀메이지 핵심/확장 스킬 (룬 공명 필드)"""

    skills = []

    # 1. 룬 각인 ? 기본 BRV, 대상에 랜덤 룬 각인
    rune_etch = Skill(
        "battle_mage_rune_etch",
        "룬 각인",
        "BRV 피해와 함께 대상에 랜덤 룬 1개를 각인한다."
    )
    rune_etch.effects = [
        DamageEffect(DamageType.BRV, 1.25, stat_type="hybrid")
    ]
    rune_etch.costs = []
    rune_etch.sfx = ("combat", "attack_physical")
    rune_etch.metadata = {
        "basic_attack": True,
        "carve_random_rune": True,
        "max_rune_slots": 4,
        "rune_trigger": False,
        "resonance_gain": 1
    }
    skills.append(rune_etch)

    # 2. 룬 폭발 ? 기본 HP, 대상 룬 연쇄 폭발
    rune_burst = Skill(
        "battle_mage_rune_burst",
        "룬 폭발",
        "대상에 새겨진 룬을 연쇄 폭발시켜 하이브리드 피해를 준다."
    )
    rune_burst.effects = [
        DamageEffect(DamageType.HP, 0.9, stat_type="hybrid",
                     gimmick_bonus={"field": "total_runes", "multiplier": 0.17})
    ]
    rune_burst.costs = []
    rune_burst.sfx = ("skill", "explosion")
    rune_burst.metadata = {
        "basic_attack": True,
        "detonate_target_runes": True,
        "spread_chance": 0.3,
        "aoe_falloff": [0.7, 0.5],
        "resonance_gain_per_rune": 10
    }
    skills.append(rune_burst)

    # 3. 룬 신호 ? 파티 룬 트리거 부여
    rune_signal = Skill(
        "battle_mage_rune_signal",
        "룬 신호",
        "아군에게 룬 트리거를 부여해 자신의 공격으로 룬을 기폭하게 한다."
    )
    rune_signal.effects = [
        BuffEffect("rune_trigger", 1.0, duration=2, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.15, duration=2, is_party_wide=True)
    ]
    rune_signal.costs = [MPCost(6)]
    rune_signal.target_type = "party"
    rune_signal.sfx = ("skill", "haste")
    rune_signal.metadata = {"support": True, "rune_trigger": True}
    skills.append(rune_signal)

    # 4. 촉매 전환 ? 룬 타입 변환/재배치
    catalyst_swap = Skill(
        "battle_mage_catalyst_swap",
        "촉매 전환",
        "대상에게 새겨진 룬을 다른 속성으로 전환해 연쇄 효과를 바꾼다."
    )
    catalyst_swap.effects = [
        StatusEffect(StatusType.SHOCK, duration=1, value=1.0, chance=0.25),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=2, target="self")
    ]
    catalyst_swap.costs = [MPCost(7)]
    catalyst_swap.sfx = ("skill", "magic_cast")
    catalyst_swap.metadata = {
        "swap_runes": True,
        "swap_count": 2,
        "swap_order": ["fire", "lightning", "ice", "earth", "arcane"]
    }
    skills.append(catalyst_swap)

    # 5. 공명 앵커 ? 연쇄 보증 디버프
    resonance_anchor = Skill(
        "battle_mage_resonance_anchor",
        "공명 앵커",
        "첫 폭발 피해를 증폭시키는 앵커를 대상을 걸어 룬 연쇄를 보증한다."
    )
    resonance_anchor.effects = [
        BuffEffect(BuffType.DEFENSE_DOWN, 0.12, duration=2),
        StatusEffect(StatusType.WEAKNESS, duration=2, value=1.0, chance=0.5),
        GimmickEffect(GimmickOperation.SET, "resonance_anchor", 1, apply_to_target=True)
    ]
    resonance_anchor.costs = [MPCost(8)]
    resonance_anchor.sfx = ("skill", "slow")
    resonance_anchor.metadata = {"anchor_bonus": 0.3}
    skills.append(resonance_anchor)

    # 6. 룬 압축 ? 이중 각인 + 게이지 충전
    rune_compression = Skill(
        "battle_mage_rune_compression",
        "룬 압축",
        "압축된 마력을 새겨 두 개의 룬을 동시에 각인하고 공명 게이지를 채운다."
    )
    rune_compression.effects = [
        DamageEffect(DamageType.BRV, 1.15, stat_type="hybrid"),
        GimmickEffect(GimmickOperation.ADD, "resonance_gauge", 12)
    ]
    rune_compression.costs = [MPCost(5)]
    rune_compression.sfx = ("skill", "elemental")
    rune_compression.metadata = {
        "carve_random_rune": True,
        "carve_count": 2,
        "max_rune_slots": 4
    }
    skills.append(rune_compression)

    # 7. 충격 각인 ? 번개 룬 확정 부여 + 쇼크
    shock_imprint = Skill(
        "battle_mage_shock_imprint",
        "충격 각인",
        "[전기 속성] 번개 룬을 강제로 각인하고 쇼크를 남긴다."
    )
    shock_imprint.effects = [
        DamageEffect(DamageType.BRV_HP, 1.2, stat_type="hybrid", element="lightning"),
        StatusEffect(StatusType.SHOCK, duration=1, value=1.0, chance=0.5)
    ]
    shock_imprint.costs = [MPCost(7)]
    shock_imprint.sfx = ("skill", "lightning")
    shock_imprint.metadata = {
        "element": "lightning",
        "carve_rune_type": "lightning",
        "carve_count": 1,
        "resonance_gain_per_rune": 8
    }
    skills.append(shock_imprint)

    # 8. 공명 펄스 ? 게이지를 일부 소모해 룬 폭발 강화
    resonance_pulse = Skill(
        "battle_mage_resonance_pulse",
        "공명 펄스",
        "축적된 공명 게이지를 방출해 룬 폭발을 확산시키고 추가 피해를 준다."
    )
    resonance_pulse.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="hybrid"),
        GimmickEffect(GimmickOperation.ADD, "resonance_gauge", 18)
    ]
    resonance_pulse.target_type = "all_enemies"
    resonance_pulse.is_aoe = True
    resonance_pulse.costs = [MPCost(9)]
    resonance_pulse.sfx = ("skill", "bolt2")
    resonance_pulse.metadata = {
        "carve_random_rune": True,
        "carve_all_targets": True,
        "carve_count": 2,
        "max_rune_slots": 4,
        "detonate_all_runes": True,
        "spread_chance": 0.45,
        "aoe_falloff": [0.75, 0.55],
        "resonance_gain_per_rune": 12,
        "resonance_pulse_consume": True
    }
    skills.append(resonance_pulse)

    # 9. 룬 융합 ? 전장에 비전 룬 각인 + 하이브리드 광역
    rune_fusion = Skill(
        "battle_mage_rune_fusion",
        "룬 융합",
        "모든 적에게 비전 룬을 각인시키며 파동을 일으켜 광역 피해를 준다."
    )
    rune_fusion.effects = [
        DamageEffect(DamageType.BRV, 1.1, stat_type="hybrid")
    ]
    rune_fusion.target_type = "all_enemies"
    rune_fusion.is_aoe = True
    rune_fusion.costs = [MPCost(9)]
    rune_fusion.sfx = ("skill", "magic_cast")
    rune_fusion.metadata = {
        "carve_rune_type": "arcane",
        "carve_all_targets": True,
        "carve_count": 1,
        "max_rune_slots": 4
    }
    skills.append(rune_fusion)

    # 10. 연쇄 낙뢰 ? 번개 룬 폭발 특화
    chain_thunder = Skill(
        "battle_mage_chain_thunder",
        "연쇄 낙뢰",
        "[전기 속성] 번개 룬을 기폭시켜 연쇄 전격을 퍼뜨린다."
    )
    chain_thunder.effects = [
        DamageEffect(DamageType.HP, 1.25, stat_type="hybrid", element="lightning",
                     gimmick_bonus={"field": "total_runes", "multiplier": 0.2}),
        StatusEffect(StatusType.SHOCK, duration=1, value=1.0, chance=0.45)
    ]
    chain_thunder.costs = [MPCost(11)]
    chain_thunder.sfx = ("skill", "bolt3")
    chain_thunder.metadata = {
        "element": "lightning",
        "detonate_target_runes": True,
        "spread_chance": 0.5,
        "aoe_falloff": [0.8, 0.6],
        "resonance_gain_per_rune": 12
    }
    skills.append(chain_thunder)

    # 11. 룬 방벽 ? 대지 룬 각인 + 파티 방어 버프
    rune_barrier = Skill(
        "battle_mage_rune_barrier",
        "룬 방벽",
        "대지 룬을 새겨 적을 묶고 파티에 방어 장벽을 부여한다."
    )
    rune_barrier.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="hybrid"),
        BuffEffect(BuffType.DEFENSE_UP, 0.15, duration=2, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.15, duration=2, is_party_wide=True)
    ]
    rune_barrier.costs = [MPCost(8)]
    rune_barrier.sfx = ("skill", "earth")
    rune_barrier.metadata = {
        "carve_rune_type": "earth",
        "carve_count": 1,
        "resonance_gain_per_rune": 8
    }
    skills.append(rune_barrier)

    # 12. 비전 파동 ? 공명 게이지 충전형 광역 타격
    arcane_wave = Skill(
        "battle_mage_arcane_wave",
        "비전 파동",
        "비전 에너지를 방출해 광역 BRV·HP 피해를 주고 공명 게이지를 채운다. 전장에 새겨진 룬을 함께 폭발시킨다."
    )
    arcane_wave.effects = [
        DamageEffect(DamageType.BRV_HP, 1.2, stat_type="hybrid"),
        GimmickEffect(GimmickOperation.ADD, "resonance_gauge", 14)
    ]
    arcane_wave.target_type = "all_enemies"
    arcane_wave.is_aoe = True
    arcane_wave.costs = [MPCost(10)]
    arcane_wave.sfx = ("skill", "elemental")
    arcane_wave.metadata = {
        "detonate_all_runes": True,
        "resonance_gain_per_rune": 8
    }
    skills.append(arcane_wave)

    # 13. 룬 폭풍 ? 전장에 랜덤 룬 2개씩 부여하는 강력한 광역
    rune_storm = Skill(
        "battle_mage_rune_storm",
        "룬 폭풍",
        "모든 적에게 무작위 룬 2개를 새기고 공명 게이지를 크게 채운다."
    )
    rune_storm.effects = [
        DamageEffect(DamageType.BRV, 1.15, stat_type="hybrid"),
        GimmickEffect(GimmickOperation.ADD, "resonance_gauge", 16)
    ]
    rune_storm.target_type = "all_enemies"
    rune_storm.is_aoe = True
    rune_storm.costs = [MPCost(12)]
    rune_storm.sfx = ("skill", "flare")
    rune_storm.metadata = {
        "carve_random_rune": True,
        "carve_all_targets": True,
        "carve_count": 2,
        "max_rune_slots": 4,
        "resonance_gain_per_rune": 10
    }
    skills.append(rune_storm)

    # 14. 그랜드 레조넌스 ? 궁극기, 전장 룬 동시 폭발
    ultimate = Skill(
        "battle_mage_grand_resonance",
        "그랜드 레조넌스",
        "전장 모든 룬을 강제로 폭발시켜 광역 피해와 팀 MP 회복을 제공한다."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="hybrid",
                     gimmick_bonus={"field": "total_runes", "multiplier": 0.2}),
        BuffEffect(BuffType.MP_REGEN, 8, duration=2, is_party_wide=True),
        BuffEffect(BuffType.ATTACK_UP, 0.18, duration=2, is_party_wide=True)
    ]
    ultimate.costs = [MPCost(16)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "detonate_all_runes": True,
        "resonance_gain_per_rune": 10
    }
    skills.append(ultimate)

    return skills


def register_battle_mage_skills(skill_manager):
    """배틀메이지 스킬 등록"""
    skills = create_battle_mage_skills()

    teamwork = TeamworkSkill(
        "battle_mage_teamwork",
        "룬 오케스트라",
        "파티에 룬 트리거를 배포하고 즉시 룬을 1회 기폭시킨다.",
        gauge_cost=150
    )
    teamwork.effects = [
        BuffEffect("rune_trigger", 1.0, duration=2, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.18, duration=2, is_party_wide=True),
        BuffEffect(BuffType.SPEED_UP, 0.12, duration=2, is_party_wide=True)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "rune_trigger": True, "detonate_one": True}
    skills.append(teamwork)

    for skill in skills:
        skill_manager.register_skill(skill)

    return [s.skill_id for s in skills]
