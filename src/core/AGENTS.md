<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# core/

## Purpose
게임 엔진의 핵심 인프라를 담당하는 모듈. 설정 관리, 이벤트 버스, 로깅, 난이도, 진동 피드백, 핫 리로드를 제공한다.

## Key Files

| File | Description |
|------|-------------|
| `event_bus.py` | Pub/Sub 패턴 구현체. `EventBus` 클래스와 전역 `event_bus` 인스턴스, `Events` 상수 클래스 포함. 모든 시스템 간 통신의 중심 |
| `config.py` | YAML 기반 설정 관리. `Config` 클래스로 `config.yaml` 로드. `get_config()` 싱글턴 함수로 접근 |
| `logger.py` | 구조화 로깅 시스템. `Logger` 클래스, `Loggers` 상수(카테고리명), `get_logger(name)` 팩토리 함수 |
| `difficulty.py` | 난이도 시스템. `DifficultyLevel` enum(평온/보통/도전/악몽/지옥), `DifficultyModifiers` dataclass, `DifficultySystem` 클래스 |
| `vibration_system.py` | 게임패드 진동 관리. `VibrationPattern` enum, `VibrationConfig` dataclass, `vibration_manager` 전역 인스턴스 |
| `hot_reload.py` | 개발 모드 핫 리로드. `watchdog` 라이브러리 기반. `check_and_reload()` 함수로 변경 감지 |

## For AI Agents

### Working In This Directory
- `event_bus`는 전역 싱글턴. `event_bus.subscribe(Events.XXX, callback)` / `event_bus.publish(Events.XXX, data)` 패턴 사용
- `Events` 클래스의 상수를 반드시 사용할 것 (문자열 직접 사용 금지)
- `get_config()`, `get_logger()` 팩토리 함수로만 접근 (직접 인스턴스화 금지)
- 새 이벤트 추가 시 `Events` 클래스에 상수 추가 후 사용
- 설정값은 `config.get("section.key", default)` 패턴으로 읽기

### Testing Requirements
- `tests/test_event_bus.py` 또는 상위 `tests/` 확인
- 이벤트 구독/발행은 테스트 후 `event_bus.clear_subscribers()` 정리 필수

### Common Patterns
```python
# 이벤트 구독
from src.core.event_bus import event_bus, Events
event_bus.subscribe(Events.COMBAT_START, self._on_combat_start)

# 설정 읽기
from src.core.config import get_config
config = get_config()
value = config.get("combat.brave.base_brv", 100)

# 로거 사용
from src.core.logger import get_logger, Loggers
logger = get_logger(Loggers.SYSTEM)
logger.info("메시지")
```

## Dependencies

### Internal
- 없음 (다른 src/ 모듈에 의존하지 않는 기반 레이어)

### External
- `yaml` (PyYAML): 설정 파일 파싱
- `watchdog`: 핫 리로드 파일 감시 (선택적)
- `pygame`: 진동 시스템 (게임패드 제어)

<!-- MANUAL: -->
