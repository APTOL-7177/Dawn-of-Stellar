from dataclasses import dataclass
from enum import Enum
from typing import Final, Mapping

from src.ui.visual_tokens import TokenName, VisualColor, get_color


class PanelVariant(str, Enum):
    DEFAULT = "default"
    RAISED = "raised"
    TOOLTIP = "tooltip"
    DANGER = "danger"


@dataclass(frozen=True, slots=True)
class GlyphSet:
    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str
    horizontal: str
    vertical: str
    separator_left: str
    separator_right: str
    title_left: str
    title_right: str
    selector: str
    drag: str


@dataclass(frozen=True, slots=True)
class PanelStyle:
    variant: PanelVariant
    foreground: VisualColor
    background: VisualColor
    border: VisualColor
    title: VisualColor
    focus: VisualColor


CONSOLE_GLYPHS: Final = GlyphSet(
    top_left="╔",
    top_right="╗",
    bottom_left="╚",
    bottom_right="╝",
    horizontal="═",
    vertical="║",
    separator_left="╠",
    separator_right="╣",
    title_left="╡",
    title_right="╞",
    selector="▶",
    drag="◆",
)
ASCII_GLYPHS: Final = GlyphSet(
    top_left="+",
    top_right="+",
    bottom_left="+",
    bottom_right="+",
    horizontal="-",
    vertical="|",
    separator_left="+",
    separator_right="+",
    title_left="[",
    title_right="]",
    selector=">",
    drag="#",
)

_PANEL_TOKENS: Final[Mapping[PanelVariant, tuple[TokenName, TokenName, TokenName, TokenName]]] = {
    PanelVariant.DEFAULT: ("text.primary", "surface.panel", "line.default", "accent.cyan"),
    PanelVariant.RAISED: ("text.primary", "surface.raised", "line.strong", "accent.amber"),
    PanelVariant.TOOLTIP: ("text.primary", "state.tooltip", "accent.amber", "accent.amber"),
    PanelVariant.DANGER: ("text.primary", "surface.raised", "threat.critical", "threat.critical"),
}


def glyphs_for(console_glyphs_supported: bool = True) -> GlyphSet:
    if console_glyphs_supported:
        return CONSOLE_GLYPHS
    return ASCII_GLYPHS


def get_panel_style(variant: PanelVariant = PanelVariant.DEFAULT) -> PanelStyle:
    foreground, background, border, title = _PANEL_TOKENS[variant]
    return PanelStyle(
        variant=variant,
        foreground=get_color(foreground),
        background=get_color(background),
        border=get_color(border),
        title=get_color(title),
        focus=get_color("state.focus"),
    )
