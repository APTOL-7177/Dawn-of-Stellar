<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# bot

## Purpose
외부 봇 클라이언트를 위해 게임 상태를 JSON 파일로 내보내는 시스템. 현재는 봇 연동 기능이 비활성화되어 있으며(`_export_enabled = False`), 모든 내보내기 호출이 무시된다.

## Key Files
| File | Description |
|------|-------------|
| `game_state_exporter.py` | 게임 상태(전투/탐험)를 `user_data/bot_state.json`으로 내보내는 모듈. 현재 비활성화 상태 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- 봇 기능은 현재 **의도적으로 비활성화**됨 - `_export_enabled = False` 하드코딩
- `enable_export(True)` 호출해도 활성화되지 않음 (함수가 요청을 무시)
- 파일 경로: `user_data/bot_state.json`, `user_data/bot_command.json`, `user_data/enable_bot.txt`
- 봇 기능을 다시 활성화하려면 `_export_enabled = False` 초기값을 `True`로 변경하고 `enable_export()` 함수 로직 복원 필요
- `threading.Lock`으로 파일 쓰기 동기화 - 멀티스레드 안전
- 내보내기 간격: 50ms (`_export_interval = 0.05`)

### Testing Requirements
- 봇 기능 비활성화 상태에서 `export_combat_state()` 호출 시 예외 없이 즉시 반환 확인
- `is_export_enabled()` → 항상 `False` 반환 확인

### Common Patterns
```python
from src.bot.game_state_exporter import export_combat_state, is_export_enabled

# 내보내기 상태 확인 (항상 False)
if is_export_enabled():
    export_combat_state(combat_manager, current_char, screen_text)
```

## Dependencies

### Internal
- `src.core.logger` - 로깅

### External
- `json`, `threading`, `pathlib` - 표준 라이브러리

<!-- MANUAL: -->
