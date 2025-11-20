"""
부활 시스템

부활 아이템 및 부활 스킬을 사용하여 캐릭터를 부활시키는 시스템
"""

from typing import List, Optional, Tuple, Dict, Any, Union
from dataclasses import dataclass

from src.character.character import Character
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.player_state import PlayerStateManager
from src.core.logger import get_logger


class RevivalSystem:
    """부활 시스템"""
    
    def __init__(self, player_state_manager: PlayerStateManager):
        """
        초기화
        
        Args:
            player_state_manager: 플레이어 상태 관리자
        """
        self.player_state_manager = player_state_manager
        self.logger = get_logger("multiplayer.revival")
    
    def revive_character(
        self,
        player: MultiplayerPlayer,
        character: Character,
        revive_item: Optional[Any] = None,
        revive_skill: Optional[Any] = None,
        skill_user: Optional[Character] = None,
        target_position: Optional[Tuple[int, int]] = None,
        hp_percentage: float = 0.5
    ) -> bool:
        """
        캐릭터 부활
        
        Args:
            player: 플레이어 객체
            character: 부활할 캐릭터
            revive_item: 부활 아이템 (선택적)
            revive_skill: 부활 스킬 (선택적)
            skill_user: 스킬 사용자 (부활 스킬 사용 시)
            target_position: 부활 위치 (None이면 플레이어 옆에 스폰)
            hp_percentage: 부활 시 HP 비율 (기본 0.5 = 50%, 스킬/아이템에 따라 다름)
            
        Returns:
            부활 성공 여부
        """
        # 이미 살아있는지 확인
        is_alive = False
        if hasattr(character, 'is_alive'):
            is_alive = character.is_alive
        elif hasattr(character, 'current_hp'):
            is_alive = character.current_hp > 0
        
        if is_alive:
            self.logger.warning(f"캐릭터 {character.name}은(는) 이미 살아있습니다")
            return False
        
        # 부활 처리
        try:
            # HP 회복 비율 결정
            actual_hp_percentage = hp_percentage  # 기본값 사용
            
            # 부활 스킬의 경우 메타데이터에서 비율 가져오기
            if revive_skill and hasattr(revive_skill, 'metadata'):
                skill_metadata = revive_skill.metadata
                # 부활 스킬의 경우 percentage 효과 확인
                if skill_metadata.get('revival', False):
                    # HealEffect에서 percentage 가져오기
                    for effect in getattr(revive_skill, 'effects', []):
                        if hasattr(effect, 'heal_type') and hasattr(effect, 'percentage'):
                            actual_hp_percentage = effect.percentage
                            break
            
            # 부활 아이템의 경우 effect_value 확인
            if revive_item and hasattr(revive_item, 'effect_value'):
                if hasattr(revive_item, 'effect_type') and revive_item.effect_type == "revive":
                    # effect_value가 비율이거나 고정값일 수 있음
                    item_value = revive_item.effect_value
                    if isinstance(item_value, float) and 0 < item_value <= 1:
                        actual_hp_percentage = item_value
                    elif isinstance(item_value, int) and item_value > 0:
                        # 고정값인 경우 (예: 100, 150)
                        actual_hp_percentage = None  # 아래에서 처리
            
            # HP 회복 (최대 HP의 일부로 부활)
            max_hp = getattr(character, 'max_hp', None)
            if max_hp is None:
                # StatManager를 통해 max_hp 가져오기
                if hasattr(character, 'stat_manager'):
                    max_hp = character.stat_manager.get_stat('hp')
            
            if max_hp:
                if actual_hp_percentage is not None:
                    revive_hp = int(max_hp * actual_hp_percentage)
                elif revive_item and hasattr(revive_item, 'effect_value'):
                    # 고정값 사용
                    revive_hp = min(int(revive_item.effect_value), max_hp)
                else:
                    revive_hp = int(max_hp * 0.5)  # 기본 50%
                
                character.current_hp = revive_hp
            else:
                # max_hp를 찾을 수 없으면 기본값 사용
                character.current_hp = 50
            
            # MP 회복 (최대 MP의 일부로 부활)
            max_mp = getattr(character, 'max_mp', None)
            if max_mp is None:
                # StatManager를 통해 max_mp 가져오기
                if hasattr(character, 'stat_manager'):
                    max_mp = character.stat_manager.get_stat('mp')
            
            if max_mp:
                revive_mp = int(max_mp * 0.5)  # 최대 MP의 50%로 부활
                character.current_mp = revive_mp
            else:
                # max_mp를 찾을 수 없으면 기본값 사용
                character.current_mp = 25
            
            # is_alive 플래그 설정
            if hasattr(character, 'is_alive'):
                character.is_alive = True
            
            # 상처 상태 초기화 (있는 경우)
            if hasattr(character, 'current_wounds'):
                character.current_wounds = 0
            
            # 상태 효과 제거 (부활 시 모든 상태 효과 제거)
            if hasattr(character, 'status_effects'):
                character.status_effects.clear()
            
            # 플레이어 옆에 스폰 (스킬 사용 시 스킬 사용자 옆에, 아니면 플레이어 옆에)
            spawn_player = player
            if skill_user and hasattr(skill_user, 'player_id'):
                # 스킬 사용자가 다른 플레이어일 수 있음
                skill_user_player_id = getattr(skill_user, 'player_id', None)
                if skill_user_player_id and self.player_state_manager:
                    # 세션에서 플레이어 객체 찾기
                    if hasattr(self.player_state_manager, 'session') and self.player_state_manager.session:
                        session = self.player_state_manager.session
                        if hasattr(session, 'players') and skill_user_player_id in session.players:
                            spawn_player = session.players[skill_user_player_id]
                            self.logger.debug(f"스킬 사용자 플레이어 찾기 성공: {skill_user_player_id}")
                        else:
                            self.logger.warning(f"세션에서 스킬 사용자 플레이어를 찾을 수 없음: {skill_user_player_id}")
            
            spawn_x, spawn_y = self.player_state_manager.handle_character_revival(
                spawn_player,
                character,
                target_position
            )
            
            # max_hp 가져오기
            max_hp_display = getattr(character, 'max_hp', None)
            if max_hp_display is None and hasattr(character, 'stat_manager'):
                max_hp_display = character.stat_manager.get_stat('hp')
            
            revival_method = "아이템"
            if revive_skill:
                revival_method = f"스킬 ({revive_skill.name if hasattr(revive_skill, 'name') else '부활'})"
            elif skill_user:
                revival_method = f"스킬 (사용자: {skill_user.name if hasattr(skill_user, 'name') else 'Unknown'})"
            
            self.logger.info(
                f"✅ 캐릭터 {character.name} 부활 완료 "
                f"({revival_method}, HP: {character.current_hp}/{max_hp_display or '?'}, "
                f"위치: ({spawn_x}, {spawn_y}))"
            )
            
            return True
        
        except Exception as e:
            self.logger.error(f"캐릭터 부활 실패: {e}", exc_info=True)
            return False
    
    def can_revive(self, character: Character) -> bool:
        """
        부활 가능 여부 확인
        
        Args:
            character: 부활할 캐릭터
            
        Returns:
            부활 가능 여부
        """
        # 이미 살아있으면 부활 불가
        is_alive = False
        if hasattr(character, 'is_alive'):
            is_alive = character.is_alive
        elif hasattr(character, 'current_hp'):
            is_alive = character.current_hp > 0
        
        if is_alive:
            return False
        
        return True
    
    def get_dead_characters(self, player: MultiplayerPlayer) -> List[Character]:
        """
        플레이어의 사망한 캐릭터 목록 가져오기
        
        Args:
            player: 플레이어 객체
            
        Returns:
            사망한 캐릭터 목록
        """
        dead_characters = []
        
        if hasattr(player, 'party') and player.party:
            for character in player.party:
                is_alive = True
                if hasattr(character, 'is_alive'):
                    is_alive = character.is_alive
                elif hasattr(character, 'current_hp'):
                    is_alive = character.current_hp > 0
                
                if not is_alive:
                    dead_characters.append(character)
        
        return dead_characters
    
    def get_all_dead_characters(
        self,
        players: Dict[str, MultiplayerPlayer]
    ) -> Dict[str, List[Character]]:
        """
        모든 플레이어의 사망한 캐릭터 목록 가져오기
        
        Args:
            players: 플레이어 딕셔너리
            
        Returns:
            {player_id: [dead_characters]} 사망한 캐릭터 목록
        """
        all_dead = {}
        
        for player_id, player in players.items():
            dead_characters = self.get_dead_characters(player)
            if dead_characters:
                all_dead[player_id] = dead_characters
        
        return all_dead

