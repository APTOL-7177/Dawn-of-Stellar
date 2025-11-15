"""
Pytest 공통 설정 및 Fixture
"""

import pytest
from src.core.config import initialize_config


@pytest.fixture(scope="session", autouse=True)
def setup_config():
    """테스트 세션 전체에서 사용할 설정 초기화"""
    initialize_config()
    yield


@pytest.fixture(autouse=True)
def reset_systems():
    """각 테스트 전후로 시스템 초기화"""
    yield

    # 전역 시스템 리셋
    from src.combat import atb_system, brave_system, damage_calculator

    # ATB 시스템 리셋
    if atb_system._atb_system is not None:
        atb_system._atb_system.clear()
        atb_system._atb_system = None

    # Brave 시스템 리셋
    brave_system._brave_system = None

    # Damage Calculator 리셋
    damage_calculator._damage_calculator = None
