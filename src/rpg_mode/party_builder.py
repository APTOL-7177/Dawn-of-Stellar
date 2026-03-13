"""
RPG 모드 파티 자동 구성

주인공(크리스) + 동료 3명을 archetype 기반으로 자동 편성한다.
첫 번째 동료 '릴리'는 메인 히로인으로 고정.
"""

import random
from typing import List, Optional, Tuple

from src.character.character import Character
from src.character.character_loader import load_character_data
from src.core.logger import get_logger

logger = get_logger("rpg_party_builder")

# 메인 히로인 (고정 첫 번째 동료)
HEROINE_NAME = "릴리"
HEROINE_DEFAULT_JOB = "priest"  # 힐러 역할

# 나머지 동료 이름 풀 (스토리 NPC와 겹치지 않음)
COMPANION_NAMES = [
    "하루", "소라", "레온", "아이라", "노아",
    "루나", "카엘", "시온", "에밀",
]

# 직업 → 역할 매핑
ROLE_TANK = "tank"
ROLE_HEALER = "healer"
ROLE_PHYSICAL_DPS = "physical_dps"
ROLE_MAGIC_DPS = "magic_dps"

# archetype 키워드 → 역할 분류
_ARCHETYPE_ROLE_MAP = {
    # 탱커
    "탱커": ROLE_TANK,
    "지휘관": ROLE_TANK,
    "피해 지연 탱커": ROLE_TANK,
    # 힐러/서포터
    "힐러": ROLE_HEALER,
    "서포터": ROLE_HEALER,
    "포션 마스터": ROLE_HEALER,
    "버퍼": ROLE_HEALER,
    # 물리 딜러
    "물리 딜러": ROLE_PHYSICAL_DPS,
    "암살 특화": ROLE_PHYSICAL_DPS,
    "내공 전사": ROLE_PHYSICAL_DPS,
    "반격 전문가": ROLE_PHYSICAL_DPS,
    "하이리스크 하이리턴": ROLE_PHYSICAL_DPS,
    "SCATTER": ROLE_PHYSICAL_DPS,
    "연격 특화": ROLE_PHYSICAL_DPS,
    "화염 특화 딜러": ROLE_PHYSICAL_DPS,
    "원거리 물리 딜러": ROLE_PHYSICAL_DPS,
    # 마법 딜러
    "마법 딜러": ROLE_MAGIC_DPS,
    "원샷 딜러": ROLE_MAGIC_DPS,
    "하이브리드 딜러": ROLE_MAGIC_DPS,
    "트릭스터 유틸리티": ROLE_MAGIC_DPS,
    "디버프 특화": ROLE_MAGIC_DPS,
    "변신 술사": ROLE_MAGIC_DPS,
}

# 역할별 대표 직업 (job_id)
TANK_JOBS = ["paladin", "knight", "dimensionist", "illusionist"]
HEALER_JOBS = ["cleric", "priest", "druid", "bard", "alchemist"]
PHYSICAL_DPS_JOBS = [
    "warrior", "assassin", "samurai", "gladiator", "monk",
    "berserker", "breaker", "pirate", "rogue", "sniper",
    "archer", "dragon_knight", "sword_saint", "ninja",
]
MAGIC_DPS_JOBS = [
    "archmage", "elementalist", "battle_mage", "time_mage",
    "necromancer", "philosopher", "spellblade", "shaman",
    "engineer", "hacker", "magician", "dark_knight", "vampire",
]


def _classify_job_role(job_id: str) -> str:
    """직업의 archetype을 읽어 역할을 분류한다."""
    data = load_character_data(job_id)
    if data:
        archetype = data.get("archetype", "")
        # archetype 문자열에서 키워드 매칭
        for keyword, role in _ARCHETYPE_ROLE_MAP.items():
            if keyword in archetype:
                return role

    # 폴백: 하드코딩 목록
    if job_id in TANK_JOBS:
        return ROLE_TANK
    if job_id in HEALER_JOBS:
        return ROLE_HEALER
    if job_id in PHYSICAL_DPS_JOBS:
        return ROLE_PHYSICAL_DPS
    return ROLE_MAGIC_DPS


def build_rpg_party(protagonist_job: str, level: int = 1) -> List[Character]:
    """
    RPG 모드 파티를 자동 구성한다.

    첫 번째 동료는 메인 히로인 '릴리' (힐러 역할 고정).
    나머지 2명은 역할 밸런스에 맞춰 자동 편성.

    Args:
        protagonist_job: 크리스의 직업 (영문 job_id, 예: "warrior")
        level: 초기 레벨

    Returns:
        [크리스, 릴리, 동료2, 동료3] 리스트
    """
    # 1) 주인공 생성
    chris = Character(name="크리스", character_class=protagonist_job, level=level)
    chris_role = _classify_job_role(protagonist_job)
    logger.info(f"주인공 크리스: {protagonist_job} (역할: {chris_role})")

    # 2) 히로인 릴리 생성
    lily_job = HEROINE_DEFAULT_JOB
    # 크리스가 신관(priest)이면 릴리는 성직자(cleric)로 할당
    if protagonist_job == "priest":
        lily_job = "cleric"
    # 크리스가 성직자(cleric)면 릴리는 신관(priest) 유지 (기본값)
    elif protagonist_job == "cleric":
        lily_job = "priest"
    # 크리스가 다른 힐러 직업이면 릴리는 서포트 마법 딜러로
    elif chris_role == ROLE_HEALER:
        lily_job = "bard"  # 버퍼/서포터 겸 딜러
    lily = Character(name=HEROINE_NAME, character_class=lily_job, level=level)
    lily_role = _classify_job_role(lily_job)
    logger.info(f"히로인 릴리: {lily_job} (역할: {lily_role})")

    # 3) 나머지 2명의 역할 결정 (크리스 + 릴리 역할 고려)
    needed_roles = _determine_remaining_roles(chris_role, lily_role)

    # 4) 각 역할에 맞는 직업 선택 (중복 불가)
    used_jobs = {protagonist_job, lily_job}
    companion_jobs = []

    for role in needed_roles:
        job = _pick_job_for_role(role, used_jobs)
        companion_jobs.append(job)
        used_jobs.add(job)

    # 5) 나머지 동료 이름 랜덤 선택 (2명)
    names = random.sample(COMPANION_NAMES, 2)

    # 6) 파티 구성: 크리스 → 릴리 → 동료2 → 동료3
    party = [chris, lily]
    for name, job_id in zip(names, companion_jobs):
        companion = Character(name=name, character_class=job_id, level=level)
        logger.info(f"동료 {name}: {job_id}")
        party.append(companion)

    return party


def _determine_needed_roles(chris_role: str) -> List[str]:
    """
    크리스의 역할을 고려하여 동료 3명의 역할을 결정한다.

    기본 구성: 탱커1, 힐러1, 딜러2 (크리스 포함 4명)
    """
    # 기본 필요 역할
    base_roles = {
        ROLE_TANK: 1,
        ROLE_HEALER: 1,
    }
    # 딜러 슬롯 (물리/마법 혼합)
    dps_needed = 2

    # 크리스가 이미 채우는 역할 차감
    if chris_role == ROLE_TANK:
        base_roles[ROLE_TANK] -= 1
    elif chris_role == ROLE_HEALER:
        base_roles[ROLE_HEALER] -= 1
    else:
        # 크리스가 딜러면 딜러 1슬롯 차감
        dps_needed -= 1

    needed = []
    for role, count in base_roles.items():
        needed.extend([role] * count)

    # 남은 슬롯을 딜러로 채움
    remaining = 3 - len(needed)
    for _ in range(remaining):
        # 물리/마법 딜러를 번갈아 배치
        if chris_role == ROLE_PHYSICAL_DPS:
            needed.append(ROLE_MAGIC_DPS)
        elif chris_role == ROLE_MAGIC_DPS:
            needed.append(ROLE_PHYSICAL_DPS)
        else:
            needed.append(random.choice([ROLE_PHYSICAL_DPS, ROLE_MAGIC_DPS]))

    return needed


def _determine_remaining_roles(chris_role: str, lily_role: str) -> List[str]:
    """
    크리스 + 릴리의 역할을 고려하여 나머지 동료 2명의 역할을 결정한다.

    기본 구성: 탱커1, 힐러1, 딜러2 (4명 합산)
    """
    filled_roles = [chris_role, lily_role]

    has_tank = ROLE_TANK in filled_roles
    has_healer = ROLE_HEALER in filled_roles

    needed = []

    # 탱커가 없으면 반드시 추가
    if not has_tank:
        needed.append(ROLE_TANK)

    # 힐러가 없으면 반드시 추가
    if not has_healer:
        needed.append(ROLE_HEALER)

    # 남은 슬롯을 딜러로 채움
    remaining = 2 - len(needed)
    for _ in range(remaining):
        # 크리스 역할과 반대 타입의 딜러 배치
        if chris_role == ROLE_PHYSICAL_DPS:
            needed.append(ROLE_MAGIC_DPS)
        elif chris_role == ROLE_MAGIC_DPS:
            needed.append(ROLE_PHYSICAL_DPS)
        else:
            needed.append(random.choice([ROLE_PHYSICAL_DPS, ROLE_MAGIC_DPS]))

    return needed


def _pick_job_for_role(role: str, used_jobs: set) -> str:
    """역할에 맞는 직업을 하나 선택한다 (중복 제외)."""
    pool_map = {
        ROLE_TANK: TANK_JOBS,
        ROLE_HEALER: HEALER_JOBS,
        ROLE_PHYSICAL_DPS: PHYSICAL_DPS_JOBS,
        ROLE_MAGIC_DPS: MAGIC_DPS_JOBS,
    }
    pool = [j for j in pool_map.get(role, PHYSICAL_DPS_JOBS) if j not in used_jobs]

    if not pool:
        # 모든 직업 풀에서 미사용 직업 선택
        all_jobs = TANK_JOBS + HEALER_JOBS + PHYSICAL_DPS_JOBS + MAGIC_DPS_JOBS
        pool = [j for j in all_jobs if j not in used_jobs]

    return random.choice(pool)
