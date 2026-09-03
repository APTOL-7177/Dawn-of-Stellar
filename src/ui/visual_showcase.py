from dataclasses import dataclass
from typing import Final

from src.ui.visual_primitives import PanelVariant, glyphs_for, get_panel_style
from src.ui.visual_tokens import InteractionState, TokenName, raylib_color


@dataclass(frozen=True, slots=True)
class ShowcaseRow:
    label: str
    token: TokenName
    rgba: tuple[int, int, int, int]


SHOWCASE_STATES: Final = (
    ("default", "state.default"),
    ("hover", "state.hover"),
    ("active", "state.active"),
    ("focus", "state.focus"),
    ("disabled", "state.disabled"),
    ("tooltip", "state.tooltip"),
    ("drag", "state.drag"),
)


def build_showcase_rows(alpha: int = 255) -> tuple[ShowcaseRow, ...]:
    return tuple(
        ShowcaseRow(label=label, token=token, rgba=raylib_color(token, alpha=alpha))
        for label, token in SHOWCASE_STATES
    )


def build_visual_showcase_lines(console_glyphs_supported: bool = True) -> tuple[str, ...]:
    glyphs = glyphs_for(console_glyphs_supported=console_glyphs_supported)
    width = 42
    top = f"{glyphs.top_left}{glyphs.horizontal * (width - 2)}{glyphs.top_right}"
    bottom = f"{glyphs.bottom_left}{glyphs.horizontal * (width - 2)}{glyphs.bottom_right}"
    title = f"{glyphs.vertical} VISUAL TOKENS: COMMAND LATTICE        {glyphs.vertical}"
    rows = tuple(
        f"{glyphs.vertical} {row.label.upper():<8} {row.token:<16} {row.rgba!s:<11} {glyphs.vertical}"
        for row in build_showcase_rows()
    )
    raised = get_panel_style(PanelVariant.RAISED)
    footer = f"{glyphs.vertical} PANEL {raised.variant.value:<7} border={raised.border.name:<12} {glyphs.vertical}"
    return (top, title, *rows, footer, bottom)


def interaction_states() -> tuple[str, ...]:
    return tuple(state.value for state in InteractionState)
