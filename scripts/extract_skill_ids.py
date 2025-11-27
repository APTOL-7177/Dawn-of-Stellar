"""각 직업의 실제 스킬 ID 추출"""
import os
import re

skill_dir = 'src/character/skills/job_skills'

results = {}

for f in sorted(os.listdir(skill_dir)):
    if not f.endswith('_skills.py'):
        continue
    job = f.replace('_skills.py', '')
    path = os.path.join(skill_dir, f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Skill ID 찾기
    pattern = r'(?:Skill|TeamworkSkill)\s*\(\s*["\']([^"\']+)["\']'
    matches = re.findall(pattern, content)
    
    if matches:
        # 접두사 제거한 ID 목록
        prefix = job + '_'
        clean_ids = []
        for m in matches:
            if m.startswith(prefix):
                clean_ids.append(m[len(prefix):])
            else:
                clean_ids.append(m)
        results[job] = clean_ids
        print(f'{job}:')
        for cid in clean_ids:
            print(f'  - {cid}')
        print()
