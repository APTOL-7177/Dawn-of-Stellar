"""
lighting.py - 동적 셀 단위 라이트맵

PointLight를 셀 좌표로 배치하고, multiply 블렌드로 어둠 효과와
빛이 닿는 영역의 색상 틴팅을 구현합니다.
횃불 등의 flicker(깜빡임) 효과를 지원합니다.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.lighting")


@dataclass
class PointLight:
    """
    점 광원

    Attributes:
        x: 셀 단위 X 좌표
        y: 셀 단위 Y 좌표
        radius: 빛이 닿는 반경 (셀 단위)
        color: RGB 빛 색상 (기본 흰색)
        intensity: 빛 강도 (0.0 ~ 1.0)
        flicker: 깜빡임 활성화 여부 (횃불 등)
        flicker_speed: 깜빡임 속도 (Hz)
        flicker_amplitude: 강도 변동 폭 (0.0 ~ 1.0)
        _flicker_phase: 내부 깜빡임 위상 (자동 관리)
        _current_intensity: 깜빡임 적용 후 실제 강도
    """
    x: float
    y: float
    radius: float
    color: Tuple[int, int, int] = field(default_factory=lambda: (255, 220, 160))
    intensity: float = 1.0
    flicker: bool = False
    flicker_speed: float = 3.5       # Hz (초당 사이클)
    flicker_amplitude: float = 0.15  # 강도 변동 폭
    _flicker_phase: float = field(default=0.0, init=False, repr=False)
    _current_intensity: float = field(default=1.0, init=False, repr=False)

    def __post_init__(self) -> None:
        # 각 광원마다 랜덤 초기 위상으로 자연스러운 깜빡임
        self._flicker_phase = random.uniform(0, 2 * math.pi)
        self._current_intensity = self.intensity

    def update(self, dt: float) -> None:
        """깜빡임 상태 업데이트"""
        if not self.flicker:
            self._current_intensity = self.intensity
            return

        self._flicker_phase += self.flicker_speed * 2 * math.pi * dt
        # 사인 파형 기반 깜빡임 + 작은 노이즈로 자연스러움 추가
        sine_val = math.sin(self._flicker_phase)
        noise = random.uniform(-0.05, 0.05)
        delta = (sine_val + noise) * self.flicker_amplitude
        self._current_intensity = max(0.1, min(1.0, self.intensity + delta))


class LightingEffect(EffectLayer):
    """
    동적 셀 단위 라이트맵 이펙트

    처리 과정:
      1. 배경을 주변광(ambient) 색상으로 채운 라이트맵 Surface 생성
      2. 각 PointLight의 영향 범위를 소프트 서클로 라이트맵에 그림
      3. BLEND_MULT 모드로 원본 surface에 곱합산

    사용 예시:
        lighting = LightingEffect()
        torch = PointLight(x=10, y=5, radius=6, flicker=True)
        lighting.add_light(torch)
    """

    def __init__(
        self,
        enabled: bool = True,
        tile_width: int = 10,
        tile_height: int = 13,
        ambient_color: Tuple[int, int, int] = (30, 25, 40),
    ) -> None:
        """
        Args:
            enabled: 이펙트 활성화 여부
            tile_width: 셀 너비 (픽셀)
            tile_height: 셀 높이 (픽셀)
            ambient_color: 배경 주변광 색상 (어두운 영역의 색)
        """
        super().__init__(enabled)
        self.tile_width: int = tile_width
        self.tile_height: int = tile_height
        # 주변광: 빛이 닿지 않는 영역의 색상
        self.ambient_color: Tuple[int, int, int] = ambient_color

        self._lights: List[PointLight] = []
        self._lightmap: Optional[pygame.Surface] = None
        self._lightmap_size: Tuple[int, int] = (0, 0)

    def add_light(self, light: PointLight) -> None:
        """광원 추가"""
        self._lights.append(light)

    def remove_light(self, light: PointLight) -> None:
        """광원 제거"""
        if light in self._lights:
            self._lights.remove(light)

    def clear_lights(self) -> None:
        """모든 광원 제거"""
        self._lights.clear()

    def set_tile_size(self, tile_width: int, tile_height: int) -> None:
        """
        타일 크기 업데이트 (디스플레이 초기화 후 호출)

        Args:
            tile_width: 셀 너비 (픽셀)
            tile_height: 셀 높이 (픽셀)
        """
        self.tile_width = tile_width
        self.tile_height = tile_height
        # 라이트맵 재생성 강제
        self._lightmap = None

    def update(self, dt: float) -> None:
        """모든 광원의 깜빡임 상태 업데이트"""
        if not self.enabled:
            return
        for light in self._lights:
            light.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        """
        라이트맵을 surface에 multiply 블렌드로 합성

        Args:
            surface: 렌더링 대상 Surface
        """
        if not self.enabled:
            return

        w, h = surface.get_size()

        # 라이트맵 Surface 준비 (크기 변경 시 재생성)
        if self._lightmap_size != (w, h) or self._lightmap is None:
            self._lightmap = pygame.Surface((w, h))
            self._lightmap_size = (w, h)

        # 라이트맵을 주변광 색상으로 초기화 (어두운 배경)
        self._lightmap.fill(self.ambient_color)

        # 각 광원을 라이트맵에 그리기
        for light in self._lights:
            self._draw_light(self._lightmap, light)

        # BLEND_MULT: 라이트맵 색상이 (255,255,255)이면 원본 그대로,
        # (0,0,0)이면 완전히 어두워짐
        surface.blit(self._lightmap, (0, 0), special_flags=pygame.BLEND_MULT)

    def _draw_light(self, lightmap: pygame.Surface, light: PointLight) -> None:
        """
        소프트 원형 그라디언트로 단일 광원을 라이트맵에 그리기

        Args:
            lightmap: 라이트맵 Surface
            light: 그릴 광원
        """
        lw, lh = lightmap.get_size()
        # 셀 단위 좌표를 픽셀 좌표로 변환 (셀 중심)
        cx = int(light.x * self.tile_width + self.tile_width / 2)
        cy = int(light.y * self.tile_height + self.tile_height / 2)
        # 반경을 픽셀 단위로 변환 (타일 크기 평균 사용)
        pixel_radius = int(light.radius * (self.tile_width + self.tile_height) / 2)

        if pixel_radius <= 0:
            return

        lr, lg, lb = light.color
        cur_intensity = light._current_intensity

        # 소프트 그라디언트: 여러 동심원을 알파/색상 감소로 표현
        steps = min(pixel_radius, 24)  # 단계 수 (성능 균형)
        for step in range(steps, 0, -1):
            ratio = step / steps  # 1.0(중심) ~ 0(외곽)
            # 중심에서 외곽으로 갈수록 어두워지는 소프트 에지
            soft_ratio = ratio * ratio  # 이차 감쇠로 자연스러운 falloff
            r_step = int(pixel_radius * ratio)

            # 광원 색상과 주변광의 선형 보간
            ar, ag, ab = self.ambient_color
            blend_r = int(ar + (lr - ar) * soft_ratio * cur_intensity)
            blend_g = int(ag + (lg - ag) * soft_ratio * cur_intensity)
            blend_b = int(ab + (lb - ab) * soft_ratio * cur_intensity)

            # 클램프
            blend_r = max(0, min(255, blend_r))
            blend_g = max(0, min(255, blend_g))
            blend_b = max(0, min(255, blend_b))

            try:
                pygame.draw.circle(
                    lightmap,
                    (blend_r, blend_g, blend_b),
                    (cx, cy),
                    r_step,
                )
            except Exception:
                pass
