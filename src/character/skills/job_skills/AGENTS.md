<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# character/skills/job_skills/

## Purpose
35개 직업별 스킬을 Python 코드로 정의하는 모듈. 각 파일은 해당 직업의 스킬 객체를 생성하고 반환하는 팩토리 함수를 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `warrior_skills.py` | 전사 직업 스킬 정의 |
| `mage_skills.py` / `wizard_skills.py` | 마법사 계열 스킬 |
| `archer_skills.py` | 궁수 스킬 |
| `assassin_skills.py` | 암살자 스킬 |
| `cleric_skills.py` | 성직자(힐러) 스킬 |
| `paladin_skills.py` | 팔라딘 스킬 |
| `dark_knight_skills.py` | 암흑 기사 스킬 |
| `berserker_skills.py` | 광전사 스킬 |
| `elementalist_skills.py` | 정령술사 스킬 |
| `archmage_skills.py` | 대마법사 스킬 |
| `engineer_skills.py` | 엔지니어 스킬 |
| `hacker_skills.py` | 해커 스킬 |
| `bard_skills.py` | 음유시인 스킬 |
| `druid_skills.py` | 드루이드 스킬 |
| `gladiator_skills.py` | 검투사 스킬 |
| `illusionist_skills.py` | 환술사 스킬 |
| `dimensionist_skills.py` | 차원술사 스킬 |
| `dragon_knight_skills.py` | 용기사 스킬 |
| `battle_mage_skills.py` | 배틀메이지 스킬 |
| `breaker_skills.py` | 브레이커 스킬 |
| (그 외 직업 파일들) | 각 직업별 스킬 |

## For AI Agents

### Working In This Directory
- 각 파일은 `get_{job_id}_skills() -> List[Skill]` 패턴의 팩토리 함수 포함
- 스킬은 `Skill` 객체에 `costs`, `effects`, `target_type`, `metadata` 설정하여 구성
- YAML 기반 스킬과 Python 기반 스킬이 혼용됨 — `yaml_skill_loader`가 우선
- 기믹 스킬은 `gimmick_effect.py` 효과와 `gimmick_cost.py` 비용 사용
- 신규 직업 추가: 파일 이름 규칙 `{job_id}_skills.py` 준수

### Testing Requirements
- 직업 스킬 로드 테스트: 팩토리 함수 호출 후 스킬 수/ID 검증
- 스킬 실행 시뮬레이션: 더미 전투 상황에서 각 스킬 `can_use` + `execute` 테스트

### Common Patterns
```python
# 스킬 팩토리 사용
from src.character.skills.job_skills.warrior_skills import get_warrior_skills
skills = get_warrior_skills()

# 스킬 빌더 패턴
from src.character.skills.skill import Skill
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.effects.damage_effect import DamageEffect

skill = Skill(skill_id="blade_storm", name="블레이드 스톰")
skill.costs.append(MPCost(60))
skill.effects.append(DamageEffect(power=2.5))
skill.target_type = "all_enemies"
skill.metadata["basic_attack"] = False
```

## Dependencies

### Internal
- `src.character.skills.skill` — `Skill`, `SkillResult`
- `src.character.skills.costs.*` — 비용 구현체
- `src.character.skills.effects.*` — 효과 구현체
- `data/skills/*.yaml` — YAML 정의 스킬 (yaml_skill_loader 경유)

### External
- 없음

<!-- MANUAL: -->
