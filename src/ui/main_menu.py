"""
Main Menu - 메인 메뉴

게임 시작 시 표시되는 메인 메뉴
"""

import tcod.console
import tcod.event
import math
import random
import time as _time_module
from typing import Optional, List
from enum import Enum

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatcher, PointerDispatchResult, PointerEvent, PointerEventKind, PointerRegion
from src.core.logger import get_logger
from src.audio import play_bgm, play_sfx
from src.ui.effects import (
    TextScrambler,
    ColorCycler,
    render_scrambled_text,
)


def _clamp(v: int) -> int:
    return max(0, min(255, v))


class MenuResult(Enum):
    """메뉴 결과"""
    NEW_GAME = "new_game"
    STORY_MODE = "story_mode"  # 스토리 모드 (튜토리얼)
    RPG_MODE = "rpg_mode"  # RPG 모드 (튜토리얼 완료 후 해금)
    CONTINUE = "continue"
    MULTIPLAYER = "multiplayer"  # 멀티플레이
    TRAINING = "training"  # 트레이닝 모드
    SHOP = "shop"
    SETTINGS = "settings"
    CREDITS = "credits"  # 크레딧
    QUIT = "quit"
    NONE = "none"


class MainMenu:
    """
    메인 메뉴

    - 새 게임
    - 계속하기
    - 멀티플레이
    - 상점
    - 설정
    - 종료
    """

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("main_menu")
        self.result: MenuResult = MenuResult.NONE

        # 글리치 레벨 감지 (싱글톤 기반)
        try:
            from src.story.story_system import get_story_system
            story_sys = get_story_system()
            if story_sys.cain_defeated:
                self.glitch_level = 0
            elif story_sys.sephiroth_defeated:
                self.glitch_level = 1
            elif story_sys.sephiroth_encountered:
                self.glitch_level = 2
            else:
                self.glitch_level = 0
        except Exception:
            self.glitch_level = 0

        # 글리치 타이머 (간헐적 효과용)
        self._glitch_timer = 0.0
        self._glitch_active = False
        self._glitch_flash_timer = 0.0

        # 애니메이션
        self.animation_frame = 0
        self._last_render_time = 0.0

        # ── 비트맵 폰트 (4x5 픽셀 - DAWN, STELLAR용) ──
        self.big_font = {
            'D': [
                [1,1,1,0],
                [1,0,0,1],
                [1,0,0,1],
                [1,0,0,1],
                [1,1,1,0]
            ],
            'A': [
                [0,1,1,0],
                [1,0,0,1],
                [1,1,1,1],
                [1,0,0,1],
                [1,0,0,1]
            ],
            'W': [
                [1,0,0,1],
                [1,0,0,1],
                [1,0,1,1],
                [1,1,0,1],
                [1,0,0,1]
            ],
            'N': [
                [1,0,0,1],
                [1,1,0,1],
                [1,0,1,1],
                [1,0,0,1],
                [1,0,0,1]
            ],
            'S': [
                [0,1,1,1],
                [1,0,0,0],
                [0,1,1,0],
                [0,0,0,1],
                [1,1,1,0]
            ],
            'T': [
                [1,1,1,1],
                [0,1,1,0],
                [0,1,1,0],
                [0,1,1,0],
                [0,1,1,0]
            ],
            'E': [
                [1,1,1,1],
                [1,0,0,0],
                [1,1,1,0],
                [1,0,0,0],
                [1,1,1,1]
            ],
            'L': [
                [1,0,0,0],
                [1,0,0,0],
                [1,0,0,0],
                [1,0,0,0],
                [1,1,1,1]
            ],
            'R': [
                [1,1,1,0],
                [1,0,0,1],
                [1,1,1,0],
                [1,0,1,0],
                [1,0,0,1]
            ],
        }

        # 작은 글씨 폰트 (3x3 픽셀 - OF용)
        self.small_font = {
            'O': [
                [1,1,1],
                [1,0,1],
                [1,1,1]
            ],
            'F': [
                [1,1,1],
                [1,1,0],
                [1,0,0]
            ],
        }

        self.subtitle = "별빛의 여명"

        # ── 3레이어 시차 별빛 (credits_ui 동일 기법) ──
        self.stars_layers: List[List[dict]] = [[], [], []]
        self._init_stars()

        # ── 유성 ──
        self.meteors: List[dict] = []

        # ── 타이틀 파티클 ──
        self.particles: List[dict] = []

        # 타이틀 색상
        self.title_gradient = [
            (100, 150, 255),
            (150, 180, 255),
            (200, 220, 255),
            (255, 240, 200),
            (255, 255, 150),
        ]

        # ── 텍스트 이펙트 ──
        self._subtitle_scrambler = TextScrambler(
            self.subtitle, duration=1.5, style="decode"
        )
        self._subtitle_scramble_done = False

        try:
            from src.core.config import get_config
            self._game_version = f"v{get_config().get('game.version', '1.0.0')}"
        except Exception:
            self._game_version = "v1.0.0"
        self._version_scrambler = TextScrambler(
            self._game_version, duration=0.8, style="random"
        )

        # 테두리/장식 색상 사이클러 (내부 phase로만 애니메이션, 느린 속도)
        self._border_cycler = ColorCycler(
            colors=[
                (60, 80, 180),
                (100, 120, 220),
                (80, 100, 200),
                (120, 140, 255),
            ],
            speed=0.25,
            mode="wave",
        )
        self._star_cycler = ColorCycler(
            colors=[
                (150, 180, 255),
                (255, 255, 200),
                (200, 220, 255),
                (255, 240, 150),
            ],
            speed=0.4,
            mode="sparkle",
        )
        # 메뉴 프레임 색상 사이클러
        self._frame_cycler = ColorCycler(
            colors=[
                (50, 70, 160),
                (80, 100, 200),
                (60, 90, 180),
                (100, 120, 230),
            ],
            speed=0.2,
            mode="wave",
        )

        # ── 레이아웃 ──
        self.title_start_y = 3

        # dt 계산용 (render에서 사용)
        self._last_render_time = 0.0

        # ── 다이얼 메뉴 초기화 ──
        self._init_dial()

    def _init_stars(self):
        """3레이어 시차 별빛 초기화"""
        for layer in range(3):
            count = [60, 35, 15][layer]
            speed = [0.02, 0.05, 0.12][layer]
            for _ in range(count):
                self.stars_layers[layer].append({
                    "x": random.uniform(0, self.screen_width),
                    "y": random.uniform(0, self.screen_height),
                    "brightness": random.uniform(0.3, 1.0),
                    "twinkle_phase": random.uniform(0, math.pi * 2),
                    "twinkle_speed": random.uniform(1.0, 3.0),
                    "speed": speed,
                    "char": random.choice("·.+*") if layer < 2 else random.choice("+*"),
                })

    def _init_dial(self):
        """다이얼 메뉴 초기화"""
        from src.persistence.save_system import SaveSystem
        save_system = SaveSystem()
        has_saves = len(save_system.list_saves()) > 0

        # RPG 모드 해금 여부 확인
        rpg_unlocked = self._check_rpg_unlock()

        self.dial_items = [
            {
                "text": "새 게임",
                "action": self._new_game,
                "description": "새로운 모험을 시작합니다",
                "enabled": True,
                "color": (140, 200, 255),
            },
            {
                "text": "튜토리얼",
                "action": self._open_story_mode,
                "description": "스토리와 함께 게임 시스템을 배웁니다",
                "enabled": True,
                "color": (140, 200, 255),
            },
            {
                "text": "RPG 모드" if rpg_unlocked else "RPG 모드 ■",
                "action": self._open_rpg_mode if rpg_unlocked else None,
                "description": "차원의 잔향 - 자유 탐험 RPG" if rpg_unlocked else "튜토리얼을 완료하면 해금됩니다",
                "enabled": rpg_unlocked,
                "color": (180, 160, 255),
            },
            {
                "text": "계속하기",
                "action": self._continue_game,
                "description": "저장된 게임을 불러옵니다",
                "enabled": has_saves,
                "color": (140, 255, 200),
            },
            {
                "text": "멀티플레이",
                "action": self._open_multiplayer,
                "description": "다른 플레이어와 함께 모험하기",
                "enabled": True,
                "color": (140, 255, 200),
            },
            {
                "text": "트레이닝",
                "action": self._open_training,
                "description": "허수아비와 전투하며 캐릭터를 연습합니다",
                "enabled": True,
                "color": (255, 220, 140),
            },
            {
                "text": "메타 진행",
                "action": self._open_shop,
                "description": "별빛의 파편으로 직업과 패시브를 구매합니다",
                "enabled": True,
                "color": (255, 220, 140),
            },
            {
                "text": "설정",
                "action": self._open_settings,
                "description": "게임 설정을 변경합니다",
                "enabled": True,
                "color": (180, 180, 200),
            },
            {
                "text": "크레딧",
                "action": self._open_credits,
                "description": "제작진 정보를 확인합니다",
                "enabled": True,
                "color": (180, 180, 200),
            },
            {
                "text": "종료",
                "action": self._quit_game,
                "description": "게임을 종료합니다",
                "enabled": True,
                "color": (150, 150, 170),
            },
        ]

        self.dial_index = 0
        self.dial_visible_range = 3  # 선택 항목 위아래 ±3개 표시
        self.dial_center_y = 31
        self.dial_frame_width = 40
        self.dial_frame_x = (self.screen_width - self.dial_frame_width) // 2

    # ── 액션 메서드 (변경 없음) ──────────────────────────────

    def _new_game(self) -> None:
        """새 게임 시작"""
        self.logger.info("새 게임 선택")
        self.result = MenuResult.NEW_GAME

    def _continue_game(self) -> None:
        """게임 계속하기"""
        self.logger.info("계속하기 선택")
        self.result = MenuResult.CONTINUE

    def _open_multiplayer(self) -> None:
        """멀티플레이 메뉴 열기"""
        self.logger.info("멀티플레이 선택")
        self.result = MenuResult.MULTIPLAYER

    def _open_shop(self) -> None:
        """상점 열기"""
        self.logger.info("상점 선택")
        self.result = MenuResult.SHOP

    def _open_settings(self) -> None:
        """설정 열기"""
        self.logger.info("설정 선택")
        self.result = MenuResult.SETTINGS

    def _quit_game(self) -> None:
        """게임 종료"""
        self.logger.info("종료 선택")
        self.result = MenuResult.QUIT

    def _open_story_mode(self) -> None:
        """스토리 모드(튜토리얼) 열기"""
        self.logger.info("튜토리얼(스토리 모드) 선택")
        self.result = MenuResult.STORY_MODE

    def _open_rpg_mode(self) -> None:
        """RPG 모드 열기"""
        self.logger.info("RPG 모드 선택")
        self.result = MenuResult.RPG_MODE

    @staticmethod
    def _check_rpg_unlock() -> bool:
        """RPG 모드 해금 여부 확인 (튜토리얼 전체 완료)"""
        try:
            from src.rpg_mode.rpg_mode_manager import RPGModeManager
            return RPGModeManager.check_unlock()
        except Exception:
            return False

    def _open_training(self) -> None:
        """트레이닝 모드 열기"""
        self.logger.info("트레이닝 모드 선택")
        self.result = MenuResult.TRAINING

    def _open_credits(self) -> None:
        """크레딧 열기"""
        self.logger.info("크레딧 선택")
        self.result = MenuResult.CREDITS

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리 (다이얼 회전)

        Args:
            action: 게임 액션

        Returns:
            메뉴가 종료되었으면 True
        """
        if action in (GameAction.MOVE_UP, GameAction.MOVE_LEFT):
            self._dial_rotate(-1)
        elif action in (GameAction.MOVE_DOWN, GameAction.MOVE_RIGHT):
            self._dial_rotate(1)
        elif action == GameAction.CONFIRM:
            return self._dial_select()
        elif action in (GameAction.ESCAPE, GameAction.QUIT):
            self.result = MenuResult.QUIT
            return True

        return False

    def _dial_rotate(self, direction: int):
        """다이얼 회전 (다음 활성 항목으로 이동)"""
        n = len(self.dial_items)
        original = self.dial_index
        for _ in range(n):
            self.dial_index = (self.dial_index + direction) % n
            if self.dial_items[self.dial_index]["enabled"]:
                break
        if self.dial_index != original:
            try:
                play_sfx("ui", "cursor_move")
                from src.core.vibration_system import vibration_manager
                vibration_manager.rumble_direct(0.2, 0.2, 100)
            except Exception:
                pass

    def _dial_select(self) -> bool:
        """다이얼 항목 선택"""
        item = self.dial_items[self.dial_index]
        if item["enabled"] and item["action"]:
            item["action"]()
            return self.result != MenuResult.NONE
        else:
            try:
                play_sfx("ui", "cursor_error")
            except Exception:
                pass
        return False

    def pointer_regions(self) -> tuple[PointerRegion, ...]:
        regions = []
        for index, item in enumerate(self.dial_items):
            offset = index - self.dial_index
            if offset > len(self.dial_items) // 2:
                offset -= len(self.dial_items)
            elif offset < -len(self.dial_items) // 2:
                offset += len(self.dial_items)
            if abs(offset) > self.dial_visible_range:
                continue
            y = self.dial_center_y + offset * 2
            description = str(item.get("description", ""))
            regions.append(
                PointerRegion(
                    region_id=str(index),
                    x=self.dial_frame_x + 2,
                    y=y,
                    width=self.dial_frame_width - 4,
                    height=1,
                    command=GameAction.CONFIRM,
                    tooltip=description,
                    enabled=True,
                )
            )
        return tuple(regions)

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        dispatcher = PointerDispatcher(self.pointer_regions())
        result = dispatcher.dispatch(event)
        region = dispatcher.region_at(event.position)
        region_id = result.hovered_region_id or (region.region_id if region else None)
        if region_id is not None:
            self.dial_index = int(region_id)
        if event.kind is PointerEventKind.WHEEL:
            self._dial_rotate(-1 if event.wheel_delta > 0 else 1)
            return result
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            self.result = MenuResult.QUIT
            return result.with_value(True)
        if event.kind is PointerEventKind.CLICK and result.action is not None:
            value = self.handle_input(result.action)
            return PointerDispatchResult(event=event, action=result.action, value=value, tooltip=region.tooltip if region else result.tooltip)
        return result

    # ── 렌더링 헬퍼 ──────────────────────────────────────────

    def _render_bg(self, console, t):
        """배경 우주 그라데이션 + 오로라"""
        aurora_limit = self.screen_height * 0.35

        # 글리치 간헐적 깜빡임 타이머 업데이트
        if self.glitch_level >= 2:
            self._glitch_timer += 0.033
            # 2~3초 간격으로 글리치 깜빡임
            if not self._glitch_active and self._glitch_timer > random.uniform(2.0, 3.0):
                self._glitch_active = True
                self._glitch_flash_timer = random.uniform(0.1, 0.25)
                self._glitch_timer = 0.0
            if self._glitch_active:
                self._glitch_flash_timer -= 0.033
                if self._glitch_flash_timer <= 0:
                    self._glitch_active = False
        elif self.glitch_level == 1:
            self._glitch_timer += 0.033
            if not self._glitch_active and self._glitch_timer > random.uniform(8.0, 12.0):
                self._glitch_active = True
                self._glitch_flash_timer = 0.05  # 1프레임 정도
                self._glitch_timer = 0.0
            if self._glitch_active:
                self._glitch_flash_timer -= 0.033
                if self._glitch_flash_timer <= 0:
                    self._glitch_active = False

        for y in range(self.screen_height):
            gi = max(0, int(3 + (y / self.screen_height) * 15))
            base_r, base_g, base_b = gi // 4, gi // 5, gi
            if y < aurora_limit:
                # 오로라가 있는 상단 영역: 셀별 계산
                for x in range(self.screen_width):
                    wave1 = math.sin(x * 0.06 + t * 0.8) * math.sin(y * 0.1 + t * 0.3)
                    wave2 = math.sin(x * 0.04 - t * 0.5 + 2.0) * math.cos(y * 0.07 + t * 0.4)
                    intensity = max(0, (wave1 + wave2) * 0.5)
                    y_factor = max(0, 1.0 - (y / aurora_limit))
                    intensity *= y_factor * 0.5
                    r = _clamp(base_r + int(intensity * 20))
                    g = _clamp(base_g + int(intensity * 55))
                    b = _clamp(base_b + int(intensity * 35))
                    # 글리치 레벨 2: 오로라에 붉은 톤 추가
                    if self.glitch_level >= 2:
                        red_wave = math.sin(x * 0.08 + t * 1.2) * 0.3
                        r = _clamp(r + int(max(0, red_wave) * 80 * y_factor))
                        g = _clamp(int(g * 0.7))
                    # 글리치 깜빡임 중이면 강한 적색
                    if self._glitch_active and random.random() < 0.15:
                        r = _clamp(r + random.randint(40, 100))
                        g = max(0, g - 20)
                        b = max(0, b - 20)
                    console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))
            else:
                # 오로라 없는 하단 영역: 균일 색상
                for x in range(self.screen_width):
                    console.rgb[y, x] = (ord(' '), (base_r, base_g, base_b), (base_r, base_g, base_b))

    def _render_stars(self, console, t):
        """3레이어 시차 별빛 렌더링"""
        for li in range(3):
            for star in self.stars_layers[li]:
                star["y"] += star["speed"]
                if star["y"] >= self.screen_height:
                    star["y"] = 0
                    star["x"] = random.uniform(0, self.screen_width)

                twinkle = 0.5 + 0.5 * math.sin(
                    t * star["twinkle_speed"] + star["twinkle_phase"]
                )
                brt = star["brightness"] * twinkle

                if li == 0:
                    color = (
                        _clamp(int(120 * brt)),
                        _clamp(int(130 * brt)),
                        _clamp(int(200 * brt)),
                    )
                elif li == 1:
                    v = _clamp(int(180 * brt))
                    color = (v, v, _clamp(int(v * 0.9)))
                else:
                    color = (
                        _clamp(int(220 * brt)),
                        _clamp(int(210 * brt)),
                        _clamp(int(170 * brt)),
                    )

                sx, sy = int(star["x"]), int(star["y"])
                if 0 <= sx < self.screen_width and 0 <= sy < self.screen_height:
                    console.print(sx, sy, star["char"], fg=color)

    def _update_meteors(self, console):
        """유성 업데이트 및 렌더링"""
        if random.random() < 0.02:
            self.meteors.append({
                "x": random.uniform(0, self.screen_width * 0.7),
                "y": random.uniform(0, self.screen_height * 0.3),
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
            if m["life"] > 0 and m["x"] < self.screen_width + 10 and m["y"] < self.screen_height + 10:
                for i in range(m["trail"]):
                    tx = int(m["x"] - m["vx"] * i * 0.4)
                    ty = int(m["y"] - m["vy"] * i * 0.4)
                    if 0 <= tx < self.screen_width and 0 <= ty < self.screen_height:
                        fade = max(0, m["life"] - i * 0.1)
                        v = _clamp(int(255 * fade))
                        ch = "*" if i == 0 else "·"
                        console.print(tx, ty, ch, fg=(v, v, _clamp(int(v * 0.7))))
                remaining.append(m)
        self.meteors = remaining[-15:]

    def _render_decoration_line(self, console, y, idx_offset):
        """상하 장식 라인: ══════════════ ✦ ══════════════"""
        cx = self.screen_width // 2
        half_len = 16

        # 중앙 별 (sparkle 모드 - 고정 위치, 내부 phase가 애니메이션)
        star_color = self._star_cycler.get_color(0)
        console.print(cx, y, "✦", fg=star_color)

        # 좌우 장식선 (ColorCycler wave - 공간 인덱스만 사용)
        for i in range(1, half_len + 1):
            line_color = self._border_cycler.get_color(i)
            lx = cx - i
            rx = cx + i
            if 0 <= lx < self.screen_width:
                console.print(lx, y, "═", fg=line_color)
            if 0 <= rx < self.screen_width:
                console.print(rx, y, "═", fg=line_color)

    def _render_title(self, console, t):
        """비트맵 타이틀 (DAWN/OF/STELLAR) - 8방향 글로우 + 색상 펄스"""
        title_y = self.title_start_y
        color_shift = math.sin(t / 3.0) * 30

        # 메인 타이틀 색상 (DAWN, STELLAR)
        if self.glitch_level >= 2 and self._glitch_active:
            # 글리치 깜빡임 중: 붉은 톤
            main_color = (
                _clamp(int(220 + color_shift)),
                _clamp(int(60 + color_shift * 0.3)),
                _clamp(int(60 + color_shift * 0.2)),
            )
            of_color = (
                _clamp(int(200 + color_shift * 0.3)),
                _clamp(int(80 + color_shift * 0.2)),
                _clamp(int(50 + color_shift * 0.1)),
            )
        else:
            main_color = (
                _clamp(int(140 + color_shift)),
                _clamp(int(200 + color_shift)),
                _clamp(int(255 + color_shift * 0.5)),
            )
            of_color = (
                _clamp(int(255 + color_shift * 0.3)),
                _clamp(int(220 + color_shift * 0.3)),
                _clamp(int(150 + color_shift * 0.2)),
            )
        shadow_color = (20, 30, 50)
        glow_pulse = 0.7 + 0.3 * math.sin(t / 2.0)

        def render_bitmap_text(text, font_dict, y_offset, char_width, color, use_glow):
            letter_spacing = 1
            total_width = (char_width + letter_spacing) * len(text) - letter_spacing
            start_x = (self.screen_width - total_width) // 2
            cur_x = start_x

            for char in text:
                if char not in font_dict:
                    cur_x += char_width + letter_spacing
                    continue
                for cy, row in enumerate(font_dict[char]):
                    for cx_off, pixel in enumerate(row):
                        if pixel != 1:
                            continue
                        px = cur_x + cx_off
                        py = title_y + y_offset + cy

                        # 그림자
                        sx, sy = px + 1, py + 1
                        if 0 <= sx < self.screen_width and 0 <= sy < self.screen_height:
                            ch_v, fg_v, _ = console.rgb[sy, sx]
                            console.rgb[sy, sx] = (ch_v, fg_v, shadow_color)

                        # 8방향 글로우 (대각선 포함) + 색상 펄스
                        if use_glow:
                            gc = (
                                _clamp(int(max(0, color[0] - 80) * glow_pulse)),
                                _clamp(int(max(0, color[1] - 80) * glow_pulse)),
                                _clamp(int(max(0, color[2] - 80) * glow_pulse)),
                            )
                            for dx in (-1, 0, 1):
                                for dy in (-1, 0, 1):
                                    if dx == 0 and dy == 0:
                                        continue
                                    gx, gy = px + dx, py + dy
                                    if 0 <= gx < self.screen_width and 0 <= gy < self.screen_height:
                                        ch_v, fg_v, cur_bg = console.rgb[gy, gx]
                                        if cur_bg[0] <= 100 and cur_bg[1] <= 100 and cur_bg[2] <= 100:
                                            console.rgb[gy, gx] = (ch_v, fg_v, gc)

                        # 메인 블록
                        if 0 <= px < self.screen_width and 0 <= py < self.screen_height:
                            ch_v, fg_v, _ = console.rgb[py, px]
                            console.rgb[py, px] = (ch_v, fg_v, color)

                cur_x += char_width + letter_spacing

        # DAWN (y=3~7)
        render_bitmap_text("DAWN", self.big_font, 0, 4, main_color, True)
        # OF (y=9~11)
        render_bitmap_text("OF", self.small_font, 6, 3, of_color, False)
        # STELLAR (y=13~17)
        render_bitmap_text("STELLAR", self.big_font, 10, 4, main_color, True)

    def _render_divider(self, console):
        """구분선 + 서브타이틀: ── ✦ 별빛의 여명 ✦ ──"""
        divider_y = 19

        if not self._subtitle_scramble_done:
            # 스크램블 디코딩 중
            subtitle_x = (self.screen_width - len(self.subtitle)) // 2
            render_scrambled_text(
                console, subtitle_x, divider_y,
                self._subtitle_scrambler,
                fg_resolved=(200, 200, 255),
                fg_scrambled=(0, 180, 80),
            )
        else:
            # 완료: 장식 구분선 포함 렌더링
            sub_len = len(self.subtitle)
            # "── ✦ {subtitle} ✦ ──" = sub_len + 10
            total_len = sub_len + 10
            dx = (self.screen_width - total_len) // 2

            sub_brightness = _clamp(int(200 + 55 * math.sin(self.animation_frame / 50.0)))
            sub_color = (sub_brightness, sub_brightness, 255)
            star_color = self._star_cycler.get_color(0)
            dash_color = self._border_cycler.get_color(0)

            # 글리치 모드: 서브타이틀 왜곡
            display_subtitle = self.subtitle
            if self.glitch_level >= 2 and self._glitch_active:
                display_subtitle = ''.join(
                    random.choice("█▓▒░") if random.random() < 0.3 else c
                    for c in self.subtitle
                )
                sub_color = (255, 80, 80)

            # 좌측: ──
            console.print(dx, divider_y, "──", fg=dash_color)
            # 좌측 ✦
            console.print(dx + 3, divider_y, "✦", fg=star_color)
            # 서브타이틀
            console.print(dx + 5, divider_y, display_subtitle, fg=sub_color)
            # 우측 ✦
            console.print(dx + 5 + sub_len + 1, divider_y, "✦", fg=star_color)
            # 우측: ──
            console.print(dx + 5 + sub_len + 3, divider_y, "──", fg=dash_color)

    # ── 다이얼 메뉴 렌더링 ─────────────────────────────────

    def _render_dial(self, console, t):
        """다이얼 메뉴 전체 렌더링"""
        n = len(self.dial_items)
        cy = self.dial_center_y

        # 비선택 항목 (먼 것부터 가까운 것 순으로)
        for dist in range(self.dial_visible_range, 0, -1):
            for direction in (-1, 1):
                offset = dist * direction
                idx = (self.dial_index + offset) % n
                item = self.dial_items[idx]
                self._render_dial_item(console, item, cy, offset, t)

        # 선택 항목 (프레임 포함, 맨 마지막에 그려서 위에 표시)
        selected = self.dial_items[self.dial_index]
        self._render_dial_selected(console, selected, cy, t)

        # 네비게이션 화살표 (맥동)
        arrow_brightness = 0.4 + 0.6 * math.sin(t * 3.0)
        arrow_v = _clamp(int(180 * arrow_brightness))
        arrow_color = (arrow_v, arrow_v, _clamp(int(arrow_v * 1.3)))

        arrow_y_top = cy - 9
        arrow_y_bot = cy + 9
        cx = self.screen_width // 2

        if arrow_y_top >= 0:
            console.print(cx, arrow_y_top, "▲", fg=arrow_color)
        if arrow_y_bot < self.screen_height:
            console.print(cx, arrow_y_bot, "▼", fg=arrow_color)

        # 항목 카운터 (우하단 다이얼 영역)
        counter = f"{self.dial_index + 1}/{n}"
        counter_x = self.dial_frame_x + self.dial_frame_width - len(counter) - 1
        counter_y = cy + 3
        if counter_y < self.screen_height:
            console.print(counter_x, counter_y, counter, fg=(80, 80, 100))

    def _render_dial_item(self, console, item, center_y, offset, t):
        """비선택 다이얼 항목 렌더링 (곡선 배치 + 밝기 감소)"""
        abs_off = abs(offset)

        # Y 위치 (선택 항목 위/아래, 간격 2)
        if offset < 0:
            y = center_y - 3 + (offset + 1) * 2
        else:
            y = center_y + 3 + (offset - 1) * 2

        if y < 0 or y >= self.screen_height:
            return

        # 밝기 (거리에 따라 감소)
        brightness = max(0.15, 1.0 - abs_off * 0.28)

        # 색상 결정
        if not item["enabled"]:
            base_color = (60, 60, 70)
        else:
            base_color = item["color"]

        text_color = tuple(_clamp(int(c * brightness)) for c in base_color)
        deco_color = tuple(_clamp(int(c * brightness * 0.35)) for c in base_color)

        # 텍스트
        text = item["text"]

        # 장식 (거리에 따라 다른 스타일 - 곡선감 표현)
        if abs_off == 1:
            left_deco = "── "
            right_deco = " ──"
        elif abs_off == 2:
            left_deco = " ╌ "
            right_deco = " ╌ "
        else:
            left_deco = "  · "
            right_deco = " ·  "

        # 글리치 효과
        if self.glitch_level >= 2 and self._glitch_active and random.random() < 0.2:
            text = ''.join(
                random.choice("█▓▒░") if random.random() < 0.5 else c
                for c in text
            )
            text_color = (_clamp(int(255 * brightness)), 50, 50)

        # 전체 문자열 중앙 정렬
        full = f"{left_deco}{text}{right_deco}"
        full_x = (self.screen_width - len(full)) // 2

        # 장식과 텍스트를 각각 다른 색으로 렌더링
        console.print(full_x, y, left_deco, fg=deco_color)
        console.print(full_x + len(left_deco), y, text, fg=text_color)
        console.print(full_x + len(left_deco) + len(text), y, right_deco, fg=deco_color)

    def _render_dial_selected(self, console, item, center_y, t):
        """선택된 다이얼 항목 렌더링 (프레임 + 선택 레일)"""
        fw = self.dial_frame_width
        fx = self.dial_frame_x
        cy = center_y

        # 프레임 색상 (애니메이션)
        fc = self._frame_cycler.get_color(0)

        # ── 선택 레일 (프레임 양쪽으로 뻗는 수평선) ──
        rail_color = tuple(_clamp(c // 3) for c in fc)
        for rx in range(3, fx):
            console.print(rx, cy, "─", fg=rail_color)
        for rx in range(fx + fw, self.screen_width - 3):
            console.print(rx, cy, "─", fg=rail_color)

        # 레일 끝 장식 (방향 표시)
        rail_tip = tuple(_clamp(c // 2) for c in fc)
        console.print(2, cy, "◀", fg=rail_tip)
        console.print(self.screen_width - 3, cy, "▶", fg=rail_tip)

        # ── 프레임 상단 ──
        fy_top = cy - 1
        console.print(fx, fy_top, "╔", fg=fc)
        for i in range(1, fw - 1):
            console.print(fx + i, fy_top, "═", fg=fc)
        console.print(fx + fw - 1, fy_top, "╗", fg=fc)

        # ── 프레임 좌우 (본체 행) ──
        console.print(fx, cy, "║", fg=fc)
        console.print(fx + fw - 1, cy, "║", fg=fc)

        # 프레임 내부 배경 (반투명 효과)
        for bx in range(fx + 1, fx + fw - 1):
            ch_v = console.rgb[cy, bx][0]
            console.rgb[cy, bx] = (ch_v, (200, 200, 200), (25, 30, 50))

        # ── 프레임 하단 ──
        fy_bot = cy + 1
        console.print(fx, fy_bot, "╚", fg=fc)
        for i in range(1, fw - 1):
            console.print(fx + i, fy_bot, "═", fg=fc)
        console.print(fx + fw - 1, fy_bot, "╝", fg=fc)

        # ── 선택 항목 텍스트 ──
        text = item["text"]

        # 색상 (밝은 맥동)
        pulse = 0.85 + 0.15 * math.sin(t * 2.5)
        if not item["enabled"]:
            text_color = (100, 100, 100)
        elif self.glitch_level >= 2 and self._glitch_active:
            text_color = (255, 80, 80)
            text = ''.join(
                random.choice("█▓▒░") if random.random() < 0.3 else c
                for c in text
            )
        else:
            text_color = tuple(
                _clamp(int(c * pulse)) for c in item["color"]
            )

        # ▸ 마커 (맥동 애니메이션)
        marker_pulse = 0.5 + 0.5 * math.sin(t * 4.0)
        marker_color = (
            _clamp(int(255 * marker_pulse)),
            _clamp(int(255 * marker_pulse)),
            _clamp(int(180 * marker_pulse)),
        )

        # 텍스트 렌더링 (프레임 내부 - 텍스트 기준 중앙 정렬)
        text_x = fx + (fw - len(text)) // 2
        console.print(text_x - 3, cy, "▸", fg=marker_color)
        console.print(text_x, cy, text, fg=text_color)

        # ── 설명 텍스트 (프레임 아래) ──
        desc = item["description"]
        desc_x = (self.screen_width - len(desc)) // 2
        desc_y = cy + 2
        desc_brightness = 0.65 + 0.1 * math.sin(t * 1.5)
        desc_color = tuple(_clamp(int(160 * desc_brightness)) for _ in range(3))

        if 0 <= desc_y < self.screen_height:
            console.print(desc_x, desc_y, desc, fg=desc_color)

    def _update_particles(self, console):
        """타이틀 주변 미세 반짝이 파티클"""
        # 생성 (0.1 확률)
        if random.random() < 0.1:
            self.particles.append({
                "x": random.uniform(self.screen_width * 0.2, self.screen_width * 0.8),
                "y": random.uniform(self.title_start_y, self.title_start_y + 15),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.5, 0.0),
                "life": random.uniform(0.3, 1.0),
                "char": random.choice("·.*"),
                "color": random.choice([
                    (200, 200, 255), (255, 255, 200), (180, 220, 255),
                ]),
            })

        remaining = []
        for p in self.particles:
            p["x"] += p["vx"] * 0.3
            p["y"] += p["vy"] * 0.3
            p["life"] -= 0.03
            if p["life"] > 0:
                alpha = min(1.0, p["life"])
                px, py = int(p["x"]), int(p["y"])
                if 0 <= px < self.screen_width and 0 <= py < self.screen_height:
                    c = p["color"]
                    fc = (
                        _clamp(int(c[0] * alpha)),
                        _clamp(int(c[1] * alpha)),
                        _clamp(int(c[2] * alpha)),
                    )
                    console.print(px, py, p["char"], fg=fc)
                remaining.append(p)
        self.particles = remaining[-30:]

    # ── 메인 렌더 ────────────────────────────────────────────

    def render(self, console: tcod.console.Console) -> None:
        """
        메인 메뉴 렌더링

        Args:
            console: 렌더링할 콘솔
        """
        console.clear()
        self.animation_frame += 1

        # dt 계산
        _now = _time_module.time()
        _dt = min(0.1, _now - self._last_render_time) if self._last_render_time > 0 else 0.033
        self._last_render_time = _now
        t = _now

        # 이펙트 업데이트
        self._border_cycler.update(_dt)
        self._star_cycler.update(_dt)
        self._frame_cycler.update(_dt)

        if not self._subtitle_scramble_done:
            self._subtitle_scrambler.update(_dt)
            self._version_scrambler.update(_dt)
            if self._subtitle_scrambler.is_complete:
                self._subtitle_scramble_done = True

        # 1. 배경 (그라데이션 + 오로라)
        self._render_bg(console, t)

        # 2. 3레이어 별빛
        self._render_stars(console, t)

        # 3. 유성
        self._update_meteors(console)

        # 4. 상단 장식 라인 (y=1)
        self._render_decoration_line(console, 1, self.animation_frame)

        # 5. 비트맵 타이틀 (DAWN/OF/STELLAR)
        self._render_title(console, t)

        # 6. 타이틀 파티클
        self._update_particles(console)

        # 7. 구분선 + 서브타이틀 (y=19)
        self._render_divider(console)

        # 8-10. 다이얼 메뉴 (프레임 + 항목 + 설명)
        self._render_dial(console, t)

        # 11. 조작 안내 (좌하단)
        controls = "▲▼: 회전  Z: 선택  X: 종료"
        console.print(2, self.screen_height - 2, controls, fg=Colors.GRAY)

        # 12. 버전 정보 (우하단)
        version = self._game_version
        # 글리치 레벨 2: 버전 텍스트 간헐적 글리치 치환
        if self.glitch_level >= 2 and self._glitch_active:
            version = ''.join(
                random.choice("█▓▒░") if random.random() < 0.4 else c
                for c in version
            )
        version_x = self.screen_width - len(self._game_version) - 2
        version_y = self.screen_height - 2
        if not self._version_scrambler.is_complete:
            render_scrambled_text(
                console, version_x, version_y,
                self._version_scrambler,
                fg_resolved=Colors.GRAY,
                fg_scrambled=(0, 120, 0),
            )
        else:
            if self.glitch_level >= 2 and self._glitch_active:
                console.print(version_x, version_y, version, fg=(200, 50, 50))
            else:
                console.print(version_x, version_y, version, fg=Colors.GRAY)

        # 업데이트 알림
        try:
            from src.core.updater import is_update_available, get_update_status
            if is_update_available():
                status = get_update_status()
                latest = status.get("latest_version", "")
                update_text = f"新 v{latest} 업데이트 가능! aptol.itch.io/dawn-of-stellar"
                if (self.animation_frame // 30) % 2 == 0:
                    update_color = Colors.YELLOW
                else:
                    update_color = (200, 180, 0)
                ux = self.screen_width - len(update_text) - 2
                console.print(ux, version_y - 1, update_text, fg=update_color)
        except Exception:
            pass

        # 13. 하단 장식 라인
        self._render_decoration_line(console, self.screen_height - 1, self.animation_frame + 20)

    def reset(self) -> None:
        """메뉴 상태 초기화"""
        self.result = MenuResult.NONE


def _handle_main_menu_pointer_event(menu: MainMenu, event) -> bool:
    pointer_event = unified_input_handler.process_pointer_event(event)
    if pointer_event is None:
        return False
    result = menu.handle_pointer_event(pointer_event)
    return bool(result.value and menu.result is not MenuResult.NONE)


def run_main_menu(console: tcod.console.Console, context: tcod.context.Context) -> MenuResult:
    """
    메인 메뉴 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        메뉴 선택 결과
    """
    import time

    # 메인 메뉴 BGM 재생
    play_bgm("main_menu")

    # 업데이트 확인 (백그라운드, 비동기)
    try:
        from src.core.updater import check_for_updates, is_update_available, get_update_message
        from src.core.config import get_config
        current_ver = get_config().get("game.version", "0.0.0")
        check_for_updates(current_ver)
    except Exception:
        pass  # 업데이터 로드 실패 시 무시

    menu = MainMenu(console.width, console.height)

    # 애니메이션을 위한 시간 관리
    last_time = time.time()
    frame_time = 1.0 / 30.0  # 30 FPS

    # 핫 리로드 체크를 위한 변수
    last_hot_reload_check = time.time()

    # 이전 화면에서 남은 입력 이벤트 제거 (키 반복/캐스케이드 방지)
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        current_time = time.time()
        delta_time = current_time - last_time

        # 핫 리로드 체크 (개발 모드일 때만, 드물게 체크)
        if current_time - last_hot_reload_check >= 1.0:  # 1초마다 한 번만
            last_hot_reload_check = current_time
            try:
                from src.core.config import get_config
                config = get_config()
                if config.development_mode:
                    from src.core.hot_reload import check_and_reload
                    reloaded = check_and_reload()
                    if reloaded:
                        from src.core.logger import get_logger, Loggers
                        logger = get_logger(Loggers.SYSTEM)
                        logger.info(f"📦 [메뉴] 재로드된 모듈: {', '.join(reloaded)}")
            except Exception:
                pass  # 핫 리로드 오류는 무시

        # 프레임 제한 (30 FPS)
        if delta_time >= frame_time:
            last_time = current_time

            # 렌더링 (매 프레임마다 애니메이션 업데이트)
            menu.render(console)
            context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass

        # 키보드 입력 우선 처리
        keyboard_processed = False
        for event in tcod.event.get():
            if _handle_main_menu_pointer_event(menu, event):
                return menu.result

            action = unified_input_handler.process_tcod_event(event)

            if action:
                keyboard_processed = True
                if menu.handle_input(action):
                    # 메뉴 선택 SFX 재생 (키보드 입력 시)
                    if action == GameAction.CONFIRM:
                        try:
                            from src.audio import play_sfx
                            play_sfx("ui", "cursor_select")
                        except Exception as e:
                            pass
                    return menu.result

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return MenuResult.QUIT

        # 게임패드 입력 처리 (키보드 입력이 없었을 때만)
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if menu.handle_input(gamepad_action):
                    # 메뉴 선택 SFX 재생 (게임패드 입력 시)
                    if gamepad_action == GameAction.CONFIRM:
                        try:
                            from src.audio import play_sfx
                            play_sfx("ui", "cursor_select")
                        except Exception as e:
                            pass
                    return menu.result

        # CPU 사용률 낮추기
        time.sleep(0.01)
