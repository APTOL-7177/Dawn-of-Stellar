<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# Dawn of Stellar (별빛의 여명)

## Purpose
Python 기반 로그라이크 RPG 게임. TCOD 엔진과 Pygame을 사용하며, Final Fantasy 스타일의 ATB(Active Time Battle) 전투 시스템, 36개 직업, 414개+ 스킬, 멀티플레이어, AI/RL 봇, 스토리 모드를 제공한다. 버전 3.1.1.

## Key Files

| File | Description |
|------|-------------|
| `main.py` | 게임 메인 엔트리 포인트 (CLI 인자 파싱, 게임 루프 시작) |
| `config.yaml` | 게임 전역 설정 (오디오, AI, 접근성, 전투 밸런스 등) |
| `requirements.txt` | Python 의존성 목록 |
| `pyproject.toml` | 프로젝트 메타데이터 |
| `launcher.py` | 게임 런처 (자동 업데이트 포함) |
| `build.spec` | PyInstaller 빌드 스펙 |
| `install.nsi` | NSIS 인스톨러 스크립트 |
| `bot_client.py` | AI 봇 클라이언트 |
| `llm_macro.py` | LLM 기반 매크로 플레이어 |
| `GAME_REFERENCE.md` | 게임 레퍼런스 문서 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `src/` | 게임 소스 코드 전체 (see `src/AGENTS.md`) |
| `data/` | YAML 기반 게임 데이터 - 캐릭터, 스킬, 튜토리얼 (see `data/AGENTS.md`) |
| `docs/` | 설계 문서, 위키, 밸런스 문서 (see `docs/AGENTS.md`) |
| `tests/` | 테스트 스위트 (see `tests/AGENTS.md`) |
| `scripts/` | 개발/분석 유틸리티 스크립트 (see `scripts/AGENTS.md`) |
| `config/` | 키바인딩, 게임패드 매핑 등 설정 파일 (see `config/AGENTS.md`) |
| `assets/` | 오디오, 이미지 등 게임 리소스 (see `assets/AGENTS.md`) |
| `build/` | 빌드 설정 및 배포 (see `build/AGENTS.md`) |
| `training/` | RL 학습 관련 파일 (see `training/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- Python 3.10+ 필수. 핵심 의존성: tcod, pygame, pyyaml, websockets
- `main.py`가 게임 엔트리 포인트. `--dev` 플래그로 개발 모드 실행 가능
- 게임 데이터는 `data/` 하위 YAML 파일로 관리 (코드 수정 없이 밸런스 조정 가능)
- 한국어가 주 언어 (코드 주석, 게임 텍스트 모두 한국어)
- Install: `pip install -r requirements.txt`
- Run: `python main.py` (개발모드: `--dev`, 디버그: `--debug --log=DEBUG`)
- Lint: `black src tests` / `isort src tests` / `pylint src` / `mypy src`

### Testing Requirements
- `pytest tests/` 로 전체 테스트 실행
- 빠른 테스트: `pytest tests -m "not slow"`
- 커버리지: `pytest tests --cov=src --cov-report=term-missing`
- 전투 시스템 변경 시 `tests/unit/combat/` 테스트 확인
- 멀티플레이어 변경 시 `tests/test_multiplayer_*.py` 확인

### Common Patterns
- YAML 데이터 드리븐 설계 (캐릭터, 스킬, 레시피 등)
- 이벤트 버스 패턴 (`src/core/event_bus.py`)
- ATB (Active Time Battle) 전투 시스템
- 직업별 기믹 시스템 (각 직업 고유 메커니즘)
- snake_case 함수/변수, PascalCase 클래스
- 도메인 약어 허용: `hp`, `mp`, `atb`, `brv`
- Conventional Commit: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

## Dependencies

### External
- `tcod` >= 16.0 - 로그라이크 렌더링 엔진
- `pygame` >= 2.5 - 오디오 및 입력 처리
- `pyyaml` >= 6.0 - YAML 데이터 파싱
- `websockets` >= 12.0 - 멀티플레이어 네트워킹
- `numpy` >= 1.26 - 수치 계산 (tcod 의존성)
- `openai` >= 1.0 - LLM 통합 (선택)

<!-- MANUAL: -->
