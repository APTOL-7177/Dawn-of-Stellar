"""
Cursor Menu System - 커서 기반 메뉴 시스템

방향키로 커서 이동, Z로 선택, X로 취소하는 범용 메뉴 시스템
"""

from typing import List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
import tcod.console

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction
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
    is_selected: bool = False  # 선택된 항목인지 표시 (색상 구분용)

    @property
    def data(self):
        """하위 호환성을 위한 data 속성 (value의 별칭)"""
        return self.value


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
        wrapped = False

        while True:
            prev_index = self.cursor_index
            self.cursor_index = (self.cursor_index - 1) % len(self.items)

            # 순환 감지 (맨 위에서 맨 아래로)
            if prev_index == 0 and self.cursor_index == len(self.items) - 1:
                wrapped = True

            if self.items[self.cursor_index].enabled:
                moved = True
                break

            # 한 바퀴 돌았으면 원래 위치로
            if self.cursor_index == original_index:
                break

        # 스크롤 조정
        if wrapped:
            # 순환: 맨 아래로 스크롤
            self.scroll_offset = max(0, len(self.items) - self.max_visible_items)
        elif self.cursor_index < self.scroll_offset:
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
        wrapped = False

        while True:
            prev_index = self.cursor_index
            self.cursor_index = (self.cursor_index + 1) % len(self.items)

            # 순환 감지 (맨 아래에서 맨 위로)
            if prev_index == len(self.items) - 1 and self.cursor_index == 0:
                wrapped = True

            if self.items[self.cursor_index].enabled:
                moved = True
                break

            # 한 바퀴 돌았으면 원래 위치로
            if self.cursor_index == original_index:
                break

        # 스크롤 조정
        if wrapped:
            # 순환: 맨 위로 스크롤
            self.scroll_offset = 0
        elif self.cursor_index >= self.scroll_offset + self.max_visible_items:
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

        # 메뉴 아이템 영역 시작 위치
        items_start_y = current_y
        visible_items = self.items[self.scroll_offset:self.scroll_offset + self.max_visible_items]
        items_height = min(len(visible_items), self.max_visible_items)

        # 배경 렌더링 (얇은 반투명 배경)
        # 메뉴 아이템 영역
        console.draw_rect(
            self.x,
            items_start_y,
            self.width,
            items_height,
            ord(" "),
            bg=(20, 20, 30)  # 어두운 파란색 배경
        )

        # 아이템 렌더링
        for i, item in enumerate(visible_items):
            actual_index = self.scroll_offset + i
            item_y = items_start_y + i

            # 선택된 아이템 하이라이트 배경
            if actual_index == self.cursor_index:
                console.draw_rect(
                    self.x,
                    item_y,
                    self.width,
                    1,
                    ord(" "),
                    bg=(40, 40, 60)  # 밝은 하이라이트
                )

            # 커서 표시
            cursor = ">" if actual_index == self.cursor_index else " "

            # 색상 결정
            if not item.enabled:
                color = Colors.DARK_GRAY
            elif actual_index == self.cursor_index:
                # 커서가 있는 항목은 선택 여부에 관계없이 강조 색상
                if item.is_selected:
                    color = (150, 255, 150)  # 더 밝은 초록색 (커서 + 선택됨)
                else:
                    color = Colors.UI_TEXT_SELECTED
            elif item.is_selected:
                # 선택된 항목 (초록색 계열, 커서가 없을 때)
                color = (100, 255, 100)  # 밝은 초록색
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

        # 스크롤 표시
        if len(self.items) > self.max_visible_items:
            # 위쪽 화살표
            if self.scroll_offset > 0:
                console.print(
                    self.x + self.width - 2,
                    items_start_y,
                    "▲",
                    fg=Colors.YELLOW
                )

            # 아래쪽 화살표
            if self.scroll_offset + self.max_visible_items < len(self.items):
                console.print(
                    self.x + self.width - 2,
                    items_start_y + items_height - 1,
                    "▼",
                    fg=Colors.YELLOW
                )

        # 설명 렌더링
        if self.show_description:
            selected = self.get_selected_item()
            if selected and selected.description:
                desc_y = items_start_y + items_height + 1

                # 설명 배경
                console.draw_rect(
                    self.x,
                    desc_y,
                    self.width,
                    2,  # 2줄
                    ord(" "),
                    bg=(15, 15, 25)  # 더 어두운 배경
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

    def handle_input(self, action: GameAction, event: Optional[tcod.event.KeyDown] = None) -> None:
        """입력 처리"""
        if action == GameAction.CONFIRM:
            self.handle_confirm()
        elif action == GameAction.CANCEL:
            self.handle_cancel()
        elif event and isinstance(event, tcod.event.KeyDown):
            # 문자 입력
            if event.sym == tcod.event.KeySym.BACKSPACE:
                self.handle_backspace()
            elif 32 <= event.sym <= 126:  # ASCII 문자 범위 (공백~~)
                char = chr(event.sym)
                self.handle_char_input(char)
    
    def get_result(self) -> Optional[str]:
        """입력 결과 반환 (확인된 경우만)"""
        if self.confirmed:
            # 빈 문자열도 허용 (랜덤 이름 선택을 위해)
            return self.text.strip() if self.text.strip() else ""
        return None
