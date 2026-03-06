<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/characters/

## Purpose
35개 직업(Job)의 기본 스탯, 기믹, 특성, BRV 성장치를 YAML로 정의한다. 각 파일은 `src/character/character_loader.py` 가 게임 시작 시 로드한다.

## Key Files
| File | Description |
|------|-------------|
| `warrior.yaml` | 전사 — 근거리 물리 딜러, 기본 참조 직업 |
| `knight.yaml` | 기사 — 탱커, Duty 시스템 보유 |
| `archmage.yaml` | 대마법사 — 융합 스킬 시스템 |
| `rogue.yaml` | 로그 — 라틴어 스킬명, 스텔스 기믹 |
| `samurai.yaml` | 사무라이 — 최근 리메이크 완료 직업 |
| `hacker.yaml` | 해커 — 기믹 디버그 이슈 다수 |
| `dimensionist.yaml` | 차원술사 — 리워크 설계 문서 존재 |

## For AI Agents
### Working In This Directory
- 직업 YAML 스키마: `name`, `stats`, `gimmick`, `traits`, `brv_growth` 필드 포함
- 신규 직업 추가 시 `src/character/skills/job_skills/{job}_skills.py` 도 함께 생성 필요
- 직업 스탯 밸런스 검토: `scripts/analyze_job_stats.py` 실행
- 기믹 필드 검증: `scripts/verify_gimmick_fields.py` 실행
- 리메이크 설계 문서: `docs/design/` 참조

## Dependencies
### Internal
- `src/character/character_loader.py` — 이 디렉토리 전체 로드
- `src/character/job_stats_loader.py` — 스탯 파싱
- `src/character/gimmick_updater.py` — 기믹 처리

<!-- MANUAL: -->
