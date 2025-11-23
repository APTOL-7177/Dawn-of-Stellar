"""
던전 플로어 전환 관리자 (Floor Transition Manager)

던전과 마을 사이의 전환을 관리합니다.
"""

from typing import Optional, Any, Dict
from src.core.logger import get_logger

logger = get_logger("floor_transition")


class FloorTransitionManager:
    """층 전환 관리자 - 멀티플레이어 지원"""
    
    def __init__(self, player_id: str = "default"):
        self.player_id = player_id  # 멀티플레이어용 플레이어 ID
        self.current_floor = 0  # 0 = 마을
        self.can_visit_town = True
        self.town_bgm = "town.ogg"
        # dungeon_bgm은 층별로 동적 계산 (바이옴 시스템)
        self.is_ready = False  # 준비 상태
    
    def get_biome_bgm(self, floor_number: int) -> str:
        """
        층 번호에 따른 바이옴 BGM 반환
        
        10개 바이옴이 순환 (biome_0 ~ biome_9)
        1층 = biome_0, 2층 = biome_1, ..., 10층 = biome_9, 11층 = biome_0
        
        Args:
            floor_number: 던전 층 번호
            
        Returns:
            바이옴 BGM 트랙명 (예: "biome_3")
        """
        if floor_number <= 0:
            return self.town_bgm
        
        biome_index = (floor_number - 1) % 10
        return f"biome_{biome_index}"
    
    def enter_dungeon_floor(self, floor_number: int) -> dict:
        """
        던전 층 입장
        
        Args:
            floor_number: 입장할 층 번호
            
        Returns:
            전환 정보
        """
        self.current_floor = floor_number
        self.can_visit_town = True  # 다음 층 이동 시 마을 방문 가능
        self.is_ready = False  # 던전 입장 시 준비 해제
        
        # 바이옴별 BGM 계산
        biome_bgm = self.get_biome_bgm(floor_number)
        
        logger.info(f"[Player {self.player_id}] 던전 {floor_number}층 입장 → BGM: {biome_bgm}")
        
        return {
            "location": "dungeon",
            "floor": floor_number,
            "bgm": biome_bgm,  # 바이옴별 BGM
            "can_return_to_town": True
        }
    
    def return_to_town(self) -> dict:
        """
        마을로 귀환
        
        Returns:
            전환 정보
        """
        if not self.can_visit_town:
            logger.warning(f"[Player {self.player_id}] 아직 마을로 돌아갈 수 없습니다.")
            return {"success": False, "message": "아직 마을로 돌아갈 수 없습니다."}
        
        self.can_visit_town = False  # 한 번 방문하면 다음 층까지 방문 불가
        self.is_ready = False  # 마을 도착 시 준비 해제
        
        logger.info(f"[Player {self.player_id}] {self.current_floor}층에서 마을로 귀환")
        
        return {
            "success": True,
            "location": "town",
            "bgm": self.town_bgm,
            "last_floor": self.current_floor
        }
    
    def leave_town(self) -> dict:
        """
        마을에서 던전으로 출발 - 자동 준비 상태
        
        Returns:
            출발 정보
        """
        self.is_ready = True  # 마을 떠날 때 자동 준비
        logger.info(f"[Player {self.player_id}] 마을 출발 - 자동 준비 완료")
        
        return {
            "success": True,
            "is_ready": True,
            "message": "던전으로 출발합니다. 준비 완료!"
        }
    
    def get_current_location(self) -> dict:
        """현재 위치 정보 (바이옴 BGM 포함)"""
        if self.current_floor == 0:
            return {
                "location": "town",
                "floor": 0,
                "bgm": self.town_bgm
            }
        else:
            # 던전: 바이옴별 BGM
            biome_bgm = self.get_biome_bgm(self.current_floor)
            return {
                "location": "dungeon",
                "floor": self.current_floor,
                "bgm": biome_bgm
            }
    
    def on_floor_clear(self):
        """층 클리어 시 - 마을 방문 가능하게"""
        self.can_visit_town = True
        logger.info(f"{self.current_floor}층 클리어! 마을 방문 가능")


# 멀티플레이어 지원: 플레이어별 인스턴스
_floor_transition_managers: Dict[str, FloorTransitionManager] = {}

def get_floor_transition_manager(player_id: str = "default") -> FloorTransitionManager:
    """
    플레이어별 FloorTransitionManager 가져오기
    
    Args:
        player_id: 플레이어 ID (멀티플레이어용)
        
    Returns:
        해당 플레이어의 FloorTransitionManager
    """
    if player_id not in _floor_transition_managers:
        _floor_transition_managers[player_id] = FloorTransitionManager(player_id)
    return _floor_transition_managers[player_id]


def rest_at_inn(party_members: list, cost: int, player_gold: int) -> dict:
    """
    여관에서 휴식
    
    Args:
        party_members: 파티 멤버 리스트
        cost: 비용
        player_gold: 플레이어 골드
        
    Returns:
        결과
    """
    if player_gold < cost:
        return {
            "success": False,
            "message": f"골드가 부족합니다. (필요: {cost}, 보유: {player_gold})"
        }
    
    # 파티 전체 회복 + 부활
    revived_count = 0
    for member in party_members:
        # HP/MP 완전 회복
        if hasattr(member, 'max_hp'):
            member.current_hp = member.max_hp
        if hasattr(member, 'max_mp'):
            member.current_mp = member.max_mp
        
        # 쓰러진 상태 회복
        if hasattr(member, 'is_alive') and not member.is_alive:
            member.is_alive = True
            member.current_hp = member.max_hp
            revived_count += 1
            logger.info(f"{member.name} 부활!")
        
        # 상태이상 제거
        if hasattr(member, 'status_effects'):
            member.status_effects.clear()
    
    logger.info(f"여관에서 휴식: 파티 {len(party_members)}명 회복, {revived_count}명 부활")
    
    return {
        "success": True,
        "message": f"파티 전원이 완전히 회복되었습니다! ({revived_count}명 부활)",
        "cost": cost,
        "revived": revived_count
    }
