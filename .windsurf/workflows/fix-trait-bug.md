---
description: 트레이트(패시브/조건부 효과)가 작동하지 않는 버그를 수정하는 워크플로우
---

# 트레이트 버그 수정

## 1. 트레이트 데이터 확인
// turbo
`data/characters/<job>.yaml`의 `traits:` 섹션에서 해당 트레이트의 `id`, `type`, `conditions`, `effects`를 확인한다.

## 2. 트레이트 효과 코드 탐색
`src/character/trait_effects.py`에서 해당 트레이트 ID를 검색한다.
- `grep_search`로 `trait_id`나 `트레이트명`을 검색
- 파일이 ~211KB이므로 정확한 줄 번호를 먼저 파악

## 3. 기믹 연동 트레이트인지 확인
기믹과 연동되는 트레이트는 `src/character/gimmick_trait_effects.py`에 있을 수 있다.
`grep_search`로 해당 트레이트 ID를 양쪽 파일에서 검색한다.

## 4. 트리거 지점 확인
`src/combat/combat_manager.py`에서 트레이트 효과가 호출되는 지점:
- 턴 시작/종료
- 공격 시/피격 시
- 스킬 사용 후
- 상태이상 적용 시

## 5. 조건 판정 로직 검증
`conditional` 타입 트레이트의 경우:
- `conditions` 딕셔너리의 키가 코드에서 올바르게 평가되는지
- 비교 연산자 (>, >=, ==) 정확한지
- 컨텍스트에서 필요한 값이 전달되는지

## 6. 수정 및 테스트
```bash
pytest tests/ -x -q -k "trait"
```
