"""Hacker Skills - 해커 스킬 (멀티스레드 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_hacker_skills():
    """해커 10개 스킬 생성 (멀티스레드 시스템 - 최대 3개 프로그램 동시 실행)"""

    # 1. 기본 BRV: 코드 주입
    code_injection = Skill("hacker_code_injection", "코드 주입", "기본 해킹 공격")
    code_injection.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical")
    ]
    code_injection.costs = []  # 기본 공격은 MP 소모 없음
    code_injection.sfx = ("skill", "computer")  # 코드 주입
    code_injection.metadata = {}

    # 2. 기본 HP: 데이터 유출
    data_breach = Skill("hacker_data_breach", "데이터 유출", "정보 탈취 HP 공격")
    data_breach.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical")
    ]
    data_breach.costs = []  # 기본 공격은 MP 소모 없음
    data_breach.sfx = ("skill", "load")  # 데이터 유출
    data_breach.metadata = {}

    # 3. 바이러스 실행 (적 전체 공격력 + 마법력 -15%)
    run_virus = Skill("hacker_run_virus", "바이러스 실행", "적 전체 공격력 + 마법력 -15% 프로그램 실행")
    run_virus.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_virus", 1, max_value=1),  # 프로그램 실행 (on/off)
        BuffEffect(BuffType.ATTACK_DOWN, 0.15, duration=99),  # 프로그램 실행 동안 지속
        BuffEffect(BuffType.MAGIC_DOWN, 0.15, duration=99)  # 마법력도 동시 감소
    ]
    run_virus.costs = []  # MP 소모 0으로 변경
    run_virus.target_type = "all_enemies"
    run_virus.is_aoe = True
    run_virus.sfx = ("skill", "switch")  # 바이러스 실행
    # run_virus.cooldown = 2  # 쿨다운 시스템 제거됨
    run_virus.metadata = {"program_type": "virus", "debuff": "attack_down"}

    # 4. 백도어 실행 (적 전체 방어력 + 마법방어력 -20%)
    run_backdoor = Skill("hacker_run_backdoor", "백도어 실행", "적 전체 방어력 + 마법방어력 -20% 프로그램 실행")
    run_backdoor.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_backdoor", 1, max_value=1),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.2, duration=99),
        BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, 0.2, duration=99)
    ]
    run_backdoor.costs = []  # MP 소모 0으로 변경
    run_backdoor.target_type = "all_enemies"
    run_backdoor.is_aoe = True
    run_backdoor.sfx = ("skill", "computer")  # 백도어 실행
    # run_backdoor.cooldown = 2  # 쿨다운 시스템 제거됨
    run_backdoor.metadata = {"program_type": "backdoor", "debuff": "defense_down"}

    # 5. DDoS 실행 (적 전체 속도 -35%)
    run_ddos = Skill("hacker_run_ddos", "DDoS 실행", "적 전체 속도 -35% 프로그램 실행")
    run_ddos.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_ddos", 1, max_value=1),
        BuffEffect(BuffType.SPEED_DOWN, 0.35, duration=99)
    ]
    run_ddos.costs = []  # MP 소모 0으로 변경
    run_ddos.target_type = "all_enemies"
    run_ddos.is_aoe = True
    run_ddos.sfx = ("skill", "machine")  # DDoS 실행
    # run_ddos.cooldown = 3  # 쿨다운 시스템 제거됨
    run_ddos.metadata = {"program_type": "ddos", "debuff": "speed_down"}

    # 6. 랜섬웨어 실행 (적 전체 매 턴 HP 피해 - 마법력 비례)
    run_ransomware = Skill("hacker_run_ransomware", "랜섬웨어 실행", "적 전체 매 턴 마법력 35% HP 피해 프로그램")
    run_ransomware.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_ransomware", 1, max_value=1),
        BuffEffect(BuffType.CUSTOM, 0, duration=99, custom_stat="hp_drain_magic")  # DoT 효과 (마법력 비례)
    ]
    run_ransomware.costs = []  # MP 소모 0으로 변경
    run_ransomware.target_type = "all_enemies"
    run_ransomware.is_aoe = True
    run_ransomware.sfx = ("skill", "computer")  # 랜섬웨어 실행
    # run_ransomware.cooldown = 4  # 쿨다운 시스템 제거됨
    run_ransomware.metadata = {
        "program_type": "ransomware",
        "debuff": "hp_drain",
        "dot": True,
        "magic_percentage": 0.35  # 마법력의 35%만큼 매 턴 HP 감소
    }

    # 7. 스파이웨어 실행 (적 전체 명중률 감소)
    run_spyware = Skill("hacker_run_spyware", "스파이웨어 실행", "적 전체 명중률 -25% 프로그램")
    run_spyware.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_spyware", 1, max_value=1),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.25, duration=99)  # 적 명중률 -25%
    ]
    run_spyware.costs = []  # MP 소모 0으로 변경
    run_spyware.target_type = "all_enemies"
    run_spyware.is_aoe = True
    run_spyware.sfx = ("skill", "save")  # 스파이웨어 실행
    # run_spyware.cooldown = 2  # 쿨다운 시스템 제거됨
    run_spyware.metadata = {"program_type": "spyware", "info_gathering": True}

    # 8. 프로그램 종료 (모든 프로그램 종료하여 강력한 공격)
    terminate_all = Skill("hacker_terminate_all", "프로그램 종료", "모든 프로그램 종료하여 강력한 공격")
    terminate_all.effects = [
        # 실행 중인 프로그램 수에 비례한 공격 (피해량 감소: 2.5 -> 1.8, multiplier: 0.6 -> 0.4)
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magical",
                    gimmick_bonus={"field": "total_programs", "multiplier": 0.4}),
        # 모든 프로그램 종료
        GimmickEffect(GimmickOperation.SET, "program_virus", 0),
        GimmickEffect(GimmickOperation.SET, "program_backdoor", 0),
        GimmickEffect(GimmickOperation.SET, "program_ddos", 0),
        GimmickEffect(GimmickOperation.SET, "program_ransomware", 0),
        GimmickEffect(GimmickOperation.SET, "program_spyware", 0)
    ]
    terminate_all.costs = [MPCost(2)]  # MP 소모량 15 -> 5로 감소
    terminate_all.sfx = ("skill", "laser")  # 프로그램 종료
    # terminate_all.cooldown = 5  # 쿨다운 시스템 제거됨
    terminate_all.metadata = {"terminate_all": True}

    # 9. 시스템 과부하 (프로그램 유지하면서 강력한 공격)
    system_overload = Skill("hacker_system_overload", "시스템 과부하", "프로그램 수에 비례한 강력한 공격")
    system_overload.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="magical",
                    gimmick_bonus={"field": "total_programs", "multiplier": 0.5})
    ]
    system_overload.costs = [MPCost(7)]
    system_overload.sfx = ("skill", "machine")  # 시스템 과부하
    # system_overload.cooldown = 4  # 쿨다운 시스템 제거됨
    system_overload.metadata = {"program_scaling": True}

    # 10. 궁극기: 멀티스레드 폭주 (모든 프로그램 즉시 실행 + 극대 공격)
    ultimate = Skill("hacker_ultimate", "멀티스레드 폭주", "적 전체에 모든 프로그램 즉시 실행 + 극대 공격")
    ultimate.effects = [
        # 모든 프로그램 즉시 실행
        GimmickEffect(GimmickOperation.SET, "program_virus", 1),
        GimmickEffect(GimmickOperation.SET, "program_backdoor", 1),
        GimmickEffect(GimmickOperation.SET, "program_ddos", 1),
        # 극대 공격
        DamageEffect(DamageType.BRV, 4.0, stat_type="magical"),
        DamageEffect(DamageType.HP, 4.5, stat_type="magical"),
        # 모든 디버프 적용
        BuffEffect(BuffType.ATTACK_DOWN, 0.15, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.2, duration=5),
        BuffEffect(BuffType.SPEED_DOWN, 0.35, duration=5),
        # 자신 버프
        BuffEffect(BuffType.MAGIC_UP, 0.8, duration=4)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.target_type = "all_enemies"
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "multithread_rampage": True}

    return [code_injection, data_breach, run_virus, run_backdoor, run_ddos,
            run_ransomware, run_spyware, terminate_all, system_overload, ultimate]

def register_hacker_skills(skill_manager):
    """해커 스킬 등록"""
    skills = create_hacker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 시스템 오버라이드
    teamwork = TeamworkSkill(
        "hacker_teamwork",
        "시스템 오버라이드",
        "적 전체 버프 제거 + 디버프 1개씩 부여 + 본인 프로그램 3개 즉시 실행",
        gauge_cost=225
    )
    teamwork.effects = [
        # 적 전체 버프 제거 (메타데이터로 처리 - 실제로는 BuffEffect로 구현하기 복잡)
        # 디버프 1개씩 부여 (공격력/방어력/속도 중 -30%, 3턴)
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=3, target="all_enemies"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=3, target="all_enemies"),
        BuffEffect(BuffType.SPEED_DOWN, 0.3, duration=3, target="all_enemies"),
        # 본인 프로그램 3개 즉시 실행 (MP 소모 없음) (메타데이터로 처리)
    ]
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True}
    skills.append(teamwork)
    return skills
