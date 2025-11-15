"""
BRV 밸런스 조정 스크립트
- 1레벨 기준 init_brv: 120, max_brv: 455
- 직업별 특성에 따라 차별화
"""

import os
import yaml
from pathlib import Path

# 직업별 BRV 설정 (1레벨 기준)
BRV_CONFIG = {
    # 탱커형 (높은 BRV)
    "warrior": {"init_brv": 135, "max_brv": 490},
    "knight": {"init_brv": 130, "max_brv": 485},
    "paladin": {"init_brv": 138, "max_brv": 495},
    "gladiator": {"init_brv": 140, "max_brv": 500},
    "dark_knight": {"init_brv": 132, "max_brv": 488},
    "berserker": {"init_brv": 145, "max_brv": 505},  # 가장 높음 (리스크 보상)

    # 물리 딜러형 (중상 BRV)
    "samurai": {"init_brv": 125, "max_brv": 465},
    "sword_saint": {"init_brv": 128, "max_brv": 470},
    "dragon_knight": {"init_brv": 127, "max_brv": 468},
    "monk": {"init_brv": 122, "max_brv": 462},
    "breaker": {"init_brv": 130, "max_brv": 475},  # BRV 특화

    # 속도형 물리 딜러 (중간 BRV)
    "assassin": {"init_brv": 108, "max_brv": 440},
    "rogue": {"init_brv": 110, "max_brv": 442},

    # 원거리 물리 딜러 (중간 BRV)
    "archer": {"init_brv": 118, "max_brv": 455},
    "sniper": {"init_brv": 115, "max_brv": 450},
    "pirate": {"init_brv": 120, "max_brv": 458},

    # 마법 딜러형 (낮은 BRV)
    "mage": {"init_brv": 105, "max_brv": 435},
    "archmage": {"init_brv": 102, "max_brv": 430},
    "elementalist": {"init_brv": 108, "max_brv": 438},
    "time_mage": {"init_brv": 100, "max_brv": 425},
    "necromancer": {"init_brv": 103, "max_brv": 432},
    "dimensionist": {"init_brv": 98, "max_brv": 422},

    # 하이브리드 딜러 (중간 BRV)
    "spellblade": {"init_brv": 117, "max_brv": 453},
    "battle_mage": {"init_brv": 119, "max_brv": 456},

    # 지원/힐러형 (낮은 BRV)
    "cleric": {"init_brv": 112, "max_brv": 445},
    "priest": {"init_brv": 110, "max_brv": 443},
    "druid": {"init_brv": 115, "max_brv": 448},
    "shaman": {"init_brv": 107, "max_brv": 437},

    # 버퍼/디버퍼형 (낮은 BRV)
    "bard": {"init_brv": 106, "max_brv": 436},
    "hacker": {"init_brv": 95, "max_brv": 420},

    # 특수형 (역할에 따라)
    "alchemist": {"init_brv": 113, "max_brv": 446},
    "engineer": {"init_brv": 116, "max_brv": 451},
    "philosopher": {"init_brv": 104, "max_brv": 434},
    "vampire": {"init_brv": 121, "max_brv": 460},  # 생존 특화
}

def update_character_brv(file_path: Path):
    """캐릭터 파일의 BRV 값을 업데이트합니다."""
    character_id = file_path.stem

    if character_id not in BRV_CONFIG:
        print(f"[WARN] {character_id}: BRV 설정 없음 (건너뜀)")
        return

    # YAML 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # BRV 값 업데이트
    brv_config = BRV_CONFIG[character_id]

    if 'base_stats' not in data:
        data['base_stats'] = {}

    old_init_brv = data['base_stats'].get('init_brv', 'N/A')
    old_max_brv = data['base_stats'].get('max_brv', 'N/A')

    data['base_stats']['init_brv'] = brv_config['init_brv']
    data['base_stats']['max_brv'] = brv_config['max_brv']

    # stat_growth에 max_brv 성장률 추가 (init_brv의 약 60% 비율)
    if 'stat_growth' not in data:
        data['stat_growth'] = {}

    # init_brv 성장률 조정 (기존 값이 너무 높으면 줄임)
    if 'init_brv' in data['stat_growth']:
        old_growth = data['stat_growth']['init_brv']
        # 레벨당 3~5 정도로 조정
        new_growth = round(brv_config['init_brv'] * 0.035, 1)  # 약 3.5%
        data['stat_growth']['init_brv'] = new_growth
    else:
        data['stat_growth']['init_brv'] = round(brv_config['init_brv'] * 0.035, 1)

    # max_brv 성장률 추가 (init_brv 성장률의 약 60%)
    data['stat_growth']['max_brv'] = round(data['stat_growth']['init_brv'] * 0.6, 1)

    # YAML 파일 쓰기
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"[OK] {character_id:15s}: init_brv {old_init_brv:>4} -> {brv_config['init_brv']:>3}, "
          f"max_brv {old_max_brv:>4} -> {brv_config['max_brv']:>3}")

def main():
    """모든 캐릭터 파일의 BRV를 업데이트합니다."""
    characters_dir = Path(__file__).parent.parent / "data" / "characters"

    print("=" * 80)
    print("BRV 밸런스 조정 시작")
    print("=" * 80)
    print()

    yaml_files = sorted(characters_dir.glob("*.yaml"))

    for yaml_file in yaml_files:
        update_character_brv(yaml_file)

    print()
    print("=" * 80)
    print(f"[완료] {len(yaml_files)}개 캐릭터 업데이트")
    print("=" * 80)
    print()
    print("[BRV 범위 요약]")
    print(f"  - init_brv: {min(cfg['init_brv'] for cfg in BRV_CONFIG.values())} ~ "
          f"{max(cfg['init_brv'] for cfg in BRV_CONFIG.values())} (평균: 120)")
    print(f"  - max_brv:  {min(cfg['max_brv'] for cfg in BRV_CONFIG.values())} ~ "
          f"{max(cfg['max_brv'] for cfg in BRV_CONFIG.values())} (평균: 455)")

if __name__ == "__main__":
    main()
