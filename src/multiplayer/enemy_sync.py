"""
적 이동 동기화 시스템

멀티플레이에서 적의 0.65초 간격 움직임을 관리합니다.
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class EnemySyncManager:
    """적 이동 동기화 관리자"""
    
    def __init__(
        self,
        session: MultiplayerSession,
        network_manager: Optional[NetworkManager] = None,
        is_host: bool = False,
        exploration: Optional[Any] = None
    ):
        """
        초기화
        
        Args:
            session: 멀티플레이 세션
            network_manager: 네트워크 관리자
            is_host: 호스트 여부
            exploration: 탐험 시스템 (적 위치 업데이트용)
        """
        self.session = session
        self.network_manager = network_manager
        self.is_host = is_host
        self.exploration = exploration
        self.logger = get_logger("multiplayer.enemy_sync")
        
        # 적 이동 간격 (0.65초)
        self.move_interval = MultiplayerConfig.SYNC_INTERVAL_ENEMY
        self.last_move_time = 0.0
        
        # 적 위치 캐시
        self.enemy_positions: Dict[str, Tuple[int, int]] = {}  # {enemy_id: (x, y)}
        
        # 네트워크 메시지 핸들러 등록
        if self.network_manager:
            self._register_handlers()
    
    def set_host_mode(self, is_host: bool):
        """
        호스트 모드 동적 전환 (호스트 마이그레이션용)

        Args:
            is_host: 새로운 호스트 여부
        """
        old_is_host = self.is_host
        self.is_host = is_host
        self.logger.info(f"EnemySyncManager 호스트 모드 전환: {old_is_host} -> {is_host}")

        # 핸들러 갱신: 호스트가 되면 적 이동 수신 핸들러 해제
        if self.network_manager:
            if is_host and not old_is_host:
                self.network_manager.unregister_handler(
                    MessageType.ENEMY_MOVE,
                    self._handle_enemy_move
                )
            elif not is_host and old_is_host:
                self.network_manager.register_handler(
                    MessageType.ENEMY_MOVE,
                    self._handle_enemy_move
                )

    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        if not self.network_manager:
            return

        # 적 이동 메시지 핸들러 (클라이언트만)
        if not self.is_host:
            self.network_manager.register_handler(
                MessageType.ENEMY_MOVE,
                self._handle_enemy_move
            )
    
    def can_move_enemies(self, current_time: float) -> bool:
        """
        적 이동 가능 여부 확인
        
        Args:
            current_time: 현재 시간
            
        Returns:
            이동 가능 여부
        """
        # 호스트만 적을 이동시킬 수 있음
        if not self.is_host:
            return False
        
        # 0.65초 간격 체크
        if current_time - self.last_move_time < self.move_interval:
            return False
        
        return True
    
    def update_move_time(self, current_time: float):
        """
        이동 시간 업데이트
        
        Args:
            current_time: 현재 시간
        """
        self.last_move_time = current_time
    
    def _collect_enemy_positions(
        self,
        enemies: List[Any],
        current_time: float
    ) -> Dict[str, Dict[str, Any]]:
        """브로드캐스트용 적 위치 데이터 수집"""
        enemy_positions: Dict[str, Dict[str, Any]] = {}

        for enemy in enemies:
            try:
                if not enemy:
                    continue

                enemy_id = self._get_enemy_id(enemy)
                if not enemy_id:
                    continue

                if not hasattr(enemy, 'x') or not hasattr(enemy, 'y'):
                    continue

                try:
                    x = int(enemy.x)
                    y = int(enemy.y)
                except (ValueError, TypeError, AttributeError):
                    self.logger.warning(f"적 {enemy_id}의 위치를 읽을 수 없음")
                    continue

                # spawn 좌표도 포함 (클라이언트에서 안정적 ID 생성용)
                spawn_x = getattr(enemy, 'spawn_x', None)
                spawn_y = getattr(enemy, 'spawn_y', None)
                enemy_type = getattr(enemy, 'enemy_id', None)

                pos_data = {
                    "x": x,
                    "y": y,
                    "timestamp": current_time
                }
                if spawn_x is not None:
                    pos_data["spawn_x"] = int(spawn_x)
                if spawn_y is not None:
                    pos_data["spawn_y"] = int(spawn_y)
                if enemy_type:
                    pos_data["enemy_type"] = str(enemy_type)

                enemy_positions[enemy_id] = pos_data
            except Exception as e:
                self.logger.error(f"적 위치 수집 실패: {e}", exc_info=True)
                continue

        return enemy_positions

    async def sync_enemy_positions(
        self,
        enemies: List[Any],
        check_interval: bool = True,
        current_time: Optional[float] = None
    ):
        """
        적 위치 동기화 (호스트 -> 모든 클라이언트)
        
        Args:
            enemies: 적 리스트
            check_interval: 이동 간격 체크 여부
            current_time: 외부에서 전달된 현재 시간 (없으면 time.time 사용)
        """
        try:
            if not self.is_host or not self.network_manager:
                return
            
            if not isinstance(enemies, list):
                self.logger.warning(f"잘못된 적 리스트 타입: {type(enemies)}")
                return
            
            if current_time is None:
                current_time = time.time()
            
            # 이동 가능 여부 확인
            if check_interval and not self.can_move_enemies(current_time):
                return
            
            enemy_positions = self._collect_enemy_positions(enemies, current_time)
            if not enemy_positions:
                return
            
            # 적 이동 메시지 전송
            try:
                move_message = MessageBuilder.enemy_move(enemy_positions)
                await self.network_manager.broadcast(move_message)
                
                # 이동 시간 업데이트
                self.update_move_time(current_time)
                
                self.logger.debug(f"적 위치 동기화 브로드캐스트: {len(enemy_positions)}마리")
            except Exception as e:
                self.logger.error(f"적 위치 동기화 브로드캐스트 실패: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"적 위치 동기화 실패: {e}", exc_info=True)

    def sync_enemy_positions_sync(
        self,
        enemies: List[Any],
        check_interval: bool = True,
        current_time: Optional[float] = None
    ):
        """
        동기 컨텍스트에서 적 위치 동기화

        Args:
            enemies: 적 리스트
            check_interval: 이동 간격 체크 여부
            current_time: 외부에서 전달된 현재 시간 (없으면 time.time 사용)
        """
        try:
            if not self.is_host or not self.network_manager:
                return

            if not isinstance(enemies, list):
                self.logger.warning(f"잘못된 적 리스트 타입: {type(enemies)}")
                return

            if current_time is None:
                current_time = time.time()

            if check_interval and not self.can_move_enemies(current_time):
                return

            enemy_positions = self._collect_enemy_positions(enemies, current_time)
            if not enemy_positions:
                return

            move_message = MessageBuilder.enemy_move(enemy_positions)
            self.network_manager.broadcast_sync(move_message)
            self.update_move_time(current_time)
            self.logger.debug(f"적 위치 동기화 브로드캐스트: {len(enemy_positions)}마리")
        except Exception as e:
            self.logger.error(f"적 위치 동기화 실패(동기): {e}", exc_info=True)
    
    async def _handle_enemy_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        적 이동 메시지 처리 (클라이언트)
        
        Args:
            message: 적 이동 메시지
            sender_id: 발신자 ID (호스트)
        """
        if self.is_host:
            return
        
        enemy_positions = message.data.get("enemies", {})
        
        # 캐시 업데이트 (머지 방식: 기존 위치 유지하면서 새 데이터 갱신)
        updated_positions = {}
        enemy_spawn_data = {}  # {enemy_id: {spawn_x, spawn_y, enemy_type}}
        for enemy_id, pos_data in enemy_positions.items():
            x = pos_data.get("x", 0)
            y = pos_data.get("y", 0)
            updated_positions[enemy_id] = (x, y)
            # spawn 좌표 메타데이터 저장
            if "spawn_x" in pos_data or "spawn_y" in pos_data:
                enemy_spawn_data[enemy_id] = {
                    "spawn_x": pos_data.get("spawn_x"),
                    "spawn_y": pos_data.get("spawn_y"),
                    "enemy_type": pos_data.get("enemy_type")
                }

        # 머지: 새로 받은 위치로 갱신하되, 수신되지 않은 기존 캐시는 유지
        self.enemy_positions.update(updated_positions)

        # 실제 exploration.enemies 위치 업데이트
        if hasattr(self, 'exploration') and self.exploration:
            if hasattr(self.exploration, 'enemies'):
                updated_count = 0
                matched_msg_ids = set()

                for enemy in self.exploration.enemies:
                    # 수신된 spawn 좌표로 로컬 적 객체에 spawn_x/spawn_y 설정
                    # (클라이언트에서 spawn 좌표가 없는 경우 호스트 데이터로 보완)
                    enemy_id = self._get_enemy_id(enemy)

                    # 1차: ID로 직접 매칭
                    if enemy_id in self.enemy_positions:
                        new_x, new_y = self.enemy_positions[enemy_id]
                        old_x, old_y = enemy.x, enemy.y
                        enemy.x = new_x
                        enemy.y = new_y
                        matched_msg_ids.add(enemy_id)
                        updated_count += 1
                        if old_x != new_x or old_y != new_y:
                            self.logger.debug(f"적 {enemy_id} 위치 업데이트: ({old_x}, {old_y}) -> ({new_x}, {new_y})")
                        continue

                    # 2차: spawn 좌표 기반 매칭 (메시지의 spawn 좌표 vs 적의 spawn/현재 좌표)
                    matched = False
                    for msg_enemy_id, spawn_info in enemy_spawn_data.items():
                        if msg_enemy_id in matched_msg_ids:
                            continue
                        msg_spawn_x = spawn_info.get("spawn_x")
                        msg_spawn_y = spawn_info.get("spawn_y")
                        if msg_spawn_x is None or msg_spawn_y is None:
                            continue

                        local_spawn_x = getattr(enemy, 'spawn_x', None)
                        local_spawn_y = getattr(enemy, 'spawn_y', None)

                        if local_spawn_x == msg_spawn_x and local_spawn_y == msg_spawn_y:
                            # spawn 좌표 일치 - 적 객체에 spawn 정보 설정 및 ID 캐시 갱신
                            if not hasattr(enemy, 'spawn_x') or enemy.spawn_x is None:
                                enemy.spawn_x = msg_spawn_x
                                enemy.spawn_y = msg_spawn_y
                            if spawn_info.get("enemy_type") and not getattr(enemy, 'enemy_id', None):
                                enemy.enemy_id = spawn_info["enemy_type"]
                            # 캐시된 ID 무효화하여 다음 호출 시 안정 ID 재생성
                            try:
                                if hasattr(enemy, '_multiplayer_sync_id'):
                                    delattr(enemy, '_multiplayer_sync_id')
                            except Exception:
                                pass

                            new_x, new_y = self.enemy_positions[msg_enemy_id]
                            enemy.x = new_x
                            enemy.y = new_y
                            matched_msg_ids.add(msg_enemy_id)
                            updated_count += 1
                            self.logger.debug(f"적 spawn 기반 매칭: {msg_enemy_id} -> ({new_x}, {new_y})")
                            matched = True
                            break

                    if matched:
                        continue

                    # 3차: 메시지의 spawn 좌표와 적의 현재 위치가 같은 경우 (최초 동기화)
                    for msg_enemy_id, spawn_info in enemy_spawn_data.items():
                        if msg_enemy_id in matched_msg_ids:
                            continue
                        msg_spawn_x = spawn_info.get("spawn_x")
                        msg_spawn_y = spawn_info.get("spawn_y")
                        if msg_spawn_x is None or msg_spawn_y is None:
                            continue

                        if int(enemy.x) == msg_spawn_x and int(enemy.y) == msg_spawn_y:
                            # 현재 위치가 호스트의 spawn 좌표와 같으면 매칭
                            enemy.spawn_x = msg_spawn_x
                            enemy.spawn_y = msg_spawn_y
                            if spawn_info.get("enemy_type"):
                                enemy.enemy_id = spawn_info["enemy_type"]
                            try:
                                if hasattr(enemy, '_multiplayer_sync_id'):
                                    delattr(enemy, '_multiplayer_sync_id')
                            except Exception:
                                pass

                            new_x, new_y = self.enemy_positions[msg_enemy_id]
                            enemy.x = new_x
                            enemy.y = new_y
                            matched_msg_ids.add(msg_enemy_id)
                            updated_count += 1
                            self.logger.debug(f"적 초기위치 매칭: {msg_enemy_id} -> ({new_x}, {new_y})")
                            break
                
                # 4차 fallback: 매칭 안 된 적과 메시지를 순서대로 강제 매칭
                if updated_count < len(self.exploration.enemies):
                    unmatched_msg_ids = [mid for mid in updated_positions if mid not in matched_msg_ids]
                    unmatched_enemies = [e for e in self.exploration.enemies
                                         if self._get_enemy_id(e) not in matched_msg_ids]
                    for enemy, msg_id in zip(unmatched_enemies, unmatched_msg_ids):
                        new_x, new_y = updated_positions[msg_id]
                        enemy.x = new_x
                        enemy.y = new_y
                        # spawn 정보도 설정하여 다음 매칭 안정화
                        if msg_id in enemy_spawn_data:
                            si = enemy_spawn_data[msg_id]
                            if si.get("spawn_x") is not None:
                                enemy.spawn_x = si["spawn_x"]
                                enemy.spawn_y = si["spawn_y"]
                            if si.get("enemy_type"):
                                enemy.enemy_id = si["enemy_type"]
                        try:
                            if hasattr(enemy, '_multiplayer_sync_id'):
                                delattr(enemy, '_multiplayer_sync_id')
                        except Exception:
                            pass
                        matched_msg_ids.add(msg_id)
                        updated_count += 1
                        self.logger.debug(f"적 강제 매칭: {msg_id} -> ({new_x}, {new_y})")

                if updated_count == 0:
                    self.logger.warning(f"적 위치 동기화 실패: {len(self.exploration.enemies)}마리 중 0마리 업데이트됨")
                    self.logger.debug(f"수신한 적 ID: {list(updated_positions.keys())}")
                    self.logger.debug(f"로컬 적 ID: {[self._get_enemy_id(e) for e in self.exploration.enemies]}")
        
        self.logger.debug(f"적 위치 동기화 수신: {len(enemy_positions)}마리")
    
    def _get_enemy_id(self, enemy: Any) -> str:
        """
        적 ID 생성
        
        Args:
            enemy: 적 객체
            
        Returns:
            적 ID
        """
        cached_id = getattr(enemy, '_multiplayer_sync_id', None)
        if cached_id:
            return str(cached_id)

        # 멀티플레이에서는 "현재 좌표"를 ID에 쓰면 이동할 때마다 ID가 바뀌어 동기화가 깨집니다.
        # 가능한 경우 spawn 좌표 기반의 안정 ID를 우선 사용합니다.
        enemy_type = getattr(enemy, 'enemy_id', None)
        spawn_x = getattr(enemy, 'spawn_x', None)
        spawn_y = getattr(enemy, 'spawn_y', None)
        stable_id: Optional[str] = None

        if enemy_type and spawn_x is not None and spawn_y is not None:
            stable_id = f"{enemy_type}_{spawn_x}_{spawn_y}"
        elif spawn_x is not None and spawn_y is not None:
            stable_id = f"enemy_{spawn_x}_{spawn_y}"
        elif hasattr(enemy, 'id') and getattr(enemy, 'id'):
            # id가 이미 호스트 기준으로 동기화된 경우에만 사용됩니다.
            stable_id = str(getattr(enemy, 'id'))
        elif enemy_type:
            stable_id = str(enemy_type)
        elif hasattr(enemy, 'x') and hasattr(enemy, 'y'):
            # 마지막 fallback: 최초 좌표를 캐시해서 이후 이동 시에도 ID가 변하지 않도록 함
            stable_id = f"enemy_{int(enemy.x)}_{int(enemy.y)}"
        else:
            stable_id = f"enemy_unknown_{id(enemy)}"

        # _multiplayer_sync_id를 최초 호출 시 반드시 설정 (이후 이동해도 ID 유지)
        try:
            setattr(enemy, '_multiplayer_sync_id', stable_id)
        except Exception:
            pass

        return stable_id
    
    def get_enemy_position(self, enemy_id: str) -> Optional[Tuple[int, int]]:
        """
        적 위치 가져오기
        
        Args:
            enemy_id: 적 ID
            
        Returns:
            (x, y) 위치, 없으면 None
        """
        return self.enemy_positions.get(enemy_id)

