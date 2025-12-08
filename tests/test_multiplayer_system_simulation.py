"""
멀티플레이 시스템 시뮬레이션 테스트

네트워크 지연, 경쟁 상태, 예외 상황 등을 포함한 포괄적인 시스템 테스트입니다.
"""

import pytest
import asyncio
import time
import queue
import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass

from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.protocol import NetworkMessage, MessageType, MessageBuilder
from src.core.logger import get_logger

# 테스트용 로거 설정
logger = logging.getLogger("multiplayer.simulation")
logger.setLevel(logging.DEBUG)


class NetworkLink:
    """네트워크 링크 시뮬레이터 (지연, 패킷 손실, 순서 뒤바뀜 등 시뮬레이션)"""
    
    def __init__(self, latency_ms: float = 0.0, jitter_ms: float = 0.0, drop_rate: float = 0.0):
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.drop_rate = drop_rate
        self.queue: List[Tuple[float, NetworkMessage, str, str]] = []  # (arrival_time, msg, source, dest)
        self.connected = True
    
    def send(self, message: NetworkMessage, source_id: str, dest_id: str):
        """메시지 전송"""
        if not self.connected:
            return
            
        import random
        
        # 패킷 손실 시뮬레이션
        if self.drop_rate > 0 and random.random() < self.drop_rate:
            logger.debug(f"[Network] Packet dropped: {message.type} from {source_id} to {dest_id}")
            return
            
        # 지연 시간 계산
        delay = self.latency_ms + random.uniform(-self.jitter_ms, self.jitter_ms)
        delay = max(0, delay) / 1000.0  # ms -> seconds
        
        arrival_time = time.time() + delay
        self.queue.append((arrival_time, message, source_id, dest_id))
        
        # 도착 시간 순으로 정렬 (우선순위 큐 역할)
        self.queue.sort(key=lambda x: x[0])
        
    def process(self, current_time: float) -> List[Tuple[NetworkMessage, str, str]]:
        """도착한 메시지 처리"""
        arrived = []
        remaining = []
        
        for item in self.queue:
            arrival_time, msg, src, dst = item
            if arrival_time <= current_time:
                arrived.append((msg, src, dst))
            else:
                remaining.append(item)
        
        self.queue = remaining
        return arrived


class MockClient:
    """모의 클라이언트"""
    
    def __init__(self, player_id: str, name: str, network: NetworkLink, session: MultiplayerSession):
        self.player_id = player_id
        self.player_name = name
        self.network = network
        self.session = session
        self.player = MultiplayerPlayer(player_id, name)
        
        # 클라이언트 상태
        self.is_host = False
        self.current_floor = 0
        self.known_players: Dict[str, Dict] = {}
        self.received_messages: List[NetworkMessage] = []
        self.position = (0, 0)
        
    def update(self):
        """클라이언트 업데이트 (메시지 수신 등)"""
        # 실제 환경에서는 소켓에서 읽겠지만, 여기서는 NetworkLink가 중앙에서 분배
        pass
        
    def handle_message(self, message: NetworkMessage):
        """메시지 처리 핸들러"""
        self.received_messages.append(message)
        
        if message.type == MessageType.CONNECTION_ACCEPTED:
            self.session.add_player(self.player)
            
        elif message.type == MessageType.PLAYER_JOINED:
            for p_data in message.data.get("players", []):
                self.known_players[p_data["player_id"]] = p_data
                
        elif message.type == MessageType.PLAYER_MOVE:
            pid = message.player_id
            if pid != self.player_id:
                if pid not in self.known_players:
                    self.known_players[pid] = {}
                self.known_players[pid]["x"] = message.data["x"]
                self.known_players[pid]["y"] = message.data["y"]
                
        elif message.type == MessageType.HOST_MIGRATED:
            logger.info(f"[{self.player_id}] Received HOST_MIGRATED: {message.data}")
            new_host_id = message.data["new_host_id"]
            if new_host_id == self.player_id:
                self.is_host = True
                logger.info(f"[{self.player_id}] I am the new host!")
            else:
                self.is_host = False

    def connect(self):
        """서버 연결 시도"""
        msg = MessageBuilder.connect(self.player_id, self.player_name)
        self.network.send(msg, self.player_id, "server")
        
    def move(self, x: int, y: int):
        """이동 요청"""
        self.position = (x, y)
        # 클라이언트는 즉시 반영 (예측 이동)
        self.player.x = x
        self.player.y = y
        
        # 서버에 통지
        msg = MessageBuilder.player_move(self.player_id, x, y)
        self.network.send(msg, self.player_id, "server")
        
    def disconnect(self):
        """연결 종료"""
        msg = NetworkMessage(MessageType.DISCONNECT, player_id=self.player_id)
        self.network.send(msg, self.player_id, "server")


class ServerSimulator:
    """서버 시뮬레이터 (호스트 역할 포함)"""
    
    def __init__(self, session: MultiplayerSession, network: NetworkLink):
        self.session = session
        self.network = network
        self.message_handlers = {
            MessageType.CONNECT: self.handle_connect,
            MessageType.DISCONNECT: self.handle_disconnect,
            MessageType.PLAYER_MOVE: self.handle_move,
            # 추가 핸들러...
        }
        
    def process_message(self, message: NetworkMessage, source_id: str):
        """메시지 처리"""
        if message.type in self.message_handlers:
            self.message_handlers[message.type](message, source_id)
            
    def handle_connect(self, message: NetworkMessage, source_id: str):
        player_id = message.player_id
        name = message.data.get("player_name", "Unknown")
        
        # 플레이어 객체 생성 및 추가는 MockClient에서 이미 했지만,
        # 여기서는 세션에 등록되는 과정을 시뮬레이션
        # 실제로는 session.add_player가 여기서 호출되어야 함
        # 하지만 MockClient 구조상 약간 다름.
        # 시뮬레이션 편의를 위해 여기서 응답만 보냄
        
        response = MessageBuilder.connection_accepted(player_id, self.session.session_id)
        self.network.send(response, "server", player_id)
        
        # 다른 플레이어들에게 알림
        players_data = []
        for pid, p in self.session.players.items():
            players_data.append(p.serialize())
            
        notify = MessageBuilder.player_list(players_data)
        self.broadcast(notify)
        
    def handle_disconnect(self, message: NetworkMessage, source_id: str):
        self.session.remove_player(source_id)
        # 실제로는 여기서 호스트 마이그레이션 등을 처리하고 브로드캐스트
        
    def handle_move(self, message: NetworkMessage, source_id: str):
        player = self.session.get_player(source_id)
        if player:
            # 타임스탬프 검사 (실제 MovementSyncManager 로직 반영)
            timestamp = message.timestamp
            if hasattr(player, 'last_movement_timestamp'):
                if timestamp < player.last_movement_timestamp:
                    return
                player.last_movement_timestamp = timestamp

            player.x = message.data["x"]
            player.y = message.data["y"]
            
            # 다른 플레이어들에게 브로드캐스트 (Echo)
            # 실제 서버는 검증 로직이 들어감
            self.broadcast(message, exclude_id=source_id)
            
    def broadcast(self, message: NetworkMessage, exclude_id: str = None):
        for pid in self.session.players:
            if pid != exclude_id:
                self.network.send(message, "server", pid)


class TestSystemSimulation:
    """시스템 시뮬레이션 테스트"""
    
    def test_basic_lifecycle_simulation(self):
        """기본 생명주기 시뮬레이션 (연결 -> 이동 -> 연결 종료)"""
        network = NetworkLink(latency_ms=10)
        session = MultiplayerSession(max_players=4)
        server = ServerSimulator(session, network)
        
        clients = []
        for i in range(3):
            client = MockClient(f"player_{i}", f"Player {i}", network, session)
            clients.append(client)
            
        # 1. 모든 클라이언트 연결
        for client in clients:
            client.connect()
            
        # 시뮬레이션 루프 (약 1초간)
        start_time = time.time()
        while time.time() - start_time < 1.0:
            # 네트워크 처리
            messages = network.process(time.time())
            for msg, src, dst in messages:
                if dst == "server":
                    server.process_message(msg, src)
                else:
                    # 클라이언트에게 전달
                    for client in clients:
                        if client.player_id == dst:
                            client.handle_message(msg)
                            
            time.sleep(0.01)
            
        # 모든 클라이언트가 세션에 있는지 확인
        assert session.player_count == 3
        for client in clients:
            assert client.player_id in session.players
            
        # 2. 이동 시뮬레이션
        clients[0].move(10, 20)
        
        # 처리 대기
        start_time = time.time()
        while time.time() - start_time < 0.5:
            messages = network.process(time.time())
            for msg, src, dst in messages:
                if dst == "server":
                    server.process_message(msg, src)
                else:
                    for client in clients:
                        if client.player_id == dst:
                            client.handle_message(msg)
            time.sleep(0.01)
            
        # 서버 상태 확인
        p0 = session.get_player(clients[0].player_id)
        assert p0.x == 10
        assert p0.y == 20
        
        # 다른 클라이언트들이 위치 업데이트를 받았는지 확인
        assert clients[1].known_players[clients[0].player_id]["x"] == 10
        assert clients[1].known_players[clients[0].player_id]["y"] == 20
        
    def test_race_condition_movement(self):
        """이동 동기화 경쟁 상태 테스트 (패킷 순서 뒤바뀜)"""
        # 지연 시간 변동폭을 크게 주어 순서가 뒤바뀔 수 있게 함
        network = NetworkLink(latency_ms=100, jitter_ms=50) 
        session = MultiplayerSession(max_players=2)
        server = ServerSimulator(session, network)
        
        client = MockClient("racer", "Racer", network, session)
        client.connect()
        
        # 연결 처리 (충분한 시간 대기)
        start_time = time.time()
        while time.time() - start_time < 1.0:
            messages = network.process(time.time())
            for msg, src, dst in messages:
                if dst == "server":
                    server.process_message(msg, src)
                elif dst == "racer":
                    client.handle_message(msg)
            time.sleep(0.01)
            
        # 빠르게 여러 번 이동
        # 패킷 1: (1,1)
        # 패킷 2: (2,2)
        # 패킷 3: (3,3)
        
        # NetworkLink 구현상, jitter가 크면 순서가 뒤바뀔 수 있음
        # 예: 패킷 3이 먼저 도착, 그 다음 패킷 2가 도착하면
        # 서버는 (3,3) -> (2,2) 순으로 업데이트할 수 있음
        # 이렇게 되면 최종 위치가 (2,2)가 되어버림 (구형 패킷 덮어쓰기)
        
        client.move(1, 1)
        time.sleep(0.005)
        client.move(2, 2)
        time.sleep(0.005)
        client.move(3, 3)
        
        # 처리 대기 (충분히 길게)
        start_time = time.time()
        while time.time() - start_time < 2.0:
            messages = network.process(time.time())
            for msg, src, dst in messages:
                if dst == "server":
                    server.process_message(msg, src)
            time.sleep(0.01)
            
        # 최종 위치 확인
        server_player = session.get_player("racer")
        
        logger.info(f"Server final position: {server_player.x}, {server_player.y}")
        
        # 만약 (3,3)이 아닌 다른 위치라면, 구형 패킷이 최신 패킷을 덮어쓴 것임
        # 이는 버그이므로 수정해야 함
        
        # 여기서는 "올바른 동작"을 테스트함. 즉, (3,3)이어야 함.
        # 실패한다면 버그가 있는 것.
        assert server_player.x == 3
        assert server_player.y == 3
        
    def test_disconnect_handling(self):
        """연결 끊김 및 호스트 마이그레이션 테스트"""
        network = NetworkLink()
        session = MultiplayerSession(max_players=3)
        server = ServerSimulator(session, network)
        
        c1 = MockClient("p1", "Host", network, session)
        c2 = MockClient("p2", "Client", network, session)
        
        # 연결 설정 (수동으로 호스트 설정)
        session.add_player(c1.player) # p1은 호스트
        session.add_player(c2.player)
        
        assert session.host_id == "p1"
        
        # 호스트 연결 종료
        session.remove_player("p1")
        
        # 서버 로직에서 호스트 마이그레이션 메시지 발송 시뮬레이션
        # remove_player는 session 내부 로직으로 이미 호스트를 p2로 변경함
        assert session.host_id == "p2"
        
        migration_msg = MessageBuilder.host_migrated("p2")
        # 중요: session.remove_player("p1") 호출 후, p1은 session.players에 없음.
        # 따라서 server.broadcast는 p2에게만 메시지를 보냄.
        # MockClient c2가 메시지를 받는지 확인.
        server.broadcast(migration_msg)
        
        # 클라이언트 업데이트 (반복적으로 수행)
        # 메시지가 큐에 들어가고 process에서 꺼내와야 함
        
        received_migration = False
        start_time = time.time()
        while time.time() - start_time < 1.0:
            messages = network.process(time.time())
            for msg, src, dst in messages:
                 if dst == "p2":
                     c2.handle_message(msg)
                     if msg.type == MessageType.HOST_MIGRATED:
                         received_migration = True
            if c2.is_host:
                break
            time.sleep(0.01)
            
        # p2가 자신이 호스트임을 인지했는지 확인
        assert c2.is_host is True, f"p2 should be promoted to host. Received migration msg: {received_migration}"
