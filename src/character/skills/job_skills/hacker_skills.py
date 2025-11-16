"""Hacker Skills - 해커 스킬 (네트워크 접근 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_hacker_skills():
    """해커 10개 스킬 (네트워크 접근 시스템)"""
    skills = []

    # 1. 기본 BRV: 포트 스캔 (Port Scan)
    port_scan = Skill("hacker_port_scan", "포트 스캔", "네트워크 침투 시작")
    port_scan.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "access_level", 1, max_value=5)
    ]
    port_scan.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(port_scan)

    # 2. 기본 HP: 데이터 유출 (Data Breach)
    data_breach = Skill("hacker_data_breach", "데이터 유출", "정보 탈취 공격")
    data_breach.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "access_level", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "access_level", 1, max_value=5)
    ]
    data_breach.costs = []  # 기본 공격은 MP 소모 없음
    skills.append(data_breach)

    # 3. 방화벽 파괴 (Crack Firewall)
    crack_firewall = Skill("hacker_crack_firewall", "방화벽 파괴", "방어 체계 무력화")
    crack_firewall.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "access_level", 1, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "firewall_break_count", 1, max_value=999),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.25, duration=3)
    ]
    crack_firewall.costs = [MPCost(4)]
    crack_firewall.cooldown = 2
    skills.append(crack_firewall)

    # 4. DDoS 공격 (DDoS Attack)
    ddos_attack = Skill("hacker_ddos", "DDoS 공격", "연속 데이터 공격")
    ddos_attack.effects = [
        DamageEffect(DamageType.BRV, 1.2, gimmick_bonus={"field": "access_level", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.2, gimmick_bonus={"field": "access_level", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.2, gimmick_bonus={"field": "access_level", "multiplier": 0.25}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "access_level", "multiplier": 0.25}, stat_type="magical")
    ]
    ddos_attack.costs = [MPCost(8)]
    ddos_attack.cooldown = 3
    skills.append(ddos_attack)

    # 5. 루트 접근 (Root Access Hack)
    root_access_hack = Skill("hacker_root_access", "루트 접근", "최고 권한 획득")
    root_access_hack.effects = [
        GimmickEffect(GimmickOperation.ADD, "access_level", 2, max_value=5),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=4)
    ]
    root_access_hack.costs = [MPCost(10)]
    root_access_hack.target_type = "self"
    root_access_hack.cooldown = 4
    skills.append(root_access_hack)

    # 6. 바이러스 업로드 (Virus Upload)
    virus_upload = Skill("hacker_virus_upload", "바이러스 업로드", "악성 코드 감염")
    virus_upload.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "access_level", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.3, gimmick_bonus={"field": "access_level", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.1, gimmick_bonus={"field": "access_level", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 0.9, gimmick_bonus={"field": "access_level", "multiplier": 0.3}, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=4)
    ]
    virus_upload.costs = [MPCost(12)]
    virus_upload.cooldown = 4
    skills.append(virus_upload)

    # 7. 시스템 과부하 (System Overload)
    system_overload = Skill("hacker_system_overload", "시스템 과부하", "강제 다운")
    system_overload.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, gimmick_bonus={"field": "access_level", "multiplier": 0.4}, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "firewall_break_count", 1, max_value=999)
    ]
    system_overload.costs = [MPCost(15)]
    system_overload.cooldown = 4
    skills.append(system_overload)

    # 8. 백도어 설치 (Backdoor Install)
    backdoor_install = Skill("hacker_backdoor_install", "백도어 설치", "영구 접근 확보")
    backdoor_install.effects = [
        GimmickEffect(GimmickOperation.ADD, "access_level", 3, max_value=5),
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=5),
        BuffEffect(BuffType.EVASION_UP, 0.3, duration=5)
    ]
    backdoor_install.costs = [MPCost(18)]
    backdoor_install.target_type = "self"
    backdoor_install.cooldown = 6
    skills.append(backdoor_install)

    # 9. 네트워크 붕괴 (Network Collapse)
    network_collapse = Skill("hacker_network_collapse", "네트워크 붕괴", "완전한 파괴")
    network_collapse.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, gimmick_bonus={"field": "access_level", "multiplier": 0.6}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.0, gimmick_bonus={"field": "firewall_break_count", "multiplier": 0.15}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "access_level", 3),
        GimmickEffect(GimmickOperation.ADD, "firewall_break_count", 2, max_value=999)
    ]
    network_collapse.costs = [MPCost(22), StackCost("access_level", 3)]
    network_collapse.cooldown = 5
    skills.append(network_collapse)

    # 10. 궁극기: 제로데이 익스플로잇 (Zero-Day Exploit)
    zero_day_exploit = Skill("hacker_zero_day", "제로데이 익스플로잇", "완벽한 해킹")
    zero_day_exploit.effects = [
        DamageEffect(DamageType.BRV, 3.5, gimmick_bonus={"field": "access_level", "multiplier": 0.8}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "access_level", "multiplier": 0.7}, stat_type="magical"),
        DamageEffect(DamageType.HP, 4.5, gimmick_bonus={"field": "firewall_break_count", "multiplier": 0.3}, stat_type="magical"),
        BuffEffect(BuffType.MAGIC_UP, 0.8, duration=6),
        BuffEffect(BuffType.CRITICAL_UP, 0.6, duration=6),
        GimmickEffect(GimmickOperation.SET, "access_level", 5),
        GimmickEffect(GimmickOperation.ADD, "firewall_break_count", 5, max_value=999)
    ]
    zero_day_exploit.costs = [MPCost(30)]
    zero_day_exploit.is_ultimate = True
    zero_day_exploit.cooldown = 10
    skills.append(zero_day_exploit)

    return skills

def register_hacker_skills(skill_manager):
    skills = create_hacker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
