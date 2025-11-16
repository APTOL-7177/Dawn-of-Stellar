"""
난이도 시스템

게임 난이도에 따른 배율 관리
- 적 HP/공격력 조정
- 플레이어 데미지 조정
- 경험치/드랍률 조정
"""

from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass

from src.core.config import Config


class DifficultyLevel(Enum):
    """난이도 레벨"""
    PEACEFUL = "평온"
    NORMAL = "보통"
    CHALLENGE = "도전"
    NIGHTMARE = "악몽"
    HELL = "지옥"


@dataclass
class DifficultyModifiers:
    """난이도 배율"""
    enemy_hp_multiplier: float
    enemy_damage_multiplier: float
    player_damage_multiplier: float
    exp_multiplier: float
    drop_rate_multiplier: float

    name: str = ""
    description: str = ""


class DifficultySystem:
    """난이도 시스템"""

    def __init__(self, config: Config):
        self.config = config
        self.current_difficulty = DifficultyLevel.NORMAL
        self._load_difficulty_data()

    def _load_difficulty_data(self):
        """config.yaml에서 난이도 데이터 로드"""
        self.difficulty_data: Dict[DifficultyLevel, DifficultyModifiers] = {}

        difficulty_config = self.config.get("difficulty.levels", {})

        # 각 난이도별 데이터 로드
        for level in DifficultyLevel:
            level_data = difficulty_config.get(level.value, {})

            self.difficulty_data[level] = DifficultyModifiers(
                enemy_hp_multiplier=level_data.get("enemy_hp_multiplier", 1.0),
                enemy_damage_multiplier=level_data.get("enemy_damage_multiplier", 1.0),
                player_damage_multiplier=level_data.get("player_damage_multiplier", 1.0),
                exp_multiplier=level_data.get("exp_multiplier", 1.0),
                drop_rate_multiplier=level_data.get("drop_rate_multiplier", 1.0),
                name=level_data.get("name", level.value),
                description=level_data.get("description", "")
            )

    def set_difficulty(self, difficulty: DifficultyLevel):
        """난이도 설정"""
        self.current_difficulty = difficulty

    def get_modifiers(self) -> DifficultyModifiers:
        """현재 난이도의 배율 반환"""
        return self.difficulty_data[self.current_difficulty]

    def get_enemy_hp_multiplier(self) -> float:
        """적 HP 배율"""
        return self.difficulty_data[self.current_difficulty].enemy_hp_multiplier

    def get_enemy_damage_multiplier(self) -> float:
        """적 공격력 배율"""
        return self.difficulty_data[self.current_difficulty].enemy_damage_multiplier

    def get_player_damage_multiplier(self) -> float:
        """플레이어 데미지 배율"""
        return self.difficulty_data[self.current_difficulty].player_damage_multiplier

    def get_exp_multiplier(self) -> float:
        """경험치 배율"""
        return self.difficulty_data[self.current_difficulty].exp_multiplier

    def get_drop_rate_multiplier(self) -> float:
        """드랍률 배율"""
        return self.difficulty_data[self.current_difficulty].drop_rate_multiplier

    def get_difficulty_info(self, difficulty: DifficultyLevel) -> Dict[str, Any]:
        """난이도 정보 반환 (UI 표시용)"""
        modifiers = self.difficulty_data[difficulty]

        return {
            "level": difficulty.value,
            "name": modifiers.name,
            "description": modifiers.description,
            "modifiers": {
                "적 체력": f"{int(modifiers.enemy_hp_multiplier * 100)}%",
                "적 공격력": f"{int(modifiers.enemy_damage_multiplier * 100)}%",
                "플레이어 데미지": f"{int(modifiers.player_damage_multiplier * 100)}%",
                "경험치": f"{int(modifiers.exp_multiplier * 100)}%",
                "드랍률": f"{int(modifiers.drop_rate_multiplier * 100)}%"
            }
        }

    def get_all_difficulties_info(self) -> list:
        """모든 난이도 정보 반환"""
        return [self.get_difficulty_info(level) for level in DifficultyLevel]

    def to_dict(self) -> Dict[str, Any]:
        """저장용 딕셔너리 변환"""
        return {
            "difficulty": self.current_difficulty.value
        }

    @classmethod
    def from_dict(cls, config: Config, data: Dict[str, Any]) -> 'DifficultySystem':
        """저장 데이터에서 복원"""
        system = cls(config)

        difficulty_str = data.get("difficulty", "보통")

        # 문자열을 DifficultyLevel로 변환
        for level in DifficultyLevel:
            if level.value == difficulty_str:
                system.current_difficulty = level
                break

        return system


# 전역 인스턴스 (게임 세션별로 생성)
_difficulty_system = None


def get_difficulty_system(config: Config = None) -> DifficultySystem:
    """난이도 시스템 전역 인스턴스 반환"""
    global _difficulty_system

    if _difficulty_system is None and config is not None:
        _difficulty_system = DifficultySystem(config)

    return _difficulty_system


def set_difficulty_system(system: DifficultySystem):
    """난이도 시스템 전역 인스턴스 설정"""
    global _difficulty_system
    _difficulty_system = system


def reset_difficulty_system():
    """난이도 시스템 리셋"""
    global _difficulty_system
    _difficulty_system = None
