"""
네트워크 관리자

P2P 멀티플레이를 위한 WebSocket 기반 네트워크 레이어
"""

import asyncio
import json
import time
import gzip
import socket
from typing import Dict, Callable, Optional, Set, Any, List
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
            
            await asyncio.gather(*[
                self._send_raw(data, client) for client in targets.values()
            ], return_exceptions=True)
    
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
    
    async def start_server(self):
        """서버 시작 (사용 가능한 포트 자동 검색)"""
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
                    self.clients[client_id] = websocket
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
                    
                    # 연결 승인 메시지 전송
                    session_id = self.session.session_id if self.session else "unknown"
                    accept_msg = MessageBuilder.connection_accepted(
                        client_id,
                        session_id
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
                                "player_id": local_player.player_id,
                                "player_name": local_player.player_name,
                                "x": local_player.x,
                                "y": local_player.y,
                                "is_host": local_player.is_host,
                                "party_count": len(local_player.party) if local_player.party else 0
                            } for local_player in self.session.players.values()
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
                # 클라이언트 제거
                if client_id:
                    # 먼저 세션에서 플레이어 제거
                    player_was_in_session = False
                    if self.session and client_id in self.session.players:
                        self.session.remove_player(client_id)
                        player_was_in_session = True
                        self.logger.info(f"세션에서 플레이어 제거: {client_id}")
                    
                    # 클라이언트를 딕셔너리에서 제거
                    was_in_clients = client_id in self.clients
                    if was_in_clients:
                        del self.clients[client_id]
                    if client_id in self.ping_history:
                        del self.ping_history[client_id]
                    
                    # 연결 종료 메시지 브로드캐스트 (다른 클라이언트들에게만, 연결이 끊어진 클라이언트 제외)
                    # 플레이어가 세션에 있었고 다른 클라이언트가 남아있는 경우에만 브로드캐스트
                    if player_was_in_session and self.clients:
                        try:
                            disconnect_msg = NetworkMessage(
                                type=MessageType.PLAYER_LEFT,
                                player_id=client_id
                            )
                            # 연결이 끊어진 클라이언트를 제외하고 브로드캐스트
                            await self.broadcast(disconnect_msg)
                        except Exception as e:
                            # 연결 종료 중일 때는 메시지 전송 실패가 흔할 수 있으므로 경고만 출력
                            self.logger.debug(f"연결 종료 메시지 브로드캐스트 실패 (무시 가능): {e}")
                    
                    self.logger.info(f"클라이언트 연결 종료: {client_id}")
        
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
        
        # 서버 시작 로그 (실제 접속 가능한 IP 주소 표시)
        self.logger.info(f"호스트 서버 시작 완료: ws://0.0.0.0:{self.port}")
        self.logger.info(f"로컬 네트워크 접속 주소: ws://{local_ip}:{self.port}")
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
        """서버 중지"""
        self.logger.info("호스트 서버 중지 중...")
        
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
    
    async def connect(self, player_id: str, player_name: str):
        """
        호스트에 연결
        
        Args:
            player_id: 플레이어 ID
            player_name: 플레이어 이름
        """
        self.player_id = player_id
        self.connection_state = ConnectionState.CONNECTING
        
        try:
            self.logger.info(f"호스트에 연결 중: {self.ws_url}")
            
            # WebSocket 연결
            self.websocket = await websockets.connect(self.ws_url)
            self.logger.info("WebSocket 연결 성공")
            
            # 연결 메시지 전송
            connect_msg = MessageBuilder.connect(player_id, player_name)
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
                    
                    # 세션 시드 메시지도 바로 수신 (호스트가 바로 보냄)
                    try:
                        seed_data = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                        seed_message = await self._receive_message(seed_data)
                        if seed_message:
                            await self._handle_message(seed_message, "host")
                            self.logger.info(f"세션 시드 메시지 처리 완료: {seed_message.type}")
                    except asyncio.TimeoutError:
                        self.logger.warning("세션 시드 메시지 타임아웃 (백그라운드 루프에서 수신 예정)")
                else:
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
                        await self._handle_message(message, "host")
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("호스트 연결 종료")
                self.connection_state = ConnectionState.DISCONNECTED
                break
            except Exception as e:
                self.logger.error(f"메시지 수신 루프 오류: {e}", exc_info=True)
                await asyncio.sleep(0.1)
    
    async def disconnect(self):
        """연결 종료"""
        self.logger.info("호스트 연결 종료 중...")
        
        # 핑 루프 중지
        await self.stop_ping_loop()
        
        # 연결 종료
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connection_state = ConnectionState.DISCONNECTED
        self.logger.info("호스트 연결 종료 완료")

