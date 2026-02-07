# Add Skill Command

새로운 스킬을 추가합니다.

## 사용법
`/add-skill <skill_name> <skill_type>`

예: `/add-skill shadow_strike brv_attack`

## 스킬 타입
- `brv_attack`: BRV 공격
- `hp_attack`: HP 공격
- `brv_hp_attack`: BRV+HP 공격
- `support`: 지원 스킬
- `debuff`: 디버프
- `ultimate`: 궁극기

## 실행 내용

### 1. 스킬 데이터 파일 생성
`data/skills/<skill_name>.yaml`:
```yaml
id: shadow_strike
name: "그림자 강타"
name_en: "Shadow Strike"
type: brv_attack
description: "그림자에서 나타나 강력한 일격을 가합니다"

costs:
  mp: 25
  cast_time: 1.2

effects:
  - type: damage
    element: physical
    multiplier: 2.8
    stat_base: strength
    ignore_defense: 0.2  # 20% 방어 관통

  - type: status
    effect: blind
    duration: 2
    chance: 0.3

  - type: brv_break_bonus
    multiplier: 1.5

requirements:
  min_level: 1
  classes:
    - 암살자
    - 닌자

animation:
  effect: "shadow_slash"
  sound: "critical_hit"
```

### 2. 스킬 구현 클래스 생성
`src/character/skills/<skill_name>.py`:
```python
from src.character.skills.skill_base import Skill, SkillType, SkillEffect
from typing import Dict, Any

class ShadowStrike(Skill):
    """그림자 강타 스킬"""

    def __init__(self):
        super().__init__(
            id="shadow_strike",
            name="그림자 강타",
            skill_type=SkillType.BRV_ATTACK,
            mp_cost=25,
            cast_time=1.2
        )

    def execute(self, context: Dict[str, Any]) -> SkillEffect:
        """스킬 실행"""
        user = context["user"]
        target = context["target"]

        # 데미지 계산
        base_damage = user.strength * 2.8
        defense_ignored = target.defense * 0.2
        effective_defense = target.defense - defense_ignored

        final_damage = max(0, base_damage - effective_defense)

        # 상태 이상 판정
        effects = []
        if self.roll_chance(0.3):
            effects.append({
                "type": "blind",
                "duration": 2
            })

        return SkillEffect(
            damage=final_damage,
            damage_type="brv",
            status_effects=effects,
            animation="shadow_slash",
            sound="critical_hit"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        """사용 가능 여부"""
        return user.mp >= self.mp_cost
```

### 3. 스킬 등록
`src/character/skills/__init__.py` 업데이트:
```python
from .shadow_strike import ShadowStrike

SKILL_REGISTRY = {
    # ... 기존 스킬들
    "shadow_strike": ShadowStrike,
}
```

### 4. 스킬 데이터베이스 업데이트
`src/character/skills/skill_database.py` 에 등록

### 5. 테스트 작성
`tests/unit/skills/test_<skill_name>.py`:
```python
import pytest
from src.character.skills.shadow_strike import ShadowStrike
from src.character.character import Character

def test_shadow_strike_damage():
    """그림자 강타 데미지 계산 테스트"""
    skill = ShadowStrike()
    user = Character("테스트", "암살자")
    target = Character("더미", "전사")

    context = {"user": user, "target": target}
    effect = skill.execute(context)

    assert effect.damage > 0
    assert effect.damage_type == "brv"

def test_shadow_strike_blind():
    """그림자 강타 실명 효과 테스트"""
    # 테스트 구현
    pass
```

### 6. 문서 업데이트
`docs/guides/skills.md` 에 스킬 설명 추가

## 체크리스트
- [ ] 스킬 데이터 파일 생성
- [ ] 스킬 구현 클래스 생성
- [ ] 스킬 등록
- [ ] 데이터베이스 업데이트
- [ ] 테스트 작성
- [ ] 문서 업데이트
- [ ] 밸런스 검증
