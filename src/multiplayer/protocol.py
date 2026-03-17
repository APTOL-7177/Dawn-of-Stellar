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
    HOST_MIGRATED = "host_migrated"  # 호스트 마이그레이션 알림
    
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
    MOVEMENT_REJECTED = "movement_rejected"  # 이동 거절 (롤백용)
    POSITION_SYNC = "position_sync"  # 위치 동기화 (주기적)
    REQUEST_COMBAT_START = "request_combat_start"  # 클라이언트가 호스트에게 전투 시작 요청
    COMBAT_START = "combat_start"
    COMBAT_JOIN = "combat_join"
    COMBAT_ACTION = "combat_action"
    COMBAT_FLEE_RESULT = "combat_flee_result"  # 도망 결과 브로드캐스트
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
    FLOOR_READY = "floor_ready"  # 층 이동 준비 상태 동기화
    
    # 채집/아이템
    HARVEST = "harvest"  # 채집 오브젝트 수집
    ITEM_DROPPED = "item_dropped"  # 아이템 드롭
    GOLD_DROPPED = "gold_dropped"  # 골드 드롭
    
    # 전리품/창고 동기화
    LOOT_CLAIMED = "loot_claimed"  # 전리품 선점 결과
    STORAGE_UPDATE = "storage_update"  # 창고 변경 알림

    # 호감도/유대 시스템
    AFFINITY_UPDATE = "affinity_update"  # 호감도 변경 동기화
    BOND_SKILL_TRIGGERED = "bond_skill_triggered"  # 연계스킬 발동 알림
    CHAIN_ABILITY_TRIGGERED = "chain_ability_triggered"  # 체인어빌리티 발동 알림
    CHAIN_ABILITY_CONFIRMED = "chain_ability_confirmed"  # 체인어빌리티 확정 알림

    # 시너지/합체기
    COMBO_SKILL_EXECUTED = "combo_skill_executed"  # 합체기 실행 알림

    # 랜덤 이벤트
    RANDOM_EVENT_TRIGGER = "random_event_trigger"  # 랜덤 이벤트 발생
    RANDOM_EVENT_CHOICE = "random_event_choice"  # 랜덤 이벤트 선택지 결과

    # 퍼즐
    PUZZLE_SOLVED = "puzzle_solved"  # 퍼즐 해결 알림

    # 전투 결과/종료
    ACTION_RESULT = "action_result"  # 액션 실행 결과 브로드캐스트
    COMBAT_END = "combat_end"  # 전투 종료 알림

    # 상태 복구 (재연결용)
    REQUEST_STATE_SYNC = "request_state_sync"  # 클라이언트 -> 호스트: 전투 상태 요청
    FULL_STATE_SYNC = "full_state_sync"  # 호스트 -> 클라이언트: 전체 전투 상태 응답

    # 에러 (테스트용)
    ERROR = "error"


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
    def serialize_character_for_combat(character) -> Dict[str, Any]:
        """
        캐릭터의 핵심 전투 데이터를 직렬화

        Args:
            character: Character 객체 (아군)

        Returns:
            직렬화된 캐릭터 전투 데이터
        """
        return {
            "id": getattr(character, 'id', str(id(character))),
            "name": getattr(character, 'name', '아군'),
            "job_id": getattr(character, 'job_id', getattr(character, 'character_class', 'warrior')),
            "job_name": getattr(character, 'job_name', '전사'),
            "level": getattr(character, 'level', 1),
            "max_hp": getattr(character, 'max_hp', 100),
            "current_hp": getattr(character, 'current_hp', 100),
            "max_mp": getattr(character, 'max_mp', 50),
            "current_mp": getattr(character, 'current_mp', 50),
            "physical_attack": getattr(character, 'physical_attack', 10),
            "physical_defense": getattr(character, 'physical_defense', 10),
            "magic_attack": getattr(character, 'magic_attack', 10),
            "magic_defense": getattr(character, 'magic_defense', 10),
            "speed": getattr(character, 'speed', 50),
            "max_brv": getattr(character, 'max_brv', 1000),
            "init_brv": getattr(character, 'init_brv', 333),
            "current_brv": getattr(character, 'current_brv', 0),
            "is_alive": getattr(character, 'is_alive', True),
            "owner_player_id": getattr(character, 'owner_player_id', None),
        }

    @staticmethod
    def combat_start(participants: list, enemies: list, position: tuple, all_parties: Optional[Dict[str, list]] = None) -> NetworkMessage:
        """
        전투 시작 메시지 생성 (적 전체 데이터 + 모든 참여자 파티 포함)

        Args:
            participants: 참여자 ID 리스트
            enemies: 적 객체 리스트
            position: 전투 위치 (x, y)
            all_parties: 모든 참여 플레이어의 파티 데이터
                         {player_id: [serialized_character_data, ...]}
        """
        # 적 전체 데이터 직렬화 (클라이언트가 동일한 적을 구성할 수 있도록)
        serialized_enemies = []
        for e in enemies:
            if isinstance(e, str):
                serialized_enemies.append({"id": e})
            else:
                enemy_data = {
                    "id": getattr(e, 'id', str(e)),
                    "enemy_id": getattr(e, 'enemy_id', None),
                    "name": getattr(e, 'name', '적'),
                    "level": getattr(e, 'level', 1),
                    "max_hp": getattr(e, 'max_hp', 100),
                    "current_hp": getattr(e, 'current_hp', 100),
                    "max_mp": getattr(e, 'max_mp', 0),
                    "current_mp": getattr(e, 'current_mp', 0),
                    "physical_attack": getattr(e, 'physical_attack', 10),
                    "physical_defense": getattr(e, 'physical_defense', 5),
                    "magic_attack": getattr(e, 'magic_attack', 10),
                    "magic_defense": getattr(e, 'magic_defense', 5),
                    "speed": getattr(e, 'speed', 50),
                    "max_brv": getattr(e, 'max_brv', 1000),
                    "init_brv": getattr(e, 'init_brv', 333),
                    "current_brv": getattr(e, 'current_brv', 0),
                    "luck": getattr(e, 'luck', 10),
                    "accuracy": getattr(e, 'accuracy', 70),
                    "evasion": getattr(e, 'evasion', 10),
                    "is_boss": getattr(e, 'is_boss', False),
                    "is_floor_boss": getattr(e, 'is_floor_boss', False),
                    "is_enemy": True,
                    "is_alive": getattr(e, 'is_alive', True),
                }
                serialized_enemies.append(enemy_data)

        msg_data = {
            "participants": participants,
            "enemies": [ed.get("id", "") for ed in serialized_enemies],
            "enemy_data": serialized_enemies,
            "position": {"x": position[0], "y": position[1]}
        }

        # 모든 참여자 파티 정보 포함
        if all_parties:
            msg_data["all_parties"] = all_parties

        return NetworkMessage(
            type=MessageType.COMBAT_START,
            data=msg_data
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
    def job_selection_complete(player_id: str, party_data: List[Dict[str, Any]] = None) -> NetworkMessage:
        """직업 선택 완료 메시지 생성 (파티 데이터 포함)"""
        return NetworkMessage(
            type=MessageType.JOB_SELECTION_COMPLETE,
            player_id=player_id,
            data={
                "party_data": party_data or []
            }
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
    def item_dropped(x: int, y: int, item_data: Dict[str, Any], dropped_by_player_id: Optional[str] = None) -> NetworkMessage:
        """아이템 드롭 메시지 생성"""
        return NetworkMessage(
            type=MessageType.ITEM_DROPPED,
            data={
                "x": x,
                "y": y,
                "item": item_data,
                "dropped_by_player_id": dropped_by_player_id
            }
        )
    
    @staticmethod
    def gold_dropped(x: int, y: int, amount: int, dropped_by_player_id: Optional[str] = None) -> NetworkMessage:
        """골드 드롭 메시지 생성"""
        return NetworkMessage(
            type=MessageType.GOLD_DROPPED,
            data={
                "x": x,
                "y": y,
                "amount": amount,
                "dropped_by_player_id": dropped_by_player_id
            }
        )
    
    @staticmethod
    def state_update(data: Dict[str, Any]) -> NetworkMessage:
        """
        상태 업데이트 메시지 생성 (전투 상태 동기화용)
        
        Args:
            data: 상태 업데이트 데이터 (combat_action, combat_state, timestamp 등)
        """
        return NetworkMessage(
            type=MessageType.STATE_UPDATE,
            data={
                "data": data
            }
        )
    
    @staticmethod
    def floor_ready(player_id: str, ready: bool, ready_players: List[str], total_players: int) -> NetworkMessage:
        """
        층 이동 준비 상태 메시지 생성
        
        Args:
            player_id: 준비 상태를 변경한 플레이어 ID
            ready: 준비 여부
            ready_players: 현재 준비된 플레이어 ID 목록
            total_players: 전체 플레이어 수
        """
        return NetworkMessage(
            type=MessageType.FLOOR_READY,
            player_id=player_id,
            data={
                "ready": ready,
                "ready_players": ready_players,
                "total_players": total_players
            }
        )

    @staticmethod
    def floor_change(direction: str = "floor_down", from_town: bool = False) -> NetworkMessage:
        """
        층 이동 메시지 생성
        
        Args:
            direction: 이동 방향 ("floor_up" 또는 "floor_down")
            from_town: 마을에서 출발 여부
        """
        return NetworkMessage(
            type=MessageType.FLOOR_CHANGE,
            data={
                "direction": direction,
                "from_town": from_town
            }
        )
    
    @staticmethod
    def request_combat_start(position: Tuple[int, int], enemy_id: Optional[str] = None) -> NetworkMessage:
        """
        전투 시작 요청 메시지 생성 (클라이언트 -> 호스트)
        
        Args:
            position: 전투 위치 (x, y)
            enemy_id: 조우한 적 ID (선택사항)
        """
        return NetworkMessage(
            type=MessageType.REQUEST_COMBAT_START,
            data={
                "position": {"x": position[0], "y": position[1]},
                "enemy_id": enemy_id
            }
        )
    
    @staticmethod
    def host_migrated(new_host_id: str) -> NetworkMessage:
        """
        호스트 마이그레이션 알림 메시지 생성
        
        Args:
            new_host_id: 새로운 호스트 플레이어 ID
        """
        return NetworkMessage(
            type=MessageType.HOST_MIGRATED,
            data={
                "new_host_id": new_host_id
            }
        )
    
    @staticmethod
    def custom(msg_type: MessageType, data: Dict[str, Any]) -> NetworkMessage:
        """
        커스텀 메시지 생성

        Args:
            msg_type: 메시지 타입
            data: 메시지 데이터
        """
        return NetworkMessage(
            type=msg_type,
            data=data
        )

    @staticmethod
    def action_selection_start(actor_id: str, actor_name: str, player_id: str) -> NetworkMessage:
        """
        액션 선택 시작 메시지 생성 (호스트 -> 특정 클라이언트)

        원격 플레이어의 캐릭터 턴이 되었을 때 해당 플레이어에게 행동 선택을 요청합니다.

        Args:
            actor_id: 행동할 캐릭터 ID
            actor_name: 행동할 캐릭터 이름
            player_id: 대상 플레이어 ID
        """
        return NetworkMessage(
            type=MessageType.ACTION_SELECTION_START,
            player_id=player_id,
            data={
                "actor_id": actor_id,
                "actor_name": actor_name,
                "player_id": player_id
            }
        )

    @staticmethod
    def action_result(actor_id: str, result_data: Dict[str, Any], combat_state: Optional[Dict[str, Any]] = None) -> NetworkMessage:
        """
        액션 실행 결과 브로드캐스트 메시지 생성 (호스트 -> 모든 클라이언트)

        Args:
            actor_id: 행동한 캐릭터 ID
            result_data: 액션 실행 결과 데이터
            combat_state: 최신 전투 상태 스냅샷 (선택적)
        """
        data = {
            "actor_id": actor_id,
            "result": result_data
        }
        if combat_state:
            data["combat_state"] = combat_state
        return NetworkMessage(
            type=MessageType.ACTION_RESULT,
            data=data
        )

    @staticmethod
    def combat_end(result: str, rewards: Optional[Dict[str, Any]] = None) -> NetworkMessage:
        """
        전투 종료 메시지 생성 (호스트 -> 모든 클라이언트)

        Args:
            result: 전투 결과 ("victory", "defeat", "fled")
            rewards: 보상 데이터 (승리 시)
        """
        data: Dict[str, Any] = {
            "result": result
        }
        if rewards:
            data["rewards"] = rewards
        return NetworkMessage(
            type=MessageType.COMBAT_END,
            data=data
        )

    @staticmethod
    def movement_rejected(reason: str, correct_position: Tuple[int, int]) -> NetworkMessage:
        """
        이동 거절 메시지 생성 (호스트 -> 클라이언트)
        
        Args:
            reason: 거절 사유
            correct_position: 올바른 위치 (x, y)
        """
        return NetworkMessage(
            type=MessageType.MOVEMENT_REJECTED,
            data={
                "reason": reason,
                "x": correct_position[0],
                "y": correct_position[1]
            }
        )
