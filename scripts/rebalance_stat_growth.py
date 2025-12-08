"""
스탯 성장량 재조정 스크립트

성기사를 기준으로 모든 직업의 스탯 성장량을 재구성합니다.
각 직업의 아키타입에 맞게 중요한 스탯은 높게, 덜 중요한 스탯은 낮게 조정합니다.
"""

import yaml
from pathlib import Path

# 성기사 스탯 (기준)
PALADIN_STATS = {
    'hp': {'base': 197, 'growth': 46},
    'mp': {'base': 67, 'growth': 4.5},
    'init_brv': {'base': 138, 'growth': 32.6},
    'strength': {'base': 67, 'growth': 16.7},
    'defense': {'base': 76, 'growth': 19.8},
    'magic': {'base': 38, 'growth': 9.0},
    'spirit': {'base': 79, 'growth': 20.2},
    'speed': {'base': 43, 'growth': 10.1},
    'max_brv': {'base': 495, 'growth': 139.0},
}

# 성기사의 성장 비율 계산
PALADIN_RATIOS = {
    stat: data['growth'] / data['base']
    for stat, data in PALADIN_STATS.items()
}

print("=== 성기사 성장 비율 ===")
for stat, ratio in PALADIN_RATIOS.items():
    print(f"{stat}: {ratio:.4f}")

# 직업별 중요 스탯 정의 (높은 성장 = 1.15, 보통 = 1.0, 낮은 성장 = 0.85)
ARCHETYPE_STAT_WEIGHTS = {
    # 물리 딜러
    'warrior': {'strength': 1.15, 'hp': 1.1, 'defense': 1.0, 'speed': 1.05, 'magic': 0.85, 'spirit': 0.9},
    'berserker': {'strength': 1.15, 'hp': 1.0, 'defense': 0.85, 'speed': 1.05, 'magic': 0.85, 'spirit': 0.85},
    'assassin': {'strength': 1.15, 'speed': 1.15, 'hp': 0.9, 'defense': 0.85, 'magic': 0.85, 'spirit': 0.85},
    'rogue': {'strength': 1.1, 'speed': 1.15, 'hp': 0.95, 'defense': 0.9, 'magic': 0.85, 'spirit': 0.9},
    'archer': {'strength': 1.1, 'speed': 1.1, 'hp': 0.9, 'defense': 0.85, 'magic': 0.9, 'spirit': 0.9},
    'sniper': {'strength': 1.15, 'speed': 1.1, 'hp': 0.85, 'defense': 0.85, 'magic': 0.85, 'spirit': 0.85},
    'sword_saint': {'strength': 1.15, 'speed': 1.1, 'hp': 1.05, 'defense': 1.0, 'magic': 0.9, 'spirit': 0.9},
    'samurai': {'strength': 1.15, 'speed': 1.05, 'hp': 1.05, 'defense': 1.0, 'magic': 0.85, 'spirit': 0.9},
    'gladiator': {'strength': 1.15, 'hp': 1.1, 'defense': 1.0, 'speed': 1.0, 'magic': 0.85, 'spirit': 0.9},
    'pirate': {'strength': 1.1, 'speed': 1.1, 'hp': 1.0, 'defense': 0.95, 'magic': 0.85, 'spirit': 0.85},
    'breaker': {'strength': 1.15, 'hp': 1.05, 'defense': 1.0, 'speed': 0.9, 'magic': 0.85, 'spirit': 0.9},
    'dragon_knight': {'strength': 1.15, 'hp': 1.1, 'defense': 1.05, 'speed': 1.0, 'magic': 0.9, 'spirit': 0.95},

    # 마법 딜러
    'magician': {'magic': 1.15, 'mp': 1.15, 'hp': 0.85, 'defense': 0.85, 'spirit': 1.0, 'speed': 1.0},
    'archmage': {'magic': 1.15, 'mp': 1.15, 'hp': 0.85, 'defense': 0.85, 'spirit': 1.05, 'speed': 0.95},
    'battle_mage': {'magic': 1.1, 'strength': 1.05, 'mp': 1.1, 'hp': 0.95, 'defense': 0.9, 'spirit': 0.95, 'speed': 1.05},
    'spellblade': {'magic': 1.1, 'strength': 1.1, 'mp': 1.05, 'hp': 1.0, 'defense': 0.95, 'spirit': 0.95, 'speed': 1.05},
    'elementalist': {'magic': 1.15, 'mp': 1.1, 'hp': 0.9, 'defense': 0.85, 'spirit': 1.0, 'speed': 1.0},
    'time_mage': {'magic': 1.15, 'mp': 1.15, 'hp': 0.85, 'defense': 0.85, 'spirit': 1.0, 'speed': 1.1},
    'necromancer': {'magic': 1.15, 'mp': 1.1, 'hp': 0.9, 'defense': 0.85, 'spirit': 1.0, 'speed': 0.95},
    'dark_knight': {'strength': 1.1, 'magic': 1.1, 'hp': 1.0, 'defense': 0.95, 'spirit': 0.95, 'mp': 1.05, 'speed': 1.0},
    'illusionist': {'magic': 1.1, 'mp': 1.1, 'hp': 0.85, 'defense': 0.85, 'spirit': 0.95, 'speed': 1.15},
    'dimensionist': {'magic': 1.15, 'mp': 1.15, 'hp': 0.85, 'defense': 0.85, 'spirit': 1.15, 'speed': 1.0},

    # 탱커
    'knight': {'defense': 1.15, 'hp': 1.15, 'spirit': 1.05, 'strength': 1.0, 'magic': 0.85, 'speed': 0.85},
    'paladin': {'defense': 1.15, 'spirit': 1.15, 'hp': 1.1, 'strength': 1.0, 'magic': 0.9, 'mp': 1.0, 'speed': 0.9},

    # 서포터/힐러
    'cleric': {'spirit': 1.15, 'mp': 1.15, 'hp': 0.95, 'defense': 1.0, 'magic': 1.05, 'strength': 0.85, 'speed': 0.95},
    'priest': {'spirit': 1.15, 'mp': 1.15, 'hp': 0.9, 'defense': 0.95, 'magic': 1.05, 'strength': 0.85, 'speed': 0.9},
    'druid': {'spirit': 1.1, 'magic': 1.1, 'mp': 1.1, 'hp': 1.0, 'defense': 0.95, 'strength': 0.85, 'speed': 0.95},
    'bard': {'spirit': 1.05, 'mp': 1.15, 'speed': 1.1, 'hp': 0.9, 'defense': 0.85, 'magic': 1.0, 'strength': 0.85},
    'shaman': {'spirit': 1.15, 'magic': 1.1, 'mp': 1.1, 'hp': 0.95, 'defense': 0.9, 'strength': 0.85, 'speed': 0.95},

    # 하이브리드
    'monk': {'strength': 1.1, 'spirit': 1.1, 'hp': 1.05, 'defense': 1.0, 'speed': 1.1, 'magic': 0.85, 'mp': 0.9},
    'alchemist': {'magic': 1.05, 'mp': 1.1, 'hp': 0.95, 'defense': 0.9, 'spirit': 1.0, 'strength': 0.9, 'speed': 1.0},
    'engineer': {'strength': 1.05, 'magic': 1.05, 'mp': 1.05, 'hp': 1.0, 'defense': 1.0, 'spirit': 0.95, 'speed': 0.95},
    'hacker': {'magic': 1.1, 'speed': 1.15, 'mp': 1.1, 'hp': 0.85, 'defense': 0.85, 'spirit': 0.95, 'strength': 0.85},
    'philosopher': {'spirit': 1.1, 'magic': 1.1, 'mp': 1.15, 'hp': 0.9, 'defense': 0.9, 'strength': 0.85, 'speed': 0.95},
    'vampire': {'strength': 1.1, 'magic': 1.05, 'hp': 1.0, 'defense': 0.95, 'spirit': 0.9, 'mp': 1.05, 'speed': 1.1},  # 흡혈귀
}

def rebalance_character(char_file: Path):
    """캐릭터 파일의 스탯 성장량을 재조정"""
    with open(char_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    class_name = data.get('class_name', '')
    job_id = char_file.stem

    # 중요 스탯 가중치 가져오기
    weights = ARCHETYPE_STAT_WEIGHTS.get(job_id, {})

    if not weights:
        print(f"[WARN] {class_name} ({job_id}): 가중치 미정의, 스킵")
        return

    # 기본 스탯 가져오기
    base_stats = data.get('base_stats', {})

    # 새로운 성장량 계산
    new_growth = {}
    for stat in ['hp', 'mp', 'init_brv', 'strength', 'defense', 'magic', 'spirit', 'speed', 'max_brv']:
        base_value = base_stats.get(stat)
        if base_value is None:
            # physical_attack -> strength 등 매핑
            if stat == 'strength':
                base_value = base_stats.get('physical_attack')
            elif stat == 'defense':
                base_value = base_stats.get('physical_defense')
            elif stat == 'magic':
                base_value = base_stats.get('magic_attack')
            elif stat == 'spirit':
                base_value = base_stats.get('magic_defense')

        if base_value is None:
            continue

        # 성기사 비율 적용
        base_ratio = PALADIN_RATIOS.get(stat, 0.25)

        # 가중치 적용
        weight = weights.get(stat, 1.0)

        # 최종 성장량 = base_value * base_ratio * weight
        growth = round(base_value * base_ratio * weight, 1)

        new_growth[stat] = growth

    # luck, accuracy, evasion은 고정값 유지
    if 'stat_growth' in data:
        new_growth['luck'] = data['stat_growth'].get('luck', 3.0)
        new_growth['accuracy'] = data['stat_growth'].get('accuracy', 1.6)
        new_growth['evasion'] = data['stat_growth'].get('evasion', 1.2)

    # 업데이트
    data['stat_growth'] = new_growth

    # 파일 저장
    with open(char_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"[OK] {class_name} ({job_id}): 스탯 성장량 재조정 완료")

def main():
    """모든 캐릭터 파일 처리"""
    char_dir = Path('data/characters')

    for char_file in sorted(char_dir.glob('*.yaml')):
        try:
            rebalance_character(char_file)
        except Exception as e:
            print(f"[ERROR] {char_file.name}: 오류 - {e}")

    print("\n=== 재조정 완료 ===")

if __name__ == '__main__':
    main()
