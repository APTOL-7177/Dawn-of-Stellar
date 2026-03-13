"""
폰트 아틀라스 - BDF/TTF 폰트 로드 및 글리프 캐시

pygame.freetype를 사용하여 폰트를 로드하고,
글리프를 셀 크기에 맞게 렌더링하여 캐시.
CJK 문자는 2셀 폭으로 처리.
"""

import os
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pygame
import pygame.freetype

from src.core.logger import get_logger

logger = get_logger("font_atlas")


def is_wide_char(ch: int) -> bool:
    """2셀 폭 문자 여부 판별

    BDF FONTBOUNDINGBOX(18px)가 한글(12px)을 포함하므로
    모든 글리프가 1셀에 들어감. 항상 False 반환.
    (향후 FONTBOUNDINGBOX보다 넓은 폰트 사용 시 재활성화)
    """
    return False


class FontAtlas:
    """
    폰트 글리프 아틀라스

    BDF 또는 TTF 폰트를 로드하고 글리프를 셀 크기에 맞게
    pygame.Surface로 캐시합니다.
    """

    def __init__(self) -> None:
        if not pygame.freetype.was_init():
            pygame.freetype.init()

        self.font: Optional[pygame.freetype.Font] = None
        self.tile_width: int = 0
        self.tile_height: int = 0
        self._glyph_cache: Dict[int, pygame.Surface] = {}
        self._wide_glyph_cache: Dict[int, pygame.Surface] = {}
        self._font_path: str = ""

    # ------------------------------------------------------------------
    # 폰트 로드
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_bdf_bbox(path: str) -> Optional[Tuple[int, int]]:
        """BDF 파일에서 FONTBOUNDINGBOX 읽기 → (width, height)"""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith('FONTBOUNDINGBOX'):
                        parts = line.split()
                        if len(parts) >= 3:
                            return int(parts[1]), int(parts[2])
                    if line.startswith('CHARS'):
                        break  # 헤더 끝
        except Exception:
            pass
        return None

    def load_bdf(self, path: str) -> bool:
        """BDF 비트맵 폰트 로드"""
        try:
            self.font = pygame.freetype.Font(path)
            self.font.origin = False  # 단순 top-left 좌표 사용

            # BDF FONTBOUNDINGBOX에서 타일 크기 결정 (tcod과 동일 방식)
            bbox = self._parse_bdf_bbox(path)
            if bbox and bbox[0] > 0 and bbox[1] > 0:
                self.tile_width = bbox[0]
                self.tile_height = bbox[1]
            else:
                # 폴백: freetype 메트릭
                metrics = self.font.get_metrics("M")
                if metrics and metrics[0]:
                    self.tile_width = int(metrics[0][4])
                    self.tile_height = int(
                        self.font.get_sized_ascender() - self.font.get_sized_descender()
                    )
                else:
                    surf, rect = self.font.render("A", fgcolor=(255, 255, 255))
                    self.tile_width = rect.width
                    self.tile_height = rect.height

            if self.tile_width <= 0 or self.tile_height <= 0:
                self.tile_width = max(self.tile_width, 8)
                self.tile_height = max(self.tile_height, 16)

            self._font_path = path
            logger.info(
                f"BDF 폰트 로드: {path}, "
                f"셀 크기: {self.tile_width}x{self.tile_height}"
            )
            return True
        except Exception as e:
            logger.error(f"BDF 폰트 로드 실패: {path}, {e}")
            return False

    def load_truetype(self, path: str, tile_width: int, tile_height: int) -> bool:
        """TrueType/OpenType 폰트 로드"""
        try:
            self.font = pygame.freetype.Font(path)
            self.font.origin = False  # 단순 top-left 좌표 사용
            self.tile_width = tile_width
            self.tile_height = tile_height

            # 폰트 크기를 셀 높이에 맞춤
            self.font.size = tile_height

            # 실제 글리프가 셀에 맞는지 확인하고 크기 조정
            metrics = self.font.get_metrics("M")
            if metrics and metrics[0]:
                actual_advance = int(metrics[0][4])
                if actual_advance > 0 and actual_advance != tile_width:
                    scale = tile_width / actual_advance
                    self.font.size = int(tile_height * scale)

            self._font_path = path
            logger.info(
                f"TTF 폰트 로드: {path}, "
                f"셀 크기: {self.tile_width}x{self.tile_height}"
            )
            return True
        except Exception as e:
            logger.error(f"TTF 폰트 로드 실패: {path}, {e}")
            return False

    # ------------------------------------------------------------------
    # 글리프 렌더링
    # ------------------------------------------------------------------

    def _render_glyph(self, ch: int, wide: bool = False) -> pygame.Surface:
        """단일 글리프를 셀 크기 Surface로 렌더링 (흰색, 투명 배경)"""
        w = self.tile_width * (2 if wide else 1)
        h = self.tile_height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        if self.font is None or ch < 0x20:
            return surf

        try:
            c = chr(ch)
            # origin=False: render()가 top-left 기준 Surface와 Rect 반환
            glyph_surf, glyph_rect = self.font.render(c, fgcolor=(255, 255, 255))

            # 셀 중앙 정렬 (수평 + 수직)
            x = max(0, (w - glyph_rect.width) // 2)
            y = max(0, (h - glyph_rect.height) // 2)

            surf.blit(glyph_surf, (x, y))
        except Exception:
            pass

        return surf

    def get_glyph(self, ch: int) -> pygame.Surface:
        """글리프 Surface 반환 (캐시)"""
        if ch in self._glyph_cache:
            return self._glyph_cache[ch]

        wide = is_wide_char(ch)
        if wide and ch in self._wide_glyph_cache:
            return self._wide_glyph_cache[ch]

        surf = self._render_glyph(ch, wide=wide)
        if wide:
            self._wide_glyph_cache[ch] = surf
        else:
            self._glyph_cache[ch] = surf
        return surf

    def render_cell(
        self,
        target: pygame.Surface,
        px: int,
        py: int,
        ch: int,
        fg: Tuple[int, int, int],
        bg: Tuple[int, int, int],
    ) -> None:
        """셀 하나를 target Surface에 렌더링

        Args:
            target: 대상 Surface
            px, py: 픽셀 좌표
            ch: 문자 코드포인트
            fg: 전경색 (R, G, B)
            bg: 배경색 (R, G, B)
        """
        wide = is_wide_char(ch)
        w = self.tile_width * (2 if wide else 1)
        h = self.tile_height

        # 배경 채우기
        target.fill(bg, (px, py, w, h))

        # 공백이면 배경만
        if ch <= 0x20:
            return

        # 글리프 렌더링
        glyph = self.get_glyph(ch)

        # fg 색상 적용 (tint)
        tinted = glyph.copy()
        tinted.fill(fg + (0,), special_flags=pygame.BLEND_RGB_MULT)

        target.blit(tinted, (px, py))

    def clear_cache(self) -> None:
        """글리프 캐시 초기화"""
        self._glyph_cache.clear()
        self._wide_glyph_cache.clear()

    @property
    def is_loaded(self) -> bool:
        return self.font is not None and self.tile_width > 0 and self.tile_height > 0
