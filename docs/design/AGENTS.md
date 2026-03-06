<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# docs/design/

## Purpose
직업 리메이크 및 신규 스킬 시스템 설계 문서 15개를 보관한다. 구현 전 설계 검토 및 AI 에이전트 컨텍스트 제공 목적이다.

## Key Files
| File | Description |
|------|-------------|
| `REMAKE_CLASSES_GUIDE.md` | 전체 리메이크 직업 작업 가이드라인 |
| `archmage_fusion_skills_redesign.md` | 대마법사 융합 스킬 재설계 |
| `elementalist_remake.md` | 엘리멘탈리스트 리메이크 설계 |
| `gladiator_remake.md` | 글래디에이터 리메이크 설계 |
| `hacker_remake.md` | 해커 리메이크 설계 |
| `paladin_remake.md` | 팔라딘 리메이크 설계 |
| `priest_remake.md` | 프리스트 리메이크 설계 |
| `rogue_remake.md` | 로그 리메이크 설계 |
| `ROGUE_LATIN_SKILLS.md` | 로그 라틴어 스킬명 목록 |
| `samurai_remake.md` | 사무라이 리메이크 설계 |
| `SAMURAI_FINAL_SUMMARY.md` | 사무라이 최종 구현 요약 |
| `SAMURAI_IMPLEMENTATION_LOG.md` | 사무라이 구현 로그 |
| `SHAMAN_REMAKE.md` | 샤먼 리메이크 설계 |
| `spellblade_battlemage_remake.md` | 스펠블레이드/배틀메이지 리메이크 |
| `tank_defense_skills.md` | 탱커 방어 스킬 설계 |

## For AI Agents
### Working In This Directory
- 직업 구현 전 해당 직업의 리메이크 문서를 반드시 참조
- 새 직업 설계 시 기존 파일(`{job}_remake.md`) 형식 따를 것
- 구현 완료 후 `SAMURAI_IMPLEMENTATION_LOG.md` 패턴으로 구현 로그 작성 권장

## Dependencies
### Internal
- `data/characters/` — 설계가 실제 YAML로 구현된 결과물
- `src/character/skills/job_skills/` — 스킬 구현체

<!-- MANUAL: -->
