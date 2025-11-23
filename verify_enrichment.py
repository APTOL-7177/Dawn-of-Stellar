"""
게임 엔리치먼트 시스템 검증 스크립트

새로 추가된 모든 시스템을 테스트합니다.
"""

import sys
import traceback

def test_imports():
    """Import 테스트"""
    print("=" * 60)
    print("1. Import 테스트")
    print("=" * 60)
    
    try:
        from src.town.town_manager import TownManager, FacilityType
        print("✓ TownManager")
        
        from src.cooking.potion_brewing import PotionDatabase, PotionBrewer
        print("✓ PotionDatabase")
        
        from src.cooking.bomb_crafting import BombDatabase, BombCrafter
        print("✓ BombDatabase")
        
        from src.world.interactive_object import InteractiveObjectGenerator, InteractiveObject
        print("✓ InteractiveObject")
        
        from src.world.environmental_effects import EnvironmentalEffectGenerator, EnvironmentalEffectType
        print("✓ EnvironmentalEffect")
        
        from src.quest.quest_manager import QuestManager, QuestType
        print("✓ QuestManager")
        
        from src.town.town_map import TownMap, BuildingType
        print("✓ TownMap")
        
        from src.gathering.ingredient import IngredientDatabase, IngredientCategory
        print("✓ IngredientDatabase")
        
        print("\n✅ 모든 Import 성공!\n")
        return True
    except Exception as e:
        print(f"\n❌ Import 실패: {e}")
        traceback.print_exc()
        return False


def test_materials():
    """재료 테스트"""
    print("=" * 60)
    print("2. 재료 시스템 테스트")
    print("=" * 60)
    
    from src.gathering.ingredient import IngredientDatabase, IngredientCategory
    
    # 건설 자재
    construction_materials = ["wood", "stone", "iron_ore", "copper_ore", "silver_ore", "gold_ore", "mithril_ore"]
    print(f"건설 자재: {len(construction_materials)}종")
    for mat_id in construction_materials:
        mat = IngredientDatabase.get_ingredient(mat_id)
        if mat:
            print(f"  ✓ {mat.name} ({mat.rarity.value})")
        else:
            print(f"  ❌ {mat_id} not found")
    
    # 연금술 재료
    alchemy_materials = ["glass_vial", "alchemical_catalyst", "pure_water", "fire_essence", 
                         "ice_essence", "lightning_essence", "mana_blossom", "moonflower", 
                         "ether", "crystal_shard"]
    print(f"\n연금술 재료: {len(alchemy_materials)}종")
    for mat_id in alchemy_materials:
        mat = IngredientDatabase.get_ingredient(mat_id)
        if mat:
            print(f"  ✓ {mat.name}")
    
    # 폭발물 재료
    explosive_materials = ["gunpowder", "metal_scrap", "explosive_crystal", "fuse", "bomb_casing", "sulfur", "charcoal"]
    print(f"\n폭발물 재료: {len(explosive_materials)}종")
    for mat_id in explosive_materials:
        mat = IngredientDatabase.get_ingredient(mat_id)
        if mat:
            print(f"  ✓ {mat.name}")
    
    print(f"\n✅ 재료 시스템 테스트 완료!\n")


def test_potions():
    """포션 테스트"""
    print("=" * 60)
    print("3. 포션 시스템 테스트")
    print("=" * 60)
    
    from src.cooking.potion_brewing import PotionDatabase
    
    recipes = PotionDatabase.get_all_recipes()
    print(f"총 {len(recipes)}종의 포션 레시피")
    
    for recipe in recipes[:5]:  # 처음 5개만
        print(f"  {recipe.name} (난이도: {recipe.difficulty})")
        print(f"    - 재료: {', '.join(recipe.ingredients.keys())}")
        print(f"    - 효과: {recipe.effects}")
    
    print(f"\n✅ {len(recipes)}종 포션 레시피 확인 완료!\n")


def test_bombs():
    """폭탄 테스트"""
    print("=" * 60)
    print("4. 폭탄 시스템 테스트")
    print("=" * 60)
    
    from src.cooking.bomb_crafting import BombDatabase
    
    recipes = BombDatabase.get_all_recipes()
    print(f"총 {len(recipes)}종의 폭탄 레시피")
    
    for recipe in recipes[:5]:  # 처음 5개만
        print(f"  {recipe.name} (난이도: {recipe.difficulty})")
        print(f"    - 데미지: {recipe.damage}, 범위: {recipe.aoe_range}")
        print(f"    - 재료: {', '.join(recipe.ingredients.keys())}")
    
    print(f"\n✅ {len(recipes)}종 폭탄 레시피 확인 완료!\n")


def test_quests():
    """퀘스트 테스트"""
    print("=" * 60)
    print("5. 퀘스트 시스템 테스트")
    print("=" * 60)
    
    from src.quest.quest_manager import QuestManager, QuestType
    
    quest_types = list(QuestType)
    print(f"퀘스트 타입: {len(quest_types)}종")
    for qt in quest_types:
        print(f"  ✓ {qt.value}")
    
    # 퀘스트 생성 테스트
    qm = QuestManager()
    qm.generate_quests(player_level=5, count=10)
    
    print(f"\n생성된 퀘스트: {len(qm.available_quests)}개")
    for quest in qm.available_quests[:3]:  # 처음 3개
        print(f"  {quest.name} ({quest.quest_type.value}) - {quest.difficulty.value}")
    
    print(f"\n✅ 퀘스트 시스템 테스트 완료!\n")


def test_environments():
    """환경 효과 테스트"""
    print("=" * 60)
    print("6. 환경 효과 테스트")
    print("=" * 60)
    
    from src.world.environmental_effects import EnvironmentalEffectType, EnvironmentalEffectGenerator
    
    effect_types = list(EnvironmentalEffectType)
    print(f"환경 효과: {len(effect_types)}종")
    for et in effect_types:
        print(f"  ✓ {et.value}")
    
    # 환경 생성 테스트
    effects = EnvironmentalEffectGenerator.generate_for_floor(5, 50, 30)
    print(f"\n생성된 환경 효과: {len(effects)}개")
    
    print(f"\n✅ 환경 효과 시스템 테스트 완료!\n")


def test_interactive_objects():
    """상호작용 오브젝트 테스트"""
    print("=" * 60)
    print("7. 상호작용 오브젝트 테스트")
    print("=" * 60)
    
    from src.world.interactive_object import InteractiveObjectType, InteractiveObjectGenerator
    
    object_types = list(InteractiveObjectType)
    print(f"오브젝트 타입: {len(object_types)}종")
    for ot in object_types:
        print(f"  ✓ {ot.value}")
    
    # 오브젝트 생성 테스트
    objects = InteractiveObjectGenerator.generate_for_floor(5, count=3)
    print(f"\n생성된 오브젝트: {len(objects)}개")
    
    print(f"\n✅ 상호작용 오브젝트 시스템 테스트 완료!\n")


def test_town_map():
    """타운 맵 테스트"""
    print("=" * 60)
    print("8. 타운 맵 테스트")
    print("=" * 60)
    
    from src.town.town_map import TownMap, BuildingType
    
    town = TownMap()
    
    print(f"타운 크기: {town.width}x{town.height}")
    print(f"건물 수: {len(town.buildings)}개")
    
    building_types = list(BuildingType)
    print(f"\n건물 타입: {len(building_types)}종")
    for bt in building_types:
        print(f"  ✓ {bt.value}")
    
    for building in town.buildings:
        print(f"  {building.name} at ({building.x}, {building.y})")
    
    print(f"\n✅ 타운 맵 시스템 테스트 완료!\n")


def test_town_manager():
    """타운 매니저 테스트"""
    print("=" * 60)
    print("9. 타운 매니저 테스트")
    print("=" * 60)
    
    from src.town.town_manager import TownManager, FacilityType
    
    tm = TownManager()
    
    print("시설 목록:")
    for facility_type, facility in tm.facilities.items():
        print(f"  {facility_type.value}: Lv.{facility.level}")
        print(f"    - {facility.get_effect_description()}")
    
    # 허브 저장소 테스트
    test_inventory = {"wood": 10, "stone": 5}
    stored = tm.store_construction_materials(test_inventory)
    print(f"\n허브 저장소 테스트:")
    print(f"  저장된 자재: {stored}")
    print(f"  허브 저장소: {tm.get_hub_storage()}")
    
    print(f"\n✅ 타운 매니저 테스트 완료!\n")


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 60)
    print("게임 엔리치먼트 시스템 검증")
    print("=" * 60 + "\n")
    
    tests = [
        ("Import", test_imports),
        ("재료", test_materials),
        ("포션", test_potions),
        ("폭탄", test_bombs),
        ("퀘스트", test_quests),
        ("환경", test_environments),
        ("오브젝트", test_interactive_objects),
        ("타운 맵", test_town_map),
        ("타운 매니저", test_town_manager)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
        except Exception as e:
            print(f"\n❌ {name} 테스트 실패!")
            print(f"에러: {e}")
            traceback.print_exc()
            results.append((name, False))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n총 {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 🎉")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
