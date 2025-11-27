"""스킬 ID 불일치 점검 스크립트"""
import yaml
import os
import re

char_dir = 'data/characters'
skill_dir = 'src/character/skills/job_skills'

def get_registered_skills(job_name):
    """코드에서 등록된 스킬 ID 찾기"""
    skill_file = os.path.join(skill_dir, f'{job_name}_skills.py')
    if not os.path.exists(skill_file):
        return []
    
    with open(skill_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skill("skill_id", ...) 패턴 찾기
    pattern = r'Skill\(["\']([^"\']+)["\']'
    matches = re.findall(pattern, content)
    
    # TeamworkSkill 패턴도 찾기
    teamwork_pattern = r'TeamworkSkill\(["\']([^"\']+)["\']'
    teamwork_matches = re.findall(teamwork_pattern, content)
    
    return matches + teamwork_matches

# 모든 직업 점검
print("=== 스킬 ID 점검 ===\n")
issues = []
all_jobs = []

for yaml_file in sorted(os.listdir(char_dir)):
    if not yaml_file.endswith('.yaml'):
        continue
    
    job_name = yaml_file.replace('.yaml', '')
    yaml_path = os.path.join(char_dir, yaml_file)
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    yaml_skills = data.get('skills', [])
    if not yaml_skills:
        continue
    
    # 코드에서 등록된 스킬 ID 가져오기
    registered = get_registered_skills(job_name)
    
    # 접두사
    prefix = job_name + '_'
    
    # 불일치 찾기
    missing = []
    for yaml_skill in yaml_skills:
        if yaml_skill == 'teamwork':
            expected_id = prefix + 'teamwork'
        else:
            expected_id = prefix + yaml_skill
        
        if expected_id not in registered and yaml_skill not in registered:
            missing.append(yaml_skill)
    
    skill_count = len(yaml_skills)
    missing_count = len(missing)
    status = "✓" if missing_count == 0 else "✗"
    
    all_jobs.append({
        'name': job_name,
        'class_name': data.get('class_name', job_name),
        'skill_count': skill_count,
        'missing': missing,
        'registered_count': len(registered),
        'description': data.get('description', ''),
        'archetype': data.get('archetype', '')
    })
    
    if missing:
        issues.append({
            'job': job_name,
            'class_name': data.get('class_name', job_name),
            'missing': missing
        })

# 불일치 출력
print("=== 불일치 직업 ===")
for issue in issues:
    print(f"\n{issue['class_name']} ({issue['job']}):")
    for m in issue['missing']:
        print(f"  - {m}")

print(f"\n총 {len(issues)}개 직업에서 불일치 발견")

# 전체 직업 요약
print("\n\n=== 전체 직업 현황 ===")
print(f"{'직업명':<12} {'영문':<15} {'아키타입':<15} {'스킬수':<6} {'코드':<6} {'상태'}")
print("-" * 70)
for job in all_jobs:
    status = "✓" if len(job['missing']) == 0 else f"✗ ({len(job['missing'])}개 누락)"
    print(f"{job['class_name']:<12} {job['name']:<15} {job['archetype']:<15} {job['skill_count']:<6} {job['registered_count']:<6} {status}")
