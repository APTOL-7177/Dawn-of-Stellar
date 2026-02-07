---
description: 새로운 캐릭터(직업)를 추가하는 워크플로우
---

# 새 캐릭터(직업) 추가

## 1. 기존 캐릭터 YAML 패턴 파악
// turbo
`data/characters/` 에서 비슷한 역할군의 기존 캐릭터 YAML 2~3개를 읽어 필드 구조와 스탯 범위를 확인한다.

## 2. 캐릭터 데이터 YAML 생성
`data/characters/<job_id>.yaml` 파일을 생성한다. 필수 구조:
```yaml
class_name: <한글 직업명>
description: <한글 설명>
slogan: <한 줄 슬로건>
archetype: <역할 설명>
base_stats:
  hp: <150~200>
  mp: <25~60>
  init_brv: <100~160>
  physical_attack: <30~85>
  physical_defense: <40~65>
  magic_attack: <30~85>
  magic_defense: <40~60>
  speed: <55~75>
  max_brv: <280~400>
stat_growth:
  hp: <30~50>
  mp: <1.5~5>
  init_brv: <25~35>
  strength: <15~25>
  defense: <8~16>
  magic: <5~22>
  spirit: <8~15>
  speed: <12~20>
  max_brv: <75~110>
  luck: <0.8~1.5>
  accuracy: <1.2~2.0>
  evasion: <0.8~1.5>
traits:
  - id: <trait_id>
    name: <한글명>
    description: <설명>
    type: <passive|conditional>
    effects: { ... }
gimmick:
  type: <gimmick_type>
  name: <한글명>
  description: <설명>
skills:
  - teamwork
  - <skill_id_1>
  - <skill_id_2>
  - ultimate
bonuses: { ... }
```
- 스탯 범위는 기존 캐릭터들의 분포를 참고한다.
- `gimmick.type`은 고유해야 한다.

## 3. 직업 전용 스킬 추가
`/add-skill` 워크플로우를 참고하여 해당 직업의 스킬 YAML들을 `data/skills/`에 생성한다.

## 4. 기믹 업데이터 구현
`src/character/gimmick_updater.py`에 새 기믹 타입에 대한 초기화/업데이트/렌더 로직을 추가한다.
- `_initialize_<gimmick_type>(self, character)` 메서드
- `_update_<gimmick_type>(self, character, context)` 메서드

## 5. 트레이트 효과 구현
`src/character/trait_effects.py`에 새 트레이트의 효과 로직을 추가한다.

## 6. 캐릭터 로더에 등록 확인
// turbo
`src/character/character_loader.py`가 YAML 기반으로 자동 로드하는지 확인한다. 수동 등록이 필요하면 추가한다.

## 7. 테스트
```bash
pytest tests/ -x -q
python main.py --dev
```
