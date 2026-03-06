<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/

## Purpose
게임 데이터 정의 디렉토리. 직업(캐릭터), 스킬, 튜토리얼 등 게임 콘텐츠를 YAML 형식으로 정의하며, `src/` 코드에 의해 런타임에 로드된다.

## Key Files
| File | Description |
|------|-------------|
| `passives.yaml` | 전체 패시브 스킬 정의 목록 |
| `teamwork_skills.yaml` | 파티 팀워크 스킬 정의 |
| `cooking_recipes.yaml` | 요리/폭탄/포션 제조 레시피 목록 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `characters/` | 35개 직업별 스탯/기믹/특성 YAML (see `characters/AGENTS.md`) |
| `skills/` | 414개 스킬 정의 YAML (see `skills/AGENTS.md`) |
| `tutorials/` | 8개 튜토리얼 단계 YAML (see `tutorials/AGENTS.md`) |

## For AI Agents
### Working In This Directory
- 새 직업 추가 시: `characters/` 에 `{job_name}.yaml` 생성 후 `src/character/character_loader.py` 에 등록
- 새 스킬 추가 시: `skills/` 에 YAML 생성, `docs/YAML_SKILL_SFX_GUIDE.md` 참고
- YAML 스키마 변경 시 `src/character/yaml_skill_loader.py` 와 동기화 필요
- 스킬 ID 중복 확인: `scripts/check_skill_ids.py` 실행

## Dependencies
### Internal
- `src/character/character_loader.py` — 직업 YAML 로드
- `src/character/skills/yaml_skill_loader.py` — 스킬 YAML 로드
- `src/tutorial/tutorial_manager.py` — 튜토리얼 YAML 로드
### External
- PyYAML (런타임 파싱)

<!-- MANUAL: -->
