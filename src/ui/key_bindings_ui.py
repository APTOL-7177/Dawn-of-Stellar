"""
키 바인딩 설정 UI

키보드와 게임패드의 키 설정을 변경할 수 있는 UI
"""

from enum import Enum
from typing import Optional, List, Tuple
import tcod

from src.ui.input_handler import (
    InputHandler, GameAction, unified_input_handler,
    key_binding_manager, KEY_NAME_TO_KEYSYM, KEYSYM_TO_KEY_NAME
)
from src.ui.tcod_display import render_space_background
from src.core.logger import get_logger, Loggers
from src.audio import play_sfx


logger = get_logger(Loggers.UI)


class KeyBindingTab(Enum):
    """키 바인딩 탭"""
    KEYBOARD = "keyboard"
    GAMEPAD = "gamepad"


class KeyBindingsUI:
    """키 바인딩 설정 UI"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0
        self.current_tab = KeyBindingTab.KEYBOARD
        self.scroll_offset = 0
        self.max_visible_items = 12
        
        # 키 입력 대기 상태
        self.waiting_for_key = False
        self.waiting_action = None
        
        # 키보드 액션 목록 (4방향 이동)
        self.keyboard_actions = [
            ("이동 - 위", "move_up"),
            ("이동 - 아래", "move_down"),
            ("이동 - 왼쪽", "move_left"),
            ("이동 - 오른쪽", "move_right"),
            ("확인", "confirm"),
            ("취소", "cancel"),
            ("대기", "wait"),
            ("메뉴", "menu"),
            ("탈출", "escape"),
            ("인벤토리", "open_inventory"),
            ("기믹 상세", "gimmick_detail"),
            ("페이지 위", "page_up"),
            ("페이지 아래", "page_down"),
        ]
        
        # 게임패드 버튼 목록
        self.gamepad_buttons = [
            ("버튼 A (✕)", 0),
            ("버튼 B (○)", 1),
            ("버튼 X (□)", 2),
            ("버튼 Y (△)", 3),
            ("LB (L1)", 4),
            ("RB (R1)", 5),
            ("Back (Select)", 6),
            ("Start", 7),
            ("LS (L3)", 8),
            ("RS (R3)", 9),
        ]
        
        # D-pad 방향 (4방향)
        self.dpad_directions = [
            ("D-pad / 스틱", "dpad_info"),  # 정보 표시용
        ]

    def get_current_items(self) -> List[Tuple[str, any]]:
        """현재 탭의 아이템 목록 반환"""
        if self.current_tab == KeyBindingTab.KEYBOARD:
            return self.keyboard_actions
        else:
            return self.gamepad_buttons + self.dpad_directions

    def handle_input(self, action: GameAction) -> Optional[str]:
        """입력 처리"""
        items = self.get_current_items()
        
        if self.waiting_for_key:
            # 키 입력 대기 중 - ESC로 취소
            if action == GameAction.ESCAPE:
                self.waiting_for_key = False
                self.waiting_action = None
                play_sfx("ui", "cursor_cancel")
            return None
        
        if action == GameAction.MOVE_UP:
            self.selected_index = max(0, self.selected_index - 1)
            # 스크롤 조정
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            play_sfx("ui", "cursor_move")
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = min(len(items) - 1, self.selected_index + 1)
            # 스크롤 조정
            if self.selected_index >= self.scroll_offset + self.max_visible_items:
                self.scroll_offset = self.selected_index - self.max_visible_items + 1
            play_sfx("ui", "cursor_move")
        elif action == GameAction.MOVE_LEFT or action == GameAction.MOVE_RIGHT:
            # 탭 전환
            if self.current_tab == KeyBindingTab.KEYBOARD:
                self.current_tab = KeyBindingTab.GAMEPAD
            else:
                self.current_tab = KeyBindingTab.KEYBOARD
            self.selected_index = 0
            self.scroll_offset = 0
            play_sfx("ui", "cursor_move")
        elif action == GameAction.CONFIRM:
            # 키 변경 시작
            if self.current_tab == KeyBindingTab.KEYBOARD:
                self.waiting_for_key = True
                self.waiting_action = items[self.selected_index][1]
                play_sfx("ui", "cursor_ok")
            else:
                item = items[self.selected_index]
                # D-pad 정보 항목은 바인딩 변경 불가
                if isinstance(item[1], int):
                    self.waiting_for_key = True
                    self.waiting_action = item
                    play_sfx("ui", "cursor_ok")
                else:
                    play_sfx("ui", "cursor_cancel")
        elif action == GameAction.CANCEL:
            # 기본값으로 리셋 (현재 선택된 항목만)
            self._reset_current_binding()
            play_sfx("ui", "cursor_cancel")
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            # 저장하고 닫기
            key_binding_manager.save_bindings()
            play_sfx("ui", "cursor_cancel")
            return "close"
        
        return None

    def handle_key_input(self, event: tcod.event.KeyDown) -> bool:
        """키 입력 대기 중 키 처리"""
        if not self.waiting_for_key:
            return False
        
        # ESC는 취소
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.waiting_for_key = False
            self.waiting_action = None
            return True
        
        # 키 이름 가져오기
        key_name = self._keysym_to_name(event.sym)
        if not key_name:
            return True  # 알 수 없는 키는 무시
        
        if self.current_tab == KeyBindingTab.KEYBOARD:
            # 키보드 바인딩 변경
            action_name = self.waiting_action
            current_keys = key_binding_manager.get_keys_for_action(action_name)
            if key_name not in current_keys:
                # 기존 키 목록에 추가 (최대 3개)
                if len(current_keys) >= 3:
                    current_keys = current_keys[1:]  # 가장 오래된 키 제거
                current_keys.append(key_name)
                key_binding_manager.set_keyboard_binding(action_name, current_keys)
            logger.info(f"키보드 바인딩 변경: {action_name} -> {current_keys}")
        else:
            # 게임패드 버튼/D-pad 바인딩 변경
            item = self.waiting_action
            if isinstance(item[1], int):
                # 버튼
                button_id = item[1]
                key_binding_manager.set_gamepad_button_key(button_id, key_name)
                logger.info(f"게임패드 버튼 {button_id} -> 키 '{key_name}'")
            else:
                # D-pad 방향
                direction = item[1]
                key_binding_manager.gamepad_dpad_to_key[direction] = key_name
                logger.info(f"D-pad {direction} -> 키 '{key_name}'")
        
        self.waiting_for_key = False
        self.waiting_action = None
        play_sfx("ui", "cursor_ok")
        return True

    def _keysym_to_name(self, keysym: int) -> Optional[str]:
        """KeySym을 키 이름으로 변환"""
        if keysym in KEYSYM_TO_KEY_NAME:
            return KEYSYM_TO_KEY_NAME[keysym]
        
        # ASCII 문자
        if 32 <= keysym <= 126:
            return chr(keysym)
        
        return None

    def _reset_current_binding(self):
        """현재 선택된 바인딩을 기본값으로 리셋"""
        items = self.get_current_items()
        
        if self.current_tab == KeyBindingTab.KEYBOARD:
            action_name = items[self.selected_index][1]
            # 기본 키보드 바인딩 (KeyBindingManager._load_defaults에서 가져옴)
            defaults = {
                "move_up": ["UP", "k", "KP_8"],
                "move_down": ["DOWN", "j", "KP_2"],
                "move_left": ["LEFT", "h", "KP_4"],
                "move_right": ["RIGHT", "l", "KP_6"],
                "move_up_left": ["y", "KP_7"],
                "move_up_right": ["u", "KP_9"],
                "move_down_left": ["b", "KP_1"],
                "move_down_right": ["n", "KP_3"],
                "confirm": ["z", "RETURN"],
                "cancel": ["x", "ESCAPE"],
                "attack": ["SPACE"],
                "interact": ["e"],
                "wait": ["PERIOD", "KP_5"],
                "pickup": ["p"],
                "menu": ["m"],
                "escape": ["ESCAPE"],
                "open_inventory": ["i"],
                "open_character": ["c"],
                "open_skills": ["s"],
                "gimmick_detail": ["g"],
                "page_up": ["PAGEUP"],
                "page_down": ["PAGEDOWN"],
            }
            if action_name in defaults:
                key_binding_manager.set_keyboard_binding(action_name, defaults[action_name])
        else:
            item = items[self.selected_index]
            if isinstance(item[1], int):
                # 버튼 기본값
                button_defaults = {
                    0: "z", 1: "x", 2: "e", 3: "SPACE",
                    4: "i", 5: "c", 6: "ESCAPE", 7: "m",
                    8: "TAB", 9: "p",
                }
                button_id = item[1]
                if button_id in button_defaults:
                    key_binding_manager.set_gamepad_button_key(button_id, button_defaults[button_id])
            else:
                # D-pad 기본값
                dpad_defaults = {
                    "up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT",
                }
                direction = item[1]
                if direction in dpad_defaults:
                    key_binding_manager.gamepad_dpad_to_key[direction] = dpad_defaults[direction]

    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, console.width, console.height)

        # 제목
        title = "=== 키 설정 ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 255, 100))

        # 탭
        tab_y = 4
        keyboard_color = (255, 255, 100) if self.current_tab == KeyBindingTab.KEYBOARD else (150, 150, 150)
        gamepad_color = (255, 255, 100) if self.current_tab == KeyBindingTab.GAMEPAD else (150, 150, 150)
        
        console.print(10, tab_y, "[ 키보드 ]", fg=keyboard_color)
        console.print(30, tab_y, "[ 게임패드 ]", fg=gamepad_color)
        console.print(10, tab_y + 1, "─" * 40, fg=(100, 100, 100))

        # 현재 탭 아이템 표시
        items = self.get_current_items()
        y = 7
        
        for i in range(self.scroll_offset, min(self.scroll_offset + self.max_visible_items, len(items))):
            item = items[i]
            label = item[0]
            
            # 선택 커서
            if i == self.selected_index:
                console.print(5, y, "►", fg=(255, 255, 100))
                label_color = (255, 255, 255)
            else:
                label_color = (180, 180, 180)

            # 레이블
            console.print(7, y, label, fg=label_color)

            # 현재 바인딩된 키 표시
            if self.current_tab == KeyBindingTab.KEYBOARD:
                action_name = item[1]
                keys = key_binding_manager.get_keys_for_action(action_name)
                key_display = ", ".join([key_binding_manager.get_display_name(k) for k in keys[:3]])
            else:
                if isinstance(item[1], int):
                    # 버튼
                    button_id = item[1]
                    key = key_binding_manager.get_key_for_gamepad_button(button_id)
                    key_display = key_binding_manager.get_display_name(key) if key else "-"
                else:
                    # D-pad
                    direction = item[1]
                    key = key_binding_manager.get_key_for_dpad(direction)
                    key_display = key_binding_manager.get_display_name(key) if key else "-"
            
            key_color = (100, 200, 255) if i == self.selected_index else (120, 160, 200)
            console.print(35, y, f"[ {key_display} ]", fg=key_color)
            
            y += 1

        # 스크롤 인디케이터
        if self.scroll_offset > 0:
            console.print(self.screen_width // 2, 6, "▲", fg=(150, 150, 150))
        if self.scroll_offset + self.max_visible_items < len(items):
            console.print(self.screen_width // 2, 7 + self.max_visible_items, "▼", fg=(150, 150, 150))

        # 키 입력 대기 중 표시
        if self.waiting_for_key:
            box_width = 30
            box_height = 5
            box_x = (self.screen_width - box_width) // 2
            box_y = (self.screen_height - box_height) // 2
            
            # 박스 배경
            for dy in range(box_height):
                for dx in range(box_width):
                    console.print(box_x + dx, box_y + dy, " ", bg=(30, 30, 60))
            
            # 테두리
            for dx in range(box_width):
                console.print(box_x + dx, box_y, "─", fg=(200, 200, 200))
                console.print(box_x + dx, box_y + box_height - 1, "─", fg=(200, 200, 200))
            for dy in range(box_height):
                console.print(box_x, box_y + dy, "│", fg=(200, 200, 200))
                console.print(box_x + box_width - 1, box_y + dy, "│", fg=(200, 200, 200))
            console.print(box_x, box_y, "┌", fg=(200, 200, 200))
            console.print(box_x + box_width - 1, box_y, "┐", fg=(200, 200, 200))
            console.print(box_x, box_y + box_height - 1, "└", fg=(200, 200, 200))
            console.print(box_x + box_width - 1, box_y + box_height - 1, "┘", fg=(200, 200, 200))
            
            # 메시지
            msg = "새 키를 누르세요..."
            console.print(box_x + (box_width - len(msg)) // 2, box_y + 2, msg, fg=(255, 255, 100))
            cancel_msg = "ESC: 취소"
            console.print(box_x + (box_width - len(cancel_msg)) // 2, box_y + 3, cancel_msg, fg=(150, 150, 150))

        # 조작법 (게임패드 연결 시 게임패드 버튼으로 표시)
        help_y = self.screen_height - 4
        use_gamepad = unified_input_handler.gamepad_connected
        
        if use_gamepad:
            move_help = key_binding_manager.get_movement_help(True)
            confirm_key = key_binding_manager.get_action_display("confirm", True)
            cancel_key = key_binding_manager.get_action_display("cancel", True)
            escape_key = key_binding_manager.get_action_display("escape", True)
            help_text = f"{move_help}  {confirm_key}: 변경  {cancel_key}: 기본값  {escape_key}: 저장"
        else:
            help_text = "←→: 탭 전환  ↑↓: 선택  Z: 변경  X: 기본값  ESC: 저장하고 닫기"
        
        console.print(5, help_y, help_text, fg=(180, 180, 180))
        
        # 게임패드 탭일 때 추가 설명
        if self.current_tab == KeyBindingTab.GAMEPAD:
            console.print(
                5, help_y + 1,
                f"게임패드 레이아웃: {key_binding_manager.gamepad_layout.upper()}",
                fg=(150, 200, 150)
            )


def open_key_bindings(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> None:
    """
    키 바인딩 설정 화면 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
    """
    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    ui = KeyBindingsUI(console.width, console.height)

    logger.info("키 바인딩 설정 열림")

    import time
    import pygame

    while True:
        # 렌더링
        ui.render(console)
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            pygame.event.pump()
        except:
            pass

        # 키보드 입력 처리 (논블로킹)
        for event in tcod.event.get():
            # 키 입력 대기 중이면 직접 처리
            if ui.waiting_for_key:
                if isinstance(event, tcod.event.KeyDown):
                    ui.handle_key_input(event)
                continue
            
            # 일반 입력 처리
            action = unified_input_handler.process_tcod_event(event)

            if action:
                result = ui.handle_input(action)

                if result == "close":
                    logger.info("키 바인딩 설정 닫힘")
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                key_binding_manager.save_bindings()
                return

        # 게임패드 입력 처리 (키 입력 대기 중이 아닐 때만)
        if not ui.waiting_for_key:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                result = ui.handle_input(gamepad_action)

                if result == "close":
                    logger.info("키 바인딩 설정 닫힘")
                    return

        # CPU 사용률 낮추기
        time.sleep(0.01)
