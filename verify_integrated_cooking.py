import sys
import os
import yaml

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

# Mocking dependencies
from unittest.mock import MagicMock
sys.modules['src.core.logger'] = MagicMock()
mock_logger = MagicMock()
mock_logger.info = print
mock_logger.error = print
mock_logger.warning = print
sys.modules['src.core.logger'].get_logger = lambda x: mock_logger

# Mock Ingredient class
class MockIngredient:
    def __init__(self, item_id, category, food_value=1.0):
        self.item_id = item_id
        self.category = category
        self.food_value = food_value
        self.name = item_id

# Import after mocking
from src.cooking.recipe import RecipeDatabase, IngredientCategory

def verify_integrated_cooking():
    print("=== Verifying Integrated Cooking System ===")
    
    # Initialize database
    RecipeDatabase.initialize()
    print(f"Total Recipes Loaded: {len(RecipeDatabase.RECIPES)}")
    
    # 1. Test YAML Recipe (Exact Match)
    print("\n[Test 1] YAML Recipe: Herb Soup (herb x2)")
    ingredients = [
        MockIngredient("herb", IngredientCategory.VEGETABLE),
        MockIngredient("herb", IngredientCategory.VEGETABLE)
    ]
    recipe = RecipeDatabase.find_recipe(ingredients)
    print(f"Result: {recipe.result.name}")
    if recipe.result.name == "약초 수프":
        print("PASS")
    else:
        print(f"FAIL (Expected '약초 수프')")

    # 2. Test Category Recipe (Mushroom Stew)
    print("\n[Test 2] Category Recipe: Mushroom Stew (Mushroom x3)")
    ingredients = [
        MockIngredient("red_mushroom", IngredientCategory.MUSHROOM),
        MockIngredient("blue_mushroom", IngredientCategory.MUSHROOM),
        MockIngredient("red_mushroom", IngredientCategory.MUSHROOM)
    ]
    recipe = RecipeDatabase.find_recipe(ingredients)
    print(f"Result: {recipe.result.name}")
    if recipe.result.name == "버섯 스튜":
        print("PASS")
    else:
        print(f"FAIL (Expected '버섯 스튜')")

    # 3. Test Nested Cooking (Pizza Chain)
    print("\n[Test 3] Nested Cooking Chain: Pizza")
    # Step 1: Dough (Flour + Water)
    print("  Step 1: Making Dough...")
    ingredients_dough = [
        MockIngredient("flour", IngredientCategory.GRAIN),
        MockIngredient("water", IngredientCategory.FILLER)
    ]
    recipe_dough = RecipeDatabase.find_recipe(ingredients_dough)
    print(f"  -> Result: {recipe_dough.result.name}")
    
    # Step 2: Tomato Sauce (Tomato x2 + Herb + Salt)
    print("  Step 2: Making Tomato Sauce...")
    ingredients_sauce = [
        MockIngredient("tomato", IngredientCategory.VEGETABLE),
        MockIngredient("tomato", IngredientCategory.VEGETABLE),
        MockIngredient("herb", IngredientCategory.VEGETABLE),
        MockIngredient("salt", IngredientCategory.SPICE)
    ]
    recipe_sauce = RecipeDatabase.find_recipe(ingredients_sauce)
    print(f"  -> Result: {recipe_sauce.result.name}")
    
    # Step 3: Pizza (Dough + Tomato Sauce + Cheese + Meat)
    print("  Step 3: Making Pizza...")
    # Mock cooked items
    dough = MockIngredient("dough", IngredientCategory.GRAIN) # Dough is grain category
    sauce = MockIngredient("tomato_sauce", IngredientCategory.VEGETABLE) # Sauce is veg category
    cheese = MockIngredient("cheese", IngredientCategory.DAIRY)
    meat = MockIngredient("meat", IngredientCategory.MEAT)
    
    ingredients_pizza = [dough, sauce, cheese, meat]
    recipe_pizza = RecipeDatabase.find_recipe(ingredients_pizza)
    print(f"  -> Result: {recipe_pizza.result.name}")
    
    if recipe_pizza.result.name == "콤비네이션 피자":
        print("PASS")
    else:
        print(f"FAIL (Expected '콤비네이션 피자')")

    # 4. Test Rebalance Stats (Beef Wellington)
    print("\n[Test 4] Rebalance Stats: Beef Wellington")
    # steak + dough + mushroom_stew + butter
    ingredients = [
        MockIngredient("steak", IngredientCategory.PREPARED_DISH),
        MockIngredient("dough", IngredientCategory.GRAIN),
        MockIngredient("mushroom_stew", IngredientCategory.PREPARED_DISH),
        MockIngredient("butter", IngredientCategory.DAIRY)
    ]
    recipe = RecipeDatabase.find_recipe(ingredients)
    print(f"Result: {recipe.result.name} (HP: {recipe.result.hp_restore})")
    if recipe.result.hp_restore == 1000:
        print("PASS (HP == 1000)")
    else:
        print(f"FAIL (HP != 1000)")
        
    # 5. Test Fallback
    print("\n[Test 5] Fallback: Wet Goop")
    ingredients = [
        MockIngredient("rock", IngredientCategory.FILLER),
        MockIngredient("stick", IngredientCategory.FILLER)
    ]
    recipe = RecipeDatabase.find_recipe(ingredients)
    print(f"Result: {recipe.result.name}")
    if recipe.result.name == "축축한 음식":
        print("PASS")
    else:
        print(f"FAIL")

    # 6. Test New Effects (Golden Apple Pie - Critical)
    print("\n[Test 6] New Effects: Golden Apple Pie (Critical)")
    # golden_apple + dough + honey + butter
    ingredients = [
        MockIngredient("golden_apple", IngredientCategory.FRUIT),
        MockIngredient("dough", IngredientCategory.GRAIN),
        MockIngredient("honey", IngredientCategory.SWEETENER),
        MockIngredient("butter", IngredientCategory.DAIRY)
    ]
    recipe = RecipeDatabase.find_recipe(ingredients)
    print(f"Result: {recipe.result.name} (Crit: {recipe.result.critical_rate})")
    if recipe.result.critical_rate == 0.2:
        print("PASS (Crit == 0.2)")
    else:
        print(f"FAIL (Crit != 0.2)")

    # 7. Test New Effects (Fireproof Chili - Resist)
    print("\n[Test 7] New Effects: Fireproof Chili (Resist)")
    # meat x2 + spice x2 + tomato_sauce
    ingredients = [
        MockIngredient("meat", IngredientCategory.MEAT),
        MockIngredient("meat", IngredientCategory.MEAT),
        MockIngredient("spice", IngredientCategory.SPICE),
        MockIngredient("spice", IngredientCategory.SPICE),
        MockIngredient("tomato_sauce", IngredientCategory.VEGETABLE)
    ]
    recipe = RecipeDatabase.find_recipe(ingredients)
    print(f"Result: {recipe.result.name} (Fire Resist: {recipe.result.elemental_resist.get('fire')})")
    if recipe.result.elemental_resist.get('fire') == 0.5:
        print("PASS (Fire Resist == 0.5)")
    else:
        print(f"FAIL (Fire Resist != 0.5)")

if __name__ == "__main__":
    verify_integrated_cooking()
