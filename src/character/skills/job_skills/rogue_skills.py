"""Rogue Skills - 도적 (절도 & 회피 시스템)

적에게서 아이템을 훔쳐라!
회피로 생존, 암살로 마무리

"정정당당? 그건 바보들이나 하는 거지"
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
    """도적 스킬 생성 (절도 & 회피 시스템)"""
    
    skills = []
    
    # 1. 기습 (기본 BRV + 크리티컬)
    ambush = Skill(
        "rogue_ambush",
        "기습",
        "빠른 기습 공격. 크리티컬 확률 UP."
    )
    ambush.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="physical"),
        BuffEffect(BuffType.CRITICAL_UP, 0.15, duration=2, target="self")
    ]
    ambush.costs = []
    ambush.sfx = ("combat", "attack_physical")
    ambush.metadata = {
        "basic_attack": True,
        "crit_boost": True
    }
    skills.append(ambush)
    
    # 2. 급소 찌르기 (기본 HP)
    vital_strike = Skill(
        "rogue_vital_strike",
        "급소 찌르기",
        "급소를 노린 HP 공격."
    )
    vital_strike.effects = [
        DamageEffect(DamageType.HP, 1.8, stat_type="physical"),
    ]
    vital_strike.costs = []
    vital_strike.sfx = ("combat", "critical")
    vital_strike.metadata = {
        "basic_attack": True,
        "critical_bonus": 0.3
    }
    skills.append(vital_strike)
    
    # 3. 훔치기 (아이템 획득)
    steal = Skill(
        "rogue_steal",
        "훔치기",
        "적에게서 아이템 훔치기! 훔친 아이템 +1."
    )
    steal.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    steal.costs = [MPCost(4)]
    steal.sfx = ("item", "get_item")
    steal.metadata = {
        "steal": True,
        "item_gain": 1,
        "steal_chance": 0.7
    }
    skills.append(steal)
    
    # 4. 연막탄 (회피 모드)
    smoke = Skill(
        "rogue_smoke",
        "연막탄",
        "연막으로 은신. 회피 +50%, 속도 +30% (3턴)."
    )
    smoke.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=3, target="self"),
        BuffEffect(BuffType.SPEED_UP, 0.30, duration=3, target="self"),
    ]
    smoke.costs = [MPCost(6)]
    smoke.target_type = "self"
    smoke.sfx = ("skill", "haste")
    smoke.metadata = {
        "stealth": True,
        "evasion_mode": True
    }
    skills.append(smoke)
    
    # 5. 훔친 아이템 사용
    use_item = Skill(
        "rogue_use_item",
        "아이템 사용",
        "훔친 아이템 사용. HP 25% 회복 또는 버프. (훔친 아이템 -1)"
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
    
    # 6. 독 바르기 (DoT 공격)
    poison = Skill(
        "rogue_poison",
        "독 바르기",
        "무기에 독을 바른다. 4턴 독 피해."
    )
    poison.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0,
                    damage_stat="physical", damage_multiplier=0.10),
    ]
    poison.costs = [MPCost(7)]
    poison.sfx = ("character", "status_debuff")
    poison.metadata = {
        "poison": True,
        "dot": "물공 10%/턴"
    }
    skills.append(poison)
    
    # 7. 보물 탐지 (대량 아이템 획득)
    treasure = Skill(
        "rogue_treasure",
        "보물 탐지",
        "보물을 찾아낸다! 훔친 아이템 +3."
    )
    treasure.effects = [
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 3, max_value=10),
        BuffEffect(BuffType.LUCK, 0.20, duration=3)
    ]
    treasure.costs = [MPCost(5)]
    treasure.target_type = "self"
    treasure.sfx = ("item", "get_item")
    treasure.metadata = {
        "item_gain": 3,
        "luck_boost": True
    }
    skills.append(treasure)
    
    # 8. 백스탭 (후방 공격)
    backstab = Skill(
        "rogue_backstab",
        "백스탭",
        "치명적인 후방 공격. 크리 +40% (이번 공격)."
    )
    backstab.effects = [
        DamageEffect(DamageType.BRV_HP, 2.4, stat_type="physical"),
        BuffEffect(BuffType.CRITICAL_UP, 0.40, duration=1, target="self"),
    ]
    backstab.costs = [MPCost(9)]
    backstab.sfx = ("combat", "critical")
    backstab.metadata = {
        "backstab": True,
        "crit_bonus": 0.40
    }
    skills.append(backstab)
    
    # 9. 암살 (처형기)
    assassinate = Skill(
        "rogue_assassinate",
        "암살",
        "암살 시도! HP 30% 이하 적 즉사 15% 확률."
    )
    assassinate.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 2.5, stat_type="physical"),
    ]
    assassinate.costs = [MPCost(12)]
    assassinate.sfx = ("combat", "damage_high")
    assassinate.metadata = {
        "execute": True,
        "instant_kill_threshold": 0.30,
        "instant_kill_chance": 0.15
    }
    skills.append(assassinate)
    
    # 10. 궁극기: 그림자 습격
    ultimate = Skill(
        "rogue_ultimate",
        "그림자 습격",
        "그림자에서 습격! 전체 피해 + 모든 아이템 효과 + 은신."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical"),
        DamageEffect(DamageType.HP, 3.2, stat_type="physical"),
        BuffEffect(BuffType.EVASION_UP, 0.60, duration=4, target="self"),
        BuffEffect(BuffType.CRITICAL_UP, 0.50, duration=4, target="self"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10)
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
        "stealth_after": True
    }
    skills.append(ultimate)
    
    # 팀워크: 대약탈
    teamwork = TeamworkSkill(
        "rogue_teamwork",
        "대약탈",
        "대규모 약탈! 전체 피해 + 훔친 아이템 +5 + 회피 버프.",
        gauge_cost=150
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10),
        BuffEffect(BuffType.EVASION_UP, 0.30, duration=3)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "item_gain": 5
    }
    skills.append(teamwork)

    # ============================================================
    # 라틴어 스킬 세트 (YAML과 매칭) - 기본/핵심/강화/궁극기 구성
    # ============================================================

    # 기본 BRV: Umbra Ictus
    umbra_ictus = Skill(
        "rogue_umbra_ictus",
        "Umbra Ictus",
        "어둠 속에서 찌르는 기본 BRV 공격."
    )
    umbra_ictus.effects = [DamageEffect(DamageType.BRV, 1.2, stat_type="physical")]
    umbra_ictus.costs = []
    umbra_ictus.sfx = ("combat", "attack_physical")
    umbra_ictus.metadata = {"basic_attack": True, "shadow": True}
    skills.append(umbra_ictus)

    # 기본 HP: Nox Cadens
    nox_cadens = Skill(
        "rogue_nox_cadens",
        "Nox Cadens",
        "밤하늘을 가르는 HP 일격. 치명타에 특화된 기본기."
    )
    nox_cadens.effects = [DamageEffect(DamageType.HP, 1.1, stat_type="physical")]
    nox_cadens.costs = []
    nox_cadens.sfx = ("combat", "critical")
    nox_cadens.metadata = {"basic_attack": True, "critical_bonus": 0.25}
    skills.append(nox_cadens)

    # 기민 찌르기: Celer Punctio
    celer_punctio = Skill(
        "celer_punctio",
        "Celer Punctio",
        "순간 가속 후 찌르기. 속도와 회피를 끌어올린다."
    )
    celer_punctio.effects = [
        DamageEffect(DamageType.BRV, 1.05, stat_type="physical"),
        BuffEffect(BuffType.SPEED_UP, 0.15, duration=2, target="self"),
        BuffEffect(BuffType.EVASION_UP, 0.10, duration=2, target="self"),
    ]
    celer_punctio.costs = [MPCost(3)]
    celer_punctio.sfx = ("skill", "haste")
    skills.append(celer_punctio)

    # 장난/혼란: Ludibrium
    ludibrium = Skill(
        "ludibrium",
        "Ludibrium",
        "교란을 일으켜 적을 혼란시킨다."
    )
    ludibrium.effects = [
        DamageEffect(DamageType.BRV, 0.9, stat_type="physical"),
        StatusEffect(StatusType.CONFUSION, duration=2, value=1.0, chance=0.35)
    ]
    ludibrium.costs = [MPCost(4)]
    ludibrium.sfx = ("character", "status_debuff")
    skills.append(ludibrium)

    # 연막: Fumus Velum
    fumus_velum = Skill(
        "fumus_velum",
        "Fumus Velum",
        "연막으로 몸을 숨기고 회피를 높인다."
    )
    fumus_velum.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.40, duration=3, target="self"),
        BuffEffect(BuffType.SPEED_UP, 0.20, duration=3, target="self"),
    ]
    fumus_velum.costs = [MPCost(6)]
    fumus_velum.target_type = "self"
    fumus_velum.sfx = ("skill", "haste")
    skills.append(fumus_velum)

    # 등 뒤 상처: Dorsum Vulnus
    dorsum_vulnus = Skill(
        "dorsum_vulnus",
        "Dorsum Vulnus",
        "후방을 노린 치명 일격. 독 극대화."
    )
    dorsum_vulnus.effects = [
        DamageEffect(DamageType.BRV_HP, 1.45, stat_type="physical"),
        BuffEffect(BuffType.CRITICAL_UP, 0.30, duration=2, target="self"),
    ]
    dorsum_vulnus.costs = [MPCost(8)]
    dorsum_vulnus.sfx = ("combat", "critical")
    skills.append(dorsum_vulnus)

    # 절도: Furtum
    furtum = Skill(
        "furtum",
        "Furtum",
        "재빠르게 훔쳐낸다. 훔친 아이템 +1."
    )
    furtum.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    furtum.costs = [MPCost(4)]
    furtum.sfx = ("item", "get_item")
    skills.append(furtum)

    # 회피 자세: Elusio Forma
    elusio_forma = Skill(
        "elusio_forma",
        "Elusio Forma",
        "형체를 흐리게 만들어 회피를 극대화한다."
    )
    elusio_forma.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.30, duration=3, target="self"),
        BuffEffect(BuffType.SPEED_UP, 0.10, duration=3, target="self"),
    ]
    elusio_forma.costs = [MPCost(5)]
    elusio_forma.target_type = "self"
    elusio_forma.sfx = ("skill", "haste")
    skills.append(elusio_forma)

    # 독 도포: Venenum Illitus
    venenum_illitus = Skill(
        "venenum_illitus",
        "Venenum Illitus",
        "무기에 독을 바르고 찌른다."
    )
    venenum_illitus.effects = [
        DamageEffect(DamageType.BRV_HP, 1.25, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=3, value=1.0, damage_multiplier=0.10, damage_stat="physical"),
    ]
    venenum_illitus.costs = [MPCost(6)]
    venenum_illitus.sfx = ("character", "status_debuff")
    skills.append(venenum_illitus)

    # 맹독 검: Toxicum Lamina
    toxicum_lamina = Skill(
        "toxicum_lamina",
        "Toxicum Lamina",
        "맹독을 묻힌 칼날로 베어 HP 피해를 준다."
    )
    toxicum_lamina.effects = [
        DamageEffect(DamageType.HP, 1.35, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=4, value=1.0, damage_multiplier=0.12, damage_stat="physical"),
    ]
    toxicum_lamina.costs = [MPCost(8)]
    toxicum_lamina.sfx = ("combat", "damage_high")
    skills.append(toxicum_lamina)

    # 역병 구체: Pestis Orbis
    pestis_orbis = Skill(
        "pestis_orbis",
        "Pestis Orbis",
        "독기를 담은 구체를 던져 광역 독을 퍼뜨린다."
    )
    pestis_orbis.effects = [
        DamageEffect(DamageType.BRV, 0.95, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=3, value=1.0, damage_multiplier=0.08, damage_stat="physical"),
    ]
    pestis_orbis.target_type = "all_enemies"
    pestis_orbis.is_aoe = True
    pestis_orbis.costs = [MPCost(9)]
    pestis_orbis.sfx = ("character", "status_debuff")
    skills.append(pestis_orbis)

    # 치명 독: Letale Venenum
    letale_venenum = Skill(
        "letale_venenum",
        "Letale Venenum",
        "강력한 치명 독을 주입해 지속 피해를 남긴다."
    )
    letale_venenum.effects = [
        DamageEffect(DamageType.BRV_HP, 1.4, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=5, value=1.0, damage_multiplier=0.15, damage_stat="physical"),
        StatusEffect(StatusType.WEAKNESS, duration=2, value=1.0, chance=0.4),
    ]
    letale_venenum.costs = [MPCost(11)]
    letale_venenum.sfx = ("combat", "damage_high")
    skills.append(letale_venenum)

    # 독 격발: Venenum Impetus
    venenum_impetus = Skill(
        "venenum_impetus",
        "Venenum Impetus",
        "중첩된 독을 폭발시켜 즉각 피해를 준다."
    )
    venenum_impetus.effects = [
        DamageEffect(DamageType.HP, 1.25, stat_type="physical"),
        StatusEffect(StatusType.POISON, duration=2, value=1.0, damage_multiplier=0.10, damage_stat="physical"),
    ]
    venenum_impetus.costs = [MPCost(9)]
    venenum_impetus.sfx = ("skill", "attack_magic")
    skills.append(venenum_impetus)

    # 조롱: Irrisio
    irrisio = Skill(
        "irrisio",
        "Irrisio",
        "조롱으로 적의 정신을 흔들어 공격력을 깎는다."
    )
    irrisio.effects = [
        BuffEffect(BuffType.ATTACK_DOWN, 0.20, duration=2),
        BuffEffect(BuffType.EVASION_UP, 0.15, duration=2, target="self"),
    ]
    irrisio.costs = [MPCost(6)]
    irrisio.sfx = ("character", "status_debuff")
    skills.append(irrisio)

    # 기만: Deceptio
    deceptio = Skill(
        "deceptio",
        "Deceptio",
        "교란 전술로 적을 실명시킨다."
    )
    deceptio.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="physical"),
        StatusEffect(StatusType.BLIND, duration=2, value=1.0, chance=0.35)
    ]
    deceptio.costs = [MPCost(7)]
    deceptio.sfx = ("character", "status_debuff")
    skills.append(deceptio)

    # 그림자 보폭: Umbra Gradus
    umbra_gradus = Skill(
        "umbra_gradus",
        "Umbra Gradus",
        "그림자처럼 움직여 회피와 속도를 크게 높인다."
    )
    umbra_gradus.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.35, duration=2, target="self"),
        BuffEffect(BuffType.SPEED_UP, 0.25, duration=2, target="self"),
    ]
    umbra_gradus.costs = [MPCost(8)]
    umbra_gradus.target_type = "self"
    umbra_gradus.sfx = ("skill", "haste")
    skills.append(umbra_gradus)

    # 수치: Dedecus
    dedecus = Skill(
        "dedecus",
        "Dedecus",
        "수치를 새겨 적의 방어를 무너뜨린다."
    )
    dedecus.effects = [
        DamageEffect(DamageType.BRV, 1.05, stat_type="physical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.18, duration=2)
    ]
    dedecus.costs = [MPCost(6)]
    dedecus.sfx = ("character", "status_debuff")
    skills.append(dedecus)

    # 암살자: Sicarius
    sicarius = Skill(
        "sicarius",
        "Sicarius",
        "암살자의 일격. HP가 낮은 적에게 추가 피해."
    )
    sicarius.effects = [
        DamageEffect(DamageType.HP, 1.65, stat_type="physical"),
        BuffEffect(BuffType.CRITICAL_UP, 0.35, duration=1, target="self"),
    ]
    sicarius.costs = [MPCost(12)]
    sicarius.sfx = ("combat", "critical")
    skills.append(sicarius)

    # 죽음의 낙인: Mortis Signum
    mortis_signum = Skill(
        "mortis_signum",
        "Mortis Signum",
        "죽음의 낙인을 찍어 받는 피해를 증가시킨다."
    )
    mortis_signum.effects = [
        DamageEffect(DamageType.BRV, 1.0, stat_type="physical"),
        StatusEffect(StatusType.EXPOSED, duration=2, value=1.0, chance=0.5)
    ]
    mortis_signum.costs = [MPCost(10)]
    mortis_signum.sfx = ("character", "status_debuff")
    skills.append(mortis_signum)

    # 그림자 죽음: Umbra Mortis
    umbra_mortis = Skill(
        "umbra_mortis",
        "Umbra Mortis",
        "그림자에서 벼락같이 덮쳐 광역 HP 피해를 준다."
    )
    umbra_mortis.effects = [
        DamageEffect(DamageType.HP, 1.25, stat_type="physical"),
        StatusEffect(StatusType.BLEED, duration=2, value=1.0, damage_multiplier=0.08, damage_stat="physical")
    ]
    umbra_mortis.target_type = "all_enemies"
    umbra_mortis.is_aoe = True
    umbra_mortis.costs = [MPCost(13)]
    umbra_mortis.sfx = ("skill", "attack_magic")
    skills.append(umbra_mortis)

    # 궁극: Umbra Incursio
    umbra_incursio = Skill(
        "umbra_incursio",
        "Umbra Incursio",
        "그림자로 돌진해 다단히트로 처치하는 궁극기."
    )
    umbra_incursio.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="physical"),
        DamageEffect(DamageType.HP, 2.2, stat_type="physical"),
        BuffEffect(BuffType.EVASION_UP, 0.25, duration=2, target="self")
    ]
    umbra_incursio.costs = [MPCost(20)]
    umbra_incursio.is_ultimate = True
    umbra_incursio.cooldown = 15
    umbra_incursio.target_type = "all_enemies"
    umbra_incursio.is_aoe = True
    umbra_incursio.sfx = ("skill", "limit_break")
    skills.append(umbra_incursio)

    return skills


def register_rogue_skills(skill_manager):
    """도적 스킬 등록"""
    skills = create_rogue_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"도적 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
