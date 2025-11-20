"""
멀티플레이 검증 유틸리티

입력 검증 및 데이터 무결성 체크를 담당합니다.
"""

from typing import Any, Optional, Dict
from src.core.logger import get_logger


logger = get_logger("multiplayer.validation")


def validate_player_id(player_id: Any) -> bool:
    """
    플레이어 ID 검증
    
    Args:
        player_id: 검증할 플레이어 ID
        
    Returns:
        유효 여부
    """
    if player_id is None:
        logger.warning("플레이어 ID가 None입니다")
        return False
    
    if not isinstance(player_id, str):
        logger.warning(f"플레이어 ID가 str 타입이 아닙니다: {type(player_id)}")
        return False
    
    if not player_id.strip():
        logger.warning("플레이어 ID가 비어있습니다")
        return False
    
    # UUID 형식 체크 (선택적)
    if len(player_id) > 100:
        logger.warning(f"플레이어 ID가 너무 깁니다: {len(player_id)}자")
        return False
    
    return True


def validate_player_name(player_name: Any) -> bool:
    """
    플레이어 이름 검증
    
    Args:
        player_name: 검증할 플레이어 이름
        
    Returns:
        유효 여부
    """
    if player_name is None:
        logger.warning("플레이어 이름이 None입니다")
        return False
    
    if not isinstance(player_name, str):
        logger.warning(f"플레이어 이름이 str 타입이 아닙니다: {type(player_name)}")
        return False
    
    if not player_name.strip():
        logger.warning("플레이어 이름이 비어있습니다")
        return False
    
    # 길이 제한
    if len(player_name) > 50:
        logger.warning(f"플레이어 이름이 너무 깁니다: {len(player_name)}자")
        return False
    
    return True


def validate_position(x: Any, y: Any) -> bool:
    """
    위치 좌표 검증
    
    Args:
        x: X 좌표
        y: Y 좌표
        
    Returns:
        유효 여부
    """
    if not isinstance(x, int) or not isinstance(y, int):
        logger.warning(f"위치 좌표가 int 타입이 아닙니다: x={type(x)}, y={type(y)}")
        return False
    
    # 합리적인 범위 체크 (음수도 가능하지만 극단적인 값은 차단)
    if abs(x) > 100000 or abs(y) > 100000:
        logger.warning(f"위치 좌표가 범위를 벗어났습니다: ({x}, {y})")
        return False
    
    return True


def validate_session_id(session_id: Any) -> bool:
    """
    세션 ID 검증
    
    Args:
        session_id: 검증할 세션 ID
        
    Returns:
        유효 여부
    """
    if session_id is None:
        logger.warning("세션 ID가 None입니다")
        return False
    
    if not isinstance(session_id, str):
        logger.warning(f"세션 ID가 str 타입이 아닙니다: {type(session_id)}")
        return False
    
    if not session_id.strip():
        logger.warning("세션 ID가 비어있습니다")
        return False
    
    return True


def validate_max_players(max_players: Any) -> bool:
    """
    최대 플레이어 수 검증
    
    Args:
        max_players: 검증할 최대 플레이어 수
        
    Returns:
        유효 여부
    """
    if not isinstance(max_players, int):
        logger.warning(f"최대 플레이어 수가 int 타입이 아닙니다: {type(max_players)}")
        return False
    
    if not (2 <= max_players <= 4):
        logger.warning(f"최대 플레이어 수가 범위를 벗어났습니다: {max_players} (2~4 사이여야 함)")
        return False
    
    return True


def sanitize_player_name(player_name: str) -> str:
    """
    플레이어 이름 정제 (악성 문자열 제거)
    
    Args:
        player_name: 정제할 플레이어 이름
        
    Returns:
        정제된 플레이어 이름
    """
    if not isinstance(player_name, str):
        return "Unknown"
    
    # 앞뒤 공백 제거
    sanitized = player_name.strip()
    
    # 길이 제한
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    
    # 빈 문자열 처리
    if not sanitized:
        sanitized = "Unknown"
    
    return sanitized

