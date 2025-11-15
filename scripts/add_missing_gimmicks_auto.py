#!/usr/bin/env python3
"""
누락된 gimmick 정의를 자동으로 YAML 파일에 추가하는 스크립트
"""

import yaml
from pathlib import Path
from typing import Dict, Any

# 직업별 기믹 정의
GIMMICK_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "berserker": {
        "type": "rage_system",
        "name": "광전사의 분노",
        "description": "전투 중 분노를 축적하여 강력한 공격 수행. HP가 낮을수록 분노 획득량 증가",
        "max_rage_stacks": 10
    },
    "gladiator": {
        "type": "arena_system",
        "name": "투기장의 영광",
        "description": "적을 처치하고 공격을 막아내며 영광 포인트 획득. 영광으로 강력한 기술 사용",
        "max_glory_points": 100
    },
    "dark_knight": {
        "type": "darkness_system",
        "name": "어둠의 힘",
        "description": "자신의 HP를 소모하여 어둠의 힘을 얻고 강력한 암흑 마법 사용",
        "max_darkness": 100
    },
    "knight": {
        "type": "duty_system",
        "name": "기사의 의무",
        "description": "아군을 보호하고 피해를 받으며 의무 스택 획득. 의무로 강력한 수호 기술 사용",
        "max_duty_stacks": 10
    },
    "paladin": {
        "type": "holy_system",
        "name": "성스러운 힘",
        "description": "적을 공격하고 아군을 치유하며 성력 획득. 성력으로 신성한 기술 사용",
        "max_holy_power": 100
    },
    "assassin": {
        "type": "stealth_system",
        "name": "은신 기술",
        "description": "은신 상태에서 치명적인 암살 기술 사용. 은신 포인트를 소모하여 강화",
        "max_stealth_points": 5
    },
    "rogue": {
        "type": "theft_system",
        "name": "절도와 회피",
        "description": "적의 아이템을 훔치고 회피 태세를 유지. 훔친 아이템으로 특수 기술 사용",
        "max_stolen_items": 10
    },
    "pirate": {
        "type": "plunder_system",
        "name": "약탈과 재물",
        "description": "전투에서 골드를 획득하고 소모하여 강력한 해적 기술 사용",
        "gold_per_hit": 10,
        "max_gold": 1000
    },
    "archer": {
        "type": "aim_system",
        "name": "정밀 조준",
        "description": "조준 포인트를 축적하여 치명적인 원거리 공격 수행",
        "max_aim_points": 5
    },
    "sniper": {
        "type": "aim_system",
        "name": "저격 집중",
        "description": "집중력을 높여 완벽한 저격 수행. 집중 스택에 비례한 데미지 증가",
        "max_focus_stacks": 5
    },
    "engineer": {
        "type": "construct_system",
        "name": "기계 부품",
        "description": "전투 중 기계 부품을 수집하여 포탑과 장치 제작",
        "max_machine_parts": 100
    },
    "monk": {
        "type": "ki_system",
        "name": "기 에너지",
        "description": "차크라를 개방하고 콤보를 쌓아 강력한 기공 기술 사용",
        "max_chakra_points": 7,
        "max_combo_count": 10
    },
    "samurai": {
        "type": "iaijutsu_system",
        "name": "거합의 도",
        "description": "의지를 집중하여 완벽한 발도 기술 수행. 의지 게이지로 특수 기술 사용",
        "max_will_gauge": 100
    },
    "sword_saint": {
        "type": "sword_aura",
        "name": "검기",
        "description": "검기를 축적하여 강력한 검술 사용. 검기는 공격 시 자동 획득",
        "max_sword_aura": 5
    },
    "dragon_knight": {
        "type": "dragon_marks",
        "name": "용의 각인",
        "description": "용의 힘을 축적하여 드래곤 브레스와 비상 기술 사용",
        "max_dragon_power": 100
    },
    "battle_mage": {
        "type": "rune_system",
        "name": "마법 룬",
        "description": "공격 시 룬을 각인하여 강력한 폭발 마법 발동",
        "max_rune_stacks": 5
    },
    "spellblade": {
        "type": "enchant_system",
        "name": "마력 부여",
        "description": "검에 마력을 부여하여 원소 속성 공격 수행",
        "max_mana_blade": 100
    },
    "necromancer": {
        "type": "necro_system",
        "name": "네크로 에너지",
        "description": "시체를 수집하고 언데드를 소환. 네크로 에너지로 강력한 주술 사용",
        "max_necro_energy": 100,
        "max_corpse_count": 10,
        "max_minion_count": 3
    },
    "time_mage": {
        "type": "time_system",
        "name": "시간 조작",
        "description": "시간 기록점을 생성하여 시간을 되돌리고 미래를 예측",
        "max_time_points": 5
    },
    "dimensionist": {
        "type": "dimension_system",
        "name": "차원 조작",
        "description": "차원의 틈을 열어 공간을 왜곡하고 차원 이동 수행",
        "max_dimension_points": 100
    },
    "priest": {
        "type": "divinity_system",
        "name": "심판의 권능",
        "description": "신의 심판을 내리고 치유하며 신성력 획득",
        "max_judgment_points": 100
    },
    "cleric": {
        "type": "divinity_system",
        "name": "신앙의 힘",
        "description": "신앙심으로 강력한 치유와 보호 마법 사용",
        "max_faith_points": 100
    },
    "bard": {
        "type": "melody_system",
        "name": "음악의 선율",
        "description": "음표를 모아 멜로디를 완성하고 강력한 버프 효과 발동",
        "max_melody_notes": 8,
        "octave_notes": ["도", "레", "미", "파", "솔", "라", "시", "도+"]
    },
    "druid": {
        "type": "shapeshifting_system",
        "name": "자연의 변신",
        "description": "자연의 힘을 모아 동물 형태로 변신. 형태마다 고유한 능력 보유",
        "max_nature_points": 100,
        "forms": ["bear", "panther", "eagle"]
    },
    "shaman": {
        "type": "totem_system",
        "name": "토템의 저주",
        "description": "토템을 설치하고 저주를 축적하여 강력한 주술 사용",
        "max_curse_stacks": 10
    },
    "vampire": {
        "type": "blood_system",
        "name": "혈액 마법",
        "description": "피를 흡수하여 블러드 풀을 채우고 강력한 흡혈 마법 사용",
        "max_blood_pool": 100,
        "lifesteal_base": 0.15
    },
    "alchemist": {
        "type": "alchemy_system",
        "name": "연금술 조합",
        "description": "포션을 조합하고 투척하여 다양한 효과 발동",
        "max_potion_stock": 10
    },
    "philosopher": {
        "type": "wisdom_system",
        "name": "지혜의 축적",
        "description": "전투 중 지식을 축적하여 현자의 돌의 힘 사용",
        "max_knowledge_stacks": 10
    },
    "hacker": {
        "type": "hack_system",
        "name": "시스템 해킹",
        "description": "적의 시스템을 해킹하고 디버프를 누적시켜 무력화",
        "max_hack_stacks": 5,
        "max_debuff_count": 10
    }
}


def add_gimmick_to_yaml(yaml_path: Path, gimmick_data: Dict[str, Any]) -> bool:
    """YAML 파일에 gimmick 정의를 추가합니다."""
    try:
        # YAML 파일 읽기
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 이미 gimmick이 있으면 건너뛰기
        if 'gimmick' in data:
            print(f"  [SKIP] 이미 gimmick이 있음: {yaml_path.stem}")
            return False

        # gimmick 추가 (skills 섹션 위에 추가)
        # YAML 파일을 텍스트로 다시 읽어서 수동 삽입
        with open(yaml_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # skills 라인 찾기
        skills_line_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('skills:'):
                skills_line_idx = i
                break

        if skills_line_idx is None:
            print(f"  [ERROR] skills 섹션을 찾을 수 없음: {yaml_path.stem}")
            return False

        # gimmick YAML 텍스트 생성
        gimmick_lines = ["gimmick:\n"]
        for key, value in gimmick_data.items():
            if isinstance(value, str):
                gimmick_lines.append(f"  {key}: {value}\n")
            elif isinstance(value, int) or isinstance(value, float):
                gimmick_lines.append(f"  {key}: {value}\n")
            elif isinstance(value, list):
                gimmick_lines.append(f"  {key}:\n")
                for item in value:
                    gimmick_lines.append(f"  - {item}\n")

        # gimmick 섹션 삽입
        lines.insert(skills_line_idx, "\n")  # 빈 줄 추가
        for line in reversed(gimmick_lines):
            lines.insert(skills_line_idx, line)

        # 파일 저장
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"  [OK] gimmick 추가 완료: {yaml_path.stem}")
        return True

    except Exception as e:
        print(f"  [ERROR] 오류 발생: {yaml_path.stem} - {e}")
        return False


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    characters_dir = project_root / "data" / "characters"

    print("=" * 80)
    print("누락된 Gimmick 자동 추가 스크립트")
    print("=" * 80)
    print()

    success_count = 0
    skip_count = 0
    error_count = 0

    for job_id, gimmick_data in GIMMICK_DEFINITIONS.items():
        yaml_path = characters_dir / f"{job_id}.yaml"

        if not yaml_path.exists():
            print(f"  [WARN] 파일 없음: {job_id}")
            error_count += 1
            continue

        print(f"\n처리 중: {job_id}")
        result = add_gimmick_to_yaml(yaml_path, gimmick_data)

        if result:
            success_count += 1
        else:
            skip_count += 1

    print()
    print("=" * 80)
    print("완료")
    print("=" * 80)
    print(f"[OK] 추가됨: {success_count}개")
    print(f"[SKIP] 건너뜀: {skip_count}개")
    print(f"[ERROR] 오류: {error_count}개")
    print("=" * 80)


if __name__ == "__main__":
    main()
