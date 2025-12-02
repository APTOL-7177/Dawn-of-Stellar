# 카인 최종 보스 통합 가이드 (30층)

## 📋 개요

30층 진 최종 보스 "닥터 아벨 카인" 전투를 게임에 통합하기 위한 가이드입니다.

---

## 🎯 카인 전투 특징

- **4분 타임어택** (세피로스보다 짧음 = 더 어려움)
- **시간 조작 메커니즘** (시간 역행, 타임라인 분기)
- **불멸 능력** (1회 부활)
- **20층 클리어 후 해금**

---

## 🔧 통합 작업

### 1. 카인 적 템플릿 추가

**파일**: `src/world/enemy_generator.py`

**ENEMY_TEMPLATES에 추가**:

```python
"abel_cain": EnemyTemplate(
    "abel_cain", "닥터 아벨 카인", 1,
    hp=1500,          # 세피로스보다 높은 HP
    mp=800,
    physical_attack=180,
    physical_defense=140,
    magic_attack=200,
    magic_defense=160,
    speed=120,
    max_brv=8000,
    init_brv=2667,
    luck=40,
    accuracy=95,
    evasion=30
),
```

**30층 보스 생성 로직 수정**:

```python
if floor_number == 30:
    template = ENEMY_TEMPLATES["abel_cain"]
    boss_name = "닥터 아벨 카인"
    boss_enemy_id = "abel_cain"
```

---

### 2. 4분 타이머 활성화

**파일**: `src/combat/combat_manager.py`

**start_combat() 메서드**:

```python
def start_combat(self, allies: List[Any], enemies: List[Any], ...):
    # 기존 전투 시작 로직...

    # 카인 전투인지 확인
    is_cain_battle = any(
        enemy.enemy_id == "abel_cain" for enemy in enemies
    )

    if is_cain_battle:
        from src.combat.boss_timer_system import get_boss_timer_system
        boss_timer = get_boss_timer_system()

        # 4분 타이머 시작
        boss_timer.start_timer(
            time_limit=240.0,  # 4분
            on_timeout=self._on_cain_timeout
        )

        boss_timer.on_warning = self._on_timer_warning

        self.logger.info("카인 전투 타이머 시작: 4분")
```

**타임아웃 콜백**:

```python
def _on_cain_timeout(self):
    """카인 타임오버 처리"""
    self.logger.warning("카인 전투 타임오버!")

    # 타임오버 스토리 재생
    from src.story.story_system import get_story_system
    story_system = get_story_system()
    timeout_story = story_system.get_cain_timeout_story()

    # 스토리 재생 (UI에서 처리)
    # self.ui.play_story(timeout_story)

    # 전투 패배 처리
    self.state = CombatState.DEFEAT

    # 게임오버
    if self.on_combat_end:
        self.on_combat_end(CombatState.DEFEAT)
```

---

### 3. 30층 진입 시 카인 조우 스토리

**파일**: `src/world/exploration.py` 또는 `src/ui/world_ui.py`

```python
def start_boss_battle(self, floor_number: int):
    # 30층 = 카인
    if floor_number == 30:
        from src.story.story_system import get_story_system
        story_system = get_story_system()

        # 카인 조우 스토리 재생
        encounter_story = story_system.get_cain_encounter_story()
        # self.ui.play_story(encounter_story)

        self.logger.info("카인과 조우!")

    # 보스 생성 및 전투 시작
    boss = EnemyGenerator.generate_boss(floor_number, is_floor_boss=True)
    # ...
```

---

### 4. 카인 격파 시 트루 엔딩

**파일**: `src/combat/combat_manager.py`

```python
def end_combat(self, state: CombatState):
    # 기존 전투 종료 로직...

    # 카인 승리 처리
    if state == CombatState.VICTORY:
        is_cain_battle = any(
            enemy.enemy_id == "abel_cain" for enemy in self.enemies
        )

        if is_cain_battle:
            # 카인 격파 스토리 재생 (트루 엔딩)
            from src.story.story_system import get_story_system
            story_system = get_story_system()

            victory_story = story_system.get_cain_defeat_story()
            # self.ui.play_story(victory_story)

            self.logger.info("카인 격파! 퍼펙트 엔딩 달성!")

    # 나머지 종료 처리...
```

---

### 5. 20층 클리어 후 30층 해금

**파일**: `src/persistence/save_system.py` 또는 진행도 관리 시스템

```python
def unlock_floor_30(self):
    """세피로스 격파 후 30층 해금"""
    from src.story.story_system import get_story_system
    story_system = get_story_system()

    if story_system.sephiroth_defeated:
        self.max_floor = 30
        self.logger.info("30층 해금! 진정한 악과의 대결이 기다린다...")
```

---

## 🎮 카인 전용 스킬 구현

### 스킬 예시

**파일**: `src/combat/cain_skills.py` (새로 생성)

```python
from typing import List
from src.combat.enemy_skills import EnemySkill, SkillTargetType

class CainSkillDatabase:
    """카인 전용 스킬"""

    @staticmethod
    def get_cain_skills() -> List[EnemySkill]:
        skills = []

        # 1. 시간 역행 (자가 회복)
        skills.append(EnemySkill(
            skill_id="cain_time_reverse",
            name="시간 역행",
            description="시간을 되돌려 HP 회복",
            target_type=SkillTargetType.SELF,
            mp_cost=100,
            heal_amount=500,
            use_probability=0.3,
            cooldown=5,
            min_hp_percent=0.0,
            max_hp_percent=0.5,  # HP 50% 이하일 때만
            sfx=("enemy", "time_reverse")
        ))

        # 2. 타임라인 분기 (전체 공격)
        skills.append(EnemySkill(
            skill_id="cain_timeline_split",
            name="타임라인 분기",
            description="여러 타임라인에서 동시 공격",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=150,
            damage_multiplier=4.0,  # 여러 번 공격 시뮬레이션
            is_magical=True,
            brv_damage=1500,
            hp_attack=True,
            use_probability=0.25,
            cooldown=4,
            sfx=("enemy", "ultimate")
        ))

        # 3. 시공 붕괴
        skills.append(EnemySkill(
            skill_id="cain_spacetime_collapse",
            name="시공 붕괴",
            description="시공간을 무기로 사용",
            target_type=SkillTargetType.RANDOM_ENEMY,
            mp_cost=120,
            damage_multiplier=5.0,
            is_magical=True,
            brv_damage=2000,
            status_effects=["stun"],
            status_duration=2,
            use_probability=0.3,
            cooldown=3,
            sfx=("enemy", "magic")
        ))

        return skills
```

---

## ⚙️ 특수 메커니즘 구현

### 불멸 능력 (1회 부활)

**파일**: `src/combat/combat_manager.py`

```python
def _check_enemy_death(self, enemy: Any):
    """적 사망 체크"""
    if enemy.current_hp <= 0:
        # 카인 불멸 체크
        if enemy.enemy_id == "abel_cain":
            if not hasattr(enemy, '_has_revived'):
                # 1회 부활
                enemy.current_hp = enemy.max_hp // 2
                enemy._has_revived = True

                # UI 메시지
                # self.ui.show_message("카인: \"하하, 내가 죽을 거라 생각했나?\"")

                self.logger.info("카인 부활! (불멸 능력)")
                return  # 사망 처리하지 않음

        # 일반 사망 처리
        enemy.is_alive = False
```

---

## 🎵 BGM 통합

**파일**: `src/audio/bgm_manager.py`

```python
def play_boss_bgm(enemy_id: str):
    if enemy_id == "abel_cain":
        # 카인 전용 BGM 재생
        # 곡 길이: 4분 (240초)
        self.play_music("cain_theme", loop=False)

        self.logger.info("카인 테마곡 재생: Throne of Time")
```

**BGM 파일 위치**: `assets/audio/bgm/cain_theme.ogg` (또는 mp3)

---

## 📊 밸런스 조정

### 타이머 시간 조정

```python
# 4분이 너무 짧으면
boss_timer.start_timer(time_limit=300.0)  # 5분

# 4분이 너무 길면
boss_timer.start_timer(time_limit=180.0)  # 3분
```

### 카인 스탯 조정

- HP 너무 높으면: `hp=1200`로 감소
- HP 너무 낮으면: `hp=2000`으로 증가
- 공격력 조정: `damage_multiplier` 값 조정

---

## ✅ 체크리스트

### 필수 항목
- [ ] 30층에서 카인 보스 생성 확인
- [ ] 카인 스킬 정상 로드
- [ ] **4분 타이머** 시작 확인
- [ ] 전투 UI에 타이머 표시
- [ ] 타임오버 시 게임오버 처리
- [ ] 카인 격파 시 **트루 엔딩** 재생
- [ ] 불멸 능력 (1회 부활) 작동

### 스토리 항목
- [ ] 30층 진입 시 조우 스토리 재생
- [ ] 카인 격파 후 퍼펙트 엔딩 재생
- [ ] 타임오버 시 시공 소멸 스토리 재생
- [ ] 세피로스 목소리 연출

### 특수 메커니즘
- [ ] 시간 역행 (HP 회복)
- [ ] 타임라인 분기 (전체 공격)
- [ ] 불멸 (1회 부활)
- [ ] 20층 클리어 후 30층 해금

---

## 🎮 난이도 컨셉

### 세피로스 vs 카인

| 항목 | 세피로스 (20층) | 카인 (30층) |
|------|----------------|------------|
| 타이머 | 7분 30초 | **4분** (더 짧음) |
| 테마 | 슬픔, 해방 | 교만, 악의 |
| 난이도 | 최종 보스 | **진 최종 보스** |
| 역할 | 희생자 | 가해자 |

**카인이 더 어려운 이유**:
- 타이머가 절반 수준 (4분 vs 7.5분)
- 더 강력한 스탯
- 불멸 능력 (1회 부활)
- 시간 조작으로 예측 불가

---

## 🚀 배포 전 최종 확인

1. **카인 전투 10회 이상 테스트**
2. **4분 타이머가 적절한지 확인**
3. **트루 엔딩 연출 완성도**
4. **20층 → 30층 진행 흐름**
5. **BGM 싱크 (4분)**

---

**작성자**: Dawn of Stellar 개발팀
**마지막 업데이트**: 2025-12-01 (4분 타이머 적용)
