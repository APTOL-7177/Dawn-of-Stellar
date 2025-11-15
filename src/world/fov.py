"""
FOV (Field of View) 시스템

플레이어 주변 시야 계산 (레이캐스팅)
"""

from typing import Set, Tuple
import math

from src.world.dungeon_generator import DungeonMap
from src.world.tile import TileType


class FOVSystem:
    """시야 시스템"""

    def __init__(self, default_radius: int = 3):
        """
        Args:
            default_radius: 기본 시야 반지름
        """
        self.default_radius = default_radius
        self.visible_tiles: Set[Tuple[int, int]] = set()

    def compute_fov(
        self,
        dungeon: DungeonMap,
        origin_x: int,
        origin_y: int,
        radius: int = None
    ) -> Set[Tuple[int, int]]:
        """
        FOV 계산 (Shadowcasting 알고리즘)

        Args:
            dungeon: 던전 맵
            origin_x: 플레이어 X 위치
            origin_y: 플레이어 Y 위치
            radius: 시야 반지름 (None이면 default 사용)

        Returns:
            보이는 타일 좌표 set
        """
        if radius is None:
            radius = self.default_radius

        self.visible_tiles.clear()

        # 플레이어 위치는 항상 보임
        self.visible_tiles.add((origin_x, origin_y))

        # 8방향 스캔
        for octant in range(8):
            self._cast_light(
                dungeon,
                origin_x,
                origin_y,
                radius,
                1,  # start row
                1.0,  # start slope
                0.0,  # end slope
                octant
            )

        # 탐험 마크 업데이트
        for x, y in self.visible_tiles:
            tile = dungeon.get_tile(x, y)
            if tile:
                tile.explored = True
                tile.visible = True

        return self.visible_tiles

    def _cast_light(
        self,
        dungeon: DungeonMap,
        cx: int,
        cy: int,
        radius: int,
        row: int,
        start_slope: float,
        end_slope: float,
        octant: int
    ):
        """
        Shadowcasting 재귀 함수

        Args:
            cx, cy: 중심 좌표
            radius: 반지름
            row: 현재 행
            start_slope: 시작 기울기
            end_slope: 끝 기울기
            octant: 팔분면 (0-7)
        """
        if start_slope < end_slope:
            return

        radius_squared = radius * radius

        for j in range(row, radius + 1):
            dx = -j - 1
            dy = -j
            blocked = False
            new_start = 0.0

            while dx <= 0:
                dx += 1

                # 좌표 변환 (octant에 따라)
                mx, my = self._transform_octant(cx, cy, dx, dy, octant)

                # 범위 체크
                if not (0 <= mx < dungeon.width and 0 <= my < dungeon.height):
                    continue

                # 거리 체크
                distance = dx * dx + dy * dy
                if distance > radius_squared:
                    continue

                l_slope = (dx - 0.5) / (dy + 0.5)
                r_slope = (dx + 0.5) / (dy - 0.5)

                if start_slope < r_slope:
                    continue
                elif end_slope > l_slope:
                    break

                # 타일 보이게
                self.visible_tiles.add((mx, my))

                # 블록 체크
                tile = dungeon.get_tile(mx, my)
                if tile and not tile.transparent:
                    if blocked:
                        new_start = r_slope
                    else:
                        blocked = True
                        self._cast_light(
                            dungeon, cx, cy, radius,
                            j + 1, start_slope, l_slope, octant
                        )
                        new_start = r_slope
                else:
                    if blocked:
                        blocked = False
                        start_slope = new_start

            if blocked:
                break

    def _transform_octant(
        self,
        cx: int,
        cy: int,
        dx: int,
        dy: int,
        octant: int
    ) -> Tuple[int, int]:
        """팔분면에 따른 좌표 변환"""
        if octant == 0:
            return (cx + dx, cy - dy)
        elif octant == 1:
            return (cx + dy, cy - dx)
        elif octant == 2:
            return (cx - dy, cy - dx)
        elif octant == 3:
            return (cx - dx, cy - dy)
        elif octant == 4:
            return (cx - dx, cy + dy)
        elif octant == 5:
            return (cx - dy, cy + dx)
        elif octant == 6:
            return (cx + dy, cy + dx)
        elif octant == 7:
            return (cx + dx, cy + dy)

        return (cx, cy)

    def clear_visibility(self, dungeon: DungeonMap):
        """현재 프레임 가시성 초기화"""
        for y in range(dungeon.height):
            for x in range(dungeon.width):
                tile = dungeon.get_tile(x, y)
                if tile:
                    tile.visible = False

    def get_visible_radius_with_modifiers(self, base_radius: int, modifiers: dict) -> int:
        """
        보정된 시야 반지름 계산

        Args:
            base_radius: 기본 반지름
            modifiers: 보정값 dict (예: {"torch": 2, "night_vision": 1})

        Returns:
            최종 반지름
        """
        total = base_radius
        for bonus in modifiers.values():
            total += bonus

        # 최소 1, 최대 10
        return max(1, min(10, total))
