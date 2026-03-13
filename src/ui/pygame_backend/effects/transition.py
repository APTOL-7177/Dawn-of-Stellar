"""
transition.py - Cogmind 스타일 화면 전환 이펙트

스케일링 이후(apply_post 단계)에 적용되는 화면 전환 효과 모음.
FADE, WIPE, DISSOLVE, SCANLINE, MATRIX_RAIN, NOISE_DECODE 모드를 지원합니다.

사용 예시:
    transition = TransitionEffect()
    transition.trigger(TransitionMode.DISSOLVE, duration=0.8, direction="in")

    # 게임 루프:
    transition.update(dt)
    transition.render(screen_surface)
"""

import math
import random
from enum import Enum, auto
from typing import List, Optional, Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.transition")


class TransitionMode(Enum):
    """화면 전환 모드 열거형"""

    FADE = auto()         # 단색으로 페이드 인/아웃 (클래식)
    WIPE_LEFT = auto()    # 왼쪽에서 오른쪽으로 와이프
    WIPE_RIGHT = auto()   # 오른쪽에서 왼쪽으로 와이프
    WIPE_DOWN = auto()    # 위에서 아래로 와이프
    DISSOLVE = auto()     # 랜덤 블록 디졸브 (Cogmind 스타일)
    SCANLINE = auto()     # 수평 스캔라인 스위프 (CRT 스타일)
    MATRIX_RAIN = auto()  # 열별 문자 레인 (Matrix 스타일)
    NOISE_DECODE = auto() # 노이즈에서 실제 화면으로 디코딩


# MATRIX_RAIN에서 사용할 ASCII/특수 문자 풀
_MATRIX_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    "!@#$%^&*<>?/\\|[]{}~;:'"
    "αβγδεζηθλμξπστφψω"
    "▓▒░█▄▀■□▪▫"
)

# DISSOLVE 블록 크기 (픽셀) - 작을수록 부드러움
_DISSOLVE_BLOCK = 6

# MATRIX_RAIN 문자 크기 (픽셀)
_MATRIX_FONT_SIZE = 14

# 와이프/스캔라인 경계 그라디언트 페이드 존 폭 (픽셀)
_FADE_ZONE = 60


class TransitionEffect(EffectLayer):
    """
    Cogmind 스타일 화면 전환 이펙트

    apply_post 단계 이후 최상위 레이어로 렌더링됩니다.
    direction="out" 이면 화면이 점점 가려지고,
    direction="in"  이면 가림이 점점 사라집니다.

    progress 프로퍼티(0.0~1.0)는 전환 진행률을 나타냅니다.
    is_active 프로퍼티로 전환 실행 중 여부를 확인하세요.
    """

    def __init__(self, enabled: bool = True) -> None:
        super().__init__(enabled)

        # ── 공통 전환 상태 ─────────────────────────────────────────────
        self._mode: TransitionMode = TransitionMode.FADE
        self._direction: str = "out"        # "in" | "out"
        self._duration: float = 1.0         # 전환 전체 시간 (초)
        self._elapsed: float = 0.0          # 경과 시간 (초)
        self._active: bool = False           # 전환 실행 중 여부
        self._finished: bool = False         # 완료 대기 (1프레임 지연 비활성화용)
        self._color: Tuple[int, int, int] = (0, 0, 0)  # 전환 기본 색상

        # ── DISSOLVE 상태 ──────────────────────────────────────────────
        # 화면을 블록으로 나눈 좌표 목록 (셔플됨)
        self._dissolve_blocks: List[Tuple[int, int]] = []
        self._dissolve_surf_size: Tuple[int, int] = (0, 0)

        # ── MATRIX_RAIN 상태 ───────────────────────────────────────────
        # 열별 낙하 진행률 오프셋 (0.0~1.0, 열마다 랜덤 지연)
        self._matrix_col_offsets: List[float] = []
        self._matrix_font: Optional[pygame.font.Font] = None
        self._matrix_surf_size: Tuple[int, int] = (0, 0)

        # ── NOISE_DECODE 상태 ──────────────────────────────────────────
        # 정적 노이즈 Surface (크기 변경 시 재생성)
        self._noise_surf: Optional[pygame.Surface] = None
        self._noise_surf_size: Tuple[int, int] = (0, 0)

        # ── 렌더링 버퍼 ────────────────────────────────────────────────
        # 반투명 오버레이용 Surface (SRCALPHA)
        self._overlay: Optional[pygame.Surface] = None
        self._overlay_size: Tuple[int, int] = (0, 0)

    # ── 공개 API ──────────────────────────────────────────────────────────

    def trigger(
        self,
        mode: TransitionMode,
        duration: float,
        direction: str = "out",
        color: Tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """
        화면 전환 시작

        Args:
            mode: 전환 모드 (TransitionMode 열거형)
            duration: 전환 지속 시간 (초, 양수)
            direction: "out"=화면을 가림, "in"=가림을 해제
            color: 전환 색상 (FADE/WIPE에서 배경색으로 사용)
        """
        if not self.enabled:
            return

        self._mode = mode
        self._duration = max(0.01, duration)
        self._direction = direction if direction in ("in", "out") else "out"
        self._color = color
        self._elapsed = 0.0
        self._active = True
        self._finished = False

        # 모드별 초기화는 render() 첫 호출 시 화면 크기를 알고 나서 수행
        # (여기서는 상태만 리셋)
        self._dissolve_blocks = []
        self._dissolve_surf_size = (0, 0)
        self._matrix_col_offsets = []
        self._matrix_surf_size = (0, 0)
        self._noise_surf = None
        self._noise_surf_size = (0, 0)

        logger.debug(
            f"전환 트리거: mode={mode.name}, dir={direction}, "
            f"duration={duration:.2f}s, color={color}"
        )

    def stop(self) -> None:
        """전환 강제 중지"""
        self._active = False
        self._finished = False
        self._elapsed = 0.0

    @property
    def is_active(self) -> bool:
        """전환 실행 중 여부"""
        return self._active

    @property
    def progress(self) -> float:
        """
        전환 진행률 (0.0 ~ 1.0, ease-in-out 적용)

        direction="out": 0.0=시작(투명), 1.0=완전히 가림
        direction="in" : 0.0=시작(완전히 가림), 1.0=완전히 해제

        smoothstep(3t² - 2t³) 이징으로 시작과 끝이 부드럽습니다.
        """
        if self._duration <= 0:
            return 1.0
        t = min(1.0, self._elapsed / self._duration)
        # smoothstep ease-in-out: 시작과 끝이 완만, 중간이 빠름
        return t * t * (3.0 - 2.0 * t)

    # ── EffectLayer 인터페이스 ────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        전환 상태 업데이트

        Args:
            dt: 경과 시간 (초)
        """
        if not self.enabled or not self._active:
            return

        self._elapsed += dt
        if self._elapsed >= self._duration:
            self._elapsed = self._duration
            # _finished만 설정, _active는 render() 이후에 해제
            # present() 안에서 update() → render() 순서이므로
            # 여기서 _active=False 하면 render()가 건너뛰어 깜빡임 발생
            self._finished = True

    def render(self, surface: pygame.Surface) -> None:
        """
        전환 이펙트를 surface에 렌더링

        Args:
            surface: 렌더링 대상 pygame Surface (스크린 해상도)
        """
        if not self.enabled or not self._active:
            return

        w, h = surface.get_size()
        p = self.progress  # 0.0 ~ 1.0 (경과 비율)

        # direction="in"이면 진행률을 반전: 가림이 점점 사라짐
        cover = p if self._direction == "out" else 1.0 - p

        try:
            mode = self._mode
            if mode == TransitionMode.FADE:
                self._render_fade(surface, w, h, cover)
            elif mode in (TransitionMode.WIPE_LEFT, TransitionMode.WIPE_RIGHT, TransitionMode.WIPE_DOWN):
                self._render_wipe(surface, w, h, cover, mode)
            elif mode == TransitionMode.DISSOLVE:
                self._render_dissolve(surface, w, h, cover)
            elif mode == TransitionMode.SCANLINE:
                self._render_scanline(surface, w, h, cover)
            elif mode == TransitionMode.MATRIX_RAIN:
                self._render_matrix_rain(surface, w, h, p)
            elif mode == TransitionMode.NOISE_DECODE:
                self._render_noise_decode(surface, w, h, cover)
        except Exception as exc:
            logger.warning(f"전환 렌더링 오류 ({self._mode.name}): {exc}")

        # 렌더링 완료 후 비활성화 (update()에서 _finished 설정됨)
        # present() 안에서 update() → render() 순서이므로
        # render()가 마지막 프레임을 그린 후에 비활성화해야 깜빡임 없음
        if self._finished:
            self._active = False
            self._finished = False
            logger.debug(f"전환 완료: mode={self._mode.name}")

    # ── 모드별 렌더링 구현 ────────────────────────────────────────────────

    def _get_overlay(self, w: int, h: int) -> pygame.Surface:
        """
        SRCALPHA 오버레이 Surface 반환 (크기 변경 시 재생성)

        Args:
            w: 필요한 너비 (픽셀)
            h: 필요한 높이 (픽셀)

        Returns:
            pygame.Surface: SRCALPHA Surface
        """
        if self._overlay_size != (w, h) or self._overlay is None:
            self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            self._overlay_size = (w, h)
        return self._overlay

    def _render_fade(
        self,
        surface: pygame.Surface,
        w: int,
        h: int,
        cover: float,
    ) -> None:
        """
        단색 페이드 렌더링

        cover=0.0이면 투명, cover=1.0이면 완전히 색상으로 덮임.

        Args:
            surface: 렌더링 대상
            w: 화면 너비
            h: 화면 높이
            cover: 가림 비율 (0.0~1.0)
        """
        alpha = int(cover * 255)
        if alpha <= 0:
            return

        overlay = self._get_overlay(w, h)
        r, g, b = self._color
        overlay.fill((r, g, b, alpha))
        surface.blit(overlay, (0, 0))

    def _render_wipe(
        self,
        surface: pygame.Surface,
        w: int,
        h: int,
        cover: float,
        mode: TransitionMode,
    ) -> None:
        """
        방향성 와이프 렌더링 (소프트 그라디언트 경계)

        경계에 _FADE_ZONE 폭의 반투명 그라디언트를 적용하여
        이전 화면이 서서히 사라지는 느낌을 줍니다.

        Args:
            surface: 렌더링 대상
            w: 화면 너비
            h: 화면 높이
            cover: 가림 비율 (0.0~1.0)
            mode: WIPE_LEFT / WIPE_RIGHT / WIPE_DOWN
        """
        r, g, b = self._color
        overlay = self._get_overlay(w, h)
        overlay.fill((0, 0, 0, 0))

        fade_zone = _FADE_ZONE

        if mode == TransitionMode.WIPE_LEFT:
            wipe_x = int(w * cover)
            # 완전 불투명 영역 (그라디언트 시작 전)
            solid_end = max(0, wipe_x - fade_zone)
            if solid_end > 0:
                pygame.draw.rect(overlay, (r, g, b, 255), (0, 0, solid_end, h))
            # 그라디언트 존: solid_end → wipe_x 사이를 알파 255→0으로 페이드
            steps = min(fade_zone, wipe_x)
            if steps > 0:
                for i in range(steps):
                    alpha = int(255 * (1.0 - i / steps))
                    px = solid_end + i
                    if 0 <= px < w:
                        pygame.draw.line(overlay, (r, g, b, alpha), (px, 0), (px, h - 1))

        elif mode == TransitionMode.WIPE_RIGHT:
            wipe_w = int(w * cover)
            start_x = w - wipe_w
            # 완전 불투명 영역
            solid_start = min(w, start_x + fade_zone)
            if solid_start < w:
                pygame.draw.rect(overlay, (r, g, b, 255), (solid_start, 0, w - solid_start, h))
            # 그라디언트 존: start_x → solid_start 사이를 알파 0→255
            steps = min(fade_zone, wipe_w)
            if steps > 0:
                for i in range(steps):
                    alpha = int(255 * i / steps)
                    px = start_x + i
                    if 0 <= px < w:
                        pygame.draw.line(overlay, (r, g, b, alpha), (px, 0), (px, h - 1))

        elif mode == TransitionMode.WIPE_DOWN:
            wipe_h = int(h * cover)
            solid_end = max(0, wipe_h - fade_zone)
            if solid_end > 0:
                pygame.draw.rect(overlay, (r, g, b, 255), (0, 0, w, solid_end))
            steps = min(fade_zone, wipe_h)
            if steps > 0:
                for i in range(steps):
                    alpha = int(255 * (1.0 - i / steps))
                    py = solid_end + i
                    if 0 <= py < h:
                        pygame.draw.line(overlay, (r, g, b, alpha), (0, py), (w - 1, py))

        surface.blit(overlay, (0, 0))

    def _build_dissolve_blocks(self, w: int, h: int) -> None:
        """
        DISSOLVE용 블록 좌표 목록 생성 및 셔플

        화면을 _DISSOLVE_BLOCK 크기의 격자로 나누고
        좌표를 무작위로 섞습니다.

        Args:
            w: 화면 너비 (픽셀)
            h: 화면 높이 (픽셀)
        """
        cols = math.ceil(w / _DISSOLVE_BLOCK)
        rows = math.ceil(h / _DISSOLVE_BLOCK)
        blocks = [
            (bx * _DISSOLVE_BLOCK, by * _DISSOLVE_BLOCK)
            for by in range(rows)
            for bx in range(cols)
        ]
        random.shuffle(blocks)
        self._dissolve_blocks = blocks
        self._dissolve_surf_size = (w, h)
        logger.debug(f"DISSOLVE 블록 생성: {len(blocks)}개 ({cols}x{rows})")

    def _render_dissolve(
        self,
        surface: pygame.Surface,
        w: int,
        h: int,
        cover: float,
    ) -> None:
        """
        랜덤 블록 디졸브 렌더링 (Cogmind 스타일, 소프트 에지)

        cover 비율만큼의 블록을 _color로 채웁니다.
        최근 등장한 블록은 반투명으로 시작하여 서서히 불투명해집니다.

        Args:
            surface: 렌더링 대상
            w: 화면 너비
            h: 화면 높이
            cover: 가림 비율 (0.0~1.0)
        """
        # 화면 크기가 바뀌었거나 아직 초기화되지 않은 경우 재생성
        if self._dissolve_surf_size != (w, h) or not self._dissolve_blocks:
            self._build_dissolve_blocks(w, h)

        total = len(self._dissolve_blocks)
        if total == 0:
            return

        r, g, b = self._color
        overlay = self._get_overlay(w, h)
        overlay.fill((0, 0, 0, 0))

        filled_count = int(cover * total)
        # 최근 등장 블록 중 일부를 반투명으로 (페이드인 느낌)
        # 전체 블록의 8%를 페이드 구간으로 사용
        fade_band = max(1, int(total * 0.08))

        for i in range(filled_count):
            bx, by = self._dissolve_blocks[i]
            # 페이드 구간에 속하는 최근 블록은 반투명
            dist_from_edge = filled_count - 1 - i
            if dist_from_edge < fade_band:
                alpha = int(255 * (dist_from_edge + 1) / fade_band)
            else:
                alpha = 255

            pygame.draw.rect(
                overlay, (r, g, b, alpha),
                (bx, by, _DISSOLVE_BLOCK, _DISSOLVE_BLOCK)
            )

        surface.blit(overlay, (0, 0))

    def _render_scanline(
        self,
        surface: pygame.Surface,
        w: int,
        h: int,
        cover: float,
    ) -> None:
        """
        수평 스캔라인 스위프 렌더링 (CRT 스타일, 위→아래, 소프트 경계)

        진행 선두에 그라디언트 페이드 존과 CRT 발광 효과를 적용하여
        화면이 서서히 전환되는 느낌을 줍니다.

        Args:
            surface: 렌더링 대상
            w: 화면 너비
            h: 화면 높이
            cover: 가림 비율 (0.0~1.0)
        """
        r, g, b = self._color
        sweep_y = int(h * cover)

        if sweep_y <= 0:
            return

        overlay = self._get_overlay(w, h)
        overlay.fill((0, 0, 0, 0))

        fade_zone = _FADE_ZONE

        # 완전 불투명 영역 (그라디언트 시작 전)
        solid_end = max(0, sweep_y - fade_zone)
        if solid_end > 0:
            pygame.draw.rect(overlay, (r, g, b, 255), (0, 0, w, solid_end))

        # 그라디언트 존: solid_end → sweep_y 사이를 알파 255→0
        steps = min(fade_zone, sweep_y)
        if steps > 0:
            for i in range(steps):
                alpha = int(255 * (1.0 - i / steps))
                py = solid_end + i
                if 0 <= py < h:
                    pygame.draw.line(overlay, (r, g, b, alpha), (0, py), (w - 1, py))

        # CRT 발광선: 경계 중앙에 은은한 밝은 선 (SRCALPHA 위에 추가)
        glow_y = max(0, sweep_y - fade_zone // 2)
        if 0 < glow_y < h:
            glow_alpha = min(120, int(180 * cover))
            for dy in range(-2, 3):
                gy = glow_y + dy
                if 0 <= gy < h:
                    line_alpha = glow_alpha * (3 - abs(dy)) // 3
                    pygame.draw.line(
                        overlay,
                        (min(255, r + 100), min(255, g + 140), min(255, b + 100), line_alpha),
                        (0, gy), (w - 1, gy),
                    )

        surface.blit(overlay, (0, 0))

    def _build_matrix_cols(self, w: int, h: int) -> None:
        """
        MATRIX_RAIN용 열별 지연 오프셋 초기화

        각 열에 0.0~0.3 사이의 랜덤 시작 지연을 부여하여
        빗방울이 다른 타이밍에 시작하는 효과를 만듭니다.

        Args:
            w: 화면 너비 (픽셀)
            h: 화면 높이 (픽셀)
        """
        col_count = max(1, w // _MATRIX_FONT_SIZE)
        # 열별 랜덤 지연: 0.0~0.3 사이 (전환 진행률 기준)
        self._matrix_col_offsets = [
            random.uniform(0.0, 0.3) for _ in range(col_count)
        ]
        self._matrix_surf_size = (w, h)
        logger.debug(f"MATRIX_RAIN 열 초기화: {col_count}열")

    def _render_matrix_rain(
        self,
        surface: pygame.Surface,
        w: int,
        h: int,
        progress: float,
    ) -> None:
        """
        Matrix 스타일 문자 레인 렌더링

        direction="out": 열별로 위에서 아래로 녹색 문자가 떨어지며 화면을 가림
        direction="in" : 반대 방향으로 문자가 사라지며 화면이 나타남

        Args:
            surface: 렌더링 대상
            w: 화면 너비
            h: 화면 높이
            progress: 원시 진행률 (0.0~1.0, 방향 반전 전)
        """
        # 화면 크기 변경 또는 미초기화 시 재생성
        if self._matrix_surf_size != (w, h) or not self._matrix_col_offsets:
            self._build_matrix_cols(w, h)

        # 폰트 초기화 (pygame.font 미초기화 상태 안전 처리)
        if self._matrix_font is None:
            try:
                self._matrix_font = pygame.font.SysFont("courier", _MATRIX_FONT_SIZE)
            except Exception:
                self._matrix_font = pygame.font.Font(None, _MATRIX_FONT_SIZE)

        col_w = _MATRIX_FONT_SIZE
        col_h = _MATRIX_FONT_SIZE
        r, g, b = self._color

        col_count = len(self._matrix_col_offsets)

        for col_idx, delay in enumerate(self._matrix_col_offsets):
            cx = col_idx * col_w

            # 이 열의 유효 진행률 (지연 반영, 0.0~1.0 클램프)
            col_progress = max(0.0, min(1.0, (progress - delay) / (1.0 - delay + 1e-6)))

            if self._direction == "out":
                # 떨어지는 문자가 열을 위에서부터 채워나감
                filled_rows = int(math.ceil(col_progress * (h / col_h)))
                # 이미 지나간 행: 배경색으로 채움
                fill_h = max(0, filled_rows * col_h - col_h)
                if fill_h > 0:
                    pygame.draw.rect(surface, (r, g, b), (cx, 0, col_w, fill_h))
                # 현재 낙하 중인 문자 (선두)
                if 0 < filled_rows <= math.ceil(h / col_h):
                    char = random.choice(_MATRIX_CHARS)
                    head_y = (filled_rows - 1) * col_h
                    try:
                        txt_surf = self._matrix_font.render(
                            char, True, (min(255, g + 80), min(255, b + 80), min(255, r + 80))
                        )
                        surface.blit(txt_surf, (cx, head_y))
                    except Exception:
                        pass
            else:
                # direction="in": 열 상단부터 문자가 사라지며 실제 화면이 나타남
                # 아직 남아있는 하단 영역을 배경색으로 유지
                revealed_h = int(col_progress * h)
                remaining_y = revealed_h
                remaining_h = h - remaining_y
                if remaining_h > 0:
                    pygame.draw.rect(
                        surface, (r, g, b),
                        (cx, remaining_y, col_w, remaining_h)
                    )
                # 해제 선두에 문자 표시
                if 0 < remaining_y < h:
                    char = random.choice(_MATRIX_CHARS)
                    try:
                        txt_surf = self._matrix_font.render(
                            char, True, (100, 255, 100)
                        )
                        surface.blit(txt_surf, (cx, remaining_y))
                    except Exception:
                        pass

    def _build_noise_surf(self, w: int, h: int) -> None:
        """
        정적 노이즈 Surface 생성

        픽셀마다 랜덤 RGB 값을 가진 노이즈 패턴을 미리 생성합니다.
        퍼포먼스를 위해 크기 변경 시에만 재생성합니다.

        Args:
            w: 화면 너비 (픽셀)
            h: 화면 높이 (픽셀)
        """
        noise = pygame.Surface((w, h))
        # pygame.PixelArray를 사용하여 빠르게 노이즈 픽셀 채우기
        try:
            pa = pygame.PixelArray(noise)
            for x in range(w):
                for y in range(h):
                    grey = random.randint(0, 200)
                    # 약간의 색조 변화로 CRT 정적 느낌
                    rr = max(0, grey + random.randint(-20, 20))
                    gg = max(0, grey + random.randint(-20, 20))
                    bb = max(0, grey + random.randint(-20, 20))
                    pa[x][y] = noise.map_rgb(
                        min(255, rr), min(255, gg), min(255, bb)
                    )
            del pa
        except Exception:
            # PixelArray 실패 시 단순 fill 폴백
            noise.fill((80, 80, 80))

        self._noise_surf = noise
        self._noise_surf_size = (w, h)
        logger.debug(f"NOISE_DECODE 노이즈 Surface 생성: {w}x{h}")

    def _render_noise_decode(
        self,
        surface: pygame.Surface,
        w: int,
        h: int,
        cover: float,
    ) -> None:
        """
        노이즈 디코딩 렌더링

        direction="out": 화면이 점점 노이즈로 덮임 (노이즈 알파 증가)
        direction="in" : 노이즈가 점점 사라지며 실제 화면 노출 (노이즈 알파 감소)

        cover=0.0이면 노이즈 없음, cover=1.0이면 완전히 노이즈로 덮임.

        Args:
            surface: 렌더링 대상
            w: 화면 너비
            h: 화면 높이
            cover: 가림 비율 (0.0~1.0)
        """
        if cover <= 0.0:
            return

        # 노이즈 Surface 초기화 또는 재생성
        if self._noise_surf_size != (w, h) or self._noise_surf is None:
            self._build_noise_surf(w, h)

        if self._noise_surf is None:
            return

        # 알파 블렌딩으로 노이즈를 반투명하게 합성
        alpha = int(cover * 255)
        self._noise_surf.set_alpha(alpha)
        surface.blit(self._noise_surf, (0, 0))

        # 노이즈 위에 scan-line 패턴으로 텍스처 강화 (cover > 0.3일 때만)
        if cover > 0.3:
            scan_alpha = int((cover - 0.3) / 0.7 * 60)
            overlay = self._get_overlay(w, h)
            r, g, b = self._color
            overlay.fill((r, g, b, scan_alpha))
            # 수평선마다 약간 어두운 라인 (CRT 정적 느낌)
            for y in range(0, h, 4):
                pygame.draw.line(overlay, (0, 0, 0, scan_alpha // 2), (0, y), (w - 1, y))
            surface.blit(overlay, (0, 0))
