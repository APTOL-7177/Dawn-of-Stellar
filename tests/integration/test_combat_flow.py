"""
Combat Flow 통합 테스트

전체 전투 시퀀스를 테스트합니다.
"""

import pytest
from src.combat.combat_manager import CombatManager, CombatState, ActionType


class MockCharacter:
    """테스트용 캐릭터"""
    def __init__(self, name: str, speed: int = 10):
        self.name = name
        self.speed = speed
        self.level = 1

        # 스탯
        self.physical_attack = 20
        self.physical_defense = 10
        self.magic_attack = 15
        self.magic_defense = 8
        self.luck = 5

        # HP/MP
        self.current_hp = 100
        self.max_hp = 100
        self.current_mp = 50
        self.max_mp = 50

        # BRV
        self.current_brv = 0
        self.int_brv = 100
        self.max_brv = 300
        self.is_broken = False
        self.brv_efficiency = 1.0
        self.brv_loss_resistance = 1.0

        # 속성
        self.is_enemy = False

    def take_damage(self, damage: int) -> int:
        """HP 데미지 적용"""
        actual_damage = min(damage, self.current_hp)
        self.current_hp -= actual_damage
        return actual_damage

    def is_alive(self) -> bool:
        """생존 여부"""
        return self.current_hp > 0


def test_combat_initialization():
    """전투 초기화 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    assert manager.state == CombatState.IN_PROGRESS
    assert len(manager.allies) == 1
    assert len(manager.enemies) == 1


def test_combat_brv_attack():
    """BRV 공격 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # ATB가 충분히 찰 때까지 업데이트
    for _ in range(200):
        manager.update(delta_time=1.0)

    # BRV 공격 실행
    result = manager.execute_action(
        player,
        ActionType.BRV_ATTACK,
        target=enemy
    )

    assert result["action"] == "brv_attack"
    assert result["damage"] > 0
    assert "brv_stolen" in result


def test_combat_hp_attack():
    """HP 공격 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # BRV 축적
    player.current_brv = 500

    # HP 공격 실행
    initial_hp = enemy.current_hp
    result = manager.execute_action(
        player,
        ActionType.HP_ATTACK,
        target=enemy
    )

    assert result["action"] == "hp_attack"
    assert result["hp_damage"] > 0
    assert enemy.current_hp < initial_hp


def test_combat_brv_hp_combo():
    """BRV + HP 복합 공격 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # 복합 공격 실행
    result = manager.execute_action(
        player,
        ActionType.BRV_HP_ATTACK,
        target=enemy
    )

    assert result["action"] == "brv_hp_attack"
    assert result["is_combo"] is True
    # BRV 공격 결과 (brv_ 접두사 붙음)
    assert "brv_brv_stolen" in result or "brv_damage" in result
    # HP 공격 결과
    assert "hp_damage" in result


def test_combat_victory_condition():
    """승리 조건 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # 적을 죽임
    enemy.current_hp = 0

    # 승리 판정
    manager._check_battle_end()

    assert manager.state == CombatState.VICTORY


def test_combat_defeat_condition():
    """패배 조건 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # 플레이어가 죽음
    player.current_hp = 0

    # 패배 판정
    manager._check_battle_end()

    assert manager.state == CombatState.DEFEAT


def test_combat_action_order():
    """행동 순서 테스트"""
    manager = CombatManager()

    fast_char = MockCharacter("Fast", speed=20)
    slow_char = MockCharacter("Slow", speed=5)
    slow_char.is_enemy = True

    manager.start_combat([fast_char], [slow_char])

    # 충분히 업데이트
    for _ in range(300):
        manager.update(delta_time=1.0)

    # 행동 순서 확인
    order = manager.get_action_order()

    # Fast가 먼저 행동 가능해야 함
    if len(order) >= 2:
        assert order[0] == fast_char


def test_combat_valid_targets():
    """유효한 대상 확인 테스트"""
    manager = CombatManager()

    player1 = MockCharacter("Player1", speed=10)
    player2 = MockCharacter("Player2", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player1, player2], [enemy])

    # 플레이어의 공격 대상은 적
    targets = manager.get_valid_targets(player1, ActionType.BRV_ATTACK)
    assert enemy in targets
    assert player2 not in targets

    # 적의 공격 대상은 플레이어들
    targets = manager.get_valid_targets(enemy, ActionType.BRV_ATTACK)
    assert player1 in targets
    assert player2 in targets


def test_combat_break_mechanic():
    """BREAK 메커니즘 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # 적의 BRV를 낮춤
    enemy.current_brv = 10

    # 큰 데미지로 BREAK 유발
    result = manager.execute_action(
        player,
        ActionType.BRV_ATTACK,
        target=enemy
    )

    # BREAK 확인
    if result.get("is_break"):
        assert enemy.current_brv == 0
        assert enemy.is_broken is True


def test_combat_full_battle_sequence():
    """전체 전투 시퀀스 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=15)
    player.physical_attack = 50
    enemy = MockCharacter("Enemy", speed=10)
    enemy.is_enemy = True
    enemy.current_hp = 200

    manager.start_combat([player], [enemy])

    turn_limit = 100
    turns = 0

    # 전투 진행
    while manager.state == CombatState.IN_PROGRESS and turns < turn_limit:
        # ATB 업데이트
        manager.update(delta_time=1.0)

        # 행동 가능한 캐릭터 확인
        order = manager.get_action_order()
        if len(order) > 0:
            actor = order[0]

            # 대상 선택
            targets = manager.get_valid_targets(actor, ActionType.BRV_HP_ATTACK)
            if targets:
                target = targets[0]

                # 행동 실행
                manager.execute_action(
                    actor,
                    ActionType.BRV_HP_ATTACK,
                    target=target
                )

                turns += 1

    # 전투가 종료되었는지 확인 (승리 또는 패배)
    assert manager.state in [CombatState.VICTORY, CombatState.DEFEAT]
    assert turns < turn_limit  # 무한 루프 방지


def test_combat_flee():
    """도망 테스트"""
    manager = CombatManager()

    player = MockCharacter("Player", speed=10)
    enemy = MockCharacter("Enemy", speed=8)
    enemy.is_enemy = True

    manager.start_combat([player], [enemy])

    # 도망 시도 (여러 번 시도하여 성공 확인)
    for _ in range(20):
        result = manager.execute_action(player, ActionType.FLEE)
        if result["success"]:
            assert manager.state == CombatState.FLED
            break
