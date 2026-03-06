<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# ui

## Purpose
tcod(libtcod) 기반 콘솔 렌더링으로 게임의 모든 화면을 담당하는 UI 컴포넌트 모음. 메인 메뉴부터 전투, 인벤토리, 상점, 퀘스트, 멀티플레이어 로비까지 53개 파일로 구성된다.

## Key Files

### 핵심 게임 화면
| File | Description |
|------|-------------|
| `world_ui.py` | `WorldUI` - 탐험 맵 렌더링 및 입력 처리. 전투/층 이동 요청 반환. 가장 큰 파일(2507줄) |
| `combat_ui.py` | `run_combat()`, `CombatState` - ATB 전투 화면, 스킬 선택, 적 타깃팅 |
| `main_menu.py` | 타이틀 화면 - 신규/이어하기/멀티플레이어/설정/종료 |
| `game_menu.py` | 인게임 일시정지 메뉴 |
| `game_result_ui.py` | 게임 오버/클리어 결과 화면 |
| `tcod_display.py` | tcod `Console`/`Context` 초기화 및 관리 |

### 인벤토리 / 아이템
| File | Description |
|------|-------------|
| `inventory_ui.py` | 인벤토리 화면 - 아이템 목록, 장착, 사용 |
| `loot_ui.py` | 전투 후 전리품 획득 화면 |
| `storage_ui.py` | 마을 창고 아이템 관리 |
| `quantity_selector_ui.py` | 아이템 수량 선택 팝업 |
| `reward_ui.py` | 퀘스트/보스 보상 표시 |

### 상점 / 제작
| File | Description |
|------|-------------|
| `shop_ui.py` | 일반 상점 - 아이템 구매/판매 |
| `gold_shop_ui.py` | 골드 전용 상점 |
| `anvil_ui.py` | 대장간 - 장비 강화 |
| `alchemy_ui.py` | 연금술 실험실 - 포션 제작 |
| `cooking_ui.py` | 요리솥 UI - `open_cooking_pot()` 진입점 |
| `gathering_ui.py` | 채집 UI - `harvest_object()` 진입점 |

### 캐릭터 / 파티
| File | Description |
|------|-------------|
| `party_setup.py` | 파티 구성 화면 |
| `passive_selection.py` | 패시브 스킬 선택 |
| `trait_selection.py` | 특성 선택 화면 |
| `possibility_selection_ui.py` | 가능성(업그레이드) 선택 |

### 퀘스트 / NPC
| File | Description |
|------|-------------|
| `quest_board_ui.py` | 퀘스트 게시판 |
| `quest_list_ui.py` | 수락한 퀘스트 목록 |
| `npc_dialog_ui.py` | NPC 대화 및 `render_story_sequence()` - 스토리 컷씬 렌더링 |
| `guild_hall_ui.py` | 길드 홀 인터페이스 |
| `rest_ui.py` | 여관 휴식 화면 |

### 필드 스킬
| File | Description |
|------|-------------|
| `field_skill_menu.py` | 필드 스킬 선택 메뉴 |
| `field_skill_ui.py` | 필드 스킬 사용 화면 |

### 멀티플레이어
| File | Description |
|------|-------------|
| `multiplayer_menu.py` | 멀티플레이어 메인 메뉴 |
| `multiplayer_lobby.py` | 멀티플레이어 로비 |
| `multiplayer_join_ui.py` | 게임 참가 화면 |
| `multiplayer_party_setup.py` | 멀티플레이어 파티 구성 |
| `multiplayer_character_reassignment_ui.py` | 멀티플레이어 캐릭터 재배정 |

### 전투 보조
| File | Description |
|------|-------------|
| `teamwork_battle_ui.py` | 팀워크 전투 UI |
| `teamwork_gauge_display.py` | 팀워크 게이지 렌더링 |
| `gauge_renderer.py` | HP/MP/BRV 게이지 렌더링 유틸리티 |
| `gauge_tileset.py` | 게이지용 타일셋 정의 |
| `cursor_menu.py` | 커서 기반 메뉴 공통 컴포넌트 |

### 기타
| File | Description |
|------|-------------|
| `intro_story.py` | 인트로 스토리 컷씬 |
| `credits_ui.py` | 크레딧 화면 |
| `settings_ui.py` | 설정 화면 |
| `key_bindings_ui.py` | 키 바인딩 설정 |
| `save_load_ui.py` | 저장/불러오기 화면 |
| `difficulty_selection_ui.py` | 난이도 선택 |
| `training_mode.py` | 훈련 모드 UI |
| `boss_test_mode.py` | 보스 테스트 모드 UI |
| `input_handler.py` | tcod 입력 이벤트 → `GameAction` 변환 |
| `ai_bug_hunter.py` | AI 버그 헌터 도구 |
| `ai_spectate_mode.py` | AI 관전 모드 |
| `bot_help_ui.py` | 봇 도움 UI |
| `shop_ui_old.py` | 구버전 상점 UI (레거시, 참조 금지) |
| `intro_story_old.py` | 구버전 인트로 (레거시, 참조 금지) |

## For AI Agents

### Working In This Directory
- 모든 렌더링은 tcod `Console`과 `Context` 객체를 인자로 받음
- `GameAction` Enum은 `src/ui/input_handler.py`에서 정의 - CONFIRM(Z/Enter), CANCEL(X/Esc), 방향키 등
- `WorldUI`는 `run_exploration(console, context, exploration, inventory, party, ...)` 반환값이 `("combat", data)` 또는 `("town", ...)` 등 튜플 형식
- `run_combat(console, context, ...)` 반환값: `CombatState` 또는 결과 딕셔너리
- `render_story_sequence(console, context, story_segments, logger)`: 스토리 컷씬 순차 렌더링
- `_old` 접미사 파일은 레거시 - 새 코드에서 import 금지
- 대부분의 UI 함수는 순수 함수 형태 (상태 없음) 또는 클래스 메서드

### Testing Requirements
- UI는 tcod 환경이 필요하여 자동화 테스트 어려움
- `boss_test_mode.py`, `training_mode.py`로 특정 전투 상황 수동 테스트 가능
- `ai_bug_hunter.py`로 자동 버그 탐지

### Common Patterns
```python
# 탐험 실행
from src.ui.world_ui import run_exploration
result = run_exploration(console, context, exploration, inventory=inv, party=party)
if result == ("combat", data):
    ...

# 전투 실행
from src.ui.combat_ui import run_combat, CombatState
combat_result = run_combat(console, context, party, enemies, ...)

# 스토리 렌더링
from src.ui.npc_dialog_ui import render_story_sequence
render_story_sequence(console, context, story_segments, logger)

# 요리솥 열기
from src.ui.cooking_ui import open_cooking_pot
open_cooking_pot(console, context, inventory, is_cooking_pot=True)

# 채집
from src.ui.gathering_ui import harvest_object
success = harvest_object(console, context, harvestable, inventory, exploration=exploration)
```

## Dependencies

### Internal
- `src.combat.*` - 전투 시스템 (combat_ui)
- `src.equipment.*` - 인벤토리/아이템
- `src.gathering.*` - 채집 오브젝트
- `src.cooking.*` - 요리 레시피
- `src.quest.*` - 퀘스트
- `src.story.*` - 스토리 시퀀스
- `src.audio.*` - BGM/SFX
- `src.core.*` - 설정, 로거, 이벤트 버스
- `src.multiplayer.*` - 멀티플레이어 네트워크

### External
- `tcod` (libtcod) - 콘솔 렌더링 엔진
- `pygame` - 이벤트 처리 (pygame.event.pump)

<!-- MANUAL: -->
