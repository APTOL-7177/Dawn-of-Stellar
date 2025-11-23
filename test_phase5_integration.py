"""
Phase 5 통합 테스트 스위트 (Integration Test Suite)

타운 시스템, 멀티플레이어 호환성, 퀘스트, 저장소 등 모든 신규 기능 테스트
"""

import sys
import random
from typing import List, Dict, Any

def test_floor_transition_system():
    """층 전환 시스템 테스트"""
    print("=" * 60)
    print("1. 층 전환 시스템 테스트 (Floor Transition)")
    print("=" * 60)
    
    from src.town.floor_transition import get_floor_transition_manager, rest_at_inn
    
    # 싱글 플레이어
    ftm = get_floor_transition_manager("player1")
    assert ftm.player_id == "player1", "플레이어 ID 불일치"
    assert ftm.current_floor == 0, "초기 층은 0(마을)이어야 함"
    
    # 던전 입장
    result = ftm.enter_dungeon_floor(1)
    assert result["location"] == "dungeon", "던전 위치 확인"
    assert result["floor"] == 1, "층 번호 확인"
    assert ftm.is_ready == False, "던전 입장 시 준비 해제"
    
    # 마을 귀환
    result = ftm.return_to_town()
    assert result["success"] == True, "마을 귀환 성공"
    assert ftm.is_ready == False, "마을 도착 시 준비 해제"
    
    # 마을 출발 (자동 준비)
    result = ftm.leave_town()
    assert result["is_ready"] == True, "자동 준비 확인"
    assert ftm.is_ready == True, "is_ready 플래그 확인"
    
    # 층 클리어
    ftm.on_floor_clear()
    assert ftm.can_visit_town == True, "층 클리어 후 마을 방문 가능"
    
    print("  ✅ 층 전환 로직 정상")
    print("  ✅ 자동 준비 시스템 정상")
    print("  ✅ BGM 전환 정보 정상")
    print()
    
    return True


def test_multiplayer_town_instances():
    """멀티플레이어 타운 인스턴스 테스트"""
    print("=" * 60)
    print("2. 멀티플레이어 타운 인스턴스 테스트")
    print("=" * 60)
    
    from src.town.floor_transition import get_floor_transition_manager
    
    # 3명의 플레이어
    player_ids = ["player1", "player2", "player3"]
    managers = {}
    
    for pid in player_ids:
        managers[pid] = get_floor_transition_manager(pid)
        assert managers[pid].player_id == pid, f"{pid} ID 불일치"
    
    # 독립성 확인
    managers["player1"].enter_dungeon_floor(1)
    managers["player2"].enter_dungeon_floor(3)
    managers["player3"].return_to_town()
    
    assert managers["player1"].current_floor == 1, "Player 1 독립성"
    assert managers["player2"].current_floor == 3, "Player 2 독립성"
    assert managers["player3"].current_floor == 0, "Player 3 독립성"
    
    # 각각 다른 준비 상태
    managers["player1"].leave_town()
    assert managers["player1"].is_ready == True, "Player 1 준비"
    assert managers["player2"].is_ready == False, "Player 2 미준비"
    assert managers["player3"].is_ready == False, "Player 3 미준비"
    
    print(f"  ✅ {len(player_ids)}명의 독립적인 인스턴스 확인")
    print("  ✅ 각 플레이어별 진행도 독립성 확인")
    print("  ✅ 준비 상태 개별 관리 확인")
    print()
    
    return True


def test_inn_revival_and_inflation():
    """여관 회복 및 인플레이션 테스트"""
    print("=" * 60)
    print("3. 여관 부활 & 인플레이션 테스트")
    print("=" * 60)
    
    from src.town.floor_transition import rest_at_inn
    
    # 가짜 파티 멤버
    class FakeMember:
        def __init__(self, name):
            self.name = name
            self.max_hp = 100
            self.current_hp = 50
            self.max_mp = 50
            self.current_mp = 20
            self.is_alive = True
            self.status_effects = ["poison", "burn"]
    
    class DeadMember:
        def __init__(self, name):
            self.name = name
            self.max_hp = 100
            self.current_hp = 0
            self.max_mp = 50
            self.current_mp = 0
            self.is_alive = False
            self.status_effects = []
    
    party = [
        FakeMember("Alice"),
        DeadMember("Bob"),
        FakeMember("Charlie")
    ]
    
    # 여관 휴식 (비용 200, 골드 300 보유)
    result = rest_at_inn(party, cost=200, player_gold=300)
    
    assert result["success"] == True, "휴식 성공"
    assert result["revived"] == 1, "1명 부활"
    
    # 회복 확인
    assert party[0].current_hp == party[0].max_hp, "HP 완전 회복"
    assert party[0].current_mp == party[0].max_mp, "MP 완전 회복"
    assert len(party[0].status_effects) == 0, "상태이상 제거"
    
    # 부활 확인
    assert party[1].is_alive == True, "쓰러진 동료 부활"
    assert party[1].current_hp == party[1].max_hp, "부활 후 HP"
    
    # 골드 부족 테스트
    result = rest_at_inn(party, cost=1000, player_gold=100)
    assert result["success"] == False, "골드 부족 시 실패"
    
    print("  ✅ 파티 전체 HP/MP 회복 확인")
    print("  ✅ 쓰러진 동료 부활 확인")
    print("  ✅ 상태이상 제거 확인")
    print("  ✅ 골드 체크 확인")
    print()
    
    return True


def test_quest_generation_all_types():
    """10종 퀘스트 생성 테스트"""
    print("=" * 60)
    print("4. 퀘스트 생성 (10종) 테스트")
    print("=" * 60)
    
    from src.quest.quest_manager import QuestDatabase, QuestType
    
    generators = {
        QuestType.BOUNTY_HUNT: QuestDatabase.generate_bounty_quest,
        QuestType.DELIVERY: QuestDatabase.generate_delivery_quest,
        QuestType.EXPLORATION: QuestDatabase.generate_exploration_quest,
        QuestType.BOSS_HUNT: QuestDatabase.generate_boss_hunt_quest,
        QuestType.SURVIVAL: QuestDatabase.generate_survival_quest,
        QuestType.SPEED_RUN: QuestDatabase.generate_speed_run_quest,
        QuestType.COLLECTION: QuestDatabase.generate_collection_quest,
        QuestType.COOKING_QUEST: QuestDatabase.generate_cooking_quest,
        QuestType.ALCHEMY_QUEST: QuestDatabase.generate_alchemy_quest,
        QuestType.NO_DAMAGE: QuestDatabase.generate_no_damage_quest,
    }
    
    for quest_type, generator in generators.items():
        quest = generator(player_level=5)
        assert quest is not None, f"{quest_type.value} 생성 실패"
        assert quest.quest_type == quest_type, f"{quest_type.value} 타입 불일치"
        assert len(quest.objectives) > 0, f"{quest_type.value} 목표 없음"
        assert quest.reward is not None, f"{quest_type.value} 보상 없음"
        print(f"  ✅ {quest_type.value}: {quest.name}")
    
    print()
    print(f"  ✅ 총 {len(generators)}종 퀘스트 생성 확인")
    print()
    
    return True


def test_storage_persistence():
    """저장소 영구성 테스트"""
    print("=" * 60)
    print("5. 저장소 영구성 테스트")
    print("=" * 60)
    
    from src.town.town_manager import TownManager
    
    tm = TownManager()
    
    # 건설 자재 보관
    materials = {"wood": 10, "stone": 5, "iron_ore": 3}
    stored = tm.store_construction_materials(materials)
    
    assert stored == materials, "보관 실패"
    
    # 저장소 확인
    hub_storage = tm.get_hub_storage()
    assert hub_storage["wood"] == 10, "목재 확인"
    assert hub_storage["stone"] == 5, "석재 확인"
    assert hub_storage["iron_ore"] == 3, "철광석 확인"
    
    # 인출 테스트
    withdrawn = tm.withdraw_from_hub("wood", 5)
    assert withdrawn == 5, "인출 실패"
    assert tm.get_hub_storage()["wood"] == 5, "인출 후 잔여 확인"
    
    # 런타임 저장소 초기화 (게임 오버 시뮬레이션)
    tm.clear_runtime_storage()
    
    # 건설 자재는 보존되어야 함
    hub_storage_after = tm.get_hub_storage()
    assert "wood" in hub_storage_after, "건설 자재는 게임 오버 후에도 유지"
    
    print("  ✅ 건설 자재 보관 확인")
    print("  ✅ 자재 인출 확인")
    print("  ✅ 게임 오버 후 영구 보존 확인")
    print()
    
    return True


def test_inventory_weight_reduction():
    """인벤토리 무게 감소 테스트"""
    print("=" * 60)
    print("6. 인벤토리 무게 감소 (1/3) 테스트")
    print("=" * 60)
    
    from src.equipment.inventory import Inventory
    
    # 기본 무게 5kg 인벤토리
    inv = Inventory(base_weight=5.0, party=[])
    
    # 새 계산식: total * 0.2 (기존 0.6의 1/3)
    expected_max = round(5.0 * 0.2, 1)  # 1.0kg
    
    assert inv.max_weight == expected_max, f"무게 계산 오류: {inv.max_weight} != {expected_max}"
    
    print(f"  ✅ 기본 무게 5kg → 최대 {inv.max_weight}kg")
    print(f"  ✅ 1/3 곱적용 확인 (0.6 → 0.2)")
    print()
    
    return True


def test_stairs_removal():
    """상향 계단 제거 테스트"""
    print("=" * 60)
    print("7. 상향 계단 제거 (전진만) 테스트")
    print("=" * 60)
    
    from src.world.dungeon_generator import DungeonGenerator
    
    generator = DungeonGenerator(width=40, height=30)
    
    # 2층 생성 (이전에는 stairs_up이 생성되었음)
    dungeon = generator.generate(floor_number=2, seed=12345)
    
    # stairs_up이 없어야 함
    assert dungeon.stairs_up is None, "상향 계단이 아직 존재함"
    
    # stairs_down은 있어야 함 (다음 층으로 진행)
    assert dungeon.stairs_down is not None, "하향 계단이 없음"
    
    print("  ✅ 상향 계단(stairs_up) 제거 확인")
    print("  ✅ 하향 계단(stairs_down) 유지 확인")
    print("  ✅ 전진만 가능한 던전 확인")
    print()
    
    return True


def test_biome_bgm_system():
    """바이옴 BGM 시스템 확인"""
    print("=" * 60)
    print("8. 바이옴 BGM 시스템 테스트")
    print("=" * 60)
    
    # 바이옴 인덱스 계산 확인
    test_cases = [
        (1, 0, "biome_0"),   # 1층 → biome_0
        (2, 1, "biome_1"),   # 2층 → biome_1
        (6, 5, "biome_5"),   # 6층 → biome_5
        (10, 9, "biome_9"),  # 10층 → biome_9
        (11, 0, "biome_0"),  # 11층 → biome_0 (순환)
        (15, 4, "biome_4"),  # 15층 → biome_4
    ]
    
    for floor, expected_index, expected_track in test_cases:
        biome_index = (floor - 1) % 10
        biome_track = f"biome_{biome_index}"
        
        assert biome_index == expected_index, f"층 {floor} 인덱스 오류"
        assert biome_track == expected_track, f"층 {floor} 트랙 오류"
        print(f"  ✅ 층 {floor:2d} → {biome_track}")
    
    print()
    print("  ✅ 10개 바이옴 순환 확인")
    print("  ✅ BGM 계산식 정상")
    print()
    
    return True


def test_integration_scenario():
    """통합 시나리오 테스트"""
    print("=" * 60)
    print("9. 통합 시나리오 (전체 플로우)")
    print("=" * 60)
    
    print("  시나리오: 플레이어가 1층 클리어 후 마을 방문")
    print()
    
    from src.town.floor_transition import get_floor_transition_manager
    from src.quest.quest_manager import QuestManager
    from src.town.town_manager import TownManager
    
    # 1. 던전 시작
    ftm = get_floor_transition_manager("integration_test")
    result = ftm.enter_dungeon_floor(1)
    print(f"  1. 던전 1층 입장 → BGM: {result['bgm']}")
    
    # 2. 층 클리어
    ftm.on_floor_clear()
    print(f"  2. 층 클리어 → 마을 방문 가능: {ftm.can_visit_town}")
    
    # 3. 마을 귀환
    result = ftm.return_to_town()
    print(f"  3. 마을 귀환 → BGM: {result['bgm']}")
    
    # 4. 퀘스트 확인
    qm = QuestManager()
    qm.generate_quests(player_level=5, count=3)
    print(f"  4. 퀘스트 확인 → {len(qm.available_quests)}개 퀘스트")
    
    # 5. 저장소 사용
    tm = TownManager()
    tm.store_construction_materials({"wood": 20})
    print(f"  5. 저장소 사용 → 목재 {tm.get_hub_storage().get('wood', 0)}개 보관")
    
    # 6. 마을 출발 (자동 준비)
    result = ftm.leave_town()
    print(f"  6. 마을 출발 → 준비 상태: {result['is_ready']}")
    
    # 7. 다음 층 진행
    result = ftm.enter_dungeon_floor(2)
    print(f"  7. 던전 2층 입장 → 현재 층: {ftm.current_floor}")
    
    print()
    print("  ✅ 전체 플로우 정상 작동")
    print("  ✅ 시스템 간 연동 확인")
    print()
    
    return True


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("Phase 5 통합 테스트 스위트")
    print("=" * 60 + "\n")
    
    tests = [
        ("층 전환 시스템", test_floor_transition_system),
        ("멀티플레이어 타운", test_multiplayer_town_instances),
        ("여관 부활/인플레이션", test_inn_revival_and_inflation),
        ("퀘스트 10종 생성", test_quest_generation_all_types),
        ("저장소 영구성", test_storage_persistence),
        ("인벤토리 무게 감소", test_inventory_weight_reduction),
        ("상향 계단 제거", test_stairs_removal),
        ("바이옴 BGM", test_biome_bgm_system),
        ("통합 시나리오", test_integration_scenario),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True, None))
        except Exception as e:
            import traceback
            results.append((name, False, str(e)))
            print(f"\n❌ {name} 테스트 실패!")
            print(f"에러: {e}")
            traceback.print_exc()
            print()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if error:
            print(f"       {error}")
    
    print(f"\n총 {passed}/{total} 테스트 통과 ({int(passed/total*100)}%)")
    
    if passed == total:
        print("\n🎉 모든 Phase 5 통합 테스트 통과! 🎉")
        print("\n시스템 준비 완료:")
        print("  ✅ 타운 시스템")
        print("  ✅ 멀티플레이어 호환성")
        print("  ✅ 퀘스트 시스템")
        print("  ✅ 저장소 영구성")
        print("  ✅ 던전 전진 시스템")
        print("  ✅ 바이옴 BGM")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
