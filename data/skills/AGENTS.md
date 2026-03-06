<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/skills/

## Purpose
414개 스킬의 YAML 정의 저장소. 각 파일은 스킬 1개를 정의하며, `src/character/skills/yaml_skill_loader.py` 가 런타임에 로드하여 직업 스킬 풀에 등록한다.

## Key Files
| File | Description |
|------|-------------|
| `abyss_blade.yaml` | 심연의 검 — 다크 나이트 스킬 예시 |
| `acid_flask.yaml` | 산성 플라스크 — 연금술사 투척 스킬 |

> 414개 파일 전체 목록은 `scripts/extract_skill_ids.py` 로 확인.

## For AI Agents
### Working In This Directory
- 스킬 YAML 스키마 및 SFX 태그: `docs/YAML_SKILL_SFX_GUIDE.md` 필독
- 필수 필드: `id`, `name`, `type`, `cost`, `effect`
- SFX 필드: `assets/audio/se/` 파일명과 반드시 일치
- 중복 ID 확인: `scripts/check_skill_ids.py`
- 미사용/아카이브 스킬: `archive/skills_unused_yaml/` (225개)
- 스킬 효과 구현체: `src/character/skills/effects/`

## Dependencies
### Internal
- `src/character/skills/yaml_skill_loader.py` — 이 디렉토리 전체 로드
- `src/character/skills/skill_initializer.py` — 스킬 객체 초기화
- `assets/audio/se/` — SFX 참조

<!-- MANUAL: -->
