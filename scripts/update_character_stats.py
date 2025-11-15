"""
28개 직업 스탯을 원본 데이터에 맞춰 업데이트하는 스크립트
"""
import yaml
import os

# 원본 스탯 데이터 (character.py 2062-2091줄에서 추출)
ORIGINAL_STATS = {
    "전사": {"hp": 210, "p_atk": 60, "m_atk": 40, "p_def": 60, "m_def": 60, "speed": 60, "mp": 32},
    "아크메이지": {"hp": 121, "p_atk": 43, "m_atk": 78, "p_def": 33, "m_def": 67, "speed": 58, "mp": 89},
    "궁수": {"hp": 164, "p_atk": 74, "m_atk": 33, "p_def": 44, "m_def": 43, "speed": 68, "mp": 45},
    "도적": {"hp": 150, "p_atk": 64, "m_atk": 38, "p_def": 43, "m_def": 49, "speed": 93, "mp": 41},
    "성기사": {"hp": 197, "p_atk": 67, "m_atk": 38, "p_def": 76, "m_def": 62, "speed": 43, "mp": 67},
    "암흑기사": {"hp": 189, "p_atk": 71, "m_atk": 54, "p_def": 58, "m_def": 51, "speed": 52, "mp": 53},
    "몽크": {"hp": 172, "p_atk": 82, "m_atk": 51, "p_def": 59, "m_def": 64, "speed": 76, "mp": 58},
    "바드": {"hp": 107, "p_atk": 43, "m_atk": 66, "p_def": 38, "m_def": 58, "speed": 69, "mp": 73},
    "네크로맨서": {"hp": 134, "p_atk": 44, "m_atk": 84, "p_def": 39, "m_def": 74, "speed": 48, "mp": 84},
    "용기사": {"hp": 181, "p_atk": 78, "m_atk": 62, "p_def": 67, "m_def": 58, "speed": 61, "mp": 48},
    "검성": {"hp": 164, "p_atk": 83, "m_atk": 31, "p_def": 51, "m_def": 47, "speed": 71, "mp": 39},
    "정령술사": {"hp": 107, "p_atk": 49, "m_atk": 85, "p_def": 42, "m_def": 69, "speed": 59, "mp": 94},
    "암살자": {"hp": 134, "p_atk": 81, "m_atk": 28, "p_def": 34, "m_def": 39, "speed": 87, "mp": 35},
    "기계공학자": {"hp": 156, "p_atk": 63, "m_atk": 59, "p_def": 54, "m_def": 48, "speed": 53, "mp": 61},
    "무당": {"hp": 121, "p_atk": 48, "m_atk": 86, "p_def": 44, "m_def": 77, "speed": 64, "mp": 76},
    "해적": {"hp": 164, "p_atk": 74, "m_atk": 34, "p_def": 52, "m_def": 41, "speed": 77, "mp": 37},
    "사무라이": {"hp": 167, "p_atk": 74, "m_atk": 45, "p_def": 58, "m_def": 53, "speed": 67, "mp": 43},
    "드루이드": {"hp": 175, "p_atk": 53, "m_atk": 81, "p_def": 48, "m_def": 69, "speed": 59, "mp": 71},
    "철학자": {"hp": 107, "p_atk": 38, "m_atk": 76, "p_def": 54, "m_def": 86, "speed": 49, "mp": 97},
    "시간술사": {"hp": 121, "p_atk": 54, "m_atk": 77, "p_def": 49, "m_def": 64, "speed": 57, "mp": 103},
    "연금술사": {"hp": 135, "p_atk": 59, "m_atk": 72, "p_def": 44, "m_def": 58, "speed": 54, "mp": 69},
    "검투사": {"hp": 172, "p_atk": 79, "m_atk": 41, "p_def": 56, "m_def": 48, "speed": 64, "mp": 29},
    "기사": {"hp": 216, "p_atk": 79, "m_atk": 46, "p_def": 72, "m_def": 54, "speed": 48, "mp": 34},
    "신관": {"hp": 143, "p_atk": 42, "m_atk": 79, "p_def": 57, "m_def": 89, "speed": 52, "mp": 81},
    "마검사": {"hp": 164, "p_atk": 67, "m_atk": 70, "p_def": 54, "m_def": 61, "speed": 58, "mp": 62},
    "차원술사": {"hp": 84, "p_atk": 33, "m_atk": 88, "p_def": 28, "m_def": 72, "speed": 47, "mp": 91},
    "광전사": {"hp": 327, "p_atk": 64, "m_atk": 13, "p_def": 22, "m_def": 21, "speed": 74, "mp": 22},
    "마법사": {"hp": 121, "p_atk": 43, "m_atk": 78, "p_def": 33, "m_def": 67, "speed": 58, "mp": 86},
}

# 파일명 매핑 (한글 → 영문)
FILENAME_MAP = {
    "전사": "warrior",
    "아크메이지": "archmage",
    "궁수": "archer",
    "도적": "rogue",
    "성기사": "paladin",
    "암흑기사": "dark_knight",
    "몽크": "monk",
    "바드": "bard",
    "네크로맨서": "necromancer",
    "용기사": "dragon_knight",
    "검성": "sword_saint",
    "정령술사": "elementalist",
    "암살자": "assassin",
    "기계공학자": "engineer",
    "무당": "shaman",
    "해적": "pirate",
    "사무라이": "samurai",
    "드루이드": "druid",
    "철학자": "philosopher",
    "시간술사": "time_mage",
    "연금술사": "alchemist",
    "검투사": "gladiator",
    "기사": "knight",
    "신관": "priest",
    "마검사": "spellblade",
    "차원술사": "dimensionist",
    "광전사": "berserker",
    "마법사": "mage",
}

def update_character_yaml(class_name: str, stats: dict):
    """YAML 파일의 스탯을 업데이트"""
    filename = FILENAME_MAP.get(class_name)
    if not filename:
        print(f"[WARN] {class_name}: No filename mapping")
        return

    filepath = f"X:/Dos/data/characters/{filename}.yaml"

    if not os.path.exists(filepath):
        print(f"[WARN] {class_name}: File not found ({filepath})")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 스탯 업데이트
        if 'base_stats' in data:
            data['base_stats']['hp'] = stats['hp']
            data['base_stats']['mp'] = stats['mp']
            data['base_stats']['physical_attack'] = stats['p_atk']
            data['base_stats']['physical_defense'] = stats['p_def']
            data['base_stats']['magic_attack'] = stats['m_atk']
            data['base_stats']['magic_defense'] = stats['m_def']
            data['base_stats']['speed'] = stats['speed']

            # 불필요한 필드 제거
            data['base_stats'].pop('strength', None)
            data['base_stats'].pop('defense', None)
            data['base_stats'].pop('magic', None)
            data['base_stats'].pop('spirit', None)
            data['base_stats'].pop('luck', None)
            data['base_stats'].pop('accuracy', None)
            data['base_stats'].pop('evasion', None)

        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"[OK] {class_name} ({filename}.yaml) updated")

    except Exception as e:
        print(f"[ERROR] {class_name}: {e}")

def main():
    """모든 직업 업데이트"""
    print("=" * 60)
    print("Updating 28 character stats...")
    print("=" * 60)

    for class_name, stats in ORIGINAL_STATS.items():
        update_character_yaml(class_name, stats)

    print("=" * 60)
    print("Update complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
