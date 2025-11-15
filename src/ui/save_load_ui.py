"""
저장/로드 UI

게임 상태 저장 및 불러오기
"""

import tcod.console
import tcod.event
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from src.persistence.save_system import SaveSystem
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.ui.cursor_menu import CursorMenu, MenuItem, TextInputBox
from src.core.logger import get_logger


logger = get_logger("save_load_ui")


class SaveLoadMode(Enum):
    """저장/로드 모드"""
    SAVE = "save"
    LOAD = "load"


class SaveLoadUI:
    """저장/로드 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        mode: SaveLoadMode,
        save_system: SaveSystem
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            mode: 저장/로드 모드
            save_system: 저장 시스템
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.mode = mode
        self.save_system = save_system

        # 저장 파일 목록
        self.save_files = self.save_system.list_saves()
        self.cursor = 0

        # 상태
        self.closed = False
        self.selected_save: Optional[str] = None

        # 새 저장 (저장 모드)
        self.creating_new_save = False
        self.name_input: Optional[TextInputBox] = None

        # 확인 메시지
        self.confirm_message: Optional[str] = None
        self.confirm_yes = False

        logger.info(f"저장/로드 UI 열기: {mode.value}, {len(self.save_files)}개 파일")

    def handle_input(self, action: GameAction, event: tcod.event.KeyDown = None) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션
            event: 키보드 이벤트

        Returns:
            닫기 여부
        """
        # 이름 입력 중
        if self.creating_new_save and self.name_input:
            return self._handle_name_input(action, event)

        # 확인 메시지
        if self.confirm_message:
            return self._handle_confirm(action)

        # 목록 탐색
        if action == GameAction.MOVE_UP:
            if self.mode == SaveLoadMode.SAVE:
                # 저장 모드: "새 저장" 포함
                self.cursor = max(-1, self.cursor - 1)
            else:
                # 로드 모드: 목록만
                self.cursor = max(0, self.cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            max_cursor = len(self.save_files) - 1
            self.cursor = min(max_cursor, self.cursor + 1)
        elif action == GameAction.CONFIRM:
            if self.mode == SaveLoadMode.SAVE:
                # 저장
                if self.cursor == -1:
                    # 새 저장
                    self._start_new_save()
                elif 0 <= self.cursor < len(self.save_files):
                    # 덮어쓰기 확인 (범위 체크 추가)
                    save_name = self.save_files[self.cursor]["name"]
                    self.confirm_message = f"'{save_name}'에 덮어쓰시겠습니까?"
                    self.confirm_yes = False
            else:
                # 로드
                if 0 <= self.cursor < len(self.save_files):
                    save_name = self.save_files[self.cursor]["name"]
                    self.selected_save = save_name
                    self.closed = True
                    return True
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.closed = True
            return True

        # 삭제 (DEL 키)
        elif action == GameAction.MENU and self.cursor >= 0 and self.cursor < len(self.save_files):
            # 삭제 확인
            save_name = self.save_files[self.cursor]["name"]
            self.confirm_message = f"'{save_name}'을(를) 삭제하시겠습니까?"
            self.confirm_yes = False

        return False

    def _handle_name_input(self, action: GameAction, event: tcod.event.KeyDown) -> bool:
        """이름 입력 처리"""
        if action == GameAction.CONFIRM:
            self.name_input.handle_confirm()
            if self.name_input.confirmed:
                save_name = self.name_input.get_result()
                if save_name:
                    # 저장 파일 이름 확정
                    self.selected_save = save_name
                    self.creating_new_save = False
                    self.closed = True
                    return True
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.creating_new_save = False
            self.name_input = None
        elif event and event.sym == tcod.event.KeySym.BACKSPACE:
            self.name_input.handle_backspace()
        elif event and event.sym < 128:
            try:
                char = chr(event.sym)
                if char.isprintable():
                    self.name_input.handle_char_input(char)
            except Exception as e:
                # 유효하지 않은 키 심볼 무시
                logger.debug(f"유효하지 않은 키 입력: {e}")

        return False

    def _handle_confirm(self, action: GameAction) -> bool:
        """확인 메시지 처리"""
        if action == GameAction.MOVE_LEFT:
            self.confirm_yes = True
        elif action == GameAction.MOVE_RIGHT:
            self.confirm_yes = False
        elif action == GameAction.CONFIRM:
            if self.confirm_yes:
                # YES 선택
                if self.mode == SaveLoadMode.SAVE:
                    # 덮어쓰기 또는 삭제 (범위 체크)
                    if 0 <= self.cursor < len(self.save_files):
                        if "삭제" in self.confirm_message:
                            # 삭제
                            save_name = self.save_files[self.cursor]["name"]
                            self.save_system.delete_save(save_name)
                            logger.info(f"저장 파일 삭제: {save_name}")

                            # 목록 새로고침
                            self.save_files = self.save_system.list_saves()
                            self.cursor = max(0, min(self.cursor, len(self.save_files) - 1))
                        else:
                            # 덮어쓰기
                            save_name = self.save_files[self.cursor]["name"]
                            self.selected_save = save_name
                            self.closed = True
                            return True

            # 확인 메시지 닫기
            self.confirm_message = None
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.confirm_message = None

        return False

    def _start_new_save(self):
        """새 저장 시작"""
        self.creating_new_save = True

        # 기본 이름 생성
        now = datetime.now()
        default_name = now.strftime("save_%Y%m%d_%H%M%S")

        self.name_input = TextInputBox(
            title="새 저장",
            prompt="저장 파일 이름:",
            max_length=30,
            x=(self.screen_width - 50) // 2,
            y=20,
            width=50,
            default_text=default_name
        )

    def render(self, console: tcod.console.Console):
        """저장/로드 화면 렌더링"""
        console.clear()

        # 제목
        title = "게임 저장" if self.mode == SaveLoadMode.SAVE else "게임 불러오기"
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 이름 입력 중
        if self.creating_new_save and self.name_input:
            self.name_input.render(console)
            return

        # 확인 메시지
        if self.confirm_message:
            self._render_confirm_dialog(console)
            return

        # 저장 파일 목록
        y = 5

        # "새 저장" 옵션 (저장 모드만)
        if self.mode == SaveLoadMode.SAVE:
            is_selected = (self.cursor == -1)
            prefix = "►" if is_selected else " "
            console.print(
                10,
                y,
                f"{prefix} [새 저장...]",
                fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
            )
            y += 2

        # 파일 목록
        if not self.save_files:
            console.print(
                10,
                y,
                "저장 파일이 없습니다.",
                fg=Colors.GRAY
            )
        else:
            for i, save_info in enumerate(self.save_files):
                is_selected = (self.cursor == i)
                prefix = "►" if is_selected else " "

                save_name = save_info["name"]
                save_time = save_info["save_time"]
                floor = save_info.get("floor", 1)
                party_size = save_info.get("party_size", 0)

                # 이름
                console.print(
                    10,
                    y,
                    f"{prefix} {save_name}",
                    fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
                )

                # 정보
                info_text = f"  {floor}층, 파티 {party_size}명"
                console.print(
                    15,
                    y + 1,
                    info_text,
                    fg=Colors.GRAY
                )

                # 저장 시간
                try:
                    dt = datetime.fromisoformat(save_time)
                    time_text = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_text = save_time

                console.print(
                    15,
                    y + 2,
                    time_text,
                    fg=Colors.DARK_GRAY
                )

                y += 4

        # 도움말
        help_y = self.screen_height - 3
        if self.mode == SaveLoadMode.SAVE:
            help_text = "↑↓: 선택  Z: 저장  M: 삭제  X: 취소"
        else:
            help_text = "↑↓: 선택  Z: 불러오기  M: 삭제  X: 취소"

        console.print(
            (self.screen_width - len(help_text)) // 2,
            help_y,
            help_text,
            fg=Colors.GRAY
        )

    def _render_confirm_dialog(self, console: tcod.console.Console):
        """확인 대화상자 렌더링"""
        # 중앙 박스
        box_width = 50
        box_height = 8
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x,
            box_y,
            box_width,
            box_height,
            "확인",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 메시지
        msg_lines = []
        if len(self.confirm_message) > box_width - 6:
            # 줄바꿈
            words = self.confirm_message.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > box_width - 6:
                    msg_lines.append(current_line)
                    current_line = word
                else:
                    current_line += (" " if current_line else "") + word
            if current_line:
                msg_lines.append(current_line)
        else:
            msg_lines = [self.confirm_message]

        y = box_y + 2
        for line in msg_lines:
            console.print(
                box_x + (box_width - len(line)) // 2,
                y,
                line,
                fg=Colors.UI_TEXT
            )
            y += 1

        # YES / NO 버튼
        y = box_y + box_height - 3
        yes_color = Colors.UI_TEXT_SELECTED if self.confirm_yes else Colors.UI_TEXT
        no_color = Colors.UI_TEXT_SELECTED if not self.confirm_yes else Colors.UI_TEXT

        console.print(
            box_x + 15,
            y,
            "[ 예 ]" if self.confirm_yes else "  예  ",
            fg=yes_color
        )

        console.print(
            box_x + 30,
            y,
            "[아니오]" if not self.confirm_yes else " 아니오 ",
            fg=no_color
        )

        # 도움말
        console.print(
            box_x + (box_width - 30) // 2,
            y + 2,
            "←→: 선택  Z: 확인  X: 취소",
            fg=Colors.GRAY
        )


def show_save_screen(
    console: tcod.console.Console,
    context: tcod.context.Context,
    game_state: Dict[str, Any]
) -> bool:
    """
    저장 화면 표시 (로그라이크 방식 - 현재 파일만 덮어쓰기)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        game_state: 저장할 게임 상태

    Returns:
        저장 성공 여부
    """
    save_system = SaveSystem()

    # 현재 세이브 슬롯 가져오기 (없으면 새 슬롯 생성)
    current_slot = game_state.get("save_slot", None)

    if current_slot is None:
        # 새 게임이면 빈 슬롯 찾기
        for i in range(1, 11):  # 최대 10개 슬롯
            if not save_system.save_exists(i):
                current_slot = i
                game_state["save_slot"] = i
                break

        if current_slot is None:
            # 빈 슬롯이 없으면 슬롯 1 사용
            current_slot = 1
            game_state["save_slot"] = 1

    # 현재 슬롯에 바로 저장 (UI 없이)
    success = save_system.save_game(current_slot, game_state)
    if success:
        logger.info(f"게임 저장 완료: 슬롯 {current_slot}")
    else:
        logger.error(f"게임 저장 실패: 슬롯 {current_slot}")

    return success


def show_load_screen(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> Optional[Dict[str, Any]]:
    """
    불러오기 화면 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        로드된 게임 상태 (취소 시 None)
    """
    save_system = SaveSystem()
    ui = SaveLoadUI(console.width, console.height, SaveLoadMode.LOAD, save_system)
    handler = InputHandler()

    logger.info("불러오기 화면 표시")

    while not ui.closed:
        # 렌더링
        ui.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                if ui.handle_input(action):
                    # 로드 실행
                    if ui.selected_save:
                        game_state = save_system.load_game(ui.selected_save)
                        if game_state:
                            logger.info(f"게임 로드 완료: {ui.selected_save}")
                        return game_state
                    return None

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None

    return None
