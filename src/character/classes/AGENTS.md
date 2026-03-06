<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# character/classes/

## Purpose
직업(Job) 클래스 패키지 초기화 모듈. 실제 직업 데이터는 `data/characters/*.yaml`에 정의되며, 이 디렉토리는 Python 패키지 선언(`__init__.py`)만 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화. 직업 클래스 import 게이트웨이 |

## For AI Agents

### Working In This Directory
- 직업 로직 자체는 `src/character/character_loader.py`와 `data/characters/*.yaml`에 있음
- 35개 직업: alchemist, archer, archmage, assassin, bard, battle_mage, berserker, breaker, cleric, dark_knight, dimensionist, dragon_knight, druid, elementalist, engineer, gladiator, hacker, illusionist, knight, monk, necromancer, ninja, paladin, priest, ranger, rogue, samurai, shaman, spellblade, summoner, thief, warrior, witch, wizard + 추가 직업들
- 새 직업 추가 시: `data/characters/{job_id}.yaml` 생성 → `data/skills/` YAML 추가 → `src/character/skills/job_skills/{job_id}_skills.py` 추가

### Testing Requirements
- 직업 로딩 테스트: `Character("테스트", "{job_id}", level=1)` 생성 후 스탯 검증

### Common Patterns
```python
# 직업 데이터 로드
from src.character.character_loader import load_character_data
data = load_character_data("warrior")
```

## Dependencies

### Internal
- `src.character.character_loader` — YAML 직업 데이터 로딩
- `data/characters/*.yaml` — 35개 직업 데이터 파일

### External
- 없음

<!-- MANUAL: -->
