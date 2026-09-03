"""
부트 스플래시 트랜지션 - 인트로 → 메인 메뉴 사이 연출

DOS 레트로 스타일의 화려한 부팅 시퀀스:
  Phase 1: 매트릭스 레인 (위에서 내려오는 초록 문자)
  Phase 2: "APTOL" 글리치 스크램블 등장
  Phase 3: 스튜디오 페이드아웃
  Phase 4: 게임 타이틀 + 별빛 파티클
  Phase 5: CRT 스캔라인 전환
"""

import tcod.console
import tcod.event
import time
import math
import random
import unicodedata
from typing import List

from src.ui.input_handler import unified_input_handler, GameAction
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerEvent, PointerEventKind
from src.core.logger import get_logger

logger = get_logger("boot_splash")

# 매트릭스 문자 풀
_MATRIX_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>?/\\▓▒░█"

# 타이틀 박스 설정 (프로그래밍으로 그려서 CJK 너비 문제 방지)
_BOX_WIDTH = 38
_BOX_INNER = _BOX_WIDTH - 2
_TITLE_LINES = [
    ("border_top", None),
    ("empty", None),
    ("text", "던 오브 스텔라"),
    ("text", "Dawn of Stellar"),
    ("empty", None),
    ("border_bottom", None),
]


def _clamp(v: int) -> int:
    """색상값을 0~255 범위로 클램프"""
    return max(0, min(255, v))


def _display_width(s: str) -> int:
    """문자열의 실제 표시 너비 계산 (CJK 문자는 2칸)"""
    width = 0
    for c in s:
        if unicodedata.east_asian_width(c) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width


class BootSplash:
    """부트 스플래시 시퀀스"""

    def __init__(self, screen_width: int, screen_height: int, glitch_level: int = 0):
        self.w = screen_width
        self.h = screen_height
        self.glitch_level = glitch_level

        # 매트릭스 레인 상태 (열별 낙하 위치)
        self.rain_cols: List[dict] = []
        for x in range(self.w):
            self.rain_cols.append({
                "x": x,
                "y": random.randint(-self.h, 0),
                "speed": random.uniform(0.3, 1.0),
                "trail_len": random.randint(4, 12),
                "char": random.choice(_MATRIX_CHARS),
            })

        # 별 파티클
        self.stars: List[dict] = []
        self.skip_requested = False

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        if event.kind is PointerEventKind.CLICK and event.button in (PointerButton.LEFT, PointerButton.RIGHT):
            self.skip_requested = True
            action = GameAction.CANCEL if event.button is PointerButton.RIGHT else GameAction.CONFIRM
            return PointerDispatchResult(event=event, action=action)
        return PointerDispatchResult(event=event)

    def _skip_check(self) -> bool:
        """Z키/Enter/ESC로 스킵"""
        for event in tcod.event.get():
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event is not None and self.handle_pointer_event(pointer_event).action is not None:
                return True
            if isinstance(event, tcod.event.KeyDown):
                return True
        action = unified_input_handler.get_action()
        if action in (GameAction.CONFIRM, GameAction.CANCEL):
            return True
        return False

    def _render_matrix_rain(self, console: tcod.console.Console, progress: float):
        """매트릭스 레인 렌더링"""
        for col in self.rain_cols:
            col["y"] += col["speed"]
            if col["y"] > self.h + col["trail_len"]:
                col["y"] = random.randint(-self.h // 2, 0)
                col["speed"] = random.uniform(0.3, 1.0)
                col["char"] = random.choice(_MATRIX_CHARS)

            head_y = int(col["y"])
            x = col["x"]

            # 글리치 레벨 2: 일부 열 깜빡임 (10% 확률로 열 전체 스킵)
            if self.glitch_level >= 2 and random.random() < 0.10:
                continue
            # 글리치 레벨 1: 아주 드물게 열 깜빡임 (2%)
            elif self.glitch_level == 1 and random.random() < 0.02:
                continue

            for i in range(col["trail_len"]):
                y = head_y - i
                if 0 <= y < self.h and 0 <= x < self.w:
                    if i == 0:
                        char = random.choice(_MATRIX_CHARS) if random.random() < 0.3 else col["char"]
                        if self.glitch_level >= 2:
                            # 초록+빨간색 혼합
                            if random.random() < 0.3:
                                console.print(x, y, char, fg=(255, 80, 80))
                            else:
                                console.print(x, y, char, fg=(200, 255, 200))
                        elif self.glitch_level == 1 and random.random() < 0.05:
                            # 아주 가끔 1~2열만 붉은 깜빡임
                            console.print(x, y, char, fg=(255, 100, 100))
                        else:
                            console.print(x, y, char, fg=(200, 255, 200))
                    else:
                        fade = _clamp(180 - i * 20)
                        if random.random() < 0.1:
                            col["char"] = random.choice(_MATRIX_CHARS)
                        if self.glitch_level >= 2 and random.random() < 0.15:
                            console.print(x, y, col["char"], fg=(fade, 0, 0))
                        else:
                            console.print(x, y, col["char"], fg=(0, fade, 0))

    def _render_studio_text(self, console: tcod.console.Console, progress: float):
        """APTOL 스튜디오 텍스트 (글리치 스크램블 효과)"""
        text = "A P T O L"
        sub_text = "P R E S E N T S"

        cx = self.w // 2
        cy = self.h // 2

        # 글리치 레벨에 따른 부패율 조정
        if self.glitch_level >= 2:
            corrupt_threshold = 0.6  # 60% 부패
        elif self.glitch_level == 1:
            corrupt_threshold = 0.4  # 40% 부패
        else:
            corrupt_threshold = 0.3  # 기본 30% (progress < 0.6일 때 미공개 문자)

        if progress < 0.6:
            revealed = int(len(text) * (progress / 0.6))
            display = ""
            for i, c in enumerate(text):
                if c == " ":
                    display += " "
                elif i < revealed:
                    # 글리치 모드: 이미 공개된 글자도 다시 깨질 수 있음
                    if self.glitch_level >= 2 and random.random() < 0.2:
                        display += random.choice("█▓▒░")
                    else:
                        display += c
                else:
                    display += random.choice(_MATRIX_CHARS)
            if self.glitch_level >= 2:
                # 빨간 글리치 문자 색상
                r = random.randint(150, 255)
                fg = (r, random.randint(0, 50), random.randint(0, 30))
            else:
                r = random.randint(0, 30)
                fg = (r, _clamp(random.randint(180, 255)), r)
        else:
            display = text
            # 글리치 레벨 2: 수평 떨림
            if self.glitch_level >= 2 and random.random() < 0.3:
                display = ''.join(
                    random.choice("█▓▒░") if random.random() < corrupt_threshold and c != ' ' else c
                    for c in text
                )
            elif self.glitch_level == 1 and random.random() < 0.1:
                display = ''.join(
                    random.choice("▒░") if random.random() < 0.1 and c != ' ' else c
                    for c in text
                )

            pulse = math.sin(progress * 8) * 25
            if self.glitch_level >= 2:
                fg = (_clamp(int(220 + pulse)), _clamp(int(80 + pulse * 0.3)), _clamp(int(80 + pulse * 0.3)))
            else:
                fg = (_clamp(int(200 + pulse)), _clamp(int(210 + pulse)), 250)

        # 글리치 레벨 2: 수평 떨림 (x 오프셋 랜덤)
        x_offset = 0
        if self.glitch_level >= 2 and random.random() < 0.15:
            x_offset = random.choice([-2, -1, 1, 2])

        x = cx - len(display) // 2 + x_offset
        console.print(x, cy - 1, display, fg=fg)

        if progress > 0.4:
            sub_progress = (progress - 0.4) / 0.6
            alpha = min(1.0, sub_progress * 2)
            gray = _clamp(int(120 * alpha))
            console.print(cx - len(sub_text) // 2, cy + 1, sub_text, fg=(gray, gray, gray))

    def _render_title(self, console: tcod.console.Console, progress: float):
        """게임 타이틀 렌더링 (박스를 프로그래밍으로 그려서 테두리 정렬 보장)"""
        num_lines = len(_TITLE_LINES)
        start_y = self.h // 2 - num_lines // 2
        box_x = self.w // 2 - _BOX_WIDTH // 2

        border_color = (0, 180, 200)
        side_color = (0, 160, 180)

        for i, (ltype, content) in enumerate(_TITLE_LINES):
            line_delay = i * 0.08
            lp = max(0, min(1.0, (progress - line_delay) / 0.3))
            if lp <= 0:
                continue

            y = start_y + i

            if ltype in ("border_top", "border_bottom"):
                # 상/하 테두리를 고정 위치에 그리기
                if ltype == "border_top":
                    full = "╔" + "═" * _BOX_INNER + "╗"
                else:
                    full = "╚" + "═" * _BOX_INNER + "╝"

                if lp < 1.0:
                    revealed = int(len(full) * lp)
                    display = "".join(
                        c if j < revealed else random.choice("─┄┈")
                        for j, c in enumerate(full)
                    )
                    fg = (0, _clamp(int(200 * lp)), _clamp(int(100 * lp)))
                else:
                    display = full
                    fg = border_color
                console.print(box_x, y, display, fg=fg)

            elif ltype == "empty":
                # 좌/우 테두리만 고정 위치에 그리기
                fade = _clamp(int(160 * lp)) if lp < 1.0 else 160
                sc = (0, fade, _clamp(int(fade * 0.9)))
                console.print(box_x, y, "║", fg=sc)
                console.print(box_x + _BOX_WIDTH - 1, y, "║", fg=sc)

            elif ltype == "text":
                # 좌/우 테두리
                fade = _clamp(int(160 * lp)) if lp < 1.0 else 160
                sc = (0, fade, _clamp(int(fade * 0.9)))
                console.print(box_x, y, "║", fg=sc)
                console.print(box_x + _BOX_WIDTH - 1, y, "║", fg=sc)

                # 텍스트를 박스 안에서 중앙 정렬
                text_w = _display_width(content)
                text_x = box_x + 1 + (_BOX_INNER - text_w) // 2

                if lp < 1.0:
                    revealed = int(len(content) * lp)
                    display = ""
                    for j, c in enumerate(content):
                        if j < revealed:
                            display += c
                        elif c == " ":
                            display += " "
                        else:
                            display += random.choice("░▒▓█")
                    fg = (0, _clamp(int(200 * lp)), _clamp(int(100 * lp)))
                else:
                    display = content
                    if "던" in content:
                        pulse = math.sin(time.time() * 3 + i * 0.5) * 20
                        fg = (_clamp(int(180 + pulse)), _clamp(int(200 + pulse)), 250)
                    else:
                        pulse = math.sin(time.time() * 4) * 30
                        fg = (250, _clamp(int(210 + pulse)), _clamp(int(100 + pulse)))
                console.print(text_x, y, display, fg=fg)

        # 별빛의 여명 서브타이틀
        if progress > 0.7:
            sub_progress = (progress - 0.7) / 0.3
            subtitle = "── 별빛의 여명 ──"
            # 글리치 레벨 2: 서브타이틀 간헐적 글리치
            if self.glitch_level >= 2 and random.random() < 0.2:
                subtitle = ''.join(
                    random.choice("█▓▒░") if random.random() < 0.3 and c not in (' ', '─', '─') else c
                    for c in subtitle
                )
            sub_y = start_y + num_lines + 1
            alpha = min(1.0, sub_progress * 2)
            gray = _clamp(int(200 * alpha))
            pulse = int(math.sin(time.time() * 2) * 25 * alpha)
            if self.glitch_level >= 2:
                console.print(
                    self.w // 2 - _display_width(subtitle) // 2, sub_y,
                    subtitle,
                    fg=(_clamp(gray + pulse), _clamp(int(gray * 0.3)), _clamp(int(gray * 0.3)))
                )
            else:
                console.print(
                    self.w // 2 - _display_width(subtitle) // 2, sub_y,
                    subtitle,
                    fg=(_clamp(gray + pulse), gray, _clamp(int(gray * 0.8)))
                )

        # 별 파티클
        if progress > 0.3:
            if random.random() < 0.3:
                self.stars.append({
                    "x": random.randint(2, self.w - 3),
                    "y": random.randint(1, self.h - 2),
                    "life": random.uniform(0.3, 1.0),
                    "char": random.choice(".*+"),
                })

            remaining = []
            for star in self.stars:
                star["life"] -= 0.02
                if star["life"] > 0:
                    b = _clamp(int(255 * star["life"]))
                    # 글리치 레벨 2: 별 파티클 일부 붉은색
                    if self.glitch_level >= 2 and random.random() < 0.25:
                        console.print(
                            star["x"], star["y"], star["char"],
                            fg=(b, _clamp(int(b * 0.3)), _clamp(int(b * 0.3)))
                        )
                    else:
                        console.print(
                            star["x"], star["y"], star["char"],
                            fg=(b, b, _clamp(int(b * 0.8)))
                        )
                    remaining.append(star)
            self.stars = remaining[-50:]

    def _render_scanlines(self, console: tcod.console.Console, progress: float):
        """CRT 스캔라인으로 화면 지우기"""
        sweep_y = int(self.h * progress)
        for y in range(min(sweep_y, self.h)):
            # 글리치 레벨 2: 간헐적 빈 라인 (노이즈 라인)
            if self.glitch_level >= 2 and random.random() < 0.08:
                for x in range(self.w):
                    console.print(x, y, random.choice("█▓"), fg=(_clamp(random.randint(80, 200)), 0, 0))
                continue

            for x in range(self.w):
                if y > sweep_y - 3:
                    if random.random() < 0.5:
                        if self.glitch_level >= 2:
                            # 더 진한 스캔라인 + 빨간 섞임
                            if random.random() < 0.3:
                                console.print(x, y, random.choice("░▒▓█"), fg=(_clamp(random.randint(80, 200)), 0, 0))
                            else:
                                console.print(x, y, random.choice("░▒▓█"), fg=(0, _clamp(random.randint(80, 200)), 0))
                        else:
                            console.print(x, y, random.choice("░▒▓"), fg=(0, _clamp(random.randint(50, 150)), 0))
                else:
                    console.print(x, y, " ")

    def run(self, console: tcod.console.Console, context: tcod.context.Context) -> None:
        """부트 스플래시 시퀀스 실행"""
        logger.info("부트 스플래시 시작")

        def stop_bgm(*, fade_out: bool) -> None:
            return None

        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        import pygame
        try:
            pygame.event.clear()
        except Exception:
            pass

        # 부트 스플래시 전용 BGM 재생
        try:
            from src.audio.audio_manager import play_bgm, stop_bgm as stop_boot_bgm
            stop_bgm = stop_boot_bgm
            play_bgm("boot_splash", loop=False, fade_in=False)
        except Exception:
            pass

        # 서버실 비프음 (Electrocardiogram) 로드
        _beep_sound = None
        _beep_next_time = 0.0
        _logo_done = False
        try:
            import numpy as np
            from pathlib import Path
            import sys
            if hasattr(sys, '_MEIPASS'):
                _base = Path(sys.executable).parent.parent if Path(sys.executable).parent.name == '_internal' else Path(sys.executable).parent
            else:
                _base = Path(__file__).parent.parent.parent
            _beep_path = _base / "assets" / "audio" / "se" / "Electrocardiogram.ogg"
            if _beep_path.exists():
                _beep_sound = pygame.mixer.Sound(str(_beep_path))
                logger.info(f"서버실 비프음 로드: {_beep_path}")
        except Exception as e:
            logger.debug(f"비프음 로드 실패: {e}")

        splash_start_time = time.time()

        # 인트로에서 넘어온 잔여 입력 이벤트 소진 (key-up 지연 대응)
        grace_until = time.time() + 0.5
        while time.time() < grace_until:
            for _ in tcod.event.get():
                pass
            unified_input_handler.get_action()
            try:
                import pygame
                pygame.event.pump()
                pygame.event.clear()
            except Exception:
                pass
            time.sleep(1.0 / 30.0)

        phases = [
            ("matrix_rain", 2.5),
            ("studio", 2.5),
            ("fade_studio", 0.6),
            ("title", 3.0),
            ("scanline_out", 1.0),
        ]

        for phase_name, phase_duration in phases:
            phase_start = time.time()

            while True:
                elapsed = time.time() - phase_start
                progress = min(1.0, elapsed / phase_duration)

                if self._skip_check():
                    logger.info("부트 스플래시 스킵됨")
                    try:
                        stop_bgm(fade_out=False)
                    except Exception:
                        pass
                    return

                try:
                    pygame.event.pump()
                except Exception:
                    pass

                console.clear()

                # 서버실 비프음: logo.wav 종료 후 불규칙 재생
                if _beep_sound is not None:
                    now = time.time()
                    if not _logo_done:
                        # logo.wav(BGM)가 끝났는지 체크
                        try:
                            if not pygame.mixer.music.get_busy():
                                _logo_done = True
                                _beep_next_time = now + random.uniform(0.1, 0.3)
                        except Exception:
                            pass
                    elif now >= _beep_next_time:
                        try:
                            _beep_sound.set_volume(random.uniform(0.15, 0.45))
                            _beep_sound.play()
                        except Exception:
                            pass
                        # 다음 비프까지 불규칙 대기 (서버실 느낌)
                        _beep_next_time = now + random.uniform(0.1, 0.3)

                if phase_name == "matrix_rain":
                    self._render_matrix_rain(console, progress)
                    if progress > 0.7:
                        hint = _clamp(int((progress - 0.7) / 0.3 * 100))
                        console.print(
                            self.w // 2 - 4, self.h // 2 - 1,
                            "A P T O L", fg=(0, hint, 0)
                        )

                elif phase_name == "studio":
                    self._render_matrix_rain(console, 1.0)
                    # 매트릭스 레인을 서서히 어둡게 (1→2 장면 밝기 급변 방지)
                    dim = max(0.25, 1.0 - progress * 3.0)
                    for y in range(self.h):
                        for x in range(self.w):
                            r, g, b = console.fg[y, x]
                            console.fg[y, x] = (_clamp(int(r * dim)), _clamp(int(g * dim)), _clamp(int(b * dim)))
                    self._render_studio_text(console, progress)

                elif phase_name == "fade_studio":
                    dim = max(0.0, 1.0 - progress)
                    self._render_matrix_rain(console, 1.0)
                    for y in range(self.h):
                        for x in range(self.w):
                            r, g, b = console.fg[y, x]
                            console.fg[y, x] = (
                                _clamp(int(r * dim) // 5),
                                _clamp(int(g * dim) // 5),
                                _clamp(int(b * dim) // 5),
                            )
                    bright = _clamp(int(250 * dim))
                    text = "A P T O L"
                    sub = "P R E S E N T S"
                    cx, cy = self.w // 2, self.h // 2
                    console.print(cx - len(text) // 2, cy - 1, text, fg=(bright, bright, bright))
                    console.print(cx - len(sub) // 2, cy + 1, sub, fg=(_clamp(bright // 2), _clamp(bright // 2), _clamp(bright // 2)))

                elif phase_name == "title":
                    self._render_title(console, progress)
                    # 글리치 레벨 2: 간헐적 글리치 깜빡임 (전체 화면 노이즈 1프레임)
                    if self.glitch_level >= 2 and random.random() < 0.05:
                        for gy in range(random.randint(1, 3)):
                            ny = random.randint(0, self.h - 1)
                            for nx in range(self.w):
                                if random.random() < 0.6:
                                    console.print(nx, ny, random.choice("█▓▒░"), fg=(random.randint(150, 255), 0, 0))
                    # 글리치 레벨 1: 아주 드물게 한 프레임 글리치
                    elif self.glitch_level == 1 and random.random() < 0.01:
                        ny = random.randint(0, self.h - 1)
                        for nx in range(self.w):
                            if random.random() < 0.3:
                                console.print(nx, ny, random.choice("▒░"), fg=(random.randint(100, 200), 50, 50))

                elif phase_name == "scanline_out":
                    self._render_title(console, 1.0)
                    self._render_scanlines(console, progress)

                context.present(console)
                time.sleep(1.0 / 30.0)

                if elapsed >= phase_duration:
                    break

        # 부트 스플래시 BGM 정지
        try:
            stop_bgm(fade_out=True)
        except Exception:
            pass

        logger.info("부트 스플래시 완료")


def show_boot_splash(console: tcod.console.Console, context: tcod.context.Context,
                     glitch_level: int = 0) -> None:
    """부트 스플래시 표시 (인트로 → 메인 메뉴 사이)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        glitch_level: 글리치 강도 (0=없음, 1=약, 2=강)
    """
    splash = BootSplash(console.width, console.height, glitch_level=glitch_level)
    splash.run(console, context)
