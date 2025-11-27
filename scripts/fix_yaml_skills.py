"""YAML 스킬 ID를 코드와 일치하도록 자동 수정"""
import os
import re
import yaml

skill_dir = 'src/character/skills/job_skills'
char_dir = 'data/characters'

def get_skill_ids_from_code(job_name):
    """코드에서 스킬 ID 추출 (접두사 제거)"""
    skill_file = os.path.join(skill_dir, f'{job_name}_skills.py')
    if not os.path.exists(skill_file):
        return []
    
    with open(skill_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(?:Skill|TeamworkSkill)\s*\(\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern, content)
    
    prefix = job_name + '_'
    clean_ids = []
    for m in matches:
        if m.startswith(prefix):
            clean_ids.append(m[len(prefix):])
        else:
            clean_ids.append(m)
    
    return clean_ids

def fix_yaml_file(job_name):
    """YAML 파일의 스킬 목록을 코드와 일치하도록 수정"""
    yaml_path = os.path.join(char_dir, f'{job_name}.yaml')
    if not os.path.exists(yaml_path):
        return False, "YAML 파일 없음"
    
    # 코드에서 스킬 ID 가져오기
    code_skills = get_skill_ids_from_code(job_name)
    if not code_skills:
        return False, "코드에 스킬 없음"
    
    # YAML 파일 읽기
    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # skills: 섹션 찾기
    skills_pattern = r'(skills:\s*\n)((?:[-#\s].*\n)*?)(\n*(?:[a-z]|$))'
    match = re.search(skills_pattern, content)
    
    if not match:
        return False, "skills 섹션 없음"
    
    # 새 스킬 목록 생성 (teamwork을 첫번째로)
    new_skills = ['- teamwork']
    for skill in code_skills:
        if skill != 'teamwork':
            new_skills.append(f'- {skill}')
    
    new_skills_text = 'skills:\n' + '\n'.join(new_skills) + '\n'
    
    # 기존 skills 섹션을 새 것으로 교체
    before = content[:match.start()]
    after = content[match.end():]
    if match.group(3).strip():
        after = match.group(3) + after
    
    new_content = before + new_skills_text + '\n' + after.lstrip('\n')
    
    # 파일 저장
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True, f"{len(code_skills)}개 스킬"

# 모든 직업 처리
print("=== YAML 스킬 ID 수정 ===\n")
success_count = 0
fail_count = 0

for yaml_file in sorted(os.listdir(char_dir)):
    if not yaml_file.endswith('.yaml'):
        continue
    
    job_name = yaml_file.replace('.yaml', '')
    success, msg = fix_yaml_file(job_name)
    
    if success:
        print(f"✓ {job_name}: {msg}")
        success_count += 1
    else:
        print(f"✗ {job_name}: {msg}")
        fail_count += 1

print(f"\n완료: {success_count}개 성공, {fail_count}개 실패")
