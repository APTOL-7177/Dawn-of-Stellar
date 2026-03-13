"""
파티 시너지 UI

활성 파티 보너스와 합체기 목록을 표시합니다.
"""

import tcod
from typing import List, Optional, Any

from src.combat.job_synergy import get_synergy_manager, ComboSkill, PartyBonus


# 색상 상수
COLOR_TITLE    = (255, 215,   0)  # 금색   - 제목 / 합체기 이름
COLOR_BONUS    = (100, 255, 100)  # 녹색   - 파티 보너스 이름
COLOR_DESC     = (200, 200, 200)  # 밝은 회색 - 설명
COLOR_SECTION  = (180, 180,  80)  # 황색   - 섹션 헤더
COLOR_DISABLED = (120, 120, 120)  # 어두운 회색 - 사용 불가
COLOR_HIGHLIGHT= (255, 255, 150)  # 연노랑 - 커서 강조
COLOR_KEY_HINT = (150, 150, 150)  # 키 힌트
COLOR_BORDER   = ( 80,  80, 120)  # 테두리
COLOR_EFFECT   = (160, 220, 160)  # 효과 수치
COLOR_INFO     = (180, 180, 120)  # 부가 정보


class SynergyUI:
    """파티 시너지 보너스 및 합체기 목록 UI"""

    PANEL_W = 62
    PANEL_H = 38

    def __init__(
        self,
        party_members: list,
        synergy_manager=None,
        affinity_manager=None,
    ):
        self.party_members = party_members
        self.synergy_manager = synergy_manager or get_synergy_manager()
        self.affinity_manager = affinity_manager
        self.scroll_offset = 0
        self.cursor_index = 0
        self.is_active = False

        # 파티 직업 목록
        self._party_jobs: List[str] = []
        for m in party_members:
            job = getattr(m, "job_id", None) or getattr(m, "job", None) or ""
            if isinstance(job, str) and job:
                self._party_jobs.append(job)

        # 렌더링 항목 목록 – 각 원소는 (type_str, object_or_None)
        # 유효 타입: "section" | "bonus" | "combo" | "empty"
        self._items: List[tuple] = []
        self._build_items()

    # ──────────────────────────────────────────────────────────────
    # 항목 구성
    # ──────────────────────────────────────────────────────────────

    def _build_items(self):
        self._items = []

        # 섹션 1: 활성 파티 보너스
        self._items.append(("section", "[ 활성 보너스 ]"))
        active_bonuses: List[PartyBonus] = self.synergy_manager.get_active_bonuses()
        if active_bonuses:
            for bonus in active_bonuses:
                self._items.append(("bonus", bonus))
        else:
            self._items.append(("empty", "활성 보너스 없음"))

        # 빈 줄 구분
        self._items.append(("sep", None))

        # 섹션 2: 합체기 목록
        self._items.append(("section", "[ 합체기 목록 ]"))
        all_combos: List[ComboSkill] = self.synergy_manager.get_all_combos()
        if all_combos:
            for combo in all_combos:
                self._items.append(("combo", combo))
        else:
            self._items.append(("empty", "합체기 없음"))

    def _navigable_indices(self) -> List[int]:
        """커서 이동 가능한 항목 인덱스"""
        return [
            i for i, (t, _) in enumerate(self._items)
            if t in ("bonus", "combo")
        ]

    def _is_combo_available(self, combo: ComboSkill) -> bool:
        for req_job in combo.required_jobs:
            if req_job not in self._party_jobs:
                return False
        return True

    # ──────────────────────────────────────────────────────────────
    # 공개 인터페이스
    # ──────────────────────────────────────────────────────────────

    def open(self):
        self.is_active = True
        self.scroll_offset = 0
        self.cursor_index = 0
        self._build_items()

        # 커서를 첫 번째 탐색 가능 항목으로 초기화
        nav = self._navigable_indices()
        if nav:
            self.cursor_index = nav[0]

    def close(self):
        self.is_active = False

    def handle_input(self, key) -> bool:
        """
        입력 처리.
        반환값: True = UI 계속 유지, False = UI 닫기.
        """
        if not self.is_active:
            return False

        sym = getattr(key, "sym", None)

        if sym == tcod.event.KeySym.ESCAPE:
            self.close()
            return False

        if sym in (tcod.event.KeySym.UP, tcod.event.KeySym.k):
            self._move_up()
            return True

        if sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.j):
            self._move_down()
            return True

        return True

    # ──────────────────────────────────────────────────────────────
    # 커서 / 스크롤
    # ──────────────────────────────────────────────────────────────

    def _move_up(self):
        nav = self._navigable_indices()
        if not nav:
            return
        try:
            pos = nav.index(self.cursor_index)
        except ValueError:
            pos = 0
        if pos > 0:
            self.cursor_index = nav[pos - 1]
            self._clamp_scroll()

    def _move_down(self):
        nav = self._navigable_indices()
        if not nav:
            return
        try:
            pos = nav.index(self.cursor_index)
        except ValueError:
            pos = -1
        if pos < len(nav) - 1:
            self.cursor_index = nav[pos + 1]
            self._clamp_scroll()

    def _clamp_scroll(self):
        max_visible = self._visible_rows()
        if self.cursor_index < self.scroll_offset:
            self.scroll_offset = self.cursor_index
        elif self.cursor_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.cursor_index - max_visible + 1

    def _visible_rows(self) -> int:
        """스크롤 영역의 최대 행 수 (패널 내부 여백 포함)"""
        return self.PANEL_H - 5  # 테두리 2 + 제목 1 + 힌트 1 + 여백 1

    # ──────────────────────────────────────────────────────────────
    # 렌더링
    # ──────────────────────────────────────────────────────────────

    def render(self, console: tcod.console.Console):
        if not self.is_active:
            return

        cw = console.width
        ch = console.height
        pw = min(self.PANEL_W, cw - 4)
        ph = min(self.PANEL_H, ch - 4)
        x0 = (cw - pw) // 2
        y0 = (ch - ph) // 2

        # 배경
        for dy in range(ph):
            for dx in range(pw):
                console.print(x0 + dx, y0 + dy, " ", bg=(20, 20, 40))

        # 테두리
        console.draw_frame(x0, y0, pw, ph, fg=COLOR_BORDER, bg=(20, 20, 40))

        # 제목
        title = "파티 시너지"
        console.print(
            x0 + (pw - len(title) - 2) // 2,
            y0,
            f" {title} ",
            fg=COLOR_TITLE,
            bg=(20, 20, 40),
        )

        # 키 힌트
        hint = "↑↓: 이동   ESC: 닫기"
        console.print(
            x0 + (pw - len(hint)) // 2,
            y0 + ph - 1,
            hint,
            fg=COLOR_KEY_HINT,
            bg=(20, 20, 40),
        )

        # 콘텐츠 영역
        cx = x0 + 2
        cy_start = y0 + 2
        max_w = pw - 4
        max_rows = self._visible_rows()

        row = 0          # 현재 화면 행 (0-based, cy_start 기준)
        for idx, (item_type, obj) in enumerate(self._items):
            if row >= max_rows:
                break
            if idx < self.scroll_offset:
                continue

            is_cursor = (idx == self.cursor_index)
            y = cy_start + row

            if item_type == "section":
                console.print(cx, y, str(obj)[:max_w], fg=COLOR_SECTION)
                row += 1

            elif item_type == "sep":
                row += 1  # 빈 줄

            elif item_type == "empty":
                console.print(cx + 2, y, str(obj)[:max_w], fg=COLOR_DISABLED)
                row += 1

            elif item_type == "bonus":
                row += self._render_bonus(console, cx, y, obj, is_cursor, max_w, max_rows - row)

            elif item_type == "combo":
                row += self._render_combo(console, cx, y, obj, is_cursor, max_w, max_rows - row)

        # 스크롤 인디케이터
        total = len(self._items)
        if total > max_rows:
            bar_h = max_rows
            scroll_ratio = self.scroll_offset / max(1, total - max_rows)
            thumb_y = int(scroll_ratio * (bar_h - 1))
            for sy in range(bar_h):
                char = "█" if sy == thumb_y else "│"
                color = COLOR_TITLE if sy == thumb_y else COLOR_BORDER
                console.print(x0 + pw - 1, cy_start + sy, char, fg=color, bg=(20, 20, 40))

    # ──────────────────────────────────────────────────────────────
    # 항목 렌더 헬퍼 – 소비한 행 수 반환
    # ──────────────────────────────────────────────────────────────

    def _render_bonus(
        self,
        console: tcod.console.Console,
        x: int, y: int,
        bonus: PartyBonus,
        is_cursor: bool,
        max_w: int,
        remaining_rows: int,
    ) -> int:
        """파티 보너스 렌더링. 사용한 행 수 반환."""
        used = 0
        prefix = "> " if is_cursor else "  "
        name_color = COLOR_HIGHLIGHT if is_cursor else COLOR_BONUS

        # 행 1: 이름
        name_line = (prefix + bonus.name)[:max_w]
        console.print(x, y + used, name_line, fg=name_color)
        used += 1

        if remaining_rows <= used:
            return used

        # 행 2: 효과 요약
        if bonus.effects:
            parts = []
            for k, v in list(bonus.effects.items())[:4]:
                if isinstance(v, float):
                    parts.append(f"{k}: {v:+.0%}")
                else:
                    parts.append(f"{k}: {v}")
            effect_line = ("    " + ", ".join(parts))[:max_w]
            console.print(x, y + used, effect_line, fg=COLOR_EFFECT)
            used += 1

            if remaining_rows <= used:
                return used

        # 행 3: 설명 (커서 위치일 때)
        if is_cursor and bonus.description:
            desc_line = ("    " + bonus.description)[:max_w]
            console.print(x, y + used, desc_line, fg=COLOR_DESC)
            used += 1

        return used

    def _render_combo(
        self,
        console: tcod.console.Console,
        x: int, y: int,
        combo: ComboSkill,
        is_cursor: bool,
        max_w: int,
        remaining_rows: int,
    ) -> int:
        """합체기 렌더링. 사용한 행 수 반환."""
        available = self._is_combo_available(combo)
        used = 0
        prefix = "> " if is_cursor else "  "

        if available:
            name_color = COLOR_HIGHLIGHT if is_cursor else COLOR_TITLE
        else:
            name_color = COLOR_DISABLED

        # 행 1: 이름 + 게이지 코스트
        gauge_tag = f"[게이지 {combo.gauge_cost}]"
        name_part = prefix + combo.name
        name_line = f"{name_part}  {gauge_tag}"[:max_w]
        console.print(x, y + used, name_line, fg=name_color)
        used += 1

        if remaining_rows <= used:
            return used

        # 행 2: 필요 직업 + 최소 호감도
        req_str = ", ".join(combo.required_jobs)
        info_line = f"    필요 직업: {req_str}  / 호감도 Lv{combo.min_affinity}+"
        info_color = COLOR_INFO if available else COLOR_DISABLED
        console.print(x, y + used, info_line[:max_w], fg=info_color)
        used += 1

        if remaining_rows <= used:
            return used

        # 행 3: 설명 (커서 위치일 때)
        if is_cursor and combo.description:
            desc_line = ("    " + combo.description)[:max_w]
            desc_color = COLOR_DESC if available else COLOR_DISABLED
            console.print(x, y + used, desc_line, fg=desc_color)
            used += 1

        return used
