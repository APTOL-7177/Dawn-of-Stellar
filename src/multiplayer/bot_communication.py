"""
Bot Communication Network

봇 간 정보 공유 시스템:
- 발견한 아이템 위치 공유
- 자원 노드 정보 교환
- 위험 지역 알림
- 중복 수집 방지
"""

import time
from typing import Dict, Any, Optional, Tuple, List, Set
from src.core.logger import get_logger

logger = get_logger("bot_communication")


class BotCommunicationNetwork:
    """
    봇 간 정보 공유 네트워크 (싱글톤)
    
    모든 봇이 공유하는 중앙 정보 저장소
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # 발견한 아이템 {(x, y): {item, discovered_by, time, claimed_by}}
        self.discovered_items: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        # 자원 노드 {(x, y): {type, quantity, discovered_by, time}}
        self.resource_nodes: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        # 위험 지역 {(x, y): {threat_type, level, time}}
        self.danger_zones: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        # 관심 지점 {(x, y): {type: "chest|stairs|npc", time}}
        self.interest_points: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        # 봇 상태 {bot_id: {position, health, activity, time}}
        self.bot_states: Dict[str, Dict[str, Any]] = {}
        
        # 공유된 특수 위치
        self.shared_locations: Dict[str, Tuple[int, int]] = {}  # {name: (x, y)}
        
        logger.info("봇 소통 네트워크 초기화 완료")
    
    def share_item_location(self, bot_id: str, position: Tuple[int, int], item: Any):
        """
        아이템 위치 공유
        
        Args:
            bot_id: 발견한 봇 ID
            position: 아이템 위치 (x, y)
            item: 아이템 객체
        """
        if position not in self.discovered_items:
            self.discovered_items[position] = {
                "item": item,
                "discovered_by": bot_id,
                "time": time.time(),
                "claimed_by": None
            }
            
            item_name = getattr(item, 'name', 'Unknown')
            logger.info(f"봇 {bot_id}가 아이템 발견 공유: {item_name} at {position}")
    
    def claim_item(self, position: Tuple[int, int], bot_id: str) -> bool:
        """
        아이템 수집 선언 (중복 방지)
        
        Args:
            position: 아이템 위치
            bot_id: 수집하는 봇 ID
        
        Returns:
            수집 가능 여부
        """
        if position in self.discovered_items:
            item_data = self.discovered_items[position]
            
            # 이미 다른 봇이 수집 중
            if item_data.get("claimed_by") and item_data["claimed_by"] != bot_id:
                return False
            
            item_data["claimed_by"] = bot_id
            return True
        
        return False
    
    def unclaim_item(self, position: Tuple[int, int], bot_id: str):
        """아이템 수집 취소"""
        if position in self.discovered_items:
            item_data = self.discovered_items[position]
            if item_data.get("claimed_by") == bot_id:
                item_data["claimed_by"] = None
    
    def remove_item(self, position: Tuple[int, int]):
        """수집 완료된 아이템 제거"""
        if position in self.discovered_items:
            del self.discovered_items[position]
    
    def share_resource_node(self, bot_id: str, position: Tuple[int, int], 
                           node_type: str, quantity: int):
        """
        자원 노드 공유
        
        Args:
            bot_id: 발견한 봇
            position: 노드 위치
            node_type: 노드 타입 (ingredient, mineral 등)
            quantity: 수량
        """
        self.resource_nodes[position] = {
            "type": node_type,
            "quantity": quantity,
            "discovered_by": bot_id,
            "time": time.time()
        }
        
        logger.info(f"봇 {bot_id}가 자원 노드 공유: {node_type} x{quantity} at {position}")
    
    def update_resource_node(self, position: Tuple[int, int], new_quantity: int):
        """자원 노드 수량 업데이트"""
        if position in self.resource_nodes:
            if new_quantity <= 0:
                del self.resource_nodes[position]
            else:
                self.resource_nodes[position]["quantity"] = new_quantity
    
    def share_danger_zone(self, bot_id: str, position: Tuple[int, int], 
                         threat_type: str, level: int):
        """
        위험 지역 공유
        
        Args:
            bot_id: 발견한 봇
            position: 위험 지역 위치
            threat_type: 위협 타입 (enemy, trap 등)
            level: 위협 레벨
        """
        self.danger_zones[position] = {
            "threat_type": threat_type,
            "level": level,
            "reported_by": bot_id,
            "time": time.time()
        }
        
        logger.warning(f"봇 {bot_id}가 위험 지역 보고: {threat_type} (Lv.{level}) at {position}")
    
    def is_danger_zone(self, position: Tuple[int, int]) -> bool:
        """위험 지역인지 확인"""
        return position in self.danger_zones
    
    def share_interest_point(self, bot_id: str, position: Tuple[int, int], point_type: str):
        """
        관심 지점 공유 (보물상자, 계단, NPC 등)
        
        Args:
            bot_id: 발견한 봇
            position: 지점 위치
            point_type: 지점 타입
        """
        self.interest_points[position] = {
            "type": point_type,
            "discovered_by": bot_id,
            "time": time.time()
        }
        
        logger.info(f"봇 {bot_id}가 관심 지점 공유: {point_type} at {position}")
    
    def update_bot_state(self, bot_id: str, position: Tuple[int, int], 
                        health_percent: float, activity: str):
        """
        봇 상태 업데이트
        
        Args:
            bot_id: 봇 ID
            position: 현재 위치
            health_percent: HP 퍼센트 (0.0~1.0)
            activity: 현재 활동 (exploring, farming, combat 등)
        """
        self.bot_states[bot_id] = {
            "position": position,
            "health": health_percent,
            "activity": activity,
            "time": time.time()
        }
    
    def get_nearest_unclaimed_item(self, current_pos: Tuple[int, int], 
                                    bot_id: str, max_distance: int = 20) -> Optional[Tuple[Tuple[int, int], Any]]:
        """
        가장 가까운 미수집 아이템 찾기
        
        Args:
            current_pos: 현재 위치
            bot_id: 봇 ID
            max_distance: 최대 거리
        
        Returns:
            (위치, 아이템) 또는 None
        """
        nearest = None
        nearest_dist = float('inf')
        
        for pos, data in self.discovered_items.items():
            # 이미 다른 봇이 수집 중
            if data.get("claimed_by") and data["claimed_by"] != bot_id:
                continue
            
            # 거리 계산
            dist = abs(pos[0] - current_pos[0]) + abs(pos[1] - current_pos[1])
            
            if dist <= max_distance and dist < nearest_dist:
                nearest_dist = dist
                nearest = (pos, data["item"])
        
        return nearest
    
    def get_nearby_resources(self, current_pos: Tuple[int, int], 
                            max_distance: int = 15) -> List[Tuple[Tuple[int, int], Dict]]:
        """
        근처 자원 노드 목록
        
        Args:
            current_pos: 현재 위치
            max_distance: 최대 거리
        
        Returns:
            [(위치, 노드 정보), ...]
        """
        nearby = []
        
        for pos, data in self.resource_nodes.items():
            dist = abs(pos[0] - current_pos[0]) + abs(pos[1] - current_pos[1])
            if dist <= max_distance:
                nearby.append((pos, data))
        
        # 거리순 정렬
        nearby.sort(key=lambda x: abs(x[0][0] - current_pos[0]) + abs(x[0][1] - current_pos[1]))
        
        return nearby
    
    def set_shared_location(self, name: str, position: Tuple[int, int], bot_id: str):
        """
        특수 위치 공유 (예: "보물방", "안전지대")
        
        Args:
            name: 위치 이름
            position: 위치
            bot_id: 공유한 봇
        """
        self.shared_locations[name] = position
        logger.info(f"📍 봇 {bot_id}가 특수 위치 공유: {name} at {position}")
    
    def get_shared_location(self, name: str) -> Optional[Tuple[int, int]]:
        """공유된 위치 가져오기"""
        return self.shared_locations.get(name)
    
    def cleanup_old_data(self, max_age: float = 300.0):
        """
        오래된 데이터 정리 (5분 이상)
        
        Args:
            max_age: 최대 유지 시간 (초)
        """
        current_time = time.time()
        
        # 오래된 아이템 제거
        old_items = [pos for pos, data in self.discovered_items.items() 
                     if current_time - data["time"] > max_age]
        for pos in old_items:
            del self.discovered_items[pos]
        
        # 오래된 위험 지역 제거
        old_dangers = [pos for pos, data in self.danger_zones.items() 
                       if current_time - data["time"] > max_age]
        for pos in old_dangers:
            del self.danger_zones[pos]
        
        if old_items or old_dangers:
            logger.debug(f"오래된 데이터 정리: 아이템 {len(old_items)}개, 위험지역 {len(old_dangers)}개")


# 싱글톤 인스턴스 가져오기 헬퍼
def get_communication_network() -> BotCommunicationNetwork:
    """봇 소통 네트워크 인스턴스 가져오기"""
    return BotCommunicationNetwork()
