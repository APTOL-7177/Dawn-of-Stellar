<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# character/

## Purpose
캐릭터 생성·스탯 관리·직업 시스템·파티 관리를 담당. 35개 직업의 YAML 데이터를 로딩하고, StatManager를 통해 레벨 성장·장비 보너스·버프를 통합 관리한다.

## Key Files

| File | Description |
|------|-------------|
| `character.py` | `Character` 클래스. YAML에서 직업 데이터 로드, StatManager 초기화, HP/MP/BRV/ATB 현재값 관리 |
| `stats.py` | 스탯 시스템 핵심. `Stats` enum(스탯 이름 상수), `Stat` 클래스(보너스 시스템), `StatManager`(전체 스탯 관리), `GrowthType` enum |
| `party.py` | `Party` 클래스. 파티 멤버 목록, 팀워크 게이지, 파티 전체 HP/MP 연산 |
| `character_loader.py` | YAML 직업 데이터 로더. `load_character_data()`, `get_base_stats()`, `get_gimmick()`, `get_traits()`, `get_skills()` |
| `job_stats_loader.py` | 직업별 스탯 테이블 로드 및 레벨업 성장치 계산 |
| `skill_types.py` | 스킬 타입 enum 및 분류 상수 정의 |
| `basic_attacks.py` | 기본 공격(BRV 공격, HP 공격) 스킬 정의 |
| `trait_effects.py` | 특성(Trait) 효과 시스템. `get_trait_effect_manager()` 팩토리 |
| `upgrade_applier.py` | 장비 업그레이드 보너스 적용 |
| `gimmick_trait_effects.py` | 기믹 특성 효과 정의 |
| `gimmick_updater.py` | `GimmickUpdater` 클래스. 전투 중 기믹 상태 갱신 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `classes/` | 직업 클래스 정의 (see `classes/AGENTS.md`) |
| `skills/` | 스킬 시스템 전체 (see `skills/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- 캐릭터 생성: `Character(name, character_class, level)` — `character_class`는 직업 ID 문자열 (예: `"warrior"`, `"mage"`)
- 스탯 접근: `character.stat_manager.get_value(Stats.ATK)` — `Stats` enum 상수 사용 필수
- 직업 데이터는 `data/characters/{job_id}.yaml`에 있음 (35개)
- `current_hp`, `current_mp`는 `Character` 직속 속성; `max_hp`, `max_mp`는 StatManager 프로퍼티
- 보너스 추가: `stat.add_bonus(source="장비명", value=50)` / 제거: `stat.remove_bonus(source)`
- 새 직업 추가 시 `data/characters/`에 YAML 추가 + `job_stats_loader` 데이터 테이블 확인

### Testing Requirements
- `tests/test_character*.py` 또는 `tests/test_stats*.py` 확인
- 레벨업 테스트: `stat_manager.apply_level_up(level)` 후 스탯 검증

### Common Patterns
```python
# 캐릭터 생성
from src.character.character import Character
char = Character(name="홍길동", character_class="warrior", level=10)

# 스탯 접근
from src.character.stats import Stats
atk = char.stat_manager.get_value(Stats.ATK)
max_hp = char.max_hp  # 프로퍼티

# 보너스 적용
char.stat_manager.add_bonus(Stats.DEF, source="방어구", value=30)
```

## Dependencies

### Internal
- `src.core.event_bus` — `Events.CHARACTER_*` 이벤트 발행
- `src.core.logger` — 캐릭터 로그
- `src.combat.status_effects` — `StatusManager` 통합

### External
- `yaml` (PyYAML): `data/characters/*.yaml` 로딩

<!-- MANUAL: -->
