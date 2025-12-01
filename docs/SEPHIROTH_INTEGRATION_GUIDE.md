# 세피로스 최종 보스 통합 가이드

## 📋 개요

20층 최종 보스 "세피로스" 전투를 게임에 통합하기 위한 단계별 가이드입니다.

---

## 🎯 구현된 시스템

### ✅ 완료된 항목

1. **세계관/스토리 설정**: `docs/SEPHIROTH_LORE.md`
2. **세피로스 스킬**: `src/combat/sephiroth_skills.py` (3페이즈, 13개 스킬)
3. **타이머 시스템**: `src/combat/boss_timer_system.py` (7분 30초)
4. **적 생성 로직**: `src/world/enemy_generator.py` (20층 = 세피로스)
5. **스토리 시스템**: `src/story/story_system.py` (조우/승리/타임오버 스토리)

---

## 🔧 통합 작업 (TODO)

### 1. 전투 UI에 타이머 표시

**파일**: `src/ui/combat_ui.py`

**위치**: 전투 상태 표시 영역 (상단)

**구현 방법**:

```python
from src.combat.boss_timer_system import get_boss_timer_system

def render_combat_status(self, ...):
    # 기존 코드...

    # 보스 타이머 표시
    boss_timer = get_boss_timer_system()
    if boss_timer.is_active:
        remaining = boss_timer.get_remaining_time_display()

        # 남은 시간에 따라 색상 변경
        if boss_timer.get_remaining_time() <= 30:
            color = "red"  # 30초 이하: 빨강
        elif boss_timer.get_remaining_time() <= 60:
            color = "yellow"  # 1분 이하: 노랑
        else:
            color = "white"  # 정상

        # 타이머 표시
        timer_text = f"⏱️  남은 시간: {remaining}  ⏱️"
        # UI에 출력 (상단 중앙)
```

**표시 위치**: 화면 상단 중앙, 현재 턴 정보 위

---

### 2. 전투 시작 시 타이머 활성화

**파일**: `src/combat/combat_manager.py`

**메서드**: `start_combat()`

**구현 방법**:

```python
def start_combat(self, allies: List[Any], enemies: List[Any], ...):
    # 기존 전투 시작 로직...

    # 세피로스 전투인지 확인
    is_sephiroth_battle = any(
        enemy.enemy_id == "sephiroth" for enemy in enemies
    )

    if is_sephiroth_battle:
        from src.combat.boss_timer_system import get_boss_timer_system
        boss_timer = get_boss_timer_system()

        # 7분 30초 타이머 시작
        boss_timer.start_timer(
            time_limit=450.0,  # 7분 30초
            on_timeout=self._on_sephiroth_timeout
        )

        # 경고 콜백
        boss_timer.on_warning = self._on_timer_warning

        self.logger.info("세피로스 전투 타이머 시작: 7분 30초")

    # 나머지 전투 시작 로직...
```

**타임아웃 콜백**:

```python
def _on_sephiroth_timeout(self):
    """세피로스 타임오버 처리"""
    self.logger.warning("세피로스 전투 타임오버!")

    # 타임오버 스토리 재생
    from src.story.story_system import get_story_system
    story_system = get_story_system()
    timeout_story = story_system.get_sephiroth_timeout_story()

    # 스토리 재생 (UI에서 처리)
    # self.ui.play_story(timeout_story)

    # 전투 패배 처리
    self.state = CombatState.DEFEAT

    # 게임오버
    if self.on_combat_end:
        self.on_combat_end(CombatState.DEFEAT)
```

**경고 콜백**:

```python
def _on_timer_warning(self, remaining_seconds: int):
    """타이머 경고 (1분, 30초, 10초)"""
    self.logger.warning(f"세피로스 타이머 경고: {remaining_seconds}초 남음")

    # UI에 경고 메시지 표시
    warning_msg = f"⚠️ 경고: {remaining_seconds}초 남음! ⚠️"
    # self.ui.show_warning(warning_msg)
```

---

### 3. 매 턴마다 타이머 체크

**파일**: `src/combat/combat_manager.py`

**메서드**: `update()` 또는 턴 진행 루프

**구현 방법**:

```python
def update(self):
    # 기존 업데이트 로직...

    # 보스 타이머 체크
    from src.combat.boss_timer_system import get_boss_timer_system
    boss_timer = get_boss_timer_system()

    if boss_timer.is_active:
        # 타임아웃 체크
        if boss_timer.check_timeout():
            # 타임아웃 처리는 콜백에서 자동 실행됨
            return

    # 나머지 전투 로직...
```

---

### 4. 전투 종료 시 타이머 정지

**파일**: `src/combat/combat_manager.py`

**메서드**: `end_combat()`

**구현 방법**:

```python
def end_combat(self, state: CombatState):
    # 기존 전투 종료 로직...

    # 보스 타이머 정지
    from src.combat.boss_timer_system import get_boss_timer_system
    boss_timer = get_boss_timer_system()

    if boss_timer.is_active:
        boss_timer.stop_timer()
        self.logger.info("보스 타이머 중지")

    # 세피로스 승리 처리
    if state == CombatState.VICTORY:
        is_sephiroth_battle = any(
            enemy.enemy_id == "sephiroth" for enemy in self.enemies
        )

        if is_sephiroth_battle:
            # 세피로스 격파 스토리 재생
            from src.story.story_system import get_story_system
            story_system = get_story_system()
            story_system.set_sephiroth_defeated(True)

            victory_story = story_system.get_sephiroth_defeat_story()
            # self.ui.play_story(victory_story)

            self.logger.info("세피로스 격파! 진 엔딩 해금")

    # 나머지 종료 처리...
```

---

### 5. 20층 진입 시 세피로스 조우 스토리

**파일**: `src/world/exploration.py` 또는 `src/ui/world_ui.py`

**위치**: 보스 전투 시작 전

**구현 방법**:

```python
def start_boss_battle(self, floor_number: int):
    # 20층 = 세피로스
    if floor_number == 20:
        from src.story.story_system import get_story_system
        story_system = get_story_system()

        # 세피로스 조우 스토리 재생
        encounter_story = story_system.get_sephiroth_encounter_story()
        # self.ui.play_story(encounter_story)

        story_system.set_sephiroth_encountered(True)

        self.logger.info("세피로스와 조우!")

    # 보스 생성 및 전투 시작
    boss = EnemyGenerator.generate_boss(floor_number, is_floor_boss=True)
    # ...
```

---

### 6. 세피로스 페이즈 전환 메시지

**파일**: `src/combat/combat_manager.py` 또는 AI 시스템

**위치**: 적 행동 선택 시

**구현 방법**:

```python
def select_enemy_action(self, enemy: Any):
    # 세피로스인지 확인
    if enemy.enemy_id == "sephiroth":
        from src.combat.sephiroth_skills import SephirothSkillDatabase

        # 현재 페이즈 확인
        current_phase = SephirothSkillDatabase.get_current_phase(
            enemy.current_hp, enemy.max_hp
        )

        # 페이즈 전환 체크 (이전 페이즈 저장 필요)
        if not hasattr(enemy, '_last_phase'):
            enemy._last_phase = current_phase

        if current_phase != enemy._last_phase:
            # 페이즈 전환 메시지
            transition_msg = SephirothSkillDatabase.get_phase_transition_message(current_phase)
            # self.ui.show_message(transition_msg)

            enemy._last_phase = current_phase

        # 페이즈별 대사
        hp_percent = enemy.current_hp / enemy.max_hp
        dialogue = SephirothSkillDatabase.get_phase_dialogue(current_phase, hp_percent)
        # self.ui.show_dialogue(enemy.name, dialogue)

    # 기존 적 행동 선택 로직...
```

---

### 7. 메뉴/일시정지 시 타이머 일시정지

**파일**: 메뉴 시스템, 전투 UI

**구현 방법**:

```python
def open_menu():
    # 보스 타이머 일시정지
    from src.combat.boss_timer_system import get_boss_timer_system
    boss_timer = get_boss_timer_system()

    if boss_timer.is_active:
        boss_timer.pause_timer()

    # 메뉴 표시...

def close_menu():
    # 보스 타이머 재개
    from src.combat.boss_timer_system import get_boss_timer_system
    boss_timer = get_boss_timer_system()

    if boss_timer.is_active:
        boss_timer.resume_timer()

    # 메뉴 닫기...
```

---

## 🎮 BGM 통합

### 세피로스 테마곡 설정

**파일**: `src/audio/bgm_manager.py` (또는 오디오 시스템)

**구현**:

```python
def play_boss_bgm(enemy_id: str):
    if enemy_id == "sephiroth":
        # 세피로스 전용 BGM 재생
        # 곡 길이: 7분 30초 (450초)
        self.play_music("sephiroth_theme", loop=False)

        self.logger.info("세피로스 테마곡 재생: Dance of Madness")
```

**BGM 파일 위치**: `assets/audio/bgm/sephiroth_theme.ogg` (또는 mp3)

---

## 🐛 디버그 및 테스트

### 세피로스 전투 테스트 명령어

**개발 모드 플래그**:

```bash
# 20층으로 바로 이동
python main.py --dev --floor=20

# 타이머 비활성화 (테스트용)
python main.py --dev --no-timer

# 세피로스 HP 조정 (밸런스 테스트)
python main.py --dev --boss-hp-multiplier=0.5
```

### 로그 확인

**관련 로거**:
- `combat`: 전투 로직
- `boss_timer`: 타이머 시스템
- `enemy`: 적 생성
- `story`: 스토리 이벤트

**로그 레벨 조정**:
```bash
python main.py --log=DEBUG
```

---

## 📊 밸런스 조정

### 세피로스 스탯 조정

**파일**: `src/world/enemy_generator.py`

**템플릿 위치**: 233-241줄

```python
"sephiroth": EnemyTemplate(
    "sephiroth", "세피로스", 1,
    hp=1000,          # 기본 HP (레벨 스케일링 적용됨)
    mp=500,           # 기본 MP
    physical_attack=150,  # 물리 공격력
    physical_defense=120, # 물리 방어력
    magic_attack=160,     # 마법 공격력
    magic_defense=130,    # 마법 방어력
    speed=100,            # 속도
    max_brv=6400,         # 최대 BRV
    init_brv=2133,        # 초기 BRV
    luck=30,              # 행운
    accuracy=90,          # 명중률
    evasion=25            # 회피율
),
```

**스케일링 공식** (866-893줄):
- 레벨 배율: `floor_number * 0.8`
- 보스 스탯 배율: `1.445배`
- 보스 HP 배율: `3.5배`
- 층 보스 강화: `1.5배 HP, 1.3배 스탯`
- 약화 조정: `0.8배 전체 스탯` (현재 적용 중)

**권장 조정**:
- HP가 너무 높으면: `hp` 값 감소 또는 약화 배율 증가 (`0.8` → `0.7`)
- HP가 너무 낮으면: 약화 배율 증가 (`0.8` → `0.9`)
- 공격력 조정: `damage_multiplier` (스킬별로 조정 가능)

### 타이머 시간 조정

**파일**: 위 통합 가이드 "2. 전투 시작 시 타이머 활성화"

**시간 변경**:
```python
boss_timer.start_timer(
    time_limit=450.0,  # 7분 30초
    # 테스트: 600.0 (10분), 300.0 (5분)
)
```

---

## 🎨 UI 개선 아이디어

### 타이머 표시 강화

- 남은 시간에 따라 색상 변경 (초록 → 노랑 → 빨강)
- 10초 이하일 때 깜빡임 효과
- 타이머 바 표시 (진행도 시각화)

### 페이즈 전환 연출

- 화면 효과 (페이드, 셰이크)
- 페이즈 전환 시 BGM 변화 (페이즈별 다른 섹션 재생)
- 세피로스 대사 음성 효과

### 타임오버 연출

- 화면 점멸 효과
- 시공간 왜곡 효과 (화면 흔들림, 색상 반전)
- 느린 모션 효과

---

## ✅ 체크리스트

통합 완료 전 확인 사항:

### 필수 항목
- [ ] 20층에서 세피로스 보스 생성 확인
- [ ] 세피로스 스킬 13개 정상 로드
- [ ] 7분 30초 타이머 시작 확인
- [ ] 전투 UI에 타이머 표시
- [ ] 타임오버 시 게임오버 처리
- [ ] 세피로스 격파 시 진 엔딩 재생
- [ ] 페이즈 전환 (HP 66%, 33%) 확인

### 스토리 항목
- [ ] 20층 진입 시 조우 스토리 재생
- [ ] 세피로스 격파 후 승리 스토리 재생
- [ ] 타임오버 시 패배 스토리 재생
- [ ] 페이즈별 대사 표시

### 밸런스 항목
- [ ] 세피로스 HP가 적절한가?
- [ ] 7분 30초가 적절한 시간인가?
- [ ] 스킬 데미지가 밸런스에 맞는가?
- [ ] 플레이어 레벨 10~15 기준 클리어 가능한가?

### 오디오 항목
- [ ] 세피로스 테마곡 재생 (7분 30초)
- [ ] 스킬 효과음
- [ ] 페이즈 전환 효과음
- [ ] 타임오버 경고음

---

## 🚀 배포 전 최종 확인

1. **풀 플레이스루 테스트**: 1층부터 20층까지 정상 진행 확인
2. **세피로스 전투 10회 이상 테스트**: 승리/패배/타임오버 모든 경우
3. **밸런스 확인**: 다양한 직업/파티 구성으로 테스트
4. **버그 확인**: 타이머 관련 버그, 페이즈 전환 버그 등
5. **스토리 연출 확인**: 모든 컷신이 정상 재생되는지

---

## 📝 향후 개선 아이디어

- **하드모드**: 5분 타이머, 세피로스 스탯 1.5배
- **세피로스 2페이즈**: 30층에 더 강력한 세피로스 재등장
- **숨겨진 페이즈**: HP 0%에서 최종 발악 (1회 부활)
- **멀티 엔딩**: 타이머 시간에 따라 다른 엔딩
- **업적 시스템**: "3분 안에 세피로스 격파" 등

---

**작성자**: Dawn of Stellar 개발팀
**마지막 업데이트**: 2025-12-01
