<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/skills/

## Purpose
414+ 스킬 YAML 파일 저장소. 각 스킬은 파일명(skill_id.yaml)으로 정의되며, 데미지 계산, 코스트, 효과, 타겟팅, 조건을 포함합니다. 모든 직업(35개) 스킬이 여기에 집중됩니다.

## Key Files
| File | Count | Description |
|------|-------|-------------|
| (이름순 정렬) | 414+ | slash.yaml, power_slash.yaml, cure.yaml, ... |
| - | - | 직업별 스킬: warrior/, rogue/, mage/ 같은 폴더 없음 (모두 flat) |

## Structure Per File
```yaml
skill_id: "slash"
name: "참격"
description: "기본 참격 공격"
cost:
  type: "mp"
  amount: 5
damage:
  type: "physical"
  formula: "ATK * 1.0"
  scaling: 1.0
effects:
  - type: "damage"
    target: "enemy"
  - type: "status"
    status: "bleed"
    chance: 0.3
targeting:
  type: "single_enemy"
condition:
  job: "warrior"
  level: 1
animated: true
sfx: "slash.wav"
```

## For AI Agents

### Working In This Directory
- 모든 스킬이 평면 구조(414+ .yaml 파일)로 data/skills/ 직접 저장
- skill_id = 파일명 (snake_case): slash, power_slash, cure, heal, etc.
- character.yaml 에서 skills 리스트로 skill_id 참조
- yaml_skill_loader.py 가 skill_id 로 skills/ 에서 YAML 로드

### Common Patterns
- cost: type (mp, hp, gimmick, stack), amount 정의
- damage: type (physical, magical, mixed), formula (stat 계산식), scaling (배수)
- effects: 배열로 순차 적용 (damage -> status -> buff 등)
- targeting: single_enemy, all_enemies, self, ally 등
- condition: job (직업 제한), level (습득 레벨), other (기타 조건)
- status_effects: 상태 이상 부여 (poison, bleed, sleep, etc.)
- animated: true/false 애니메이션 표시 여부

## Dependencies
- src/character/skills/yaml_skill_loader.py - YAML 로드 및 Skill 인스턴스화
- src/character/skills/skill.py - Skill 데이터 클래스
- src/character/skills/effects/ - 효과 모듈 (damage_effect.py, status_effect.py 등)
- src/combat/damage_calculator.py - damage formula 계산

<!-- MANUAL: -->
