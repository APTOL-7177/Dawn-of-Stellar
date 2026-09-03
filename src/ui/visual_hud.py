"""전투 HUD/탐험 비주얼 슬라이스 — semantic 토큰 단일 진실공급원

visual_tokens의 토큰과 visual_primitives의 글리프만 사용해
HP/MP/BRV/ATB 게이지 색, 상태/피격/선택 피드백, HUD 프레임,
reduced-motion 지속시간을 결정한다. 하드코딩 RGB는 여기 두지 않는다.
"""

from dataclasses import dataclass
from typing import Final, Literal

from src.ui.visual_primitives import glyphs_for
from src.ui.visual_tokens import TokenName, VisualColor, get_color

GaugeKind = Literal["hp", "mp", "brv", "atb"]
FeedbackState = Literal["idle", "hover", "selected", "disabled"]

# 게이지 채움 강도 비율 → 상태 토큰 임계값 (기존 gauge_renderer의 60%/30% 경계 유지)
_HP_MID_THRESHOLD: Final = 0.3
_HP_HIGH_THRESHOLD: Final = 0.6

_FEEDBACK_TOKENS: Final[dict[str, tuple[TokenName, TokenName]]] = {
    "idle": ("text.secondary", "surface.panel"),
    "hover": ("state.focus", "surface.panel"),
    "selected": ("state.focus", "state.active"),
    "disabled": ("state.disabled", "surface.panel"),
}

_NORMAL_MOTION: Final[dict[str, float]] = {
    "fill": 0.8,
    "damage_trail": 0.3,
    "heal_flash": 0.6,
    "blink": 0.5,
}


def hp_status_token(ratio: float) -> TokenName:
    """HP 비율(0~1)을 status.* 토큰으로 사상."""
    if ratio <= _HP_MID_THRESHOLD:
        return "status.hp_low"
    if ratio <= _HP_HIGH_THRESHOLD:
        return "status.hp_mid"
    return "status.hp_high"


def gauge_fill_token(kind: GaugeKind, ratio: float = 1.0) -> TokenName:
    """게이지 종류별 semantic 채움 토큰."""
    if kind == "hp":
        return hp_status_token(ratio)
    if kind == "mp":
        return "status.mp"
    if kind == "brv":
        return "status.brv"
    # ATB: 게이지 차오름 정도를 강조 강도로 표현 (준비됨=focus 계열)
    return "accent.cyan"


def gauge_colors(kind: GaugeKind, ratio: float = 1.0) -> tuple[VisualColor, VisualColor]:
    """게이지 전경/배경 토큰 쌍. 배경은 전경의 반휘도 대비용 surface.sunken 기반."""
    token = gauge_fill_token(kind, ratio)
    return get_color(token), get_color("surface.sunken")


def threat_status_token(severity: float) -> TokenName:
    """적 위협도(0~1, 1=치명)를 threat.* 토큰으로 사상."""
    if severity <= 0.25:
        return "threat.low"
    if severity <= 0.5:
        return "threat.medium"
    if severity <= 0.8:
        return "threat.high"
    return "threat.critical"


def feedback_tokens(state: FeedbackState) -> tuple[VisualColor, VisualColor]:
    """상태/피격/선택 피드백 (전경, 배경) 토큰 쌍."""
    fg, bg = _FEEDBACK_TOKENS[state]
    return get_color(fg), get_color(bg)


@dataclass(frozen=True, slots=True)
class HudFrame:
    """텍스트 콘솔(Raylib/TCOD 공용)에 그릴 HUD 프레임 라인."""

    lines: tuple[str, ...]


def build_hud_frame(
    width: int,
    title: str,
    console_glyphs_supported: bool = True,
    variant_border: TokenName = "line.default",
) -> HudFrame:
    """지정 폭의 HUD 프레임을 글리프셋으로 렌더링.

    백엔드(Raylib/TCOD)에 관계없이 동일 토큰·글리프 계약을 공유한다.
    콘솔 글리프(╔═╗) 미지원 환경은 ASCII(+,-)로 자동 폴백한다.
    """
    glyphs = glyphs_for(console_glyphs_supported)
    title_text = f"{title}"  # 상단 프레임에 제목 삽입 (visual_primitives 타이틀 글리프 사용)
    top = glyphs.top_left + glyphs.horizontal + title_text + glyphs.horizontal * (
        width - 3 - len(title_text)
    ) + glyphs.top_right
    label = f"{glyphs.vertical}{title_text.center(width - 2)}{glyphs.vertical}"
    bottom = glyphs.bottom_left + glyphs.horizontal * (width - 2) + glyphs.bottom_right
    # variant_border는 Raylib 렌더러가 색상 토큰으로 프레임을 칠할 때 참조한다.
    del variant_border
    return HudFrame(lines=(top, label, bottom))


def motion_durations(reduced_motion: bool = False) -> dict[str, float]:
    """애니메이션 지속시간(초). reduced-motion이면 모든 모션 0."""
    if reduced_motion:
        return {key: 0.0 for key in _NORMAL_MOTION}
    return dict(_NORMAL_MOTION)
