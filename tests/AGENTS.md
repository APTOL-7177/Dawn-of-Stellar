<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# tests/

## Purpose
게임 테스트 스위트. pytest 기반 테스트: 멀티플레이어, 팀워크, 단위 테스트, 통합 테스트를 포함합니다.

## Key Files
| File | Description |
|------|-------------|
| test_multiplayer_*.py | 멀티플레이어 기능 테스트 (9개 파일) |
| test_teamwork_*.py | 팀워크 스킬 테스트 (4개 파일) |
| test_*_remake.py | 직업 리메이크 검증 테스트 |
| test_character_*.py | 캐릭터 시스템 테스트 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| unit/ | 단위 테스트 (combat/, tutorial/ 하위 구조) |
| integration/ | 통합 테스트 (combat_flow, multiplayer_flow 등) |

## For AI Agents

### Working In This Directory
- pytest 로 실행: `pytest tests/`
- test_*.py 파일명 규칙 자동 발견
- conftest.py 는 pytest 픽스처 정의 (있으면)
- unit/ 은 단일 모듈 테스트, integration/ 은 시스템 연동 테스트

### Common Patterns
- 테스트 함수: `test_feature_name()` 형식
- 픽스처: @pytest.fixture 로 테스트 환경 설정
- 어설션: assert 로 결과 검증
- Mocking: unittest.mock 으로 의존성 격리

## Dependencies
- pytest - 테스트 프레임워크
- src/ - 테스트 대상 모듈
- data/ - 테스트 데이터 (YAML)

<!-- MANUAL: -->
