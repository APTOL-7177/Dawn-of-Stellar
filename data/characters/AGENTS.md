<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/characters/

## Purpose
35개 직업별 캐릭터 YAML 정의. 각 파일은 직업 이름(warrior.yaml, berserker.yaml 등)으로 저장되며, 기본 스탯, 성장률, 고유 메커니즘(gimmick), 스킬 리스트를 정의합니다.

## Key Files
| File | Description |
|------|-------------|
| warrior.yaml | 전사 직업 (기본 근력 딜러) |
| berserker.yaml | 광전사 (광폭화 메커니즘) |
| knight.yaml | 기사 (방어 탱킹) |
| archer.yaml | 궁수 (원거리 딜러) |
| mage.yaml | 마법사 (마법 계수 딜러) |
| alchemist.yaml | 연금술사 (요리/합성 특화) |
| rogue.yaml | 로그 (암살/독 특화) |
| (30개 더) | paladin, samurai, time_mage, dimensionist, illusionist 등 |

## Structure Per File
```yaml
job_name: "warrior"          # 직업명
base_stats:
  hp: 100
  mp: 20
  attack: 18
  defense: 16
  ...
growth_rates:
  hp_growth: 1.2
  attack_growth: 1.1
  ...
gimmick:
  name: "rage"               # 고유 메커니즘
  max_value: 100
  ...
skills:
  - skill_id: "slash"        # skills/ 에서 참조
    learn_level: 1
  - skill_id: "power_slash"
    learn_level: 5
```

## For AI Agents

### Working In This Directory
- 파일 이름 = 직업 ID (snake_case): warrior, berserker, knight, archer 등
- character_loader.py 가 load_character(job_id) 시 자동으로 job_id.yaml 찾음
- 각 직업은 35개 직업 시스템의 일부로 게임의 직업 선택/전직 시스템과 연동

### Common Patterns
- base_stats: HP, MP, ATK, DEF, MAT, MDF, SPD, EVA, ACC 기본값
- growth_rates: 레벨업당 스탯 증가율 (곱하기 방식)
- gimmick: 직업 고유 메커니즘 (rage, focus, casts, combo 등)
- skills: learn_level 순서대로 자동 학습

## Dependencies
- src/character/character_loader.py - YAML 로드 및 직업 인스턴스화
- src/character/gimmick_updater.py - gimmick 필드 처리
- src/character/job_stats_loader.py - 직업별 성장률 적용

<!-- MANUAL: -->
