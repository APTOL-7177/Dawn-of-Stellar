# 튜토리얼 시스템 사용 가이드

## 개요
Dawn of Stellar의 튜토리얼 시스템은 초보자들이 게임을 쉽게 배울 수 있도록 도와주는 자동화된 시스템입니다.

## 주요 기능
- ✅ **단계별 학습**: 기본 조작부터 고급 전투까지
- ✅ **인터랙티브**: 실제로 행동하며 배우기
- ✅ **스킵 가능**: 언제든 건너뛸 수 있음
- ✅ **힌트 시스템**: 막혔을 때 자동으로 도움말 표시
- ✅ **스토리 통합**: 게임 세계관과 자연스럽게 융합
- ✅ **진행 상태 저장**: 중단했다가 다시 시작 가능

## 빠른 시작

### 1. 예제 실행
```bash
# 튜토리얼 시스템 빠른 테스트
python examples/tutorial_example.py
```

### 2. 메인 게임에 통합

```python
from src.tutorial.tutorial_integration import show_tutorial_intro_with_story

# 게임 시작 시
integration = show_tutorial_intro_with_story(
    console,
    context,
    skip_intro_story=False  # 인트로 스토리 표시
)

# 메인 게임 루프에서
while running:
    # 이벤트 처리
    for event in tcod.event.wait(timeout=0.016):
        # 튜토리얼 입력 처리
        if integration.handle_tutorial_input(event):
            continue  # 튜토리얼이 처리했으면 건너뜀

        # 일반 게임 입력 처리
        handle_game_input(event)

    # 튜토리얼 업데이트
    integration.update_tutorial(delta_time)

    # 게임 렌더링
    render_game(console)

    # 튜토리얼 UI 렌더링
    integration.render_tutorial_ui()

    # 화면 업데이트
    context.present(console)
```

## 튜토리얼 단계

### 기본 조작 (Basics)
1. **기본 이동** - 방향키로 이동하기
2. **기본 상호작용** - NPC와 대화, 메뉴 열기

### 전투 시스템 (Combat)
3. **전투 입문** - 첫 전투 경험
4. **ATB 시스템** - Active Time Battle 이해
5. **BRV/HP 시스템** - Brave 메커니즘과 BREAK
6. **스킬 시스템** - 다양한 스킬 활용

### 관리 시스템 (Management)
7. **직업 시스템** - 33개 직업 이해
8. **파티 관리** - 파티 구성과 역할 분담
9. **장비와 인벤토리** - 장비 관리

### 탐험 (Exploration)
10. **던전 탐험** - 던전 메커니즘

## 새 튜토리얼 추가하기

### 1. YAML 파일 생성
`data/tutorials/XX_new_tutorial.yaml` 파일을 생성:

```yaml
id: new_tutorial
title: "새 튜토리얼"
order: 11
category: advanced
enabled: true
skippable: true

description: |
  새로운 기능을 배웁니다.

objective: "특정 행동 완료하기"

messages:
  - text: "환영합니다!"
    color: [255, 255, 255]
    pause: 2.0
    effect: "typing"

completion_condition:
  type: "position_reached"
  target_x: 5
  target_y: 5
  radius: 1
  message: "완료했습니다!"

hints:
  - text: "힌트 메시지"
    trigger_time: 10.0

ui_highlights:
  - element: "target"
    color: [255, 255, 0]
    pulse: true
    description: "목표"

rewards:
  exp: 100
  gold: 50
  message: "훌륭합니다!"

next_step: null  # 다음 단계 ID
```

### 2. 설정 파일 업데이트
`data/tutorials/tutorial_config.yaml`의 `tutorial_order`에 추가:

```yaml
tutorial_order:
  - basic_movement
  - basic_interaction
  # ... 기존 단계들
  - new_tutorial  # 새 단계 추가
```

### 3. 자동 로드
튜토리얼 매니저가 자동으로 로드합니다!

## 완료 조건 타입

### 1. `position_reached` - 위치 도달
```yaml
completion_condition:
  type: "position_reached"
  target_x: 10
  target_y: 10
  radius: 1
```

### 2. `npc_interaction` - NPC 상호작용
```yaml
completion_condition:
  type: "npc_interaction"
  npc_id: "tutorial_guide"
```

### 3. `combat_victory` - 전투 승리
```yaml
completion_condition:
  type: "combat_victory"
  enemy_count: 1
  allow_escape: false
```

### 4. `action_count` - 행동 횟수
```yaml
completion_condition:
  type: "action_count"
  required_actions: 3
  combat_required: true
```

### 5. `skill_usage_variety` - 다양한 스킬 사용
```yaml
completion_condition:
  type: "skill_usage_variety"
  required_skill_types:
    - "brv_attack"
    - "hp_attack"
    - "support"
```

### 6. `combat_action_sequence` - 특정 행동 순서
```yaml
completion_condition:
  type: "combat_action_sequence"
  required_sequence:
    - action: "brv_attack"
      result: "break_enemy"
    - action: "hp_attack"
      target: "same_enemy"
```

## 이벤트

튜토리얼 시스템은 다음 이벤트를 발행합니다:

```python
# 튜토리얼 시작
"tutorial.started" -> {"tutorial_id": str, "title": str}

# 단계 완료
"tutorial.step_complete" -> {"tutorial_id": str, "title": str, "rewards": dict}

# 모든 튜토리얼 완료
"tutorial.all_complete" -> {"completed_count": int}

# 튜토리얼 건너뜀
"tutorial.skipped_all" -> {}
```

이벤트를 구독하여 커스텀 로직을 추가할 수 있습니다:

```python
from src.core.event_bus import event_bus

def on_tutorial_complete(data):
    print(f"튜토리얼 완료: {data['title']}")
    # 보상 지급, 통계 업데이트 등

event_bus.subscribe("tutorial.step_complete", on_tutorial_complete)
```

## 설정

`data/tutorials/tutorial_config.yaml`에서 설정 가능:

```yaml
global:
  enabled: true              # 튜토리얼 시스템 활성화
  auto_start: true          # 신규 플레이어 자동 시작
  can_skip_all: true        # 전체 스킵 허용
  can_skip_individual: true # 개별 단계 스킵 허용
  show_hints: true          # 힌트 표시
  hint_delay: 10.0          # 힌트 대기 시간 (초)

ui:
  overlay_opacity: 0.7      # 오버레이 투명도
  highlight_pulse_speed: 1.0 # 강조 펄스 속도
  text_speed: 0.05          # 텍스트 속도 (초/글자)
```

## 테스트

```bash
# 단위 테스트 실행
pytest tests/unit/tutorial/ -v

# 특정 테스트만 실행
pytest tests/unit/tutorial/test_tutorial_manager.py::TestTutorialManager::test_start_tutorial -v

# 커버리지 포함
pytest tests/unit/tutorial/ --cov=src/tutorial --cov-report=html
```

## 문제 해결

### 튜토리얼이 로드되지 않음
- `data/tutorials/` 디렉토리가 존재하는지 확인
- YAML 파일 문법이 올바른지 확인
- 로그 확인: `logs/system.log`

### 완료 조건이 작동하지 않음
- `game_state`가 올바르게 업데이트되는지 확인
- 이벤트가 발행되는지 확인
- 완료 조건 파라미터 확인

### UI가 표시되지 않음
- `integration.render_tutorial_ui()`가 호출되는지 확인
- 콘솔 크기가 충분한지 확인 (최소 80x40 권장)

## 향후 계획

- [ ] 동영상 가이드 (애니메이션)
- [ ] 다국어 지원
- [ ] 적응형 튜토리얼 (플레이어 숙련도 추적)
- [ ] 컨텍스트 힌트 (게임 중 언제든 도움말)
- [ ] 튜토리얼 에디터 (GUI)

## 라이선스

이 튜토리얼 시스템은 Dawn of Stellar 프로젝트의 일부입니다.
