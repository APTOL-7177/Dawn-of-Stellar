"""Rogue Skills - 도적 (맹독 & 속도 시스템)

치명적인 독과 압도적인 속도로 적을 서서히 무력화하는 암살자.
독 중첩으로 적을 약화시키고, 최고의 속도로 전장을 지배한다.

"독은 느리지만, 확실하지."
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost
from src.core.logger import get_logger

logger = get_logger("rogue_skills")


def create_rogue_skills():
    """도적 스킬 생성 (맹독 & 속도 시스템)"""

    skills = []

    # ── 기본기 (2개) ──────────────────────────────────

    # 1. 독침 (기본 BRV + 독 중첩)
    venom_stab = Skill(
        "rogue_venom_stab",
        "독침",
        "독 묻은 단검으로 찌른다. 독 중첩 +1."
    )
    venom_stab.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 1, max_value=5, apply_to_target=True)
    ]
    venom_stab.costs = []
    venom_stab.sfx = ("combat", "attack_physical")
    venom_stab.metadata = {
        "basic_attack": True,
        "venom": True,
        "venom_add": 1
    }
    skills.append(venom_stab)

    # 2. 급소 찌르기 (기본 HP, 속도 비례 보너스)
    vital_strike = Skill(
        "rogue_vital_strike",
        "급소 찌르기",
        "급소를 노린 HP 공격. 속도 차이에 비례해 피해 증가."
    )
    vital_strike.effects = [
        DamageEffect(DamageType.HP, 1.6, stat_type="physical"),
    ]
    vital_strike.costs = []
    vital_strike.sfx = ("combat", "critical")
    vital_strike.metadata = {
        "basic_attack": True,
        "speed_scaling": True,
        "speed_bonus_max": 0.50
    }
    skills.append(vital_strike)

    # ── 독 계열 (3개) ──────────────────────────────────

    # 3. 맹독 도포 (강력한 단일 독)
    deadly_venom = Skill(
        "rogue_deadly_venom",
        "맹독 도포",
        "[암흑 속성] 치명적인 독을 주입한다. 독 중첩 +2."
    )
    deadly_venom.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical", element="dark"),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 2, max_value=5, apply_to_target=True),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                     damage_stat="physical", damage_multiplier=0.10),
    ]
    deadly_venom.costs = [MPCost(6)]
    deadly_venom.sfx = ("character", "status_debuff")
    deadly_venom.metadata = {
        "venom": True,
        "venom_add": 2,
        "poison": True
    }
    skills.append(deadly_venom)

    # 4. 독안개 (AoE 독 살포)
    poison_mist = Skill(
        "rogue_poison_mist",
        "독안개",
        "[암흑 속성] 독 안개를 뿌려 전체 적에게 독을 퍼뜨린다. 독 중첩 +1."
    )
    poison_mist.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="physical", element="dark"),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 1, max_value=5, apply_to_target=True),
        BuffEffect(BuffType.SPEED_DOWN, 0.15, duration=2),
    ]
    poison_mist.target_type = "all_enemies"
    poison_mist.is_aoe = True
    poison_mist.costs = [MPCost(8)]
    poison_mist.sfx = ("character", "status_debuff")
    poison_mist.metadata = {
        "venom": True,
        "venom_add": 1,
        "aoe": True,
        "slow": True
    }
    skills.append(poison_mist)

    # 5. 독 폭발 (독 중첩 소모 → 폭발 피해)
    venom_burst = Skill(
        "rogue_venom_burst",
        "독 폭발",
        "[암흑 속성] 축적된 독을 폭발시킨다! 독 중첩 수×1.5배 피해. 중첩 전부 소모."
    )
    venom_burst.effects = [
        DamageEffect(DamageType.HP, 1.5, stat_type="physical", element="dark"),
        GimmickEffect(GimmickOperation.SET, "venom_stacks", 0, apply_to_target=True),
    ]
    venom_burst.costs = [MPCost(10)]
    venom_burst.sfx = ("combat", "damage_high")
    venom_burst.metadata = {
        "venom_burst": True,
        "venom_consume_all": True,
        "damage_per_stack": 1.5
    }
    skills.append(venom_burst)

    # ── 속도/유틸리티 (4개) ──────────────────────────────

    # 6. 연막탄 (회피 + 속도 버프)
    smoke = Skill(
        "rogue_smoke",
        "연막탄",
        "연막으로 은신. 회피 +50%, 속도 +30% (3턴)."
    )
    smoke.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=3, target="self"),
        BuffEffect(BuffType.SPEED_UP, 0.30, duration=3, target="self"),
    ]
    smoke.costs = [MPCost(5)]
    smoke.target_type = "self"
    smoke.sfx = ("skill", "haste")
    smoke.metadata = {
        "stealth": True,
        "evasion_mode": True,
        "buff_skill": True
    }
    skills.append(smoke)

    # 7. 신속 (ATB 부스트 + 크리 버프)
    swift_step = Skill(
        "rogue_swift_step",
        "신속",
        "순간 가속! ATB +40%, 다음 공격 크리 +30%."
    )
    swift_step.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.40, duration=1, target="self"),
        BuffEffect(BuffType.CRITICAL_UP, 0.30, duration=2, target="self"),
    ]
    swift_step.costs = [MPCost(4)]
    swift_step.target_type = "self"
    swift_step.sfx = ("skill", "haste")
    swift_step.metadata = {
        "atb_boost": 0.40,
        "speed_skill": True
    }
    skills.append(swift_step)

    # 8. 훔치기 (아이템 획득 + 독)
    steal = Skill(
        "rogue_steal",
        "훔치기",
        "적에게서 아이템을 훔친다! 훔친 아이템 +1, 독 중첩 +1."
    )
    steal.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 1, max_value=5, apply_to_target=True),
    ]
    steal.costs = [MPCost(4)]
    steal.sfx = ("item", "get_item")
    steal.metadata = {
        "steal": True,
        "item_gain": 1,
        "steal_chance": 0.7,
        "venom": True,
        "venom_add": 1
    }
    skills.append(steal)

    # 9. 아이템 사용 (훔친 아이템 소비)
    use_item = Skill(
        "rogue_use_item",
        "아이템 사용",
        "훔친 아이템 사용. HP 25% 회복 + 공격 +20% (3턴). (훔친 아이템 -1)"
    )
    use_item.effects = [
        HealEffect(HealType.HP, percentage=0.25),
        BuffEffect(BuffType.ATTACK_UP, 0.20, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "stolen_items", 1)
    ]
    use_item.costs = [StackCost("stolen_items", 1)]
    use_item.target_type = "self"
    use_item.sfx = ("item", "use_item")
    use_item.metadata = {
        "item_cost": 1,
        "random_effect": True
    }
    skills.append(use_item)

    # ── 디버프/제어 (2개) ──────────────────────────────

    # 10. 약점 노출 (방어 디버프 + 표식)
    expose = Skill(
        "rogue_expose",
        "약점 노출",
        "적의 약점을 간파한다. 방어 -25% (3턴) + 독 중첩 +1."
    )
    expose.effects = [
        BuffEffect(BuffType.DEFENSE_DOWN, 0.25, duration=3),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 1, max_value=5, apply_to_target=True),
        StatusEffect(StatusType.MARK, duration=3, value=1.0),
    ]
    expose.costs = [MPCost(6)]
    expose.sfx = ("character", "status_debuff")
    expose.metadata = {
        "debuff": True,
        "mark": True,
        "venom": True,
        "venom_add": 1,
        "party_damage_bonus": 0.10
    }
    skills.append(expose)

    # 11. 족쇄 (속도 디버프 + 독)
    hamstring = Skill(
        "rogue_hamstring",
        "족쇄",
        "다리를 노려 속도를 크게 떨어뜨린다. 속도 -30% (3턴) + 독 중첩 +1."
    )
    hamstring.effects = [
        DamageEffect(DamageType.BRV, 1.3, stat_type="physical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.30, duration=3),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 1, max_value=5, apply_to_target=True),
    ]
    hamstring.costs = [MPCost(5)]
    hamstring.sfx = ("combat", "attack_physical")
    hamstring.metadata = {
        "slow": True,
        "venom": True,
        "venom_add": 1
    }
    skills.append(hamstring)

    # ── 마무리 (2개) ──────────────────────────────────

    # 12. 암살 (처형기)
    assassinate = Skill(
        "rogue_assassinate",
        "암살",
        "치명적 일격! 독 5중첩 시 즉사 15% + 필중."
    )
    assassinate.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 2.5, stat_type="physical"),
    ]
    assassinate.costs = [MPCost(12)]
    assassinate.sfx = ("combat", "damage_high")
    assassinate.metadata = {
        "execute": True,
        "venom_execute": True,
        "instant_kill_threshold_stacks": 5,
        "instant_kill_chance": 0.15,
        "guaranteed_hit_on_max_venom": True
    }
    skills.append(assassinate)

    # 13. 궁극기: 사신의 독무
    ultimate = Skill(
        "rogue_ultimate",
        "사신의 독무",
        "[암흑 속성] 독의 춤! 전체 피해 + 전체 독 +3 + 속도 대폭 증가."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical", element="dark"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical", element="dark"),
        DamageEffect(DamageType.HP, 3.0, stat_type="physical", element="dark"),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 3, max_value=5, apply_to_target=True),
        BuffEffect(BuffType.SPEED_UP, 0.40, duration=4, target="self"),
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=4, target="self"),
        BuffEffect(BuffType.CRITICAL_UP, 0.40, duration=4, target="self"),
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aoe": True,
        "venom": True,
        "venom_add": 3
    }
    skills.append(ultimate)

    # ── 팀워크 (1개) ──────────────────────────────────

    # 14. 대약탈
    teamwork = TeamworkSkill(
        "rogue_teamwork",
        "대약탈",
        "대규모 약탈! 전체 피해 + 훔친 아이템 +5 + 전체 독 +2.",
        gauge_cost=150
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10),
        GimmickEffect(GimmickOperation.ADD, "venom_stacks", 2, max_value=5, apply_to_target=True),
        BuffEffect(BuffType.SPEED_UP, 0.25, duration=3, is_party_wide=True),
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "item_gain": 5,
        "venom": True,
        "venom_add": 2
    }
    skills.append(teamwork)

    return skills


def register_rogue_skills(skill_manager):
    """도적 스킬 등록"""
    skills = create_rogue_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    logger.info(f"도적 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
