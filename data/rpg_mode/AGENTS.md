<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/rpg_mode/

## Purpose
RPG 모드 게임 설정. 월드 생성, 지역 허브, 인카운터 설정, 보상 테이블을 정의합니다.

## Key Files
| File | Description |
|------|-------------|
| rpg_config.yaml | RPG 모드 전역 설정 (난이도, 보상, 인카운터 비율) |

## Structure Per File
```yaml
rpg_mode:
  difficulty: "normal"
  encounter_rate: 0.3
  treasure_drop_rate: 0.5
  experience_multiplier: 1.0
  regions:
    - name: "Forest"
      enemy_levels: [1, 5]
      treasure_table: "common"
  boss_encounters:
    - name: "Forest Guardian"
      level: 10
      rewards:
        gold: 500
        items: ["rare_sword"]
```

## For AI Agents

### Working In This Directory
- RPG 모드 런타임 설정 (게임 시작 시 로드)
- src/rpg_mode/ 모듈에서 참조

### Common Patterns
- difficulty: 인카운터 강도, 보상 배수 조정
- encounter_rate: 지역별 전투 확률
- treasure_drop_rate: 아이템 드롭 비율
- boss_encounters: 보스 전투 정의

## Dependencies
- src/rpg_mode/ - RPG 모드 런타임

<!-- MANUAL: -->
