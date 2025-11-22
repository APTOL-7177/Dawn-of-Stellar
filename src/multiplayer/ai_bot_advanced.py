"""
고급 AI 봇 시스템 - 멀티플레이어 테스트 및 자동 플레이어

실제 게임 파일을 사용하여 멀티플레이어 테스트를 수행하는 고급 AI 봇입니다.
- 캐릭터 자동 선택
- 자동 특성 선택
- 호스트 자동 패시브 선택
- 자동 전투
- 난이도 선택 (항상 보통)
- 개선된 탐험 AI
- 명령 시스템 (숫자 키)
- 전투 회피 로직
- 플레이어 부족 시 자동 봇 채우기
"""

import time
import random
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.session import MultiplayerSession
from src.core.logger import get_logger
from src.persistence.meta_progress import get_meta_progress
from src.multiplayer.bot_communication import get_communication_network
from src.multiplayer.bot_tasks import TaskQueue, TaskType, BotTask
from src.core.event_bus import event_bus, Events


class BotBehavior(Enum):
    """봇 행동 패턴"""
    PASSIVE = "passive"
    EXPLORER = "explorer"
    AGGRESSIVE = "aggressive"
    FOLLOW = "follow"
    RANDOM = "random"
    SUPPORT = "support"  # 서포터 (다른 플레이어 지원)


class BotCommand(Enum):
    """봇 명령 타입"""
    HELP_REQUEST = "help_request"  # 도움 요청
    SHOW_INVENTORY = "show_inventory"  # 인벤토리 보기 (ITEM_CHECK 대체)
    ITEM_REQUEST = "item_request"  # 아이템 요청
    GOLD_REQUEST = "gold_request"  # 골드 요청
    EXPLORATION_REQUEST = "exploration_request"  # 탐험 요청
    FOLLOW_PLAYER = "follow_player"  # 플레이어 따라가기
    AVOID_COMBAT = "avoid_combat"  # 전투 회피
    
    # New Commands
    FARM_AND_FOLLOW = "farm_and_follow"      # 따라가면서 파밍
    GATHER_RESOURCES = "gather_resources"     # 주변 자원 수집
    GOTO_AND_FARM = "goto_and_farm"        # 특정 위치로 이동하며 파밍
    SHARE_LOCATION = "share_location"       # 현재 위치 공유
    GOTO_SHARED_LOCATION = "goto_shared_location" # 공유된 위치로 이동
    DISTRIBUTE_ITEMS = "distribute_items"     # 아이템 분배
    HOLD_POSITION = "hold_position"        # 현재 위치 대기
    SCOUT_AREA = "scout_area"          # 주변 정찰


class FarmingBehavior:
    """파밍 행동 모듈"""
    
    def __init__(self, bot):
        self.bot = bot
        self.farming_priority = {
            "equipment": 10,      # 장비 최우선
            "ingredient": 8,      # 재료
            "consumable": 6,      # 소비품
            "gold": 5,            # 골드
            "cooking_item": 7     # 요리 재료
        }
        self.communication = get_communication_network()
    
    def should_farm(self, nearby_objects: List[Any]) -> bool:
        """파밍 여부 결정"""
        # 인벤토리 공간 확인
        if self.bot.bot_inventory.weight >= self.bot.bot_inventory.capacity:
            return False
        
        # 가치있는 아이템이 있는지 확인
        valuable_items = self._filter_valuable(nearby_objects)
        return len(valuable_items) > 0
    
    def _filter_valuable(self, objects: List[Any]) -> List[Any]:
        """가치있는 아이템 필터링 (인벤토리 상태와 아이템 등급 고려)"""
        valuable = []
        
        # 인벤토리 여유 공간 계산
        if hasattr(self.bot, 'bot_inventory'):
            current_weight = self.bot.bot_inventory.weight
            max_weight = self.bot.bot_inventory.capacity
            free_weight = max_weight - current_weight
            is_critical_space = free_weight < (max_weight * 0.1) # 10% 미만
        else:
            is_critical_space = False
        
        for obj in objects:
            # 아이템 가치 평가
            item_value = 0
            item_rarity = "common"
            
            # 아이템 속성 확인 (객체 구조에 따라 다를 수 있음)
            if hasattr(obj, 'rarity'):
                item_rarity = obj.rarity
            if hasattr(obj, 'type'):
                if obj.type == 'equipment':
                    item_value += 50
                elif obj.type == 'consumable':
                    item_value += 20
                elif obj.type == 'ingredient':
                    item_value += 10
            
            # 등급별 가점
            rarity_scores = {'legendary': 100, 'epic': 80, 'rare': 50, 'uncommon': 20, 'common': 0}
            item_value += rarity_scores.get(item_rarity, 0)
            
            # 공간이 부족할 때는 가치 있는 것만
            if is_critical_space:
                if item_value < 50: # 장비나 레어 이상만
                    continue
            
            valuable.append(obj)
            
        return valuable
    
    def get_farming_target(self, nearby_objects: List[Any]) -> Optional[Any]:
        """가장 우선순위 높은 파밍 대상 반환"""
        if not nearby_objects:
            return None
            
        # 가치 평가 점수가 높은 순으로 정렬
        def calculate_score(obj):
            score = 0
            if hasattr(obj, 'type'):
                score += self.farming_priority.get(obj.type, 0) * 10
            if hasattr(obj, 'rarity'):
                rarity_scores = {'legendary': 100, 'epic': 80, 'rare': 50, 'uncommon': 20, 'common': 0}
                score += rarity_scores.get(obj.rarity, 0)
            # 거리 페널티는 별도로 계산해야 하지만 여기선 생략
            return score

        return max(nearby_objects, key=calculate_score, default=nearby_objects[0])




@dataclass
class BotPartySetup:
    """봇 파티 설정"""
    selected_jobs: List[str] = None
    selected_traits: Dict[str, List[str]] = None  # {job_id: [trait_ids]}
    selected_passives: List[str] = None
    difficulty: str = "normal"
    
    def __post_init__(self):
        if self.selected_jobs is None:
            self.selected_jobs = []
        if self.selected_traits is None:
            self.selected_traits = {}
        if self.selected_passives is None:
            self.selected_passives = []


class AdvancedAIBot:
    """고급 AI 봇 클래스"""
    
    def __init__(
        self,
        bot_id: str,
        bot_name: str,
        network_manager: NetworkManager,
        session: MultiplayerSession,
        behavior: BotBehavior = BotBehavior.EXPLORER,
        is_host: bool = False
    ):
        """
        고급 AI 봇 초기화
        
        Args:
            bot_id: 봇 ID
            bot_name: 봇 이름
            network_manager: 네트워크 관리자
            session: 멀티플레이 세션
            behavior: 봇 행동 패턴
            is_host: 호스트 여부
        """
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.network_manager = network_manager
        self.session = session
        self.behavior = behavior
        self.is_host = is_host
        self.logger = get_logger("multiplayer.ai_bot_advanced")
        
        # 봇 상태
        self.is_active = False
        self.current_x = 0
        self.current_y = 0
        self.last_action_time = 0.0
        self.action_interval = 0.3  # 0.3초 간격으로 액션 (더 빠른 반응)
        
        # 파티 설정
        self.party_setup = BotPartySetup()
        self.character_allocation = 1  # 기본 1명
        
        # 탐험 상태
        self.explored_positions: Set[Tuple[int, int]] = set()
        self.target_position: Optional[Tuple[int, int]] = None
        self.path_to_target: List[Tuple[int, int]] = []  # 목표까지의 경로
        self.last_direction = (0, 0)
        self.nearby_players: Dict[str, Tuple[int, int]] = {}  # {player_id: (x, y)}
        self.nearby_enemies: List[Tuple[int, int]] = []  # [(x, y), ...]
        
        # 전투 회피
        self.avoid_combat_radius = 5  # 다른 플레이어와 이 거리 이상 떨어져 있으면 전투 회피
        self.combat_avoidance_active = False
        
        # 명령 시스템
        self.pending_commands: List[BotCommand] = []
        self.command_cooldown: Dict[BotCommand, float] = {}
        
        # 자동 전투 상태
        self.in_combat = False
        self.combat_state: Optional[Dict[str, Any]] = None
        self.combat_manager: Optional[Any] = None  # 전투 관리자 참조
        self.combat_ui: Optional[Any] = None  # 전투 UI 참조
        self.current_combat_actor: Optional[Any] = None  # 현재 전투 행동자
        
        # 전투 트리거 (적 충돌 시)
        self.pending_combat_trigger: Optional[Dict[str, Any]] = None  # 전투 트리거 정보 (적 충돌 시)
        
        # 난이도 설정 (봇은 항상 보통)
        self.difficulty = "normal"  # 항상 보통
        
        # 봇 인벤토리 (무게 기반, 플레이어와 완전 분리)
        from src.equipment.inventory import Inventory
        self.bot_inventory = Inventory(base_weight=5.0, party=[])  # 5kg 기본 무게
        
        # 자동 관리 설정
        self.auto_equip_enabled = True
        self.equip_check_interval = 10.0  # 10초마다 체크
        self.last_equip_check_time = 0.0
        
        self.auto_use_items = True
        self.hp_use_threshold = 0.3  # HP 30% 이하면 사용
        self.mp_use_threshold = 0.2  # MP 20% 이하면 사용
        
        self.auto_cook_enabled = True
        self.auto_cleanup_inventory = True
        self.min_free_weight_percent = 0.3  # 30% 여유 유지
        
        # 메시지 핸들러 등록
        self._register_handlers()
        
        # 직업/특성/패시브 데이터 로드
        self._load_game_data()
        
        # New AI Components
        self.communication = get_communication_network()
        self.farming = FarmingBehavior(self)
        self.task_queue = TaskQueue()
        
        # Mode
        self.current_mode = "simple"
        
        # 파티 정보 (다른 플레이어 직업)
        self.other_player_jobs: Dict[str, str] = {}  # {player_id: job_id}
        
        # 이미 수집한 아이템 블랙리스트 (중복 파밍 방지)
        self.harvested_blacklist: Set[Any] = set()  # (x, y) or item_id
        self.blacklist_clear_time = 0.0
        
        # 상호작용 상태 관리 (Z키 3번 누르기 시퀀스 등)
        self.interaction_state = {
            "active": False,
            "target_pos": None,
            "step": 0,
            "last_step_time": 0.0
        }


    
    def _load_game_data(self):
        """게임 데이터 로드"""
        # 직업 데이터 로드
        jobs_path = Path("data/characters")
        self.available_jobs: List[Dict[str, Any]] = []
        if jobs_path.exists():
            for job_file in jobs_path.glob("*.yaml"):
                try:
                    with open(job_file, 'r', encoding='utf-8') as f:
                        job_data = yaml.safe_load(f)
                        if job_data:
                            job_id = job_file.stem
                            job_data['id'] = job_id
                            # 봇은 모든 직업이 해금된 것으로 처리
                            job_data['unlocked'] = True
                            self.available_jobs.append(job_data)
                except Exception as e:
                    self.logger.warning(f"직업 파일 로드 실패: {job_file} - {e}")
        
        # 패시브 데이터 로드
        passives_path = Path("data/passives.yaml")
        self.available_passives: List[Dict[str, Any]] = []
        if passives_path.exists():
            try:
                with open(passives_path, 'r', encoding='utf-8') as f:
                    passives_data = yaml.safe_load(f)
                    if passives_data and 'passives' in passives_data:
                        # 봇은 모든 패시브가 해금된 것으로 처리
                        for passive in passives_data['passives']:
                            passive['unlocked'] = True
                            passive['purchased'] = True
                        self.available_passives = passives_data['passives']
            except Exception as e:
                self.logger.warning(f"패시브 파일 로드 실패: {e}")
        
        # 특성 데이터 로드 (모든 직업의 모든 특성 해금)
        self.available_traits: Dict[str, List[Dict[str, Any]]] = {}
        for job_data in self.available_jobs:
            job_id = job_data.get('id', '')
            traits = job_data.get('traits', [])
            # 모든 특성을 해금된 것으로 처리
            for trait in traits:
                trait['unlocked'] = True
            self.available_traits[job_id] = traits
        
        self.logger.info(f"게임 데이터 로드 완료: 직업 {len(self.available_jobs)}개, 패시브 {len(self.available_passives)}개 (모두 해금됨)")
    
    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        self.network_manager.register_handler(
            MessageType.PLAYER_MOVE,
            self._handle_player_move
        )
        self.network_manager.register_handler(
            MessageType.GAME_START,
            self._handle_game_start
        )
        self.network_manager.register_handler(
            MessageType.TURN_CHANGED,
            self._handle_turn_changed
        )
        self.network_manager.register_handler(
            MessageType.JOB_SELECTED,
            self._handle_job_selected
        )
        self.network_manager.register_handler(
            MessageType.COMBAT_START,
            self._handle_combat_start
        )
    
    def _handle_player_move(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """플레이어 이동 메시지 처리"""
        if sender_id == self.bot_id:
            return
        
        player_id = message.data.get("player_id") or sender_id
        if player_id and player_id != self.bot_id:
            x = message.data.get("x", 0)
            y = message.data.get("y", 0)
            self.nearby_players[player_id] = (x, y)
            
            # FOLLOW 패턴인 경우 타겟 업데이트
            if self.behavior == BotBehavior.FOLLOW and not self.target_position:
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
    
    def _handle_turn_changed(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """턴 변경 메시지 처리"""
        current_player_id = message.data.get("current_player_id")
        if current_player_id == self.bot_id:
            # 자신의 턴이면 자동으로 직업 선택
            self._auto_select_job()
    
    def _handle_job_selected(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """직업 선택 메시지 처리"""
        job_id = message.data.get("job_id")
        player_id = message.data.get("player_id")
        if job_id and player_id != self.bot_id:
            # 다른 플레이어가 선택한 직업 기록
            self.logger.info(f"다른 플레이어 {player_id}가 직업 선택: {job_id}")
            
            # 로컬 상태에 저장
            self.other_player_jobs[player_id] = job_id
            
            # 파티 구성 정보 업데이트 (나중에 역할 분담에 사용)
            if self.session and player_id in self.session.players:
                 # 세션 객체의 플레이어 정보에도 업데이트 (선택 사항)
                 pass

    def _auto_select_job(self):
        """자동 직업 선택 (턴 변경 시 호출)"""
        if not self.available_jobs:
            return

        # 이미 선택했으면 스킵
        if self.party_setup.selected_jobs:
            return
            
        # 파티 밸런스 고려하여 직업 선택
        selected_job = self._choose_balanced_job()
        
        # 직업 선택 메시지 전송
        try:
            msg = MessageBuilder.job_select(self.bot_id, selected_job['id'])
            if not self.network_manager.is_host:
                self.network_manager.send(msg)
            else:
                self.network_manager.broadcast(msg)
            
            # 로컬 상태 업데이트
            self.party_setup.selected_jobs = [selected_job['id']]
            self.logger.info(f"봇 {self.bot_name} 직업 선택 완료: {selected_job['id']}")
            
            # 채팅으로 역할 알림
            role_msg = "전투에 참여합니다!"
            job_id = selected_job['id'].lower()
            if any(x in job_id for x in ["knight", "paladin", "warrior", "tank"]):
                role_msg = "제가 앞장서겠습니다! (Tank)"
            elif any(x in job_id for x in ["priest", "healer", "cleric", "druid"]):
                role_msg = "치유는 제게 맡기세요. (Healer)"
            elif any(x in job_id for x in ["archer", "mage", "wizard", "rogue"]):
                role_msg = "뒤에서 지원하겠습니다. (DPS)"
                
            self._send_chat_message(f"{self.bot_name}: {role_msg}")
            
        except Exception as e:
            self.logger.error(f"직업 선택 메시지 전송 실패: {e}")

    def _choose_balanced_job(self) -> Dict[str, Any]:
        """파티 밸런스를 고려한 직업 선택"""
        # 현재 파티의 직업 구성 확인
        current_roles = {"tank": 0, "healer": 0, "dps": 0}
        
        # 다른 플레이어들의 직업 확인
        for pid, job_id in self.other_player_jobs.items():
            job_lower = job_id.lower()
            if any(x in job_lower for x in ["knight", "paladin", "tank", "guardian"]):
                current_roles["tank"] += 1
            elif any(x in job_lower for x in ["priest", "healer", "cleric", "druid", "bard", "shaman"]):
                current_roles["healer"] += 1
            else:
                current_roles["dps"] += 1
        
        # 필요한 역할 파악 (Tank 1, Healer 1, 나머지 DPS 가정)
        needed_role = "dps"
        if current_roles["tank"] == 0:
            needed_role = "tank"
        elif current_roles["healer"] == 0:
            needed_role = "healer"
            
        # 해당 역할군의 직업 후보군 추출
        candidates = []
        for job in self.available_jobs:
            job_id = job.get('id', '').lower()
            is_tank = any(x in job_id for x in ["knight", "paladin", "tank", "guardian", "warrior"])
            is_healer = any(x in job_id for x in ["priest", "healer", "cleric", "druid", "bard", "shaman", "alchemist"])
            
            if needed_role == "tank" and is_tank:
                candidates.append(job)
            elif needed_role == "healer" and is_healer:
                candidates.append(job)
            elif needed_role == "dps" and not is_tank and not is_healer:
                candidates.append(job)
                
        # 후보가 없으면 전체에서 랜덤 선택
        if not candidates:
            candidates = self.available_jobs
            
        import random
        return random.choice(candidates)

    def _handle_combat_start(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """전투 시작 메시지 처리"""
        self.in_combat = True
        self.combat_state = message.data
        self.logger.info(f"봇 {self.bot_name} 전투 시작")
    
    def set_combat_manager(self, combat_manager: Any, combat_ui: Any = None):
        """
        전투 관리자 설정 (전투 중 자동 액션 선택용)
        
        Args:
            combat_manager: 전투 관리자
            combat_ui: 전투 UI (선택적)
        """
        self.combat_manager = combat_manager
        self.combat_ui = combat_ui
    
    def _check_job_gimmick(self, actor: Any) -> Dict[str, Any]:
        """직업별 기믹 상태 확인"""
        # 직업 ID 확인
        job_id = actor.job_id if hasattr(actor, 'job_id') else "unknown"
        gimmick_info = {"ready": False, "type": "none", "value": 0}
        
        # 기믹 데이터 확인 (gimmick_manager 또는 status_effects)
        # 여기서는 일반화된 로직으로 가정
        if hasattr(actor, 'gimmick_value'):
            gimmick_info["value"] = actor.gimmick_value
            
            # 직업별 임계값 체크
            if "berserker" in job_id.lower() or "warrior" in job_id.lower():
                # 분노 게이지 (50 이상이면 강화 스킬 사용)
                if actor.gimmick_value >= 50:
                    gimmick_info["ready"] = True
                    gimmick_info["type"] = "rage"
                    
            elif "mage" in job_id.lower() or "wizard" in job_id.lower():
                # 마나 스택 (3스택 이상이면 방출)
                if actor.gimmick_value >= 3:
                    gimmick_info["ready"] = True
                    gimmick_info["type"] = "stack"
                    
            elif "rogue" in job_id.lower() or "assassin" in job_id.lower():
                # 연계 점수 (5점이면 마무리 일격)
                if actor.gimmick_value >= 5:
                    gimmick_info["ready"] = True
                    gimmick_info["type"] = "combo"
        
        return gimmick_info

    def auto_combat_action(self, actor: Any, allies: List[Any], enemies: List[Any]) -> Optional[Dict[str, Any]]:
        """
        자동 전투 액션 선택 (개선된 AI)
        
        Args:
            actor: 행동자 캐릭터
            allies: 아군 리스트
            enemies: 적군 리스트
        
        Returns:
            액션 딕셔너리 또는 None
        """
        if not self.combat_manager:
            return None
        
        # 살아있는 적 필터링
        alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
        if not alive_enemies:
            return None
        
        # 살아있는 아군 필터링
        alive_allies = [a for a in allies if getattr(a, 'is_alive', True)]
        
        # 0. 위기 관리 (아이템 사용)
        hp_ratio = actor.current_hp / actor.max_hp if actor.max_hp > 0 else 0
        mp_ratio = actor.current_mp / actor.max_mp if actor.max_mp > 0 else 0
        
        if hp_ratio < 0.3: # HP 30% 미만
             # 포션 찾기 (인벤토리 연동 필요)
             # 실제로는 self.bot_inventory 확인
             recovery_action = self._use_recovery_item(actor, "hp")
             if recovery_action:
                 return recovery_action
        
        if mp_ratio < 0.2: # MP 20% 미만
             recovery_action = self._use_recovery_item(actor, "mp")
             if recovery_action:
                 return recovery_action

    def _use_recovery_item(self, actor: Any, item_type: str) -> Optional[Dict[str, Any]]:
        """회복 아이템 사용"""
        if not hasattr(self, 'bot_inventory'):
            return None
            
        inventory = self.bot_inventory
        if not inventory:
            return None
            
        # 인벤토리에서 회복 아이템 찾기
        # (inventory 구조에 따라 다르지만, 여기서는 아이템 리스트를 순회한다고 가정)
        best_item = None
        best_slot = -1
        
        for i, item in enumerate(inventory.items):
            if not item: continue
            
            # 아이템 속성 확인
            if item_type == "hp" and getattr(item, 'heal_hp', 0) > 0:
                best_item = item
                best_slot = i
                break # 첫 번째 발견한 것 사용 (더 좋은 로직 가능)
            elif item_type == "mp" and getattr(item, 'heal_mp', 0) > 0:
                best_item = item
                best_slot = i
                break
                
        if best_item and best_slot != -1:
            return {
                "type": "item",
                "item_index": best_slot, # 인벤토리 슬롯 인덱스
                "target": actor # 자신에게 사용
            }
            
        return None 
             
        # 위협도 평가 및 전략적 선택
        threat_assessment = self._assess_threats(actor, alive_allies, alive_enemies)
        
        # 1. 아군 보호 우선 (위험한 아군이 있으면 힐)
        critical_allies = threat_assessment.get("critical_allies", [])
        if critical_allies:
            heal_action = self._select_smart_heal_action(actor, critical_allies, alive_allies)
            if heal_action:
                return heal_action

        # 2. 직업 기믹 활용 (필살기/강화 스킬)
        gimmick_info = self._check_job_gimmick(actor)
        if gimmick_info["ready"]:
             # 기믹 소모 스킬 찾기
             gimmick_skill = self._find_gimmick_skill(actor, gimmick_info["type"])
             if gimmick_skill:
                 target = alive_enemies[0] # 기본적으로 가장 가까운/위협적인 적
                 
                 # BREAK 상태인 적이 있으면 우선 타겟팅
                 break_enemies = threat_assessment.get("break_enemies", [])
                 if break_enemies:
                     target = break_enemies[0]
                     
                 return {
                     "type": "skill",
                     "skill_id": gimmick_skill,
                     "target": target
                 }

        # 3. 버프/디버프 스킬 사용 (아군 버프 또는 적 디버프)
        buff_action = self._select_buff_action(actor, alive_allies, alive_enemies)
        if buff_action:
            return buff_action
        
        # 4. 전략적 공격 (위협도가 높은 적 우선, BREAK 상태 활용)
        attack_action = self._select_smart_attack_action(actor, alive_enemies, threat_assessment)
        if attack_action:
            return attack_action
        
        # 5. 기본 공격 (폴백)
        return self._select_basic_attack(actor, alive_enemies)

    def _find_gimmick_skill(self, actor: Any, gimmick_type: str) -> Optional[str]:
        """기믹을 사용하는 스킬 찾기"""
        if not hasattr(actor, 'skill_ids'):
            return None
            
        # 스킬 정보에서 gimmick 관련 태그 확인 (가정)
        for skill_id in actor.skill_ids:
            skill = self._get_skill_info(skill_id)
            if not skill: continue
            
            # 스킬 설명이나 태그에 기믹 관련 내용이 있는지 확인
            # 예: "consumes rage", "finisher", "overload"
            tags = skill.get('tags', [])
            description = skill.get('description', '').lower()
            
            if gimmick_type == "rage" and ("rage" in description or "strong" in tags):
                return skill_id
            elif gimmick_type == "combo" and "finisher" in tags:
                return skill_id
            elif gimmick_type == "stack" and "burst" in tags:
                return skill_id
                
        return None


    
    def _assess_threats(self, actor: Any, allies: List[Any], enemies: List[Any]) -> Dict[str, Any]:
        """위협도 평가"""
        assessment = {
            "critical_allies": [],  # 위험한 아군 (HP 30% 이하)
            "low_hp_allies": [],    # HP가 낮은 아군 (HP 50% 이하)
            "threat_enemies": [],    # 위협적인 적 (높은 공격력 또는 낮은 HP)
            "break_enemies": []     # BREAK 상태인 적
        }
        
        # 아군 평가
        for ally in allies:
            if not hasattr(ally, 'current_hp') or not hasattr(ally, 'max_hp'):
                continue
            
            hp_ratio = ally.current_hp / ally.max_hp if ally.max_hp > 0 else 0
            
            if hp_ratio <= 0.3:
                assessment["critical_allies"].append((ally, hp_ratio))
            elif hp_ratio <= 0.5:
                assessment["low_hp_allies"].append((ally, hp_ratio))
        
        # 적 평가
        for enemy in enemies:
            # BREAK 상태 확인
            if hasattr(enemy, 'current_brv') and hasattr(enemy, 'max_brv'):
                if enemy.current_brv <= 0:
                    assessment["break_enemies"].append(enemy)
            
            # 위협도 계산 (공격력 + 낮은 HP = 높은 위협도)
            threat_score = 0
            if hasattr(enemy, 'stats'):
                # 공격력 추정 (strength 또는 magic 중 높은 값)
                atk = max(
                    getattr(enemy.stats, 'STRENGTH', 0),
                    getattr(enemy.stats, 'MAGIC', 0)
                )
                threat_score += atk
            
            if hasattr(enemy, 'current_hp') and hasattr(enemy, 'max_hp'):
                hp_ratio = enemy.current_hp / enemy.max_hp if enemy.max_hp > 0 else 0
                # 낮은 HP = 높은 위협도 (빨리 처치 가능)
                threat_score += (1.0 - hp_ratio) * 100
            
            assessment["threat_enemies"].append((enemy, threat_score))
        
        # 위협도 순으로 정렬
        assessment["threat_enemies"].sort(key=lambda x: x[1], reverse=True)
        assessment["critical_allies"].sort(key=lambda x: x[1])  # HP가 낮을수록 우선
        
        return assessment
    
    def _select_smart_heal_action(self, actor: Any, critical_allies: List[Any], all_allies: List[Any]) -> Optional[Dict[str, Any]]:
        """지능적인 힐 액션 선택"""
        if not hasattr(actor, 'skill_ids') or not actor.skill_ids:
            return None
        
        # MP 확인
        current_mp = getattr(actor, 'current_mp', 0)
        
        # 힐 스킬 찾기
        heal_skills = []
        for skill_id in actor.skill_ids:
            skill = self._get_skill_info(skill_id)
            if not skill:
                continue
            
            # 힐 스킬 확인
            if (skill.get('heal_amount', 0) > 0 or 
                'heal' in skill_id.lower() or 
                'cure' in skill_id.lower() or
                skill.get('target_type') == 'single_ally' or
                skill.get('target_type') == 'all_allies'):
                
                mp_cost = skill.get('mp_cost', 0)
                if current_mp >= mp_cost:
                    heal_skills.append((skill_id, skill))
        
        if not heal_skills:
            return None
        
        # 가장 효과적인 힐 스킬 선택 (회복량이 큰 것 우선)
        best_skill = None
        best_heal = 0
        
        for skill_id, skill in heal_skills:
            heal_amount = skill.get('heal_amount', 0)
            if heal_amount > best_heal:
                best_skill = (skill_id, skill)
                best_heal = heal_amount
        
        if not best_skill:
            # 회복량 정보가 없으면 첫 번째 힐 스킬 사용
            best_skill = (heal_skills[0][0], heal_skills[0][1])
        
        skill_id, skill = best_skill
        
        # 타겟 선택 (가장 위험한 아군)
        if critical_allies:
            target = critical_allies[0][0]  # 가장 위험한 아군
        else:
            # 전체 힐 스킬인 경우 타겟 불필요
            target = None
        
        # 전체 힐 스킬인 경우
        if skill.get('target_type') == 'all_allies':
            return {
                "type": "skill",
                "skill_id": skill_id,
                "target": None  # 전체 타겟
            }
        
        return {
            "type": "skill",
            "skill_id": skill_id,
            "target": target
        }
    
    def _select_buff_action(self, actor: Any, allies: List[Any], enemies: List[Any]) -> Optional[Dict[str, Any]]:
        """버프/디버프 액션 선택"""
        if not hasattr(actor, 'skill_ids') or not actor.skill_ids:
            return None
        
        current_mp = getattr(actor, 'current_mp', 0)
        
        # 버프/디버프 스킬 찾기
        buff_skills = []
        for skill_id in actor.skill_ids:
            skill = self._get_skill_info(skill_id)
            if not skill:
                continue
            
            # 버프/디버프 확인
            has_buff = bool(skill.get('buff_stats', {}))
            has_debuff = bool(skill.get('debuff_stats', {}))
            
            if has_buff or has_debuff:
                mp_cost = skill.get('mp_cost', 0)
                if current_mp >= mp_cost:
                    buff_skills.append((skill_id, skill, has_buff, has_debuff))
        
        if not buff_skills:
            return None
        
        # 버프/디버프 스킬 사용 확률 (30%로 증가)
        if random.random() < 0.3:
            skill_id, skill, has_buff, has_debuff = random.choice(buff_skills)
            
            # 타겟 선택
            target = None
            if has_buff:
                # 아군 버프: 가장 약한 아군
                weak_ally = min(
                    allies,
                    key=lambda a: getattr(a, 'current_hp', 999) if hasattr(a, 'current_hp') else 999
                )
                target = weak_ally
            elif has_debuff:
                # 적 디버프: 가장 강한 적
                strong_enemy = max(
                    enemies,
                    key=lambda e: getattr(e, 'current_hp', 0) if hasattr(e, 'current_hp') else 0
                )
                target = strong_enemy
            
            return {
                "type": "skill",
                "skill_id": skill_id,
                "target": target
            }
        
        return None
    
    def _select_smart_attack_action(self, actor: Any, enemies: List[Any], threat_assessment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """지능적인 공격 액션 선택"""
        if not hasattr(actor, 'skill_ids') or not actor.skill_ids:
            return None
        
        current_mp = getattr(actor, 'current_mp', 0)
        
        # BREAK 상태인 적이 있으면 우선 공격 (마무리)
        break_enemies = threat_assessment.get("break_enemies", [])
        if break_enemies:
            target = break_enemies[0]
            # HP 공격 스킬 우선 사용
            hp_attack_skill = self._find_hp_attack_skill(actor, current_mp)
            if hp_attack_skill:
                return {
                    "type": "skill",
                    "skill_id": hp_attack_skill,
                    "target": target
                }
        
        # 위협도가 높은 적 선택
        threat_enemies = threat_assessment.get("threat_enemies", [])
        if threat_enemies:
            target = threat_enemies[0][0]  # 가장 위협적인 적
        else:
            # 위협도 평가 실패 시 가장 약한 적
            target = min(
                enemies,
                key=lambda e: getattr(e, 'current_hp', 999) if hasattr(e, 'current_hp') else 999
            )
        
        # 스킬 사용 확률 (행동 패턴에 따라)
        skill_probability = 0.6  # 기본 확률 증가 (30% -> 60%)
        if self.behavior == BotBehavior.AGGRESSIVE:
            skill_probability = 0.7  # 공격적 봇은 더 자주 스킬 사용 (50% -> 70%)
        elif self.behavior == BotBehavior.SUPPORT:
            skill_probability = 0.5  # 서포터도 더 자주 스킬 사용 (20% -> 50%)
        
        # 기믹 상태에 따른 스킬 강화 (추가)
        gimmick_info = self._check_job_gimmick(actor)
        if gimmick_info["ready"]:
            skill_probability = 0.9 # 기믹이 준비되면 스킬 사용 확률 대폭 증가
            
        if random.random() < skill_probability:
            # 가장 효과적인 공격 스킬 선택
            best_skill = self._find_best_attack_skill(actor, target, current_mp)
            if best_skill:
                return {
                    "type": "skill",
                    "skill_id": best_skill,
                    "target": target
                }
        
        # 기본 공격 - 직업의 기본 공격 스킬 사용
        return self._select_job_basic_attack(actor, target)
    
    def _select_basic_attack(self, actor: Any, enemies: List[Any]) -> Dict[str, Any]:
        """기본 공격 선택"""
        # 가장 약한 적 선택
        target = min(
            enemies,
            key=lambda e: getattr(e, 'current_hp', 999) if hasattr(e, 'current_hp') else 999
        )
        
        # 직업의 기본 공격 스킬 사용
        return self._select_job_basic_attack(actor, target)
    
    def _select_job_basic_attack(self, actor: Any, target: Any) -> Dict[str, Any]:
        """직업의 기본 공격 스킬 선택"""
        # actor의 skill_ids에서 기본 공격 스킬 찾기
        if hasattr(actor, 'skill_ids') and actor.skill_ids:
            # 첫 번째 스킬 = 기본 BRV 공격
            # 두 번째 스킬 = 기본 HP 공격
            brv_skill_id = actor.skill_ids[0] if len(actor.skill_ids) > 0 else None
            hp_skill_id = actor.skill_ids[1] if len(actor.skill_ids) > 1 else None
            
            # BREAK 상태인 적이면 HP 공격 스킬 사용
            if hp_skill_id:
                if hasattr(target, 'current_brv') and hasattr(target, 'max_brv'):
                    if target.current_brv <= 0:
                        # BREAK 상태이면 HP 공격 스킬 사용
                        return {
                            "type": "skill",
                            "skill_id": hp_skill_id,
                            "target": target
                        }
            
            # 기본적으로 BRV 공격 스킬 사용
            if brv_skill_id:
                return {
                    "type": "skill",
                    "skill_id": brv_skill_id,
                    "target": target
                }
        
        # 폴백: 스킬이 없으면 기본 BRV 공격
        return {
            "type": "brv_attack",
            "target": target
        }
    
    def _get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """스킬 정보 가져오기"""
        if not self.combat_manager:
            return None
        
        try:
            skill_manager = getattr(self.combat_manager, 'skill_manager', None)
            if skill_manager:
                skill = skill_manager.get_skill(skill_id)
                if skill:
                    return {
                        'heal_amount': getattr(skill, 'heal_amount', 0),
                        'mp_cost': getattr(skill, 'mp_cost', 0),
                        'target_type': getattr(skill, 'target_type', None),
                        'buff_stats': getattr(skill, 'buff_stats', {}),
                        'debuff_stats': getattr(skill, 'debuff_stats', {}),
                        'brv_multiplier': getattr(skill, 'brv_multiplier', 1.0),
                        'hp_attack': getattr(skill, 'hp_attack', False)
                    }
        except Exception as e:
            self.logger.debug(f"스킬 정보 가져오기 실패: {skill_id}, {e}")
        
        return None
    
    def _find_hp_attack_skill(self, actor: Any, current_mp: int) -> Optional[str]:
        """HP 공격 스킬 찾기"""
        if not hasattr(actor, 'skill_ids') or not actor.skill_ids:
            return None
        
        for skill_id in actor.skill_ids:
            skill = self._get_skill_info(skill_id)
            if skill and skill.get('hp_attack', False):
                if current_mp >= skill.get('mp_cost', 0):
                    return skill_id
        
        return None
    
    def _find_best_attack_skill(self, actor: Any, target: Any, current_mp: int) -> Optional[str]:
        """가장 효과적인 공격 스킬 찾기"""
        if not hasattr(actor, 'skill_ids') or not actor.skill_ids:
            return None
        
        best_skill = None
        best_score = 0
        
        for skill_id in actor.skill_ids:
            skill = self._get_skill_info(skill_id)
            if not skill:
                continue
            
            mp_cost = skill.get('mp_cost', 0)
            if current_mp < mp_cost:
                continue
            
            # 스킬 점수 계산 (데미지 배율 + HP 공격 보너스)
            score = skill.get('brv_multiplier', 1.0)
            if skill.get('hp_attack', False):
                score += 2.0  # HP 공격은 높은 우선순위
            
            # BREAK 상태인 적이면 HP 공격 스킬 우선
            if hasattr(target, 'current_brv') and target.current_brv <= 0:
                if skill.get('hp_attack', False):
                    score += 5.0
            
            if score > best_score:
                best_score = score
                best_skill = skill_id
        
        return best_skill
    
    def auto_select_job(self, available_jobs: List[str], selected_by_others: Set[str]) -> Optional[str]:
        """
        직업 자동 선택 (봇은 모든 직업이 해금된 것으로 처리)
        
        Args:
            available_jobs: 선택 가능한 직업 ID 리스트 (봇은 모든 직업 사용 가능)
            selected_by_others: 다른 플레이어가 선택한 직업 ID 집합
        
        Returns:
            선택한 직업 ID 또는 None
        """
        # 봇은 모든 직업을 사용할 수 있음 (개발 모드와 동일)
        all_job_ids = [job.get('id', '') for job in self.available_jobs if job.get('id')]
        
        # 다른 플레이어가 선택하지 않은 직업만 필터링
        available = [job for job in all_job_ids if job not in selected_by_others]
        
        if not available:
            # 모든 직업이 선택됨: 랜덤 선택
            available = all_job_ids
        
        # 행동 패턴에 따라 직업 선택
        if self.behavior == BotBehavior.AGGRESSIVE:
            # 공격적: 물리 딜러 우선
            preferred = ["warrior", "knight", "berserker", "assassin", "archer", "gladiator", "samurai"]
        elif self.behavior == BotBehavior.SUPPORT:
            # 서포터: 힐러/서포터 우선
            preferred = ["cleric", "priest", "druid", "bard", "shaman", "alchemist"]
        else:
            # 기본: 밸런스 있는 파티 구성
            preferred = ["warrior", "archmage", "cleric", "archer", "rogue", "knight"]
        
        # 선호 직업 중 선택 가능한 것 찾기
        for job in preferred:
            if job in available:
                return job
        
        # 선호 직업이 없으면 랜덤 선택
        return random.choice(available) if available else None
    
    def auto_select_traits(self, job_id: str, available_traits: List[str] = None) -> List[str]:
        """
        특성 자동 선택 (봇은 모든 특성이 해금된 것으로 처리)
        
        Args:
            job_id: 직업 ID
            available_traits: 선택 가능한 특성 ID 리스트 (None이면 모든 특성 사용)
        
        Returns:
            선택한 특성 ID 리스트 (최대 2개)
        """
        # 봇은 모든 특성을 사용할 수 있음 (개발 모드와 동일)
        if available_traits is None:
            # 직업의 모든 특성 가져오기
            job_traits = self.available_traits.get(job_id, [])
            available_traits = [trait.get('id', '') for trait in job_traits if trait.get('id')]
        
        if len(available_traits) <= 2:
            return available_traits
        
        # 랜덤으로 2개 선택
        return random.sample(available_traits, 2)
    
    def auto_select_passives(self, available_passives: List[Dict[str, Any]] = None, max_cost: int = 10) -> List[str]:
        """
        패시브 자동 선택 (호스트만, 봇은 모든 패시브가 해금된 것으로 처리)
        
        Args:
            available_passives: 선택 가능한 패시브 리스트 (None이면 모든 패시브 사용)
            max_cost: 최대 코스트
        
        Returns:
            선택한 패시브 ID 리스트
        """
        if not self.is_host:
            return []
        
        # 봇은 모든 패시브를 사용할 수 있음 (개발 모드와 동일)
        if available_passives is None:
            available_passives = self.available_passives
        
        # 모든 패시브가 해금된 것으로 처리
        unlocked = available_passives
        
        if not unlocked:
            return []
        
        # 코스트 효율이 좋은 패시브 우선 선택
        # 코스트 2 패시브 우선
        cost_2_passives = [p for p in unlocked if p.get("cost", 999) == 2]
        cost_3_passives = [p for p in unlocked if p.get("cost", 999) == 3]
        cost_4_passives = [p for p in unlocked if p.get("cost", 999) == 4]
        cost_5_passives = [p for p in unlocked if p.get("cost", 999) == 5]
        
        selected = []
        total_cost = 0
        
        # 코스트 2 패시브 2개 선택 (총 4 코스트)
        for p in cost_2_passives[:2]:
            if total_cost + p.get("cost", 0) <= max_cost:
                selected.append(p["id"])
                total_cost += p.get("cost", 0)
        
        # 남은 코스트로 추가 패시브 선택
        remaining = max_cost - total_cost
        if remaining >= 3:
            for p in cost_3_passives:
                if total_cost + p.get("cost", 0) <= max_cost:
                    selected.append(p["id"])
                    total_cost += p.get("cost", 0)
                    break
        
        return selected
    
    
    def _check_nearby_players(self) -> bool:
        """주변에 다른 플레이어가 있는지 확인"""
        if not self.nearby_players:
            return False
        
        for player_id, (px, py) in self.nearby_players.items():
            distance = abs(px - self.current_x) + abs(py - self.current_y)
            if distance <= self.avoid_combat_radius:
                return True
        
        return False
    
    def _should_avoid_combat(self) -> bool:
        """전투 회피 여부 결정"""
        # 명령으로 전투 회피 모드가 활성화되어 있으면 전투 회피
        if self.combat_avoidance_active:
            return True
        
        # 다른 플레이어와 떨어져 있으면 전투 회피 (기본 동작)
        if not self._check_nearby_players():
            return True
        
        return False
    
    
    def _get_bot_inventory(self) -> Optional[Any]:
        """
        봇 인벤토리 가져오기
        
        Returns:
            봇의 인벤토리 객체 (Inventory)
        """
        return self.bot_inventory
    
    def _score_equipment(self, equip: Any, character: Any = None) -> float:
        """
        장비 점수 계산 (높을수록 좋음)
        
        고려 사항:
        - 장비 등급 (Common < Uncommon < Rare < Epic < Legendary < Unique)
        - 스탯 보너스 총합
        - 레벨 요구사항 vs 캐릭터 레벨
        - 직업 적합성 (물리 vs 마법)
        
        Args:
            equip: Equipment 객체
            character: 착용할 캐릭터 (None이면 일반 점수)
        
        Returns:
            장비 점수 (0~10000)
        """
        from src.equipment.item_system import Equipment, ItemRarity
        
        if not isinstance(equip, Equipment):
            return 0.0
        
        score = 0.0
        
        # 1. 등급 점수 (0~1000)
        rarity_scores = {
            ItemRarity.COMMON: 100,
            ItemRarity.UNCOMMON: 250,
            ItemRarity.RARE: 500,
            ItemRarity.EPIC: 800,
            ItemRarity.LEGENDARY: 1000,
            ItemRarity.UNIQUE: 1200
        }
        score += rarity_scores.get(equip.rarity, 100)
        
        # 2. 레벨 점수 (0~500)
        item_level = getattr(equip, 'level_requirement', 1)
        if character:
            char_level = getattr(character, 'level', 1)
            if item_level > char_level:
                # 장착 불가능
                return 0.0
            # 레벨이 높을수록 좋음
            score += min(item_level * 50, 500)
        else:
            score += min(item_level * 50, 500)
        
        # 3. 스탯 보너스 점수 (0~5000)
        total_stats = equip.get_total_stats()
        stat_score = 0.0
        
        # 캐릭터별 유용한 스탯 가중치
        if character:
            char_job = getattr(character, 'job_id', '')
            is_physical = 'warrior' in char_job.lower() or 'ranger' in char_job.lower()
            is_magical = 'mage' in char_job.lower() or 'priest' in char_job.lower()
            
            for stat, value in total_stats.items():
                if stat in ['physical_attack', 'strength']:
                    stat_score += value * (3.0 if is_physical else 1.0)
                elif stat in ['magic_attack', 'magic', 'spirit']:
                    stat_score += value * (3.0 if is_magical else 1.0)
                elif stat in ['physical_defense', 'magic_defense', 'hp', 'defense']:
                    stat_score += value * 2.0
                elif stat in ['speed', 'accuracy', 'evasion']:
                    stat_score += value * 2.5
                elif stat in ['critical', 'luck']:
                    stat_score += value * 2.0
                else:
                    stat_score += value
        else:
            # 전체 스탯 합계
            for stat, value in total_stats.items():
                stat_score += value
        
        score += min(stat_score, 5000)
        
        # 4. 유니크 효과 보너스 (0~1000)
        if getattr(equip, 'unique_effect', None):
            score += 500
        
        # 5. 특수 효과 보너스 (0~1500)
        special_effects = getattr(equip, 'special_effects', [])
        if special_effects:
            score += min(len(special_effects) * 300, 1500)
        
        return score
    
    def _auto_manage_equipment(self):
        """
        인벤토리의 장비를 파티원에게 자동 장착
        
        프로세스:
        1. 봇 인벤토리에서 모든 장비 수집
        2. 각 파티원에 대해:
           - 현재 장착 장비 vs 인벤토리 장비 비교
           - 더 나은 장비 발견 시 교체
        3. 교체된 장비는 봇 인벤토리에 보관
        """
        inventory = self._get_bot_inventory()
        if not inventory:
            return
        
        # 파티원 가져오기 (봇의 캐릭터들)
        party = getattr(self.session.players.get(self.bot_id), 'party', []) if self.session else []
        if not party:
            return
        
        from src.equipment.item_system import Equipment, EquipSlot
        
        # 인벤토리에서 모든 장비 수집
        equipment_slots = {}
        for slot_idx, slot in enumerate(inventory.slots):
            if isinstance(slot.item, Equipment):
                equip_slot_type = slot.item.equip_slot
                if equip_slot_type not in equipment_slots:
                    equipment_slots[equip_slot_type] = []
                equipment_slots[equip_slot_type].append((slot_idx, slot.item))
        
        # 각 파티원에 대해 최적 장비 찾기
        equipped_count = 0
        for character in party:
            for slot_type in [EquipSlot.WEAPON, EquipSlot.ARMOR, EquipSlot.ACCESSORY]:
                # 현재 장착 장비
                current_equip = getattr(character, f'equipped_{slot_type.value}', None)
                current_score = self._score_equipment(current_equip, character) if current_equip else 0.0
                
                # 인벤토리에서 최고 점수 장비 찾기
                best_equip = None
                best_score = current_score
                best_slot_idx = None
                
                if slot_type in equipment_slots:
                    for slot_idx, equip in equipment_slots[slot_type]:
                        score = self._score_equipment(equip, character)
                        if score > best_score:
                            best_score = score
                            best_equip = equip
                            best_slot_idx = slot_idx
                
                # 더 나은 장비 발견 시 교체
                if best_equip and best_slot_idx is not None:
                    # 현재 장비를 인벤토리에 보관
                    if current_equip:
                        inventory.add_item(current_equip, quantity=1)
                    
                    # 새 장비 장착
                    setattr(character, f'equipped_{slot_type.value}', best_equip)
                    
                    # 인벤토리에서 제거
                    inventory.remove_item(best_slot_idx, quantity=1)
                    
                    equipped_count += 1
                    self.logger.info(
                        f"봇 {self.bot_name} 장비 자동 장착: {character.name}에게 "
                        f"{getattr(best_equip, 'name', 'Unknown')} 장착 (점수: {best_score:.0f})"
                    )
        
        if equipped_count > 0:
            self.logger.info(f"봇 {self.bot_name} 장비 자동 관리 완료: {equipped_count}개 장비 장착")
    
    def _check_and_use_items(self):
        """
        파티원 상태 확인 및 자동 아이템 사용
        
        우선순위:
        1. 사망 → 부활 아이템/음식
        2. HP < 30% → 회복 포션/음식
        3. MP < 20% → MP 포션/음식
        """
        if not self.auto_use_items:
            return
        
        inventory = self._get_bot_inventory()
        if not inventory or len(inventory.slots) == 0:
            return
        
        # 파티원 가져오기
        party = getattr(self.session.players.get(self.bot_id), 'party', []) if self.session else []
        if not party:
            return
        
        from src.equipment.item_system import Consumable
        from src.cooking.recipe import CookedFood
        
        # 각 파티원 상태 확인
        for character in party:
            if not hasattr(character, 'current_hp') or not hasattr(character, 'max_hp'):
                continue
            
            # 1. 사망 체크 (최우선)
            if not getattr(character, 'is_alive', True):
                # 부활 아이템 찾기
                for slot_idx, slot in enumerate(inventory.slots):
                    item = slot.item
                    # 부활 포션
                    if isinstance(item, Consumable) and getattr(item, 'effect_type', '') == 'revive':
                        if inventory.use_consumable(slot_idx, character):
                            self.logger.info(f"봇 {self.bot_name} 부활 아이템 사용: {character.name}")
                            break
                    # 부활 음식
                    elif isinstance(item, CookedFood):
                        hp_restore = getattr(item, 'hp_restore', 0)
                        if hp_restore > 0:
                            if inventory.use_consumable(slot_idx, character):
                                self.logger.info(f"봇 {self.bot_name} 부활 음식 사용: {character.name}")
                                break
                continue  # 부활 시도 후 다음 캐릭터로
            
            # 2. HP 체크
            hp_ratio = character.current_hp / max(character.max_hp, 1)
            if hp_ratio < self.hp_use_threshold:
                # HP 회복 아이템 찾기
                for slot_idx, slot in enumerate(inventory.slots):
                    item = slot.item
                    # HP 포션
                    if isinstance(item, Consumable):
                        effect_type = getattr(item, 'effect_type', '')
                        if effect_type in ['heal_hp', 'heal_both']:
                            if inventory.use_consumable(slot_idx, character):
                                self.logger.info(
                                    f"봇 {self.bot_name} HP 회복 아이템 사용: {character.name} "
                                    f"(HP {character.current_hp}/{character.max_hp})"
                                )
                                break
                    # HP 회복 음식
                    elif isinstance(item, CookedFood):
                        hp_restore = getattr(item, 'hp_restore', 0)
                        if hp_restore > 0:
                            if inventory.use_consumable(slot_idx, character):
                                self.logger.info(
                                    f"봇 {self.bot_name} HP 회복 음식 사용: {character.name} "
                                    f"(HP {character.current_hp}/{character.max_hp})"
                                )
                                break
            
            # 3. MP 체크
            if hasattr(character, 'current_mp') and hasattr(character, 'max_mp'):
                mp_ratio = character.current_mp / max(character.max_mp, 1)
                if mp_ratio < self.mp_use_threshold:
                    # MP 회복 아이템 찾기
                    for slot_idx, slot in enumerate(inventory.slots):
                        item = slot.item
                        # MP 포션
                        if isinstance(item, Consumable):
                            effect_type = getattr(item, 'effect_type', '')
                            if effect_type in ['heal_mp', 'heal_both']:
                                if inventory.use_consumable(slot_idx, character):
                                    self.logger.info(
                                        f"봇 {self.bot_name} MP 회복 아이템 사용: {character.name} "
                                        f"(MP {character.current_mp}/{character.max_mp})"
                                    )
                                    break
                        # MP 회복 음식
                        elif isinstance(item, CookedFood):
                            mp_restore = getattr(item, 'mp_restore', 0)
                            if mp_restore > 0:
                                if inventory.use_consumable(slot_idx, character):
                                    self.logger.info(
                                        f"봇 {self.bot_name} MP 회복 음식 사용: {character.name} "
                                        f"(MP {character.current_mp}/{character.max_mp})"
                                    )
                                    break
    
    def _use_combat_items(self):
        """
        전투 중 전투 아이템 전략적 사용
        
        전략:
        1. 전투 시작 → 버프 아이템 사용 (공격력, 방어력 증가)
        2. 강한 적 → 디버프 아이템 (방어력 감소, 속도 감소)
        3. 적 HP 낮음 → 공격 아이템 (추가 데미지)
        """
        if not self.in_combat or not self.combat_manager:
            return
        
        inventory = self._get_bot_inventory()
        if not inventory or len(inventory.slots) == 0:
            return
        
        # 파티원 가져오기
        party = getattr(self.session.players.get(self.bot_id), 'party', []) if self.session else []
        if not party:
            return
        
        from src.equipment.item_system import Consumable
        from src.cooking.recipe import CookedFood
        
        # 전투 상태 분석
        combat_state = getattr(self.combat_manager, 'state', None)
        enemies = getattr(self.combat_manager, 'enemies', [])
        
        if not enemies:
            return
        
        # 1. 전투 초반 → 버프 아이템/음식 사용
        combat_turn = getattr(self.combat_manager, 'turn', 0)
        if combat_turn <= 2:  # 첫 2턴 이내
            for character in party:
                if not getattr(character, 'is_alive', True):
                    continue
                
                # 버프 음식 찾기
                for slot_idx, slot in enumerate(inventory.slots):
                    item = slot.item
                    
                    # 버프 효과가 있는 음식
                    if isinstance(item, CookedFood):
                        buff_type = getattr(item, 'buff_type', None)
                        if buff_type in ['attack', 'defense', 'speed', 'magic']:
                            # 이미 버프가 있는지 확인
                            active_buffs = getattr(character, 'active_buffs', {})
                            buff_key = f"{buff_type}_up"
                            if buff_key not in active_buffs:
                                if inventory.use_consumable(slot_idx, character):
                                    self.logger.info(
                                        f"봇 {self.bot_name} 전투 버프 사용: {character.name} "
                                        f"({getattr(item, 'name', 'Unknown')} - {buff_type})"
                                    )
                                    break  # 캐릭터당 1개만
        
        # 2. 강한 적에게 디버프 아이템
        for enemy in enemies:
            if not getattr(enemy, 'is_alive', True):
                continue
            
            enemy_hp_ratio = enemy.current_hp / max(enemy.max_hp, 1)
            
            # 적 HP가 70% 이상이면 디버프 고려
            if enemy_hp_ratio >= 0.7:
                for slot_idx, slot in enumerate(inventory.slots):
                    item = slot.item
                    
                    # 디버프 포션 (예: 방어력 감소, 속도 감소)
                    if isinstance(item, Consumable):
                        effect_type = getattr(item, 'effect_type', '')
                        if 'debuff' in effect_type or 'weaken' in effect_type:
                            if inventory.use_consumable(slot_idx, enemy):
                                self.logger.info(
                                    f"봇 {self.bot_name} 디버프 아이템 사용: {getattr(item, 'name', 'Unknown')} "
                                    f"({enemy.name}에게 사용)"
                                )
                                break # Break after using one item on this enemy
        
        # 3. 적 HP 낮을 때 → 공격 아이템
        for enemy in enemies:
            if not getattr(enemy, 'is_alive', True):
                continue
            
            enemy_hp_ratio = enemy.current_hp / max(enemy.max_hp, 1)
            
            # 적 HP가 30% 이하면 공격 아이템으로 마무리
            if enemy_hp_ratio <= 0.3:
                for slot_idx, slot in enumerate(inventory.slots):
                    item = slot.item
                    
                    # 공격 아이템 (예: 폭탄, 마법 스크롤)
                    if isinstance(item, Consumable):
                        effect_type = getattr(item, 'effect_type', '')
                        if 'damage' in effect_type or 'attack' in effect_type:
                            self.logger.debug(
                                f"봇 {self.bot_name} 공격 아이템 감지: {getattr(item, 'name', 'Unknown')} "
                                f"(적 HP: {enemy.current_hp}/{enemy.max_hp})"
                            )
                            # 실제 사용은 combat_manager 통합 필요
                            break
    
    def decide_action(self, character: Any, allies: list, enemies: list) -> dict:
        """
        전투 중 봇의 행동 결정 (combat_manager에서 호출)
        
        Args:
            character: 봇이 조종하는 캐릭터
            allies: 아군 목록
            enemies: 적군 목록
        
        Returns:
            행동 정보 딕셔너리
            {
                "type": "attack" | "hp_attack" | "skill" | "defend",
                "skill": Skill (if type == "skill"),
                "target": target_character
            }
        """
        # 1. 스킬 사용 여부 판단
        if self._should_use_skill_in_combat(character, enemies):
            # 2. 최적 스킬 선택
            selected_skill = self._select_best_skill(character, enemies, allies)
            
            if selected_skill:
                # 3. 타겟 선택
                target = self._select_skill_target(selected_skill, character, allies, enemies)
                
                if target:
                    self.logger.info(
                        f"봇 {self.bot_name} 스킬 사용: {character.name} → {getattr(selected_skill, 'name', 'Unknown')}"
                    )
                    return {
                        "type": "skill",
                        "skill": selected_skill,
                        "target": target
                    }
        
        # 4. 스킬이 없으면 기본 공격 (BRV or HP)
        return self._decide_basic_attack(character, enemies)
    
    def _select_skill_target(self, skill: Any, character: Any, allies: list, enemies: list) -> Any:
        """
        스킬 타겟 선택
        
        Returns:
            선택된 타겟 (단일 or 리스트)
        """
        target_type = str(getattr(skill, 'target_type', 'single_enemy')).lower()
        
        # Self 타겟
        if target_type == 'self':
            return character
        
        # 전체 aoe
        if 'all_enemies' in target_type or getattr(skill, 'is_aoe', False):
            return [e for e in enemies if getattr(e, 'is_alive', True)]
        
        if 'all_allies' in target_type:
            return [a for a in allies if getattr(a, 'is_alive', True)]
        
        # 단일 아군 (회복)
        if 'ally' in target_type:
            alive_allies = [a for a in allies if getattr(a, 'is_alive', True)]
            if not alive_allies:
                return None
            
            # HP 가장 낮은 아군
            weakest = min(alive_allies, key=lambda a: a.current_hp / max(a.max_hp, 1))
            return weakest
        
        # 단일 적 (기본)
        alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
        if not alive_enemies:
            return None
        
        # HP 가장 낮은 적 (마무리 우선)
        weakest_enemy = min(alive_enemies, key=lambda e: e.current_hp)
        return weakest_enemy
    
    def _decide_basic_attack(self, character: Any, enemies: list) -> dict:
        """
        기본 공격 결정 (BRV vs HP)
        
        Returns:
            공격 행동 정보
        """
        alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
        
        if not alive_enemies:
            return {"type": "defend", "target": None}
        
        # BRV 확인
        current_brv = getattr(character, 'current_brv', 0)
        
        # 타겟 선택 (HP 가장 낮은 적)
        target = min(alive_enemies, key=lambda e: e.current_hp)
        
        # HP 공격 판단
        if current_brv >= 100:  # BRV 100 이상이면 HP 공격 고려
            # HP 공격 70% 확률
            import random
            if random.random() < 0.7:
                return {
                    "type": "hp_attack",
                    "target": target
                }
        
        # 직업별 고유 기본 공격 스킬 확인 (첫 번째 스킬)
        skills = getattr(character, 'skills', [])
        if skills and len(skills) > 0:
            basic_skill = skills[0]
            can_use, _ = basic_skill.can_use(character)
            if can_use:
                self.logger.info(f"봇 {self.bot_name} 고유 기본 공격 사용: {basic_skill.name}")
                return {
                    "type": "skill",
                    "skill": basic_skill,
                    "target": target
                }
        
        # BRV 공격 (Fallback)
        return {
            "type": "attack",  # BRV 공격
            "target": target
        }
    
    def _should_use_skill_in_combat(self, character: Any, enemies: list) -> bool:
        """
        전투 중 스킬 사용 여부 결정 (지능적 판단)
        
        고려사항:
        - MP 상태
        - 기믹 스택 상태
        - 적 상황
        - 직업 역할
        
        Returns:
            True면 스킬 사용 권장
        """
        if not hasattr(character, 'current_mp') or not hasattr(character, 'max_mp'):
            return False
        
        mp_ratio = character.current_mp / max(character.max_mp, 1)
        
        # 기믹 스택 확인 (스택이 높으면 소비 스킬 사용)
        has_high_stacks = False
        if hasattr(character, 'gimmick_values'):
            for key, value in character.gimmick_values.items():
                if value >= 4:  # 스택 4개 이상
                    has_high_stacks = True
                    break
        
        # 스택이 많으면 MP가 낮아도 스킬 사용
        if has_high_stacks:
            return True
        
        # 적이 많거나 (2명 이상) 보스급 (HP 높음)이면 스킬 우선 (3명 -> 2명 완화)
        enemy_count = len([e for e in enemies if getattr(e, 'is_alive', True)])
        if enemy_count >= 2 and mp_ratio >= 0.2: # 조건 완화 (MP 0.3 -> 0.2)
            return True
        
        # MP가 충분하면 스킬 적극 사용 (0.4 -> 0.15로 대폭 완화)
        return mp_ratio >= 0.15
    
    def _select_best_skill(self, character: Any, enemies: list, allies: list = None) -> Any:
        """
        전투 상황에 맞는 최적의 스킬 선택 (지능적 AI)
        
        직업별 우선순위:
        - 힐러: 아군 HP 체크 → 회복 스킬
        - 탱커: 방어/보호 스킬
        - 딜러: 기믹 스택 관리 → 폭딜 스킬
        - 서포터: 버프/디버프
        
        Returns:
            선택된 스킬 또는 None
        """
        skills = getattr(character, 'skills', [])
        job_id = getattr(character, 'job_id', '')
        
        # 첫 2개는 기본 공격이므로 제외
        available_skills = skills[2:] if len(skills) > 2 else []
        
        if not available_skills:
            return None
        
        # 사용 가능한 스킬만 필터링
        usable_skills = []
        for skill in available_skills:
            can_use, reason = skill.can_use(character)
            if can_use:
                usable_skills.append(skill)
        
        if not usable_skills:
            return None
        
        # 기믹 스택 확인
        gimmick_values = getattr(character, 'gimmick_values', {})
        
        # === 직업별 맞춤 스킬 선택 ===
        
        # 1. 힐러 직업 (Cleric, Shaman 등)
        if 'cleric' in job_id.lower() or 'priest' in job_id.lower():
            # 아군 HP 체크
            if allies:
                for ally in allies:
                    if not getattr(ally, 'is_alive', True):
                        # 부활 스킬 우선
                        for skill in usable_skills:
                            if '부활' in getattr(skill, 'name', '') or 'resurrect' in getattr(skill, 'id', '').lower():
                                self.logger.info(f"봇 {self.bot_name} 부활 스킬 선택: {skill.name}")
                                return skill
                    
                    hp_ratio = ally.current_hp / max(ally.max_hp, 1)
                    if hp_ratio < 0.5:
                        # 회복 스킬
                        for skill in usable_skills:
                            target_type = str(getattr(skill, 'target_type', ''))
                            if 'ally' in target_type.lower() or 'heal' in getattr(skill, 'name', '').lower():
                                self.logger.info(f"봇 {self.bot_name} 회복 스킬 선택: {skill.name}")
                                return skill
        
        # 2. 탱커 직업 (Knight, Guardian 등)
        if 'knight' in job_id.lower() or 'guardian' in job_id.lower():
            # 보호 스킬 우선
            for skill in usable_skills:
                if '보호' in getattr(skill, 'name', '') or 'protect' in getattr(skill, 'id', '').lower():
                    self.logger.info(f"봇 {self.bot_name} 보호 스킬 선택: {skill.name}")
                    return skill
        
        # 3. 스택 관리가 중요한 직업
        stack_based_jobs = ['spellblade', 'dragon_knight', 'alchemist', 'sniper', 'vampire', 'shaman']
        for job_key in stack_based_jobs:
            if job_key in job_id.lower():
                # 스택이 높으면 소비 스킬 사용
                max_stack = max(gimmick_values.values()) if gimmick_values else 0
                
                if max_stack >= 5:
                    # 궁극기/강력 스킬 우선
                    for skill in usable_skills:
                        skill_name = getattr(skill, 'name', '')
                        # 소비 스킬 찾기
                        if any(keyword in skill_name for keyword in ['폭발', '폭풍', '궁극', '데드아이', '광란']):
                            self.logger.info(f"봇 {self.bot_name} 스택 소비 스킬: {skill.name} (스택: {max_stack})")
                            return skill
                
                elif max_stack < 3:
                    # 스택 쌓기 스킬 찾기 (기본 공격 아닌 것 중)
                    for skill in usable_skills:
                        effects = getattr(skill, 'effects', [])
                        for effect in effects:
                            if hasattr(effect, 'operation') and 'ADD' in str(effect.operation):
                                self.logger.info(f"봇 {self.bot_name} 스택 쌓기 스킬: {skill.name}")
                                return skill
        
        # 4. AOE 스킬 우선 (적이 3명 이상)
        enemy_count = len([e for e in enemies if getattr(e, 'is_alive', True)])
        if enemy_count >= 3:
            for skill in usable_skills:
                target_type = str(getattr(skill, 'target_type', ''))
                is_aoe = getattr(skill, 'is_aoe', False)
                if 'all_enemies' in target_type.lower() or is_aoe or 'aoe' in target_type.lower():
                    self.logger.info(f"봇 {self.bot_name} AOE 스킬 선택 (적 {enemy_count}명): {skill.name}")
                    return skill
        
        # 5. 디버프 스킬 (보스급 적)
        for enemy in enemies:
            if not getattr(enemy, 'is_alive', True):
                continue
            
            enemy_hp_ratio = enemy.current_hp / max(enemy.max_hp, 1)
            enemy_hp_total = enemy.max_hp
            
            # HP가 높은 적 (보스급)
            if enemy_hp_total > 500 or enemy_hp_ratio > 0.8:
                for skill in usable_skills:
                    skill_name = getattr(skill, 'name', '').lower()
                    if any(keyword in skill_name for keyword in ['디버프', 'debuff', '약화', '저주', '독']):
                        self.logger.info(f"봇 {self.bot_name} 디버프 스킬 (보스급): {skill.name}")
                        return skill
        
        # 6. MP 효율이 가장 좋은 스킬 (기본 선택)
        best_skill = None
        best_score = 0
        
        for skill in usable_skills:
            # 스킬 점수 계산
            damage_multiplier = getattr(skill, 'power', 1.0)
            
            # 효과 분석
            effects = getattr(skill, 'effects', [])
            effect_score = 0
            for effect in effects:
                effect_type_str = str(type(effect).__name__)
                if 'Damage' in effect_type_str:
                    effect_score += 2.0
                elif 'Buff' in effect_type_str or 'Debuff' in effect_type_str:
                    effect_score += 1.5
                elif 'Heal' in effect_type_str:
                    effect_score += 1.8
            
            # MP 비용
            mp_cost = 0
            for cost in getattr(skill, 'costs', []):
                if hasattr(cost, 'amount'):
                    mp_cost += cost.amount
            
            # 효율 = (데미지 + 효과) / MP
            total_value = damage_multiplier + effect_score
            efficiency = total_value / max(mp_cost, 1)
            
            if efficiency > best_score:
                best_score = efficiency
                best_skill = skill
        
        if best_skill:
            self.logger.info(f"봇 {self.bot_name} 효율 스킬: {best_skill.name} (효율: {best_score:.2f})")
        
        return best_skill
    
    def _calculate_item_priority(self, item: Any) -> int:
        """
        아이템 우선순위 점수
        
        점수 체계:
        - 장비 (장착 가능): 100 + (레벨 * 10)
        - 요리/포션: 50 + (효과 * 5)
        - 재료 (레시피 있음): 30
        - 재료 (일반): 10
        - 기타: 5
        
        Returns:
            우선순위 점수 (높을수록 중요)
        """
        from src.equipment.item_system import Equipment, Consumable
        from src.cooking.recipe import CookedFood
        from src.gathering.ingredient import Ingredient
        
        priority = 0
        
        # 장비
        if isinstance(item, Equipment):
            level = getattr(item, 'level_requirement', 1)
            priority = 100 + (level * 10)
        # 요리/포션
        elif isinstance(item, (Consumable, CookedFood)):
            if isinstance(item, Consumable):
                effect_value = getattr(item, 'effect_value', 0)
                priority = 50 + int(effect_value * 0.1)
            else:  # CookedFood
                hp_restore = getattr(item, 'hp_restore', 0)
                mp_restore = getattr(item, 'mp_restore', 0)
                priority = 50 + int((hp_restore + mp_restore) * 0.05)
        # 재료
        elif isinstance(item, Ingredient):
            priority = 30  # 재료는 중간 우선순위
        # 기타
        else:
            priority = 5
        
        return priority
    
    def _optimize_inventory(self):
        """
        인벤토리 무게 최적화
        
        현재 무게가 최대 무게의 70% 초과 시:
        - 우선순위 낮은 아이템부터 드롭
        - 최소 30% 여유 공간 유지
        """
        if not self.auto_cleanup_inventory:
            return
        
        inventory = self._get_bot_inventory()
        if not inventory:
            return
        
        # 무게 체크
        weight_ratio = inventory.current_weight / max(inventory.max_weight, 0.1)
        if weight_ratio < 0.7:  # 70% 미만이면 정리 불필요
            return
        
        # 모든 아이템에 우선순위 부여
        items_with_priority = []
        for slot_idx, slot in enumerate(inventory.slots):
            priority = self._calculate_item_priority(slot.item)
            items_with_priority.append((slot_idx, slot.item, priority, slot.quantity))
        
        # 우선순위 낮은 순으로 정렬
        items_with_priority.sort(key=lambda x: x[2])  # priority로 정렬
        
        # 목표: 30% 여유 공간 확보
        target_weight = inventory.max_weight * (1.0 - self.min_free_weight_percent)
        dropped_items = []
        
        for slot_idx, item, priority, quantity in items_with_priority:
            if inventory.current_weight <= target_weight:
                break  # 목표 달성
            
            # 아이템 제거
            item_name = getattr(item, 'name', 'Unknown')
            item_weight = getattr(item, 'weight', 0.5) * quantity
            
            # 슬롯에서 제거
            inventory.remove_item(slot_idx, quantity=quantity)
            dropped_items.append((item_name, quantity, item_weight))
            
            self.logger.debug(
                f"봇 {self.bot_name} 아이템 드롭: {item_name} x{quantity} "
                f"(우선순위: {priority}, 무게: {item_weight:.1f}kg)"
            )
        
        if dropped_items:
            total_dropped_weight = sum(w for _, _, w in dropped_items)
            self.logger.info(
                f"봇 {self.bot_name} 인벤토리 정리 완료: {len(dropped_items)}종류 아이템 드롭 "
                f"({total_dropped_weight:.1f}kg 확보, 현재: {inventory.current_weight:.1f}/{inventory.max_weight:.1f}kg)"
            )
    
    def _check_and_harvest(self) -> Optional[Dict[str, Any]]:
        """주변에 채집 가능한 오브젝트가 있는지 확인하고 채집 액션 반환"""
        # exploration 시스템 가져오기
        exploration = self._get_exploration_system()
        if not exploration:
            return None
        
        # 주변 채집 오브젝트 찾기 (맨하탄 거리 1 이내 - 바로 옆)
        max_distance = 1
        closest_harvestable = None
        closest_distance = max_distance + 1
        
        from src.gathering.harvestable import HarvestableType
        
        for harvestable in exploration.dungeon.harvestables:
            # 요리솥은 제외 (채집이 아님, 별도 처리)
            if harvestable.object_type == HarvestableType.COOKING_POT:
                continue
            
            # 이미 이 봇이 채집한 오브젝트는 제외 (멀티플레이: 개인 보상)
            if not harvestable.can_harvest(self.bot_id):
                continue
            
            # 맨하탄 거리 계산
            distance = abs(harvestable.x - self.current_x) + abs(harvestable.y - self.current_y)
            
            # 범위 내이고 더 가까우면 선택
            if distance <= max_distance and distance < closest_distance:
                closest_harvestable = harvestable
                closest_distance = distance
        
        if closest_harvestable:
            # 채집 액션 반환
            return {
                "type": "harvest",
                "harvestable": closest_harvestable,
                "x": closest_harvestable.x,
                "y": closest_harvestable.y
            }
        
        return None
    
    def _check_and_cook(self) -> Optional[Dict[str, Any]]:
        """주변에 요리솥이 있는지 확인하고 요리 액션 반환"""
        # exploration 시스템 가져오기
        exploration = self._get_exploration_system()
        if not exploration:
            return None
        
        # 봇의 인벤토리 가져오기
        inventory = self._get_bot_inventory()
        if not inventory:
            return None
        
        # 인벤토리에 재료가 있는지 확인
        available_ingredients = self._get_available_ingredients_for_cooking(inventory)
        if not available_ingredients or len(available_ingredients) < 1:
            return None  # 재료가 없으면 요리 불가
        
        # 주변 요리솥 찾기 (맨하탄 거리 2 이내)
        max_distance = 2
        closest_cooking_pot = None
        closest_distance = max_distance + 1
        
        from src.gathering.harvestable import HarvestableType
        
        for harvestable in exploration.dungeon.harvestables:
            # 요리솥만 찾기
            if harvestable.object_type != HarvestableType.COOKING_POT:
                continue
            
            # 맨하탄 거리 계산
            distance = abs(harvestable.x - self.current_x) + abs(harvestable.y - self.current_y)
            
            # 범위 내이고 더 가까우면 선택
            if distance <= max_distance and distance < closest_distance:
                closest_cooking_pot = harvestable
                closest_distance = distance
        
        if closest_cooking_pot:
            # 요리 액션 반환
            return {
                "type": "cook",
                "cooking_pot": closest_cooking_pot,
                "x": closest_cooking_pot.x,
                "y": closest_cooking_pot.y,
                "ingredients": available_ingredients
            }
        
        return None
    
    def _get_available_ingredients_for_cooking(self, inventory: Any) -> List[Any]:
        """인벤토리에서 요리 가능한 재료 목록 가져오기"""
        ingredients = []
        
        if not inventory or not hasattr(inventory, 'slots'):
            return ingredients
        
        from src.gathering.ingredient import Ingredient
        from src.equipment.item_system import ItemType
        
        for i, slot in enumerate(inventory.slots):
            if slot is None:
                continue
            if not hasattr(slot, 'item') or slot.item is None:
                continue
            
            # Ingredient 타입 확인
            item_type = getattr(slot.item, 'item_type', None)
            if item_type == ItemType.MATERIAL:
                # Ingredient 객체인지 확인
                if isinstance(slot.item, Ingredient) or hasattr(slot.item, 'category'):
                    ingredients.append((i, slot.item))
        
        return ingredients
    
    def _get_bot_inventory(self) -> Optional[Any]:
        """봇의 인벤토리 가져오기"""
        # 세션에서 봇 플레이어 가져오기
        if not self.session:
            return None
        
        bot_player = self.session.players.get(self.bot_id)
        if not bot_player:
            return None
        
        # 봇 플레이어의 인벤토리 가져오기
        if hasattr(bot_player, 'inventory'):
            return bot_player.inventory
        
        # exploration 시스템에서 인벤토리 가져오기 시도
        exploration = self._get_exploration_system()
        if exploration and hasattr(exploration, 'inventory'):
            return exploration.inventory
        
        return None
    
    def _check_and_pickup(self) -> Optional[Dict[str, Any]]:
        """주변에 드롭된 아이템/골드가 있는지 확인하고 줍기 액션 반환"""
        # exploration 시스템 가져오기
        exploration = self._get_exploration_system()
        if not exploration:
            return None
        
        # 주변 타일 확인 (맨하탄 거리 1 이내)
        max_distance = 1
        closest_item = None
        closest_gold = None
        closest_distance = max_distance + 1
        
        from src.world.tile import TileType
        
        for dx in range(-max_distance, max_distance + 1):
            for dy in range(-max_distance, max_distance + 1):
                if abs(dx) + abs(dy) > max_distance:
                    continue
                
                x = self.current_x + dx
                y = self.current_y + dy
                
                tile = exploration.dungeon.get_tile(x, y)
                if not tile:
                    continue
                
                # 드롭된 아이템 확인 (봇이 드롭한 것은 무시)
                if tile.tile_type == TileType.DROPPED_ITEM and tile.dropped_item:
                    # 봇이 드롭한 아이템인지 확인
                    dropped_by = getattr(tile, 'dropped_by_player_id', None)
                    if dropped_by:
                        # 세션에서 해당 플레이어가 봇인지 확인
                        if self.session and self.session.players.get(dropped_by):
                            player = self.session.players[dropped_by]
                            if getattr(player, 'is_bot', False):
                                # 봇이 드롭한 아이템이면 무시
                                continue
                    
                    distance = abs(dx) + abs(dy)
                    if distance < closest_distance:
                        closest_item = (x, y, tile.dropped_item)
                        closest_distance = distance
                
                # 드롭된 골드 확인 (봇이 드롭한 것은 무시)
                if tile.tile_type == TileType.GOLD and tile.gold_amount > 0:
                    # 봇이 드롭한 골드인지 확인
                    dropped_by = getattr(tile, 'dropped_by_player_id', None)
                    if dropped_by:
                        # 세션에서 해당 플레이어가 봇인지 확인
                        if self.session and self.session.players.get(dropped_by):
                            player = self.session.players[dropped_by]
                            if getattr(player, 'is_bot', False):
                                # 봇이 드롭한 골드면 무시
                                continue
                    
                    distance = abs(dx) + abs(dy)
                    if distance < closest_distance:
                        closest_gold = (x, y, tile.gold_amount)
                        closest_distance = distance
        
        # 아이템 우선 (골드보다 가치가 높다고 가정)
        if closest_item:
            return {
                "type": "pickup_item",
                "x": closest_item[0],
                "y": closest_item[1],
                "item": closest_item[2]
            }
        
        if closest_gold:
            return {
                "type": "pickup_gold",
                "x": closest_gold[0],
                "y": closest_gold[1],
                "amount": closest_gold[2]
            }
        
        return None
    
    def _get_exploration_system(self) -> Optional[Any]:
        """exploration 시스템 가져오기"""
        # 세션에서 exploration 가져오기 시도
        if self.session and hasattr(self.session, 'exploration'):
            return self.session.exploration
        
        # network_manager에서 가져오기 시도
        if self.network_manager and hasattr(self.network_manager, 'current_exploration'):
            exploration = self.network_manager.current_exploration
            # 세션에 exploration 저장 (다음번 빠른 접근을 위해)
            if exploration and self.session:
                self.session.exploration = exploration
            return exploration
        
        self.logger.debug(f"봇 {self.bot_name} 탐험 시스템을 찾을 수 없음")
        return None
    
    def _get_improved_exploration_move(self) -> Dict[str, Any]:
        """개선된 탐험 이동 (A* 변형 알고리즘 사용)"""
        # 탐험 시스템 가져오기
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            # 탐험 시스템이 없으면 기본 이동
            return {
                "type": "move",
                "dx": 0,
                "dy": 0,
                "x": self.current_x,
                "y": self.current_y
            }
        
        dungeon = exploration.dungeon
        
        # 현재 위치 기록
        self.explored_positions.add((self.current_x, self.current_y))
        
        # 현재 위치 주변 탐험 완료 여부 확인
        if self._is_area_fully_explored():
            # 탐험 완료한 구역이면 멀리 떠나기 (계단이나 미탐험 지역으로)
            return self._move_away_from_completed_area()
        
        # A* 변형 알고리즘으로 탐험 목표 찾기
        exploration_target = self._find_exploration_target()
        
        if exploration_target:
            # 목표를 찾았으면 A* 경로로 이동
            path = self._find_exploration_path(
                (self.current_x, self.current_y),
                exploration_target,
                dungeon,
                exploration
            )
            
            if path and len(path) > 0:
                # 경로의 첫 번째 위치로 이동
                next_x, next_y = path[0]
                dx = next_x - self.current_x
                dy = next_y - self.current_y
                
                # 이동 가능 여부 최종 확인
                if (0 <= next_x < dungeon.width and 
                    0 <= next_y < dungeon.height and
                    dungeon.is_walkable(next_x, next_y)):
                    return {
                        "type": "move",
                        "dx": dx,
                        "dy": dy,
                        "x": next_x,
                        "y": next_y
                    }
        
        # 목표를 찾지 못했거나 경로가 없으면 폴백 (기존 로직)
        return self._get_fallback_exploration_move(exploration, dungeon)
    
    def _find_exploration_target(self) -> Optional[Tuple[int, int]]:
        """
        탐험 목표 찾기 (미탐험 지역, 채집물, 계단 등)
        
        Returns:
            가장 우선순위가 높은 목표 위치 (x, y) 또는 None
        """
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return None
        
        dungeon = exploration.dungeon
        current_pos = (self.current_x, self.current_y)
        
        # 탐험 범위 (현재 위치에서 일정 거리 내)
        search_radius = 15
        
        # 우선순위 1: 아직 채집하지 않은 채집물
        from src.gathering.harvestable import HarvestableType
        best_target = None
        closest_distance = float('inf')
        
        for harvestable in dungeon.harvestables:
            # 요리솥은 제외 (요리는 별도 로직에서 처리)
            if harvestable.object_type == HarvestableType.COOKING_POT:
                continue
            
            # 이미 채집했으면 스킵
            if not harvestable.can_harvest(self.bot_id):
                continue
            
            target_pos = (harvestable.x, harvestable.y)
            
            # 채집물 위치가 이동 불가능하면(장애물), 인접한 이동 가능 타일을 목표로 설정
            if not dungeon.is_walkable(harvestable.x, harvestable.y):
                best_neighbor = None
                min_neighbor_dist = float('inf')
                
                # 상하좌우 인접 타일 확인
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = harvestable.x + dx, harvestable.y + dy
                    
                    # 이동 가능한지 확인
                    if (0 <= nx < dungeon.width and 
                        0 <= ny < dungeon.height and
                        dungeon.is_walkable(nx, ny)):
                        
                        # 봇과의 거리 계산
                        d = self._heuristic(current_pos, (nx, ny))
                        if d < min_neighbor_dist:
                            min_neighbor_dist = d
                            best_neighbor = (nx, ny)
                
                if best_neighbor:
                    target_pos = best_neighbor
                else:
                    # 접근 가능한 인접 타일이 없으면 포기
                    continue
            
            distance = self._heuristic(current_pos, target_pos)
            
            # 탐험 범위 내이고 가장 가까운 것
            if distance <= search_radius and distance < closest_distance:
                best_target = target_pos
                closest_distance = distance
        
        if best_target:
            return best_target
        
        # 우선순위 2: 미탐험 지역 (가까운 것부터)
        best_target = None
        closest_distance = float('inf')
        
        # 현재 위치 주변에서 미탐험 지역 찾기
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                check_x = self.current_x + dx
                check_y = self.current_y + dy
                
                # 맵 범위 확인
                if not (0 <= check_x < dungeon.width and 0 <= check_y < dungeon.height):
                    continue
                
                # 이동 불가능한 타일은 스킵
                if not dungeon.is_walkable(check_x, check_y):
                    continue
                
                # 이미 탐험한 위치는 스킵
                if (check_x, check_y) in self.explored_positions:
                    # 던전 타일의 explored 상태도 확인
                    tile = dungeon.get_tile(check_x, check_y)
                    if tile and tile.explored:
                        continue
                
                # 미탐험 지역 발견
                target_pos = (check_x, check_y)
                distance = self._heuristic(current_pos, target_pos)
                
                # 가장 가까운 미탐험 지역 선택
                if distance < closest_distance:
                    best_target = target_pos
                    closest_distance = distance
        
        if best_target:
            return best_target
        
        # 우선순위 3: 계단 (다음 층으로 이동)
        from src.world.tile import TileType
        for room in dungeon.rooms:
            for y in range(room.y1, room.y2):
                for x in range(room.x1, room.x2):
                    tile = dungeon.get_tile(x, y)
                    if tile and tile.tile_type in [TileType.STAIRS_DOWN, TileType.STAIRS_UP]:
                        # 계단까지의 거리가 너무 멀지 않으면
                        distance = self._heuristic(current_pos, (x, y))
                        if distance <= search_radius:
                            return (x, y)
        
        return None
    
    def _find_exploration_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        dungeon: Any,
        exploration: Any
    ) -> List[Tuple[int, int]]:
        """
        A* 변형 알고리즘으로 탐험 경로 찾기
        
        탐험 우선순위:
        1. 미탐험 지역을 통과하는 경로 우선 (낮은 비용)
        2. 탐험된 지역은 높은 비용
        3. 적 위치는 매우 높은 비용
        4. 잠긴 문은 통과 불가
        
        Args:
            start: 시작 위치 (x, y)
            goal: 목표 위치 (x, y)
            dungeon: 던전 맵
            exploration: 탐험 시스템
        
        Returns:
            경로 리스트 [(x1, y1), (x2, y2), ...] (목표 제외, 시작점부터)
        """
        import heapq
        from src.world.tile import TileType
        
        # 적의 위치 수집
        enemy_positions = set()
        if exploration and hasattr(exploration, 'enemies'):
            for enemy in exploration.enemies:
                if hasattr(enemy, 'x') and hasattr(enemy, 'y'):
                    enemy_positions.add((int(enemy.x), int(enemy.y)))
        
        # 플레이어(봇 포함) 위치 수집 (충돌 방지용)
        player_positions = set()
        if exploration and hasattr(exploration, 'session') and exploration.session:
            for pid, p in exploration.session.players.items():
                # 자기 자신은 제외
                if pid == self.bot_id:
                    continue
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    # 생존해 있는 플레이어만 벽 취급
                    is_dead = False
                    if hasattr(p, 'is_party_alive'):
                        if callable(p.is_party_alive):
                            if not p.is_party_alive():
                                is_dead = True
                        else:
                            if not p.is_party_alive:
                                is_dead = True
                    
                    if not is_dead:
                        player_positions.add((int(p.x), int(p.y)))
        
        # 로컬 플레이어도 추가 (싱글플레이 호환성)
        if exploration and hasattr(exploration, 'player'):
            p = exploration.player
            # 로컬 플레이어 ID 확인
            local_pid = getattr(p, 'player_id', None)
            if local_pid != self.bot_id:
                # 생존 체크 (간략하게)
                all_dead = True
                if hasattr(p, 'party'):
                    for m in p.party:
                        if getattr(m, 'current_hp', 0) > 0:
                            all_dead = False
                            break
                
                if not all_dead:
                    player_positions.add((int(p.x), int(p.y)))
        
        # 잠긴 문 위치
        locked_doors = set()
        if hasattr(dungeon, 'locked_doors'):
            for door_x, door_y, _ in dungeon.locked_doors:
                locked_doors.add((door_x, door_y))
        
        # 시작점과 목표점이 같으면 빈 경로 반환
        if start == goal:
            return []
        
        # A* 알고리즘
        open_set = [(0, start)]  # (f_score, position)
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        g_score: Dict[Tuple[int, int], float] = {start: 0}
        f_score: Dict[Tuple[int, int], float] = {start: self._heuristic(start, goal)}
        closed_set: Set[Tuple[int, int]] = set()
        
        # 4방향 이동 (상, 하, 좌, 우) - 대각선 이동 제외로 더 정확한 경로
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # 목표에 도달
            if current == goal:
                # 경로 재구성
                path = []
                path_current = current
                while path_current is not None:
                    path.append(path_current)
                    path_current = came_from.get(path_current)
                path.reverse()
                # 시작점 제외
                if path and path[0] == start:
                    path = path[1:]
                return path
            
            # 인접 노드 확인
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # 맵 범위 확인
                if not (0 <= neighbor[0] < dungeon.width and 0 <= neighbor[1] < dungeon.height):
                    continue
                
                # 이동 가능 여부 확인
                tile = dungeon.get_tile(neighbor[0], neighbor[1])
                if not tile or not dungeon.is_walkable(neighbor[0], neighbor[1]):
                    continue
                
                # 잠긴 문 확인
                if tile.tile_type == TileType.LOCKED_DOOR or neighbor in locked_doors:
                    continue
                
                # 이미 확인한 노드 스킵
                if neighbor in closed_set:
                    continue
                
                # 비용 계산 (탐험 우선순위 반영)
                move_cost = 1.0
                
                # 미탐험 지역은 낮은 비용 (우선순위 높음)
                if neighbor not in self.explored_positions:
                    # 던전 타일의 explored 상태도 확인
                    if not (tile and tile.explored):
                        move_cost = 0.5  # 미탐험 지역은 절반 비용
                else:
                    # 탐험된 지역은 높은 비용
                    move_cost = 2.0
                
                # 적 근처는 매우 높은 비용
                if neighbor in enemy_positions:
                    move_cost += 15.0  # 적 근처는 매우 높은 비용
                elif any(abs(neighbor[0] - ex) + abs(neighbor[1] - ey) <= 2 for ex, ey in enemy_positions):
                    move_cost += 5.0  # 적 근처 2칸 이내는 높은 비용
                
                # G 점수 계산
                tentative_g_score = g_score[current] + move_cost
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        # 경로를 찾을 수 없음 (폴백 사용)
        return []
    
    def _get_fallback_exploration_move(self, exploration: Any, dungeon: Any) -> Dict[str, Any]:
        """폴백 탐험 이동 (A*로 경로를 찾지 못했을 때)"""
        import random
        
        # 잠긴 문 위치 가져오기
        locked_doors = set()
        if hasattr(dungeon, 'locked_doors'):
            for door_x, door_y, _ in dungeon.locked_doors:
                locked_doors.add((door_x, door_y))
        
        # 주변 4방향 확인 (이동 가능한 방향만)
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        # 이동 가능한 방향만 필터링 (잠긴 문 제외)
        valid_directions = []
        for dx, dy in directions:
            new_x = self.current_x + dx
            new_y = self.current_y + dy
            
            # 잠긴 문 위치는 제외
            if (new_x, new_y) in locked_doors:
                continue
            
            # 맵 범위 확인 및 이동 가능 여부 확인
            if (0 <= new_x < dungeon.width and 
                0 <= new_y < dungeon.height and
                dungeon.is_walkable(new_x, new_y)):
                valid_directions.append((dx, dy))
        
        if not valid_directions:
            # 이동 가능한 방향이 없으면 제자리
            return {
                "type": "move",
                "dx": 0,
                "dy": 0,
                "x": self.current_x,
                "y": self.current_y
            }
        
        # 미탐험 지역 우선
        unexplored = []
        explored = []
        
        for dx, dy in valid_directions:
            new_pos = (self.current_x + dx, self.current_y + dy)
            if new_pos not in self.explored_positions:
                unexplored.append((dx, dy))
            else:
                explored.append((dx, dy))
        
        # 전투 회피 체크
        if self._should_avoid_combat():
            # 적이 있는 방향 제외
            safe_directions = []
            for dx, dy in (unexplored if unexplored else explored):
                new_pos = (self.current_x + dx, self.current_y + dy)
                if new_pos not in self.nearby_enemies:
                    safe_directions.append((dx, dy))
            
            if safe_directions:
                dx, dy = random.choice(safe_directions)
            elif unexplored:
                dx, dy = random.choice(unexplored)
            elif explored:
                dx, dy = random.choice(explored)
            else:
                dx, dy = random.choice(valid_directions)
        else:
            # 미탐험 지역 우선, 없으면 탐험된 지역
            if unexplored:
                dx, dy = random.choice(unexplored)
            elif explored:
                dx, dy = random.choice(explored)
            else:
                dx, dy = random.choice(valid_directions)
        
        new_x = self.current_x + dx
        new_y = self.current_y + dy
        
        return {
            "type": "move",
            "dx": dx,
            "dy": dy,
            "x": new_x,
            "y": new_y
        }
    
    def _is_area_fully_explored(self) -> bool:
        """현재 위치 주변 구역이 완전히 탐험되었는지 확인 (맵 밝힘 + 파밍 완료)"""
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return False
        
        dungeon = exploration.dungeon
        radius = 8  # 확인 반경 증가 (더 넓은 범위 확인)
        
        # 현재 위치가 속한 방 찾기
        current_room = None
        for room in dungeon.rooms:
            if (room.x1 <= self.current_x < room.x2 and 
                room.y1 <= self.current_y < room.y2):
                current_room = room
                break
        
        # 주변 타일 확인
        checked_count = 0
        explored_count = 0
        has_unexplored = False
        has_unharvested = False
        
        check_positions = []
        
        # 현재 방이 있으면 방 내부만 확인, 없으면 반경 내 확인
        if current_room:
            # 방 내부 모든 타일 확인
            for y in range(current_room.y1, current_room.y2):
                for x in range(current_room.x1, current_room.x2):
                    check_positions.append((x, y))
        else:
            # 반경 내 타일 확인
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    check_positions.append((self.current_x + dx, self.current_y + dy))
        
        # 각 위치 확인
        for check_x, check_y in check_positions:
            # 맵 범위 체크
            if not (0 <= check_x < dungeon.width and 0 <= check_y < dungeon.height):
                continue
            
            # 이동 불가능한 타일은 무시
            if not dungeon.is_walkable(check_x, check_y):
                continue
            
            checked_count += 1
            
            # 던전 타일의 explored 상태 확인 (실제 탐험 상태)
            tile = dungeon.get_tile(check_x, check_y)
            if tile and tile.explored:
                explored_count += 1
                # 봇의 explored_positions에도 추가 (동기화)
                if (check_x, check_y) not in self.explored_positions:
                    self.explored_positions.add((check_x, check_y))
            else:
                # 탐험하지 않은 타일 발견
                has_unexplored = True
                continue  # 탐험 안 된 곳이 있으면 채집 확인 불필요
            
            # 채집물 확인 (이 봇이 아직 채집하지 않은 채집물이 있는지)
            from src.gathering.harvestable import HarvestableType
            for harvestable in dungeon.harvestables:
                if (harvestable.x == check_x and harvestable.y == check_y and
                    harvestable.object_type != HarvestableType.COOKING_POT and
                    harvestable.can_harvest(self.bot_id)):
                    has_unharvested = True
                    break
        
        # 확인한 타일이 없으면 완료된 것으로 간주하지 않음
        if checked_count == 0:
            return False
        
        # 탐험되지 않은 타일이 있으면 미완료
        if has_unexplored:
            return False
        
        # 채집하지 않은 채집물이 있으면 미완료
        if has_unharvested:
            return False
        
        # 모든 타일을 탐험하고 채집 완료
        # 적어도 5개 이상의 타일을 확인했고, 모두 탐험된 경우에만 완료로 간주
        return checked_count >= 5 and explored_count == checked_count
    
    def _move_away_from_completed_area(self) -> Dict[str, Any]:
        """탐험 완료한 구역에서 멀리 떠나기 (A* 알고리즘 사용)"""
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return {
                "type": "move",
                "dx": 0,
                "dy": 0,
                "x": self.current_x,
                "y": self.current_y
            }
        
        dungeon = exploration.dungeon
        
        # 1순위: 미탐험 지역으로 이동 (A* 경로 사용)
        unexplored_target = None
        max_search_distance = 25  # 더 멀리 있는 미탐험 지역도 찾기
        closest_distance = float('inf')
        
        # 현재 위치 주변에서 미탐험 지역 찾기
        for y in range(max(0, self.current_y - max_search_distance), 
                      min(dungeon.height, self.current_y + max_search_distance + 1)):
            for x in range(max(0, self.current_x - max_search_distance),
                          min(dungeon.width, self.current_x + max_search_distance + 1)):
                # 이동 가능한 타일만 확인
                if not dungeon.is_walkable(x, y):
                    continue
                
                # 잠긴 문 제외
                from src.world.tile import TileType
                tile = dungeon.get_tile(x, y)
                if tile and tile.tile_type == TileType.LOCKED_DOOR:
                    continue
                
                # 탐험하지 않은 곳 찾기
                if not tile or not tile.explored:
                    # 봇이 이미 방문한 곳도 제외 (explored_positions)
                    if (x, y) not in self.explored_positions:
                        distance = abs(x - self.current_x) + abs(y - self.current_y)
                        if distance < closest_distance:
                            closest_distance = distance
                            unexplored_target = (x, y)
        
        # 미탐험 지역이 있으면 A* 경로로 이동
        if unexplored_target:
            path = self._find_exploration_path(
                (self.current_x, self.current_y),
                unexplored_target,
                dungeon,
                exploration
            )
            
            if path and len(path) > 0:
                # 경로의 첫 번째 위치로 이동
                next_x, next_y = path[0]
                dx = next_x - self.current_x
                dy = next_y - self.current_y
                
                # 이동 가능 여부 최종 확인
                if (0 <= next_x < dungeon.width and 
                    0 <= next_y < dungeon.height and
                    dungeon.is_walkable(next_x, next_y)):
                    return {
                        "type": "move",
                        "dx": dx,
                        "dy": dy,
                        "x": next_x,
                        "y": next_y
                    }
        
        # 2순위: 계단 위치로 이동 (A* 경로 사용)
        target_positions = []
        if dungeon.stairs_down:
            target_positions.append(dungeon.stairs_down)
        if dungeon.stairs_up:
            target_positions.append(dungeon.stairs_up)
        
        if target_positions:
            closest_stairs = None
            closest_distance = float('inf')
            
            for stairs_x, stairs_y in target_positions:
                distance = abs(stairs_x - self.current_x) + abs(stairs_y - self.current_y)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_stairs = (stairs_x, stairs_y)
            
            if closest_stairs:
                # A* 경로로 계단까지 이동
                path = self._find_exploration_path(
                    (self.current_x, self.current_y),
                    closest_stairs,
                    dungeon,
                    exploration
                )
                
                if path and len(path) > 0:
                    # 경로의 첫 번째 위치로 이동
                    next_x, next_y = path[0]
                    dx = next_x - self.current_x
                    dy = next_y - self.current_y
                    
                    # 이동 가능 여부 최종 확인
                    if (0 <= next_x < dungeon.width and 
                        0 <= next_y < dungeon.height and
                        dungeon.is_walkable(next_x, next_y)):
                        return {
                            "type": "move",
                            "dx": dx,
                            "dy": dy,
                            "x": next_x,
                            "y": next_y
                        }
                
                # A* 경로를 찾지 못했으면 방향 기반 이동 (폴백)
                stairs_x, stairs_y = closest_stairs
                dx = 1 if stairs_x > self.current_x else (-1 if stairs_x < self.current_x else 0)
                dy = 1 if stairs_y > self.current_y else (-1 if stairs_y < self.current_y else 0)
                
                # 대각선 이동 방지
                if dx != 0 and dy != 0:
                    if random.random() < 0.5:
                        dx = 0
                    else:
                        dy = 0
                
                new_x = self.current_x + dx
                new_y = self.current_y + dy
                
                # 이동 가능 여부 확인
                if (0 <= new_x < dungeon.width and 
                    0 <= new_y < dungeon.height and
                    dungeon.is_walkable(new_x, new_y)):
                    return {
                        "type": "move",
                        "dx": dx,
                        "dy": dy,
                        "x": new_x,
                        "y": new_y
                    }
        
        # 3순위: 다른 방으로 이동 (현재 방이 아닌 다른 방 찾기)
        current_room = None
        for room in dungeon.rooms:
            if (room.x1 <= self.current_x < room.x2 and 
                room.y1 <= self.current_y < room.y2):
                current_room = room
                break
        
        if current_room:
            # 다른 방 찾기
            for room in dungeon.rooms:
                if room == current_room:
                    continue
                
                # 다른 방의 중심으로 이동
                room_center_x = (room.x1 + room.x2) // 2
                room_center_y = (room.y1 + room.y2) // 2
                
                # 방 중심 방향으로 이동
                dx = 1 if room_center_x > self.current_x else (-1 if room_center_x < self.current_x else 0)
                dy = 1 if room_center_y > self.current_y else (-1 if room_center_y < self.current_y else 0)
                
                # 대각선 이동 방지
                if dx != 0 and dy != 0:
                    if random.random() < 0.5:
                        dx = 0
                    else:
                        dy = 0
                
                new_x = self.current_x + dx
                new_y = self.current_y + dy
                
                # 이동 가능 여부 확인
                if (0 <= new_x < dungeon.width and 
                    0 <= new_y < dungeon.height and
                    dungeon.is_walkable(new_x, new_y)):
                    # 잠긴 문 확인
                    from src.world.tile import TileType
                    tile = dungeon.get_tile(new_x, new_y)
                    if tile and tile.tile_type != TileType.LOCKED_DOOR:
                        return {
                            "type": "move",
                            "dx": dx,
                            "dy": dy,
                            "x": new_x,
                            "y": new_y
                        }
        
        # 4순위: 랜덤하게 멀리 이동 (탐험한 곳이 아닌 곳 우선)
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(directions)
        
        for dx, dy in directions:
            # 여러 타일 떨어진 곳 시도
            for distance in range(1, 5):  # 1~4타일 떨어진 곳 시도
                new_x = self.current_x + dx * distance
                new_y = self.current_y + dy * distance
                
                # 이동 가능 여부 확인
                if (0 <= new_x < dungeon.width and 
                    0 <= new_y < dungeon.height and
                    dungeon.is_walkable(new_x, new_y)):
                    # 잠긴 문 확인
                    from src.world.tile import TileType
                    tile = dungeon.get_tile(new_x, new_y)
                    if tile and tile.tile_type != TileType.LOCKED_DOOR:
                        # 1타일씩 이동 (실제 이동)
                        return {
                            "type": "move",
                            "dx": dx,
                            "dy": dy,
                            "x": self.current_x + dx,
                            "y": self.current_y + dy
                        }
        
        # 이동할 수 없으면 제자리
        return {
            "type": "move",
            "dx": 0,
            "dy": 0,
            "x": self.current_x,
            "y": self.current_y
        }
    
    def _get_help_message(self) -> str:
        """도움말 메시지 생성"""
        return (
            "=== 봇 명령어 목록 ===\n"
            "[1] 도움 요청: 봇이 도움말을 출력합니다.\n"
            "[2] 아이템 확인: 봇의 인벤토리를 확인 요청합니다.\n"
            "[3] 아이템 요청: 봇에게 아이템 공유를 요청합니다.\n"
            "[4] 골드 요청: 봇에게 골드 공유를 요청합니다.\n"
            "[5] 탐험 모드: 봇이 자유롭게 탐험하며 파밍합니다.\n"
            "[6] 따라오기: 봇이 플레이어를 따라다닙니다.\n"
            "[7] 전투 회피 토글: 적을 피하거나 공격적으로 변합니다.\n"
            "[8] 파밍하며 이동: 이동 경로상의 자원을 적극적으로 채집합니다.\n"
            "[9] 위치 공유: 봇이 현재 위치를 채팅으로 알립니다.\n"
            "[0] 대기: 봇이 현재 위치에서 대기합니다."
        )

    def execute_command(self, command: BotCommand, target_player_id: Optional[str] = None):
        """
        명령 실행
        
        Args:
            command: 명령 타입
            target_player_id: 대상 플레이어 ID (있는 경우)
        """
        current_time = time.time()
        
        # 쿨타임 체크 (FOLLOW_PLAYER 명령은 쿨타임 없이 항상 처리 가능)
        if command != BotCommand.FOLLOW_PLAYER:
            if command in self.command_cooldown:
                if current_time - self.command_cooldown[command] < 5.0:  # 5초 쿨타임
                    return
            
            self.command_cooldown[command] = current_time
        
        if command == BotCommand.HELP_REQUEST:
            self.logger.info(f"봇 {self.bot_name} 도움 요청")
            # 채팅 메시지로 도움 요청 및 도움말 출력
            self._send_chat_message(self._get_help_message())
            
            # 로컬 플레이어의 로그에도 표시 (호스트인 경우)
            if self.is_host and self.session:
                # message_log 시스템이 있다면 추가
                pass
        
        elif command == BotCommand.SHOW_INVENTORY:
            self.logger.info(f"봇 {self.bot_name} 아이템 확인 요청")
            self._send_chat_message(f"{self.bot_name}: 아이템을 확인해주세요")
        
        elif command == BotCommand.ITEM_REQUEST:
            self.logger.info(f"봇 {self.bot_name} 아이템 요청")
            self._send_chat_message(f"{self.bot_name}: 아이템을 공유해주세요")
        
        elif command == BotCommand.GOLD_REQUEST:
            self.logger.info(f"봇 {self.bot_name} 골드 요청")
            self._send_chat_message(f"{self.bot_name}: 골드를 공유해주세요")
        
        elif command == BotCommand.EXPLORATION_REQUEST:
            # 탐험 모드로 전환
            self.behavior = BotBehavior.EXPLORER
            self.target_position = None  # 목표 위치 초기화
            self.path_to_target = []  # 경로 초기화
            self.logger.info(f"봇 {self.bot_name} 탐험 모드로 전환")
            self._send_chat_message(f"{self.bot_name}: 탐험 모드로 전환했습니다!")
        
        elif command == BotCommand.FOLLOW_PLAYER:
            # FOLLOW_PLAYER 명령은 쿨타임 없이 항상 위치 업데이트 가능하도록 처리
            # (이미 FOLLOW 모드인 경우에도 위치를 업데이트)
            
            # 로컬 플레이어 위치 찾기
            target_pos = None
            
            # 1. nearby_players에서 찾기 (최신 위치 확인)
            if target_player_id and target_player_id in self.nearby_players:
                target_pos = self.nearby_players[target_player_id]
            
            # 2. 세션에서 플레이어 위치 찾기 (가장 최신 위치)
            if target_player_id and self.session:
                if target_player_id in self.session.players:
                    player = self.session.players[target_player_id]
                    if hasattr(player, 'x') and hasattr(player, 'y'):
                        new_pos = (int(player.x), int(player.y))
                        # nearby_players에도 업데이트
                        self.nearby_players[target_player_id] = new_pos
                        target_pos = new_pos
            
            # 3. exploration 시스템에서 로컬 플레이어 위치 찾기
            if not target_pos:
                exploration = self._get_exploration_system()
                if exploration and hasattr(exploration, 'player'):
                    new_pos = (exploration.player.x, exploration.player.y)
                    if target_player_id:
                        self.nearby_players[target_player_id] = new_pos
                    target_pos = new_pos
            
            if target_pos:
                # 위치 업데이트 (이미 FOLLOW 모드여도 위치를 갱신)
                old_pos = self.target_position
                self.target_position = target_pos
                self.behavior = BotBehavior.FOLLOW
                # 경로 초기화 (새 목표로 경로 재계산)
                self.path_to_target = []
                
                if old_pos != target_pos:
                    self.logger.info(f"봇 {self.bot_name} 플레이어 {target_player_id or '로컬 플레이어'} 따라가기 위치 업데이트: {old_pos} -> {target_pos}")
                else:
                    self.logger.info(f"봇 {self.bot_name} 플레이어 {target_player_id or '로컬 플레이어'} 따라가기 시작 (목표 위치: {target_pos})")
                    self._send_chat_message(f"{self.bot_name}: 따라가겠습니다!")
            else:
                self.logger.warning(f"봇 {self.bot_name} 따라갈 플레이어 위치를 찾을 수 없습니다.")
                self._send_chat_message(f"{self.bot_name}: 따라갈 플레이어를 찾을 수 없습니다.")
        
        elif command == BotCommand.AVOID_COMBAT:
            # 전투 회피 모드 토글
            self.combat_avoidance_active = not self.combat_avoidance_active
            if self.combat_avoidance_active:
                self.logger.info(f"봇 {self.bot_name} 전투 회피 모드 활성화")
                self._send_chat_message(f"{self.bot_name}: 전투 회피 모드 활성화")
            else:
                self.logger.info(f"봇 {self.bot_name} 전투 회피 모드 비활성화")
                self._send_chat_message(f"{self.bot_name}: 전투 회피 모드 비활성화")

        elif command == BotCommand.FARM_AND_FOLLOW:
            # 파밍하며 따라가기
            self.behavior = BotBehavior.FOLLOW
            self.current_mode = "farm"  # 파밍 모드 플래그 (활용 필요)
            
            # 타겟 설정은 FOLLOW_PLAYER와 동일하게 처리 필요하지만 여기선 생략
            self._send_chat_message(f"{self.bot_name}: 이동하며 적극적으로 파밍합니다!")

        elif command == BotCommand.GATHER_RESOURCES:
            # 주변 자원 수집
            self.behavior = BotBehavior.EXPLORER
            self._send_chat_message(f"{self.bot_name}: 주변 자원을 수집합니다.")
            
            # 즉시 스캔 시도
            farmable = self._scan_for_farmable_items()
            if farmable:
                target = farmable[0]
                if self.communication.claim_item(target["position"], self.bot_id):
                    self.task_queue.add_task(
                        TaskType.FARM, 
                        priority=target["priority"], 
                        data=target
                    )

        elif command == BotCommand.SHARE_LOCATION:
            # 위치 공유
            pos = (self.current_x, self.current_y)
            self.communication.set_shared_location(f"{self.bot_name}_loc", pos, self.bot_id)
            self._send_chat_message(f"{self.bot_name}: 현재 위치 {pos} 공유했습니다.")
            
        elif command == BotCommand.HOLD_POSITION:
            # 대기
            self.behavior = BotBehavior.PASSIVE
            self.path_to_target = []
            self.target_position = None
            self._send_chat_message(f"{self.bot_name}: 대기합니다.")
            
        elif command == BotCommand.SCOUT_AREA:
            # 정찰
            self.behavior = BotBehavior.EXPLORER
            self._send_chat_message(f"{self.bot_name}: 주변을 정찰합니다.")

    
    def _send_chat_message(self, message: str):
        """채팅 메시지 전송"""
        try:
            chat_msg = MessageBuilder.chat_message(
                player_id=self.bot_id,
                message=message
            )
            
            # 1. 호스트에게 전송
            if not self.network_manager.is_host:
                self.network_manager.send(chat_msg)
            else:
                # 호스트인 경우 브로드캐스트
                self.network_manager.broadcast(chat_msg)
                
                # 2. 호스트의 로컬 채팅창(UI)에도 메시지 추가 (중요)
                # 이벤트 버스를 통해 UI에 알림
                event_bus.publish(Events.CHAT_MESSAGE_RECEIVED, {
                    "player_id": self.bot_id,
                    "message": message,
                    "player_name": self.bot_name
                })
                
                if hasattr(self.session, 'add_chat_message'):
                    self.session.add_chat_message(self.bot_id, message)
                else:
                    # 세션에 직접 추가할 수 없다면, 이벤트 큐나 콜백을 찾아야 함
                    # 여기서는 game_state나 ui_manager 접근을 시도
                    pass

        except Exception as e:
            self.logger.error(f"채팅 메시지 전송 실패: {e}", exc_info=True)
    
        # 시야 내 채집물 자동 채집 처리 (이동 없이)
        self._auto_harvest_in_vision()

    def _auto_harvest_in_vision(self):
        """시야 내 채집물 자동 채집 (이동 불필요)"""
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return
            
        # 이미 채집한 목록 (블랙리스트) 확인
        # 시야 범위 (기본 8칸)
        vision_range = 8
        current_x, current_y = self.current_x, self.current_y
        
        # 주변 탐색 (네트워크 통신 기반이 더 효율적이지만, 로컬 시뮬레이션에서는 직접 확인)
        # 1. 미수집 아이템 (CommunicationNetwork 활용)
        unclaimed = self.communication.get_nearest_unclaimed_item((current_x, current_y), self.bot_id)
        if unclaimed:
            pos, item = unclaimed
            dist = max(abs(pos[0] - current_x), abs(pos[1] - current_y)) # Chebyshev distance
            
            # 시야 내에 있으면 즉시 획득 (이동 없이)
            if dist <= vision_range:
                if pos not in self.harvested_blacklist:
                    self.logger.info(f"봇 {self.bot_name} 시야 내 아이템 자동 획득: {getattr(item, 'name', 'Unknown')} at {pos}")
                    
                    # 인벤토리 추가
                    inventory = self._get_bot_inventory()
                    if inventory:
                        inventory.add_item(item, quantity=1)
                        
                    # 네트워크 동기화 및 정리
                    self.communication.claim_item(pos, self.bot_id)
                    self.communication.remove_item(pos)
                    self.harvested_blacklist.add(pos)
                    
                    # 시각적 효과 (선택사항)
                    self._send_chat_message(f"아이템을 발견해서 챙겼어! ({getattr(item, 'name', 'Unknown')})")

        # 2. 자원 노드 (직접 탐색)
        if hasattr(exploration.dungeon, 'harvestables'):
            for harvestable in exploration.dungeon.harvestables:
                # 위치 확인
                h_x, h_y = harvestable.x, harvestable.y
                pos = (h_x, h_y)
                
                if pos in self.harvested_blacklist:
                    continue
                    
                # 거리 계산
                dist = max(abs(h_x - current_x), abs(h_y - current_y))
                
                if dist <= vision_range:
                    # 채집 가능 여부 확인
                    if harvestable.can_harvest(self.bot_id):
                        # 즉시 채집
                        results = harvestable.harvest(self.bot_id)
                        if results:
                            self.logger.info(f"봇 {self.bot_name} 시야 내 자원 자동 채집: {harvestable.object_type.display_name} at {pos}")
                            
                            # 인벤토리 추가
                            inventory = self._get_bot_inventory()
                            if inventory:
                                for item_id, qty in results.items():
                                    # 아이템 ID로 아이템 객체 생성 필요 (여기선 생략하고 로그만)
                                    # 실제 구현 시 IngredientDatabase 사용
                                    pass
                            
                            # 블랙리스트 추가
                            self.harvested_blacklist.add(pos)
                            self.communication.unclaim_item(pos, self.bot_id)
                            
                            # 상호작용 효과 처리 (한 번만)
                            if hasattr(exploration, 'handle_interaction'):
                                exploration.handle_interaction(h_x, h_y, self.bot_id)

    def _scan_for_farmable_items(self) -> List[Dict[str, Any]]:
        """주변 파밍 가능한 아이템 스캔"""
        
        # 블랙리스트 정리 (일정 시간 지나면 초기화)
        import time
        current_time = time.time()
        if current_time - self.blacklist_clear_time > 60.0: # 1분마다 초기화
            self.logger.debug(f"봇 {self.bot_name} 블랙리스트 초기화 (크기: {len(self.harvested_blacklist)})")
            self.harvested_blacklist.clear()
            self.blacklist_clear_time = current_time
            
        farmable_items = []
        
        # 1. 통신 네트워크에서 미수집 아이템 확인 (드롭된 아이템 등)
        current_pos = (self.current_x, self.current_y)
        nearest_item = self.communication.get_nearest_unclaimed_item(
            current_pos, self.bot_id
        )
        
        if nearest_item:
            pos, item = nearest_item
            
            # 블랙리스트 확인
            if pos not in self.harvested_blacklist:
                self.logger.debug(f"봇 {self.bot_name} 아이템 발견: {getattr(item, 'name', 'Unknown')} at {pos}")
                farmable_items.append({
                    "type": "item",
                    "position": pos,
                    "object": item,
                    "priority": 10
                })
            else:
                self.logger.debug(f"봇 {self.bot_name} 아이템 {pos} 블랙리스트에 있어 무시")
            
        # 2. 자원 노드 확인 - 봇은 채집(이동 필요)을 하지 않고 시야 내 자동 채집으로 처리하므로 여기서는 제외
        # (단, 특수 상호작용이 필요한 경우 예외)
        # nearby_resources = self.communication.get_nearby_resources(current_pos)
        # for pos, node_data in nearby_resources:
        #     # ...
            
        return farmable_items

    def _plan_farming_route(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """파밍 경로 계획 (단순 A*가 아닌 경유지 포함)"""
        # 기본적으로는 end로 가되, 가는 길에 있는 아이템을 들르도록
        # 현재는 단순하게 end로 가는 경로 반환 (향후 개선)
        return self._find_path(start, end)

    def _execute_farming_action(self, target: Dict[str, Any]):
        """파밍 액션 수행"""
        target_pos = target["position"]
        
        # 이동 및 접근 체크 (_move_to_interact 활용)
        # _move_to_interact는 인접하면 True, 이동 중이면 True(이동 명령 내림), 접근 불가면 False 반환
        if not self._move_to_interact(target_pos[0], target_pos[1]):
            self.logger.debug(f"봇 {self.bot_name} 파밍 목표 접근 불가: {target_pos}")
            self.harvested_blacklist.add(target_pos)
            return

        # 현재 위치가 목표와 인접해 있는지 확인 (대각선 포함)
        dx = abs(self.current_x - target_pos[0])
        dy = abs(self.current_y - target_pos[1])
        # 자원 위(0,0) 또는 인접(1칸)
        if not (dx <= 1 and dy <= 1):
            # 아직 이동 중
            return

        # 도착했으면 수집 (이동 시 자동으로 수행됨)
        if target["type"] == "item" or target["type"] == "resource":
            self.logger.info(f"봇 {self.bot_name} 아이템/자원 위치 도착 및 수집 완료 처리: {target_pos}")
            
            # 1. 아이템 획득 (봇 인벤토리)
            if target.get("object") and hasattr(self, 'bot_inventory'):
                # 아이템 객체가 있으면 인벤토리에 추가 (무게 체크 등은 생략하거나 간단히)
                # 여기서는 시뮬레이션이므로 로그만 남기거나 간단히 처리
                item_name = getattr(target["object"], 'name', 'Unknown')
                self.logger.info(f"봇 {self.bot_name} 인벤토리에 추가: {item_name}")
                # self.bot_inventory.add_item(target["object"]) # 실제 구현 필요 시 추가
            
            # 2. HARVEST 메시지 전송 (네트워크 동기화)
            try:
                # 자원 타입 확인
                obj_type = "unknown"
                if target["type"] == "resource" and "data" in target:
                    obj_type = target["data"].get("type", "resource")
                elif target["type"] == "item":
                    obj_type = "item"
                
                harvest_msg = MessageBuilder.harvest(
                    x=target_pos[0],
                    y=target_pos[1],
                    object_type=obj_type
                )
                
                if not self.network_manager.is_host:
                    self.network_manager.send(harvest_msg)
                else:
                    # 호스트인 경우 브로드캐스트 및 로컬 처리
                    # (주의: 비동기 컨텍스트 확인)
                    import asyncio
                    server_loop = getattr(self.network_manager, '_server_event_loop', None)
                    if server_loop and server_loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self.network_manager.broadcast(harvest_msg),
                            server_loop
                        )
                    else:
                        self.network_manager.broadcast(harvest_msg)
                        
                    # 호스트라면 실제 던전에서도 제거 처리 (ExplorationSystem)
                    exploration = self._get_exploration_system()
                    if exploration and hasattr(exploration, 'dungeon'):
                        # 해당 위치의 harvestable을 찾아 harvested=True로 설정
                        if hasattr(exploration.dungeon, 'harvestables'):
                            for h in exploration.dungeon.harvestables:
                                if h.x == target_pos[0] and h.y == target_pos[1]:
                                    h.harvested = True
                                    break
            except Exception as e:
                self.logger.error(f"봇 채집 메시지 전송 실패: {e}", exc_info=True)

            # 3. 블랙리스트 및 통신망 정리
            # 블랙리스트에 추가 (수집 완료)
            self.harvested_blacklist.add(target_pos)
            
            # 봇 간 조정: 선점 해제 및 아이템 제거
            self.communication.unclaim_item(target_pos, self.bot_id)
            self.communication.remove_item(target_pos)
            
            # 기뻐하는 반응 (채팅) - 확률적으로
            import random
            if target.get("priority", 0) >= 10 and random.random() < 0.3:
                 self._send_chat_message(f"{self.bot_name}: 찾았다!")

    def _check_equipment_durability(self) -> bool:
        """장비 내구도 확인 (30% 미만이면 True)"""
        if not hasattr(self, 'bot_inventory') or not self.bot_inventory:
            return False
            
        inventory = self.bot_inventory
        if not hasattr(inventory, 'party') or not inventory.party:
            return False
            
        # 봇의 캐릭터 (첫 번째 멤버)
        if len(inventory.party) == 0:
            return False
            
        character = inventory.party[0]
        
        if not hasattr(character, 'equipment'):
            return False
            
        for slot, item in character.equipment.items():
            if item and hasattr(item, 'current_durability') and hasattr(item, 'max_durability'):
                if item.current_durability < item.max_durability * 0.3:
                    return True
        return False

    def _check_and_repair(self) -> Optional[Dict[str, Any]]:
        """장비 수리 행동 결정 (모루/상점 이용)"""
        # 1. 내구도 체크
        if not self._check_equipment_durability():
            return None
            
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return None
            
        dungeon = exploration.dungeon
        
        # 2. 현재 위치가 수리 가능한 곳인지 확인
        current_tile = dungeon.get_tile(self.current_x, self.current_y)
        if current_tile:
            from src.world.tile import TileType
            # 모루 (무료, 1회성)
            if current_tile.tile_type == TileType.ANVIL and not getattr(current_tile, 'used', False):
                # 즉시 수리 수행 (상호작용 불필요, 봇 특권)
                self._perform_repair(current_tile)
                return None # 행동 완료
                
            # 상점 (유료)
            elif current_tile.tile_type == TileType.SHOP:
                # 골드 확인 (최소 100G 가정)
                if self.bot_inventory.gold >= 100:
                    self._perform_repair(current_tile, use_gold=True)
                    return None

        # 3. 주변(시야 내) 수리 시설 탐색 및 이동
        repair_target = None
        min_dist = float('inf')
        
        # 시야 내 타일 스캔 (반경 15칸)
        scan_radius = 15
        for dy in range(-scan_radius, scan_radius + 1):
            for dx in range(-scan_radius, scan_radius + 1):
                nx, ny = self.current_x + dx, self.current_y + dy
                if 0 <= nx < dungeon.width and 0 <= ny < dungeon.height:
                    tile = dungeon.get_tile(nx, ny)
                    if not tile or not tile.explored:
                        continue
                        
                    from src.world.tile import TileType
                    is_target = False
                    
                    # 사용하지 않은 모루
                    if tile.tile_type == TileType.ANVIL and not getattr(tile, 'used', False):
                        is_target = True
                    # 상점 (골드 있을 때)
                    elif tile.tile_type == TileType.SHOP and self.bot_inventory.gold >= 100:
                        is_target = True
                        
                    if is_target:
                        dist = abs(self.current_x - nx) + abs(self.current_y - ny)
                        if dist < min_dist:
                            min_dist = dist
                            repair_target = (nx, ny)
                            
        if repair_target:
            # 이동 명령 반환
            tx, ty = repair_target
            self.logger.info(f"봇 {self.bot_name} 수리 시설({tx},{ty})로 이동 (내구도 부족)")
            path = self._find_path((self.current_x, self.current_y), repair_target)
            if len(path) > 1:
                next_step = path[1]
                return {"x": next_step[0], "y": next_step[1]}
                
        return None

    def _perform_repair(self, tile, use_gold=False):
        """수리 실행"""
        inventory = self.bot_inventory
        if not inventory or not inventory.party:
            return
            
        character = inventory.party[0]
        
        # 수리 대상 아이템 수집
        items = []
        for slot, item in character.equipment.items():
            if item and hasattr(item, 'current_durability'):
                items.append(item)
        # 인벤토리는 생략 (봇은 장착 장비가 중요)
                
        if not items:
            return

        if use_gold:
            # 상점 수리 (전체 수리)
            total_cost = 0
            repair_list = []
            
            for item in items:
                if not hasattr(item, 'max_durability'): continue
                missing = item.max_durability - item.current_durability
                if missing > 0:
                    # 비용 계산 (약식)
                    cost = int(missing * 2) 
                    total_cost += cost
                    repair_list.append(item)
            
            if total_cost > 0 and inventory.gold >= total_cost:
                inventory.remove_gold(total_cost)
                for item in repair_list:
                    item.current_durability = item.max_durability
                    # 스탯 업데이트 필요 시 호출
                    
                self.logger.info(f"봇 {self.bot_name} 상점에서 {len(repair_list)}개 아이템 수리 완료 (비용: {total_cost}G)")
        else:
            # 모루 수리 (가장 급한 1개)
            # 내구도 비율이 가장 낮은 아이템 선택
            repairable_items = [i for i in items if hasattr(i, 'max_durability') and i.current_durability < i.max_durability]
            
            if repairable_items:
                target_item = min(repairable_items, key=lambda i: i.current_durability / max(1, i.max_durability))
                target_item.current_durability = target_item.max_durability
                tile.used = True
                self.logger.info(f"봇 {self.bot_name} 모루에서 {target_item.name} 수리 완료")

    def _decide_next_action_intelligent(self):
        """지능형 행동 결정 (우선순위 기반)"""
        # 전투 중이거나 전투 트리거 대기 중이면 탐험/채집 로직 중단
        if self.in_combat:
            return
            
        if self.pending_combat_trigger:
            # 타임아웃 체크 (5초)
            trigger_time = self.pending_combat_trigger.get("time", 0)
            import time
            if time.time() - trigger_time > 5.0:
                self.logger.warning(f"봇 {self.bot_name} 전투 트리거 타임아웃. 상태 초기화.")
                self.pending_combat_trigger = None
                self.in_combat = False
            else:
                return
        
        # 0. 장비 수리 체크 (전투 전 최우선)
        repair_action = self._check_and_repair()
        if repair_action:
            if repair_action.get("type") == "move":
                self._execute_move(repair_action)
            return

        # 1. 전투 상황 평가 (전투 중이 아니더라도 적이 근처에 있으면)
        if self.nearby_enemies:
            combat_action = self._evaluate_combat_situation()
            if combat_action:
                self._execute_move(combat_action) # 이동으로 반영 (전투 시스템 연동 필요)
                return

        # 2. 위험 회피 (전투 회피 모드일 때)
        if self.combat_avoidance_active and self._detect_danger():
            return self._avoid_combat_action()
            
        # 3. 태스크 큐 처리
        task = self.task_queue.peek_next_task()
        if task:
            # 현재 수행 중인 작업이 없거나, 더 높은 우선순위 작업이 있다면 교체
            current_task = self.task_queue.get_next_task()
            if current_task:
                self._execute_task(current_task)
            return

        # 4. 명령 수행 (기존 pending_commands)
        if self.pending_commands:
            # 명령 가져오기 (제거하지 않고 확인만, execute_command에서 처리하거나 여기서 처리)
            # 기존 로직은 pop(0)를 했음
            command = self.pending_commands.pop(0)
            
            # FOLLOW_PLAYER 명령의 경우 로컬 플레이어 ID 전달
            target_player_id = None
            if command == BotCommand.FOLLOW_PLAYER:
                # exploration 시스템에서 로컬 플레이어 ID 가져오기
                exploration = self._get_exploration_system()
                if exploration and hasattr(exploration, 'local_player_id'):
                    target_player_id = exploration.local_player_id
                # nearby_players가 비어있으면 세션에서 로컬 플레이어 찾기
                if not target_player_id and self.session:
                    # 봇이 아닌 플레이어 중 첫 번째를 따라가기
                    for player_id, player in self.session.players.items():
                        if player_id != self.bot_id and not player_id.startswith('bot_'):
                            target_player_id = player_id
                            break
            
            self.execute_command(command, target_player_id=target_player_id)
            return
            
        # 5. 파밍 (FarmingBehavior)
        if self.behavior == BotBehavior.EXPLORER:
            # 현재 파밍 태스크가 큐에 있다면 스캔 건너뛰기 (목표 고정)
            has_farming_task = any(t.type == TaskType.FARM for t in self.task_queue.tasks)
            if has_farming_task:
                # self.logger.debug(f"봇 {self.bot_name} 파밍 진행 중이므로 스캔 건너뜀")
                return

            # 스캔 쿨타임 적용 (2초)
            import time
            if not hasattr(self, 'last_scan_time') or time.time() - self.last_scan_time > 2.0:
                self.last_scan_time = time.time()
                
                farmable = self._scan_for_farmable_items()
                if farmable:
                    target = farmable[0]
                    
                    # 중복 태스크 확인 (이미 큐에 있는지)
                    is_duplicate = False
                    for task in self.task_queue.tasks:
                        if task.type == TaskType.FARM and task.data.get("position") == target["position"]:
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        self.logger.debug(f"봇 {self.bot_name} 중복 태스크 무시: {target['position']}")
                        return

                    # 아이템 선점
                    if self.communication.claim_item(target["position"], self.bot_id):
                        self.logger.info(f"봇 {self.bot_name} 파밍 목표 설정: {target['position']}")
                        self.task_queue.add_task(
                            TaskType.FARM, 
                            priority=target["priority"], 
                            data=target
                        )
                        return

        # 6. 기본 행동 (따라가기/탐험)
        # 시야 내 자동 채집이 추가되었으므로 별도의 파밍 행동 없이 이동만 수행
        if self.behavior == BotBehavior.FOLLOW:
            self._follow_nearest_player()
        elif self.behavior == BotBehavior.EXPLORER:
            self._explore_map()
            
        # 시야 내 자동 채집 실행
        self._auto_harvest_in_vision()

    def _evaluate_combat_situation(self) -> Optional[Dict[str, Any]]:
        """전투 상황 평가"""
        # 필드에서 적을 발견했을 때의 행동 결정
        
        # 가장 가까운 적 확인
        nearest_enemy = None
        min_dist = float('inf')
        for ex, ey in self.nearby_enemies:
            dist = abs(self.current_x - ex) + abs(self.current_y - ey)
            if dist < min_dist:
                min_dist = dist
                nearest_enemy = (ex, ey)
                
        if not nearest_enemy:
            return None
            
        # 전투 시작 전 아군 상태 체크
        # 아군(봇 포함)들이 너무 멀리 있으면 대기
        exploration = self._get_exploration_system()
        if exploration and hasattr(exploration, 'session') and exploration.session:
            all_players = exploration.session.players
            nearby_allies_count = 0
            max_ally_dist = 5 # 5칸 이내를 '근처'로 간주
            
            current_pos = (self.current_x, self.current_y)
            
            for pid, p in all_players.items():
                if pid == self.bot_id:
                    continue
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    ally_dist = abs(self.current_x - p.x) + abs(self.current_y - p.y)
                    if ally_dist <= max_ally_dist:
                        nearby_allies_count += 1
            
            # 혼자이고 적과 가까우면(3칸 이내), 아군을 기다리거나 도망 (단, 적이 매우 약하면 제외)
            if nearby_allies_count == 0 and min_dist <= 3:
                # 아군의 HP/MP 상태 확인 (지능적 판단)
                allies_avg_hp = 0
                allies_count = 0
                
                for pid, p in all_players.items():
                    if hasattr(p, 'current_hp') and hasattr(p, 'max_hp'):
                        hp_ratio = p.current_hp / max(p.max_hp, 1)
                        allies_avg_hp += hp_ratio
                        allies_count += 1
                        
                avg_hp = allies_avg_hp / max(allies_count, 1)
                
                # 아군 상태가 전체적으로 나쁘면(50% 미만) 무조건 후퇴
                if avg_hp < 0.5:
                    self.logger.info(f"봇 {self.bot_name} 아군 상태 위험({avg_hp:.1%})! 전투 회피")
                    return self._avoid_combat_action()

                # 일단 아군 쪽으로 후퇴하거나 대기
                self.logger.info(f"봇 {self.bot_name} 아군 없음! 전투 전 대기/후퇴")
                # 가장 가까운 아군 찾기
                nearest_ally_pos = None
                min_ally_dist = float('inf')
                for pid, p in all_players.items():
                    if pid == self.bot_id: continue
                    if hasattr(p, 'x') and hasattr(p, 'y'):
                        d = abs(self.current_x - p.x) + abs(self.current_y - p.y)
                        if d < min_ally_dist:
                            min_ally_dist = d
                            nearest_ally_pos = (p.x, p.y)
                
                if nearest_ally_pos:
                    self.target_position = nearest_ally_pos
                    return self._get_follow_move()
                else:
                    # 아군도 없으면 도망
                    return self._avoid_combat_action()

        # 전투 회피 모드이면 도망
        if self.combat_avoidance_active:
             return self._avoid_combat_action()
             
        # 그렇지 않으면 전투 돌입 (적에게 접근하여 충돌)
        # 턴제 게임이므로 필드에서는 그냥 부딪혀서 전투 화면으로 전환하면 됨
        return self._get_move_towards_enemy(nearest_enemy)

    def _get_move_towards_enemy(self, enemy_pos: Tuple[int, int]) -> Dict[str, Any]:
        """적에게 이동 (전투 돌입)"""
        path = self._find_path((self.current_x, self.current_y), enemy_pos)
        if len(path) > 1:
             next_pos = path[1]
             return {"x": next_pos[0], "y": next_pos[1], "type": "move"}
        return None

    def _execute_task(self, task: BotTask):
        """태스크 실행"""
        # 실행 전 블랙리스트 체크 (중요: 이미 완료된 태스크 폐기)
        if task.type == TaskType.FARM:
            target_pos = task.data.get("position")
            if target_pos and target_pos in self.harvested_blacklist:
                # 이미 블랙리스트에 있는 대상은 스킵
                return

        if task.type == TaskType.FARM:
            self._execute_farming_action(task.data)
            
        elif task.type == TaskType.MOVE:
            target = task.data.get("target")
            if target:
                self._move_towards(target[0], target[1])
                
        elif task.type == TaskType.FOLLOW:
            target_id = task.data.get("target_id")
            # ...

    def _detect_danger(self) -> bool:
        """위험 감지"""
        # 주변 적 확인
        if self.nearby_enemies:
            return True
        # 위험 지역 확인
        if self.communication.is_danger_zone((self.current_x, self.current_y)):
            return True
        return False

    def _move_towards(self, target_x: int, target_y: int):
        """목표 지점으로 한 칸 이동"""
        # 목표가 바로 인접해 있으면 경로 탐색 없이 바로 이동 시도 (진동 방지)
        dx = target_x - self.current_x
        dy = target_y - self.current_y
        dist = abs(dx) + abs(dy)
        
        # 인접 여부 확인 (상하좌우 1칸 또는 대각선 1칸)
        is_adjacent = (dist == 1) or (abs(dx) == 1 and abs(dy) == 1)
        
        if is_adjacent:
            # 이동 가능 여부 확인 (중요: 갈 수 없는데 계속 시도하면 서성임 발생)
            exploration = self._get_exploration_system()
            if exploration and hasattr(exploration, 'dungeon'):
                if not exploration.dungeon.is_walkable(target_x, target_y):
                    self.logger.debug(f"봇 {self.bot_name} 인접 이동 불가 (장애물): ({target_x}, {target_y})")
                    return

            self.logger.debug(f"봇 {self.bot_name} 인접 이동 시도: ({target_x}, {target_y})")
            self._execute_move({"x": target_x, "y": target_y})
            return

        path = self._find_path((self.current_x, self.current_y), (target_x, target_y))
        if len(path) > 1:
            next_pos = path[1]
            self.logger.debug(f"봇 {self.bot_name} 경로 이동: {next_pos}")
            self._execute_move({"x": next_pos[0], "y": next_pos[1]})
        else:
             # 경로 못 찾으면 기존 방식(직선) fallback
             self.logger.debug(f"봇 {self.bot_name} 경로 없음. 직선 이동 시도")
             dx = target_x - self.current_x
             dy = target_y - self.current_y
             move_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
             move_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
             self._execute_move({"x": self.current_x + move_x, "y": self.current_y + move_y})

    def _follow_nearest_player(self):
        """가장 가까운 플레이어 따라가기"""
        # 기존 _get_follow_move 활용
        move = self._get_follow_move()
        if move:
            self._execute_move(move)

    def _explore_map(self):
        """지도 탐험"""
        # 기존 _get_improved_exploration_move 활용
        move = self._get_improved_exploration_move()
        if move:
            self._execute_move(move)
            
    def _avoid_combat_action(self):
        """전투 회피 행동"""
        # 적과 멀어지는 방향으로 이동
        exploration = self._get_exploration_system()
        if not exploration:
            return
            
        best_move = None
        max_dist = -1
        
        possible_moves = [
            (0, 1), (0, -1), (1, 0), (-1, 0)
        ]
        
        for dx, dy in possible_moves:
            nx, ny = self.current_x + dx, self.current_y + dy
            if not exploration.dungeon.is_walkable(nx, ny):
                continue
                
            # 적과의 최소 거리 계산
            min_enemy_dist = float('inf')
            for ex, ey in self.nearby_enemies:
                dist = abs(nx - ex) + abs(ny - ey)
                min_enemy_dist = min(min_enemy_dist, dist)
                
            if min_enemy_dist > max_dist:
                max_dist = min_enemy_dist
                best_move = {"x": nx, "y": ny}
                
        if best_move:
            self._execute_move(best_move)

    def _find_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """경로 찾기 (A* Safe Path 사용)"""
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return [start, end]
            
        dungeon = exploration.dungeon
        
        # _find_safe_path는 시작점을 제외한 경로를 반환함
        path = self._find_safe_path(start, end, dungeon, exploration)
        
        if not path:
            # 경로 없음
            return [start]
            
        # 시작점 포함하여 반환
        return [start] + path

    def start(self):
        """봇 시작"""
        self.is_active = True
        
        # 상태 초기화 (즉시 움직이도록)
        if self.behavior == BotBehavior.EXPLORER:
            self.target_position = None
            self.path_to_target = []
        
        # 초기 위치를 세션 플레이어에서 가져오기
        if self.session and self.bot_id in self.session.players:
            bot_player = self.session.players[self.bot_id]
            if hasattr(bot_player, 'x') and hasattr(bot_player, 'y'):
                self.current_x = bot_player.x
                self.current_y = bot_player.y
                self.logger.info(f"봇 {self.bot_name} 초기 위치 설정: ({self.current_x}, {self.current_y})")
                
                # 위치가 유효한지 확인 (벽 끼임 방지)
                self._unstuck_if_needed()
        
        # 마지막 액션 시간을 현재 시간으로 설정 (즉시 액션 가능하도록)
        import time
        self.last_action_time = time.time() - self.action_interval  # 즉시 액션 가능하도록
        
        self.logger.info(f"고급 AI 봇 {self.bot_name} 시작 (행동: {self.behavior.value}, 호스트: {self.is_host}, 위치: ({self.current_x}, {self.current_y}))")

    def _unstuck_if_needed(self):
        """벽에 끼어있으면 탈출"""
        exploration = self._get_exploration_system()
        if not exploration or not hasattr(exploration, 'dungeon'):
            return
            
        dungeon = exploration.dungeon
        
        # 현재 위치가 이동 불가능하면
        if not (0 <= self.current_x < dungeon.width and 
                0 <= self.current_y < dungeon.height and
                dungeon.is_walkable(self.current_x, self.current_y)):
            
            self.logger.warning(f"봇 {self.bot_name} 벽 끼임 감지! ({self.current_x}, {self.current_y})")
            
            # 주변 탐색 (반경 5칸)
            for r in range(1, 6):
                for dx in range(-r, r+1):
                    for dy in range(-r, r+1):
                        nx, ny = self.current_x + dx, self.current_y + dy
                        
                        if (0 <= nx < dungeon.width and 
                            0 <= ny < dungeon.height and
                            dungeon.is_walkable(nx, ny)):
                            
                            # 이동 가능한 위치 발견
                            self.current_x = nx
                            self.current_y = ny
                            
                            # 세션 업데이트
                            if self.session and self.bot_id in self.session.players:
                                bot_player = self.session.players[self.bot_id]
                                bot_player.x = nx
                                bot_player.y = ny
                                
                            self.logger.info(f"봇 {self.bot_name} 탈출 성공: ({nx}, {ny})")
                            return
                            
            # 주변에서도 못 찾으면 플레이어 근처로 이동
            if self.nearby_players:
                for pid, pos in self.nearby_players.items():
                    nx, ny = pos
                    if dungeon.is_walkable(nx, ny):
                        self.current_x = nx
                        self.current_y = ny
                        self.logger.info(f"봇 {self.bot_name} 플레이어 {pid} 근처로 탈출: ({nx}, {ny})")
                        return
                        
            # 그래도 안되면 시작 지점(계단 등)으로
            if dungeon.stairs_up:
                self.current_x, self.current_y = dungeon.stairs_up
                self.logger.info(f"봇 {self.bot_name} 시작 지점으로 탈출: {dungeon.stairs_up}")
    
    def stop(self):
        """봇 중지"""
        self.is_active = False
        self.logger.info(f"고급 AI 봇 {self.bot_name} 중지")
    
    def update(self, current_time: float):
        """봇 업데이트"""
        if not self.is_active:
            self.logger.debug(f"봇 {self.bot_name} 비활성화 상태")
            return
        
        # 현재 위치를 세션 플레이어와 동기화
        if self.session and self.bot_id in self.session.players:
            bot_player = self.session.players[self.bot_id]
            if hasattr(bot_player, 'x') and hasattr(bot_player, 'y'):
                # 세션 플레이어 위치가 더 최신인 경우 업데이트
                # 단, 봇이 최근에 이동 명령을 보냈다면(1초 이내) 롤백 방지를 위해 스킵
                time_since_action = current_time - self.last_action_time
                if time_since_action > 1.0 and (bot_player.x != self.current_x or bot_player.y != self.current_y):
                    old_pos = (self.current_x, self.current_y)
                    self.current_x = bot_player.x
                    self.current_y = bot_player.y
                    self.logger.debug(f"봇 {self.bot_name} 위치 동기화: {old_pos} -> ({self.current_x}, {self.current_y})")
        
        # 1순위: 전투 중인지 확인 (최우선 차단)
        if self.in_combat:
            # 전투 중에는 필드 이동 로직 수행하지 않음
            return

        # 2순위: 장비 자동 관리 (주기적 체크)
        if self.auto_equip_enabled and current_time - self.last_equip_check_time >= self.equip_check_interval:
            try:
                self._auto_manage_equipment()
                self.last_equip_check_time = current_time
            except Exception as e:
                self.logger.error(f"봇 장비 자동 관리 실패: {e}", exc_info=True)
        
        # 아이템 자동 사용 (매 액션마다 체크)
        if self.auto_use_items:
            try:
                self._check_and_use_items()
            except Exception as e:
                self.logger.error(f"봇 아이템 자동 사용 실패: {e}", exc_info=True)
        
        # 전투 아이템 사용 (전투 중)
        if self.in_combat:
            try:
                self._use_combat_items()
            except Exception as e:
                self.logger.error(f"봇 전투 아이템 사용 실패: {e}", exc_info=True)
        
        # 인벤토리 자동 정리 (매 액션마다 체크)
        if self.auto_cleanup_inventory:
            try:
                self._optimize_inventory()
            except Exception as e:
                self.logger.error(f"봇 인벤토리 정리 실패: {e}", exc_info=True)
        
        # 액션 간격 체크
        time_since_last_action = current_time - self.last_action_time
        if time_since_last_action < self.action_interval:
            return
        
        self.last_action_time = current_time
        
        # 다음 액션 간격을 랜덤하게 설정 (0.25 ~ 0.55초) - 인간적인 반응 속도 및 불규칙성 부여
        import random
        self.action_interval = random.uniform(0.25, 0.55)
        
        # 지능형 행동 결정
        self._decide_next_action_intelligent()
    
    def get_difficulty(self) -> str:
        """난이도 가져오기 (봇은 항상 보통)"""
        return self.difficulty
    
    def handle_command_key(self, key: str) -> bool:
        """
        명령 키 처리 (숫자 키)
        
        Args:
            key: 눌린 키 ('1', '2', '3', ...)
        
        Returns:
            명령 처리 여부
        """
        command_map = {
            '1': BotCommand.HELP_REQUEST,
            '2': BotCommand.SHOW_INVENTORY,  # ITEM_CHECK -> SHOW_INVENTORY
            '3': BotCommand.ITEM_REQUEST,
            '4': BotCommand.GOLD_REQUEST,
            '5': BotCommand.EXPLORATION_REQUEST,
            '6': BotCommand.FOLLOW_PLAYER,
            '7': BotCommand.AVOID_COMBAT,
            '8': BotCommand.FARM_AND_FOLLOW,
            '9': BotCommand.SHARE_LOCATION,
            '0': BotCommand.HOLD_POSITION,
        }
        
        command = command_map.get(key)
        if command:
            self.pending_commands.append(command)
            self.logger.info(f"봇 {self.bot_name} 명령 수신: {command.value} (키: {key})")
            
            # SHOW_INVENTORY는 즉시 처리 (UI 열기)
            if command == BotCommand.SHOW_INVENTORY:
                self._handle_show_inventory()
                return True
            
            return True
        
        return False

    def _handle_show_inventory(self):
        """봇 인벤토리 보여주기 (UI 열기 요청)"""
        # 이 메서드는 봇 내부에서 호출되지만, 실제 UI를 여는 것은 WorldUI에서 처리해야 함
        # 따라서 여기서는 로그만 남기고, WorldUI에서 handle_command_key의 반환값을 활용하거나
        # 봇 상태에 'inventory_open_requested' 플래그를 설정하여 UI가 감지하게 해야 함.
        
        # 하지만 구조상 WorldUI가 handle_command_key를 호출하고 있으므로, 
        # WorldUI에서 직접 처리하는 것이 더 깔끔함.
        # 여기서는 봇이 "알겠습니다, 인벤토리를 보여드릴게요"라고 말하는 정도만 수행
        self._send_chat_message(f"{self.bot_name}: 인벤토리를 보여드릴게요.")
    
    def _decide_action(self) -> Optional[Dict[str, Any]]:
        """행동 결정"""
        # 가끔은 주위를 살피며 멈칫하기 (인간적인 행동)
        import random
        # 기본 5% 확률로 잠시 대기 (생각하는 듯한 연출)
        pause_chance = 0.05
        
        # 최근에 이동을 계속 했으면(피로도 개념) 잠시 멈출 확률 증가
        if hasattr(self, 'recent_positions') and len(self.recent_positions) >= 8:
             # 같은 곳을 맴돌고 있다면(서성임) 멈추지 말고 움직여야 하므로 체크
             unique_pos = set(self.recent_positions)
             if len(unique_pos) > 4: # 활발히 움직인 경우
                 pause_chance = 0.12
        
        if random.random() < pause_chance:
            return None
        
        # 우선순위 1: 요리솥이 있고 재료가 있으면 요리
        cook_action = self._check_and_cook()
        if cook_action:
            return cook_action
        
        # 우선순위 2: 채집 가능한 것이 있으면 채집
        harvest_action = self._check_and_harvest()
        if harvest_action:
            return harvest_action
        
        # 우선순위 3: 드롭된 아이템/골드가 있으면 줍기
        pickup_action = self._check_and_pickup()
        if pickup_action:
            return pickup_action
        
        # 우선순위 4: 이동
        if self.behavior == BotBehavior.EXPLORER:
            return self._get_improved_exploration_move()
        elif self.behavior == BotBehavior.FOLLOW:
            if self.target_position:
                return self._get_follow_move()
            else:
                return self._get_improved_exploration_move()
        elif self.behavior == BotBehavior.AGGRESSIVE:
            # 적을 찾아 이동 (현재는 탐험)
            return self._get_improved_exploration_move()
        else:
            return self._get_improved_exploration_move()
    
    def _get_follow_move(self) -> Dict[str, Any]:
        """따라다니기 이동 (A* 길찾기 알고리즘 사용)"""
        # 목표 위치가 없으면 탐험 모드로 전환
        if not self.target_position:
            self.behavior = BotBehavior.EXPLORER
            self.path_to_target = []
            return self._get_improved_exploration_move()
        
        # 목표 위치를 최신화 (플레이어가 이동했을 수 있음)
        target_x, target_y = self.target_position
        target_changed = False
        
        # nearby_players나 세션에서 최신 위치 확인
        exploration = self._get_exploration_system()
        
        # 0. exploration.player 직접 확인 (가장 확실한 로컬 플레이어 위치)
        if exploration and hasattr(exploration, 'player'):
            # 로컬 플레이어 위치
            local_pos = (exploration.player.x, exploration.player.y)
            if local_pos != self.target_position:
                target_x, target_y = local_pos
                self.target_position = local_pos
                target_changed = True
                # self.logger.debug(f"봇 {self.bot_name} 따라가기 목표 위치(로컬) 업데이트: {local_pos}")

        if exploration and hasattr(exploration, 'local_player_id'):
            local_player_id = exploration.local_player_id
            # nearby_players에서 최신 위치 확인
            if local_player_id in self.nearby_players:
                new_pos = self.nearby_players[local_player_id]
                if new_pos != self.target_position:
                    target_x, target_y = new_pos
                    self.target_position = new_pos
                    target_changed = True
                    self.logger.debug(f"봇 {self.bot_name} 따라가기 목표 위치 업데이트: {new_pos}")
        
        # 세션에서도 최신 위치 확인
        if self.session:
            for player_id, player in self.session.players.items():
                if player_id != self.bot_id and not player_id.startswith('bot_'):
                    if hasattr(player, 'x') and hasattr(player, 'y'):
                        new_pos = (int(player.x), int(player.y))
                        if new_pos != self.target_position:
                            target_x, target_y = new_pos
                            self.target_position = new_pos
                            self.nearby_players[player_id] = new_pos
                            target_changed = True
                            self.logger.debug(f"봇 {self.bot_name} 따라가기 목표 위치 세션에서 업데이트: {new_pos}")
                        break
        
        # 탐험 시스템 가져오기
        if not exploration or not hasattr(exploration, 'dungeon'):
            return self._get_improved_exploration_move()
        
        dungeon = exploration.dungeon
        
        # 목표 위치가 변경되었거나 경로가 없으면 새로운 경로 계산
        if target_changed or not self.path_to_target or (self.current_x, self.current_y) not in self.path_to_target:
            # 목표 위치가 플레이어 위치라면, 플레이어와 겹치지 않도록 인접한 타일을 목표로 설정
            actual_target = (target_x, target_y)
            
            # 목표 위치가 장애물(플레이어 등)일 수 있으므로 인접한 타일 중 가장 가까운 곳을 찾음
            if (target_x, target_y) != (self.current_x, self.current_y):
                min_dist = float('inf')
                best_adj = None
                
                # 8방향 확인 (대각선 포함)
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dx == 0 and dy == 0: continue
                        
                        adj_x, adj_y = target_x + dx, target_y + dy
                        
                        # 맵 범위 및 이동 가능 확인
                        if (0 <= adj_x < dungeon.width and 
                            0 <= adj_y < dungeon.height and 
                            dungeon.is_walkable(adj_x, adj_y)):
                            
                            dist = abs(self.current_x - adj_x) + abs(self.current_y - adj_y)
                            if dist < min_dist:
                                min_dist = dist
                                best_adj = (adj_x, adj_y)
                
                if best_adj:
                    actual_target = best_adj
                    # self.logger.debug(f"봇 {self.bot_name} 따라가기 목표 조정: {self.target_position} -> {actual_target}")

            self.path_to_target = self._find_safe_path(
                (self.current_x, self.current_y),
                actual_target,
                dungeon,
                exploration
            )
        
        # 경로가 있으면 다음 위치로 이동
        if self.path_to_target:
            # 현재 위치가 경로에 있으면 제거
            if self.path_to_target and self.path_to_target[0] == (self.current_x, self.current_y):
                self.path_to_target.pop(0)
            
            # 경로의 다음 위치로 이동
            if self.path_to_target:
                next_x, next_y = self.path_to_target[0]
                dx = next_x - self.current_x
                dy = next_y - self.current_y
                
                # 이동 가능 여부 확인
                if (0 <= next_x < dungeon.width and 
                    0 <= next_y < dungeon.height and
                    dungeon.is_walkable(next_x, next_y)):
                    return {
                        "type": "move",
                        "dx": dx,
                        "dy": dy,
                        "x": next_x,
                        "y": next_y
                    }
        
        # 경로가 없거나 이동 불가능하면 단순 이동 시도
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
        
        # 대각선 이동 방지
        if dx != 0 and dy != 0:
            if random.random() < 0.5:
                dx = 0
            else:
                dy = 0
        
        new_x = self.current_x + dx
        new_y = self.current_y + dy
        
        # 이동 가능 여부 확인
        if (0 <= new_x < dungeon.width and 
            0 <= new_y < dungeon.height and
            dungeon.is_walkable(new_x, new_y)):
            return {
                "type": "move",
                "dx": dx,
                "dy": dy,
                "x": new_x,
                "y": new_y
            }
        else:
            # 이동 불가능하면 경로 초기화하고 탐험 모드로 전환
            self.path_to_target = []
            return self._get_improved_exploration_move()
    
    def _find_safe_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        dungeon: Any,
        exploration: Any
    ) -> List[Tuple[int, int]]:
        """
        A* 길찾기 알고리즘을 사용하여 안전한 경로 찾기
        
        Args:
            start: 시작 위치 (x, y)
            goal: 목표 위치 (x, y)
            dungeon: 던전 맵
            exploration: 탐험 시스템 (적 위치 확인용)
        
        Returns:
            경로 리스트 [(x1, y1), (x2, y2), ...]
        """
        import heapq
        from src.world.tile import TileType
        
        # 적의 위치 수집
        enemy_positions = set()
        if exploration and hasattr(exploration, 'enemies'):
            for enemy in exploration.enemies:
                if hasattr(enemy, 'x') and hasattr(enemy, 'y'):
                    enemy_positions.add((int(enemy.x), int(enemy.y)))
        
        # 플레이어(봇 포함) 위치 수집 (충돌 방지용)
        player_positions = set()
        if exploration and hasattr(exploration, 'session') and exploration.session:
            for pid, p in exploration.session.players.items():
                # 자기 자신은 제외
                if pid == self.bot_id:
                    continue
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    # 생존해 있는 플레이어만 벽 취급
                    is_dead = False
                    if hasattr(p, 'is_party_alive'):
                        if callable(p.is_party_alive):
                            if not p.is_party_alive():
                                is_dead = True
                        else:
                            if not p.is_party_alive:
                                is_dead = True
                    
                    if not is_dead:
                        player_positions.add((int(p.x), int(p.y)))
        
        # 로컬 플레이어도 추가 (싱글플레이 호환성)
        if exploration and hasattr(exploration, 'player'):
            p = exploration.player
            # 로컬 플레이어 ID 확인
            local_pid = getattr(p, 'player_id', None)
            if local_pid != self.bot_id:
                # 생존 체크 (간략하게)
                all_dead = True
                if hasattr(p, 'party'):
                    for m in p.party:
                        if getattr(m, 'current_hp', 0) > 0:
                            all_dead = False
                            break
                
                if not all_dead:
                    player_positions.add((int(p.x), int(p.y)))
        
        # 시작점과 목표점이 같으면 빈 경로 반환
        if start == goal:
            return []
        
        # A* 알고리즘
        open_set = [(0, start)]  # (f_score, position)
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        g_score: Dict[Tuple[int, int], float] = {start: 0}
        f_score: Dict[Tuple[int, int], float] = {start: self._heuristic(start, goal)}
        closed_set: Set[Tuple[int, int]] = set()
        
        # 4방향 이동 (상, 하, 좌, 우)
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # 목표에 도달
            if current == goal:
                # 경로 재구성
                path = []
                path_current = current
                while path_current is not None:
                    path.append(path_current)
                    path_current = came_from.get(path_current)
                path.reverse()
                # 시작점 제외 (이미 시작점에 있으므로)
                if path and path[0] == start:
                    path = path[1:]
                self.logger.debug(f"봇 {self.bot_name} 경로 찾기 완료: {len(path)}칸")
                return path
            
            # 인접 노드 확인
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # 맵 범위 확인
                if not (0 <= neighbor[0] < dungeon.width and 0 <= neighbor[1] < dungeon.height):
                    continue
                
                # 이동 가능 여부 확인
                tile = dungeon.get_tile(neighbor[0], neighbor[1])
                if not tile or not dungeon.is_walkable(neighbor[0], neighbor[1]):
                    continue
                
                # 잠긴 문 확인
                if tile.tile_type == TileType.LOCKED_DOOR:
                    continue
                
                # 이미 확인한 노드 스킵
                if neighbor in closed_set:
                    continue
                
                # 비용 계산 (기본 1 + 적 근처 페널티)
                move_cost = 1.0
                if neighbor in enemy_positions:
                    move_cost += 10.0  # 적 근처는 높은 비용
                elif any(abs(neighbor[0] - ex) + abs(neighbor[1] - ey) <= 2 for ex, ey in enemy_positions):
                    move_cost += 3.0  # 적 근처 2칸 이내는 중간 비용
                
                # G 점수 계산
                tentative_g_score = g_score[current] + move_cost
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        # 경로를 찾을 수 없음
        self.logger.warning(f"봇 {self.bot_name} 목표 위치까지 경로를 찾을 수 없음: {start} -> {goal}")
        return []
    
    def _heuristic(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """맨하탄 거리 휴리스틱"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def _execute_action(self, action: Dict[str, Any]):
        """행동 실행"""
        if action["type"] == "move":
            self._execute_move(action)
        elif action["type"] == "harvest":
            self._execute_harvest(action)
        elif action["type"] == "pickup_item":
            self._execute_pickup_item(action)
        elif action["type"] == "pickup_gold":
            self._execute_pickup_gold(action)
        elif action["type"] == "cook":
            self._execute_cook(action)
    
    def _execute_move(self, action: Dict[str, Any]):
        """이동 실행"""
        # 전투 중이면 이동 불가
        if self.in_combat:
            self.logger.debug(f"봇 {self.bot_name} 전투 중이라 이동 불가")
            return

        new_x = action["x"]
        new_y = action["y"]
        
        # 이동 실패 횟수 체크 및 무한 서성임 방지
        current_pos = (self.current_x, self.current_y)
        target_pos = (new_x, new_y)
        
        # 최근 방문한 위치 확인 (순환 감지)
        if not hasattr(self, 'recent_positions'):
            self.recent_positions = []
            
        self.recent_positions.append(current_pos)
        if len(self.recent_positions) > 10:
            self.recent_positions.pop(0)
            
        # 최근 10번의 이동 중 같은 위치가 3번 이상 반복되면 서성임으로 간주
        if self.recent_positions.count(target_pos) >= 3:
            self.logger.debug(f"봇 {self.bot_name} 서성임 감지: {target_pos} 회피")
            # 랜덤 이동으로 탈출 시도
            import random
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            new_x = self.current_x + dx
            new_y = self.current_y + dy
        
        # 탐험 시스템 가져오기
        exploration = self._get_exploration_system()
        if exploration:
            # 이동 가능 여부 확인
            if (0 <= new_x < exploration.dungeon.width and 
                0 <= new_y < exploration.dungeon.height and
                exploration.dungeon.is_walkable(new_x, new_y)):
                
                # 적과의 충돌 확인 (이동 전에! 플레이어처럼)
                if hasattr(exploration, 'get_enemy_at'):
                    enemy = exploration.get_enemy_at(new_x, new_y)
                    if enemy:
                        self.logger.info(f"봇 {self.bot_name} 적 발견! 전투 트리거 at ({enemy.x}, {enemy.y})")
                        # 적이 있으면 이동하지 않고 전투 트리거 (플레이어처럼)
                        # 전투 트리거는 탐험 시스템의 encounter_enemy 호출
                        if hasattr(exploration, 'encounter_enemy'):
                             # 호스트인 경우 직접 전투 시작, 아니면 요청
                             # 하지만 여기서는 exploration 시스템을 통해 처리
                             # 봇은 '플레이어'가 아니므로 exploration.encounter_enemy가 잘 작동하는지 확인 필요
                             # 봇 ID를 전달하여 누가 전투를 시작했는지 알림
                             exploration.encounter_enemy(enemy, initiator_id=self.bot_id)
                        
                        # 전투 트리거 플래그만 설정 (위의 호출이 비동기거나 즉시 전환되지 않을 경우를 대비)
                        self.pending_combat_trigger = {
                            "enemy": enemy,
                            "position": (new_x, new_y)
                        }
                        # 실제 위치는 업데이트하지 않음 (플레이어처럼)
                        return
                
                # 적이 없으면 정상 이동
                # 세션의 플레이어 위치 업데이트
                if self.session and self.bot_id in self.session.players:
                    bot_player = self.session.players[self.bot_id]
                    bot_player.x = new_x
                    bot_player.y = new_y
                
                self.current_x = new_x
                self.current_y = new_y
                
                # 계단에 도달했는지 확인 (다음 층 이동 준비)
                from src.world.tile import TileType
                tile = exploration.dungeon.get_tile(new_x, new_y)
                if tile and tile.tile_type in [TileType.STAIRS_DOWN, TileType.STAIRS_UP]:
                    # 계단에 도달하면 자동으로 준비 상태 설정
                    if self.session:
                        self.session.set_floor_ready(self.bot_id, True)
                        self.logger.info(f"봇 {self.bot_name} 계단 도달, 다음 층 이동 준비 완료")
                
                # 이동 메시지 브로드캐스트
                try:
                    move_message = MessageBuilder.player_move(
                        player_id=self.bot_id,
                        x=new_x,
                        y=new_y,
                        timestamp=time.time()
                    )
                    
                    if not self.network_manager.is_host:
                        self.network_manager.send(move_message)
                    else:
                        # 호스트인 경우 브로드캐스트 (비동기)
                        import asyncio
                        server_loop = getattr(self.network_manager, '_server_event_loop', None)
                        if server_loop and server_loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                self.network_manager.broadcast(move_message),
                                server_loop
                            )
                        else:
                            self.network_manager.broadcast(move_message)
                        
                        # 중요: 호스트는 브로드캐스트 메시지를 받지 못하므로 직접 이동 처리 호출
                        # (그래야 ExplorationSystem 상태 갱신 및 채집 로직이 동작함)
                        exploration = self._get_exploration_system()
                        if exploration and hasattr(exploration, 'update_player_movement'):
                            exploration.update_player_movement(self.bot_id, 0, 0)
                except Exception as e:
                    self.logger.error(f"이동 메시지 전송 실패: {e}", exc_info=True)
            else:
                self.logger.debug(f"봇 {self.bot_name} 이동 불가: ({new_x}, {new_y})")
                # 이동 불가 시 최근 위치 리스트 초기화하여 다른 방향 시도 유도
                if hasattr(self, 'recent_positions'):
                    self.recent_positions = []
        else:
            self.logger.warning(f"봇 {self.bot_name} 탐험 시스템을 찾을 수 없음")
    
    def _move_to_interact(self, target_x: int, target_y: int) -> bool:
        """상호작용을 위해 대상의 인접한 이동 가능 타일로 이동"""
        exploration = self._get_exploration_system()
        if not exploration:
            return False
            
        # 이미 인접해 있는지 확인 (대각선 포함)
        dx = abs(self.current_x - target_x)
        dy = abs(self.current_y - target_y)
        
        # 자원과 겹쳐있는 경우(dx=0, dy=0)도 포함
        if dx <= 1 and dy <= 1:
            return True
            
        # 인접 타일 중 이동 가능한 곳 찾기 (대각선 포함 8방향)
        neighbors = []
        for offset_x in [-1, 0, 1]:
            for offset_y in [-1, 0, 1]:
                if offset_x == 0 and offset_y == 0: continue
                
                nx, ny = target_x + offset_x, target_y + offset_y
                if (0 <= nx < exploration.dungeon.width and 
                    0 <= ny < exploration.dungeon.height and
                    exploration.dungeon.is_walkable(nx, ny)):
                    neighbors.append((nx, ny))
        
        if not neighbors:
            self.logger.debug(f"봇 {self.bot_name} 상호작용 불가: 접근 가능한 인접 타일 없음 ({target_x}, {target_y})")
            return False
            
        # 가장 가까운 인접 타일 찾기
        best_neighbor = None
        min_dist = float('inf')
        
        for nx, ny in neighbors:
            d = abs(self.current_x - nx) + abs(self.current_y - ny) # 이동 거리는 Manhattan
            if d < min_dist:
                min_dist = d
                best_neighbor = (nx, ny)
        
        if best_neighbor:
            self._move_towards(best_neighbor[0], best_neighbor[1])
            return True # 이동 시작함
            
        return False

    def _execute_harvest(self, action: Dict[str, Any]):
        """채집 실행"""
        harvestable = action.get("harvestable")
        if not harvestable:
            return
        
        exploration = self._get_exploration_system()
        if not exploration:
            return
            
        # 거리 체크 (1칸 이내여야 채집 가능)
        dist = abs(self.current_x - harvestable.x) + abs(self.current_y - harvestable.y)
        if dist > 1:
            # 거리가 멀면 접근 시도 (새로운 로직 사용)
            if not self._move_to_interact(harvestable.x, harvestable.y):
                # 접근 불가능하면 블랙리스트 추가
                self.logger.debug(f"봇 {self.bot_name} 채집 대상 접근 불가, 포기")
                pos = (harvestable.x, harvestable.y)
                self.harvested_blacklist.add(pos)
            return
        
        try:
            # 즉시 채집 시도 (3단계 상호작용 제거)
            # 실제 채집 데이터 처리
            success = False
            if harvestable.can_harvest(self.bot_id):
                results = harvestable.harvest(self.bot_id)
                if results:
                    success = True
                    self.logger.info(f"봇 {self.bot_name} 채집 성공: {harvestable.object_type.display_name} (재료: {len(results)}종류)")
                    
                    # 봇의 인벤토리에 추가
                    inventory = self._get_bot_inventory()
                    if inventory:
                        for item in results:
                            inventory.add_item(item, quantity=1)
                        
                        # 수집 완료 처리 (통신 네트워크)
                        # 중요: 개인 보상이므로 remove_item 호출하지 않음 (오브젝트 유지)
                        pos = (harvestable.x, harvestable.y)
                        # self.communication.remove_item(pos)  <- 제거
                        self.communication.unclaim_item(pos, self.bot_id)
            
            # 성공 여부와 상관없이 무조건 블랙리스트 추가 (중요: 서성임 방지)
            pos = (harvestable.x, harvestable.y)
            self.harvested_blacklist.add(pos)
            
            # 상호작용 효과 (시각/청각) - 한 번만 호출
            if hasattr(exploration, 'handle_interaction'):
                exploration.handle_interaction(harvestable.x, harvestable.y, self.bot_id)
            
            # 상태 초기화 (혹시 남아있을 수 있는 상태)
            self.interaction_state = {"active": False, "step": 0}
            
            # 채집 후 회피 이동 (서성임 방지)
            self._force_flee_move(harvestable.x, harvestable.y)
                
        except Exception as e:
            self.logger.error(f"봇 {self.bot_name} 채집 중 오류: {e}", exc_info=True)
            # 오류 발생 시에도 블랙리스트 추가하여 무한 반복 방지
            pos = (harvestable.x, harvestable.y)
            self.harvested_blacklist.add(pos)
            self.interaction_state = {"active": False, "step": 0}


    def _force_flee_move(self, from_x: int, from_y: int):
        """특정 위치에서 벗어나는 이동 (전진 또는 후퇴)"""
        exploration = self._get_exploration_system()
        if not exploration: return
        
        best_move = None
        
        # 1. 원래 목표 지점이 있다면 그쪽으로 전진 시도
        if self.target_position:
            tx, ty = self.target_position
            path = self._find_path((self.current_x, self.current_y), (tx, ty))
            if len(path) > 1:
                next_pos = path[1]
                # 채집물 위치가 아니면 이동
                if next_pos != (from_x, from_y):
                    best_move = {"x": next_pos[0], "y": next_pos[1]}
        
        # 2. 목표가 없거나 막혔다면, 채집물 위치를 통과(Pass Through) 시도
        if not best_move:
            # 채집물이 있던 자리가 이제 비었다면(수집됨), 그 자리를 밟고 지나가는 것이 자연스러움
            # 단, 아직 오브젝트가 남아있을 수 있으므로 is_walkable 체크
            if exploration.dungeon.is_walkable(from_x, from_y):
                # 봇이 채집물과 인접해 있을 때만 유효
                dist = abs(self.current_x - from_x) + abs(self.current_y - from_y)
                if dist == 1:
                    best_move = {"x": from_x, "y": from_y}
        
        # 3. 통과도 안되면, 가능한 아무 방향으로나 이동 (단, 채집물 방향 제외)
        if not best_move:
            possible_moves = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = self.current_x + dx, self.current_y + dy
                
                # 맵 밖이나 벽이면 제외
                if not exploration.dungeon.is_walkable(nx, ny):
                    continue
                    
                # 채집물 위치면 제외
                if (nx, ny) == (from_x, from_y):
                    continue
                    
                possible_moves.append((nx, ny))
            
            if possible_moves:
                import random
                nx, ny = random.choice(possible_moves)
                best_move = {"x": nx, "y": ny}
                
        # 이동 실행
        if best_move:
            self._execute_move(best_move)
            # 태스크 큐에 추가하여 연속 이동 유도 (흐름 유지)
            self.task_queue.add_task(
                TaskType.MOVE, 
                priority=20, 
                data={"target": (best_move["x"], best_move["y"])}
            )
    
    def _execute_pickup_item(self, action: Dict[str, Any]):
        """드롭된 아이템 줍기"""
        x = action.get("x")
        y = action.get("y")
        item = action.get("item")
        
        if not item or not x or not y:
            return
        
        exploration = self._get_exploration_system()
        if not exploration:
            return
        
        # 봇의 인벤토리에 추가
        inventory = self._get_bot_inventory()
        if not inventory:
            return
        
        item_name = getattr(item, 'name', 'Unknown')
        try:
            if inventory.add_item(item, quantity=1):
                # 타일에서 아이템 제거
                from src.world.tile import TileType
                tile = exploration.dungeon.get_tile(x, y)
                if tile and tile.tile_type == TileType.DROPPED_ITEM:
                    tile.tile_type = TileType.FLOOR
                    tile.dropped_item = None
                    self.logger.info(
                        f"봇 {self.bot_name} 아이템 줍기: {item_name} "
                        f"(무게: {inventory.current_weight:.1f}kg/{inventory.max_weight:.1f}kg)"
                    )
                    
                    # 블랙리스트 추가 및 공유 정보 업데이트
                    pos = (x, y)
                    self.harvested_blacklist.add(pos)
                    self.communication.remove_item(pos)
                    self.communication.unclaim_item(pos, self.bot_id)
            else:
                self.logger.warning(f"봇 {self.bot_name} 인벤토리 가득 참: {item_name} 줍기 실패")
                # 실패해도 블랙리스트 추가 (재시도 방지)
                self.harvested_blacklist.add((x, y))
        except Exception as e:
            self.logger.error(f"봇 아이템 줍기 오류: {e}", exc_info=True)
            self.harvested_blacklist.add((x, y))
    
    def _execute_pickup_gold(self, action: Dict[str, Any]):
        """드롭된 골드 줍기"""
        x = action.get("x")
        y = action.get("y")
        amount = action.get("amount", 0)
        
        if amount <= 0 or not x or not y:
            return
        
        exploration = self._get_exploration_system()
        if not exploration:
            return
        
        # 봇의 인벤토리에 골드 추가
        inventory = self._get_bot_inventory()
        if not inventory:
            return
        
        try:
            # 타일에서 골드 제거
            from src.world.tile import TileType
            tile = exploration.dungeon.get_tile(x, y)
            if tile and tile.tile_type == TileType.GOLD:
                tile.tile_type = TileType.FLOOR
                tile.gold_amount = 0
                inventory.add_gold(amount)
                self.logger.info(f"봇 {self.bot_name} 골드 줍기: {amount}골드 (총 {inventory.gold}G)")
                
                # 블랙리스트 추가
                pos = (x, y)
                self.harvested_blacklist.add(pos)
        except Exception as e:
            self.logger.error(f"봇 골드 줍기 오류: {e}", exc_info=True)
            self.harvested_blacklist.add((x, y))
    
    def _execute_cook(self, action: Dict[str, Any]):
        """요리 실행"""
        ingredients_data = action.get("ingredients", [])
        if not ingredients_data:
            return
        
        inventory = self._get_bot_inventory()
        if not inventory:
            return
        
        try:
            # 재료 선택 (최대 4개, 랜덤 또는 최적 조합)
            selected_ingredients = self._select_ingredients_for_cooking(ingredients_data)
            if not selected_ingredients or len(selected_ingredients) < 1:
                return
            
            # 레시피 찾기
            from src.cooking.recipe import RecipeDatabase
            RecipeDatabase.initialize()
            
            ingredients = [ing for _, ing in selected_ingredients]
            recipe = RecipeDatabase.find_recipe(ingredients)
            
            if not recipe:
                return
            
            # 요리 실행
            cooked_food = recipe.result
            
            # 요리솥 보너스 적용
            import random
            if action.get("cooking_pot"):
                # HP/MP 회복량 증가
                if hasattr(cooked_food, 'hp_restore') and cooked_food.hp_restore > 0:
                    cooked_food.hp_restore = int(cooked_food.hp_restore * 1.2)
                
                if hasattr(cooked_food, 'mp_restore') and cooked_food.mp_restore > 0:
                    cooked_food.mp_restore = int(cooked_food.mp_restore * 1.2)
                
                # 버프 지속시간 증가
                if hasattr(cooked_food, 'buff_duration') and cooked_food.buff_duration > 0:
                    cooked_food.buff_duration = int(cooked_food.buff_duration * 1.2)
                
                # 추가 아이템 생성 (10% 확률)
                if random.random() < 0.1:
                    from copy import deepcopy
                    extra_food = deepcopy(recipe.result)
                    inventory.add_item(extra_food, quantity=1)
                    self.logger.info(f"봇 {self.bot_name} 요리솥 보너스: 추가 음식 생성! {extra_food.name}")
            
            # 인벤토리에서 재료 제거 (높은 인덱스부터)
            slot_indices = [slot_idx for slot_idx, _ in selected_ingredients]
            for slot_idx in sorted(slot_indices, reverse=True):
                inventory.remove_item(slot_idx, quantity=1)
            
            # 요리 결과를 인벤토리에 추가
            success = inventory.add_item(cooked_food, quantity=1)
            if success:
                self.logger.info(f"봇 {self.bot_name} 요리 완료: {cooked_food.name}")
            else:
                self.logger.warning(f"봇 {self.bot_name} 요리 실패: 인벤토리 가득 참")
        
        except Exception as e:
            self.logger.error(f"봇 요리 실패: {e}", exc_info=True)
    
    def _select_ingredients_for_cooking(self, available_ingredients: List[Any]) -> List[Any]:
        """요리할 재료 선택 (최적 조합 찾기)"""
        if not available_ingredients:
            return []
        
        # 최대 4개까지 선택
        max_ingredients = min(4, len(available_ingredients))
        
        # 간단한 전략: 랜덤으로 1~4개 선택
        # 더 나은 전략: 레시피를 고려한 최적 조합 찾기
        import random
        
        # 1~4개 랜덤 선택
        num_ingredients = random.randint(1, max_ingredients)
        selected = random.sample(available_ingredients, num_ingredients)
        
        return selected


class AdvancedBotManager:
    """고급 봇 관리자"""
    
    def __init__(
        self,
        network_manager: NetworkManager,
        session: MultiplayerSession,
        auto_fill: bool = True,
        min_players: int = 2
    ):
        """
        고급 봇 관리자 초기화
        
        Args:
            network_manager: 네트워크 관리자
            session: 멀티플레이 세션
            auto_fill: 플레이어 부족 시 자동 채우기
            min_players: 최소 플레이어 수
        """
        self.network_manager = network_manager
        self.session = session
        self.auto_fill = auto_fill
        self.min_players = min_players
        self.logger = get_logger("multiplayer.bot_manager_advanced")
        
        self.bots: Dict[str, AdvancedAIBot] = {}
        self.is_running = False
        self.last_update_time = 0.0
        self.update_interval = 0.1
        self.last_auto_fill_check = 0.0
        self.auto_fill_interval = 5.0  # 5초마다 체크
    
    def auto_select_difficulty(self) -> str:
        """난이도 자동 선택 (봇은 항상 보통)"""
        return "normal"
    
    def add_bot(
        self,
        bot_id: str,
        bot_name: str,
        behavior: BotBehavior = BotBehavior.EXPLORER,
        is_host: bool = False
    ) -> AdvancedAIBot:
        """봇 추가"""
        bot = AdvancedAIBot(
            bot_id=bot_id,
            bot_name=bot_name,
            network_manager=self.network_manager,
            session=self.session,
            behavior=behavior,
            is_host=is_host
        )
        self.bots[bot_id] = bot
        self.logger.info(f"고급 봇 추가: {bot_name} (ID: {bot_id}, 행동: {behavior.value})")
        return bot
    
    def remove_bot(self, bot_id: str):
        """봇 제거"""
        if bot_id in self.bots:
            self.bots[bot_id].stop()
            del self.bots[bot_id]
            self.logger.info(f"봇 제거: {bot_id}")
    
    def start_all(self):
        """모든 봇 시작"""
        if len(self.bots) == 0:
            self.logger.warning("봇 매니저: 시작할 봇이 없습니다")
            return
        
        self.logger.info(f"봇 매니저: {len(self.bots)}개의 봇 시작 중...")
        for bot_id, bot in self.bots.items():
            try:
                bot.start()
                self.logger.info(f"봇 매니저: 봇 {bot.bot_name} (ID: {bot_id}) 시작 완료")
            except Exception as e:
                self.logger.error(f"봇 매니저: 봇 {bot_id} 시작 실패: {e}", exc_info=True)
        
        self.is_running = True
        self.logger.info(f"봇 매니저: {len(self.bots)}개의 봇 시작 완료 (is_running={self.is_running})")
    
    def stop_all(self):
        """모든 봇 중지"""
        for bot in self.bots.values():
            bot.stop()
        self.is_running = False
        self.logger.info("모든 봇 중지")
    
    def update(self, current_time: float):
        """모든 봇 업데이트"""
        if not self.is_running:
            self.logger.debug(f"봇 매니저가 실행 중이 아님 (is_running={self.is_running}, 봇 수: {len(self.bots)})")
            return
        
        if current_time - self.last_update_time < self.update_interval:
            return
        
        self.last_update_time = current_time
        
        # 자동 채우기 체크
        if self.auto_fill and current_time - self.last_auto_fill_check >= self.auto_fill_interval:
            self._check_and_fill_players(current_time)
            self.last_auto_fill_check = current_time
        
        # 모든 봇 업데이트
        if len(self.bots) == 0:
            self.logger.debug("업데이트할 봇이 없음")
            return
        
        updated_count = 0
        for bot_id, bot in self.bots.items():
            try:
                if bot.is_active:
                    bot.update(current_time)
                    updated_count += 1
                else:
                    self.logger.debug(f"봇 {bot.bot_name} (ID: {bot_id}) 비활성화 상태")
            except Exception as e:
                self.logger.error(f"봇 {bot_id} 업데이트 오류: {e}", exc_info=True)
        
        if updated_count > 0:
            self.logger.debug(f"봇 매니저 업데이트: {updated_count}/{len(self.bots)}개 봇 업데이트됨")
    
    def _check_and_fill_players(self, current_time: float):
        """플레이어 부족 시 자동 채우기"""
        # 실제 플레이어 수 확인
        real_players = [p for p in self.session.players.values() if p.player_id not in self.bots]
        bot_count = len(self.bots)
        total_players = len(real_players) + bot_count
        
        if total_players < self.min_players:
            # 봇 추가
            needed = self.min_players - total_players
            self.logger.info(f"플레이어 부족: {total_players}/{self.min_players}, {needed}개 봇 추가")
            
            for i in range(needed):
                bot_id = f"bot_{int(current_time)}_{i}"
                bot_name = f"봇 {bot_count + i + 1}"
                # 기본적으로 탐험 모드로 시작 (PASSIVE 방지)
                behavior = BotBehavior.EXPLORER
                self.add_bot(bot_id, bot_name, behavior, is_host=False)
            
            # 새로 추가된 봇 시작
            for bot in list(self.bots.values())[-needed:]:
                bot.start()
    
    def get_bot(self, bot_id: str) -> Optional[AdvancedAIBot]:
        """봇 가져오기"""
        return self.bots.get(bot_id)
    
    def get_all_bots(self) -> List[AdvancedAIBot]:
        """모든 봇 가져오기"""
        return list(self.bots.values())

