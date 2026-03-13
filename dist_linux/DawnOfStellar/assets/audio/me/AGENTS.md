<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/audio/me/

## Purpose
뮤직 이펙트 OGG 파일들을 관리합니다. 저주, 패배, 팬페어, 게임오버, 상태 이상 음향 효과입니다.

## Key Files
| File | Description |
|------|-------------|
| Curse1.ogg | 저주 이펙트 1 |
| Curse2.ogg | 저주 이펙트 2 |
| Defeat1.ogg | 패배 음악 1 |
| Defeat2.ogg | 패배 음악 2 |
| Fanfare1.ogg | 팬페어 1 (아이템 획득) |
| Fanfare2.ogg | 팬페어 2 (레벨업) |
| Fanfare3.ogg | 팬페어 3 (보스 승리) |
| Gag.ogg | 개그/웃음 효과음 |
| Gameover1.ogg | 게임오버 음악 1 |
| Gameover2.ogg | 게임오버 음악 2 |

## Subdirectories
없음

## For AI Agents

### Working In This Directory
- OGG 형식 (압축 지원, 빠른 로드)
- 단축 효과음으로 반복 재생 불필요
- 특수 상황(저주, 패배) 발생 시 트리거됨

### Common Patterns
- 재생 길이: 1-3초 (예외적으로 팬페어는 5초)
- 파일명 숫자: 같은 타입의 변형 (무작위 선택 가능)
- 영어 + 숫자 작명 컨벤션

## Dependencies
- src/audio/audio_manager.py (뮤직 이펙트 재생)
- src/character/skills/effects/status_effect.py (상태 이상 이펙트 음)
- src/game_result_ui.py (결과 음향 효과)

<!-- MANUAL: -->
