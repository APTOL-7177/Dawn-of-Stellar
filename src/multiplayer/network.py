"""
네트워크 관리자

P2P 멀티플레이를 위한 WebSocket 기반 네트워크 레이어
"""

import asyncio
import json
import time
import gzip
import socket
from typing import Dict, Callable, Optional, Set, Any, List, Tuple
from enum import Enum

import websockets
from websockets.server import ServerConnection
from websockets.client import ClientConnection

from src.multiplayer.protocol import NetworkMessage, MessageType, MessageBuilder
from src.multiplayer.config import MultiplayerConfig
from src.core.logger import get_logger


class ConnectionState(Enum):
    """연결 상태"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class NetworkManager:
    """네트워크 관리자 (호스트/클라이언트 공통)"""
    
    def __init__(self, is_host: bool = False, session: Optional[Any] = None):
        """
        네트워크 관리자 초기화
        
        Args:
            is_host: 호스트 여부
            session: 멀티플레이 세션 참조 (호스트일 때 세션 정보 전송용)
        """
        self.is_host = is_host
        self.player_id: Optional[str] = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.session: Optional[Any] = session  # 세션 참조
        
        # WebSocket 연결
        self.websocket: Optional[Any] = None
        self.server: Optional[Any] = None  # 호스트일 때만 사용
        
        # 클라이언트 연결 (호스트일 때만)
        self.clients: Dict[str, ServerConnection] = {}
        
        # 서버 이벤트 루프 참조 (동기 코드에서 브로드캐스트용)
        self._server_event_loop: Optional[Any] = None
        
        # 메시지 핸들러
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # 네트워크 통계
        self.ping_history: Dict[str, List[float]] = {}  # {player_id: [ping, ...]}
        self.last_ping_time: Dict[str, float] = {}  # {player_id: timestamp}
        self.ping_interval = 1.0  # 1초마다 핑 측정
        self._max_ping_history = 50  # 플레이어당 최대 핑 기록 수 (무한 성장 방지)
        
        # 압축 설정
        self.use_compression = MultiplayerConfig.message_compression
        self.compression_threshold = 1024  # 1KB 이상일 때만 압축
        
        # 세션 초기화 정보 (호스트가 클라이언트에게 전송할 정보)
        self.current_floor: Optional[int] = None
        self.current_dungeon: Optional[Any] = None
        self.current_exploration: Optional[Any] = None
        
        self.logger = get_logger("multiplayer.network")
        
        # 백그라운드 태스크
        self._ping_task: Optional[asyncio.Task] = None
        self._running = False
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """메시지 핸들러 등록"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    def unregister_handler(self, message_type: MessageType, handler: Callable):
        """메시지 핸들러 제거"""
        if message_type in self.message_handlers:
            if handler in self.message_handlers[message_type]:
                self.message_handlers[message_type].remove(handler)
    
    async def _handle_message(self, message: NetworkMessage, sender_id: Optional[str] = None):
        """메시지 처리"""
        message_type = message.type
        
        # FLOOR_READY 메시지 직접 처리 (세션 업데이트 및 브로드캐스트)
        if message_type == MessageType.FLOOR_READY:
            if self.session:
                player_id = message.player_id
                ready = message.data.get("ready", False)
                ready_players = message.data.get("ready_players", [])
                
                # 호스트인 경우: 업데이트된 상태를 모든 클라이언트에게 브로드캐스트
                if self.is_host:
                    # sender-bound 인가: WS 연결에서 파생된 sender_id가 진짜 원천.
                    authorized_player_id = message.resolve_sender_player_id(sender_id)
                    if not authorized_player_id:
                        self.logger.warning(
                            f"FLOOR_READY 스푸핑 의심 거부: sender={sender_id}, "
                            f"payload player_id={message.player_id}"
                        )
                        return
                    self.session.set_floor_ready(authorized_player_id, ready)
                    # MessageBuilder는 모듈 상단에서 임포트됨 (지역 import 금지 — UnboundLocalError 유발)
                    updated_msg = MessageBuilder.floor_ready(
                        player_id=authorized_player_id,
                        ready=ready,
                        ready_players=list(self.session.floor_ready_players),
                        total_players=len(self.session.players)
                    )
                    await self.broadcast(updated_msg, exclude=sender_id)
                    self.logger.debug(f"층 이동 준비 상태 업데이트 브로드캐스트: {len(self.session.floor_ready_players)}/{len(self.session.players)}")
                else:
                    self.session.replace_floor_ready(ready_players)
                    self.logger.debug(f"층 이동 준비 상태 동기화: {len(self.session.floor_ready_players)}/{message.data.get('total_players', 0)}")
        
        # FLOOR_CHANGE 메시지 직접 처리 (클라이언트에서 층 변경 트리거)
        if message_type == MessageType.FLOOR_CHANGE:
            if not self.is_host and self.session:
                direction = message.data.get("direction", "floor_down")
                from_town = message.data.get("from_town", False)
                
                # 세션에 층 변경 대기 플래그 설정 (WorldUI에서 확인)
                self.session.floor_change_pending = True
                self.session.floor_change_direction = direction
                self.session.floor_change_from_town = from_town
                
                self.logger.info(f"FLOOR_CHANGE 수신: direction={direction}, from_town={from_town}")
        
        # DUNGEON_DATA 메시지 직접 처리 (클라이언트에서 던전 업데이트)
        if message_type == MessageType.DUNGEON_DATA:
            if not self.is_host:
                # 새 던전 데이터 저장 (network_manager에 직접 저장 - client에서 접근)
                self.pending_dungeon_data = message.data.get("dungeon")
                self.pending_floor_number = message.data.get("floor_number", 1)
                self.pending_dungeon_seed = message.data.get("seed")
                self.dungeon_data_received = True
                
                self.logger.info(f"DUNGEON_DATA 수신: floor={self.pending_floor_number}")
        
        # COMBAT_JOIN 메시지 처리 (호스트만 — late join 정합 검증, t_7846bbe3 §5.4)
        if message_type == MessageType.COMBAT_JOIN:
            if self.is_host and self.session:
                session = self.session
                joiner_id = message.player_id or sender_id
                combat_id = message.data.get("combat_id")
                joiner_epoch = message.data.get("epoch", message.epoch)
                exploration = self.current_exploration
                handler = getattr(exploration, 'combat_join_handler', None) if exploration else None

                server_epoch = session.epoch if session else 0
                # 요청자 생존: 세션 플레이어의 파티에 생존 캐릭터가 있는지 확인
                requester_alive = True
                mp_player = session.players.get(joiner_id)
                if mp_player is not None:
                    party = getattr(mp_player, 'party', None) or []
                    if party:
                        requester_alive = any(getattr(c, 'is_alive', True) for c in party)

                if handler is None or not combat_id:
                    # 합류 처리 경로가 없으면 로그 후 무시 (grace 부재 상태에서 조용히 통과시키지 않음)
                    self.logger.warning(
                        f"late COMBAT_JOIN 무시 (검증 핸들러 부재): player={joiner_id}, combat={combat_id}"
                    )
                else:
                    allowed, reason = handler.validate_late_join(
                        joiner_id,
                        combat_id,
                        epoch=joiner_epoch,
                        server_epoch=server_epoch,
                        requester_alive=requester_alive,
                    )
                    if allowed:
                        # 합류 승인: 실제 합류 처리 (자동 합류 경로와 동일 처리)
                        player_obj = mp_player
                        if exploration and player_obj is not None and hasattr(exploration, '_add_player_to_combat'):
                            try:
                                import asyncio as _asyncio
                                _asyncio.get_running_loop()
                                _asyncio.ensure_future(exploration._add_player_to_combat(joiner_id, player_obj, combat_id))
                            except RuntimeError:
                                # 실행 루프 밖(동기 컨텍스트)이면 합류 표시만 하고 로그 남김
                                handler.mark_player_joined(combat_id, joiner_id)
                                self.logger.info(f"late join 합류 표시 (동기 컨텍스트): {joiner_id} → {combat_id}")
                    else:
                        # 거부: 로그 남기고 무시 (합류 처리 안 함)
                        self.logger.warning(
                            f"late COMBAT_JOIN 거부: player={joiner_id}, combat={combat_id}, reason={reason}"
                        )

        # REQUEST_COMBAT_START 메시지 처리 (호스트만)
        if message_type == MessageType.REQUEST_COMBAT_START:
            if self.is_host and self.session:
                position_data = message.data.get("position", {})
                x = position_data.get("x")
                y = position_data.get("y")
                enemy_id = message.data.get("enemy_id")
                
                if x is not None and y is not None:
                    # 이미 해당 위치 근처에서 전투가 진행 중이면 기존 전투에 합류
                    if self.current_exploration and hasattr(self.current_exploration, 'active_combat_id') and self.current_exploration.active_combat_id:
                        active_pos = getattr(self.current_exploration, 'active_combat_position', None)
                        if active_pos:
                            dist = abs(x - active_pos[0]) + abs(y - active_pos[1])
                            if dist <= 5:  # 5타일 이내면 같은 전투로 간주
                                self.logger.info(f"전투 요청 ({x},{y}): 이미 진행 중인 전투 {self.current_exploration.active_combat_id}에 합류 처리")
                                # 이미 전투 중이므로 추가 브로드캐스트 불필요 (자동 합류 시스템이 처리)
                                return

                    # 전투 시작 브로드캐스트
                    # MessageBuilder는 모듈 상단에서 임포트됨 (지역 import 금지 — UnboundLocalError 유발)

                    # 현재 탐험 시스템에서 적 정보 가져오기
                    enemies = []
                    if self.current_exploration:
                        # 해당 위치의 적 찾기
                        target_enemy = self.current_exploration.get_enemy_at(x, y)
                        if target_enemy:
                            # _trigger_combat_with_enemy 로직 재사용하여 참여할 적 결정
                            # (여기서는 실제 trigger는 하지 않고 참여자만 계산)
                            combat_enemies = [target_enemy]
                            combat_range = MultiplayerConfig.participation_radius_enemy
                            for other in self.current_exploration.enemies:
                                if other == target_enemy: continue
                                dist = abs(other.x - target_enemy.x) + abs(other.y - target_enemy.y)
                                if dist <= combat_range:
                                    combat_enemies.append(other)
                            
                            # 최대 4마리 제한 로직 등은 생략하고 일단 보냄 (클라이언트가 동기화)
                            enemies = combat_enemies
                    
                    # 참여자 (플레이어들)
                    participants = []
                    if self.current_exploration:
                        participants = self.current_exploration._get_nearby_participants((x, y))
                    
                    # 참여 플레이어 ID 수집 (세션의 모든 플레이어)
                    all_player_ids = sorted(self.session.players.keys()) if self.session else []

                    # 참여 플레이어별 파티 정보 수집
                    all_parties = None
                    if self.current_exploration and hasattr(self.current_exploration, '_collect_all_parties'):
                        all_parties = self.current_exploration._collect_all_parties((x, y))
                        self.logger.info(f"합류 파티 구성 완료: {len(all_parties) if all_parties else 0}명 플레이어")
                    else:
                        # current_exploration이 None이거나 메서드가 없는 경우: 세션 플레이어에서 직접 수집
                        self.logger.warning(
                            f"current_exploration={'None' if not self.current_exploration else 'no _collect_all_parties'} "
                            f"→ session.players에서 파티 직접 수집 (폴백)"
                        )
                        if self.session and self.session.players:
                            # MessageBuilder는 모듈 상단에서 임포트됨 (지역 import 금지 — UnboundLocalError 유발)
                            all_parties = {}
                            for pid, mp_player in self.session.players.items():
                                party = getattr(mp_player, 'party', None) or []
                                serialized = []
                                for character in party:
                                    if character and getattr(character, 'is_alive', True):
                                        try:
                                            character.owner_player_id = pid
                                        except Exception:
                                            pass
                                        try:
                                            serialized.append(
                                                MessageBuilder.serialize_character_for_combat(character)
                                            )
                                        except Exception as e:
                                            self.logger.error(f"캐릭터 직렬화 실패 ({pid}): {e}")
                                if serialized:
                                    all_parties[pid] = serialized
                            self.logger.info(f"합류 파티 구성 완료 (폴백): {len(all_parties)}명 플레이어")

                    # 전투 시작 메시지 브로드캐스트
                    start_msg = MessageBuilder.combat_start(
                        participants=all_player_ids,
                        enemies=enemies,
                        position=(x, y),
                        all_parties=all_parties
                    )
                    start_msg.data["participant_player_ids"] = all_player_ids
                    await self.broadcast(start_msg)
                    
                    # 호스트 자신도 전투 시작 처리 (이벤트 버스 등 활용)
                    # 실제로는 exploration_multiplayer.py에서 COMBAT_START 핸들러가 처리함
                    self.logger.info(f"전투 시작 요청 승인: ({x}, {y})")
        
        # MOVEMENT_REJECTED 메시지 처리 (클라이언트만)
        if message_type == MessageType.MOVEMENT_REJECTED:
            if not self.is_host and self.current_exploration:
                reason = message.data.get("reason", "unknown")
                correct_x = message.data.get("x")
                correct_y = message.data.get("y")
                
                if correct_x is not None and correct_y is not None:
                    self.logger.warning(f"이동 거절됨 ({reason}): ({correct_x}, {correct_y})로 롤백")
                    # 롤백 함수 호출
                    if hasattr(self.current_exploration, "rollback_player_position"):
                        self.current_exploration.rollback_player_position(correct_x, correct_y)

        # REQUEST_SNAPSHOT 메시지 처리 (호스트만 — 통합 스냅샷 회신, t_7846bbe3 §5.3 / t_ceed55de)
        if message_type == MessageType.REQUEST_SNAPSHOT:
            if self.is_host and self.session:
                requester_id = message.resolve_sender_player_id(sender_id) or message.player_id
                session = self.session
                snapshot = {
                    "session": session.serialize(),
                    "players": {
                        pid: {
                            "player_id": pid,
                            "player_name": getattr(p, "player_name", pid),
                            "x": getattr(p, "x", 0),
                            "y": getattr(p, "y", 0),
                            "is_host": getattr(p, "is_host", False),
                        }
                        for pid, p in session.players.items()
                    },
                    "positions": {
                        pid: {"x": getattr(p, "x", 0), "y": getattr(p, "y", 0)}
                        for pid, p in session.players.items()
                    },
                    "combat": None,
                }
                reply = MessageBuilder.full_snapshot(
                    epoch=session.epoch,
                    revision=session.state_revision,
                    snapshot=snapshot,
                )
                ws = self.clients.get(requester_id) if requester_id else None
                if ws is not None:
                    try:
                        await self._send_raw(reply.to_json().encode("utf-8"), ws)
                        self.logger.info(
                            f"FULL_SNAPSHOT 응답 전송: requester={requester_id}, "
                            f"epoch={session.epoch}, revision={session.state_revision}"
                        )
                    except Exception as e:
                        self.logger.warning(f"FULL_SNAPSHOT 응답 실패 ({requester_id}): {e}")
                else:
                    self.logger.warning(f"REQUEST_SNAPSHOT 무시 (요청자 소켓 없음): {requester_id}")

        # 세션 상태 메시지 직접 처리 (클라이언트 — UI 플래그/알림 기록, t_ceed55de)
        if message_type == MessageType.FULL_SNAPSHOT and not self.is_host:
            await self._apply_full_snapshot(message)
        if message_type == MessageType.CHARACTER_REVIVAL and not self.is_host:
            await self._apply_character_revival(message, sender_id)
        if message_type == MessageType.SESSION_STALE and not self.is_host:
            self.session_stale = True
            self._record_ui_notice(
                "session_stale",
                server_epoch=message.data.get("server_epoch"),
                client_epoch=message.data.get("client_epoch"),
            )
        if message_type == MessageType.SESSION_ENDED and not self.is_host:
            # 플래그/알림은 _receive_loop에서 이미 기록되지만, 직접 호출 경로에서도 보장
            if not self.session_ended:
                self.session_ended = True
                self._record_ui_notice("session_ended", reason=message.data.get("reason", "unknown"))

        # 핸들러 호출
        if message_type in self.message_handlers:
            for handler in self.message_handlers[message_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message, sender_id)
                    else:
                        handler(message, sender_id)
                except Exception as e:
                    self.logger.error(f"메시지 핸들러 오류 ({message_type.value}): {e}", exc_info=True)
    
    async def _send_raw(self, data: bytes, target: Optional[Any] = None):
        """원시 데이터 전송"""
        try:
            if target:
                await target.send(data)
            elif self.websocket:
                await self.websocket.send(data)
            else:
                self.logger.warning("전송할 연결이 없습니다")
        except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError) as e:
            # 연결이 이미 끊어진 경우는 예상되는 상황이므로 경고만 출력
            self.logger.debug(f"연결이 끊어진 상태에서 메시지 전송 시도 (무시): {e}")
        except Exception as e:
            self.logger.error(f"데이터 전송 오류: {e}", exc_info=True)
            raise
    
    async def send(self, message: NetworkMessage, target_id: Optional[str] = None):
        """
        메시지 전송
        
        Args:
            message: 전송할 메시지
            target_id: 특정 플레이어에게만 전송 (None이면 호스트에게 전송 또는 브로드캐스트)
        """
        try:
            # 메시지 직렬화
            if self.use_compression and len(message.to_json()) > self.compression_threshold:
                # 압축 전송
                compressed = message.compress()
                data = b"COMPRESSED:" + compressed
            else:
                # 일반 전송
                data = message.to_json().encode('utf-8')
            
            # 전송
            if self.is_host:
                # 호스트: 브로드캐스트 또는 특정 클라이언트에게 전송
                if target_id:
                    if target_id in self.clients:
                        await self._send_raw(data, self.clients[target_id])
                else:
                    # 브로드캐스트 (연결이 끊어진 클라이언트는 자동으로 예외 처리됨)
                    if self.clients:
                        # gather의 return_exceptions=True로 각 전송 실패가 전체를 중단시키지 않도록 함
                        results = await asyncio.gather(*[
                            self._send_raw(data, client) for client in self.clients.values()
                        ], return_exceptions=True)
                        # 예외가 발생한 결과는 로그로만 기록 (이미 _send_raw에서 처리됨)
            else:
                # 클라이언트: 호스트에게 전송
                if self.websocket:
                    await self._send_raw(data, self.websocket)
        
        except Exception as e:
            self.logger.error(f"메시지 전송 오류: {e}", exc_info=True)
    
    async def broadcast(self, message: NetworkMessage, exclude: Optional[str] = None):
        """
        브로드캐스트 (쌍방향 동기화 - 모든 플레이어 사용 가능)
        
        Args:
            message: 브로드캐스트할 메시지
            exclude: 제외할 플레이어 ID
        """
        # 클라이언트는 호스트에게만 전송 (호스트가 모든 클라이언트에게 브로드캐스트)
        if not self.is_host:
            # 클라이언트는 호스트에게만 전송
            await self.send(message)
            return
        
        if exclude:
            targets = {pid: client for pid, client in self.clients.items() if pid != exclude}
        else:
            targets = self.clients
        
        if targets:
            data = message.to_json().encode('utf-8')
            if self.use_compression and len(data) > self.compression_threshold:
                data = b"COMPRESSED:" + message.compress()
            
            results = await asyncio.gather(*[
                self._send_raw(data, client) for client in targets.values()
            ], return_exceptions=True)
            # 전송 실패 클라이언트 감지 및 로깅
            for (pid, _client), result in zip(targets.items(), results):
                if isinstance(result, Exception):
                    self.logger.warning(f"브로드캐스트 전송 실패 (player: {pid}): {result}")
    
    def broadcast_sync(self, message: NetworkMessage, exclude: Optional[str] = None):
        """
        동기 컨텍스트에서 브로드캐스트 호출
        
        이벤트 루프가 실행 중이면 run_coroutine_threadsafe를 사용하고,
        그렇지 않으면 새 이벤트 루프를 생성하여 실행합니다.
        
        Args:
            message: 브로드캐스트할 메시지
            exclude: 제외할 플레이어 ID
        """
        try:
            # 서버 이벤트 루프 확인 (호스트)
            event_loop = getattr(self, '_server_event_loop', None)
            
            # 클라이언트 이벤트 루프 확인
            if event_loop is None:
                event_loop = getattr(self, '_client_event_loop', None)
            
            if event_loop and event_loop.is_running():
                # 실행 중인 이벤트 루프가 있으면 run_coroutine_threadsafe 사용
                future = asyncio.run_coroutine_threadsafe(
                    self.broadcast(message, exclude),
                    event_loop
                )
                # 결과를 기다리지 않고 반환 (논블로킹)
                return
            
            # 현재 스레드에서 이벤트 루프 확인
            try:
                loop = asyncio.get_running_loop()
                # 이미 실행 중인 루프가 있으면 태스크로 추가
                asyncio.create_task(self.broadcast(message, exclude))
            except RuntimeError:
                # 실행 중인 루프가 없으면 새로 생성하여 실행
                asyncio.run(self.broadcast(message, exclude))
                
        except Exception as e:
            self.logger.error(f"동기 브로드캐스트 실패: {e}", exc_info=True)

    def send_sync(self, message: NetworkMessage, target_id: Optional[str] = None):
        """
        동기 컨텍스트에서 send 호출

        broadcast_sync와 동일한 폴백 패턴을 사용합니다.

        Args:
            message: 전송할 메시지
            target_id: 특정 플레이어에게만 전송
        """
        try:
            event_loop = getattr(self, '_server_event_loop', None)
            if event_loop is None:
                event_loop = getattr(self, '_client_event_loop', None)

            if event_loop and event_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.send(message, target_id),
                    event_loop
                )
                return

            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self.send(message, target_id))
            except RuntimeError:
                asyncio.run(self.send(message, target_id))

        except Exception as e:
            self.logger.error(f"동기 send 실패: {e}", exc_info=True)

    async def _receive_message(self, data: bytes, sender_id: Optional[str] = None) -> Optional[NetworkMessage]:
        """메시지 수신 및 파싱"""
        try:
            # 압축 확인
            if data.startswith(b"COMPRESSED:"):
                compressed = data[len(b"COMPRESSED:"):]
                message = NetworkMessage.decompress(compressed)
            else:
                json_str = data.decode('utf-8')
                message = NetworkMessage.from_json(json_str)
            
            return message
        except Exception as e:
            self.logger.error(f"메시지 파싱 오류: {e}", exc_info=True)
            return None
    
    async def _start_ping_loop(self):
        """핑 측정 루프 (백그라운드 태스크)"""
        while self._running:
            try:
                if self.is_host and self.clients:
                    # 호스트: 모든 클라이언트에게 핑 요청
                    # 딕셔너리 크기 변경 방지를 위해 리스트로 복사
                    client_ids = list(self.clients.keys())
                    for client_id in client_ids:
                        # 클라이언트가 아직 연결되어 있는지 확인
                        if client_id not in self.clients:
                            continue
                        ping_msg = MessageBuilder.ping_request()
                        ping_msg.player_id = self.player_id
                        ping_msg.data["target_id"] = client_id
                        await self.send(ping_msg, client_id)
                        self.last_ping_time[client_id] = time.time()
                
                elif not self.is_host and self.connection_state == ConnectionState.CONNECTED:
                    # 클라이언트: 호스트에게 핑 요청
                    ping_msg = MessageBuilder.ping_request()
                    ping_msg.player_id = self.player_id
                    await self.send(ping_msg)
                    self.last_ping_time["host"] = time.time()
                
                await asyncio.sleep(self.ping_interval)
            
            except Exception as e:
                self.logger.error(f"핑 측정 루프 오류: {e}", exc_info=True)
                await asyncio.sleep(self.ping_interval)
    
    def record_ping(self, player_id: str, ping_ms: float) -> None:
        """핑 값을 기록하고 최대 크기(_max_ping_history)를 초과하면 오래된 항목 제거"""
        if player_id not in self.ping_history:
            self.ping_history[player_id] = []
        history = self.ping_history[player_id]
        history.append(ping_ms)
        if len(history) > self._max_ping_history:
            # 최근 _max_ping_history 개만 유지
            self.ping_history[player_id] = history[-self._max_ping_history:]

    def calculate_average_ping(self, player_id: str) -> float:
        """평균 핑 계산"""
        if player_id not in self.ping_history or not self.ping_history[player_id]:
            return 0.0

        # 최근 10개의 평균
        recent_pings = self.ping_history[player_id][-10:]
        return sum(recent_pings) / len(recent_pings)
    
    def get_ping_status(self, player_id: str) -> str:
        """핑 상태 반환 (색상 표시용)"""
        ping = self.calculate_average_ping(player_id)
        
        if ping < 100:
            return "green"  # 좋음
        elif ping < 300:
            return "yellow"  # 보통
        else:
            return "red"  # 나쁨
    
    async def start_ping_loop(self):
        """핑 측정 루프 시작"""
        if self._ping_task is None or self._ping_task.done():
            self._running = True
            self._ping_task = asyncio.create_task(self._start_ping_loop())
    
    async def stop_ping_loop(self):
        """핑 측정 루프 중지"""
        self._running = False
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass


class HostNetworkManager(NetworkManager):
    """호스트 네트워크 관리자"""
    
    def __init__(self, port: int = 5000, session: Optional[Any] = None):
        """
        호스트 네트워크 관리자 초기화

        Args:
            port: 서버 포트
            session: 멀티플레이 세션 참조
        """
        super().__init__(is_host=True, session=session)
        self.port = port
        self.server: Optional[Any] = None
        self._local_ip: Optional[str] = None

        # UPnP 상태
        self.upnp_success: bool = False
        self.external_ip: Optional[str] = None
        self._upnp_mapped_port: Optional[int] = None

        # 세대 토큰 (t_7846bbe3 §5.2): player_id별 현재 연결 세대. 재접속 시 증가.
        self._client_generations: Dict[str, int] = {}

    def _register_client_socket(self, client_id: str, websocket) -> int:
        """클라이언트 소켓 등록 및 세대 토큰 발급. 현재 세대를 반환한다.

        동일 player_id의 기존 소켓이 있으면 즉시 닫는다(superseded, t_7846bbe3 §5.2).
        닫힌 구 handle_client는 세대 불일치로 finally 정리를 건너뛴다.
        """
        existing_ws = self.clients.get(client_id)
        if existing_ws is not None and existing_ws is not websocket:
            self._close_superseded(existing_ws)
            self.logger.info(f"동일 player_id 재접속: 구 연결 대체 (player={client_id})")
        self.clients[client_id] = websocket
        generation = self._client_generations.get(client_id, 0) + 1
        self._client_generations[client_id] = generation
        return generation

    def _close_superseded(self, websocket) -> None:
        """대체된 구 소켓을 닫는다 (동기 컨텍스트에서 fire-and-forget)."""
        try:
            asyncio.get_running_loop()
            asyncio.create_task(websocket.close(code=4000, reason="superseded"))
        except RuntimeError:
            try:
                asyncio.run(websocket.close(code=4000, reason="superseded"))
            except Exception:
                pass
        except Exception:
            pass

    async def _cleanup_client(self, client_id: str, generation: Optional[int] = None) -> bool:
        """클라이언트 연결 정리. 세대 토큰이 현재와 일치할 때만 실제 정리를 수행한다.

        HOST_MIGRATED는 발송하지 않는다 (P2P 토폴로지에서 진짜 migration 불가,
        t_7846bbe3 §5.1 정책). 호스트 상실 시 클라이언트는 SESSION_ENDED/소켓 종료로
        세션 종료를 인지한다.

        Returns:
            실제 정리가 수행되었으면 True, 세대 불일치로 건너뛰었으면 False
        """
        # 세대 검증: 구 세대의 finally는 정리를 건너뛴다 (유령 PLAYER_LEFT 방지)
        current_generation = self._client_generations.get(client_id)
        if generation is not None and current_generation is not None and generation != current_generation:
            self.logger.debug(f"정리 건너뜀 (세대 불일치: {generation} != {current_generation}): {client_id}")
            return False

        # 먼저 세션에서 플레이어 제거
        player_was_in_session = False
        if self.session and client_id in self.session.players:
            _, _new_host_id = self.session.remove_player(client_id)
            player_was_in_session = True
            self.logger.info(f"세션에서 플레이어 제거: {client_id}")
            # 참고: host migration은 비활성화 정책이므로 new_host_id는 무시한다

        # 클라이언트를 딕셔너리에서 제거
        was_in_clients = client_id in self.clients
        if was_in_clients:
            del self.clients[client_id]
        if client_id in self.ping_history:
            del self.ping_history[client_id]

        # 연결 종료 메시지 브로드캐스트 (PLAYER_LEFT만 — migration 없음)
        if player_was_in_session and self.clients:
            try:
                disconnect_msg = NetworkMessage(
                    type=MessageType.PLAYER_LEFT,
                    player_id=client_id
                )
                await self.broadcast(disconnect_msg)
            except Exception as e:
                self.logger.debug(f"연결 종료 메시지 브로드캐스트 실패 (무시 가능): {e}")

        self.logger.info(f"클라이언트 연결 종료: {client_id}")
        return True
    
    @staticmethod
    def find_available_port(start_port: int = 5000, max_attempts: int = 100) -> int:
        """
        사용 가능한 포트 찾기
        
        Args:
            start_port: 시작 포트
            max_attempts: 최대 시도 횟수
            
        Returns:
            사용 가능한 포트 번호
        """
        for port in range(start_port, start_port + max_attempts):
            try:
                # 포트가 사용 가능한지 확인
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("0.0.0.0", port))
                    return port
            except OSError:
                # 포트가 사용 중이면 다음 포트 시도
                continue
        
        # 사용 가능한 포트를 찾지 못한 경우
        raise RuntimeError(f"사용 가능한 포트를 찾을 수 없습니다 ({start_port}~{start_port + max_attempts - 1})")
    
    async def start_server(self, port: Optional[int] = None):
        """서버 시작 (사용 가능한 포트 자동 검색)

        Args:
            port: 사용할 포트 (None이면 기존 self.port 유지, t_ceed55de —
                  원 호스트가 로비를 다시 열 때 포트를 지정해 재개할 수 있다)
        """
        if port is not None:
            self.port = port
        # 현재 실행 중인 이벤트 루프 저장 (동기 코드에서 브로드캐스트용)
        try:
            self._server_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # 이벤트 루프가 실행 중이 아니면 None으로 유지
            self._server_event_loop = None
        
        original_port = self.port

        # 사용 가능한 포트 찾기
        try:
            self.port = HostNetworkManager.find_available_port(self.port)
            if self.port != original_port:
                self.logger.info(f"포트 {original_port}가 사용 중입니다. 포트 {self.port}로 자동 변경되었습니다.")
            else:
                self.logger.info(f"호스트 서버 시작: 포트 {self.port}")
        except RuntimeError as e:
            self.logger.error(f"서버 시작 실패: {e}")
            raise
        
        async def handle_client(websocket: ServerConnection):
            """클라이언트 연결 처리"""
            client_id = None
            try:
                self.logger.info(f"새로운 클라이언트 연결: {websocket.remote_address}")
                
                # 클라이언트로부터 연결 메시지 수신 대기
                try:
                    data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    self.logger.debug(f"클라이언트로부터 데이터 수신: {len(data)} bytes")
                    message = await self._receive_message(data)
                    
                    if message is None:
                        self.logger.warning(f"메시지 파싱 실패: 받은 데이터를 파싱할 수 없음 (데이터 길이: {len(data)})")
                        await websocket.close(code=1008, reason="Invalid message format")
                        return  # continue 대신 return 사용
                    
                    # 타입 확인 (디버깅용 로그 추가)
                    self.logger.debug(f"받은 메시지 타입: {message.type}, 타입 클래스: {type(message.type)}, 값: {message.type.value if hasattr(message.type, 'value') else message.type}")
                    self.logger.debug(f"예상 타입: {MessageType.CONNECT}, 타입 클래스: {type(MessageType.CONNECT)}, 값: {MessageType.CONNECT.value}")
                    
                    # 타입 비교 (값으로 비교)
                    received_type_value = message.type.value if hasattr(message.type, 'value') else str(message.type)
                    expected_type_value = MessageType.CONNECT.value
                    
                    self.logger.debug(f"메시지 타입 체크: 받은={received_type_value}, 예상={expected_type_value}, 타입 객체={message.type}, MessageType.CONNECT={MessageType.CONNECT}")
                    
                    # 타입이 MessageType.CONNECT인지 확인
                    if message.type != MessageType.CONNECT:
                        self.logger.warning(f"올바른 연결 메시지가 아닙니다: 받은 타입={received_type_value} ({message.type}), 예상={expected_type_value} ({MessageType.CONNECT})")
                        await websocket.close(code=1008, reason=f"Expected CONNECT message, got {received_type_value}")
                        return  # continue 대신 return 사용
                    
                    # CONNECT 메시지 처리
                    client_id = message.player_id
                    client_name = message.data.get("player_name", "플레이어")

                    # 프로토콜 버전 검증 (t_7846bbe3 §4.3): 미지원 버전은 거부
                    client_protocol_version = message.data.get("protocol_version")
                    if client_protocol_version is not None and client_protocol_version != MultiplayerConfig.protocol_version:
                        self.logger.warning(
                            f"프로토콜 버전 불일치 거부: client={client_protocol_version}, "
                            f"server={MultiplayerConfig.protocol_version}"
                        )
                        reject_msg = MessageBuilder.connection_rejected(client_id or "unknown", "version_mismatch")
                        await self._send_raw(reject_msg.to_json().encode('utf-8'), websocket)
                        await websocket.close(code=4001, reason="version_mismatch")
                        return

                    # 세션 epoch 검증 (t_7846bbe3 §4.1/§5.2): 구 세대 재접속은 거부
                    server_epoch = self.session.epoch if self.session else 0
                    client_epoch = message.data.get("epoch", message.epoch)
                    if client_epoch and server_epoch and client_epoch != server_epoch:
                        self.logger.warning(
                            f"세션 epoch 불일치 거부: client={client_epoch}, server={server_epoch}"
                        )
                        stale_msg = MessageBuilder.session_stale(server_epoch, client_epoch)
                        await self._send_raw(stale_msg.to_json().encode('utf-8'), websocket)
                        await websocket.close(code=4002, reason="session_stale")
                        return

                    # 동일 player_id 재접속: 구 소켓 대체 + 세대 토큰 발급
                    # (_register_client_socket이 supersede close를 수행, t_7846bbe3 §5.2)
                    generation = self._register_client_socket(client_id, websocket)
                    self.ping_history[client_id] = []
                    
                    self.logger.info(f"클라이언트 연결 승인: {client_id} ({client_name})")
                    
                    # 세션에 플레이어 추가 (호스트가 세션이 있고, 플레이어가 아직 없는 경우)
                    if self.session and client_id not in self.session.players:
                        from src.multiplayer.player import MultiplayerPlayer
                        new_player = MultiplayerPlayer(
                            player_id=client_id,
                            player_name=client_name,
                            x=0,
                            y=0,
                            party=[],
                            is_host=False
                        )
                        self.session.add_player(new_player)
                        self.logger.info(f"세션에 플레이어 추가: {client_name} ({client_id})")
                    
                    # 연결 승인 메시지 전송 (세션 epoch 태그 — 클라이언트가 학습하여 재접속 CONNECT에 태그, t_7846bbe3 §5.2)
                    session_id = self.session.session_id if self.session else "unknown"
                    accept_msg = MessageBuilder.connection_accepted(
                        client_id,
                        session_id,
                        epoch=server_epoch
                    )
                    await self._send_raw(accept_msg.to_json().encode('utf-8'), websocket)
                    
                    # 세션 시드는 항상 전송 (게임 시작 전이라도 세션 시드는 필요)
                    if self.session:
                        try:
                            seed_msg = MessageBuilder.session_seed(
                                self.session.session_seed,
                                self.session.session_id
                            )
                            await self._send_raw(seed_msg.to_json().encode('utf-8'), websocket)
                            self.logger.info(f"세션 시드 전송: {self.session.session_seed}")
                        except Exception as e:
                            self.logger.error(f"세션 시드 전송 실패: {e}", exc_info=True)
                    
                    # 던전 데이터 전송 (호스트가 게임을 시작한 경우)
                    if self.session and self.current_dungeon and self.current_floor is not None:
                        try:
                            # 던전 데이터 전송 (세션 시드는 이미 위에서 전송됨)
                            from src.persistence.save_system import serialize_dungeon
                            dungeon_seed = self.session.generate_dungeon_seed_for_floor(self.current_floor)
                            enemies = self.current_exploration.enemies if self.current_exploration else []
                            dungeon_data = serialize_dungeon(self.current_dungeon, enemies=enemies)
                            
                            # 호스트의 현재 위치를 시작 위치로 포함 (클라이언트가 호스트 근처에 스폰되도록)
                            if self.current_exploration and hasattr(self.current_exploration, 'player'):
                                dungeon_data["player_start_x"] = self.current_exploration.player.x
                                dungeon_data["player_start_y"] = self.current_exploration.player.y
                                self.logger.info(f"던전 데이터에 시작 위치 포함: ({dungeon_data['player_start_x']}, {dungeon_data['player_start_y']})")
                            
                            dungeon_msg = MessageBuilder.dungeon_data(
                                dungeon_data,
                                self.current_floor,
                                dungeon_seed
                            )
                            await self._send_raw(dungeon_msg.to_json().encode('utf-8'), websocket)
                            self.logger.info(f"던전 데이터 전송: {self.current_floor}층")
                            
                            # 3. 기존 플레이어 목록 및 위치 전송
                            players_data = []
                            for player_id, player in self.session.players.items():
                                players_data.append({
                                    "player_id": player.player_id,
                                    "player_name": player.player_name,
                                    "x": player.x,
                                    "y": player.y,
                                    "is_host": player.is_host,
                                    "party_count": len(player.party) if player.party else 0
                                })
                            
                            if players_data:
                                player_list_msg = MessageBuilder.player_list(players_data)
                                await self._send_raw(player_list_msg.to_json().encode('utf-8'), websocket)
                                self.logger.info(f"플레이어 목록 전송: {len(players_data)}명")
                            
                        except Exception as e:
                            self.logger.error(f"세션 정보 전송 실패: {e}", exc_info=True)
                    else:
                        # 게임 시작 전 연결이어도 플레이어 목록은 전송
                        if self.session:
                            try:
                                players_data = []
                                for player_id, player in self.session.players.items():
                                    players_data.append({
                                        "player_id": player.player_id,
                                        "player_name": player.player_name,
                                        "x": player.x,
                                        "y": player.y,
                                        "is_host": player.is_host,
                                        "party_count": len(player.party) if player.party else 0
                                    })
                                
                                if players_data:
                                    player_list_msg = MessageBuilder.player_list(players_data)
                                    await self._send_raw(player_list_msg.to_json().encode('utf-8'), websocket)
                                    self.logger.info(f"플레이어 목록 전송 (로비): {len(players_data)}명")
                            except Exception as e:
                                self.logger.error(f"플레이어 목록 전송 실패: {e}", exc_info=True)
                    
                    # 연결 이벤트 발생
                    await self._handle_message(message, client_id)
                    
                    # 모든 클라이언트에게 새 플레이어 추가 알림 (브로드캐스트)
                    if self.session:
                        player_joined_msg = MessageBuilder.player_list([
                            {
                                "player_id": session_player.player_id,
                                "player_name": session_player.player_name,
                                "x": session_player.x,
                                "y": session_player.y,
                                "is_host": session_player.is_host,
                                "party_count": len(session_player.party) if session_player.party else 0
                            } for session_player in self.session.players.values()
                        ])
                        await self.broadcast(player_joined_msg)
                        self.logger.info(f"플레이어 목록 브로드캐스트: {len(self.session.players)}명")
                    
                    # 메시지 수신 루프
                    while True:
                        try:
                            data = await websocket.recv()
                            message = await self._receive_message(data, client_id)
                            if message:
                                await self._handle_message(message, client_id)
                        except websockets.exceptions.ConnectionClosed:
                            self.logger.info(f"클라이언트 연결 종료: {client_id}")
                            break
                        except websockets.exceptions.ConnectionClosedOK:
                            self.logger.info(f"클라이언트 연결 정상 종료: {client_id}")
                            break
                        except websockets.exceptions.ConnectionClosedError as e:
                            self.logger.warning(f"클라이언트 연결 종료 오류: {client_id}, {e}")
                            break
                        except Exception as e:
                            self.logger.error(f"메시지 수신 오류: {e}", exc_info=True)
                            break
                
                except websockets.exceptions.ConnectionClosed:
                    self.logger.info("클라이언트가 연결 메시지 전에 연결을 종료했습니다")
                    return  # continue 대신 return 사용
                except websockets.exceptions.ConnectionClosedOK:
                    self.logger.info("클라이언트가 연결 메시지 전에 연결을 정상 종료했습니다")
                    return  # continue 대신 return 사용
                except websockets.exceptions.ConnectionClosedError as e:
                    self.logger.warning(f"클라이언트 연결 종료 오류: {e}")
                    return  # continue 대신 return 사용
                except asyncio.TimeoutError:
                    self.logger.warning("연결 타임아웃: 클라이언트로부터 연결 메시지를 받지 못했습니다")
                    try:
                        await websocket.close(code=1008, reason="Connection timeout")
                    except Exception:
                        pass
                    return  # continue 대신 return 사용
            
            except Exception as e:
                self.logger.error(f"클라이언트 처리 오류: {e}", exc_info=True)
            finally:
                # 세대 토큰 기반 정리 (t_7846bbe3 §5.2):
                # 재접속으로 자신의 소켓이 대체된 구 handle_client는 정리를 건너뛴다.
                if client_id:
                    my_generation = self._client_generations.get(client_id, -1) if client_id not in self.clients else None
                    # clients[client_id]가 내 소켓이 아니면 나는 이미 대체된 구 세대다
                    if client_id in self.clients and self.clients[client_id] is not websocket:
                        self.logger.debug(f"정리 건너뜀 (대체된 구 세대): {client_id}")
                        return
                    await self._cleanup_client(client_id, generation=my_generation)
        
        # 서버 시작 (포트 바인딩 실패 시 재시도)
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.server = await websockets.serve(handle_client, "0.0.0.0", self.port)
                self.connection_state = ConnectionState.CONNECTED
                break
            except OSError as e:
                if attempt < max_retries - 1:
                    # 포트가 갑자기 사용 불가능해진 경우 다른 포트 찾기
                    old_port = self.port
                    self.port = HostNetworkManager.find_available_port(self.port + 1)
                    self.logger.warning(f"포트 {old_port} 바인딩 실패. 포트 {self.port}로 재시도합니다.")
                else:
                    self.logger.error(f"서버 시작 실패: 포트 바인딩 실패 ({self.port})")
                    raise
        
        # 로컬 네트워크 IP 주소 가져오기
        local_ip = HostNetworkManager.get_local_ip()
        self._local_ip = local_ip

        # UPnP 자동 포트 포워딩 시도
        try:
            from src.multiplayer.upnp import try_port_mapping, is_available as upnp_available
            if upnp_available():
                self.logger.info("UPnP 자동 포트개방 시도 중...")
                success, ext_ip, ext_port = try_port_mapping(self.port)
                self.upnp_success = success
                if success:
                    self.external_ip = ext_ip
                    self._upnp_mapped_port = ext_port
                    self.logger.info(f"UPnP 포트개방 성공! 외부 접속: {ext_ip}:{ext_port}")
                else:
                    self.logger.info("UPnP 포트개방 실패 - 수동 포트포워딩 필요")
            else:
                self.logger.info("UPnP 라이브러리 미설치 - 자동 포트개방 건너뜀")
        except Exception as e:
            self.logger.warning(f"UPnP 처리 중 오류: {e}")

        # 서버 시작 로그 (실제 접속 가능한 IP 주소 표시)
        self.logger.info(f"호스트 서버 시작 완료: ws://0.0.0.0:{self.port}")
        self.logger.info(f"로컬 네트워크 접속 주소: ws://{local_ip}:{self.port}")
        if self.upnp_success and self.external_ip:
            self.logger.info(f"외부 접속 주소 (UPnP): {self.external_ip}:{self._upnp_mapped_port}")
        else:
            self.logger.info(f"같은 네트워크의 플레이어들은 이 주소로 연결하세요: {local_ip}:{self.port}")

        # 핑 루프 시작
        await self.start_ping_loop()
    
    @staticmethod
    def get_local_ip() -> str:
        """
        로컬 네트워크 IP 주소 가져오기
        
        Returns:
            로컬 네트워크 IP 주소 (예: 192.168.1.100)
        """
        try:
            # 외부 서버에 연결을 시도하여 실제 네트워크 인터페이스의 IP 가져오기
            # 이 방법이 가장 안정적으로 실제 네트워크 IP를 반환합니다
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 실제로 연결하지 않고, 로컬 네트워크 인터페이스만 확인
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            # 실패하면 hostname을 사용하여 시도
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                # 127.0.0.1이 아닌 경우만 반환
                if ip != "127.0.0.1":
                    return ip
            except Exception:
                pass
            
            # 모두 실패하면 localhost 반환
            return "127.0.0.1"
    
    @property
    def local_ip(self) -> str:
        """로컬 네트워크 IP 주소 (캐시된 값 또는 재계산)"""
        if self._local_ip:
            return self._local_ip
        self._local_ip = HostNetworkManager.get_local_ip()
        return self._local_ip
    
    async def stop_server(self):
        """서버 중지 (SESSION_ENDED 통보 후 종료, t_7846bbe3 §5.1)"""
        self.logger.info("호스트 서버 중지 중...")

        # SESSION_ENDED 통보 (정상 종료 — 클라이언트가 재연결 루프 없이 로비 복귀하도록)
        if self.clients:
            try:
                ended_msg = MessageBuilder.session_ended(reason="host_stopped")
                await self.broadcast(ended_msg)
                await asyncio.sleep(0.05)  # 전송 플러시 대기
            except Exception as e:
                self.logger.debug(f"SESSION_ENDED 브로드캐스트 실패 (무시 가능): {e}")

        # UPnP 포트 매핑 제거
        if self._upnp_mapped_port is not None:
            try:
                from src.multiplayer.upnp import remove_port_mapping
                remove_port_mapping(self._upnp_mapped_port)
                self._upnp_mapped_port = None
                self.upnp_success = False
            except Exception as e:
                self.logger.warning(f"UPnP 포트 매핑 제거 실패: {e}")

        # 핑 루프 중지
        await self.stop_ping_loop()

        # 모든 클라이언트 연결 종료
        if self.clients:
            await asyncio.gather(*[
                client.close() for client in self.clients.values()
            ], return_exceptions=True)
            self.clients.clear()

        # 서버 종료
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self.connection_state = ConnectionState.DISCONNECTED
        self.logger.info("호스트 서버 중지 완료")


class ClientNetworkManager(NetworkManager):
    """클라이언트 네트워크 관리자"""

    # host transport 표식: 클라이언트는 서버(호스트)와의 단일 WebSocket에서
    # 모든 메시지를 받는다. sender_id로 사용할 수 있는 실제 발신 플레이어 ID는
    # 페이로드에만 있으므로, "이 메시지는 신뢰된 host transport 경유"라는 사실을
    # payload actor(player_id)와 구분된 상수로 표현한다.
    HOST_TRANSPORT_SENDER = "__host_transport__"

    def __init__(self, host_address: str, port: int = 5000):
        """
        클라이언트 네트워크 관리자 초기화
        
        Args:
            host_address: 호스트 주소 (IP 또는 호스트명)
            port: 호스트 포트
        """
        super().__init__(is_host=False)
        self.host_address = host_address
        self.port = port
        self.ws_url = f"ws://{host_address}:{port}"
        
        # 재연결 설정
        self._player_name: Optional[str] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_delay = 2.0  # 초기 대기 시간 (초)
        self._reconnect_max_delay = 30.0  # 최대 대기 시간 (초)
        self._auto_reconnect = True  # 자동 재연결 활성화
        # 호스트 세션 epoch (t_7846bbe3 §4.1): CONNECTION_ACCEPTED에서 학습
        self.session_epoch: int = 0
        # 세션 종료/만료 플래그 (main.py UI에서 확인)
        self.session_ended: bool = False
        self.session_stale: bool = False
        # UI 연동 상태 (t_ceed55de): FULL_SNAPSHOT 저장, 부활 대기열, UI 알림 목록
        self.last_full_snapshot: Optional[Dict[str, Any]] = None
        self.pending_revivals: List[Tuple[str, str, int, int]] = []
        self.ui_notices: List[Dict[str, Any]] = []
        self.player_state_manager: Optional[Any] = None

    def _record_ui_notice(self, notice_type: str, **detail) -> None:
        """UI 폴링용 알림 기록 (SESSION_ENDED/SESSION_STALE/FULL_SNAPSHOT 등)."""
        notice = {"type": notice_type}
        notice.update(detail)
        self.ui_notices.append(notice)
        # 무한 증가 방지: 최근 20개만 유지
        if len(self.ui_notices) > 20:
            del self.ui_notices[:-20]

    async def reconnect(self):
        """명시적 재접속 (UI '다시 접속' 경로, t_ceed55de).

        자동 재연결(_attempt_reconnect)과 달리 플래그 초기화 후 즉시 1회 접속을 시도한다.
        SESSION_ENDED/SESSION_STALE로 포기한 상태에서도 원 호스트가 같은 세션(epoch)으로
        서버를 다시 열었다면 재합류가 가능하다.
        """
        if not self.player_id or not self._player_name:
            raise Exception("재접속에 필요한 플레이어 정보가 없습니다")
        # 상태 초기화: 세션 종료/만료 플래그는 재접속 성공 시 해제
        self._auto_reconnect = True
        self._reconnect_attempts = 0
        self.session_ended = False
        self.session_stale = False
        await self.connect(self.player_id, self._player_name)

    async def _apply_full_snapshot(self, message: NetworkMessage):
        """FULL_SNAPSHOT 적용 (t_7846bbe3 §5.3): 스냅샷 저장 + UI 알림."""
        self.last_full_snapshot = message.data.get("snapshot", {})
        self.session_epoch = message.epoch or self.session_epoch
        self._record_ui_notice(
            "full_snapshot",
            epoch=message.epoch,
            revision=message.revision,
        )
        self.logger.info(
            f"FULL_SNAPSHOT 수신: epoch={message.epoch}, revision={message.revision}"
        )

    async def _apply_character_revival(self, message: NetworkMessage, sender_id: Optional[str] = None):
        """CHARACTER_REVIVAL 수신 → player_state/마크 복원 (t_7846bbe3 §5.5, t_ceed55de).

        클라이언트 경로 전용: 호스트는 브로드캐스트 원천이므로 자기 자신 메시지에 대해
        복원을 수행하지 않는다.
        """
        if self.is_host:
            return
        player_id = message.player_id
        character_id = message.data.get("character_id")
        x = int(message.data.get("x", 0))
        y = int(message.data.get("y", 0))
        hp_pct = message.data.get("hp_pct")

        self.pending_revivals.append((player_id, character_id, x, y))
        if len(self.pending_revivals) > 50:
            del self.pending_revivals[:-50]

        session = self.session
        if session is None:
            session = getattr(self, "_last_session_ref", None)
        player = session.players.get(player_id) if session and hasattr(session, "players") else None
        if player is not None:
            target = None
            for character in getattr(player, "party", None) or []:
                cid = getattr(character, "id", None) or getattr(character, "name", None)
                if cid == character_id:
                    target = character
                    break
            if target is not None:
                max_hp = getattr(target, "max_hp", None)
                if max_hp is None and hasattr(target, "stat_manager"):
                    try:
                        max_hp = target.stat_manager.get_stat("hp")
                    except Exception:
                        max_hp = None
                target.is_alive = True
                if max_hp and hp_pct is not None:
                    target.current_hp = int(max_hp * float(hp_pct))
                elif not getattr(target, "current_hp", 0):
                    target.current_hp = int((max_hp or 100) * 0.5)
                if hasattr(target, "is_ghost"):
                    target.is_ghost = False
                # 이동 인가 기준점 재설정 (부활 위치 기준)
                if hasattr(player, "reset_movement_state"):
                    try:
                        player.reset_movement_state(x=x, y=y)
                    except (TypeError, ValueError):
                        pass
                # 마크 복원
                psm = getattr(self, "player_state_manager", None)
                if psm is not None:
                    try:
                        psm.update_player_state(player)
                    except Exception as e:
                        self.logger.debug(f"마크 복원 실패 (무시): {e}")
                self.logger.info(
                    f"CHARACTER_REVIVAL 적용: player={player_id}, char={character_id}, pos=({x}, {y})"
                )
        else:
            self.logger.debug(
                f"CHARACTER_REVIVAL 수신 (플레이어 미확인, 대기열에 보관): {player_id}/{character_id}"
            )
        self._record_ui_notice("character_revival", player_id=player_id, character_id=character_id, x=x, y=y)
    
    async def connect(self, player_id: str, player_name: str):
        """
        호스트에 연결
        
        Args:
            player_id: 플레이어 ID
            player_name: 플레이어 이름
        """
        self.player_id = player_id
        self._player_name = player_name  # 재연결용 저장
        self._reconnect_attempts = 0  # 연결 성공 시 재시도 횟수 초기화
        self.connection_state = ConnectionState.CONNECTING
        
        try:
            self.logger.info(f"호스트에 연결 중: {self.ws_url}")
            
            # WebSocket 연결
            self.websocket = await websockets.connect(self.ws_url)
            self.logger.info("WebSocket 연결 성공")
            
            # 연결 메시지 전송 (학습한 세션 epoch 태그 — 구 세대 재접속은 서버가 거부, t_7846bbe3 §4.1/§5.2)
            connect_msg = MessageBuilder.connect(player_id, player_name, epoch=self.session_epoch)
            connect_data = connect_msg.to_json().encode('utf-8')
            self.logger.debug(f"연결 메시지 전송: {len(connect_data)} bytes, 타입={connect_msg.type}, player_id={player_id}")
            await self._send_raw(connect_data, self.websocket)
            self.logger.debug("연결 메시지 전송 완료, 응답 대기 중...")
            
            # 연결 승인 메시지 수신 (메시지 수신 루프 시작 전에 먼저 수신)
            try:
                data = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
                self.logger.debug(f"호스트로부터 데이터 수신: {len(data)} bytes")
                message = await self._receive_message(data)
                self.logger.debug(f"메시지 파싱 완료: message={message}, type={message.type if message else None}")
                
                if message is None:
                    self.logger.error("메시지 파싱 실패: None 반환")
                    raise Exception("호스트로부터 받은 메시지를 파싱할 수 없습니다")
                
                if message.type == MessageType.CONNECTION_ACCEPTED:
                    self.logger.info("호스트 연결 승인됨")
                    session_id = message.data.get("session_id", "unknown")
                    self.logger.info(f"세션 ID: {session_id}")
                    await self._handle_message(message)
                    self.connection_state = ConnectionState.CONNECTED
                    # 호스트 세션 epoch 저장 (재접속 시 CONNECT에 태그)
                    self.session_epoch = message.epoch or getattr(self, 'session_epoch', 0)
                    
                    # 세션 시드 메시지도 바로 수신 (호스트가 바로 보냄)
                    try:
                        seed_data = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                        seed_message = await self._receive_message(seed_data)
                        if seed_message:
                            await self._handle_message(seed_message, self.HOST_TRANSPORT_SENDER)
                            self.logger.info(f"세션 시드 메시지 처리 완료: {seed_message.type}")
                    except asyncio.TimeoutError:
                        self.logger.warning("세션 시드 메시지 타임아웃 (백그라운드 루프에서 수신 예정)")
                else:
                    # 세션 만료 거부: 재연결 루프를 즉시 포기 (t_7846bbe3 §4.3)
                    if message.type == MessageType.SESSION_STALE:
                        self.logger.warning(
                            f"접속 거부 (세션 epoch 불일치): server={message.data.get('server_epoch')}, "
                            f"client={message.data.get('client_epoch')}"
                        )
                        self.session_stale = True
                        self._auto_reconnect = False
                        self.connection_state = ConnectionState.DISCONNECTED
                        try:
                            await self.websocket.close()
                        except Exception:
                            pass
                        self.websocket = None
                        raise Exception("재접속 거부: 세션이 만료되었습니다 (구 세대)")
                    # 예상하지 못한 메시지 타입
                    raise Exception(f"연결 거부됨: 받은 메시지 타입={message.type} (예상: {MessageType.CONNECTION_ACCEPTED})")
            
            except websockets.exceptions.ConnectionClosedOK as e:
                self.logger.warning(f"호스트 연결 정상 종료: {e}")
                self.connection_state = ConnectionState.DISCONNECTED
                raise Exception("호스트가 연결을 종료했습니다")
            except websockets.exceptions.ConnectionClosedError as e:
                self.logger.error(f"호스트 연결 종료 오류: {e}")
                self.connection_state = ConnectionState.DISCONNECTED
                raise Exception(f"호스트 연결 종료: {e}")
            except asyncio.TimeoutError:
                self.logger.error("연결 승인 메시지 타임아웃: 호스트로부터 응답이 없습니다")
                self.connection_state = ConnectionState.DISCONNECTED
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                raise Exception("연결 타임아웃: 호스트로부터 응답이 없습니다")
            
            # 핑 루프 시작
            await self.start_ping_loop()
            
            # 메시지 수신 루프 시작
            asyncio.create_task(self._receive_loop())
            
            # 클라이언트 이벤트 루프 참조 저장 (동기 코드에서 전송용)
            try:
                self._client_event_loop = asyncio.get_running_loop()
            except RuntimeError:
                self.logger.warning("실행 중인 이벤트 루프를 찾을 수 없습니다")
        
        except Exception as e:
            self.connection_state = ConnectionState.DISCONNECTED
            self.logger.error(f"호스트 연결 실패: {e}", exc_info=True)
            raise
    
    async def _receive_loop(self):
        """메시지 수신 루프"""
        while self.connection_state == ConnectionState.CONNECTED:
            try:
                if self.websocket:
                    data = await self.websocket.recv()
                    message = await self._receive_message(data)
                    if message:
                        # 세션 종료 통보: 재연결 시도 없이 세션 종료 상태로 전환 (t_7846bbe3 §5.1)
                        if message.type == MessageType.SESSION_ENDED:
                            self.logger.warning(f"세션 종료 통보 수신: {message.data.get('reason', 'unknown')}")
                            self.session_ended = True
                            self._auto_reconnect = False
                            self.connection_state = ConnectionState.DISCONNECTED
                            self._record_ui_notice("session_ended", reason=message.data.get("reason", "unknown"))
                            await self._handle_message(message, self.HOST_TRANSPORT_SENDER)
                            break
                        # FULL_SNAPSHOT/CHARACTER_REVIVAL은 _handle_message 내 직접 처리 경로에서
                        # 단일 적용된다 (t_ceed55de — 이중 적용 방지를 위해 여기선 라우팅하지 않음)
                        await self._handle_message(message, self.HOST_TRANSPORT_SENDER)
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("호스트 연결 종료")
                self.connection_state = ConnectionState.DISCONNECTED
                # 자동 재연결 시도
                if self._auto_reconnect:
                    asyncio.create_task(self._attempt_reconnect())
                break
            except Exception as e:
                self.logger.error(f"메시지 수신 루프 오류: {e}", exc_info=True)
                await asyncio.sleep(0.1)
    
    async def _attempt_reconnect(self):
        """
        자동 재연결 시도
        
        지수 백오프(exponential backoff)를 사용하여 재연결을 시도합니다.
        """
        if not self._auto_reconnect or not self.player_id or not self._player_name:
            self.logger.warning("재연결에 필요한 정보가 없습니다")
            return
        
        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            self.connection_state = ConnectionState.RECONNECTING
            
            # 지수 백오프 대기 시간 계산
            delay = min(
                self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                self._reconnect_max_delay
            )
            
            self.logger.info(
                f"재연결 시도 {self._reconnect_attempts}/{self._max_reconnect_attempts} "
                f"({delay:.1f}초 후)"
            )
            
            await asyncio.sleep(delay)
            
            try:
                # WebSocket 재연결
                self.websocket = await asyncio.wait_for(
                    websockets.connect(self.ws_url),
                    timeout=10.0
                )
                self.logger.info("WebSocket 재연결 성공")
                
                # 연결 메시지 전송 (학습한 epoch 태그, t_7846bbe3 §5.2)
                connect_msg = MessageBuilder.connect(self.player_id, self._player_name, epoch=self.session_epoch)
                await self._send_raw(connect_msg.to_json().encode('utf-8'), self.websocket)

                # 연결 승인 대기
                data = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
                message = await self._receive_message(data)

                # 세션 만료/종료 거부: 재연결 루프를 즉시 포기한다 (t_7846bbe3 §4.3)
                if message and message.type == MessageType.SESSION_STALE:
                    self.logger.warning(
                        f"재접속 거부 (세션 epoch 불일치): server={message.data.get('server_epoch')}, "
                        f"client={message.data.get('client_epoch')}"
                    )
                    self.session_stale = True
                    self._auto_reconnect = False
                    self.connection_state = ConnectionState.DISCONNECTED
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                    self.websocket = None
                    return
                if message and message.type == MessageType.CONNECTION_REJECTED:
                    self.logger.warning(f"재접속 거부: {message.data.get('reason', 'unknown')}")
                    self._auto_reconnect = False
                    self.connection_state = ConnectionState.DISCONNECTED
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                    self.websocket = None
                    return
                
                if message and message.type == MessageType.CONNECTION_ACCEPTED:
                    self.logger.info("재연결 성공!")
                    self.connection_state = ConnectionState.CONNECTED
                    self._reconnect_attempts = 0
                    
                    # 세션 시드 메시지 수신
                    try:
                        seed_data = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                        seed_message = await self._receive_message(seed_data)
                        if seed_message:
                            await self._handle_message(seed_message, self.HOST_TRANSPORT_SENDER)
                    except asyncio.TimeoutError:
                        pass
                    
                    # 전투 상태 동기화 요청 (진행 중인 전투가 있을 경우)
                    try:
                        state_sync_msg = NetworkMessage(
                            type=MessageType.REQUEST_STATE_SYNC,
                            player_id=self.player_id,
                            data={}
                        )
                        await self._send_raw(state_sync_msg.to_json().encode('utf-8'), self.websocket)
                        self.logger.info("전투 상태 동기화 요청 전송")

                        # FULL_STATE_SYNC 응답 수신 (타임아웃 3초)
                        try:
                            sync_data = await asyncio.wait_for(self.websocket.recv(), timeout=3.0)
                            sync_message = await self._receive_message(sync_data)
                            if sync_message and sync_message.type == MessageType.FULL_STATE_SYNC:
                                await self._handle_message(sync_message, self.HOST_TRANSPORT_SENDER)
                                self.logger.info("전투 상태 동기화 완료")
                            elif sync_message:
                                # 전투 중이 아니라 다른 메시지가 온 경우 정상 처리
                                await self._handle_message(sync_message, self.HOST_TRANSPORT_SENDER)
                        except asyncio.TimeoutError:
                            self.logger.debug("전투 상태 동기화 응답 없음 (전투 중이 아닐 수 있음)")
                    except Exception as e:
                        self.logger.debug(f"전투 상태 동기화 요청 실패 (무시 가능): {e}")

                    # 핑 루프 재시작
                    await self.start_ping_loop()

                    # 메시지 수신 루프 재시작
                    asyncio.create_task(self._receive_loop())
                    return
                else:
                    raise Exception("재연결 승인 실패")
                    
            except Exception as e:
                self.logger.warning(f"재연결 시도 {self._reconnect_attempts} 실패: {e}")
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                    self.websocket = None
        
        # 최대 재시도 횟수 초과
        self.logger.error(
            f"재연결 실패: 최대 재시도 횟수({self._max_reconnect_attempts}) 초과"
        )
        self.connection_state = ConnectionState.DISCONNECTED
        self._auto_reconnect = False  # 더 이상 재연결 시도 안 함
    
    async def disconnect(self):
        """연결 종료"""
        self.logger.info("호스트 연결 종료 중...")
        
        # 자동 재연결 비활성화 (사용자가 수동으로 종료하는 경우)
        self._auto_reconnect = False
        
        # 핑 루프 중지
        await self.stop_ping_loop()
        
        # 연결 종료
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connection_state = ConnectionState.DISCONNECTED
        self.logger.info("호스트 연결 종료 완료")
    
    def set_auto_reconnect(self, enabled: bool):
        """
        자동 재연결 활성화/비활성화
        
        Args:
            enabled: 활성화 여부
        """
        self._auto_reconnect = enabled
        self.logger.info(f"자동 재연결 {'활성화' if enabled else '비활성화'}")
