"""
멀티플레이 플레이어 객체

각 플레이어의 정보와 상태를 관리합니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import uuid4
import time


@dataclass
class MultiplayerPlayer:
    """멀티플레이 플레이어"""
    
    player_id: str  # 고유 ID
    player_name: str  # 플레이어 이름
    x: int = 0
    y: int = 0
    party: List[Any] = field(default_factory=list)  # 플레이어의 파티 (최대 4명)
    character_id: Optional[str] = None  # 현재 조작 중인 캐릭터 ID
    
    # 호스트 여부
    is_host: bool = False
    
    # 봇 여부
    is_bot: bool = False
    
    # 네트워크 동기화용
    last_update_time: float = field(default_factory=time.time)
    velocity_x: float = 0.0  # 예측용 속도
    velocity_y: float = 0.0
    
    # 연결 상태
    is_connected: bool = True
    last_ping: float = 0.0
    ping: float = 0.0  # 밀리초
    
    # 세션 정보
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not self.player_id:
            self.player_id = str(uuid4())
    
    def update_position(self, x: int, y: int):
        """위치 업데이트"""
        self.velocity_x = x - self.x
        self.velocity_y = y - self.y
        self.x = x
        self.y = y
        self.last_update_time = time.time()
    
    def serialize(self) -> Dict[str, Any]:
        """직렬화"""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "x": self.x,
            "y": self.y,
            "character_id": self.character_id,
            "party_count": len(self.party),
            "is_connected": self.is_connected,
            "ping": self.ping,
            "is_bot": self.is_bot
        }
    
    @property
    def is_party_alive(self) -> bool:
        """파티 생존 여부 확인"""
        if not self.party:
            return True # 파티가 없으면 살아있는 것으로 간주 (또는 로직에 따라 False)
            
        for member in self.party:
            # member는 Character 객체 또는 딕셔너리(직렬화된 경우)
            if isinstance(member, dict):
                if member.get('current_hp', 0) > 0:
                    return True
            else:
                if getattr(member, 'current_hp', 0) > 0 and getattr(member, 'is_alive', True):
                    return True
        return False

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "MultiplayerPlayer":
        """역직렬화"""
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            x=data.get("x", 0),
            y=data.get("y", 0),
            character_id=data.get("character_id"),
            is_connected=data.get("is_connected", True),
            ping=data.get("ping", 0.0),
            is_bot=data.get("is_bot", False)
        )
