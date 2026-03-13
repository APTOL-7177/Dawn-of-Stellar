"""
glitch.py - Cogmind 스타일 글리치 오버레이 이펙트

플레이어가 큰 피해를 받거나 시스템 이벤트 발생 시
화면에 시각적 노이즈/데이터 손상 아티팩트를 표시합니다.
trigger()로 순간 발동 후 페이드아웃하거나,
set_persistent()로 낮은 강도의 상시 글리치를 설정할 수 있습니다.

서브이펙트 (강도에 따라 조합):
  - 수평선 변위  : 화면의 임의 수평 슬라이스가 좌우로 밀림
  - 색채 분리    : 적색 채널 좌, 청색 채널 우 (크로마틱 어버레이션)
  - 블록 손상    : 임의 직사각 영역이 무작위 색상으로 채워짐
  - 스캔라인 깜빡임: 임의 수평선이 밝아지거나 어두워짐
  - 정적 노이즈 밴드: TV 스태틱 노이즈가 수평 띠 형태로 나타남
"""

import math
import random
from typing import List, Optional, Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.glitch")

# ── 강도 임계값 ────────────────────────────────────────────────────────────
_THRESH_MEDIUM: float = 0.3   # 이 이상: 수평 변위 + 정적 밴드 추가
_THRESH_HEAVY: float = 0.7    # 이 이상: 블록 손상 추가


class GlitchEffect(EffectLayer):
    """
    Cogmind 스타일 글리치 오버레이 이펙트

    EffectManager 파이프라인에서 CRT 이전, 플래시 이후에 적용하면
    레트로 데이터 손상 분위기를 연출할 수 있습니다.

    사용 예시::

        glitch = GlitchEffect()

        # 피격 시 강한 글리치 버스트
        glitch.trigger(intensity=0.9, duration=0.35)

        # 시스템 손상 상태의 상시 약한 글리치
        glitch.set_persistent(intensity=0.15)

        # 매 프레임
        glitch.update(dt)
        glitch.render(screen)
    """

    def __init__(self, enabled: bool = True) -> None:
        """
        Args:
            enabled: 이펙트 활성화 여부
        """
        super().__init__(enabled)

        # ── 순간 트리거 상태 ────────────────────────────────────────────
        self._burst_intensity: float = 0.0   # 현재 버스트 강도
        self._burst_duration: float = 0.0    # 남은 버스트 시간 (초)
        self._burst_total: float = 0.0       # 전체 버스트 시간 (감쇠 계산용)

        # ── 상시(persistent) 글리치 상태 ───────────────────────────────
        self._persistent_intensity: float = 0.0

        # ── 렌더링용 임시 Surface 캐시 ──────────────────────────────────
        # 크기가 같을 때 재사용하여 GC 압력 최소화
        self._work_surf: Optional[pygame.Surface] = None
        self._work_surf_size: Tuple[int, int] = (0, 0)

        # 색채 분리용 채널 Surface (R, B 각각)
        self._ch_surf: Optional[pygame.Surface] = None
        self._ch_surf_size: Tuple[int, int] = (0, 0)

        # 스캔라인/노이즈용 단일 행 Surface (너비만 맞으면 재사용)
        self._row_surf: Optional[pygame.Surface] = None
        self._row_surf_w: int = 0

        logger.debug("GlitchEffect 초기화 완료")

    # ── 공개 API ─────────────────────────────────────────────────────────

    def trigger(self, intensity: float = 1.0, duration: float = 0.3) -> None:
        """
        순간 글리치 버스트를 트리거합니다.

        이미 버스트 중이면 더 강한 쪽으로 갱신합니다.

        Args:
            intensity: 글리치 강도 (0.0~1.0)
            duration:  버스트 지속 시간 (초)
        """
        if not self.enabled:
            return
        intensity = max(0.0, min(1.0, intensity))
        duration = max(0.0, duration)
        if intensity >= self._burst_intensity or self._burst_duration <= 0:
            self._burst_intensity = intensity
            self._burst_duration = duration
            self._burst_total = duration
        logger.debug(f"글리치 트리거: intensity={intensity:.2f}, duration={duration:.2f}s")

    def set_persistent(self, intensity: float = 0.0) -> None:
        """
        상시 글리치 강도를 설정합니다.

        시스템 손상 등 지속 상태를 표현할 때 사용합니다.
        0.0으로 설정하면 비활성화됩니다.

        Args:
            intensity: 상시 글리치 강도 (0.0=없음, 1.0=최대)
        """
        self._persistent_intensity = max(0.0, min(1.0, intensity))

    @property
    def is_active(self) -> bool:
        """현재 글리치 효과가 활성화된 상태인지 여부"""
        return (
            self.enabled
            and (self._burst_duration > 0 or self._persistent_intensity > 0.0)
        )

    # ── EffectLayer 인터페이스 ───────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        버스트 타이머를 갱신합니다.

        Args:
            dt: 경과 시간 (초)
        """
        if not self.enabled:
            return
        if self._burst_duration > 0:
            self._burst_duration -= dt
            if self._burst_duration < 0:
                self._burst_duration = 0.0
                self._burst_intensity = 0.0

    def render(self, surface: pygame.Surface) -> None:
        """
        글리치 오버레이를 surface에 직접 적용합니다.

        실제 강도 = max(버스트 감쇠 강도, 상시 강도)

        Args:
            surface: 렌더링 대상 pygame Surface
        """
        if not self.enabled:
            return

        intensity = self._effective_intensity()
        if intensity <= 0.0:
            return

        w, h = surface.get_size()
        if w <= 0 or h <= 0:
            return

        try:
            self._apply_glitch(surface, w, h, intensity)
        except Exception as exc:
            # 렌더링 오류가 게임 루프를 방해하지 않도록 조용히 처리
            logger.warning(f"글리치 렌더링 오류: {exc}")

    # ── 내부 구현 ────────────────────────────────────────────────────────

    def _effective_intensity(self) -> float:
        """버스트(감쇠 적용) 강도와 상시 강도 중 큰 값을 반환합니다."""
        if self._burst_duration > 0 and self._burst_total > 0:
            decay = self._burst_duration / self._burst_total
            burst = self._burst_intensity * decay
        else:
            burst = 0.0
        return max(burst, self._persistent_intensity)

    def _apply_glitch(
        self, surface: pygame.Surface, w: int, h: int, intensity: float
    ) -> None:
        """
        강도에 따라 서브이펙트를 조합하여 surface에 적용합니다.

        Args:
            surface:   렌더링 대상
            w:         Surface 너비 (픽셀)
            h:         Surface 높이 (픽셀)
            intensity: 유효 글리치 강도 (0.0~1.0)
        """
        # ── 1. 스캔라인 깜빡임 (모든 강도에서 동작) ─────────────────────
        self._scanline_flicker(surface, w, h, intensity)

        # ── 2. 색채 분리 (크로마틱 어버레이션) ──────────────────────────
        self._chromatic_aberration(surface, w, h, intensity)

        # ── 3. 수평선 변위 + 정적 노이즈 밴드 (중간 이상) ───────────────
        if intensity >= _THRESH_MEDIUM:
            self._horizontal_displacement(surface, w, h, intensity)
            self._static_noise_bands(surface, w, h, intensity)

        # ── 4. 블록 손상 (강한 강도) ─────────────────────────────────
        if intensity >= _THRESH_HEAVY:
            self._block_corruption(surface, w, h, intensity)

    # ── 서브이펙트 ───────────────────────────────────────────────────────

    def _scanline_flicker(
        self, surface: pygame.Surface, w: int, h: int, intensity: float
    ) -> None:
        """
        임의 수평 스캔라인을 밝히거나 어둡게 합니다.

        강도에 비례해 깜빡이는 라인 수와 밝기 변화폭이 커집니다.

        Args:
            surface:   렌더링 대상
            w:         너비 (픽셀)
            h:         높이 (픽셀)
            intensity: 글리치 강도 (0.0~1.0)
        """
        count = max(1, int(intensity * 12))
        # 확률적 발동: 낮은 강도에서는 항상 표시하지 않음
        if random.random() > intensity * 0.9 + 0.1:
            count = max(1, count // 3)

        # 1픽셀 높이 임시 Surface로 BLEND blit (draw.line은 special_flags 미지원)
        line_surf = pygame.Surface((w, 1))

        for _ in range(count):
            y = random.randint(0, h - 1)
            # 밝아지거나 어두워짐 (50:50)
            if random.random() < 0.5:
                # 밝게: BLEND_ADD로 흰색 선 추가
                val = int(random.uniform(30, 120) * intensity)
                line_surf.fill((val, val, val))
                surface.blit(line_surf, (0, y), special_flags=pygame.BLEND_ADD)
            else:
                # 어둡게: BLEND_MULT로 어두운 선 곱하기
                val = max(0, 255 - int(random.uniform(60, 180) * intensity))
                line_surf.fill((val, val, val))
                surface.blit(line_surf, (0, y), special_flags=pygame.BLEND_MULT)

    def _chromatic_aberration(
        self, surface: pygame.Surface, w: int, h: int, intensity: float
    ) -> None:
        """
        적색 채널을 왼쪽, 청색 채널을 오른쪽으로 이동하여 RGB 분리 효과를 냅니다.

        낮은 강도에서는 1~2 픽셀 오프셋으로 미묘하게 표현됩니다.

        Args:
            surface:   렌더링 대상
            w:         너비 (픽셀)
            h:         높이 (픽셀)
            intensity: 글리치 강도 (0.0~1.0)
        """
        offset = max(1, int(intensity * 6))
        if offset < 1:
            return

        # 채널 Surface 캐시 관리 (SRCALPHA 필요)
        if self._ch_surf_size != (w, h) or self._ch_surf is None:
            self._ch_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            self._ch_surf_size = (w, h)

        ch = self._ch_surf

        # 적색 채널: surface를 왼쪽으로 offset 이동 후 R만 추출
        ch.fill((0, 0, 0, 0))
        ch.blit(surface, (-offset, 0))
        # R만 남기기 위해 G, B 채널을 0으로 덮음
        # pygame에 채널 마스킹 기능이 없으므로 BLEND_MULT 활용
        # (255, 0, 0, 255) 마스크로 곱하면 R만 생존
        ch.fill((255, 0, 0, 80), special_flags=pygame.BLEND_MULT)
        surface.blit(ch, (0, 0), special_flags=pygame.BLEND_ADD)

        # 청색 채널: surface를 오른쪽으로 offset 이동 후 B만 추출
        ch.fill((0, 0, 0, 0))
        ch.blit(surface, (offset, 0))
        ch.fill((0, 0, 255, 80), special_flags=pygame.BLEND_MULT)
        surface.blit(ch, (0, 0), special_flags=pygame.BLEND_ADD)

    def _horizontal_displacement(
        self, surface: pygame.Surface, w: int, h: int, intensity: float
    ) -> None:
        """
        화면을 임의 수평 밴드로 분할하여 각 밴드를 좌우로 이동시킵니다.

        밴드 수와 최대 이동폭은 강도에 비례합니다.

        Args:
            surface:   렌더링 대상
            w:         너비 (픽셀)
            h:         높이 (픽셀)
            intensity: 글리치 강도 (0.0~1.0)
        """
        # 작업 Surface 준비
        if self._work_surf_size != (w, h) or self._work_surf is None:
            self._work_surf = pygame.Surface((w, h))
            self._work_surf_size = (w, h)

        work = self._work_surf
        work.blit(surface, (0, 0))

        # 밴드 수: 3~8개 (강도 비례)
        band_count = random.randint(3, max(3, int(3 + intensity * 5)))
        # 최대 변위: 강도에 비례 (최대 약 w의 5%)
        max_shift = max(2, int(w * 0.05 * intensity))

        # 밴드 경계를 무작위로 생성
        band_ys: List[int] = sorted(random.sample(range(1, h), min(band_count, h - 1)))
        band_ys = [0] + band_ys + [h]

        for i in range(len(band_ys) - 1):
            y0 = band_ys[i]
            y1 = band_ys[i + 1]
            band_h = y1 - y0
            if band_h <= 0:
                continue
            # 50% 확률로만 이 밴드를 변위시킴
            if random.random() < 0.5:
                continue

            shift = random.randint(-max_shift, max_shift)
            if shift == 0:
                continue

            # 해당 밴드를 surface에서 잘라 shift만큼 이동해서 다시 그림
            src_rect = pygame.Rect(0, y0, w, band_h)
            row_surf = work.subsurface(src_rect)

            # 이동 후 빈 영역을 검정으로 채움
            pygame.draw.rect(surface, (0, 0, 0), src_rect)
            surface.blit(row_surf, (shift, y0))

    def _static_noise_bands(
        self, surface: pygame.Surface, w: int, h: int, intensity: float
    ) -> None:
        """
        TV 스태틱과 유사한 노이즈 픽셀 밴드를 수평으로 표시합니다.

        강도에 따라 밴드 수와 두께가 증가합니다.

        Args:
            surface:   렌더링 대상
            w:         너비 (픽셀)
            h:         높이 (픽셀)
            intensity: 글리치 강도 (0.0~1.0)
        """
        # 밴드 수: 1~4개
        band_count = max(1, int(intensity * 4))
        # 각 밴드의 최대 두께 (픽셀)
        max_band_h = max(2, int(intensity * 20))

        # 행 단위 노이즈 Surface (너비가 같으면 재사용)
        if self._row_surf_w != w or self._row_surf is None:
            # 높이 1인 Surface를 너비 방향으로 채운 뒤 원하는 높이만큼 blit
            self._row_surf = pygame.Surface((w, 1))
            self._row_surf_w = w

        row = self._row_surf

        for _ in range(band_count):
            y_start = random.randint(0, h - 1)
            band_h = random.randint(1, max_band_h)
            alpha_base = int(random.uniform(0.3, 0.8) * 255 * intensity)

            for row_y in range(y_start, min(y_start + band_h, h)):
                # 행 전체를 랜덤 그레이 픽셀로 채움
                noise_val = random.randint(0, 255)
                row.fill((noise_val, noise_val, noise_val))
                # ADD 블렌딩으로 기존 픽셀에 노이즈를 더함
                surface.blit(row, (0, row_y), special_flags=pygame.BLEND_ADD)

    def _block_corruption(
        self, surface: pygame.Surface, w: int, h: int, intensity: float
    ) -> None:
        """
        임의 직사각 블록을 무작위 색상으로 채워 데이터 손상을 표현합니다.

        블록 수와 크기가 강도에 비례합니다.

        Args:
            surface:   렌더링 대상
            w:         너비 (픽셀)
            h:         높이 (픽셀)
            intensity: 글리치 강도 (0.0~1.0)
        """
        # 블록 수: 2~10개
        block_count = max(2, int((intensity - _THRESH_HEAVY) / (1.0 - _THRESH_HEAVY) * 8 + 2))

        # 최대 블록 크기 (화면의 약 15% x 8%)
        max_bw = max(4, int(w * 0.15 * intensity))
        max_bh = max(2, int(h * 0.08 * intensity))

        for _ in range(block_count):
            bw = random.randint(2, max_bw)
            bh = random.randint(1, max_bh)
            bx = random.randint(0, max(0, w - bw))
            by = random.randint(0, max(0, h - bh))

            # 절반 확률로 순수 랜덤 색상, 나머지 절반은 화면 다른 부분 복사
            if random.random() < 0.5:
                # 랜덤 색상 블록
                r = random.randint(0, 255)
                g = random.randint(0, 60)   # 녹색은 낮게 유지 (데이터 손상 느낌)
                b = random.randint(0, 255)
                pygame.draw.rect(surface, (r, g, b), (bx, by, bw, bh))
            else:
                # 데이터모시: 화면의 다른 위치에서 블록을 복사 (subsurface 사용)
                src_x = random.randint(0, max(0, w - bw))
                src_y = random.randint(0, max(0, h - bh))
                # 원본 영역이 대상 영역과 같으면 스킵
                if src_x == bx and src_y == by:
                    continue
                try:
                    src_rect = pygame.Rect(src_x, src_y, bw, bh)
                    # subsurface는 픽셀 복사 없이 뷰를 제공하므로
                    # 같은 surface 내 복사 시 artefact가 발생할 수 있음
                    # → copy()로 독립 Surface 확보
                    block_copy = surface.subsurface(src_rect).copy()
                    surface.blit(block_copy, (bx, by))
                except ValueError:
                    # 범위 초과 등의 경우 무시
                    pass
