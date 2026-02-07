# Testing Expert Skill

Dawn of Stellar 테스트 작성 및 디버깅 전문 스킬

## 테스트 구조
```
tests/
├── conftest.py              — 공통 fixtures
├── unit/
│   ├── combat/              — 전투 유닛 테스트
│   └── tutorial/            — 튜토리얼 유닛 테스트
├── integration/
│   └── test_combat_flow.py  — 전투 통합 테스트
├── test_*.py                — 기능별 테스트 (41개+)
└── run_multiplayer_tests.py — 멀티플레이어 전용
```

## 테스트 명령어
```bash
# 전체 테스트
pytest tests/ -ra -q --strict-markers

# 빠른 테스트 (slow 제외)
pytest tests/ -m "not slow" -q

# 특정 키워드
pytest tests/ -k "damage" -x -v

# 커버리지
pytest tests/ --cov=src --cov-report=term-missing

# 상세 에러 출력
pytest tests/ -x -v --tb=long

# 멀티플레이어
python tests/run_multiplayer_tests.py
```

## Pytest 설정 (pyproject.toml)
- `addopts`: `-ra -q --strict-markers`
- `testpaths`: `["tests"]`
- markers: `slow`, `integration`, `unit`
- 타입 힌트 검사 완화 (tests에서는 untyped 허용)

## 테스트 작성 패턴

### 스킬 테스트
```python
import pytest
from unittest.mock import MagicMock

def test_skill_damage():
    """스킬 데미지 계산 검증"""
    # Setup
    skill = create_test_skill(multiplier=2.5, stat_base="strength")
    user = create_test_character(physical_attack=50)
    target = create_test_character(physical_defense=20)
    
    # Execute
    result = skill.execute(user=user, target=target)
    
    # Verify
    assert result.damage > 0
    assert result.damage == (50 * 2.5 - 20)  # 예상 데미지

def test_skill_mp_cost():
    """MP 부족 시 스킬 사용 불가"""
    skill = create_test_skill(mp_cost=50)
    user = create_test_character(mp=10)
    assert not skill.can_use(user)
```

### 기믹 테스트
```python
def test_gimmick_initialization():
    """기믹 초기화 검증"""
    char = create_test_character(job="gladiator")
    gimmick = GimmickUpdater()
    gimmick.initialize(char)
    assert char.gimmick_data["cheer"] == 0

def test_gimmick_demand_fulfill():
    """기믹 요구 충족 검증"""
    char = create_test_character(job="gladiator")
    context = {"action_type": "kill", "target_id": "enemy_1"}
    result = gimmick.check_demand_fulfillment(char, context)
    assert result.fulfilled is True
```

### 데미지 계산 테스트
```python
def test_damage_formula():
    """데미지 공식 검증: atk / (def + 1) * multiplier"""
    calc = DamageCalculator()
    # stat_modifier = 50 / (20 + 1) ≈ 2.38
    # base_damage = max(1, int(2.38 * 2.0)) = 4
    damage = calc.calculate_brv_damage(
        attacker=mock_char(physical_attack=50),
        defender=mock_char(physical_defense=20),
        skill_multiplier=2.0,
    )
    assert damage.final_damage > 0

def test_damage_minimum_one():
    """데미지가 최소 1 이상인지"""
    damage = calc.calculate_brv_damage(
        attacker=mock_char(physical_attack=10),
        defender=mock_char(physical_defense=999),
        skill_multiplier=1.0,
    )
    assert damage.final_damage >= 1
```

## 회귀 테스트 추가 가이드
버그 수정 시 반드시:
1. 버그를 재현하는 테스트를 먼저 작성
2. 테스트가 실패하는 것을 확인
3. 수정 적용
4. 테스트가 통과하는 것을 확인
5. 기존 테스트가 모두 통과하는지 확인
