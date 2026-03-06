<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# story

## Purpose
시공교란 컨셉의 게임 스토리를 관리하는 간소화 시스템. 보스 조우/처치 플래그를 추적하고, 오프닝/보스 조우 스토리 시퀀스를 `StorySegment` 리스트로 제공한다.

## Key Files
| File | Description |
|------|-------------|
| `story_system.py` | `StorySegment` 데이터클래스, `StorySystem` 클래스, `get_story_system()` 싱글톤 - 스토리 플래그 및 컷씬 시퀀스 관리 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `StorySystem`은 싱글톤 - `get_story_system()`으로 전역 접근
- 주요 플래그:
  - `sephiroth_encountered`, `sephiroth_defeated`, `true_ending_unlocked`, `glitch_mode`
  - `cain_defeated`
- 보스 플로어 트리거: 20층 = 세피로스 조우, 30층 = 카인 조우 (`main.py` 참조)
- 스토리 렌더링: `src/ui/npc_dialog_ui.py`의 `render_story_sequence(console, context, story, logger)` 사용
- `StorySegment` 구조: `text`, `pause`(초), `color`
- `is_glitch_mode()`: 세피로스 조우 후 처치 전 → 글리치 시각 효과 활성화
- `is_true_ending_mode()`: 세피로스 처치 후 → 진 엔딩 모드
- 스토리 메서드: `get_opening_story()`, `get_sephiroth_encounter_story()`, `get_cain_encounter_story()`

### Testing Requirements
- 플래그 상태 전환 검증: `set_sephiroth_encountered()` → `glitch_mode=True`
- `is_glitch_mode()` 로직 테스트 (조우 O, 처치 X → True)
- `is_true_ending_mode()` 로직 테스트

### Common Patterns
```python
from src.story.story_system import get_story_system
from src.ui.npc_dialog_ui import render_story_sequence

story_system = get_story_system()
# 보스 조우 처리
story_system.set_sephiroth_encountered()
encounter_story = story_system.get_sephiroth_encounter_story()
render_story_sequence(console, context, encounter_story, logger)
```

## Dependencies

### Internal
- `src.ui.npc_dialog_ui` - `render_story_sequence()` (스토리 렌더링)

### External
- `dataclasses`, `typing` - 표준 라이브러리

<!-- MANUAL: -->
