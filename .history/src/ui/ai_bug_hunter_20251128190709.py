"""
AI 버그 헌터 - AI 관전 모드를 사용한 자동 버그 탐지

싱글플레이의 AI 관전 모드가 곧 버그 헌터입니다.
ai_spectate_mode.py의 run_ai_spectate_mode를 호출합니다.
"""

import tcod.console
from typing import Optional, Dict, Any

from src.core.logger import get_logger


logger = get_logger("ai_bug_hunter")


def run_ai_bug_hunter(console: tcod.console.Console, context: tcod.context.Context) -> Optional[Dict[str, Any]]:
    """
    AI 버그 헌터 실행 (AI 관전 모드 래퍼)
    
    Returns:
        결과 딕셔너리
    """
    from src.ui.ai_spectate_mode import run_ai_spectate_mode, get_bug_count
    
    logger.info("AI 버그 헌터 시작 (AI 관전 모드 사용)")
    
    result = run_ai_spectate_mode(console, context)
    
    bugs_found = get_bug_count()
    logger.info(f"AI 버그 헌터 완료: {bugs_found}개 버그 발견")
    
    return {
        "success": result.get("success", False),
        "stats": result.get("stats", {}),
        "bugs_found": bugs_found
    }
