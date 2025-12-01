"""
보스 전투 타이머 시스템

7분 30초 타임어택 메커니즘
"""

import time
from typing import Optional, Callable
from src.core.logger import get_logger


logger = get_logger("boss_timer")


class BossTimerSystem:
    """
    보스 전투 타이머

    특정 보스(세피로스 등)와의 전투에서 시간 제한 적용
    """

    def __init__(self):
        self.is_active: bool = False
        self.time_limit: float = 0.0  # 제한 시간 (초)
        self.start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.total_paused_duration: float = 0.0

        # 콜백
        self.on_timeout: Optional[Callable[[], None]] = None
        self.on_warning: Optional[Callable[[int], None]] = None  # 경고 (남은 초)

        # 경고 설정 (1분, 30초, 10초 남았을 때)
        self.warning_thresholds = [60, 30, 10]
        self.warnings_triggered = set()

    def start_timer(self, time_limit: float, on_timeout: Optional[Callable[[], None]] = None):
        """
        타이머 시작

        Args:
            time_limit: 제한 시간 (초)
            on_timeout: 타임아웃 콜백
        """
        self.is_active = True
        self.time_limit = time_limit
        self.start_time = time.time()
        self.pause_time = None
        self.total_paused_duration = 0.0
        self.on_timeout = on_timeout
        self.warnings_triggered.clear()

        logger.info(f"보스 타이머 시작: {time_limit}초 제한")

    def pause_timer(self):
        """타이머 일시정지 (메뉴 등)"""
        if self.is_active and self.pause_time is None:
            self.pause_time = time.time()
            logger.debug("타이머 일시정지")

    def resume_timer(self):
        """타이머 재개"""
        if self.is_active and self.pause_time is not None:
            paused_duration = time.time() - self.pause_time
            self.total_paused_duration += paused_duration
            self.pause_time = None
            logger.debug(f"타이머 재개 (일시정지 시간: {paused_duration:.2f}초)")

    def stop_timer(self):
        """타이머 중지"""
        self.is_active = False
        self.start_time = None
        self.pause_time = None
        logger.info("보스 타이머 중지")

    def get_elapsed_time(self) -> float:
        """
        경과 시간 (초)

        Returns:
            경과 시간 (일시정지 시간 제외)
        """
        if not self.is_active or self.start_time is None:
            return 0.0

        current_time = time.time()

        # 일시정지 중이면 일시정지 시점까지만 계산
        if self.pause_time is not None:
            elapsed = self.pause_time - self.start_time - self.total_paused_duration
        else:
            elapsed = current_time - self.start_time - self.total_paused_duration

        return max(0.0, elapsed)

    def get_remaining_time(self) -> float:
        """
        남은 시간 (초)

        Returns:
            남은 시간
        """
        if not self.is_active:
            return 0.0

        remaining = self.time_limit - self.get_elapsed_time()
        return max(0.0, remaining)

    def is_timeout(self) -> bool:
        """
        타임아웃 여부

        Returns:
            타임아웃 여부
        """
        if not self.is_active:
            return False

        return self.get_remaining_time() <= 0.0

    def check_timeout(self) -> bool:
        """
        타임아웃 체크 및 콜백 실행

        Returns:
            타임아웃 여부
        """
        if self.is_timeout():
            logger.warning("보스 전투 타임아웃!")
            if self.on_timeout:
                self.on_timeout()
            self.stop_timer()
            return True

        # 경고 체크
        remaining = self.get_remaining_time()
        for threshold in self.warning_thresholds:
            if threshold not in self.warnings_triggered and remaining <= threshold:
                self.warnings_triggered.add(threshold)
                logger.warning(f"보스 타이머 경고: {threshold}초 남음")
                if self.on_warning:
                    self.on_warning(threshold)

        return False

    def format_time(self, seconds: float) -> str:
        """
        시간 포맷 (MM:SS)

        Args:
            seconds: 초

        Returns:
            포맷된 시간 문자열
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def get_remaining_time_display(self) -> str:
        """
        남은 시간 표시용 문자열

        Returns:
            "MM:SS" 형식
        """
        return self.format_time(self.get_remaining_time())

    def get_elapsed_time_display(self) -> str:
        """
        경과 시간 표시용 문자열

        Returns:
            "MM:SS" 형식
        """
        return self.format_time(self.get_elapsed_time())


# 전역 타이머 시스템 싱글톤
_boss_timer_system: Optional[BossTimerSystem] = None


def get_boss_timer_system() -> BossTimerSystem:
    """보스 타이머 시스템 싱글톤 가져오기"""
    global _boss_timer_system
    if _boss_timer_system is None:
        _boss_timer_system = BossTimerSystem()
    return _boss_timer_system
