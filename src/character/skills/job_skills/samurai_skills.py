"""Samurai Skills - 사무라이 (검심 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_samurai_skills():
    """사무라이 10개 스킬 생성 (검심 시스템)"""
    skills = []

    # ============================================================
    # 기본 스킬 3개 (BRV / HP / 방어)
    # ============================================================

    # 1. 켄기 - 기본 BRV 공격
    kengi = Skill("samurai_kengi", "켄기", "기본 검술 공격. 관찰 스택 획득")
    kengi.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        GimmickEffect(GimmickOperation.ADD, "kenatsu", 5, max_value=100)
    ]
    kengi.costs = []  # MP 0
    kengi.sfx = ("combat", "attack_physical")
    kengi.metadata = {"basic_attack": True, "kenatsu_gain": 5}
    skills.append(kengi)

    # 2. 밧토우쥬츠 - 기본 HP 공격
    battojutsu = Skill("samurai_battojutsu", "밧토우쥬츠", "기본 HP 공격. 선제 시 크리티컬 확정")
    battojutsu.effects = [
        DamageEffect(DamageType.HP, 1.5),
        GimmickEffect(GimmickOperation.CONSUME, "observation", 2)  # 관찰 -2
    ]
    battojutsu.costs = []  # MP 0
    battojutsu.sfx = ("combat", "critical")
    battojutsu.metadata = {
        "basic_attack": True,
        "first_strike_bonus": True,  # 선제 시 크리티컬 (특성에서 처리)
        "observation_cost": 2
    }
    skills.append(battojutsu)

    # 3. 미키리 카마에 - 기본 방어 (패링 스킬)
    mikiri_kamae = Skill("samurai_mikiri_kamae", "미키리 카마에", "캐스트 중 피격 시 100% 패링 반격 (MP 0)")
    mikiri_kamae.effects = [
        # 캐스트 완료 시 기본 데미지 (패링 성공 시엔 발동 안 함)
        DamageEffect(DamageType.BRV_HP, 1.0),
    ]
    mikiri_kamae.costs = []  # MP 0 (기본 방어 스킬)
    mikiri_kamae.cast_time = 1.5  # ATB 150% 캐스트
    mikiri_kamae.sfx = ("skill", "protect")
    mikiri_kamae.metadata = {
        "basic_defense": True,  # 기본 방어 스킬
        "parry": True,  # 패링 기술
        "parry_damage_multiplier": 2.5,  # 패링 성공 시 데미지 2.5배
        "parry_observation_gain": 3,  # 패링 성공 시 관찰 +3
        "parry_kenatsu_gain": 40,     # 패링 성공 시 검압 +40
        "cast_time": 1.5,
        "interruptible": True,  # 중단 가능
        "counter_on_interrupt": True  # 캐스트 중 피격 시 카운터
    }
    skills.append(mikiri_kamae)

    # ============================================================
    # 일반 스킬 (MP 소모)
    # ============================================================

    # 4. 겟코우기리 - 관찰 소모 없는 공격
    gekko_giri = Skill("samurai_gekko_giri", "겟코우기리", "관찰 스택을 소모하지 않는 우아한 베기")
    gekko_giri.effects = [
        DamageEffect(DamageType.BRV, 2.2),
        GimmickEffect(GimmickOperation.ADD, "kenatsu", 8, max_value=100)
    ]
    gekko_giri.costs = [MPCost(6)]
    gekko_giri.sfx = ("combat", "attack_physical")
    gekko_giri.metadata = {"no_observation_cost": True, "kenatsu_gain": 8}
    skills.append(gekko_giri)

    # 5. 메이쿄시스이 - 관찰력 증가
    meikyo_shisui = Skill("samurai_meikyo_shisui", "메이쿄시스이", "마음을 비워 관찰력 증가")
    meikyo_shisui.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3, target="self"),
        GimmickEffect(GimmickOperation.ADD, "observation", 2, max_value=15)  # 관찰 +2
    ]
    meikyo_shisui.costs = [MPCost(5)]
    meikyo_shisui.target_type = "self"
    meikyo_shisui.sfx = ("character", "status_buff")
    meikyo_shisui.metadata = {"observation_gain": 2, "buff": True}
    skills.append(meikyo_shisui)

    # 6. 기의 타테 - 아군 보호 패링
    gi_no_tate = Skill("samurai_gi_no_tate", "기의 타테", "아군 1명을 지키는 의리의 방패")
    gi_no_tate.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=1, target="ally"),  # 임시 방어
    ]
    gi_no_tate.costs = [MPCost(12)]
    gi_no_tate.target_type = "ally"
    gi_no_tate.sfx = ("skill", "protect")
    gi_no_tate.metadata = {
        "protect_ally": True,
        "parry_for_ally": True,
        "observation_gain": 4,   # 성공 시 관찰 +4
        "kenatsu_gain": 50,      # 성공 시 검압 +50
        "counter_multiplier": 2.5  # 반격 2.5배
    }
    skills.append(gi_no_tate)

    # ============================================================
    # 검압 소모 스킬 (검압 게이지 필요)
    # ============================================================

    # 7. 미키리 - 적 BRV 흡수
    mikiri = Skill("samurai_mikiri", "미키리", "적의 BRV를 간파하여 흡수")
    mikiri.effects = [
        # BRV 흡수는 기믹 업데이터에서 처리
        GimmickEffect(GimmickOperation.CONSUME, "kenatsu", 30),
        GimmickEffect(GimmickOperation.ADD, "observation", 1, max_value=15)
    ]
    mikiri.costs = [StackCost("kenatsu", 30)]
    mikiri.target_type = "enemy"
    mikiri.sfx = ("skill", "debuff")
    mikiri.metadata = {
        "brv_steal": True,
        "steal_rate_base": 0.5,     # 기본 50%
        "steal_rate_mushin": 0.6,   # 무심 60%
        "steal_rate_kensei": 0.8,   # 검성 80%
        "kenatsu_cost": 30,
        "observation_gain": 1
    }
    skills.append(mikiri)

    # 8. 켄아츠잔 - 검압 베기
    kenatsuan = Skill("samurai_kenatsuan", "켄아츠잔", "검압 소모 강력 공격")
    kenatsuan.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0),
        GimmickEffect(GimmickOperation.CONSUME, "kenatsu", 50),
        GimmickEffect(GimmickOperation.CONSUME, "observation", 1)
    ]
    kenatsuan.costs = [StackCost("kenatsu", 50)]
    kenatsuan.sfx = ("combat", "damage_high")
    kenatsuan.metadata = {"kenatsu_cost": 50, "observation_cost": 1, "spender": True}
    skills.append(kenatsuan)

    # ============================================================
    # 특수 스킬 (즉시 발동)
    # ============================================================

    # 9. 요미 - 적 행동 예측 (턴 소모 없음, MP 소량)
    yomi = Skill(
        "samurai_yomi",
        "요미",
        "무심 5+에서 즉시 발동, 토글 ON 동안 적 전체(최대 4명)의 다음 2턴 행동/ATB를 예측하고 매턴 MP 8 소모",
    )
    yomi.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.1, duration=2, target="self"),  # 부가 효과
    ]
    yomi.costs = [MPCost(5)]  # MP 소량 소모
    yomi.target_type = "self"
    yomi.instant = True  # 턴 소모 없음 (ATB 소모 X)
    yomi.sfx = ("skill", "scan")
    yomi.metadata = {
        "instant": True,  # 즉시 발동
        "prediction": True,
        "prediction_turns": 2,  # 다음 2턴 예측
        "show_enemy_actions": True,
        "condition": "mushin",  # 무심(5+) 상태에서만 사용 가능
        "toggle": True,  # ON/OFF 토글
        "max_mp_penalty": 0.0,  # 토글 유지비 없음 (필요 시 조정)
        "toggle_mp_per_turn": 8,  # 토글 ON 유지 시 매턴 MP 소모
    }
    skills.append(yomi)

    # 10. 텐치쥬잔 - 패링형 궁극기
    tenchijuzan = Skill("samurai_tenchijuzan", "텐치쥬잔", "천지를 가르는 일격 (패링 중/성공 후 사용 시 강화)")
    tenchijuzan.effects = [
        DamageEffect(DamageType.HP, 2.5),  # 기본 (평시)
        GimmickEffect(GimmickOperation.CONSUME, "observation", 3)
    ]
    tenchijuzan.costs = [MPCost(20), StackCost("kenatsu", 60)]
    tenchijuzan.cast_time = 0.5
    tenchijuzan.cooldown = 5
    tenchijuzan.sfx = ("skill", "ultima")
    tenchijuzan.metadata = {
        "parry_ultimate": True,  # 패링형 궁극기
        "normal_damage": 2.5,    # 평시 HP 2.5배
        "parry_damage": 6.0,     # 패링 중/성공 후 HP 6.0배
        "parry_bonus": "brv_reset",  # 패링 강화 시 적 BRV 초기화
        "condition": "kensei",   # 검성(10+) 상태에서만 사용 가능
        "observation_cost": 3,
        "kenatsu_cost": 60,
        "parry_window": 3  # 패링 성공 후 3턴 내 사용 시 강화
    }
    skills.append(tenchijuzan)

    # ============================================================
    # 궁극기 (타이밍형)
    # ============================================================

    # 11. 무료타이가 - 최종 궁극기
    ultimate = Skill("samurai_ultimate", "무료타이가", "무량한 검의 흐름으로 모든 것을 베다")
    ultimate.effects = [
        DamageEffect(DamageType.HP, 2.0),  # 기본 (평시)
        BuffEffect(BuffType.INVINCIBLE, 1.0, duration=3, target="self"),  # 패링 강화 시만
        GimmickEffect(GimmickOperation.SET, "observation", 0)  # 관찰 초기화
    ]
    ultimate.costs = [MPCost(30), StackCost("kenatsu", 100)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "parry_ultimate": True,  # 패링형 궁극기
        "normal_damage": 2.0,    # 평시 HP 2.0배 (전체)
        "parry_damage": 5.0,     # 패링 중/성공 후 HP 5.0배 (전체)
        "parry_bonus": "invincible_3",  # 패링 강화 시 무적 3턴
        "kenatsu_cost": 100,
        "observation_reset": True,
        "parry_window": 3  # 패링 성공 후 3턴 내 사용 시 강화
    }
    skills.append(ultimate)

    # ============================================================
    # 팀워크 스킬
    # ============================================================

    # 12. 켄세이노오시에 - 검성의 가르침
    teamwork = TeamworkSkill(
        "samurai_teamwork",
        "켄세이노오시에",
        "검성의 가르침을 아군에게 전수한다",
        gauge_cost=200
    )
    teamwork.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "observation", 3, max_value=15),
        GimmickEffect(GimmickOperation.ADD, "kenatsu", 40, max_value=100)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "observation_gain": 3,
        "kenatsu_gain": 40,
        "party_counter_rate": 0.2  # 아군 전체 반격률 +20% (3턴)
    }
    skills.append(teamwork)

    return skills

def register_samurai_skills(skill_manager):
    """사무라이 스킬 등록"""
    skills = create_samurai_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
