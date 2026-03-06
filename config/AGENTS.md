<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# config/

## Purpose
런타임 입력 설정 및 사용자 데이터를 보관한다. 게임패드/키보드 매핑, 진동 설정, 메타 진행 저장 데이터 4개 파일로 구성된다.

## Key Files
| File | Description |
|------|-------------|
| `key_bindings.yaml` | 키보드 키 바인딩 설정 |
| `gamepad_mappings.yaml` | 게임패드 버튼 매핑 설정 |
| `vibration.yaml` | 진동 강도/패턴 설정 |
| `meta_progress.json` | 플레이어 메타 진행 데이터 (런타임 생성/수정) |

## For AI Agents
### Working In This Directory
- `meta_progress.json` 은 런타임에 게임이 직접 수정함 — 수동 편집 주의
- 키 바인딩 변경 시 `src/core/config.py` 와 동기화 확인
- 게임패드 테스트: `scripts/test_gamepad.py`, `scripts/quick_gamepad_test.py`
- 진동 시스템 참조: `src/core/vibration_system.py`

## Dependencies
### Internal
- `src/core/config.py` — 설정 파일 로드
- `src/core/vibration_system.py` — vibration.yaml 사용
- `src/persistence/meta_progress.py` — meta_progress.json 읽기/쓰기
### External
- PyYAML, json (표준 라이브러리)

<!-- MANUAL: -->
