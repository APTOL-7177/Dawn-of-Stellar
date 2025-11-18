# python-tcod 마이그레이션 가이드

## 완료된 재구축

NewProject가 **python-tcod 기반**으로 완전히 재구축되었습니다!

### 주요 변경사항

#### ✅ 기술 스택 변경
- ❌ pygame → ✅ **python-tcod** (로그라이크 최적화)
- ✅ 이벤트 기반 아키텍처 유지
- ✅ YAML 설정 시스템 유지

#### ✅ 추가된 시스템
1. **확장 가능한 스탯 시스템**
   - 기본 스탯: hp, mp, strength, defense, magic, spirit, speed, luck
   - 확장 스탯: stamina, vitality, dexterity, perception, endurance, charisma
   - 성장 타입: linear, exponential, logarithmic, custom
   - 완전히 동적 추가/제거 가능

2. **확장 가능한 스킬 시스템**
   - 전투 스킬: brv_attack, hp_attack, support, debuff, ultimate
   - 필드 스킬: lockpicking, detection, stealth, tracking
   - 크래프팅 스킬: cooking, alchemy, smithing, enchanting
   - 플러그인 방식으로 새 스킬 타입 추가 가능

3. **상처 시스템**
   - 데미지의 25%가 영구 상처로 전환
   - 자연 회복은 느림
   - 치유 아이템으로 효과적 회복
   - 최대 HP의 50%까지 누적 가능

4. **채집 시스템**
   - 필드에서 자원 채집
   - 스태미나 소비
   - 손재주 스탯 영향
   - 획득량은 1-3개 랜덤

5. **요리 시스템**
   - 재료로 음식 제작
   - 품질 등급: poor, normal, good, excellent
   - 실패 시 재료 손실
   - 손재주 스탯 영향

6. **필드 스킬**
   - 자물쇠 해제 (lockpicking)
   - 탐지 (detection)
   - 은신 (stealth)

#### ❌ 제거된 시스템
- 멀티플레이어
- 모바일 지원

---

## python-tcod 개요

### 왜 tcod인가?

**python-tcod**는 로그라이크 게임에 최적화된 라이브러리:
- 🎮 ASCII/타일 기반 렌더링
- 🗺️ FOV (Field of View) 알고리즘 내장
- 🧭 경로 찾기 (Pathfinding) 지원
- 🏗️ 던전 생성 알고리즘
- ⚡ 고성능
- 🔧 로그라이크 개발에 필요한 모든 도구

### 기본 구조

```python
import tcod

# 1. 타일셋 로드
tileset = tcod.tileset.load_tilesheet(
    "tileset.png", 32, 8, tcod.tileset.CHARMAP_TCOD
)

# 2. 컨텍스트 생성
context = tcod.context.new(
    columns=80, rows=50,
    tileset=tileset,
    title="게임 제목"
)

# 3. 콘솔 생성
console = tcod.console.Console(80, 50)

# 4. 게임 루프
while True:
    console.clear()

    # 렌더링
    console.print(x, y, "@", fg=(255, 255, 255))

    context.present(console)

    # 입력 처리
    for event in tcod.event.wait():
        if isinstance(event, tcod.event.Quit):
            raise SystemExit()
```

---

## 프로젝트 구조

```
NewProject/
├── src/
│   ├── core/              # 핵심 시스템
│   │   ├── event_bus.py   # ✅ 이벤트 시스템
│   │   ├── config.py      # ✅ 설정 관리
│   │   └── logger.py      # ✅ 로깅
│   │
│   ├── character/         # 캐릭터 시스템
│   │   ├── stats.py       # ✅ 확장 가능한 스탯
│   │   └── skill_types.py # ✅ 확장 가능한 스킬 타입
│   │
│   ├── field/             # 필드 시스템
│   │   ├── gathering.py   # ✅ 채집
│   │   ├── cooking.py     # ✅ 요리
│   │   └── field_skills.py# ✅ 필드 스킬
│   │
│   ├── systems/           # 게임 시스템
│   │   └── wound_system.py# ✅ 상처 시스템
│   │
│   └── ui/                # UI 시스템
│       ├── tcod_display.py# ✅ TCOD 렌더링
│       └── input_handler.py# ✅ 입력 처리
│
├── config.yaml            # ✅ 게임 설정
└── requirements.txt       # ✅ tcod 의존성
```

---

## 현재 구현 상태

### ✅ 완료
- [x] 프로젝트 구조
- [x] 핵심 시스템 (EventBus, Config, Logger)
- [x] 확장 가능한 스탯 시스템
- [x] 확장 가능한 스킬 시스템
- [x] 상처 시스템
- [x] 채집 시스템
- [x] 요리 시스템
- [x] 필드 스킬 시스템
- [x] TCOD 디스플레이 기본 구조
- [x] 입력 핸들러

### 🚧 다음 단계
1. **게임 엔진** (`src/core/game_engine.py`)
   - TCOD 게임 루프 통합
   - 상태 머신 (메뉴, 게임, 인벤토리 등)

2. **캐릭터 클래스 구현** (`src/character/character.py`)
   - StatManager 통합
   - 스킬 관리

3. **전투 시스템** (`src/combat/`)
   - ATB 시스템
   - Brave 시스템
   - 데미지 계산

4. **월드 시스템** (`src/world/`)
   - TCOD 던전 생성
   - FOV 시스템
   - 타일 관리

---

## 확장 가능한 시스템 사용법

### 스탯 시스템 확장

```python
from src.character.stats import StatManager, GrowthType

# 1. 기본 스탯 설정
stats_config = {
    "hp": {"base_value": 100, "growth_rate": 10, "growth_type": "linear"},
    "strength": {"base_value": 10, "growth_rate": 1.1, "growth_type": "exponential"}
}

stat_manager = StatManager(stats_config)

# 2. 동적으로 새 스탯 추가
stat_manager.add_stat("luck", base_value=5, growth_rate=0.5, growth_type=GrowthType.LINEAR)

# 3. 스탯 값 가져오기
hp = stat_manager.get_value("hp")  # 총 값 (기본 + 보너스)

# 4. 보너스 추가/제거
stat_manager.add_bonus("strength", "장비", 5)
stat_manager.remove_bonus("strength", "장비")

# 5. 레벨업 적용
stat_manager.apply_level_up(level=10)
```

### 스킬 시스템 확장

```python
from src.character.skill_types import SkillType, SkillCategory, skill_type_registry

# 1. 새로운 스킬 타입 정의
class TeleportSkill(SkillType):
    def __init__(self):
        super().__init__(
            type_id="teleport",
            name="순간이동",
            category=SkillCategory.FIELD,
            target_type=SkillTargetType.AREA
        )

    def can_use(self, user, context):
        return user.mp >= 50

    def execute(self, user, target, context):
        # 순간이동 로직
        return {"success": True, "new_position": target}

# 2. 스킬 타입 등록
skill_type_registry.register(TeleportSkill())

# 3. 스킬 사용
skill_type = skill_type_registry.get("teleport")
result = skill_type.execute(player, target_pos, {})
```

### 필드 시스템 사용

```python
from src.field import gathering_system, cooking_system

# 1. 채집
result = gathering_system.gather(character, "herb")
if result["success"]:
    print(f"채집 성공! {result['yield']}개 획득")

# 2. 요리
result = cooking_system.cook(character, "herb_soup", inventory)
if result["success"]:
    print(f"요리 성공! 품질: {result['quality']}")
    food_item = result["item"]
```

### 상처 시스템 사용

```python
from src.systems.wound_system import get_wound_system

wound_system = get_wound_system()

# 1. 데미지 적용 (자동으로 상처 계산)
result = wound_system.apply_damage(character, 100)
print(f"HP 데미지: {result['hp_damage']}, 상처: {result['wound']}")

# 2. 자연 회복 (매 턴)
healed = wound_system.natural_healing(character)

# 3. 아이템으로 회복
result = wound_system.heal_with_item(character, 50)
print(f"HP 회복: {result['hp_healed']}, 상처 회복: {result['wound_healed']}")

# 4. 유효 최대 HP
effective_max_hp = wound_system.get_effective_max_hp(character)
```

---

## TCOD 렌더링 가이드

### 기본 렌더링

```python
from src.ui.tcod_display import get_display

display = get_display()

# 게임 루프
while True:
    display.clear()

    # 맵 렌더링
    display.render_map(game_map)

    # 사이드바 렌더링 (캐릭터 정보)
    display.render_sidebar(player)

    # 메시지 로그
    display.render_messages(message_log)

    # 모든 콘솔 합성 및 표시
    display.compose()
    display.present()
```

### 입력 처리

```python
from src.ui.input_handler import input_handler, GameAction
import tcod.event

for event in tcod.event.wait():
    action = input_handler.dispatch(event)

    if action == GameAction.QUIT:
        break
    elif action in [GameAction.MOVE_UP, GameAction.MOVE_DOWN, ...]:
        dx, dy = input_handler.get_direction(action)
        player.move(dx, dy)
    elif action == GameAction.INTERACT:
        player.interact()
```

---

## Claude Skills 활용

### 사용 가능한 Skills

1. **@combat-analyzer** - 전투 분석
   ```
   @combat-analyzer analyze-logs
   @combat-analyzer check-balance
   ```

2. **@data-validator** - 데이터 검증
   ```
   @data-validator check-characters
   @data-validator check-skills
   ```

3. **@content-generator** - 콘텐츠 생성
   ```
   @content-generator create-character "암살자" melee
   @content-generator create-skill "그림자 베기" brv_attack
   ```

---

## 설정 파일

### config.yaml 주요 설정

```yaml
# 디스플레이 (TCOD)
display:
  screen_width: 80
  screen_height: 50
  tileset: "assets/fonts/dejavu10x10_gs_tc.png"

# 확장 가능한 스탯
character:
  stats:
    base_stats: [hp, mp, strength, defense, magic, spirit, speed, luck]
    extended_stats: [stamina, vitality, dexterity, perception, endurance, charisma]
    growth_types: [linear, exponential, logarithmic, custom]

# 스킬 타입
skills:
  skill_types:
    combat: [brv_attack, hp_attack, support, debuff, ultimate]
    field: [lockpicking, detection, stealth, tracking]
    crafting: [cooking, alchemy, smithing, enchanting]

# 상처 시스템
wound_system:
  enabled: true
  wound_threshold: 0.25
  max_wound_percentage: 0.5

# 필드 시스템
field_systems:
  gathering:
    enabled: true
    stamina_cost: 10
  cooking:
    enabled: true
    stamina_cost: 15
```

---

## 다음 단계

### 즉시 시작 가능

1. **게임 엔진 구현**
   ```python
   # src/core/game_engine.py
   class GameEngine:
       def __init__(self):
           self.display = get_display()
           self.input_handler = input_handler

       def run(self):
           while True:
               # 렌더링
               # 입력 처리
               # 게임 로직
               pass
   ```

2. **캐릭터 클래스 이전**
   - 기존 28개 클래스 데이터를 data/characters/ 에 YAML로 이전
   - StatManager 통합

3. **전투 시스템 구현**
   - ATB + Brave 시스템
   - TCOD 전투 UI

---

## 참고 자료

- **python-tcod 공식 문서**: https://python-tcod.readthedocs.io/
- **TCOD 튜토리얼**: http://rogueliketutorials.com/
- **프로젝트 설계**: `PROJECT_DESIGN.md`
- **빠른 시작**: `QUICKSTART.md`

---

**python-tcod로 로그라이크의 진수를 경험하세요!** 🎮✨
