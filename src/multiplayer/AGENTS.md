<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# multiplayer/

## Purpose
P2P WebSocket 기반 멀티플레이어 시스템. 세션 관리, 네트워크 통신, 전투/탐험 동기화, AI 봇(규칙 기반 + LLM 기반), 부활 시스템을 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `network.py` | `NetworkManager` 클래스. WebSocket 호스트/클라이언트 공통 레이어. `ConnectionState` enum |
| `session.py` | `MultiplayerSession` 클래스. 세션 생명주기, 플레이어 관리(최대 2~4명), 던전 캐시, 밸런스 설정 |
| `player.py` | `MultiplayerPlayer` 클래스. 네트워크 플레이어 상태 |
| `player_state.py` | 플레이어 상태 직렬화/역직렬화 |
| `protocol.py` | `NetworkMessage`, `MessageType`, `MessageBuilder`. 메시지 프로토콜 정의 |
| `combat_sync.py` | 전투 상태 동기화. 턴 순서, 행동, 데미지 결과 공유 |
| `exploration_multiplayer.py` | 탐험 동기화. 플레이어 위치, 이벤트 공유 |
| `movement_sync.py` | 플레이어 이동 동기화 |
| `enemy_sync.py` | 적 상태 동기화 (호스트 권위 모델) |
| `loot_sync.py` | 아이템 드랍 동기화 |
| `combat_join.py` | 전투 참여 처리 (탐험 중 전투 시작 시 다른 플레이어 합류) |
| `party_setup.py` | 멀티플레이 파티 구성 UI 연결 |
| `game_mode.py` | 게임 모드 설정 (협동/경쟁 등) |
| `ai_bot.py` | 규칙 기반 AI 봇. 자동화된 플레이어 대체 |
| `llm_player_bot.py` | LLM 기반 AI 봇. 자연어 전략 결정 |
| `bot_communication.py` | 봇 통신 레이어 |
| `bot_tasks.py` | 봇 작업 큐 관리 |
| `revival_system.py` | 플레이어 부활 시스템 |
| `skill_revival_handler.py` | 스킬 기반 부활 처리 |
| `validation.py` | 네트워크 메시지 검증 |
| `config.py` | `MultiplayerConfig` 클래스. 적 수/HP/데미지 배율 설정 |
| `test_helper.py` | 멀티플레이 테스트 유틸리티 |

## For AI Agents

### Working In This Directory
- 호스트/클라이언트 구분: `NetworkManager(is_host=True/False)`
- 세션 제한: `2 <= max_players <= 4` (위반 시 `ValueError`)
- 메시지 프로토콜: `MessageBuilder`로 생성 → `NetworkManager.send()` 발송
- 동기화 모델: 호스트 권위(Host-Authoritative) — 적 상태는 호스트가 관리
- 봇 사용: `AiBot` (규칙 기반) 또는 `LLMPlayerBot` (LLM 기반) 중 선택
- `MultiplayerConfig.enemy_count_multiplier` 등으로 멀티플레이 밸런스 조정
- WebSocket 라이브러리: `websockets` (비동기 asyncio 기반)

### Testing Requirements
- `test_helper.py` 활용하여 네트워크 없이 로컬 테스트
- 동기화 테스트: `combat_sync.py`의 메시지 직렬화/역직렬화 검증
- 세션 테스트: 플레이어 참가/퇴장 시 상태 일관성 검증

### Common Patterns
```python
# 호스트 세션 생성
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
session = MultiplayerSession(max_players=4, host_id="player1")
network = NetworkManager(is_host=True, session=session)

# 클라이언트 연결
client_network = NetworkManager(is_host=False)
await client_network.connect(host_address="192.168.1.100", port=8765)

# 메시지 핸들러 등록
from src.multiplayer.protocol import MessageType
network.register_handler(MessageType.COMBAT_ACTION, on_combat_action)
```

## Dependencies

### Internal
- `src.core.logger` — 네트워크 로그
- `src.character.character` — 캐릭터 상태 직렬화
- `src.combat.combat_manager` — 전투 동기화 연동
- `src.world.exploration` — 탐험 동기화 연동

### External
- `websockets`: WebSocket 비동기 통신
- `asyncio`: 비동기 이벤트 루프
- `gzip`: 메시지 압축

<!-- MANUAL: -->
