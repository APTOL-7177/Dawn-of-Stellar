<!-- Generated: 2026-03-07 -->

# src - 별빛의 여명 (Dawn of Stellar)

## Purpose

메인 소스 코드 디렉토리. Python 기반 로그라이크 RPG (v3.1.1)로, tcod/pygame 렌더링, 35개 직업, 414+ 스킬, ATB 전투 시스템, 멀티플레이 지원을 포함합니다.

## Key Subdirectories

| Directory | Purpose |
|-----------|---------|
| `core/` | 핵심 유틸리티 (설정, 로거, 이벤트 버스, 진동, 경로) |
| `combat/` | ATB 전투 시스템, 데미지 계산, 적 스킬, Brave 시스템 |
| `world/` | 던전 생성, 탐색, 맵 렌더링, FOV, 타일 시스템 |
| `character/` | 캐릭터, 직업 통계, 기믹, 특성 (skills/ 서브시스템 포함) |
| `character/classes/` | 직업 클래스 정의 |
| `character/skills/` | 스킬 핵심 시스템 (costs/, effects/, job_skills/ 포함) |
| `character/skills/costs/` | MP, HP, 기믹, 스택 코스트 구현 |
| `character/skills/effects/` | 스킬 효과 (데미지, 힐, 버프, 상태이상, 브레이크) |
| `character/skills/job_skills/` | 35개 직업별 스킬 구현 |
| `ui/` | 50+ UI 모듈 (pygame_backend 렌더링, 전투 UI, 인벤토리) |
| `multiplayer/` | P2P 멀티플레이, 세션 관리, 동기화 |
| `tutorial/` | 튜토리얼 시스템, 던전, UI |
| `equipment/` | 장비 및 인벤토리 시스템 |
| `cooking/` | 요리, 폭탄 제작, 약 양조 |
| `gathering/` | 채집, 재료, 채집 가능 객체 |
| `persistence/` | 저장/로드, 메타 진행도 |
| `quest/` | 퀘스트 매니저 |
| `achievement/` | 업적 및 마일스톤 |
| `audio/` | 오디오 매니저 |
| `town/` | 마을, 지도 전환, 층 관리 |
| `story/` | 스토리 시스템 |
| `systems/` | 상처 게이지 시스템 |
| `field/` | 필드 스킬 (요리, 채집) |
| `bot/` | 게임 상태 내보내기, AI 플레이어 봇 |
| `utils/` | 유틸리티 모듈 |
| `ai/`, `gym/`, `rl/` | AI 학습 및 강화학습 모듈 |

## Key Files (Root)

| File | Description |
|------|-------------|
| `__init__.py` | 버전 정보 (v3.1.1) 및 메타데이터 |

## For AI Agents

### Working In This Directory

- **게임 아키텍처**: 큰 변경 전에 각 모듈의 AGENTS.md 참고
- **직업/스킬 추가**: `character/skills/job_skills/` 참고
- **전투 로직**: `combat/` 모듈 참고
- **멀티플레이**: `multiplayer/` 문서 참고
- **UI 변경**: `ui/` 및 `ui/pygame_backend/` 참고

### Testing Requirements

- 단위 테스트: `tests/unit/`
- 통합 테스트: `tests/integration/`
- 멀티플레이 테스트: `tests/test_multiplayer_*.py`
- 직업 테스트: `tests/test_*_remake.py`

### Common Patterns

- YAML 기반 데이터 로딩 (캐릭터, 스킬, 레시피)
- 이벤트 버스 패턴 (core/event_bus.py)
- 상태 기계 (전투, 튜토리얼)
- 이펙트 체인 (스킬 → 데미지 → 상태이상)

## Dependencies

### Internal
- `config.yaml` - 게임 설정
- `data/characters/` - 35개 직업 YAML 정의
- `data/skills/` - 414+ 스킬 YAML 정의
- `data/tutorials/` - 튜토리얼 설정

### External
- `tcod` - 터미널 렌더링 (v14+)
- `pygame` - 그래픽 및 이벤트 처리
- `pyyaml` - YAML 파싱
- `numpy` - 수치 계산

<!-- MANUAL: -->
