# 보스 대사 시스템 구현 가이드

## 프로젝트 개요
세피로스와 카인의 상황별 대사 시스템 구현 및 림버스 컴퍼니 스타일의 랜덤 위치 떠다니는 대사 효과 추가

---

## 완료된 작업

### 1. ✅ boss_dialogue.py 생성 (완료)
**파일**: `src/combat/boss_dialogue.py`

**내용**:
- 세피로스와 카인의 상황별 대사 딕셔너리 정의
- `get_dialogue(boss_id, situation)`: 상황에 맞는 대사 랜덤 선택
- `print_dialogue(logger, dialogue)`: 붉은색 텍스트로 로그에 출력 (`\033[91m`)

**정의된 상황**:
- `combat_start`: 전투 시작 (✓ 구현됨)
- `preemptive_strike`: 카인 선제공격 (✓ 구현됨)
- `preemptive_strike_survival`: 선제공격 생존 시 (✓ 구현됨)
- `phase_2_transition`: 페이즈 2 전환 (66% HP 이하)
- `phase_3_transition`: 페이즈 3 전환 (33% HP 이하)
- `break_received`: BREAK 당했을 때
- `break_counterattack`: BREAK 반격 (✓ 구현됨)
- `strong_attack`: 강한 공격 사용
- `low_hp`: 보스 HP 낮음 (30% 이하)
- `player_low_hp`: 플레이어 HP 낮음 (30% 이하)
- `player_death`: 플레이어 사망
- `ultimate`: 궁극기 사용

### 2. ✅ combat_manager.py 부분 수정 (완료)

#### 2-1. start_combat() - 보스 페이즈 추적 초기화
**위치**: `src/combat/combat_manager.py` 라인 264-278

```python
# 보스 전투 시작 대사
for enemy in self.enemies:
    boss_id = getattr(enemy, 'enemy_id', None)
    if boss_id in ['sephiroth', 'abel_cain']:
        # 페이즈 추적을 위한 속성 초기화
        enemy._current_phase = 1
        enemy._low_hp_dialogue_shown = False

        dialogue = boss_dialogue.get_dialogue(boss_id, "combat_start")
        if dialogue:
            boss_dialogue.print_dialogue(self.logger, dialogue)
```

#### 2-2. 이미 구현된 대사
- ✅ `combat_start`: start_combat()에서 호출 (라인 276-278)
- ✅ `preemptive_strike`: _execute_cain_preemptive_strike()에서 호출 (라인 1609)
- ✅ `preemptive_strike_survival`: _execute_cain_preemptive_strike()에서 호출 (라인 1647)
- ✅ `break_counterattack`: _execute_break_counterattack()에서 호출 (라인 1588-1593)

---

## 미완료 작업 (다음 에이전트가 구현할 내용)

### 3. ⚠️ 턴 시작 시 대사 체크 (미구현)

**구현 위치**: `src/combat/combat_manager.py`의 `GimmickUpdater.on_turn_start(actor, context)` 호출 직후 (약 라인 575 이후)

**구현 내용**:
```python
# GimmickUpdater.on_turn_start(actor, context) 이후에 추가

# === 보스 대사: 페이즈 전환, low_hp, player_low_hp 체크 ===
if hasattr(actor, 'enemy_id') and actor.enemy_id in ['sephiroth', 'abel_cain']:
    from src.combat.boss_dialogue import get_boss_dialogue
    boss_dialogue = get_boss_dialogue()

    # 1. 페이즈 전환 체크
    hp_percent = actor.current_hp / actor.max_hp if actor.max_hp > 0 else 0
    current_phase = 1
    if hp_percent < 0.33:
        current_phase = 3
    elif hp_percent < 0.66:
        current_phase = 2

    previous_phase = getattr(actor, '_current_phase', 1)
    if current_phase > previous_phase:
        # 페이즈 전환 발생
        if current_phase == 2:
            dialogue = boss_dialogue.get_dialogue(actor.enemy_id, "phase_2_transition")
            if dialogue:
                boss_dialogue.print_dialogue(self.logger, dialogue)
        elif current_phase == 3:
            dialogue = boss_dialogue.get_dialogue(actor.enemy_id, "phase_3_transition")
            if dialogue:
                boss_dialogue.print_dialogue(self.logger, dialogue)
        actor._current_phase = current_phase

    # 2. 보스 HP 낮음 대사 (30% 이하, 한 번만 출력)
    if hp_percent <= 0.3 and not getattr(actor, '_low_hp_dialogue_shown', False):
        dialogue = boss_dialogue.get_dialogue(actor.enemy_id, "low_hp")
        if dialogue:
            boss_dialogue.print_dialogue(self.logger, dialogue)
            actor._low_hp_dialogue_shown = True

# 아군 턴 시작 시 플레이어 HP 체크
if actor in self.allies:
    # 보스가 살아있는지 확인
    boss = None
    for enemy in self.enemies:
        if hasattr(enemy, 'enemy_id') and enemy.enemy_id in ['sephiroth', 'abel_cain']:
            if getattr(enemy, 'is_alive', True):
                boss = enemy
                break

    if boss:
        # 플레이어 HP 낮음 대사 (30% 이하)
        hp_percent = actor.current_hp / actor.max_hp if actor.max_hp > 0 else 0
        if hp_percent <= 0.3:
            from src.combat.boss_dialogue import get_boss_dialogue
            boss_dialogue = get_boss_dialogue()

            # 10% 확률로 대사 출력 (너무 자주 나오지 않도록)
            import random
            if random.random() < 0.1:
                dialogue = boss_dialogue.get_dialogue(boss.enemy_id, "player_low_hp")
                if dialogue:
                    boss_dialogue.print_dialogue(self.logger, dialogue)
```

### 4. ⚠️ 플레이어 사망 시 대사 (미구현)

**구현 위치**: `src/combat/combat_manager.py`의 `_on_character_death()` 함수 (약 라인 2979)

**구현 내용**:
```python
def _on_character_death(self, data: Dict[str, Any]) -> None:
    """캐릭터 사망 이벤트 처리"""
    character = data.get("character")
    if not character:
        return

    # ... 기존 코드 ...

    # === 보스 대사: 플레이어 사망 ===
    # 아군이 죽었을 때 보스 대사 출력
    if character in self.allies:
        # 보스가 살아있는지 확인
        for enemy in self.enemies:
            if hasattr(enemy, 'enemy_id') and enemy.enemy_id in ['sephiroth', 'abel_cain']:
                if getattr(enemy, 'is_alive', True):
                    from src.combat.boss_dialogue import get_boss_dialogue
                    boss_dialogue = get_boss_dialogue()

                    dialogue = boss_dialogue.get_dialogue(enemy.enemy_id, "player_death")
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue)
                    break  # 한 번만 출력

    # ... 기존 코드 계속 ...
```

### 5. ⚠️ 궁극기/강한 공격 대사 (미구현)

**구현 위치**: `src/combat/combat_manager.py`의 스킬 실행 부분 (execute_skill_action 등)

**구현 방법**:
1. 스킬 실행 전/후에 메타데이터 체크
2. `is_ultimate=True` 또는 `damage > 500` 같은 조건 확인
3. 해당 조건 만족 시 대사 출력

**예시 코드** (스킬 실행 부분에 추가):
```python
# 스킬 실행 전
if hasattr(actor, 'enemy_id') and actor.enemy_id in ['sephiroth', 'abel_cain']:
    from src.combat.boss_dialogue import get_boss_dialogue
    boss_dialogue = get_boss_dialogue()

    # 궁극기 체크
    if getattr(skill, 'is_ultimate', False) or getattr(skill, 'metadata', {}).get('is_ultimate', False):
        dialogue = boss_dialogue.get_dialogue(actor.enemy_id, "ultimate")
        if dialogue:
            boss_dialogue.print_dialogue(self.logger, dialogue)

    # 강한 공격 체크 (예상 데미지가 높은 경우)
    # 이 부분은 스킬의 multiplier나 base_damage를 확인하여 판단
    elif getattr(skill, 'base_damage', 0) > 300 or getattr(skill, 'multiplier', 1.0) > 3.0:
        import random
        if random.random() < 0.3:  # 30% 확률
            dialogue = boss_dialogue.get_dialogue(actor.enemy_id, "strong_attack")
            if dialogue:
                boss_dialogue.print_dialogue(self.logger, dialogue)
```

### 6. ⚠️ BREAK 당했을 때 대사 (미구현)

**구현 위치**: `src/combat/brave_system.py`의 BREAK 처리 부분 또는 `combat_manager.py`에서 BREAK 발생 감지

**구현 방법**:
```python
# BREAK 발생 시
if defender.is_broken and hasattr(defender, 'enemy_id') and defender.enemy_id in ['sephiroth', 'abel_cain']:
    from src.combat.boss_dialogue import get_boss_dialogue
    boss_dialogue = get_boss_dialogue()

    dialogue = boss_dialogue.get_dialogue(defender.enemy_id, "break_received")
    if dialogue:
        boss_dialogue.print_dialogue(self.logger, dialogue)
```

---

## 7. ⚠️ 랜덤 위치 떠다니는 대사 시스템 (림버스 컴퍼니 스타일) - 미구현 ⭐ 핵심 작업

### 목표
현재 로그에만 출력되는 대사를 **화면의 랜덤한 위치**에 떠다니게 표시

### 구현 파일
`src/ui/combat_ui.py`

### 구현 계획

#### 7-1. FloatingDialogue 클래스 추가

```python
# src/ui/combat_ui.py 상단에 추가

@dataclass
class FloatingDialogue:
    """화면에 떠다니는 대사"""
    text: str
    x: int
    y: int
    color: Tuple[int, int, int] = (255, 100, 100)  # 기본 붉은색
    frames_remaining: int = 300  # 5초 (60 FPS 기준)
    fade_start: int = 60  # 마지막 1초부터 페이드 아웃
```

#### 7-2. CombatUI 클래스에 속성 추가

```python
class CombatUI:
    def __init__(self, ...):
        # ... 기존 코드 ...

        # 떠다니는 대사 목록
        self.floating_dialogues: List[FloatingDialogue] = []
```

#### 7-3. 대사 추가 메서드 구현

```python
def add_floating_dialogue(self, text: str, color: Tuple[int, int, int] = (255, 100, 100)):
    """
    화면의 랜덤한 빈 공간에 떠다니는 대사 추가

    Args:
        text: 대사 내용
        color: 텍스트 색상 (기본: 붉은색)
    """
    import random

    # 화면의 중앙 영역에 랜덤 위치 선정 (좌우 여백 제외)
    min_x = 10
    max_x = self.screen_width - len(text) - 10
    min_y = 5
    max_y = self.screen_height - 15  # 하단 UI 영역 제외

    # 기존 대사와 겹치지 않는 위치 찾기 (최대 10번 시도)
    for attempt in range(10):
        x = random.randint(min_x, max_x)
        y = random.randint(min_y, max_y)

        # 기존 대사와 너무 가까운지 체크
        too_close = False
        for existing in self.floating_dialogues:
            if abs(existing.x - x) < 20 and abs(existing.y - y) < 3:
                too_close = True
                break

        if not too_close:
            break

    # 대사 추가
    dialogue = FloatingDialogue(
        text=text,
        x=x,
        y=y,
        color=color,
        frames_remaining=300,
        fade_start=60
    )
    self.floating_dialogues.append(dialogue)
    self.logger.debug(f"떠다니는 대사 추가: {text} at ({x}, {y})")
```

#### 7-4. 렌더링 메서드 추가

```python
def _render_floating_dialogues(self, console: tcod.console.Console):
    """떠다니는 대사 렌더링"""
    to_remove = []

    for dialogue in self.floating_dialogues:
        # 프레임 감소
        dialogue.frames_remaining -= 1

        if dialogue.frames_remaining <= 0:
            to_remove.append(dialogue)
            continue

        # 페이드 아웃 효과
        color = dialogue.color
        if dialogue.frames_remaining <= dialogue.fade_start:
            # 알파값 감소 효과 (색상 어둡게)
            fade_ratio = dialogue.frames_remaining / dialogue.fade_start
            color = (
                int(dialogue.color[0] * fade_ratio),
                int(dialogue.color[1] * fade_ratio),
                int(dialogue.color[2] * fade_ratio)
            )

        # 대사 출력
        console.print(
            dialogue.x,
            dialogue.y,
            f'"{dialogue.text}"',
            fg=color
        )

    # 만료된 대사 제거
    for dialogue in to_remove:
        self.floating_dialogues.remove(dialogue)
```

#### 7-5. render() 메서드에 통합

```python
def render(self, console: tcod.console.Console):
    """렌더링"""
    # ... 기존 렌더링 코드 ...

    # 떠다니는 대사 렌더링 (최상위 레이어)
    self._render_floating_dialogues(console)

    # ... 나머지 코드 ...
```

#### 7-6. boss_dialogue.py 수정 - CombatUI 연동

```python
# src/combat/boss_dialogue.py

@staticmethod
def print_dialogue(logger: Any, dialogue: str, combat_ui: Optional[Any] = None) -> None:
    """
    대사를 붉은 글씨로 출력

    Args:
        logger: 로거 객체
        dialogue: 대사
        combat_ui: CombatUI 객체 (떠다니는 대사용, 선택적)
    """
    if dialogue:
        # 로그에 출력
        logger.info(f"\033[91m\"{dialogue}\"\033[0m")

        # CombatUI가 있으면 화면에도 표시
        if combat_ui and hasattr(combat_ui, 'add_floating_dialogue'):
            combat_ui.add_floating_dialogue(dialogue, color=(255, 100, 100))
```

#### 7-7. combat_manager.py 수정 - CombatUI 참조 추가

```python
# combat_manager.py의 모든 boss_dialogue.print_dialogue() 호출 수정

# 기존:
boss_dialogue.print_dialogue(self.logger, dialogue)

# 수정:
# CombatUI 참조 가져오기 (combat_manager에 combat_ui 속성 추가 필요)
boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))
```

**CombatManager에 combat_ui 속성 추가**:
```python
# src/combat/combat_manager.py

class CombatManager:
    def __init__(self):
        # ... 기존 코드 ...
        self.combat_ui: Optional[Any] = None  # UI 참조 (나중에 설정)
```

**CombatUI에서 CombatManager에 자신을 등록**:
```python
# src/ui/combat_ui.py의 __init__

def __init__(self, ..., combat_manager: CombatManager, ...):
    # ... 기존 코드 ...

    # CombatManager에 자신을 등록
    combat_manager.combat_ui = self
```

---

## 구현 순서 권장사항

1. **먼저 로그 기반 대사 완성** (우선순위 높음):
   - 3번: 턴 시작 시 대사 체크
   - 4번: 플레이어 사망 시 대사
   - 5번: 궁극기/강한 공격 대사
   - 6번: BREAK 당했을 때 대사

2. **그 다음 떠다니는 대사 시스템** (우선순위 중간):
   - 7-1 ~ 7-5: FloatingDialogue 시스템 구현
   - 7-6 ~ 7-7: CombatUI 연동

3. **테스트 및 밸런스 조정**:
   - 대사가 너무 자주 나오지 않는지 확인
   - 화면에 대사가 너무 많이 겹치지 않는지 확인
   - 색상, 지속 시간, 페이드 아웃 효과 조정

---

## 테스트 방법

### 보스 전투 실행
```bash
python main.py --dev
# 게임 시작 후 보스 테스트 모드 진입
```

### 특정 상황 테스트
- **페이즈 전환**: 보스 HP를 66%, 33% 이하로 만들기
- **low_hp**: 보스 HP를 30% 이하로 만들기
- **player_low_hp**: 아군 HP를 30% 이하로 만들기
- **player_death**: 아군 한 명 사망시키기
- **BREAK**: 보스를 BREAK 시키기
- **궁극기**: 보스가 궁극기 사용할 때까지 대기

---

## 추가 개선 아이디어

1. **대사 변화**:
   - 전투 진행 상황에 따라 대사 톤 변경 (절박함 증가)
   - 특정 스킬 사용 시 전용 대사

2. **UI 효과**:
   - 떠다니는 대사에 그림자 효과
   - 대사가 약간 흔들리는 애니메이션
   - 중요한 대사는 크기를 키우거나 색상 변경

3. **음향 효과**:
   - 대사 출력 시 효과음 재생
   - 보스 목소리 샘플링 (선택적)

4. **난이도별 대사**:
   - 높은 난이도에서는 더 도발적이거나 절망적인 대사

---

## 참고 파일

- `src/combat/boss_dialogue.py` - 대사 시스템 핵심
- `src/combat/combat_manager.py` - 전투 로직 및 대사 호출
- `src/ui/combat_ui.py` - UI 렌더링
- `src/world/enemy_generator.py` - 보스 생성 (HP, MP 등)

---

## 문제 해결

### 대사가 출력되지 않는 경우
1. boss_id가 'sephiroth' 또는 'abel_cain'인지 확인
2. `get_boss_dialogue()`가 제대로 임포트되었는지 확인
3. 로거 레벨 확인 (`--log=DEBUG`)

### 떠다니는 대사가 안 보이는 경우
1. `_render_floating_dialogues()`가 `render()` 메서드에서 호출되는지 확인
2. z-order 확인 (다른 UI 요소에 가려지지 않도록)
3. 좌표가 화면 밖이 아닌지 확인

### 대사가 너무 자주 나오는 경우
1. 확률 조정 (`random.random() < 0.1` 등)
2. 쿨다운 추가 (마지막 대사 출력 시간 추적)

---

## 마무리

이 문서를 따라 구현하면 림버스 컴퍼니 스타일의 우울하고 배덕적인 보스 대사 시스템이 완성됩니다.

**핵심 포인트**:
- 다양한 상황에서 대사 출력 (전투가 살아있게)
- 화면에 랜덤하게 떠다니는 효과 (몰입감 증가)
- 붉은 색 텍스트로 보스의 광기 표현

**Happy Coding!** 🎮✨
