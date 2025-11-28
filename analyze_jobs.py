"""직업 데이터 분석 스크립트"""
import yaml
from pathlib import Path

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 디렉토리
char_dir = Path('data/characters')
skill_dir = Path('data/skills')

# 모든 직업 파일 로드
jobs = {}
for f in char_dir.glob('*.yaml'):
    data = load_yaml(f)
    jobs[f.stem] = data

# 모든 스킬 파일 목록
skill_files = {f.stem for f in skill_dir.glob('*.yaml')}

print(f'=== 직업 수: {len(jobs)}')
print(f'=== 스킬 파일 수: {len(skill_files)}')

# 각 직업별 분석
issues = []

for job_id, data in sorted(jobs.items()):
    job_issues = []
    name = data.get('name', '?')
    
    # 스킬 목록 확인
    skills = data.get('skills', [])
    
    # 스킬 파일 존재 여부 확인
    for skill_id in skills:
        full_skill_id = f'{job_id}_{skill_id}'
        if full_skill_id not in skill_files and skill_id not in skill_files:
            job_issues.append(f'스킬 파일 없음: {skill_id}')
    
    # 특성 목록 확인
    traits = data.get('traits', [])
    for trait in traits:
        trait_id = trait.get('id') if isinstance(trait, dict) else trait
        # 특성 구조 검증
        if isinstance(trait, dict):
            if 'id' not in trait:
                job_issues.append(f'특성 id 누락: {trait}')
            if 'name' not in trait:
                job_issues.append(f'특성 name 누락: {trait_id}')
    
    # 기믹 확인
    gimmick = data.get('gimmick', {})
    if gimmick:
        gimmick_type = gimmick.get('type')
        if not gimmick_type:
            job_issues.append('기믹 type 누락')
    
    # base_stats 확인
    base_stats = data.get('base_stats', {})
    required_stats = ['hp', 'mp', 'init_brv', 'physical_attack', 'physical_defense', 
                      'magic_attack', 'magic_defense', 'speed']
    for stat in required_stats:
        if stat not in base_stats:
            job_issues.append(f'base_stats에 {stat} 누락')
    
    if job_issues:
        issues.append((job_id, name, job_issues))
        print(f'\n=== {job_id} ({name}) - {len(job_issues)}개 문제 ===')
        for issue in job_issues:
            print(f'  - {issue}')

print(f'\n\n=== 총 {len(issues)}개 직업에서 문제 발견 ===')
