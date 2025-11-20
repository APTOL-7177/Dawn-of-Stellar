"""
전투 도중 합류 시스템

다른 플레이어가 전투 중인 지역에 진입 시 자동으로 전투에 참여합니다.
"""

import time
from typing import List, Dict, Optional, Tuple, Any, Set
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class CombatJoinHandler:
    """전투 도중 합류 처리"""
    
    def __init__(self, session: Optional[MultiplayerSession] = None):
        """
        초기화
        
        Args:
            session: 멀티플레이 세션
        """
        self.session = session
        self.logger = get_logger("multiplayer.combat_join")
        
        # 참여 가능 반경 (타일)
        self.participation_radius = MultiplayerConfig.participation_radius  # 5 타일
        
        # 합류 체크 주기 (초)
        self.join_check_interval = 0.5  # 0.5초마다 체크
        self.last_check_time = 0.0
        
        # 현재 진행 중인 전투 위치 추적
        self.active_combat_positions: Dict[str, Tuple[int, int]] = {}  # {combat_id: (x, y)}
        
        # 이미 합류한 플레이어 추적 (중복 합류 방지)
        self.joined_players: Dict[str, Set[str]] = {}  # {combat_id: {player_id, ...}}
    
    def register_combat(self, combat_id: str, position: Tuple[int, int]):
        """
        전투 등록 (전투 시작 시 호출)
        
        Args:
            combat_id: 전투 ID
            position: 전투 위치 (x, y)
        """
        try:
            if not combat_id or not isinstance(combat_id, str):
                self.logger.error(f"잘못된 전투 ID: {combat_id}")
                return
            
            if not position or not isinstance(position, tuple) or len(position) != 2:
                self.logger.error(f"잘못된 전투 위치: {position}")
                return
            
            x, y = position
            if not isinstance(x, int) or not isinstance(y, int):
                self.logger.error(f"전투 위치 좌표가 정수가 아님: {position}")
                return
            
            self.active_combat_positions[combat_id] = position
            if combat_id not in self.joined_players:
                self.joined_players[combat_id] = set()
            self.logger.info(f"전투 등록: {combat_id} at {position}")
        except Exception as e:
            self.logger.error(f"전투 등록 실패: {e}", exc_info=True)
    
    def unregister_combat(self, combat_id: str):
        """
        전투 해제 (전투 종료 시 호출)
        
        Args:
            combat_id: 전투 ID
        """
        if combat_id in self.active_combat_positions:
            del self.active_combat_positions[combat_id]
        if combat_id in self.joined_players:
            del self.joined_players[combat_id]
        self.logger.info(f"전투 해제: {combat_id}")
    
    def calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """
        맨하탄 거리 계산
        
        Args:
            pos1: 위치 1 (x, y)
            pos2: 위치 2 (x, y)
            
        Returns:
            거리
        """
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def can_join_combat(self, player_id: str, player_position: Tuple[int, int], combat_id: str) -> bool:
        """
        전투 합류 가능 여부 확인
        
        Args:
            player_id: 플레이어 ID
            player_position: 플레이어 위치 (x, y)
            combat_id: 전투 ID
            
        Returns:
            합류 가능 여부
        """
        try:
            if not player_id or not isinstance(player_id, str):
                self.logger.warning(f"잘못된 플레이어 ID: {player_id}")
                return False
            
            if not combat_id or not isinstance(combat_id, str):
                self.logger.warning(f"잘못된 전투 ID: {combat_id}")
                return False
            
            if not player_position or not isinstance(player_position, tuple) or len(player_position) != 2:
                self.logger.warning(f"잘못된 플레이어 위치: {player_position}")
                return False
            
            # 전투가 진행 중인지 확인
            if combat_id not in self.active_combat_positions:
                return False
            
            # 이미 합류한 플레이어인지 확인
            if player_id in self.joined_players.get(combat_id, set()):
                return False
            
            # 거리 계산
            combat_position = self.active_combat_positions[combat_id]
            if not combat_position:
                self.logger.warning(f"전투 위치를 찾을 수 없음: {combat_id}")
                return False
            
            distance = self.calculate_distance(player_position, combat_position)
            
            # 반경 내에 있는지 확인
            return distance <= self.participation_radius
        except Exception as e:
            self.logger.error(f"전투 합류 가능 여부 확인 실패: {e}", exc_info=True)
            return False
    
    def find_nearby_combats(self, player_position: Tuple[int, int]) -> List[str]:
        """
        근처 진행 중인 전투 찾기
        
        Args:
            player_position: 플레이어 위치 (x, y)
            
        Returns:
            근처 전투 ID 리스트
        """
        nearby_combats = []
        
        for combat_id, combat_position in self.active_combat_positions.items():
            distance = self.calculate_distance(player_position, combat_position)
            if distance <= self.participation_radius:
                nearby_combats.append(combat_id)
        
        return nearby_combats
    
    def mark_player_joined(self, combat_id: str, player_id: str):
        """
        플레이어가 전투에 합류했음을 표시
        
        Args:
            combat_id: 전투 ID
            player_id: 플레이어 ID
        """
        if combat_id not in self.joined_players:
            self.joined_players[combat_id] = set()
        self.joined_players[combat_id].add(player_id)
        self.logger.info(f"플레이어 {player_id} 전투 {combat_id}에 합류 표시")
    
    def check_auto_join(self, current_time: float, all_players: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        자동 합류 체크 (주기적으로 호출)
        
        Args:
            current_time: 현재 시간
            all_players: 모든 플레이어 딕셔너리 {player_id: player_object}
            
        Returns:
            합류할 플레이어 정보 리스트 [{"player_id": ..., "combat_id": ..., "position": ...}, ...]
        """
        try:
            if not isinstance(current_time, (int, float)) or current_time < 0:
                self.logger.warning(f"잘못된 시간 값: {current_time}")
                return []
            
            if not isinstance(all_players, dict):
                self.logger.warning(f"잘못된 플레이어 딕셔너리: {type(all_players)}")
                return []
            
            # 주기적으로 체크 (0.5초마다)
            if current_time - self.last_check_time < self.join_check_interval:
                return []
            
            self.last_check_time = current_time
            
            # 전투가 진행 중이 아니면 스킵
            if not self.active_combat_positions:
                return []
            
            join_requests = []
            
            # 모든 플레이어 확인
            for player_id, player in all_players.items():
                try:
                    if not player_id or not isinstance(player_id, str):
                        continue
                    
                    if not player:
                        continue
                    
                    if not hasattr(player, 'x') or not hasattr(player, 'y'):
                        continue
                    
                    try:
                        x = int(player.x)
                        y = int(player.y)
                        player_position = (x, y)
                    except (ValueError, TypeError, AttributeError):
                        self.logger.warning(f"플레이어 {player_id}의 위치를 읽을 수 없음")
                        continue
                    
                    # 근처 전투 찾기
                    nearby_combats = self.find_nearby_combats(player_position)
                    
                    for combat_id in nearby_combats:
                        # 합류 가능 여부 확인
                        if self.can_join_combat(player_id, player_position, combat_id):
                            join_requests.append({
                                "player_id": player_id,
                                "player": player,
                                "combat_id": combat_id,
                                "position": player_position
                            })
                except Exception as e:
                    self.logger.error(f"플레이어 {player_id} 합류 체크 실패: {e}", exc_info=True)
                    continue
            
            return join_requests
        except Exception as e:
            self.logger.error(f"자동 합류 체크 실패: {e}", exc_info=True)
            return []

