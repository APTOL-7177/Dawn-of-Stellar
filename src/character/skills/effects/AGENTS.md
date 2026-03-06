<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# character/skills/effects/

## Purpose
스킬 효과 구현체. `SkillEffect` 추상 인터페이스를 구현하는 25개 이상의 구체적인 효과 타입. 데미지, 힐, 버프, 상태이상, BRV 조작 등을 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `base.py` | `SkillEffect` 추상 기반 클래스. `apply(user, targets, context)` 인터페이스 정의 |
| `damage_effect.py` | ATK 기반 데미지 효과 (가장 일반적) |
| `fixed_damage_effect.py` | 고정 수치 데미지 효과 |
| `heal_effect.py` | HP 회복 효과 |
| `buff_effect.py` | 스탯 버프/디버프 효과 |
| `shield_effect.py` | 보호막(쉴드) 부여 효과 |
| `status_effect.py` | 상태이상 적용 효과 (독, 화상, 빙결 등) |
| `atb_effect.py` | ATB 게이지 조작 효과 (가속/감속) |
| `break_effect.py` | BREAK 유발 효과 |
| `lifesteal_effect.py` | 흡혈 효과 (데미지 → HP 회복) |
| `cleanse_effect.py` | 상태이상 해제 효과 |
| `protect_effect.py` | 보호 효과 (피해 대신 받기) |
| `taunt_effect.py` | 도발 효과 (타겟 강제 변경) |
| `steal_buff_effect.py` | 버프 탈취 효과 |
| `support_fire_effect.py` | 지원 사격 효과 |
| `gimmick_effect.py` | 직업 기믹 트리거 효과 |
| `archmage_effects.py` | 대마법사 직업 전용 특수 효과 |

## For AI Agents

### Working In This Directory
- 모든 효과 클래스는 `base.py`의 `SkillEffect`를 상속
- `apply(user, targets, context) -> SkillResult` 시그니처 준수
- 효과는 순서대로 실행됨 — `skill.effects` 리스트 순서가 중요
- 새 효과 추가 시 `base.py` 상속 + `__init__.py` export 추가
- `context` 딕셔너리에는 전투 상태 정보가 포함됨

### Testing Requirements
- 각 효과 단위 테스트: 더미 캐릭터에 적용 후 결과 검증
- 복합 효과 테스트: 여러 효과 순서 적용 시나리오

### Common Patterns
```python
# 데미지 효과 생성
from src.character.skills.effects.damage_effect import DamageEffect
effect = DamageEffect(power=1.5, element="fire")
result = effect.apply(user=caster, targets=[enemy], context={"brave_system": brave})

# 스킬에 효과 추가
skill.effects.append(DamageEffect(power=2.0))
skill.effects.append(StatusEffect(status_type="burn", duration=3))
```

## Dependencies

### Internal
- `src.combat.damage_calculator` — 데미지 계산
- `src.combat.brave_system` — BRV 조작
- `src.combat.status_effects` — 상태이상 적용
- `src.combat.atb_system` — ATB 게이지 조작
- `src.character.stats` — 스탯 접근

### External
- 없음

<!-- MANUAL: -->
