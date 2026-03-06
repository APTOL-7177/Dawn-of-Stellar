<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# Dawn of Stellar

## Purpose
DOS 레트로 스타일 턴제 RPG 게임. Python + tcod(libtcod) 엔진 기반. ATB(Active Time Battle) 전투 시스템, Brave 시스템, 35개 직업, 414개 스킬, 멀티플레이어 지원.

## Key Files
| File | Description |
|------|-------------|
| `main.py` | 게임 엔트리포인트 |
| `launcher.py` | 게임 런처 (모드 선택) |
| `launcher_cli.py` | CLI 런처 |
| `config.yaml` | 게임 전역 설정 |
| `requirements.txt` | Python 의존성 |
| `setup.py` | 패키지 설정 |
| `pyproject.toml` | 빌드 설정 |
| `build_final.bat` | Windows 패키징 스크립트 |
| `build_final_linux.sh` | Linux 패키징 스크립트 |
| `install.nsi` | Windows 설치관리자 |
| `run_multiplayer_tests.py` | 멀티플레이어 통합 테스트 실행 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `src/` | 게임 소스 코드 - 245개 Python 파일, 21개 모듈 (see `src/AGENTS.md`) |
| `data/` | 게임 데이터 - 스킬, 캐릭터, 튜토리얼 YAML (see `data/AGENTS.md`) |
| `docs/` | 설계 문서, 위키, 밸런스 가이드 - 30개 문서 (see `docs/AGENTS.md`) |
| `tests/` | pytest 테스트 스위트 - 53개 파일 (see `tests/AGENTS.md`) |
| `scripts/` | 유틸리티 스크립트 - 밸런싱, 검증, 분석 - 63개 (see `scripts/AGENTS.md`) |
| `config/` | 입력/진동/메타 설정 - 4개 설정 파일 (see `config/AGENTS.md`) |
| `assets/` | 오디오 리소스 - 398개 파일 (bg:24, me:8, se:366) (see `assets/AGENTS.md`) |
| `archive/` | 미사용 스킬 백업, 설계 문서 (see `archive/AGENTS.md`) |
| `examples/` | 예제 코드 (see `examples/AGENTS.md`) |
| `web/` | 실험적 브라우저 빌드 (see `web/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- Python 3.10+, 4-space indent, 100-char line limit
- Black/isort/pylint/mypy 포맷팅 및 타입 체크
- snake_case 함수/변수, PascalCase 클래스
- 도메인 약어 허용: hp, mp, atb, brv
- YAML 키는 lowercase snake_case, 스킬/직업 ID는 고유하고 안정적으로 유지 (세이브 호환성)
- 복잡한 시스템에는 docstring 작성, 주석은 코드 반복이 아닌 의도 설명에 집중

### Build & Run
- 설치: `pip install -e .[dev]` 또는 `pip install -r requirements.txt`
- 실행: `python main.py` (`--dev` 모든 직업 해금, `--debug --log=DEBUG` 상세 로그)
- 패키징: `build_final_linux.sh` 또는 `build_final.bat`
- 린트: `black src tests && isort src tests`
- 정적 분석: `pylint src`
- 타입체크: `mypy src`

### Testing Requirements
- `pytest tests` (전체)
- `pytest tests -m "not slow"` (빠른 테스트)
- `pytest tests --cov=src --cov-report=term-missing` (커버리지)
- 멀티플레이어 통합 테스트: `python run_multiplayer_tests.py`
- Pytest 마커 strict 모드 (`--strict-markers`), 기본 옵션 `-ra -q`

### Common Patterns
- Conventional Commit: feat:, fix:, refactor:, docs:, test:, chore:
- 한국어/영어 커밋 메시지 모두 허용, 현재 시제 짧게
- PR 오픈 전: 변경 동기 기술, 실행한 테스트 명령 목록, 데이터/에셋 영향 명시
- `dist/`, `user_data/` 는 커밋 금지

## Dependencies

### External
- Python 3.10+
- tcod (libtcod) - 로그라이크 엔진 (콘솔, FOV, 경로 탐색)
- pygame - 오디오/입력
- PyYAML - 데이터 로딩
- numpy - 맵 처리

<!-- MANUAL: -->
