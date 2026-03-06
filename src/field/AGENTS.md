<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# field

## Purpose
필드(탐험 맵)에서 사용하는 스킬, 요리솥 상호작용, 채집 로직을 담당하는 모듈. 탐험 중 플레이어가 필드 오브젝트와 상호작용하는 진입점 역할을 한다.

## Key Files
| File | Description |
|------|-------------|
| `field_skills.py` | `FieldSkillManager` - `SkillCategory.FIELD` 스킬 실행 (자물쇠 해제, 탐지, 은신 등) |
| `cooking.py` | 탐험 중 요리솥(`COOKING_POT`) 감지 및 `src/ui/cooking_ui.py` 연동 |
| `gathering.py` | 탐험 중 채집 포인트(`Harvestable`) 감지 및 `src/ui/gathering_ui.py` 연동 |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `FieldSkillManager`는 `skill_type_registry.get_by_category(SkillCategory.FIELD)`로 스킬 목록 로드
- 필드 스킬은 `src/character/skill_types.py`의 레지스트리에 등록된 것만 사용 가능
- 요리솥 상호작용: `WorldUI.handle_input(CONFIRM)` → `_find_nearby_cooking_pot()` → `open_cooking_pot()` 호출
- 채집: `_find_all_nearby_harvestables()` → `harvest_object()` 순서로 처리
- `console`/`context`/`inventory`가 모두 `None`이 아닌지 반드시 확인 후 UI 호출
- 필드 스킬 실행 결과는 `Dict[str, Any]` 또는 `None` 반환

### Testing Requirements
- `FieldSkillManager.use_skill()` - 미등록 스킬 ID, 잘못된 카테고리 처리 테스트
- 요리솥/채집 근처 감지 로직 단위 테스트

### Common Patterns
```python
from src.field.field_skills import FieldSkillManager

manager = FieldSkillManager()
result = manager.use_skill(
    skill_type_id="detect",
    user=player,
    target=None,
    context={"exploration": exploration}
)
```

## Dependencies

### Internal
- `src.character.skill_types` - `skill_type_registry`, `SkillCategory`
- `src.ui.cooking_ui` - `open_cooking_pot()`
- `src.ui.gathering_ui` - `harvest_object()`
- `src.core.logger` - 로깅

### External
- `typing` - 표준 라이브러리

<!-- MANUAL: -->
