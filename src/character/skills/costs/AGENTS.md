<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# character/skills/costs - 스킬 코스트 시스템

## Purpose

스킬 사용 시 소비되는 자원을 정의하는 플러그인 시스템. MP, HP, 기믹, 스택 기반 코스트를 지원합니다.

## Key Files

| File | Description |
|------|-------------|
| `base.py` | SkillCost 기본 클래스 (인터페이스) |
| `mp_cost.py` | MP 코스트 구현 |
| `hp_cost.py` | HP 코스트 구현 (다크 나이트 등) |
| `gimmick_cost.py` | 기믹 게이지 코스트 구현 (직업별 기믹) |
| `stack_cost.py` | 스택 기반 코스트 (누적 사용 제한) |

## For AI Agents

### Working In This Directory

- **새 코스트 유형 추가**: `base.py`에서 SkillCost 상속하여 새 클래스 작성
- **기존 코스트 수정**: 각 코스트 파일의 `calculate()` 메서드 수정
- **코스트 검증**: `validate()` 메서드에서 사용 가능 여부 확인

### Testing Requirements

- 코스트 차감 테스트: 정확한 양 차감 확인
- 코스트 불가능 테스트: 자원 부족 시 스킬 사용 불가
- 코스트 복구 테스트: 전투 중 자원 복구 메커니즘

### Common Patterns

- 전략 패턴 (코스트 유형별 클래스)
- 플러그인 패턴 (스킬에 동적으로 코스트 추가)
- 검증 패턴 (`validate()` 메서드로 사전 확인)

## Dependencies

### Internal
- `../skill.py` - Skill 클래스에서 코스트 사용
- `../../character.py` - 캐릭터 능력치 (MP, HP, 기믹 게이지)

### External
없음 (순수 Python)

<!-- MANUAL: -->
