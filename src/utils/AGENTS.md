<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# utils

## Purpose
프로젝트 전반에서 공유하는 범용 유틸리티 모듈. 현재는 `__init__.py` 단일 파일만 존재하며 공개 인터페이스가 비어 있다.

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 빈 모듈 초기화 파일 (현재 내용 없음) |

## For AI Agents

### Working In This Directory
- 현재 이 디렉토리는 실질적인 구현 없이 예약된 상태
- 범용 유틸리티가 필요한 경우 이 모듈에 추가하는 것이 적절
- 기존 유틸리티성 코드는 각 도메인 모듈(`src/core/logger.py`, `src/core/config.py` 등)에 분산되어 있음
- 새 유틸리티 추가 시 `src/core/`와 중복되지 않도록 확인

### Testing Requirements
- 현재 테스트 불필요
- 유틸리티 함수 추가 시 단위 테스트 필수

### Common Patterns
```python
# 현재 비어 있음
# from src.utils import some_util
```

## Dependencies

### Internal
없음

### External
없음

<!-- MANUAL: -->
