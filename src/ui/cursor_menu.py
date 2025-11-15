"""
Cursor Menu System - 커서 기반 메뉴 시스템

방향키로 커서 이동, Z로 선택, X로 취소하는 범용 메뉴 시스템
"""

from typing import List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
import tcod.console

from src.ui.tcod_display import Colors
from src.core.logger import get_logger
from src.audio import play_sfx


@dataclass
class MenuItem:
    """메뉴 아이템"""
    text: str
    action: Optional[Callable[[], Any]] = None
    enabled: bool = True
    description: str = ""
    value: Any = None  # 추가 데이터 저장용


class CursorMenu:
    """
    커서 메뉴 시스템

    방향키(↑↓)로 커서 이동, Z로 선택, X로 취소
    """

    def __init__(
        self,
        title: str,
        items: List[MenuItem],
        x: int = 0,
        y: int = 0,
        width: int = 40,
        show_description: bool = True
    ):
        """
        Args:
            title: 메뉴 제목
            items: 메뉴 아이템 리스트
            x, y: 메뉴 위치
            width: 메뉴 너비
            show_description: 설명 표시 여부
        """
        self.title = title
        self.items = items
        self.x = x
        self.y = y
        self.width = width
        self.show_description = show_description

        self.cursor_index = 0
        self.scroll_offset = 0
        self.max_visible_items = 10  # 한 번에 보이는 최대 아이템 수

        self.logger = get_logger("cursor_menu")

        # 첫 번째 활성화된 아이템으로 커서 이동
        self._move_to_first_enabled()

    def _move_to_first_enabled(self) -> None:
        """첫 번째 활성화된 아이템으로 커서 이동"""
        for i, item in enumerate(self.items):
            if item.enabled:
                self.cursor_index = i
                return

    def move_cursor_up(self) -> None:
        """커서 위로 이동"""
        if not self.items:
            return

        # 이전 활성화된 아이템 찾기
        original_index = self.cursor_index
        moved = False
        while True:
            self.cursor_index = (self.cursor_index - 1) % len(self.items)

            if self.items[self.cursor_index].enabled:
                moved = True
                break

            # 한 바퀴 돌았으면 원래 위치로
            if self.cursor_index == original_index:
                break

        # 스크롤 조정
        if self.cursor_index < self.scroll_offset:
            self.scroll_offset = self.cursor_index

        # 커서 이동 효과음
        if moved:
            play_sfx("ui", "cursor_move")

    def move_cursor_down(self) -> None:
        """커서 아래로 이동"""
        if not self.items:
            return

        # 다음 활성화된 아이템 찾기
        original_index = self.cursor_index
        moved = False
        while True:
            self.cursor_index = (self.cursor_index + 1) % len(self.items)

            if self.items[self.cursor_index].enabled:
                moved = True
                break

            # 한 바퀴 돌았으면 원래 위치로
            if self.cursor_index == original_index:
                break

        # 스크롤 조정
        if self.cursor_index >= self.scroll_offset + self.max_visible_items:
            self.scroll_offset = self.cursor_index - self.max_visible_items + 1

        # 커서 이동 효과음
        if moved:
            play_sfx("ui", "cursor_move")

    def get_selected_item(self) -> Optional[MenuItem]:
        """현재 선택된 아이템 반환"""
        if 0 <= self.cursor_index < len(self.items):
            return self.items[self.cursor_index]
        return None

    def execute_selected(self) -> Any:
        """선택된 아이템의 액션 실행"""
        item = self.get_selected_item()
        if item and item.enabled and item.action:
            self.logger.debug(f"메뉴 아이템 실행: {item.text}")
            play_sfx("ui", "cursor_select")  # 선택 효과음
            return item.action()
        elif item and not item.enabled:
            play_sfx("ui", "cursor_error")  # 에러 효과음
        return None

    def render(self, console: tcod.console.Console) -> None:
        """
        메뉴 렌더링

        Args:
            console: 렌더링할 콘솔
        """
        current_y = self.y

        # 제목 렌더링
        if self.title:
            console.print(
                self.x + self.width // 2 - len(self.title) // 2,
                current_y,
                self.title,
                fg=Colors.UI_TEXT_SELECTED
            )
            current_y += 2

        # 테두리
        title_offset = 2 if self.title else 0
        description_height = 3 if self.show_description else 0
        frame_height = min(len(self.items), self.max_visible_items) + 2 + description_height

        console.draw_frame(
            self.x,
            self.y + title_offset,
            self.width,
            frame_height,
            "",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 아이템 렌더링
        visible_items = self.items[self.scroll_offset:self.scroll_offset + self.max_visible_items]

        for i, item in enumerate(visible_items):
            actual_index = self.scroll_offset + i
            item_y = current_y + i

            # 커서 표시
            cursor = ">" if actual_index == self.cursor_index else " "

            # 색상 결정
            if not item.enabled:
                color = Colors.DARK_GRAY
            elif actual_index == self.cursor_index:
                color = Colors.UI_TEXT_SELECTED
            else:
                color = Colors.UI_TEXT

            # 아이템 텍스트
            text = f"{cursor} {item.text}"
            console.print(
                self.x + 2,
                item_y,
                text[:self.width - 4],  # 너비 제한
                fg=color
            )

        # 설명 렌더링
        if self.show_description:
            selected = self.get_selected_item()
            if selected and selected.description:
                desc_y = current_y + min(len(self.items), self.max_visible_items) + 1

                # 설명 구분선
                console.print(
                    self.x + 1,
                    desc_y - 1,
                    "─" * (self.width - 2),
                    fg=Colors.UI_BORDER
                )

                # 설명 텍스트 (여러 줄 지원)
                desc_lines = self._wrap_text(selected.description, self.width - 4)
                for i, line in enumerate(desc_lines[:2]):  # 최대 2줄
                    console.print(
                        self.x + 2,
                        desc_y + i,
                        line,
                        fg=Colors.GRAY
                    )

        # 스크롤 표시
        if len(self.items) > self.max_visible_items:
            # 위쪽 화살표
            if self.scroll_offset > 0:
                console.print(
                    self.x + self.width - 2,
                    self.y + title_offset + 1,
                    "▲",
                    fg=Colors.UI_TEXT
                )

            # 아래쪽 화살표
            if self.scroll_offset + self.max_visible_items < len(self.items):
                console.print(
                    self.x + self.width - 2,
                    current_y + self.max_visible_items - 1,
                    "▼",
                    fg=Colors.UI_TEXT
                )

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """텍스트를 최대 너비로 줄바꿈"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)
            if current_length + word_length + len(current_line) <= max_width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length

        if current_line:
            lines.append(" ".join(current_line))

        return lines


class TextInputBox:
    """
    텍스트 입력 박스

    이름 입력 등에 사용
    """

    def __init__(
        self,
        title: str,
        prompt: str,
        max_length: int = 20,
        x: int = 20,
        y: int = 15,
        width: int = 40,
        default_text: str = ""
    ):
        """
        Args:
            title: 제목
            prompt: 입력 안내 메시지
            max_length: 최대 입력 길이
            x, y: 위치
            width: 너비
            default_text: 기본 텍스트
        """
        self.title = title
        self.prompt = prompt
        self.max_length = max_length
        self.x = x
        self.y = y
        self.width = width

        self.text = default_text[:max_length] if default_text else ""
        self.confirmed = False
        self.cancelled = False

    def handle_char_input(self, char: str) -> None:
        """문자 입력 처리"""
        if len(self.text) < self.max_length:
            # 한글, 영문, 숫자, 공백만 허용
            if char.isprintable():
                self.text += char
                play_sfx("ui", "cursor_move")  # 입력 효과음
        else:
            play_sfx("ui", "cursor_error")  # 최대 길이 도달

    def handle_backspace(self) -> None:
        """백스페이스 처리"""
        if self.text:
            self.text = self.text[:-1]
            play_sfx("ui", "cursor_cancel")  # 삭제 효과음

    def handle_confirm(self) -> None:
        """확인 처리"""
        # 빈 입력도 허용 (랜덤 이름 선택용)
        self.confirmed = True
        play_sfx("ui", "cursor_select")  # 확인 효과음

    def handle_cancel(self) -> None:
        """취소 처리"""
        self.cancelled = True
        play_sfx("ui", "cursor_cancel")  # 취소 효과음

    def render(self, console: tcod.console.Console) -> None:
        """텍스트 입력 박스 렌더링"""
        # 테두리
        console.draw_frame(
            self.x,
            self.y,
            self.width,
            6,
            self.title,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 안내 메시지
        console.print(
            self.x + 2,
            self.y + 1,
            self.prompt,
            fg=Colors.UI_TEXT
        )

        # 입력 필드
        input_bg_width = self.width - 4
        console.draw_rect(
            self.x + 2,
            self.y + 3,
            input_bg_width,
            1,
            ord(" "),
            bg=Colors.DARK_GRAY
        )

        # 입력된 텍스트
        display_text = self.text + "_"  # 커서 표시
        console.print(
            self.x + 3,
            self.y + 3,
            display_text[:input_bg_width - 2],
            fg=Colors.WHITE
        )

        # 도움말
        help_text = "Enter: 확인  ESC: 취소  Backspace: 삭제"
        console.print(
            self.x + 2,
            self.y + 4,
            help_text[:self.width - 4],
            fg=Colors.GRAY
        )

    def get_result(self) -> Optional[str]:
        """입력 결과 반환 (확인된 경우만)"""
        if self.confirmed:
            # 빈 문자열도 허용 (랜덤 이름 선택을 위해)
            return self.text.strip() if self.text.strip() else ""
        return None
