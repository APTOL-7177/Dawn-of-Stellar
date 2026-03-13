"""
effects/__init__.py - 이펙트 패키지

비주얼 이펙트 파이프라인을 관리하는 EffectManager와
각 이펙트 레이어를 노출합니다.

파이프라인 순서:
    셀 렌더링 → 글로우 → 파티클 → 라이팅 → 스케일링 →
    셰이크 → 플래시 → 글리치 → CRT → 전환 → flip

사용 예시:
    from src.ui.pygame_backend.effects import EffectManager

    manager = EffectManager()
    manager.update(dt)
    manager.apply(screen_surface)
"""

from typing import Optional, Tuple

import pygame

from src.core.config import get_config
from src.core.logger import get_logger

from src.ui.pygame_backend.effects.base import EffectLayer
from src.ui.pygame_backend.effects.glow import GlowEffect
from src.ui.pygame_backend.effects.particles import ParticleEffect
from src.ui.pygame_backend.effects.lighting import LightingEffect, PointLight
from src.ui.pygame_backend.effects.crt import CRTEffect
from src.ui.pygame_backend.effects.screen_effects import ScreenEffects
from src.ui.pygame_backend.effects.glitch import GlitchEffect
from src.ui.pygame_backend.effects.transition import TransitionEffect, TransitionMode
from src.ui.pygame_backend.effects.text_effects import (
    TextScrambler,
    TextTypewriter,
    ColorCycler,
    render_scrambled_text,
)

logger = get_logger("effects")


def _cfg(key: str, default):
    """config.yaml의 display.effects 섹션에서 값을 읽습니다. 섹션이 없으면 기본값 반환."""
    try:
        return get_config().get(f"display.effects.{key}", default)
    except RuntimeError:
        # config가 아직 초기화되지 않은 경우 기본값 사용
        return default


class EffectManager:
    """
    시각 이펙트 파이프라인 매니저

    각 이펙트 레이어를 순서대로 관리하고,
    update(dt) / apply(surface) 메서드로 게임 루프와 연동합니다.

    config.yaml의 display.effects 섹션에서 각 이펙트를 on/off할 수 있습니다:

        display:
          effects:
            glow: true
            particles: true
            lighting: false
            crt: true
            screen_effects: true
            crt_scanline_alpha: 40
            crt_vignette_strength: 0.55
            glow_intensity: 0.8
            ambient_r: 30
            ambient_g: 25
            ambient_b: 40
    """

    def __init__(
        self,
        tile_width: int = 10,
        tile_height: int = 13,
    ) -> None:
        """
        Args:
            tile_width: 셀 너비 (픽셀) - 라이팅 좌표 계산에 사용
            tile_height: 셀 높이 (픽셀)
        """
        # ── config에서 활성화 플래그 읽기 ───────────────────────────────
        glow_enabled: bool       = bool(_cfg("glow", True))
        particles_enabled: bool  = bool(_cfg("particles", True))
        lighting_enabled: bool   = bool(_cfg("lighting", False))
        crt_enabled: bool        = bool(_cfg("crt", True))
        screen_enabled: bool     = bool(_cfg("screen_effects", True))

        # ── 글로우 이펙트 ─────────────────────────────────────────────
        glow_intensity: float = float(_cfg("glow_intensity", 0.8))
        self.glow = GlowEffect(
            enabled=glow_enabled,
            intensity=glow_intensity,
        )

        # ── 파티클 이펙트 ─────────────────────────────────────────────
        self.particles = ParticleEffect(enabled=particles_enabled)

        # ── 라이팅 이펙트 ─────────────────────────────────────────────
        ambient_r: int = int(_cfg("ambient_r", 30))
        ambient_g: int = int(_cfg("ambient_g", 25))
        ambient_b: int = int(_cfg("ambient_b", 40))
        self.lighting = LightingEffect(
            enabled=lighting_enabled,
            tile_width=tile_width,
            tile_height=tile_height,
            ambient_color=(ambient_r, ambient_g, ambient_b),
        )

        # ── CRT 이펙트 ────────────────────────────────────────────────
        crt_alpha: int         = int(_cfg("crt_scanline_alpha", 40))
        crt_vignette: float    = float(_cfg("crt_vignette_strength", 0.55))
        self.crt = CRTEffect(
            enabled=crt_enabled,
            scanline_alpha=crt_alpha,
            vignette_strength=crt_vignette,
        )

        # ── 화면 셰이크/플래시 ────────────────────────────────────────
        self.screen_fx = ScreenEffects(enabled=screen_enabled)

        # ── 글리치 이펙트 (Cogmind 스타일) ──────────────────────────
        glitch_enabled: bool = bool(_cfg("glitch", True))
        self.glitch = GlitchEffect(enabled=glitch_enabled)

        # ── 화면 전환 이펙트 (Cogmind 스타일) ───────────────────────
        self.transition = TransitionEffect(enabled=True)

        # 렌더링 순서를 유지하는 파이프라인 목록
        # (셰이크/플래시/글리치/전환은 apply_post() 내부에서 순서 제어)
        self._pipeline: list[EffectLayer] = [
            self.glow,
            self.particles,
            self.lighting,
            self.screen_fx,
            self.glitch,
            self.crt,
            self.transition,
        ]

        logger.info(
            f"EffectManager 초기화: "
            f"glow={glow_enabled}, particles={particles_enabled}, "
            f"lighting={lighting_enabled}, crt={crt_enabled}, "
            f"screen_fx={screen_enabled}, glitch={glitch_enabled}"
        )

    # ── 타일 크기 업데이트 ────────────────────────────────────────────────

    def set_tile_size(self, tile_width: int, tile_height: int) -> None:
        """
        타일 크기 동기화 (PygameDisplay 초기화 완료 후 호출)

        Args:
            tile_width: 셀 너비 (픽셀)
            tile_height: 셀 높이 (픽셀)
        """
        self.lighting.set_tile_size(tile_width, tile_height)

    # ── 파이프라인 제어 ───────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        모든 이펙트 레이어 상태 업데이트

        게임 루프의 매 프레임 호출합니다.

        Args:
            dt: 경과 시간 (초)
        """
        for layer in self._pipeline:
            if layer.enabled:
                layer.update(dt)

    def apply(self, surface: pygame.Surface) -> None:
        """
        콘솔 해상도 이펙트를 surface에 적용 (스케일링 전)

        파이프라인: 글로우 → 파티클 → 라이팅

        Args:
            surface: 콘솔 해상도 오프스크린 Surface
        """
        if self.glow.enabled:
            self.glow.render(surface)
        if self.particles.enabled:
            self.particles.render(surface)
        if self.lighting.enabled:
            self.lighting.render(surface)

    def apply_post(
        self,
        screen: pygame.Surface,
        scaled: pygame.Surface,
        dest_rect: tuple,
    ) -> None:
        """
        스크린 해상도 이펙트 적용 (스케일링 후)

        파이프라인: 셰이크 → blit → 플래시 → 글리치 → CRT → 전환

        Args:
            screen: 최종 출력 윈도우 Surface
            scaled: 스케일링된 콘솔 Surface
            dest_rect: (x, y, w, h) 스케일링 대상 영역
        """
        dx, dy = dest_rect[0], dest_rect[1]

        # 셰이크: 오프셋 적용
        if self.screen_fx.enabled and self.screen_fx.is_shaking:
            ox, oy = self.screen_fx.shake_offset
            dx += ox
            dy += oy

        screen.blit(scaled, (dx, dy))

        # 플래시: 반투명 컬러 오버레이
        if self.screen_fx.enabled:
            self.screen_fx.render(screen)

        # 글리치: 데이터 손상 아티팩트 (Cogmind 스타일)
        if self.glitch.enabled and self.glitch.is_active:
            self.glitch.render(screen)

        # CRT: 스캔라인 + 비네팅
        if self.crt.enabled:
            self.crt.render(screen)

        # 전환: 화면 전환 효과 (최상위 레이어)
        if self.transition.enabled and self.transition.is_active:
            self.transition.render(screen)

    def apply_all(self, surface: pygame.Surface) -> None:
        """
        단일 Surface에 전체 파이프라인 적용 (하위 호환용)

        Args:
            surface: 최종 출력 Surface
        """
        self.apply(surface)

        if self.screen_fx.enabled and self.screen_fx.is_shaking:
            ox, oy = self.screen_fx.shake_offset
            if ox != 0 or oy != 0:
                tmp = surface.copy()
                surface.fill((0, 0, 0))
                surface.blit(tmp, (ox, oy))

        if self.screen_fx.enabled:
            self.screen_fx.render(surface)
        if self.glitch.enabled and self.glitch.is_active:
            self.glitch.render(surface)
        if self.crt.enabled:
            self.crt.render(surface)
        if self.transition.enabled and self.transition.is_active:
            self.transition.render(surface)

    # ── 편의 트리거 메서드 ────────────────────────────────────────────────

    def trigger_shake(self, intensity: float, duration: float) -> None:
        """
        화면 셰이크 트리거 (ScreenEffects 위임)

        Args:
            intensity: 최대 오프셋 픽셀 (예: 8.0)
            duration: 지속 시간 (초, 예: 0.35)
        """
        self.screen_fx.trigger_shake(intensity, duration)

    def trigger_flash(
        self,
        color: Tuple[int, int, int],
        duration: float,
        max_alpha: int = 160,
    ) -> None:
        """
        화면 플래시 트리거 (ScreenEffects 위임)

        Args:
            color: 플래시 RGB 색상 (예: (255, 80, 80))
            duration: 지속 시간 (초, 예: 0.2)
            max_alpha: 최대 불투명도 (0~255)
        """
        self.screen_fx.trigger_flash(color, duration, max_alpha)

    def emit_particles(
        self,
        x: float,
        y: float,
        event_type: str = "spark",
        count: Optional[int] = None,
    ) -> None:
        """
        파티클 방출 (ParticleEffect 위임)

        Args:
            x: 화면 X 좌표 (픽셀)
            y: 화면 Y 좌표 (픽셀)
            event_type: "spark" | "magic" | "heal"
            count: 생성 개수 (None이면 프리셋 기본값)
        """
        self.particles.emit(x, y, event_type, count)

    def add_light(self, light: PointLight) -> None:
        """광원 추가 (LightingEffect 위임)"""
        self.lighting.add_light(light)

    def remove_light(self, light: PointLight) -> None:
        """광원 제거 (LightingEffect 위임)"""
        self.lighting.remove_light(light)

    def clear_lights(self) -> None:
        """모든 광원 제거 (LightingEffect 위임)"""
        self.lighting.clear_lights()

    # ── 글리치 편의 메서드 (Cogmind 스타일) ─────────────────────────────

    def trigger_glitch(
        self,
        intensity: float = 1.0,
        duration: float = 0.3,
    ) -> None:
        """
        글리치 버스트 트리거 (GlitchEffect 위임)

        피격, 시스템 이벤트 등에서 화면 왜곡 효과를 발생시킵니다.

        Args:
            intensity: 글리치 강도 (0.0~1.0)
            duration: 지속 시간 (초)
        """
        self.glitch.trigger(intensity, duration)

    def set_persistent_glitch(self, intensity: float = 0.0) -> None:
        """
        상시 글리치 강도 설정 (GlitchEffect 위임)

        시스템 손상 상태 등 지속적인 시각 왜곡에 사용합니다.
        0.0으로 설정하면 비활성화됩니다.

        Args:
            intensity: 상시 글리치 강도 (0.0~1.0)
        """
        self.glitch.set_persistent(intensity)

    # ── 전환 편의 메서드 (Cogmind 스타일) ────────────────────────────────

    def trigger_transition(
        self,
        mode: TransitionMode,
        duration: float = 0.5,
        direction: str = "out",
        color: Tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """
        화면 전환 효과 트리거 (TransitionEffect 위임)

        화면 간 전환 시 시각적 연출에 사용합니다.

        Args:
            mode: 전환 모드 (TransitionMode 열거형)
            duration: 전환 지속 시간 (초)
            direction: "out"=화면을 가림, "in"=가림을 해제
            color: 전환 색상
        """
        self.transition.trigger(mode, duration, direction, color)

    @property
    def is_transitioning(self) -> bool:
        """화면 전환 중 여부"""
        return self.transition.is_active


# 패키지 공개 API
__all__ = [
    "EffectManager",
    "EffectLayer",
    "GlowEffect",
    "ParticleEffect",
    "LightingEffect",
    "PointLight",
    "CRTEffect",
    "ScreenEffects",
    "GlitchEffect",
    "TransitionEffect",
    "TransitionMode",
    "TextScrambler",
    "TextTypewriter",
    "ColorCycler",
    "render_scrambled_text",
]
