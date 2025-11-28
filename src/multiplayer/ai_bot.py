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
    LLM_AI = "llm_ai"  # LLM 기반 AI (AutoPlayAI 사용)


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
        
        # LLM AI (LLM_AI 행동 패턴일 때만 초기화)
        self.llm_ai = None
        self.party = []  # 봇이 조종하는 파티
        self.inventory = None  # 인벤토리
        self.exploration = None  # 탐험 시스템 참조
        self.floor_number = 1
        
        if self.behavior == BotBehavior.LLM_AI:
            self._init_llm_ai()
        
        # 메시지 핸들러 등록
        self._register_handlers()
    
    def _init_llm_ai(self):
        """LLM AI 초기화"""
        try:
            from src.multiplayer.llm_player_bot import create_auto_play_ai, PlayStyle
            self.llm_ai = create_auto_play_ai(model="qwen3:0.6b", style=PlayStyle.BALANCED)
            self.logger.info(f"봇 {self.bot_name}: LLM AI 초기화 완료")
        except Exception as e:
            self.logger.warning(f"LLM AI 초기화 실패, EXPLORER로 폴백: {e}")
            self.behavior = BotBehavior.EXPLORER
    
    def set_party(self, party: List[Any]):
        """파티 설정 (전투 AI용)"""
        self.party = party
    
    def set_exploration(self, exploration: Any, floor_number: int = 1):
        """탐험 시스템 참조 설정"""
        self.exploration = exploration
        self.floor_number = floor_number
    
    def set_inventory(self, inventory: Any):
        """인벤토리 설정"""
        self.inventory = inventory
    
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
        
        elif self.behavior == BotBehavior.LLM_AI:
            # LLM 기반 AI 행동
            return self._get_llm_ai_move()
        
        return None
    
    def _get_llm_ai_move(self) -> Optional[Dict[str, Any]]:
        """LLM AI 이동 행동 생성"""
        if not self.llm_ai or not self.exploration:
            return self._get_exploration_move()

        try:
            from src.multiplayer.llm_player_bot import ExplorationState

            # 파티 상태 계산
            alive = [c for c in self.party if hasattr(c, 'is_alive') and c.is_alive]
            if not alive:
                alive = self.party if self.party else []

            party_hp = 100.0
            party_mp = 100.0
            if alive:
                party_hp = sum(c.current_hp / c.max_hp * 100 for c in alive if hasattr(c, 'max_hp') and c.max_hp > 0) / len(alive)
                party_mp = sum(c.current_mp / c.max_mp * 100 for c in alive if hasattr(c, 'max_mp') and c.max_mp > 0) / len(alive)

            # 실제 시야(FOV) 기반 정보 수집
            visible_tiles = []
            nearby_enemies = []
            nearby_items = []
            unexplored_directions = []

            # FOV 시야 내 적 감지
            if hasattr(self.exploration, 'fov_map') and self.exploration.fov_map:
                for e in self.exploration.enemies:
                    if self.exploration.fov_map.visible[e.x, e.y]:
                        nearby_enemies.append(f"{e.name}@({e.x},{e.y})")
            else:
                # FOV 없으면 거리 기반
                nearby_enemies = [
                    e.name for e in self.exploration.enemies
                    if abs(e.x - self.current_x) <= 5 and abs(e.y - self.current_y) <= 5
                ]

            # 미탐험 방향 감지
            directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            if hasattr(self.exploration, 'dungeon') and self.exploration.dungeon:
                for dx, dy in directions:
                    nx, ny = self.current_x + dx, self.current_y + dy
                    tile = self.exploration.dungeon.get_tile(nx, ny)
                    if tile and tile.walkable and not tile.explored:
                        unexplored_directions.append((dx, dy))

            # 탐험 상태 구성
            state = ExplorationState(
                current_floor=self.floor_number,
                current_position=(self.current_x, self.current_y),
                visible_tiles=visible_tiles[:50],  # 최대 50개
                discovered_rooms=len(self.explored_positions) // 10,
                total_rooms=10,
                nearby_enemies=nearby_enemies[:10],  # 최대 10개
                nearby_items=nearby_items[:10],  # 최대 10개
                nearby_exits=[],
                party_hp_percent=party_hp,
                party_mp_percent=party_mp,
                has_healing_point=False,
                floor_type="dungeon",
                stairs_down_position=None,
                unexplored_directions=unexplored_directions if unexplored_directions else directions
            )

            # AI 행동 결정
            action = self.llm_ai.decide_exploration_action(state)

            # 행동을 이동으로 변환
            dx, dy = 0, 0

            if action.action_type == "move" and action.direction:
                dx, dy = action.direction
            elif action.action_type == "fight" and nearby_enemies:
                # 가장 가까운 적 방향으로
                if self.exploration and hasattr(self.exploration, 'enemies'):
                    closest = min(self.exploration.enemies,
                        key=lambda e: abs(e.x - self.current_x) + abs(e.y - self.current_y))
                    dx = 1 if closest.x > self.current_x else (-1 if closest.x < self.current_x else 0)
                    dy = 1 if closest.y > self.current_y else (-1 if closest.y < self.current_y else 0)
                else:
                    dx, dy = random.choice([(0, -1), (0, 1), (-1, 0), (1, 0)])
            elif action.action_type == "move" and action.target_position:
                # 목표 위치로
                tx, ty = action.target_position
                dx = 1 if tx > self.current_x else (-1 if tx < self.current_x else 0)
                dy = 1 if ty > self.current_y else (-1 if ty < self.current_y else 0)
            else:
                # 기본: 미탐험 방향으로
                if unexplored_directions:
                    dx, dy = random.choice(unexplored_directions)
                else:
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
        except Exception as e:
            self.logger.warning(f"LLM AI 행동 결정 오류: {e}")
            return self._get_exploration_move()
    
    def get_combat_action(self, combat_manager: Any, current_char: Any) -> Optional[Dict[str, Any]]:
        """
        전투 AI 행동 결정 (외부에서 호출)

        Args:
            combat_manager: 전투 매니저
            current_char: 현재 행동할 캐릭터

        Returns:
            전투 행동 딕셔너리
        """
        if self.behavior != BotBehavior.LLM_AI or not self.llm_ai:
            # LLM AI가 아니면 기본 공격
            return {"type": "brv_attack", "target_index": 0}

        try:
            from src.multiplayer.llm_player_bot import GameStateConverter
            from src.combat.bot_action import BotActionType

            combat_state = GameStateConverter.from_combat_manager(combat_manager, current_char, self.inventory)
            bot = self.llm_ai.create_combat_bot(current_char)
            action = bot.decide_combat_action(combat_state)

            action_name = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)
            self.logger.debug(f"봇 {self.bot_name} 전투 행동: {action_name}")

            # BotActionType을 문자열로 변환
            action_type = action_name if isinstance(action_name, str) else action.action_type.value

            return {
                "type": action_type,
                "target_index": action.target_index if hasattr(action, 'target_index') else 0,
                "skill_id": action.skill_id if hasattr(action, 'skill_id') else None
            }
        except Exception as e:
            self.logger.warning(f"전투 AI 행동 결정 오류: {e}")
            return {"type": "brv_attack", "target_index": 0}
    
    def shutdown(self):
        """봇 종료 및 리소스 정리"""
        self.stop()
        if self.llm_ai:
            try:
                self.llm_ai.shutdown()
            except:
                pass
            self.llm_ai = None

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
    
    def add_llm_ai_bot(
        self,
        bot_id: str,
        bot_name: str,
        party: List[Any] = None,
        inventory: Any = None
    ) -> AIBot:
        """
        LLM AI 봇 추가 (간편 메서드)
        
        Args:
            bot_id: 봇 ID
            bot_name: 봇 이름
            party: 봇이 조종할 파티
            inventory: 인벤토리
            
        Returns:
            생성된 봇 객체
        """
        bot = self.add_bot(bot_id, bot_name, BotBehavior.LLM_AI)
        if party:
            bot.set_party(party)
        if inventory:
            bot.set_inventory(inventory)
        return bot
    
    def shutdown_all(self):
        """모든 봇 종료 및 리소스 정리"""
        for bot in self.bots.values():
            bot.shutdown()
        self.bots.clear()
        self.is_running = False
        self.logger.info("모든 봇 종료 및 정리 완료")

