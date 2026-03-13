# Claude Code 프로젝트 가이드 - Dawn of Stellar

**프로젝트명**: Dawn of Stellar (별빛의 여명)
**버전**: 6.0.0 (기믹 시스템 활성화)
**언어**: Python 3.10+
**장르**: 로그라이크 RPG + JRPG 퓨전
**GitHub**: https://github.com/APTOL-7177/Dawn-of-Stellar

## 프로젝트 개요

Final Fantasy 스타일의 **Brave 전투 시스템**과 **32가지 고유 기믹**을 가진 Python 기반 로그라이크 RPG입니다.
33개 캐릭터 클래스, ATB 전투, AI 동료, 절차적 던전 생성, 완전한 한국어 지원을 제공합니다.

### 주요 특징
- ⚔️ **ATB + Brave 복합 전투**: 실시간 게이지 + BRV/HP 이중 데미지 시스템
- 🎭 **33개 직업 + 32가지 기믹**: 각 직업마다 고유한 메커니즘 (열 관리, 탄창 시스템, 지원사격 등)
- 🤖 **전술적 AI 시스템**: 동료/적 모두 상황 판단 기반 의사결정
- 🗺️ **절차적 던전 생성**: BSP 알고리즘 기반 무한 던전
- 📊 **데이터 주도 설계**: YAML 기반 밸런싱 및 콘텐츠 관리

---

## 프로젝트 구조

### 핵심 원칙
1. **관심사의 분리**: 각 모듈은 하나의 명확한 책임
2. **이벤트 기반**: `event_bus`를 통한 느슨한 결합
3. **데이터 주도**: YAML 기반 설정 및 콘텐츠
4. **테스트 우선**: 모든 기능은 테스트 가능
5. **기믹 시스템 통합**: `GimmickUpdater`를 통한 자동 업데이트

### 디렉토리 구조
```
Dawn-of-Stellar/
├── src/              # 소스 코드
│   ├── core/        # 핵심 시스템 (engine, event_bus, config, logger)
│   ├── combat/      # 전투 시스템 (ATB, Brave, 데미지 계산)
│   ├── character/   # 캐릭터 시스템 (클래스, 스킬, 스탯, 기믹)
│   ├── world/       # 월드 시스템 (맵, 던전 생성)
│   ├── ai/          # AI 시스템 (동료 AI, 적 AI, 전술 AI)
│   ├── equipment/   # 장비 시스템 (장비, 인벤토리)
│   ├── ui/          # UI 시스템 (디스플레이, 메뉴, 입력)
│   ├── audio/       # 오디오 시스템 (BGM, SFX)
│   ├── persistence/ # 저장/로드 시스템
│   ├── tutorial/    # 튜토리얼 시스템
│   ├── story/       # 스토리 시스템
│   ├── gathering/   # 채집 시스템
│   ├── cooking/     # 요리 시스템
│   └── utils/       # 유틸리티
├── data/            # 게임 데이터 (YAML)
│   ├── characters/  # 캐릭터 데이터 (33개)
│   ├── skills/      # 스킬 데이터
│   ├── equipment/   # 장비 데이터
│   └── config.yaml  # 전역 설정
├── assets/          # 에셋 (오디오, 폰트)
├── tests/           # 테스트
│   ├── unit/        # 단위 테스트
│   └── integration/ # 통합 테스트
├── docs/            # 문서
└── .claude/         # Claude Code 설정
    ├── commands/    # 커스텀 명령어
    └── skills/      # 커스텀 스킬
```

---

## 빠른 시작

### 게임 실행
```bash
# 기본 실행
python main.py

# 개발 모드 (모든 클래스 잠금 해제)
python main.py --dev

# 디버그 모드 (상세 로그)
python main.py --debug --log=DEBUG
```

### 테스트 실행
```bash
# 전체 테스트
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=src --cov-report=html

# 특정 테스트만
pytest tests/unit/combat/ -v
```

### Claude Code 커스텀 명령어
- `/test` - 테스트 실행
- `/run` - 게임 실행
- `/build` - 프로젝트 빌드
- `/add-job <name>` - 새 직업 추가
- `/add-skill <name>` - 새 스킬 추가
- `/debug-combat` - 전투 디버깅

---

## 핵심 시스템 설명

### 1. Event Bus (이벤트 버스)
모든 시스템 간 통신은 이벤트를 통해 이루어집니다.

**위치**: `src/core/event_bus.py`

**사용 예시**:
```python
from src.core.event_bus import event_bus, Events

# 이벤트 발행
event_bus.publish(Events.COMBAT_TURN_START, {
    "actor": character,
    "turn": turn_count
})

# 이벤트 구독
def on_turn_start(data):
    print(f"{data['actor'].name}의 턴 시작!")

event_bus.subscribe(Events.COMBAT_TURN_START, on_turn_start)
```

**주요 이벤트**:
- `Events.COMBAT_START`, `Events.COMBAT_END`
- `Events.COMBAT_TURN_START`, `Events.COMBAT_TURN_END`
- `Events.COMBAT_ACTION`, `Events.COMBAT_DAMAGE_DEALT`
- `Events.CHARACTER_LEVEL_UP`, `Events.CHARACTER_DEATH`

### 2. Combat System (전투 시스템)
**ATB + Brave** 복합 전투 시스템

**위치**: `src/combat/`

**핵심 컴포넌트**:
- `combat_manager.py`: 전투 흐름 제어, 기믹 업데이트 통합
- `atb_system.py`: ATB 게이지 관리 (0-2000, 행동 임계값 1000)
- `brave_system.py`: BRV/HP 메커니즘, BREAK 시스템
- `damage_calculator.py`: 데미지 계산 (물리/마법, 속성, 크리티컬)
- `status_effects.py`: 상태 효과 관리 (독, 화상, 스턴 등)

**전투 흐름**:
```
전투 시작
  → ATB 게이지 자동 증가 (속도 비례)
  → ATB >= 1000인 캐릭터 행동 가능
  → 스킬 선택 및 실행
  → 데미지/상태 효과 적용
  → 기믹 업데이트 (턴 시작/종료/공격 시)
  → ATB 소비 (행동 후)
  → 승리/패배 판정
전투 종료
```

**BREAK 시스템**:
- 적의 BRV를 0으로 만들면 **BREAK** 발동
- BREAK 시: HP 데미지 1.5배, 적 ATB 초기화, wound damage 추가
- BREAK 상태 해제는 다음 턴 시작 시

**기믹 연동**:
`combat_manager.py`가 `GimmickUpdater`를 호출하여 다음 시점에 기믹 업데이트:
- 턴 시작: `GimmickUpdater.on_turn_start()`
- 턴 종료: `GimmickUpdater.on_turn_end()`
- 스킬 사용: `GimmickUpdater.on_skill_use()`
- 아군 공격: `GimmickUpdater.on_ally_attack()` (지원사격 등 트리거)

### 3. Character System (캐릭터 시스템)
**33개 직업**, 각 10개 스킬 + 5개 특성

**위치**: `src/character/`

**스탯 구조**:
```python
{
    "hp": 100,        # 체력
    "mp": 50,         # 마나
    "brv": 0,         # 브레이브 (축적 데미지)
    "strength": 15,   # 물리 공격력
    "defense": 12,    # 물리 방어력
    "magic": 10,      # 마법 공격력
    "spirit": 10,     # 마법 방어력
    "speed": 10,      # 속도 (ATB 증가율)
    "luck": 5,        # 행운 (크리티컬율)
    "evasion": 5      # 회피율
}
```

**스킬 타입**:
- `BRV_ATTACK`: BRV 축적 (HP 데미지 없음)
- `HP_ATTACK`: BRV를 소비해 HP 데미지
- `BRV_HP_ATTACK`: 둘 다 동시에
- `SUPPORT`: 아군 지원
- `DEBUFF`: 적 약화
- `ULTIMATE`: 궁극기 (쿨다운 있음)

### 4. Gimmick System (기믹 시스템) ⭐ 핵심 특징
**32가지 고유 기믹**으로 직업별 차별화

**위치**: `src/character/gimmick_updater.py`

**구현된 기믹** (9개):
1. `heat_management` - 기계공학자: 열 관리 (0-100, 최적/위험/오버히트 구간)
2. `timeline_system` - 시간술사: 타임라인 (-5 ~ +5, 과거/현재/미래)
3. `yin_yang_flow` - 몽크: 음양 기 흐름 (0-100, 균형 유지)
4. `madness_threshold` - 버서커: 광기 역치 (HP 낮을수록 증가, 100 도달 시 사망)
5. `thirst_gauge` - 뱀파이어: 갈증 게이지 (흡혈로 충족, 굶주림 시 HP 손실)
6. `probability_distortion` - 차원술사: 확률 왜곡 (게이지 소모로 확률 조작)
7. `stealth_exposure` - 암살자: 은신-노출 딜레마 (은신 중 크리티컬, 노출 시 재은신 쿨다운)
8. `magazine_system` - 저격수: 탄창 재장전 (6발 탄창, 다양한 탄환 타입)
9. `support_fire` - 궁수: 지원사격 (아군 마킹 시 자동 사격, 콤보 보너스)

**미구현 기믹** (23개):
- `alchemy_system`, `break_system`, `crowd_cheer`, `darkness_system`, `dilemma_choice`
- `divinity_system`, `dragon_marks`, `duty_system`, `elemental_counter`, `elemental_spirits`
- `enchant_system`, `holy_system`, `iaijutsu_system`, `melody_system`, `multithread_system`
- `plunder_system`, `rune_resonance`, `shapeshifting_system`, `stance_system`, `sword_aura`
- `theft_system`, `totem_system`, `undead_legion`

**기믹 구현 방법**:
```python
# gimmick_updater.py에 추가
@staticmethod
def on_turn_start(character):
    gimmick_type = getattr(character, 'gimmick_type', None)
    if gimmick_type == "your_gimmick_name":
        GimmickUpdater._update_your_gimmick(character)

@staticmethod
def _update_your_gimmick(character):
    """기믹 로직 구현"""
    # 턴마다 실행할 로직
    pass
```

### 5. AI System (AI 시스템)
전술적 의사결정 트리

**위치**: `src/ai/`

**AI 우선순위**:
1. 긴급 힐 (HP < 30%)
2. 지원 힐 (HP < 60%)
3. 궁극기 (게이지 100%)
4. 전술 스킬 (기믹 고려)
5. HP 공격 (BRV 충분 시)
6. BRV 공격 (기본)

**AI 모드**:
- `aggressive`: 공격적 (HP 공격 우선)
- `defensive`: 방어적 (BRV 축적 우선)
- `balanced`: 균형 (상황 판단)
- `support`: 지원 (아군 버프 우선)

### 6. World System (월드 시스템)
절차적 던전 생성

**위치**: `src/world/`

**던전 생성 알고리즘**:
1. BSP (Binary Space Partitioning)로 방 분할
2. 복도로 방 연결
3. 적, 아이템, 특수 오브젝트 배치

**타일 타입**:
- `FLOOR`: 이동 가능
- `WALL`: 벽
- `DOOR`: 문 (잠금 가능)
- `STAIRS_UP/DOWN`: 계단
- `CHEST`: 상자
- `ENEMY`: 적

---

## 코딩 컨벤션

### Python 스타일
- **PEP 8** 준수
- **Type hints** 필수
- **Docstring** Google 스타일

```python
def calculate_damage(attacker: Character, defender: Character, skill: Skill) -> int:
    """데미지를 계산합니다.

    Args:
        attacker: 공격자 캐릭터
        defender: 방어자 캐릭터
        skill: 사용 스킬

    Returns:
        계산된 데미지 값

    Raises:
        ValueError: 유효하지 않은 스킬 타입
    """
    # 구현
    pass
```

### 명명 규칙
- 변수/함수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### 주석
- 한국어 주석 권장
- 복잡한 로직은 반드시 주석
- TODO, FIXME, NOTE 태그 사용

```python
# TODO: ATB 증가 속도 밸런스 조정 필요
# FIXME: 크리티컬 확률이 잘못 계산됨
# NOTE: 이 부분은 Final Fantasy VII의 ATB 시스템을 참고
```

---

## 데이터 구조

### 캐릭터 데이터 (YAML)
```yaml
# data/characters/archer.yaml
class_name: "궁수"
description: "아군을 마킹하여 지원사격으로 돕는 원거리 딜러"
base_stats:
  hp: 80
  mp: 50
  strength: 12
  defense: 8
  magic: 6
  spirit: 8
  speed: 12
  luck: 10
  evasion: 1.8
  max_brv: 2.5

traits:
- id: support_fire_master
  name: 지원 사격의 달인
  description: 연속 지원 사격 2회 이상 시 데미지 +20%
  type: conditional
  conditions:
    support_fire_combo_min: 2
  effects:
    damage_bonus: 0.2

gimmick:
  type: support_fire
  name: 지원사격 시스템
  description: 아군을 마킹하여 자동 지원 사격. 연속 지원 시 콤보 보너스
  max_marks: 3
  shots_per_mark: 3
  arrow_types:
  - normal
  - piercing
  - fire
  - ice
  - poison
  - explosive
  - holy

skills:
- archer_direct_shot
- archer_power_shot
- archer_mark_normal
- archer_mark_piercing
- archer_mark_fire
- archer_mark_ice
- archer_mark_poison
- archer_mark_explosive
- archer_mark_holy
- archer_ultimate
```

### 스킬 데이터 (Python)
```python
# src/character/skills/job_skills/archer_skills.py
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation

def create_archer_skills():
    """궁수 10개 스킬 생성"""

    # 일반 화살 마킹
    mark_normal = Skill("archer_mark_normal", "일반 화살 지원", "아군 마킹: 일반 화살 (배율 1.5)")
    mark_normal.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_normal", 1, max_value=3),
        GimmickEffect(GimmickOperation.SET, "mark_shots_normal", 3),
    ]
    mark_normal.costs = []  # MP 0
    mark_normal.target_type = "ally"
    mark_normal.metadata = {"arrow_type": "normal", "multiplier": 1.5}

    return [mark_normal, ...]
```

---

## 테스트 작성

### 단위 테스트
```python
# tests/unit/combat/test_damage_calculator.py
import pytest
from src.combat.damage_calculator import DamageCalculator
from src.character.character import Character

def test_physical_damage_calculation():
    """물리 데미지 계산 테스트"""
    calc = DamageCalculator()
    attacker = Character("전사", "전사")
    defender = Character("고블린", "고블린")

    damage = calc.calculate_physical_damage(attacker, defender, multiplier=2.0)

    assert damage > 0
    assert isinstance(damage, int)
```

### 통합 테스트
```python
# tests/integration/test_combat_flow.py
def test_combat_with_gimmicks():
    """기믹 시스템 통합 전투 테스트"""
    manager = CombatManager()
    archer = Character("궁수", "archer")
    warrior = Character("전사", "warrior")
    enemy = Enemy("고블린", level=1)

    manager.start_combat([archer, warrior], [enemy])

    # 궁수가 전사 마킹
    mark_skill = archer.get_skill("archer_mark_normal")
    manager.execute_action(archer, ActionType.SKILL, warrior, mark_skill)

    # 전사 공격 시 지원사격 발동 확인
    result = manager.execute_action(warrior, ActionType.BRV_ATTACK, enemy)

    assert archer.support_fire_combo == 1  # 콤보 카운트 증가
```

---

## 자주 사용하는 패턴

### 1. 새 직업 추가
```bash
# Claude Code 명령어 사용
/add-job <job_name>

# 수동으로 추가
1. data/characters/<job_name>.yaml 생성
2. src/character/skills/job_skills/<job_name>_skills.py 생성
3. 기믹이 있다면 gimmick_updater.py에 추가
4. tests/test_<job_name>.py 테스트 작성
```

### 2. 기믹 시스템 추가
```python
# 1. gimmick_updater.py의 on_turn_start/end에 추가
elif gimmick_type == "your_gimmick":
    GimmickUpdater._update_your_gimmick(character)

# 2. 업데이트 로직 구현
@staticmethod
def _update_your_gimmick(character):
    """기믹 업데이트 로직"""
    current_value = getattr(character, 'gimmick_value', 0)
    character.gimmick_value = min(100, current_value + 10)
    logger.debug(f"{character.name} 기믹 +10 (총: {character.gimmick_value})")

# 3. GimmickStateChecker에 조건 체커 추가
@staticmethod
def is_gimmick_active(character) -> bool:
    if character.gimmick_type == "your_gimmick":
        return getattr(character, 'gimmick_value', 0) >= 50
    return False
```

### 3. 전투 디버깅
```bash
/debug-combat         # 전투 디버깅 도구 실행
tail -100 logs/combat_latest.log  # 최근 로그 확인
```

### 4. 밸런스 조정
1. `data/config.yaml`에서 전역 밸런스 조정
2. 캐릭터별 조정: `data/characters/<job>.yaml` 수정
3. 스킬별 조정: 스킬 파일에서 multiplier, mp cost 수정
4. `/test` 실행으로 검증

---

## 문제 해결

### 빌드 실패
```bash
pip install -r requirements.txt  # 의존성 재설치
rm -rf __pycache__ .pytest_cache  # 캐시 삭제
pytest tests/ -v  # 테스트 재실행
```

### 테스트 실패
```bash
pytest --lf -v  # 실패한 테스트만 재실행
pytest -vv --tb=long  # 상세 traceback
pytest tests/unit/combat/test_damage.py::test_physical_damage -v  # 특정 테스트
```

### 기믹 시스템 디버깅
```python
# logger 레벨 조정
python main.py --log=DEBUG

# gimmick_updater.py 로그 확인
logger = get_logger("gimmick")  # 기믹 전용 로거
```

### 성능 문제
```bash
python -m cProfile -o profile.stats main.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

---

## 배포

### 실행 파일 생성
```bash
pyinstaller --onefile --name="DawnOfStellar" main.py

# 실행 파일 위치
dist/DawnOfStellar.exe  # Windows
dist/DawnOfStellar      # Linux/Mac
```

### 릴리스 체크리스트
- [ ] 모든 테스트 통과
- [ ] 코드 품질 검사 통과 (pylint, mypy)
- [ ] 문서 업데이트 (CHANGELOG.md, README.md)
- [ ] 버전 번호 업데이트
- [ ] 빌드 및 실행 파일 생성
- [ ] 릴리스 노트 작성
- [ ] 기믹 시스템 전체 구현 확인

---

## 참고 자료

- **GitHub**: https://github.com/APTOL-7177/Dawn-of-Stellar
- **설계 문서**: `PROJECT_DESIGN.md`, `JOB_MECHANISM_REDESIGN.md`
- **기믹 문서**: `COMPLETE_JOB_SYSTEM_DESIGN.md`, `GIMMICK_UI_DESIGN.md`
- **API 문서**: `docs/api/`

## 현재 작업 우선순위

1. ⚠️ **미구현 기믹 시스템 구현** (23개 남음)
2. 🐛 **테스트 실패 수정** (데미지 계산 관련 일부 테스트)
3. ⚡ **성능 최적화** (대규모 전투 시 프레임 드랍)
4. 📱 **UI/UX 개선** (기믹 상태 표시 강화)

---

**Happy Coding! 즐거운 개발 되세요!** 🎮✨
