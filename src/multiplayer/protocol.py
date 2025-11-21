"""
멀티플레이 메시지 프로토콜

클라이언트와 호스트 간 통신에 사용되는 메시지 타입과 구조를 정의합니다.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import json
import time
import gzip


class MessageType(Enum):
    """메시지 타입"""
    # 연결 관련
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CONNECTION_ACCEPTED = "connection_accepted"
    CONNECTION_REJECTED = "connection_rejected"
    
    # 세션 관련
    SESSION_START = "session_start"
    SESSION_SEED = "session_seed"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    
    # 파티 설정 관련
    LOBBY_COMPLETE = "lobby_complete"  # 로비 완료 (파티 설정 시작)
    JOB_SELECTED = "job_selected"
    JOB_DESELECTED = "job_deselected"
    JOB_SELECTION_COMPLETE = "job_selection_complete"  # 플레이어가 직업 선택 완료
    TURN_CHANGED = "turn_changed"  # 직업 선택 턴 변경
    REQUEST_JOB = "request_job"
    RELEASE_JOB = "release_job"
    PASSIVES_SET = "passives_set"
    GAME_START = "game_start"  # 게임 시작 (호스트가 패시브/난이도 선택 완료 후)
    
    # 캐릭터 상태
    CHARACTER_DEATH = "character_death"
    CHARACTER_REVIVAL = "character_revival"
    PLAYER_MARK_UPDATE = "player_mark_update"
    
    # 게임 상태
    PLAYER_MOVE = "player_move"
    MOVE_REQUEST = "move_request"
    POSITION_SYNC = "position_sync"  # 위치 동기화 (주기적)
    COMBAT_START = "combat_start"
    COMBAT_JOIN = "combat_join"
    COMBAT_ACTION = "combat_action"
    ACTION_SELECTION_START = "action_selection_start"
    
    # 상태 동기화
    CHARACTER_STATES_UPDATE = "character_states_update"
    STATE_SYNC = "state_sync"
    STATE_UPDATE = "state_update"  # 전투 상태 업데이트 (클라이언트 동기화용)
    
    # 인벤토리
    INVENTORY_UPDATE = "inventory_update"
    ITEM_USED = "item_used"
    ITEM_PICKED_UP = "item_picked_up"
    
    # 적 관련
    ENEMY_MOVE = "enemy_move"
    
    # NPC 관련
    NPC_MOVE = "npc_move"
    
    # 전투 합류
    COMBAT_AUTO_JOIN = "combat_auto_join"
    
    # 네트워크
    PING_REQUEST = "ping_request"
    PONG_RESPONSE = "pong_response"
    
    # 채팅
    CHAT_MESSAGE = "chat_message"
    
    # 던전
    DUNGEON_DATA = "dungeon_data"
    FLOOR_CHANGE = "floor_change"
    
    # 채집/아이템
    HARVEST = "harvest"  # 채집 오브젝트 수집
    ITEM_DROPPED = "item_dropped"  # 아이템 드롭
    GOLD_DROPPED = "gold_dropped"  # 골드 드롭


@dataclass
class NetworkMessage:
    """네트워크 메시지 기본 구조"""
    type: MessageType
    player_id: Optional[str] = None
    timestamp: float = 0.0
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.data is None:
            self.data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """메시지를 딕셔너리로 변환"""
        return {
            "type": self.type.value,
            "player_id": self.player_id,
            "timestamp": self.timestamp,
            "data": self.data
        }
    
    def to_json(self) -> str:
        """메시지를 JSON 문자열로 변환"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkMessage":
        """딕셔너리에서 메시지 생성"""
        # 타입 파싱 (문자열 또는 이미 MessageType인 경우 처리)
        type_value = data.get("type")
        if isinstance(type_value, MessageType):
            msg_type = type_value
        elif isinstance(type_value, str):
            try:
                # 먼저 직접 변환 시도
                msg_type = MessageType(type_value)
            except ValueError:
                # "MessageType.CONNECT" 같은 형식일 수 있음
                if "MessageType." in type_value:
                    enum_name = type_value.split(".")[-1]
                    # CONNECT -> connect로 변환
                    enum_name_lower = enum_name.lower()
                    msg_type = MessageType(enum_name_lower)
                else:
                    # 소문자로 변환 시도
                    try:
                        msg_type = MessageType(type_value.lower())
                    except ValueError:
                        raise ValueError(f"Cannot parse message type: {type_value}")
        else:
            raise ValueError(f"Invalid message type: {type_value}")
        
        return cls(
            type=msg_type,
            player_id=data.get("player_id"),
            timestamp=data.get("timestamp", time.time()),
            data=data.get("data", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "NetworkMessage":
        """JSON 문자열에서 메시지 생성"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def compress(self) -> bytes:
        """메시지 압축"""
        json_str = self.to_json()
        return gzip.compress(json_str.encode('utf-8'))
    
    @classmethod
    def decompress(cls, compressed: bytes) -> "NetworkMessage":
        """압축된 메시지 해제"""
        json_str = gzip.decompress(compressed).decode('utf-8')
        return cls.from_json(json_str)


class MessageBuilder:
    """메시지 빌더 유틸리티 클래스"""
    
    @staticmethod
    def connect(player_id: str, player_name: str, version: str = "5.0.0") -> NetworkMessage:
        """연결 메시지 생성"""
        return NetworkMessage(
            type=MessageType.CONNECT,
            player_id=player_id,
            data={
                "player_name": player_name,
                "version": version
            }
        )
    
    @staticmethod
    def connection_accepted(player_id: str, session_id: str) -> NetworkMessage:
        """연결 승인 메시지 생성"""
        return NetworkMessage(
            type=MessageType.CONNECTION_ACCEPTED,
            player_id=player_id,
            data={
                "session_id": session_id
            }
        )
    
    @staticmethod
    def connection_rejected(player_id: str, reason: str) -> NetworkMessage:
        """연결 거부 메시지 생성"""
        return NetworkMessage(
            type=MessageType.CONNECTION_REJECTED,
            player_id=player_id,
            data={
                "reason": reason
            }
        )
    
    @staticmethod
    def session_seed(seed: int, session_id: str) -> NetworkMessage:
        """세션 시드 메시지 생성"""
        return NetworkMessage(
            type=MessageType.SESSION_SEED,
            data={
                "seed": seed,
                "session_id": session_id
            }
        )
    
    @staticmethod
    def dungeon_data(dungeon_data: Dict[str, Any], floor_number: int, seed: int) -> NetworkMessage:
        """
        던전 데이터 메시지 생성
        
        Args:
            dungeon_data: 직렬화된 던전 데이터
            floor_number: 층 번호
            seed: 던전 생성 시드
        """
        return NetworkMessage(
            type=MessageType.DUNGEON_DATA,
            data={
                "dungeon": dungeon_data,
                "floor_number": floor_number,
                "seed": seed
            }
        )
    
    @staticmethod
    def player_list(players: List[Dict[str, Any]]) -> NetworkMessage:
        """
        플레이어 목록 메시지 생성
        
        Args:
            players: 플레이어 정보 리스트 [{"player_id": str, "player_name": str, "x": int, "y": int, ...}]
        """
        return NetworkMessage(
            type=MessageType.PLAYER_JOINED,
            data={
                "players": players
            }
        )
    
    @staticmethod
    def player_move(player_id: str, x: int, y: int, timestamp: float = None) -> NetworkMessage:
        """
        플레이어 이동 메시지 생성
        
        Args:
            player_id: 플레이어 ID
            x: X 좌표
            y: Y 좌표
            timestamp: 타임스탬프 (없으면 현재 시간)
        """
        import time
        if timestamp is None:
            timestamp = time.time()
        
        return NetworkMessage(
            type=MessageType.PLAYER_MOVE,
            player_id=player_id,
            timestamp=timestamp,
            data={
                "x": x,
                "y": y
            }
        )
    
    @staticmethod
    def position_sync(positions: Dict[str, Dict[str, Any]]) -> NetworkMessage:
        """
        위치 동기화 메시지 생성 (주기적)
        
        Args:
            positions: {player_id: {"x": int, "y": int, "timestamp": float}}
        """
        import time
        return NetworkMessage(
            type=MessageType.POSITION_SYNC,
            timestamp=time.time(),
            data={
                "positions": positions
            }
        )
    
    @staticmethod
    def move_request(player_id: str, dx: int, dy: int) -> NetworkMessage:
        """이동 요청 메시지 생성"""
        return NetworkMessage(
            type=MessageType.MOVE_REQUEST,
            player_id=player_id,
            data={
                "dx": dx,
                "dy": dy
            }
        )
    
    @staticmethod
    def combat_start(participants: list, enemies: list, position: tuple) -> NetworkMessage:
        """전투 시작 메시지 생성"""
        return NetworkMessage(
            type=MessageType.COMBAT_START,
            data={
                "participants": participants,
                "enemies": [e if isinstance(e, str) else getattr(e, 'id', str(e)) for e in enemies],
                "position": {"x": position[0], "y": position[1]}
            }
        )
    
    @staticmethod
    def combat_join(player_id: str, characters: list, combat_state: dict) -> NetworkMessage:
        """전투 합류 메시지 생성"""
        return NetworkMessage(
            type=MessageType.COMBAT_JOIN,
            player_id=player_id,
            data={
                "characters": characters,
                "combat_state": combat_state
            }
        )
    
    @staticmethod
    def combat_action(player_id: str, actor_id: str, action: dict) -> NetworkMessage:
        """전투 액션 메시지 생성"""
        return NetworkMessage(
            type=MessageType.COMBAT_ACTION,
            player_id=player_id,
            data={
                "actor_id": actor_id,
                "action": action
            }
        )
    
    @staticmethod
    def enemy_move(enemy_positions: Dict[str, Dict[str, Any]]) -> NetworkMessage:
        """
        적 이동 메시지 생성
        
        Args:
            enemy_positions: {enemy_id: {"x": int, "y": int, "timestamp": float}}
        """
        import time
        return NetworkMessage(
            type=MessageType.ENEMY_MOVE,
            timestamp=time.time(),
            data={
                "enemies": enemy_positions
            }
        )
    
    @staticmethod
    def npc_move(npc_positions: Dict[str, Dict[str, Any]]) -> NetworkMessage:
        """
        NPC 이동 메시지 생성
        
        Args:
            npc_positions: {npc_id: {"x": int, "y": int, "old_x": int, "old_y": int}}
        """
        import time
        return NetworkMessage(
            type=MessageType.NPC_MOVE,
            timestamp=time.time(),
            data={
                "npcs": npc_positions
            }
        )
    
    @staticmethod
    def ping_request() -> NetworkMessage:
        """핑 요청 메시지 생성"""
        return NetworkMessage(
            type=MessageType.PING_REQUEST,
            data={}
        )
    
    @staticmethod
    def pong_response(timestamp: float) -> NetworkMessage:
        """퐁 응답 메시지 생성"""
        return NetworkMessage(
            type=MessageType.PONG_RESPONSE,
            data={
                "timestamp": timestamp
            }
        )
    
    @staticmethod
    def chat_message(player_id: str, message: str) -> NetworkMessage:
        """채팅 메시지 생성"""
        return NetworkMessage(
            type=MessageType.CHAT_MESSAGE,
            player_id=player_id,
            data={
                "message": message
            }
        )
    
    @staticmethod
    def lobby_complete(player_count: int) -> NetworkMessage:
        """
        로비 완료 메시지 생성 (파티 설정 시작)
        
        Args:
            player_count: 현재 플레이어 수
        """
        return NetworkMessage(
            type=MessageType.LOBBY_COMPLETE,
            data={
                "player_count": player_count
            }
        )
    
    @staticmethod
    def job_selected(job_id: str, player_id: str) -> NetworkMessage:
        """직업 선택 메시지 생성"""
        return NetworkMessage(
            type=MessageType.JOB_SELECTED,
            player_id=player_id,
            data={
                "job_id": job_id
            }
        )
    
    @staticmethod
    def job_deselected(job_id: str, player_id: str) -> NetworkMessage:
        """직업 해제 메시지 생성"""
        return NetworkMessage(
            type=MessageType.JOB_DESELECTED,
            player_id=player_id,
            data={
                "job_id": job_id
            }
        )
    
    @staticmethod
    def job_selection_complete(player_id: str) -> NetworkMessage:
        """직업 선택 완료 메시지 생성"""
        return NetworkMessage(
            type=MessageType.JOB_SELECTION_COMPLETE,
            player_id=player_id,
            data={}
        )
    
    @staticmethod
    def turn_changed(current_player_id: str, player_order: List[str]) -> NetworkMessage:
        """턴 변경 메시지 생성"""
        return NetworkMessage(
            type=MessageType.TURN_CHANGED,
            data={
                "current_player_id": current_player_id,
                "player_order": player_order
            }
        )
    
    @staticmethod
    def game_start(dungeon_data: Dict[str, Any], floor_number: int, dungeon_seed: int, difficulty: str, passives: Optional[List[str]] = None, player_positions: Optional[Dict[str, Tuple[int, int]]] = None) -> NetworkMessage:
        """게임 시작 메시지 생성"""
        data = {
            "dungeon": dungeon_data,
            "floor_number": floor_number,
            "seed": dungeon_seed,
            "difficulty": difficulty
        }
        if passives:
            data["passives"] = passives
        if player_positions:
            # 플레이어 위치를 딕셔너리로 변환 (JSON 직렬화 가능하도록)
            data["player_positions"] = {pid: {"x": pos[0], "y": pos[1]} for pid, pos in player_positions.items()}
        return NetworkMessage(
            type=MessageType.GAME_START,
            data=data
        )
    
    @staticmethod
    def passives_set(passives: List[str]) -> NetworkMessage:
        """패시브 설정 메시지 생성"""
        return NetworkMessage(
            type=MessageType.PASSIVES_SET,
            data={
                "passives": passives
            }
        )
    
    @staticmethod
    def character_revival(player_id: str, character_id: str, position: Tuple[int, int]) -> NetworkMessage:
        """캐릭터 부활 메시지 생성"""
        return NetworkMessage(
            type=MessageType.CHARACTER_REVIVAL,
            player_id=player_id,
            data={
                "character_id": character_id,
                "x": position[0],
                "y": position[1]
            }
        )
    
    @staticmethod
    def player_mark_update(player_id: str, is_visible: bool) -> NetworkMessage:
        """플레이어 마크 업데이트 메시지 생성"""
        return NetworkMessage(
            type=MessageType.PLAYER_MARK_UPDATE,
            player_id=player_id,
            data={
                "is_visible": is_visible
            }
        )
    
    @staticmethod
    def harvest(x: int, y: int, object_type: str) -> NetworkMessage:
        """채집 메시지 생성"""
        return NetworkMessage(
            type=MessageType.HARVEST,
            data={
                "x": x,
                "y": y,
                "object_type": object_type
            }
        )
    
    @staticmethod
    def item_picked_up(x: int, y: int) -> NetworkMessage:
        """아이템 획득 메시지 생성"""
        return NetworkMessage(
            type=MessageType.ITEM_PICKED_UP,
            data={
                "x": x,
                "y": y
            }
        )
    
    @staticmethod
    def item_dropped(x: int, y: int, item_data: Dict[str, Any]) -> NetworkMessage:
        """아이템 드롭 메시지 생성"""
        return NetworkMessage(
            type=MessageType.ITEM_DROPPED,
            data={
                "x": x,
                "y": y,
                "item": item_data
            }
        )
    
    @staticmethod
    def gold_dropped(x: int, y: int, amount: int) -> NetworkMessage:
        """골드 드롭 메시지 생성"""
        return NetworkMessage(
            type=MessageType.GOLD_DROPPED,
            data={
                "x": x,
                "y": y,
                "amount": amount
            }
        )

