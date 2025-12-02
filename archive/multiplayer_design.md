# Dawn of Stellar - 멀티플레이 구현 방안

## 목차

1. [개요](#개요)
2. [현재 아키텍처 분석](#현재-아키텍처-분석)
3. [멀티플레이 모드 분류](#멀티플레이-모드-분류)
4. [구현 방안](#구현-방안)
5. [기술 스택 비교](#기술-스택-비교)
6. [구현 단계별 계획](#구현-단계별-계획)
7. [예상 도전 과제](#예상-도전-과제)
8. [권장 방안](#권장-방안)

---

## 개요

Dawn of Stellar는 현재 단일 플레이어 로그라이크 RPG입니다. 이 문서는 다양한 멀티플레이 구현 방안을 비교 분석하고, 각 방안의 장단점과 구현 복잡도를 제시합니다.

**상세 P2P 멀티플레이 설계**: [`multiplayer_p2p_detailed.md`](multiplayer_p2p_detailed.md) 참고

### 멀티플레이 요구사항

1. **게임 특성**
   - 턴제 전투 (ATB + BRV 시스템) → **멀티플레이: 실시간 전투**
   - 절차적 던전 생성 → **시드 기반 동기화**
   - 실시간 맵 탐험 (던전 내 이동) → **개별 캐릭터 독립 이동**
   - 파티 기반 전투 (최대 4명) → **근처 아군만 전투 참여**
   - 이벤트 기반 아키텍처 (EventBus)

2. **목표 사용자 경험**
   - 최대 4명 동시 플레이
   - 협동 모드 (Co-op)
   - 경쟁 모드 (PvP, 선택 사항)
   - 안정적인 연결과 지연 최소화
   - 단일 게임 세션 저장 가능
   
3. **멀티플레이 전용 규칙** (싱글플레이와 다름)
   - 실시간 전투 (행동 선택 중에도 ATB 증가)
   - 행동 선택 중 ATB 1/50 감소 (아군/적군 모두)
   - 1.5초 대기 시간 중 ATB 증가 안 함
   - 적의 2초 간격 움직임
   - 파티 공유 인벤토리

---

## 현재 아키텍처 분석

### 시스템 구조

```
Application Layer (main.py)
    ↓
Core Systems (EventBus, Config, Logger)
    ↓
Game Systems (Combat, World, Character, UI)
    ↓
Data/Persistence Layer (Save/Load)
```

### 핵심 특징

1. **이벤트 기반 아키텍처**
   - `EventBus`를 통한 느슨한 결합
   - 모든 시스템 간 통신은 이벤트로 처리
   - 멀티플레이에서 이벤트 동기화 필요

2. **게임 상태 관리**
   - `CombatManager`: 전투 상태 및 턴 관리
   - `ExplorationSystem`: 던전 탐험 상태
   - `Character`: 캐릭터 상태 (HP, MP, BRV 등)

3. **랜덤 요소**
   - 던전 생성: 절차적 (시드 기반 가능)
   - 적 생성: 층별 랜덤
   - 아이템 드롭: 확률 기반

### 멀티플레이 영향 분석

| 시스템 | 멀티플레이 영향 | 동기화 필요성 |
|--------|----------------|--------------|
| 전투 시스템 | 높음 | 모든 클라이언트에서 동일한 결과 필요 |
| 맵 탐험 | 높음 | 플레이어 위치, 적 위치, 상호작용 객체 |
| 캐릭터 상태 | 높음 | HP, MP, BRV, 버프/디버프 등 |
| 던전 생성 | 중간 | 시드 기반으로 동일 던전 생성 가능 |
| 인벤토리 | 중간 | 파티 공유 vs 개인별 |

---

## 멀티플레이 모드 분류

### 1. 협동 모드 (Cooperative)

**설명**: 여러 플레이어가 함께 같은 던전을 탐험하고 전투를 진행

**특징**:
- 공통 파티 또는 개별 캐릭터
- 공유 인벤토리 또는 개인 인벤토리
- 모든 플레이어가 같은 맵 공간에서 이동
- 전투 시 모든 플레이어가 참여

**장점**:
- 구현이 상대적으로 단순
- 플레이어 간 상호작용 자연스러움
- 협동 전략 중요성 부각

**단점**:
- 플레이어별 턴 대기 시간 발생
- 네트워크 지연 시 경험 저하
- 어디까지나 여러명이 함께 이동해야 함

### 2. 경쟁 모드 (Competitive)

**설명**: 플레이어들이 각각 독립적으로 던전을 탐험하고 결과를 비교

**특징**:
- 각 플레이어가 독립적인 던전 인스턴스
- 동일 시드 또는 서로 다른 시드 사용
- 진행 속도, 클리어 시간, 생존 등 경쟁 요소

**장점**:
- 네트워크 동기화 부담 적음
- 플레이어가 자유롭게 자신의 속도로 진행
- 서버 부하 최소화

**단점**:
- 협동 요소 부재
- 리더보드/랭킹 시스템 필요
- 실시간 상호작용 부족

### 3. 하이브리드 모드

**설명**: 협동과 경쟁 요소를 결합 (예: 팀 vs 팀, 또는 개인 vs 개인 + 특정 구간 협동)

**특징**:
- 모드에 따라 협동/경쟁 전환
- 전투만 협동, 탐험은 개별 등의 변형 가능

**장점**:
- 다양한 게임플레이 경험 제공
- 플레이어 선호도에 맞춤

**단점**:
- 구현 복잡도 높음
- 밸런싱 어려움

---

## 구현 방안

### 방안 1: Hotseat (로컬 멀티플레이)

**개념**: 같은 기기에서 플레이어들이 순서대로 플레이

#### 구현 방식

```
[플레이어 1 턴] → [플레이어 2 턴] → [플레이어 3 턴] → [플레이어 4 턴] → 순환
```

**기술적 요구사항**:
- 네트워킹 불필요
- UI 수정: 플레이어 전환 화면 추가
- 상태 관리: 현재 활성 플레이어 추적

**구현 예시**:

```python
class HotseatManager:
    def __init__(self, players: List[Player]):
        self.players = players
        self.current_player_index = 0
        self.active_player: Optional[Player] = None
    
    def next_turn(self):
        """다음 플레이어로 턴 전환"""
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.active_player = self.players[self.current_player_index]
        # UI 업데이트: "플레이어 X의 턴입니다" 메시지
```

**장점**:
- ✅ 구현이 가장 간단
- ✅ 네트워크 지연 없음
- ✅ 서버 비용 없음
- ✅ 보안 문제 최소화
- ✅ 기존 코드 수정 최소화

**단점**:
- ❌ 원격 플레이 불가
- ❌ 동시에 여러 플레이어 조작 불가
- ❌ 단일 화면에서만 가능

**적용 시나리오**:
- 같은 컴퓨터에서 가족/친구들과 함께 플레이
- 전투는 협동, 맵 탐험은 턴제로 전환

**예상 개발 시간**: 1-2주

---

### 방안 2: P2P (Peer-to-Peer) 실시간 멀티플레이

**개념**: 플레이어 중 한 명이 호스트가 되어 게임 세션을 호스팅하고, 다른 플레이어들이 클라이언트로 연결

#### 아키텍처

```
[호스트 (서버 역할)] ←→ [클라이언트 1]
     ↑                      ↓
     └──────────────────────┘
         [클라이언트 2]
              ↓
         [클라이언트 3]
```

**기술 스택**:
- **프로토콜**: TCP (신뢰성) 또는 UDP (실시간성)
- **라이브러리 옵션**:
  1. `socket` (Python 내장) - 가장 기본
  2. `asyncio` + `aiohttp` - 비동기 통신
  3. `websockets` - WebSocket 프로토콜 (Web 지원)
  4. `netplay` (Python 게임용) - 게임 특화
  5. `pygame-net` - Pygame 기반 네트워킹

**메시지 구조**:

```python
# 메시지 타입 정의
class MessageType(Enum):
    # 연결
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    
    # 게임 상태
    PLAYER_MOVE = "player_move"
    PLAYER_ACTION = "player_action"
    COMBAT_ACTION = "combat_action"
    TURN_CHANGE = "turn_change"
    
    # 동기화
    STATE_SYNC = "state_sync"
    HEALTH_UPDATE = "health_update"
    
    # 던전
    DUNGEON_REQUEST = "dungeon_request"
    DUNGEON_RESPONSE = "dungeon_response"

# 메시지 구조
@dataclass
class NetworkMessage:
    type: MessageType
    player_id: str
    timestamp: float
    data: Dict[str, Any]
```

**호스트 서버 예시**:

```python
import asyncio
import json
from typing import Dict, List
from enum import Enum

class P2PServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.clients: Dict[str, asyncio.StreamWriter] = {}
        self.game_state = None  # 공유 게임 상태
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """클라이언트 연결 처리"""
        client_id = f"client_{len(self.clients)}"
        self.clients[client_id] = writer
        
        # 초기 상태 전송
        await self.send_game_state(writer, client_id)
        
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                
                message = json.loads(data.decode())
                await self.handle_message(client_id, message)
        
        except Exception as e:
            print(f"클라이언트 {client_id} 연결 종료: {e}")
        finally:
            del self.clients[client_id]
            writer.close()
            await writer.wait_closed()
    
    async def handle_message(self, client_id: str, message: dict):
        """메시지 처리 및 브로드캐스트"""
        # 게임 상태 업데이트
        self.update_game_state(client_id, message)
        
        # 다른 클라이언트들에게 브로드캐스트
        await self.broadcast(message, exclude=client_id)
    
    async def broadcast(self, message: dict, exclude: str = None):
        """모든 클라이언트에게 메시지 전송"""
        data = json.dumps(message).encode()
        for client_id, writer in self.clients.items():
            if client_id != exclude:
                writer.write(data)
                await writer.drain()
```

**클라이언트 예시**:

```python
class P2PClient:
    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port
        self.reader = None
        self.writer = None
        self.player_id = None
    
    async def connect(self):
        """서버에 연결"""
        self.reader, self.writer = await asyncio.open_connection(
            self.server_host, self.server_port
        )
        # 연결 메시지 전송
        await self.send({
            "type": "connect",
            "player_id": self.player_id
        })
        
        # 메시지 수신 루프 시작
        asyncio.create_task(self.receive_loop())
    
    async def send(self, message: dict):
        """메시지 전송"""
        data = json.dumps(message).encode()
        self.writer.write(data)
        await self.writer.drain()
    
    async def receive_loop(self):
        """메시지 수신 루프"""
        while True:
            data = await self.reader.read(1024)
            if not data:
                break
            
            message = json.loads(data.decode())
            self.handle_message(message)
```

**장점**:
- ✅ 전용 서버 불필요
- ✅ 구현이 상대적으로 단순
- ✅ 플레이어 간 직접 연결로 지연 최소화 가능
- ✅ 비용 없음 (서버 유지비 없음)

**단점**:
- ❌ 호스트가 나가면 게임 종료
- ❌ NAT/방화벽 문제로 연결 어려울 수 있음
- ❌ 호스트의 네트워크/PC 성능이 병목
- ❌ 치트 방지 어려움 (클라이언트 권한)
- ❌ 지연 시간이 플레이어 위치에 따라 다름

**적용 시나리오**:
- 친구들과 로컬 네트워크에서 플레이
- 임시 세션 (길지 않은 플레이)
- 개발/테스트 단계

**예상 개발 시간**: 3-4주

---

### 방안 3: Client-Server (전용 서버)

**개념**: 별도의 전용 서버가 게임 상태를 관리하고, 모든 클라이언트가 서버에 연결

#### 아키텍처

```
[전용 서버]
     ↑
     ├─── [클라이언트 1]
     ├─── [클라이언트 2]
     ├─── [클라이언트 3]
     └─── [클라이언트 4]
```

**기술 스택**:
- **서버 프레임워크**:
  1. `FastAPI` + `WebSockets` - 현대적, 빠름, 문서화 좋음
  2. `Flask-SocketIO` - 간단한 웹소켓 통신
  3. `Tornado` - 비동기 웹 프레임워크
  4. `aiohttp` + WebSocket - 가벼움
- **데이터베이스** (선택 사항):
  - `SQLite` (경량)
  - `PostgreSQL` (확장성)
  - `Redis` (캐싱/세션 관리)

**서버 아키텍처**:

```python
# 서버 예시 (FastAPI + WebSockets)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import json

app = FastAPI()

class GameServer:
    def __init__(self):
        self.active_games: Dict[str, GameSession] = {}
        self.connected_clients: Dict[str, WebSocket] = {}
    
    async def connect_client(self, websocket: WebSocket, player_id: str):
        """클라이언트 연결"""
        await websocket.accept()
        self.connected_clients[player_id] = websocket
        
        # 게임 세션 찾기 또는 생성
        game_session = await self.get_or_create_session(player_id)
        await game_session.add_player(player_id, websocket)
    
    async def handle_message(self, player_id: str, message: dict):
        """클라이언트 메시지 처리"""
        game_session = self.get_player_session(player_id)
        if not game_session:
            return
        
        # 게임 로직 실행 (서버에서만 실행)
        result = await game_session.process_action(player_id, message)
        
        # 결과를 모든 클라이언트에 브로드캐스트
        await game_session.broadcast_state()

class GameSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.players: Dict[str, WebSocket] = {}
        self.game_state = None  # 게임 상태 (서버에서 관리)
    
    async def process_action(self, player_id: str, action: dict):
        """게임 액션 처리 (서버에서만 실행)"""
        # 입력 검증
        if not self.validate_action(player_id, action):
            return {"error": "Invalid action"}
        
        # 게임 로직 실행
        result = await self.game_logic.execute(action)
        
        # 상태 업데이트
        self.update_state(result)
        
        return result
    
    async def broadcast_state(self):
        """모든 플레이어에게 상태 브로드캐스트"""
        state_snapshot = self.get_state_snapshot()
        for player_id, websocket in self.players.items():
            await websocket.send_json({
                "type": "state_update",
                "data": state_snapshot
            })

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    server = get_game_server()  # 싱글톤 인스턴스
    await server.connect_client(websocket, player_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            await server.handle_message(player_id, data)
    except WebSocketDisconnect:
        await server.disconnect_client(player_id)
```

**게임 상태 동기화**:

```python
class GameStateSync:
    """게임 상태 동기화 관리"""
    
    def __init__(self):
        self.state_version = 0  # 상태 버전 관리
        self.state_history = []  # 상태 히스토리 (롤백용)
    
    def get_state_snapshot(self) -> dict:
        """현재 상태 스냅샷 생성"""
        return {
            "version": self.state_version,
            "combat": self.combat_state.serialize(),
            "exploration": self.exploration_state.serialize(),
            "players": [p.serialize() for p in self.players]
        }
    
    def apply_state_update(self, update: dict):
        """상태 업데이트 적용"""
        # 낙관적 잠금: 버전 체크
        if update["version"] != self.state_version:
            raise StateConflictError("State version mismatch")
        
        # 상태 업데이트
        self.update_state(update["data"])
        self.state_version += 1
        
        # 히스토리 저장 (최근 100개)
        self.state_history.append({
            "version": self.state_version - 1,
            "state": self.get_state_snapshot()
        })
        if len(self.state_history) > 100:
            self.state_history.pop(0)
```

**장점**:
- ✅ 서버가 게임 상태의 권위자 (Authority)
- ✅ 치트 방지 용이
- ✅ 안정적인 연결 (서버가 항상 온라인)
- ✅ 확장 가능 (여러 게임 세션 동시 운영)
- ✅ NAT/방화벽 문제 없음 (서버가 공개 IP)
- ✅ 지연 시간 일관성 (모든 클라이언트가 서버에만 연결)

**단점**:
- ❌ 서버 구축 및 유지비용
- ❌ 구현 복잡도 높음
- ❌ 서버 확장 시 인프라 관리 필요
- ❌ 개발 시간 증가

**적용 시나리오**:
- 상업적 배포
- 대규모 멀티플레이
- 리더보드/랭킹 시스템
- 장기적인 지원 계획

**예상 개발 시간**: 6-8주

---

### 방안 4: WebSocket 기반 실시간 멀티플레이

**개념**: HTTP 기반 WebSocket을 사용하여 브라우저와 네이티브 클라이언트 모두 지원

#### 특징

- **프로토콜**: WebSocket (HTTP 업그레이드)
- **통신 방식**: 양방향 실시간 통신
- **장점**: 웹 브라우저 지원, 방화벽 친화적

#### 기술 스택

```python
# 서버: FastAPI + WebSockets
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# 클라이언트: websockets 라이브러리 또는 브라우저 WebSocket API
import websockets
# 또는 브라우저에서: const ws = new WebSocket('ws://server:port');
```

**메시지 프로토콜 예시**:

```python
# 메시지 포맷
{
    "type": "player_move",
    "player_id": "player_1",
    "timestamp": 1234567890.123,
    "data": {
        "x": 10,
        "y": 5,
        "direction": "right"
    }
}

# 피드백 메시지
{
    "type": "state_update",
    "timestamp": 1234567890.124,
    "data": {
        "players": [...],
        "combat": {...},
        "exploration": {...}
    }
}
```

**장점**:
- ✅ 웹 브라우저 지원 (웹 버전 게임 가능)
- ✅ 방화벽 친화적 (HTTP 포트 사용)
- ✅ 표준 프로토콜 (라이브러리 풍부)
- ✅ 실시간 양방향 통신

**단점**:
- ❌ 서버 필요 (방안 3과 유사)
- ❌ TCP 기반이므로 UDP보다 약간 느릴 수 있음

**예상 개발 시간**: 5-7주 (서버 구축 포함)

---

### 방안 5: 비동기 턴 기반 멀티플레이

**개념**: 각 플레이어가 독립적으로 턴을 진행하고, 특정 지점(전투 등)에서만 동기화

#### 아키텍처

```
플레이어 1: [탐험] → [전투 시작] → [턴 대기] → [전투 종료] → [탐험]
플레이어 2: [탐험] → [전투 시작] → [턴 대기] → [전투 종료] → [탐험]
플레이어 3: [탐험] → [전투 시작] → [턴 대기] → [전투 종료] → [탐험]
플레이어 4: [탐험] → [전투 시작] → [턴 대기] → [전투 종료] → [탐험]

동기화 지점:
- 전투 시작: 모든 플레이어 준비 확인
- 턴 순서: ATB 게이지에 따라
- 전투 종료: 결과 공유
```

**구현 예시**:

```python
class AsyncTurnBasedMultiplayer:
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.current_phase = "exploration"  # exploration, combat
    
    async def start_combat(self, player_ids: List[str]):
        """전투 시작 - 모든 플레이어가 준비될 때까지 대기"""
        # 모든 플레이어가 전투 영역에 도착했는지 확인
        await self.wait_for_all_players(player_ids)
        
        # 전투 상태로 전환
        self.current_phase = "combat"
        
        # 전투 시작 메시지 브로드캐스트
        await self.broadcast({
            "type": "combat_start",
            "combat_state": self.combat_manager.get_state()
        })
    
    async def wait_for_all_players(self, player_ids: List[str]):
        """모든 플레이어가 준비될 때까지 대기"""
        ready_players = set()
        
        while ready_players != set(player_ids):
            # 플레이어 준비 상태 확인
            for player_id in player_ids:
                if await self.is_player_ready(player_id):
                    ready_players.add(player_id)
            
            await asyncio.sleep(0.1)  # 폴링 간격
```

**장점**:
- ✅ 플레이어가 독립적으로 탐험 가능
- ✅ 전투만 동기화하므로 네트워크 부하 적음
- ✅ 탐험 중 네트워크 지연 영향 최소화
- ✅ 구현 복잡도 중간

**단점**:
- ❌ 전투 시작 시 대기 시간 발생 가능
- ❌ 탐험과 전투 간 상태 전환 복잡
- ❌ 플레이어 간 상호작용 제한적

**예상 개발 시간**: 4-6주

---

### 방안 6: 하이브리드 모드 (Hotseat + P2P)

**개념**: 로컬 플레이어들은 Hotseat으로, 원격 플레이어들은 P2P로 연결

#### 아키텍처

```
[로컬 그룹]
  플레이어 A (호스트) ← Hotseat → 플레이어 B
        ↓
    [P2P 네트워크]
        ↓
  [원격 그룹]
  플레이어 C ← Hotseat → 플레이어 D
```

**장점**:
- ✅ 로컬 플레이어는 지연 없이 플레이
- ✅ 원격 플레이어도 참여 가능
- ✅ 네트워크 대역폭 절약 (로컬 그룹 내부 통신 불필요)

**단점**:
- ❌ 구현 복잡도 매우 높음
- ❌ 로컬과 원격 간 동기화 복잡

**예상 개발 시간**: 6-8주

---

## 기술 스택 비교

### 네트워킹 라이브러리 비교

| 라이브러리 | 프로토콜 | 비동기 | 웹 지원 | 학습 곡선 | 권장도 |
|-----------|---------|--------|---------|----------|--------|
| `socket` (내장) | TCP/UDP | ❌ | ❌ | 낮음 | ⭐⭐ |
| `asyncio` + `socket` | TCP/UDP | ✅ | ❌ | 중간 | ⭐⭐⭐ |
| `websockets` | WebSocket | ✅ | ✅ | 낮음 | ⭐⭐⭐⭐ |
| `aiohttp` + WebSocket | WebSocket | ✅ | ✅ | 중간 | ⭐⭐⭐⭐ |
| `FastAPI` + WebSocket | WebSocket | ✅ | ✅ | 중간 | ⭐⭐⭐⭐⭐ |
| `Flask-SocketIO` | WebSocket | ✅ | ✅ | 낮음 | ⭐⭐⭐⭐ |
| `Tornado` | WebSocket/HTTP | ✅ | ✅ | 높음 | ⭐⭐⭐ |

**권장**: `FastAPI` + `websockets`
- 현대적이고 빠름
- 비동기 지원 우수
- 자동 API 문서 생성
- 타입 힌팅 지원

---

## 구현 단계별 계획

### Phase 1: 기반 구조 (2주)

1. **네트워크 레이어 설계**
   - 메시지 프로토콜 정의
   - 네트워크 관리자 클래스 작성
   - 연결/재연결 로직

2. **게임 상태 직렬화**
   - 모든 게임 객체 직렬화 가능하도록 수정
   - 상태 스냅샷 생성/복원 메서드

3. **이벤트 동기화 시스템**
   - EventBus를 네트워크 이벤트와 연결
   - 로컬/원격 이벤트 구분

### Phase 2: 기본 멀티플레이 (3주)

1. **연결 및 인증**
   - 플레이어 연결/해제
   - 세션 관리
   - 기본 핑/퐁

2. **상태 동기화**
   - 주기적 상태 스냅샷 전송
   - 델타 업데이트 (변경된 부분만)

3. **입력 동기화**
   - 플레이어 입력 네트워크 전송
   - 입력 검증 및 적용

### Phase 3: 전투 시스템 (3주)

1. **턴 기반 전투 동기화**
   - ATB 게이지 동기화
   - 턴 순서 관리
   - 액션 실행 및 결과 공유

2. **전투 상태 관리**
   - HP/MP/BRV 동기화
   - 버프/디버프 상태 동기화
   - 전투 종료 처리

### Phase 4: 던전 탐험 (2주)

1. **맵 동기화**
   - 플레이어 위치 동기화
   - 적 위치 및 상태 동기화
   - 상호작용 객체 동기화

2. **던전 생성 동기화**
   - 시드 기반 던전 생성 (모든 클라이언트에서 동일)
   - 던전 상태 공유

### Phase 5: 최적화 및 안정화 (2주)

1. **성능 최적화**
   - 메시지 압축
   - 배치 업데이트
   - 지연 보정 (Lag Compensation)

2. **에러 처리**
   - 네트워크 오류 처리
   - 재연결 로직
   - 상태 복구

3. **테스트**
   - 로컬 네트워크 테스트
   - 인터넷 환경 테스트
   - 부하 테스트

---

## 예상 도전 과제

### 1. 게임 상태 동기화

**문제**: 모든 클라이언트에서 게임 상태가 동일해야 함

**해결 방안**:
- 서버 권위 (Server Authority): 서버가 게임 상태의 유일한 권위자
- 결정론적 로직: 시드 기반 랜덤 사용
- 상태 스냅샷 + 델타 업데이트

### 2. 네트워크 지연 (Latency)

**문제**: 네트워크 지연으로 인한 반응 지연

**해결 방안**:
- 클라이언트 예측 (Client-side Prediction)
- 지연 보정 (Lag Compensation)
- 인터폴레이션 (보간)

### 3. 네트워크 불안정

**문제**: 패킷 손실, 연결 끊김

**해결 방안**:
- TCP 사용 (신뢰성)
- 재전송 로직
- 상태 복구 메커니즘

### 4. 치트 방지

**문제**: 클라이언트에서 게임 로직을 조작

**해결 방안**:
- 서버 검증: 모든 중요한 액션을 서버에서 검증
- 입력 검증: 비정상적인 입력 거부
- 암호화 (선택 사항)

### 5. NAT/방화벽 문제

**문제**: P2P 연결 시 NAT 통과 어려움

**해결 방안**:
- STUN/TURN 서버 사용
- 중계 서버 사용 (방안 3, 4)
- UPnP 사용 (선택 사항)

---

## 권장 방안

### 단계별 추천

#### 1단계: Hotseat (즉시 구현 가능)

**이유**:
- 구현이 가장 간단
- 네트워크 문제 없음
- 기존 코드 수정 최소화
- 같은 기기에서 플레이하는 사용자에게 유용

**구현 우선순위**: 최우선

---

#### 2단계: P2P 멀티플레이 (중기)

**이유**:
- 전용 서버 없이도 원격 플레이 가능
- 구현 복잡도 중간
- 친구들과 쉽게 플레이 가능

**기술 스택**: `websockets` 또는 `asyncio` + `socket`

**구현 우선순위**: 높음

---

#### 3단계: 전용 서버 (장기)

**이유**:
- 상업적 배포 시 필수
- 치트 방지
- 확장 가능성

**기술 스택**: `FastAPI` + `WebSockets`

**구현 우선순위**: 중간 (상업화 계획 시)

---

### 최종 권장 사항

**초기 개발**: **Hotseat + P2P 하이브리드**

1. **Hotseat으로 시작**: 로컬 멀티플레이 빠르게 구현
2. **P2P 추가**: 원격 플레이 기능 추가
3. **점진적 개선**: 필요에 따라 전용 서버로 전환

**이유**:
- 빠른 시장 출시 가능
- 비용 효율적 (서버 비용 없음)
- 기술적 위험 낮음
- 사용자 피드백 수집 가능

---

## 추가 고려사항

### 저장 시스템

**문제**: 멀티플레이 세션 저장 및 복원

**해결 방안**:
- 호스트/서버가 저장 파일 관리
- 세션 ID 기반 저장
- 플레이어별 진행 상황 개별 저장 (선택 사항)

### 매치메이킹

**향후 확장**:
- 자동 매칭 시스템
- 방 목록 (Lobby)
- 친구 초대

### 관전 모드

**향후 확장**:
- 플레이어가 떠난 후 관전자로 전환
- 리플레이 시스템

---

## 결론

Dawn of Stellar의 멀티플레이 구현은 다음 순서로 진행하는 것을 권장합니다:

1. **즉시**: Hotseat 모드 구현
2. **단기 (1-2개월)**: P2P 멀티플레이 구현
   - 상세 설계: [`multiplayer_p2p_detailed.md`](multiplayer_p2p_detailed.md) 참고
   - 실시간 전투, 개별 탐험, 파티 공유 인벤토리 등
3. **중기 (3-6개월)**: 안정화 및 최적화
4. **장기 (필요시)**: 전용 서버로 전환

각 단계는 독립적으로 작동하므로, 점진적으로 기능을 추가하면서 사용자 피드백을 반영할 수 있습니다.

---

## 추가 참고 문서

- **P2P 멀티플레이 상세 설계**: [`multiplayer_p2p_detailed.md`](multiplayer_p2p_detailed.md)
  - 실시간 전투 시스템 상세 설계
  - 개별 캐릭터 이동 시스템
  - 상태 동기화 및 인벤토리 공유
  - 네트워크 최적화 및 추가 고려사항

