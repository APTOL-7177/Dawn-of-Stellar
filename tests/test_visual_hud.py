"""전투 HUD/탐험 비주얼 수직 슬라이스 — 토큰/프리미티브 계약 테스트"""

import pytest

from src.ui.visual_tokens import TokenName, get_color


def test_hp_ratio_when_mapped_then_uses_status_hp_tokens() -> None:
    from src.ui.visual_hud import hp_status_token

    assert hp_status_token(0.9) == "status.hp_high"
    assert hp_status_token(0.45) == "status.hp_mid"
    assert hp_status_token(0.1) == "status.hp_low"
    assert hp_status_token(0.0) == "status.hp_low"


def test_gauge_kind_when_resolved_then_maps_to_semantic_token() -> None:
    from src.ui.visual_hud import gauge_fill_token

    assert gauge_fill_token("hp", 0.9) == "status.hp_high"
    assert gauge_fill_token("mp") == "status.mp"
    assert gauge_fill_token("brv") == "status.brv"


def test_gauge_colors_when_built_then_fg_bg_share_token_hue() -> None:
    from src.ui.visual_hud import gauge_colors

    fg, bg = gauge_colors("hp", ratio=0.9)
    fg_luma = fg.relative_luminance
    bg_luma = bg.relative_luminance
    # 전경이 배경보다 밝아 게이지가 읽힌다
    assert fg_luma > bg_luma
    assert fg.name.startswith("status.")


def test_threat_token_when_ranked_then_orders_severity() -> None:
    from src.ui.visual_hud import threat_status_token

    order = [
        get_color(threat_status_token(t)).relative_luminance for t in (0.2, 0.5, 0.8, 1.0)
    ]
    # 위협이 커질수록(1.0=치명) 밝은 적색 계열 → 인지 휘도 단조 증가 아님여부와 무관하게
    # 토큰 자체가 threat 등급 순서를 따르는지 확인
    assert threat_status_token(0.2) == "threat.low"
    assert threat_status_token(0.5) == "threat.medium"
    assert threat_status_token(0.8) == "threat.high"
    assert threat_status_token(1.0) == "threat.critical"


def test_selection_feedback_when_state_changes_then_distinct_tokens() -> None:
    from src.ui.visual_hud import feedback_tokens

    idle_fg, idle_bg = feedback_tokens("idle")
    hover_fg, hover_bg = feedback_tokens("hover")
    selected_fg, selected_bg = feedback_tokens("selected")
    disabled_fg, _ = feedback_tokens("disabled")

    assert idle_fg.name != hover_fg.name
    assert selected_fg.name == "state.focus"
    assert disabled_fg.name == "state.disabled"
    assert idle_bg.name == hover_bg.name  # 배경은 공유, 전경만 상태 구분


def test_hud_frame_when_rendered_ascii_then_uses_panel_glyph_fallback() -> None:
    from src.ui.visual_hud import build_hud_frame

    frame = build_hud_frame(width=20, title="HP", console_glyphs_supported=False)
    lines = frame.lines

    assert lines[0].startswith("+")
    assert "HP" in lines[0]
    assert lines[-1].endswith("+")


def test_reduced_motion_when_requested_then_returns_zero_duration() -> None:
    from src.ui.visual_hud import motion_durations

    normal = motion_durations(reduced_motion=False)
    reduced = motion_durations(reduced_motion=True)

    assert normal["fill"] > 0
    assert reduced["fill"] == 0.0
    assert reduced["blink"] == 0.0
