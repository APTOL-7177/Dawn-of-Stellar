"""Illusionist Skills - 환술사 스킬 (환영 군단 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.atb_effect import AtbEffect
from src.character.skills.costs.mp_cost import MPCost

def create_illusionist_skills():
    """환술사 스킬 생성 (환영 군단 시스템)"""

    # === 기본 공격 ===

    # 1. 기본 BRV: 환영 베기
    phantom_slash = Skill("illusionist_phantom_slash", "환영 베기",
                         "환영과 함께 BRV 피해 (물리)")
    phantom_slash.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="physical")
    ]
    phantom_slash.costs = []
    phantom_slash.sfx = ("combat", "attack_sword")
    phantom_slash.metadata = {"basic_attack": True, "scaling": "physical"}

    # 2. 기본 HP: 거울 파편
    mirror_shard = Skill("illusionist_mirror_shard", "거울 파편",
                        "거울 파편으로 HP 피해 (마법)")
    mirror_shard.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical")
    ]
    mirror_shard.costs = []
    mirror_shard.sfx = ("combat", "attack_magic")
    mirror_shard.metadata = {"basic_attack": True, "scaling": "magical"}

    # === 환영 소환 스킬 ===

    # 3. 환영 소환
    summon_phantom = Skill("illusionist_summon_phantom", "환영 소환",
                          "환영 1~2개 생성, 회피율 +10% (1턴)")
    summon_phantom.effects = [
        GimmickEffect(GimmickOperation.ADD, "phantom_count", 1, max_value=4),  # phantom_hits 자동 업데이트
        BuffEffect(BuffType.EVASION_UP, 0.10, duration=1)
    ]
    summon_phantom.costs = [MPCost(8)]
    summon_phantom.target_type = "self"
    summon_phantom.sfx = ("skill", "summon")
    summon_phantom.metadata = {"phantom_generation": True, "bonus_phantom_chance": 0.30}

    # 4. 환영 군단 소집
    phantom_army = Skill("illusionist_phantom_army", "환영 군단 소집",
                        "환영 슬롯 최대(4개) 충전, 회피 +20% (2턴)")
    # 환영 군단 소집: phantom_count 설정 (phantom_hits는 자동으로 업데이트됨)
    phantom_army.effects = [
        GimmickEffect(GimmickOperation.SET, "phantom_count", 4),  # phantom_hits 자동 초기화
        BuffEffect(BuffType.EVASION_UP, 0.20, duration=2)
    ]
    phantom_army.costs = [MPCost(18)]
    phantom_army.cooldown = 4
    phantom_army.target_type = "self"
    phantom_army.sfx = ("skill", "summon")
    phantom_army.metadata = {"phantom_generation": True, "fill_to_max": True}

    # 5. 거울 대체
    mirror_replacement = Skill("illusionist_mirror_replacement", "거울 대체",
                              "환영 1개 소멸 → HP 15% 회복 + 잔상 +35")
    mirror_replacement.effects = [
        GimmickEffect(GimmickOperation.ADD, "phantom_count", -1, min_value=0),
        HealEffect(percentage=0.15),
        GimmickEffect(GimmickOperation.ADD, "afterimage_gauge", 35, max_value=100)
    ]
    mirror_replacement.costs = [MPCost(5)]
    mirror_replacement.target_type = "self"
    mirror_replacement.sfx = ("character", "hp_heal")
    mirror_replacement.metadata = {"phantom_consume": True, "requires_phantom": 1}

    # === 회피/방어 스킬 ===

    # 6. 환영 회피
    phantom_dodge = Skill("illusionist_phantom_dodge", "환영 회피",
                         "이번 턴 회피율 +50%, 회피 성공 시 환영 생성")
    phantom_dodge.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=1)
    ]
    phantom_dodge.costs = [MPCost(6)]
    phantom_dodge.target_type = "self"
    phantom_dodge.sfx = ("character", "status_buff")
    phantom_dodge.metadata = {"evasion_skill": True, "on_evade_summon": True}

    # 7. 거울 방패
    mirror_shield = Skill("illusionist_mirror_shield", "거울 방패",
                         "아군에게 환영 보호막 부여 (피해 2회 흡수)")
    mirror_shield.effects = [
        BuffEffect(BuffType.BARRIER, 2.0, duration=3, custom_stat="phantom_absorb")  # 2히트 흡수
    ]
    mirror_shield.costs = [MPCost(10)]
    mirror_shield.target_type = "ally"
    mirror_shield.sfx = ("skill", "barrier")
    mirror_shield.metadata = {"shield_skill": True, "absorb_hits": 2}

    # 8. 위상 이동
    phase_walk = Skill("illusionist_phase_walk", "위상 이동",
                      "1턴간 확정 회피, 공격 불가, 환영 1개 생성")
    phase_walk.effects = [
        BuffEffect(BuffType.EVASION_UP, 10.0, duration=3),  # 사실상 확정 회피 (2턴 동안 유지)
        StatusEffect(StatusType.SILENCE, duration=1),  # 공격 불가
        GimmickEffect(GimmickOperation.ADD, "phantom_count", 1, max_value=4)
    ]
    phase_walk.costs = [MPCost(12)]
    phase_walk.target_type = "self"
    phase_walk.sfx = ("skill", "teleport")
    phase_walk.metadata = {"guaranteed_evasion": True, "cannot_attack": True}

    # 9. 공유 환상
    shared_illusion = Skill("illusionist_shared_illusion", "공유 환상",
                           "환영 1개 소모, 아군 전체 회피 +25% (2턴)")
    shared_illusion.effects = [
        GimmickEffect(GimmickOperation.ADD, "phantom_count", -1, min_value=0),
        BuffEffect(BuffType.EVASION_UP, 0.25, duration=2)
    ]
    shared_illusion.costs = [MPCost(14)]
    shared_illusion.target_type = "all_allies"
    shared_illusion.is_aoe = True
    shared_illusion.sfx = ("skill", "barrier")
    shared_illusion.metadata = {"party_buff": True, "requires_phantom": 1}

    # === 공격 스킬 ===

    # 10. 환영 일격 (물리)
    phantom_strike = Skill("illusionist_phantom_strike", "환영 일격",
                          "환영과 함께 다단히트 BRV 공격 (물리)")
    phantom_strike.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="physical",
                    gimmick_bonus={"field": "phantom_count", "multiplier": 0.4})
    ]
    phantom_strike.costs = [MPCost(8)]
    phantom_strike.target_type = "single_enemy"
    phantom_strike.sfx = ("combat", "multi_hit")
    phantom_strike.metadata = {"multi_hit": True, "scaling": "physical", "hit_delay": 0.2}

    # 11. 거울 폭풍 (마법)
    mirror_storm = Skill("illusionist_mirror_storm", "거울 폭풍",
                        "환영과 함께 전체 다단히트 BRV 공격 (마법)")
    mirror_storm.effects = [
        DamageEffect(DamageType.BRV, 0.9, stat_type="magical",
                    gimmick_bonus={"field": "phantom_count", "multiplier": 0.25})
    ]
    mirror_storm.costs = [MPCost(12)]
    mirror_storm.target_type = "all_enemies"
    mirror_storm.is_aoe = True
    mirror_storm.sfx = ("skill", "elemental")
    mirror_storm.metadata = {"multi_hit": True, "scaling": "magical", "hit_delay": 0.2}

    # 12. 수렴의 칼날 (물리 HP)
    convergence_blade = Skill("illusionist_convergence_blade", "수렴의 칼날",
                             "환영 수렴 HP 공격, 환영당 +25% (물리)")
    convergence_blade.effects = [
        DamageEffect(DamageType.HP, 2.0, stat_type="physical",
                    gimmick_bonus={"field": "phantom_count", "multiplier": 0.25})
    ]
    convergence_blade.costs = [MPCost(14)]
    convergence_blade.target_type = "single_enemy"
    convergence_blade.sfx = ("combat", "attack_sword")
    convergence_blade.metadata = {"hp_attack": True, "scaling": "physical"}

    # 13. 환영우 (마법 BRV+HP)
    phantom_rain = Skill("illusionist_phantom_rain", "환영우",
                        "전체 BRV → 랜덤 HP 공격, 환영 많을수록 타수 증가 (마법)")
    phantom_rain.effects = [
        DamageEffect(DamageType.BRV, 0.35, stat_type="magical"),
        DamageEffect(DamageType.HP, 0.12, stat_type="magical",
                    gimmick_bonus={"field": "phantom_count", "multiplier": 0.1}),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.10, duration=2)  # 적 명중 감소
    ]
    phantom_rain.costs = [MPCost(18)]
    phantom_rain.target_type = "all_enemies"
    phantom_rain.is_aoe = True
    phantom_rain.sfx = ("skill", "rain")
    phantom_rain.metadata = {"multi_hit": True, "scaling": "magical", "random_hp": True}

    # === 디버프/유틸 스킬 ===

    # 14. 혼란의 장막 (마법)
    confusion_veil = Skill("illusionist_confusion_veil", "혼란의 장막",
                          "적 전체 명중률 -20% (3턴), 환영 보유 시 추가 -5%")
    confusion_veil.effects = [
        BuffEffect(BuffType.ACCURACY_DOWN, 0.20, duration=3)
    ]
    confusion_veil.costs = [MPCost(9)]
    confusion_veil.target_type = "all_enemies"
    confusion_veil.is_aoe = True
    confusion_veil.sfx = ("character", "status_debuff")
    confusion_veil.metadata = {"debuff_skill": True, "phantom_bonus": 0.05}

    # 15. 분산 도발 (물리)
    taunt_split = Skill("illusionist_taunt_split", "분산 도발",
                       "적 타겟을 환영에게 분산, 환영 우선 타격")
    taunt_split.effects = [
        BuffEffect(BuffType.CUSTOM, 1.0, duration=2, custom_stat="taunt")
    ]
    taunt_split.costs = [MPCost(7)]
    taunt_split.target_type = "self"
    taunt_split.sfx = ("character", "taunt")
    taunt_split.metadata = {"tank_skill": True, "phantom_priority": True}

    # 16. 거울 함정 (마법)
    mirror_trap = Skill("illusionist_mirror_trap", "거울 함정",
                       "거울 함정 설치, 적 공격 시 30% 확률로 40% 반사 (마법)")
    mirror_trap.effects = [
        BuffEffect(BuffType.COUNTER, 0.40, duration=2)  # 40% 반사
    ]
    mirror_trap.costs = [MPCost(11)]
    mirror_trap.target_type = "self"
    mirror_trap.sfx = ("skill", "trap")
    mirror_trap.metadata = {"trap_skill": True, "reflect_chance": 0.30, "scaling": "magical"}

    # === 잔상 스킬 ===

    # 17. 잔상 폭발 (마법)
    afterimage_burst = Skill("illusionist_afterimage_burst", "잔상 폭발",
                            "잔상 소모 → 전체 BRV+HP (마법), 잔상 1당 +1%")
    afterimage_burst.effects = [
        GimmickEffect(GimmickOperation.SET, "afterimage_gauge", 0),  # 전부 소모
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "phantom_count", 1, max_value=4)
    ]
    afterimage_burst.costs = [MPCost(14)]
    afterimage_burst.target_type = "all_enemies"
    afterimage_burst.is_aoe = True
    afterimage_burst.sfx = ("skill", "explosion")
    afterimage_burst.metadata = {"requires_afterimage": 50, "scaling": "magical", "afterimage_scaling": 0.01}

    # === 궁극기 ===

    # 18. 무한 반사 (물리)
    infinite_reflection = Skill("illusionist_infinite_reflection", "무한 반사",
                               "모든 환영 수렴, (환영+1)×0.6 다단 HP (물리), 확정 회피 1턴")
    infinite_reflection.effects = [
        DamageEffect(DamageType.HP, 0.6, stat_type="physical",
                    gimmick_bonus={"field": "phantom_count", "multiplier": 0.6}),
        GimmickEffect(GimmickOperation.SET, "phantom_count", 0),  # 환영 전부 소모
        GimmickEffect(GimmickOperation.SET, "afterimage_gauge", 0),  # 잔상 전부 소모
        BuffEffect(BuffType.EVASION_UP, 10.0, duration=1),  # 확정 회피
        GimmickEffect(GimmickOperation.ADD, "phantom_count", 2, max_value=4)  # 2개 재생성
    ]
    infinite_reflection.costs = [MPCost(28)]
    infinite_reflection.target_type = "single_enemy"
    infinite_reflection.is_ultimate = True
    infinite_reflection.sfx = ("skill", "limit_break")
    infinite_reflection.metadata = {
        "ultimate": True, 
        "requires_afterimage": 80, 
        "scaling": "physical",
        "multi_hit": True,
        "hit_delay": 0.2,
        "max_hits": 10
    }

    # === 팀워크 스킬 ===

    # 19. 팀워크: 거울의 미궁
    teamwork = TeamworkSkill(
        "illusionist_teamwork",
        "거울의 미궁",
        "적 전체 명중 -50% (2턴) + 확정 회피 (아군 전체 1턴) + 환영 4개 생성",
        gauge_cost=275
    )
    teamwork.effects = [
        # 적 전체 명중률 대폭 감소
        BuffEffect(BuffType.ACCURACY_DOWN, 0.50, duration=2),
        # 아군 전체 확정 회피 (1턴)
        BuffEffect(BuffType.EVASION_UP, 10.0, duration=1),
        # 환영 최대 생성
        GimmickEffect(GimmickOperation.SET, "phantom_count", 4)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "party_evasion": True}

    # === 방어형 스킬 ===

    # 20. 거울 감응 (Mirror Resonance) - 방어형 스킬
    mirror_resonance = Skill("illusionist_mirror_resonance", "거울 감응",
                            "환영 3개 이상일 때 방어력/마법방어력 +25%, 회피 성공 시 환영 복구")
    mirror_resonance.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.25, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.25, duration=3)
    ]
    mirror_resonance.costs = [MPCost(9)]
    mirror_resonance.target_type = "self"
    mirror_resonance.sfx = ("skill", "protect")
    mirror_resonance.metadata = {
        "tank_skill": True,
        "requires_phantom": 3,
        "evasion_synergy": True,
        "on_evade_restore_phantom": True,
        "skill_category": "defense"
    }

    # 21. 환영 장막 (Phantom Aegis) - 방어형 스킬
    phantom_aegis = Skill("illusionist_phantom_aegis", "환영 장막",
                         "받는 피해 50%를 환영이 대신 받음, 피해 받은 환영 즉시 파괴")
    phantom_aegis.effects = [
        GimmickEffect(GimmickOperation.ADD, "phantom_count", 1, max_value=4)  # 보너스 환영
    ]
    phantom_aegis.costs = [MPCost(13)]
    phantom_aegis.target_type = "self"
    phantom_aegis.sfx = ("skill", "barrier")
    phantom_aegis.metadata = {
        "tank_skill": True,
        "requires_phantom": 1,
        "phantom_damage_redirect": 0.50,
        "destroy_phantom_on_redirect": True,
        "skill_category": "defense"
    }

    return [
        phantom_slash, mirror_shard,  # 기본 공격
        summon_phantom, phantom_army, mirror_replacement,  # 환영 소환
        phantom_dodge, mirror_shield, phase_walk, shared_illusion,  # 회피/방어
        phantom_strike, mirror_storm, convergence_blade, phantom_rain,  # 공격
        confusion_veil, taunt_split, mirror_trap,  # 디버프/유틸
        afterimage_burst,  # 잔상
        infinite_reflection,  # 궁극기
        teamwork,  # 팀워크
        mirror_resonance, phantom_aegis  # 방어형 스킬
    ]


def register_illusionist_skills(skill_manager):
    """환술사 스킬 등록"""
    skills = create_illusionist_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
