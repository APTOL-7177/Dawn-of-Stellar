---
description: 전투 시스템 버그를 디버깅하는 워크플로우
---

# 전투 버그 디버깅

## 1. 증상 분류
사용자가 보고한 버그를 다음 카테고리로 분류:
- **스킬 미발동**: 스킬 효과가 적용되지 않음
- **데미지 이상**: 데미지가 0이거나 비정상적으로 높음
- **상태이상 미적용**: 버프/디버프가 걸리지 않음
- **기믹 오동작**: 직업 기믹이 예상대로 작동하지 않음
- **ATB/턴 이상**: 턴 순서가 비정상적
- **크래시/에러**: 런타임 에러 발생

## 2. 관련 코드 탐색
카테고리별 핵심 파일:
- **스킬**: `src/character/skills/skill.py`, `src/character/skills/yaml_skill_loader.py`, `src/character/skills/custom_handlers.py`
- **데미지**: `src/combat/damage_calculator.py`, `src/combat/brave_system.py`
- **상태이상**: `src/combat/status_effects.py`
- **기믹**: `src/character/gimmick_updater.py`, `src/character/gimmick_trait_effects.py`
- **ATB**: `src/combat/atb_system.py`
- **전투 흐름**: `src/combat/combat_manager.py`
- **트레이트**: `src/character/trait_effects.py`

`code_search` 도구로 관련 키워드를 검색하여 정확한 위치를 찾는다.

## 3. 데이터 확인
// turbo
해당 스킬/캐릭터의 YAML 데이터를 확인한다:
- `data/skills/<skill_id>.yaml` — 효과, MP 비용, 타입
- `data/characters/<job>.yaml` — 기믹, 트레이트, 스킬 목록

## 4. 실행 경로 추적
`combat_manager.py`에서 해당 스킬/효과가 실행되는 경로를 추적한다:
- `execute_skill()` → 스킬 효과 적용
- `apply_damage()` → 데미지 계산
- `on_ally_attack()` / `on_enemy_attack()` → 반격/트레이트 트리거
- `_update_gimmick()` → 기믹 업데이트

## 5. 근본 원인 수정
- 최소한의 변경으로 근본 원인을 수정한다.
- 하류 워크어라운드보다 상류 수정을 우선한다.
- 수정 전후 동작을 명확히 설명한다.

## 6. 회귀 테스트
```bash
pytest tests/ -x -q
```
관련 테스트가 없으면 간단한 테스트 케이스를 추가한다.

## 7. 수동 검증 안내
```bash
python main.py --dev --debug --log=DEBUG
```
사용자에게 재현 방법과 확인 포인트를 안내한다.
