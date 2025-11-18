#!/usr/bin/env python3
"""
버그 수정 검증 스크립트
"""

import sys
sys.path.insert(0, '/home/user/Dos')

from src.world.enemy_generator import ENEMY_TEMPLATES, EnemyGenerator, SimpleEnemy
from src.combat.atb_system import ATBSystem
from src.combat.combat_manager import CombatManager, CombatState
from src.core.config import initialize_config

# 설정 초기화
initialize_config()


def test_enemy_balance():
    """1레벨 적 밸런싱 확인"""
    print("\n=== 1레벨 적 밸런싱 테스트 ===")

    # 슬라임 스탯 확인
    slime = ENEMY_TEMPLATES["slime"]
    print(f"\n슬라임 (Lv {slime.level}) - 마법형:")
    print(f"  HP: {slime.hp}, MP: {slime.mp}")
    print(f"  물리 공격력: {slime.physical_attack}, 물리 방어력: {slime.physical_defense}")
    print(f"  마법 공격력: {slime.magic_attack}, 마법 방어력: {slime.magic_defense}")
    print(f"  속도: {slime.speed}, 행운: {slime.luck}, 명중: {slime.accuracy}, 회피: {slime.evasion}")
    print(f"  최대 BRV: {slime.max_brv}, 초기 BRV: {slime.init_brv} ({slime.init_brv/slime.max_brv*100:.1f}%)")

    # 고블린 스탯 확인
    goblin = ENEMY_TEMPLATES["goblin"]
    print(f"\n고블린 (Lv {goblin.level}) - 균형형:")
    print(f"  HP: {goblin.hp}, MP: {goblin.mp}")
    print(f"  물리 공격력: {goblin.physical_attack}, 물리 방어력: {goblin.physical_defense}")
    print(f"  마법 공격력: {goblin.magic_attack}, 마법 방어력: {goblin.magic_defense}")
    print(f"  속도: {goblin.speed}, 행운: {goblin.luck}, 명중: {goblin.accuracy}, 회피: {goblin.evasion}")
    print(f"  최대 BRV: {goblin.max_brv}, 초기 BRV: {goblin.init_brv} ({goblin.init_brv/goblin.max_brv*100:.1f}%)")

    # 늑대 스탯 확인
    wolf = ENEMY_TEMPLATES["wolf"]
    print(f"\n늑대 (Lv {wolf.level}) - 물리형:")
    print(f"  HP: {wolf.hp}, MP: {wolf.mp}")
    print(f"  물리 공격력: {wolf.physical_attack}, 물리 방어력: {wolf.physical_defense}")
    print(f"  마법 공격력: {wolf.magic_attack}, 마법 방어력: {wolf.magic_defense}")
    print(f"  속도: {wolf.speed}, 행운: {wolf.luck}, 명중: {wolf.accuracy}, 회피: {wolf.evasion}")
    print(f"  최대 BRV: {wolf.max_brv}, 초기 BRV: {wolf.init_brv} ({wolf.init_brv/wolf.max_brv*100:.1f}%)")

    # 평균 계산
    avg_hp = (slime.hp + goblin.hp + wolf.hp) / 3
    avg_mp = (slime.mp + goblin.mp + wolf.mp) / 3
    avg_patk = (slime.physical_attack + goblin.physical_attack + wolf.physical_attack) / 3
    avg_pdef = (slime.physical_defense + goblin.physical_defense + wolf.physical_defense) / 3
    avg_matk = (slime.magic_attack + goblin.magic_attack + wolf.magic_attack) / 3
    avg_mdef = (slime.magic_defense + goblin.magic_defense + wolf.magic_defense) / 3
    avg_spd = (slime.speed + goblin.speed + wolf.speed) / 3
    avg_luck = (slime.luck + goblin.luck + wolf.luck) / 3
    avg_acc = (slime.accuracy + goblin.accuracy + wolf.accuracy) / 3
    avg_eva = (slime.evasion + goblin.evasion + wolf.evasion) / 3

    print(f"\n=== 1레벨 약한 적 평균 스탯 ===")
    print(f"  HP: {avg_hp:.1f} (목표: 200)")
    print(f"  MP: {avg_mp:.1f} (목표: 40)")
    print(f"  물리 공격력: {avg_patk:.1f} (목표: 55)")
    print(f"  물리 방어력: {avg_pdef:.1f} (목표: 45)")
    print(f"  마법 공격력: {avg_matk:.1f} (목표: 55)")
    print(f"  마법 방어력: {avg_mdef:.1f} (목표: 45)")
    print(f"  속도: {avg_spd:.1f} (목표: 55)")
    print(f"  행운: {avg_luck:.1f} (목표: 10)")
    print(f"  명중: {avg_acc:.1f} (목표: 65)")
    print(f"  회피: {avg_eva:.1f} (목표: 12)")

    # 검증 (평균이 목표치에 가까운지)
    assert abs(avg_hp - 200) < 30, f"평균 HP가 목표치에서 너무 벗어남: {avg_hp:.1f}"
    assert abs(avg_patk - 55) < 15, f"평균 물리 공격력이 목표치에서 너무 벗어남: {avg_patk:.1f}"
    assert abs(avg_spd - 55) < 10, f"평균 속도가 목표치에서 너무 벗어남: {avg_spd:.1f}"

    # 모든 적이 레벨 1인지 확인
    for enemy_id, template in ENEMY_TEMPLATES.items():
        assert template.level == 1, f"{enemy_id}의 레벨이 1이 아닙니다: {template.level}"

    print("\n✓ 적 밸런싱 테스트 통과!")
    print("✓ 모든 적이 레벨 1 기준으로 설정됨!")
    print("✓ BRV 값이 템플릿에 명시적으로 정의됨!")


def test_atb_system():
    """ATB 시스템 동작 확인"""
    print("\n=== ATB 시스템 테스트 ===")

    # 간단한 캐릭터 클래스
    class DummyCharacter:
        def __init__(self, name, speed):
            self.name = name
            self.speed = speed

    atb = ATBSystem()

    # 전투원 등록
    player = DummyCharacter("플레이어", 10)
    enemy = DummyCharacter("슬라임", 8)

    atb.register_combatant(player)
    atb.register_combatant(enemy)

    print(f"\n초기 ATB 게이지:")
    print(f"  플레이어: {atb.get_gauge(player).current}")
    print(f"  슬라임: {atb.get_gauge(enemy).current}")

    # 일반 업데이트 (시간 흐름)
    print(f"\n일반 업데이트 (is_player_turn=False):")
    for i in range(5):
        atb.update(delta_time=1.0, is_player_turn=False)
        print(f"  프레임 {i+1} - 플레이어: {atb.get_gauge(player).current:.1f}, 슬라임: {atb.get_gauge(enemy).current:.1f}")

    player_gauge_before = atb.get_gauge(player).current

    # 플레이어 턴 중 업데이트 (시간 정지)
    print(f"\n플레이어 턴 중 업데이트 (is_player_turn=True):")
    for i in range(5):
        atb.update(delta_time=1.0, is_player_turn=True)
        print(f"  프레임 {i+1} - 플레이어: {atb.get_gauge(player).current:.1f}, 슬라임: {atb.get_gauge(enemy).current:.1f}")

    player_gauge_after = atb.get_gauge(player).current

    # 검증: 플레이어 턴 중에는 ATB가 증가하지 않아야 함
    assert player_gauge_before == player_gauge_after, "플레이어 턴 중 ATB가 증가했습니다!"

    print("\n✓ ATB 시스템 테스트 통과!")
    print("  → 플레이어 턴 중 ATB가 정지하는 것을 확인했습니다.")


def test_combat_state():
    """전투 상태 전환 테스트"""
    print("\n=== 전투 상태 전환 테스트 ===")

    combat = CombatManager()

    print(f"초기 상태: {combat.state}")
    assert combat.state == CombatState.NOT_STARTED

    # 전투 시작
    class DummyCharacter:
        def __init__(self, name):
            self.name = name
            self.speed = 10
            self.current_brv = 0
            self.max_brv = 1000
            self.is_alive = True

    allies = [DummyCharacter("플레이어")]
    enemies = [DummyCharacter("슬라임")]

    combat.start_combat(allies, enemies)
    print(f"전투 시작 후: {combat.state}")
    assert combat.state == CombatState.IN_PROGRESS

    # 상태 변경 테스트
    combat.state = CombatState.PLAYER_TURN
    print(f"플레이어 턴으로 변경: {combat.state}")
    assert combat.state == CombatState.PLAYER_TURN

    combat.state = CombatState.IN_PROGRESS
    print(f"진행 중으로 변경: {combat.state}")
    assert combat.state == CombatState.IN_PROGRESS

    print("\n✓ 전투 상태 전환 테스트 통과!")


def test_level_scaling():
    """레벨 스케일링 테스트"""
    print("\n=== 레벨 스케일링 테스트 ===")

    # 1층 슬라임 (level_modifier = 1.0)
    slime_template = ENEMY_TEMPLATES["slime"]
    slime_floor1 = SimpleEnemy(slime_template, level_modifier=1.0)
    print(f"\n1층 슬라임:")
    print(f"  HP: {slime_floor1.max_hp} (템플릿: {slime_template.hp})")
    print(f"  물리 공격력: {slime_floor1.physical_attack} (템플릿: {slime_template.physical_attack})")
    print(f"  최대 BRV: {slime_floor1.max_brv} (템플릿: {slime_template.max_brv})")
    print(f"  초기 BRV: {slime_floor1.current_brv} (템플릿: {slime_template.init_brv})")

    # 5층 슬라임 (level_modifier = 1.0 + (5-1)*0.5 = 3.0)
    slime_floor5 = SimpleEnemy(slime_template, level_modifier=3.0)
    print(f"\n5층 슬라임 (3배 스케일링):")
    print(f"  HP: {slime_floor5.max_hp} (1층의 {slime_floor5.max_hp/slime_floor1.max_hp:.1f}배)")
    print(f"  물리 공격력: {slime_floor5.physical_attack} (1층의 {slime_floor5.physical_attack/slime_floor1.physical_attack:.1f}배)")
    print(f"  최대 BRV: {slime_floor5.max_brv} (1층의 {slime_floor5.max_brv/slime_floor1.max_brv:.1f}배)")
    print(f"  초기 BRV: {slime_floor5.current_brv} (1층의 {slime_floor5.current_brv/slime_floor1.current_brv:.1f}배)")

    # 스케일링 검증
    assert slime_floor5.max_hp == slime_floor1.max_hp * 3, "HP 스케일링 오류"
    assert slime_floor5.physical_attack == slime_floor1.physical_attack * 3, "공격력 스케일링 오류"
    assert slime_floor5.max_brv == slime_floor1.max_brv * 3, "최대 BRV 스케일링 오류"
    assert slime_floor5.current_brv == slime_floor1.current_brv * 3, "초기 BRV 스케일링 오류"

    print("\n✓ 레벨 스케일링 테스트 통과!")


def test_enemy_generation():
    """적 생성 테스트"""
    print("\n=== 적 생성 테스트 ===")

    # 1층 적 생성
    enemies_floor1 = EnemyGenerator.generate_enemies(floor_number=1, num_enemies=3)
    print(f"\n1층 생성된 적 ({len(enemies_floor1)}마리):")
    for enemy in enemies_floor1:
        print(f"  - {enemy.name}: HP {enemy.max_hp}, ATK {enemy.physical_attack}, BRV {enemy.current_brv}/{enemy.max_brv}")

    # 5층 적 생성
    enemies_floor5 = EnemyGenerator.generate_enemies(floor_number=5, num_enemies=3)
    print(f"\n5층 생성된 적 ({len(enemies_floor5)}마리):")
    for enemy in enemies_floor5:
        print(f"  - {enemy.name}: HP {enemy.max_hp}, ATK {enemy.physical_attack}, BRV {enemy.current_brv}/{enemy.max_brv}")

    # 10층 적 생성
    enemies_floor10 = EnemyGenerator.generate_enemies(floor_number=10, num_enemies=3)
    print(f"\n10층 생성된 적 ({len(enemies_floor10)}마리):")
    for enemy in enemies_floor10:
        print(f"  - {enemy.name}: HP {enemy.max_hp}, ATK {enemy.physical_attack}, BRV {enemy.current_brv}/{enemy.max_brv}")

    # 적절한 수 생성 확인
    assert len(enemies_floor1) == 3, "1층 적 수 오류"
    assert len(enemies_floor5) == 3, "5층 적 수 오류"
    assert len(enemies_floor10) == 3, "10층 적 수 오류"

    # 5층이 1층보다 강한지 확인
    avg_hp_floor1 = sum(e.max_hp for e in enemies_floor1) / len(enemies_floor1)
    avg_hp_floor5 = sum(e.max_hp for e in enemies_floor5) / len(enemies_floor5)
    assert avg_hp_floor5 > avg_hp_floor1, "5층 적이 1층보다 약함"

    print("\n✓ 적 생성 테스트 통과!")


if __name__ == "__main__":
    try:
        test_enemy_balance()
        test_level_scaling()
        test_enemy_generation()
        test_atb_system()
        test_combat_state()

        print("\n" + "="*50)
        print("모든 테스트 통과! ✓")
        print("="*50)

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
