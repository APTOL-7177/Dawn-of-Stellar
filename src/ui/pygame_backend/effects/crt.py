"""
crt.py - CRT 모니터 효과

스캔라인과 비네팅(주변부 어두워짐) 오버레이를 적용합니다.
오버레이는 프리렌더링되어 리사이즈 시에만 재생성됩니다. 토글 가능.
"""

from typing import Optional, Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.crt")


class CRTEffect(EffectLayer):
    """
    CRT 스캔라인 + 비네팅 이펙트

    오버레이 Surface를 프리렌더링하고 BLEND_MULT 또는 직접 blit으로 합성합니다.
    화면 크기가 변경될 때만 오버레이를 재생성하여 성능을 유지합니다.
    """

    def __init__(
        self,
        enabled: bool = True,
        scanline_alpha: int = 40,
        vignette_strength: float = 0.55,
        scanline_gap: int = 2,
    ) -> None:
        """
        Args:
            enabled: 이펙트 활성화 여부
            scanline_alpha: 스캔라인 어두운 선의 불투명도 (0~255)
            vignette_strength: 비네팅 강도 (0.0=없음, 1.0=매우 강함)
            scanline_gap: 스캔라인 간격 (픽셀)
        """
        super().__init__(enabled)
        self.scanline_alpha: int = max(0, min(255, scanline_alpha))
        self.vignette_strength: float = max(0.0, min(1.0, vignette_strength))
        self.scanline_gap: int = max(1, scanline_gap)

        # 프리렌더링된 오버레이 (크기 변경 시 재생성)
        self._overlay: Optional[pygame.Surface] = None
        self._overlay_size: Tuple[int, int] = (0, 0)

    def update(self, dt: float) -> None:
        """CRT 이펙트는 정적 - 상태 변화 없음"""
        pass

    def render(self, surface: pygame.Surface) -> None:
        """
        CRT 오버레이를 surface에 적용

        Args:
            surface: 렌더링 대상 Surface
        """
        if not self.enabled:
            return

        w, h = surface.get_size()

        # 오버레이 재생성 필요 여부 확인 (초기화 또는 크기 변경)
        if self._overlay_size != (w, h) or self._overlay is None:
            self._build_overlay(w, h)

        if self._overlay is None:
            return

        # 오버레이를 화면에 합성 (BLEND_MULT: 오버레이의 어두운 부분이 화면을 어둡게)
        surface.blit(self._overlay, (0, 0), special_flags=pygame.BLEND_MULT)

    def _build_overlay(self, w: int, h: int) -> None:
        """
        스캔라인 + 비네팅 오버레이를 프리렌더링

        Args:
            w: 화면 너비 (픽셀)
            h: 화면 높이 (픽셀)
        """
        try:
            # BLEND_MULT 모드: (255,255,255)=원본 그대로, 낮을수록 어두워짐
            overlay = pygame.Surface((w, h))
            overlay.fill((255, 255, 255))  # 흰색 기반

            # ── 스캔라인 렌더링 ──────────────────────────────────────────
            # scanline_gap 픽셀마다 어두운 수평선을 그어 CRT 라인 효과 구현
            scan_color_val = 255 - self.scanline_alpha
            scan_color = (scan_color_val, scan_color_val, scan_color_val)

            for y in range(0, h, self.scanline_gap):
                pygame.draw.line(overlay, scan_color, (0, y), (w - 1, y))

            # ── 비네팅 렌더링 ────────────────────────────────────────────
            # 중심에서 외곽으로 갈수록 어두워지는 원형 그라디언트
            # 별도 Surface에서 생성 후 BLEND_MULT로 합성
            vignette = pygame.Surface((w, h))
            vignette.fill((255, 255, 255))

            cx, cy = w // 2, h // 2
            max_dist = (cx * cx + cy * cy) ** 0.5

            # 비네팅은 동심원을 여러 단계로 그려 그라디언트 근사
            steps = 60
            for step in range(steps, 0, -1):
                ratio = step / steps  # 1.0(외곽) ~ 0(중심)
                # 비네팅 강도에 따라 어두워지는 정도 조절
                darkness = int(self.vignette_strength * ratio * ratio * 120)
                color_val = max(0, 255 - darkness)
                radius = int(max_dist * ratio * 1.1)  # 약간 크게 그려 모서리 커버
                pygame.draw.ellipse(
                    vignette,
                    (color_val, color_val, color_val),
                    (cx - radius, cy - int(radius * h / w), radius * 2, int(radius * 2 * h / w)),
                )

            # 스캔라인 오버레이에 비네팅 합성
            overlay.blit(vignette, (0, 0), special_flags=pygame.BLEND_MULT)

            self._overlay = overlay
            self._overlay_size = (w, h)
            logger.debug(f"CRT 오버레이 재생성: {w}x{h}")

        except Exception as exc:
            logger.warning(f"CRT 오버레이 생성 오류: {exc}")
            self._overlay = None

    def rebuild(self) -> None:
        """오버레이 강제 재생성 (설정 변경 후 호출)"""
        self._overlay = None
        self._overlay_size = (0, 0)
