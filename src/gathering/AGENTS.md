<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# gathering

## Purpose
던전 맵에 배치되는 채집 포인트(HarvestableObject)와 채집 가능한 재료 아이템(Ingredient) 데이터를 정의하는 수집 시스템.

## Key Files
| File | Description |
|------|-------------|
| `harvestable.py` | `HarvestableType` Enum, `HarvestableObject` 데이터클래스 - 채집 포인트 타입 및 맵 심볼 정의 |
| `ingredient.py` | `IngredientCategory` Enum, `Ingredient` 데이터클래스, `IngredientDatabase` - 재료 아이템 데이터 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `HarvestableType` 종류: BERRY_BUSH(♣), MUSHROOM_PATCH(♠), HERB_PLANT(♦), TREE(♣), ROCK(O), WATER(≈), CARCASS(X), COOKING_POT(Ω)
- `HarvestableObject`는 `@dataclass` - `x`, `y` 위치, `object_type`, `harvested` 플래그 포함
- `IngredientCategory` 종류: MEAT, VEGETABLE, FRUIT, MUSHROOM, FISH, EGG, DAIRY, GRAIN, SPICE, SWEETENER, FILLER, PREPARED_DISH, CONSTRUCTION, ALCHEMY, EXPLOSIVE
- `Ingredient`는 `src/equipment/item_system.py`의 `Item`을 상속 - `food_value`, `category` 추가 속성
- `IngredientDatabase`는 재료 ID → Ingredient 매핑 제공
- 채집 UI는 `src/ui/gathering_ui.py`의 `harvest_object()` 참조
- 던전 생성 시 `world/dungeon_generator.py`가 `harvestables` 리스트에 `HarvestableObject` 배치

### Testing Requirements
- `HarvestableType.display_name`, `symbol` 프로퍼티 검증
- `IngredientCategory.display_name` 한글 반환 확인
- `HarvestableObject.harvested` 플래그 토글 테스트

### Common Patterns
```python
from src.gathering.harvestable import HarvestableType, HarvestableObject
from src.gathering.ingredient import IngredientDatabase, IngredientCategory

# 채집 포인트 생성
h = HarvestableObject(x=5, y=3, object_type=HarvestableType.BERRY_BUSH)
print(h.object_type.symbol)   # "♣"
print(h.object_type.display_name)  # "베리 덤불"

# 재료 조회
db = IngredientDatabase()
ingredient = db.get("carrot")
```

## Dependencies

### Internal
- `src.equipment.item_system` - `Item`, `ItemType`, `ItemRarity` (Ingredient 부모 클래스)

### External
- `enum`, `dataclasses`, `typing`, `random` - 표준 라이브러리

<!-- MANUAL: -->
