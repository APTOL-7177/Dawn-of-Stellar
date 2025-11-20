"""모든 직업의 올스탯 총합 계산"""
import yaml
from pathlib import Path

# 캐릭터 데이터 디렉토리
data_dir = Path("data/characters")

jobs_data = []

# 모든 직업 YAML 파일 읽기
for yaml_file in sorted(data_dir.glob("*.yaml")):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    job_name = data.get('class_name', yaml_file.stem)
    base_stats = data.get('base_stats', {})
    
    # 스탯 총합 계산 (HP는 4당 1, MP는 1.5당 1, 초기BRV는 2당 1로 정규화)
    hp = base_stats.get('hp', 0) / 4.0  # HP는 4당 1
    mp = base_stats.get('mp', 0) / 1.5  # MP는 1.5당 1
    physical_attack = base_stats.get('physical_attack', 0)
    physical_defense = base_stats.get('physical_defense', 0)
    magic_attack = base_stats.get('magic_attack', 0)
    magic_defense = base_stats.get('magic_defense', 0)
    speed = base_stats.get('speed', 0)
    init_brv = base_stats.get('init_brv', 0) / 2.0  # 초기BRV는 2당 1
    
    stat_total = hp + mp + physical_attack + physical_defense + magic_attack + magic_defense + speed + init_brv
    
    jobs_data.append({
        'name': job_name,
        'file': yaml_file.stem,
        'stats': base_stats,
        'total': stat_total
    })

# 총합 기준으로 정렬 (내림차순)
jobs_data.sort(key=lambda x: x['total'], reverse=True)

# 마크다운 형식으로 출력
print("# 직업별 올스탯 총합 (HP 4당 1, MP 1.5당 1, 초기BRV 2당 1로 정규화)\n")
print("| 직업명 | 총합 | HP(정규화) | MP(정규화) | 물공 | 물방 | 마공 | 마방 | 속도 | 초기BRV(정규화) | 초기BRV(원본) | HP(원본) | MP(원본) |")
print("|--------|------|-----------|-----------|------|------|------|------|------|--------------|------------|---------|---------|")

for job in jobs_data:
    stats = job['stats']
    hp_norm = stats.get('hp', 0) / 4.0
    mp_norm = stats.get('mp', 0) / 1.5
    init_brv_norm = stats.get('init_brv', 0) / 2.0
    print(f"| {job['name']} | {job['total']:.1f} | "
          f"{hp_norm:.1f} | "
          f"{mp_norm:.1f} | "
          f"{stats.get('physical_attack', 0)} | "
          f"{stats.get('physical_defense', 0)} | "
          f"{stats.get('magic_attack', 0)} | "
          f"{stats.get('magic_defense', 0)} | "
          f"{stats.get('speed', 0)} | "
          f"{init_brv_norm:.1f} | "
          f"{stats.get('init_brv', 0)} | "
          f"{stats.get('hp', 0)} | "
          f"{stats.get('mp', 0)} |")

print("\n## 통계")
print(f"- **총 직업 수**: {len(jobs_data)}개")
avg_total = sum(j['total'] for j in jobs_data) / len(jobs_data)
print(f"- **평균 스탯 총합**: {avg_total:.1f}")
max_job = max(jobs_data, key=lambda x: x['total'])
min_job = min(jobs_data, key=lambda x: x['total'])
print(f"- **최고 스탯 총합**: {max_job['total']:.1f} ({max_job['name']})")
print(f"- **최저 스탯 총합**: {min_job['total']:.1f} ({min_job['name']})")
print(f"- **스탯 총합 범위**: {max_job['total'] - min_job['total']:.1f}")

