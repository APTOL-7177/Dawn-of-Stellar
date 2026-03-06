<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# combat/

## Purpose
ATB(Active Time Battle) 기반 전투 시스템 전체를 담당. BRV/HP 이중 공격 체계, 상태이상, 데미지 계산, 보스 기믹, 경험치 지급까지 전투 흐름 전체를 관리한다.

## Key Files

| File | Description |
|------|-------------|
| `combat_manager.py` | 전투 흐름 총괄. `CombatManager` 클래스, `CombatState`/`ActionType` enum. ATB·Brave·DamageCalculator 서브시스템 통합 |
| `atb_system.py` | ATB 게이지 관리. `ATBGauge` 클래스(threshold=1000, max=2000), `ATBSystem` 전역 관리자. 속도 기반 게이지 증가 |
| `brave_system.py` | BRV 시스템. DFFOO 스타일 BRV/HP 이중 공격. BREAK 시 보너스 데미지+스턴. `get_brave_system()` 싱글턴 |
| `damage_calculator.py` | 데미지 공식 계산. ATK/DEF 비율, 크리티컬, 원소 속성, 난이도 배율 적용. `get_damage_calculator()` 싱글턴 |
| `status_effects.py` | 상태이상 정의 및 관리. `StatusType` enum, `StatusEffect` dataclass, `StatusManager` 클래스 |
| `casting_system.py` | 캐스팅(시전) 시스템. 캐스팅 중 ATB 게이지 동결, 인터럽트 처리 |
| `enemy_skills.py` | 적 스킬 정의. `EnemySkill` dataclass, `SkillTargetType` enum. 적 고유 스킬 데이터 |
| `enemy_skills_new.py` | 리팩토링된 적 스킬 (현재 활성 버전) |
| `boss_gimmicks.py` | 보스 전투 기믹 시스템. 페이즈별 패턴 전환, 특수 메커니즘 |
| `boss_dialogue.py` | 보스 전투 중 대사 시스템 |
| `boss_timer_system.py` | 보스 타이머 기믹 (시간 제한 전투) |
| `sephiroth_skills.py` | Sephiroth 보스(30층) 전용 스킬 정의 |
| `cain_skills.py` | Abel&Cain 보스(20층) 전용 스킬 정의 |
| `experience_system.py` | 전투 후 경험치 계산 및 레벨업 처리. `RewardCalculator` 클래스, 드랍 아이템 생성 |

## For AI Agents

### Working In This Directory
- 전투 서브시스템은 모두 싱글턴: `get_atb_system()`, `get_brave_system()`, `get_damage_calculator()`
- `CombatState` 흐름: `NOT_STARTED` → `IN_PROGRESS` → `PLAYER_TURN`/`ENEMY_TURN` → `VICTORY`/`DEFEAT`/`FLED`
- ATB 게이지는 `threshold=1000` 도달 시 행동 가능 (`can_act` 프로퍼티)
- `enemy_skills_backup.py`, `damage_calculator_backup.py`는 레거시 백업 — 수정 금지
- 보스 스킬 추가 시 해당 `*_skills.py` 파일에만 추가

### Testing Requirements
- 전투 테스트: `tests/test_combat*.py` 확인
- 보스 기믹 테스트: `src/ui/boss_test_mode.py` (인터랙티브 테스트 UI)
- ATB/Brave 단위 테스트는 싱글턴 리셋 후 진행

### Common Patterns
```python
# 전투 시작
from src.combat.combat_manager import CombatManager, CombatState
manager = CombatManager()
manager.start_combat(allies=party.members, enemies=enemy_list)

# ATB 시스템
from src.combat.atb_system import get_atb_system
atb = get_atb_system()
atb.register(character)
atb.update(delta_time)
ready = atb.get_ready_actors()

# 상태이상 적용
from src.combat.status_effects import StatusType, StatusEffect
effect = StatusEffect(type=StatusType.POISON, duration=3, value=50)
character.status_manager.apply(effect)
```

## Dependencies

### Internal
- `src.core.config` — 전투 설정 로드 (`combat.*` 키)
- `src.core.event_bus` — `Events.COMBAT_*`, `Events.CHARACTER_*` 이벤트 발행
- `src.core.logger` — 전투 로그
- `src.core.vibration_system` — 피격/스킬 진동 피드백
- `src.character.stats` — `Stats` enum으로 ATK/DEF/SPD 접근
- `src.character.gimmick_updater` — 기믹 특성 업데이트
- `src.audio` — 전투 효과음

### External
- 없음 (순수 Python)

<!-- MANUAL: -->
