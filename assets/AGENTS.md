<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/

## Purpose
게임 정적 자산 디렉토리. 오디오 파일(배경음악, 효과음, ME)과 게임 아이콘을 포함한다.

## Key Files
| File | Description |
|------|-------------|
| `logo.ico` | 게임 아이콘 (Windows 실행 파일용) |
| `logo.png` | 게임 로고 이미지 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `audio/` | 전체 오디오 자산 — bg/me/se 3개 카테고리 (see `audio/AGENTS.md`) |

## For AI Agents
### Working In This Directory
- 오디오 파일 추가 시 반드시 `audio/` 하위 적절한 카테고리에 배치
- 파일명은 소문자+언더스코어 형식 유지
- 아이콘 교체 시 `.ico` 와 `.png` 동시 업데이트

## Dependencies
### Internal
- `src/audio/audio_manager.py` — 오디오 파일 로드
- `data/skills/` — 스킬 YAML의 SFX 필드가 `audio/se/` 파일명 참조

<!-- MANUAL: -->
