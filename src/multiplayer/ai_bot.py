"""
AI 봇 시스템 - 멀티플레이어 테스트 및 자동 플레이어

실제 게임 파일을 사용하여 멀티플레이어 테스트를 수행하는 AI 봇입니다.
나중에 확장하여 플레이어 부족 시 자동으로 채울 수 있습니다.
"""

import time
import random
from typing import Optional, Dict, Any, List
from enum import Enum
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.session import MultiplayerSession
from src.core.logger import get_logger


class BotBehavior(Enum):
    """봇 행동 패턴"""
    PASSIVE = "passive"  # 수동적 (거의 움직이지 않음)
    EXPLORER = "explorer"  # 탐험형 (맵을 돌아다님)
    AGGRESSIVE = "aggressive"  # 공격적 (적을 찾아 공격)
    FOLLOW = "follow"  # 따라다니기 (다른 플레이어를 따라감)
    RANDOM = "random"  # 랜덤 행동


class AIBot:
    """AI 봇 클래스"""
    
    def __init__(
        self,
        bot_id: str,
        bot_name: str,
        network_manager: NetworkManager,
        session: MultiplayerSession,
        behavior: BotBehavior = BotBehavior.EXPLORER
    ):
        """
        AI 봇 초기화
        
        Args:
            bot_id: 봇 ID
            bot_name: 봇 이름
            network_manager: 네트워크 관리자
            session: 멀티플레이 세션
            behavior: 봇 행동 패턴
        """
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.network_manager = network_manager
        self.session = session
        self.behavior = behavior
        self.logger = get_logger("multiplayer.ai_bot")
        
        # 봇 상태
        self.is_active = False
        self.current_x = 0
        self.current_y = 0
        self.last_action_time = 0.0
        self.action_interval = 0.5  # 0.5초마다 행동
        
        # 탐험 상태
        self.explored_positions = set()
        self.target_position: Optional[tuple] = None
        self.last_direction = (0, 0)
        
        # 메시지 핸들러 등록
        self._register_handlers()
    
    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        # 플레이어 이동 메시지 수신 (다른 플레이어 위치 추적)
        self.network_manager.register_handler(
            MessageType.PLAYER_MOVE,
            self._handle_player_move
        )
        
        # 게임 시작 메시지 수신
        self.network_manager.register_handler(
            MessageType.GAME_START,
            self._handle_game_start
        )
    
    def _handle_player_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """플레이어 이동 메시지 처리"""
        if sender_id == self.bot_id:
            return  # 자신의 메시지는 무시
        
        # 다른 플레이어의 위치 업데이트 (FOLLOW 행동 패턴용)
        player_id = message.data.get("player_id") or sender_id
        if player_id and player_id != self.bot_id:
            x = message.data.get("x", 0)
            y = message.data.get("y", 0)
            # 필요시 다른 플레이어 위치 저장 (FOLLOW 패턴용)
            if self.behavior == BotBehavior.FOLLOW:
                self.target_position = (x, y)
    
    def _handle_game_start(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """게임 시작 메시지 처리"""
        player_positions = message.data.get("player_positions", {})
        if self.bot_id in player_positions:
            pos = player_positions[self.bot_id]
            self.current_x = pos.get("x", 0)
            self.current_y = pos.get("y", 0)
            self.logger.info(f"봇 {self.bot_name} 초기 위치 설정: ({self.current_x}, {self.current_y})")
    
    def start(self):
        """봇 시작"""
        self.is_active = True
        self.logger.info(f"AI 봇 {self.bot_name} 시작 (행동 패턴: {self.behavior.value})")
    
    def stop(self):
        """봇 중지"""
        self.is_active = False
        self.logger.info(f"AI 봇 {self.bot_name} 중지")
    
    def update(self, current_time: float):
        """
        봇 업데이트 (주기적으로 호출)
        
        Args:
            current_time: 현재 시간
        """
        if not self.is_active:
            return
        
        # 행동 간격 체크
        if current_time - self.last_action_time < self.action_interval:
            return
        
        self.last_action_time = current_time
        
        # 행동 패턴에 따라 행동 결정
        action = self._decide_action()
        if action:
            self._execute_action(action)
    
    def _decide_action(self) -> Optional[Dict[str, Any]]:
        """
        행동 결정
        
        Returns:
            행동 딕셔너리 또는 None
        """
        if self.behavior == BotBehavior.PASSIVE:
            # 수동적: 가끔만 움직임
            if random.random() < 0.1:  # 10% 확률로 움직임
                return self._get_random_move()
            return None
        
        elif self.behavior == BotBehavior.EXPLORER:
            # 탐험형: 미탐험 지역으로 이동
            return self._get_exploration_move()
        
        elif self.behavior == BotBehavior.AGGRESSIVE:
            # 공격적: 적을 찾아 이동 (현재는 랜덤 이동)
            return self._get_random_move()
        
        elif self.behavior == BotBehavior.FOLLOW:
            # 따라다니기: 다른 플레이어를 따라감 (현재는 랜덤 이동)
            return self._get_random_move()
        
        elif self.behavior == BotBehavior.RANDOM:
            # 랜덤 행동
            if random.random() < 0.7:  # 70% 확률로 움직임
                return self._get_random_move()
            return None
        
        return None
    
    def _get_random_move(self) -> Dict[str, Any]:
        """랜덤 이동 행동 생성"""
        directions = [
            (0, -1),  # 위
            (0, 1),   # 아래
            (-1, 0),  # 왼쪽
            (1, 0),   # 오른쪽
            (-1, -1), # 왼쪽 위
            (1, -1),  # 오른쪽 위
            (-1, 1),  # 왼쪽 아래
            (1, 1)    # 오른쪽 아래
        ]
        
        # 이전 방향 유지 확률 (30%)
        if random.random() < 0.3 and self.last_direction != (0, 0):
            dx, dy = self.last_direction
        else:
            dx, dy = random.choice(directions)
            self.last_direction = (dx, dy)
        
        new_x = self.current_x + dx
        new_y = self.current_y + dy
        
        return {
            "type": "move",
            "dx": dx,
            "dy": dy,
            "x": new_x,
            "y": new_y
        }
    
    def _get_exploration_move(self) -> Dict[str, Any]:
        """탐험형 이동 행동 생성"""
        # 현재 위치 기록
        self.explored_positions.add((self.current_x, self.current_y))
        
        # 주변 미탐험 지역 찾기
        directions = [
            (0, -1),  # 위
            (0, 1),   # 아래
            (-1, 0),  # 왼쪽
            (1, 0),   # 오른쪽
        ]
        
        unexplored_directions = []
        for dx, dy in directions:
            new_pos = (self.current_x + dx, self.current_y + dy)
            if new_pos not in self.explored_positions:
                unexplored_directions.append((dx, dy))
        
        if unexplored_directions:
            # 미탐험 지역으로 이동
            dx, dy = random.choice(unexplored_directions)
        else:
            # 모든 방향이 탐험됨: 랜덤 이동
            dx, dy = random.choice(directions)
        
        new_x = self.current_x + dx
        new_y = self.current_y + dy
        
        return {
            "type": "move",
            "dx": dx,
            "dy": dy,
            "x": new_x,
            "y": new_y
        }
    
    def _get_follow_move(self) -> Dict[str, Any]:
        """따라다니기 이동 행동 생성"""
        if not self.target_position:
            return self._get_random_move()
        
        target_x, target_y = self.target_position
        
        # 목표 위치로 이동
        dx = 0
        dy = 0
        
        if target_x > self.current_x:
            dx = 1
        elif target_x < self.current_x:
            dx = -1
        
        if target_y > self.current_y:
            dy = 1
        elif target_y < self.current_y:
            dy = -1
        
        # 대각선 이동 방지 (한 번에 한 방향만)
        if dx != 0 and dy != 0:
            if random.random() < 0.5:
                dx = 0
            else:
                dy = 0
        
        new_x = self.current_x + dx
        new_y = self.current_y + dy
        
        return {
            "type": "move",
            "dx": dx,
            "dy": dy,
            "x": new_x,
            "y": new_y
        }
    
    def _execute_action(self, action: Dict[str, Any]):
        """
        행동 실행
        
        Args:
            action: 행동 딕셔너리
        """
        if action["type"] == "move":
            self._execute_move(action)
    
    def _execute_move(self, action: Dict[str, Any]):
        """이동 행동 실행"""
        new_x = action["x"]
        new_y = action["y"]
        
        # 위치 업데이트
        self.current_x = new_x
        self.current_y = new_y
        
        # 네트워크로 이동 메시지 전송
        try:
            move_message = MessageBuilder.player_move(
                player_id=self.bot_id,
                x=new_x,
                y=new_y,
                timestamp=time.time()
            )
            
            # 클라이언트인 경우 호스트에게만 전송
            if not self.network_manager.is_host:
                self.network_manager.send(move_message)
            else:
                # 호스트인 경우 브로드캐스트
                self.network_manager.broadcast(move_message)
            
            self.logger.debug(f"봇 {self.bot_name} 이동: ({new_x}, {new_y})")
        except Exception as e:
            self.logger.error(f"봇 이동 메시지 전송 실패: {e}", exc_info=True)


class BotManager:
    """봇 관리자"""
    
    def __init__(
        self,
        network_manager: NetworkManager,
        session: MultiplayerSession
    ):
        """
        봇 관리자 초기화
        
        Args:
            network_manager: 네트워크 관리자
            session: 멀티플레이 세션
        """
        self.network_manager = network_manager
        self.session = session
        self.bots: Dict[str, AIBot] = {}
        self.logger = get_logger("multiplayer.bot_manager")
        self.is_running = False
        self.last_update_time = 0.0
        self.update_interval = 0.1  # 0.1초마다 업데이트
    
    def add_bot(
        self,
        bot_id: str,
        bot_name: str,
        behavior: BotBehavior = BotBehavior.EXPLORER
    ) -> AIBot:
        """
        봇 추가
        
        Args:
            bot_id: 봇 ID
            bot_name: 봇 이름
            behavior: 행동 패턴
        
        Returns:
            생성된 봇 객체
        """
        bot = AIBot(
            bot_id=bot_id,
            bot_name=bot_name,
            network_manager=self.network_manager,
            session=self.session,
            behavior=behavior
        )
        self.bots[bot_id] = bot
        self.logger.info(f"봇 추가: {bot_name} (ID: {bot_id}, 행동: {behavior.value})")
        return bot
    
    def remove_bot(self, bot_id: str):
        """봇 제거"""
        if bot_id in self.bots:
            self.bots[bot_id].stop()
            del self.bots[bot_id]
            self.logger.info(f"봇 제거: {bot_id}")
    
    def start_all(self):
        """모든 봇 시작"""
        for bot in self.bots.values():
            bot.start()
        self.is_running = True
        self.logger.info(f"{len(self.bots)}개의 봇 시작")
    
    def stop_all(self):
        """모든 봇 중지"""
        for bot in self.bots.values():
            bot.stop()
        self.is_running = False
        self.logger.info("모든 봇 중지")
    
    def update(self, current_time: float):
        """
        모든 봇 업데이트
        
        Args:
            current_time: 현재 시간
        """
        if not self.is_running:
            return
        
        # 업데이트 간격 체크
        if current_time - self.last_update_time < self.update_interval:
            return
        
        self.last_update_time = current_time
        
        # 모든 봇 업데이트
        for bot in self.bots.values():
            try:
                bot.update(current_time)
            except Exception as e:
                self.logger.error(f"봇 업데이트 오류: {e}", exc_info=True)
    
    def get_bot(self, bot_id: str) -> Optional[AIBot]:
        """봇 가져오기"""
        return self.bots.get(bot_id)
    
    def get_all_bots(self) -> List[AIBot]:
        """모든 봇 가져오기"""
        return list(self.bots.values())

