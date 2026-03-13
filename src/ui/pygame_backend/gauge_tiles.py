"""
게이지 타일 렌더러 - PUA 코드포인트 → pygame.Surface 직접 렌더링

tcod 타일셋 없이 pygame 직접 픽셀 렌더링으로 32분할 정밀 게이지 복원.
기존 gauge_tileset.py의 PUA 코드포인트 매핑을 동일하게 사용.
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pygame

from src.core.logger import get_logger

logger = get_logger("gauge_tiles")

# gauge_tileset.py와 동일한 상수
GAUGE_TILE_BASE = 0xE000
GAUGE_DIVISIONS = 32

# 색상 인덱스 (gauge_tileset.py와 동일)
COLOR_MAP = {
    0: 'hp_high',
    1: 'hp_mid',
    2: 'hp_low',
    3: 'hp_bg',
    4: 'mp_fill',
    5: 'mp_bg',
    6: 'brv_fill',
    7: 'brv_bg',
    8: 'damage_trail',
    9: 'wound',
    10: 'atb_fill',
    11: 'cast_fill',
    12: 'wound_stripe',
    13: 'wound_fill_right',
}

# 특수 타일 타입 (오른쪽 채움, 빗금)
SPECIAL_TYPES = {'wound_stripe', 'wound_fill_right'}

# 경계 타일 범위 (Supplementary Private Use Area-A)
BOUNDARY_TILE_START = 0xF0000
BOUNDARY_TILE_END = 0xFFFFD

# 경계 타일 메타데이터 레지스트리 (GaugeTileManager가 등록, PygameGaugeTileManager가 읽음)
# key: codepoint, value: dict with hp_pixels, wound_pixels, hp_color, bg_color,
#   wound_stripe_color, cell_index, cell_start, wound_start_pixel
_boundary_tile_registry: Dict[int, Dict] = {}


def register_boundary_tile(codepoint: int, meta: Dict) -> None:
    """경계 타일 메타데이터 등록"""
    _boundary_tile_registry[codepoint] = meta


def get_boundary_tile_meta(codepoint: int) -> Optional[Dict]:
    """경계 타일 메타데이터 조회"""
    return _boundary_tile_registry.get(codepoint)

NUM_COLORS = len(COLOR_MAP)
STRIDE = GAUGE_DIVISIONS + 1  # 33 (0~32 fill levels)


def is_gauge_tile(ch: int) -> bool:
    """PUA 게이지 타일 코드포인트 여부"""
    if GAUGE_TILE_BASE <= ch < GAUGE_TILE_BASE + NUM_COLORS * STRIDE:
        return True
    if BOUNDARY_TILE_START <= ch <= BOUNDARY_TILE_END:
        return True
    return False


def _decode_codepoint(ch: int) -> Tuple[int, int]:
    """PUA 코드포인트 → (color_index, fill_level) 디코딩"""
    offset = ch - GAUGE_TILE_BASE
    color_index = offset // STRIDE
    fill_level = offset % STRIDE
    return color_index, fill_level


class PygameGaugeTileManager:
    """pygame 직접 렌더링 게이지 타일 관리자

    PUA 코드포인트를 받아 해당 게이지 패턴을 pygame.Surface로 렌더링.
    tcod tileset 의존 없이 동작.
    """

    _instance: Optional['PygameGaugeTileManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._tile_cache: Dict[Tuple[int, Tuple, Tuple], pygame.Surface] = {}
        self._tile_width: int = 10
        self._tile_height: int = 16
        self._initialized = True

    def set_tile_size(self, width: int, height: int) -> None:
        """타일 크기 설정 (폰트 아틀라스와 동기화)"""
        if width != self._tile_width or height != self._tile_height:
            self._tile_width = width
            self._tile_height = height
            self._tile_cache.clear()
            logger.info(f"게이지 타일 크기 설정: {width}x{height}")

    def get_tile_surface(
        self,
        ch: int,
        fg: Tuple[int, int, int],
        bg: Tuple[int, int, int],
    ) -> pygame.Surface:
        """PUA 코드포인트에 해당하는 게이지 타일 Surface 반환

        Args:
            ch: PUA 코드포인트
            fg: 전경색 (채움 색상)
            bg: 배경색

        Returns:
            렌더링된 pygame.Surface (tile_width x tile_height)
        """
        cache_key = (ch, fg, bg)
        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        tw = self._tile_width
        th = self._tile_height

        surf = pygame.Surface((tw, th))
        surf.fill(bg)

        if BOUNDARY_TILE_START <= ch <= BOUNDARY_TILE_END:
            meta = get_boundary_tile_meta(ch)
            if meta:
                self._render_boundary_tile(surf, tw, th, meta)
            else:
                # 메타데이터 없으면 폴백: fg로 채움
                surf.fill(fg)
            # 경계 타일은 캐시하지 않음 (메타데이터가 동적으로 변할 수 있음)
            return surf

        color_index, fill_level = _decode_codepoint(ch)
        color_name = COLOR_MAP.get(color_index, '')

        if color_name == 'wound_stripe':
            self._render_stripe(surf, tw, th, fill_level, fg, bg)
        elif color_name == 'wound_fill_right':
            self._render_right_fill(surf, tw, th, fill_level, fg, bg)
        else:
            self._render_left_fill(surf, tw, th, fill_level, fg, bg)

        self._tile_cache[cache_key] = surf
        return surf

    def render_gauge_cell(
        self,
        target: pygame.Surface,
        px: int,
        py: int,
        ch: int,
        fg: Tuple[int, int, int],
        bg: Tuple[int, int, int],
    ) -> None:
        """게이지 셀을 target Surface에 직접 렌더링

        font_atlas.render_cell() 대체용. PUA 코드포인트 전용.
        """
        tile = self.get_tile_surface(ch, fg, bg)
        target.blit(tile, (px, py))

    # ------------------------------------------------------------------
    # 내부 렌더링
    # ------------------------------------------------------------------

    def _render_left_fill(
        self, surf: pygame.Surface, tw: int, th: int,
        fill_level: int, fg: Tuple[int, int, int], bg: Tuple[int, int, int],
    ) -> None:
        """왼쪽에서 오른쪽으로 채움 (기본 게이지)"""
        fill_pixels = int((fill_level / GAUGE_DIVISIONS) * tw)
        if fill_pixels > 0:
            surf.fill(fg, (0, 0, fill_pixels, th))

    def _render_right_fill(
        self, surf: pygame.Surface, tw: int, th: int,
        fill_level: int, fg: Tuple[int, int, int], bg: Tuple[int, int, int],
    ) -> None:
        """오른쪽에서 왼쪽으로 채움 (상처 영역)"""
        fill_pixels = int((fill_level / GAUGE_DIVISIONS) * tw)
        start_x = tw - fill_pixels
        if fill_pixels > 0:
            surf.fill(fg, (start_x, 0, fill_pixels, th))

    def _render_stripe(
        self, surf: pygame.Surface, tw: int, th: int,
        fill_level: int, fg: Tuple[int, int, int], bg: Tuple[int, int, int],
    ) -> None:
        """빗금 패턴 (상처 빗금)

        fill_level을 셀 인덱스(오프셋)으로 사용하여 인접 셀과 빗금 연속.
        """
        stripe_width = 2
        stripe_gap = 3
        stripe_period = stripe_width + stripe_gap

        x_offset = (fill_level * tw) % stripe_period

        # 픽셀 단위 빗금 렌더링
        pixels = pygame.PixelArray(surf)
        fg_color = surf.map_rgb(fg)
        # bg는 이미 fill됨

        for py_local in range(th):
            for px_local in range(tw):
                if ((x_offset + px_local) + py_local) % stripe_period < stripe_width:
                    pixels[px_local, py_local] = fg_color

        pixels.close()

    def _render_boundary_tile(
        self, surf: pygame.Surface, tw: int, th: int, meta: Dict
    ) -> None:
        """경계 타일 렌더링 (HP + 빈 공간 + 상처 빗금이 한 셀에 있는 경우)"""
        hp_pixels = meta.get('hp_pixels', 0)
        wound_pixels = meta.get('wound_pixels', 0)
        hp_color = meta.get('hp_color', (50, 220, 50))
        bg_color = meta.get('bg_color', (20, 80, 20))
        wound_stripe_color = meta.get('wound_stripe_color', (0, 0, 0))
        cell_index = meta.get('cell_index', 0)
        cell_start = meta.get('cell_start', 0)
        wound_start_pixel = meta.get('wound_start_pixel', 0)

        # divisions → tile_width 스케일링
        scale = tw / GAUGE_DIVISIONS if GAUGE_DIVISIONS > 0 else 1.0
        actual_hp = max(0, min(tw, int(hp_pixels * scale + 0.5)))
        actual_wound = max(0, min(tw, int(wound_pixels * scale + 0.5)))

        # HP + 상처가 셀 전체를 거의 채우면 간격 제거
        if hp_pixels + wound_pixels >= GAUGE_DIVISIONS - 1:
            actual_wound = tw - actual_hp
            actual_wound = max(0, min(tw, actual_wound))

        # 상처 시작 위치 (셀 내)
        if wound_start_pixel > 0:
            if wound_start_pixel < cell_start:
                wound_start_in_cell = 0
            else:
                wound_start_in_cell = max(0, min(tw, int((wound_start_pixel - cell_start) * scale + 0.5)))
        else:
            wound_start_in_cell = tw - actual_wound if actual_wound > 0 else tw

        # 배경 채우기
        surf.fill(bg_color)

        # HP 영역 (왼쪽)
        hp_end = min(actual_hp, wound_start_in_cell)
        if hp_end > 0:
            surf.fill(hp_color, (0, 0, hp_end, th))

        # 상처 영역 (빗금 패턴)
        if actual_wound > 0 and wound_start_in_cell < tw:
            stripe_width = 2
            stripe_gap = 3
            stripe_period = stripe_width + stripe_gap
            x_offset = (cell_index * tw) % stripe_period

            # 상처 영역 배경 (게이지 배경색 사용)
            surf.fill(bg_color, (wound_start_in_cell, 0, tw - wound_start_in_cell, th))

            # 빗금 패턴
            pixels = pygame.PixelArray(surf)
            stripe_col = surf.map_rgb(wound_stripe_color)
            for py_local in range(th):
                for px_local in range(wound_start_in_cell, tw):
                    if ((x_offset + px_local) + py_local) % stripe_period < stripe_width:
                        pixels[px_local, py_local] = stripe_col
            pixels.close()

    def clear_cache(self) -> None:
        """타일 캐시 초기화"""
        self._tile_cache.clear()


def get_gauge_tile_manager() -> PygameGaugeTileManager:
    """싱글톤 게이지 타일 관리자 반환"""
    return PygameGaugeTileManager()
