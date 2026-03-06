<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/tutorials/

## Purpose
8개 튜토리얼 단계의 YAML 정의. 순서대로 번호가 매겨진 7개의 단계 파일과 전체 설정 파일로 구성된다.

## Key Files
| File | Description |
|------|-------------|
| `01_basic_movement.yaml` | 1단계: 기본 이동 조작 |
| `02_basic_interaction.yaml` | 2단계: 오브젝트 상호작용 |
| `03_combat_intro.yaml` | 3단계: 전투 입문 |
| `04_atb_system.yaml` | 4단계: ATB(액티브 타임 배틀) 시스템 |
| `05_brave_system.yaml` | 5단계: Brave 포인트 시스템 |
| `06_skill_system.yaml` | 6단계: 스킬 사용법 |
| `07_job_system.yaml` | 7단계: 직업 시스템 |
| `tutorial_config.yaml` | 튜토리얼 전역 설정 (스킵 허용 여부 등) |

## For AI Agents
### Working In This Directory
- 튜토리얼 단계 순서는 파일명 번호로 결정됨 — 번호 변경 시 로더도 수정 필요
- 구현체: `src/tutorial/tutorial_manager.py`, `src/tutorial/tutorial_step.py`
- 튜토리얼 테스트: `tests/unit/tutorial/test_tutorial_manager.py`

## Dependencies
### Internal
- `src/tutorial/tutorial_manager.py` — 이 디렉토리 로드
- `src/tutorial/tutorial_step.py` — 각 단계 파싱

<!-- MANUAL: -->
