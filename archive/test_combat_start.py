"""전투 시작 테스트"""
import sys
import traceback

try:
    from src.core.game_engine import GameEngine
    from src.combat.combat_manager import get_combat_manager
    from src.character.character_factory import CharacterFactory
    from src.world.enemy_generator import EnemyGenerator

    print("초기화 중...")

    # 캐릭터 생성
    factory = CharacterFactory()
    player = factory.create_character("warrior", "테스트전사", level=5)

    # 적 생성
    enemy_gen = EnemyGenerator()
    enemy = enemy_gen.generate_enemy("goblin", 5, "normal")

    print(f"플레이어: {player.name} (HP: {player.current_hp}/{player.max_hp})")
    print(f"적: {enemy.name} (HP: {enemy.current_hp}/{enemy.max_hp})")

    # 전투 시작
    print("\n전투 시작...")
    combat = get_combat_manager()
    combat.start_combat([player], [enemy])

    print("전투 시작 성공!")

except Exception as e:
    print(f"\n❌ 에러 발생: {e}")
    print("\n=== 전체 트레이스백 ===")
    traceback.print_exc()
    sys.exit(1)
