# Dawn of Stellar - 빠른 시작 가이드

## 프로젝트 설정 완료!

NewProject에 **구조적이고 확장 가능한** 새로운 프로젝트 베이스가 준비되었습니다.

## 현재 상태

### ✅ 완료된 작업

1. **폴더 구조 생성**
   - 명확하게 분리된 모듈 구조
   - Core, Combat, Character, World, AI 등 시스템별 디렉토리

2. **Claude Code 통합**
   - `.claude/commands/` - 커스텀 슬래시 커맨드 6개
   - `.claude/CLAUDE.md` - 프로젝트 전용 가이드

3. **핵심 시스템 구현**
   - ✅ `EventBus`: 이벤트 기반 통신 시스템
   - ✅ `Config`: YAML 기반 설정 관리
   - ✅ `Logger`: 구조화된 로깅

4. **설정 파일**
   - ✅ `config.yaml`: 게임 설정 (난이도, ATB, 오디오 등)
   - ✅ `requirements.txt`: Python 의존성
   - ✅ `pyproject.toml`: 프로젝트 메타데이터
   - ✅ `.gitignore`: Git 제외 파일

5. **문서**
   - ✅ `README.md`: 프로젝트 소개
   - ✅ `PROJECT_DESIGN.md`: 상세 설계 문서
   - ✅ `docs/architecture.md`: 아키텍처 문서

6. **테스트 가능한 메인 엔트리**
   - ✅ `main.py`: 명령줄 인자 지원

### 🚧 다음 단계 (구현 필요)

1. **게임 엔진** (`src/core/game_engine.py`)
   - 메인 게임 루프
   - 시스템 초기화 및 통합

2. **전투 시스템** (`src/combat/`)
   - `combat_manager.py`: 전투 흐름
   - `atb_system.py`: ATB 게이지
   - `brave_system.py`: BRV/HP 메커니즘
   - `damage_calculator.py`: 데미지 계산

3. **캐릭터 시스템** (`src/character/`)
   - `character.py`: 캐릭터 클래스
   - `classes/`: 28개 직업 구현
   - `skills/`: 스킬 시스템

4. **월드 시스템** (`src/world/`)
   - `dungeon_generator.py`: 절차적 던전 생성
   - `map.py`: 맵 관리

## 사용 가능한 명령어

### 게임 실행
```bash
# 기본 실행
python main.py

# 개발 모드
python main.py --dev

# 디버그 모드
python main.py --debug --log=DEBUG
```

### Claude Code 명령어
프로젝트 루트에서 사용 가능:

- `/test` - 테스트 실행
- `/run [mode]` - 게임 실행
- `/build` - 프로젝트 빌드
- `/add-character <name>` - 새 캐릭터 클래스 추가
- `/add-skill <name>` - 새 스킬 추가
- `/debug-combat` - 전투 디버깅

## 프로젝트 구조

```
NewProject/
├── .claude/              # Claude Code 설정
│   ├── commands/        # 커스텀 명령어 (6개)
│   └── CLAUDE.md        # 프로젝트 가이드
│
├── src/                 # 소스 코드
│   ├── core/           # ✅ 핵심 시스템 (완료)
│   │   ├── event_bus.py
│   │   ├── config.py
│   │   └── logger.py
│   ├── combat/         # 🚧 전투 시스템
│   ├── character/      # 🚧 캐릭터 시스템
│   ├── world/          # 🚧 월드 시스템
│   ├── ai/             # 🚧 AI 시스템
│   ├── equipment/      # 🚧 장비 시스템
│   ├── multiplayer/    # 🚧 멀티플레이어
│   ├── ui/             # 🚧 UI 시스템
│   ├── audio/          # 🚧 오디오 시스템
│   ├── persistence/    # 🚧 저장/로드
│   └── utils/          # 🚧 유틸리티
│
├── data/               # 게임 데이터 (YAML)
├── assets/             # 에셋 (오디오, 폰트)
├── tests/              # 테스트
├── docs/               # 문서
├── scripts/            # 개발 도구
│
├── main.py             # ✅ 메인 엔트리 포인트
├── config.yaml         # ✅ 게임 설정
├── requirements.txt    # ✅ 의존성
└── README.md           # ✅ 프로젝트 소개
```

## 개발 워크플로우

### 1. 새 기능 추가

```bash
# 1. 브랜치 생성
git checkout -b feature/new-system

# 2. 코드 작성
# src/<system>/ 에 모듈 추가

# 3. 테스트 작성
# tests/unit/<system>/ 에 테스트 추가

# 4. 테스트 실행
pytest tests/ -v

# 5. 커밋 및 푸시
git commit -m "feat: Add new system"
git push origin feature/new-system
```

### 2. 캐릭터 클래스 추가

```bash
# Claude Code 명령어 사용
/add-character 암살자

# 또는 수동으로:
# 1. data/characters/assassin.yaml 생성
# 2. src/character/classes/assassin.py 구현
# 3. tests/unit/character/test_assassin.py 작성
```

### 3. 스킬 추가

```bash
# Claude Code 명령어 사용
/add-skill shadow_strike brv_attack

# 또는 수동으로:
# 1. data/skills/shadow_strike.yaml 생성
# 2. src/character/skills/shadow_strike.py 구현
# 3. tests/unit/skills/test_shadow_strike.py 작성
```

## 아키텍처 하이라이트

### 이벤트 기반 통신

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

### 설정 관리

```python
from src.core.config import get_config

config = get_config()

# 설정 값 가져오기
max_gauge = config.get("combat.atb.max_gauge", 2000)

# 프로퍼티로 접근
if config.development_mode:
    # 개발자 기능 활성화
    pass
```

### 로깅

```python
from src.core.logger import get_logger

logger = get_logger("combat")
logger.info("전투 시작", {"enemy_count": 3})
logger.error("데미지 계산 실패", {"reason": "잘못된 스탯"})
```

## 기술 스택

- **언어**: Python 3.10+
- **설정**: YAML (PyYAML)
- **테스트**: pytest, pytest-cov
- **타입 체크**: mypy
- **코드 품질**: pylint, black
- **문서**: Sphinx
- **게임 라이브러리**: pygame (예정)

## 핵심 설계 원칙

1. **관심사의 분리**: 각 모듈은 하나의 책임
2. **이벤트 기반**: 느슨한 결합
3. **데이터 주도**: YAML 기반 콘텐츠
4. **테스트 우선**: 모든 기능은 테스트 가능

## 마이그레이션 계획

현재 프로젝트(`X:\로그라이크_2\`)에서 새 프로젝트로 이전:

### Phase 1: 핵심 시스템 (1-2주)
- ✅ 프로젝트 구조
- ✅ Core 시스템
- 🚧 Character 시스템
- 🚧 Combat 시스템

### Phase 2: 주요 기능 (2-3주)
- 🚧 World 시스템
- 🚧 Equipment 시스템
- 🚧 UI 시스템
- 🚧 Audio 시스템

### Phase 3: 고급 기능 (2-3주)
- 🚧 AI 시스템
- 🚧 Multiplayer 시스템
- 🚧 저장/로드 시스템
- 🚧 테스트 작성

## 문제 해결

### 의존성 설치 오류
```bash
pip install -r requirements.txt
```

### 설정 파일 오류
```bash
# config.yaml 경로 확인
python main.py --config=config.yaml
```

### 테스트 실패
```bash
# 상세 출력
pytest tests/ -vv --tb=long
```

## 참고 문서

- **설계 문서**: [`PROJECT_DESIGN.md`](PROJECT_DESIGN.md)
- **아키텍처**: [`docs/architecture.md`](docs/architecture.md)
- **Claude 가이드**: [`.claude/CLAUDE.md`](.claude/CLAUDE.md)
- **프로젝트 소개**: [`README.md`](README.md)

## 다음 할 일

1. **즉시**: `src/core/game_engine.py` 구현
2. **그 다음**: 전투 시스템 (`src/combat/`) 구현
3. **그 다음**: 캐릭터 시스템 (`src/character/`) 구현
4. **그 다음**: 기존 프로젝트에서 코드 마이그레이션

---

**Happy Coding! 🚀**

모든 것이 준비되었습니다. 이제 개발을 시작하세요!
