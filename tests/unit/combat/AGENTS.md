<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/unit/combat/

## Purpose
전투 시스템 단위 테스트. ATB 시스템, 데미지 계산, 상태 이상, 스킬 효과를 개별 검증합니다.

## Key Files
| File | Description |
|------|-------------|
| test_atb_system.py | ATB 턴 계산, 턴 순서, 캐스팅 시간 테스트 |
| (추가 테스트 파일) | 데미지, 상태 이상, 스킬 효과 등 |

## Test Coverage
```
test_atb_system.py:
  - test_turn_order_calculation
  - test_casting_time_application
  - test_break_skill_interrupt
  - test_multiple_characters_simultaneous_action
```

## For AI Agents

### Working In This Directory
- test_atb_system.py 는 핵심 전투 로직 검증
- src/combat/atb_system.py 의 turn_count, casting_time 계산 확인
- break 스킬로 캐스팅 중단 테스트
- 다중 캐릭터 동시 행동 순서 검증

### Common Patterns
- Fixture: `combat_manager`, `player_character`, `enemy_character` 등
- Mock: `damage_calculator`, `skill_manager` 등 의존성 격리
- Parametrize: 여러 직업, 스킬, 조건 조합 테스트

## Dependencies
- pytest
- src/combat/atb_system.py - 테스트 대상
- src/character/ - 캐릭터 인스턴스
- src/combat/damage_calculator.py - 데미지 로직

<!-- MANUAL: -->
