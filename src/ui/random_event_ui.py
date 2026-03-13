"""
랜덤 이벤트 UI

던전/월드 탐험 중 랜덤 이벤트 발생 시 표시하는 tcod 기반 UI.
이벤트 설명과 선택지를 표시하고, 플레이어의 선택을 받는다.
"""
import tcod.console
import tcod.event
from typing import Optional, List, Any

from src.core.logger import get_logger
from src.ui.input_handler import unified_input_handler, GameAction

logger = get_logger("random_event_ui")

# 카테고리별 색상
CATEGORY_COLORS = {
    "npc_rescue": (100, 200, 255),
    "hidden_treasure": (255, 215, 0),
    "trap": (255, 100, 100),
    "merchant": (100, 255, 150),
    "story": (200, 180, 255),
    "mystery": (180, 100, 255),
    "blessing": (255, 255, 150),
    "curse": (200, 50, 50),
    "challenge": (255, 150, 50),
}

CATEGORY_NAMES = {
    "npc_rescue": "조우",
    "hidden_treasure": "보물",
    "trap": "함정",
    "merchant": "상인",
    "story": "이야기",
    "mystery": "미스터리",
    "blessing": "축복",
    "curse": "저주",
    "challenge": "도전",
}


def _wrap_text(text: str, max_width: int) -> List[str]:
    """텍스트 줄바꿈"""
    if len(text) <= max_width:
        return [text]
    result = []
    words = text.split(" ")
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        if len(test) > max_width:
            if current:
                result.append(current)
            current = word
        else:
            current = test
    if current:
        result.append(current)
    return result if result else [""]


class RandomEventUI:
    """랜덤 이벤트 선택 UI"""

    def __init__(self):
        self.is_active = False
        self._event = None
        self._party_jobs: List[str] = []
        self._inventory = None
        self._selected_idx = 0
        self._choice_count = 0
        self._result_idx = -1  # 최종 선택 (-1 = 선택 안 함)

    def open(self, event: Any, party_jobs: List[str], inventory: Any = None):
        """이벤트 UI 열기"""
        self._event = event
        self._party_jobs = party_jobs
        self._inventory = inventory
        self._selected_idx = 0
        self._choice_count = len(event.choices) if hasattr(event, 'choices') else 0
        self._result_idx = -1
        self.is_active = True

    def render(self, console: tcod.console.Console):
        """tcod 콘솔에 렌더링"""
        if not self.is_active or not self._event:
            return

        event = self._event
        con_w = console.width
        con_h = console.height

        # 창 크기 계산
        win_w = min(56, con_w - 4)
        # 높이: 제목(2) + 설명(~3) + 구분(1) + 선택지(count*2) + 안내(2) + 여유(2)
        win_h = min(8 + self._choice_count * 2 + 4, con_h - 4)
        win_x = (con_w - win_w) // 2
        win_y = (con_h - win_h) // 2

        # 배경 어둡게
        for y in range(con_h):
            for x in range(con_w):
                console.rgb["fg"][y][x] = (
                    console.rgb["fg"][y][x][0] // 3,
                    console.rgb["fg"][y][x][1] // 3,
                    console.rgb["fg"][y][x][2] // 3,
                )

        # 카테고리 색상
        cat = getattr(event, 'category', '')
        title_color = CATEGORY_COLORS.get(cat, (200, 200, 200))
        cat_name = CATEGORY_NAMES.get(cat, "이벤트")

        # 프레임
        console.draw_frame(
            win_x, win_y, win_w, win_h,
            title=f" {cat_name} ",
            fg=title_color,
            bg=(20, 15, 30),
        )

        row = win_y + 1
        inner_w = win_w - 4

        # 이벤트 이름
        console.print(win_x + 2, row, event.name, fg=(255, 255, 255))
        row += 2

        # 설명
        desc_lines = _wrap_text(event.description, inner_w)
        for line in desc_lines:
            if row >= win_y + win_h - 2:
                break
            console.print(win_x + 2, row, line, fg=(180, 180, 180))
            row += 1
        row += 1

        # 구분선
        if row < win_y + win_h - self._choice_count * 2 - 3:
            console.print(win_x + 2, row, "-" * inner_w, fg=(80, 80, 80))
            row += 1

        # 선택지 표시
        for i, choice in enumerate(event.choices):
            if row >= win_y + win_h - 2:
                break

            # 요구사항 체크
            can_choose = True
            req_text = ""
            reqs = choice.requirements if hasattr(choice, 'requirements') else {}
            if reqs and isinstance(reqs, dict):
                if "has_job" in reqs:
                    required_job = reqs["has_job"]
                    if required_job not in self._party_jobs:
                        can_choose = False
                        req_text = f" (필요: {required_job})"
                if "min_gold" in reqs and self._inventory is not None:
                    min_gold = reqs["min_gold"]
                    current_gold = getattr(self._inventory, 'gold', 0)
                    if current_gold < min_gold:
                        can_choose = False
                        req_text += f" (골드 부족: {current_gold}/{min_gold}G)"
                    else:
                        req_text += f" ({min_gold}G)"
                if "has_item" in reqs:
                    required_item = reqs["has_item"]
                    has_it = False
                    if self._inventory and hasattr(self._inventory, 'items'):
                        for slot in self._inventory.items:
                            if slot and hasattr(slot, 'item_id') and slot.item_id == required_item:
                                has_it = True
                                break
                    if not has_it:
                        can_choose = False
                        req_text += f" (필요: {required_item})"

            # 커서 표시
            if i == self._selected_idx:
                marker = ">"
                if can_choose:
                    fg = (255, 255, 100)
                else:
                    fg = (180, 80, 80)
            else:
                marker = " "
                if can_choose:
                    fg = (200, 200, 200)
                else:
                    fg = (100, 60, 60)

            text = choice.text if hasattr(choice, 'text') else str(choice)
            display = f"{marker} {i+1}. {text}{req_text}"
            if len(display) > inner_w:
                display = display[:inner_w - 1] + "."

            console.print(win_x + 2, row, display, fg=fg)
            row += 1

        # 안내
        row = win_y + win_h - 2
        console.print(
            win_x + 2, row,
            "[Up/Down] 선택  [Enter] 결정  [Esc] 무시",
            fg=(120, 120, 120),
        )

    def handle_input(self, event: tcod.event.KeyDown):
        """입력 처리"""
        if not self.is_active:
            return

        # tcod 키 직접 처리 (가장 확실한 방법)
        if event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.KP_8):
            self._selected_idx = (self._selected_idx - 1) % max(self._choice_count, 1)
        elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.KP_2):
            self._selected_idx = (self._selected_idx + 1) % max(self._choice_count, 1)
        elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            self._confirm_selection()
        elif event.sym == tcod.event.KeySym.ESCAPE:
            self._result_idx = -1
            self.is_active = False
        elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.RIGHT,
                           tcod.event.KeySym.KP_4, tcod.event.KeySym.KP_6):
            pass  # 좌우 입력은 무시 (창 닫힘 방지)
        else:
            # 문자 키 처리 (Z=확인, X=취소, K=위, J=아래)
            char = ""
            if hasattr(event, 'sym') and event.sym.value < 128:
                try:
                    char = chr(event.sym.value).lower()
                except (ValueError, OverflowError):
                    pass

            if char == 'k':
                self._selected_idx = (self._selected_idx - 1) % max(self._choice_count, 1)
            elif char == 'j':
                self._selected_idx = (self._selected_idx + 1) % max(self._choice_count, 1)
            elif char == 'z':
                self._confirm_selection()
            elif char == 'x':
                self._result_idx = -1
                self.is_active = False

    def _confirm_selection(self):
        """현재 선택 확정"""
        if self._choice_count == 0:
            self._result_idx = -1
            self.is_active = False
            return

        # 요구사항 체크
        choice = self._event.choices[self._selected_idx]
        reqs = choice.requirements if hasattr(choice, 'requirements') else {}
        if reqs and isinstance(reqs, dict):
            if "has_job" in reqs:
                if reqs["has_job"] not in self._party_jobs:
                    return  # 선택 불가
            if "min_gold" in reqs and self._inventory is not None:
                if getattr(self._inventory, 'gold', 0) < reqs["min_gold"]:
                    return  # 골드 부족
            if "has_item" in reqs and self._inventory is not None:
                required_item = reqs["has_item"]
                has_it = False
                if hasattr(self._inventory, 'items'):
                    for slot in self._inventory.items:
                        if slot and hasattr(slot, 'item_id') and slot.item_id == required_item:
                            has_it = True
                            break
                if not has_it:
                    return  # 아이템 없음

        self._result_idx = self._selected_idx
        self.is_active = False

    def get_selected_choice(self) -> int:
        """선택된 선택지 인덱스 반환 (-1이면 선택 안 함)"""
        return self._result_idx
