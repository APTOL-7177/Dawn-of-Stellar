<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/audio/bg/

## Purpose
배경음악 WAV 파일들을 관리합니다. 던전, 보스 전투, 월드맵, 메뉴 테마 등 게임의 주요 장면별 배경음악입니다.

## Key Files
| File | Description |
|------|-------------|
| battle.wav | 일반 전투 테마 |
| boss.wav | 보스 전투 테마 |
| forest.wav | 숲 던전 배경음악 |
| caves.wav | 동굴 던전 배경음악 |
| menu.wav | 메인 메뉴 테마 |
| intro.wav | 인트로/로고 테마 |
| fanfare.wav | 승리 팬페어 |
| gameover.wav | 게임 오버 음악 |
| desert.wav | 사막 던전 배경음악 |
| icelands.wav | 얼음 던전 배경음악 |
| party_setup.wav | 파티 설정 메뉴 음악 |
| logo.wav | 로고 스플래시 음악 |
| menu2.wav | 서브 메뉴 테마 |
| pianosolo.wav | 피아노 솔로 (엔딩/보스 테마) |
| danger.wav | 위험 상황 경고음 |
| frostlands.wav | 빙설 지역 배경음악 |
| badlands.wav | 악지 던전 배경음악 |
| highlands.wav | 고지 던전 배경음악 |
| devillands.wav | 악마 영역 배경음악 |
| Timewalker.wav | 시간 여행 테마 |

## Subdirectories
없음

## For AI Agents

### Working In This Directory
- WAV 형식 유지 (높은 음질, 루프 가능)
- 배경음악은 반복 재생(loop)되므로 시작/끝이 자연스러운지 확인
- src/audio/audio_manager.py의 get_bgm() 또는 play_bg_music()에서 참조

### Common Patterns
- 파일명은 장면/던전 이름과 일치하도록 작명
- 평균 길이: 2-4분 (루프 편의)
- 메뉴 음악은 반복성이 낮도록 설계

## Dependencies
- src/audio/audio_manager.py (배경음악 재생)
- src/world/exploration.py (던전별 배경음악 트리거)
- src/combat/combat_manager.py (전투 음악 트리거)

<!-- MANUAL: -->
