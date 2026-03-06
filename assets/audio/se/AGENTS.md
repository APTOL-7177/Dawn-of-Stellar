<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# assets/audio/se/

## Purpose
효과음(Sound Effect) 345개 파일. 스킬 발동, UI 조작, 환경 소리 등 게임 내 모든 효과음을 포함한다.

## For AI Agents
### Working In This Directory
- 현재 파일 수: 345개
- SE 파일명은 `data/skills/*.yaml` 의 `sfx` 필드에서 직접 참조됨
- 파일명 불일치 시 스킬 사용 시 오류 발생
- 네이밍 규칙 및 SFX 태그 사용법: `docs/YAML_SKILL_SFX_GUIDE.md` 필독
- 새 스킬 SE 추가 시 해당 스킬 YAML `sfx` 필드도 함께 업데이트
- SE 파일 존재 여부 검증: `scripts/verify_skills.py` 실행
- 개별 파일 목록: `ls assets/audio/se/` 로 확인

## Dependencies
### Internal
- `data/skills/*.yaml` — `sfx` 필드에서 이 디렉토리 파일명 참조
- `src/audio/audio_manager.py` — SE 재생
- `docs/YAML_SKILL_SFX_GUIDE.md` — 네이밍 규칙

<!-- MANUAL: -->
