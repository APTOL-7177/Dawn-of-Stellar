"""
캐릭터 데이터 로더 - YAML 기반

YAML 파일에서 28개 직업의 스탯과 기믹 정보를 로드합니다.
"""
import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from src.core.logger import get_logger

logger = get_logger("character_loader")

# 캐릭터 데이터 디렉토리
CHARACTER_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "characters"

# 한글 직업명 → 영문 파일명 매핑
CLASS_FILE_MAP = {
    "전사": "warrior",
    "아크메이지": "archmage",
    "궁수": "archer",
    "도적": "rogue",
    "성기사": "paladin",
    "암흑기사": "dark_knight",
    "몽크": "monk",
    "바드": "bard",
    "네크로맨서": "necromancer",
    "용기사": "dragon_knight",
    "검성": "sword_saint",
    "정령술사": "elementalist",
    "암살자": "assassin",
    "기계공학자": "engineer",
    "무당": "shaman",
    "해적": "pirate",
    "사무라이": "samurai",
    "드루이드": "druid",
    "철학자": "philosopher",
    "시간술사": "time_mage",
    "연금술사": "alchemist",
    "검투사": "gladiator",
    "기사": "knight",
    "신관": "priest",
    "마검사": "spellblade",
    "차원술사": "dimensionist",
    "광전사": "berserker",
    "마법사": "mage",
}

# 캐시 (한 번만 로드)
_character_data_cache: Dict[str, Dict[str, Any]] = {}


def load_character_data(class_name: str) -> Optional[Dict[str, Any]]:
    """
    캐릭터 클래스 데이터를 YAML에서 로드합니다.

    Args:
        class_name: 한글 직업명 또는 영문 job_id (예: "전사", "warrior", "assassin")

    Returns:
        캐릭터 데이터 딕셔너리 또는 None (실패 시)
    """
    # 캐시 확인
    if class_name in _character_data_cache:
        return _character_data_cache[class_name]

    # 파일명 가져오기
    # 1. 한글이면 매핑 테이블에서 찾기
    file_name = CLASS_FILE_MAP.get(class_name)

    # 2. 매핑이 없으면 영문 job_id로 간주하고 직접 사용
    if not file_name:
        file_name = class_name

    # 파일 경로
    file_path = CHARACTER_DATA_DIR / f"{file_name}.yaml"

    if not file_path.exists():
        logger.warning(f"캐릭터 데이터 파일 없음: {file_path}")
        return None

    try:
        # YAML 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 캐시에 저장
        _character_data_cache[class_name] = data

        logger.debug(f"캐릭터 데이터 로드 완료: {class_name}")
        return data

    except Exception as e:
        logger.error(f"캐릭터 데이터 로드 실패 ({class_name}): {e}")
        return None


def get_base_stats(class_name: str) -> Dict[str, int]:
    """
    직업의 기본 스탯을 가져옵니다.

    Args:
        class_name: 한글 직업명

    Returns:
        기본 스탯 딕셔너리 (hp, mp, physical_attack, etc.)
    """
    data = load_character_data(class_name)
    if not data or 'base_stats' not in data:
        logger.warning(f"{class_name} 기본 스탯 없음. 기본값 반환")
        return {
            "hp": 100,
            "mp": 50,
            "init_brv": 1000,
            "physical_attack": 50,
            "physical_defense": 50,
            "magic_attack": 50,
            "magic_defense": 50,
            "speed": 50
        }

    return data['base_stats']


def get_gimmick(class_name: str) -> Optional[Dict[str, Any]]:
    """
    직업의 기믹 시스템 정보를 가져옵니다.

    Args:
        class_name: 한글 직업명

    Returns:
        기믹 데이터 딕셔너리 또는 None
    """
    data = load_character_data(class_name)
    if not data or 'gimmick' not in data:
        return None

    return data['gimmick']


def get_traits(class_name: str) -> list:
    """
    직업의 고유 특성 목록을 가져옵니다.

    Args:
        class_name: 한글 직업명

    Returns:
        특성 리스트
    """
    data = load_character_data(class_name)
    if not data or 'traits' not in data:
        return []

    return data['traits']


def get_skills(class_name: str) -> list:
    """
    직업의 스킬 목록을 가져옵니다.

    Args:
        class_name: 한글 직업명

    Returns:
        스킬 ID 리스트
    """
    data = load_character_data(class_name)
    if not data or 'skills' not in data:
        return []

    return data['skills']


def get_bonuses(class_name: str) -> Dict[str, Any]:
    """
    직업의 클래스 보너스를 가져옵니다.

    Args:
        class_name: 한글 직업명

    Returns:
        보너스 딕셔너리
    """
    data = load_character_data(class_name)
    if not data or 'bonuses' not in data:
        return {}

    return data['bonuses']


def get_all_classes() -> list:
    """
    사용 가능한 모든 직업 목록을 반환합니다.

    Returns:
        한글 직업명 리스트
    """
    return list(CLASS_FILE_MAP.keys())


def reload_data():
    """캐시를 지우고 데이터를 다시 로드합니다."""
    global _character_data_cache
    _character_data_cache.clear()
    logger.info("캐릭터 데이터 캐시 초기화")


# 모듈 로드 시 데이터 유효성 검사 (선택 사항)
def validate_all_data():
    """모든 캐릭터 데이터가 로드 가능한지 검증합니다."""
    logger.info("캐릭터 데이터 검증 시작...")
    success_count = 0
    fail_count = 0

    for class_name in get_all_classes():
        data = load_character_data(class_name)
        if data:
            success_count += 1
        else:
            fail_count += 1
            logger.error(f"검증 실패: {class_name}")

    logger.info(f"캐릭터 데이터 검증 완료: 성공 {success_count}, 실패 {fail_count}")
    return fail_count == 0
