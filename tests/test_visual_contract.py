from src.ui.visual_primitives import PanelVariant, get_panel_style, glyphs_for
from src.ui.visual_showcase import build_showcase_rows, build_visual_showcase_lines
from src.ui.visual_tokens import InteractionState, TokenName, get_color, raylib_color


def test_raylib_color_when_alpha_override_then_returns_rgba_tuple() -> None:
    token: TokenName = "accent.cyan"

    rgba = raylib_color(token, alpha=192)

    assert rgba == (78, 244, 210, 192)


def test_interaction_state_when_resolved_then_uses_high_contrast_backgrounds() -> None:
    hover = get_color("state.hover")
    focus = get_color("state.focus")

    hover_luma = hover.relative_luminance
    focus_luma = focus.relative_luminance

    assert hover_luma < focus_luma
    assert InteractionState.FOCUS.value == "focus"


def test_glyphs_for_when_ascii_requested_then_box_drawing_has_console_fallback() -> None:
    glyphs = glyphs_for(console_glyphs_supported=False)

    assert glyphs.top_left == "+"
    assert glyphs.horizontal == "-"
    assert glyphs.vertical == "|"
    assert glyphs.selector == ">"


def test_panel_style_when_tooltip_variant_then_uses_tooltip_surface_and_strong_line() -> None:
    style = get_panel_style(PanelVariant.TOOLTIP)

    assert style.background.name == "state.tooltip"
    assert style.border.name in {"line.strong", "accent.amber"}
    assert style.title.name == "accent.amber"


def test_showcase_rows_when_built_then_cover_required_interaction_states() -> None:
    rows = build_showcase_rows(alpha=224)

    assert tuple(row.label for row in rows) == tuple(state.value for state in InteractionState)
    assert all(row.rgba[3] == 224 for row in rows)


def test_visual_showcase_lines_when_ascii_requested_then_render_panel_evidence() -> None:
    lines = build_visual_showcase_lines(console_glyphs_supported=False)

    assert lines[0].startswith("+-")
    assert "FOCUS" in "\n".join(lines)
    assert lines[-1].endswith("+")
