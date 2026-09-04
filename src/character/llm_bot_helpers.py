# -*- coding: utf-8 -*-
"""닌자 변형 선택 등 LLM/RL 봇 공용 헬퍼 (t_082c6a99).

variants 프리미티브(ninja_elemental_ninjutsu)의 AI 측 정책을 모아둔다.
UI/AI 어디서든 동일 greedy 정책을 공유한다.
"""
from typing import Any, Dict, Optional

NINJA_SEAL_ELEMENTS = ("fire", "ice", "thunder", "wind")


def pick_ninja_variant(seal_state: Dict[str, int]) -> str:
    """만화경 인법 greedy: 가장 낮은 인 속성을 채운다 (설계 §7.5).

    인이 모두 1 이상이면 fire부터 순서대로(만화경 도달 후 유지 동작).
    """
    if not seal_state:
        return "fire"
    return min(
        NINJA_SEAL_ELEMENTS,
        key=lambda e: (int(seal_state.get(f"seal_{e}", seal_state.get(e, 0)) or 0), NINJA_SEAL_ELEMENTS.index(e)),
    )


def apply_variant_to_action_skill(skill: Any, seal_state: Optional[Dict[str, int]] = None) -> Optional[str]:
    """스킬이 variant_capable이면 greedy 변형을 metadata에 주입한다.

    RL/폴백 AI decode 후 호출 — 액션 공간 확장 없이 기본/최적 변형만 사용.
    반환값: 적용된 변형 키 (variant_capable 아님 → None)
    """
    meta = getattr(skill, "metadata", None) or {}
    if not meta.get("variant_capable"):
        return None
    options = meta.get("variant_options") or {}
    if not options:
        return None

    if seal_state is None:
        selected = meta.get("variant_default")
    else:
        selected = pick_ninja_variant(seal_state)
        if selected not in options:
            selected = meta.get("variant_default")
    if selected and selected in options:
        meta["_selected_variant"] = selected
        return selected
    return None
