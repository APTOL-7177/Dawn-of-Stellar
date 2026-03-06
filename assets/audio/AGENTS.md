<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/audio/

## Purpose
게임 오디오 자산을 bg(배경음악), me(승리/패배 팡파레), se(효과음) 3개 카테고리로 분류하여 관리한다. 총 398개 파일.

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `bg/` | 배경음악 26개 — 필드/던전/전투 BGM (see `bg/AGENTS.md`) |
| `me/` | ME(Musical Effect) 27개 — 레벨업/승리/패배 짧은 팡파레 (see `me/AGENTS.md`) |
| `se/` | 효과음 345개 — 스킬/UI/환경 사운드 (see `se/AGENTS.md`) |

## For AI Agents
### Working In This Directory
- 오디오 포맷: 프로젝트 표준 포맷(OGG/WAV) 확인 후 추가
- SE 파일명은 `data/skills/` YAML의 `sfx` 필드와 정확히 일치해야 함
- SFX 네이밍 규칙: `docs/YAML_SKILL_SFX_GUIDE.md` 참조
- 오디오 로드: `src/audio/audio_manager.py`

## Dependencies
### Internal
- `src/audio/audio_manager.py` — 런타임 로드
- `data/skills/*.yaml` — SE 파일명 참조

<!-- MANUAL: -->
