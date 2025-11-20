"""
스킬 부활 처리

부활 스킬 사용 시 부활 시스템과 연동하여 처리
"""

from typing import Optional, Any, Dict
from src.character.character import Character
from src.character.skills.skill import Skill
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.revival_system import RevivalSystem
from src.multiplayer.player_state import PlayerStateManager
from src.core.logger import get_logger


class SkillRevivalHandler:
    """스킬 부활 처리기"""
    
    def __init__(self, revival_system: RevivalSystem):
        """
        초기화
        
        Args:
            revival_system: 부활 시스템
        """
        self.revival_system = revival_system
        self.logger = get_logger("multiplayer.skill_revival")
    
    def is_revival_skill(self, skill: Skill) -> bool:
        """
        부활 스킬인지 확인
        
        Args:
            skill: 스킬 객체
            
        Returns:
            부활 스킬 여부
        """
        if not skill:
            return False
        
        # 메타데이터에서 revival 플래그 확인
        if hasattr(skill, 'metadata') and skill.metadata:
            if skill.metadata.get('revival', False):
                return True
        
        # 스킬 ID로 확인
        revival_skill_ids = [
            'cleric_resurrect',
            'resurrection',
            'priest_resurrection'
        ]
        
        if hasattr(skill, 'skill_id') and skill.skill_id in revival_skill_ids:
            return True
        
        # 스킬 이름으로 확인
        revival_skill_names = ['부활', 'Resurrection', 'Resurrect']
        if hasattr(skill, 'name') and skill.name in revival_skill_names:
            return True
        
        return False
    
    def can_target_revive(self, target: Character) -> bool:
        """
        대상이 부활 가능한지 확인
        
        Args:
            target: 대상 캐릭터
            
        Returns:
            부활 가능 여부
        """
        return self.revival_system.can_revive(target)
    
    def handle_skill_revival(
        self,
        skill: Skill,
        user: Character,
        target: Character,
        player: Optional[MultiplayerPlayer] = None
    ) -> bool:
        """
        스킬 부활 처리
        
        Args:
            skill: 부활 스킬
            user: 스킬 사용자
            target: 대상 캐릭터 (부활할 캐릭터)
            player: 대상 캐릭터의 플레이어 객체 (선택적)
            
        Returns:
            부활 성공 여부
        """
        if not self.is_revival_skill(skill):
            self.logger.warning(f"스킬 {skill.name if hasattr(skill, 'name') else 'Unknown'}은 부활 스킬이 아닙니다")
            return False
        
        if not self.can_target_revive(target):
            self.logger.warning(f"캐릭터 {target.name}은(는) 부활할 수 없습니다")
            return False
        
        # 플레이어 객체 찾기 (없으면 None)
        if not player and hasattr(target, 'player_id'):
            # target의 player_id로 플레이어 객체 찾기
            target_player_id = getattr(target, 'player_id', None)
            if target_player_id and self.revival_system:
                # PlayerStateManager를 통해 세션 접근
                if hasattr(self.revival_system, 'player_state_manager') and self.revival_system.player_state_manager:
                    player_state_manager = self.revival_system.player_state_manager
                    if hasattr(player_state_manager, 'session') and player_state_manager.session:
                        session = player_state_manager.session
                        if hasattr(session, 'players') and target_player_id in session.players:
                            player = session.players[target_player_id]
                            self.logger.debug(f"타겟 플레이어 찾기 성공: {target_player_id}")
                        else:
                            self.logger.warning(f"세션에서 타겟 플레이어를 찾을 수 없음: {target_player_id}")
        
        # 부활 처리
        success = self.revival_system.revive_character(
            player=player or None,
            character=target,
            revive_skill=skill,
            skill_user=user,
            hp_percentage=self._get_revival_hp_percentage(skill)
        )
        
        if success:
            self.logger.info(
                f"✅ 스킬 부활 성공: {user.name}이(가) {target.name}을(를) 부활시켰습니다"
            )
        
        return success
    
    def _get_revival_hp_percentage(self, skill: Skill) -> float:
        """
        부활 스킬의 HP 회복 비율 가져오기
        
        Args:
            skill: 부활 스킬
            
        Returns:
            HP 회복 비율 (0.0 ~ 1.0)
        """
        # 기본값: 50%
        default_percentage = 0.5
        
        if not hasattr(skill, 'effects'):
            return default_percentage
        
        # HealEffect에서 percentage 찾기
        for effect in skill.effects:
            if hasattr(effect, 'heal_type') and hasattr(effect, 'percentage'):
                return effect.percentage
        
        # 메타데이터에서 확인
        if hasattr(skill, 'metadata') and skill.metadata:
            metadata = skill.metadata
            # 클레릭 부활: 75%
            if metadata.get('revival', False) and skill.skill_id == 'cleric_resurrect':
                return 0.75
            # 기타 부활 스킬: 메타데이터 확인
            if 'revival_hp_percentage' in metadata:
                return metadata['revival_hp_percentage']
        
        return default_percentage
    
    def process_skill_effect(
        self,
        skill: Skill,
        user: Character,
        target: Character,
        skill_result: Any,
        player: Optional[MultiplayerPlayer] = None
    ) -> bool:
        """
        스킬 효과 처리 중 부활 처리
        
        Args:
            skill: 사용한 스킬
            user: 스킬 사용자
            target: 대상 캐릭터
            skill_result: 스킬 실행 결과
            player: 대상 캐릭터의 플레이어 객체 (선택적)
            
        Returns:
            부활 처리 여부
        """
        # 부활 스킬인지 확인
        if not self.is_revival_skill(skill):
            return False
        
        # 부활 처리
        return self.handle_skill_revival(skill, user, target, player)

