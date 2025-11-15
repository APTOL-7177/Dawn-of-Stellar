"""
캐릭터 로더 테스트
"""
import pytest
from src.character.character_loader import (
    load_character_data,
    get_base_stats,
    get_gimmick,
    get_traits,
    get_skills,
    get_all_classes,
    validate_all_data
)


def test_load_warrior_data():
    """전사 데이터 로드 테스트"""
    data = load_character_data("전사")
    assert data is not None
    assert data['class_name'] == "전사"
    assert 'base_stats' in data
    assert 'gimmick' in data


def test_get_warrior_stats():
    """전사 기본 스탯 테스트"""
    stats = get_base_stats("전사")
    assert stats['hp'] == 210
    assert stats['mp'] == 32
    assert stats['physical_attack'] == 60
    assert stats['physical_defense'] == 60
    assert stats['magic_attack'] == 40
    assert stats['magic_defense'] == 60
    assert stats['speed'] == 60


def test_get_archmage_stats():
    """아크메이지 기본 스탯 테스트"""
    stats = get_base_stats("아크메이지")
    assert stats['hp'] == 121
    assert stats['mp'] == 89
    assert stats['physical_attack'] == 43
    assert stats['magic_attack'] == 78


def test_get_warrior_gimmick():
    """전사 기믹 시스템 테스트"""
    gimmick = get_gimmick("전사")
    assert gimmick is not None
    assert gimmick['type'] == "stance_system"
    assert 'stances' in gimmick
    assert len(gimmick['stances']) == 6


def test_get_archmage_gimmick():
    """아크메이지 기믹 시스템 테스트"""
    gimmick = get_gimmick("아크메이지")
    assert gimmick is not None
    assert gimmick['type'] == "elemental_counter"
    assert 'elements' in gimmick


def test_get_warrior_traits():
    """전사 특성 테스트"""
    traits = get_traits("전사")
    assert len(traits) >= 3
    trait_names = [t['name'] for t in traits]
    assert "적응형 무술" in trait_names


def test_get_warrior_skills():
    """전사 스킬 테스트"""
    skills = get_skills("전사")
    assert len(skills) > 0
    assert "power_strike" in skills


def test_get_all_classes():
    """전체 직업 목록 테스트"""
    classes = get_all_classes()
    assert len(classes) == 28
    assert "전사" in classes
    assert "아크메이지" in classes
    assert "정령술사" in classes
    assert "마법사" in classes


def test_validate_all_data():
    """전체 데이터 검증 테스트"""
    result = validate_all_data()
    assert result is True


def test_unknown_class():
    """알 수 없는 직업 테스트"""
    data = load_character_data("없는직업")
    assert data is None


def test_berserker_stats():
    """광전사 스탯 테스트 (가장 높은 HP)"""
    stats = get_base_stats("광전사")
    assert stats['hp'] == 327
    assert stats['physical_attack'] == 64


def test_dimensionist_stats():
    """차원술사 스탯 테스트 (가장 낮은 HP)"""
    stats = get_base_stats("차원술사")
    assert stats['hp'] == 84
    assert stats['magic_attack'] == 88


def test_time_mage_mp():
    """시간술사 MP 테스트 (가장 높은 MP)"""
    stats = get_base_stats("시간술사")
    assert stats['mp'] == 103


def test_rogue_speed():
    """도적 속도 테스트 (가장 높은 속도)"""
    stats = get_base_stats("도적")
    assert stats['speed'] == 93


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
