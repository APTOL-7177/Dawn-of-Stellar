# Claude Code 프로젝트 가이드 - Dawn of Stellar

**프로젝트명**: Dawn of Stellar (별빛의 여명)
**버전**: 5.0.0 (재구조화)
**언어**: Python 3.10+
**장르**: 로그라이크 RPG + JRPG 퓨전

## 프로젝트 개요

Final Fantasy 스타일의 Brave 전투 시스템을 가진 Python 기반 로그라이크 RPG입니다.
28개 캐릭터 클래스, ATB 전투, AI 동료, 멀티플레이어를 지원하며 완전한 한국어 지원을 제공합니다.

## 프로젝트 구조

### 핵심 원칙
1. **관심사의 분리**: 각 모듈은 하나의 명확한 책임
2. **이벤트 기반**: `event_bus`를 통한 느슨한 결합
3. **데이터 주도**: YAML 기반 설정 및 콘텐츠
4. **테스트 우선**: 모든 기능은 테스트 가능

### 디렉토리 구조
```
NewProject/
├── src/              # 소스 코드
│   ├── core/        # 핵심 시스템 (engine, event_bus, config, logger)
│   ├── combat/      # 전투 시스템 (ATB, Brave, 데미지 계산)
│   ├── character/   # 캐릭터 시스템 (클래스, 스킬, 스탯)
│   ├── world/       # 월드 시스템 (맵, 던전 생성, 상호작용)
│   ├── ai/          # AI 시스템 (동료 AI, 적 AI, 전술 AI)
│   ├── equipment/   # 장비 시스템 (장비, 인벤토리)
│   ├── multiplayer/ # 멀티플레이어 (네트워크, 동기화)
│   ├── ui/          # UI 시스템 (디스플레이, 메뉴, 입력)
│   ├── audio/       # 오디오 시스템 (BGM, SFX)
│   ├── persistence/ # 저장/로드 시스템
│   └── utils/       # 유틸리티
├── data/            # 게임 데이터 (YAML)
├── assets/          # 에셋 (오디오, 폰트)
├── tests/           # 테스트
├── docs/            # 문서
└── scripts/         # 개발 도구
```

## 실행 방법

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
```

### 커스텀 명령어
- `/test` - 테스트 실행
- `/run` - 게임 실행
- `/build` - 프로젝트 빌드
- `/add-character <name>` - 새 캐릭터 클래스 추가
- `/add-skill <name>` - 새 스킬 추가
- `/debug-combat` - 전투 디버깅

## 핵심 시스템 설명

### 1. Event Bus (이벤트 버스)
모든 시스템 간 통신은 이벤트를 통해 이루어집니다.

**위치**: `src/core/event_bus.py`

**사용 예시**:
```python
from src.core.event_bus import event_bus

# 이벤트 발행
event_bus.publish("character.level_up", {
    "character_id": char.id,
    "new_level": char.level
})

# 이벤트 구독
def on_level_up(data):
    print(f"레벨업: {data['new_level']}")

event_bus.subscribe("character.level_up", on_level_up)
```

**주요 이벤트**:
- `combat.start`, `combat.end`, `combat.turn_start`
- `character.level_up`, `character.hp_change`, `character.death`
- `skill.cast`, `skill.execute`, `skill.interrupt`
- `world.floor_change`, `world.item_pickup`

### 2. Combat System (전투 시스템)
ATB + Brave 시스템의 복합 전투

**위치**: `src/combat/`

**핵심 컴포넌트**:
- `combat_manager.py`: 전투 흐름 제어
- `atb_system.py`: ATB 게이지 관리 (0-2000, 행동 임계값 1000)
- `brave_system.py`: BRV/HP 메커니즘, BREAK 시스템
- `damage_calculator.py`: 데미지 계산 (물리/마법, 속성, 크리티컬)

**전투 흐름**:
```
전투 시작
  → ATB 게이지 증가 (매 프레임)
  → ATB >= 1000인 캐릭터 행동
  → 스킬 선택 및 실행
  → 데미지/상태 효과 적용
  → ATB 감소 (행동 후)
  → 승리/패배 판정
전투 종료
```

**BREAK 시스템**:
- 적의 BRV를 0으로 만들면 BREAK 발동
- BREAK 시 보너스 데미지 + 스턴
- BREAK 중인 적은 행동 불가

### 3. Character System (캐릭터 시스템)
28개 직업, 각 6개 스킬

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
    "luck": 5         # 행운 (크리티컬율)
}
```

**스킬 타입**:
- `BRV_ATTACK`: BRV 축적 (HP 데미지 없음)
- `HP_ATTACK`: BRV를 소비해 HP 데미지
- `BRV_HP_ATTACK`: 둘 다 동시에
- `SUPPORT`: 아군 지원
- `DEBUFF`: 적 약화
- `ULTIMATE`: 궁극기

### 4. World System (월드 시스템)
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

### 5. AI System (AI 시스템)
전술적 의사결정 트리

**위치**: `src/ai/`

**AI 우선순위**:
1. 긴급 힐 (HP < 30%)
2. 지원 힐 (HP < 60%)
3. 궁극기 (게이지 100%)
4. 전술 스킬
5. HP 공격
6. BRV 공격

**AI 모드**:
- `aggressive`: 공격적 (HP 공격 우선)
- `defensive`: 방어적 (BRV 축적 우선)
- `balanced`: 균형 (상황 판단)
- `support`: 지원 (아군 버프 우선)

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

## 데이터 구조

### 캐릭터 데이터 (YAML)
```yaml
# data/characters/warrior.yaml
class_name: "전사"
description: "강력한 물리 공격력과 높은 방어력"
base_stats:
  hp: 120
  mp: 30
  strength: 18
  defense: 15
  magic: 8
  spirit: 10
  speed: 10
  luck: 5

skills:
  - power_strike
  - shield_bash
  - war_cry
  - berserk

passives:
  - heavy_armor_mastery
  - counter_stance
```

### 스킬 데이터 (YAML)
```yaml
# data/skills/power_strike.yaml
id: power_strike
name: "강타"
type: brv_attack
description: "강력한 일격으로 적을 가격합니다"

costs:
  mp: 15
  cast_time: 1.0

effects:
  - type: damage
    element: physical
    multiplier: 2.5
    stat_base: strength

  - type: brv_break_bonus
    multiplier: 1.2
```

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

def test_defense_reduces_damage():
    """방어력이 데미지 감소 테스트"""
    calc = DamageCalculator()
    attacker = Character("전사", "전사")
    weak_defender = Character("약한적", "약한적")
    weak_defender.defense = 5

    strong_defender = Character("강한적", "강한적")
    strong_defender.defense = 20

    damage_weak = calc.calculate_physical_damage(attacker, weak_defender)
    damage_strong = calc.calculate_physical_damage(attacker, strong_defender)

    assert damage_weak > damage_strong
```

### 통합 테스트
```python
# tests/integration/test_combat_flow.py
import pytest
from src.core.game_engine import GameEngine
from src.combat.combat_manager import CombatManager

def test_full_combat_sequence():
    """전체 전투 시퀀스 테스트"""
    engine = GameEngine()
    combat = CombatManager()

    # 전투 시작
    player = engine.create_character("플레이어", "전사")
    enemy = engine.create_enemy("고블린", level=1)

    combat.start_combat([player], [enemy])

    # 턴 실행
    while combat.is_active:
        combat.update(delta_time=0.016)

    # 승리 확인
    assert not enemy.is_alive()
    assert player.is_alive()
```

## 자주 사용하는 패턴

### 1. 새 캐릭터 클래스 추가
1. `data/characters/<class_name>.yaml` 생성
2. `src/character/classes/<class_name>.py` 구현
3. `src/character/classes/__init__.py` 등록
4. `tests/unit/character/test_<class_name>.py` 테스트 작성

**또는**: `/add-character <class_name>` 명령어 사용

### 2. 새 스킬 추가
1. `data/skills/<skill_name>.yaml` 생성
2. `src/character/skills/<skill_name>.py` 구현
3. `src/character/skills/__init__.py` 등록
4. `tests/unit/skills/test_<skill_name>.py` 테스트 작성

**또는**: `/add-skill <skill_name> <type>` 명령어 사용

### 3. 전투 디버깅
```bash
# 최근 전투 로그 확인
tail -100 logs/combat_latest.log

# ATB 시스템 검증
python scripts/debug_atb.py

# 데미지 계산 검증
python scripts/debug_damage.py
```

**또는**: `/debug-combat` 명령어 사용

### 4. 밸런스 조정
1. `config.yaml`에서 전역 밸런스 조정
2. 캐릭터별 조정: `data/characters/` 수정
3. 스킬별 조정: `data/skills/` 수정
4. 테스트 실행으로 검증

## 문제 해결

### 빌드 실패
```bash
# 의존성 재설치
pip install -r requirements.txt

# 캐시 삭제
rm -rf __pycache__ .pytest_cache .mypy_cache

# 테스트 재실행
pytest tests/ -v
```

### 테스트 실패
```bash
# 실패한 테스트만 재실행
pytest --lf -v

# 상세 출력
pytest -vv --tb=long

# 특정 테스트만
pytest tests/unit/combat/test_damage.py::test_physical_damage -v
```

### 전투 버그
1. `/debug-combat logs` - 로그 확인
2. `/debug-combat atb` - ATB 시스템 검증
3. `/debug-combat damage` - 데미지 계산 검증
4. 문제 재현 테스트 작성

### 성능 문제
```bash
# 프로파일링
python -m cProfile -o profile.stats main.py

# 프로파일 분석
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

## 배포

### 실행 파일 생성
```bash
# PyInstaller로 빌드
pyinstaller --onefile --name="DawnOfStellar" main.py

# 실행 파일 위치
dist/DawnOfStellar.exe  # Windows
dist/DawnOfStellar      # Linux/Mac
```

### 릴리스 체크리스트
- [ ] 모든 테스트 통과
- [ ] 코드 품질 검사 통과 (pylint, mypy)
- [ ] 문서 업데이트
- [ ] CHANGELOG.md 업데이트
- [ ] 버전 번호 업데이트 (`version.py`)
- [ ] 빌드 및 실행 파일 생성
- [ ] 릴리스 노트 작성

## 참고 자료

- **프로젝트 설계**: `PROJECT_DESIGN.md`
- **API 문서**: `docs/api/`
- **아키텍처 문서**: `docs/architecture.md`
- **스킬 가이드**: `docs/guides/skills.md`
- **캐릭터 가이드**: `docs/guides/characters.md`

## 연락처 및 기여

- **이슈 트래킹**: GitHub Issues
- **기여 가이드**: `CONTRIBUTING.md`
- **코드 리뷰**: Pull Request 필수
- **커뮤니케이션**: 한국어/영어 모두 환영

---

**Happy Coding! 즐거운 개발 되세요!** 🎮✨
