<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# character/skills - 스킬 시스템

## Purpose

게임의 414+ 스킬을 관리하는 중앙 시스템. YAML 기반 스킬 정의, 스킬 로더, 스킬 매니저, 효과 시스템(costs/, effects/), 35개 직업의 스킬 구현(job_skills/)을 포함합니다.

## Key Files

| File | Description |
|------|-------------|
| `skill.py` | 스킬 기본 클래스 (이름, 설명, 코스트, 효과, 애니메이션) |
| `yaml_skill_loader.py` | YAML 파일에서 스킬 정의 로드 |
| `skill_manager.py` | 캐릭터별 스킬 관리 (스킬 학습, 환원, 사용) |
| `skill_initializer.py` | 스킬 인스턴스 생성 및 초기화 |
| `custom_handlers.py` | 특수 스킬 핸들러 (커스텀 로직) |
| `teamwork_skill.py` | 팀워크 스킬 (파티 협력) |
| `teamwork_effects.py` | 팀워크 효과 구현 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `costs/` | 코스트 시스템 (MP, HP, 기믹, 스택) - 자세한 내용은 costs/AGENTS.md 참고 |
| `effects/` | 스킬 효과 (데미지, 힐, 버프, 상태이상, 브레이크) - 자세한 내용은 effects/AGENTS.md 참고 |
| `job_skills/` | 35개 직업별 스킬 구현 - 자세한 내용은 job_skills/AGENTS.md 참고 |

## For AI Agents

### Working In This Directory

- **스킬 기본 로직**: `skill.py` 수정
- **스킬 로드**: `yaml_skill_loader.py` 수정
- **스킬 추가**: `data/skills/` 디렉토리에 YAML 파일 추가
- **매니저 로직**: `skill_manager.py` 수정
- **팀워크 스킬**: `teamwork_skill.py` 및 `teamwork_effects.py` 수정

### Testing Requirements

- 스킬 로드 테스트: YAML 파싱 및 클래스 생성
- 스킬 사용 테스트: 코스트 차감, 효과 적용
- 팀워크 스킬 테스트: 파티원 상호작용
- 효과 체인 테스트: 스킬 → 코스트 → 효과 순서

### Common Patterns

- 전략 패턴 (코스트, 효과는 플러그인 형태)
- 데코레이터 패턴 (스킬 효과 체인)
- YAML 기반 데이터 정의
- 이벤트 콜백 (스킬 사용, 효과 적용 시)

## Dependencies

### Internal
- `../character.py` - 캐릭터에 적용할 스킬
- `../stats.py` - 능력치 기반 데미지 계산
- `../../combat/damage_calculator.py` - 데미지 계산
- `../../core/event_bus.py` - 스킬 사용 이벤트
- `costs/` - 코스트 구현
- `effects/` - 효과 구현
- `job_skills/` - 직업별 스킬

### External
- `pyyaml` - YAML 스킬 로드
- `data/skills/` - 414+ 스킬 YAML 파일
- `data/teamwork_skills.yaml` - 팀워크 스킬 정의

<!-- MANUAL: -->
