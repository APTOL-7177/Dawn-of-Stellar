"""
이벤트 어댑터 - pygame 이벤트 → tcod 이벤트 변환

tcod.event.KeyDown / Quit 등과 isinstance() 호환을 위해
tcod 이벤트 클래스를 상속. tcod.event.wait()/get()을 monkey-patch하여
pygame 이벤트 소스로 자동 전환.
"""

import pygame
import tcod.event

from typing import Iterator, Optional
from src.core.logger import get_logger

logger = get_logger("event_adapter")

# ──────────────────────────────────────────────────────────────────
# pygame.K_* → tcod.event.KeySym.* 매핑
# ──────────────────────────────────────────────────────────────────

_PG_TO_TCOD_KEY = {
    # 특수 키
    pygame.K_ESCAPE: tcod.event.KeySym.ESCAPE,
    pygame.K_RETURN: tcod.event.KeySym.RETURN,
    pygame.K_KP_ENTER: tcod.event.KeySym.KP_ENTER,
    pygame.K_TAB: tcod.event.KeySym.TAB,
    pygame.K_BACKSPACE: tcod.event.KeySym.BACKSPACE,
    pygame.K_DELETE: tcod.event.KeySym.DELETE,
    pygame.K_INSERT: tcod.event.KeySym.INSERT,
    pygame.K_SPACE: tcod.event.KeySym.SPACE,

    # 방향키
    pygame.K_UP: tcod.event.KeySym.UP,
    pygame.K_DOWN: tcod.event.KeySym.DOWN,
    pygame.K_LEFT: tcod.event.KeySym.LEFT,
    pygame.K_RIGHT: tcod.event.KeySym.RIGHT,

    # 텐키
    pygame.K_KP_0: tcod.event.KeySym.KP_0,
    pygame.K_KP_1: tcod.event.KeySym.KP_1,
    pygame.K_KP_2: tcod.event.KeySym.KP_2,
    pygame.K_KP_3: tcod.event.KeySym.KP_3,
    pygame.K_KP_4: tcod.event.KeySym.KP_4,
    pygame.K_KP_5: tcod.event.KeySym.KP_5,
    pygame.K_KP_6: tcod.event.KeySym.KP_6,
    pygame.K_KP_7: tcod.event.KeySym.KP_7,
    pygame.K_KP_8: tcod.event.KeySym.KP_8,
    pygame.K_KP_9: tcod.event.KeySym.KP_9,

    # 페이지/홈/엔드
    pygame.K_PAGEUP: tcod.event.KeySym.PAGEUP,
    pygame.K_PAGEDOWN: tcod.event.KeySym.PAGEDOWN,
    pygame.K_HOME: tcod.event.KeySym.HOME,
    pygame.K_END: tcod.event.KeySym.END,

    # F키
    pygame.K_F1: tcod.event.KeySym.F1,
    pygame.K_F2: tcod.event.KeySym.F2,
    pygame.K_F3: tcod.event.KeySym.F3,
    pygame.K_F4: tcod.event.KeySym.F4,
    pygame.K_F5: tcod.event.KeySym.F5,
    pygame.K_F6: tcod.event.KeySym.F6,
    pygame.K_F7: tcod.event.KeySym.F7,
    pygame.K_F8: tcod.event.KeySym.F8,
    pygame.K_F9: tcod.event.KeySym.F9,
    pygame.K_F10: tcod.event.KeySym.F10,
    pygame.K_F11: tcod.event.KeySym.F11,
    pygame.K_F12: tcod.event.KeySym.F12,

    # 수정 키
    pygame.K_LSHIFT: tcod.event.KeySym.LSHIFT,
    pygame.K_RSHIFT: tcod.event.KeySym.RSHIFT,
    pygame.K_LCTRL: tcod.event.KeySym.LCTRL,
    pygame.K_RCTRL: tcod.event.KeySym.RCTRL,
    pygame.K_LALT: tcod.event.KeySym.LALT,
    pygame.K_RALT: tcod.event.KeySym.RALT,

    # 기호
    pygame.K_PERIOD: tcod.event.KeySym.PERIOD,
    pygame.K_COMMA: tcod.event.KeySym.COMMA,
    pygame.K_SLASH: tcod.event.KeySym.SLASH,
    pygame.K_BACKSLASH: tcod.event.KeySym.BACKSLASH,
    pygame.K_SEMICOLON: tcod.event.KeySym.SEMICOLON,
    pygame.K_MINUS: tcod.event.KeySym.MINUS,
    pygame.K_EQUALS: tcod.event.KeySym.EQUALS,
    pygame.K_LEFTBRACKET: tcod.event.KeySym.LEFTBRACKET,
    pygame.K_RIGHTBRACKET: tcod.event.KeySym.RIGHTBRACKET,
    pygame.K_BACKQUOTE: tcod.event.KeySym.GRAVE,
    pygame.K_QUOTE: tcod.event.KeySym.APOSTROPHE,
}

# 영문 알파벳 (a-z)
for _i in range(26):
    _pg_key = pygame.K_a + _i
    # tcod.event.KeySym 값은 SDL 스캔코드와 다를 수 있으므로 문자열로 매핑
    _tcod_name = chr(ord('a') + _i)
    _tcod_sym = getattr(tcod.event.KeySym, _tcod_name, None)
    if _tcod_sym is not None:
        _PG_TO_TCOD_KEY[_pg_key] = _tcod_sym

# 숫자 (0-9)
for _i in range(10):
    _pg_key = pygame.K_0 + _i
    _tcod_name = f"N{_i}"
    _tcod_sym = getattr(tcod.event.KeySym, _tcod_name, None)
    if _tcod_sym is None:
        # 일부 tcod 버전에서는 숫자가 직접 문자 값으로 매핑
        _tcod_sym = ord(str(_i))
    _PG_TO_TCOD_KEY[_pg_key] = _tcod_sym


def _pg_key_to_tcod_sym(pg_key: int) -> int:
    """pygame 키코드를 tcod KeySym으로 변환"""
    sym = _PG_TO_TCOD_KEY.get(pg_key)
    if sym is not None:
        return sym
    # 매핑되지 않은 키: 직접 코드 사용 (ASCII 범위)
    if 0 < pg_key < 128:
        return pg_key
    return 0


def _pg_mod_to_tcod_mod(pg_mod: int) -> int:
    """pygame 수정 키 상태를 tcod modifier로 변환"""
    mod = 0
    if pg_mod & pygame.KMOD_SHIFT:
        mod |= tcod.event.Modifier.SHIFT
    if pg_mod & pygame.KMOD_CTRL:
        mod |= tcod.event.Modifier.CTRL
    if pg_mod & pygame.KMOD_ALT:
        mod |= tcod.event.Modifier.ALT
    return mod


# ──────────────────────────────────────────────────────────────────
# tcod 이벤트 호환 래퍼
# ──────────────────────────────────────────────────────────────────

class PygameKeyDown(tcod.event.KeyDown):
    """pygame KEYDOWN → tcod.event.KeyDown 호환 객체

    tcod.event.KeyDown을 상속하여 isinstance() 체크 통과.
    """

    def __init__(self, pg_event: pygame.event.Event) -> None:
        self.type = "KEYDOWN"
        self.sym = _pg_key_to_tcod_sym(pg_event.key)
        self.mod = _pg_mod_to_tcod_mod(pg_event.mod)
        self.scancode = getattr(pg_event, 'scancode', 0)
        self.repeat = getattr(pg_event, 'repeat', False)
        # sdl_event 속성 (일부 코드에서 접근)
        self.sdl_event = None


class PygameKeyUp(tcod.event.KeyUp):
    """pygame KEYUP → tcod.event.KeyUp 호환"""

    def __init__(self, pg_event: pygame.event.Event) -> None:
        self.type = "KEYUP"
        self.sym = _pg_key_to_tcod_sym(pg_event.key)
        self.mod = _pg_mod_to_tcod_mod(pg_event.mod)
        self.scancode = getattr(pg_event, 'scancode', 0)
        self.sdl_event = None


class PygameQuit(tcod.event.Quit):
    """pygame QUIT → tcod.event.Quit 호환"""

    def __init__(self) -> None:
        self.type = "QUIT"
        self.sdl_event = None


class PygameTextInput(tcod.event.TextInput):
    """pygame TEXTINPUT → tcod.event.TextInput 호환"""

    def __init__(self, pg_event: pygame.event.Event) -> None:
        self.type = "TEXTINPUT"
        self.text = pg_event.text
        self.sdl_event = None


class PygameMouseMotion(tcod.event.MouseMotion):
    """pygame MOUSEMOTION → tcod.event.MouseMotion 호환"""

    def __init__(self, pg_event: pygame.event.Event, tile_size: tuple = (1, 1)) -> None:
        self.type = "MOUSEMOTION"
        self.pixel = pg_event.pos
        self.pixel_motion = pg_event.rel
        # 셀 좌표 변환 (tile_size가 주어진 경우)
        tw, th = tile_size
        self.tile = (pg_event.pos[0] // max(1, tw), pg_event.pos[1] // max(1, th))
        self.tile_motion = (pg_event.rel[0] // max(1, tw), pg_event.rel[1] // max(1, th))
        self.state = pg_event.buttons[0] if pg_event.buttons else 0
        self.sdl_event = None


class PygameMouseButtonDown(tcod.event.MouseButtonDown):
    """pygame MOUSEBUTTONDOWN → tcod.event.MouseButtonDown 호환"""

    def __init__(self, pg_event: pygame.event.Event, tile_size: tuple = (1, 1)) -> None:
        self.type = "MOUSEBUTTONDOWN"
        self.pixel = pg_event.pos
        self.button = pg_event.button
        tw, th = tile_size
        self.tile = (pg_event.pos[0] // max(1, tw), pg_event.pos[1] // max(1, th))
        self.sdl_event = None


class PygameMouseButtonUp(tcod.event.MouseButtonUp):
    """pygame MOUSEBUTTONUP → tcod.event.MouseButtonUp 호환"""

    def __init__(self, pg_event: pygame.event.Event, tile_size: tuple = (1, 1)) -> None:
        self.type = "MOUSEBUTTONUP"
        self.pixel = pg_event.pos
        self.button = pg_event.button
        tw, th = tile_size
        self.tile = (pg_event.pos[0] // max(1, tw), pg_event.pos[1] // max(1, th))
        self.sdl_event = None


class PygameWindowEvent(tcod.event.WindowEvent):
    """범용 창 이벤트"""

    def __init__(self, type_str: str = "WINDOWEVENT") -> None:
        self.type = type_str
        self.sdl_event = None


# ──────────────────────────────────────────────────────────────────
# 이벤트 변환 엔진
# ──────────────────────────────────────────────────────────────────

class EventAdapter:
    """pygame 이벤트를 tcod 이벤트로 변환하는 어댑터

    사용법:
        adapter = EventAdapter(tile_width, tile_height)
        for event in adapter.get():
            ...  # tcod 이벤트 처리 코드 그대로 사용
    """

    def __init__(self, tile_width: int = 10, tile_height: int = 13) -> None:
        self.tile_size = (tile_width, tile_height)

    def set_tile_size(self, tw: int, th: int) -> None:
        self.tile_size = (tw, th)

    def _convert(self, pg_event: pygame.event.Event) -> Optional[tcod.event.Event]:
        """pygame 이벤트 → tcod 호환 이벤트"""
        if pg_event.type == pygame.QUIT:
            return PygameQuit()
        elif pg_event.type == pygame.KEYDOWN:
            return PygameKeyDown(pg_event)
        elif pg_event.type == pygame.KEYUP:
            return PygameKeyUp(pg_event)
        elif pg_event.type == pygame.TEXTINPUT:
            return PygameTextInput(pg_event)
        elif pg_event.type == pygame.MOUSEMOTION:
            return PygameMouseMotion(pg_event, self.tile_size)
        elif pg_event.type == pygame.MOUSEBUTTONDOWN:
            return PygameMouseButtonDown(pg_event, self.tile_size)
        elif pg_event.type == pygame.MOUSEBUTTONUP:
            return PygameMouseButtonUp(pg_event, self.tile_size)
        elif pg_event.type == pygame.WINDOWRESIZED:
            evt = PygameWindowEvent("WINDOWRESIZED")
            evt.width = pg_event.x
            evt.height = pg_event.y
            return evt
        return None

    def get(self) -> Iterator[tcod.event.Event]:
        """pygame 이벤트를 tcod 이벤트로 변환하여 생성 (non-blocking)"""
        for pg_event in pygame.event.get():
            converted = self._convert(pg_event)
            if converted is not None:
                yield converted

    def wait(self, timeout: Optional[float] = None) -> Iterator[tcod.event.Event]:
        """pygame 이벤트를 대기하며 tcod 이벤트로 변환 (blocking)

        tcod.event.wait()와 유사하게 최소 1개 이벤트가 있을 때까지 대기.
        """
        # 이미 큐에 이벤트가 있으면 바로 반환
        events = list(self.get())
        if events:
            yield from events
            return

        # 이벤트 대기 (pygame.event.wait는 블로킹)
        if timeout is not None:
            # timeout이 지정된 경우 pygame.event.wait에 timeout 전달
            pg_event = pygame.event.wait(int(timeout * 1000))
        else:
            pg_event = pygame.event.wait()

        if pg_event.type != pygame.NOEVENT:
            converted = self._convert(pg_event)
            if converted is not None:
                yield converted

        # 대기 중 추가된 이벤트도 처리
        yield from self.get()


# ──────────────────────────────────────────────────────────────────
# tcod.event monkey-patch 함수
# ──────────────────────────────────────────────────────────────────

# 전역 어댑터 인스턴스 (install()에서 설정)
_global_adapter: Optional[EventAdapter] = None


def _pygame_event_wait(timeout: Optional[float] = None) -> Iterator[tcod.event.Event]:
    """tcod.event.wait() 대체"""
    if _global_adapter is not None:
        yield from _global_adapter.wait(timeout)


def _pygame_event_get() -> Iterator[tcod.event.Event]:
    """tcod.event.get() 대체"""
    if _global_adapter is not None:
        yield from _global_adapter.get()


def install(tile_width: int = 10, tile_height: int = 13) -> EventAdapter:
    """이벤트 어댑터를 설치하고 tcod.event.wait/get을 monkey-patch

    Args:
        tile_width: 타일 폭 (마우스 좌표 → 셀 좌표 변환용)
        tile_height: 타일 높이

    Returns:
        설치된 EventAdapter 인스턴스
    """
    global _global_adapter

    _global_adapter = EventAdapter(tile_width, tile_height)

    # monkey-patch tcod.event
    tcod.event.wait = _pygame_event_wait
    tcod.event.get = _pygame_event_get

    logger.info(
        f"이벤트 어댑터 설치 완료 - tcod.event.wait/get monkey-patched "
        f"(tile: {tile_width}x{tile_height})"
    )

    return _global_adapter


def uninstall() -> None:
    """monkey-patch 복원 (롤백용)"""
    global _global_adapter
    # tcod 원본 복원은 불가능하므로 어댑터만 제거
    _global_adapter = None
    logger.info("이벤트 어댑터 제거 완료")
