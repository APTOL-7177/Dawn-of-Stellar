---
description: 직업 기믹 오동작을 수정하는 워크플로우
---

# 직업 기믹 버그 수정

## 1. 기믹 정의 확인
// turbo
해당 직업의 `data/characters/<job>.yaml`에서 `gimmick:` 섹션을 읽어 기믹 타입과 설정값을 파악한다.

## 2. 기믹 업데이터 코드 탐색
`src/character/gimmick_updater.py`에서 해당 기믹 타입의 메서드를 찾는다:
- `_initialize_<gimmick_type>` — 전투 시작 시 초기화
- `_update_<gimmick_type>` — 턴/라운드마다 업데이트
- `_render_<gimmick_type>` — UI 표시
- `check_demand_fulfillment` / `generate_crowd_demand` 등 기믹별 서브 메서드

주의: `gimmick_updater.py`는 매우 큰 파일(300K+)이므로 `grep_search`로 정확한 메서드 위치를 먼저 찾는다.

## 3. 트레이트 연동 확인
// turbo
`src/character/gimmick_trait_effects.py`와 `src/character/trait_effects.py`에서 해당 기믹과 연동되는 트레이트 효과를 확인한다.

## 4. 이벤트 훅 확인
`src/combat/combat_manager.py`에서 기믹 업데이트가 호출되는 지점을 확인한다:
- 턴 시작/종료
- 라운드 시작/종료
- 스킬 사용 후
- 피격 시
- 킬 시

올바른 context (action_type, target_id, hp_percent 등)가 전달되는지 검증한다.

## 5. 조건 판정 로직 수정
기믹 조건(예: 관중 요구, 룬 폭발, 환호 게이지 등)의 판정 로직을 수정한다.
- 경계값 오류 (off-by-one) 확인
- 컨텍스트 누락 확인
- 조건 충족 이벤트 타이밍 확인

## 6. 테스트
```bash
pytest tests/ -x -q -k "gimmick or <job_name>"
```

## 7. 수동 검증
```bash
python main.py --dev
```
해당 직업을 파티에 넣고 기믹 동작을 확인한다.
