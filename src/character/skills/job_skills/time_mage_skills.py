"""Time Mage Skills - 시간술사 스킬 (타임라인 균형 시스템)"""
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
    """시간술사 10개 스킬 생성 (타임라인 균형 시스템)"""

    # === 기본 공격 ===

    # 1. 기본 BRV: 시간 가속
    time_bolt = Skill("time_mage_time_bolt", "시간 탄환",
                     "시간 에너지로 BRV 피해")
    time_bolt.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical")
    ]
    time_bolt.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 시간 충격
    time_shock = Skill("time_mage_time_shock", "시간 충격",
                      "시간의 힘으로 HP 피해")
    time_shock.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical")
    ]
    time_shock.costs = []  # 기본 공격은 MP 소모 없음

    # === 과거 스킬 (타임라인 -1 또는 -2) ===

    # 3. 슬로우 (느려지기) - 과거 스킬
    slow = Skill("time_mage_slow", "슬로우",
                "적 ATB -50%, 속도 -50% 3턴, 타임라인 -1 (과거)")
    slow.effects = [
        AtbEffect(atb_change=-250),  # ATB 즉시 감소
        BuffEffect(BuffType.SPEED_DOWN, 0.5, duration=3),  # 속도도 감소 (지속)
        GimmickEffect(GimmickOperation.ADD, "timeline", -1, min_value=-5)
    ]
    slow.costs = []
    slow.target_type = "single_enemy"
    slow.metadata = {"timeline_shift": -1, "skill_type": "past"}

    # 4. 시간 정지 (스톱) - 과거 스킬
    stop = Skill("time_mage_stop", "시간 정지",
                "적 1턴 스턴, 타임라인 -1 (과거)")
    stop.effects = [
        StatusEffect(StatusType.STUN, duration=1),
        GimmickEffect(GimmickOperation.ADD, "timeline", -1, min_value=-5)
    ]
    stop.costs = [MPCost(9)]
    stop.target_type = "single_enemy"
    # stop.cooldown = 3  # 쿨다운 시스템 제거됨
    stop.metadata = {"timeline_shift": -1, "skill_type": "past"}

    # 5. 시간 역행 - 과거 스킬
    rewind = Skill("time_mage_rewind", "시간 역행",
                  "HP 20% 회복, 디버프 제거, 타임라인 -2 (과거)")
    rewind.effects = [
        HealEffect(percentage=0.38),  # 시간 되돌리기 (0.29 → 0.38 증가)
        GimmickEffect(GimmickOperation.ADD, "timeline", -2, min_value=-5)
    ]
    rewind.costs = [MPCost(7)]
    rewind.target_type = "self"
    # rewind.cooldown = 4  # 쿨다운 시스템 제거됨
    rewind.metadata = {"timeline_shift": -2, "skill_type": "past"}

    # 6. 과거 반복 - 과거 스킬 (MP 대량 회복으로 이전 스킬 재사용 가능)
    repeat = Skill("time_mage_repeat", "과거 반복",
                  "MP 30 회복 + 마법력 +30%, 타임라인 -1 (과거)")
    repeat.effects = [
        HealEffect(heal_type=HealType.MP, base_amount=30),
        BuffEffect(BuffType.MAGIC_UP, 0.3, duration=2),
        GimmickEffect(GimmickOperation.ADD, "timeline", -1, min_value=-5)
    ]
    repeat.costs = [MPCost(6)]
    repeat.target_type = "self"
    # repeat.cooldown = 5  # 쿨다운 시스템 제거됨
    repeat.metadata = {"timeline_shift": -1, "skill_type": "past", "mp_recovery": True}

    # === 현재 스킬 (타임라인 변화 없음) ===

    # 7. 시간 정렬 - 현재 스킬 (타임라인 → 0)
    align = Skill("time_mage_align", "시간 정렬",
                 "타임라인을 0(현재)으로 리셋, HP 20% 회복")
    align.effects = [
        GimmickEffect(GimmickOperation.SET, "timeline", 0),
        HealEffect(percentage=0.38)  # 시간 정렬 (0.29 → 0.38 증가)
    ]
    align.costs = [MPCost(5)]
    align.target_type = "self"
    align.metadata = {"timeline_shift": "reset", "skill_type": "present"}

    # 8. 시간의 균형 - 현재 스킬 (현재 상태에서만 사용 가능)
    balance = Skill("time_mage_balance", "시간의 균형",
                   "현재(0) 상태에서만 발동, 배율 4.5 대량 피해")
    balance.effects = [
        DamageEffect(DamageType.BRV_HP, 4.5, stat_type="magical",
                    conditional_bonus={"condition": "at_present", "multiplier": 1.0})
    ]
    balance.costs = [MPCost(10)]
    # balance.cooldown = 6  # 쿨다운 시스템 제거됨
    balance.metadata = {"requires_timeline": 0, "skill_type": "present"}

    # === 미래 스킬 (타임라인 +1 또는 +2) ===

    # 9. 헤이스트 (가속) - 미래 스킬
    haste = Skill("time_mage_haste", "헤이스트",
                 "아군 ATB +100%, 속도 +100% 3턴, 타임라인 +1 (미래)")
    haste.effects = [
        AtbEffect(atb_change=500),  # ATB 즉시 증가
        BuffEffect(BuffType.SPEED_UP, 1.0, duration=3),  # 속도도 증가 (지속)
        GimmickEffect(GimmickOperation.ADD, "timeline", 1, max_value=5)
    ]
    haste.costs = [MPCost(6)]
    haste.target_type = "ally"
    # haste.cooldown = 3  # 쿨다운 시스템 제거됨
    haste.metadata = {"timeline_shift": 1, "skill_type": "future"}

    # 10. 예지 - 미래 스킬
    foresight = Skill("time_mage_foresight", "예지",
                     "회피율 +50%, 타임라인 +1 (미래)")
    foresight.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.ADD, "timeline", 1, max_value=5)
    ]
    foresight.costs = [MPCost(4)]
    foresight.target_type = "self"
    foresight.metadata = {"timeline_shift": 1, "skill_type": "future"}

    # 11. 시간 도약 (퀵) - 미래 스킬 (ATB 대폭 증가로 거의 즉시 턴 획득)
    leap = Skill("time_mage_leap", "시간 도약",
                "ATB +150%, 속도 +200% 1턴 (거의 즉시 다음 턴), 타임라인 +2 (미래)")
    leap.effects = [
        AtbEffect(atb_change=750),  # ATB 즉시 대폭 증가
        BuffEffect(BuffType.SPEED_UP, 2.0, duration=1),  # 속도 +200%
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=1),  # 공격력도 증가
        GimmickEffect(GimmickOperation.ADD, "timeline", 2, max_value=5)
    ]
    leap.costs = [MPCost(9)]
    leap.target_type = "self"
    # leap.cooldown = 5  # 쿨다운 시스템 제거됨
    leap.metadata = {"timeline_shift": 2, "skill_type": "future", "quick_turn": True}

    # 12. 궁극기: 시간 파동 - 현재 스킬
    wave = Skill("time_mage_wave", "시간 파동",
                "타임라인 무관 최대 효과, 전체 공격")
    wave.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "timeline", 0)  # 현재로 리셋
    ]
    wave.costs = [MPCost(30)]
    wave.target_type = "all_enemies"
    wave.is_ultimate = True
    wave.cooldown = 15  # 궁극기 쿨타임 15턴
    wave.is_aoe = True
    wave.metadata = {"timeline_shift": "reset", "skill_type": "ultimate"}

    return [time_bolt, time_shock, slow, stop, rewind, repeat,
            align, balance, haste, foresight, leap, wave]

def register_time_mage_skills(skill_manager):
    """시간술사 스킬 등록"""
    skills = create_time_mage_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 시간 정지
    teamwork = TeamworkSkill(
        "time_mage_teamwork",
        "시간 정지",
        "적 전체 기절 (1턴, 저항 불가) + ATB 초기화 + 아군 전체 ATB +500 + 타임라인 초기화",
        gauge_cost=275
    )
    teamwork.effects = [
        # 적 전체 기절 (1턴, 저항 불가)
        StatusEffect("STUN", duration=1, cannot_resist=True),
        # ATB 초기화 (적 전체)
        AtbEffect(atb_change=-999, target_all_enemies=True),  # 충분히 큰 음수로 ATB 0 만들기
        # 아군 전체 ATB +500
        AtbEffect(atb_change=500, is_party_wide=True),
        # 타임라인 초기화 (0으로 설정)
        GimmickEffect(GimmickOperation.SET, "timeline", 0)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True, "atb_reset_enemies": True, "atb_boost_allies": 500}
    skills.append(teamwork)
    return skills
