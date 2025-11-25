"""마을 창고 저장/복원 테스트"""
from src.town.town_manager import get_town_manager
from src.persistence.save_system import serialize_item, deserialize_item
from src.equipment.item_system import Equipment, ItemType, ItemRarity, EquipSlot
from src.gathering.ingredient import IngredientDatabase

print("=" * 70)
print("마을 창고 저장/복원 테스트")
print("=" * 70)

# 1. 초기 상태
manager = get_town_manager()
print(f"\n1. 초기 창고 상태: {len(manager.hub_storage)}개 아이템")

# 2. 아이템 추가
weapon = Equipment(
    item_id="test_sword",
    name="테스트 검",
    description="테스트용 무기",
    item_type=ItemType.WEAPON,
    rarity=ItemRarity.RARE,
    level_requirement=1,
    base_stats={"physical_attack": 50},
    affixes=[],
    equip_slot=EquipSlot.WEAPON,
    weight=3.0,
    sell_price=500
)

# 재료 추가
ingredient = IngredientDatabase.get_ingredient("berry")
if ingredient:
    manager.hub_storage.append(serialize_item(ingredient))
    print(f"   재료 추가: {ingredient.name}")
else:
    print(f"   재료 찾을 수 없음: berry")

# 장비 추가
manager.hub_storage.append(serialize_item(weapon))
print(f"   장비 추가: {weapon.name}")

print(f"\n2. 아이템 추가 후: {len(manager.hub_storage)}개 아이템")

# 3. 저장
town_data = manager.to_dict()
print(f"\n3. to_dict() 결과: hub_storage에 {len(town_data['hub_storage'])}개 아이템")

# 4. 복원
from src.town.town_manager import TownManager
restored_manager = TownManager.from_dict(town_data)
print(f"\n4. from_dict() 복원: {len(restored_manager.hub_storage)}개 아이템")

# 5. 전역 인스턴스 교체 시뮬레이션
import src.town.town_manager as town_module
old_id = id(town_module._town_manager)
town_module._town_manager = restored_manager
new_id = id(town_module._town_manager)

print(f"\n5. 전역 인스턴스 교체:")
print(f"   기존 ID: {old_id}")
print(f"   새로운 ID: {new_id}")
print(f"   교체됨: {old_id != new_id}")

# 6. get_town_manager()로 확인
manager_after = get_town_manager()
print(f"\n6. get_town_manager() 호출:")
print(f"   창고 아이템: {len(manager_after.hub_storage)}개")
print(f"   ID: {id(manager_after)}")
print(f"   복원된 매니저와 동일: {id(manager_after) == new_id}")

# 7. 아이템 복원 확인
print(f"\n7. 저장된 아이템 목록:")
for i, item_data in enumerate(manager_after.hub_storage):
    item = deserialize_item(item_data)
    print(f"   {i+1}. {item.name} ({item.item_type.value})")

# 8. 검증
if len(manager_after.hub_storage) == 2:
    print("\n결과: 성공! 마을 창고 아이템이 정상적으로 저장/복원됩니다.")
else:
    print(f"\n결과: 실패! 예상 2개, 실제 {len(manager_after.hub_storage)}개")

print("=" * 70)
