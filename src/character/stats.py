"""
Stats - 확장 가능한 스탯 시스템

완전히 데이터 주도적이고 확장 가능한 스탯 관리
"""

from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import math


class GrowthType(Enum):
    """스탯 성장 타입"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    CUSTOM = "custom"


class Stat:
    """
    개별 스탯 클래스

    각 스탯은 기본값, 보너스, 성장 방식을 가집니다.
    """

    def __init__(
        self,
        name: str,
        base_value: float,
        growth_rate: float = 1.0,
        growth_type: GrowthType = GrowthType.LINEAR,
        min_value: float = 0,
        max_value: Optional[float] = None,
        custom_growth_func: Optional[Callable[[int, float], float]] = None
    ) -> None:
        self.name = name
        self._base_value = base_value
        self.growth_rate = growth_rate
        self.growth_type = growth_type
        self.min_value = min_value
        self.max_value = max_value
        self.custom_growth_func = custom_growth_func

        # 보너스 (장비, 버프 등)
        self._bonuses: Dict[str, float] = {}

    @property
    def base_value(self) -> float:
        """기본 값"""
        return self._base_value

    @base_value.setter
    def base_value(self, value: float) -> None:
        """기본 값 설정 (최소/최대 제한 적용)"""
        self._base_value = self._clamp(value)

    @property
    def total_value(self) -> float:
        """총 값 (기본 + 모든 보너스)"""
        total = self._base_value + sum(self._bonuses.values())
        return self._clamp(total)

    def add_bonus(self, source: str, value: float) -> None:
        """
        보너스 추가

        Args:
            source: 보너스 출처 (예: "장비", "버프")
            value: 보너스 값
        """
        self._bonuses[source] = value

    def remove_bonus(self, source: str) -> None:
        """보너스 제거"""
        self._bonuses.pop(source, None)

    def get_bonus(self, source: str) -> float:
        """특정 출처의 보너스 조회"""
        return self._bonuses.get(source, 0.0)

    def clear_bonuses(self) -> None:
        """모든 보너스 제거"""
        self._bonuses.clear()

    def calculate_growth(self, level: int) -> float:
        """
        레벨에 따른 스탯 성장 계산 (증분 적용)
        
        주의: 이 메서드는 현재 _base_value를 기준으로 다음 레벨의 값을 계산합니다.
        따라서 순차적인 레벨업(1->2->3...) 시에만 올바르게 작동합니다.

        Args:
            level: 새로운 레벨 (도달하는 레벨)

        Returns:
            성장된 스탯 값 (새로운 base_value)
        """
        if self.growth_type == GrowthType.LINEAR:
            # 선형 성장: 매 레벨마다 growth_rate만큼 증가
            return self._base_value + self.growth_rate

        elif self.growth_type == GrowthType.EXPONENTIAL:
            # 지수 성장: 매 레벨마다 growth_rate 비율만큼 증가 (복리)
            return self._base_value * (1.0 + self.growth_rate)

        elif self.growth_type == GrowthType.LOGARITHMIC:
            # 로그 성장: 레벨이 오를수록 증가폭 감소
            # log(L+1) - log(L) 만큼의 비율로 증가하도록 근사
            # 이전 값 + rate * (log(level+1) - log(level))
            # level은 새로운 레벨. 이전 레벨은 level-1
            if level > 1:
                delta = math.log(level + 1) - math.log(level)
                return self._base_value + self.growth_rate * delta * 10 # 스케일 보정
            return self._base_value

        elif self.growth_type == GrowthType.CUSTOM and self.custom_growth_func:
            return self.custom_growth_func(level, self._base_value)

        return self._base_value

    def _clamp(self, value: float) -> float:
        """값을 최소/최대 범위 내로 제한"""
        value = max(value, self.min_value)
        if self.max_value is not None:
            value = min(value, self.max_value)
        return value

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "base_value": self._base_value,
            "total_value": self.total_value,
            "growth_rate": self.growth_rate,
            "growth_type": self.growth_type.value,
            "bonuses": self._bonuses.copy()
        }


class StatManager:
    """
    스탯 매니저

    캐릭터의 모든 스탯을 관리하는 중앙 시스템
    """

    def __init__(self, stats_config: Dict[str, Any]) -> None:
        """
        Args:
            stats_config: 스탯 설정 딕셔너리
        """
        self.stats: Dict[str, Stat] = {}
        self._initialize_stats(stats_config)

    def _initialize_stats(self, config: Dict[str, Any]) -> None:
        """설정에서 스탯 초기화"""
        for stat_name, stat_config in config.items():
            self.stats[stat_name] = Stat(
                name=stat_name,
                base_value=stat_config.get("base_value", 0),
                growth_rate=stat_config.get("growth_rate", 1.0),
                growth_type=GrowthType(stat_config.get("growth_type", "linear")),
                min_value=stat_config.get("min_value", 0),
                max_value=stat_config.get("max_value")
            )

    def get(self, stat_name: str) -> Optional[Stat]:
        """스탯 가져오기"""
        return self.stats.get(stat_name)

    def get_value(self, stat_name: str, use_total: bool = True) -> float:
        """
        스탯 값 가져오기

        Args:
            stat_name: 스탯 이름
            use_total: True면 총 값, False면 기본 값

        Returns:
            스탯 값 (스탯이 없으면 0)
        """
        stat = self.get(stat_name)
        if stat is None:
            return 0.0
        return stat.total_value if use_total else stat.base_value

    def set_base_value(self, stat_name: str, value: float) -> None:
        """기본 값 설정"""
        stat = self.get(stat_name)
        if stat:
            stat.base_value = value

    def modify(self, stat_name: str, amount: float) -> None:
        """기본 값 수정 (상대적)"""
        stat = self.get(stat_name)
        if stat:
            stat.base_value += amount

    def add_bonus(self, stat_name: str, source: str, value: float) -> None:
        """보너스 추가"""
        stat = self.get(stat_name)
        if stat:
            stat.add_bonus(source, value)

    def remove_bonus(self, stat_name: str, source: str) -> None:
        """보너스 제거"""
        stat = self.get(stat_name)
        if stat:
            stat.remove_bonus(source)

    def apply_level_up(self, level: int) -> None:
        """
        레벨업 시 모든 스탯 성장 적용

        Args:
            level: 새 레벨
        """
        from src.core.logger import get_logger
        logger = get_logger("stats")
        
        for stat_name, stat in self.stats.items():
            old_base = stat.base_value
            old_total = stat.total_value
            old_bonuses = sum(stat._bonuses.values())
            
            # base_value만 재계산 (장비 보너스는 유지)
            stat.base_value = stat.calculate_growth(level)
            
            new_base = stat.base_value
            new_total = stat.total_value
            base_gain = new_base - old_base
            total_gain = new_total - old_total
            
            # 로그 출력 (변화가 있는 경우만)
            if base_gain != 0:
                logger.info(f"[레벨업] {stat_name}: base {old_base:.1f} → {new_base:.1f} (+{base_gain:.1f}), "
                          f"total {old_total:.1f} → {new_total:.1f} (+{total_gain:.1f}), "
                          f"보너스: {old_bonuses:.1f} (변화 없음)")
                logger.debug(f"  - growth_type: {stat.growth_type.value}, growth_rate: {stat.growth_rate:.2f}")

    def add_stat(
        self,
        name: str,
        base_value: float,
        growth_rate: float = 1.0,
        growth_type: GrowthType = GrowthType.LINEAR
    ) -> None:
        """
        새로운 스탯 추가 (동적 확장)

        Args:
            name: 스탯 이름
            base_value: 기본 값
            growth_rate: 성장률
            growth_type: 성장 타입
        """
        self.stats[name] = Stat(name, base_value, growth_rate, growth_type)

    def remove_stat(self, name: str) -> None:
        """스탯 제거"""
        self.stats.pop(name, None)

    def has_stat(self, name: str) -> bool:
        """스탯 존재 여부"""
        return name in self.stats

    def get_all_stats(self) -> Dict[str, float]:
        """모든 스탯의 총 값"""
        return {name: stat.total_value for name, stat in self.stats.items()}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (저장용)"""
        return {
            name: stat.to_dict() for name, stat in self.stats.items()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatManager":
        """딕셔너리에서 복원"""
        manager = cls.__new__(cls)
        manager.stats = {}

        for name, stat_data in data.items():
            manager.stats[name] = Stat(
                name=stat_data["name"],
                base_value=stat_data["base_value"],
                growth_rate=stat_data["growth_rate"],
                growth_type=GrowthType(stat_data["growth_type"])
            )
            # 보너스 복원
            for source, value in stat_data.get("bonuses", {}).items():
                manager.stats[name].add_bonus(source, value)

        return manager


# 자주 사용하는 스탯 이름 상수
class Stats:
    """스탯 이름 상수"""
    # 기본 스탯
    HP = "hp"
    MP = "mp"
    INIT_BRV = "init_brv"  # 초기 브레이브 (전투 시작 시 BRV)
    MAX_BRV = "max_brv"    # 최대 브레이브
    STRENGTH = "strength"
    DEFENSE = "defense"
    MAGIC = "magic"
    SPIRIT = "spirit"
    SPEED = "speed"
    LUCK = "luck"
    ACCURACY = "accuracy"  # 명중률
    EVASION = "evasion"    # 회피율

    # 확장 스탯
    STAMINA = "stamina"
    VITALITY = "vitality"
    DEXTERITY = "dexterity"
    PERCEPTION = "perception"
    ENDURANCE = "endurance"
    CHARISMA = "charisma"

    # 파생 스탯 (계산된 값)
    CRIT_RATE = "crit_rate"
    CRIT_DAMAGE = "crit_damage"
