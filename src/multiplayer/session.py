"""
멀티플레이 세션 관리

게임 세션의 생명주기와 플레이어 관리를 담당합니다.
"""

import random
import time
from typing import Dict, List, Optional, Set, Any
from uuid import uuid4

from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class MultiplayerSession:
    """멀티플레이 세션"""
    
    def __init__(self, max_players: int = 4, host_id: Optional[str] = None):
        """
        세션 초기화
        
        Args:
            max_players: 최대 플레이어 수 (2, 3, 또는 4)
            host_id: 호스트 플레이어 ID (없으면 첫 번째 플레이어가 호스트)
            
        Raises:
            ValueError: max_players가 2~4 범위를 벗어난 경우
        """
        # 최대 플레이어 수 검증
        if not (2 <= max_players <= 4):
            raise ValueError(f"max_players는 2~4 사이여야 합니다 (받음: {max_players})")
        
        self.session_id = str(uuid4())
        self.max_players = max_players
        self.host_id = host_id
        
        self.players: Dict[str, MultiplayerPlayer] = {}
        self.player_count = 0
        
        # 세션 시드 (던전 생성용)
        self.session_seed = random.randint(0, 2**31 - 1)
        
        # 던전 캐시
        self.floors: Dict[int, Any] = {}  # {floor: dungeon}
        
        # 밸런스 설정 (싱글플레이와 동일)
        self.balance_settings = {
            "enemy_count_multiplier": MultiplayerConfig.enemy_count_multiplier,
            "enemy_hp_multiplier": MultiplayerConfig.enemy_hp_multiplier,
            "enemy_damage_multiplier": MultiplayerConfig.enemy_damage_multiplier,
            "exp_multiplier": 1.0,
            "drop_rate_multiplier": 1.0
        }
        
        self.logger = get_logger("multiplayer.session")
        self.created_at = time.time()
        self.is_active = True
        
        # 다음 층 이동 준비 상태 (모든 플레이어가 준비해야 이동 가능)
        self.floor_ready_players: Set[str] = set()
    
    def add_player(self, player: MultiplayerPlayer) -> bool:
        """
        플레이어 추가
        
        Args:
            player: 추가할 플레이어
            
        Returns:
            추가 성공 여부
            
        Raises:
            TypeError: player가 None이거나 MultiplayerPlayer가 아닌 경우
            ValueError: player_id가 없는 경우
        """
        # None 체크
        if player is None:
            self.logger.error(f"세션 {self.session_id}: 플레이어가 None입니다")
            raise TypeError("player는 None일 수 없습니다")
        
        # 타입 체크
        if not isinstance(player, MultiplayerPlayer):
            self.logger.error(f"세션 {self.session_id}: 잘못된 플레이어 타입: {type(player)}")
            raise TypeError(f"player는 MultiplayerPlayer 타입이어야 합니다 (받음: {type(player)})")
        
        # player_id 체크
        if not player.player_id:
            self.logger.error(f"세션 {self.session_id}: 플레이어 ID가 없습니다")
            raise ValueError("player.player_id는 필수입니다")
        
        # 최대 인원 체크
        if self.player_count >= self.max_players:
            self.logger.warning(f"세션 {self.session_id}: 최대 인원 도달 ({self.max_players}명)")
            return False
        
        # 이미 존재하는 플레이어 체크
        if player.player_id in self.players:
            self.logger.warning(f"세션 {self.session_id}: 플레이어 {player.player_id} 이미 존재")
            return False
        
        # 플레이어 추가
        player.session_id = self.session_id
        self.players[player.player_id] = player
        self.player_count += 1
        
        # 첫 번째 플레이어를 호스트로 설정
        if self.host_id is None:
            self.host_id = player.player_id
            player.is_host = True
            self.logger.info(f"세션 {self.session_id}: 플레이어 {player.player_id}를 호스트로 설정")
        elif player.player_id == self.host_id:
            player.is_host = True
        
        self.logger.info(
            f"세션 {self.session_id}: 플레이어 {player.player_name} ({player.player_id}) 추가 "
            f"(현재: {self.player_count}/{self.max_players})"
        )
        
        return True
    
    def remove_player(self, player_id: str) -> bool:
        """
        플레이어 제거
        
        Args:
            player_id: 제거할 플레이어 ID
            
        Returns:
            제거 성공 여부
            
        Raises:
            TypeError: player_id가 None이거나 str이 아닌 경우
        """
        # None 체크
        if player_id is None:
            self.logger.error(f"세션 {self.session_id}: player_id가 None입니다")
            raise TypeError("player_id는 None일 수 없습니다")
        
        # 타입 체크
        if not isinstance(player_id, str):
            self.logger.error(f"세션 {self.session_id}: 잘못된 player_id 타입: {type(player_id)}")
            raise TypeError(f"player_id는 str 타입이어야 합니다 (받음: {type(player_id)})")
        
        if player_id not in self.players:
            self.logger.warning(f"세션 {self.session_id}: 플레이어 {player_id}가 존재하지 않습니다")
            return False
        
        player = self.players[player_id]
        del self.players[player_id]
        self.player_count -= 1
        
        self.logger.info(
            f"세션 {self.session_id}: 플레이어 {player.player_name} ({player_id}) 제거 "
            f"(현재: {self.player_count}/{self.max_players})"
        )
        
        # 호스트가 나간 경우, 다른 플레이어를 호스트로 설정
        if player_id == self.host_id:
            if self.players:
                # 아직 플레이어가 있으면 새로운 호스트 선택
                new_host_id = next(iter(self.players.keys()))
                self.host_id = new_host_id
                if new_host_id in self.players:
                    self.players[new_host_id].is_host = True
                self.logger.info(f"세션 {self.session_id}: 새로운 호스트 {new_host_id}")
            else:
                # 모든 플레이어가 나간 경우
                self.host_id = None
                self.logger.warning(f"세션 {self.session_id}: 모든 플레이어가 나감 (호스트 없음)")
        
        return True
    
    def get_player(self, player_id: str) -> Optional[MultiplayerPlayer]:
        """
        플레이어 가져오기
        
        Args:
            player_id: 플레이어 ID
            
        Returns:
            플레이어 객체, 없으면 None
            
        Raises:
            TypeError: player_id가 None이거나 str이 아닌 경우
        """
        if player_id is None:
            raise TypeError("player_id는 None일 수 없습니다")
        if not isinstance(player_id, str):
            raise TypeError(f"player_id는 str 타입이어야 합니다 (받음: {type(player_id)})")
        
        return self.players.get(player_id)
    
    def is_host(self, player_id: str) -> bool:
        """
        호스트 여부 확인
        
        Args:
            player_id: 플레이어 ID
            
        Returns:
            호스트 여부
            
        Raises:
            TypeError: player_id가 None이거나 str이 아닌 경우
        """
        if player_id is None:
            return False
        if not isinstance(player_id, str):
            return False
        
        return player_id == self.host_id and self.host_id is not None
    
    def is_full(self) -> bool:
        """세션이 가득 찼는지 확인"""
        return self.player_count >= self.max_players
    
    def generate_dungeon_seed_for_floor(self, floor_number: int) -> int:
        """
        층별 던전 시드 생성
        
        Args:
            floor_number: 층 번호
            
        Returns:
            층별 고유 시드
        """
        # 세션 시드와 층 번호를 조합하여 고유한 시드 생성
        return hash((self.session_seed, floor_number)) % (2**31)
    
    def get_balance_multiplier(self, key: str) -> float:
        """
        밸런스 배율 조회
        
        Args:
            key: 밸런스 키 (예: "enemy_count_multiplier")
            
        Returns:
            배율 값
        """
        return self.balance_settings.get(key, 1.0)
    
    def serialize(self) -> Dict[str, Any]:
        """세션 직렬화"""
        return {
            "session_id": self.session_id,
            "max_players": self.max_players,
            "host_id": self.host_id,
            "player_count": self.player_count,
            "players": {
                pid: player.serialize() for pid, player in self.players.items()
            },
            "session_seed": self.session_seed,
            "created_at": self.created_at,
            "is_active": self.is_active
        }
    
    def set_floor_ready(self, player_id: str, ready: bool = True) -> None:
        """
        다음 층 이동 준비 상태 설정
        
        Args:
            player_id: 플레이어 ID
            ready: 준비 여부
        """
        if ready:
            self.floor_ready_players.add(player_id)
        else:
            self.floor_ready_players.discard(player_id)
        self.logger.debug(f"플레이어 {player_id} 층 이동 준비 상태: {ready} (준비: {len(self.floor_ready_players)}/{self.player_count})")
    
    def is_all_ready_for_floor_change(self) -> bool:
        """
        모든 플레이어가 다음 층 이동 준비가 되었는지 확인
        
        Returns:
            모든 플레이어가 준비되었으면 True
        """
        # 모든 플레이어(봇 포함)가 준비 상태인지 확인
        all_players = set(self.players.keys())
        return len(self.floor_ready_players) > 0 and self.floor_ready_players == all_players
    
    def reset_floor_ready(self) -> None:
        """다음 층 이동 준비 상태 초기화 (층 이동 후)"""
        self.floor_ready_players.clear()
        self.logger.debug("층 이동 준비 상태 초기화")
    
    def __repr__(self) -> str:
        return (
            f"MultiplayerSession(session_id={self.session_id}, "
            f"players={self.player_count}/{self.max_players}, "
            f"host={self.host_id})"
        )

