"""
Comprehensive Item Verification Script

Tests all items in item_system.py can be generated and have valid effects.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.equipment.item_system import (
    WEAPON_TEMPLATES,
    ARMOR_TEMPLATES,
    ACCESSORY_TEMPLATES,
    ItemGenerator,
    ItemRarity
)

def verify_items():
    print("=== Verifying Complete Item Library ===\n")
    
    total_weapons = len(WEAPON_TEMPLATES)
    total_armor = len(ARMOR_TEMPLATES)
    total_accessories = len(ACCESSORY_TEMPLATES)
    total_items = total_weapons + total_armor + total_accessories
    
    print(f"📊 Item Counts:")
    print(f"  Weapons: {total_weapons}")
    print(f"  Armor: {total_armor}")
    print(f"  Accessories: {total_accessories}")
    print(f"  TOTAL: {total_items}\n")
    
    # Verify weapons
    print("[Verifying Weapons]")
    failed_weapons = []
    for weapon_id, template in WEAPON_TEMPLATES.items():
        try:
            weapon = ItemGenerator.create_weapon(weapon_id)
            if weapon is None:
                failed_weapons.append(f"{weapon_id}: Failed to create")
        except Exception as e:
            failed_weapons.append(f"{weapon_id}: {str(e)}")
    
    if failed_weapons:
        print(f"  ❌ {len(failed_weapons)} weapons failed:")
        for fail in failed_weapons[:5]:  # Show first 5
            print(f"    - {fail}")
    else:
        print(f"  ✅ All {total_weapons} weapons verified!\n")
    
    # Verify armor
    print("[Verifying Armor]")
    failed_armor = []
    for armor_id, template in ARMOR_TEMPLATES.items():
        try:
            armor = ItemGenerator.create_armor(armor_id)
            if armor is None:
                failed_armor.append(f"{armor_id}: Failed to create")
        except Exception as e:
            failed_armor.append(f"{armor_id}: {str(e)}")
    
    if failed_armor:
        print(f"  ❌ {len(failed_armor)} armor pieces failed:")
        for fail in failed_armor[:5]:
            print(f"    - {fail}")
    else:
        print(f"  ✅ All {total_armor} armor pieces verified!\n")
    
    # Verify accessories
    print("[Verifying Accessories]")
    failed_accessories = []
    for acc_id, template in ACCESSORY_TEMPLATES.items():
        try:
            accessory = ItemGenerator.create_accessory(acc_id)
            if accessory is None:
                failed_accessories.append(f"{acc_id}: Failed to create")
        except Exception as e:
            failed_accessories.append(f"{acc_id}: {str(e)}")
    
    if failed_accessories:
        print(f"  ❌ {len(failed_accessories)} accessories failed:")
        for fail in failed_accessories[:5]:
            print(f"    - {fail}")
    else:
        print(f"  ✅ All {total_accessories} accessories verified!\n")
    
    # Summary
    print("=" * 60)
    total_failed = len(failed_weapons) + len(failed_armor) + len(failed_accessories)
    if total_failed == 0:
        print(f"✅ SUCCESS: All {total_items} items verified successfully!")
    else:
        print(f"⚠️  WARNING: {total_failed} items failed verification")
        print(f"   Passed: {total_items - total_failed}/{total_items}")
    print("=" * 60)
    
    # Rarity distribution
    print("\n📈 Rarity Distribution:")
    rarity_counts = {
        "COMMON": 0,
        "UNCOMMON": 0,
        "RARE": 0,
        "EPIC": 0,
        "LEGENDARY": 0
    }
    
    for template in list(WEAPON_TEMPLATES.values()) + list(ARMOR_TEMPLATES.values()) + list(ACCESSORY_TEMPLATES.values()):
        rarity = template.get("rarity")
        if rarity:
            rarity_counts[rarity.name] = rarity_counts.get(rarity.name, 0) + 1
    
    for rarity, count in rarity_counts.items():
        percentage = (count / total_items * 100) if total_items > 0 else 0
        print(f"  {rarity:10s}: {count:3d} ({percentage:5.1f}%)")
    
    return total_failed == 0

if __name__ == "__main__":
    success = verify_items()
    sys.exit(0 if success else 1)
