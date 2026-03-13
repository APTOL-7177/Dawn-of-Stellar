"""
screen_effects.py - 화면 셰이크 및 플래시 이펙트

화면 셰이크: offset 기반으로 렌더링 표면을 일시적으로 이동
화면 플래시: 반투명 컬러 오버레이로 순간적인 발광/피격 효과 구현
"""

import math
import random
from typing import Optional, Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.screen")


class ScreenEffects(EffectLayer):
    """
    화면 셰이크 + 플래시 이펙트

    EffectManager의 파이프라인에서 스케일링 이후, CRT 이전에 적용됩니다.

    사용 예시:
        screen_fx = ScreenEffects()
        screen_fx.trigger_shake(intensity=8.0, duration=0.35)
        screen_fx.trigger_flash(color=(255, 80, 80), duration=0.2)
    """

    def __init__(self, enabled: bool = True) -> None:
        super().__init__(enabled)

        # ── 셰이크 상태 ─────────────────────────────────────────────────
        self._shake_intensity: float = 0.0   # 최대 오프셋 픽셀
        self._shake_duration: float = 0.0    # 남은 셰이크 시간 (초)
        self._shake_total: float = 0.0       # 전체 셰이크 시간 (감쇠 계산용)
        self._shake_offset: Tuple[int, int] = (0, 0)  # 현재 오프셋

        # ── 플래시 상태 ─────────────────────────────────────────────────
        self._flash_color: Tuple[int, int, int] = (255, 255, 255)
        self._flash_duration: float = 0.0    # 남은 플래시 시간 (초)
        self._flash_total: float = 0.0       # 전체 플래시 시간 (페이드아웃 계산용)
        self._flash_max_alpha: int = 160     # 최대 알파 (0~255)

        # 플래시 렌더링용 Surface (크기 변경 시 재생성)
        self._flash_surf: Optional[pygame.Surface] = None
        self._flash_surf_size: Tuple[int, int] = (0, 0)

    # ── 트리거 메서드 ────────────────────────────────────────────────────

    def trigger_shake(self, intensity: float, duration: float) -> None:
        """
        화면 셰이크 트리거

        이미 셰이크 중이면 더 강한 쪽으로 덮어씌웁니다.

        Args:
            intensity: 최대 오프셋 픽셀 (예: 8.0)
            duration: 셰이크 지속 시간 (초, 예: 0.35)
        """
        if not self.enabled:
            return
        # 더 강한 셰이크가 요청되면 덮어씀
        if intensity >= self._shake_intensity or self._shake_duration <= 0:
            self._shake_intensity = max(0.0, intensity)
            self._shake_duration = max(0.0, duration)
            self._shake_total = self._shake_duration
        logger.debug(f"셰이크 트리거: intensity={intensity}, duration={duration}")

    def trigger_flash(
        self,
        color: Tuple[int, int, int],
        duration: float,
        max_alpha: int = 160,
    ) -> None:
        """
        화면 플래시 트리거

        Args:
            color: 플래시 RGB 색상 (예: (255, 80, 80) for 피격)
            duration: 플래시 지속 시간 (초, 예: 0.2)
            max_alpha: 플래시 최대 불투명도 (0~255)
        """
        if not self.enabled:
            return
        self._flash_color = color
        self._flash_duration = max(0.0, duration)
        self._flash_total = self._flash_duration
        self._flash_max_alpha = max(0, min(255, max_alpha))
        logger.debug(f"플래시 트리거: color={color}, duration={duration}")

    # ── EffectLayer 인터페이스 ───────────────────────────────────────────

    def update(self, dt: float) -> None:
        """셰이크 및 플래시 상태 업데이트"""
        if not self.enabled:
            self._shake_offset = (0, 0)
            return

        # 셰이크 업데이트
        if self._shake_duration > 0:
            self._shake_duration -= dt
            if self._shake_duration <= 0:
                self._shake_duration = 0.0
                self._shake_offset = (0, 0)
            else:
                # 시간이 지날수록 감쇠하는 셰이크 (선형 감쇠)
                decay = self._shake_duration / self._shake_total if self._shake_total > 0 else 0
                current_intensity = self._shake_intensity * decay
                ox = random.uniform(-current_intensity, current_intensity)
                oy = random.uniform(-current_intensity, current_intensity)
                self._shake_offset = (int(ox), int(oy))
        else:
            self._shake_offset = (0, 0)

        # 플래시 업데이트
        if self._flash_duration > 0:
            self._flash_duration -= dt
            if self._flash_duration < 0:
                self._flash_duration = 0.0

    @property
    def shake_offset(self) -> Tuple[int, int]:
        """현재 셰이크 오프셋 (EffectManager에서 blit 위치에 적용)"""
        return self._shake_offset

    @property
    def is_shaking(self) -> bool:
        """셰이크 중 여부"""
        return self._shake_duration > 0

    @property
    def is_flashing(self) -> bool:
        """플래시 중 여부"""
        return self._flash_duration > 0

    def render(self, surface: pygame.Surface) -> None:
        """
        플래시 오버레이 렌더링 (셰이크는 EffectManager의 blit offset으로 처리)

        Args:
            surface: 렌더링 대상 Surface
        """
        if not self.enabled:
            return

        # 플래시 렌더링
        if self._flash_duration > 0 and self._flash_total > 0:
            w, h = surface.get_size()

            # 플래시 Surface 준비
            if self._flash_surf_size != (w, h) or self._flash_surf is None:
                self._flash_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                self._flash_surf_size = (w, h)

            # 페이드아웃: 남은 시간 비율에 따라 알파 감소
            fade_ratio = self._flash_duration / self._flash_total
            alpha = int(self._flash_max_alpha * fade_ratio)

            if alpha > 0:
                r, g, b = self._flash_color
                self._flash_surf.fill((r, g, b, alpha))
                surface.blit(self._flash_surf, (0, 0))
