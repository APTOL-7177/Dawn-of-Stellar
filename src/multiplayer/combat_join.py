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
        self.participation_radius = MultiplayerConfig.participation_radius_player  # 10 타일
        
        # 합류 체크 주기 (초)
        self.join_check_interval = 0.5  # 0.5초마다 체크
        self.last_check_time = 0.0
        
        # 현재 진행 중인 전투 위치 추적
        self.active_combat_positions: Dict[str, Tuple[int, int]] = {}  # {combat_id: (x, y)}
        # 전투 시작 시각 추적 (late-join grace window 검증용, t_7846bbe3 §5.4)
        self.combat_start_times: Dict[str, float] = {}  # {combat_id: start_monotonic_time}
        # 이미 합류한 플레이어 추적 (중복 합류 방지)
        self.joined_players: Dict[str, Set[str]] = {}  # {combat_id: {player_id, ...}}

        # late-join 허용 시간 (초). 전투 시작 후 이 시간이 지나면 합류 거부
        self.late_join_grace = MultiplayerConfig.combat_join_grace_window
    
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
            self.combat_start_times[combat_id] = time.time()
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
        if combat_id in self.combat_start_times:
            del self.combat_start_times[combat_id]
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
    
    def validate_late_join(
        self,
        player_id: str,
        combat_id: str,
        epoch: int,
        combat_epoch_start: Optional[float] = None,
        server_epoch: Optional[int] = None,
        requester_alive: bool = True,
        grace_window: Optional[float] = None,
    ) -> Tuple[bool, Optional[str]]:
        """late COMBAT_JOIN 정합 검증 (t_7846bbe3 §5.4)

        검증 순서: (a) epoch 일치, (b) 전투 active, (c) 요청자 생존,
        (d) 중복 합류, (e) grace window 이내.

        Args:
            player_id: 합류 요청 플레이어 ID
            combat_id: 대상 전투 ID
            epoch: 요청 메시지의 세션 epoch
            combat_epoch_start: 전투 시작 시각 (monotonic). None이면 내부 기록 사용
            server_epoch: 호스트의 현재 세션 epoch
            requester_alive: 요청자 생존 여부
            grace_window: 허용 시간(초) override. None이면 기본값 사용

        Returns:
            (허용 여부, 거부 사유 — 허용 시 None)
        """
        # (a) epoch 일치
        if server_epoch is not None and epoch != server_epoch:
            self.logger.warning(f"late join 거부 (epoch 불일치): player={player_id}, {epoch} != {server_epoch}")
            return False, "epoch_mismatch"

        # (b) 전투 active
        if combat_id not in self.active_combat_positions:
            return False, "combat_not_active"

        # (c) 요청자 생존
        if not requester_alive:
            return False, "requester_dead"

        # (d) 중복 합류
        if player_id in self.joined_players.get(combat_id, set()):
            return False, "already_joined"

        # (e) grace window (wall clock 기준 — 전투 시작 시각도 time.time()으로 기록)
        if grace_window is None:
            grace_window = self.late_join_grace
        start = combat_epoch_start
        if start is None:
            start = self.combat_start_times.get(combat_id)
        if start is not None:
            elapsed = time.time() - start
            if elapsed > grace_window:
                self.logger.warning(
                    f"late join 거부 (grace 초과): player={player_id}, combat={combat_id}, "
                    f"elapsed={elapsed:.1f}s > grace={grace_window:.1f}s"
                )
                return False, "grace_exceeded"

        return True, None
    
    def mark_player_joined(self, combat_id: str, player_id: str, combat_manager: Optional[Any] = None, characters: Optional[List[Any]] = None):
        """
        플레이어가 전투에 합류했음을 표시하고 ATB/BRV 초기화

        Args:
            combat_id: 전투 ID
            player_id: 플레이어 ID
            combat_manager: 전투 관리자 (ATB/BRV 초기화용)
            characters: 합류 플레이어의 캐릭터 리스트
        """
        if combat_id not in self.joined_players:
            self.joined_players[combat_id] = set()
        self.joined_players[combat_id].add(player_id)
        self.logger.info(f"플레이어 {player_id} 전투 {combat_id}에 합류 표시")

        # ATB 시스템에 새 전투원 등록 및 BRV 초기화
        if combat_manager and characters:
            for char in characters:
                try:
                    if hasattr(combat_manager, 'atb') and combat_manager.atb:
                        combat_manager.atb.register_combatant(char)
                        self.logger.debug(f"ATB 등록: {getattr(char, 'name', 'Unknown')}")
                    if hasattr(combat_manager, 'brave') and combat_manager.brave:
                        combat_manager.brave.initialize_brv(char)
                        self.logger.debug(f"BRV 초기화: {getattr(char, 'name', 'Unknown')}")
                except Exception as e:
                    self.logger.error(f"합류 캐릭터 초기화 실패: {e}", exc_info=True)
    
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

