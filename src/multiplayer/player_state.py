"""
멀티플레이 플레이어 상태 관리

캐릭터 사망/부활, 마크 표시 등을 관리합니다.
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import time

from src.character.character import Character
from src.multiplayer.player import MultiplayerPlayer
from src.core.logger import get_logger


@dataclass
class PlayerMarkState:
    """플레이어 마크 상태"""
    
    player_id: str
    is_visible: bool = True  # @ 마크 표시 여부
    last_death_time: Optional[float] = None  # 마지막 사망 시간
    
    def __post_init__(self):
        """초기화 후 처리"""
        pass


class PlayerStateManager:
    """플레이어 상태 관리자"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger("multiplayer.player_state")
        self.mark_states: Dict[str, PlayerMarkState] = {}  # {player_id: PlayerMarkState}
    
    def update_player_state(self, player: MultiplayerPlayer):
        """
        플레이어 상태 업데이트 (사망 여부 체크)
        
        Args:
            player: 플레이어 객체
        """
        # 플레이어의 모든 캐릭터가 살아있는지 확인
        all_dead = True
        
        if hasattr(player, 'party') and player.party:
            for character in player.party:
                # Character 객체는 is_alive 속성을 가지고 있음
                if hasattr(character, 'is_alive'):
                    if character.is_alive:
                        all_dead = False
                        break
                # is_alive 속성이 없으면 current_hp로 판단
                elif hasattr(character, 'current_hp'):
                    if character.current_hp > 0:
                        all_dead = False
                        break
        
        # 마크 상태 업데이트
        if player.player_id not in self.mark_states:
            self.mark_states[player.player_id] = PlayerMarkState(player_id=player.player_id)
        
        mark_state = self.mark_states[player.player_id]
        
        if all_dead:
            # 모든 캐릭터가 죽었으면 마크 숨김
            if mark_state.is_visible:
                mark_state.is_visible = False
                mark_state.last_death_time = time.time()
                self.logger.info(f"플레이어 {player.player_id}의 모든 캐릭터가 사망 - @ 마크 숨김")
        else:
            # 하나라도 살아있으면 마크 표시
            if not mark_state.is_visible:
                mark_state.is_visible = True
                mark_state.last_death_time = None
                self.logger.info(f"플레이어 {player.player_id}의 캐릭터 부활 - @ 마크 표시")
    
    def is_mark_visible(self, player_id: str) -> bool:
        """
        플레이어 마크 표시 여부 확인
        
        Args:
            player_id: 플레이어 ID
            
        Returns:
            마크 표시 여부
        """
        if player_id not in self.mark_states:
            return True  # 기본값: 표시
        
        return self.mark_states[player_id].is_visible
    
    def handle_character_revival(
        self,
        player: MultiplayerPlayer,
        revived_character: Character,
        revive_position: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        """
        캐릭터 부활 처리
        
        Args:
            player: 플레이어 객체
            revived_character: 부활한 캐릭터
            revive_position: 부활 위치 (None이면 플레이어 옆에 스폰)
            
        Returns:
            (x, y) 부활 위치
        """
        # 부활 위치 결정
        if revive_position:
            x, y = revive_position
        else:
            # 플레이어 옆에 스폰 (플레이어 위치 기준 상하좌우 중 하나)
            x, y = self._find_spawn_position_near_player(player)
        
        # 캐릭터 위치 설정 (Character 객체는 x, y 속성을 가지지 않을 수 있음)
        # 맵 탐험 시스템에서 별도로 관리될 수 있으므로 여기서는 설정하지 않음
        # 대신 부활 위치를 반환하여 상위 시스템에서 처리하도록 함
        try:
            if hasattr(revived_character, 'x'):
                revived_character.x = x
            if hasattr(revived_character, 'y'):
                revived_character.y = y
        except (AttributeError, TypeError) as e:
            # x, y 속성이 없거나 설정할 수 없는 경우 무시
            self.logger.debug(f"캐릭터 위치 설정 실패 (속성 없음): {e}")
        
        # 상태 업데이트
        self.update_player_state(player)
        
        self.logger.info(
            f"플레이어 {player.player_id}의 캐릭터 {revived_character.name} 부활 "
            f"위치: ({x}, {y})"
        )
        
        return (x, y)
    
    def _find_spawn_position_near_player(
        self,
        player: MultiplayerPlayer,
        radius: int = 2
    ) -> Tuple[int, int]:
        """
        플레이어 옆에 안전한 스폰 위치 찾기
        
        Args:
            player: 플레이어 객체
            radius: 검색 반경
            
        Returns:
            (x, y) 스폰 위치
        """
        # 플레이어 위치
        px, py = player.x, player.y
        
        # 플레이어 옆 위치들 (상하좌우 대각선 포함)
        positions = [
            (px + 1, py),      # 오른쪽
            (px - 1, py),      # 왼쪽
            (px, py + 1),      # 아래
            (px, py - 1),      # 위
            (px + 1, py + 1),  # 오른쪽 아래
            (px + 1, py - 1),  # 오른쪽 위
            (px - 1, py + 1),  # 왼쪽 아래
            (px - 1, py - 1),  # 왼쪽 위
        ]
        
        # 첫 번째 유효한 위치 반환 (실제로는 맵 유효성 체크 필요)
        for x, y in positions:
            # 여기서는 단순히 첫 번째 위치 반환
            # 실제 구현에서는 맵의 walkable 체크 필요
            return (x, y)
        
        # 모든 위치가 유효하지 않으면 플레이어 위치 반환
        return (px, py)
    
    def get_mark_positions(self, players: Dict[str, MultiplayerPlayer]) -> Dict[str, Tuple[int, int]]:
        """
        마크가 표시될 플레이어들의 위치 반환
        
        Args:
            players: 플레이어 딕셔너리
            
        Returns:
            {player_id: (x, y)} 마크가 표시될 플레이어 위치
        """
        positions = {}
        
        for player_id, player in players.items():
            if self.is_mark_visible(player_id):
                positions[player_id] = (player.x, player.y)
        
        return positions
    
    def handle_character_death(
        self,
        player: MultiplayerPlayer,
        dead_character: Character
    ):
        """
        캐릭터 사망 처리
        
        Args:
            player: 플레이어 객체
            dead_character: 사망한 캐릭터
        """
        # 상태 업데이트 (모든 캐릭터가 죽었는지 확인)
        self.update_player_state(player)
        
        self.logger.info(
            f"플레이어 {player.player_id}의 캐릭터 {dead_character.name} 사망"
        )

