"""
base.py - 이펙트 레이어 추상 기반 클래스

모든 시각 이펙트가 구현해야 하는 공통 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod

import pygame


class EffectLayer(ABC):
    """
    이펙트 레이어 추상 기반 클래스

    모든 이펙트는 이 클래스를 상속받아 update()와 render()를
    구현해야 합니다.
    """

    def __init__(self, enabled: bool = True) -> None:
        # 이펙트 활성화 여부 (config에서 제어)
        self.enabled: bool = enabled

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        이펙트 상태 업데이트

        Args:
            dt: 경과 시간 (초 단위)
        """
        ...

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        """
        이펙트를 surface에 렌더링

        Args:
            surface: 렌더링 대상 pygame Surface
        """
        ...

    def enable(self) -> None:
        """이펙트 활성화"""
        self.enabled = True

    def disable(self) -> None:
        """이펙트 비활성화"""
        self.enabled = False
