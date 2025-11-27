"""
Input Handler - tcod 및 게임패드 입력 처리

키보드/마우스/게임패드 입력을 처리하는 시스템
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


class GamepadHandler:
    """
    게임패드 입력 핸들러

    pygame joystick을 사용하여 게임패드 입력을 처리
    """

    def __init__(self) -> None:
        self.logger = get_logger("gamepad")

        # pygame 초기화 (이미 초기화되어 있다면 생략)
        if not pygame.get_init():
            pygame.init()

        # joystick 초기화
        pygame.joystick.init()

        # 게임패드 인스턴스
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.connected = False

        # 입력 상태 추적
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
                8: GameAction.OPEN_SKILLS,  # Left Stick - 스킬
                9: GameAction.PICKUP,       # Right Stick - 줍기
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
                8: GameAction.OPEN_SKILLS,  # L3 - 스킬
                9: GameAction.PICKUP,       # R3 - 줍기
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
                8: GameAction.OPEN_SKILLS,  # Left Stick - 스킬
                9: GameAction.PICKUP,       # Right Stick - 줍기
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
                8: GameAction.OPEN_SKILLS,  # 버튼 9 - 스킬
                9: GameAction.PICKUP,       # 버튼 10 - 줍기
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

        # Xbox 컨트롤러 감지
        if any(keyword in name_lower for keyword in ['xbox', 'x-input', 'microsoft']):
            return GamepadLayout.XBOX

        # PlayStation 컨트롤러 감지
        elif any(keyword in name_lower for keyword in ['playstation', 'dualshock', 'ds4', 'ps4', 'ps5']):
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
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.connected = True

                # 레이아웃 자동 감지
                joystick_name = self.joystick.get_name()
                self.current_layout = self._detect_layout(joystick_name)
                self.default_button_mappings = self.layout_mappings[self.current_layout]

                # 진동 시스템에 게임패드 설정
                vibration_manager.set_joystick(self.joystick)

                self.logger.info(f"게임패드 연결됨: {joystick_name} (레이아웃: {self.current_layout.value})")

                # 초기 상태 저장
                self._update_states()
            else:
                self.connected = False
                vibration_manager.set_joystick(None)
                self.logger.debug("게임패드 없음")
        except Exception as e:
            self.logger.error(f"게임패드 초기화 실패: {e}")
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

        Returns:
            GameAction 또는 None
        """
        if not self.connected or not self.joystick:
            return None

        # 버튼 입력 확인
        for button_id, action in self.button_mappings.items():
            if button_id < self.joystick.get_numbuttons():
                current_state = self.joystick.get_button(button_id)
                prev_state = self.prev_button_states.get(button_id, False)

                # 버튼이 눌렸을 때만 액션 반환
                if current_state and not prev_state:
                    self.logger.debug(f"게임패드 버튼 {button_id} -> {action.value}")
                    return action

        # D-pad 입력 확인
        for hat_id in range(self.joystick.get_numhats()):
            current_hat = self.joystick.get_hat(hat_id)
            prev_hat = self.prev_hat_states.get(hat_id, (0, 0))

            if current_hat != prev_hat and current_hat != (0, 0):
                action = self.hat_mappings.get(current_hat)
                if action:
                    self.logger.debug(f"게임패드 D-pad {current_hat} -> {action.value}")
                    return action

        # 아날로그 스틱 입력 확인 (디지털 입력으로 변환)
        action = self._get_analog_stick_action()
        if action:
            return action

        return None

    def _get_analog_stick_action(self) -> Optional[GameAction]:
        """아날로그 스틱을 디지털 입력으로 변환"""
        if not self.joystick:
            return None

        # 왼쪽 스틱 (보통 axis 0=x, 1=y)
        if self.joystick.get_numaxes() >= 2:
            x_axis = self.joystick.get_axis(0)
            y_axis = self.joystick.get_axis(1)

            # 데드존 적용
            if abs(x_axis) > self.deadzone or abs(y_axis) > self.deadzone:
                # 8방향 입력 계산
                if y_axis < -self.deadzone and x_axis < -self.deadzone:
                    return GameAction.MOVE_UP_LEFT
                elif y_axis < -self.deadzone and x_axis > self.deadzone:
                    return GameAction.MOVE_UP_RIGHT
                elif y_axis > self.deadzone and x_axis < -self.deadzone:
                    return GameAction.MOVE_DOWN_LEFT
                elif y_axis > self.deadzone and x_axis > self.deadzone:
                    return GameAction.MOVE_DOWN_RIGHT
                elif y_axis < -self.deadzone:
                    return GameAction.MOVE_UP
                elif y_axis > self.deadzone:
                    return GameAction.MOVE_DOWN
                elif x_axis < -self.deadzone:
                    return GameAction.MOVE_LEFT
                elif x_axis > self.deadzone:
                    return GameAction.MOVE_RIGHT

        return None

    def update(self) -> None:
        """프레임마다 호출하여 상태 업데이트"""
        if self.connected and self.joystick:
            self._update_states()
        else:
            # 연결 상태 확인
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

    def get_action(self) -> Optional[GameAction]:
        """
        통합 입력 처리

        우선순위: 게임패드 > 키보드
        """
        # 게임패드 입력 우선
        gamepad_action = self.gamepad_handler.get_action()
        if gamepad_action:
            return gamepad_action

        # 키보드 입력 처리 (tcod 이벤트가 필요하므로 별도 처리)
        # 이 부분은 메인 루프에서 tcod 이벤트와 함께 호출되어야 함

        return None

    def process_tcod_event(self, event) -> Optional[GameAction]:
        """tcod 이벤트를 처리하여 액션 반환"""
        return self.keyboard_handler.dispatch(event)

    def update_gamepad(self) -> None:
        """게임패드 상태 업데이트"""
        self.gamepad_handler.update()

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


# 전역 인스턴스
input_handler = InputHandler()
gamepad_handler = GamepadHandler()
unified_input_handler = UnifiedInputHandler()
