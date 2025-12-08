"""
요리 레시피 밸런스 조정 스크립트 v3
- 고기 기반 요리는 재료가 흔하므로 회복량 하향
- 희귀 재료(드래곤 고기, 마법 허브 등) 요리만 높은 회복량 유지
"""

import re

# 파일 읽기
with open(r'src\cooking\recipe.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 고기 기반 고급 요리 -> 일반 요리 수준으로 하향
# 희귀 재료 요리는 그대로 유지

# 고기 기반 요리 너프 (HIGH -> MEDIUM 수준으로)
meat_based_nerf = {
    # 일반 고기 요리들 - 고급이지만 재료 구하기 쉬움
    'samgyetang': (130, 70, {'max_hp_bonus': 35, 'buff_duration': 12}),  # 270->130
    'galbi_jjim': (120, 55, {'buff_duration': 10}),  # 250->120
    'steak': (100, 40, {'buff_duration': 10}),  # 210->100
    'steak_dinner': (140, 70, {'max_hp_bonus': 40, 'buff_duration': 15}),  # 260->140
    'beef_stew_royal': (135, 65, {'max_hp_bonus': 45, 'buff_duration': 14}),  # 260->135
    'boyang_tang': (125, 65, {'max_hp_bonus': 35, 'buff_duration': 14}),  # 240->125
    'barbecue': (95, 45, {'max_hp_bonus': 20, 'buff_duration': 10}),  # 200->95
    'roast_chicken': (90, 40, {'buff_duration': 10}),  # 200->90
    'braised_chicken': (100, 50, {'max_hp_bonus': 25, 'buff_duration': 12}),  # 190->100
    'bulgogi': (85, 40, {'buff_duration': 12}),  # 180->85
    'spicy_chicken': (80, 42, {'buff_duration': 14}),  # 170->80
    'steak_salad': (90, 50, {'buff_duration': 12}),  # 170->90
    'fireproof_chili': (95, 50, {'buff_duration': 18}),  # 180->95
    
    # 피자, 파스타 등 고기+다른 재료 - 약간만 하향
    'pizza': (120, 65, {'max_hp_bonus': 30, 'buff_duration': 15}),  # 240->120
    'carbonara': (110, 65, {'buff_duration': 14}),  # 220->110
    'club_sandwich': (85, 55, {'buff_duration': 12}),  # 160->85
    'assassins_stew': (80, 55, {'critical_rate': 0.12, 'buff_duration': 20}),  # 160->80, 치명타도 약간 하향
    
    # 생선 요리 - 생선도 어느정도 구하기 쉬움
    'grilled_fish': (70, 45, {}),  # 150->70
    'sushi': (90, 70, {'max_hp_bonus': 20, 'max_mp_bonus': 20, 'buff_duration': 12}),  # 180->90
    'sushi_premium': (110, 80, {'max_hp_bonus': 25, 'max_mp_bonus': 25, 'buff_duration': 16}),  # 230->110
    'fish_and_chips': (85, 65, {'max_hp_bonus': 20, 'max_mp_bonus': 15, 'buff_duration': 12}),  # 180->85
    'seafood_paella': (100, 80, {'buff_duration': 15}),  # 180->100
    'seafood_pasta': (95, 65, {'buff_duration': 14}),  # 170->95
    'truffle_risotto': (110, 80, {'buff_duration': 18}),  # 220->110 (송로버섯은 희귀하지만 적당히)
    
    # 치즈/크림 기반도 약간 하향
    'cheesecake': (65, 90, {'max_mp_bonus': 35, 'buff_duration': 16}),  # 120->65
}

# 희귀 재료 요리는 유지 (드래곤, 불사조, 황금사과 등)
# 마법 허브 기반도 약간 하향 (마법 허브도 그렇게 희귀하진 않음)
magic_herb_nerf = {
    'herb_stew': (70, 85, {'max_mp_bonus': 30, 'buff_duration': 10}),  # 130->70
    'mana_potion_food': (50, 100, {'max_mp_bonus': 45, 'buff_duration': 12}),  # 90->50
    'mana_potion_cooked': (50, 100, {'max_mp_bonus': 50, 'buff_duration': 12}),  # 90->50
    'wizard_pie': (45, 100, {'max_mp_bonus': 50, 'buff_duration': 14}),  # 80->45
    'magic_stew': (45, 100, {'max_mp_bonus': 45, 'buff_duration': 12}),  # 80->45
    'magic_pasta': (55, 90, {'max_mp_bonus': 45, 'buff_duration': 12}),  # 100->55
    'mana_cake': (55, 100, {'max_mp_bonus': 55, 'buff_duration': 16}),  # 100->55
    'star_fruit_tart': (55, 95, {'max_mp_bonus': 55, 'buff_duration': 18}),  # 100->55
    'mushroom_lasagna': (60, 90, {'max_mp_bonus': 45, 'buff_duration': 12}),  # 120->60
    'mushroom_stew': (60, 90, {'buff_duration': 10}),  # 120->60
    'time_warp_tea': (40, 95, {'cooldown_reduction': 0.18, 'buff_duration': 22}),  # 80->40
}

def update_recipe(content, recipe_id, hp, mp, extras):
    """레시피 값 업데이트"""
    pattern = rf'(recipe_id="{recipe_id}".*?hp_restore=)\d+'
    content = re.sub(pattern, rf'\g<1>{hp}', content, flags=re.DOTALL)
    pattern = rf'(recipe_id="{recipe_id}".*?mp_restore=)\d+'
    content = re.sub(pattern, rf'\g<1>{mp}', content, flags=re.DOTALL)
    return content

# 모든 레시피 업데이트
all_recipes = {**meat_based_nerf, **magic_herb_nerf}

for recipe_id, (hp, mp, extras) in all_recipes.items():
    content = update_recipe(content, recipe_id, hp, mp, extras)
    print(f"Nerfed: {recipe_id} -> HP:{hp}, MP:{mp}")

# 파일 저장
with open(r'src\cooking\recipe.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n총 {len(all_recipes)}개 고기/생선/마법허브 기반 레시피 너프 완료!")
print("- 일반 고기 요리: HP 80~140, MP 40~80 수준으로 하향")
print("- 마법 허브 요리: HP 40~70, MP 85~100 수준으로 하향")
print("- 희귀 재료(드래곤, 불사조 등)는 유지")
