<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/

## Purpose
게임 전체 테스트 스위트. 단위 테스트, 통합 테스트, 재현 스크립트, 멀티플레이어 테스트를 포함한다. pytest 기반으로 실행된다.

## Key Files
| File | Description |
|------|-------------|
| `conftest.py` | pytest 전역 픽스처 및 설정 |
| `test_multiplayer_basic.py` | 멀티플레이어 기본 동작 테스트 |
| `test_multiplayer_regression.py` | 멀티플레이어 회귀 테스트 |
| `test_skill_system.py` | 스킬 시스템 전체 테스트 |
| `test_character_yaml.py` | 캐릭터 YAML 로딩 검증 |
| `test_teamwork_comprehensive.py` | 팀워크 스킬 종합 테스트 |
| `test_remake_gimmicks.py` | 리메이크 직업 기믹 테스트 |
| `repro_sword_aura.py` | 소드 오라 버그 재현 스크립트 |
| `run_multiplayer_tests.py` | 멀티플레이어 테스트 일괄 실행 |
| `verify_skill_updates.py` | 스킬 업데이트 검증 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `integration/` | 전투 플로우 통합 테스트 (see `integration/AGENTS.md`) |
| `unit/` | 단위 테스트 — combat/tutorial 하위 분류 (see `unit/AGENTS.md`) |

## For AI Agents
### Working In This Directory
- 테스트 실행: `pytest tests/` (루트에서)
- 멀티플레이어 테스트만: `python tests/run_multiplayer_tests.py`
- 새 직업/스킬 추가 시 해당 `test_{job}.py` 파일 함께 작성
- `repro_*.py` 파일은 버그 재현용 — 수정 후 삭제하지 말고 보존
- `verify_*.py` 파일은 일회성 검증 스크립트

## Dependencies
### Internal
- `src/` — 테스트 대상 모든 소스
- `data/` — 테스트에서 실제 YAML 로드
### External
- pytest

<!-- MANUAL: -->
