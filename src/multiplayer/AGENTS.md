<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# 멀티플레이 시스템

## 목적
P2P 네트워크 기반 멀티플레이 게임플레이. 플레이어 간 실시간 동기화, 공동 탐색, 협력 전투, 롤백 기반 검증 시스템을 포함합니다. ATB 시스템과 통합된 멀티플레이 전투, 상태 머신 기반 세션 관리, LLM 봇 플레이어를 지원합니다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| network.py | P2P 네트워크 (TCP/UDP 소켓, UPnP) |
| session.py | 멀티플레이 세션 관리 |
| protocol.py | 네트워크 프로토콜 정의 (메시지 형식) |
| player.py | 플레이어 상태 관리 |
| player_state.py | 플레이어 게임 상태 |
| atb_multiplayer.py | ATB 시스템 멀티플레이 통합 |
| combat_sync.py | 전투 상태 동기화 및 검증 |
| combat_join.py | 전투 참여 프로토콜 |
| exploration_multiplayer.py | 탐색 모드 멀티플레이 |
| movement_sync.py | 플레이어 이동 동기화 |
| loot_sync.py | 아이템/전리품 동기화 |
| enemy_sync.py | 적 상태 동기화 |
| ai_bot.py | AI 플레이어 (멀티플레이 봇) |
| llm_player_bot.py | LLM 기반 플레이어 |
| bot_tasks.py | 봇 AI 행동 관리 |
| bot_communication.py | 봇 플레이어 통신 |
| revival_system.py | 부활 시스템 |
| skill_revival_handler.py | 스킬 기반 부활 처리 |
| config.py | 멀티플레이 설정 |
| validation.py | 상태 검증 로직 |
| upnp.py | UPnP 포트 포워딩 |
| test_helper.py | 테스트 헬퍼 |
| party_setup.py | 멀티플레이 파티 설정 |
| game_mode.py | 멀티플레이 게임 모드 |

## AI 에이전트를 위한 가이드
### 이 디렉토리에서 작업할 때
- 네트워크 동기화는 결정론적이고 일관성 있어야 합니다.
- 모든 상태 변경은 검증 가능해야 합니다 (롤백 필요).
- 메시지는 타임스탬프와 시퀀스 번호를 포함합니다.
- 세션은 상태 머신으로 관리됩니다 (대기 → 준비 → 진행 → 완료).

### 테스트 요구사항
- 네트워크 지연 시뮬레이션 (지연, 패킷 손실)으로 검증합니다.
- 상태 동기화는 다중 클라이언트 시뮬레이션으로 검증합니다.
- ATB 타이밍 동기화는 결정론적 재생으로 검증합니다.
- 검증 실패는 명확한 로그를 남깁니다.

### 일반적인 패턴
- 메시지는 JSON으로 직렬화됩니다.
- 각 플레이어는 고유한 ID와 포트를 가집니다.
- 상태 변경은 이벤트로 브로드캐스트됩니다.
- 약한 일관성 모델 (최종 일관성)을 사용합니다.

## 의존성
### 내부
- `src/character/` - 캐릭터 정보
- `src/combat/` - ATB 시스템, 전투 로직
- `src/world/` - 맵 데이터
- `src/ai/` - LLM 봇 플레이어
- `src/tutorial/` - 튜토리얼 통합

### 외부
- `asyncio` - 비동기 네트워킹
- `socket` - TCP/UDP 소켓
- `miniupnpc` - UPnP 포트 포워딩
- `pydantic` - 메시지 검증

<!-- MANUAL: -->
