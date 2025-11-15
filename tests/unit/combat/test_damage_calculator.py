"""
Damage Calculator 테스트
"""

import pytest
from src.combat.damage_calculator import DamageCalculator, DamageResult, get_damage_calculator


class MockCharacter:
    """테스트용 캐릭터"""
    def __init__(self, name: str):
        self.name = name
        self.physical_attack = 100
        self.physical_defense = 50
        self.magic_attack = 80
        self.magic_defense = 40
        self.luck = 5
        self.current_brv = 500


def test_damage_calculator_initialization():
    """데미지 계산기 초기화 테스트"""
    calc = DamageCalculator()

    assert calc.brv_damage_multiplier > 0
    assert calc.hp_damage_multiplier > 0
    assert calc.break_damage_bonus >= 1.0


def test_calculate_brv_damage_basic():
    """기본 BRV 데미지 계산 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result = calc.calculate_brv_damage(attacker, defender, skill_multiplier=1.0)

    assert isinstance(result, DamageResult)
    assert result.final_damage > 0
    assert result.base_damage > 0


def test_calculate_brv_damage_with_multiplier():
    """BRV 데미지 스킬 배율 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result1 = calc.calculate_brv_damage(attacker, defender, skill_multiplier=1.0)
    result2 = calc.calculate_brv_damage(attacker, defender, skill_multiplier=2.0)

    # 배율 2배면 데미지도 대략 2배
    assert result2.final_damage > result1.final_damage


def test_calculate_brv_damage_defense():
    """방어력에 따른 BRV 데미지 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    weak_defender = MockCharacter("Weak")
    weak_defender.physical_defense = 20

    strong_defender = MockCharacter("Strong")
    strong_defender.physical_defense = 80

    result_weak = calc.calculate_brv_damage(attacker, weak_defender)
    result_strong = calc.calculate_brv_damage(attacker, strong_defender)

    # 방어력이 낮은 대상이 더 큰 데미지
    assert result_weak.final_damage >= result_strong.final_damage


def test_calculate_hp_damage_basic():
    """기본 HP 데미지 계산 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result, wound_damage = calc.calculate_hp_damage(
        attacker, defender, brv_points=500, hp_multiplier=1.0
    )

    assert isinstance(result, DamageResult)
    assert result.final_damage > 0
    assert wound_damage > 0
    # 상처 데미지는 HP 데미지의 일부
    assert wound_damage < result.final_damage


def test_calculate_hp_damage_break_bonus():
    """HP 데미지 BREAK 보너스 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result_normal, _ = calc.calculate_hp_damage(
        attacker, defender, brv_points=500, is_break=False
    )
    result_break, _ = calc.calculate_hp_damage(
        attacker, defender, brv_points=500, is_break=True
    )

    # BREAK 시 보너스 데미지
    assert result_break.final_damage > result_normal.final_damage


def test_calculate_hp_damage_multiplier():
    """HP 데미지 배율 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result1, _ = calc.calculate_hp_damage(
        attacker, defender, brv_points=500, hp_multiplier=1.0
    )
    result2, _ = calc.calculate_hp_damage(
        attacker, defender, brv_points=500, hp_multiplier=2.0
    )

    # 배율 2배면 데미지도 대략 2배
    assert result2.final_damage > result1.final_damage


def test_calculate_hp_damage_wound():
    """상처 데미지 계산 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result, wound_damage = calc.calculate_hp_damage(
        attacker, defender, brv_points=500
    )

    # 상처 데미지는 HP 데미지의 약 25%
    expected_wound = int(result.final_damage * calc.wound_damage_rate)
    assert abs(wound_damage - expected_wound) <= 1  # 반올림 오차 허용


def test_calculate_magic_damage():
    """마법 데미지 계산 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result = calc.calculate_magic_damage(attacker, defender, skill_multiplier=1.5)

    assert result.final_damage > 0
    assert result.base_damage > 0


def test_calculate_magic_damage_with_element():
    """속성 마법 데미지 계산 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    result = calc.calculate_magic_damage(
        attacker, defender, skill_multiplier=1.0, element="fire"
    )

    assert result.final_damage > 0
    assert result.details["element"] == "fire"


def test_critical_hit():
    """크리티컬 판정 테스트"""
    calc = DamageCalculator()

    # 행운이 높은 캐릭터
    lucky_char = MockCharacter("Lucky")
    lucky_char.luck = 50

    # 여러 번 테스트하여 크리티컬 발생 확인
    critical_count = 0
    for _ in range(100):
        if calc._check_critical(lucky_char):
            critical_count += 1

    # 행운이 높으면 크리티컬 확률도 높음
    assert critical_count > 10  # 최소 10% 이상


def test_damage_variance():
    """데미지 랜덤 변수 테스트"""
    calc = DamageCalculator()
    attacker = MockCharacter("Attacker")
    defender = MockCharacter("Defender")

    damages = []
    for _ in range(10):
        result = calc.calculate_brv_damage(attacker, defender)
        damages.append(result.final_damage)

    # 랜덤 변수로 인해 데미지가 다름
    assert len(set(damages)) > 1  # 최소 2개 이상 다른 값


def test_get_damage_calculator_singleton():
    """전역 데미지 계산기 싱글톤 테스트"""
    calc1 = get_damage_calculator()
    calc2 = get_damage_calculator()

    assert calc1 is calc2
