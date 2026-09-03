"""
Credits UI - 크레딧 화면 (리메이크)

다양한 시각 효과와 트랜지션이 포함된 영화 스타일 크레딧:
  - 멀티레이어 별빛 시차, 매트릭스 레인, 오로라, 성운, 회로 기판 배경
  - 글리치 스크램블, 타이프라이터, 슬라이드, 스캔 리빌, 박스 드로잉 텍스트 효과
  - CRT 스캔라인, 디졸브 트랜지션
"""

import tcod.console
import tcod.event
import math
import time
import random
import unicodedata
from typing import List, Tuple

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerEvent, PointerEventKind
from src.ui.visual_tokens import TokenName, rgb
from src.core.logger import get_logger

_MATRIX_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>?/\\▓▒░█"
_GLITCH_CHARS = "░▒▓█┃┫┣╋╬╂"


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def _display_width(s: str) -> int:
    w = 0
    for c in s:
        if unicodedata.east_asian_width(c) in ('W', 'F'):
            w += 2
        else:
            w += 1
    return w


class CreditsUI:
    """다양한 시각 효과가 포함된 영화 스타일 크레딧 화면"""
    controls_token: TokenName = "text.secondary"

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        self.w = screen_width
        self.h = screen_height
        self.logger = get_logger("credits_ui")

        self.start_time = time.time()
        self.should_close = False
        self.frame = 0

        # 3레이어 별빛 시스템
        self.stars_layers: List[List[dict]] = [[], [], []]
        self._init_stars()

        # 매트릭스 레인
        self.rain_cols: List[dict] = []
        self._init_rain()

        # 유성
        self.meteors: List[dict] = []

        # 파티클
        self.particles: List[dict] = []

        # 디졸브 맵
        self.dissolve_map: List[Tuple[int, int]] = []
        self._init_dissolve_map()

        # 섹션
        self.sections = self._build_sections()
        self.total_duration = sum(s["duration"] for s in self.sections)

        self._prev_section = -1

    def _get_version(self) -> str:
        try:
            from src.core.config import get_config
            return get_config().get("game", {}).get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def _init_stars(self):
        for layer in range(3):
            count = [60, 35, 15][layer]
            speed = [0.02, 0.05, 0.12][layer]
            for _ in range(count):
                self.stars_layers[layer].append({
                    "x": random.uniform(0, self.w),
                    "y": random.uniform(0, self.h),
                    "brightness": random.uniform(0.3, 1.0),
                    "twinkle_phase": random.uniform(0, math.pi * 2),
                    "twinkle_speed": random.uniform(1.0, 3.0),
                    "speed": speed,
                    "char": random.choice("·.+*") if layer < 2 else random.choice("+*"),
                })

    def _init_rain(self):
        for x in range(self.w):
            self.rain_cols.append({
                "x": x,
                "y": random.randint(-self.h, 0),
                "speed": random.uniform(0.3, 1.0),
                "trail_len": random.randint(4, 12),
                "char": random.choice(_MATRIX_CHARS),
            })

    def _init_dissolve_map(self):
        cells = [(x, y) for y in range(self.h) for x in range(self.w)]
        random.shuffle(cells)
        self.dissolve_map = cells

    def _build_sections(self):
        gold = (255, 215, 100)
        bright_gold = (255, 235, 150)
        silver = (200, 200, 220)
        white = (255, 255, 255)
        light_blue = (150, 200, 255)
        dim = (120, 120, 140)
        cyan = (100, 220, 255)
        green = (100, 255, 150)

        return [
            {
                "lines": [
                    ("DAWN OF STELLAR", bright_gold),
                    ("별빛의 여명", gold),
                ],
                "duration": 18.0, "fade_time": 3.0,
                "bg": "deep_space", "reveal": "box_draw", "dismiss": "scanline",
            },
            {
                "lines": [
                    ("CREATED BY", silver),
                    ("", white),
                    ("앱톨", bright_gold),
                    ("APTOL", gold),
                ],
                "duration": 20.0, "fade_time": 3.0,
                "bg": "matrix", "reveal": "glitch", "dismiss": "dissolve",
            },
            {
                "lines": [
                    ("GAME DESIGN", silver),
                    ("게임 기획", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 16.0, "fade_time": 2.5,
                "bg": "nebula", "reveal": "typewriter", "dismiss": "fade",
            },
            {
                "lines": [
                    ("SYSTEM DESIGN", silver),
                    ("시스템 설계", dim),
                    ("", white),
                    ("ATB + BRV 전투 시스템", cyan),
                    ("36종 직업 시스템", cyan),
                    ("로그라이크 던전 생성", cyan),
                ],
                "duration": 18.0, "fade_time": 2.5,
                "bg": "circuit", "reveal": "scan", "dismiss": "scanline",
            },
            {
                "lines": [
                    ("PROGRAMMING", silver),
                    ("프로그래밍", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 16.0, "fade_time": 2.5,
                "bg": "matrix", "reveal": "glitch", "dismiss": "fade",
            },
            {
                "lines": [
                    ("ENGINE & FRAMEWORK", silver),
                    ("엔진 & 프레임워크", dim),
                    ("", white),
                    ("Python 3.10+", green),
                    ("Pygame", green),
                    ("TCOD", green),
                ],
                "duration": 16.0, "fade_time": 2.5,
                "bg": "deep_space", "reveal": "slide", "dismiss": "dissolve",
            },
            {
                "lines": [
                    ("ART DIRECTION", silver),
                    ("아트 디렉션", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 14.0, "fade_time": 2.0,
                "bg": "aurora", "reveal": "fade", "dismiss": "fade",
            },
            {
                "lines": [
                    ("SOUND & MUSIC", silver),
                    ("사운드 & 음악", dim),
                    ("", white),
                    ("앱톨", white),
                ],
                "duration": 14.0, "fade_time": 2.0,
                "bg": "waveform", "reveal": "typewriter", "dismiss": "fade",
            },
            {
                "lines": [
                    ("GAME FEATURES", silver),
                    ("게임 특징", dim),
                    ("", white),
                    ("★ Final Fantasy 스타일 ATB 전투", light_blue),
                    ("★ BRV/HP 공격 전략 시스템", light_blue),
                    ("★ 36종의 고유한 직업", light_blue),
                    ("★ 52종의 요리 레시피", light_blue),
                ],
                "duration": 20.0, "fade_time": 2.5,
                "bg": "meteor_shower", "reveal": "slide", "dismiss": "scanline",
            },
            {
                "lines": [
                    ("GAME FEATURES", silver),
                    ("게임 특징", dim),
                    ("", white),
                    ("★ 연금술 시스템", light_blue),
                    ("★ 팀워크 스킬", light_blue),
                    ("★ 멀티플레이어 지원", light_blue),
                    ("★ 메타 진행 시스템", light_blue),
                ],
                "duration": 20.0, "fade_time": 2.5,
                "bg": "aurora", "reveal": "typewriter", "dismiss": "dissolve",
            },
            {
                "lines": [
                    ("SPECIAL THANKS", silver),
                    ("특별한 감사", dim),
                    ("", white),
                    ("플레이해 주신 모든 분들께", white),
                    ("감사드립니다", white),
                    ("", white),
                    ("Thank you for playing!", gold),
                ],
                "duration": 22.0, "fade_time": 3.0,
                "bg": "sparkle", "reveal": "fade", "dismiss": "fade",
            },
            {
                "lines": [
                    ("© 2024-2025 APTOL", dim),
                    ("All Rights Reserved", dim),
                    ("", white),
                    (f"VERSION {self._get_version()}", gold),
                ],
                "duration": 18.0, "fade_time": 3.0,
                "bg": "circuit", "reveal": "scan", "dismiss": "scanline",
            },
            {
                "lines": [
                    ("Dawn of Stellar", bright_gold),
                    ("별빛의 여명", gold),
                    ("", white),
                    ("별빛이 당신의 여정을 비추길...", light_blue),
                    ("May the starlight guide your journey...", silver),
                ],
                "duration": 28.0, "fade_time": 4.0,
                "bg": "finale", "reveal": "box_draw", "dismiss": "fade",
            },
        ]

    # ── 배경 효과 ─────────────────────────────────────

    def _render_stars_overlay(self, console, t, layers=None, count_limit=None):
        """별빛 오버레이 (공용)"""
        if layers is None:
            layers = range(3)
        for li in layers:
            layer = self.stars_layers[li]
            limit = count_limit or len(layer)
            for star in layer[:limit]:
                star["y"] += star["speed"]
                if star["y"] >= self.h:
                    star["y"] = 0
                    star["x"] = random.uniform(0, self.w)

                twinkle = 0.5 + 0.5 * math.sin(t * star["twinkle_speed"] + star["twinkle_phase"])
                b = star["brightness"] * twinkle

                if li == 0:
                    color = (_clamp(int(120 * b)), _clamp(int(130 * b)), _clamp(int(200 * b)))
                elif li == 1:
                    v = _clamp(int(180 * b))
                    color = (v, v, _clamp(int(v * 0.9)))
                else:
                    color = (_clamp(int(220 * b)), _clamp(int(210 * b)), _clamp(int(170 * b)))

                sx, sy = int(star["x"]), int(star["y"])
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    console.print(sx, sy, star["char"], fg=color)

    def _fill_dark_gradient(self, console):
        """어두운 우주 그라데이션"""
        for y in range(self.h):
            gi = max(0, int(3 + (y / self.h) * 12))
            r, g, b = gi // 4, gi // 5, gi
            for x in range(self.w):
                console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))

    def _bg_deep_space(self, console, t):
        self._fill_dark_gradient(console)
        self._render_stars_overlay(console, t)
        self._update_meteors(console, t, 0.02)

    def _bg_matrix(self, console, t):
        for y in range(self.h):
            for x in range(self.w):
                console.rgb[y, x] = (ord(' '), (0, 0, 0), (0, 5, 0))

        for col in self.rain_cols:
            col["y"] += col["speed"]
            if col["y"] > self.h + col["trail_len"]:
                col["y"] = random.randint(-self.h // 2, 0)
                col["speed"] = random.uniform(0.3, 1.0)
                col["char"] = random.choice(_MATRIX_CHARS)

            head_y = int(col["y"])
            x = col["x"]
            for i in range(col["trail_len"]):
                y = head_y - i
                if 0 <= y < self.h and 0 <= x < self.w:
                    if i == 0:
                        ch = random.choice(_MATRIX_CHARS) if random.random() < 0.3 else col["char"]
                        console.print(x, y, ch, fg=(150, 255, 150))
                    else:
                        fade = _clamp(120 - i * 15)
                        console.print(x, y, col["char"], fg=(0, fade, 0))

    def _bg_nebula(self, console, t):
        for y in range(self.h):
            for x in range(self.w):
                r = _clamp(int(8 + 6 * math.sin(x * 0.05 + t * 0.3)))
                g = _clamp(int(4 + 4 * math.sin(y * 0.08 + t * 0.2 + 1.5)))
                b = _clamp(int(15 + 10 * math.sin((x + y) * 0.04 + t * 0.25)))
                console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))
        self._render_stars_overlay(console, t, layers=[0], count_limit=20)

    def _bg_circuit(self, console, t):
        for y in range(self.h):
            for x in range(self.w):
                console.rgb[y, x] = (ord(' '), (0, 2, 5), (0, 2, 5))

        for i in range(0, self.w, 8):
            pulse = 0.3 + 0.7 * abs(math.sin(t * 0.5 + i * 0.1))
            g = _clamp(int(25 * pulse))
            b = _clamp(int(40 * pulse))
            for y in range(self.h):
                if (y + int(t * 2)) % 4 == 0:
                    console.print(i, y, "─", fg=(0, g, b))

        for j in range(0, self.h, 6):
            pulse = 0.3 + 0.7 * abs(math.sin(t * 0.4 + j * 0.15))
            g = _clamp(int(25 * pulse))
            b = _clamp(int(40 * pulse))
            for x in range(self.w):
                if (x + int(t * 3)) % 6 == 0:
                    console.print(x, j, "│", fg=(0, g, b))

        for i in range(0, self.w, 8):
            for j in range(0, self.h, 6):
                pulse = abs(math.sin(t + i * 0.2 + j * 0.3))
                if pulse > 0.7:
                    console.print(i, j, "◆", fg=(0, _clamp(int(60 * pulse)), _clamp(int(80 * pulse))))

    def _bg_aurora(self, console, t):
        for y in range(self.h):
            for x in range(self.w):
                wave1 = math.sin(x * 0.06 + t * 0.8) * math.sin(y * 0.1 + t * 0.3)
                wave2 = math.sin(x * 0.04 - t * 0.5 + 2.0) * math.cos(y * 0.07 + t * 0.4)
                intensity = max(0, (wave1 + wave2) * 0.5)
                y_factor = max(0, 1.0 - (y / (self.h * 0.4)))
                intensity *= y_factor
                r = _clamp(int(intensity * 30))
                g = _clamp(int(intensity * 80 + 3))
                b = _clamp(int(intensity * 50 + 8))
                console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))
        self._render_stars_overlay(console, t, layers=[0], count_limit=30)

    def _bg_waveform(self, console, t):
        for y in range(self.h):
            for x in range(self.w):
                console.rgb[y, x] = (ord(' '), (2, 2, 8), (2, 2, 8))

        num_bars = 40
        bar_width = max(1, self.w // num_bars)
        for i in range(num_bars):
            height = abs(math.sin(t * 2.0 + i * 0.4)) * 0.4
            height += abs(math.sin(t * 3.5 + i * 0.7)) * 0.3
            height += abs(math.sin(t * 1.2 + i * 0.2)) * 0.3
            bar_h = int(height * self.h * 0.4)

            bx = i * bar_width + bar_width // 2
            for dy in range(bar_h):
                by = self.h - 1 - dy
                if 0 <= bx < self.w and 0 <= by < self.h:
                    ratio = dy / max(1, bar_h)
                    if ratio < 0.6:
                        r, g, b = 0, _clamp(int(80 + 100 * ratio)), _clamp(int(60 * ratio))
                    elif ratio < 0.85:
                        r, g, b = _clamp(int(150 * (ratio - 0.6) / 0.25)), 140, 0
                    else:
                        r, g, b = 180, 60, 0
                    console.print(bx, by, "█", fg=(r, g, b))

    def _bg_meteor_shower(self, console, t):
        self._fill_dark_gradient(console)
        self._render_stars_overlay(console, t)
        self._update_meteors(console, t, 0.15)

    def _bg_sparkle(self, console, t):
        self._fill_dark_gradient(console)
        self._render_stars_overlay(console, t)

        if random.random() < 0.3:
            cx, cy = self.w // 2, self.h // 2
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.0)
            self.particles.append({
                "x": cx + random.uniform(-5, 5),
                "y": cy + random.uniform(-3, 3),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.uniform(0.5, 1.5),
                "char": random.choice(".*+·"),
                "color": random.choice([
                    (255, 220, 100), (200, 200, 255), (255, 180, 180),
                    (180, 255, 200), (255, 255, 200),
                ]),
            })

        remaining = []
        for p in self.particles:
            p["x"] += p["vx"] * 0.5
            p["y"] += p["vy"] * 0.5
            p["life"] -= 0.03
            if p["life"] > 0:
                alpha = min(1.0, p["life"])
                px, py = int(p["x"]), int(p["y"])
                if 0 <= px < self.w and 0 <= py < self.h:
                    c = p["color"]
                    fc = (_clamp(int(c[0] * alpha)), _clamp(int(c[1] * alpha)), _clamp(int(c[2] * alpha)))
                    console.print(px, py, p["char"], fg=fc)
                remaining.append(p)
        self.particles = remaining[-80:]

    def _bg_finale(self, console, t):
        for y in range(self.h):
            for x in range(self.w):
                wave = math.sin(x * 0.05 + t * 0.6) * math.sin(y * 0.08 + t * 0.2)
                y_factor = max(0, 1.0 - (y / (self.h * 0.5)))
                intensity = max(0, wave) * y_factor
                base_b = max(0, int(3 + (y / self.h) * 10))
                r = _clamp(int(intensity * 25 + 2))
                g = _clamp(int(intensity * 50 + base_b // 4))
                b = _clamp(int(intensity * 35 + base_b))
                console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))

        self._render_stars_overlay(console, t)
        self._update_meteors(console, t, 0.08)

        if random.random() < 0.15:
            self.particles.append({
                "x": random.uniform(0, self.w),
                "y": random.uniform(0, self.h),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.3, 0.0),
                "life": random.uniform(0.3, 1.0),
                "char": random.choice("·.*"),
                "color": (200, 200, 255),
            })

        remaining = []
        for p in self.particles:
            p["x"] += p["vx"] * 0.3
            p["y"] += p["vy"] * 0.3
            p["life"] -= 0.02
            if p["life"] > 0:
                a = min(1.0, p["life"])
                px, py = int(p["x"]), int(p["y"])
                if 0 <= px < self.w and 0 <= py < self.h:
                    c = p["color"]
                    console.print(px, py, p["char"], fg=(_clamp(int(c[0]*a)), _clamp(int(c[1]*a)), _clamp(int(c[2]*a))))
                remaining.append(p)
        self.particles = remaining[-60:]

    def _update_meteors(self, console, t, spawn_chance=0.05):
        if random.random() < spawn_chance:
            self.meteors.append({
                "x": random.uniform(0, self.w * 0.7),
                "y": random.uniform(0, self.h * 0.3),
                "vx": random.uniform(1.5, 3.5),
                "vy": random.uniform(0.8, 2.0),
                "life": random.uniform(0.4, 1.0),
                "trail": random.randint(3, 8),
            })

        remaining = []
        for m in self.meteors:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            m["life"] -= 0.03
            if m["life"] > 0 and m["x"] < self.w + 10 and m["y"] < self.h + 10:
                for i in range(m["trail"]):
                    tx = int(m["x"] - m["vx"] * i * 0.4)
                    ty = int(m["y"] - m["vy"] * i * 0.4)
                    if 0 <= tx < self.w and 0 <= ty < self.h:
                        fade = max(0, m["life"] - i * 0.1)
                        v = _clamp(int(255 * fade))
                        ch = "*" if i == 0 else "·"
                        console.print(tx, ty, ch, fg=(v, v, _clamp(int(v * 0.7))))
                remaining.append(m)
        self.meteors = remaining[-15:]

    # ── 텍스트 효과 ───────────────────────────────────

    def _render_text_fade(self, console, lines, alpha, start_y, time_in):
        for i, (text, base_color) in enumerate(lines):
            if not text:
                continue
            color = (_clamp(int(base_color[0] * alpha)),
                     _clamp(int(base_color[1] * alpha)),
                     _clamp(int(base_color[2] * alpha)))
            x = (self.w - _display_width(text)) // 2
            y = start_y + i * 2

            if i == 0 and alpha > 0.5:
                pulse = 0.9 + 0.1 * math.sin(self.frame / 15.0)
                color = (min(255, int(color[0] * pulse)),
                         min(255, int(color[1] * pulse)),
                         min(255, int(color[2] * pulse)))

            console.print(x, y, text, fg=color)

    def _render_text_glitch(self, console, lines, alpha, start_y, time_in):
        # 완전 표시 상태면 글리치 없이 렌더
        if alpha >= 1.0:
            self._render_text_fade(console, lines, alpha, start_y, time_in)
            return

        reveal = min(1.0, alpha * 1.5)
        for i, (text, base_color) in enumerate(lines):
            if not text:
                continue
            x = (self.w - _display_width(text)) // 2
            y = start_y + i * 2

            line_delay = i * 0.08
            lp = max(0, min(1.0, (reveal - line_delay) / 0.5))
            if lp <= 0:
                continue

            if lp < 1.0:
                revealed = int(len(text) * lp)
                display = ""
                for j, c in enumerate(text):
                    if c == " ":
                        display += " "
                    elif j < revealed:
                        display += c
                    else:
                        display += random.choice(_GLITCH_CHARS)
                glitch_r = random.randint(0, 30) if random.random() < 0.3 else 0
                color = (_clamp(int(base_color[0] * alpha) + glitch_r),
                         _clamp(int(base_color[1] * alpha)),
                         _clamp(int(base_color[2] * alpha)))
            else:
                display = text
                color = (_clamp(int(base_color[0] * alpha)),
                         _clamp(int(base_color[1] * alpha)),
                         _clamp(int(base_color[2] * alpha)))

            console.print(x, y, display, fg=color)

    def _render_text_typewriter(self, console, lines, alpha, start_y, time_in):
        total_chars = sum(len(t) for t, _ in lines if t)
        chars_to_show = int(total_chars * min(1.0, alpha * 1.8))

        char_count = 0
        for i, (text, base_color) in enumerate(lines):
            if not text:
                continue
            x = (self.w - _display_width(text)) // 2
            y = start_y + i * 2

            color = (_clamp(int(base_color[0] * alpha)),
                     _clamp(int(base_color[1] * alpha)),
                     _clamp(int(base_color[2] * alpha)))

            if char_count + len(text) <= chars_to_show:
                console.print(x, y, text, fg=color)
                char_count += len(text)
            elif char_count < chars_to_show:
                show = chars_to_show - char_count
                partial = text[:show]
                console.print(x, y, partial, fg=color)
                cursor_x = x + _display_width(partial)
                if int(self.frame / 8) % 2 == 0:
                    console.print(cursor_x, y, "█", fg=(200, 200, 200))
                char_count = chars_to_show

    def _render_text_slide(self, console, lines, alpha, start_y, time_in):
        for i, (text, base_color) in enumerate(lines):
            if not text:
                continue
            target_x = (self.w - _display_width(text)) // 2
            y = start_y + i * 2

            line_delay = i * 0.15
            lp = max(0, min(1.0, (alpha * 1.5 - line_delay) / 0.6))
            if lp <= 0:
                continue

            eased = 1.0 - (1.0 - lp) ** 3
            if i % 2 == 0:
                offset = int((1.0 - eased) * -self.w * 0.5)
            else:
                offset = int((1.0 - eased) * self.w * 0.5)

            x = target_x + offset
            fade = min(1.0, lp * 2) * alpha
            color = (_clamp(int(base_color[0] * fade)),
                     _clamp(int(base_color[1] * fade)),
                     _clamp(int(base_color[2] * fade)))
            console.print(x, y, text, fg=color)

    def _render_text_scan(self, console, lines, alpha, start_y, time_in):
        scan_progress = min(1.0, alpha * 1.5)
        for i, (text, base_color) in enumerate(lines):
            if not text:
                continue
            x = (self.w - _display_width(text)) // 2
            y = start_y + i * 2

            revealed_count = int(len(text) * scan_progress)
            display = ""
            for j, c in enumerate(text):
                display += c if j < revealed_count else " "

            color = (_clamp(int(base_color[0] * alpha)),
                     _clamp(int(base_color[1] * alpha)),
                     _clamp(int(base_color[2] * alpha)))
            console.print(x, y, display, fg=color)

            if scan_progress < 1.0:
                scan_x_pos = x + _display_width(text[:revealed_count])
                if 0 <= scan_x_pos < self.w:
                    console.print(scan_x_pos, y, "▌", fg=(0, 200, 255))

    def _render_text_box_draw(self, console, lines, alpha, start_y, time_in):
        max_tw = max(_display_width(t) for t, _ in lines if t) + 6
        box_w = max(max_tw, 30)
        box_h = len(lines) * 2 + 2
        box_x = (self.w - box_w) // 2
        box_y = start_y - 1

        reveal = min(1.0, alpha * 1.3)
        bc = (0, _clamp(int(180 * alpha)), _clamp(int(200 * alpha)))
        inner = box_w - 2

        if reveal > 0:
            # 상단 테두리
            br = min(1.0, reveal * 3)
            top = "╔" + "═" * inner + "╗"
            d = ""
            rw = int(len(top) * br)
            for j, c in enumerate(top):
                d += c if j < rw else (random.choice("─┄┈") if random.random() < 0.5 else " ")
            console.print(box_x, box_y, d[:box_w], fg=bc)

            # 하단 테두리
            if reveal > 0.3:
                bbr = min(1.0, (reveal - 0.3) * 3)
                bot = "╚" + "═" * inner + "╝"
                d = ""
                rw = int(len(bot) * bbr)
                for j, c in enumerate(bot):
                    d += c if j < rw else (random.choice("─┄┈") if random.random() < 0.5 else " ")
                console.print(box_x, box_y + box_h - 1, d[:box_w], fg=bc)

            # 좌우 테두리
            if reveal > 0.1:
                sr = min(1.0, (reveal - 0.1) * 2)
                for row in range(1, box_h - 1):
                    if row < int((box_h - 2) * sr) + 1:
                        ry = box_y + row
                        console.print(box_x, ry, "║", fg=bc)
                        console.print(box_x + box_w - 1, ry, "║", fg=bc)

        # 텍스트
        tr = max(0, (reveal - 0.2) / 0.8)
        if tr > 0:
            for i, (text, base_color) in enumerate(lines):
                if not text:
                    continue
                line_delay = i * 0.08
                lp = max(0, min(1.0, (tr - line_delay) / 0.4))
                if lp <= 0:
                    continue

                x = (self.w - _display_width(text)) // 2
                y = start_y + i * 2

                if lp < 1.0:
                    revealed = int(len(text) * lp)
                    display = ""
                    for j, c in enumerate(text):
                        if j < revealed:
                            display += c
                        elif c == " ":
                            display += " "
                        else:
                            display += random.choice("░▒▓█")
                    fg = (0, _clamp(int(200 * lp * alpha)), _clamp(int(100 * lp * alpha)))
                else:
                    display = text
                    pulse = math.sin(self.frame / 12.0 + i * 0.5) * 15
                    fg = (_clamp(int(base_color[0] * alpha + pulse)),
                          _clamp(int(base_color[1] * alpha + pulse)),
                          _clamp(int(base_color[2] * alpha)))

                console.print(x, y, display, fg=fg)

    # ── 퇴장 효과 ─────────────────────────────────────

    def _dismiss_scanline(self, console, progress):
        sweep_y = int(self.h * progress)
        for y in range(min(sweep_y, self.h)):
            for x in range(self.w):
                if y > sweep_y - 3:
                    if random.random() < 0.4:
                        console.print(x, y, random.choice("░▒"), fg=(0, _clamp(random.randint(20, 60)), 0))
                    else:
                        console.print(x, y, " ")
                else:
                    console.print(x, y, " ")

    def _dismiss_dissolve(self, console, progress):
        cells_to_clear = int(len(self.dissolve_map) * progress)
        for idx in range(min(cells_to_clear, len(self.dissolve_map))):
            x, y = self.dissolve_map[idx]
            if 0 <= x < self.w and 0 <= y < self.h:
                console.print(x, y, " ")

    # ── 메인 렌더 ─────────────────────────────────────

    def _get_section_timing(self):
        elapsed = time.time() - self.start_time
        accumulated = 0.0

        for i, section in enumerate(self.sections):
            section_start = accumulated
            section_end = accumulated + section["duration"]
            fade_time = section["fade_time"]

            if elapsed < section_end:
                time_in = elapsed - section_start

                if time_in < fade_time:
                    alpha = time_in / fade_time
                    phase = "reveal"
                elif time_in > section["duration"] - fade_time:
                    remaining = section["duration"] - time_in
                    alpha = remaining / fade_time
                    phase = "dismiss"
                else:
                    alpha = 1.0
                    phase = "display"

                return i, max(0.0, min(1.0, alpha)), time_in, phase

            accumulated = section_end

        return len(self.sections), 0.0, 0.0, "done"

    def render(self, console: tcod.console.Console) -> None:
        self.frame += 1
        t = time.time()
        console.clear()

        section_idx, alpha, time_in, phase = self._get_section_timing()

        if section_idx >= len(self.sections):
            msg = "[ Z / Enter: 돌아가기 ]"
            console.print((self.w - len(msg)) // 2, self.h // 2, msg, fg=rgb(self.controls_token))
            return

        section = self.sections[section_idx]

        if section_idx != self._prev_section:
            self._prev_section = section_idx
            self._init_dissolve_map()

        # 배경 효과
        bg_map = {
            "deep_space": self._bg_deep_space,
            "matrix": self._bg_matrix,
            "nebula": self._bg_nebula,
            "circuit": self._bg_circuit,
            "aurora": self._bg_aurora,
            "waveform": self._bg_waveform,
            "meteor_shower": self._bg_meteor_shower,
            "sparkle": self._bg_sparkle,
            "finale": self._bg_finale,
        }
        bg_map.get(section.get("bg", "deep_space"), self._bg_deep_space)(console, t)

        # 텍스트 영역
        lines = section["lines"]
        start_y = (self.h - len(lines) * 2) // 2

        # 텍스트 효과
        text_map = {
            "fade": self._render_text_fade,
            "glitch": self._render_text_glitch,
            "typewriter": self._render_text_typewriter,
            "slide": self._render_text_slide,
            "scan": self._render_text_scan,
            "box_draw": self._render_text_box_draw,
        }
        reveal_type = section.get("reveal", "fade")
        text_map.get(reveal_type, self._render_text_fade)(console, lines, alpha, start_y, time_in)

        # 퇴장 오버레이 (fade가 아닌 경우)
        dismiss_type = section.get("dismiss", "fade")
        if phase == "dismiss" and dismiss_type != "fade":
            fade_time = section["fade_time"]
            remaining = section["duration"] - time_in
            dp = max(0.0, min(1.0, 1.0 - remaining / fade_time))
            if dismiss_type == "scanline":
                self._dismiss_scanline(console, dp)
            elif dismiss_type == "dissolve":
                self._dismiss_dissolve(console, dp)

        # 하단 안내
        controls = "→/↓: 스킵  |  Z/Enter/X/ESC: 돌아가기"
        console.print((self.w - len(controls)) // 2, self.h - 2, controls, fg=rgb(self.controls_token))

        progress = f"[{section_idx + 1}/{len(self.sections)}]"
        console.print(self.w - len(progress) - 2, self.h - 2, progress, fg=rgb("text.muted"))

    def handle_input(self, action: GameAction) -> bool:
        if action in (GameAction.CONFIRM, GameAction.CANCEL, GameAction.ESCAPE):
            self.should_close = True
            return True
        if action in (GameAction.MOVE_DOWN, GameAction.MOVE_RIGHT):
            self._skip_to_next_section()
        return False

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        if event.kind is PointerEventKind.WHEEL:
            if event.wheel_delta < 0:
                self._skip_to_next_section()
                return PointerDispatchResult(event=event, action=GameAction.MOVE_DOWN)
            if event.wheel_delta > 0:
                self._skip_to_previous_section()
                return PointerDispatchResult(event=event, action=GameAction.MOVE_UP)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            self.handle_input(GameAction.CANCEL)
            return PointerDispatchResult(event=event, action=GameAction.CANCEL)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.LEFT:
            self.handle_input(GameAction.CONFIRM)
            return PointerDispatchResult(event=event, action=GameAction.CONFIRM)
        return PointerDispatchResult(event=event)

    def _skip_to_next_section(self):
        elapsed = time.time() - self.start_time
        accumulated = 0.0
        for section in self.sections:
            accumulated += section["duration"]
            if elapsed < accumulated:
                self.start_time = time.time() - accumulated
                break

    def _skip_to_previous_section(self):
        elapsed = time.time() - self.start_time
        accumulated = 0.0
        previous_start = 0.0
        for section in self.sections:
            section_end = accumulated + section["duration"]
            if elapsed < section_end:
                target = previous_start if elapsed - accumulated < 1.0 else accumulated
                self.start_time = time.time() - target
                break
            previous_start = accumulated
            accumulated = section_end


def run_credits(console: tcod.console.Console, context: tcod.context.Context) -> None:
    """크레딧 화면 실행"""
    try:
        from src.audio import play_bgm
        play_bgm("credits", loop=False, fade_in=True)
    except Exception:
        pass

    credits_ui = CreditsUI(console.width, console.height)

    last_time = time.time()
    frame_time = 1.0 / 30.0

    while not credits_ui.should_close:
        current_time = time.time()
        delta_time = current_time - last_time

        if delta_time >= frame_time:
            last_time = current_time
            credits_ui.render(console)
            context.present(console)

        try:
            import pygame
            pygame.event.pump()
        except Exception:
            pass

        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event is not None:
                pointer_result = credits_ui.handle_pointer_event(pointer_event)
                if pointer_result.action is not None and credits_ui.should_close:
                    try:
                        from src.audio.audio_manager import get_audio_manager
                        get_audio_manager().stop_bgm(fade_out=True)
                    except Exception:
                        pass
                    return
            if action:
                if credits_ui.handle_input(action):
                    try:
                        from src.audio.audio_manager import get_audio_manager
                        get_audio_manager().stop_bgm(fade_out=True)
                    except Exception:
                        pass
                    return

            if isinstance(event, tcod.event.Quit):
                try:
                    from src.audio.audio_manager import get_audio_manager
                    get_audio_manager().stop_bgm(fade_out=True)
                except Exception:
                    pass
                return

        gamepad_action = unified_input_handler.get_action()
        if gamepad_action:
            if credits_ui.handle_input(gamepad_action):
                try:
                    from src.audio.audio_manager import get_audio_manager
                    get_audio_manager().stop_bgm(fade_out=True)
                except Exception:
                    pass
                return

        time.sleep(0.01)

    try:
        from src.audio.audio_manager import get_audio_manager
        get_audio_manager().stop_bgm(fade_out=True)
    except Exception:
        pass
