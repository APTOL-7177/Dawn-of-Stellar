"""
Find problematic items in item_system.py
"""

import re

# Read the file
with open("src/equipment/item_system.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find items with problematic effects
invalid_effects = [
    "night_vision", "lunar_power", "inventory_space", 
    "carry_weight", "map_reveal", "terrain_ignore", "flight"
]

# Find descriptions with stats/effects (contains +, %, numbers)
effect_pattern = re.compile(r'"description":\s*"[^"]*[+%][^"]*"', re.MULTILINE)
description_issues = effect_pattern.findall(content)

# Find duplicate item names
name_pattern = re.compile(r'"name":\s*"([^"]+)"', re.MULTILINE)
names = name_pattern.findall(content)
duplicates = {}
for name in names:
    if names.count(name) > 1:
        if name not in duplicates:
            duplicates[name] = names.count(name)

print("=" * 60)
print("PROBLEMATIC ITEMS REPORT")
print("=" * 60)

print(f"\n📋 Descriptions with effects (should be item descriptions): {len(description_issues)}")
for i, desc in enumerate(description_issues[:10], 1):
    print(f"  {i}. {desc[:80]}...")

print(f"\n🔄 Duplicate item names: {len(duplicates)}")
for name, count in duplicates.items():
    print(f"  - '{name}' appears {count} times")

print(f"\n❌ Invalid effects to remove:")
for effect in invalid_effects:
    count = content.count(effect)
    if count > 0:
        print(f"  - {effect}: {count} occurrences")

print("\n" + "=" * 60)
