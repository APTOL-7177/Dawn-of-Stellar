"""
ATB System 테스트
"""

import pytest
from src.combat.atb_system import ATBSystem, ATBGauge, get_atb_system


class MockCharacter:
    """테스트용 캐릭터"""
    def __init__(self, name: str, speed: int = 10):
        self.name = name
        self.speed = speed
        self.is_enemy = False


def test_atb_gauge_initialization():
    """ATB 게이지 초기화 테스트"""
    char = MockCharacter("Test", 10)
    gauge = ATBGauge(char, max_gauge=2000, threshold=1000)

    assert gauge.current == 0
    assert gauge.max_gauge == 2000
    assert gauge.threshold == 1000
    assert gauge.percentage == 0.0
    assert not gauge.can_act


def test_atb_gauge_increase():
    """ATB 게이지 증가 테스트"""
    char = MockCharacter("Test", 10)
    gauge = ATBGauge(char, max_gauge=2000, threshold=1000)

    gauge.increase(500)
    assert gauge.current == 500
    assert gauge.percentage == 0.25
    assert not gauge.can_act

    gauge.increase(500)
    assert gauge.current == 1000
    assert gauge.can_act


def test_atb_gauge_status_effects():
    """ATB 게이지 상태이상 테스트"""
    char = MockCharacter("Test", 10)
    gauge = ATBGauge(char)

    # 기절 상태
    gauge.is_stunned = True
    assert gauge.get_effective_speed() == 0.0

    # 헤이스트 상태
    gauge.is_stunned = False
    gauge.haste_multiplier = 1.5
    assert gauge.get_effective_speed() == 15.0

    # 슬로우 상태
    gauge.haste_multiplier = 1.0
    gauge.slow_multiplier = 2.0
    assert gauge.get_effective_speed() == 5.0


def test_atb_system_register_combatant():
    """ATB 시스템 전투원 등록 테스트"""
    system = ATBSystem()
    char1 = MockCharacter("Warrior", 10)
    char2 = MockCharacter("Mage", 8)

    system.register_combatant(char1)
    system.register_combatant(char2)

    assert len(system.combatants) == 2
    assert char1 in system.gauges
    assert char2 in system.gauges


def test_atb_system_update():
    """ATB 시스템 업데이트 테스트"""
    system = ATBSystem()
    char = MockCharacter("Test", 10)

    system.register_combatant(char)
    gauge = system.get_gauge(char)

    # 여러 프레임 업데이트
    for _ in range(100):
        system.update(delta_time=1.0)

    # ATB가 증가했는지 확인
    assert gauge.current > 0


def test_atb_system_action_order():
    """ATB 시스템 행동 순서 테스트"""
    system = ATBSystem()
    char1 = MockCharacter("Fast", 20)
    char2 = MockCharacter("Slow", 5)

    system.register_combatant(char1)
    system.register_combatant(char2)

    # 충분히 업데이트
    for _ in range(200):
        system.update(delta_time=1.0)

    # Fast가 먼저 행동 가능해야 함
    order = system.get_action_order()
    if len(order) > 0:
        assert order[0] == char1 or system.get_gauge(char1).current > system.get_gauge(char2).current


def test_atb_system_consume():
    """ATB 소비 테스트"""
    system = ATBSystem()
    char = MockCharacter("Test", 10)

    system.register_combatant(char)
    gauge = system.get_gauge(char)

    # ATB를 1000으로 설정
    gauge.current = 1500

    # 소비
    system.consume_atb(char, 1000)
    assert gauge.current == 500


def test_atb_system_status_effects():
    """ATB 시스템 상태이상 적용 테스트"""
    system = ATBSystem()
    char = MockCharacter("Test", 10)

    system.register_combatant(char)

    # 헤이스트 적용
    system.apply_status_effect(char, "haste")
    effects = system.get_status_effects(char)
    assert "헤이스트" in effects

    # 슬로우 적용
    system.apply_status_effect(char, "slow")
    effects = system.get_status_effects(char)
    assert "슬로우" in effects

    # 기절 적용
    system.apply_status_effect(char, "stun")
    effects = system.get_status_effects(char)
    assert "기절" in effects


def test_atb_system_clear():
    """ATB 시스템 초기화 테스트"""
    system = ATBSystem()
    char = MockCharacter("Test", 10)

    system.register_combatant(char)
    assert len(system.combatants) == 1

    system.clear()
    assert len(system.combatants) == 0
    assert len(system.gauges) == 0


def test_get_atb_system_singleton():
    """전역 ATB 시스템 싱글톤 테스트"""
    system1 = get_atb_system()
    system2 = get_atb_system()

    assert system1 is system2
