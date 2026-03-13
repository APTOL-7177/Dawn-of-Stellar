<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/unit/

## Purpose
단위 테스트. 개별 모듈의 기능을 격리하여 테스트합니다. combat/, tutorial/ 하위 구조로 나뉩니다.

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| combat/ | 전투 시스템 단위 테스트 (test_atb_system.py 등) |
| tutorial/ | 튜토리얼 시스템 단위 테스트 |

## For AI Agents

### Working In This Directory
- 각 모듈별 독립 테스트
- 외부 의존성은 Mock 으로 격리
- 빠른 실행 속도 목표 (초 단위)

### Common Patterns
- test_atb_system.py: ATB 턴 계산, 턴 순서, 캐스팅 로직
- test_damage_calculator.py: 데미지 공식, 크리티컬, 회피 판정
- test_status_effect.py: 상태 이상 부여, 해제, 중복 처리
- Fixture: character, skill, combat_state 등 반복되는 설정

## Dependencies
- pytest
- src/combat/ - 테스트 대상
- unittest.mock - 의존성 Mocking

<!-- MANUAL: -->
