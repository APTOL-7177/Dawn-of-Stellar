<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# core - 핵심 유틸리티

## Purpose

게임 핵심 시스템을 관리하는 유틸리티 모듈. 설정 로딩, 로깅, 이벤트 버스, 진동 시스템, 경로 해석, 자동 업데이트를 포함합니다.

## Key Files

| File | Description |
|------|-------------|
| `config.py` | 게임 설정 로딩 및 관리 (게임패드, 키 바인딩, 난이도) |
| `logger.py` | 구조화된 로깅 시스템 (DEBUG, INFO, WARNING, ERROR) |
| `event_bus.py` | 게임 이벤트 발행-구독 패턴 |
| `vibration_system.py` | 진동/럼블 피드백 (DualSense, Xbox 컨트롤러) |
| `paths.py` | 프로젝트 경로 해석 (data/, config/, assets/) |
| `updater.py` | 자동 업데이트 및 버전 관리 |
| `difficulty.py` | 난이도 설정 및 게임 밸런싱 |
| `hot_reload.py` | 개발 중 핫 리로드 기능 |

## For AI Agents

### Working In This Directory

- **설정 추가**: `config.py`에서 Config 클래스 수정
- **로그 추가**: `logger.py`의 log_*() 메서드 사용
- **이벤트 추가**: `event_bus.py`의 emit() / subscribe() 패턴
- **경로 조회**: `paths.py`의 get_*_path() 함수 사용
- **진동 피드백**: `vibration_system.py`의 vibrate() 메서드

### Testing Requirements

- 설정 로드 테스트: `test_config_loading()`
- 이벤트 버스 테스트: 발행/구독 동작 확인
- 경로 해석 테스트: 모든 OS에서 경로 정확성 확인
- 로그 레벨 테스트: 각 레벨의 출력 확인

### Common Patterns

- 싱글톤 패턴 (Logger, EventBus)
- 설정 캐싱 (초기화 시 로드, 메모리 저장)
- 이벤트 핸들러 체인 (여러 리스너 지원)
- 경로 정규화 (OS별 슬래시 처리)

## Dependencies

### Internal
- `config.yaml` - 게임 설정 파일
- `config/key_bindings.yaml` - 키 바인딩
- `config/gamepad_mappings.yaml` - 게임패드 매핑
- `config/vibration.yaml` - 진동 강도 설정

### External
- `pyyaml` - YAML 설정 파싱
- `pygame` - 게임패드 입력
- `requests` - 업데이트 확인 (updater.py)

<!-- MANUAL: -->
