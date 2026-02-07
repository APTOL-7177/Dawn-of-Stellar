---
description: 스킬이 작동하지 않거나 효과가 없는 버그를 수정하는 워크플로우
---

# 스킬 버그 수정

## 1. 스킬 데이터 확인
// turbo
`data/skills/<skill_id>.yaml`을 읽어 스킬 정의를 확인한다:
- `id`, `name`, `type` 필드 존재 여부
- `effects` 리스트가 비어있지 않은지
- `costs.mp`, `costs.cast_time` 값이 적절한지

## 2. 스킬 로딩 경로 확인
`src/character/skills/yaml_skill_loader.py`에서 해당 스킬이 로드되는지 확인한다.
- YAML → Skill 객체 변환 과정
- `effects` 파싱이 올바른지
- 커스텀 핸들러가 필요한 스킬인지 (`custom_handlers.py` 확인)

## 3. 스킬 실행 경로 추적
`src/character/skills/skill.py`에서 `execute()` 메서드의 실행 흐름을 추적한다.
- 효과별 처리: `src/character/skills/effects/` 디렉토리의 핸들러
- 직업별 특수 스킬: `src/character/skills/job_skills/<job>.py`

## 4. 전투 매니저 연동 확인
`src/combat/combat_manager.py`에서:
- `execute_skill()` 호출 시 올바른 컨텍스트가 전달되는지
- 대상 선택이 올바른지
- 스킬 효과 적용 후 후처리(기믹 업데이트, 트레이트 트리거)가 동작하는지

## 5. 근본 원인 수정
- YAML 데이터 누락 → 필드 추가
- 효과 핸들러 미등록 → 핸들러 구현/등록
- 컨텍스트 누락 → 호출부에서 컨텍스트 전달
- 조건 판정 오류 → 조건 로직 수정

## 6. 테스트
```bash
pytest tests/ -x -q -k "skill"
```

## 7. 수동 검증
```bash
python main.py --dev --debug --log=DEBUG
```
해당 스킬을 가진 캐릭터로 전투에서 스킬을 사용하여 확인한다.
