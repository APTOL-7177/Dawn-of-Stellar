<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# quest

## Purpose
플레이어에게 단기/중기 목표를 제공하는 퀘스트 관리 시스템. 다양한 퀘스트 타입(현상금 사냥, 운반, 탐험, 보스 토벌 등)과 난이도, 보상, 진행도 추적을 담당한다.

## Key Files
| File | Description |
|------|-------------|
| `quest_manager.py` | `QuestType`, `QuestDifficulty`, `QuestObjective`, `QuestReward`, `Quest`, `QuestManager` - 전체 퀘스트 시스템 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `QuestType` 종류: BOUNTY_HUNT, DELIVERY, EXPLORATION, BOSS_HUNT, SURVIVAL, SPEED_RUN, COLLECTION, COOKING_QUEST, ALCHEMY_QUEST, NO_DAMAGE
- `QuestDifficulty`: EASY, NORMAL, HARD, LEGENDARY
- `QuestObjective` 구조: `description`, `target`(적 ID/아이템 ID/층번호), `current`, `required`
  - `is_complete` 프로퍼티: `current >= required`
  - `progress_text` 프로퍼티: `"current/required"` 형식
- `QuestReward` 구조: 골드, 경험치, 아이템, 별의 파편
- 퀘스트 UI는 `src/ui/quest_board_ui.py`, `src/ui/quest_list_ui.py` 참조
- `QuestManager`는 활성 퀘스트 목록 관리, 진행도 업데이트, 완료 처리

### Testing Requirements
- `QuestObjective.is_complete`, `progress_text` 프로퍼티 단위 테스트
- 퀘스트 진행도 업데이트 → 완료 전환 테스트
- 난이도별 보상 차등 확인

### Common Patterns
```python
from src.quest.quest_manager import QuestManager, QuestType, QuestDifficulty

manager = QuestManager()
quests = manager.generate_quests(floor=5, count=3)
manager.update_progress("bounty_hunt", target="goblin", count=1)
completed = manager.check_completions()
```

## Dependencies

### Internal
- `src.core.logger` - 로깅

### External
- `enum`, `dataclasses`, `typing`, `random` - 표준 라이브러리

<!-- MANUAL: -->
