<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# systems/

## Purpose
개별 게임 시스템 모듈. 현재 상처(Wound) 시스템이 핵심으로, HP 데미지의 일부를 영구 상처로 전환하여 최대 HP를 감소시키는 메커니즘을 구현한다.

## Key Files

| File | Description |
|------|-------------|
| `wound_system.py` | `WoundSystem` 클래스. 데미지 일부를 상처로 전환(기본 25%), 최대 HP의 50%까지 상처 누적, 회복 아이템 효율 1.5배 |

## For AI Agents

### Working In This Directory
- `WoundSystem`은 싱글턴 패턴 — `get_wound_system()` 또는 직접 인스턴스화
- 상처 임계값: `wound_threshold=0.25` (데미지의 25%가 상처)
- 최대 상처: `max_wound_percentage=0.5` (최대 HP의 50%까지)
- 자연 회복률: `natural_healing_rate=0.01` (턴당 1%)
- 상처 시스템 활성화 여부: `config.get("wound_system.enabled", True)`
- `apply_damage(character, damage)` → `{"hp_damage": int, "wound": int}` 반환
- `Events.CHARACTER_HP_CHANGE` 이벤트 구독으로 자동 상처 처리

### Testing Requirements
- 상처 누적 테스트: 연속 피격 후 `character.wound` 값 검증
- 최대 상처 상한선 테스트: 50% 초과 불가 확인
- 시스템 비활성화 테스트: `enabled=False` 시 상처 0 확인

### Common Patterns
```python
# 상처 시스템 적용
from src.systems.wound_system import WoundSystem
wound_sys = WoundSystem()
result = wound_sys.apply_damage(character, damage=100)
# result["hp_damage"] = 100, result["wound"] = 25

# 상처 자연 회복 (턴 종료 시)
wound_sys.natural_heal(character)

# 상처 치료 (회복 아이템)
wound_sys.heal_wound(character, heal_amount=50)
```

## Dependencies

### Internal
- `src.core.event_bus` — `Events.CHARACTER_HP_CHANGE` 구독
- `src.core.config` — `wound_system.*` 설정
- `src.core.logger` — 상처 로그

### External
- 없음

<!-- MANUAL: -->
