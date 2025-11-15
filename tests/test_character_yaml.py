"""
Character 클래스와 YAML 통합 테스트
"""
import pytest
from src.character.character import Character


def test_create_warrior():
    """전사 캐릭터 생성 테스트"""
    char = Character("테스트전사", "전사")
    assert char.name == "테스트전사"
    assert char.character_class == "전사"
    assert char.max_hp == 210
    assert char.max_mp == 32
    assert char.strength == 60
    assert char.defense == 60
    assert char.magic == 40
    assert char.spirit == 60
    assert char.speed == 60


def test_create_archmage():
    """아크메이지 캐릭터 생성 테스트"""
    char = Character("테스트메이지", "아크메이지")
    assert char.name == "테스트메이지"
    assert char.character_class == "아크메이지"
    assert char.max_hp == 121
    assert char.max_mp == 89
    assert char.magic == 78


def test_warrior_gimmick_initialization():
    """전사 기믹 초기화 테스트"""
    char = Character("전사1", "전사")
    assert hasattr(char, 'current_stance')
    assert char.current_stance == "balanced"
    assert hasattr(char, 'available_stances')
    assert len(char.available_stances) == 6


def test_archmage_gimmick_initialization():
    """아크메이지 기믹 초기화 테스트"""
    char = Character("메이지1", "아크메이지")
    assert hasattr(char, 'fire_count')
    assert hasattr(char, 'ice_count')
    assert hasattr(char, 'lightning_count')
    assert char.fire_count == 0
    assert char.ice_count == 0
    assert char.lightning_count == 0


def test_character_traits_loaded():
    """캐릭터 특성 로드 테스트"""
    char = Character("전사1", "전사")
    assert hasattr(char, 'available_traits')
    assert len(char.available_traits) >= 3


def test_character_skills_loaded():
    """캐릭터 스킬 로드 테스트"""
    char = Character("전사1", "전사")
    assert hasattr(char, 'skill_ids')
    assert len(char.skill_ids) > 0


def test_create_all_classes():
    """모든 직업 생성 테스트"""
    from src.character.character_loader import get_all_classes

    classes = get_all_classes()
    for class_name in classes:
        char = Character(f"테스트_{class_name}", class_name)
        assert char.character_class == class_name
        assert char.max_hp > 0
        assert char.max_mp > 0


def test_berserker_high_hp():
    """광전사 높은 HP 테스트"""
    char = Character("광전사1", "광전사")
    assert char.max_hp == 327


def test_dimensionist_low_hp():
    """차원술사 낮은 HP 테스트"""
    char = Character("차원술사1", "차원술사")
    assert char.max_hp == 84


def test_character_hp_damage():
    """캐릭터 데미지 테스트"""
    char = Character("전사1", "전사")
    initial_hp = char.current_hp
    char.take_damage(50)
    assert char.current_hp == initial_hp - 50
    assert char.is_alive is True


def test_character_death():
    """캐릭터 사망 테스트"""
    char = Character("전사1", "전사")
    char.take_damage(1000)
    assert char.current_hp == 0
    assert char.is_alive is False


def test_character_heal():
    """캐릭터 힐 테스트"""
    char = Character("전사1", "전사")
    char.take_damage(50)
    healed = char.heal(30)
    assert healed == 30


def test_character_mp_consumption():
    """캐릭터 MP 소모 테스트"""
    char = Character("아크메이지1", "아크메이지")
    initial_mp = char.current_mp
    success = char.consume_mp(20)
    assert success is True
    assert char.current_mp == initial_mp - 20


def test_character_level_up():
    """캐릭터 레벨업 테스트"""
    char = Character("전사1", "전사")
    old_hp = char.max_hp
    char.level_up()
    assert char.level == 2
    assert char.max_hp > old_hp
    assert char.current_hp == char.max_hp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
