"""
챕터 선택 UI
Dawn of Stellar - 별빛의 여명

스토리 모드 챕터를 선택하는 화면
- 별 파티클 배경 애니메이션
- Act별 색상 테마 & NPC 가이드 아이콘
- 진행률 바 시각화
- 동적 커서 & 정보 패널
"""

import math
import time
import random
from typing import Optional, List, Tuple

import tcod.console
import tcod.event

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion
from src.ui.visual_tokens import rgb
from src.audio import play_sfx
from src.core.logger import get_logger
from src.story_mode.story_mode_manager import (
    StoryModeProgress,
    CHAPTER_ORDER,
    CHAPTER_META,
    ACT_INFO,
)

logger = get_logger("story_mode")

# NPC 아이콘 (검증된 유니코드 문자만 사용)
NPC_ICONS = {
    "selena": ("✦", (0, 200, 255)),     # 시공의 안내자 - 시안
    "karnos": ("◆", (255, 100, 100)),   # 고대의 전사 - 적색
    "mira":   ("★", (255, 200, 100)),   # 시간의 마법사 - 황금
    "tord":   ("◆", (100, 200, 100)),   # 차원의 대장장이 - 녹색
    "lina":   ("★", (255, 150, 200)),   # 시공의 요리사 - 핑크
}

NPC_NAMES_KR = {
    "selena": "셀레나",
    "karnos": "카르노스",
    "mira": "미라",
    "tord": "토르드",
    "lina": "리나",
}

# 별 파티클 문자 (검증된 문자만)
_STAR_CHARS = [".", "*", "★", "☆", "✦", "+", "·"]
_STAR_COLORS_BASE = [
    (80, 80, 140), (100, 100, 180), (60, 80, 160),
    (120, 120, 200), (90, 90, 150), (70, 100, 170),
]


class StarParticle:
    """배경 별 파티클"""
    __slots__ = ('x', 'y', 'char', 'color', 'speed', 'phase', 'brightness')

    def __init__(self, w: int, h: int):
        self.x = random.randint(0, w - 1)
        self.y = random.randint(0, h - 1)
        self.char = random.choice(_STAR_CHARS)
        base = random.choice(_STAR_COLORS_BASE)
        self.color = base
        self.speed = random.uniform(0.3, 1.5)
        self.phase = random.uniform(0, math.pi * 2)
        self.brightness = random.uniform(0.3, 1.0)


class ChapterSelectState:
    """챕터 선택 화면 상태"""

    def __init__(self, w: int, h: int):
        # 별 파티클 생성 (밀도: 화면의 ~3%)
        count = max(20, (w * h) // 35)
        self.stars: List[StarParticle] = [StarParticle(w, h) for _ in range(count)]
        # 유성 효과
        self.meteors: List[dict] = []
        self._meteor_timer = 0.0


def _chapter_select_row_map() -> list[tuple[str, str]]:
    current_act = None
    row_map = []
    for ch_id in CHAPTER_ORDER:
        meta = CHAPTER_META[ch_id]
        ch_act = meta.get("act", "")
        if ch_act != current_act:
            current_act = ch_act
            row_map.append(("act_header", ch_act))
        row_map.append(("chapter", ch_id))
    return row_map


def _chapter_select_scroll_offset(selectable: list[str], cursor: int, max_visible: int) -> int:
    row_map = _chapter_select_row_map()
    selectable_set = set(selectable)
    cursor_abs = 0
    for idx, (rtype, rid) in enumerate(row_map):
        if rtype == "chapter" and rid in selectable_set:
            sel_idx = selectable.index(rid) if rid in selectable else -1
            if sel_idx == cursor:
                cursor_abs = idx
                break
    scroll_offset = max(0, cursor_abs - max_visible // 2)
    return min(scroll_offset, max(0, len(row_map) - max_visible))


def _chapter_pointer_regions(
    console_width: int,
    console_height: int,
    selectable: list[str],
    cursor: int,
) -> tuple[PointerRegion, ...]:
    list_x = max(2, (console_width - 60) // 2)
    list_y = 5
    max_visible = console_height - list_y - 12
    scroll_offset = _chapter_select_scroll_offset(selectable, cursor, max_visible)
    visible_rows = _chapter_select_row_map()[scroll_offset:scroll_offset + max_visible]
    selectable_set = set(selectable)
    regions = []
    for draw_idx, (rtype, rid) in enumerate(visible_rows):
        if rtype == "chapter" and rid in selectable_set:
            meta = CHAPTER_META[rid]
            tooltip = f"{meta.get('learning', '')} / 가이드: {meta.get('npc_guide', 'selena')}"
            regions.append(PointerRegion(rid, list_x, list_y + draw_idx, 58, 1, GameAction.CONFIRM, tooltip))
    return tuple(regions)


def _chapter_pointer_action(event: PointerEvent, regions: tuple[PointerRegion, ...]) -> tuple[GameAction | None, str | None, str | None]:
    result = PointerDispatcher(regions).dispatch(event)
    if event.kind is PointerEventKind.HOVER:
        return None, result.hovered_region_id, result.tooltip
    if event.kind is PointerEventKind.WHEEL:
        return result.action, None, None
    if event.kind is PointerEventKind.CLICK:
        if event.button is PointerButton.RIGHT:
            return GameAction.CANCEL, None, None
        if event.button is PointerButton.LEFT:
            return result.action, result.hovered_region_id, None
    return None, None, None


def run_chapter_select(
    console: tcod.console.Console,
    context: tcod.context.Context,
    progress: StoryModeProgress,
) -> Optional[str]:
    """
    챕터 선택 화면 실행

    Returns:
        선택된 chapter_id, None(뒤로), "__skip_all__"(전체 스킵)
    """
    cursor = 0
    animation_frame = 0
    w, h = console.width, console.height

    # 해금된 챕터 목록 (선택 가능)
    selectable = []
    for ch_id in CHAPTER_ORDER:
        if progress.is_chapter_unlocked(ch_id):
            selectable.append(ch_id)

    # 커서 초기 위치: 다음 진행할 챕터
    next_ch = progress.get_next_chapter()
    if next_ch and next_ch in selectable:
        cursor = selectable.index(next_ch)

    # 파티클 상태
    state = ChapterSelectState(w, h)

    # 입력 큐 비우기
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()
    time.sleep(0.05)
    for _ in tcod.event.get():
        pass

    last_time = time.time()
    pointer_tooltip: str | None = None

    while True:
        current_time = time.time()
        delta = current_time - last_time

        if delta >= 1.0 / 30.0:
            last_time = current_time
            animation_frame += 1
            _render_chapter_select(
                console, progress, cursor, selectable, animation_frame, state, pointer_tooltip
            )
            context.present(console)

        # pygame 이벤트
        try:
            import pygame
            pygame.event.pump()
        except Exception:
            pass

        # 키보드 입력
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event is not None:
                regions = _chapter_pointer_regions(w, h, selectable, cursor)
                pointer_action, hovered_chapter, tooltip = _chapter_pointer_action(pointer_event, regions)
                if hovered_chapter in selectable:
                    cursor = selectable.index(hovered_chapter)
                if tooltip is not None:
                    pointer_tooltip = tooltip
                if pointer_action is not None:
                    action = pointer_action
            if action:
                keyboard_processed = True

            if action == GameAction.MOVE_UP:
                cursor = max(0, cursor - 1)
                play_sfx("ui", "cursor_move")
            elif action == GameAction.MOVE_DOWN:
                cursor = min(len(selectable) - 1, cursor + 1)
                play_sfx("ui", "cursor_move")
            elif action == GameAction.CONFIRM:
                if selectable:
                    play_sfx("ui", "cursor_select")
                    return selectable[cursor]
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                play_sfx("ui", "cursor_cancel")
                return None

            # Tab: 전체 스킵
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.K_TAB:
                    return "__skip_all__"

            if isinstance(event, tcod.event.Quit):
                return None

        # 게임패드
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if gamepad_action == GameAction.MOVE_UP:
                    cursor = max(0, cursor - 1)
                    play_sfx("ui", "cursor_move")
                elif gamepad_action == GameAction.MOVE_DOWN:
                    cursor = min(len(selectable) - 1, cursor + 1)
                    play_sfx("ui", "cursor_move")
                elif gamepad_action == GameAction.CONFIRM:
                    if selectable:
                        play_sfx("ui", "cursor_select")
                        return selectable[cursor]
                elif gamepad_action == GameAction.CANCEL or gamepad_action == GameAction.ESCAPE:
                    play_sfx("ui", "cursor_cancel")
                    return None

        time.sleep(0.01)


def _render_star_background(
    console: tcod.console.Console, state: ChapterSelectState, frame: int
):
    """별 파티클 배경 렌더링"""
    w, h = console.width, console.height

    # 기본 배경: 깊은 우주 그라데이션
    for y in range(h):
        # 상단은 더 어두운 남색, 하단은 짙은 보라
        t = y / max(1, h - 1)
        r = int(2 + t * 8)
        g = int(2 + t * 4)
        b = int(8 + t * 18)
        for x in range(w):
            console.rgb[y, x] = (ord(" "), (r, g, b), (r, g, b))

    # 별 파티클 렌더링
    for star in state.stars:
        # 밝기 펄스
        pulse = math.sin(frame * 0.05 * star.speed + star.phase)
        brightness = star.brightness * (0.5 + 0.5 * pulse)
        if brightness < 0.15:
            continue

        sx, sy = star.x, star.y
        if 0 <= sx < w and 0 <= sy < h:
            r = min(255, int(star.color[0] * brightness))
            g = min(255, int(star.color[1] * brightness))
            b = min(255, int(star.color[2] * brightness))
            if r + g + b > 30:  # 너무 어두운 별은 건너뛰기
                console.print(sx, sy, star.char, fg=(r, g, b))

    # 유성 효과 (간헐적)
    state._meteor_timer += 1
    if state._meteor_timer > 120 and random.random() < 0.02:
        state._meteor_timer = 0
        state.meteors.append({
            "x": random.randint(0, w - 1),
            "y": 0,
            "dx": random.choice([-1, 0, 1]),
            "dy": 1,
            "life": random.randint(4, 8),
            "color": random.choice([(200, 200, 255), (255, 200, 150), (150, 200, 255)]),
        })

    new_meteors = []
    for m in state.meteors:
        mx, my = int(m["x"]), int(m["y"])
        if 0 <= mx < w and 0 <= my < h and m["life"] > 0:
            fade = m["life"] / 8.0
            c = m["color"]
            console.print(mx, my, "*", fg=(int(c[0]*fade), int(c[1]*fade), int(c[2]*fade)))
            # 꼬리
            tx, ty = mx - m["dx"], my - m["dy"]
            if 0 <= tx < w and 0 <= ty < h:
                console.print(tx, ty, "·", fg=(int(c[0]*fade*0.4), int(c[1]*fade*0.4), int(c[2]*fade*0.4)))
            m["x"] += m["dx"]
            m["y"] += m["dy"]
            m["life"] -= 1
            new_meteors.append(m)
    state.meteors = new_meteors


def _render_progress_bar(
    console: tcod.console.Console, x: int, y: int, width: int,
    completed: int, total: int, color: Tuple[int, int, int], frame: int,
):
    """진행률 바 렌더링"""
    if total <= 0:
        return

    ratio = completed / total
    filled = int(width * ratio)

    # 바 배경
    bar_bg = "░" * width
    console.print(x, y, bar_bg, fg=(40, 40, 60))

    # 바 채움
    if filled > 0:
        bar_fill = "█" * filled
        # 끝부분 펄스
        pulse = 0.7 + 0.3 * math.sin(frame * 0.1)
        pc = (min(255, int(color[0] * pulse)),
              min(255, int(color[1] * pulse)),
              min(255, int(color[2] * pulse)))
        console.print(x, y, bar_fill, fg=pc)

    # 퍼센트
    pct_text = f"{int(ratio * 100)}%"
    console.print(x + width + 1, y, pct_text, fg=color)


def _render_chapter_select(
    console: tcod.console.Console,
    progress: StoryModeProgress,
    cursor: int,
    selectable: list,
    frame: int,
    state: ChapterSelectState,
    pointer_tooltip: str | None = None,
):
    """챕터 선택 화면 렌더링"""
    console.clear()
    w, h = console.width, console.height

    # 1) 별 파티클 배경
    _render_star_background(console, state, frame)

    # 2) 타이틀 영역
    title = "★ 시공의 여명 ★"
    # 무지개빛 펄스
    hue_shift = frame * 0.03
    tr = max(0, min(255, int(180 + 75 * math.sin(hue_shift))))
    tg = max(0, min(255, int(180 + 75 * math.sin(hue_shift + 2.1))))
    tb = max(0, min(255, int(200 + 55 * math.sin(hue_shift + 4.2))))
    title_color = (tr, tg, tb)
    console.print((w - len(title)) // 2, 1, title, fg=title_color)

    # 장식 라인
    deco_line = "─═══─═══─═══─═══─═══─═══─"
    deco_brightness = 0.3 + 0.15 * math.sin(frame * 0.04)
    deco_color = (int(80 * deco_brightness), int(80 * deco_brightness), int(140 * deco_brightness))
    console.print((w - len(deco_line)) // 2, 2, deco_line, fg=deco_color)

    # 전체 진행률 바
    completed_count = len(progress.completed_chapters)
    total = len(CHAPTER_ORDER)
    _render_progress_bar(console, (w - 34) // 2, 3, 28, completed_count, total,
                         (100, 200, 255), frame)
    prog_label = f"전체 진행: {completed_count}/{total}"
    console.print((w - len(prog_label)) // 2 - 1, 3, "", fg=(100, 200, 255))

    # 구분선
    line = "─" * (min(60, w - 4))
    console.print((w - len(line)) // 2, 4, line, fg=(40, 40, 70))

    # 3) 챕터 리스트 (Act 그룹별, 스크롤 지원)
    list_x = max(2, (w - 60) // 2)
    list_y = 5
    selectable_set = set(selectable)

    # 스크롤 영역 계산
    max_visible = h - list_y - 12  # 하단 정보 패널용 공간 확보

    row_map = _chapter_select_row_map()

    scroll_offset = _chapter_select_scroll_offset(selectable, cursor, max_visible)

    visible_rows = row_map[scroll_offset:scroll_offset + max_visible]

    # 스크롤 인디케이터
    if scroll_offset > 0:
        console.print(w - 3, list_y, "▲", fg=(120, 120, 180))
    if scroll_offset + max_visible < len(row_map):
        console.print(w - 3, list_y + max_visible - 1, "▼", fg=(120, 120, 180))

    for draw_idx, (rtype, rid) in enumerate(visible_rows):
        y = list_y + draw_idx

        if rtype == "act_header":
            act_info = ACT_INFO.get(rid, {})
            act_color = act_info.get("color", (150, 150, 200))
            act_title = act_info.get("title", "")
            act_subtitle = act_info.get("subtitle", "")

            # Act 헤더 장식
            header_text = f"╔═ {act_title}: {act_subtitle} ═╗"
            # Act별 완료율 계산
            act_chapters = [c for c in CHAPTER_ORDER if CHAPTER_META[c].get("act") == rid]
            act_done = sum(1 for c in act_chapters if progress.is_chapter_completed(c))
            act_total = len(act_chapters)

            # 펄스 효과 (현재 진행 중인 Act만)
            cur_act = progress.get_current_act()
            if rid == cur_act:
                pulse = 0.7 + 0.3 * math.sin(frame * 0.08)
                ac = (min(255, int(act_color[0] * pulse)),
                      min(255, int(act_color[1] * pulse)),
                      min(255, int(act_color[2] * pulse)))
            else:
                dim = 0.6 if act_done == act_total else 0.4
                ac = (int(act_color[0] * dim), int(act_color[1] * dim), int(act_color[2] * dim))

            console.print(list_x, y, header_text, fg=ac)

            # Act 완료율 미니바
            mini_bar_x = list_x + len(header_text) + 1
            if mini_bar_x + 12 < w:
                mini_filled = int(8 * (act_done / max(1, act_total)))
                mini_bar = "█" * mini_filled + "░" * (8 - mini_filled)
                console.print(mini_bar_x, y, mini_bar, fg=ac)
                console.print(mini_bar_x + 9, y, f"{act_done}/{act_total}", fg=ac)
            continue

        ch_id = rid
        meta = CHAPTER_META[ch_id]
        completed = progress.is_chapter_completed(ch_id)
        unlocked = ch_id in selectable_set
        npc_id = meta.get("npc_guide", "selena")

        # 상태 아이콘
        if completed:
            ch_state = progress.chapter_states.get(ch_id)
            if ch_state and ch_state.skipped:
                icon, icon_color = "-", (100, 100, 100)
            else:
                icon, icon_color = "✓", (0, 220, 80)
        elif unlocked:
            # 다음 챕터면 특별한 아이콘
            if ch_id == progress.get_next_chapter():
                icon, icon_color = "▶", (255, 215, 0)
            else:
                icon, icon_color = "○", (200, 200, 100)
        else:
            icon, icon_color = "×", (50, 50, 60)

        # NPC 가이드 아이콘
        npc_icon, npc_color = NPC_ICONS.get(npc_id, ("?", (150, 150, 150)))

        text = f"{meta['title']}: {meta['subtitle']}"

        is_cursor = False
        if unlocked:
            sel_idx = selectable.index(ch_id) if ch_id in selectable else -1
            if sel_idx == cursor:
                is_cursor = True

        if is_cursor:
            # 커서 행: 밝은 하이라이트 + 깜빡이는 화살표
            pulse = math.sin(frame * 0.15)
            arrow_chars = [">", ">>", ">", ">>"]
            arrow = arrow_chars[frame // 8 % len(arrow_chars)]

            # 선택 행 배경 하이라이트
            act_color = ACT_INFO.get(meta.get("act", "act1"), {}).get("color", (100, 100, 200))
            bg_r, bg_g, bg_b = rgb("state.active")
            for bx in range(list_x - 1, min(list_x + 58, w)):
                if 0 <= bx < w and 0 <= y < h:
                    console.rgb["bg"][y, bx] = (bg_r, bg_g, bg_b)

            fg_color = (255, 255, 255)
            console.print(list_x, y, arrow, fg=(255, 215, 0))
            console.print(list_x + 2, y, icon, fg=icon_color)
            console.print(list_x + 4, y, npc_icon, fg=npc_color)
            console.print(list_x + 6, y, text, fg=fg_color)

            # 플레이 시간 표시
            if completed:
                ch_state = progress.chapter_states.get(ch_id)
                if ch_state and ch_state.play_time > 0:
                    mins = int(ch_state.play_time) // 60
                    secs = int(ch_state.play_time) % 60
                    console.print(list_x + 48, y, f"({mins}:{secs:02d})", fg=(150, 150, 180))
        elif unlocked:
            console.print(list_x + 1, y, " ", fg=Colors.UI_TEXT)
            console.print(list_x + 2, y, icon, fg=icon_color)
            console.print(list_x + 4, y, npc_icon, fg=(npc_color[0]//2, npc_color[1]//2, npc_color[2]//2))
            console.print(list_x + 6, y, text, fg=Colors.UI_TEXT)

            if completed:
                ch_state = progress.chapter_states.get(ch_id)
                if ch_state and ch_state.play_time > 0:
                    mins = int(ch_state.play_time) // 60
                    secs = int(ch_state.play_time) % 60
                    console.print(list_x + 48, y, f"({mins}:{secs:02d})", fg=(80, 80, 100))
        else:
            # 잠긴 챕터
            console.print(list_x + 2, y, icon, fg=icon_color)
            locked_text = f"{meta['title']}: ????????"
            console.print(list_x + 6, y, locked_text, fg=(40, 40, 50))

    # 4) 하단 정보 패널
    panel_y = h - 10
    panel_line = "─" * (min(60, w - 4))
    console.print((w - len(panel_line)) // 2, panel_y, panel_line, fg=(40, 40, 70))

    if selectable and 0 <= cursor < len(selectable):
        selected_ch = selectable[cursor]
        meta = CHAPTER_META[selected_ch]
        npc_id = meta.get("npc_guide", "selena")
        npc_icon, npc_color = NPC_ICONS.get(npc_id, ("?", (150, 150, 150)))
        npc_name = NPC_NAMES_KR.get(npc_id, npc_id)
        act_color = ACT_INFO.get(meta.get("act", "act1"), {}).get("color", (150, 150, 200))

        # 챕터 이름 (Act 색상)
        ch_title = f"{meta['title']}: {meta['subtitle']}"
        console.print(list_x + 2, panel_y + 1, ch_title, fg=act_color)

        # 학습 목표 (황금색)
        console.print(list_x + 2, panel_y + 3, "학습 목표", fg=(255, 215, 0))
        learning = meta.get("learning", "")
        # 긴 학습 목표 줄바꿈
        max_learn_w = min(54, w - list_x - 6)
        if len(learning) > max_learn_w:
            console.print(list_x + 4, panel_y + 4, learning[:max_learn_w], fg=(200, 200, 200))
            console.print(list_x + 4, panel_y + 5, learning[max_learn_w:max_learn_w*2], fg=(200, 200, 200))
        else:
            console.print(list_x + 4, panel_y + 4, learning, fg=(200, 200, 200))

        # NPC 가이드 (아이콘 + 이름 + 역할)
        npc_roles = {
            "selena": "시공의 안내자",
            "karnos": "고대의 전사",
            "mira": "시간의 마법사",
            "tord": "차원의 대장장이",
            "lina": "시공의 요리사",
        }
        role = npc_roles.get(npc_id, "")
        guide_text = f"{npc_icon} {npc_name} - {role}"
        console.print(list_x + 2, panel_y + 6, "가이드", fg=(150, 200, 255))
        console.print(list_x + 4, panel_y + 7, guide_text, fg=npc_color)

    # 5) 하단 조작 안내
    help_y = h - 2
    if pointer_tooltip:
        tip = pointer_tooltip[: min(60, w - 6)]
        console.print((w - len(tip)) // 2, help_y - 1, tip, fg=rgb("accent.amber"), bg=rgb("state.tooltip"))
    controls = "↑↓/Wheel: 선택  Left/Z: 시작  Right/X: 뒤로  Tab: 전체 스킵"
    console.print((w - len(controls)) // 2, help_y, controls, fg=(100, 100, 140))
