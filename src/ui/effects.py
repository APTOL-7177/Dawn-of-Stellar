"""
백엔드 독립 이펙트 모듈

config.yaml의 display.backend 설정에 따라
pygame_backend 또는 raylib_backend의 이펙트를 동적으로 임포트합니다.

사용법:
    from src.ui.effects import trigger_skill_effect, TextScrambler, TransitionMode
"""


def _is_raylib() -> bool:
    """현재 백엔드가 raylib인지 확인 (지연 평가)"""
    try:
        from src.core.config import get_config
        return get_config().get("display.backend", "pygame") == "raylib"
    except Exception:
        return False


def __getattr__(name: str):
    """모듈 레벨 지연 임포트 — 실제 사용 시점에 백엔드 결정"""
    _raylib = _is_raylib()

    # text_effects
    if name in ("TextScrambler", "TextTypewriter", "ColorCycler", "render_scrambled_text"):
        if _raylib:
            from src.ui.raylib_backend.effects import text_effects as mod
        else:
            from src.ui.pygame_backend.effects import text_effects as mod
        obj = getattr(mod, name)
        globals()[name] = obj
        return obj

    # skill_effects
    if name in ("trigger_skill_effect", "trigger_status_effect", "trigger_item_effect"):
        if _raylib:
            from src.ui.raylib_backend.effects import skill_effects as mod
        else:
            from src.ui.pygame_backend.effects import skill_effects as mod
        obj = getattr(mod, name)
        globals()[name] = obj
        return obj

    # transition
    if name in ("TransitionMode", "TransitionEffect"):
        if _raylib:
            from src.ui.raylib_backend.effects import transition as mod
        else:
            from src.ui.pygame_backend.effects import transition as mod
        obj = getattr(mod, name)
        globals()[name] = obj
        return obj

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TextScrambler",
    "TextTypewriter",
    "ColorCycler",
    "render_scrambled_text",
    "trigger_skill_effect",
    "trigger_status_effect",
    "trigger_item_effect",
    "TransitionMode",
    "TransitionEffect",
]
