"""
Cursor Menu System - 커서 기반 메뉴 시스템

방향키로 커서 이동, Z로 선택, X로 취소하는 범용 메뉴 시스템
"""

from typing import List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
import tcod.console

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.ui.pointer import PointerDispatcher, PointerEvent, PointerRegion, PointerDispatchResult
from src.ui.ui_renderer import SelectionHighlight
from src.core.logger import get_logger
from src.core.vibration_system import vibration_manager, VibrationPattern
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
        self.max_visible_items = 8  # 한 번에 보이는 최대 아이템 수

        self.logger = get_logger("cursor_menu")

        # UI 효과
        self._highlight = SelectionHighlight(
            base_bg=(40, 40, 60), pulse_bg=(60, 60, 100), speed=3.0
        )
        self._last_time = 0.0

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

        # 커서 이동 효과음 및 진동
        if moved:
            play_sfx("ui", "cursor_move")
            from src.core.vibration_system import vibration_manager
            vibration_manager.rumble_direct(0.2, 0.2, 100)

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

        # 커서 이동 효과음 및 진동
        if moved:
            play_sfx("ui", "cursor_move")
            from src.core.vibration_system import vibration_manager
            vibration_manager.rumble_direct(0.2, 0.2, 100)

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
            vibration_manager.vibrate(VibrationPattern.MEDIUM_TAP)  # 선택 진동
            return item.action()
        elif item and not item.enabled:
            play_sfx("ui", "cursor_error")  # 에러 효과음
            vibration_manager.vibrate(VibrationPattern.FAILURE)  # 실패 진동
        return None

    def handle_input(self, action: GameAction) -> Any:
        """
        입력 처리 후 결과 반환

        Args:
            action: 게임 액션

        Returns:
            CONFIRM 시 선택된 아이템의 value (없으면 None),
            그 외에는 None
        """
        if action == GameAction.MOVE_UP:
            self.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.move_cursor_down()
        elif action == GameAction.CONFIRM:
            item = self.get_selected_item()
            if item and item.enabled:
                play_sfx("ui", "cursor_select")
                vibration_manager.vibrate(VibrationPattern.MEDIUM_TAP)
                if item.action:
                    return item.action()
                return item.value
            elif item and not item.enabled:
                play_sfx("ui", "cursor_error")
                vibration_manager.vibrate(VibrationPattern.FAILURE)
        return None

    def pointer_regions(self) -> tuple[PointerRegion, ...]:
        regions = []
        for index, item in enumerate(self.items):
            if self.scroll_offset <= index < self.scroll_offset + self.max_visible_items:
                regions.append(
                    PointerRegion(
                        region_id=str(index),
                        x=self.x,
                        y=self._item_y(index),
                        width=self.width,
                        height=1,
                        command=GameAction.CONFIRM,
                        tooltip=item.description,
                        enabled=item.enabled,
                    )
                )
        return tuple(regions)

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        result = PointerDispatcher(self.pointer_regions()).dispatch(event)
        if result.hovered_region_id is not None:
            self._focus_pointer_region(result.hovered_region_id)
        if result.action is None:
            return result
        value = self.handle_input(result.action)
        return result.with_value(value)

    def _focus_pointer_region(self, region_id: str) -> None:
        index = int(region_id)
        if 0 <= index < len(self.items):
            self.cursor_index = index
            self._sync_scroll_to_cursor()

    def _sync_scroll_to_cursor(self) -> None:
        if self.cursor_index < self.scroll_offset:
            self.scroll_offset = self.cursor_index
        elif self.cursor_index >= self.scroll_offset + self.max_visible_items:
            self.scroll_offset = self.cursor_index - self.max_visible_items + 1

    def _item_y(self, index: int) -> int:
        items_start_y = self.y + (2 if self.title else 0)
        return items_start_y + index - self.scroll_offset

    def render(self, console: tcod.console.Console) -> None:
        """
        메뉴 렌더링

        Args:
            console: 렌더링할 콘솔
        """
        import time as _time

        # dt 계산
        now = _time.monotonic()
        dt = now - self._last_time if self._last_time else 0.016
        self._last_time = now
        self._highlight.update(dt)

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

            # 선택된 아이템 하이라이트 배경 (펄스 효과)
            if actual_index == self.cursor_index:
                highlight_bg = self._highlight.get_bg_color()
                console.draw_rect(
                    self.x,
                    item_y,
                    self.width,
                    1,
                    ord(" "),
                    bg=highlight_bg
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
                    4,  # 4줄
                    ord(" "),
                    bg=(15, 15, 25)  # 더 어두운 배경
                )

                # 설명 텍스트 (여러 줄 지원)
                desc_lines = self._wrap_text(selected.description, self.width - 4)
                for i, line in enumerate(desc_lines[:4]):  # 최대 4줄
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


def show_teleporter_choice_menu(console: tcod.console.Console, context: tcod.context.Context) -> Optional[bool]:
    """
    텔레포터 선택 메뉴 표시

    Returns:
        True: 텔레포트 실행
        False: 취소
        None: 메뉴 취소됨
    """
    # 메뉴 아이템 생성
    menu_items = [
        MenuItem(
            text="텔레포트 하기",
            description="텔레포터를 사용하여 이동합니다",
            value=True
        ),
        MenuItem(
            text="취소하기",
            description="텔레포트를 취소합니다",
            value=False
        )
    ]

    # 메뉴 생성
    menu = CursorMenu(
        title="🌀 텔레포터",
        items=menu_items,
        x=console.width // 2 - 20,
        y=console.height // 2 - 5,
        width=40
    )

    import time
    import pygame

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    # 메뉴 루프
    while True:
        # 화면 렌더링
        console.clear()
        menu.render(console)
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            pygame.event.pump()
        except:
            pass

        # 입력 처리 함수
        def process_menu_action(action):
            if action == GameAction.CONFIRM:
                selected = menu.get_selected_item()
                if selected and selected.value is not None:
                    return ("selected", selected.value)
            elif action == GameAction.CANCEL:
                return ("cancel", None)
            elif action == GameAction.MOVE_UP:
                menu.move_cursor_up()
            elif action == GameAction.MOVE_DOWN:
                menu.move_cursor_down()
            return None

        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            if action:
                keyboard_processed = True
                result = process_menu_action(action)
                if result:
                    return result[1]

            if isinstance(event, tcod.event.Quit):
                raise SystemExit()

        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                result = process_menu_action(gamepad_action)
                if result:
                    return result[1]

        # CPU 사용률 낮추기
        time.sleep(0.01)


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
        # 테두리 (더블라인 박스)
        from src.ui.ui_renderer import draw_styled_box
        draw_styled_box(
            console,
            self.x,
            self.y,
            self.width,
            6,
            title=self.title,
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

        # 입력된 텍스트 (커서 표시 없이 - 활성화된 박스는 호출자가 별도로 처리)
        console.print(
            self.x + 3,
            self.y + 3,
            self.text[:input_bg_width - 2],
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

    def handle_input(self, action: GameAction, event=None, text_event=None) -> None:
        """입력 처리

        Args:
            action: GameAction
            event: tcod.event.KeyDown (키보드 키 입력)
            text_event: tcod.event.TextInput (IME 조합 완료 문자 - 한글 등)
        """
        if action == GameAction.CONFIRM:
            self.handle_confirm()
        elif action == GameAction.CANCEL:
            self.handle_cancel()
        # IME 텍스트 입력 (한글 등 조합 문자)
        elif text_event and isinstance(text_event, tcod.event.TextInput):
            for ch in text_event.text:
                if ch.isprintable():
                    self.handle_char_input(ch)
        # MOVE_UP, MOVE_DOWN은 텍스트 입력에서 무시 (커서 이동 없음)
        elif event and isinstance(event, tcod.event.KeyDown):
            # 특수 키만 처리 - 문자 입력은 TextInput 이벤트로 처리 (이중 입력 방지)
            if event.sym == tcod.event.KeySym.BACKSPACE:
                self.handle_backspace()
    
    def get_result(self) -> Optional[str]:
        """입력 결과 반환 (확인된 경우만)"""
        if self.confirmed:
            # 빈 문자열도 허용 (랜덤 이름 선택을 위해)
            return self.text.strip() if self.text.strip() else ""
        return None
