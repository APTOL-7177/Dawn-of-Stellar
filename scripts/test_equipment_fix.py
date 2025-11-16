"""장비 스탯 적용 테스트 스크립트"""

import sys
sys.path.insert(0, "X:/develop/Dos")

from src.character.character import Character
from src.equipment.item_system import ItemGenerator

def test_equipment_stats():
    """장비 착용 시 스탯이 제대로 적용되는지 테스트"""
    print("=" * 60)
    print("장비 스탯 적용 테스트")
    print("=" * 60)

    # 캐릭터 생성
    char = Character("테스트 전사", "전사", level=1)

    print(f"\n[초기 스탯]")
    print(f"HP: {char.max_hp}")
    print(f"방어력: {char.defense}")
    print(f"물리 공격력: {char.strength}")

    # 무기 생성 (철검: 물리 공격력 +15, 명중률 +5)
    weapon = ItemGenerator.create_weapon("iron_sword", add_random_affixes=False)
    print(f"\n[장착할 무기: {weapon.name}]")
    print(f"스탯: {weapon.get_total_stats()}")

    # 무기 착용
    char.equip_item("weapon", weapon)
    print(f"\n[무기 착용 후]")
    print(f"물리 공격력: {char.strength} (기대: 초기값 + 15)")

    # 방어구 생성 (가죽 갑옷: 물리 방어력 +10, HP +20)
    armor = ItemGenerator.create_armor("leather_armor", add_random_affixes=False)
    print(f"\n[장착할 방어구: {armor.name}]")
    print(f"스탯: {armor.get_total_stats()}")

    # 방어구 착용
    initial_defense = char.defense
    initial_max_hp = char.max_hp

    char.equip_item("armor", armor)
    print(f"\n[방어구 착용 후]")
    print(f"HP: {char.max_hp} (기대: {initial_max_hp} + 20 = {initial_max_hp + 20})")
    print(f"방어력: {char.defense} (기대: {initial_defense} + 10 = {initial_defense + 10})")

    # 검증
    if char.max_hp == initial_max_hp + 20:
        print("\n[OK] HP 증가 정상!")
    else:
        print(f"\n[FAIL] HP 증가 실패! 예상: {initial_max_hp + 20}, 실제: {char.max_hp}")

    if char.defense == initial_defense + 10:
        print("[OK] 방어력 증가 정상!")
    else:
        print(f"[FAIL] 방어력 증가 실패! 예상: {initial_defense + 10}, 실제: {char.defense}")

    # 장비 해제 테스트
    print(f"\n[장비 해제 테스트]")
    char.unequip_item("armor")
    print(f"HP: {char.max_hp} (기대: {initial_max_hp})")
    print(f"방어력: {char.defense} (기대: {initial_defense})")

    if char.max_hp == initial_max_hp:
        print("\n[OK] 장비 해제 후 HP 복원 정상!")
    else:
        print(f"\n[FAIL] 장비 해제 후 HP 복원 실패! 예상: {initial_max_hp}, 실제: {char.max_hp}")

    if char.defense == initial_defense:
        print("[OK] 장비 해제 후 방어력 복원 정상!")
    else:
        print(f"[FAIL] 장비 해제 후 방어력 복원 실패! 예상: {initial_defense}, 실제: {char.defense}")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    test_equipment_stats()
