from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

from src.ui.input_handler import GameAction


class PointerEventKind(Enum):
    HOVER = "hover"
    CLICK = "click"
    WHEEL = "wheel"
    DRAG_START = "drag_start"
    DRAG_MOVE = "drag_move"
    DRAG_END = "drag_end"

    def at(
        self,
        *,
        tile: tuple[int, int],
        pixel: tuple[int, int],
        button: PointerButton | None = None,
        wheel_delta: int = 0,
        drag_origin: PointerPosition | None = None,
    ) -> PointerEvent:
        return PointerEvent(
            kind=self,
            position=PointerPosition(tile=tile, pixel=pixel),
            button=button,
            wheel_delta=wheel_delta,
            drag_origin=drag_origin,
        )


class PointerButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PointerPosition:
    tile: tuple[int, int]
    pixel: tuple[int, int]


@dataclass(frozen=True, slots=True)
class PointerEvent:
    kind: PointerEventKind
    position: PointerPosition
    button: PointerButton | None = None
    wheel_delta: int = 0
    drag_origin: PointerPosition | None = None


@dataclass(frozen=True, slots=True)
class PointerRegion:
    region_id: str
    x: int
    y: int
    width: int
    height: int
    command: GameAction | None = None
    tooltip: str = ""
    enabled: bool = True

    def contains(self, position: PointerPosition) -> bool:
        tile_x, tile_y = position.tile
        return self.x <= tile_x < self.x + self.width and self.y <= tile_y < self.y + self.height


@dataclass(frozen=True, slots=True)
class PointerDispatchResult:
    event: PointerEvent
    action: GameAction | None = None
    value: str | bool | int | float | None = None
    hovered_region_id: str | None = None
    tooltip: str | None = None

    def with_value(self, value: str | bool | int | float | None) -> PointerDispatchResult:
        return replace(self, value=value)


class RawPointerEvent(Protocol):
    @property
    def type(self) -> str: ...

    @property
    def tile(self) -> tuple[int, int]: ...

    @property
    def pixel(self) -> tuple[int, int]: ...

    @property
    def button(self) -> int: ...

    @property
    def state(self) -> int: ...

    @property
    def x(self) -> int: ...

    @property
    def y(self) -> int: ...

    @property
    def wheel_y(self) -> int: ...


class PointerNormalizer:
    def __init__(self) -> None:
        self._pressed_button: PointerButton | None = None
        self._drag_origin: PointerPosition | None = None
        self._dragging = False

    def normalize(self, event: RawPointerEvent) -> PointerEvent | None:
        event_type = event.type.upper()
        match event_type:
            case "MOUSEMOTION":
                return self._normalize_motion(event)
            case "MOUSEBUTTONDOWN":
                return self._normalize_button_down(event)
            case "MOUSEBUTTONUP":
                return self._normalize_button_up(event)
            case "MOUSEWHEEL":
                return self._normalize_wheel(event)
            case _:
                return None

    def _normalize_motion(self, event: RawPointerEvent) -> PointerEvent:
        positioned = _require_position(event)
        position = _position_from(positioned)
        motion = _motion_state(event)
        if self._pressed_button is not None and motion != 0:
            drag_origin = self._drag_origin or position
            if not self._dragging:
                self._dragging = True
                return PointerEvent(
                    kind=PointerEventKind.DRAG_START,
                    position=position,
                    button=self._pressed_button,
                    drag_origin=drag_origin,
                )
            return PointerEvent(
                kind=PointerEventKind.DRAG_MOVE,
                position=position,
                button=self._pressed_button,
                drag_origin=drag_origin,
            )
        return PointerEvent(kind=PointerEventKind.HOVER, position=position)

    def _normalize_button_down(self, event: RawPointerEvent) -> PointerEvent:
        button_event = _require_button(event)
        button = _pointer_button(button_event.button)
        position = _position_from(button_event)
        self._pressed_button = button
        self._drag_origin = position
        self._dragging = False
        return PointerEvent(kind=PointerEventKind.CLICK, position=position, button=button)

    def _normalize_button_up(self, event: RawPointerEvent) -> PointerEvent | None:
        button_event = _require_button(event)
        button = _pointer_button(button_event.button)
        position = _position_from(button_event)
        drag_origin = self._drag_origin
        was_dragging = self._dragging
        self._pressed_button = None
        self._drag_origin = None
        self._dragging = False
        if not was_dragging:
            return None
        return PointerEvent(
            kind=PointerEventKind.DRAG_END,
            position=position,
            button=button,
            drag_origin=drag_origin,
        )

    def _normalize_wheel(self, event: RawPointerEvent) -> PointerEvent:
        position = _position_from_optional(event)
        return PointerEvent(
            kind=PointerEventKind.WHEEL,
            position=position,
            wheel_delta=_wheel_delta(event),
        )


class PointerDispatcher:
    def __init__(self, regions: tuple[PointerRegion, ...] = ()) -> None:
        self._regions = regions

    def dispatch(self, event: PointerEvent) -> PointerDispatchResult:
        region = self.region_at(event.position)
        match event.kind:
            case PointerEventKind.HOVER:
                return PointerDispatchResult(
                    event=event,
                    hovered_region_id=region.region_id if region else None,
                    tooltip=region.tooltip if region and region.tooltip else None,
                )
            case PointerEventKind.CLICK:
                return PointerDispatchResult(event=event, action=_click_action(event, region))
            case PointerEventKind.WHEEL:
                return PointerDispatchResult(event=event, action=_wheel_action(event.wheel_delta))
            case PointerEventKind.DRAG_START | PointerEventKind.DRAG_MOVE | PointerEventKind.DRAG_END:
                return PointerDispatchResult(
                    event=event,
                    hovered_region_id=region.region_id if region else None,
                )
            case unreachable:
                raise AssertionError(f"unreachable pointer event kind: {unreachable!r}")

    def region_at(self, position: PointerPosition) -> PointerRegion | None:
        for region in self._regions:
            if region.enabled and region.contains(position):
                return region
        return None


def _click_action(event: PointerEvent, region: PointerRegion | None) -> GameAction | None:
    match event.button:
        case PointerButton.LEFT:
            return region.command if region and region.command else GameAction.CONFIRM
        case PointerButton.RIGHT:
            return GameAction.CANCEL
        case PointerButton.MIDDLE:
            return GameAction.MENU
        case PointerButton.UNKNOWN | None:
            return None
        case unreachable:
            raise AssertionError(f"unreachable pointer button: {unreachable!r}")


def _wheel_action(delta: int) -> GameAction | None:
    if delta > 0:
        return GameAction.MOVE_UP
    if delta < 0:
        return GameAction.MOVE_DOWN
    return None


def _pointer_button(button: int) -> PointerButton:
    match button:
        case 1:
            return PointerButton.LEFT
        case 2:
            return PointerButton.MIDDLE
        case 3:
            return PointerButton.RIGHT
        case 4 | 5:
            return PointerButton.UNKNOWN
        case _:
            return PointerButton.UNKNOWN


def _position_from(event: RawPointerEvent) -> PointerPosition:
    return PointerPosition(tile=event.tile, pixel=event.pixel)


def _position_from_optional(event: RawPointerEvent) -> PointerPosition:
    if hasattr(event, "tile") and hasattr(event, "pixel"):
        return PointerPosition(tile=event.tile, pixel=event.pixel)
    return PointerPosition(tile=(0, 0), pixel=(0, 0))


def _require_position(event: RawPointerEvent) -> RawPointerEvent:
    if hasattr(event, "tile") and hasattr(event, "pixel"):
        return event
    raise AttributeError("pointer event is missing tile/pixel coordinates")


def _require_button(event: RawPointerEvent) -> RawPointerEvent:
    if hasattr(event, "button") and hasattr(event, "tile") and hasattr(event, "pixel"):
        return event
    raise AttributeError("pointer button event is missing button/tile/pixel data")


def _motion_state(event: RawPointerEvent) -> int:
    if hasattr(event, "state"):
        return int(event.state)
    return 0


def _wheel_delta(event: RawPointerEvent) -> int:
    if hasattr(event, "wheel_y"):
        return int(event.wheel_y)
    if hasattr(event, "y"):
        return int(event.y)
    if hasattr(event, "button"):
        match int(event.button):
            case 4:
                return 1
            case 5:
                return -1
            case _:
                return 0
    return 0
