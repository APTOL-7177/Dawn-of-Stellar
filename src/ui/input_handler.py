"""
Input Handler - tcod 입력 처리

키보드/마우스 입력을 처리하는 시스템
"""

import tcod.event
from typing import Optional, Dict, Callable, Any
from enum import Enum

from src.core.logger import get_logger


class GameAction(Enum):
    """게임 액션"""
    # 이동
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    MOVE_UP_LEFT = "move_up_left"
    MOVE_UP_RIGHT = "move_up_right"
    MOVE_DOWN_LEFT = "move_down_left"
    MOVE_DOWN_RIGHT = "move_down_right"

    # 행동
    INTERACT = "interact"
    PICKUP = "pickup"
    ATTACK = "attack"
    WAIT = "wait"

    # 메뉴
    OPEN_INVENTORY = "open_inventory"
    OPEN_CHARACTER = "open_character"
    OPEN_SKILLS = "open_skills"
    OPEN_MAP = "open_map"

    # 시스템
    ESCAPE = "escape"
    QUIT = "quit"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    MENU = "menu"

    # 페이징
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"

    # 인벤토리 전용
    INVENTORY_DESTROY = "inventory_destroy"


class InputHandler(tcod.event.EventDispatch[Optional[GameAction]]):
    """
    입력 핸들러

    tcod 이벤트를 게임 액션으로 변환
    """

    def __init__(self) -> None:
        self.logger = get_logger("input")

        # 키 바인딩 (KeySym 사용)
        self.key_bindings: Dict[int, GameAction] = {
            # 이동 (화살표)
            tcod.event.KeySym.UP: GameAction.MOVE_UP,
            tcod.event.KeySym.DOWN: GameAction.MOVE_DOWN,
            tcod.event.KeySym.LEFT: GameAction.MOVE_LEFT,
            tcod.event.KeySym.RIGHT: GameAction.MOVE_RIGHT,

            # 이동 (텐키)
            tcod.event.KeySym.KP_8: GameAction.MOVE_UP,
            tcod.event.KeySym.KP_2: GameAction.MOVE_DOWN,
            tcod.event.KeySym.KP_4: GameAction.MOVE_LEFT,
            tcod.event.KeySym.KP_6: GameAction.MOVE_RIGHT,
            tcod.event.KeySym.KP_7: GameAction.MOVE_UP_LEFT,
            tcod.event.KeySym.KP_9: GameAction.MOVE_UP_RIGHT,
            tcod.event.KeySym.KP_1: GameAction.MOVE_DOWN_LEFT,
            tcod.event.KeySym.KP_3: GameAction.MOVE_DOWN_RIGHT,
            tcod.event.KeySym.KP_5: GameAction.WAIT,

            # 행동 (대문자 사용)
            tcod.event.KeySym.SPACE: GameAction.ATTACK,
            tcod.event.KeySym.PERIOD: GameAction.WAIT,

            # 시스템
            tcod.event.KeySym.ESCAPE: GameAction.ESCAPE,
            tcod.event.KeySym.RETURN: GameAction.MENU,  # Enter: 메뉴/확정

            # 페이징
            tcod.event.KeySym.PAGEUP: GameAction.PAGE_UP,
            tcod.event.KeySym.PAGEDOWN: GameAction.PAGE_DOWN,
        }

        # 문자 키 바인딩 (소문자 ord 값)
        self.char_bindings: Dict[str, GameAction] = {
            # vi 키
            'k': GameAction.MOVE_UP,
            'j': GameAction.MOVE_DOWN,
            'h': GameAction.MOVE_LEFT,
            'l': GameAction.MOVE_RIGHT,
            'y': GameAction.MOVE_UP_LEFT,
            'u': GameAction.MOVE_UP_RIGHT,
            'b': GameAction.MOVE_DOWN_LEFT,
            'n': GameAction.MOVE_DOWN_RIGHT,

            # 행동
            'e': GameAction.INTERACT,
            'g': GameAction.PICKUP,

            # 메뉴
            'i': GameAction.OPEN_INVENTORY,
            'c': GameAction.OPEN_CHARACTER,
            's': GameAction.OPEN_SKILLS,
            'm': GameAction.MENU,  # 정렬/메뉴

            # 인벤토리
            'v': GameAction.INVENTORY_DESTROY,  # 파괴/버리기

            # 시스템 (Z = 선택, X = 취소)
            'z': GameAction.CONFIRM,
            'x': GameAction.CANCEL,
            'q': GameAction.QUIT,
        }

    def ev_quit(self, event: tcod.event.Quit) -> Optional[GameAction]:
        """종료 이벤트"""
        return GameAction.QUIT

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[GameAction]:
        """키 다운 이벤트"""
        # KeySym으로 먼저 확인
        action = self.key_bindings.get(event.sym)

        # 문자 키로 확인
        if not action:
            # Unicode 문자로 변환 시도
            try:
                char = chr(event.sym)
                action = self.char_bindings.get(char.lower())
            except (ValueError, OverflowError) as e:
                # 유효하지 않은 키 심볼 (무시)
                self.logger.debug(f"유효하지 않은 키 심볼: {event.sym}")

        if action:
            self.logger.debug(f"키 입력: {event.sym} -> {action.value}")
        else:
            self.logger.debug(f"키 입력 무시: {event.sym} (문자: {chr(event.sym) if event.sym < 128 else 'N/A'})")

        return action

    def get_direction(self, action: GameAction) -> Optional[tuple]:
        """
        액션을 방향 벡터로 변환

        Args:
            action: 게임 액션

        Returns:
            (dx, dy) 또는 None
        """
        direction_map = {
            GameAction.MOVE_UP: (0, -1),
            GameAction.MOVE_DOWN: (0, 1),
            GameAction.MOVE_LEFT: (-1, 0),
            GameAction.MOVE_RIGHT: (1, 0),
            GameAction.MOVE_UP_LEFT: (-1, -1),
            GameAction.MOVE_UP_RIGHT: (1, -1),
            GameAction.MOVE_DOWN_LEFT: (-1, 1),
            GameAction.MOVE_DOWN_RIGHT: (1, 1),
        }

        return direction_map.get(action)


# 전역 인스턴스
input_handler = InputHandler()
