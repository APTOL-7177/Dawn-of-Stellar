import sys
import os
import yaml

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Mocking dependencies that might not be easily importable in isolation
from unittest.mock import MagicMock
sys.modules['src.core.event_bus'] = MagicMock()
sys.modules['src.core.config'] = MagicMock()
sys.modules['src.core.logger'] = MagicMock()
sys.modules['src.character.stats'] = MagicMock()

# Mock logger to print to stdout
mock_logger = MagicMock()
mock_logger.info = print
mock_logger.error = print
mock_logger.warning = print
sys.modules['src.core.logger'].get_logger = lambda x: mock_logger

# Mock config
mock_config = MagicMock()
mock_config.get.return_value = True
sys.modules['src.core.config'].get_config = lambda: mock_config

# Now import the cooking system
from src.field.cooking import cooking_system, Recipe

def verify_cooking_system():
    print("=== Verifying Cooking System ===")
    
    # Check if recipes are loaded
    recipes = cooking_system.get_all_recipes()
    print(f"Loaded {len(recipes)} recipes.")
    
    if len(recipes) == 0:
        print("FAIL: No recipes loaded.")
        return
    
    # Check specific recipes
    check_recipes = ["herb_soup", "ambrosia", "kimchi_stew"]
    for r_id in check_recipes:
        recipe = cooking_system.get_recipe(r_id)
        if recipe:
            print(f"PASS: Found recipe {r_id} - {recipe.name}")
            print(f"  - Ingredients: {recipe.ingredients}")
            print(f"  - Effects: {recipe.effects}")
            print(f"  - Difficulty: {recipe.difficulty}")
        else:
            print(f"FAIL: Recipe {r_id} not found.")

    # Test cooking simulation
    print("\n=== Simulating Cooking ===")
    character = MagicMock()
    character.name = "TestChar"
    character.current_mp = 100
    character.dexterity = 10 # Good stats
    
    inventory = {"herb": 10}
    
    # Test cooking herb soup
    result = cooking_system.cook(character, "herb_soup", inventory)
    if result["success"]:
        print(f"PASS: Cooked herb_soup successfully. Quality: {result['quality']}")
        print(f"  - Item: {result['item']}")
    else:
        print("FAIL: Failed to cook herb_soup.")

if __name__ == "__main__":
    verify_cooking_system()
