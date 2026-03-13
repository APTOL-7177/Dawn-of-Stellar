<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/unit/tutorial/

## Purpose
튜토리얼 시스템 단위 테스트. Step 진행, 조건 평가, UI 오버레이, 튜토리얼 완료 추적을 검증합니다.

## Key Files
| File | Description |
|------|-------------|
| (tutorial test files) | Step 진행, 조건, 완료 로직 |

## Test Coverage
```
Tutorial system tests:
  - test_step_progression
  - test_condition_evaluation
  - test_tutorial_completion
  - test_tutorial_persistence (저장/로드)
```

## For AI Agents

### Working In This Directory
- src/tutorial/tutorial_manager.py 의 step 진행 로직 검증
- 조건 평가: player_level, job, item_count 등
- 튜토리얼 완료 후 아이템/스킬 언락
- 저장 시스템과 튜토리얼 진행도 동기화

### Common Patterns
- Fixture: `tutorial_manager`, `player_character` 등
- Mock: UI 렌더링 (비즈니스 로직만 테스트)
- State 검증: 진행도, 완료 여부, 언락 항목

## Dependencies
- pytest
- src/tutorial/ - 튜토리얼 시스템
- src/persistence/ - 저장 시스템

<!-- MANUAL: -->
