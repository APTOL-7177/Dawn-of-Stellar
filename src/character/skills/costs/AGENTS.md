<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# character/skills/costs/

## Purpose
스킬 사용 비용 구현체. `SkillCost` 추상 인터페이스를 구현하는 구체적인 비용 타입들을 정의한다.

## Key Files

| File | Description |
|------|-------------|
| `base.py` | `SkillCost` 추상 기반 클래스. `can_afford(user, context)` / `pay(user, context)` 인터페이스 정의 |
| `mp_cost.py` | MP 소모 비용. 가장 일반적인 스킬 비용 |
| `hp_cost.py` | HP 소모 비용. 자기 HP를 소비하는 스킬용 |
| `stack_cost.py` | 스택 소모 비용. 직업 고유 스택 자원 소비 |
| `gimmick_cost.py` | 기믹 자원 소모 비용. 직업 기믹 게이지 소비 |

## For AI Agents

### Working In This Directory
- 모든 비용 클래스는 `base.py`의 `SkillCost`를 상속
- `can_afford(user, context) -> (bool, str)` : 비용 지불 가능 여부와 실패 이유 반환
- `pay(user, context)` : 실제 비용 차감 (can_afford 확인 후 호출)
- 새 비용 타입 추가 시 `base.py` 상속 + `__init__.py` 등록

### Testing Requirements
- 단위 테스트: 각 비용 타입에 대해 충분한 자원/부족한 자원 상황 테스트

### Common Patterns
```python
# MP 비용 생성
from src.character.skills.costs.mp_cost import MPCost
cost = MPCost(amount=50)
can, reason = cost.can_afford(character, context={})
if can:
    cost.pay(character, context={})

# 스킬에 비용 추가
skill.costs.append(MPCost(50))
skill.costs.append(HPCost(10))  # 복수 비용 가능
```

## Dependencies

### Internal
- `src.character.stats` — MP/HP 현재값 접근

### External
- 없음

<!-- MANUAL: -->
