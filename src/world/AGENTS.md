<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# world - 던전 및 탐색 시스템

## Purpose

로그라이크 던전 생성, 플레이어 탐색, 맵 렌더링, 시야(FOV), 적 배치, 타일 시스템을 관리합니다.

## Key Files

| File | Description |
|------|-------------|
| `exploration.py` | 플레이어 탐색, 인벤토리 상호작용, 몬스터 마주침 |
| `dungeon_generator.py` | 로그라이크 던전 절차적 생성 (방, 복도, 계단) |
| `enemy_generator.py` | 몬스터 배치 및 밸런싱 (직업, 레벨, 능력치) |
| `map_renderer.py` | tcod 기반 맵 그리기, 조명, FOV 시각화 |
| `fov.py` | 시야 계산 (recursive shadowcast) |
| `tile.py` | 타일 데이터 구조 (타입, 속성, 걷기 가능 여부) |
| `field_skills.py` | 필드 스킬 (채집, 요리) |
| `interactive_object.py` | 상호작용 객체 (보물 상자, NPC) |
| `environmental_effects.py` | 환경 효과 (화염, 독, 얼음 바닥) |
| `random_events.py` | 무작위 이벤트 및 마주침 |

## For AI Agents

### Working In This Directory

- **던전 생성 알고리즘**: `dungeon_generator.py` 수정
- **적 배치 규칙**: `enemy_generator.py`에서 레벨/직업 선택 로직
- **맵 렌더링 최적화**: `map_renderer.py`의 드로잉 순서
- **FOV 알고리즘**: `fov.py`에서 시야 계산 방식 변경
- **환경 효과**: `environmental_effects.py`에 새 효과 추가

### Testing Requirements

- 던전 생성 테스트: 방과 복도 연결성 확인
- 적 배치 테스트: 직업 분포, 능력치 범위
- FOV 테스트: 대칭성, 벽 처리
- 타일 충돌 테스트: 걷기 불가능한 타일 처리
- 성능 테스트: 큰 맵의 렌더링 속도

### Common Patterns

- 절차적 생성 (랜덤 시드 기반)
- 공간 분할 (BSP 또는 그리드 기반)
- 레이 캐스팅 (FOV 계산)
- 계층화된 렌더링 (배경 → 객체 → 플레이어 → UI)
- 월드 좌표 vs 스크린 좌표 변환

## Dependencies

### Internal
- `character/` - 플레이어, 적 캐릭터 데이터
- `combat/` - 몬스터 마주침 시 전투 시작
- `core/logger.py` - 디버그 로깅
- `core/event_bus.py` - 몬스터 마주침, 레벨 변경 이벤트

### External
- `tcod` - FOV, 맵 렌더링
- `numpy` - 그리드 기반 맵 데이터
- `pygame` - 그래픽 렌더링 (대체 백엔드)

<!-- MANUAL: -->
