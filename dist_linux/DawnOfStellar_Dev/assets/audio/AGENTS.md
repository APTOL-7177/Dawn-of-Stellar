<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/audio/

## Purpose
게임 오디오 파일 루트 디렉토리입니다. 배경음악(bg), 뮤직 이펙트(me), 사운드 이펙트(se) 세 카테고리로 조직되어 있습니다.

## Key Files
없음 (서브디렉토리만 포함)

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| bg/ | 배경음악 (WAV 형식) - 던전, 보스, 메뉴, 전투 테마 |
| me/ | 뮤직 이펙트 (OGG 형식) - 저주, 패배, 팬페어 등 |
| se/ | 사운드 이펙트 (OGG 형식) - 공격, 방어, 아이템 효과음 등 |

## For AI Agents

### Working In This Directory
- 오디오 파일 추가 시 해당 카테고리 디렉토리에 배치
- 파일명은 영문 + 숫자로 통일 (예: Attack1.ogg, Battle3.wav)
- src/audio/audio_manager.py에서 경로 지정 확인

### Common Patterns
- WAV: 배경음악 (높은 음질, 루프 처리)
- OGG: 이펙트 (압축, 빠른 로드)
- 오디오 재생은 pygame.mixer 또는 별도 오디오 엔진 사용

## Dependencies
- src/audio/audio_manager.py (오디오 재생 관리)
- src/ui/tcod_display.py (음소거 토글 UI)

<!-- MANUAL: -->
