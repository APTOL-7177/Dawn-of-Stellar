<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# world/

## Purpose
던전 생성, 탐험 시스템, FOV, 타일, 적 스폰, 환경 효과, 랜덤 이벤트를 담당. BSP 알고리즘으로 절차적 던전을 생성하고, `ExplorationSystem`이 플레이어 이동 및 이벤트 처리를 관리한다.

## Key Files

| File | Description |
|------|-------------|
| `exploration.py` | `ExplorationSystem` 클래스. 플레이어 이동, 충돌, 이벤트 처리. `ExplorationEvent` enum, `Enemy`/`Player` dataclass 포함 |
| `dungeon_generator.py` | BSP 알고리즘 기반 절차적 던전 생성. `DungeonMap`, `Rect`, `BSPNode` 클래스 |
| `tile.py` | `Tile` dataclass, `TileType` enum (WALL/FLOOR/STAIRS/DOOR 등) |
| `fov.py` | `FOVSystem` 클래스. 시야(Field of View) 계산 — 플레이어 탐색 반경 내 타일 공개 |
| `enemy_generator.py` | `EnemyGenerator` 클래스. 층 번호·난이도 기반 적 스폰 |
| `map_renderer.py` | 던전 맵 TCOD 렌더링 |
| `interactive_object.py` | 상호작용 가능 오브젝트 (상자, 문, NPC, 마법진 등) |
| `environmental_effects.py` | 환경 효과 시스템 (독 타일, 화염 타일 등) — 타일 밟을 때 효과 적용 |
| `random_events.py` | 랜덤 탐험 이벤트 정의 및 트리거 |
| `field_skills.py` | 필드 스킬 사용 처리 (탐험 중 스킬 사용) |

## For AI Agents

### Working In This Directory
- `ExplorationEvent` enum이 모든 탐험 결과를 나타냄: `COMBAT`, `ITEM_FOUND`, `BOSS_ROOM`, `STAIRS_DOWN` 등
- `ExplorationResult` dataclass: `success: bool`, `event: ExplorationEvent`, `message: str`, `data: Dict`
- 던전 생성: `DungeonMap(width, height, seed)` → BSP 분할 → 방 생성 → 복도 연결
- `Enemy` dataclass는 탐험용 엔티티 (전투용 `SimpleEnemy`와 다름)
- FOV 반경: 기본 `fov_radius=3` (Player dataclass)
- 층 전환: `ExplorationEvent.STAIRS_DOWN` / `STAIRS_UP` 이벤트로 처리

### Testing Requirements
- 던전 생성 테스트: `DungeonMap` 생성 후 방 수·복도 연결 검증
- 탐험 이벤트 테스트: `ExplorationSystem.move()` 결과 이벤트 타입 검증

### Common Patterns
```python
# 던전 생성
from src.world.dungeon_generator import DungeonMap
dungeon = DungeonMap(width=80, height=50, seed=12345)
dungeon.generate()

# 탐험 시스템
from src.world.exploration import ExplorationSystem, ExplorationEvent
exploration = ExplorationSystem(dungeon=dungeon, player=player)
result = exploration.move(dx=1, dy=0)
if result.event == ExplorationEvent.COMBAT:
    enemies = result.data["enemies"]
```

## Dependencies

### Internal
- `src.core.event_bus` — `Events.WORLD_*` 이벤트 발행
- `src.core.logger` — `Loggers.WORLD` 카테고리
- `src.core.config` — 던전 설정 (`world.dungeon.*`)
- `src.audio` — 탐험 효과음

### External
- `tcod` (python-tcod): FOV 계산, 맵 렌더링

<!-- MANUAL: -->
