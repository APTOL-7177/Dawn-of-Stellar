<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 -->

# character/classes - 직업 클래스 정의

## Purpose

35개 직업의 클래스 정의를 저장합니다. 각 직업의 메타데이터, 기본 스킬, 기믹 유형, 능력치 성장 곡선을 포함합니다.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 직업 클래스 레지스트리 및 팩토리 함수 |

## Subdirectories

현재 이 디렉토리는 Python 클래스 정의를 저장하지 않고, YAML 데이터 파일(`data/characters/`)에서 로드합니다.

## For AI Agents

### Working In This Directory

- **직업 추가**: `data/characters/` 디렉토리에 새 YAML 파일 추가
- **직업 메타데이터**: `__init__.py`의 직업 레지스트리 수정
- **기믹 유형**: `character/gimmick_updater.py`에서 직업별 기믹 로직 구현

### Testing Requirements

- 직업 로드 테스트: 모든 직업이 올바르게 로드되는지 확인
- 직업 능력치 테스트: 각 직업의 기본 능력치가 의도한 범위 내
- 기믹 시스템 테스트: 직업별 기믹 메커니즘 동작

### Common Patterns

- 레지스트리 패턴 (직업 ID → 직업 데이터)
- YAML 기반 데이터 구조
- 직업별 다형성 (기믹, 기본 공격 등)

## Dependencies

### Internal
- `../character.py` - Character 클래스
- `../character_loader.py` - YAML 로드
- `../../data/characters/` - 직업 YAML 정의

### External
- `pyyaml` - YAML 파싱

<!-- MANUAL: -->
