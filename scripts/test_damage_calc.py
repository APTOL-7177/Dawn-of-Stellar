"""데미지 계산 테스트"""
import sys
sys.path.insert(0, 'X:/develop/Dos')

from src.core.config import initialize_config
from src.combat.damage_calculator import DamageCalculator
from src.character.character import Character

# Config 초기화
initialize_config()

# 데미지 계산기
calc = DamageCalculator()

# 바드 생성 (물리 43, 마법 66)
bard = Character("테스트바드", "바드")
print(f"바드 스탯: strength={bard.strength}, magic={bard.magic}, defense={bard.defense}, spirit={bard.spirit}")

# 적 생성 (임의의 고블린)
goblin = Character("고블린", "전사")  # 기본 스탯 사용
print(f"고블린 스탯: defense={goblin.defense}, spirit={goblin.spirit}")

# 물리 BRV 데미지 계산 (바드 배율 1.3)
print("\n=== 물리 공격으로 계산 ===")
result_physical = calc.calculate_brv_damage(bard, goblin, skill_multiplier=1.3)
print(f"기본 데미지: {result_physical.base_damage}")
print(f"최종 데미지: {result_physical.final_damage}")
print(f"크리티컬: {result_physical.is_critical}")
print(f"상세: {result_physical.details}")

# 마법 BRV 데미지 계산 (바드 배율 1.3)
print("\n=== 마법 공격으로 계산 ===")
result_magic = calc.calculate_magic_damage(bard, goblin, skill_multiplier=1.3)
print(f"기본 데미지: {result_magic.base_damage}")
print(f"최종 데미지: {result_magic.final_damage}")
print(f"크리티컬: {result_magic.is_critical}")
print(f"상세: {result_magic.details}")

# 전사와 비교
print("\n=== 전사 비교 (물리 60) ===")
warrior = Character("테스트전사", "전사")
print(f"전사 스탯: strength={warrior.strength}, magic={warrior.magic}")
result_warrior = calc.calculate_brv_damage(warrior, goblin, skill_multiplier=1.6)  # 전사 배율
print(f"기본 데미지: {result_warrior.base_damage}")
print(f"최종 데미지: {result_warrior.final_damage}")

# 메이지와 비교
print("\n=== 메이지 비교 (마법 78) ===")
mage = Character("테스트메이지", "메이지")
print(f"메이지 스탯: strength={mage.strength}, magic={mage.magic}")
result_mage = calc.calculate_magic_damage(mage, goblin, skill_multiplier=1.5)  # 메이지 배율
print(f"기본 데미지: {result_mage.base_damage}")
print(f"최종 데미지: {result_mage.final_damage}")
