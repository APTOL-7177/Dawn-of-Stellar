"""장비 내구도 저장/복원 테스트"""
import json
from pathlib import Path
from src.equipment.item_system import Equipment, ItemType, ItemRarity, EquipSlot
from src.persistence.save_system import serialize_item, deserialize_item

# 테스트용 장비 생성
print("=" * 70)
print("장비 내구도 저장/복원 테스트")
print("=" * 70)

# 1. 장비 생성 (내구도 감소)
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

print(f"\n1. 원본 장비 생성:")
print(f"   이름: {weapon.name}")
print(f"   등급: {weapon.rarity.display_name}")
print(f"   최대 내구도: {weapon.max_durability}")
print(f"   현재 내구도: {weapon.current_durability}")

# 2. 내구도 감소 시뮬레이션
weapon.current_durability = 80
print(f"\n2. 내구도 감소 시뮬레이션:")
print(f"   현재 내구도: {weapon.current_durability} (80으로 감소)")

# 3. 직렬화 (저장)
serialized = serialize_item(weapon)
print(f"\n3. 직렬화 결과:")
print(f"   max_durability: {serialized.get('max_durability')}")
print(f"   current_durability: {serialized.get('current_durability')}")

# 4. JSON 저장 테스트
test_save_path = Path("test_durability_save.json")
with open(test_save_path, 'w', encoding='utf-8') as f:
    json.dump(serialized, f, indent=2, ensure_ascii=False)
print(f"\n4. JSON 파일 저장: {test_save_path}")

# 5. JSON 로드 테스트
with open(test_save_path, 'r', encoding='utf-8') as f:
    loaded_data = json.load(f)
print(f"\n5. JSON 파일 로드:")
print(f"   max_durability: {loaded_data.get('max_durability')}")
print(f"   current_durability: {loaded_data.get('current_durability')}")

# 6. 역직렬화 (복원)
restored_weapon = deserialize_item(loaded_data)
print(f"\n6. 역직렬화 결과:")
print(f"   이름: {restored_weapon.name}")
print(f"   등급: {restored_weapon.rarity.display_name}")
print(f"   최대 내구도: {restored_weapon.max_durability}")
print(f"   현재 내구도: {restored_weapon.current_durability}")

# 7. 검증
success = True
if weapon.max_durability != restored_weapon.max_durability:
    print(f"\n❌ 최대 내구도 불일치: {weapon.max_durability} != {restored_weapon.max_durability}")
    success = False
if weapon.current_durability != restored_weapon.current_durability:
    print(f"\n❌ 현재 내구도 불일치: {weapon.current_durability} != {restored_weapon.current_durability}")
    success = False

if success:
    print("\n✅ 모든 테스트 통과! 장비 내구도가 정상적으로 저장/복원됩니다.")
else:
    print("\n❌ 테스트 실패!")

# 8. 정리
test_save_path.unlink()
print(f"\n8. 테스트 파일 삭제: {test_save_path}")
print("=" * 70)
