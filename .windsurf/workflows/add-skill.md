---
description: 새로운 YAML 스킬을 추가하는 워크플로우
---

# 새 스킬 추가

## 1. 기존 스킬 패턴 확인
// turbo
`data/skills/` 디렉토리에서 추가하려는 스킬과 유사한 타입의 기존 스킬 YAML을 2~3개 읽어 패턴을 파악한다.

## 2. 스킬 YAML 파일 생성
`data/skills/<skill_id>.yaml` 파일을 생성한다. 필수 필드:
```yaml
id: <snake_case_id>          # 고유, 안정적
name: <한글 스킬명>
type: <brv_attack|hp_attack|brv_hp_attack|support|debuff|ultimate>
description: <한글 설명>
costs:
  mp: <정수>
  cast_time: <float>
effects:
  - type: damage
    element: <physical|fire|ice|thunder|holy|dark|wind|earth|water|non_elemental>
    multiplier: <float>
    stat_base: <strength|magic>
sfx:              # 선택
  - se
  - <효과음명>
```
- `id`는 파일명과 일치시킨다.
- 기존 스킬 평균 MP 비용/배율을 참고하여 밸런스를 맞춘다.

## 3. 캐릭터 YAML에 스킬 등록
해당 스킬을 사용할 캐릭터의 `data/characters/<job>.yaml` 파일의 `skills:` 리스트에 스킬 ID를 추가한다.

## 4. 커스텀 핸들러 필요 여부 확인
- 단순 데미지/버프/디버프: YAML만으로 충분 (yaml_skill_loader.py가 자동 로드).
- 특수 로직 (조건부 효과, 카운터, 토글 등): `src/character/skills/custom_handlers.py` 또는 `src/character/skills/job_skills/<job>.py`에 핸들러 추가.

## 5. 데이터 무결성 검증
// turbo
```bash
python -c "import yaml, pathlib; d=yaml.safe_load(pathlib.Path('data/skills/<skill_id>.yaml').read_text(encoding='utf-8')); assert d.get('id') and d.get('name') and d.get('type') and d.get('costs'), f'Missing fields: {d}'; print('OK:', d['id'])"
```

## 6. 테스트 실행
```bash
pytest tests/ -k "skill" -x -q
```
