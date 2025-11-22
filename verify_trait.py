
import sys
import os

sys.path.insert(0, os.getcwd())

from src.character.trait_effects import get_trait_effect_manager

manager = get_trait_effect_manager()
print(f"Has calculate_damage_reduction: {hasattr(manager, 'calculate_damage_reduction')}")
try:
    manager.calculate_damage_reduction("test")
    print("Call successful")
except Exception as e:
    print(f"Call failed: {e}")
