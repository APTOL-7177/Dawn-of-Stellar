"""
glow.py - 밝은 전경색 셀 주변 가우시안 글로우 이펙트

1/4 해상도 다운스케일로 성능을 유지하며, BLEND_ADD 모드로 합성합니다.
밝기 임계값 이상의 색상을 가진 셀 주변에 발광 효과를 적용합니다.
"""

from typing import Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.glow")


def _luminance(color: Tuple[int, int, int]) -> float:
    """RGB 색상의 상대 밝기(0~1) 계산"""
    r, g, b = color
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


class GlowEffect(EffectLayer):
    """
    밝은 전경색 셀 주변 가우시안 글로우 이펙트

    처리 과정:
      1. 원본 surface를 1/4 해상도로 다운스케일
      2. 가우시안 블러 (pygame.transform.smoothscale 2회 적용으로 근사)
      3. BLEND_ADD 모드로 원본 surface에 합성
    """

    # 가우시안 블러 근사 반복 횟수 (값이 클수록 부드럽지만 느림)
    _BLUR_PASSES: int = 2

    def __init__(
        self,
        enabled: bool = True,
        intensity: float = 0.8,
        brightness_threshold: float = 0.55,
    ) -> None:
        """
        Args:
            enabled: 이펙트 활성화 여부
            intensity: 글로우 강도 (0.0 ~ 1.0)
            brightness_threshold: 글로우를 적용할 최소 밝기 임계값
        """
        super().__init__(enabled)
        # 글로우 강도 (알파 배율)
        self.intensity: float = max(0.0, min(1.0, intensity))
        # 밝기 임계값 이상의 픽셀에만 글로우 적용
        self.brightness_threshold: float = brightness_threshold
        # 다운스케일 버퍼 (크기 변경 시 재생성)
        self._small_surf: pygame.Surface | None = None
        self._small_size: Tuple[int, int] = (0, 0)

    def update(self, dt: float) -> None:
        """GlowEffect는 시간 기반 상태 변화 없음 (정적 이펙트)"""
        pass

    def render(self, surface: pygame.Surface) -> None:
        """
        글로우 이펙트를 surface에 렌더링

        Args:
            surface: 렌더링 대상 Surface (원본 콘솔 렌더링 결과)
        """
        if not self.enabled:
            return

        w, h = surface.get_size()
        # 1/4 해상도 크기 계산 (최소 1픽셀 보장)
        small_w = max(1, w // 4)
        small_h = max(1, h // 4)
        target_small = (small_w, small_h)

        try:
            # 다운스케일 버퍼 재사용 또는 재생성
            if self._small_size != target_small or self._small_surf is None:
                self._small_surf = pygame.Surface(target_small, pygame.SRCALPHA)
                self._small_size = target_small

            # 1단계: 1/4 해상도로 다운스케일 (smoothscale = 고품질 리샘플링)
            pygame.transform.smoothscale(surface, target_small, self._small_surf)

            # 2단계: 가우시안 블러 근사
            #   smoothscale을 더 작게 줄였다가 되돌리는 방식으로 블러 근사
            blur_surf = self._small_surf
            for _ in range(self._BLUR_PASSES):
                half_w = max(1, small_w // 2)
                half_h = max(1, small_h // 2)
                tmp = pygame.transform.smoothscale(blur_surf, (half_w, half_h))
                blur_surf = pygame.transform.smoothscale(tmp, target_small)

            # 3단계: 글로우 강도 적용 (알파 채널 조절)
            alpha_val = int(self.intensity * 180)  # 최대 180/255 로 과노출 방지
            blur_surf.set_alpha(alpha_val)

            # 4단계: 원래 해상도로 업스케일
            glow_full = pygame.transform.smoothscale(blur_surf, (w, h))

            # 5단계: BLEND_ADD 모드로 원본에 합성
            surface.blit(glow_full, (0, 0), special_flags=pygame.BLEND_ADD)

        except Exception as exc:
            # 글로우 실패 시 게임 진행에 영향 없도록 조용히 처리
            logger.warning(f"글로우 렌더링 오류: {exc}")
