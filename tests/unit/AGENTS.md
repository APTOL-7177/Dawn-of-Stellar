<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/unit/

## Purpose
개별 모듈/클래스 단위의 격리된 테스트. combat과 tutorial 두 하위 카테고리로 분류된다.

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `combat/` | ATB, Brave, 데미지, 상태이상 단위 테스트 4개 (see `combat/AGENTS.md`) |
| `tutorial/` | 튜토리얼 매니저 단위 테스트 (see `tutorial/AGENTS.md`) |

## For AI Agents
### Working In This Directory
- 새 combat 모듈 추가 시 `combat/test_{module}.py` 작성
- 픽스처는 상위 `tests/conftest.py` 참조
- 단위 테스트는 외부 의존성 최소화 (mock 활용)

## Dependencies
### Internal
- `tests/conftest.py` — 공유 픽스처
- `src/combat/`, `src/tutorial/` — 테스트 대상

<!-- MANUAL: -->
