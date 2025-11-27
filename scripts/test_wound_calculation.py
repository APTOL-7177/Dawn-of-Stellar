"""차원 굴절 지연 피해의 상처 계산 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.character.character import Character
from src.character.gimmick_updater import GimmickUpdater
from src.core.config import initialize_config
from src.systems.wound_system import get_wound_system

def test_refraction_wound():
    """차원 굴절 지연 피해의 상처 계산 테스트"""
    print("=" * 60)
    print("차원 굴절 지연 피해 상처 계산 테스트")
    print("=" * 60)

    # 설정 초기화
    initialize_config()
    wound_system = get_wound_system()

    # 차원술사 생성
    dimensionist = Character("차원술사", "dimensionist")
    dimensionist.current_hp = dimensionist.max_hp

    print(f"\n[초기 상태]")
    print(f"  HP: {dimensionist.current_hp}/{dimensionist.max_hp}")
    print(f"  상처: {getattr(dimensionist, 'wound', 0)}")
    print(f"  굴절량: {getattr(dimensionist, 'refraction_stacks', 0)}")

    # 300 피해 받기
    print(f"\n[1단계: 300 피해 받기]")
    damage = 300
    actual_damage = dimensionist.take_damage(damage)
    refraction = getattr(dimensionist, 'refraction_stacks', 0)

    print(f"  실제 피해: {actual_damage} (85% 경감)")
    print(f"  굴절량 축적: {refraction}")
    print(f"  현재 HP: {dimensionist.current_hp}/{dimensionist.max_hp}")
    print(f"  상처: {getattr(dimensionist, 'wound', 0)}")

    # 턴 종료 - 지연 피해 발동
    print(f"\n[2단계: 턴 종료 - 지연 피해 발동]")
    old_hp = dimensionist.current_hp
    old_wound = getattr(dimensionist, 'wound', 0)

    GimmickUpdater.on_turn_end(dimensionist)

    new_hp = dimensionist.current_hp
    new_wound = getattr(dimensionist, 'wound', 0)
    new_refraction = getattr(dimensionist, 'refraction_stacks', 0)

    hp_loss = old_hp - new_hp
    wound_increase = new_wound - old_wound

    print(f"  턴 종료 전 HP: {old_hp}")
    print(f"  턴 종료 후 HP: {new_hp}")
    print(f"  HP 손실: {hp_loss}")
    print(f"  상처 증가: {wound_increase} (기대값: {int(hp_loss * wound_system.wound_threshold)})")
    print(f"  총 상처: {new_wound}")
    print(f"  굴절량 감소: {refraction - new_refraction}")

    # 상처가 올바르게 계산되었는지 확인
    expected_wound_increase = int(hp_loss * wound_system.wound_threshold)
    if abs(wound_increase - expected_wound_increase) <= 1:
        print(f"\n[OK] 차원 굴절 지연 피해가 상처에 반영됨!")
        return True
    else:
        print(f"\n[FAIL] 상처 계산 오류: {wound_increase} != {expected_wound_increase}")
        return False

if __name__ == "__main__":
    success = test_refraction_wound()
    sys.exit(0 if success else 1)
