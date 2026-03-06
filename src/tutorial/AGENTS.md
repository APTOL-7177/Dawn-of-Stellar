<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tutorial

## Purpose
YAML 기반의 다단계 튜토리얼 시스템. 이동, 상호작용, 전투, ATB/Brave 시스템, 스킬/직업 소개 등 7개 단계를 관리하며, 스토리와 통합된 플레이어블 튜토리얼도 제공한다.

## Key Files
| File | Description |
|------|-------------|
| `tutorial_manager.py` | `TutorialManager` - YAML 로드, 튜토리얼 진행 상태 추적, 이벤트 버스 통합 |
| `tutorial_step.py` | `CompletionType` Enum, `TutorialMessage`, `TutorialHint`, `UIHighlight`, `CompletionCondition`, `TutorialReward`, `TutorialStep` 데이터클래스 |
| `tutorial_mode.py` | `TutorialModeConfig` - 튜토리얼 난이도 설정 (적 HP 50%, 플레이어 HP 130% 등) |
| `tutorial_dungeon.py` | 튜토리얼 전용 던전 생성 |
| `tutorial_playable.py` | 플레이어블 튜토리얼 실행 로직 |
| `story_integration.py` | 스토리 튜토리얼 통합 |
| `story_runner.py` | 스토리 시퀀스 실행 |
| `story_tutorial_manager.py` | 스토리+튜토리얼 통합 매니저 |
| `tutorial_ui.py` | 튜토리얼 UI 렌더링 |
| `tutorial_viewer.py` | 튜토리얼 뷰어 |
| `job_selection_ui.py` | 튜토리얼 직업 선택 UI |
| `tutorial_integration.py` | 메인 게임과의 통합 진입점 |
| `tutorial_bot.py` | 튜토리얼 자동화 봇 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- 튜토리얼 데이터: `data/tutorials/*.yaml` (7개 단계 + config)
  - `01_basic_movement.yaml`, `02_basic_interaction.yaml`, `03_combat_intro.yaml`
  - `04_atb_system.yaml`, `05_brave_system.yaml`, `06_skill_system.yaml`, `07_job_system.yaml`
- `CompletionType` 종류: POSITION_REACHED, NPC_INTERACTION, COMBAT_VICTORY, ACTION_COUNT, SKILL_USAGE_VARIETY, COMBAT_ACTION_SEQUENCE, MENU_OPENED, ITEM_USED, EQUIPMENT_CHANGED, AUTO_COMPLETE, DIALOGUE_COMPLETE, ENEMY_DEFEATED, ATB_ACTION, JOB_GIMMICK_USED, PARTY_MEMBER_ADDED, PARTY_SIZE, ITEM_RECEIVED, EQUIPMENT_EQUIPPED, PASSIVE_EQUIPPED, DUNGEON_ENTERED, BOSS_DEFEATED, CHECKLIST_COMPLETE
- `TutorialModeConfig`: 적 HP/공격 50%, BRV 70%, 플레이어 HP 130%, MP 150% - 15층 목표
- `TutorialManager.is_active`, `current_step`, `completed_tutorials`, `skipped` 상태 관리
- 이벤트 버스 구독으로 게임 이벤트 수신 → 튜토리얼 진행도 자동 업데이트
- `MetaProgress.tutorial_completed = True`이면 튜토리얼 재입장 불가

### Testing Requirements
- YAML 로드 실패 처리 (파일 없음, 잘못된 형식)
- `CompletionCondition` 각 타입별 완료 조건 검증
- 튜토리얼 skip 처리 확인

### Common Patterns
```python
from src.tutorial.tutorial_manager import TutorialManager

manager = TutorialManager(data_dir="data/tutorials")
manager.start()
# 이벤트 발생 시 자동으로 진행도 업데이트됨
if manager.current_step:
    print(manager.current_step.messages)
```

## Dependencies

### Internal
- `src.core.event_bus` - 게임 이벤트 수신
- `src.core.logger` - 로깅
- `src.persistence.meta_progress` - 튜토리얼 완료 여부 영구 저장

### External
- `yaml`, `pathlib`, `typing` - 표준 라이브러리 + PyYAML

<!-- MANUAL: -->
