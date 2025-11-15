"""
Brave System 테스트
"""

import pytest
from src.combat.brave_system import BraveSystem, get_brave_system


class MockCharacter:
    """테스트용 캐릭터"""
    def __init__(self, name: str, level: int = 1):
        self.name = name
        self.level = level
        self.current_brv = 0
        self.int_brv = 100
        self.max_brv = 300
        self.current_hp = 100
        self.max_hp = 100
        self.is_broken = False
        self.brv_efficiency = 1.0
        self.brv_loss_resistance = 1.0

    def take_damage(self, damage: int) -> int:
        """HP 데미지 적용"""
        actual_damage = min(damage, self.current_hp)
        self.current_hp -= actual_damage
        return actual_damage


def test_brave_system_initialization():
    """Brave 시스템 초기화 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    system.initialize_brv(char)

    assert char.current_brv > 0
    assert char.int_brv > 0
    assert char.max_brv > char.int_brv


def test_calculate_int_brv():
    """INT BRV 계산 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test", level=5)

    int_brv = system.calculate_int_brv(char)

    # 레벨 보너스 반영 확인
    assert int_brv > 100  # 기본값 + 레벨 보너스


def test_calculate_max_brv():
    """MAX BRV 계산 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test", level=5)

    max_brv = system.calculate_max_brv(char)

    # INT BRV의 3배 이상
    int_brv = system.calculate_int_brv(char)
    assert max_brv >= int_brv * 2


def test_brv_attack():
    """BRV 공격 테스트"""
    system = BraveSystem()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    system.initialize_brv(attacker)
    system.initialize_brv(defender)

    initial_attacker_brv = attacker.current_brv
    initial_defender_brv = defender.current_brv

    # BRV 공격
    result = system.brv_attack(attacker, defender, damage=100)

    # 공격자 BRV 증가 확인
    assert attacker.current_brv > initial_attacker_brv
    # 방어자 BRV 감소 확인
    assert defender.current_brv < initial_defender_brv
    # 결과 확인
    assert result["brv_stolen"] > 0
    assert result["actual_gain"] >= 0


def test_brv_attack_break():
    """BRV 공격 BREAK 테스트"""
    system = BraveSystem()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    system.initialize_brv(attacker)
    system.initialize_brv(defender)

    # 방어자 BRV를 낮춤
    defender.current_brv = 10

    # 큰 데미지로 BREAK 유발
    result = system.brv_attack(attacker, defender, damage=1000)

    # BREAK 확인
    assert result["is_break"] is True
    assert defender.current_brv == 0
    assert defender.is_broken is True


def test_hp_attack():
    """HP 공격 테스트"""
    system = BraveSystem()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    system.initialize_brv(attacker)
    system.initialize_brv(defender)

    # BRV 축적
    attacker.current_brv = 500

    initial_hp = defender.current_hp

    # HP 공격
    result = system.hp_attack(attacker, defender, brv_multiplier=1.0)

    # HP 감소 확인
    assert result["hp_damage"] > 0
    # BRV 소비 확인
    assert attacker.current_brv == 0
    assert result["brv_consumed"] == 500


def test_hp_attack_break_bonus():
    """HP 공격 BREAK 보너스 테스트"""
    system = BraveSystem()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    system.initialize_brv(attacker)
    system.initialize_brv(defender)

    attacker.current_brv = 500

    # BREAK 상태로 설정
    defender.is_broken = True
    defender.current_brv = 0

    # HP 공격
    result = system.hp_attack(attacker, defender)

    # BREAK 보너스 적용 확인
    assert result["is_break_bonus"] is True
    assert result["hp_damage"] > 0


def test_brv_hp_attack():
    """BRV + HP 복합 공격 테스트"""
    system = BraveSystem()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    system.initialize_brv(attacker)
    system.initialize_brv(defender)

    # 복합 공격
    result = system.brv_hp_attack(attacker, defender, brv_damage=100, hp_multiplier=1.0)

    # BRV 공격 결과 확인
    assert "brv_stolen" in result
    # HP 공격 결과 확인
    assert "hp_damage" in result
    # 복합 공격 플래그 확인
    assert result["is_combo"] is True


def test_restore_brv():
    """BRV 회복 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    system.initialize_brv(char)
    char.current_brv = 100

    # BRV 회복
    restored = system.restore_brv(char, 50)

    assert restored == 50
    assert char.current_brv == 150


def test_restore_brv_max_limit():
    """BRV 회복 MAX 제한 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    system.initialize_brv(char)
    char.current_brv = char.max_brv - 10

    # MAX BRV를 초과하는 양 회복 시도
    restored = system.restore_brv(char, 100)

    # MAX BRV에서 잘렸는지 확인
    assert char.current_brv == char.max_brv
    assert restored == 10


def test_recover_int_brv():
    """INT BRV 회복 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    system.initialize_brv(char)
    char.current_brv = 0

    # INT BRV 회복
    recovered = system.recover_int_brv(char)

    assert recovered == char.int_brv
    assert char.current_brv == char.int_brv


def test_recover_int_brv_break_state():
    """BREAK 상태에서 INT BRV 회복 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    system.initialize_brv(char)
    char.current_brv = 0
    char.is_broken = True
    char.break_turn_count = 0

    # BREAK 상태에서는 1턴 후 회복
    recovered = system.recover_int_brv(char)
    assert recovered == char.int_brv
    assert char.is_broken is False


def test_is_broken():
    """BREAK 상태 확인 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    assert system.is_broken(char) is False

    char.is_broken = True
    assert system.is_broken(char) is True


def test_clear_break_state():
    """BREAK 상태 해제 테스트"""
    system = BraveSystem()
    char = MockCharacter("Test")

    char.is_broken = True
    char.break_turn_count = 5

    system.clear_break_state(char)

    assert char.is_broken is False
    assert char.break_turn_count == 0


def test_get_brave_system_singleton():
    """전역 Brave 시스템 싱글톤 테스트"""
    system1 = get_brave_system()
    system2 = get_brave_system()

    assert system1 is system2
