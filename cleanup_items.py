"""
Automated Item Cleanup Script

Fixes:
1. Descriptions with effects -> proper item descriptions
2. Removes duplicate items
3. Removes invalid effects (night_vision, inventory_space, etc.)
"""

import re

# Read file
with open("src/equipment/item_system.py", "r", encoding="utf-8") as f:
    content = f.read()

print("Starting cleanup...")

# 1. Remove invalid effects
invalid_effects_map = {
    "|night_vision": "",
    "night_vision|": "",
    "|lunar_power": "",
    "lunar_power|": "",
    "|inventory_space:[0-9]+": "",
    "inventory_space:[0-9]+|": "",
    "|carry_weight:[0-9]+": "",
    "carry_weight:[0-9]+|": "",
    "|map_reveal": "",
    "map_reveal|": "",
    "|terrain_ignore": "",
    "terrain_ignore|": "",
    "|flight": "",
    "flight|": "",
}

for pattern, replacement in invalid_effects_map.items():
    if "[0-9]" in pattern:
        content = re.sub(pattern, replacement, content)
    else:
        content = content.replace(pattern, replacement)

print("✅ Removed invalid effects")

# 2. Fix specific problematic descriptions (sample fixes)
desc_fixes = {
    '"description": "야간 능력 향상. 마법 회피 +20%"': '"description": "달빛이 깃든 부적"',
    '"description": "인벤토리 공간 +10. 모든 스탯 +5"': '"description": "다용도 실용 벨트"',
    '"description": "턴당 HP 5% 재생. 화염 약점"': '"description": "재생력이 깃든 목걸이"',
    '"description": "피격 시 데미지의 25% 반사"': '"description": "가시가 돋은 갑옷"',
    '"description": "블록 확률 30%. 블록 시 데미지 무효"': '"description": "튼튼한 방패 갑옷"',
    '"description": "회피율 +25%. 지형 무시"': '"description": "하늘을 나는 날개"',
    '"description": "탐색 효율 증가. 보물 발견률 +35%"': '"description": "방향을 가리키는 나침반"',
    '"description": "물약 효과 +30%. HP/MP 재생 +2%"': '"description": "연금술의 비밀이 담긴 돌"',
}

for old_desc, new_desc in desc_fixes.items():
    content = content.replace(old_desc, new_desc)

print("✅ Fixed problematic descriptions")

# 3. Remove duplicates - keep first occurrence, remove rest
duplicates_to_remove = [
    # war_hammer duplicate (철 메이스 section에 있는 것 제거)
    r',\s*"war_hammer":\s*\{[^}]+\"전쟁 망치\"[^}]+\}(?=\s*,\s*"titan_hammer")',
    # Excalibur duplicate in UNIQUE_ITEMS section
    r',\s*"excalibur":\s*\{[^}]+\"엑스칼리버\"[^}]+\}(?=\s*\}\s*# ItemGenerator)',
]

for pattern in duplicates_to_remove:
    content = re.sub(pattern, '', content, count=1)

print("✅ Removed some duplicates (manual review needed for all)")

# Write back
with open("src/equipment/item_system.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ Cleanup complete!")
print("⚠️  Please manually review and remove remaining duplicates:")
print("   - 할버드, 사슬 갑옷, 대마법사 로브, 비늘 갑옷")
print("   - 그림자 망토, 광전사의 가죽, 수호의 반지")
print("   - 가죽 벨트, 흡혈 반지, 불사조의 깃털")
