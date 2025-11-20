"""
멀티플레이 테스트 도우미

혼자서 멀티플레이를 테스트할 수 있는 모의 클라이언트 시스템
"""

import asyncio
import time
import random
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.protocol import MessageType, MessageBuilder
from src.core.logger import get_logger


@dataclass
class MockClient:
    """모의 클라이언트"""
    
    player_id: str
    player_name: str
    x: int = 0
    y: int = 0
    is_connected: bool = True
    last_action_time: float = 0.0
    
    def __init__(self, player_id: str, player_name: str):
        """초기화"""
        self.player_id = player_id
        self.player_name = player_name
        self.x = random.randint(5, 15)
        self.y = random.randint(5, 15)
        self.is_connected = True
        self.last_action_time = time.time()
    
    def generate_random_move(self) -> tuple[int, int]:
        """랜덤 이동 생성"""
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        return (dx, dy)
    
    def should_move(self, current_time: float, interval: float = 2.0) -> bool:
        """이동해야 하는지 확인"""
        return current_time - self.last_action_time >= interval


class MultiplayerTestHelper:
    """멀티플레이 테스트 도우미"""
    
    def __init__(self, session: MultiplayerSession):
        """
        초기화
        
        Args:
            session: 멀티플레이 세션
        """
        self.session = session
        self.logger = get_logger("multiplayer.test_helper")
        self.mock_clients: List[MockClient] = []
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    def add_mock_client(self, player_name: str) -> MockClient:
        """
        모의 클라이언트 추가
        
        Args:
            player_name: 플레이어 이름
            
        Returns:
            생성된 모의 클라이언트
        """
        # 플레이어 생성
        player = MultiplayerPlayer(
            player_id=f"mock_{len(self.mock_clients) + 1}",
            player_name=player_name
        )
        
        # 세션에 추가
        self.session.add_player(player)
        
        # 모의 클라이언트 생성
        mock_client = MockClient(player.player_id, player_name)
        self.mock_clients.append(mock_client)
        
        self.logger.info(f"모의 클라이언트 추가: {player_name} (ID: {player.player_id})")
        
        return mock_client
    
    def add_bots(self, count: int, prefix: str = "봇"):
        """
        여러 봇 추가
        
        Args:
            count: 봇 수
            prefix: 봇 이름 접두사
        """
        for i in range(count):
            bot_name = f"{prefix}{i + 1}"
            self.add_mock_client(bot_name)
        
        self.logger.info(f"{count}개의 봇 추가 완료")
    
    async def start_auto_simulation(self, interval: float = 2.0):
        """
        자동 시뮬레이션 시작
        
        Args:
            interval: 행동 간격 (초)
        """
        if self.is_running:
            self.logger.warning("이미 시뮬레이션이 실행 중입니다")
            return
        
        self.is_running = True
        self.logger.info(f"자동 시뮬레이션 시작 (간격: {interval}초)")
        
        self._task = asyncio.create_task(self._simulation_loop(interval))
    
    async def stop_auto_simulation(self):
        """자동 시뮬레이션 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("자동 시뮬레이션 중지")
    
    async def _simulation_loop(self, interval: float):
        """시뮬레이션 루프"""
        try:
            while self.is_running:
                current_time = time.time()
                
                # 각 모의 클라이언트에 대해 행동 생성
                for mock_client in self.mock_clients:
                    if not mock_client.is_connected:
                        continue
                    
                    if mock_client.should_move(current_time, interval):
                        # 랜덤 이동
                        dx, dy = mock_client.generate_random_move()
                        
                        # 플레이어 위치 업데이트
                        if mock_client.player_id in self.session.players:
                            player = self.session.players[mock_client.player_id]
                            # 경계 체크는 실제 게임에서 처리
                            new_x = player.x + dx
                            new_y = player.y + dy
                            
                            # 간단한 경계 체크 (0~50 범위)
                            new_x = max(0, min(50, new_x))
                            new_y = max(0, min(50, new_y))
                            
                            player.x = new_x
                            player.y = new_y
                            
                            mock_client.x = new_x
                            mock_client.y = new_y
                            mock_client.last_action_time = current_time
                            
                            self.logger.debug(
                                f"{mock_client.player_name} 이동: "
                                f"({player.x - dx}, {player.y - dy}) -> ({new_x}, {new_y})"
                            )
                
                await asyncio.sleep(0.5)  # 0.5초마다 체크
        
        except asyncio.CancelledError:
            self.logger.info("시뮬레이션 루프 취소됨")
        except Exception as e:
            self.logger.error(f"시뮬레이션 루프 오류: {e}", exc_info=True)
    
    def get_player_positions(self) -> Dict[str, tuple[int, int]]:
        """
        모든 플레이어 위치 가져오기
        
        Returns:
            {player_id: (x, y)} 딕셔너리
        """
        positions = {}
        
        for player_id, player in self.session.players.items():
            positions[player_id] = (player.x, player.y)
        
        return positions
    
    def remove_all_bots(self):
        """모든 봇 제거"""
        bot_ids = [mock_client.player_id for mock_client in self.mock_clients]
        
        for player_id in bot_ids:
            if player_id in self.session.players:
                # 세션에서 플레이어 제거
                if hasattr(self.session, 'remove_player'):
                    self.session.remove_player(player_id)
                elif hasattr(self.session, 'players'):
                    del self.session.players[player_id]
        
        self.mock_clients.clear()
        self.logger.info("모든 봇 제거 완료")


class LocalMultiplayerTest:
    """로컬 멀티플레이 테스트 클래스"""
    
    @staticmethod
    def create_test_session(player_count: int = 2) -> tuple[MultiplayerSession, MultiplayerTestHelper]:
        """
        테스트용 세션 생성
        
        Args:
            player_count: 플레이어 수 (2~4)
            
        Returns:
            (세션, 테스트 도우미) 튜플
            
        Raises:
            ValueError: player_count가 2~4 범위를 벗어난 경우
        """
        if not isinstance(player_count, int):
            raise TypeError(f"player_count는 int 타입이어야 합니다 (받음: {type(player_count)})")
        
        if not (2 <= player_count <= 4):
            raise ValueError(f"플레이어 수는 2~4명 사이여야 합니다 (받음: {player_count})")
        
        # 세션 생성 (검증 포함)
        try:
            session = MultiplayerSession(max_players=player_count)
        except ValueError as e:
            raise ValueError(f"세션 생성 실패: {e}") from e
        
        # 호스트 추가
        host = MultiplayerPlayer(
            player_id="host_player",
            player_name="호스트"
        )
        host.is_host = True
        session.add_player(host)
        session.host_id = host.player_id
        
        # 테스트 도우미 생성
        helper = MultiplayerTestHelper(session)
        
        # 나머지 플레이어를 봇으로 추가
        remaining = player_count - 1
        helper.add_bots(remaining, "봇")
        
        logger = get_logger("multiplayer.test")
        logger.info(f"테스트 세션 생성 완료: {player_count}명 (호스트 1명 + 봇 {remaining}명)")
        
        return session, helper


# 편의 함수
def create_test_session(player_count: int = 2) -> tuple[MultiplayerSession, MultiplayerTestHelper]:
    """
    테스트용 세션 생성 (편의 함수)
    
    Args:
        player_count: 플레이어 수 (2~4)
        
    Returns:
        (세션, 테스트 도우미) 튜플
    """
    return LocalMultiplayerTest.create_test_session(player_count)

