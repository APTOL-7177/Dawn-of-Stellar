"""장비 내구도 저장/복원 간단 테스트"""
from src.equipment.item_system import Equipment, ItemType, ItemRarity, EquipSlot
from src.persistence.save_system import serialize_item, deserialize_item

print("=" * 70)
print("장비 내구도 저장/복원 간단 테스트")
print("=" * 70)

# 1. 장비 생성
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

print(f"\n[원본] 최대: {weapon.max_durability}, 현재: {weapon.current_durability}")

# 2. 내구도 감소
weapon.current_durability = 75

print(f"[감소] 최대: {weapon.max_durability}, 현재: {weapon.current_durability}")

# 3. 저장 후 복원
serialized = serialize_item(weapon)
restored = deserialize_item(serialized)

print(f"[복원] 최대: {restored.max_durability}, 현재: {restored.current_durability}")

# 4. 검증
if weapon.max_durability == restored.max_durability and weapon.current_durability == restored.current_durability:
    print("\n결과: 성공! 내구도가 정상적으로 저장/복원됩니다.")
else:
    print("\n결과: 실패!")
    print(f"  최대 내구도: {weapon.max_durability} -> {restored.max_durability}")
    print(f"  현재 내구도: {weapon.current_durability} -> {restored.current_durability}")

print("=" * 70)
