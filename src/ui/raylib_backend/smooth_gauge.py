"""
공용 픽셀 단위 스무스 게이지 렌더러

CombatUI._draw_smooth_gauge 와 **완전히 동일한** 색상 테이블 + 렌더링 파이프라인.
전투 전용 기능(shield, ATB overflow, casting, BDF 텍스트)만 제외.
증가/감소 트레일(잔상) 포함.
"""

import pyray as rl

from src.ui.visual_hud import gauge_colors
from src.ui.visual_tokens import rgb as _token_rgb


def _resolve_colors(ratio: float, kind: str, custom_color: tuple = None):
    """kind 기반 색상 결정 — semantic 토큰 단일 진실공급원(visual_hud) 사용.

    combat_ui._draw_smooth_gauge 와 동일한 토큰 계약을 공유한다.
    """
    if custom_color:
        fg = custom_color
        bg = (max(0, fg[0] // 3), max(0, fg[1] // 3), max(0, fg[2] // 3))
        return fg, bg

    if kind == "hp":
        fg_v, bg_v = gauge_colors("hp", ratio)
        return tuple(fg_v.rgb), tuple(bg_v.rgb)
    elif kind == "mp":
        fg_v, bg_v = gauge_colors("mp")
        return tuple(fg_v.rgb), tuple(bg_v.rgb)
    elif kind == "exp":
        # 경험치는 성공 상태 토큰으로 표현
        return _token_rgb("status.success"), _token_rgb("surface.sunken")
    elif kind == "brv":
        fg_v, bg_v = gauge_colors("brv")
        return tuple(fg_v.rgb), tuple(bg_v.rgb)
    else:
        fg = _token_rgb("text.secondary")
        bg = _token_rgb("surface.sunken")
        return fg, bg


def _draw_gauge_text(
    text: str, x: int, y: int,
    fg: tuple, outline: tuple,
    font_renderer, ph: int,
) -> None:
    """게이지 내부 텍스트 렌더링 — combat_ui._draw_bdf_text 와 동일

    BDF 폰트 아틀라스가 있으면 사용, 없으면 raylib 기본 폰트로 폴백.
    검은 외곽선(4방향)으로 가독성 확보.
    """
    fg_c = rl.Color(fg[0], fg[1], fg[2], 255)
    ol_c = rl.Color(outline[0], outline[1], outline[2], 220) if outline else None

    fr = font_renderer
    if fr and getattr(fr, 'is_loaded', False) and getattr(fr, '_bdf_mode', False) and getattr(fr, '_atlas_tex', None) is not None:
        # ── BDF 아틀라스 모드 (전투 UI와 동일) ──
        tw = fr.tile_width
        cur_x = x
        for char in text:
            cp = ord(char)
            if cp <= 0x20:
                cur_x += tw
                continue
            rect_data = fr._glyph_rects.get(cp)
            if rect_data is None:
                cur_x += tw
                continue
            src = rl.Rectangle(*rect_data)
            # 외곽선 (4방향)
            if ol_c:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    rl.draw_texture_rec(
                        fr._atlas_tex, src,
                        rl.Vector2(float(cur_x + dx), float(y + dy)),
                        ol_c,
                    )
            # 본체
            rl.draw_texture_rec(
                fr._atlas_tex, src,
                rl.Vector2(float(cur_x), float(y)),
                fg_c,
            )
            cur_x += tw
    else:
        # ── 폴백: raylib 기본 폰트 + 외곽선 ──
        fs = getattr(fr, 'tile_height', ph) if fr else ph
        if ol_c:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                rl.draw_text(text, x + dx, y + dy, fs, ol_c)
        rl.draw_text(text, x, y, fs, fg_c)


def draw_smooth_gauge(
    px: int, py: int, pw: int, ph: int,
    ratio: float,
    kind: str = "",
    custom_color: tuple = None,
    wound_ratio: float = 0.0,
    trail_ratio: float = 0.0,
    text: str = "",
    font_renderer=None,
) -> None:
    """단일 픽셀 단위 정밀 게이지 바 렌더링 — combat_ui 와 동일 비주얼

    Args:
        px, py: 좌상단 픽셀 좌표 (렌더 텍스처 내)
        pw, ph: 게이지 픽셀 크기
        ratio: 채움 비율 (0.0 ~ 1.0)
        kind: 게이지 종류 ("hp", "mp", "brv", "exp"). 색상 자동 결정
        custom_color: 커스텀 채움 색상 (r,g,b). kind 대신 직접 지정
        wound_ratio: 상처 비율 (0.0 ~ 1.0). HP 게이지 오른쪽 끝 사용 불가 영역
        trail_ratio: 트레일(잔상) 비율.
            양수 = 감소 트레일 (이전값이 현재보다 클 때, 주황 잔상)
            음수 = 증가 트레일 (이전값이 현재보다 작을 때, 밝은 오버레이)
        text: 게이지 내부 텍스트 (선택)
        font_renderer: BDF 폰트 렌더러 (전투 UI와 동일 텍스트 렌더링)
    """
    ratio = max(0.0, min(1.0, ratio))

    # ── 색상 결정 (전투 UI와 동일 테이블) ──
    fg, bg = _resolve_colors(ratio, kind, custom_color)

    # 1) 배경
    rl.draw_rectangle(px, py, pw, ph, rl.Color(bg[0], bg[1], bg[2], 255))

    # 2) 상처/예약 영역 — 오른쪽 끝에 사용 불가 표시
    wound_w = 0
    if wound_ratio > 0 and kind in ("hp", "mp", ""):
        wound_w = max(1, int(wound_ratio * pw))
        wound_w = min(wound_w, pw // 2)  # 최대 50%
        if kind == "mp":
            # MP 예약: 어두운 보라색 + 파란 경계선
            rl.draw_rectangle(
                px + pw - wound_w, py, wound_w, ph,
                rl.Color(15, 8, 25, 255),
            )
            rl.draw_rectangle(
                px + pw - wound_w, py, 1, ph,
                rl.Color(60, 40, 120, 200),
            )
        else:
            # HP 상처 (기본): 검은색 + 붉은 경계선
            rl.draw_rectangle(
                px + pw - wound_w, py, wound_w, ph,
                rl.Color(10, 8, 12, 255),
            )
            rl.draw_rectangle(
                px + pw - wound_w, py, 1, ph,
                rl.Color(120, 30, 30, 200),
            )

    # 3) 트레일 (잔상) — 메인 채움 전에 그려서 아래에 보임
    fill_w = int(ratio * pw)
    if wound_w > 0:
        fill_w = min(fill_w, pw - wound_w)

    # 감소 트레일 — fill 오른쪽에 주황/금 잔상
    if trail_ratio > 0 and kind in ("hp", "brv", ""):
        trail_w = int(trail_ratio * pw)
        if wound_w > 0:
            trail_w = min(trail_w, pw - wound_w)
        if trail_w > fill_w:
            tc = rl.Color(220, 120, 40, 180) if kind == "hp" else rl.Color(200, 180, 80, 160)
            rl.draw_rectangle(px + fill_w, py, trail_w - fill_w, ph, tc)

    # 3b) 메인 채움
    if fill_w > 0:
        rl.draw_rectangle(px, py, fill_w, ph, rl.Color(fg[0], fg[1], fg[2], 255))

    # 3c) 증가 트레일 — 메인 채움 위에 밝은 오버레이
    if trail_ratio < 0 and kind in ("hp", "brv", ""):
        old_w = int(abs(trail_ratio) * pw)
        if wound_w > 0:
            old_w = min(old_w, pw - wound_w)
        if fill_w > old_w:
            tc = rl.Color(200, 255, 200, 160) if kind == "hp" else rl.Color(255, 255, 180, 160)
            rl.draw_rectangle(px + old_w, py, fill_w - old_w, ph, tc)

    # 4) 상단 하이라이트 (반투명 흰색, 높이 1/4)
    hl_h = max(1, ph // 4)
    rl.draw_rectangle(px, py, pw, hl_h, rl.Color(255, 255, 255, 18))

    # 5) 테두리
    rl.draw_rectangle_lines(px, py, pw, ph, rl.Color(70, 70, 70, 180))

    # 6) 텍스트 — combat_ui._draw_bdf_text 와 동일 (BDF 폰트 + 검은 외곽선)
    if text:
        tx = px + 8
        ty = py
        text_fg = (255, 255, 255)
        outline = (0, 0, 0)
        _draw_gauge_text(text, tx, ty, text_fg, outline, font_renderer, ph)
