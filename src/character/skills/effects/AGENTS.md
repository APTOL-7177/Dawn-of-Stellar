<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# character/skills/effects - 스킬 효과 시스템

## Purpose

스킬 사용 시 발생하는 효과를 정의하는 플러그인 시스템. 데미지, 힐, 버프, 상태이상, 브레이크, 특수 효과를 포함합니다.

## Key Files

| File | Description |
|------|-------------|
| `base.py` | SkillEffect 기본 클래스 (인터페이스) |
| `damage_effect.py` | 물리/마법 데미지 (약점, 치명타 포함) |
| `fixed_damage_effect.py` | 고정 데미지 (무시 불가) |
| `heal_effect.py` | HP 회복 (대상 선택 지원) |
| `buff_effect.py` | 능력치 증가 (STR, DEF 등) |
| `status_effect.py` | 상태이상 (중독, 마비, 침묵 등) |
| `break_effect.py` | 브레이크 효과 (특수 상태) |
| `protect_effect.py` | 보호/차단 (데미지 감소) |
| `shield_effect.py` | 보호막 (임시 HP) |
| `taunt_effect.py` | 도발 (특정 대상 집중) |
| `lifesteal_effect.py` | 흡수 (데미지의 일부 회복) |
| `atb_effect.py` | ATB 조작 (속도 변경) |
| `gimmick_effect.py` | 기믹 게이지 조작 |
| `cleanse_effect.py` | 상태이상 제거 |
| `steal_buff_effect.py` | 버프 탈취 |
| `support_fire_effect.py` | 지원 공격 (아처 스킬) |
| `archmage_effects.py` | 아크메이지 특화 효과 |

## For AI Agents

### Working In This Directory

- **새 효과 유형 추가**: `base.py`에서 SkillEffect 상속하여 새 클래스 작성
- **기존 효과 수정**: 각 효과 파일의 `apply()` 메서드 수정
- **효과 체인**: `apply()` 메서드의 반환값으로 다음 효과 연결

### Testing Requirements

- 효과 적용 테스트: 올바른 능력치/상태 변화 확인
- 효과 계산 테스트: 여러 버프/디버프 중첩 시 순서 확인
- 면역 테스트: 특성/상태로 인한 효과 무효화 확인
- 시각적 피드백 테스트: 이펙트 애니메이션 동작

### Common Patterns

- 전략 패턴 (효과 유형별 클래스)
- 데코레이터 패턴 (효과 체인)
- 플러그인 패턴 (스킬에 동적으로 효과 추가)
- 이벤트 콜백 (효과 적용 전/후 이벤트)

## Dependencies

### Internal
- `../skill.py` - Skill 클래스에서 효과 사용
- `../../character.py` - 캐릭터 능력치, 상태이상
- `../../combat/damage_calculator.py` - 데미지 계산
- `../../combat/status_effects.py` - 상태이상 관리

### External
- `numpy` - 데미지 계산 (행렬 연산)

<!-- MANUAL: -->
