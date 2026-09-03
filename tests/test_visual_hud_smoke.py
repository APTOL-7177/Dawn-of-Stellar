"""TCOD/텍스트 콘솔 스모크 — HUD 슬라이스가 TCOD 폴백에서도 동작하는지 검증.

Raylib 전용 기능(pyray)은 호출하지 않고, 토큰 결정 로직과
TCOD 콘솔 게이지 렌더링만 검증한다 (TCOD 폴백 불변 원칙).
"""

import tcod

from src.ui.visual_hud import (
    build_hud_frame,
    feedback_tokens,
    gauge_colors,
    motion_durations,
    threat_status_token,
)
from src.ui.visual_tokens import get_color


def _make_console(width: int = 80, height: int = 50) -> tcod.console.Console:
    return tcod.console.Console(width, height)


def test_smoke_tcod_render_bar_when_called_then_writes_to_console() -> None:
    from src.ui.gauge_renderer import GaugeRenderer

    console = _make_console()
    # 토큰 기반 그라디언트 게이지 (타일셋 없는 폴백 경로 포함)
    GaugeRenderer.render_bar(console, 2, 2, 20, 55, 100)
    GaugeRenderer.render_bar(console, 2, 4, 20, 10, 100)
    assert console.bg[2, 2].tolist() != [0, 0, 0] or console.bg[2, 4].tolist() != [0, 0, 0]


def test_smoke_tcod_render_atb_when_called_then_writes_to_console() -> None:
    from src.ui.gauge_renderer import GaugeRenderer

    console = _make_console()
    GaugeRenderer.render_atb_gauge(console, 2, 6, 20, 70, 100, 100)
    GaugeRenderer.render_atb_gauge(console, 2, 8, 20, 20, 100, 100)


def test_smoke_gauge_colors_when_all_kinds_then_tokens_resolve() -> None:
    for kind in ("hp", "mp", "brv", "atb"):
        fg, bg = gauge_colors(kind, ratio=0.42)
        assert fg.rgb != bg.rgb or kind == "atb"


def test_smoke_feedback_and_threat_tokens_when_resolved_then_valid_colors() -> None:
    for state in ("idle", "hover", "selected", "disabled"):
        fg, bg = feedback_tokens(state)  # type: ignore[arg-type]
        assert len(fg.rgb) == 3 and len(bg.rgb) == 3
    for severity in (0.0, 0.3, 0.6, 0.9):
        token = threat_status_token(severity)
        assert len(get_color(token).rgb) == 3


def test_smoke_hud_frame_when_console_glyphs_then_box_drawing() -> None:
    frame = build_hud_frame(width=30, title="BRV", console_glyphs_supported=True)
    assert frame.lines[0].startswith("╔")
    assert "BRV" in frame.lines[0]


def test_smoke_motion_when_reduced_then_zero() -> None:
    assert all(v == 0.0 for v in motion_durations(reduced_motion=True).values())
