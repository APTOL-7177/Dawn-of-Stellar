<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# config/

## Purpose
게임 설정 파일 디렉토리입니다. 키 바인딩, 게임패드 매핑, 진동 설정, 메타 진행도 데이터를 YAML 및 JSON 형식으로 관리합니다.

## Key Files
| File | Description |
|------|-------------|
| key_bindings.yaml | 키보드 입력 바인딩 (이동, 메뉴, 액션) |
| gamepad_mappings.yaml | 게임패드 버튼 매핑 (PS4/DualSense 컨트롤러) |
| vibration.yaml | 진동 피드백 설정 및 강도 구성 |
| meta_progress.json | 메타 진행도: 업적, 미션, 글로벌 통계 |

## Subdirectories
없음

## For AI Agents

### Working In This Directory
- 설정 파일 추가/수정 시 YAML/JSON 구문 검증 필요
- 키 바인딩 변경 시 src/ui/input_handler.py와 동기화 확인
- 메타 진행도는 src/persistence/meta_progress.py에서 로드됨

### Common Patterns
- YAML 설정 → src/core/config.py의 Config 클래스에서 로드
- JSON은 저장/로드 직렬화용 (persistence 시스템)
- 게임패드 설정은 src/ui/input_handler.py의 GamepadInput 클래스 참조

## Dependencies
- src/core/config.py (설정 로더)
- src/ui/input_handler.py (입력 처리)
- src/persistence/meta_progress.py (메타 진행도)

<!-- MANUAL: -->
