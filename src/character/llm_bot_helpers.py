# -*- coding: utf-8 -*-
"""닌자/정령술사/엔지니어 변형 선택 등 LLM/RL 봇 공용 헬퍼 (t_082c6a99, t_98b95a46).

variants 프리미티브의 AI 측 정책을 모아둔다.
UI/AI 어디서든 동일 greedy 정책을 공유한다.
"""
from typing import Any, Dict, Optional

NINJA_SEAL_ELEMENTS = ("fire", "ice", "thunder", "wind")
ELEMENTALIST_SPIRITS = ("fire", "water", "wind", "earth")


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


def pick_elementalist_variant(actor: Any = None) -> str:
    """정령 소환 greedy — 현재 장착된 융합 완성 우선 (t_98b95a46 D6).

    1. 활성 정령이 장착 융합의 한쪽만 포함하면 빠진 쪽 선택
    2. 장착 융합이 활성 정령과 안 겹치면 첫 융합의 첫 requires 선택
    3. 융합이 이미 완성돼 있으면 첫 비활성 정령 (중복 시전 방지)
    4. actor/융합 정보 부재 시 첫 비활성 정령 (최대 2개만 활성이라 항상 존재)
    """
    active = {e for e in ELEMENTALIST_SPIRITS if getattr(actor, f"spirit_{e}", 0) > 0} if actor else set()

    fusions = []
    if actor is not None:
        for skill in getattr(actor, "skills", []) or []:
            meta = getattr(skill, "metadata", None) or {}
            if meta.get("fusion"):
                reqs = [str(r) for r in (meta.get("requires") or [])]
                if reqs:
                    fusions.append(reqs)

    if fusions and active:
        for reqs in fusions:
            overlap = active.intersection(reqs)
            if overlap and len(overlap) < len(set(reqs)):
                missing = [r for r in reqs if r not in active]
                if missing:
                    return missing[0]
        for reqs in fusions:
            if not active.intersection(reqs):
                return reqs[0]

    for e in ELEMENTALIST_SPIRITS:
        if e not in active:
            return e
    return ELEMENTALIST_SPIRITS[0]


def pick_engineer_variant(character: Any = None) -> str:
    """포탑 설치 greedy (t_98b95a46 설계 §5.5).

    - 포탑 0기 → normal (무료 개전)
    - 아군 최저 HP비 < 0.5 and 치유 포탑 미설치 → heal
    - MP 여유 and 적 2명 이상 → explosive, else fire
    - 그 외 / 정보 부재 → normal
    """
    if character is None:
        return "normal"
    if getattr(character, "turret_count", 0) == 0:
        return "normal"

    allies = getattr(character, "allies", None) or []
    living = [a for a in allies if getattr(a, "is_alive", True)]
    if living:
        lowest = min(getattr(a, "current_hp", 1) / max(1, getattr(a, "max_hp", 1)) for a in living)
        if lowest < 0.5 and getattr(character, "heal_turret_count", 0) == 0:
            return "heal"

    mp = getattr(character, "current_mp", 0)
    max_mp = getattr(character, "max_mp", 1) or 1
    enemies = getattr(character, "enemies", None) or []
    enemy_count = len([e for e in enemies if getattr(e, "is_alive", True)])
    if mp >= max_mp * 0.25 and enemy_count >= 2 and getattr(character, "explosive_turret_count", 0) == 0:
        return "explosive"
    if mp >= max_mp * 0.15 and getattr(character, "fire_turret_count", 0) == 0:
        return "fire"
    return "normal"


def apply_variant_to_action_skill(
    skill: Any,
    seal_state: Optional[Dict[str, int]] = None,
    *,
    actor: Any = None,
) -> Optional[str]:
    """스킬이 variant_capable이면 greedy 변형을 metadata에 주입한다.

    RL/폴백 AI decode 후 호출 — 액션 공간 확장 없이 기본/최적 변형만 사용.
    actor가 주어지면 직업별 greedy 정책을 우선한다 (t_98b95a46 D6).
    반환값: 적용된 변형 키 (variant_capable 아님 → None)
    """
    meta = getattr(skill, "metadata", None) or {}
    if not meta.get("variant_capable"):
        return None
    options = meta.get("variant_options") or {}
    if not options:
        return None

    selected: Optional[str] = None

    if meta.get("variant_policy") == "elementalist_fusion" and actor is not None:
        selected = pick_elementalist_variant(actor)
    elif "turret_type" in str(set((options.get(meta.get("variant_default")) or {}).get("metadata_override") or {})):
        # 엔지니어 포탑: default 옵션에 turret_type이 있으면 engineer greedy
        selected = pick_engineer_variant(actor)
    elif seal_state is not None:
        selected = pick_ninja_variant(seal_state)

    if selected not in options:
        selected = meta.get("variant_default")
    if selected and selected in options:
        meta["_selected_variant"] = selected
        return selected
    return None
