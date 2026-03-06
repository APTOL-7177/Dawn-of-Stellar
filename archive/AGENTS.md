<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# archive/

## Purpose
미사용/구버전 자산과 설계 문서 보관소. 삭제 대신 이 디렉토리로 이동하여 이력을 보존한다. 게임 실행과 무관하며 참조 전용이다.

## Key Files (설계 문서, 39개 중 주요)
| File | Description |
|------|-------------|
| `README.md` | 아카이브 디렉토리 안내 |
| `GAME_OVERVIEW.md` | 초기 게임 전체 개요 |
| `JOB_MECHANISMS.md` | 직업 기믹 메커니즘 설계 원본 |
| `DIMENSIONIST_REWORK_DESIGN.md` | 차원술사 리워크 설계 |
| `BOSS_INTEGRATION_TODO.md` | 보스 통합 작업 목록 |
| `multiplayer_design.md` | 멀티플레이어 설계 문서 |
| `multiplayer_implementation_status.md` | 멀티플레이어 구현 현황 |
| `multiplayer_testing_checklist.md` | 멀티플레이어 테스트 체크리스트 |
| `combat-system.md` | 전투 시스템 초기 설계 |
| `tutorial_system_design.md` | 튜토리얼 시스템 설계 |
| `architecture.md` | 초기 아키텍처 문서 |
| `sound_files_list.md` | 오디오 파일 목록 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `characters/` | 구버전 캐릭터 데이터 (README.md만 포함) |
| `rogue/` | 로그 직업 스킬 YAML 21개 (구버전) |
| `skills_backup/` | 백업 스킬 YAML 15개 |
| `skills_unused_yaml/` | 미사용 스킬 YAML 225개 |

## For AI Agents
### Working In This Directory
- 이 디렉토리 파일은 **읽기 전용** 참조용 — 직접 수정 불필요
- 미사용 스킬 재활용 시: `skills_unused_yaml/` 에서 복사 후 `data/skills/` 로 이동
- 설계 참조 시: `multiplayer_*.md` 문서들이 현재 구현의 배경 제공
- 새 파일 아카이브 시: `scripts/archive_unused_yaml_skills.py` 사용

## Dependencies
### Internal
- 없음 (참조 전용 디렉토리)

<!-- MANUAL: -->
