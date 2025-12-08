"""
사무라이 완전 테스트 - 검심 시스템 통합 테스트

작성일: 2025-12-05
"""

import pytest
from src.character.character import Character
from src.character.skills.skill_manager import SkillManager
from src.character.gimmick_updater import GimmickUpdater
from src.combat.combat_manager import CombatManager
from src.world.enemy_generator import Enemy


@pytest.fixture
def samurai():
    """사무라이 캐릭터 생성"""
    skill_manager = SkillManager()
    samurai = Character("사무라이", "samurai")
    samurai.skill_manager = skill_manager

    # 기믹 초기화
    samurai.gimmick_type = "kenshin_system"
    samurai.observation = 0
    samurai.max_observation = 15
    samurai.kenatsu = 0
    samurai.max_kenatsu = 100

    return samurai


@pytest.fixture
def enemy():
    """테스트용 적 생성"""
    enemy = Enemy("고블린", level=1)
    enemy.current_hp = 100
    enemy.max_hp = 100
    enemy.current_brv = 0
    enemy.max_brv = 9999
    return enemy


def test_kenshin_counter_system(samurai):
    """반격 시스템 테스트"""
    # 초기 상태
    assert samurai.observation == 0
    assert samurai.kenatsu == 0

    # 피격 시 반격 적용
    damage = 50
    reduced, reflected = GimmickUpdater._apply_kenshin_counter(samurai, damage, None)

    # 초심 단계: 10% 감소, 30% 반사
    assert reduced == 45  # 50 * 0.9
    assert reflected == 15  # 50 * 0.3
    assert samurai.observation >= 1  # 관찰 스택 증가
    assert samurai.kenatsu >= 5  # 검압 증가


def test_kenshin_stages(samurai):
    """관찰 단계 테스트 (초심/무심/검성)"""
    # 초심 (0-4)
    samurai.observation = 3
    stage = GimmickUpdater._get_kenshin_stage(samurai)
    assert stage == "초심(初心)"
    damage_reduction, counter_rate = GimmickUpdater._get_kenshin_counter_values(samurai)
    assert damage_reduction == 0.10
    assert counter_rate == 0.3

    # 무심 (5-9)
    samurai.observation = 7
    stage = GimmickUpdater._get_kenshin_stage(samurai)
    assert stage == "무심(無心)"
    damage_reduction, counter_rate = GimmickUpdater._get_kenshin_counter_values(samurai)
    assert damage_reduction == 0.20
    assert counter_rate == 0.5

    # 검성 (10+)
    samurai.observation = 12
    stage = GimmickUpdater._get_kenshin_stage(samurai)
    assert stage == "검성(剣聖)"
    damage_reduction, counter_rate = GimmickUpdater._get_kenshin_counter_values(samurai)
    assert damage_reduction == 0.35
    assert counter_rate == 0.8


def test_turn_end_observation_decay(samurai):
    """턴 종료 시 관찰 스택 감소 테스트"""
    samurai.observation = 10

    GimmickUpdater._update_kenshin_system_turn_end(samurai)

    assert samurai.observation == 9  # -1 감소


def test_brv_steal(samurai, enemy):
    """BRV 흡수 테스트"""
    # 적 BRV 설정
    enemy.current_brv = 1000

    # 무심 상태 (흡수율 60%)
    samurai.observation = 7

    # 미키리 스킬 메타데이터
    class MockSkill:
        metadata = {
            "steal_rate_base": 0.5,
            "steal_rate_mushin": 0.6,
            "steal_rate_kensei": 0.8,
        }

    context = {'target': enemy}
    GimmickUpdater._apply_kenshin_brv_steal(samurai, MockSkill(), context)

    # 60% 흡수 확인
    assert samurai.current_brv == 600
    assert enemy.current_brv == 400


def test_prediction_system(samurai):
    """요미 스킬 - 적 행동 예측 테스트"""
    # 테스트용 적
    enemy1 = Enemy("적1", level=1)
    enemy1.is_alive = True
    enemy1.current_brv = 5000  # BRV 높음 → HP 공격 예상
    enemy1.max_brv = 9999
    enemy1.current_hp = 100
    enemy1.max_hp = 100
    enemy1.atb_gauge = 800
    enemy1.atb_threshold = 1000

    # 요미 스킬
    class MockSkill:
        metadata = {
            "prediction": True,
            "prediction_turns": 2
        }

    context = {'enemies': [enemy1]}
    GimmickUpdater._apply_kenshin_prediction(samurai, MockSkill(), context)

    # 예측 결과 확인
    assert hasattr(samurai, 'predicted_actions')
    assert enemy1.name in samurai.predicted_actions

    prediction = samurai.predicted_actions[enemy1.name]
    assert prediction['action'] == "HP 공격 예정"
    assert prediction['atb_percentage'] == 80
    assert samurai.prediction_active == True


def test_observation_max_limit(samurai):
    """관찰 스택 최대값 15 제한 테스트"""
    samurai.observation = 14
    samurai.max_observation = 15

    # 피격으로 관찰 증가
    GimmickUpdater._apply_kenshin_counter(samurai, 100, None)

    # 최대 15로 제한
    assert samurai.observation <= 15


def test_kenatsu_max_limit(samurai):
    """검압 게이지 최대값 100 제한 테스트"""
    samurai.kenatsu = 95
    samurai.max_kenatsu = 100

    # 피격으로 검압 증가
    GimmickUpdater._apply_kenshin_counter(samurai, 100, None)

    # 최대 100으로 제한
    assert samurai.kenatsu <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
