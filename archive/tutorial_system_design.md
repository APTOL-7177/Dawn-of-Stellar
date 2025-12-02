# 튜토리얼 시스템 설계 - Dawn of Stellar

## 개요
초보자와 JRPG에 익숙하지 않은 플레이어를 위한 종합적인 튜토리얼 시스템

## 핵심 목표
1. **단계적 학습**: 기본부터 고급까지 자연스러운 학습 곡선
2. **인터랙티브**: 읽기만 하는 것이 아닌 직접 실행하며 배우기
3. **스킵 가능**: 숙련된 플레이어는 언제든 건너뛸 수 있음
4. **재접근 가능**: 필요할 때 언제든 다시 볼 수 있음
5. **스토리 통합**: 게임 세계관과 자연스럽게 융합

## 튜토리얼 단계

### 1단계: 기본 조작 (Basic Controls)
- **목표**: 게임의 기본적인 조작법 익히기
- **내용**:
  - 방향키로 이동하기
  - 메뉴 열기/닫기 (ESC)
  - 상호작용 (E 키)
  - 대화 진행하기
- **완료 조건**: 특정 위치까지 이동하고 NPC와 대화

### 2단계: 전투 입문 (Combat Basics)
- **목표**: 전투 시스템의 기본 이해
- **내용**:
  - 전투 화면 구성 설명
  - ATB 게이지 개념
  - 기본 공격 실행
  - 적 선택하기
- **완료 조건**: 약한 적 1마리 처치

### 3단계: ATB 시스템 (ATB System)
- **목표**: ATB 게이지 시스템 이해
- **내용**:
  - ATB 게이지가 차는 속도
  - 행동 임계값 (1000)
  - 속도 스탯의 역할
  - 턴 순서 예측
- **완료 조건**: ATB를 활용한 전투 완료

### 4단계: BRV/HP 시스템 (Brave System)
- **목표**: BRV와 HP의 관계 이해
- **내용**:
  - BRV 공격과 HP 공격의 차이
  - BRV 축적의 중요성
  - BREAK 시스템
  - BRV+HP 공격 타이밍
- **완료 조건**: 적을 BREAK 시키고 처치

### 5단계: 스킬 시스템 (Skills)
- **목표**: 다양한 스킬 활용법 익히기
- **내용**:
  - 스킬 타입 (BRV, HP, BRV+HP, 지원, 디버프)
  - MP 관리
  - 스킬 선택 전략
  - 쿨다운과 캐스팅 시간
- **완료 조건**: 3가지 다른 타입의 스킬 사용

### 6단계: 직업 시스템 (Job System)
- **목표**: 직업별 특성과 역할 이해
- **내용**:
  - 28개 직업 개요
  - 직업별 특화 능력
  - 파티 구성의 중요성
  - 직업 간 시너지
- **완료 조건**: 파티원 직업 확인 및 특성 이해

### 7단계: 파티 관리 (Party Management)
- **목표**: 효과적인 파티 운영
- **내용**:
  - 파티 편성
  - 역할 분담 (탱커, 딜러, 힐러, 서포터)
  - 파티원 전환
  - AI 동료 활용
- **완료 조건**: 파티 편성 변경 및 전투 완료

### 8단계: 장비와 인벤토리 (Equipment & Inventory)
- **목표**: 장비 관리 시스템 익히기
- **내용**:
  - 장비 착용/해제
  - 장비 효과 확인
  - 인벤토리 관리
  - 아이템 사용
- **완료 조건**: 장비 변경 및 아이템 사용

### 9단계: 던전 탐험 (Dungeon Exploration)
- **목표**: 던전 탐험 메커니즘 이해
- **내용**:
  - 맵 읽기
  - 층 이동 (계단)
  - 보물 상자 발견
  - 적과의 조우
- **완료 조건**: 1개 층 탐험 완료

### 10단계: 고급 전투 (Advanced Combat)
- **목표**: 전술적 전투 운영
- **내용**:
  - 속성 시스템 (불, 물, 바람, 땅 등)
  - 상태 이상 활용
  - 콤보 시스템
  - 궁극기 사용 타이밍
- **완료 조건**: 고급 전술을 활용한 전투 승리

## 시스템 아키텍처

### 핵심 컴포넌트

#### 1. TutorialManager
```python
class TutorialManager:
    - current_step: TutorialStep
    - progress: Dict[str, bool]
    - is_active: bool
    - can_skip: bool

    Methods:
    - start_tutorial()
    - next_step()
    - skip_tutorial()
    - check_completion_condition()
    - save_progress()
    - load_progress()
```

#### 2. TutorialStep
```python
@dataclass
class TutorialStep:
    id: str
    title: str
    description: str
    objective: str
    completion_condition: Callable
    hints: List[str]
    ui_highlights: List[str]
    next_step: Optional[str]
```

#### 3. TutorialUI
```python
class TutorialUI:
    - show_objective_panel()
    - highlight_ui_element()
    - show_hint()
    - show_completion_message()
    - render_progress_bar()
```

#### 4. TutorialEventHandler
```python
class TutorialEventHandler:
    - on_player_move()
    - on_combat_start()
    - on_skill_use()
    - on_item_use()
    - on_menu_open()
```

### 데이터 구조 (YAML)

```yaml
# data/tutorials/basic_movement.yaml
id: basic_movement
title: "기본 이동"
order: 1
enabled: true

description: |
  Dawn of Stellar의 세계를 탐험하는 첫 걸음!
  방향키를 사용하여 캐릭터를 이동해보세요.

objective: "목표 지점까지 이동하기"

steps:
  - text: "방향키(↑↓←→)를 사용하여 이동할 수 있습니다."
    pause: 2.0
  - text: "밝게 표시된 위치까지 이동해보세요."
    pause: 1.0

hints:
  - "방향키를 눌러 한 칸씩 이동할 수 있습니다."
  - "대각선 이동은 지원되지 않습니다."
  - "벽이나 장애물은 통과할 수 없습니다."

completion_condition:
  type: "player_position"
  target_x: 10
  target_y: 10
  radius: 2

ui_highlights:
  - element: "player"
    color: "yellow"
    pulse: true

rewards:
  exp: 10
  message: "이동 방법을 익혔습니다!"

next_step: "basic_interaction"
```

### 이벤트 통합

튜토리얼은 이벤트 버스를 통해 게임 상태를 모니터링:

```python
# 튜토리얼 진행 이벤트
event_bus.subscribe("player.move", tutorial_manager.on_player_move)
event_bus.subscribe("combat.start", tutorial_manager.on_combat_start)
event_bus.subscribe("skill.execute", tutorial_manager.on_skill_execute)

# 튜토리얼 상태 이벤트
event_bus.publish("tutorial.started", {"step": "basic_movement"})
event_bus.publish("tutorial.step_complete", {"step": "basic_movement"})
event_bus.publish("tutorial.completed", {})
```

### UI 오버레이 시스템

특정 UI 요소를 강조하고 설명하는 오버레이:

```python
class TutorialOverlay:
    def highlight_area(self, x, y, width, height, color):
        """특정 영역을 강조 표시"""

    def draw_arrow(self, from_pos, to_pos):
        """화살표로 가이드"""

    def show_tooltip(self, text, position):
        """툴팁 표시"""

    def dim_background(self, except_area):
        """배경을 어둡게 하고 특정 영역만 밝게"""
```

### 스토리 통합

튜토리얼은 게임 스토리의 일부로 자연스럽게 통합:

```python
# 스토리 시작 시 튜토리얼 트리거
def on_game_start():
    if not player.has_completed_tutorial:
        story_system.show_intro()
        tutorial_manager.start_tutorial()

# 스토리 진행에 따라 새로운 튜토리얼 해금
def on_story_progress(chapter):
    if chapter == 2:
        tutorial_manager.unlock_tutorial("advanced_combat")
```

## 사용자 경험 흐름

```
게임 시작
  ↓
인트로 스토리 (스킵 가능)
  ↓
튜토리얼 시작 여부 선택
  ↓ (예)
1단계: 기본 조작
  ↓ (완료)
2단계: 전투 입문
  ↓ (완료)
...
  ↓
튜토리얼 완료 보상
  ↓
본 게임 시작
```

## 접근성 고려사항

1. **언제든 스킵 가능**: ESC 키로 튜토리얼 종료
2. **단계별 스킵**: 특정 단계만 건너뛰기
3. **속도 조절**: 텍스트 표시 속도 조절 가능
4. **재생 메뉴**: 설정에서 모든 튜토리얼 다시보기
5. **힌트 시스템**: 막힐 때 추가 힌트 제공

## 저장/로드

```python
# 튜토리얼 진행 상태 저장
{
    "tutorial_completed": false,
    "current_step": "combat_basics",
    "completed_steps": [
        "basic_movement",
        "basic_interaction"
    ],
    "skipped": false,
    "last_updated": "2025-11-16T12:00:00"
}
```

## 성능 고려사항

1. **레이지 로딩**: 필요한 튜토리얼만 메모리에 로드
2. **이벤트 정리**: 튜토리얼 종료 시 모든 이벤트 리스너 해제
3. **UI 최적화**: 오버레이는 필요할 때만 렌더링

## 테스트 계획

1. **단위 테스트**: 각 튜토리얼 단계의 완료 조건 검증
2. **통합 테스트**: 전체 튜토리얼 플로우 검증
3. **사용자 테스트**: 실제 초보자의 이해도 측정

## 향후 확장

1. **다국어 지원**: 튜토리얼 텍스트 다국어화
2. **동영상 가이드**: 복잡한 개념은 애니메이션으로 설명
3. **컨텍스트 힌트**: 게임 중 언제든 도움말 표시
4. **적응형 튜토리얼**: 플레이어 숙련도에 따라 자동 조절
