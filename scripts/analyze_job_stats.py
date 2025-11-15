"""모든 직업의 스탯 분석 - 물리/마법/하이브리드 분류"""
import yaml
from pathlib import Path

# 캐릭터 데이터 디렉토리
data_dir = Path("data/characters")

jobs_data = []

for yaml_file in sorted(data_dir.glob("*.yaml")):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    job_name = data.get('class_name', yaml_file.stem)
    base_stats = data.get('base_stats', {})

    p_atk = base_stats.get('physical_attack', 0)
    m_atk = base_stats.get('magic_attack', 0)

    # 분류
    if p_atk > m_atk + 10:
        job_type = "물리"
    elif m_atk > p_atk + 10:
        job_type = "마법"
    else:
        job_type = "하이브리드"

    jobs_data.append({
        'file': yaml_file.stem,
        'name': job_name,
        'p_atk': p_atk,
        'm_atk': m_atk,
        'type': job_type
    })

# 타입별로 그룹화
physical_jobs = [j for j in jobs_data if j['type'] == "물리"]
magical_jobs = [j for j in jobs_data if j['type'] == "마법"]
hybrid_jobs = [j for j in jobs_data if j['type'] == "하이브리드"]

print("=" * 80)
print("물리 공격 위주 직업 (stat_type='physical' 기본값)")
print("=" * 80)
for job in physical_jobs:
    print(f"{job['name']:15} | 물리:{job['p_atk']:3} 마법:{job['m_atk']:3} | {job['file']}")

print("\n" + "=" * 80)
print("마법 공격 위주 직업 (stat_type='magical' 필요)")
print("=" * 80)
for job in magical_jobs:
    print(f"{job['name']:15} | 물리:{job['p_atk']:3} 마법:{job['m_atk']:3} | {job['file']}")

print("\n" + "=" * 80)
print("하이브리드 직업 (스킬마다 다르게 설정)")
print("=" * 80)
for job in hybrid_jobs:
    print(f"{job['name']:15} | 물리:{job['p_atk']:3} 마법:{job['m_atk']:3} | {job['file']}")

print("\n" + "=" * 80)
print("요약")
print("=" * 80)
print(f"물리 직업: {len(physical_jobs)}개")
print(f"마법 직업: {len(magical_jobs)}개")
print(f"하이브리드: {len(hybrid_jobs)}개")
print(f"총 {len(jobs_data)}개 직업")
