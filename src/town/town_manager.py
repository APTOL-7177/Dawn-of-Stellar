"""
마을 관리자 (Town Manager)

마을의 시설, 업그레이드, 자원 등을 관리하는 시스템
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from src.core.logger import get_logger

logger = get_logger("town")


class FacilityType(Enum):
    """시설 타입"""
    KITCHEN = "kitchen"         # 주방 (요리 버프 강화)
    BLACKSMITH = "blacksmith"   # 대장간 (시작 장비 강화)
    ALCHEMY_LAB = "alchemy_lab" # 연금술 실험실 (포션 효율)
    STORAGE = "storage"         # 창고 (인벤토리 확장)


@dataclass
class Facility:
    """마을 시설"""
    type: FacilityType
    level: int = 1
    max_level: int = 4
    
    def upgrade_cost(self) -> Dict[str, int]:
        """
        다음 레벨 업그레이드 비용
        
        Returns:
            {재료ID: 수량} 딕셔너리
        """
        if self.level >= self.max_level:
            return {}
            
        # 레벨별 비용 (예시)
        # Lv 1 -> 2: 목재 10, 석재 5, 골드 100
        # Lv 2 -> 3: 목재 30, 석재 20, 철광석 10, 골드 500
        # Lv 3 -> 4: 목재 100, 석재 50, 철광석 30, 골드 2000
        
        costs = {}
        if self.level == 1:
            costs = {"wood": 10, "stone": 5, "gold": 100}
        elif self.level == 2:
            costs = {"wood": 30, "stone": 20, "iron_ore": 10, "gold": 500}
        elif self.level == 3:
            costs = {"wood": 100, "stone": 50, "iron_ore": 30, "gold": 2000}
            
        return costs
        
    def get_effect_description(self) -> str:
        """현재 레벨 효과 설명"""
        if self.type == FacilityType.KITCHEN:
            effects = [
                "기본 요리 가능",
                "요리 버프 지속시간 +20%",
                "고급(Gourmet) 레시피 해금",
                "요리 회복량 +50%"
            ]
        elif self.type == FacilityType.BLACKSMITH:
            effects = [
                "장비 수리 가능",
                "시작 장비 등급: 일반(Common)",
                "장비 재련(옵션 변경) 해금",
                "시작 장비 등급: 고급(Uncommon)"
            ]
        elif self.type == FacilityType.ALCHEMY_LAB:
            effects = [
                "포션 제작 가능",
                "포션 회복량 +20%",
                "폭탄 제작 해금",
                "포션 회복량 +50%"
            ]
        elif self.type == FacilityType.STORAGE:
            effects = [
                "최대 무게 +0",
                "최대 무게 +4",
                "최대 무게 +8",
                "아이템 무게 20% 감소 (효율적 포장)"
            ]
        else:
            return "알 수 없는 효과"
            
        # 현재 레벨까지의 효과를 모두 보여줄지, 현재 레벨만 보여줄지 결정
        # 여기서는 현재 레벨 효과만 반환
        return effects[self.level - 1] if self.level <= len(effects) else "최대 레벨 도달"


class TownManager:
    """마을 관리자"""
    
    def __init__(self):
        # 개발 모드 또는 메타 진행에서 시설 레벨 로드
        from src.core.config import get_config
        from src.persistence.meta_progress import get_meta_progress
        
        try:
            config = get_config()
            meta = get_meta_progress()
            
            if config.development_mode:
                # 개발 모드: 모든 시설 만렙
                initial_levels = {
                    FacilityType.KITCHEN: 4,
                    FacilityType.BLACKSMITH: 4,
                    FacilityType.ALCHEMY_LAB: 4,
                    FacilityType.STORAGE: 4
                }
                logger.info("마을 시설 초기화: 개발 모드 (Lv.4)")
            else:
                # 일반 모드: 메타 진행에서 로드 (영구 보존!)
                initial_levels = {
                    FacilityType.KITCHEN: meta.get_facility_level("kitchen"),
                    FacilityType.BLACKSMITH: meta.get_facility_level("blacksmith"),
                    FacilityType.ALCHEMY_LAB: meta.get_facility_level("alchemy_lab"),
                    FacilityType.STORAGE: meta.get_facility_level("storage")
                }
                logger.info(f"마을 시설 초기화: 메타 진행에서 로드 (주방 Lv.{initial_levels[FacilityType.KITCHEN]})")
        except:
            # Config 또는 메타 진행 초기화 전이면 기본값 사용
            initial_levels = {
                FacilityType.KITCHEN: 1,
                FacilityType.BLACKSMITH: 1,
                FacilityType.ALCHEMY_LAB: 1,
                FacilityType.STORAGE: 1
            }
            logger.warning("Config/Meta 미초기화 - 마을 시설 기본 레벨(1)로 시작")
        
        self.facilities: Dict[FacilityType, Facility] = {
            f_type: Facility(f_type, level=initial_levels[f_type])
            for f_type in FacilityType
        }
        
        # 허브 영구 저장소 (게임 오버 시에도 보존되는 건축 자재)
        # 건설 자재만 저장 (CONSTRUCTION category)
        self.hub_storage: Dict[str, int] = {}  # {item_id: count}
        
    def get_facility(self, facility_type: FacilityType) -> Optional[Facility]:
        """시설 가져오기"""
        return self.facilities.get(facility_type)
        
    def can_upgrade(self, facility_type: FacilityType, player_inventory: Dict[str, int], player_gold: int) -> bool:
        """
        업그레이드 가능 여부 확인
        
        Args:
            facility_type: 시설 타입
            player_inventory: 플레이어 인벤토리 {item_id: count}
            player_gold: 플레이어 골드
            
        Returns:
            가능 여부
        """
        facility = self.get_facility(facility_type)
        if not facility or facility.level >= facility.max_level:
            return False
            
        costs = facility.upgrade_cost()
        
        # 골드 확인
        if player_gold < costs.get("gold", 0):
            return False
            
        # 재료 확인
        for item_id, count in costs.items():
            if item_id == "gold":
                continue
            if player_inventory.get(item_id, 0) < count:
                return False
                
        return True
        
    def upgrade_facility(self, facility_type: FacilityType, player: Any) -> bool:
        """
        시설 업그레이드 실행
        
        Args:
            facility_type: 시설 타입
            player: 플레이어 객체 (인벤토리, 골드 접근용)
            
        Returns:
            성공 여부
        """
        if not self.can_upgrade(facility_type, player.inventory, player.gold):
            return False
            
        facility = self.get_facility(facility_type)
        costs = facility.upgrade_cost()
        
        # 비용 차감
        player.gold -= costs.get("gold", 0)
        for item_id, count in costs.items():
            if item_id == "gold":
                continue
            player.remove_item(item_id, count)
            
        # 레벨업
        facility.level += 1
        
        # 메타 진행에 저장 (영구 보존!)
        from src.persistence.meta_progress import get_meta_progress, save_meta_progress
        meta = get_meta_progress()
        meta.set_facility_level(facility.type.value, facility.level)
        save_meta_progress()
        
        logger.info(f"마을 시설 업그레이드: {facility.type.value} Lv.{facility.level} (메타 진행에 영구 저장됨)")
        
        # 효과 적용 (즉시 적용 필요한 경우)
        self._apply_facility_effect(facility, player)
        
        return True
        
    def _apply_facility_effect(self, facility: Facility, player: Any):
        """시설 효과 적용 (업그레이드 시 호출)"""
        if facility.type == FacilityType.STORAGE:
            # 인벤토리 무게 제한 확장 (기본 무게 + 시설 레벨에 따른 보너스)
            # Lv 1: +0, Lv 2: +4, Lv 3: +8, Lv 4: 무게 20% 감소 (효율적 포장)
            bonus_weight = (facility.level - 1) * 4
            if hasattr(player, 'max_weight'):
                # 기본 무게(예: 50)에 보너스 추가. 
                # 주의: 이 방식은 player.max_weight가 '기본값'인지 '현재값'인지에 따라 다름.
                # 안전하게 StatManager를 통해 보너스를 주는 것이 좋음.
                if hasattr(player, 'stat_manager'):
                    player.stat_manager.add_bonus("max_weight", "town_storage", bonus_weight)
                else:
                    # StatManager가 없으면 직접 수정 (덜 안전함)
                    player.max_weight += 10 # 단순 증가 (임시)
                
    def apply_all_effects(self, player: Any):
        """모든 시설 효과 적용 (게임 로드 시 호출)"""
        for facility in self.facilities.values():
            self._apply_facility_effect(facility, player)

    def store_construction_materials(self, player_inventory: Dict[str, int]) -> Dict[str, int]:
        """
        게임 오버 시 플레이어의 건축 자재를 허브 저장소로 이동
        
        Args:
            player_inventory: 플레이어 인벤토리 {item_id: count}
            
        Returns:
            저장된 자재 목록 {item_id: count}
        """
        from src.gathering.ingredient import IngredientDatabase, IngredientCategory
        
        stored_materials = {}
        
        for item_id, count in list(player_inventory.items()):
            ingredient = IngredientDatabase.get_ingredient(item_id)
            if ingredient and ingredient.category == IngredientCategory.CONSTRUCTION:
                # 허브 저장소에 추가
                self.hub_storage[item_id] = self.hub_storage.get(item_id, 0) + count
                stored_materials[item_id] = count
                logger.info(f"허브 저장소에 보관: {ingredient.name} x{count}")
        
        return stored_materials
    
    def store_all_materials_from_inventory(self, inventory: Any) -> Dict[str, int]:
        """
        게임 오버 시 인벤토리의 모든 재료 아이템을 허브 저장소로 이동
        
        Args:
            inventory: Inventory 객체
            
        Returns:
            저장된 재료 목록 {item_id: count}
        """
        from src.gathering.ingredient import IngredientDatabase
        
        stored_materials = {}
        
        if not hasattr(inventory, 'slots'):
            logger.warning("인벤토리에 slots 속성이 없습니다")
            return stored_materials
        
        # 인벤토리의 모든 슬롯 확인
        for slot in inventory.slots:
            if not slot or not slot.item:
                continue
            
            # item_id 가져오기
            item_id = getattr(slot.item, 'item_id', None)
            if not item_id:
                continue
            
            # 재료 아이템인지 확인
            ingredient = IngredientDatabase.get_ingredient(item_id)
            if ingredient:
                # 허브 저장소에 추가
                quantity = getattr(slot, 'quantity', 1)
                self.hub_storage[item_id] = self.hub_storage.get(item_id, 0) + quantity
                stored_materials[item_id] = stored_materials.get(item_id, 0) + quantity
                logger.info(f"허브 저장소에 보관 (게임오버): {ingredient.name} x{quantity}")
        
        return stored_materials

    
    def get_hub_storage(self) -> Dict[str, int]:
        """허브 저장소 내용 가져오기"""
        return self.hub_storage.copy()
    
    def withdraw_from_hub(self, item_id: str, count: int) -> int:
        """
        허브 저장소에서 자재 꺼내기
        
        Args:
            item_id: 아이템 ID
            count: 꺼낼 수량
            
        Returns:
            실제로 꺼낸 수량
        """
        available = self.hub_storage.get(item_id, 0)
        actual_count = min(count, available)
        
        if actual_count > 0:
            self.hub_storage[item_id] -= actual_count
            if self.hub_storage[item_id] <= 0:
                del self.hub_storage[item_id]
            logger.info(f"허브 저장소에서 꺼냄: {item_id} x{actual_count}")
        
        return actual_count
    
    def clear_runtime_storage(self):
        """
        런타임 임시 저장소 비우기 (게임 오버 시)
        허브 저장소(hub_storage)는 건설 자재만 보관하므로 유지됨
        """
        # 현재는 hub_storage가 건설 자재만 보관하므로 추가 작업 불필요
        # 일반 아이템 임시 저장소가 있다면 여기서 비움
        logger.info("런타임 저장소 초기화 (건설 자재는 보존)")
        pass

    def to_dict(self) -> Dict[str, Any]:
        """저장용 딕셔너리 변환 - 시설 레벨은 메타 진행에 저장됨"""
        return {
            # "facilities": {...},  # REMOVED - 이제 메타 진행에 저장
            "hub_storage": self.hub_storage.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TownManager":
        """딕셔너리에서 복원 + 기존 시설 레벨 마이그레이션"""
        manager = cls()
        
        # 마이그레이션: 기존 세이브 파일의 시설 레벨을 메타 진행으로 이동
        if "facilities" in data:
            from src.persistence.meta_progress import get_meta_progress, save_meta_progress
            meta = get_meta_progress()
            
            for f_type_str, f_data in data["facilities"].items():
                old_level = f_data.get("level", 1)
                current_level = meta.get_facility_level(f_type_str)
                
                # 더 높은 레벨 유지 (충돌 시)
                if old_level > current_level:
                    meta.set_facility_level(f_type_str, old_level)
                    logger.info(f"마이그레이션: {f_type_str} Lv.{old_level} → 메타 진행으로 이동")
            
            save_meta_progress()
            logger.info("기존 시설 레벨 마이그레이션 완료 (메타 진행으로 영구 저장)")
        
        # 허브 저장소 복원
        if "hub_storage" in data:
            manager.hub_storage = data["hub_storage"].copy()
            logger.info(f"허브 저장소 복원: {len(manager.hub_storage)}종류의 자재")
        
        return manager

# 전역 인스턴스
_town_manager = TownManager()

def get_town_manager() -> TownManager:
    return _town_manager
