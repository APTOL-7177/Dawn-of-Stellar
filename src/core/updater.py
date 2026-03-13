"""
자동 업데이트 체커 - itch.io 배포용

게임 시작 시 백그라운드에서 최신 버전을 확인하고,
새 버전이 있으면 메인 메뉴에 알림을 표시합니다.
"""

import threading
import urllib.request
import json
import re
from typing import Optional, Tuple
from src.core.logger import get_logger

logger = get_logger("updater")

# itch.io 설정
ITCH_USER = "aptol"
ITCH_GAME = "dawn-of-stellar"
ITCH_PAGE_URL = f"https://{ITCH_USER}.itch.io/{ITCH_GAME}"

# 업데이트 체크 결과를 저장하는 전역 상태
_update_info = {
    "checked": False,
    "available": False,
    "latest_version": None,
    "current_version": None,
    "error": None,
}


def parse_version(version_str: str) -> Tuple[int, ...]:
    """버전 문자열을 비교 가능한 튜플로 변환 (예: '6.1.0' -> (6, 1, 0))"""
    try:
        parts = re.findall(r'\d+', version_str)
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0,)


def _check_update_thread(current_version: str) -> None:
    """백그라운드 스레드에서 업데이트 확인"""
    global _update_info

    try:
        # itch.io 페이지에서 버전 정보를 가져오는 방법:
        # butler로 푸시할 때 --userversion을 사용하면
        # itch.io API로 확인 가능
        url = f"https://itch.io/api/1/x/wharf/latest?target={ITCH_USER}/{ITCH_GAME}&channel_name=windows"

        req = urllib.request.Request(url, headers={
            "User-Agent": f"DawnOfStellar/{current_version}"
        })

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            latest = data.get("latest", "")

            if latest and parse_version(latest) > parse_version(current_version):
                _update_info["available"] = True
                _update_info["latest_version"] = latest
                logger.info(f"새 버전 발견: {latest} (현재: {current_version})")
            else:
                logger.info(f"최신 버전 사용 중: {current_version}")

    except Exception as e:
        # 네트워크 오류 등은 조용히 무시 (오프라인 플레이 지원)
        _update_info["error"] = str(e)
        logger.debug(f"업데이트 확인 실패 (무시): {e}")

    _update_info["checked"] = True
    _update_info["current_version"] = current_version


def check_for_updates(current_version: str) -> None:
    """비동기로 업데이트 확인 시작 (메인 스레드 블로킹 없음)"""
    _update_info["current_version"] = current_version

    thread = threading.Thread(
        target=_check_update_thread,
        args=(current_version,),
        daemon=True
    )
    thread.start()


def get_update_status() -> dict:
    """현재 업데이트 확인 상태 반환"""
    return _update_info.copy()


def is_update_available() -> bool:
    """새 버전이 있는지 확인"""
    return _update_info["available"]


def get_update_message() -> Optional[str]:
    """업데이트 알림 메시지 반환 (없으면 None)"""
    if _update_info["available"] and _update_info["latest_version"]:
        return f"새 버전 {_update_info['latest_version']} 출시! {ITCH_PAGE_URL}"
    return None
