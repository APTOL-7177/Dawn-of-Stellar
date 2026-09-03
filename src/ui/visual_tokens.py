from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Final, Literal, Mapping, TypeAlias

Rgb: TypeAlias = tuple[int, int, int]
Rgba: TypeAlias = tuple[int, int, int, int]
TokenName: TypeAlias = Literal[
    "surface.base",
    "surface.panel",
    "surface.raised",
    "surface.sunken",
    "surface.grid",
    "text.primary",
    "text.secondary",
    "text.muted",
    "text.inverse",
    "line.subtle",
    "line.default",
    "line.strong",
    "accent.cyan",
    "accent.amber",
    "accent.blue",
    "accent.violet",
    "state.default",
    "state.hover",
    "state.active",
    "state.focus",
    "state.disabled",
    "state.tooltip",
    "state.drag",
    "status.hp_high",
    "status.hp_mid",
    "status.hp_low",
    "status.mp",
    "status.brv",
    "status.success",
    "status.warning",
    "status.error",
    "status.info",
    "rarity.common",
    "rarity.uncommon",
    "rarity.rare",
    "rarity.epic",
    "rarity.legendary",
    "threat.low",
    "threat.medium",
    "threat.high",
    "threat.critical",
]


class InteractionState(str, Enum):
    DEFAULT = "default"
    HOVER = "hover"
    ACTIVE = "active"
    FOCUS = "focus"
    DISABLED = "disabled"
    TOOLTIP = "tooltip"
    DRAG = "drag"


@dataclass(frozen=True, slots=True)
class VisualColor:
    name: TokenName
    rgb: Rgb

    def rgba(self, alpha: int = 255) -> Rgba:
        bounded_alpha = max(0, min(255, alpha))
        return (*self.rgb, bounded_alpha)

    @property
    def relative_luminance(self) -> float:
        red, green, blue = (component / 255.0 for component in self.rgb)
        return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


VISUAL_PALETTE: Final[Mapping[TokenName, VisualColor]] = MappingProxyType(
    {
        "surface.base": VisualColor("surface.base", (5, 7, 8)),
        "surface.panel": VisualColor("surface.panel", (11, 17, 20)),
        "surface.raised": VisualColor("surface.raised", (16, 26, 30)),
        "surface.sunken": VisualColor("surface.sunken", (3, 5, 6)),
        "surface.grid": VisualColor("surface.grid", (22, 36, 42)),
        "text.primary": VisualColor("text.primary", (216, 242, 232)),
        "text.secondary": VisualColor("text.secondary", (142, 178, 170)),
        "text.muted": VisualColor("text.muted", (81, 106, 102)),
        "text.inverse": VisualColor("text.inverse", (3, 17, 15)),
        "line.subtle": VisualColor("line.subtle", (32, 51, 58)),
        "line.default": VisualColor("line.default", (58, 104, 112)),
        "line.strong": VisualColor("line.strong", (113, 212, 196)),
        "accent.cyan": VisualColor("accent.cyan", (78, 244, 210)),
        "accent.amber": VisualColor("accent.amber", (242, 184, 75)),
        "accent.blue": VisualColor("accent.blue", (75, 158, 255)),
        "accent.violet": VisualColor("accent.violet", (183, 131, 255)),
        "state.default": VisualColor("state.default", (142, 178, 170)),
        "state.hover": VisualColor("state.hover", (18, 48, 55)),
        "state.active": VisualColor("state.active", (25, 75, 75)),
        "state.focus": VisualColor("state.focus", (113, 212, 196)),
        "state.disabled": VisualColor("state.disabled", (52, 71, 68)),
        "state.tooltip": VisualColor("state.tooltip", (8, 19, 22)),
        "state.drag": VisualColor("state.drag", (39, 57, 23)),
        "status.hp_high": VisualColor("status.hp_high", (98, 230, 107)),
        "status.hp_mid": VisualColor("status.hp_mid", (215, 214, 90)),
        "status.hp_low": VisualColor("status.hp_low", (242, 93, 75)),
        "status.mp": VisualColor("status.mp", (75, 158, 255)),
        "status.brv": VisualColor("status.brv", (78, 244, 210)),
        "status.success": VisualColor("status.success", (98, 230, 107)),
        "status.warning": VisualColor("status.warning", (242, 184, 75)),
        "status.error": VisualColor("status.error", (242, 93, 75)),
        "status.info": VisualColor("status.info", (75, 158, 255)),
        "rarity.common": VisualColor("rarity.common", (142, 178, 170)),
        "rarity.uncommon": VisualColor("rarity.uncommon", (98, 230, 107)),
        "rarity.rare": VisualColor("rarity.rare", (75, 158, 255)),
        "rarity.epic": VisualColor("rarity.epic", (183, 131, 255)),
        "rarity.legendary": VisualColor("rarity.legendary", (242, 184, 75)),
        "threat.low": VisualColor("threat.low", (98, 230, 107)),
        "threat.medium": VisualColor("threat.medium", (215, 214, 90)),
        "threat.high": VisualColor("threat.high", (242, 141, 75)),
        "threat.critical": VisualColor("threat.critical", (255, 59, 59)),
    }
)


def get_color(name: TokenName) -> VisualColor:
    return VISUAL_PALETTE[name]


def rgb(name: TokenName) -> Rgb:
    return get_color(name).rgb


def raylib_color(name: TokenName, alpha: int = 255) -> Rgba:
    return get_color(name).rgba(alpha)
