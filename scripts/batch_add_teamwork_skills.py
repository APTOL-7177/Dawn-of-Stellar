"""
모든 직업의 팀워크 스킬을 일괄 추가하는 스크립트

usage: python batch_add_teamwork_skills.py
"""

import os
import re
import yaml

def load_teamwork_skills_yaml():
    """YAML에서 팀워크 스킬 정보 로드"""
    yaml_path = r"X:\develop\Dawn-of-Stellar\data\teamwork_skills.yaml"
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def find_return_line(content: str) -> int:
    """return 문의 라인 인덱스를 찾습니다"""
    lines = content.split('\n')
    for i in range(len(lines) - 1, -1, -1):
        if 'return' in lines[i] and ('[' in lines[i] or 'skills' in lines[i]):
            return i
    return -1


def generate_teamwork_skill_code(job_id: str, skill_info: dict) -> str:
    """팀워크 스킬 코드 생성"""
    code = f"""
    # 팀워크 스킬: {skill_info['name']}
    teamwork = TeamworkSkill(
        "{skill_info['skill_id']}",
        "{skill_info['name']}",
        "{skill_info['description']}",
        gauge_cost={skill_info['gauge_cost']}
    )
    teamwork.effects = []  # TODO: 효과 추가
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {{"teamwork": True, "chain": True}}
    skills.append(teamwork)"""
    return code


def add_teamwork_skill(job_id: str, skill_info: dict) -> bool:
    """특정 직업에 팀워크 스킬 추가"""
    # 파일 경로
    base_path = r"X:\develop\Dawn-of-Stellar\src\character\skills\job_skills"
    file_path = os.path.join(base_path, f"{job_id}_skills.py")

    if not os.path.exists(file_path):
        print(f"[FAIL] 파일 없음: {job_id} ({file_path})")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 이미 추가되었는지 확인
        if f'"{skill_info["skill_id"]}"' in content:
            print(f"[SKIP] 이미 존재: {job_id} ({skill_info['skill_id']})")
            return True

        # Import 확인 및 추가
        if "from src.character.skills.teamwork_skill import TeamworkSkill" not in content:
            # 기존 import 찾기
            match = re.search(r'(from src\.character\.skills\..*?\n)', content)
            if match:
                insert_pos = match.end()
                content = (content[:insert_pos] +
                          "from src.character.skills.teamwork_skill import TeamworkSkill\n" +
                          content[insert_pos:])
            else:
                # 파일 시작에 추가
                lines = content.split('\n')
                lines.insert(0, "from src.character.skills.teamwork_skill import TeamworkSkill")
                content = '\n'.join(lines)

        # return 라인 찾기
        lines = content.split('\n')
        return_idx = find_return_line(content)

        if return_idx == -1:
            print(f"[WARN] return 문을 찾을 수 없음: {job_id}")
            return False

        # 팀워크 스킬 코드 생성 및 삽입
        teamwork_code = generate_teamwork_skill_code(job_id, skill_info)
        lines.insert(return_idx, teamwork_code)

        # return 라인 수정 (teamwork 추가)
        return_line = lines[return_idx + 1]
        if 'return [' in return_line and ']' in return_line:
            # 한 줄 return
            return_line = return_line.replace(']', ', teamwork]')
            lines[return_idx + 1] = return_line
        elif 'return [' in return_line:
            # 여러 줄 return
            # 마지막 ']'를 찾아서 ', teamwork]'로 바꿈
            for j in range(return_idx + 1, len(lines)):
                if ']' in lines[j]:
                    lines[j] = lines[j].replace(']', ', teamwork]')
                    break

        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"[OK] 완료: {job_id} ({skill_info['skill_id']})")
        return True

    except Exception as e:
        print(f"[ERROR] 오류: {job_id} - {e}")
        return False


def main():
    """메인 함수"""
    print("[*] Teamwork Skills Batch Add Started...\n")

    try:
        teamwork_skills = load_teamwork_skills_yaml()
    except Exception as e:
        print(f"[FAIL] YAML 로드 실패: {e}")
        return

    success_count = 0
    fail_count = 0

    for job_id, skill_info in teamwork_skills.items():
        if add_teamwork_skill(job_id, skill_info):
            success_count += 1
        else:
            fail_count += 1

    print(f"\n[SUCCESS] 성공: {success_count}")
    print(f"[FAIL] 실패: {fail_count}")
    print("[DONE] 완료!")


if __name__ == "__main__":
    main()
