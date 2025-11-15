"""
누락된 gimmick 정의를 YAML에 추가하는 스크립트
"""

import yaml
from pathlib import Path
from typing import Dict, Any

# 각 직업의 gimmick 정의 (스킬 분석 결과 기반)
GIMMICK_DEFINITIONS = {
    'alchemist': {
        'type': 'potion_system',
        'name': '포션 제조',
        'description': '전투 중 포션을 제조하여 사용하는 시스템',
        'max_stock': 10
    },
    'archer': {
        'type': 'aim_system',
        'name': '조준 시스템',
        'description': '조준 포인트를 쌓아 정확한 공격',
        'max_aim': 5
    },
    'assassin': {
        'type': 'stealth_system',
        'name': '은신 시스템',
        'description': '은신 포인트를 쌓아 치명적인 공격',
        'max_stealth': 5
    },
    'bard': {
        'type': 'melody_system',
        'name': '음표 시스템',
        'description': '음표를 조합하여 다양한 효과의 멜로디 연주',
        'max_melody': 7
    },
    'battle_mage': {
        'type': 'rune_system',
        'name': '룬 각인',
        'description': '룬 스택을 쌓아 마법과 무술을 융합',
        'max_runes': 10
    },
    'berserker': {
        'type': 'rage_system',
        'name': '분노 시스템',
        'description': '분노를 축적하여 강력한 공격력 획득',
        'max_rage': 10
    },
    'cleric': {
        'type': 'faith_system',
        'name': '신앙 포인트',
        'description': '신앙심으로 치유와 버프 강화',
        'max_faith': 100
    },
    'dark_knight': {
        'type': 'darkness_system',
        'name': '어둠의 힘',
        'description': 'HP를 소모해 어둠의 힘을 얻음',
        'max_darkness': 100
    },
    'dimensionist': {
        'type': 'dimension_system',
        'name': '차원 포인트',
        'description': '차원의 힘을 조작하여 공간 왜곡',
        'max_points': 7
    },
    'dragon_knight': {
        'type': 'dragon_power',
        'name': '용의 힘',
        'description': '용의 힘을 축적하여 드래곤 변신',
        'max_power': 100
    },
    'druid': {
        'type': 'nature_system',
        'name': '자연의 힘',
        'description': '자연 포인트로 동물 변신 및 치유',
        'max_nature': 5
    },
    'engineer': {
        'type': 'machine_system',
        'name': '기계 부품',
        'description': '부품을 수집하여 기계 장치 제작',
        'max_parts': 15
    },
    'gladiator': {
        'type': 'arena_system',
        'name': '투기장 시스템',
        'description': '영광 포인트와 킬카운트로 전투력 상승',
        'max_points': 20
    },
    'hacker': {
        'type': 'hack_system',
        'name': '해킹 시스템',
        'description': '해킹 스택으로 적 디버프',
        'max_hacks': 10
    },
    'knight': {
        'type': 'duty_system',
        'name': '기사도',
        'description': '의무 스택으로 방어 및 아군 보호',
        'max_duty': 5
    },
    'monk': {
        'type': 'ki_system',
        'name': '기 에너지',
        'description': '차크라와 콤보로 연속 공격',
        'max_ki': 100
    },
    'necromancer': {
        'type': 'necro_system',
        'name': '시체 조종',
        'description': '시체와 미니언으로 전투',
        'max_necro': 50
    },
    'paladin': {
        'type': 'holy_power',
        'name': '성스러운 힘',
        'description': '성스러운 힘으로 악을 응징',
        'max_power': 100
    },
    'philosopher': {
        'type': 'knowledge_system',
        'name': '지식 스택',
        'description': '지식을 쌓아 논리 공격',
        'max_knowledge': 10
    },
    'pirate': {
        'type': 'gold_system',
        'name': '골드 시스템',
        'description': '골드를 소모하여 강력한 공격',
        'max_gold': 9999
    },
    'priest': {
        'type': 'judgment_system',
        'name': '심판 포인트',
        'description': '심판 포인트로 치유와 공격',
        'max_judgment': 7
    },
    'rogue': {
        'type': 'venom_system',
        'name': '독과 절도',
        'description': '독 데미지와 아이템 절도',
        'max_venom': 200
    },
    'samurai': {
        'type': 'will_system',
        'name': '의지 게이지',
        'description': '의지를 모아 강력한 일격',
        'max_will': 100
    },
    'shaman': {
        'type': 'curse_system',
        'name': '저주 스택',
        'description': '저주를 쌓아 적 약화',
        'max_curse': 10
    },
    'sniper': {
        'type': 'focus_system',
        'name': '집중력',
        'description': '집중 스택으로 정확도 증가',
        'max_focus': 5
    },
    'spellblade': {
        'type': 'mana_blade',
        'name': '마나 블레이드',
        'description': '마나를 검에 담아 마검 생성',
        'max_mana': 100
    },
    'sword_saint': {
        'type': 'sword_aura',
        'name': '검기',
        'description': '검기를 모아 초월적 검술 구사',
        'max_aura': 5
    },
    'time_mage': {
        'type': 'time_system',
        'name': '시간 포인트',
        'description': '시간 기록점으로 시간 조작',
        'max_marks': 7
    },
    'vampire': {
        'type': 'blood_system',
        'name': '혈액 풀',
        'description': '피를 흡수하여 생명력 강화',
        'max_blood': 200
    }
}


def add_gimmick_to_yaml(yaml_path: Path, gimmick_def: Dict[str, Any]) -> bool:
    """YAML 파일에 gimmick 추가"""
    try:
        # YAML 로드
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 이미 gimmick이 있는지 확인
        if 'gimmick' in data and data['gimmick']:
            print(f"  ⚠ {yaml_path.stem}: 이미 gimmick 정의 있음, 건너뜀")
            return False

        # gimmick 추가
        data['gimmick'] = gimmick_def

        # YAML 저장 (한글 유지)
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"  ✓ {yaml_path.stem}: gimmick '{gimmick_def['type']}' 추가 완료")
        return True

    except Exception as e:
        print(f"  ✗ {yaml_path.stem}: 오류 발생 - {e}")
        return False


def main():
    """메인 함수"""
    project_root = Path(__file__).parent.parent
    char_dir = project_root / "data" / "characters"

    print("=" * 80)
    print("누락된 Gimmick 정의 추가 중...")
    print("=" * 80)
    print()

    success_count = 0
    skip_count = 0
    error_count = 0

    for job_id, gimmick_def in sorted(GIMMICK_DEFINITIONS.items()):
        yaml_path = char_dir / f"{job_id}.yaml"

        if not yaml_path.exists():
            print(f"  ✗ {job_id}: YAML 파일 없음")
            error_count += 1
            continue

        result = add_gimmick_to_yaml(yaml_path, gimmick_def)

        if result:
            success_count += 1
        else:
            skip_count += 1

    print()
    print("=" * 80)
    print(f"작업 완료: 성공 {success_count}개, 건너뜀 {skip_count}개, 오류 {error_count}개")
    print("=" * 80)


if __name__ == "__main__":
    main()
