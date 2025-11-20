"""모든 직업의 bonuses 확인"""
import yaml
from pathlib import Path

data_dir = Path("data/characters")

for yaml_file in sorted(data_dir.glob("*.yaml")):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    job_name = data.get('class_name', yaml_file.stem)
    archetype = data.get('archetype', 'N/A')
    bonuses = data.get('bonuses', {})
    
    print(f"{job_name:15} | {archetype:25} | {bonuses}")

