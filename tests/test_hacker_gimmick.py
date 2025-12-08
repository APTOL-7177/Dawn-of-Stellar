import pytest

from src.character.character import Character
from src.character.gimmick_updater import GimmickUpdater
from src.character.skills.skill_manager import SkillManager
from src.character.skills.job_skills.hacker_skills import register_hacker_skills
from src.character.skills.yaml_skill_loader import load_yaml_skills


class DummyTarget:
    def __init__(self):
        self.name = "더미"
        self.is_alive = True
        self.max_hp = 1000
        self.current_hp = 1000
        self.intrusion_gauge = 0


@pytest.fixture(scope="module")
def skill_manager():
    manager = SkillManager()
    register_hacker_skills(manager)
    load_yaml_skills(manager)
    return manager


@pytest.fixture
def hacker():
    return Character("해커", "hacker")


def test_ram_cost_python_skill(skill_manager, hacker):
    target = DummyTarget()
    hacker.ram = 10
    result = skill_manager.execute_skill("hacker_code_injection", hacker, target)
    assert result.success
    assert hacker.ram == 7  # ram_cost 3 적용


def test_ram_cost_yaml_skill(skill_manager, hacker):
    target = DummyTarget()
    hacker.ram = 10
    result = skill_manager.execute_skill("port_scan", hacker, target)
    assert result.success
    assert hacker.ram == 6  # costs.ram 4 적용


def test_overclock_toggle_and_upkeep(skill_manager, hacker):
    # 오버클럭 켜기
    hacker.ram = 8
    # 유지비를 명확히 보기 위해 비용 상향
    hacker.overclock_data["ram_cost_per_turn"] = 6
    hacker.overclock_data["ram_regen_bonus"] = 1
    result = skill_manager.execute_skill("overclock_mode", hacker, hacker)
    assert result.success
    assert hacker.overclock_active
    assert hacker.status_manager.has_buff("overclock")

    # 턴 시작 처리로 RAM 소모 확인 (기본 회복 3 + 보너스 1, 비용 6 → 순감소 2)
    GimmickUpdater.on_turn_start(hacker)
    assert hacker.ram == 6  # 8 +4 -6

    # 토글로 오버클럭 종료 시 버프/플래그 해제
    skill_manager.execute_skill("overclock_mode", hacker, hacker)
    assert not hacker.overclock_active
    assert not hacker.status_manager.has_buff("overclock")
