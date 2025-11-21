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
    ITEM_CHECK = "item_check"  # 아이템 확인
    ITEM_REQUEST = "item_request"  # 아이템 요청
    GOLD_REQUEST = "gold_request"  # 골드 요청
    EXPLORATION_REQUEST = "exploration_request"  # 탐험 요청
    FOLLOW_PLAYER = "follow_player"  # 플레이어 따라가기
    AVOID_COMBAT = "avoid_combat"  # 전투 회피


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
        
        # 메시지 핸들러 등록
        self._register_handlers()
        
        # 직업/특성/패시브 데이터 로드
        self._load_game_data()
    
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
            pass
    
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
        
        # 위협도 평가 및 전략적 선택
        threat_assessment = self._assess_threats(actor, alive_allies, alive_enemies)
        
        # 1. 아군 보호 우선 (위험한 아군이 있으면 힐)
        critical_allies = threat_assessment.get("critical_allies", [])
        if critical_allies:
            heal_action = self._select_smart_heal_action(actor, critical_allies, alive_allies)
            if heal_action:
                return heal_action
        
        # 2. 버프/디버프 스킬 사용 (아군 버프 또는 적 디버프)
        buff_action = self._select_buff_action(actor, alive_allies, alive_enemies)
        if buff_action:
            return buff_action
        
        # 3. 전략적 공격 (위협도가 높은 적 우선, BREAK 상태 활용)
        attack_action = self._select_smart_attack_action(actor, alive_enemies, threat_assessment)
        if attack_action:
            return attack_action
        
        # 4. 기본 공격 (폴백)
        return self._select_basic_attack(actor, alive_enemies)
    
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
        
        # BREAK 상태인 적이 있으면 우선 공격
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
    
    def _auto_select_job(self):
        """자동 직업 선택 (턴 변경 시 호출)"""
        # 실제 구현은 MultiplayerPartySetup과 통합 필요
        pass
    
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
    
    def _check_and_harvest(self) -> Optional[Dict[str, Any]]:
        """주변에 채집 가능한 오브젝트가 있는지 확인하고 채집 액션 반환"""
        # exploration 시스템 가져오기
        exploration = self._get_exploration_system()
        if not exploration:
            return None
        
        # 주변 채집 오브젝트 찾기 (맨하탄 거리 2 이내)
        max_distance = 2
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
                    # 적 주변 1칸도 위험 지역으로 간주
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            enemy_positions.add((int(enemy.x) + dx, int(enemy.y) + dy))
        
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
            # 채팅 메시지로 도움 요청 전송
            self._send_chat_message(f"{self.bot_name}: 도움이 필요합니다!")
        
        elif command == BotCommand.ITEM_CHECK:
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
    
    def _send_chat_message(self, message: str):
        """채팅 메시지 전송"""
        try:
            chat_msg = MessageBuilder.chat_message(
                player_id=self.bot_id,
                message=message
            )
            if not self.network_manager.is_host:
                self.network_manager.send(chat_msg)
            else:
                self.network_manager.broadcast(chat_msg)
        except Exception as e:
            self.logger.error(f"채팅 메시지 전송 실패: {e}", exc_info=True)
    
    def start(self):
        """봇 시작"""
        self.is_active = True
        
        # 초기 위치를 세션 플레이어에서 가져오기
        if self.session and self.bot_id in self.session.players:
            bot_player = self.session.players[self.bot_id]
            if hasattr(bot_player, 'x') and hasattr(bot_player, 'y'):
                self.current_x = bot_player.x
                self.current_y = bot_player.y
                self.logger.info(f"봇 {self.bot_name} 초기 위치 설정: ({self.current_x}, {self.current_y})")
        
        # 마지막 액션 시간을 현재 시간으로 설정 (즉시 액션 가능하도록)
        import time
        self.last_action_time = time.time() - self.action_interval  # 즉시 액션 가능하도록
        
        self.logger.info(f"고급 AI 봇 {self.bot_name} 시작 (행동: {self.behavior.value}, 호스트: {self.is_host}, 위치: ({self.current_x}, {self.current_y}))")
    
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
                if (bot_player.x != self.current_x or bot_player.y != self.current_y):
                    old_pos = (self.current_x, self.current_y)
                    self.current_x = bot_player.x
                    self.current_y = bot_player.y
                    self.logger.debug(f"봇 {self.bot_name} 위치 동기화: {old_pos} -> ({self.current_x}, {self.current_y})")
        
        # 전투 중이면 전투 액션 처리
        if self.in_combat and self.combat_manager:
            # 전투 액션은 별도로 처리 (전투 시스템에서 호출)
            return
        
        # 액션 간격 체크
        time_since_last_action = current_time - self.last_action_time
        if time_since_last_action < self.action_interval:
            return
        
        self.last_action_time = current_time
        
        # 명령 처리
        if self.pending_commands:
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
            return  # 명령 처리 후 이번 프레임은 종료
        
        # 행동 결정 및 실행
        action = self._decide_action()
        if action:
            self.logger.debug(f"봇 {self.bot_name} 액션 결정: {action.get('type', 'unknown')} at ({self.current_x}, {self.current_y})")
            self._execute_action(action)
        else:
            # 가만히 있기 (액션 없음)
            self.logger.debug(f"봇 {self.bot_name} 가만히 있기 (위치: {self.current_x}, {self.current_y})")
    
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
            '2': BotCommand.ITEM_CHECK,
            '3': BotCommand.ITEM_REQUEST,
            '4': BotCommand.GOLD_REQUEST,
            '5': BotCommand.EXPLORATION_REQUEST,
            '6': BotCommand.FOLLOW_PLAYER,
            '7': BotCommand.AVOID_COMBAT,
        }
        
        command = command_map.get(key)
        if command:
            self.pending_commands.append(command)
            self.logger.info(f"봇 {self.bot_name} 명령 수신: {command.value} (키: {key})")
            return True
        
        return False
    
    def _decide_action(self) -> Optional[Dict[str, Any]]:
        """행동 결정"""
        # 가끔은 가만히 있기 (10% 확률)
        import random
        if random.random() < 0.1:  # 10% 확률로 아무것도 하지 않음
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
            self.path_to_target = self._find_safe_path(
                (self.current_x, self.current_y),
                (target_x, target_y),
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
                    # 적 주변 1칸도 위험 지역으로 간주
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            enemy_positions.add((int(enemy.x) + dx, int(enemy.y) + dy))
        
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
        new_x = action["x"]
        new_y = action["y"]
        
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
                        # 전투 트리거는 탐험 시스템에서 처리 (봇의 위치에서 적 발견)
                        # 여기서는 전투 트리거 플래그만 설정
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
                except Exception as e:
                    self.logger.error(f"이동 메시지 전송 실패: {e}", exc_info=True)
            else:
                self.logger.debug(f"봇 {self.bot_name} 이동 불가: ({new_x}, {new_y})")
        else:
            self.logger.warning(f"봇 {self.bot_name} 탐험 시스템을 찾을 수 없음")
    
    def _execute_harvest(self, action: Dict[str, Any]):
        """채집 실행"""
        harvestable = action.get("harvestable")
        if not harvestable:
            return
        
        exploration = self._get_exploration_system()
        if not exploration:
            return
        
        try:
            # 채집 실행 (봇 ID를 전달하여 개인 보상 처리)
            if harvestable.can_harvest(self.bot_id):
                results = harvestable.harvest(self.bot_id)
                if results:
                    self.logger.info(f"봇 {self.bot_name} 채집 성공: {harvestable.object_type.display_name} (재료: {len(results)}종류)")
                    # TODO: 봇의 인벤토리에 추가 로직 필요 (현재는 봇 인벤토리 시스템이 없음)
                    # 멀티플레이에서는 호스트가 봇의 채집 결과를 처리해야 할 수 있음
        except Exception as e:
            self.logger.error(f"봇 채집 실패: {e}", exc_info=True)
    
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
        
        # 타일에서 아이템 제거
        from src.world.tile import TileType
        tile = exploration.dungeon.get_tile(x, y)
        if tile and tile.tile_type == TileType.DROPPED_ITEM:
            tile.tile_type = TileType.FLOOR
            tile.dropped_item = None
            self.logger.info(f"봇 {self.bot_name} 아이템 줍기: {getattr(item, 'name', 'Unknown')}")
    
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
        
        # 타일에서 골드 제거
        from src.world.tile import TileType
        tile = exploration.dungeon.get_tile(x, y)
        if tile and tile.tile_type == TileType.GOLD:
            tile.tile_type = TileType.FLOOR
            tile.gold_amount = 0
            self.logger.info(f"봇 {self.bot_name} 골드 줍기: {amount}골드")
    
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
                behavior = random.choice(list(BotBehavior))
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

