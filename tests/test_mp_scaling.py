"""MP 비용 레벨 스케일링 테스트"""
import sys
sys.path.insert(0, '.')

from src.character.skills.costs.mp_cost import MPCost

class MockUser:
    def __init__(self, level):
        self.level = level
        self.current_mp = 1000
        self.name = "테스트"
        self.active_traits = []

# 테스트
cost = MPCost(10)  # 기본 10 MP

print("\n=== MP 레벨 스케일링 테스트 ===")
print(f"기본 MP: 10, 1.5배 보정 = 15")
print()

for level in [1, 5, 10, 20]:
    user = MockUser(level)
    actual = cost._calculate_actual_cost(user, {})
    expected = 15 * (1.0 + (level - 1) * 0.10) if level > 1 else 15
    print(f"레벨 {level:2d}: {actual:5.0f} MP (예상: {expected:.0f})")

print("\n[OK] MP 레벨 스케일링 테스트 완료!")
