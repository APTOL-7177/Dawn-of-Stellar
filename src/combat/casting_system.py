"""
캐스팅 시스템

일부 강력한 스킬은 캐스팅 시간이 필요
ATB 기반 캐스팅: cast_time은 ATB 비율 (0.0~1.0)
예: 0.3 = ATB 30%, 0.5 = ATB 50%, 1.0 = ATB 100%
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.COMBAT)


class CastingState(Enum):
    """캐스팅 상태"""
    NOT_CASTING = "not_casting"
    CASTING = "casting"
    CAST_COMPLETE = "cast_complete"
    INTERRUPTED = "interrupted"


@dataclass
class CastingInfo:
    """캐스팅 정보"""
    caster: Any  # 시전자
    skill: Any  # 스킬
    target: Optional[Any]  # 대상
    cast_time_ratio: float  # ATB 비율 (0.0~1.0, 예: 0.3 = 30%)
    required_atb: int = 0  # 필요한 ATB 포인트
    accumulated_atb: int = 0  # 축적된 ATB 포인트
    state: CastingState = CastingState.CASTING
    interruptible: bool = True  # 중단 가능 여부

    @property
    def progress(self) -> float:
        """진행도 (0.0 ~ 1.0)"""
        if self.required_atb <= 0:
            return 1.0
        return min(1.0, self.accumulated_atb / self.required_atb)

    @property
    def is_complete(self) -> bool:
        """완료 여부"""
        return self.accumulated_atb >= self.required_atb


class CastingSystem:
    """캐스팅 시스템"""

    def __init__(self):
        self.active_casts: Dict[Any, CastingInfo] = {}  # caster -> CastingInfo
        self.cast_queue: list = []  # 완료 대기 큐

    def start_cast(
        self,
        caster: Any,
        skill: Any,
        target: Optional[Any],
        cast_time_ratio: float,
        atb_threshold: int = 1000,
        interruptible: bool = True
    ) -> CastingInfo:
        """
        캐스팅 시작

        Args:
            caster: 시전자
            skill: 스킬
            target: 대상
            cast_time_ratio: ATB 비율 (0.0~1.0, 예: 0.3 = ATB 30%)
            atb_threshold: ATB 행동 임계값 (기본 1000)
            interruptible: 중단 가능 여부

        Returns:
            CastingInfo
        """
        # 이미 캐스팅 중이면 취소
        if caster in self.active_casts:
            self.cancel_cast(caster, "새로운 시전 시작")

        # 필요한 ATB 포인트 계산 (ATB 비율 * 임계값)
        required_atb = int(cast_time_ratio * atb_threshold)

        cast_info = CastingInfo(
            caster=caster,
            skill=skill,
            target=target,
            cast_time_ratio=cast_time_ratio,
            required_atb=required_atb,
            interruptible=interruptible
        )

        self.active_casts[caster] = cast_info

        caster_name = getattr(caster, 'name', str(caster))
        skill_name = getattr(skill, 'name', str(skill))
        logger.info(f"{caster_name}가 {skill_name} 시전 시작 (ATB: {cast_time_ratio*100:.0f}% = {required_atb} 포인트)")

        return cast_info

    def update(self, caster: Any, atb_increase: int):
        """
        특정 시전자의 캐스팅 업데이트 (ATB 기반)

        Args:
            caster: 시전자
            atb_increase: 증가한 ATB 포인트
        """
        if caster not in self.active_casts:
            return

        cast_info = self.active_casts[caster]
        if cast_info.state != CastingState.CASTING:
            return

        # ATB 축적
        cast_info.accumulated_atb += atb_increase

        # 완료 체크
        if cast_info.is_complete:
            cast_info.state = CastingState.CAST_COMPLETE
            self.cast_queue.append(cast_info)

            caster_name = getattr(caster, 'name', str(caster))
            skill_name = getattr(cast_info.skill, 'name', str(cast_info.skill))
            logger.info(f"{caster_name}의 {skill_name} 시전 완료!")

            # 완료된 캐스팅 제거
            del self.active_casts[caster]

    def cancel_cast(self, caster: Any, reason: str = "중단됨"):
        """
        캐스팅 중단

        Args:
            caster: 시전자
            reason: 중단 이유
        """
        if caster not in self.active_casts:
            return

        cast_info = self.active_casts[caster]

        caster_name = getattr(caster, 'name', str(caster))
        if not cast_info.interruptible:
            logger.debug(f"{caster_name}의 시전은 중단 불가")
            return

        skill_name = getattr(cast_info.skill, 'name', str(cast_info.skill))
        logger.info(f"{caster_name}의 {skill_name} 시전 중단: {reason}")

        cast_info.state = CastingState.INTERRUPTED
        del self.active_casts[caster]

    def interrupt_on_damage(self, caster: Any, damage: int):
        """
        데미지로 인한 중단

        Args:
            caster: 시전자
            damage: 받은 데미지
        """
        if caster not in self.active_casts:
            return

        cast_info = self.active_casts[caster]

        # 중단 확률 (데미지가 클수록 높음)
        interrupt_chance = min(0.9, damage / 100.0)

        import random
        if random.random() < interrupt_chance:
            self.cancel_cast(caster, f"데미지 {damage}로 인한 중단")

    def is_casting(self, caster: Any) -> bool:
        """시전 중인지 확인"""
        return caster in self.active_casts

    def get_cast_info(self, caster: Any) -> Optional[CastingInfo]:
        """캐스팅 정보 가져오기"""
        return self.active_casts.get(caster)

    def get_completed_casts(self) -> list:
        """완료된 캐스팅 가져오기 (큐에서 제거)"""
        completed = self.cast_queue.copy()
        self.cast_queue.clear()
        return completed

    def clear(self):
        """모든 캐스팅 초기화"""
        self.active_casts.clear()
        self.cast_queue.clear()


# 전역 인스턴스
_casting_system: Optional[CastingSystem] = None


def get_casting_system() -> CastingSystem:
    """전역 캐스팅 시스템 인스턴스"""
    global _casting_system
    if _casting_system is None:
        _casting_system = CastingSystem()
    return _casting_system
