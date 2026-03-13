"""
text_effects.py - Cogmind 스타일 텍스트 애니메이션 이펙트

tcod 호환 콘솔(또는 PygameConsole)과 함께 동작하는 텍스트 애니메이션 유틸리티.
EffectLayer 서브클래스가 아닌, 콘솔 셀 데이터를 직접 수정하는 독립 유틸리티 클래스들.

주요 클래스:
    TextScrambler  - Cogmind 시그니처 텍스트 디코딩 효과
    TextTypewriter - 타자기 효과 (커서 포함)
    ColorCycler    - 텍스트 색상 사이클링

헬퍼 함수:
    render_scrambled_text - TextScrambler를 콘솔에 직접 렌더링
"""

import math
import random
from typing import Optional

# Cogmind 스타일 스크램블 문자 세트 - ASCII 박스 드로잉 + 특수문자
_SCRAMBLE_CHARS = "░▒▓█▀▄▌▐│─┌┐└┘├┤┬┴┼╔╗╚╝═║@#$%&*<>{}[]01"


class TextScrambler:
    """
    Cogmind 시그니처 텍스트 스크램블 이펙트.

    텍스트가 랜덤 문자로 나타났다가 점차 실제 텍스트로 해독되는 효과.
    터미널 해킹/데이터 수신 분위기를 연출.

    사용 예시::

        scrambler = TextScrambler("SYSTEM ONLINE", duration=0.8, style="decode")
        # 게임 루프에서:
        scrambler.update(dt)
        text = scrambler.get_display_text()

    Attributes:
        text: 최종 표시될 원본 텍스트
        duration: 전체 디코딩 소요 시간 (초)
        style: 디코딩 방식 ("decode" | "random" | "wave")
        elapsed: 누적 경과 시간
    """

    def __init__(
        self,
        text: str,
        duration: float = 0.5,
        style: str = "decode",
    ) -> None:
        """
        Args:
            text: 표시할 최종 텍스트
            duration: 전체 디코딩 시간 (초)
            style: "decode" (앞에서부터 해독), "random" (랜덤 위치 해독),
                   "wave" (파동형 해독)
        """
        self.text = text
        self.duration = max(duration, 0.01)
        self.style = style
        self.elapsed: float = 0.0

        n = len(text)

        # 각 문자가 해독되는 시점 (0.0~1.0 진행도 기준)
        self._resolve_at: list[float] = self._build_resolve_schedule(n, style)

        # 각 문자의 현재 스크램블 표시용 문자
        self._scramble_buf: list[str] = [
            random.choice(_SCRAMBLE_CHARS) if ch != " " else " "
            for ch in text
        ]

        # 각 문자가 스크램블 상태에서 몇 번 순환했는지 (decode 스타일용)
        self._cycle_count: list[int] = [0] * n
        # 각 문자가 최종 해독되었는지
        self._resolved: list[bool] = [False] * n

    # ── 스케줄 생성 ──────────────────────────────────────────────────────────

    def _build_resolve_schedule(self, n: int, style: str) -> list[float]:
        """
        각 문자 인덱스별 해독 시점(0~1 진행도)을 생성.

        Args:
            n: 텍스트 길이
            style: 디코딩 스타일

        Returns:
            인덱스별 해독 시점 리스트
        """
        if n == 0:
            return []

        if style == "decode":
            # 왼쪽에서 오른쪽으로 순차 해독, 약간의 지터 추가
            schedule = []
            for i in range(n):
                base = i / n
                jitter = random.uniform(-0.03, 0.03)
                schedule.append(max(0.0, min(1.0, base + jitter)))
            return schedule

        elif style == "random":
            # 완전 랜덤 순서로 해독
            points = [i / max(n - 1, 1) for i in range(n)]
            random.shuffle(points)
            return points

        elif style == "wave":
            # 사인파 패턴: 파동이 왼쪽에서 오른쪽으로 이동
            schedule = []
            for i in range(n):
                # 파동 앞머리가 위치를 통과하는 시점
                wave_pos = i / max(n - 1, 1)
                # 약간의 랜덤 지연 추가 (파동 뒤에서 해독)
                delay = random.uniform(0.0, 0.15)
                schedule.append(min(1.0, wave_pos * 0.85 + delay))
            return schedule

        else:
            # 알 수 없는 스타일은 decode로 폴백
            return self._build_resolve_schedule(n, "decode")

    # ── 업데이트 ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        이펙트 상태를 dt만큼 진행.

        Args:
            dt: 경과 시간 (초)
        """
        if self.is_complete:
            return

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        for i, ch in enumerate(self.text):
            if self._resolved[i]:
                continue

            if ch == " ":
                # 공백은 즉시 해독
                self._resolved[i] = True
                self._scramble_buf[i] = " "
                continue

            if progress >= self._resolve_at[i]:
                # 해독 시점 도달: 최종 문자로 확정
                self._resolved[i] = True
                self._scramble_buf[i] = ch
            else:
                # 아직 스크램블 중: 주기적으로 다른 랜덤 문자로 교체
                # progress가 해독 시점에 가까울수록 교체 빈도 감소
                proximity = progress / max(self._resolve_at[i], 0.01)
                # 60fps 기준 약 3~5프레임마다 교체
                if random.random() < (0.3 + 0.5 * (1.0 - proximity)):
                    self._scramble_buf[i] = random.choice(_SCRAMBLE_CHARS)

    # ── 상태 조회 ──────────────────────────────────────────────────────────

    def get_display_text(self) -> str:
        """
        현재 표시 텍스트 반환.

        해독된 문자는 원본, 아직 스크램블 중인 문자는 랜덤 문자로 구성.

        Returns:
            현재 프레임의 표시 문자열
        """
        return "".join(self._scramble_buf)

    def get_char_states(self) -> list[tuple[str, bool]]:
        """
        각 문자의 (표시 문자, 해독 완료 여부) 튜플 리스트 반환.

        색상 구분 렌더링에 사용:
            - is_resolved=True  → 일반 색상으로 렌더링
            - is_resolved=False → 스크램블 색상(초록)으로 렌더링

        Returns:
            [(표시 문자, 해독 완료 여부), ...] 리스트
        """
        return list(zip(self._scramble_buf, self._resolved))

    @property
    def is_complete(self) -> bool:
        """모든 문자가 해독되었으면 True."""
        return self.elapsed >= self.duration

    def reset(self) -> None:
        """이펙트를 초기 상태로 되돌림."""
        self.elapsed = 0.0
        n = len(self.text)
        self._resolve_at = self._build_resolve_schedule(n, self.style)
        self._scramble_buf = [
            random.choice(_SCRAMBLE_CHARS) if ch != " " else " "
            for ch in self.text
        ]
        self._cycle_count = [0] * n
        self._resolved = [False] * n


class TextTypewriter:
    """
    클래식 타자기 텍스트 이펙트.

    텍스트가 한 글자씩 나타나며, 끝에 깜빡이는 커서가 표시됨.
    대화 연출, 로그 메시지 등에 사용.

    사용 예시::

        typewriter = TextTypewriter("Loading...", chars_per_second=20.0)
        # 게임 루프에서:
        typewriter.update(dt)
        display = typewriter.get_display_text()  # "Load▌" 형태

    Attributes:
        text: 원본 텍스트
        chars_per_second: 초당 타이핑 문자 수
        cursor_char: 커서 문자 (기본값 "▌")
    """

    # 커서 깜빡임 주기 (초)
    _CURSOR_BLINK_PERIOD: float = 0.53

    def __init__(
        self,
        text: str,
        chars_per_second: float = 30.0,
        cursor_char: str = "▌",
    ) -> None:
        """
        Args:
            text: 타이핑할 전체 텍스트
            chars_per_second: 초당 타이핑 속도
            cursor_char: 커서로 사용할 문자
        """
        self.text = text
        self.chars_per_second = max(chars_per_second, 0.1)
        self.cursor_char = cursor_char

        self._elapsed: float = 0.0
        self._cursor_elapsed: float = 0.0
        self._cursor_visible: bool = True

    # ── 업데이트 ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        타이핑 진행 및 커서 깜빡임 상태 업데이트.

        Args:
            dt: 경과 시간 (초)
        """
        if not self.is_complete:
            self._elapsed += dt

        # 커서 깜빡임은 완료 후에도 계속
        self._cursor_elapsed += dt
        if self._cursor_elapsed >= self._CURSOR_BLINK_PERIOD:
            self._cursor_elapsed -= self._CURSOR_BLINK_PERIOD
            self._cursor_visible = not self._cursor_visible

    # ── 상태 조회 ──────────────────────────────────────────────────────────

    def get_display_text(self) -> str:
        """
        현재까지 타이핑된 텍스트 + 커서 반환.

        완료 후에는 전체 텍스트 + 깜빡이는 커서.

        Returns:
            표시할 문자열 (예: "Hello▌" 또는 "Hello ")
        """
        visible = self.text[: self.get_visible_length()]
        cursor = self.cursor_char if self._cursor_visible else " "
        return visible + cursor

    def get_visible_length(self) -> int:
        """
        현재 화면에 표시된 문자 수 반환 (커서 제외).

        Returns:
            표시 중인 원본 텍스트 문자 수
        """
        if self.is_complete:
            return len(self.text)
        chars = int(self._elapsed * self.chars_per_second)
        return min(chars, len(self.text))

    @property
    def is_complete(self) -> bool:
        """모든 텍스트가 타이핑되었으면 True."""
        total_time = len(self.text) / self.chars_per_second
        return self._elapsed >= total_time

    def skip(self) -> None:
        """타이핑을 즉시 완료 상태로 건너뜀."""
        # 완료 조건: elapsed >= len / cps
        self._elapsed = len(self.text) / self.chars_per_second + 0.001

    def reset(self) -> None:
        """타이퍼를 초기 상태로 되돌림."""
        self._elapsed = 0.0
        self._cursor_elapsed = 0.0
        self._cursor_visible = True


class ColorCycler:
    """
    텍스트 문자 색상 사이클링 이펙트.

    UI 하이라이트, 테두리, 특수 텍스트에 무지개 파동이나 펄스 효과 적용.

    사용 예시::

        cycler = ColorCycler(
            colors=[(255,0,0), (255,165,0), (0,255,0), (0,0,255)],
            speed=2.0,
            mode="wave",
        )
        # 게임 루프에서:
        cycler.update(dt)
        for i, ch in enumerate(text):
            color = cycler.get_color(i)
            # color로 ch 렌더링...

    Attributes:
        colors: 사이클링할 RGB 색상 목록
        speed: 사이클 속도 (Hz)
        mode: 색상 모드 ("wave" | "pulse" | "sparkle")
    """

    def __init__(
        self,
        colors: list[tuple[int, int, int]],
        speed: float = 2.0,
        mode: str = "wave",
    ) -> None:
        """
        Args:
            colors: RGB 색상 리스트 (최소 1개 이상)
            speed: 사이클 속도 (Hz). 높을수록 빠름
            mode: "wave" (무지개 파동), "pulse" (전체 동시 펄스),
                  "sparkle" (문자별 랜덤 반짝임)
        """
        if not colors:
            colors = [(200, 200, 200)]

        self.colors = colors
        self.speed = max(speed, 0.01)
        self.mode = mode

        self._phase: float = 0.0

        # sparkle 모드용: 문자별 독립 위상 오프셋
        self._sparkle_offsets: dict[int, float] = {}

    # ── 업데이트 ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """
        색상 사이클 위상 업데이트.

        Args:
            dt: 경과 시간 (초)
        """
        self._phase += dt * self.speed
        # 위상이 너무 커지면 wrapping (부동소수점 정밀도 유지)
        if self._phase > 1000.0:
            self._phase -= 1000.0

    # ── 색상 조회 ──────────────────────────────────────────────────────────

    def get_color(self, char_index: int) -> tuple[int, int, int]:
        """
        지정 위치 문자의 현재 색상 반환.

        Args:
            char_index: 텍스트 내 문자 위치 (0-based)

        Returns:
            RGB 색상 튜플 (각 채널 0~255)
        """
        n = len(self.colors)
        if n == 1:
            return self.colors[0]

        if self.mode == "wave":
            return self._wave_color(char_index)
        elif self.mode == "pulse":
            return self._pulse_color()
        elif self.mode == "sparkle":
            return self._sparkle_color(char_index)
        else:
            return self._wave_color(char_index)

    # ── 내부 색상 계산 ─────────────────────────────────────────────────────

    def _lerp_color(
        self,
        a: tuple[int, int, int],
        b: tuple[int, int, int],
        t: float,
    ) -> tuple[int, int, int]:
        """
        두 RGB 색상 사이를 선형 보간.

        Args:
            a: 시작 색상
            b: 끝 색상
            t: 보간 계수 (0.0~1.0)

        Returns:
            보간된 RGB 색상
        """
        return (
            int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t),
        )

    def _sample_palette(self, t: float) -> tuple[int, int, int]:
        """
        0~1 범위의 t 값으로 팔레트 색상 샘플링 (부드러운 보간).

        Args:
            t: 팔레트 위치 (0.0~1.0, 순환)

        Returns:
            보간된 RGB 색상
        """
        n = len(self.colors)
        # t를 [0, n) 범위로 매핑
        pos = (t % 1.0) * n
        idx_a = int(pos) % n
        idx_b = (idx_a + 1) % n
        frac = pos - int(pos)
        return self._lerp_color(self.colors[idx_a], self.colors[idx_b], frac)

    def _wave_color(self, char_index: int) -> tuple[int, int, int]:
        """
        무지개 파동 색상: 위치에 따라 위상이 다른 파동이 이동.

        Args:
            char_index: 문자 위치

        Returns:
            해당 위치의 현재 색상
        """
        # 위치 오프셋: 문자마다 0.07씩 위상 차이 (파동 간격 조절)
        offset = char_index * 0.07
        t = (self._phase + offset) % 1.0
        return self._sample_palette(t)

    def _pulse_color(self) -> tuple[int, int, int]:
        """
        펄스 색상: 전체 텍스트가 같은 색상으로 동기화 펄싱.

        Returns:
            현재 펄스 색상
        """
        t = self._phase % 1.0
        return self._sample_palette(t)

    def _sparkle_color(self, char_index: int) -> tuple[int, int, int]:
        """
        반짝임 색상: 문자마다 독립적인 랜덤 위상으로 불규칙 반짝임.

        Args:
            char_index: 문자 위치

        Returns:
            해당 문자의 현재 반짝임 색상
        """
        # 문자별 고정 랜덤 오프셋 (처음 호출 시 생성)
        if char_index not in self._sparkle_offsets:
            self._sparkle_offsets[char_index] = random.random()

        offset = self._sparkle_offsets[char_index]
        # 사인파로 밝기 변조 추가 (반짝임 효과)
        brightness = 0.5 + 0.5 * math.sin((self._phase + offset) * 2 * math.pi)
        t = (self._phase + offset) % 1.0
        base_color = self._sample_palette(t)

        # 밝기 적용 (어두운 쪽으로)
        dim = 0.4 + 0.6 * brightness
        return (
            int(base_color[0] * dim),
            int(base_color[1] * dim),
            int(base_color[2] * dim),
        )


def render_scrambled_text(
    console,
    x: int,
    y: int,
    scrambler: TextScrambler,
    fg_resolved: tuple[int, int, int] = (200, 200, 200),
    fg_scrambled: tuple[int, int, int] = (0, 180, 0),
) -> None:
    """
    TextScrambler의 현재 상태를 콘솔에 직접 렌더링하는 편의 함수.

    해독된 문자는 fg_resolved 색상, 아직 스크램블 중인 문자는
    Cogmind 터미널 스타일의 fg_scrambled(기본: 초록) 색상으로 표시.

    tcod 콘솔 또는 PygameConsole과 호환:
    - `console.print(x, y, string, fg=...)` 형태를 지원하는 객체 필요

    사용 예시::

        scrambler = TextScrambler("ONLINE", duration=1.0)
        # 렌더링 루프에서:
        render_scrambled_text(console, 5, 10, scrambler)

    Args:
        console: tcod.console.Console 또는 PygameConsole 호환 객체.
                 `print(x, y, string, fg)` 또는
                 `tiles_rgb['fg'][y, x]` 접근을 지원해야 함.
        x: 렌더링 시작 X 좌표 (콘솔 셀 단위)
        y: 렌더링 시작 Y 좌표 (콘솔 셀 단위)
        scrambler: 렌더링할 TextScrambler 인스턴스
        fg_resolved: 해독 완료된 문자의 RGB 색상
                     (기본값: (200, 200, 200) 밝은 회색)
        fg_scrambled: 스크램블 중인 문자의 RGB 색상
                      (기본값: (0, 180, 0) Cogmind 터미널 초록)
    """
    char_states = scrambler.get_char_states()

    # 문자별로 색상을 달리해 출력 (콘솔 API 호환 처리)
    for i, (ch, is_resolved) in enumerate(char_states):
        cx = x + i
        color = fg_resolved if is_resolved else fg_scrambled

        # tcod.console.Console: print() 메서드 사용
        # PygameConsole 등도 동일 시그니처를 지원하는 경우 동작
        try:
            console.print(cx, y, ch, fg=color)
        except TypeError:
            # fg 키워드 미지원 시 위치 인수로 재시도
            try:
                console.print(cx, y, ch, color)
            except Exception:
                # 렌더링 실패는 무시 (이펙트는 필수가 아님)
                pass


__all__ = [
    "TextScrambler",
    "TextTypewriter",
    "ColorCycler",
    "render_scrambled_text",
    "_SCRAMBLE_CHARS",
]
