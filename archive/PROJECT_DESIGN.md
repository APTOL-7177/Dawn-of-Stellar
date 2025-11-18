# Dawn of Stellar - 재구조화 설계 문서

## 설계 원칙

### 1. 관심사의 명확한 분리 (Separation of Concerns)
- 각 모듈은 하나의 책임만 가짐
- 시스템 간 명확한 경계 정의
- 인터페이스를 통한 느슨한 결합

### 2. 확장 가능한 아키텍처 (Scalable Architecture)
- 플러그인 방식의 시스템 확장
- 이벤트 기반 아키텍처로 디커플링
- 의존성 주입 패턴 활용

### 3. Claude Code 기능 적극 활용
- **Custom Commands**: 반복 작업 자동화
- **Skills**: 특화된 작업 지원
- **MCP Servers**: 외부 도구 통합

### 4. 테스트 가능한 설계
- 단위 테스트 우선 설계
- 모의 객체(Mock) 활용 가능한 인터페이스
- 통합 테스트 자동화

## 아키텍처 개요

```
┌─────────────────────────────────────────────┐
│           Main Game Loop                     │
│         (main.py / game_engine.py)           │
└──────────────┬──────────────────────────────┘
               │
        ┌──────┴──────┐
        │  Event Bus   │  ← 중앙 이벤트 시스템
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
│      Persistence Layer            │
│   (Save/Load, Data Management)    │
└───────────────────────────────────┘
```

## 폴더 구조 상세

### `/src/core/` - 핵심 시스템
게임의 근간이 되는 핵심 컴포넌트

- `game_engine.py`: 메인 게임 루프, 시스템 초기화
- `event_bus.py`: 이벤트 기반 통신 (pub-sub 패턴)
- `config.py`: 설정 관리 (YAML 기반)
- `logger.py`: 구조화된 로깅
- `registry.py`: 서비스 레지스트리 (DI 컨테이너)

### `/src/combat/` - 전투 시스템
모든 전투 관련 로직

- `combat_manager.py`: 전투 흐름 제어
- `atb_system.py`: ATB 게이지 관리
- `brave_system.py`: BRV/HP 메커니즘
- `damage_calculator.py`: 데미지 계산 엔진
- `status_effects.py`: 상태 효과 관리
- `actions/`: 전투 액션 정의

### `/src/character/` - 캐릭터 시스템
캐릭터 생성, 성장, 관리

- `character.py`: 캐릭터 기본 클래스
- `stats.py`: 스탯 관리 및 계산
- `classes/`: 28개 직업 정의
- `skills/`: 스킬 시스템
  - `skill_base.py`: 스킬 기본 클래스
  - `skill_database.py`: 스킬 데이터베이스
  - `skill_executor.py`: 스킬 실행 엔진

### `/src/world/` - 월드 시스템
맵, 던전, 상호작용

- `world_manager.py`: 월드 상태 관리
- `dungeon_generator.py`: 절차적 던전 생성
- `map.py`: 맵 데이터 구조
- `tile.py`: 타일 정의
- `interactions.py`: 오브젝트 상호작용

### `/src/ai/` - AI 시스템
모든 AI 행동 로직

- `ai_manager.py`: AI 전역 관리
- `companion_ai.py`: 동료 AI (전술적 의사결정)
- `enemy_ai.py`: 적 AI
- `decision_tree.py`: 의사결정 트리
- `tactical_analyzer.py`: 전술 분석

### `/src/equipment/` - 장비 시스템
장비, 아이템, 인벤토리

- `equipment.py`: 장비 클래스
- `inventory.py`: 인벤토리 관리
- `equipment_manager.py`: 장비 시스템 관리
- `item_generator.py`: 아이템 생성

### `/src/multiplayer/` - 멀티플레이어
네트워크 멀티플레이어

- `network.py`: 네트워크 레이어
- `protocol.py`: 통신 프로토콜
- `lobby.py`: 로비 시스템
- `sync.py`: 게임 상태 동기화

### `/src/ui/` - UI 시스템
사용자 인터페이스

- `display.py`: 디스플레이 관리
- `menus.py`: 메뉴 시스템
- `animations.py`: UI 애니메이션
- `input_handler.py`: 입력 처리
- `korean_input.py`: 한국어 입력 지원

### `/src/audio/` - 오디오 시스템
사운드 및 음악

- `audio_manager.py`: 오디오 전역 관리
- `bgm_player.py`: BGM 재생
- `sfx_player.py`: 효과음 재생

### `/src/persistence/` - 영속성 레이어
저장/로드 및 데이터 관리

- `save_manager.py`: 세이브 파일 관리
- `serializers.py`: 객체 직렬화
- `validators.py`: 데이터 검증
- `data_loader.py`: 정적 데이터 로딩

### `/src/utils/` - 유틸리티
공통 유틸리티 함수

- `math_utils.py`: 수학 연산
- `text_utils.py`: 텍스트 처리
- `timing.py`: 타이밍 유틸
- `validation.py`: 일반 검증

## Claude Code 통합

### Custom Commands (`.claude/commands/`)

#### `/test` - 테스트 실행
```markdown
Run the test suite:
- Unit tests: `pytest tests/unit/`
- Integration tests: `pytest tests/integration/`
- Coverage report: `pytest --cov=src tests/`
```

#### `/run` - 게임 실행
```markdown
Start the game with various modes:
- Development mode: `python main.py --dev`
- Debug mode: `python main.py --debug`
- Specific log level: `python main.py --log=DEBUG`
```

#### `/build` - 빌드
```markdown
Build the project:
1. Run tests
2. Check code quality (pylint, mypy)
3. Generate documentation
4. Create distributable package
```

#### `/add-character` - 캐릭터 클래스 추가
```markdown
Add a new character class:
1. Create class definition in `src/character/classes/`
2. Add skills to skill database
3. Update character creator
4. Add tests
```

#### `/add-skill` - 스킬 추가
```markdown
Add a new skill:
1. Define skill in `data/skills/`
2. Implement skill effect
3. Add to skill database
4. Write tests
```

#### `/debug-combat` - 전투 디버깅
```markdown
Debug combat issues:
1. Check latest combat logs
2. Analyze ATB timing
3. Verify damage calculations
4. Check status effects
```

### Project Instructions (`.claude/CLAUDE.md`)

프로젝트별 상세 가이드:
- 아키텍처 설명
- 코딩 컨벤션
- 주요 패턴 및 관례
- 일반적인 작업 가이드
- 문제 해결 체크리스트

## 핵심 패턴

### 1. Event-Driven Architecture
```python
# 이벤트 발행
event_bus.publish("character.level_up", {
    "character_id": char.id,
    "new_level": char.level
})

# 이벤트 구독
event_bus.subscribe("character.level_up", on_level_up)
```

### 2. Service Registry (DI Container)
```python
# 서비스 등록
registry.register("combat_manager", CombatManager())

# 서비스 사용
combat_mgr = registry.get("combat_manager")
```

### 3. Plugin Architecture
```python
# 새로운 스킬 타입 추가
@skill_registry.register("teleport")
class TeleportSkill(SkillBase):
    def execute(self, context):
        # 구현
        pass
```

### 4. Strategy Pattern
```python
# 다양한 AI 전략
class AggressiveAI(AIStrategy):
    def decide_action(self, context):
        # 공격적 AI 로직
        pass

class DefensiveAI(AIStrategy):
    def decide_action(self, context):
        # 방어적 AI 로직
        pass
```

## 데이터 구조

### Character Data (JSON/YAML)
```yaml
# data/characters/warrior.yaml
class_name: "전사"
base_stats:
  hp: 120
  mp: 30
  strength: 18
  defense: 15
skills:
  - power_strike
  - shield_bash
  - war_cry
passives:
  - heavy_armor_mastery
```

### Skill Data
```yaml
# data/skills/power_strike.yaml
id: power_strike
name: "강타"
type: brv_attack
mp_cost: 15
cast_time: 1.0
effects:
  - type: damage
    multiplier: 2.5
    stat: strength
  - type: status
    effect: stun
    chance: 0.2
```

## 마이그레이션 전략

### Phase 1: 핵심 시스템 (1-2주)
1. 프로젝트 구조 생성
2. Core 시스템 구축
3. Character 시스템 이전
4. Combat 시스템 이전

### Phase 2: 주요 기능 (2-3주)
5. World 시스템 이전
6. Equipment 시스템 이전
7. UI 시스템 재구성
8. Audio 시스템 통합

### Phase 3: 고급 기능 (2-3주)
9. AI 시스템 이전
10. Multiplayer 시스템 이전
11. 저장/로드 시스템 구축
12. 테스트 작성

### Phase 4: 검증 및 문서화 (1주)
13. 통합 테스트
14. 성능 최적화
15. 문서 작성
16. 배포 준비

## 개발 가이드라인

### 코딩 스타일
- PEP 8 준수
- Type hints 사용
- Docstring (Google 스타일)
- 한국어 주석 권장

### 테스트 원칙
- 각 모듈은 독립적으로 테스트 가능
- 최소 80% 코드 커버리지
- 통합 테스트로 시스템 간 상호작용 검증

### Git 워크플로우
- Feature branch 사용
- Commit message: 한국어 또는 영어 (일관성 유지)
- PR 리뷰 필수

### 문서화
- 모든 public API는 문서화
- 아키텍처 결정 기록 (ADR)
- 변경사항은 CHANGELOG.md에 기록

## 기술 스택

- **언어**: Python 3.10+
- **설정**: YAML (PyYAML)
- **테스트**: pytest, pytest-cov
- **타입 체크**: mypy
- **린팅**: pylint, black
- **문서**: Sphinx
- **패키징**: poetry

## 성공 지표

1. ✅ 모듈 간 순환 의존성 0개
2. ✅ 테스트 커버리지 > 80%
3. ✅ 새 캐릭터 클래스 추가 시간 < 1시간
4. ✅ 새 스킬 추가 시간 < 30분
5. ✅ 빌드 시간 < 5분
6. ✅ 명확한 문서화 및 예제 제공
