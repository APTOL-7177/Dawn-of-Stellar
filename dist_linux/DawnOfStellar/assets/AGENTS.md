<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/

## Purpose
게임 리소스 루트 디렉토리입니다. 오디오 파일, UI 이미지를 관리하며, 오디오는 배경음악(bg), 뮤직 이펙트(me), 사운드 이펙트(se)로 구분됩니다.

## Key Files
| File | Description |
|------|-------------|
| logo.png | 게임 로고 이미지 |
| logo.ico | Windows 실행 파일 아이콘 |
| background.png | 메인 UI 배경 이미지 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| audio/ | 모든 사운드 파일 루트 (bg, me, se 포함) |

## For AI Agents

### Working In This Directory
- PNG/ICO 파일은 UI 렌더링용 (src/ui/tcod_display.py)
- 이미지 형식 변경 시 pygame 또는 PIL 호환성 확인
- 오디오 서브디렉토리는 src/audio/audio_manager.py에서 참조됨

### Common Patterns
- 리소스 로드는 src/core/paths.py의 경로 설정 참조
- 이미지 해상도: 소급 픽셀 아트 (neodgm 폰트 스타일)
- 오디오 포맷: WAV (배경음악), OGG (이펙트)

## Dependencies
- src/ui/tcod_display.py (이미지 렌더링)
- src/audio/audio_manager.py (오디오 재생)
- src/core/paths.py (리소스 경로 설정)

<!-- MANUAL: -->
