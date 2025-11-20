"""
게임 모드 정의

싱글플레이와 멀티플레이 모드를 구분합니다.
"""

from enum import Enum
from typing import Optional, Dict, Any


class GameMode(Enum):
    """게임 모드"""
    SINGLE_PLAYER = "single_player"  # 싱글플레이
    MULTIPLAYER = "multiplayer"      # 멀티플레이


class MultiplayerMode(Enum):
    """멀티플레이 모드 (플레이어 수별)"""
    TWO_PLAYERS = 2   # 2인 플레이
    THREE_PLAYERS = 3  # 3인 플레이
    FOUR_PLAYERS = 4   # 4인 플레이


class GameModeManager:
    """게임 모드 관리자"""
    
    def __init__(self):
        """초기화"""
        self.current_mode: Optional[GameMode] = None
        self.multiplayer_mode: Optional[MultiplayerMode] = None
        self.is_host: bool = False
        self.session_id: Optional[str] = None
    
    def set_single_player(self):
        """싱글플레이 모드로 설정"""
        self.current_mode = GameMode.SINGLE_PLAYER
        self.multiplayer_mode = None
        self.is_host = False
        self.session_id = None
    
    def set_multiplayer(
        self,
        player_count: int,
        is_host: bool = True,
        session_id: Optional[str] = None
    ):
        """
        멀티플레이 모드로 설정
        
        Args:
            player_count: 플레이어 수 (2, 3, 또는 4)
            is_host: 호스트 여부
            session_id: 세션 ID (클라이언트인 경우)
        """
        self.current_mode = GameMode.MULTIPLAYER
        
        # 플레이어 수에 따른 모드 설정
        if player_count == 2:
            self.multiplayer_mode = MultiplayerMode.TWO_PLAYERS
        elif player_count == 3:
            self.multiplayer_mode = MultiplayerMode.THREE_PLAYERS
        elif player_count == 4:
            self.multiplayer_mode = MultiplayerMode.FOUR_PLAYERS
        else:
            raise ValueError(f"지원하지 않는 플레이어 수: {player_count}")
        
        self.is_host = is_host
        self.session_id = session_id
    
    def is_single_player(self) -> bool:
        """싱글플레이 모드인지 확인"""
        return self.current_mode == GameMode.SINGLE_PLAYER
    
    def is_multiplayer(self) -> bool:
        """멀티플레이 모드인지 확인"""
        return self.current_mode == GameMode.MULTIPLAYER
    
    def get_max_players(self) -> int:
        """
        최대 플레이어 수 가져오기
        
        Returns:
            최대 플레이어 수 (싱글플레이면 1, 멀티플레이면 2/3/4)
        """
        if self.is_single_player():
            return 1
        
        if self.multiplayer_mode:
            return self.multiplayer_mode.value
        
        return 1
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "mode": self.current_mode.value if self.current_mode else None,
            "multiplayer_mode": self.multiplayer_mode.value if self.multiplayer_mode else None,
            "is_host": self.is_host,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameModeManager':
        """딕셔너리에서 생성"""
        manager = cls()
        
        if data.get("mode") == "single_player":
            manager.set_single_player()
        elif data.get("mode") == "multiplayer":
            player_count = data.get("multiplayer_mode", 4)
            manager.set_multiplayer(
                player_count=player_count,
                is_host=data.get("is_host", True),
                session_id=data.get("session_id")
            )
        
        return manager


# 전역 게임 모드 관리자 인스턴스
_game_mode_manager: Optional[GameModeManager] = None


def get_game_mode_manager() -> GameModeManager:
    """
    게임 모드 관리자 가져오기 (싱글톤)
    
    Returns:
        GameModeManager 인스턴스
    """
    global _game_mode_manager
    
    if _game_mode_manager is None:
        _game_mode_manager = GameModeManager()
    
    return _game_mode_manager


def set_game_mode(mode: GameMode):
    """
    게임 모드 설정
    
    Args:
        mode: 게임 모드
    """
    manager = get_game_mode_manager()
    
    if mode == GameMode.SINGLE_PLAYER:
        manager.set_single_player()
    else:
        # 멀티플레이 모드는 별도로 설정 필요
        pass


def is_single_player_mode() -> bool:
    """
    싱글플레이 모드인지 확인
    
    Returns:
        싱글플레이 모드 여부
    """
    return get_game_mode_manager().is_single_player()


def is_multiplayer_mode() -> bool:
    """
    멀티플레이 모드인지 확인
    
    Returns:
        멀티플레이 모드 여부
    """
    return get_game_mode_manager().is_multiplayer()

