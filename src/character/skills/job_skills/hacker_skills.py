"""Hacker Skills - 해커 스킬 (멀티스레드 시스템)"""
from src.character.skills.skill import Skill
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
    code_injection.sfx = "332"  # FFVII tech sound
    code_injection.metadata = {}

    # 2. 기본 HP: 데이터 유출
    data_breach = Skill("hacker_data_breach", "데이터 유출", "정보 탈취 HP 공격")
    data_breach.effects = [
        DamageEffect(DamageType.HP, 1.2, stat_type="magical")
    ]
    data_breach.costs = []  # 기본 공격은 MP 소모 없음
    data_breach.sfx = "338"  # FFVII data sound
    data_breach.metadata = {}

    # 3. 바이러스 실행 (적 공격력 -20%)
    run_virus = Skill("hacker_run_virus", "바이러스 실행", "적 공격력 -20% 프로그램 실행")
    run_virus.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_virus", 1, max_value=1),  # 프로그램 실행 (on/off)
        BuffEffect(BuffType.ATTACK_DOWN, 0.2, duration=99)  # 프로그램 실행 동안 지속
    ]
    run_virus.costs = [MPCost(10)]
    run_virus.target_type = "single"
    run_virus.sfx = "344"  # FFVII virus sound
    # run_virus.cooldown = 2  # 쿨다운 시스템 제거됨
    run_virus.metadata = {"program_type": "virus", "debuff": "attack_down"}

    # 4. 백도어 실행 (적 방어력 -30%)
    run_backdoor = Skill("hacker_run_backdoor", "백도어 실행", "적 방어력 -30% 프로그램 실행")
    run_backdoor.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_backdoor", 1, max_value=1),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=99)
    ]
    run_backdoor.costs = [MPCost(12)]
    run_backdoor.target_type = "single"
    run_backdoor.sfx = "352"  # FFVII backdoor sound
    # run_backdoor.cooldown = 2  # 쿨다운 시스템 제거됨
    run_backdoor.metadata = {"program_type": "backdoor", "debuff": "defense_down"}

    # 5. DDoS 실행 (적 속도 -50%)
    run_ddos = Skill("hacker_run_ddos", "DDoS 실행", "적 속도 -50% 프로그램 실행")
    run_ddos.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_ddos", 1, max_value=1),
        BuffEffect(BuffType.SPEED_DOWN, 0.5, duration=99)
    ]
    run_ddos.costs = [MPCost(15)]
    run_ddos.target_type = "single"
    run_ddos.sfx = "362"  # FFVII ddos sound
    # run_ddos.cooldown = 3  # 쿨다운 시스템 제거됨
    run_ddos.metadata = {"program_type": "ddos", "debuff": "speed_down"}

    # 6. 랜섬웨어 실행 (적 스킬 봉인)
    run_ransomware = Skill("hacker_run_ransomware", "랜섬웨어 실행", "적 스킬 봉인 프로그램 실행")
    run_ransomware.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_ransomware", 1, max_value=1),
        BuffEffect(BuffType.SKILL_SEAL, 1.0, duration=99)  # 스킬 봉인
    ]
    run_ransomware.costs = [MPCost(18)]
    run_ransomware.target_type = "single"
    run_ransomware.sfx = "376"  # FFVII lock sound
    # run_ransomware.cooldown = 4  # 쿨다운 시스템 제거됨
    run_ransomware.metadata = {"program_type": "ransomware", "debuff": "skill_seal"}

    # 7. 스파이웨어 실행 (적 정보 획득 + 회피율 감소)
    run_spyware = Skill("hacker_run_spyware", "스파이웨어 실행", "적 정보 획득 프로그램")
    run_spyware.effects = [
        GimmickEffect(GimmickOperation.ADD, "program_spyware", 1, max_value=1),
        BuffEffect(BuffType.EVASION_DOWN, 0.3, duration=99),
        BuffEffect(BuffType.ACCURACY_UP, 0.3, duration=99)
    ]
    run_spyware.costs = [MPCost(8)]
    run_spyware.target_type = "single"
    run_spyware.sfx = "404"  # FFVII scan sound
    # run_spyware.cooldown = 2  # 쿨다운 시스템 제거됨
    run_spyware.metadata = {"program_type": "spyware", "info_gathering": True}

    # 8. 프로그램 종료 (모든 프로그램 종료하여 강력한 공격)
    terminate_all = Skill("hacker_terminate_all", "프로그램 종료", "모든 프로그램 종료하여 강력한 공격")
    terminate_all.effects = [
        # 실행 중인 프로그램 수에 비례한 공격
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magical",
                    gimmick_bonus={"field": "total_programs", "multiplier": 0.6}),
        # 모든 프로그램 종료
        GimmickEffect(GimmickOperation.SET, "program_virus", 0),
        GimmickEffect(GimmickOperation.SET, "program_backdoor", 0),
        GimmickEffect(GimmickOperation.SET, "program_ddos", 0),
        GimmickEffect(GimmickOperation.SET, "program_ransomware", 0),
        GimmickEffect(GimmickOperation.SET, "program_spyware", 0)
    ]
    terminate_all.costs = [MPCost(20)]
    terminate_all.sfx = "423"  # FFVII shutdown sound
    # terminate_all.cooldown = 5  # 쿨다운 시스템 제거됨
    terminate_all.metadata = {"terminate_all": True}

    # 9. 시스템 과부하 (프로그램 유지하면서 강력한 공격)
    system_overload = Skill("hacker_system_overload", "시스템 과부하", "프로그램 수에 비례한 강력한 공격")
    system_overload.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="magical",
                    gimmick_bonus={"field": "total_programs", "multiplier": 0.5})
    ]
    system_overload.costs = [MPCost(22)]
    system_overload.sfx = "438"  # FFVII overload sound
    # system_overload.cooldown = 4  # 쿨다운 시스템 제거됨
    system_overload.metadata = {"program_scaling": True}

    # 10. 궁극기: 멀티스레드 폭주 (모든 프로그램 즉시 실행 + 극대 공격)
    ultimate = Skill("hacker_ultimate", "멀티스레드 폭주", "모든 프로그램 즉시 실행 + 극대 공격")
    ultimate.effects = [
        # 모든 프로그램 즉시 실행
        GimmickEffect(GimmickOperation.SET, "program_virus", 1),
        GimmickEffect(GimmickOperation.SET, "program_backdoor", 1),
        GimmickEffect(GimmickOperation.SET, "program_ddos", 1),
        # 극대 공격
        DamageEffect(DamageType.BRV, 4.0, stat_type="magical"),
        DamageEffect(DamageType.HP, 4.5, stat_type="magical"),
        # 모든 디버프 적용
        BuffEffect(BuffType.ATTACK_DOWN, 0.2, duration=5),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=5),
        BuffEffect(BuffType.SPEED_DOWN, 0.5, duration=5),
        # 자신 버프
        BuffEffect(BuffType.MAGIC_UP, 0.8, duration=4)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.sfx = "696"  # FFVII ultimate tech sound
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.metadata = {"ultimate": True, "multithread_rampage": True}

    return [code_injection, data_breach, run_virus, run_backdoor, run_ddos,
            run_ransomware, run_spyware, terminate_all, system_overload, ultimate]

def register_hacker_skills(skill_manager):
    """해커 스킬 등록"""
    skills = create_hacker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
