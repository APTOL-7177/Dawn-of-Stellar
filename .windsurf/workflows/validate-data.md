---
description: YAML 게임 데이터의 무결성을 검증하는 워크플로우
---

# 게임 데이터 검증

## 1. 캐릭터 데이터 검증
// turbo
모든 `data/characters/*.yaml`을 검사한다:
```bash
python -c "
import yaml, pathlib, sys
errors = []
for f in sorted(pathlib.Path('data/characters').glob('*.yaml')):
    d = yaml.safe_load(f.read_text(encoding='utf-8'))
    required = ['class_name','description','base_stats','skills','gimmick']
    for r in required:
        if r not in d:
            errors.append(f'{f.name}: missing {r}')
    bs = d.get('base_stats', {})
    for s in ['hp','mp','physical_attack','physical_defense','speed','max_brv']:
        if s not in bs:
            errors.append(f'{f.name}: missing stat {s}')
if errors:
    print('ERRORS:'); [print(f'  - {e}') for e in errors]; sys.exit(1)
else:
    print(f'OK: {len(list(pathlib.Path(\"data/characters\").glob(\"*.yaml\")))} characters validated')
"
```

## 2. 스킬 데이터 검증
// turbo
모든 `data/skills/*.yaml`을 검사한다:
```bash
python -c "
import yaml, pathlib, sys
errors = []
for f in sorted(pathlib.Path('data/skills').glob('*.yaml')):
    d = yaml.safe_load(f.read_text(encoding='utf-8'))
    if not d: errors.append(f'{f.name}: empty file'); continue
    for r in ['id','name','type']:
        if r not in d:
            errors.append(f'{f.name}: missing {r}')
    if d.get('id') != f.stem:
        errors.append(f'{f.name}: id mismatch ({d.get(\"id\")} != {f.stem})')
if errors:
    print(f'ERRORS ({len(errors)}):'); [print(f'  - {e}') for e in errors[:30]]; sys.exit(1)
else:
    print(f'OK: {len(list(pathlib.Path(\"data/skills\").glob(\"*.yaml\")))} skills validated')
"
```

## 3. 스킬 참조 검증
// turbo
캐릭터가 참조하는 스킬이 실제 존재하는지 확인:
```bash
python -c "
import yaml, pathlib
skill_ids = {f.stem for f in pathlib.Path('data/skills').glob('*.yaml')}
special = {'teamwork','ultimate','basic_attack'}
for f in sorted(pathlib.Path('data/characters').glob('*.yaml')):
    d = yaml.safe_load(f.read_text(encoding='utf-8'))
    for s in d.get('skills', []):
        if s not in skill_ids and s not in special:
            print(f'{f.name}: missing skill ref -> {s}')
print('Done')
"
```

## 4. 팀워크 스킬 검증
// turbo
```bash
python -c "
import yaml, pathlib
d = yaml.safe_load(pathlib.Path('data/teamwork_skills.yaml').read_text(encoding='utf-8'))
print(f'Teamwork skills: {len(d)} entries')
for item in d:
    if 'id' not in item or 'name' not in item:
        print(f'  WARNING: incomplete entry {item}')
print('Done')
"
```

## 5. 결과 리포트
검증 결과를 요약하여 사용자에게 보고한다.
