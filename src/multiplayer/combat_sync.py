"""
전투 동기화 시스템

멀티플레이에서 전투 액션 실행과 상태 업데이트를 동기화합니다.
"""

import time
from typing import Dict, List, Optional, Any, Set, Tuple
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.config import MultiplayerConfig
from src.combat.combat_manager import CombatManager, ActionType, CombatState
from src.core.logger import get_logger


class CombatSyncManager:
    """전투 동기화 관리자"""
    
    def __init__(
        self,
        session: MultiplayerSession,
        network_manager: Optional[NetworkManager] = None,
        combat_manager: Optional[CombatManager] = None,
        is_host: bool = False
    ):
        """
        초기화
        
        Args:
            session: 멀티플레이 세션
            network_manager: 네트워크 관리자
            combat_manager: 전투 관리자
            is_host: 호스트 여부
        """
        self.session = session
        self.network_manager = network_manager
        self.combat_manager = combat_manager
        self.is_host = is_host
        self.logger = get_logger("multiplayer.combat_sync")
        
        # 액션 실행 큐 (호스트용)
        self.action_queue: List[Dict[str, Any]] = []  # [{player_id, actor_id, action, timestamp}, ...]
        
        # 액션 시퀀스 번호 (순서 보장용)
        self.action_sequence = 0
        self.processed_sequences: Set[int] = set()
        
        # 플레이어별 행동 선택 상태 추적 (ATB 시스템용)
        self.players_selecting_action: Set[str] = set()
        
        # 네트워크 메시지 핸들러 등록
        if self.network_manager:
            self._register_handlers()
    
    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        try:
            if not self.network_manager:
                return
            
            # 전투 액션 메시지 핸들러
            self.network_manager.register_handler(
                MessageType.COMBAT_ACTION,
                self._handle_combat_action
            )
            
            # 전투 상태 업데이트 메시지 핸들러 (클라이언트만)
            if not self.is_host:
                self.network_manager.register_handler(
                    MessageType.STATE_UPDATE,
                    self._handle_combat_state_update
                )
        except Exception as e:
            self.logger.error(f"네트워크 핸들러 등록 실패: {e}", exc_info=True)
    
    async def send_action_request(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        액션 요청 전송 (클라이언트 → 호스트)
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자 캐릭터
            action_type: 행동 타입
            target: 대상 캐릭터
            skill: 스킬 (있는 경우)
            **kwargs: 추가 옵션
            
        Returns:
            전송 성공 여부
        """
        try:
            if self.is_host:
                # 호스트는 직접 처리
                return await self._process_action_locally(player_id, actor, action_type, target, skill, **kwargs)
            
            if not self.network_manager:
                self.logger.warning("네트워크 관리자가 없어 액션 요청을 보낼 수 없습니다")
                return False
            
            # 액션 정보 직렬화
            action_data = self._serialize_action(action_type, target, skill, **kwargs)
            
            # 액터 ID 추출
            actor_id = self._get_character_id(actor)
            if not actor_id:
                self.logger.warning(f"액터 ID를 찾을 수 없음: {actor}")
                return False
            
            # 액션 요청 메시지 생성
            message = MessageBuilder.combat_action(
                player_id=player_id,
                actor_id=actor_id,
                action=action_data
            )
            
            # 호스트에게 전송
            await self.network_manager.send(message)
            
            # 행동 선택 시작 (ATB 감소용)
            self._set_player_selecting(player_id, True)
            
            self.logger.debug(f"액션 요청 전송: {player_id} -> {actor_id} ({action_type.value})")
            return True
        except Exception as e:
            self.logger.error(f"액션 요청 전송 실패: {e}", exc_info=True)
            return False
    
    async def _handle_combat_action(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        전투 액션 메시지 처리 (호스트)
        
        Args:
            message: 전투 액션 메시지
            sender_id: 발신자 ID
        """
        try:
            if not self.is_host:
                return
            
            if not self.combat_manager:
                self.logger.warning("전투 관리자가 없어 액션을 처리할 수 없습니다")
                return
            
            player_id = message.player_id or sender_id
            if not player_id:
                self.logger.warning("액션 메시지에 플레이어 ID가 없습니다")
                return
            
            # 액션 데이터 추출
            action_data = message.data.get("action", {})
            actor_id = message.data.get("actor_id")
            
            if not actor_id:
                self.logger.warning("액션 메시지에 액터 ID가 없습니다")
                return
            
            # 액터 찾기
            actor = self._find_character_by_id(actor_id)
            if not actor:
                self.logger.warning(f"액터를 찾을 수 없음: {actor_id}")
                return
            
            # 플레이어 소유 확인
            actor_player_id = self._get_player_id_from_character(actor)
            if actor_player_id != player_id:
                self.logger.warning(
                    f"플레이어 {player_id}가 소유하지 않은 캐릭터 {actor_id} 액션 시도"
                )
                return
            
            # 액션 역직렬화
            action_type, target, skill, kwargs = self._deserialize_action(action_data)
            
            # 액션 실행 및 브로드캐스트
            await self._execute_and_broadcast_action(
                player_id, actor, action_type, target, skill, **kwargs
            )
            
            # 행동 선택 완료 (ATB 감소 해제)
            self._set_player_selecting(player_id, False)
            
        except Exception as e:
            self.logger.error(f"전투 액션 처리 실패: {e}", exc_info=True)
    
    async def _process_action_locally(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        액션 로컬 처리 (호스트)
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            **kwargs: 추가 옵션
            
        Returns:
            처리 성공 여부
        """
        try:
            if not self.combat_manager:
                return False
            
            # 행동 선택 시작
            self._set_player_selecting(player_id, True)
            
            # 액션 실행 및 브로드캐스트
            success = await self._execute_and_broadcast_action(
                player_id, actor, action_type, target, skill, **kwargs
            )
            
            # 행동 선택 완료
            self._set_player_selecting(player_id, False)
            
            return success
        except Exception as e:
            self.logger.error(f"로컬 액션 처리 실패: {e}", exc_info=True)
            self._set_player_selecting(player_id, False)
            return False
    
    async def _execute_and_broadcast_action(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        액션 실행 및 브로드캐스트 (호스트)
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            **kwargs: 추가 옵션
            
        Returns:
            실행 성공 여부
        """
        try:
            if not self.combat_manager:
                return False
            
            # 액션 실행
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=action_type,
                target=target,
                skill=skill,
                **kwargs
            )
            
            # 모든 클라이언트에게 액션 결과 브로드캐스트
            if self.network_manager:
                # 액션 결과 직렬화
                action_result = self._serialize_action_result(
                    player_id, actor, action_type, target, skill, result, **kwargs
                )
                
                # 상태 업데이트 메시지 생성 및 브로드캐스트
                from src.multiplayer.protocol import MessageBuilder
                state_message = MessageBuilder.state_update({
                    "combat_action": action_result,
                    "combat_state": self._get_combat_state_snapshot(),
                    "timestamp": time.time()
                })
                
                await self.network_manager.broadcast(state_message)
            
            self.logger.debug(
                f"액션 실행 및 브로드캐스트: {player_id} -> {getattr(actor, 'name', 'Unknown')} "
                f"({action_type.value})"
            )
            
            return result.get("success", False) if isinstance(result, dict) else True
        except Exception as e:
            self.logger.error(f"액션 실행 및 브로드캐스트 실패: {e}", exc_info=True)
            return False
    
    async def _handle_combat_state_update(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        전투 상태 업데이트 메시지 처리 (클라이언트)
        
        Args:
            message: 상태 업데이트 메시지
            sender_id: 발신자 ID (호스트)
        """
        try:
            if self.is_host:
                return
            
            if not self.combat_manager:
                return
            
            data = message.data.get("data", {})
            combat_action = data.get("combat_action")
            
            if combat_action:
                # 액션 동기화 실행
                await self._sync_remote_action(combat_action)
            
            # 전투 상태 스냅샷 동기화
            combat_state = data.get("combat_state")
            if combat_state:
                self._sync_combat_state(combat_state)
            
        except Exception as e:
            self.logger.error(f"전투 상태 업데이트 처리 실패: {e}", exc_info=True)
    
    async def _sync_remote_action(self, action_data: Dict[str, Any]):
        """
        원격 액션 동기화 실행 (클라이언트)
        
        Args:
            action_data: 액션 데이터
        """
        try:
            if not self.combat_manager:
                return
            
            # 액션 데이터에서 정보 추출
            player_id = action_data.get("player_id")
            actor_id = action_data.get("actor_id")
            action_type_str = action_data.get("action_type")
            result = action_data.get("result", {})
            
            # 액터 찾기
            actor = self._find_character_by_id(actor_id)
            if not actor:
                self.logger.warning(f"동기화할 액터를 찾을 수 없음: {actor_id}")
                return
            
            # 플레이어가 로컬 플레이어인지 확인 (로컬 플레이어의 액션은 이미 실행됨)
            from src.multiplayer.game_mode import get_game_mode_manager
            game_mode_manager = get_game_mode_manager()
            local_player_id = getattr(game_mode_manager, 'local_player_id', None)
            
            if player_id == local_player_id:
                # 로컬 플레이어의 액션은 이미 실행되었으므로 스킵
                return
            
            # 액션 타입 변환
            action_type = ActionType(action_type_str) if action_type_str else None
            
            if not action_type:
                self.logger.warning(f"알 수 없는 액션 타입: {action_type_str}")
                return
            
            # 결과 정보만 표시 (실제 실행은 호스트에서만)
            # 클라이언트는 결과만 동기화하여 UI 업데이트
            
            self.logger.debug(f"원격 액션 동기화: {player_id} -> {getattr(actor, 'name', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"원격 액션 동기화 실패: {e}", exc_info=True)
    
    def _sync_combat_state(self, state_data: Dict[str, Any]):
        """
        전투 상태 동기화 (클라이언트)
        
        Args:
            state_data: 상태 데이터
        """
        try:
            if not self.combat_manager:
                return
            
            # 전투원 상태 동기화
            allies_state = state_data.get("allies", [])
            enemies_state = state_data.get("enemies", [])
            
            # 캐릭터 상태 업데이트 (HP, MP, BRV, 상태이상 등)
            for char_data in allies_state + enemies_state:
                char_id = char_data.get("id")
                if not char_id:
                    continue
                
                character = self._find_character_by_id(char_id)
                if not character:
                    continue
                
                # 상태 동기화
                if "current_hp" in char_data:
                    character.current_hp = char_data["current_hp"]
                if "current_mp" in char_data:
                    character.current_mp = char_data["current_mp"]
                if "current_brv" in char_data:
                    character.current_brv = char_data.get("current_brv", 0)
                if "is_alive" in char_data:
                    character.is_alive = char_data["is_alive"]
            
            # 전투 상태 동기화
            combat_state_str = state_data.get("combat_state")
            if combat_state_str:
                try:
                    self.combat_manager.state = CombatState(combat_state_str)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"전투 상태 변환 실패: {combat_state_str} - {e}")
            
            # 턴 카운트 동기화
            turn_count = state_data.get("turn_count")
            if turn_count is not None:
                self.combat_manager.turn_count = turn_count
            
        except Exception as e:
            self.logger.error(f"전투 상태 동기화 실패: {e}", exc_info=True)
    
    def _set_player_selecting(self, player_id: str, is_selecting: bool):
        """
        플레이어 행동 선택 상태 설정 (ATB 시스템용)
        
        Args:
            player_id: 플레이어 ID
            is_selecting: 행동 선택 중 여부
        """
        try:
            if not player_id or not isinstance(player_id, str):
                return
            
            if is_selecting:
                self.players_selecting_action.add(player_id)
            else:
                self.players_selecting_action.discard(player_id)
            
            # ATB 시스템에 반영 (멀티플레이 ATB 시스템인 경우)
            if self.combat_manager and hasattr(self.combat_manager, 'atb'):
                atb_system = self.combat_manager.atb
                if hasattr(atb_system, 'set_player_selecting'):
                    atb_system.set_player_selecting(player_id, is_selecting)
        except Exception as e:
            self.logger.error(f"플레이어 선택 상태 설정 실패: {e}", exc_info=True)
    
    def _serialize_action(
        self,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        액션 직렬화
        
        Args:
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            **kwargs: 추가 옵션
            
        Returns:
            직렬화된 액션 데이터
        """
        try:
            action_data = {
                "action_type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                "timestamp": time.time()
            }
            
            # 타겟 ID
            if target:
                target_id = self._get_character_id(target)
                if target_id:
                    action_data["target_id"] = target_id
            
            # 스킬 ID
            if skill:
                skill_id = getattr(skill, 'id', None) or getattr(skill, 'skill_id', None)
                if skill_id:
                    action_data["skill_id"] = skill_id
                skill_name = getattr(skill, 'name', None)
                if skill_name:
                    action_data["skill_name"] = skill_name
            
            # 아이템 정보
            if "item" in kwargs:
                item = kwargs["item"]
                item_id = getattr(item, 'id', None)
                if item_id:
                    action_data["item_id"] = item_id
                item_name = getattr(item, 'name', None)
                if item_name:
                    action_data["item_name"] = item_name
            
            if "item_index" in kwargs:
                action_data["item_index"] = kwargs["item_index"]
            
            return action_data
        except Exception as e:
            self.logger.error(f"액션 직렬화 실패: {e}", exc_info=True)
            return {}
    
    def _deserialize_action(self, action_data: Dict[str, Any]) -> Tuple[ActionType, Optional[Any], Optional[Any], Dict[str, Any]]:
        """
        액션 역직렬화
        
        Args:
            action_data: 직렬화된 액션 데이터
            
        Returns:
            (action_type, target, skill, kwargs)
        """
        try:
            # 액션 타입
            action_type_str = action_data.get("action_type")
            action_type = ActionType(action_type_str) if action_type_str else None
            
            if not action_type:
                raise ValueError(f"알 수 없는 액션 타입: {action_type_str}")
            
            # 타겟 찾기
            target = None
            target_id = action_data.get("target_id")
            if target_id:
                target = self._find_character_by_id(target_id)
            
            # 스킬 찾기
            skill = None
            skill_id = action_data.get("skill_id")
            if skill_id:
                # 스킬 시스템에서 스킬 찾기
                from src.character.skills.skill_manager import get_skill_manager
                skill_manager = get_skill_manager()
                skill = skill_manager.get_skill(skill_id)
            
            # 추가 옵션
            kwargs = {}
            if "item_id" in action_data:
                # 아이템은 전투 관리자의 인벤토리에서 찾기
                if self.combat_manager and hasattr(self.combat_manager, 'inventory') and self.combat_manager.inventory:
                    inventory = self.combat_manager.inventory
                    item_id = action_data["item_id"]
                    
                    # 인벤토리에서 아이템 슬롯 인덱스 찾기
                    slot_index = inventory.find_item_by_id(item_id)
                    if slot_index is not None:
                        item = inventory.get_item(slot_index)
                        if item:
                            kwargs["item"] = item
                            self.logger.debug(f"아이템 찾기 성공: {item_id} (슬롯 {slot_index})")
                        else:
                            self.logger.warning(f"아이템 슬롯 {slot_index}에서 아이템을 찾을 수 없음: {item_id}")
                    else:
                        self.logger.warning(f"인벤토리에서 아이템을 찾을 수 없음: {item_id}")
            
            if "item_index" in action_data:
                kwargs["item_index"] = action_data["item_index"]
            
            return action_type, target, skill, kwargs
        except Exception as e:
            self.logger.error(f"액션 역직렬화 실패: {e}", exc_info=True)
            return None, None, None, {}
    
    def _serialize_action_result(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any],
        skill: Optional[Any],
        result: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        액션 결과 직렬화
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            result: 액션 결과
            **kwargs: 추가 옵션
            
        Returns:
            직렬화된 액션 결과
        """
        try:
            actor_id = self._get_character_id(actor)
            
            action_result = {
                "player_id": player_id,
                "actor_id": actor_id,
                "action_type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                "result": result,
                "timestamp": time.time()
            }
            
            if target:
                target_id = self._get_character_id(target)
                if target_id:
                    action_result["target_id"] = target_id
            
            if skill:
                skill_id = getattr(skill, 'id', None) or getattr(skill, 'skill_id', None)
                if skill_id:
                    action_result["skill_id"] = skill_id
            
            return action_result
        except Exception as e:
            self.logger.error(f"액션 결과 직렬화 실패: {e}", exc_info=True)
            return {}
    
    def _get_combat_state_snapshot(self) -> Dict[str, Any]:
        """
        전투 상태 스냅샷 생성 (동기화용)
        
        Returns:
            전투 상태 데이터
        """
        try:
            if not self.combat_manager:
                return {}
            
            snapshot = {
                "combat_state": self.combat_manager.state.value if hasattr(self.combat_manager.state, 'value') else str(self.combat_manager.state),
                "turn_count": self.combat_manager.turn_count,
                "allies": [],
                "enemies": []
            }
            
            # 아군 상태
            for ally in self.combat_manager.allies:
                char_data = self._get_character_state(ally)
                if char_data:
                    snapshot["allies"].append(char_data)
            
            # 적군 상태
            for enemy in self.combat_manager.enemies:
                char_data = self._get_character_state(enemy)
                if char_data:
                    snapshot["enemies"].append(char_data)
            
            return snapshot
        except Exception as e:
            self.logger.error(f"전투 상태 스냅샷 생성 실패: {e}", exc_info=True)
            return {}
    
    def _get_character_state(self, character: Any) -> Optional[Dict[str, Any]]:
        """
        캐릭터 상태 추출 (동기화용)
        
        Args:
            character: 캐릭터 객체
            
        Returns:
            캐릭터 상태 데이터
        """
        try:
            if not character:
                return None
            
            char_id = self._get_character_id(character)
            if not char_id:
                return None
            
            char_data = {
                "id": char_id,
                "current_hp": getattr(character, 'current_hp', 0),
                "max_hp": getattr(character, 'max_hp', 0),
                "current_mp": getattr(character, 'current_mp', 0),
                "max_mp": getattr(character, 'max_mp', 0),
                "current_brv": getattr(character, 'current_brv', 0),
                "is_alive": getattr(character, 'is_alive', True)
            }
            
            # ATB 게이지 상태
            if self.combat_manager and hasattr(self.combat_manager, 'atb'):
                gauge = self.combat_manager.atb.get_gauge(character)
                if gauge:
                    char_data["atb_current"] = gauge.current
                    char_data["atb_max"] = gauge.max_gauge
                    char_data["atb_can_act"] = gauge.can_act
            
            return char_data
        except Exception as e:
            self.logger.error(f"캐릭터 상태 추출 실패: {e}", exc_info=True)
            return None
    
    def _find_character_by_id(self, character_id: str) -> Optional[Any]:
        """
        ID로 캐릭터 찾기
        
        Args:
            character_id: 캐릭터 ID
            
        Returns:
            캐릭터 객체 (없으면 None)
        """
        try:
            if not self.combat_manager:
                return None
            
            # 아군에서 찾기
            for ally in self.combat_manager.allies:
                if self._get_character_id(ally) == character_id:
                    return ally
            
            # 적군에서 찾기
            for enemy in self.combat_manager.enemies:
                if self._get_character_id(enemy) == character_id:
                    return enemy
            
            return None
        except Exception as e:
            self.logger.error(f"캐릭터 찾기 실패: {character_id}: {e}", exc_info=True)
            return None
    
    def _get_character_id(self, character: Any) -> Optional[str]:
        """
        캐릭터 ID 추출
        
        Args:
            character: 캐릭터 객체
            
        Returns:
            캐릭터 ID (없으면 None)
        """
        try:
            if not character:
                return None
            
            # ID 속성 확인
            if hasattr(character, 'id'):
                return str(getattr(character, 'id'))
            
            if hasattr(character, 'character_id'):
                return str(getattr(character, 'character_id'))
            
            # 임시 ID 생성 (위치 기반)
            if hasattr(character, 'x') and hasattr(character, 'y'):
                x = getattr(character, 'x', 0)
                y = getattr(character, 'y', 0)
                return f"char_{x}_{y}"
            
            return None
        except Exception as e:
            self.logger.error(f"캐릭터 ID 추출 실패: {e}", exc_info=True)
            return None
    
    def _get_player_id_from_character(self, character: Any) -> Optional[str]:
        """
        캐릭터에서 플레이어 ID 추출
        
        Args:
            character: 캐릭터 객체
            
        Returns:
            플레이어 ID (없으면 None)
        """
        try:
            if not character:
                return None
            
            # 직접 player_id 속성이 있는지 확인
            if hasattr(character, 'player_id'):
                return getattr(character, 'player_id', None)
            
            # owner를 통한 확인
            if hasattr(character, 'owner') and hasattr(character.owner, 'player_id'):
                return getattr(character.owner, 'player_id', None)
            
            return None
        except Exception as e:
            self.logger.error(f"플레이어 ID 추출 실패: {e}", exc_info=True)
            return None

