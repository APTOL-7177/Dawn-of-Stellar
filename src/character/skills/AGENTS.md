<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# character/skills/

## Purpose
스킬 시스템 전체. `Skill` 객체 정의, YAML 로딩, 스킬 관리자, 팀워크 스킬, 커스텀 핸들러를 포함한다. 비용(costs/)과 효과(effects/)는 하위 디렉토리로 분리되어 있다.

## Key Files

| File | Description |
|------|-------------|
| `skill.py` | `Skill` 클래스 및 `SkillResult` dataclass. `can_use()`, `execute()` 핵심 인터페이스 |
| `skill_manager.py` | `SkillManager` 클래스. 캐릭터의 스킬 목록 관리, 스킬 실행 위임 |
| `yaml_skill_loader.py` | `data/skills/*.yaml`에서 스킬 로드. `YAMLSkillLoader` 클래스 |
| `skill_initializer.py` | 캐릭터 초기화 시 스킬 세트 구성 |
| `custom_handlers.py` | 특수 스킬 동작을 위한 커스텀 핸들러 함수 등록 |
| `teamwork_skill.py` | 팀워크 스킬 클래스. 파티 협동 공격 |
| `teamwork_effects.py` | 팀워크 스킬 효과 구현 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `costs/` | 스킬 비용 구현체 (MP, HP, 스택 등) (see `costs/AGENTS.md`) |
| `effects/` | 스킬 효과 구현체 (데미지, 힐, 버프 등) (see `effects/AGENTS.md`) |
| `job_skills/` | 직업별 스킬 파이썬 정의 파일 (see `job_skills/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- `Skill` 객체는 `costs` 리스트 + `effects` 리스트 + `target_type` 문자열로 구성
- `target_type` 값: `"single_enemy"`, `"all_enemies"`, `"single_ally"`, `"all_allies"`, `"self"`
- 스킬 실행 흐름: `can_use()` → 비용 차감 → `effects` 순서대로 `apply()` → `SkillResult` 반환
- YAML 스킬은 `yaml_skill_loader.py`가 로드 → `custom_handlers.py`의 핸들러와 결합
- 새 스킬 추가: `data/skills/{skill_id}.yaml` 생성 + 필요시 `job_skills/{job}_skills.py`에 등록
- 쿨다운 시스템은 제거됨 (`# self.cooldown = 0  # 쿨다운 시스템 제거됨`)

### Testing Requirements
- 스킬 실행 테스트: `tests/test_skills*.py` 확인
- YAML 스킬 로드 검증: `YAMLSkillLoader().load_all()` 후 스킬 수 확인

### Common Patterns
```python
# 스킬 실행
skill = character.skill_manager.get_skill("fireball")
can, reason = skill.can_use(character, context={"targets": [enemy]})
if can:
    result = skill.execute(character, targets=[enemy], context={})

# YAML 스킬 로드
from src.character.skills.yaml_skill_loader import YAMLSkillLoader
loader = YAMLSkillLoader()
skill = loader.load_skill("abyss_blade")
```

## Dependencies

### Internal
- `src.character.stats` — 스탯 접근
- `src.combat.status_effects` — 상태이상 효과 적용
- `src.core.event_bus` — `Events.SKILL_*` 이벤트

### External
- `yaml` (PyYAML): `data/skills/*.yaml` 로딩

<!-- MANUAL: -->
