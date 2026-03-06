<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/integration/

## Purpose
시스템 간 상호작용을 검증하는 통합 테스트. 현재 전투 플로우 전체를 검증하는 파일 1개를 포함한다.

## Key Files
| File | Description |
|------|-------------|
| `test_combat_flow.py` | ATB 전투 플로우 전체 시나리오 통합 테스트 |

## For AI Agents
### Working In This Directory
- 통합 테스트는 실제 게임 데이터(`data/`) 를 로드하여 실행
- 새 시스템 추가 시 이 디렉토리에 `test_{system}_flow.py` 추가 권장
- 단위 테스트보다 실행 시간이 길 수 있음

## Dependencies
### Internal
- `src/combat/` — 전투 시스템 전체
- `data/characters/`, `data/skills/` — 실제 데이터 로드

<!-- MANUAL: -->
