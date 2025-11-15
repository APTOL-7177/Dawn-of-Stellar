"""
Logger - 로깅 시스템

구조화된 로깅을 위한 로거 클래스
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class Logger:
    """
    게임 로거 클래스

    카테고리별 로그 파일 및 콘솔 출력 지원
    """

    def __init__(self, name: str, log_dir: str = "logs") -> None:
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 세션 시작 시간
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")

        # 로거 생성
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 핸들러가 이미 있으면 제거 (중복 방지)
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "[%(levelname)s] %(name)s: %(message)s"
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # 파일 핸들러
        log_file = self.log_dir / f"{name}_{self.session_id}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """디버그 로그"""
        if extra:
            message = f"{message} | {extra}"
        self.logger.debug(message)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """정보 로그"""
        if extra:
            message = f"{message} | {extra}"
        self.logger.info(message)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """경고 로그"""
        if extra:
            message = f"{message} | {extra}"
        self.logger.warning(message)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """에러 로그"""
        if extra:
            message = f"{message} | {extra}"
        self.logger.error(message)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """치명적 에러 로그"""
        if extra:
            message = f"{message} | {extra}"
        self.logger.critical(message)


# 전역 로거 저장소
_loggers: Dict[str, Logger] = {}


def get_logger(name: str) -> Logger:
    """
    로거 가져오기 (없으면 생성)

    Args:
        name: 로거 이름 (예: "combat", "player", "enemy")

    Returns:
        Logger 인스턴스
    """
    if name not in _loggers:
        _loggers[name] = Logger(name)
    return _loggers[name]


# 카테고리별 로거 상수
class Loggers:
    """로거 카테고리"""
    SYSTEM = "system"
    COMBAT = "combat"
    PLAYER = "player"
    ENEMY = "enemy"
    WORLD = "world"
    AI = "ai"
    EQUIPMENT = "equipment"
    AUDIO = "audio"
    SAVE = "save"
    DEBUG = "debug"
    UI = "ui"
