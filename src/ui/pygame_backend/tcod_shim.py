"""
tcod 모듈 심(shim) - tcod 완전 제거 시 import tcod를 만족

84개 파일의 `import tcod`를 변경 없이 만족시키기 위한 최소 호환 심.
Phase 5에서 sys.modules['tcod'] = tcod_shim 으로 설치.

현재는 tcod가 설치되어 있으므로 이 모듈은 대기 상태.
tcod 제거 시 __init__.py에서 활성화.
"""

import sys
import types
from enum import IntEnum
from typing import Any, Iterator, Optional


# ──────────────────────────────────────────────────────────────────
# tcod.event 심
# ──────────────────────────────────────────────────────────────────

class KeySym(IntEnum):
    """tcod.event.KeySym 호환 키 상수"""
    # 특수 키
    ESCAPE = 27
    RETURN = 13
    KP_ENTER = 271
    TAB = 9
    BACKSPACE = 8
    DELETE = 127
    INSERT = 277
    SPACE = 32

    # 방향키
    UP = 273
    DOWN = 274
    LEFT = 276
    RIGHT = 275

    # 텐키
    KP_0 = 256
    KP_1 = 257
    KP_2 = 258
    KP_3 = 259
    KP_4 = 260
    KP_5 = 261
    KP_6 = 262
    KP_7 = 263
    KP_8 = 264
    KP_9 = 265

    # 페이지/홈/엔드
    PAGEUP = 280
    PAGEDOWN = 281
    HOME = 278
    END = 279

    # F키
    F1 = 282
    F2 = 283
    F3 = 284
    F4 = 285
    F5 = 286
    F6 = 287
    F7 = 288
    F8 = 289
    F9 = 290
    F10 = 291
    F11 = 292
    F12 = 293

    # 수정 키
    LSHIFT = 304
    RSHIFT = 303
    LCTRL = 306
    RCTRL = 305
    LALT = 308
    RALT = 307

    # 기호
    PERIOD = ord('.')
    COMMA = ord(',')
    SLASH = ord('/')
    BACKSLASH = ord('\\')
    SEMICOLON = ord(';')
    MINUS = ord('-')
    EQUALS = ord('=')
    LEFTBRACKET = ord('[')
    RIGHTBRACKET = ord(']')
    GRAVE = ord('`')
    APOSTROPHE = ord("'")

    # 영문 (a-z)
    a = ord('a')
    b = ord('b')
    c = ord('c')
    d = ord('d')
    e = ord('e')
    f = ord('f')
    g = ord('g')
    h = ord('h')
    i = ord('i')
    j = ord('j')
    k = ord('k')
    l = ord('l')
    m = ord('m')
    n = ord('n')
    o = ord('o')
    p = ord('p')
    q = ord('q')
    r = ord('r')
    s = ord('s')
    t = ord('t')
    u = ord('u')
    v = ord('v')
    w = ord('w')
    x = ord('x')
    y = ord('y')
    z = ord('z')

    # 숫자
    N0 = ord('0')
    N1 = ord('1')
    N2 = ord('2')
    N3 = ord('3')
    N4 = ord('4')
    N5 = ord('5')
    N6 = ord('6')
    N7 = ord('7')
    N8 = ord('8')
    N9 = ord('9')


class Modifier(IntEnum):
    """tcod.event.Modifier 호환"""
    NONE = 0
    SHIFT = 0x0001
    CTRL = 0x0040
    ALT = 0x0100


# ── 이벤트 기본 클래스 ──

class Event:
    """tcod.event.Event 기본"""
    type: str = ""
    sdl_event: Any = None


class Quit(Event):
    type = "QUIT"


class KeyDown(Event):
    type = "KEYDOWN"
    def __init__(self):
        self.sym = 0
        self.mod = 0
        self.scancode = 0
        self.repeat = False


class KeyUp(Event):
    type = "KEYUP"
    def __init__(self):
        self.sym = 0
        self.mod = 0
        self.scancode = 0


class TextInput(Event):
    type = "TEXTINPUT"
    def __init__(self):
        self.text = ""


class MouseMotion(Event):
    type = "MOUSEMOTION"
    def __init__(self):
        self.pixel = (0, 0)
        self.pixel_motion = (0, 0)
        self.tile = (0, 0)
        self.tile_motion = (0, 0)
        self.state = 0


class MouseButtonDown(Event):
    type = "MOUSEBUTTONDOWN"
    def __init__(self):
        self.pixel = (0, 0)
        self.tile = (0, 0)
        self.button = 0


class MouseButtonUp(Event):
    type = "MOUSEBUTTONUP"
    def __init__(self):
        self.pixel = (0, 0)
        self.tile = (0, 0)
        self.button = 0


class WindowEvent(Event):
    type = "WINDOWEVENT"


class WindowResized(WindowEvent):
    type = "WINDOWRESIZED"
    def __init__(self):
        self.width = 0
        self.height = 0


class EventDispatch:
    """tcod.event.EventDispatch 호환 기본 클래스

    InputHandler가 이 클래스를 상속합니다.
    """

    def dispatch(self, event: Event) -> Any:
        """이벤트를 적절한 핸들러로 분배"""
        if isinstance(event, Quit):
            return self.ev_quit(event)
        elif isinstance(event, KeyDown):
            return self.ev_keydown(event)
        elif isinstance(event, KeyUp):
            return self.ev_keyup(event)
        elif isinstance(event, MouseMotion):
            return self.ev_mousemotion(event)
        elif isinstance(event, MouseButtonDown):
            return self.ev_mousebuttondown(event)
        elif isinstance(event, MouseButtonUp):
            return self.ev_mousebuttonup(event)
        elif isinstance(event, TextInput):
            return self.ev_textinput(event)
        return None

    def ev_quit(self, event: Quit) -> Any:
        return None

    def ev_keydown(self, event: KeyDown) -> Any:
        return None

    def ev_keyup(self, event: KeyUp) -> Any:
        return None

    def ev_mousemotion(self, event: MouseMotion) -> Any:
        return None

    def ev_mousebuttondown(self, event: MouseButtonDown) -> Any:
        return None

    def ev_mousebuttonup(self, event: MouseButtonUp) -> Any:
        return None

    def ev_textinput(self, event: TextInput) -> Any:
        return None


def wait(timeout: Optional[float] = None) -> Iterator[Event]:
    """tcod.event.wait 폴백 (pygame 어댑터가 대체)"""
    return iter([])


def get() -> Iterator[Event]:
    """tcod.event.get 폴백 (pygame 어댑터가 대체)"""
    return iter([])


# ──────────────────────────────────────────────────────────────────
# tcod.console 심
# ──────────────────────────────────────────────────────────────────

class _ConsoleShim:
    """tcod.console.Console 심 — PygameConsole로 대체됨"""
    Console = None  # PygameConsole이 설정됨


# ──────────────────────────────────────────────────────────────────
# tcod.context 심
# ──────────────────────────────────────────────────────────────────

RENDERER_SDL2 = 0
RENDERER_OPENGL = 1
RENDERER_OPENGL2 = 2


# ──────────────────────────────────────────────────────────────────
# tcod.tileset 심
# ──────────────────────────────────────────────────────────────────

class _TilesetShim:
    """최소 Tileset 심"""

    def __init__(self, tile_width: int = 10, tile_height: int = 13):
        self.tile_width = tile_width
        self.tile_height = tile_height

    def set_tile(self, codepoint: int, tile: Any) -> None:
        pass  # PUA 타일은 gauge_tiles.py가 처리


def _set_default(tileset: Any) -> None:
    pass


def _load_bdf(path: str) -> _TilesetShim:
    return _TilesetShim()


def _load_truetype_font(path: str, w: int, h: int) -> _TilesetShim:
    return _TilesetShim(w, h)


# ──────────────────────────────────────────────────────────────────
# libtcodpy 심
# ──────────────────────────────────────────────────────────────────

# 배경 블렌드 상수
BKGND_NONE = 0
BKGND_SET = 1
BKGND_MULTIPLY = 2
BKGND_LIGHTEN = 3
BKGND_DARKEN = 4
BKGND_SCREEN = 5
BKGND_COLOR_DODGE = 6
BKGND_COLOR_BURN = 7
BKGND_ADD = 8
BKGND_ADDA = 9
BKGND_BURN = 10
BKGND_OVERLAY = 11
BKGND_ALPH = 12
BKGND_DEFAULT = 13


# ──────────────────────────────────────────────────────────────────
# 모듈 조립 및 설치
# ──────────────────────────────────────────────────────────────────

def install_shim() -> None:
    """tcod 심을 sys.modules에 설치

    호출 후 `import tcod`, `import tcod.event` 등이
    실제 tcod 없이 이 심 모듈을 반환합니다.
    """
    # 메인 tcod 모듈
    tcod_mod = types.ModuleType("tcod")

    # tcod.event
    event_mod = types.ModuleType("tcod.event")
    event_mod.KeySym = KeySym
    event_mod.Modifier = Modifier
    event_mod.Event = Event
    event_mod.Quit = Quit
    event_mod.KeyDown = KeyDown
    event_mod.KeyUp = KeyUp
    event_mod.TextInput = TextInput
    event_mod.MouseMotion = MouseMotion
    event_mod.MouseButtonDown = MouseButtonDown
    event_mod.MouseButtonUp = MouseButtonUp
    event_mod.WindowEvent = WindowEvent
    event_mod.WindowResized = WindowResized
    event_mod.EventDispatch = EventDispatch
    event_mod.wait = wait
    event_mod.get = get
    tcod_mod.event = event_mod

    # tcod.console
    console_mod = types.ModuleType("tcod.console")
    from src.ui.pygame_backend.pygame_console import PygameConsole
    console_mod.Console = PygameConsole
    tcod_mod.console = console_mod

    # tcod.context
    context_mod = types.ModuleType("tcod.context")
    context_mod.RENDERER_SDL2 = RENDERER_SDL2
    context_mod.RENDERER_OPENGL = RENDERER_OPENGL
    context_mod.RENDERER_OPENGL2 = RENDERER_OPENGL2
    context_mod.new = lambda **kwargs: None  # PygameContext가 대체
    tcod_mod.context = context_mod

    # tcod.tileset
    tileset_mod = types.ModuleType("tcod.tileset")
    tileset_mod.Tileset = _TilesetShim
    tileset_mod.set_default = _set_default
    tileset_mod.load_bdf = _load_bdf
    tileset_mod.load_truetype_font = _load_truetype_font
    tcod_mod.tileset = tileset_mod

    # tcod.libtcodpy (= tcod 루트에도 상수 노출)
    libtcodpy_mod = types.ModuleType("tcod.libtcodpy")
    for name in dir():
        if name.startswith('BKGND_'):
            setattr(libtcodpy_mod, name, globals()[name])
    tcod_mod.libtcodpy = libtcodpy_mod

    # tcod.lib (빈 심)
    lib_mod = types.ModuleType("tcod.lib")
    tcod_mod.lib = lib_mod

    # sys.modules 등록
    sys.modules["tcod"] = tcod_mod
    sys.modules["tcod.event"] = event_mod
    sys.modules["tcod.console"] = console_mod
    sys.modules["tcod.context"] = context_mod
    sys.modules["tcod.tileset"] = tileset_mod
    sys.modules["tcod.libtcodpy"] = libtcodpy_mod
    sys.modules["tcod.lib"] = lib_mod
