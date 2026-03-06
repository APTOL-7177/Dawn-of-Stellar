<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# equipment

## Purpose
아이템 정의, 인벤토리 관리, 장비 특수 효과를 담당하는 장비 시스템. 등급(Rarity), 슬롯(weapon/armor/accessory), 무게 기반 인벤토리, 이벤트 버스 연동 장비 효과를 제공한다.

## Key Files
| File | Description |
|------|-------------|
| `item_system.py` | `ItemRarity`, `ItemType`, `EquipSlot`, `ItemAffix`, `Item`, `Equipment`, `Consumable` 데이터클래스 정의 |
| `inventory.py` | `Inventory` 클래스 - 무게 기반 아이템 저장/관리, 골드 관리, 요리 쿨타임 추적 |
| `equipment_effects.py` | `EffectTrigger`, `EffectType`, `EquipmentEffect` - 장착 효과 시스템 (시야/상처/BRV/전투 연동) |
| `__init__.py` | 모듈 공개 인터페이스 |

## For AI Agents

### Working In This Directory
- `ItemRarity` Enum: COMMON, UNCOMMON, RARE, EPIC, LEGENDARY, UNIQUE (각각 색상 포함)
- `ItemType` Enum: WEAPON, ARMOR, ACCESSORY, CONSUMABLE, MATERIAL, KEY_ITEM, FOOD
- `EquipSlot`: WEAPON, ARMOR, ACCESSORY (3슬롯만 사용)
- `Inventory`는 무게 기반 - `base_weight=50.0`, 파티 스탯과 창고 시설 레벨에 따라 `max_weight` 동적 계산
- 장비 장착/해제는 `event_bus`의 `Events.EQUIPMENT_EQUIPPED` / `Events.EQUIPMENT_UNEQUIPPED` 이벤트 발행
- `EquipmentEffect`의 `EffectTrigger`로 발동 시점 지정 (ON_EQUIP, ON_HIT, PASSIVE 등)
- 순환 참조 방지를 위해 `equipment_effects` ↔ `item_system` 간 TYPE_CHECKING lazy import 사용

### Testing Requirements
- `tests/test_equipment.py` 또는 유사 파일 확인
- 인벤토리 무게 초과, 골드 음수 방지, 장비 교체 이벤트 발행 확인

### Common Patterns
```python
from src.equipment.item_system import Item, Equipment, ItemType, ItemRarity, EquipSlot
from src.equipment.inventory import Inventory

inv = Inventory(base_weight=50.0, party=party)
inv.add_item(item)
inv.add_gold(100)
equipped = inv.equip(equipment, slot=EquipSlot.WEAPON)
```

## Dependencies

### Internal
- `src.core.event_bus` - 장착/해제 이벤트 발행
- `src.core.logger` - 로깅

### External
- `dataclasses`, `enum`, `typing`, `random` - 표준 라이브러리

<!-- MANUAL: -->
