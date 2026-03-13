<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# UI 시스템

## 목적
게임의 모든 사용자 인터페이스를 관리하는 핵심 시스템. 50개 이상의 UI 모듈을 통해 전투, 메뉴, 인벤토리, 상점, 멀티플레이, 튜토리얼 등 게임의 모든 화면을 구성합니다. Pygame 기반 커스텀 렌더링 백엔드(pygame_backend/)와 TCOD 디스플레이 시스템을 포함합니다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| combat_ui.py | 전투 화면: HP/MP 게이지, 스킬 선택, 행동 예측 |
| world_ui.py | 월드 맵 렌더링, FOV, 던전 표시 |
| main_menu.py | 게임 메인 메뉴 (게임 시작, 로드, 설정) |
| game_menu.py | 게임 중 메뉴 (저장, 로드, 아이템, 설정) |
| inventory_ui.py | 인벤토리 관리, 아이템 정렬, 장비 변경 |
| shop_ui.py | 상점 시스템 (구매/판매) |
| party_setup.py | 파티 구성 (캐릭터 선택, 공격대형) |
| loot_ui.py | 전리품 수집 UI |
| game_result_ui.py | 전투 결과 화면 |
| cooking_ui.py | 요리 시스템 UI |
| gathering_ui.py | 채집 UI |
| alchemy_ui.py | 연금술 UI |
| quest_board_ui.py | 퀘스트 게시판 |
| quest_list_ui.py | 진행 중인 퀘스트 목록 |
| npc_dialog_ui.py | NPC 대사창 |
| multiplayer_menu.py | 멀티플레이 메뉴 |
| multiplayer_lobby.py | 멀티플레이 로비 |
| multiplayer_party_setup.py | 멀티플레이 파티 설정 |
| multiplayer_join_ui.py | 멀티플레이 참여 UI |
| key_bindings_ui.py | 키바인딩 설정 |
| settings_ui.py | 게임 설정 |
| save_load_ui.py | 저장/로드 |
| trait_selection.py | 특성 선택 UI |
| passive_selection.py | 패시브 스킬 선택 |
| possibility_selection_ui.py | 가능성(특수능력) 선택 |
| gauge_renderer.py | 게이지(HP/MP/상태) 렌더러 |
| input_handler.py | 입력 처리 시스템 |
| tcod_display.py | TCOD 디스플레이 백엔드 |
| pygame_backend/ | Pygame 커스텀 렌더링 시스템 (서브시스템) |

## AI 에이전트를 위한 가이드
### 이 디렉토리에서 작업할 때
- UI 모듈들은 각각 독립적인 화면을 구현합니다.
- 모든 UI는 `tcod` 라이브러리 또는 `pygame_backend`를 통해 렌더링됩니다.
- 입력은 `input_handler.py`를 통해 처리되며, 게임 상태와 동기화됩니다.
- UI 모듈들은 `src/character`, `src/combat`, `src/equipment`, `src/multiplayer` 등과 밀접하게 연계됩니다.

### 테스트 요구사항
- UI 렌더링 변경은 시각적 검증이 필요합니다.
- 입력 처리 변경은 키보드/게임패드 입력 시뮬레이션으로 검증합니다.
- 멀티플레이 UI는 네트워크 동기화를 포함하여 검증합니다.

### 일반적인 패턴
- UI 클래스는 `__init__`, `handle_input()`, `update()`, `render()` 메서드를 구현합니다.
- 게임 상태는 참조로 전달되며, UI는 상태 변경을 추적합니다.
- 메뉴 내비게이션은 커서 위치와 선택 상태로 관리됩니다.

## 의존성
### 내부
- `src/character/` - 캐릭터 데이터, 직업, 스킬
- `src/combat/` - 전투 상태, ATB 시스템
- `src/equipment/` - 인벤토리, 장비
- `src/multiplayer/` - 멀티플레이 상태 동기화
- `src/tutorial/` - 튜토리얼 오버레이
- `src/ui/pygame_backend/` - Pygame 렌더링 백엔드
- `src/world/` - 맵 렌더링, FOV
- `src/gathering/`, `src/cooking/`, `src/quest/` - 시스템별 UI

### 외부
- `tcod` - 콘솔 렌더링 라이브러리
- `pygame` - Pygame 백엔드
- `pydantic` - 데이터 검증

<!-- MANUAL: -->
