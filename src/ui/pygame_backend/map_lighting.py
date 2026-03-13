"""
맵 동적 조명 시스템

던전 맵에 셀 단위 동적 라이팅을 적용합니다.
- 플레이어 주변 따뜻한 광원 (횃불)
- 마법/아이템 발광
- FOV 연동 라이트맵
- 횃불 깜빡임 애니메이션

사용법:
    lighting = MapLighting()
    lighting.update(dt, player_x, player_y, dungeon)
    # map_renderer.render() 내에서:
    fg, bg = lighting.apply_to_tile(map_x, map_y, fg, bg, tile_visible)
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.core.logger import get_logger

logger = get_logger("map_lighting")


@dataclass
class MapLight:
    """맵 위의 광원"""
    x: float               # 맵 좌표
    y: float
    radius: float = 6.0    # 조명 반경 (타일 단위)
    color: Tuple[int, int, int] = (255, 200, 130)  # 광원 색상
    intensity: float = 1.0  # 밝기 (0.0 ~ 1.0)
    flicker: bool = False   # 깜빡임 효과
    pulse: bool = False     # 맥동 효과
    name: str = ""          # 식별용 이름

    # 내부 상태
    _flicker_offset: float = field(default_factory=lambda: random.uniform(0, math.tau))
    _pulse_phase: float = field(default_factory=lambda: random.uniform(0, math.tau))


# 프리셋 광원들
def torch_light(x: float, y: float) -> MapLight:
    """횃불 광원 (따뜻한 주황, 깜빡임)"""
    return MapLight(
        x=x, y=y, radius=5.5,
        color=(255, 180, 100), intensity=0.9,
        flicker=True, name="torch",
    )


def player_light(x: float, y: float) -> MapLight:
    """플레이어 기본 광원 (부드러운 흰색)"""
    return MapLight(
        x=x, y=y, radius=7.0,
        color=(220, 220, 255), intensity=0.85,
        flicker=False, name="player",
    )


def magic_light(x: float, y: float, color: Tuple[int, int, int] = (100, 150, 255)) -> MapLight:
    """마법 광원 (파란/보라 계열, 맥동)"""
    return MapLight(
        x=x, y=y, radius=4.0,
        color=color, intensity=0.7,
        pulse=True, name="magic",
    )


def crystal_light(x: float, y: float) -> MapLight:
    """수정 광원 (차가운 파랑)"""
    return MapLight(
        x=x, y=y, radius=3.5,
        color=(100, 200, 255), intensity=0.6,
        pulse=True, name="crystal",
    )


def fire_light(x: float, y: float) -> MapLight:
    """불꽃 광원 (강한 빨강/주황)"""
    return MapLight(
        x=x, y=y, radius=6.0,
        color=(255, 120, 50), intensity=1.0,
        flicker=True, name="fire",
    )


class MapLighting:
    """
    맵 동적 조명 시스템

    매 프레임 라이트맵을 계산하고, map_renderer가 각 타일 색상에 적용.
    """

    def __init__(
        self,
        ambient: Tuple[int, int, int] = (20, 18, 30),
        enabled: bool = True,
    ) -> None:
        self.ambient = ambient  # 주변광 (조명 없는 영역의 기본 밝기)
        self.enabled = enabled
        self._lights: List[MapLight] = []
        self._player_light: Optional[MapLight] = None
        self._time: float = 0.0

        # 라이트맵 캐시: (map_x, map_y) → (r, g, b) 밝기 승수
        self._lightmap: Dict[Tuple[int, int], Tuple[float, float, float]] = {}
        self._lightmap_dirty = True

    # ------------------------------------------------------------------
    # 광원 관리
    # ------------------------------------------------------------------

    def add_light(self, light: MapLight) -> None:
        """광원 추가"""
        self._lights.append(light)
        self._lightmap_dirty = True

    def remove_light(self, light: MapLight) -> None:
        """광원 제거"""
        if light in self._lights:
            self._lights.remove(light)
            self._lightmap_dirty = True

    def clear_lights(self) -> None:
        """모든 광원 제거 (플레이어 광원 포함)"""
        self._lights.clear()
        self._player_light = None
        self._lightmap_dirty = True

    def set_player_position(self, x: float, y: float) -> None:
        """플레이어 위치 업데이트 (자동 광원)"""
        if self._player_light is None:
            self._player_light = player_light(x, y)
        else:
            self._player_light.x = x
            self._player_light.y = y
        self._lightmap_dirty = True

    # ------------------------------------------------------------------
    # 던전 기반 자동 광원 배치
    # ------------------------------------------------------------------

    def auto_place_lights(self, dungeon) -> None:
        """던전 구조에서 자동으로 횃불/수정 배치

        방 모서리, 복도 교차점, 특수 타일에 광원을 배치합니다.
        """
        # 기존 자동 광원 제거
        self._lights = [l for l in self._lights if l.name not in ("torch", "crystal", "fire")]

        if not hasattr(dungeon, 'rooms'):
            return

        for room in dungeon.rooms:
            # 방 모서리 4곳에 횃불
            corners = [
                (room.x + 1, room.y + 1),
                (room.x + room.width - 2, room.y + 1),
                (room.x + 1, room.y + room.height - 2),
                (room.x + room.width - 2, room.y + room.height - 2),
            ]
            for cx, cy in corners:
                if 0 <= cx < dungeon.width and 0 <= cy < dungeon.height:
                    self._lights.append(torch_light(cx, cy))

        # 보스 방이 있으면 강한 불꽃 광원
        if hasattr(dungeon, 'boss_room') and dungeon.boss_room:
            br = dungeon.boss_room
            center_x = br.x + br.width // 2
            center_y = br.y + br.height // 2
            self._lights.append(fire_light(center_x, center_y))

        self._lightmap_dirty = True
        logger.debug(f"자동 광원 배치: {len(self._lights)}개")

    # ------------------------------------------------------------------
    # 프레임 업데이트
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """매 프레임 호출 — 애니메이션 업데이트"""
        if not self.enabled:
            return

        self._time += dt
        # 깜빡임/맥동 → 매 프레임 라이트맵 갱신 필요
        self._lightmap_dirty = True

    # ------------------------------------------------------------------
    # 라이트맵 계산
    # ------------------------------------------------------------------

    def _rebuild_lightmap(
        self,
        camera_x: int, camera_y: int,
        view_width: int, view_height: int,
    ) -> None:
        """보이는 영역의 라이트맵 재계산"""
        self._lightmap.clear()

        all_lights = list(self._lights)
        if self._player_light:
            all_lights.append(self._player_light)

        t = self._time

        for light in all_lights:
            # 애니메이션 적용된 intensity 계산
            intensity = light.intensity
            if light.flicker:
                # 횃불 깜빡임: 사인 파형 + 랜덤 노이즈
                flicker = (
                    0.85
                    + 0.10 * math.sin(t * 5.0 + light._flicker_offset)
                    + 0.05 * math.sin(t * 13.0 + light._flicker_offset * 2.3)
                )
                intensity *= flicker

            if light.pulse:
                # 맥동: 느린 사인 파형
                pulse = 0.7 + 0.3 * math.sin(t * 2.0 + light._pulse_phase)
                intensity *= pulse

            intensity = max(0.0, min(1.0, intensity))

            # 광원 영향 범위 (정수 타일)
            r = int(math.ceil(light.radius))
            lx, ly = int(light.x), int(light.y)

            for dy in range(-r, r + 1):
                my = ly + dy
                if my < camera_y or my >= camera_y + view_height:
                    continue
                for dx in range(-r, r + 1):
                    mx = lx + dx
                    if mx < camera_x or mx >= camera_x + view_width:
                        continue

                    # 거리 기반 감쇠 (부드러운 원형)
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > light.radius:
                        continue

                    # 이차 감쇠 (더 자연스러운 빛)
                    falloff = 1.0 - (dist / light.radius)
                    falloff = falloff * falloff  # quadratic
                    brightness = intensity * falloff

                    # 광원 색상 적용 (0~1 범위의 RGB 승수)
                    lr = (light.color[0] / 255.0) * brightness
                    lg = (light.color[1] / 255.0) * brightness
                    lb = (light.color[2] / 255.0) * brightness

                    key = (mx, my)
                    if key in self._lightmap:
                        # 기존 조명에 더하기 (여러 광원 합성)
                        prev = self._lightmap[key]
                        self._lightmap[key] = (
                            min(1.0, prev[0] + lr),
                            min(1.0, prev[1] + lg),
                            min(1.0, prev[2] + lb),
                        )
                    else:
                        self._lightmap[key] = (lr, lg, lb)

    # ------------------------------------------------------------------
    # 타일 색상 적용
    # ------------------------------------------------------------------

    def apply_to_tile(
        self,
        map_x: int,
        map_y: int,
        fg: Tuple[int, int, int],
        bg: Tuple[int, int, int],
        tile_visible: bool,
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """타일의 fg/bg에 라이팅 적용

        Args:
            map_x, map_y: 맵 좌표
            fg, bg: 원래 타일 색상
            tile_visible: FOV에 보이는지 여부

        Returns:
            (조명 적용된 fg, 조명 적용된 bg)
        """
        if not self.enabled:
            return fg, bg

        if not tile_visible:
            # FOV 밖: 원래 어두운 처리 유지
            return fg, bg

        key = (map_x, map_y)
        if key in self._lightmap:
            light = self._lightmap[key]
            # 주변광 + 동적 조명
            ar = self.ambient[0] / 255.0
            ag = self.ambient[1] / 255.0
            ab = self.ambient[2] / 255.0

            # 최종 밝기 = ambient + dynamic light
            mr = min(1.0, ar + light[0])
            mg = min(1.0, ag + light[1])
            mb = min(1.0, ab + light[2])
        else:
            # 광원이 닿지 않는 영역: 주변광만
            mr = self.ambient[0] / 255.0
            mg = self.ambient[1] / 255.0
            mb = self.ambient[2] / 255.0

        # 색상에 밝기 승수 적용
        new_fg = (
            max(0, min(255, int(fg[0] * mr))),
            max(0, min(255, int(fg[1] * mg))),
            max(0, min(255, int(fg[2] * mb))),
        )
        new_bg = (
            max(0, min(255, int(bg[0] * mr))),
            max(0, min(255, int(bg[1] * mg))),
            max(0, min(255, int(bg[2] * mb))),
        )

        return new_fg, new_bg

    def prepare_frame(
        self,
        camera_x: int, camera_y: int,
        view_width: int, view_height: int,
    ) -> None:
        """프레임 시작 시 라이트맵 준비 (render 전에 호출)"""
        if not self.enabled:
            return
        if self._lightmap_dirty:
            self._rebuild_lightmap(camera_x, camera_y, view_width, view_height)
            self._lightmap_dirty = False
