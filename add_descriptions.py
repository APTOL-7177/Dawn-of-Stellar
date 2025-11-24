"""
Add empty descriptions to all items
"""

import re

with open("src/equipment/item_system.py", "r", encoding="utf-8") as f:
    content = f.read()

print("Adding empty descriptions...")

# Pattern: find entries that have "name": but NO "description":
# Match pattern: "name": "..." followed by "rarity": WITHOUT "description" in between
pattern = r'("name":\s*"[^"]+",)\s*\n(\s+"rarity":)'
replacement = r'\1\n        "description": "",\n\2'

content = re.sub(pattern, replacement, content)

with open("src/equipment/item_system.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Added empty descriptions to all items!")
