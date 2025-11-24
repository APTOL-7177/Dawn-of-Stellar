import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.equipment.item_system import ItemGenerator, WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES, ItemType

def verify_new_items():
    print("=== Verifying Multi-Era Items ===")
    
    new_items_to_check = {
        "weapon": [
            "steam_powered_hammer", "clockwork_crossbow", "tesla_coil_wand", # Steampunk
            "stop_sign_axe", "spiked_bat", "chainsaw_sword", # Apocalypse
            "laser_saber", "plasma_rifle", "nano_swarm_staff", # Sci-Fi
            "obsidian_macuahuitl", "mjolnir_replica", # Fantasy/Past
            "portal_gun", "crowbar" # Crossover
        ],
        "armor": [
            "brass_plate_armor", "aviator_jacket", # Steampunk
            "tire_tread_armor", "hazmat_suit", # Apocalypse
            "energy_shield_suit", "power_armor_mk1" # Sci-Fi
        ],
        "accessory": [
            "pocket_watch_of_time", "goggles_of_insight", # Steampunk
            "geiger_counter", "survival_kit", # Apocalypse
            "holographic_visor", "gravity_boots" # Sci-Fi
        ]
    }

    all_passed = True

    # 1. Check Templates
    print("\n[Checking Templates]")
    for category, item_ids in new_items_to_check.items():
        templates = {}
        if category == "weapon":
            templates = WEAPON_TEMPLATES
        elif category == "armor":
            templates = ARMOR_TEMPLATES
        elif category == "accessory":
            templates = ACCESSORY_TEMPLATES
        
        for item_id in item_ids:
            if item_id in templates:
                print(f"  [PASS] {item_id} found in {category.upper()}_TEMPLATES")
            else:
                print(f"  [FAIL] {item_id} NOT found in {category.upper()}_TEMPLATES")
                all_passed = False

    # 2. Check Instantiation
    print("\n[Checking Instantiation]")
    
    for category, item_ids in new_items_to_check.items():
        for item_id in item_ids:
            try:
                item = None
                if category == "weapon":
                    item = ItemGenerator.create_weapon(item_id)
                elif category == "armor":
                    item = ItemGenerator.create_armor(item_id)
                elif category == "accessory":
                    item = ItemGenerator.create_accessory(item_id)
                
                if item:
                    print(f"  [PASS] Created {item.name} ({item.rarity.name} {category})")
                    print(f"         Stats: {item.base_stats}")
                    print(f"         Effect: {item.unique_effect}")
                else:
                    print(f"  [FAIL] Failed to create {item_id} (returned None)")
                    all_passed = False
            except Exception as e:
                print(f"  [FAIL] Error creating {item_id}: {e}")
                all_passed = False

    if all_passed:
        print("\n=== All New Items Verified Successfully! ===")
    else:
        print("\n=== Some Items Failed Verification ===")

if __name__ == "__main__":
    verify_new_items()
