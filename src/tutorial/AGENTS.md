<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# 튜토리얼 시스템

## 목적
신규 플레이어를 위한 단계별 튜토리얼 시스템. 인터랙티브 스토리, 던전 기반 튜토리얼, 직업 선택, 게임 메카닉 교육을 포함합니다. YAML 기반 튜토리얼 정의, 스토리 모드 통합, 진행 추적을 지원합니다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| tutorial_manager.py | 튜토리얼 상태 관리 및 진행 추적 |
| tutorial_dungeon.py | 튜토리얼 던전 생성 및 관리 |
| tutorial_playable.py | 튜토리얼 게임플레이 루프 |
| tutorial_step.py | 튜토리얼 단계 정의 및 검증 |
| job_selection_ui.py | 직업 선택 UI |
| story_integration.py | 스토리 모드와의 통합 |
| story_playable.py | 스토리 게임플레이 루프 |
| story_runner.py | 스토리 실행 엔진 |
| story_tutorial_manager.py | 스토리 튜토리얼 관리 |
| tutorial_bot.py | 튜토리얼 AI 봇 (NPC) |
| tutorial_integration.py | 튜토리얼 통합 헬퍼 |
| tutorial_mode.py | 튜토리얼 모드 진입점 |
| tutorial_ui.py | 튜토리얼 UI 요소 |
| tutorial_viewer.py | 튜토리얼 뷰어 (디버그/검토용) |

## AI 에이전트를 위한 가이드
### 이 디렉토리에서 작업할 때
- 튜토리얼 단계는 YAML 정의를 따릅니다 (`data/tutorials/*.yaml`).
- 진행은 조건 기반으로 검증됩니다 (스킬 사용, 아이템 수집 등).
- 튜토리얼은 스토리 모드와 일반 모드에서 실행될 수 있습니다.
- 과제 완료는 자동으로 감지되거나 플레이어 입력으로 승인됩니다.

### 테스트 요구사항
- 모든 튜토리얼 경로가 완료 가능함을 검증합니다.
- 조건 검증이 정확한지 확인합니다.
- UI 오버레이가 게임 화면을 가리지 않는지 시각적으로 검증합니다.
- 완료 후 메인 게임으로의 전환이 매끄러운지 확인합니다.

### 일반적인 패턴
- 튜토리얼은 상태 머신으로 진행됩니다 (대기 → 진행 중 → 완료).
- 각 단계는 목표(goal), 설명(description), 검증 조건(validation)을 가집니다.
- 플레이어 행동은 자동 감지되거나 명시적 승인(클릭)을 기다립니다.

## 의존성
### 내부
- `src/character/` - 캐릭터 생성
- `src/combat/` - 전투 튜토리얼
- `src/world/` - 던전 생성
- `src/ui/` - 튜토리얼 UI 오버레이
- `src/story_mode/` - 스토리 모드 통합

### 외부
- `pyyaml` - YAML 튜토리얼 정의 로드
- `pydantic` - 튜토리얼 모델 검증

<!-- MANUAL: -->
