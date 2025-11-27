"""
팀워크 스킬 자동 추가 스크립트

모든 33개 직업의 스킬 파일에 팀워크 스킬을 추가합니다.
"""

import os
import re

# 팀워크 스킬 데이터 (직업별)
TEAMWORK_SKILLS = {
    "warrior": {
        "skill_id": "warrior_teamwork",
        "name": "전장의 돌격",
        "description": "단일 대상 BRV+HP 공격 (2.2x → HP 변환) + 현재 스탠스 유지",
        "gauge_cost": 125,
        "effects_code": """[
        DamageEffect(DamageType.BRV, 2.2),
        DamageEffect(DamageType.HP, 1.0),
    ]""",
        "costs_code": "[MPCost(0)]",
        "metadata": '{"teamwork": True, "chain": True}',
    },
    "archer": {
        "skill_id": "archer_teamwork",
        "name": "일제사격",
        "description": "마킹된 모든 아군의 지원사격을 한꺼번에 발사 → 본인 HP 공격 (2.5x)",
        "gauge_cost": 150,
        "effects_code": "[DamageEffect(DamageType.HP, 2.5)]",
        "costs_code": "[MPCost(0)]",
        "metadata": '{"teamwork": True, "chain": True, "support_fire": True}',
    },
    "knight": {
        "skill_id": "knight_teamwork",
        "name": "불굴의 방패",
        "description": "아군 전체에 방어막 부여 (공격력 × 0.5, 2턴) + 의무 +2",
        "gauge_cost": 125,
        "effects_code": """[
        ShieldEffect(attack_multiplier=0.5, duration=2),
        GimmickEffect(GimmickOperation.ADD, "duty", 2),
    ]""",
        "costs_code": "[MPCost(0)]",
        "metadata": '{"teamwork": True, "chain": True, "shield": True}',
        "target_type": "party",
    },
    "cleric": {
        "skill_id": "cleric_teamwork",
        "name": "치유의 기도",
        "description": "아군 1명 최대 HP의 60% 회복 + 리젠 (최대 HP의 10%씩, 3턴) + 신앙 +1",
        "gauge_cost": 75,
        "effects_code": """[
        HealEffect(percentage=0.6),
        BuffEffect(BuffType.REGEN, 0.1, duration=3),
    ]""",
        "costs_code": "[MPCost(0)]",
        "metadata": '{"teamwork": True, "chain": True, "heal": True}',
        "target_type": "ally",
    },
    "berserker": {
        "skill_id": "berserker_teamwork",
        "name": "광란의 일격",
        "description": "단일 대상 BRV+HP (1.6x → HP 변환) + 광기 +20 + 자신 공격력 1.2배 (2턴)",
        "gauge_cost": 100,
        "effects_code": """[
        DamageEffect(DamageType.BRV, 1.6),
        DamageEffect(DamageType.HP, 1.0),
        GimmickEffect(GimmickOperation.ADD, "madness", 20),
        BuffEffect(BuffType.ATTACK_UP, 0.2, duration=2),
    ]""",
        "costs_code": "[MPCost(0)]",
        "metadata": '{"teamwork": True, "chain": True}',
    },
    "rogue": {
        "skill_id": "rogue_teamwork",
        "name": "빠른 손놀림",
        "description": "단일 대상 BRV 공격 (1.2x) + 아이템 1개 훔침 (확률 60%) + ATB +300",
        "gauge_cost": 50,
        "effects_code": "[DamageEffect(DamageType.BRV, 1.2)]",
        "costs_code": "[MPCost(0)]",
        "metadata": '{"teamwork": True, "chain": True, "steal": True, "atb": True}',
    },
}


def extract_return_statement(content: str) -> int:
    """
    create_xxx_skills() 함수의 return 문 위치를 찾습니다.
    """
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'return skills' in line or 'return [' in line:
            return i
    return -1


def add_teamwork_skill_to_file(job_id: str, file_path: str, skill_data: dict) -> bool:
    """
    특정 직업 파일에 팀워크 스킬을 추가합니다.
    """
    if not os.path.exists(file_path):
        print(f"❌ 파일 없음: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # return 위치 찾기
    lines = content.split('\n')
    return_line_idx = -1
    for i, line in enumerate(reversed(lines)):
        if 'return skills' in line or 'return [' in line:
            return_line_idx = len(lines) - 1 - i
            break

    if return_line_idx == -1:
        print(f"❌ return 문을 찾을 수 없음: {job_id}")
        return False

    # 팀워크 스킬 코드 생성
    teamwork_code = f"""
    # 팀워크 스킬
    teamwork = TeamworkSkill(
        "{skill_data['skill_id']}",
        "{skill_data['name']}",
        "{skill_data['description']}",
        gauge_cost={skill_data['gauge_cost']}
    )
    teamwork.effects = {skill_data['effects_code']}
    teamwork.costs = {skill_data['costs_code']}
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {skill_data['metadata']}"""

    if 'target_type' in skill_data:
        teamwork_code += f"\n    teamwork.target_type = \"{skill_data['target_type']}\""

    teamwork_code += "\n    skills.append(teamwork)"

    # import 추가 확인
    if "from src.character.skills.teamwork_skill import TeamworkSkill" not in content:
        # import 섹션을 찾아서 추가
        import_match = re.search(r'(from src\.character\.skills\..*?\n)', content)
        if import_match:
            insert_pos = import_match.end()
            content = (content[:insert_pos] +
                      "from src.character.skills.teamwork_skill import TeamworkSkill\n" +
                      content[insert_pos:])
        else:
            # import가 없으면 파일 시작에 추가
            content = "from src.character.skills.teamwork_skill import TeamworkSkill\n" + content

    # 함수에 코드 삽입 (return 바로 전)
    lines = content.split('\n')
    lines.insert(return_line_idx, teamwork_code)
    content = '\n'.join(lines)

    # 파일 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 완료: {job_id} ({skill_data['skill_id']})")
    return True


def main():
    """메인 함수"""
    base_path = r"X:\develop\Dawn-of-Stellar\src\character\skills\job_skills"

    for job_id, skill_data in TEAMWORK_SKILLS.items():
        file_path = os.path.join(base_path, f"{job_id}_skills.py")
        add_teamwork_skill_to_file(job_id, file_path, skill_data)

    print("\n🎉 팀워크 스킬 추가 완료!")


if __name__ == "__main__":
    main()
