"""
Status Effects Integration Test

상태 효과 시스템의 통합 테스트
"""

from src.combat import (
    StatusEffect,
    StatusManager,
    StatusType,
    create_status_effect,
    get_status_category,
    get_status_icon
)


def test_basic_functionality():
    """기본 기능 테스트"""
    print("=== Status Effects Integration Test ===\n")

    # StatusManager 생성
    manager = StatusManager("TestCharacter")
    print(f"StatusManager 생성: {manager.owner_name}")

    # 독 효과 추가
    poison = create_status_effect(
        name="독",
        status_type=StatusType.POISON,
        duration=5,
        intensity=1.5
    )
    manager.add_status(poison)
    print(f"\n독 효과 추가: {manager.get_status_display()}")
    print(f"  - 카테고리: {get_status_category(StatusType.POISON)}")
    print(f"  - 아이콘: {get_status_icon(StatusType.POISON)}")

    # 재생 효과 추가 (스택 가능)
    regen = create_status_effect(
        name="재생",
        status_type=StatusType.REGENERATION,
        duration=5,
        intensity=1.0,
        is_stackable=True,
        max_stacks=3
    )
    manager.add_status(regen)
    print(f"\n재생 효과 추가: {manager.get_status_display()}")
    print(f"  - 카테고리: {get_status_category(StatusType.REGENERATION)}")

    # 기절 효과 추가
    stun = create_status_effect(
        name="기절",
        status_type=StatusType.STUN,
        duration=2
    )
    manager.add_status(stun)
    print(f"\n기절 효과 추가: {manager.get_status_display()}")
    print(f"  - 행동 가능: {manager.can_act()}")
    print(f"  - 스킬 사용 가능: {manager.can_use_skills()}")

    # 스탯 수정치 확인
    modifiers = manager.get_stat_modifiers()
    print(f"\n현재 스탯 수정치:")
    for stat, value in modifiers.items():
        if value != 1.0:
            print(f"  - {stat}: {value:.2f}x")

    # 활성 효과 목록
    print(f"\n활성 효과: {', '.join(manager.get_active_effects())}")

    # 지속시간 갱신
    print("\n=== 1턴 경과 ===")
    expired = manager.update_duration()
    if expired:
        print(f"만료된 효과: {', '.join([e.name for e in expired])}")
    print(f"남은 효과: {manager.get_status_display()}")

    print("\n=== 1턴 더 경과 ===")
    expired = manager.update_duration()
    if expired:
        print(f"만료된 효과: {', '.join([e.name for e in expired])}")
    print(f"남은 효과: {manager.get_status_display()}")
    print(f"행동 가능: {manager.can_act()}")

    # 모든 효과 제거
    print("\n=== 모든 효과 제거 ===")
    manager.clear_all_effects()
    print(f"효과: {manager.get_status_display()}")

    print("\n=== 테스트 완료 ===")


def test_complex_scenario():
    """복잡한 시나리오 테스트"""
    print("\n\n=== Complex Scenario Test ===\n")

    manager = StatusManager("Warrior")

    # 여러 버프/디버프 동시 적용
    effects = [
        ("공격력 강화", StatusType.BOOST_ATK, 5, 1.0),
        ("속도 감소", StatusType.REDUCE_SPD, 3, 1.0),
        ("독", StatusType.POISON, 4, 2.0),
        ("가속", StatusType.HASTE, 3, 1.0),
    ]

    for name, status_type, duration, intensity in effects:
        effect = create_status_effect(name, status_type, duration, intensity)
        manager.add_status(effect)

    print(f"복합 상태 효과: {manager.get_status_display()}")

    modifiers = manager.get_stat_modifiers()
    print(f"\n스탯 수정치:")
    print(f"  - 공격력: {modifiers['physical_attack']:.2f}x")
    print(f"  - 속도: {modifiers['speed']:.2f}x")

    print(f"\n행동 가능: {manager.can_act()}")
    print(f"제어 가능: {not manager.is_controlled()}")

    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    test_basic_functionality()
    test_complex_scenario()
    print("\n모든 통합 테스트가 성공적으로 완료되었습니다!")
