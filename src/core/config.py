"""
Config - 설정 관리 시스템

YAML 기반 설정 로딩 및 관리
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """
    설정 관리 클래스

    config.yaml 파일을 로드하고 게임 설정을 관리합니다.
    """

    def __init__(self, config_path: str = "config.yaml") -> None:
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """설정 파일 로드"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def save(self) -> None:
        """설정 파일 저장"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        설정 값 가져오기

        Args:
            key_path: 점으로 구분된 키 경로 (예: "combat.atb.max_gauge")
            default: 기본값

        Returns:
            설정 값
        """
        keys = key_path.split(".")
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        설정 값 설정

        Args:
            key_path: 점으로 구분된 키 경로
            value: 설정할 값
        """
        keys = key_path.split(".")
        config = self._config

        # 마지막 키 전까지 딕셔너리 탐색
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # 마지막 키에 값 설정
        config[keys[-1]] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        설정 섹션 전체 가져오기

        Args:
            section: 섹션 이름

        Returns:
            섹션 딕셔너리
        """
        return self.get(section, {})

    # 자주 사용하는 설정들을 프로퍼티로 제공

    @property
    def development_mode(self) -> bool:
        """개발 모드 활성화 여부"""
        return self.get("development.enabled", False)

    @property
    def debug_mode(self) -> bool:
        """디버그 모드 활성화 여부"""
        return self.get("development.debug_mode", False)

    @property
    def window_width(self) -> int:
        """윈도우 너비"""
        return self.get("display.window_width", 1280)

    @property
    def window_height(self) -> int:
        """윈도우 높이"""
        return self.get("display.window_height", 720)

    @property
    def fps_limit(self) -> int:
        """FPS 제한"""
        return self.get("display.fps_limit", 120)

    @property
    def atb_enabled(self) -> bool:
        """ATB 시스템 활성화 여부"""
        return self.get("combat.atb.enabled", True)

    @property
    def atb_max_gauge(self) -> int:
        """ATB 최대 게이지"""
        return self.get("combat.atb.max_gauge", 2000)

    @property
    def difficulty(self) -> str:
        """현재 난이도"""
        return self.get("difficulty.default", "보통")

    @property
    def master_volume(self) -> float:
        """마스터 볼륨"""
        return self.get("audio.master_volume", 0.8)

    @property
    def bgm_volume(self) -> float:
        """BGM 볼륨"""
        return self.get("audio.bgm_volume", 0.6)

    @property
    def sfx_volume(self) -> float:
        """SFX 볼륨"""
        return self.get("audio.sfx_volume", 0.7)

    @property
    def auto_save_enabled(self) -> bool:
        """자동 저장 활성화 여부"""
        return self.get("save.auto_save_enabled", True)

    @property
    def language(self) -> str:
        """언어 설정"""
        return self.get("game.language", "ko")


# 전역 설정 인스턴스
config: Optional[Config] = None


def initialize_config(config_path: str = "config.yaml") -> Config:
    """
    설정 초기화

    Args:
        config_path: 설정 파일 경로

    Returns:
        Config 인스턴스
    """
    global config
    config = Config(config_path)
    return config


def get_config() -> Config:
    """
    전역 설정 인스턴스 가져오기

    Returns:
        Config 인스턴스
    """
    if config is None:
        raise RuntimeError("설정이 초기화되지 않았습니다. initialize_config()를 먼저 호출하세요.")
    return config
