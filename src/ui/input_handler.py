"""
Input Handler - tcod 및 게임패드 입력 처리

키보드/마우스/게임패드 입력을 처리하는 시스템
게임패드 입력을 키보드 입력으로 변환하는 새로운 시스템을 지원합니다.
"""

import tcod.event
import pygame
import os
import yaml
from typing import Optional, Dict, Callable, Any, Tuple
from enum import Enum
import threading
import time

from src.core.logger import get_logger

# inputs 라이브러리 (pygame보다 나은 Windows 지원)
try:
    from inputs import get_gamepad
    INPUTS_AVAILABLE = True
except ImportError:
    INPUTS_AVAILABLE = False
from src.core.vibration_system import vibration_manager, vibration_listener


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
    HARVEST = "harvest"

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
    INVENTORY_DROP = "inventory_drop"  # 아이템 드롭
    INVENTORY_DROP_GOLD = "inventory_drop_gold"  # 골드 드롭
    USE_CONSUMABLE = "use_consumable"  # 음식/소비품 사용

    # 전투 전용
    GIMMICK_DETAIL = "gimmick_detail"

    # 멀티플레이 전용
    ADD_BOT = "add_bot"  # 봇 추가
    CHAT = "chat"        # 채팅

    # 필드 스킬
    FIELD_SKILL = "field_skill"

    # 탐험 유틸리티
    TELEPORT_TO_SPAWN = "teleport_to_spawn"  # 스폰 위치로 텔레포트 (긴급 탈출)


# 키 반복(held key)이 허용되는 액션 (이동/페이징만)
_REPEATABLE_ACTIONS = frozenset({
    GameAction.MOVE_UP, GameAction.MOVE_DOWN,
    GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT,
    GameAction.MOVE_UP_LEFT, GameAction.MOVE_UP_RIGHT,
    GameAction.MOVE_DOWN_LEFT, GameAction.MOVE_DOWN_RIGHT,
    GameAction.PAGE_UP, GameAction.PAGE_DOWN,
})


class GamepadLayout(Enum):
    """게임패드 레이아웃 타입"""
    XBOX = "xbox"
    PLAYSTATION = "playstation"
    NINTENDO = "nintendo"
    GENERIC = "generic"


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
            'p': GameAction.PICKUP,  # 변경: g -> p (기믹 커맨드를 위해)

            # 메뉴
            'i': GameAction.OPEN_INVENTORY,
            'c': GameAction.OPEN_CHARACTER,
            's': GameAction.OPEN_SKILLS,
            'm': GameAction.MENU,  # 정렬/메뉴

            # 전투 (기믹 상세)
            'g': GameAction.GIMMICK_DETAIL,  # 기믹 상세 보기

            # 인벤토리
            'v': GameAction.INVENTORY_DESTROY,  # 파괴/버리기
            'd': GameAction.INVENTORY_DROP,  # 아이템 드롭
            'g': GameAction.INVENTORY_DROP_GOLD,  # 골드 드롭
            # 'f': GameAction.USE_CONSUMABLE,  # 음식/소비품 사용 (필드 스킬과 충돌하여 제거)

            # 시스템 (Z = 선택, X = 취소)
            'z': GameAction.CONFIRM,
            'x': GameAction.CANCEL,
            'q': GameAction.QUIT,

            # 채팅 / 릴리 대화
            't': GameAction.CHAT,
            # 필드 스킬
            'f': GameAction.FIELD_SKILL,
            # 스폰 위치 텔레포트 (긴급 탈출)
            'r': GameAction.TELEPORT_TO_SPAWN,

            # 게임패드용 듀얼 바인딩 (rs_left, rs_right 활용)
            'w': GameAction.GIMMICK_DETAIL,  # g 외에 w도 기믹 상세로 추가
        }

        # KeySym 바인딩에 Tab → OPEN_MAP 추가 (N키는 이동과 충돌하므로 Tab 사용)
        self.key_bindings[tcod.event.KeySym.TAB] = GameAction.OPEN_MAP

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


# 키 이름을 tcod KeySym으로 변환하는 매핑
KEY_NAME_TO_KEYSYM: Dict[str, int] = {
    # 방향키
    "UP": tcod.event.KeySym.UP,
    "DOWN": tcod.event.KeySym.DOWN,
    "LEFT": tcod.event.KeySym.LEFT,
    "RIGHT": tcod.event.KeySym.RIGHT,
    
    # 특수 키
    "SPACE": tcod.event.KeySym.SPACE,
    "RETURN": tcod.event.KeySym.RETURN,
    "ENTER": tcod.event.KeySym.RETURN,
    "ESCAPE": tcod.event.KeySym.ESCAPE,
    "ESC": tcod.event.KeySym.ESCAPE,
    "TAB": tcod.event.KeySym.TAB,
    "BACKSPACE": tcod.event.KeySym.BACKSPACE,
    "DELETE": tcod.event.KeySym.DELETE,
    "PERIOD": tcod.event.KeySym.PERIOD,
    
    # 텐키
    "KP_0": tcod.event.KeySym.KP_0,
    "KP_1": tcod.event.KeySym.KP_1,
    "KP_2": tcod.event.KeySym.KP_2,
    "KP_3": tcod.event.KeySym.KP_3,
    "KP_4": tcod.event.KeySym.KP_4,
    "KP_5": tcod.event.KeySym.KP_5,
    "KP_6": tcod.event.KeySym.KP_6,
    "KP_7": tcod.event.KeySym.KP_7,
    "KP_8": tcod.event.KeySym.KP_8,
    "KP_9": tcod.event.KeySym.KP_9,
    
    # 페이지 키
    "PAGEUP": tcod.event.KeySym.PAGEUP,
    "PAGEDOWN": tcod.event.KeySym.PAGEDOWN,
    "HOME": tcod.event.KeySym.HOME,
    "END": tcod.event.KeySym.END,
    
    # 기능 키
    "F1": tcod.event.KeySym.F1,
    "F2": tcod.event.KeySym.F2,
    "F3": tcod.event.KeySym.F3,
    "F4": tcod.event.KeySym.F4,
    "F5": tcod.event.KeySym.F5,
    "F6": tcod.event.KeySym.F6,
    "F7": tcod.event.KeySym.F7,
    "F8": tcod.event.KeySym.F8,
    "F9": tcod.event.KeySym.F9,
    "F10": tcod.event.KeySym.F10,
    "F11": tcod.event.KeySym.F11,
    "F12": tcod.event.KeySym.F12,
}

# KeySym을 키 이름으로 변환 (역방향)
KEYSYM_TO_KEY_NAME: Dict[int, str] = {v: k for k, v in KEY_NAME_TO_KEYSYM.items()}


class KeyBindingManager:
    """
    키 바인딩 관리자
    
    키보드와 게임패드의 키 바인딩을 관리하고 저장/로드합니다.
    게임패드 버튼은 키보드 키로 변환되어 처리됩니다.
    """
    
    def __init__(self):
        self.logger = get_logger("key_binding")
        self.config_path = os.path.join("config", "key_bindings.yaml")
        
        # 키보드 바인딩: action -> list of keys
        self.keyboard_bindings: Dict[str, list] = {}
        
        # 게임패드 버튼 -> 키보드 키 매핑
        self.gamepad_button_to_key: Dict[int, str] = {}
        
        # 게임패드 D-pad -> 키보드 키 매핑
        self.gamepad_dpad_to_key: Dict[str, str] = {}
        
        # 게임패드 스틱 -> 키보드 키 매핑
        self.gamepad_stick_to_key: Dict[str, str] = {}
        
        # 게임패드 설정
        self.gamepad_layout = "xbox"
        self.gamepad_deadzone = 0.3
        
        # 기본값 로드 후 설정 파일 로드
        self._load_defaults()
        self.load_bindings()
    
    def _load_defaults(self):
        """기본 키 바인딩 설정"""
        # 키보드 기본 바인딩
        self.keyboard_bindings = {
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
            "gimmick_detail": ["g", "w"],
            "inventory_destroy": ["v"],
            "inventory_drop": ["d"],
            "inventory_drop_gold": ["g"],
            "page_up": ["PAGEUP"],
            "page_down": ["PAGEDOWN"],
            "quit": ["q"],
        }
        
        # 게임패드 버튼 -> 키보드 키 기본 매핑 (Xbox 기준)
        self.gamepad_button_to_key = {
            0: "z",        # A - 확인 (Z키)
            1: "x",        # B - 취소 (X키)
            2: "e",        # X - 상호작용 (E키)
            3: "SPACE",    # Y - 공격 (Space키)
            4: "i",        # LB - 인벤토리 (I키)
            5: "c",        # RB - 캐릭터 (C키)
            6: "ESCAPE",   # Back - 탈출 (ESC키)
            7: "m",        # Start - 메뉴 (M키)
            8: "PERIOD",   # Left Stick (L3) - 대기 (.)
            9: "p",        # Right Stick (R3) - 줍기 (P키)
            "trigger_l": "s", # Left Trigger - 스킬 (S키)
            "trigger_r": "f", # Right Trigger - 필드 스킬 (F키)
            "rs_up": "PAGEUP",    # 우측 스틱 위 - 페이지 업
            "rs_down": "PAGEDOWN",# 우측 스틱 아래 - 페이지 다운
            "rs_left": "d",       # 우측 스틱 왼쪽 - 인벤토리 드롭 (D키)
            "rs_right": "v",      # 우측 스틱 오른쪽 - 인벤토리 파괴/버리기 (V키)
        }
        
        # 게임패드 D-pad -> 키보드 키 기본 매핑
        self.gamepad_dpad_to_key = {
            "up": "UP",
            "down": "DOWN",
            "left": "LEFT",
            "right": "RIGHT",
            "up_left": "y",
            "up_right": "u",
            "down_left": "b",
            "down_right": "n",
        }
        
        # 게임패드 스틱 -> 키보드 키 기본 매핑
        self.gamepad_stick_to_key = {
            "up": "UP",
            "down": "DOWN",
            "left": "LEFT",
            "right": "RIGHT",
        }
    
    def load_bindings(self) -> bool:
        """설정 파일에서 키 바인딩 로드"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.info("키 바인딩 설정 파일 없음, 기본값 사용")
                self.save_bindings()  # 기본값 저장
                return True
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return True
            
            # 키보드 바인딩 로드
            if 'keyboard' in data:
                for action, keys in data['keyboard'].items():
                    if isinstance(keys, list):
                        self.keyboard_bindings[action] = keys
                    else:
                        self.keyboard_bindings[action] = [keys]
            
            # 게임패드 설정 로드
            if 'gamepad' in data:
                gp = data['gamepad']
                
                if 'layout' in gp:
                    self.gamepad_layout = gp['layout']
                
                if 'deadzone' in gp:
                    self.gamepad_deadzone = float(gp['deadzone'])
                
                if 'button_to_key' in gp:
                    self.gamepad_button_to_key = {
                        int(k): v for k, v in gp['button_to_key'].items()
                    }
                
                if 'dpad_to_key' in gp:
                    self.gamepad_dpad_to_key = gp['dpad_to_key']
                
                if 'stick_to_key' in gp:
                    self.gamepad_stick_to_key = gp['stick_to_key']
            
            self.logger.info(f"키 바인딩 로드 완료: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"키 바인딩 로드 실패: {e}")
            return False
    
    def save_bindings(self) -> bool:
        """키 바인딩을 설정 파일에 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            data = {
                'keyboard': self.keyboard_bindings,
                'gamepad': {
                    'layout': self.gamepad_layout,
                    'deadzone': self.gamepad_deadzone,
                    'button_to_key': {
                        str(k): v for k, v in self.gamepad_button_to_key.items()
                    },
                    'dpad_to_key': self.gamepad_dpad_to_key,
                    'stick_to_key': self.gamepad_stick_to_key,
                }
            }
            
            # 주석이 포함된 YAML 헤더 추가
            header = """# Dawn of Stellar - 키 바인딩 설정
# 키보드와 게임패드 키 바인딩을 각각 설정할 수 있습니다.
# 게임패드 입력은 지정된 키보드 키로 변환되어 처리됩니다.

"""
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(header)
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"키 바인딩 저장 완료: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"키 바인딩 저장 실패: {e}")
            return False
    
    def reset_to_defaults(self):
        """기본값으로 리셋"""
        self._load_defaults()
        self.save_bindings()
        self.logger.info("키 바인딩 기본값으로 리셋")
    
    def set_keyboard_binding(self, action: str, keys: list):
        """키보드 바인딩 설정"""
        self.keyboard_bindings[action] = keys
    
    def set_gamepad_button_key(self, button_id: int, key: str):
        """게임패드 버튼 -> 키보드 키 매핑 설정"""
        self.gamepad_button_to_key[button_id] = key
    
    def get_action_for_key(self, key_name: str) -> Optional[GameAction]:
        """키 이름으로 액션 찾기"""
        key_lower = key_name.lower() if len(key_name) == 1 else key_name
        
        for action_name, keys in self.keyboard_bindings.items():
            for k in keys:
                k_compare = k.lower() if len(k) == 1 else k
                if k_compare == key_lower:
                    try:
                        return GameAction(action_name)
                    except ValueError:
                        pass
        return None
    
    def get_keys_for_action(self, action: str) -> list:
        """액션에 바인딩된 키 목록 반환"""
        return self.keyboard_bindings.get(action, [])
    
    def get_key_for_gamepad_button(self, button_id: int) -> Optional[str]:
        """게임패드 버튼에 매핑된 키보드 키 반환"""
        return self.gamepad_button_to_key.get(button_id)
    
    def get_key_for_dpad(self, direction: str) -> Optional[str]:
        """D-pad 방향에 매핑된 키보드 키 반환"""
        return self.gamepad_dpad_to_key.get(direction)
    
    def get_key_for_stick(self, direction: str) -> Optional[str]:
        """아날로그 스틱 방향에 매핑된 키보드 키 반환"""
        return self.gamepad_stick_to_key.get(direction)
    
    def key_to_keysym(self, key_name: str) -> Optional[int]:
        """키 이름을 tcod KeySym으로 변환"""
        # 대문자로 변환해서 확인
        key_upper = key_name.upper()
        if key_upper in KEY_NAME_TO_KEYSYM:
            return KEY_NAME_TO_KEYSYM[key_upper]
        
        # 단일 문자인 경우 ord 값 반환
        if len(key_name) == 1:
            return ord(key_name.lower())
        
        return None
    
    def keysym_to_key(self, keysym: int) -> str:
        """tcod KeySym을 키 이름으로 변환"""
        if keysym in KEYSYM_TO_KEY_NAME:
            return KEYSYM_TO_KEY_NAME[keysym]
        
        # ASCII 범위인 경우 문자로 변환
        if 32 <= keysym <= 126:
            return chr(keysym)
        
        return f"KEY_{keysym}"
    
    def get_display_name(self, key_name: str) -> str:
        """키 이름을 표시용 이름으로 변환"""
        display_names = {
            "UP": "↑",
            "DOWN": "↓",
            "LEFT": "←",
            "RIGHT": "→",
            "SPACE": "Space",
            "RETURN": "Enter",
            "ENTER": "Enter",
            "ESCAPE": "ESC",
            "ESC": "ESC",
            "PAGEUP": "PgUp",
            "PAGEDOWN": "PgDn",
            "PERIOD": ".",
            "KP_0": "Num0",
            "KP_1": "Num1",
            "KP_2": "Num2",
            "KP_3": "Num3",
            "KP_4": "Num4",
            "KP_5": "Num5",
            "KP_6": "Num6",
            "KP_7": "Num7",
            "KP_8": "Num8",
            "KP_9": "Num9",
        }
        
        key_upper = key_name.upper()
        if key_upper in display_names:
            return display_names[key_upper]
        
        # 단일 문자는 대문자로 표시
        if len(key_name) == 1:
            return key_name.upper()
        
        return key_name
    
    def get_gamepad_button_display_name(self, button_id: int, layout: str = None) -> str:
        """게임패드 버튼 ID를 표시용 이름으로 변환"""
        if layout is None:
            layout = self.gamepad_layout
        
        xbox_names = {
            0: "A", 1: "B", 2: "X", 3: "Y",
            4: "LB", 5: "RB", 6: "Back", 7: "Start",
            8: "LS", 9: "RS",
        }
        
        ps_names = {
            0: "✕", 1: "○", 2: "□", 3: "△",
            4: "L1", 5: "R1", 6: "Select", 7: "Start",
            8: "L3", 9: "R3",
        }
        
        nintendo_names = {
            0: "B", 1: "A", 2: "Y", 3: "X",
            4: "L", 5: "R", 6: "-", 7: "+",
            8: "LS", 9: "RS",
        }
        
        if layout == "xbox":
            return xbox_names.get(button_id, f"BTN{button_id}")
        elif layout == "playstation":
            return ps_names.get(button_id, f"BTN{button_id}")
        elif layout == "nintendo":
            return nintendo_names.get(button_id, f"BTN{button_id}")
        else:
            return f"BTN{button_id}"
    
    def get_action_display(self, action_name: str, use_gamepad: bool = False) -> str:
        """
        액션에 대한 표시용 키/버튼 이름 반환
        
        Args:
            action_name: 액션 이름 (예: "confirm", "cancel")
            use_gamepad: 게임패드 버튼으로 표시할지 여부
        
        Returns:
            표시용 문자열 (예: "Z" 또는 "A버튼")
        """
        if use_gamepad:
            # 게임패드 버튼 중 해당 키에 매핑된 버튼 찾기
            keys = self.get_keys_for_action(action_name)
            if keys:
                first_key = keys[0]
                # 해당 키에 매핑된 게임패드 버튼 찾기
                for button_id, mapped_key in self.gamepad_button_to_key.items():
                    if mapped_key.lower() == first_key.lower() or mapped_key == first_key:
                        return self.get_gamepad_button_display_name(button_id)
            # 찾지 못하면 키보드 키 반환
            return self.get_display_name(keys[0]) if keys else "?"
        else:
            # 키보드 키
            keys = self.get_keys_for_action(action_name)
            if keys:
                return self.get_display_name(keys[0])
            return "?"
    
    def get_help_text(self, actions: list, use_gamepad: bool = False, separator: str = "  ") -> str:
        """
        여러 액션에 대한 도움말 텍스트 생성
        
        Args:
            actions: (액션명, 설명) 튜플 리스트 예: [("confirm", "확인"), ("cancel", "취소")]
            use_gamepad: 게임패드 버튼으로 표시할지 여부
            separator: 구분자
        
        Returns:
            도움말 문자열 (예: "Z: 확인  X: 취소" 또는 "A: 확인  B: 취소")
        """
        parts = []
        for action_name, label in actions:
            key_display = self.get_action_display(action_name, use_gamepad)
            parts.append(f"{key_display}: {label}")
        return separator.join(parts)
    
    def get_movement_help(self, use_gamepad: bool = False) -> str:
        """이동 도움말 텍스트"""
        if use_gamepad:
            return "D-pad/스틱: 이동"
        else:
            return "↑↓←→: 이동"


# 전역 키 바인딩 매니저
key_binding_manager = KeyBindingManager()


class GamepadHandler:
    """
    게임패드 입력 핸들러

    pygame joystick을 사용하여 게임패드 입력을 처리
    """

    def __init__(self) -> None:
        self.logger = get_logger("gamepad")

        # 게임패드 인스턴스
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.connected = False

        # 입력 상태 추적 (헤드리스 여부와 무관하게 항상 초기화)
        self.prev_button_states = {}
        self.prev_axis_states = {}
        self.prev_hat_states = {}

        # 게임패드 레이아웃별 기본 매핑
        self.layout_mappings = {
            GamepadLayout.XBOX: {
                # Xbox 컨트롤러 (A/B/X/Y 순서)
                0: GameAction.CONFIRM,      # A - 확인
                1: GameAction.CANCEL,       # B - 취소
                2: GameAction.ATTACK,       # X - 공격
                3: GameAction.INTERACT,     # Y - 상호작용

                # Shoulder buttons
                4: GameAction.OPEN_INVENTORY,    # LB - 인벤토리
                5: GameAction.OPEN_CHARACTER,    # RB - 캐릭터

                # Start/Back
                6: GameAction.MENU,         # Back - 메뉴
                7: GameAction.ESCAPE,       # Start - 탈출

                # Stick clicks
                8: GameAction.FIELD_SKILL,  # Left Stick (L3) - 필드 스킬
                9: GameAction.TELEPORT_TO_SPAWN,  # Right Stick (R3) - 스폰 텔레포트
            },

            GamepadLayout.PLAYSTATION: {
                # PlayStation 컨트롤러 (Cross/Circle/Square/Triangle 순서)
                0: GameAction.CONFIRM,      # Cross - 확인
                1: GameAction.CANCEL,       # Circle - 취소
                2: GameAction.ATTACK,       # Square - 공격
                3: GameAction.INTERACT,     # Triangle - 상호작용

                # Shoulder buttons (L1/R1)
                4: GameAction.OPEN_INVENTORY,    # L1 - 인벤토리
                5: GameAction.OPEN_CHARACTER,    # R1 - 캐릭터

                # Start/Select
                6: GameAction.MENU,         # Select - 메뉴
                7: GameAction.ESCAPE,       # Start - 탈출

                # Stick clicks (L3/R3)
                8: GameAction.FIELD_SKILL,  # L3 - 필드 스킬
                9: GameAction.TELEPORT_TO_SPAWN,  # R3 - 스폰 텔레포트
            },

            GamepadLayout.NINTENDO: {
                # Nintendo Switch 컨트롤러 (B/A/Y/X 순서)
                0: GameAction.CANCEL,       # B - 취소
                1: GameAction.CONFIRM,      # A - 확인
                2: GameAction.INTERACT,     # Y - 상호작용
                3: GameAction.ATTACK,       # X - 공격

                # Shoulder buttons (L/R)
                4: GameAction.OPEN_INVENTORY,    # L - 인벤토리
                5: GameAction.OPEN_CHARACTER,    # R - 캐릭터

                # Start/Select (-/+)
                6: GameAction.MENU,         # Select (-) - 메뉴
                7: GameAction.ESCAPE,       # Start (+) - 탈출

                # Stick clicks
                8: GameAction.FIELD_SKILL,  # Left Stick (L3) - 필드 스킬
                9: GameAction.TELEPORT_TO_SPAWN,  # Right Stick (R3) - 스폰 텔레포트
            },

            GamepadLayout.GENERIC: {
                # 일반적인 매핑 (모든 컨트롤러에 호환)
                0: GameAction.CONFIRM,      # 버튼 1 - 확인
                1: GameAction.CANCEL,       # 버튼 2 - 취소
                2: GameAction.ATTACK,       # 버튼 3 - 공격
                3: GameAction.INTERACT,     # 버튼 4 - 상호작용

                # Shoulder buttons
                4: GameAction.OPEN_INVENTORY,    # L1 - 인벤토리
                5: GameAction.OPEN_CHARACTER,    # R1 - 캐릭터

                # Start/Select
                6: GameAction.MENU,         # Select - 메뉴
                7: GameAction.ESCAPE,       # Start - 탈출

                # 추가 버튼들
                8: GameAction.FIELD_SKILL,  # 버튼 9 (L3) - 필드 스킬
                9: GameAction.TELEPORT_TO_SPAWN,  # 버튼 10 (R3) - 스폰 텔레포트
            }
        }

        # 현재 레이아웃 (자동 감지)
        self.current_layout = GamepadLayout.GENERIC
        self.default_button_mappings = self.layout_mappings[self.current_layout]

        # 설정 파일 경로
        self.config_path = os.path.join("config", "gamepad_mappings.yaml")

        # 버튼 매핑 로드
        self.button_mappings = self._load_mappings()

        # D-pad 매핑 (hat)
        self.hat_mappings = {
            (0, 1): GameAction.MOVE_UP,          # 위
            (0, -1): GameAction.MOVE_DOWN,       # 아래
            (-1, 0): GameAction.MOVE_LEFT,       # 왼쪽
            (1, 0): GameAction.MOVE_RIGHT,       # 오른쪽
            (-1, 1): GameAction.MOVE_UP_LEFT,    # 왼쪽 위
            (1, 1): GameAction.MOVE_UP_RIGHT,    # 오른쪽 위
            (-1, -1): GameAction.MOVE_DOWN_LEFT, # 왼쪽 아래
            (1, -1): GameAction.MOVE_DOWN_RIGHT, # 오른쪽 아래
        }

        # 아날로그 스틱 데드존
        self.deadzone = 0.3

        # 이동 쿨타임 (키보드처럼 작동)
        # 플레이어: 0.2초, 적: 0.3초로 설정 (플레이어가 1.5배 빠름)
        self.move_cooldown = 0.2  # 첫 번째 입력 후 대기 시간
        self.repeat_cooldown = 0.2  # 연속 입력 간격 (0.05에서 변경)
        self.last_move_time = 0
        self.first_move_time = 0
        self.is_first_move = True
        self.last_action = None
        self._direction_held = False  # 방향 입력 물리적 활성 여부

        # 버튼 입력 딜레이 (같은 버튼 연속 입력 방지)
        self.button_input_delay = 0.15  # 같은 버튼 입력 간 최소 딜레이 (초)
        self.last_button_times: Dict[int, float] = {}  # 버튼별 마지막 입력 시간
        self.last_direction_time: Dict[str, float] = {}  # 방향별 마지막 입력 시간
        
        # 스틱 방향 고정 (미세한 각도 변화 무시용)
        self.locked_stick_direction: Optional[str] = None

        # 헤드리스 환경(RL 학습 등)에서는 pygame/joystick 초기화 건너뛰기
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            self.logger.info("헤드리스 환경 감지 - 게임패드 초기화 건너뛰기")
            return

        # pygame 초기화 (이미 초기화되어 있다면 생략)
        if not pygame.get_init():
            pygame.init()

        # joystick 초기화
        pygame.joystick.init()

        # 게임패드 연결 시도
        self._initialize_joystick()

    def _load_mappings(self) -> Dict[int, GameAction]:
        """설정 파일에서 버튼 매핑 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                # 레이아웃 설정 로드
                if data and 'layout' in data:
                    try:
                        self.current_layout = GamepadLayout(data['layout'])
                        self.default_button_mappings = self.layout_mappings[self.current_layout]
                    except ValueError:
                        self.logger.warning(f"알 수 없는 레이아웃: {data['layout']}, 기본값 사용")

                # 데드존 설정 로드
                if data and 'deadzone' in data:
                    self.deadzone = float(data['deadzone'])

                mappings = {}
                if data and 'button_mappings' in data:
                    for button_str, action_str in data['button_mappings'].items():
                        button_id = int(button_str)
                        action = GameAction(action_str)
                        mappings[button_id] = action

                self.logger.info(f"게임패드 설정 로드됨: 레이아웃={self.current_layout.value}, 매핑={len(mappings)}개 버튼")
                return mappings
            else:
                self.logger.debug("게임패드 설정 파일 없음, 기본 매핑 사용")
                return self.default_button_mappings.copy()
        except Exception as e:
            self.logger.error(f"게임패드 매핑 로드 실패: {e}")
            return self.default_button_mappings.copy()

    def save_mappings(self) -> bool:
        """현재 버튼 매핑을 설정 파일에 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            data = {
                'layout': self.current_layout.value,
                'deadzone': self.deadzone,
                'button_mappings': {
                    str(button_id): action.value
                    for button_id, action in self.button_mappings.items()
                }
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"게임패드 설정 저장됨: {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"게임패드 설정 저장 실패: {e}")
            return False

    def set_button_mapping(self, button_id: int, action: GameAction) -> None:
        """특정 버튼의 매핑 설정"""
        self.button_mappings[button_id] = action
        self.logger.debug(f"버튼 {button_id} -> {action.value} 매핑 설정")

    def reset_mappings(self) -> None:
        """매핑을 기본값으로 리셋"""
        self.button_mappings = self.default_button_mappings.copy()
        self.logger.info("게임패드 매핑 기본값으로 리셋")

    def _detect_layout(self, joystick_name: str) -> GamepadLayout:
        """게임패드 이름으로 레이아웃 자동 감지"""
        name_lower = joystick_name.lower()

        # Xbox 및 Xbox 호환 컨트롤러 감지 (ROG Ally, Steam Deck 등)
        if any(keyword in name_lower for keyword in ['xbox', 'x-input', 'microsoft',
                                                      'rog', 'ally', 'asus', 'steam deck',
                                                      'x360', 'xinput']):
            return GamepadLayout.XBOX

        # PlayStation 컨트롤러 감지
        elif any(keyword in name_lower for keyword in ['playstation', 'dualshock', 'ds4', 'ps4', 'ps5', 'dualsense']):
            return GamepadLayout.PLAYSTATION

        # Nintendo 컨트롤러 감지
        elif any(keyword in name_lower for keyword in ['nintendo', 'switch', 'pro controller', 'joy-con']):
            return GamepadLayout.NINTENDO

        # 기본값
        else:
            return GamepadLayout.GENERIC

    def _initialize_joystick(self) -> None:
        """게임패드 초기화"""
        try:
            # pygame 이벤트 초기화 (중요!)
            pygame.event.get()  # 기존 이벤트 비우기

            joystick_count = pygame.joystick.get_count()
            self.logger.info(f"감지된 조이스틱 수: {joystick_count}")

            if joystick_count == 0:
                self.logger.debug("게임패드 미감지")
                return

            if joystick_count > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()

                joystick_name = self.joystick.get_name()
                self.logger.info(f"게임패드 초기화 시도: {joystick_name}")

                # 버튼 수, 축 수 확인
                num_buttons = self.joystick.get_numbuttons()
                num_axes = self.joystick.get_numaxes()
                num_hats = self.joystick.get_numhats()

                self.logger.info(f"게임패드 정보: 버튼={num_buttons}, 축={num_axes}, 햇={num_hats}")

                if num_buttons > 0:  # 버튼이 하나라도 있어야 게임패드로 인정
                    self.connected = True

                    # 레이아웃 자동 감지
                    self.current_layout = self._detect_layout(joystick_name)
                    self.default_button_mappings = self.layout_mappings[self.current_layout]

                    # 진동 시스템에 게임패드 설정
                    vibration_manager.set_joystick(self.joystick)

                    self.logger.info(f"Gamepad connected: {joystick_name} (layout: {self.current_layout.value})")

                    # 초기 상태 저장
                    self._update_states()
                else:
                    self.logger.warning(f"게임패드에 버튼이 없음: {joystick_name}")
                    self.connected = False
                    vibration_manager.set_joystick(None)
            else:
                self.connected = False
                vibration_manager.set_joystick(None)
                self.logger.debug("연결된 게임패드 없음")
        except Exception as e:
            self.logger.error(f"게임패드 초기화 실패: {e}")
            import traceback
            self.logger.error(f"상세 오류: {traceback.format_exc()}")
            self.connected = False

    def _update_states(self) -> None:
        """현재 입력 상태 업데이트"""
        if not self.connected or not self.joystick:
            return

        # 버튼 상태
        self.prev_button_states = {}
        for i in range(self.joystick.get_numbuttons()):
            self.prev_button_states[i] = self.joystick.get_button(i)

        # 아날로그 스틱 상태
        self.prev_axis_states = {}
        for i in range(self.joystick.get_numaxes()):
            self.prev_axis_states[i] = self.joystick.get_axis(i)

        # D-pad 상태
        self.prev_hat_states = {}
        for i in range(self.joystick.get_numhats()):
            self.prev_hat_states[i] = self.joystick.get_hat(i)

    def get_action(self) -> Optional[GameAction]:
        """
        게임패드 입력으로부터 게임 액션 반환
        
        게임패드 입력은 먼저 키보드 키로 변환된 후, 해당 키에 바인딩된 액션으로 변환됩니다.

        Returns:
            GameAction 또는 None
        """
        if not self.connected or not self.joystick:
            return None

        try:
            # pygame 이벤트 큐 업데이트 (중요!)
            pygame.event.pump()

            # pygame 이벤트 가져오기 (디버깅용)
            pygame_events = pygame.event.get()
            
            current_time = time.time()

            # 폴링 방식으로 버튼 입력 확인 (Windows에서 더 안정적)
            for button_id in range(self.joystick.get_numbuttons()):
                current_state = self.joystick.get_button(button_id)
                prev_state = self.prev_button_states.get(button_id, False)

                # 버튼이 눌렸을 때만 처리 + 같은 버튼 딜레이 체크
                if current_state and not prev_state:
                    # 같은 버튼 입력 딜레이 체크
                    last_time = self.last_button_times.get(button_id, 0)
                    if current_time - last_time < self.button_input_delay:
                        continue
                    
                    # 키보드 키로 변환
                    key_name = key_binding_manager.get_key_for_gamepad_button(button_id)
                    
                    # LB나 L2 등의 조합을 위한 모디파이어 확인 (선택적)
                    # 여기서는 일단 기본 변환만 수행
                    
                    if key_name:
                        # 키에 해당하는 액션 찾기
                        action = key_binding_manager.get_action_for_key(key_name)
                        if action:
                            self.last_button_times[button_id] = current_time
                            self.logger.debug(f"게임패드 버튼 {button_id} -> 키 '{key_name}' -> {action.value}")
                            self._update_states()
                            return action

            # 트리거 입력 확인 (아날로그 축을 버튼처럼 사용)
            if self.joystick.get_numaxes() >= 6:
                # Xbox/PS 기준 트리거는 보통 axis 4(LT/L2), 5(RT/R2) 또는 2(LT), 5(RT) 
                # Pygame 2에서 Xbox 컨트롤러: LT는 보통 4, RT는 5.
                # PS4/PS5: L2는 4, R2는 5
                axes_to_check = {
                    4: "trigger_l",
                    5: "trigger_r"
                }
                
                # 가끔 트리거가 2, 3번 축에 매핑되는 경우도 대응
                if self.joystick.get_name().lower().find("xbox") != -1 and self.joystick.get_numaxes() == 6:
                    # SDL2의 Xbox 컨트롤러 매핑: 4=LT, 5=RT
                    pass
                
                for axis_id, trigger_name in axes_to_check.items():
                    if axis_id < self.joystick.get_numaxes():
                        val = self.joystick.get_axis(axis_id)
                        # 트리거는 보통 -1(안눌림) ~ 1(끝까지 눌림), 또는 0~1
                        # 0.5 이상 눌렸을 때 버튼 클릭으로 간주
                        is_pressed = val > 0.5
                        was_pressed = self.prev_axis_states.get(axis_id, -1.0) > 0.5
                        
                        if is_pressed and not was_pressed:
                            last_time = self.last_button_times.get(trigger_name, 0)
                            if current_time - last_time >= self.button_input_delay:
                                key_name = key_binding_manager.gamepad_button_to_key.get(trigger_name)
                                if key_name:
                                    action = key_binding_manager.get_action_for_key(key_name)
                                    if action:
                                        self.last_button_times[trigger_name] = current_time
                                        self.logger.debug(f"게임패드 {trigger_name} -> 키 '{key_name}' -> {action.value}")
                                        self._update_states()
                                        return action

            # 우측 스틱 확인 (Right Stick) - Axis 2, 3 (또는 3, 4)
            # 페이징이나 기타 기능에 활용 가능
            if self.joystick.get_numaxes() >= 4:
                # 오른쪽 스틱 X, Y축 인덱스는 보통 2, 3 또는 3, 4
                rs_x, rs_y = 2, 3
                if self.joystick.get_name().lower().find("ps") != -1:
                    rs_x, rs_y = 2, 3
                elif self.joystick.get_numaxes() >= 6:
                    rs_x, rs_y = 2, 3
                
                x_val = self.joystick.get_axis(rs_x) if rs_x < self.joystick.get_numaxes() else 0
                y_val = self.joystick.get_axis(rs_y) if rs_y < self.joystick.get_numaxes() else 0
                
                deadzone = 0.5
                rs_dir = None
                if y_val < -deadzone:
                    rs_dir = "rs_up"
                elif y_val > deadzone:
                    rs_dir = "rs_down"
                elif x_val < -deadzone:
                    rs_dir = "rs_left"
                elif x_val > deadzone:
                    rs_dir = "rs_right"
                    
                if rs_dir:
                    last_dir_time = self.last_direction_time.get(rs_dir, 0)
                    if current_time - last_dir_time >= 0.2: # 0.2초 쿨다운
                        key_name = key_binding_manager.gamepad_button_to_key.get(rs_dir)
                        if key_name:
                            action = key_binding_manager.get_action_for_key(key_name)
                            if action:
                                self.last_direction_time[rs_dir] = current_time
                                self.logger.debug(f"우측 스틱 {rs_dir} -> 키 '{key_name}' -> {action.value}")
                                self._update_states()
                                return action

            # D-pad / 아날로그 스틱 방향 입력 확인
            self._direction_held = False

            # D-pad 입력 확인 (키보드 키 변환 방식)
            action = self._get_dpad_action_via_key()
            if action:
                self._update_states()
                return action

            # 아날로그 스틱 입력 확인 (키보드 키 변환 방식)
            action = self._get_analog_stick_action_via_key()
            if action:
                self._update_states()
                return action

            # 방향 입력이 물리적으로 해제되었으면 반복 상태 리셋
            if not self._direction_held:
                self.last_action = None
                self.is_first_move = True

        except Exception as e:
            self.logger.error(f"게임패드 입력 처리 오류: {e}")

        # 상태 업데이트 (다음 입력 감지를 위해)
        self._update_states()

        return None

    def _get_dpad_action_via_key(self) -> Optional[GameAction]:
        """D-pad 입력을 키보드 키로 변환 후 액션 반환 (연속 입력 지원)
        
        D-pad는 아날로그 스틱과 동일한 매핑(stick_to_key)을 사용합니다.
        컨트롤러에 따라 D-pad가 hat, 축, 또는 버튼으로 처리되므로 모두 확인합니다.
        """
        if not self.joystick:
            return None

        direction = None
        current_time = time.time()

        # 1. D-pad (hat) 입력 확인
        for hat_id in range(self.joystick.get_numhats()):
            current_hat = self.joystick.get_hat(hat_id)
            if current_hat != (0, 0):
                direction = self._hat_to_direction(current_hat)
                break

        # 2. D-pad 버튼으로 확인 (DualSense 등 - 버튼 11-14가 D-pad)
        if not direction:
            num_buttons = self.joystick.get_numbuttons()
            # DualSense D-pad 버튼: 11=Up, 12=Down, 13=Left, 14=Right
            if num_buttons >= 15:
                dpad_up = self.joystick.get_button(11) if num_buttons > 11 else False
                dpad_down = self.joystick.get_button(12) if num_buttons > 12 else False
                dpad_left = self.joystick.get_button(13) if num_buttons > 13 else False
                dpad_right = self.joystick.get_button(14) if num_buttons > 14 else False
                
                if dpad_up:
                    direction = "up"
                elif dpad_down:
                    direction = "down"
                elif dpad_left:
                    direction = "left"
                elif dpad_right:
                    direction = "right"

        # 3. Hat과 버튼이 없으면 D-pad 축(axis)으로 확인
        # 단, Xbox/GENERIC 6축 컨트롤러에서는 axis 4,5가 LT/RT 트리거이므로
        # D-pad 축으로 사용하면 안 됨 (ROG Ally 등에서 키가 계속 눌리는 버그 발생)
        if not direction and self.joystick.get_numaxes() >= 8:
            # 8축 이상인 컨트롤러만 D-pad 축 사용 (PS 컨트롤러 등)
            num_axes = self.joystick.get_numaxes()
            dpad_x_axis = num_axes - 2
            dpad_y_axis = num_axes - 1

            dpad_x = self.joystick.get_axis(dpad_x_axis)
            dpad_y = self.joystick.get_axis(dpad_y_axis)

            dpad_deadzone = 0.5
            if abs(dpad_x) > dpad_deadzone or abs(dpad_y) > dpad_deadzone:
                direction = self._axis_to_direction(dpad_x, dpad_y, dpad_deadzone)

        if not direction:
            return None

        self._direction_held = True  # D-pad 방향 입력 감지됨

        # 아날로그 스틱 매핑(stick_to_key)을 우선 사용 (D-pad → 스틱 신호 변환)
        key_name = key_binding_manager.get_key_for_stick(direction)
        if not key_name:
            # 스틱 매핑에 없으면 D-pad 매핑 사용 (대각선 등)
            key_name = key_binding_manager.get_key_for_dpad(direction)
        if not key_name:
            return None

        # 키에 해당하는 액션 가져오기
        action = key_binding_manager.get_action_for_key(key_name)
        if not action:
            return None

        # 같은 방향 딜레이 체크
        last_dir_time = self.last_direction_time.get(direction, 0)
        time_since_last = current_time - last_dir_time

        # 첫 번째 입력 또는 방향 변경 시
        if action != self.last_action:
            # 같은 방향 딜레이 체크 (다른 방향은 즉시 허용)
            if time_since_last < self.button_input_delay:
                return None
            
            self.is_first_move = True
            self.first_move_time = current_time
            self.last_action = action
            self.last_move_time = current_time
            self.last_direction_time[direction] = current_time
            self.logger.debug(f"D-pad {direction} -> 키 '{key_name}' -> {action.value}")
            return action

        # 첫 번째 입력 후 0.3초 이내는 입력 무시
        if self.is_first_move and time_since_last < 0.3:
            return None

        # 첫 번째 입력 후 0.3초가 지나면 연속 입력 허용
        if self.is_first_move:
            self.is_first_move = False

        # 연속 입력은 0.05초마다 허용
        if time_since_last >= 0.05:
            self.last_move_time = current_time
            self.last_direction_time[direction] = current_time
            return action

        return None

    def _hat_to_direction(self, hat: Tuple[int, int]) -> Optional[str]:
        """hat 값을 방향 문자열로 변환"""
        hat_directions = {
            (0, 1): "up",
            (0, -1): "down",
            (-1, 0): "left",
            (1, 0): "right",
            (-1, 1): "up_left",
            (1, 1): "up_right",
            (-1, -1): "down_left",
            (1, -1): "down_right",
        }
        return hat_directions.get(hat)

    def _get_dpad_action(self) -> Optional[GameAction]:
        """D-pad를 키보드처럼 연속 입력으로 변환 (기존 방식 - 호환성 유지)"""
        if not self.joystick:
            return None

        # D-pad (hat) 입력 확인
        for hat_id in range(self.joystick.get_numhats()):
            current_hat = self.joystick.get_hat(hat_id)

            if current_hat != (0, 0):
                current_time = time.time()

                # 방향 계산
                action = self.hat_mappings.get(current_hat)

                if action:
                    # 키보드처럼 연속 입력 처리
                    time_since_last = current_time - self.last_move_time

                    # 첫 번째 입력 또는 방향 변경 시
                    if action != self.last_action:
                        self.is_first_move = True
                        self.first_move_time = current_time
                        self.last_action = action
                        self.last_move_time = current_time
                        return action

                    # 첫 번째 입력 후 0.5초 이내는 입력 무시
                    if self.is_first_move and time_since_last < 0.5:
                        return None

                    # 첫 번째 입력 후 0.5초가 지나면 연속 입력 허용
                    if self.is_first_move:
                        self.is_first_move = False

                    # 연속 입력은 0.1초마다 허용
                    if time_since_last >= self.repeat_cooldown:
                        self.last_move_time = current_time
                        return action

        return None

    def _get_analog_stick_action_via_key(self) -> Optional[GameAction]:
        """아날로그 스틱을 키보드 키로 변환 후 액션 반환 (연속 입력 지원)"""
        if not self.joystick:
            return None

        # 왼쪽 스틱 (보통 axis 0=x, 1=y)
        if self.joystick.get_numaxes() >= 2:
            x_axis = self.joystick.get_axis(0)
            y_axis = self.joystick.get_axis(1)

            # 데드존 적용 (ROG Ally 등 드리프트가 큰 기기 대응: 최소 0.5)
            strict_deadzone = max(key_binding_manager.gamepad_deadzone, 0.5)
            
            # 스틱이 중립 위치로 돌아왔으면 방향 잠금 해제
            if abs(x_axis) <= strict_deadzone and abs(y_axis) <= strict_deadzone:
                self.locked_stick_direction = None
                return None
            
            if abs(x_axis) > strict_deadzone or abs(y_axis) > strict_deadzone:
                current_time = time.time()

                # 스틱 방향 계산
                raw_direction = self._axis_to_direction(x_axis, y_axis, strict_deadzone)
                if not raw_direction:
                    return None

                self._direction_held = True  # 아날로그 스틱 방향 입력 감지됨

                # 방향이 고정되어 있으면 호환되는 방향인지 확인
                is_new_direction = False
                if self.locked_stick_direction:
                    # 완전히 다른 방향이면 방향 변경 허용
                    if self._is_different_direction(self.locked_stick_direction, raw_direction):
                        direction = raw_direction
                        self.locked_stick_direction = direction
                        is_new_direction = True
                    else:
                        # 미세한 변화는 무시하고 기존 방향 유지
                        direction = self.locked_stick_direction
                else:
                    # 새로운 방향 고정
                    direction = raw_direction
                    self.locked_stick_direction = direction
                    is_new_direction = True

                # 방향에 해당하는 키보드 키 가져오기
                key_name = key_binding_manager.get_key_for_stick(direction)
                if not key_name:
                    # 대각선은 D-pad 매핑 사용
                    key_name = key_binding_manager.get_key_for_dpad(direction)
                if not key_name:
                    return None

                # 키에 해당하는 액션 가져오기
                action = key_binding_manager.get_action_for_key(key_name)
                if not action:
                    return None

                # 같은 방향 딜레이 체크
                last_dir_time = self.last_direction_time.get(direction, 0)
                time_since_last = current_time - last_dir_time

                # 새로운 방향이면 첫 입력으로 처리
                if is_new_direction:
                    self.is_first_move = True
                    self.first_move_time = current_time
                    self.last_action = action
                    self.last_move_time = current_time
                    self.last_direction_time[direction] = current_time
                    self.logger.debug(f"스틱 {direction} -> 키 '{key_name}' -> {action.value} (새 방향)")
                    return action

                # 첫 번째 입력 후 0.3초 이내는 입력 무시
                if self.is_first_move and time_since_last < 0.3:
                    return None

                # 첫 번째 입력 후 0.3초가 지나면 연속 입력 허용
                if self.is_first_move:
                    self.is_first_move = False

                # 연속 입력은 0.05초마다 허용
                if time_since_last >= 0.05:
                    self.last_move_time = current_time
                    self.last_direction_time[direction] = current_time
                    return action

        return None

    def _axis_to_direction(self, x_axis: float, y_axis: float, deadzone: float) -> Optional[str]:
        """아날로그 스틱 축 값을 방향 문자열로 변환"""
        if y_axis < -deadzone and x_axis < -deadzone:
            return "up_left"
        elif y_axis < -deadzone and x_axis > deadzone:
            return "up_right"
        elif y_axis > deadzone and x_axis < -deadzone:
            return "down_left"
        elif y_axis > deadzone and x_axis > deadzone:
            return "down_right"
        elif y_axis < -deadzone:
            return "up"
        elif y_axis > deadzone:
            return "down"
        elif x_axis < -deadzone:
            return "left"
        elif x_axis > deadzone:
            return "right"
        return None

    def _is_different_direction(self, locked: str, new: str) -> bool:
        """두 방향이 완전히 다른 방향인지 확인 (미세한 각도 변화 구분)"""
        # 같은 방향이면 False
        if locked == new:
            return False
        
        # 방향별 호환 그룹 정의
        # 같은 그룹 내에서는 미세한 변화로 취급
        compatible_groups = {
            "up": {"up", "up_left", "up_right"},
            "down": {"down", "down_left", "down_right"},
            "left": {"left", "up_left", "down_left"},
            "right": {"right", "up_right", "down_right"},
            "up_left": {"up_left", "up", "left"},
            "up_right": {"up_right", "up", "right"},
            "down_left": {"down_left", "down", "left"},
            "down_right": {"down_right", "down", "right"},
        }
        
        # 고정된 방향의 호환 그룹 확인
        group = compatible_groups.get(locked, set())
        
        # 새 방향이 호환 그룹에 있으면 미세한 변화 (False)
        # 호환 그룹에 없으면 완전히 다른 방향 (True)
        return new not in group

    def _get_analog_stick_action(self) -> Optional[GameAction]:
        """아날로그 스틱을 디지털 입력으로 변환 (기존 방식 - 호환성 유지)"""
        if not self.joystick:
            return None

        # 왼쪽 스틱 (보통 axis 0=x, 1=y)
        if self.joystick.get_numaxes() >= 2:
            x_axis = self.joystick.get_axis(0)
            y_axis = self.joystick.get_axis(1)

            # 더 엄격한 데드존 적용 (0.5로 증가)
            strict_deadzone = 0.5
            if abs(x_axis) > strict_deadzone or abs(y_axis) > strict_deadzone:
                current_time = time.time()

                # 방향 계산
                action = None
                if y_axis < -strict_deadzone and x_axis < -strict_deadzone:
                    action = GameAction.MOVE_UP_LEFT
                elif y_axis < -strict_deadzone and x_axis > strict_deadzone:
                    action = GameAction.MOVE_UP_RIGHT
                elif y_axis > strict_deadzone and x_axis < -strict_deadzone:
                    action = GameAction.MOVE_DOWN_LEFT
                elif y_axis > strict_deadzone and x_axis > strict_deadzone:
                    action = GameAction.MOVE_DOWN_RIGHT
                elif y_axis < -strict_deadzone:
                    action = GameAction.MOVE_UP
                elif y_axis > strict_deadzone:
                    action = GameAction.MOVE_DOWN
                elif x_axis < -strict_deadzone:
                    action = GameAction.MOVE_LEFT
                elif x_axis > strict_deadzone:
                    action = GameAction.MOVE_RIGHT

                if action:
                    # 키보드처럼 연속 입력 처리
                    time_since_last = current_time - self.last_move_time

                    # 첫 번째 입력 또는 방향 변경 시
                    if action != self.last_action:
                        self.is_first_move = True
                        self.first_move_time = current_time
                        self.last_action = action
                        self.last_move_time = current_time
                        return action

                    # 첫 번째 입력 후 0.5초 이내는 입력 무시
                    if self.is_first_move and time_since_last < 0.5:
                        return None

                    # 첫 번째 입력 후 0.5초가 지나면 연속 입력 허용
                    if self.is_first_move:
                        self.is_first_move = False

                    # 연속 입력은 0.1초마다 허용
                    if time_since_last >= self.repeat_cooldown:
                        self.last_move_time = current_time
                        return action

        return None

    def update(self) -> None:
        """프레임마다 호출하여 연결 상태 확인"""
        # 연결 상태만 확인 (상태 업데이트는 get_action()에서 처리)
        if pygame.joystick.get_count() > 0 and not self.connected:
            self._initialize_joystick()
        elif pygame.joystick.get_count() == 0 and self.connected:
            self.connected = False
            self.joystick = None
            self.logger.info("게임패드 연결 해제됨")

    def get_direction(self, action: GameAction) -> Optional[Tuple[int, int]]:
        """
        게임패드 액션을 방향 벡터로 변환

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


class UnifiedInputHandler:
    """
    통합 입력 핸들러

    키보드와 게임패드 입력을 모두 처리
    """

    def __init__(self) -> None:
        self.keyboard_handler = InputHandler()
        self.gamepad_handler = GamepadHandler()
        self.logger = get_logger("unified_input")

        # 키보드 키별 디바운싱 (키 통합이 아닌 키별로 따로)
        self.keyboard_input_delay = 0.03  # 같은 키 입력 간 최소 딜레이 (초) - 매우 짧게
        self.last_key_times: Dict[int, float] = {}  # 키별 마지막 입력 시간

        # 화면 전환 시 입력 쿨다운 (clear_input_state 호출 후 일정 시간 입력 무시)
        self._input_cooldown_until: float = 0.0

    def get_action(self) -> Optional[GameAction]:
        """
        통합 입력 처리

        우선순위: 게임패드 > 키보드
        """
        # 화면 전환 쿨다운 중에는 입력 무시
        if time.time() < self._input_cooldown_until:
            # 게임패드 상태는 업데이트하되 액션은 반환하지 않음
            if self.gamepad_handler.connected and self.gamepad_handler.joystick:
                self.gamepad_handler._update_states()
            return None

        # 게임패드 입력 우선
        gamepad_action = self.gamepad_handler.get_action()
        if gamepad_action:
            return gamepad_action

        # 키보드 입력 처리 (tcod 이벤트가 필요하므로 별도 처리)
        # 이 부분은 메인 루프에서 tcod 이벤트와 함께 호출되어야 함

        return None

    def process_tcod_event(self, event) -> Optional[GameAction]:
        """tcod 이벤트를 처리하여 액션 반환 (게임패드 우선, 키보드 차선)"""
        # 화면 전환 쿨다운 중에는 입력 무시 (KeyUp은 상태 정리를 위해 허용)
        if time.time() < self._input_cooldown_until:
            if isinstance(event, tcod.event.KeyUp):
                key_sym = event.sym
                if key_sym in self.last_key_times:
                    del self.last_key_times[key_sym]
            # 게임패드 상태는 업데이트하되 액션은 반환하지 않음
            if self.gamepad_handler.connected and self.gamepad_handler.joystick:
                self.gamepad_handler._update_states()
            return None

        # 게임패드 입력 우선 확인
        gamepad_action = self.gamepad_handler.get_action()
        if gamepad_action:
            return gamepad_action

        # 키보드 키를 뗐을 때 디바운싱 타이머 리셋
        if isinstance(event, tcod.event.KeyUp):
            key_sym = event.sym
            if key_sym in self.last_key_times:
                del self.last_key_times[key_sym]
            return None

        # 키보드 입력 처리 (키보드 이벤트는 즉시 처리)
        if isinstance(event, tcod.event.KeyDown):
            current_time = time.time()
            key_sym = event.sym
            
            # 키 반복 (repeat=True)일 때: 이동 키만 허용, 확인/취소 등은 무시
            if event.repeat:
                # 먼저 액션을 확인하여 이동 계열인지 판단
                action = self.keyboard_handler.dispatch(event)
                if action and action in _REPEATABLE_ACTIONS:
                    last_time = self.last_key_times.get(key_sym, 0)
                    if current_time - last_time < self.keyboard_input_delay:
                        return None  # 디바운싱 간격 내 무시
                    self.last_key_times[key_sym] = current_time
                    return action
                # 이동 외 키 반복은 무시 (확인, 취소 등 오입력 방지)
                return None

            # 새로운 키 누름 (repeat=False)은 항상 허용
            action = self.keyboard_handler.dispatch(event)
            if action:
                self.last_key_times[key_sym] = current_time
            return action
        
        # 다른 이벤트 (Quit 등)는 그대로 처리
        return self.keyboard_handler.dispatch(event)


    def get_direction(self, action: GameAction) -> Optional[Tuple[int, int]]:
        """액션을 방향 벡터로 변환"""
        # 게임패드 방향 우선
        direction = self.gamepad_handler.get_direction(action)
        if direction:
            return direction

        # 키보드 방향
        return self.keyboard_handler.get_direction(action)

    @property
    def gamepad_connected(self) -> bool:
        """게임패드 연결 상태"""
        return self.gamepad_handler.connected

    def clear_input_state(self) -> None:
        """입력 상태 초기화 (메시지 박스 등에서 이전 입력이 즉시 처리되는 것 방지)"""
        # 키보드 디바운싱 타이머 리셋
        self.last_key_times.clear()

        # 화면 전환 쿨다운 설정 (200ms간 모든 입력 무시)
        # Z키 등이 물리적으로 눌린 채 다음 화면으로 넘어가는 것을 방지
        self._input_cooldown_until = time.time() + 0.20

        # tcod 이벤트 큐 플러시 (tcod/pygame 이중 큐 문제 해결)
        import tcod.event
        for _ in tcod.event.get():
            pass

        # pygame 이벤트 큐 플러시 (키보드 이벤트가 다음 화면으로 전달되는 것 방지)
        pygame.event.clear()

        # 게임패드 상태 업데이트 (현재 눌린 버튼을 "이전 상태"로 기록)
        if self.gamepad_handler.connected and self.gamepad_handler.joystick:
            self.gamepad_handler._update_states()
            # 스틱 방향 잠금 해제
            self.gamepad_handler.locked_stick_direction = None
            # 첫 이동 플래그 리셋
            self.gamepad_handler.is_first_move = True
            self.gamepad_handler.last_action = None


# 전역 인스턴스
input_handler = InputHandler()
gamepad_handler = GamepadHandler()
unified_input_handler = UnifiedInputHandler()


def iter_game_input(timeout=0.05):
    """
    키보드 + 게임패드 통합 입력 제너레이터 (블로킹).

    tcod.event.wait() 대체용. 짧은 타임아웃으로 게임패드 폴링을 허용하면서
    CPU를 과도하게 사용하지 않습니다.

    Yields:
        (action, event) 튜플:
        - action: Optional[GameAction] (키보드 또는 게임패드)
        - event: Optional[tcod.event.Event] (게임패드 입력 시 None)

    Usage:
        for action, event in iter_game_input():
            if action == GameAction.CONFIRM: ...
            elif action == GameAction.CANCEL: ...
    """
    # 게임패드 먼저 확인 (이미 큐에 입력이 있을 수 있음)
    gp_action = unified_input_handler.get_action()
    if gp_action:
        yield gp_action, None
        return

    # tcod 이벤트 대기 (타임아웃으로 게임패드 폴링 허용)
    for event in tcod.event.wait(timeout=timeout):
        if isinstance(event, tcod.event.Quit):
            yield GameAction.QUIT, event
            return
        action = unified_input_handler.process_tcod_event(event)
        yield action, event

    # tcod 타임아웃 후 게임패드 재확인
    gp_action = unified_input_handler.get_action()
    if gp_action:
        yield gp_action, None


def poll_game_input():
    """
    키보드 + 게임패드 통합 입력 제너레이터 (논블로킹).

    tcod.event.get() 대체용. 자체 프레임 루프가 있는 화면에서 사용합니다.

    Yields:
        (action, event) 튜플, iter_game_input()과 동일 형식.

    Usage:
        for action, event in poll_game_input():
            if action == GameAction.CONFIRM: ...
    """
    # 게임패드 먼저 확인
    gp_action = unified_input_handler.get_action()
    if gp_action:
        yield gp_action, None
        return

    # 대기 중인 tcod 이벤트 처리
    for event in tcod.event.get():
        if isinstance(event, tcod.event.Quit):
            yield GameAction.QUIT, event
            return
        action = unified_input_handler.process_tcod_event(event)
        yield action, event

    # tcod 이벤트 처리 후 게임패드 재확인
    gp_action = unified_input_handler.get_action()
    if gp_action:
        yield gp_action, None
