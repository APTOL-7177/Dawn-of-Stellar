"""명중률 공식 테스트 (base=65, 플레이어 보너스 1배)"""
import math

def calculate_hit_rate(accuracy: int, evasion: int) -> float:
    """
    명중률 계산
    공식: 65% + 50 * log10(명중/회피)
    """
    ratio = accuracy / max(1, evasion)
    hit_rate = 65.0 + 50.0 * math.log10(ratio)
    # 30% ~ 98% 제한
    return max(30.0, min(98.0, hit_rate))

# 플레이어 기준 명중 = 50 (보너스 없음)
player_accuracy = 50

# 적 회피 분포 (가중치)
enemy_evasion_distribution = [
    (10, 0.20),   # 회피 10: 20% (저급 적)
    (20, 0.25),   # 회피 20: 25% (일반 적)
    (30, 0.20),   # 회피 30: 20% (중급 적)
    (50, 0.20),   # 회피 50: 20% (상급 적)
    (70, 0.10),   # 회피 70: 10% (보스급)
    (100, 0.03),  # 회피 100: 3% (고급 보스)
    (150, 0.02),  # 회피 150: 2% (최종 보스)
]

print("=" * 70)
print("명중률 공식 테스트 (Base=65%, 플레이어 보너스 1배)")
print("=" * 70)
print(f"플레이어 명중: {player_accuracy}")
print(f"공식: 65% + 50 * log10(명중 / 회피)")
print(f"상한선: 98%, 하한선: 30%")
print("-" * 70)

weighted_sum = 0.0
print(f"{'적 회피':<12} {'가중치':<10} {'명중률':<12} {'회피율'}")
print("-" * 70)

for evasion, weight in enemy_evasion_distribution:
    hit_rate = calculate_hit_rate(player_accuracy, evasion)
    dodge_rate = 100.0 - hit_rate
    weighted_sum += hit_rate * weight
    print(f"{evasion:<12} {weight*100:>6.1f}%    {hit_rate:>6.1f}%      {dodge_rate:>5.1f}%")

print("-" * 70)
print(f"가중 평균 명중률: {weighted_sum:.2f}%")
print("=" * 70)

# 극단적 케이스 테스트
print("\n극단적 케이스:")
print("-" * 70)
extreme_cases = [
    (50, 5, "매우 높은 명중 우위"),
    (50, 200, "매우 높은 회피 우위"),
    (50, 50, "동등한 명중/회피"),
    (100, 10, "고명중 vs 저회피"),
    (25, 100, "저명중 vs 고회피"),
]

for acc, eva, desc in extreme_cases:
    hit_rate = calculate_hit_rate(acc, eva)
    print(f"{desc:<20} (명중 {acc}, 회피 {eva}): {hit_rate:.1f}%")

print("=" * 70)
