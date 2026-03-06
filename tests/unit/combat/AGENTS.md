<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/unit/combat/

## Purpose
전투 핵심 시스템 4개 모듈에 대한 단위 테스트.

## Key Files
| File | Description |
|------|-------------|
| `test_atb_system.py` | ATB(액티브 타임 배틀) 시스템 단위 테스트 |
| `test_brave_system.py` | Brave 포인트 시스템 단위 테스트 |
| `test_damage_calculator.py` | 데미지 계산기 단위 테스트 |
| `test_status_effects.py` | 상태이상 효과 단위 테스트 |

## For AI Agents
### Working In This Directory
- 전투 공식 변경 시 `test_damage_calculator.py` 반드시 업데이트
- ATB 타이밍 변경 시 `test_atb_system.py` 검증
- 새 상태이상 추가 시 `test_status_effects.py` 에 케이스 추가

## Dependencies
### Internal
- `src/combat/atb_system.py`
- `src/combat/brave_system.py`
- `src/combat/damage_calculator.py`
- `src/combat/status_effects.py`

<!-- MANUAL: -->
