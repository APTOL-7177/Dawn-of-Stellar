<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# combat - ATB 전투 시스템

## Purpose

Final Fantasy 스타일의 Brave 공격 전투 시스템. ATB(Active Time Battle) 큐, 데미지 계산, 스킬 발동, 상태이상, 적 AI, 보스 기믹을 포함합니다.

## Key Files

| File | Description |
|------|-------------|
| `combat_manager.py` | 전투 흐름 관리 (턴 시스템, 라운드, 패배 조건) |
| `atb_system.py` | ATB 큐 관리 (속도, 턴 계산, 액션 스케줄링) |
| `damage_calculator.py` | 데미지 계산 (공격력, 방어력, 약점, 치명타) |
| `casting_system.py` | 스킬 발동 및 캐스팅 시간 |
| `enemy_skills.py` | 적 AI 스킬 선택 로직 |
| `brave_system.py` | Brave 공격 메커니즘 (Brave 포인트, 기본 공격 강화) |
| `status_effects.py` | 상태이상 관리 (중독, 마비, 둔화, 침묵) |
| `experience_system.py` | 경험치 및 레벨업 계산 |
| `boss_gimmicks.py` | 보스 기믹 (HP 게이지, 특수 패턴) |
| `boss_dialogue.py` | 보스 대사 시스템 |
| `boss_timer_system.py` | 보스 타이머 및 턴 제한 |
| `cain_skills.py` | Cain 보스 전용 스킬 |
| `sephiroth_skills.py` | Sephiroth 보스 전용 스킬 |

## For AI Agents

### Working In This Directory

- **데미지 로직 변경**: `damage_calculator.py` 수정
- **적 AI 추가**: `enemy_skills.py`에서 선택 로직 구현
- **상태이상 추가**: `status_effects.py`에 새 효과 클래스 추가
- **전투 흐름 변경**: `combat_manager.py`의 상태 머신 수정
- **보스 기믹**: `boss_gimmicks.py`에서 패턴 정의

### Testing Requirements

- ATB 시스템 테스트: 턴 순서, 속도 계산
- 데미지 계산 테스트: 여러 조건에서의 일관성
- 상태이상 테스트: 적용, 해제, 면역 로직
- 적 AI 테스트: 스킬 선택 합리성
- 보스 기믹 테스트: 패턴 변환, 체력 임계값

### Common Patterns

- 효과 체인 (스킬 → 데미지 → 상태이상 → 게이지)
- 우선순위 큐 (ATB 시스템)
- 상태 머신 (전투 상태: 플레이어 턴, 적 턴, 스킬 캐스팅)
- 이벤트 콜백 (피해 시 회복 트리거 등)

## Dependencies

### Internal
- `character/` - 캐릭터 데이터, 스킬
- `character/skills/effects/` - 스킬 효과 (damage_effect 등)
- `core/event_bus.py` - 전투 이벤트 발행
- `core/logger.py` - 디버그 로깅

### External
- `numpy` - 데미지 계산 가속화
- `pyyaml` - 스킬 YAML 파싱

<!-- MANUAL: -->
