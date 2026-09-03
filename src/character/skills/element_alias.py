"""원소 값 alias 정규화 (t_756d8ec1, 설계 t_f13aae2e).

결정 D1: "원소를 뜻하는 element 값"의 canonical은 lightning.
- 닌자 variant key 'thunder', seal_type(인 종류), 세이브 필드 seal_thunder,
  적 콘텐츠 id, 표시 매핑("thunder": "뇌")은 원소 네임스페이스가 아니므로
  절대 변환하지 않는다.
- 이 모듈은 오직 element 값(스킬 effect.element, metadata_override["element"],
  damage calculator 조회 키)에만 적용한다.
"""

from typing import Any, Dict

# 원소 값 전용 alias (seal_type 절대 변환 금지)
ELEMENT_ALIASES: Dict[str, str] = {
    "thunder": "lightning",
}

_CANONICAL_ELEMENTS = {
    "fire", "ice", "lightning", "water", "earth", "wind", "holy", "dark",
}


def normalize_element(element: Any) -> Any:
    """element 값이 alias면 canonical로 변환, 아니면 그대로 반환.

    - None / 비문자열은 무변경 통과 (호출부 로직 보존)
    - ELEMENT_ALIASES에 없는 원소(fire/ice/wind 등)도 무변경 통과
    """
    if not isinstance(element, str):
        return element
    return ELEMENT_ALIASES.get(element.lower(), element)
