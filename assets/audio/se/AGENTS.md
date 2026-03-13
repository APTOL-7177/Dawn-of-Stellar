<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/audio/se/

## Purpose
사운드 이펙트 OGG 파일들을 관리합니다. 공격, 방어, 스킬, 아이템, 환경음 등 게임 액션 효과음입니다.

## Key Files
| File | Description |
|------|-------------|
| Attack1.ogg ~ Attack3.ogg | 일반 공격 효과음 (변형) |
| Barrier.ogg | 방어 스킬/배리어 음 |
| Absorb1.ogg ~ Absorb2.ogg | 흡수/드레인 효과음 |
| Blind.ogg | 맹목 상태 이상음 |
| Bite.ogg | 깨물기 공격음 |
| Bell1.ogg ~ Bell3.ogg | 종소리/메뉴음 |
| Applause1.ogg ~ Applause2.ogg | 박수/승리음 |
| Battle1.ogg ~ Battle6.ogg | 전투 환경음 (배경) |
| Autodoor.ogg | 문/게이트 오픈 음 |

## Subdirectories
없음

## For AI Agents

### Working In This Directory
- OGG 형식 (압축, 빠른 로드)
- 짧은 효과음 (< 2초)
- src/combat/combat_manager.py와 src/ui/combat_ui.py에서 스킬 음 트리거

### Common Patterns
- 파일명 번호: 같은 액션의 다양한 변형 (무작위 선택)
- 스킬별 효과음: 스킬 YAML에서 sound_effect 필드 참조
- 메뉴음: Bell 시리즈 (UI 선택음)

## Dependencies
- src/combat/combat_manager.py (스킬 효과음)
- src/ui/combat_ui.py (UI 피드백음)
- src/character/skills/skill.py (스킬 정의 및 음향)
- src/ui/cursor_menu.py (메뉴 선택음)

<!-- MANUAL: -->
