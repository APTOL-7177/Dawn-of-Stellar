<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# character - 캐릭터 시스템

## Purpose

캐릭터 데이터, 직업 통계, 기믹 시스템, 특성(Trait), 기본 공격을 관리합니다. 스킬 시스템은 `skills/` 서브디렉토리에서 관리됩니다.

## Key Files

| File | Description |
|------|-------------|
| `character.py` | 캐릭터 클래스 (HP, MP, 능력치, 직업, 상태) |
| `character_loader.py` | YAML에서 캐릭터 정의 로드 |
| `job_stats_loader.py` | 직업별 기본 능력치 및 성장률 로드 |
| `gimmick_updater.py` | 기믹 게이지 업데이트 (직업별 기믹 메커니즘) |
| `basic_attacks.py` | 기본 공격 로직 및 계산 |
| `stats.py` | 능력치 데이터 구조 (STR, DEX, VIT 등) |
| `skill_types.py` | 스킬 타입 분류 (물리, 마법, 힐 등) |
| `trait_effects.py` | 특성(Trait) 효과 구현 |
| `gimmick_trait_effects.py` | 기믹 기반 특성 효과 |
| `party.py` | 파티 관리 (최대 4명) |
| `upgrade_applier.py` | 능력치 증가 적용 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `skills/` | 스킬 시스템 (skill.py, costs/, effects/, job_skills/) - 자세한 내용은 skills/AGENTS.md 참고 |
| `classes/` | 직업 클래스 정의 - 자세한 내용은 classes/AGENTS.md 참고 |

## For AI Agents

### Working In This Directory

- **캐릭터 속성 추가**: `character.py`의 Character 클래스 수정
- **직업 능력치 조정**: `job_stats_loader.py`의 직업별 데이터 수정
- **기믹 시스템**: `gimmick_updater.py`에서 직업별 기믹 로직 추가
- **특성 추가**: `trait_effects.py`에서 새 특성 효과 클래스 구현
- **기본 공격 변경**: `basic_attacks.py` 수정

### Testing Requirements

- 캐릭터 생성 테스트: 직업별 기본 능력치 확인
- 능력치 성장 테스트: 레벨업 시 올바른 증가 확인
- 기믹 시스템 테스트: 직업별 기믹 게이지 동작
- 특성 효과 테스트: 각 특성의 버프/디버프 적용
- 파티 관리 테스트: 4명 이상 추가 방지

### Common Patterns

- YAML 기반 데이터 로드 (character_loader)
- 직업별 다형성 (Gimmick, Trait 처리)
- 능력치 캐싱 (초기화 후 계산)
- 이벤트 기반 업데이트 (레벨업, 장비 장착 시)

## Dependencies

### Internal
- `skills/` - 캐릭터 스킬, 스킬 매니저
- `combat/` - 전투 중 능력치 사용
- `core/event_bus.py` - 레벨업, 상태 변화 이벤트
- `core/logger.py` - 디버그 로깅

### External
- `pyyaml` - 캐릭터/직업 YAML 파싱
- `numpy` - 능력치 계산 (행렬 연산)

<!-- MANUAL: -->
