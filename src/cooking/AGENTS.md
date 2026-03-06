<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# cooking

## Purpose
돈스타브 스타일의 요리 시스템. 최대 4개의 재료를 조합하여 레시피를 매칭하고 음식 아이템을 제작하며, 포션 양조와 폭탄 제작도 포함한다.

## Key Files
| File | Description |
|------|-------------|
| `recipe.py` | `RecipePriority`, `RecipeCondition`, `Recipe` 데이터클래스 - 재료 조합 조건 및 결과 정의 |
| `potion_brewing.py` | 연금술 재료(`IngredientCategory.ALCHEMY`)로 포션 제작 로직 |
| `bomb_crafting.py` | 폭발물 재료(`IngredientCategory.EXPLOSIVE`)로 폭탄 제작 로직 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- 레시피 데이터는 `data/cooking_recipes.yaml`에서 로드됨 (코드에 하드코딩 없음)
- `RecipePriority` Enum으로 우선순위 결정 - 여러 레시피가 매칭될 때 높은 우선순위 선택
- `RecipeCondition.matches(ingredients)` - 재료 리스트(최대 4개)가 조건을 만족하는지 확인
  - `min_category`, `max_category`: 카테고리별 food_value 범위 제한
  - `required_ingredients`, `required_counts`: 특정 재료 필수 포함
  - `banned_ingredients`: 특정 재료 금지
  - `custom_check`: 커스텀 람다 조건
- 요리 UI는 `src/ui/cooking_ui.py`의 `open_cooking_pot()` 참조
- 요리 쿨타임은 `Inventory.cooking_cooldown_turn`으로 관리 (전투 턴 기준)

### Testing Requirements
- `tests/` 디렉토리의 요리 관련 테스트 확인
- `RecipeCondition.matches()` 단위 테스트 작성 권장

### Common Patterns
```python
from src.cooking.recipe import RecipeCondition, RecipePriority
from src.gathering.ingredient import IngredientCategory

# 레시피 조건 정의
condition = RecipeCondition(
    min_category={IngredientCategory.MEAT: 1.0},
    required_ingredients=["carrot"],
)
result = condition.matches(ingredients)
```

## Dependencies

### Internal
- `src.gathering.ingredient` - `Ingredient`, `IngredientCategory`
- `src.equipment.item_system` - `ItemType`

### External
- `dataclasses`, `enum`, `typing` - 표준 라이브러리

<!-- MANUAL: -->
