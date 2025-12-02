# 아키텍처 문서

## 시스템 개요

Dawn of Stellar는 이벤트 기반 아키텍처를 채택한 모듈형 게임 엔진입니다.

### 핵심 아키텍처 원칙

1. **이벤트 기반 통신**: 모든 시스템 간 통신은 `EventBus`를 통해 이루어집니다.
2. **의존성 최소화**: 각 모듈은 독립적으로 동작 가능합니다.
3. **데이터 주도 설계**: 게임 콘텐츠는 YAML 파일로 정의됩니다.
4. **테스트 가능성**: 모든 시스템은 모의 객체로 대체 가능합니다.

## 시스템 계층

```
┌─────────────────────────────────────────────┐
│         Application Layer                   │
│           (main.py)                         │
└──────────────┬──────────────────────────────┘
               │
        ┌──────▼──────┐
        │ Core Systems │
        │ - EventBus   │
        │ - Config     │
        │ - Logger     │
        └──────┬───────┘
               │
    ───────────┼───────────────────────
    │          │          │           │
┌───▼───┐  ┌──▼───┐  ┌───▼────┐  ┌──▼────┐
│Combat │  │World │  │Character│  │  UI   │
│System │  │System│  │ System  │  │System │
└───┬───┘  └──┬───┘  └───┬─────┘  └───────┘
    │         │          │
┌───▼─────────▼──────────▼─────────┐
│      Data/Persistence Layer       │
└───────────────────────────────────┘
```

## 주요 시스템

### 1. Core Systems (src/core/)

**역할**: 게임의 근간이 되는 기본 시스템

- `event_bus.py`: 이벤트 기반 통신
- `config.py`: 설정 관리
- `logger.py`: 로깅
- `game_engine.py`: 메인 게임 루프

**의존성**: 없음 (다른 시스템에 의존하지 않음)

### 2. Combat System (src/combat/)

**역할**: 전투 관련 모든 로직

- `combat_manager.py`: 전투 흐름 제어
- `atb_system.py`: ATB 게이지 관리
- `brave_system.py`: BRV/HP 메커니즘
- `damage_calculator.py`: 데미지 계산

**의존성**: Core, Character

**이벤트**:
- 발행: `combat.start`, `combat.end`, `combat.action`
- 구독: `character.death`, `skill.execute`

### 3. Character System (src/character/)

**역할**: 캐릭터 생성, 관리, 성장

- `character.py`: 캐릭터 기본 클래스
- `stats.py`: 스탯 관리
- `classes/`: 직업별 구현
- `skills/`: 스킬 시스템

**의존성**: Core

**이벤트**:
- 발행: `character.level_up`, `character.hp_change`
- 구독: `combat.action`, `equipment.equipped`

### 4. World System (src/world/)

**역할**: 맵, 던전, 상호작용

- `world_manager.py`: 월드 상태 관리
- `dungeon_generator.py`: 절차적 던전 생성
- `map.py`: 맵 데이터 구조

**의존성**: Core, Character

**이벤트**:
- 발행: `world.floor_change`, `world.item_pickup`
- 구독: `character.death`, `combat.end`

### 5. AI System (src/ai/)

**역할**: AI 행동 로직

- `ai_manager.py`: AI 전역 관리
- `companion_ai.py`: 동료 AI
- `enemy_ai.py`: 적 AI

**의존성**: Core, Character, Combat

**이벤트**:
- 발행: 없음 (직접 액션 실행)
- 구독: `combat.turn_start`

## 이벤트 흐름 예시

### 전투 시작 시퀀스

```
1. World System → event_bus.publish("combat.start", {...})
2. Combat Manager → combat.start() 호출
3. Combat Manager → event_bus.publish("combat.turn_start", {...})
4. ATB System → 게이지 업데이트 시작
5. AI System → 턴 시작 이벤트 수신, 행동 결정
```

### 스킬 실행 시퀀스

```
1. Player/AI → skill.execute() 호출
2. Skill System → event_bus.publish("skill.cast_start", {...})
3. Combat Manager → 캐스팅 시간 대기
4. Skill System → event_bus.publish("skill.execute", {...})
5. Damage Calculator → 데미지 계산
6. Character → event_bus.publish("character.hp_change", {...})
7. UI System → HP 바 업데이트
```

## 데이터 흐름

### 설정 데이터 (config.yaml)

```
config.yaml
    ↓
Config 클래스
    ↓
각 시스템에서 config.get() 호출
```

### 게임 데이터 (data/*.yaml)

```
data/characters/*.yaml
    ↓
DataLoader
    ↓
Character 생성 시 사용
```

### 저장 데이터 (saves/*.save)

```
게임 상태
    ↓
SaveManager.save()
    ↓
JSON 직렬화
    ↓
파일 저장
```

## 확장 가능성

### 새로운 시스템 추가

1. `src/` 하위에 새 디렉토리 생성
2. `__init__.py`와 모듈 파일 작성
3. 필요한 이벤트 정의 (EventBus.Events)
4. 이벤트 구독 및 발행
5. 테스트 작성

### 새로운 캐릭터 클래스 추가

1. `data/characters/<name>.yaml` 생성
2. `src/character/classes/<name>.py` 구현
3. `src/character/classes/__init__.py` 등록
4. 스킬 추가 (필요 시)

### 새로운 이벤트 타입 추가

1. `Events` 클래스에 상수 추가
2. 관련 시스템에서 이벤트 발행
3. 구독이 필요한 시스템에서 이벤트 구독

## 성능 고려사항

### 이벤트 버스

- 이벤트 히스토리는 최근 100개만 유지
- 구독자가 많은 이벤트는 성능 영향 고려
- 동기 실행이므로 콜백은 빠르게 처리

### ATB 시스템

- 60 FPS 업데이트
- 매 프레임마다 모든 캐릭터 게이지 업데이트
- 최적화: 활성 전투원만 업데이트

### 던전 생성

- BSP 알고리즘: O(n log n)
- 대형 맵은 생성 시간 증가
- 캐싱으로 재사용 가능

## 보안 고려사항

### 저장 파일

- JSON 형식 (사람이 읽을 수 있음)
- 체크섬으로 무결성 검증
- 민감 정보 없음

### 멀티플레이어

- 서버-클라이언트 모델
- 입력 검증 필수
- 치트 방지 로직

## 다음 단계

1. 각 시스템의 상세 설계 문서 작성
2. API 문서 자동 생성 (Sphinx)
3. 아키텍처 결정 기록 (ADR) 작성
