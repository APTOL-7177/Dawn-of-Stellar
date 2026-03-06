<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# town

## Purpose
마을 허브 맵과 시설 업그레이드, 던전-마을 간 층 전환을 관리하는 시스템. 주방, 대장간, 연금술 실험실, 창고, 상점, 여관, 길드홀 등의 건물과 플레이어의 이동을 처리한다.

## Key Files
| File | Description |
|------|-------------|
| `town_manager.py` | `FacilityType` Enum, `Facility` 데이터클래스, `TownManager` - 시설 레벨 관리 및 업그레이드 비용 계산 |
| `town_map.py` | `BuildingType` Enum, `Building` 데이터클래스 - 마을 허브 맵의 건물 배치 및 접근 로직 |
| `floor_transition.py` | `FloorTransitionManager` - 던전 층 입장/퇴장, 바이옴 BGM 선택, 마을 복귀 처리 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `FacilityType`: KITCHEN, BLACKSMITH, ALCHEMY_LAB, STORAGE, SHOP (각 최대 레벨 4)
- 시설 업그레이드 비용: 레벨별 목재/석재/철광석/골드 소비, SHOP은 별의 파편으로 구매
- `BuildingType`: KITCHEN, BLACKSMITH, ALCHEMY_LAB, STORAGE, QUEST_BOARD, SHOP, INN, GUILD_HALL, FOUNTAIN
- `FloorTransitionManager` 주요 메서드:
  - `get_biome_bgm(floor_number)`: 층 번호로 바이옴 BGM 결정 (10개 바이옴 순환)
  - `enter_dungeon_floor(floor_number)`: 던전 층 입장 처리
  - `on_floor_clear()`: 보스 층(20층, 30층) 클리어 후 마을 복귀 트리거
- `get_floor_transition_manager()` 싱글톤으로 전역 접근
- 마을 상태는 `ExplorationSystem.is_town = True`로 표시
- 시설 레벨은 `MetaProgress.facility_levels`에 영구 저장 (게임 오버 후에도 유지)

### Testing Requirements
- `get_biome_bgm()` - 층 번호 1~10, 11~20 순환 확인
- 시설 업그레이드 비용 레벨별 확인
- `enter_dungeon_floor()` / `on_floor_clear()` 상태 전환 테스트

### Common Patterns
```python
from src.town.floor_transition import get_floor_transition_manager

floor_mgr = get_floor_transition_manager()
bgm = floor_mgr.get_biome_bgm(floor_number=5)  # "biome_4"
floor_mgr.enter_dungeon_floor(5)
# 보스 클리어 후
floor_mgr.on_floor_clear()
```

## Dependencies

### Internal
- `src.core.logger` - 로깅
- `src.persistence.meta_progress` - 시설 레벨 영구 저장

### External
- `enum`, `dataclasses`, `typing`, `random` - 표준 라이브러리

<!-- MANUAL: -->
