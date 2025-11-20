"""
멀티플레이 파티 설정 시스템

멀티플레이 전용 파티 구성 시스템
- 직업 중복 방지 (모든 플레이어 간)
- 패시브는 호스트가 결정
- 각 플레이어는 자신의 캐릭터만 선택
"""

from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
import yaml
from pathlib import Path

from src.ui.party_setup import PartyMember
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.multiplayer.protocol import NetworkMessage, MessageType, MessageBuilder
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress


@dataclass
class MultiplayerPartySetup:
    """멀티플레이 파티 설정"""
    
    session: MultiplayerSession
    player_id: str
    is_host: bool
    
    # 현재 플레이어의 파티
    my_party: List[PartyMember] = field(default_factory=list)
    
    # 선택된 패시브 (호스트가 결정)
    selected_passives: List[str] = field(default_factory=list)
    
    # 모든 플레이어가 선택한 직업 (중복 방지용)
    used_jobs: Set[str] = field(default_factory=set)
    
    # 직업 데이터
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    
    # 네트워크 관리자 (선택적)
    network_manager: Optional[Any] = None
    
    # 상태
    is_completed: bool = False
    
    def __post_init__(self):
        self.logger = get_logger("multiplayer.party_setup")
        self.jobs = self._load_jobs()
        
        # 호스트인 경우 패시브 선택 가능
        if self.is_host:
            self.selected_passives = []
    
    def _load_jobs(self) -> List[Dict[str, Any]]:
        """직업 데이터 로드"""
        jobs = []
        characters_dir = Path("data/characters")
        
        if not characters_dir.exists():
            self.logger.error("캐릭터 디렉토리 없음: data/characters")
            return jobs
        
        # 메타 진행 정보 가져오기
        meta = get_meta_progress()
        
        # 개발 모드 확인
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)
        
        for yaml_file in sorted(characters_dir.glob("*.yaml")):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    job_id = yaml_file.stem
                    
                    # 개발 모드이거나 메타 진행에서 해금된 직업인지 확인
                    is_unlocked = dev_mode or meta.is_job_unlocked(job_id)
                    
                    jobs.append({
                        'id': job_id,
                        'name': data.get('class_name', job_id),
                        'description': data.get('description', ''),
                        'archetype': data.get('archetype', ''),
                        'stats': data.get('base_stats', {}),
                        'unlocked': is_unlocked
                    })
            except Exception as e:
                self.logger.error(f"직업 로드 실패: {yaml_file.name}: {e}")
        
        self.logger.info(f"직업 {len(jobs)}개 로드 완료")
        return jobs
    
    def get_available_jobs(self) -> List[Dict[str, Any]]:
        """
        선택 가능한 직업 목록 반환 (사용된 직업 제외)
        
        Returns:
            사용 가능한 직업 목록
        """
        available_jobs = []
        
        for job in self.jobs:
            job_id = job.get('id', '')
            
            # 해금된 직업이고, 사용되지 않은 직업만 반환
            if job.get('unlocked', False) and job_id not in self.used_jobs:
                available_jobs.append(job)
        
        return available_jobs
    
    def can_select_job(self, job_id: str) -> bool:
        """
        직업 선택 가능 여부 확인
        
        Args:
            job_id: 직업 ID
            
        Returns:
            선택 가능 여부
        """
        # 이미 사용된 직업인지 확인
        if job_id in self.used_jobs:
            return False
        
        # 해금된 직업인지 확인
        for job in self.jobs:
            if job.get('id') == job_id:
                return job.get('unlocked', False)
        
        return False
    
    def add_job_to_used_list(self, job_id: str):
        """
        직업을 사용된 목록에 추가 (호스트만)
        
        Args:
            job_id: 직업 ID
        """
        if not self.is_host:
            self.logger.warning("클라이언트는 used_jobs를 직접 수정할 수 없습니다")
            return
        
        if job_id not in self.used_jobs:
            self.used_jobs.add(job_id)
            
            # 모든 클라이언트에게 직업 사용 알림
            if self.network_manager:
                message = NetworkMessage(
                    type=MessageType.PLAYER_JOINED,  # 임시로 사용
                    data={
                        "action": "job_selected",
                        "job_id": job_id
                    }
                )
                self.network_manager.broadcast(message)
    
    def remove_job_from_used_list(self, job_id: str):
        """
        직업을 사용된 목록에서 제거 (호스트만)
        
        Args:
            job_id: 직업 ID
        """
        if not self.is_host:
            self.logger.warning("클라이언트는 used_jobs를 직접 수정할 수 없습니다")
            return
        
        if job_id in self.used_jobs:
            self.used_jobs.remove(job_id)
            
            # 모든 클라이언트에게 직업 해제 알림
            if self.network_manager:
                message = NetworkMessage(
                    type=MessageType.PLAYER_JOINED,  # 임시로 사용
                    data={
                        "action": "job_deselected",
                        "job_id": job_id
                    }
                )
                self.network_manager.broadcast(message)
    
    def add_party_member(self, member: PartyMember) -> bool:
        """
        파티 멤버 추가
        
        Args:
            member: 파티 멤버
            
        Returns:
            추가 성공 여부
        """
        # 최대 4명 체크
        if len(self.my_party) >= 4:
            self.logger.warning("파티가 가득 찼습니다 (최대 4명)")
            return False
        
        # 직업 중복 체크
        if not self.can_select_job(member.job_id):
            self.logger.warning(f"직업 {member.job_id}는 이미 사용되었거나 선택할 수 없습니다")
            return False
        
        # 파티에 추가
        self.my_party.append(member)
        
        # 사용된 직업 목록에 추가 (호스트에게 요청)
        if self.is_host:
            self.add_job_to_used_list(member.job_id)
        elif self.network_manager:
            # 클라이언트: 호스트에게 직업 선택 요청
            message = NetworkMessage(
                type=MessageType.PLAYER_JOINED,  # 임시로 사용
                player_id=self.player_id,
                data={
                    "action": "request_job",
                    "job_id": member.job_id
                }
            )
            self.network_manager.send(message)
        
        return True
    
    def remove_party_member(self, index: int) -> bool:
        """
        파티 멤버 제거
        
        Args:
            index: 제거할 멤버 인덱스
            
        Returns:
            제거 성공 여부
        """
        if index < 0 or index >= len(self.my_party):
            return False
        
        member = self.my_party[index]
        job_id = member.job_id
        
        # 파티에서 제거
        del self.my_party[index]
        
        # 사용된 직업 목록에서 제거 (호스트에게 요청)
        if self.is_host:
            self.remove_job_from_used_list(job_id)
        elif self.network_manager:
            # 클라이언트: 호스트에게 직업 해제 요청
            message = NetworkMessage(
                type=MessageType.PLAYER_JOINED,  # 임시로 사용
                player_id=self.player_id,
                data={
                    "action": "release_job",
                    "job_id": job_id
                }
            )
            self.network_manager.send(message)
        
        return True
    
    def set_passives(self, passives: List[str]) -> bool:
        """
        패시브 설정 (호스트만 가능)
        
        Args:
            passives: 선택한 패시브 목록
            
        Returns:
            설정 성공 여부
        """
        if not self.is_host:
            self.logger.warning("패시브는 호스트만 설정할 수 있습니다")
            return False
        
        self.selected_passives = passives
        
        # 모든 클라이언트에게 패시브 전송
        if self.network_manager:
            message = NetworkMessage(
                type=MessageType.PLAYER_JOINED,  # 임시로 사용
                data={
                    "action": "passives_set",
                    "passives": passives
                }
            )
            self.network_manager.broadcast(message)
        
        return True
    
    def get_all_used_jobs(self) -> Set[str]:
        """
        모든 플레이어가 사용한 직업 목록 가져오기
        
        Returns:
            사용된 직업 ID 집합
        """
        return self.used_jobs.copy()
    
    def sync_used_jobs_from_host(self, used_jobs: Set[str]):
        """
        호스트로부터 사용된 직업 목록 동기화 (클라이언트용)
        
        Args:
            used_jobs: 호스트가 보낸 사용된 직업 목록
        """
        if self.is_host:
            self.logger.warning("호스트는 이 메서드를 사용할 수 없습니다")
            return
        
        self.used_jobs = used_jobs.copy()
        self.logger.info(f"사용된 직업 목록 동기화: {len(used_jobs)}개")


class MultiplayerPartyValidator:
    """멀티플레이 파티 검증"""
    
    @staticmethod
    def validate_party(session: MultiplayerSession) -> tuple[bool, Optional[str]]:
        """
        모든 플레이어의 파티 검증
        
        Args:
            session: 멀티플레이 세션
            
        Returns:
            (검증 성공 여부, 오류 메시지)
        """
        # 1. 모든 플레이어가 파티를 구성했는지 확인
        for player_id, player in session.players.items():
            if not hasattr(player, 'party') or not player.party or len(player.party) == 0:
                return False, f"플레이어 {player.player_name}의 파티가 비어있습니다"
        
        # 2. 직업 중복 체크
        all_jobs: Set[str] = set()
        
        for player_id, player in session.players.items():
            if hasattr(player, 'party') and player.party:
                for member in player.party:
                    job_id = getattr(member, 'job_id', None)
                    if not job_id:
                        continue
                    
                    if job_id in all_jobs:
                        return False, f"직업 {job_id}가 중복되었습니다"
                    
                    all_jobs.add(job_id)
        
        return True, None

