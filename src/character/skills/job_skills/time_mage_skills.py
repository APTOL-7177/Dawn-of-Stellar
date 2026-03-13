"""Time Mage Skills - 시간술사 스킬 (가능성 슬롯 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.atb_effect import AtbEffect
from src.character.skills.costs.mp_cost import MPCost

def create_time_mage_skills():
    """시간술사 19개 스킬 생성 (가능성 슬롯 시스템)"""

    # === 기본 공격 (2개) ===

    # 0-1. 기본 BRV: 시간 왜곡
    time_distortion = Skill("time_mage_time_distortion", "시간 왜곡",
                           "시간을 왜곡하여 BRV 피해 (MAG×1.15). 25% 슬로우, 50% 가능성 생성")
    time_distortion.effects = [
        DamageEffect(DamageType.BRV, 0.75, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.10, duration=1)  # 25% 확률로 적용 (metadata에서 처리)
    ]
    time_distortion.costs = []  # 기본 공격은 MP 무료
    time_distortion.target_type = "single_enemy"
    time_distortion.sfx = ("combat", "attack_magic")
    time_distortion.metadata = {
        "basic_attack": True,
        "possibility_pair": "time_mage_slow",
        "generate_possibility_chance": 0.50,
        "debuff_chance": 0.25,
        "job": "time_mage"
    }

    # 0-2. 기본 HP: 시간 붕괴
    time_collapse = Skill("time_mage_time_collapse", "시간 붕괴",
                         "축적된 시간의 힘을 폭발! HP 피해 (MAG×1.0). 슬롯당 +8%")
    time_collapse.effects = [
        DamageEffect(DamageType.HP, 0.65, stat_type="magical",
                    gimmick_bonus={"field": "possibility_slots", "multiplier": 0.08, "count_mode": True})
    ]
    time_collapse.costs = []  # 기본 공격은 MP 무료
    time_collapse.target_type = "single_enemy"
    time_collapse.sfx = ("combat", "attack_magic")
    time_collapse.metadata = {
        "basic_attack": True,
        "possibility_pair": "time_mage_haste",
        "generate_possibility_chance": 0.50,
        "slot_bonus": 0.08,
        "job": "time_mage"
    }

    # === 공격 스킬 (4개) ===

    # 1. 타임 볼트 - 단일 BRV 공격
    time_bolt = Skill("time_mage_time_bolt", "타임 볼트",
                     "[번개 속성] 응축된 시간 에너지를 발사하여 단일 적에게 BRV 피해")
    time_bolt.effects = [
        DamageEffect(DamageType.BRV, 1.76, stat_type="magical", element="lightning")
    ]
    time_bolt.costs = [MPCost(9)]
    time_bolt.target_type = "single_enemy"
    time_bolt.sfx = ("combat", "attack_magic")
    time_bolt.metadata = {
        "possibility_pair": "time_mage_time_shock",
        "generate_possibility_chance": 0.70,
        "job": "time_mage"
    }

    # 2. 타임 쇼크 - 전체 BRV 공격
    time_shock = Skill("time_mage_time_shock", "타임 쇼크",
                      "[번개 속성] 시간의 충격파로 전체 적에게 BRV 피해")
    time_shock.effects = [
        DamageEffect(DamageType.BRV, 1.56, stat_type="magical", element="lightning")
    ]
    time_shock.costs = [MPCost(12)]
    time_shock.target_type = "all_enemies"
    time_shock.is_aoe = True
    time_shock.sfx = ("skill", "elemental")
    time_shock.metadata = {
        "possibility_pair": "time_mage_time_bolt",
        "generate_possibility_chance": 0.70,
        "job": "time_mage"
    }

    # 3. 크로노 블라스트 - 단일 HP 공격 + 가능성 확정 생성
    chrono_blast = Skill("time_mage_chrono_blast", "크로노 블라스트",
                        "[번개 속성] 시간의 폭발로 강력한 HP 피해 + 가능성 확정 생성")
    chrono_blast.effects = [
        DamageEffect(DamageType.HP, 1.95, stat_type="magical", element="lightning")
    ]
    chrono_blast.costs = [MPCost(12)]
    chrono_blast.target_type = "single_enemy"
    chrono_blast.sfx = ("skill", "explosion")
    chrono_blast.metadata = {
        "possibility_pair": "time_mage_time_wave",
        "generate_possibility_chance": 1.0,  # 100% 확정 생성
        "job": "time_mage"
    }

    # 4. 타임 웨이브 - 전체 BRV+HP 공격
    time_wave = Skill("time_mage_time_wave", "타임 웨이브",
                     "시간의 파동으로 전체 BRV → HP 피해, 20% 슬로우")
    time_wave.effects = [
        DamageEffect(DamageType.BRV, 0.91, stat_type="magical"),
        DamageEffect(DamageType.HP, 1.23, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.20, duration=2)  # 20% 슬로우
    ]
    time_wave.costs = [MPCost(16)]
    time_wave.target_type = "all_enemies"
    time_wave.is_aoe = True
    time_wave.sfx = ("skill", "elemental")
    time_wave.metadata = {
        "possibility_pair": "time_mage_chrono_blast",
        "generate_possibility_chance": 0.70,
        "job": "time_mage"
    }

    # === 버프/디버프 스킬 (6개) ===

    # 5. 헤이스트 - 아군 속도 버프
    haste = Skill("time_mage_haste", "헤이스트",
                 "아군 1명 속도 +60% (3턴)")
    haste.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.60, duration=3),
        AtbEffect(atb_change=200)  # ATB 약간 충전
    ]
    haste.costs = [MPCost(11)]
    haste.target_type = "ally"
    haste.sfx = ("skill", "haste")
    haste.metadata = {
        "possibility_pair": "time_mage_slow",
        "generate_possibility_chance": 0.70,
        "job": "time_mage"
    }

    # 6. 슬로우 - 적 속도 디버프
    slow = Skill("time_mage_slow", "슬로우",
                "적 1명 속도 -40% (3턴)")
    slow.effects = [
        BuffEffect(BuffType.SPEED_DOWN, 0.40, duration=3),
        AtbEffect(atb_change=-200)  # ATB 감소
    ]
    slow.costs = [MPCost(11)]
    slow.target_type = "single_enemy"
    slow.sfx = ("character", "status_debuff")
    slow.metadata = {
        "possibility_pair": "time_mage_haste",
        "generate_possibility_chance": 0.70,
        "job": "time_mage"
    }

    # 7. 시간 정지 - CC
    time_stop = Skill("time_mage_time_stop", "시간 정지",
                     "적 1명 1턴 행동불가 (스턴)")
    time_stop.effects = [
        StatusEffect(StatusType.STUN, duration=1)
    ]
    time_stop.costs = [MPCost(12)]
    time_stop.target_type = "single_enemy"
    time_stop.sfx = ("skill", "cast_complete")
    time_stop.metadata = {
        "possibility_pair": "time_mage_time_accel",
        "generate_possibility_chance": 0.70,
        "job": "time_mage"
    }

    # 8. 시간 가속 - ATB 충전
    time_accel = Skill("time_mage_time_accel", "시간 가속",
                      "아군 1명 ATB 75% 즉시 충전")
    time_accel.effects = [
        AtbEffect(atb_change=750)  # ATB 75% 충전
    ]
    time_accel.costs = [MPCost(15)]
    time_accel.target_type = "ally"
    time_accel.sfx = ("skill", "haste")
    time_accel.metadata = {
        "possibility_pair": "time_mage_time_stop",
        "generate_possibility_chance": 0.70,
        "self_atb_cost": 0.50,  # 시간술사 ATB 50%만 소모
        "job": "time_mage"
    }

    # 9. 미래 예지 - 회피 + 크리티컬 확정
    future_sight = Skill("time_mage_future_sight", "미래 예지",
                        "아군 1명 회피율 +50% (2턴) + 다음 공격 크리티컬 확정")
    future_sight.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=2),
        BuffEffect(BuffType.CRITICAL_UP, 1.0, duration=1)  # 다음 공격 크리티컬 확정
    ]
    future_sight.costs = [MPCost(14)]
    future_sight.target_type = "ally"
    future_sight.sfx = ("character", "status_buff")
    future_sight.metadata = {
        "possibility_pair": "time_mage_past_regression",
        "generate_possibility_chance": 0.70,
        "guaranteed_critical": True,
        "job": "time_mage"
    }

    # 10. 과거 회귀 - HP 복원
    past_regression = Skill("time_mage_past_regression", "과거 회귀",
                           "아군 1명 HP를 2턴 전 상태로 복원 (최대 70% 회복)")
    past_regression.effects = [
        HealEffect(percentage=0.70)  # 최대 70% 회복
    ]
    past_regression.costs = [MPCost(16)]
    past_regression.target_type = "ally"
    past_regression.sfx = ("character", "hp_heal")
    past_regression.metadata = {
        "possibility_pair": "time_mage_future_sight",
        "generate_possibility_chance": 0.70,
        "temporal_heal": True,
        "turns_back": 2,
        "job": "time_mage"
    }

    # === 회복/방어 스킬 (2개) ===

    # 11. 리와인드 - HP 회복 + 디버프 해제
    rewind = Skill("time_mage_rewind", "리와인드",
                  "아군 1명 HP 30% 회복 + 디버프 1개 해제")
    rewind.effects = [
        HealEffect(percentage=0.30)
    ]
    rewind.costs = [MPCost(16)]
    rewind.target_type = "ally"
    rewind.sfx = ("character", "hp_heal")
    rewind.metadata = {
        "possibility_pair": "time_mage_paradox_guard",
        "generate_possibility_chance": 0.70,
        "cleanse_debuffs": 1,
        "job": "time_mage"
    }

    # 12. 역설 방어 - 피해 감소
    paradox_guard = Skill("time_mage_paradox_guard", "역설 방어",
                         "이번 턴 방어력/마법방어력 300% 증가 (받는 피해 75% 감소)")
    paradox_guard.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 3.00, duration=1),  # 300% 방어력 증가
        BuffEffect(BuffType.SPIRIT_UP, 3.00, duration=1)   # 300% 마법방어력 증가
    ]
    paradox_guard.costs = [MPCost(14)]
    paradox_guard.target_type = "self"
    paradox_guard.sfx = ("skill", "barrier")
    paradox_guard.metadata = {
        "possibility_pair": "time_mage_rewind",
        "generate_possibility_chance": 0.70,
        "damage_reduction": 0.75,
        "job": "time_mage"
    }

    # === 가능성 시스템 스킬 (5개) ===

    # 13. 가능성 소환 - MP 0, 슬롯에서 스킬 발동
    summon_possibility = Skill("time_mage_summon_possibility", "가능성 소환",
                              "슬롯에서 가능성 1개 선택 → 85% 위력으로 즉시 발동 (MP 무료!)")
    summon_possibility.effects = []  # 특수 처리
    summon_possibility.costs = [MPCost(0)]  # MP 무료!
    summon_possibility.target_type = "special"
    summon_possibility.sfx = ("skill", "summon")
    summon_possibility.metadata = {
        "gimmick_skill": True,
        "possibility_system": True,
        "action": "summon_single",
        "power_ratio": 0.85,
        "job": "time_mage"
    }

    # 14. 시간선 교차 - 2개 동시 발동
    time_crossing = Skill("time_mage_time_crossing", "시간선 교차",
                         "슬롯의 가능성 2개 동시 발동 (각 75% 위력)")
    time_crossing.effects = []  # 특수 처리
    time_crossing.costs = [MPCost(14)]
    time_crossing.target_type = "special"
    time_crossing.sfx = ("skill", "cast_complete")
    time_crossing.metadata = {
        "gimmick_skill": True,
        "possibility_system": True,
        "action": "summon_dual",
        "power_ratio": 0.75,
        "min_possibilities": 2,
        "job": "time_mage"
    }

    # 15. 시간 폭풍 - 모든 슬롯 해방
    time_storm = Skill("time_mage_time_storm", "시간 폭풍",
                      "저장된 모든 가능성을 해방 (100% 위력). 3개 이상 시 수렴 보너스")
    time_storm.effects = []  # 특수 처리
    time_storm.costs = [MPCost(20)]
    time_storm.target_type = "special"
    time_storm.sfx = ("skill", "limit_break")
    time_storm.metadata = {
        "gimmick_skill": True,
        "possibility_system": True,
        "action": "release_all",
        "power_ratio": 1.0,
        "min_possibilities": 1,
        "convergence_bonus": {
            "min_count": 3,
            "damage_bonus": 0.40,
            "apply_time_lock": True,
            "time_lock_duration": 1
        },
        "job": "time_mage"
    }

    # 16. 운명 복제 - 아군 스킬 복제
    fate_copy = Skill("time_mage_fate_copy", "운명 복제",
                     "아군 1명의 마지막 사용 스킬을 가능성으로 저장")
    fate_copy.effects = []  # 특수 처리
    fate_copy.costs = [MPCost(6)]
    fate_copy.target_type = "ally"
    fate_copy.sfx = ("skill", "cast_complete")
    fate_copy.metadata = {
        "gimmick_skill": True,
        "possibility_system": True,
        "action": "copy_ally_skill",
        "power_ratio": 0.85,
        "cannot_copy": ["ultimate", "teamwork", "items"],
        "job": "time_mage"
    }

    # 17. 운명 덮어쓰기 - 슬롯 스킬 교체
    overwrite_fate = Skill("time_mage_overwrite_fate", "운명 덮어쓰기",
                          "지정한 슬롯의 가능성을 원하는 보유 스킬로 교체 및 강화")
    overwrite_fate.effects = []  # 특수 처리
    overwrite_fate.costs = [MPCost(10)]
    overwrite_fate.target_type = "special"
    overwrite_fate.sfx = ("skill", "cast_complete")
    overwrite_fate.metadata = {
        "gimmick_skill": True,
        "possibility_system": True,
        "action": "overwrite_slot",
        "power_ratio": 1.5,
        "cannot_select": ["ultimate", "teamwork"],
        "min_possibilities": 1,
        "job": "time_mage"
    }

    # === 궁극기 (1개) ===

    # 18. 무한 수렴 - 궁극기
    infinite_convergence = Skill("time_mage_infinite_convergence", "무한 수렴",
                                "[번개 속성] 모든 시간선의 가능성을 수렴! 저장된 가능성 + 타임 볼트/쇼크/리와인드 연속 발동 (120% 위력)")
    infinite_convergence.effects = [
        DamageEffect(DamageType.BRV, 1.62, stat_type="magical", element="lightning"),  # 피니시 피해
        DamageEffect(DamageType.HP, 1.3, stat_type="magical", element="lightning"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.20, duration=2)  # 적 전체 스탯 -20%
    ]
    infinite_convergence.costs = [MPCost(38)]
    infinite_convergence.target_type = "all_enemies"
    infinite_convergence.is_ultimate = True
    infinite_convergence.is_aoe = True
    infinite_convergence.sfx = ("skill", "limit_break")
    infinite_convergence.metadata = {
        "gimmick_skill": True,
        "possibility_system": True,
        "action": "infinite_convergence",
        "power_ratio": 1.2,
        "min_possibilities": 3,
        "chain_cast": ["time_bolt", "time_shock", "rewind"],
        "clear_slots_after": True,
        "job": "time_mage"
    }

    # === 팀워크 스킬 ===

    # 19. 팀워크: 시간 정지
    teamwork = TeamworkSkill(
        "time_mage_teamwork",
        "시공 붕괴",
        "적 전체 시간 정지 (1턴 스턴) + ATB 초기화 + 아군 전체 ATB +50% + 가능성 슬롯 모두 충전",
        gauge_cost=275
    )
    teamwork.effects = [
        StatusEffect(StatusType.STUN, duration=1),  # 적 전체 스턴
        AtbEffect(atb_change=-999),  # 적 ATB 초기화
        BuffEffect(BuffType.SPEED_DOWN, 0.50, duration=2)  # 적 속도 감소
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "atb_reset_enemies": True,
        "atb_boost_allies": 500,
        "fill_possibility_slots": True,
        "job": "time_mage"
    }

    return [
        time_distortion, time_collapse,  # 기본 공격 2개
        time_bolt, time_shock, chrono_blast, time_wave,  # 공격 4개
        haste, slow, time_stop, time_accel, future_sight, past_regression,  # 버프/디버프 6개
        rewind, paradox_guard,  # 회복/방어 2개
        summon_possibility, time_crossing, time_storm, fate_copy, overwrite_fate,  # 가능성 시스템 5개
        infinite_convergence,  # 궁극기 1개
        teamwork  # 팀워크 1개
    ]


def register_time_mage_skills(skill_manager):
    """시간술사 스킬 등록"""
    skills = create_time_mage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]