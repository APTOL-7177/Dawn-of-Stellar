<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# ai/

## Purpose
전투 중 적의 행동을 결정하는 AI 시스템. 난이도별 스킬 사용 확률 조정, 상황 기반 타겟 선택, 스킬/기본 공격 전략 결정을 담당한다.

## Key Files

| File | Description |
|------|-------------|
| `enemy_ai.py` | `EnemyAI` 클래스. `decide_action(allies, enemies)` 메서드로 행동 결정. 난이도별 스킬 사용 배율 적용 |

## For AI Agents

### Working In This Directory
- `EnemyAI(enemy, difficulty)` 생성 시 `difficulty`는 한국어: `"평온"`, `"보통"`, `"도전"`, `"악몽"`, `"지옥"`
- 영어 호환 레거시: `"easy"`, `"normal"`, `"hard"`, `"insane"`, `"hell"`
- `decide_action()` 반환값: `{"type": "attack"|"skill"|"defend", "skill": EnemySkill|None, "target": character}`
- 스킬 선택: `skill.can_use(enemy)` 필터 → 가중치 기반 랜덤 선택
- 기본 공격 폴백: 스킬 없거나 모두 쿨다운 시 `_decide_basic_attack()` 호출
- 적 스킬 정의는 `src/combat/enemy_skills.py` (또는 `enemy_skills_new.py`)에 있음

### Testing Requirements
- AI 결정 테스트: 다양한 전투 상황(저HP, 아군 다수, 강력 스킬 사용 가능)에서 결정 검증
- 난이도별 스킬 빈도 차이 통계 테스트

### Common Patterns
```python
# 적 AI 생성 및 행동 결정
from src.ai.enemy_ai import EnemyAI
ai = EnemyAI(enemy=enemy_character, difficulty="도전")
action = ai.decide_action(
    allies=[enemy_character, enemy2],  # 적 입장의 아군
    enemies=party.members              # 적 입장의 적군 (플레이어)
)
# action["type"] == "skill"이면 action["skill"] 실행
# action["type"] == "attack"이면 기본 공격
```

## Dependencies

### Internal
- `src.combat.enemy_skills` — `EnemySkill`, `SkillTargetType`
- `src.core.logger` — AI 결정 로그

### External
- `random` (표준 라이브러리): 스킬 선택 랜덤성

<!-- MANUAL: -->
