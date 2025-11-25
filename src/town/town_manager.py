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
    SHOP = "shop"               # 상점 (잡화점)


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
        
        # 상점 업그레이드 비용 (별의 파편 사용)
        if self.type == FacilityType.SHOP:
            if self.level == 1:
                costs = {}  # 별의 파편으로 구매하므로 재료 불필요
            elif self.level == 2:
                costs = {}  # 별의 파편으로 구매
            elif self.level == 3:
                costs = {}  # 별의 파편으로 구매
            elif self.level == 4:
                costs = {}  # 별의 파편으로 구매
            
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
        elif self.type == FacilityType.SHOP:
            effects = [
                "기본 상점 운영",
                "품목 종류 추가 (동시에 판매하는 아이템 종류 수 추가)",
                "재고량 증가 (1.5배 또는 2배)",
                "일부 상품 세일 (가격 20% 할인)"
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
                    FacilityType.STORAGE: 4,
                    FacilityType.SHOP: 4
                }
                logger.info("마을 시설 초기화: 개발 모드 (Lv.4)")
            else:
                # 일반 모드: 메타 진행에서 로드 (영구 보존!)
                initial_levels = {
                    FacilityType.KITCHEN: meta.get_facility_level("kitchen"),
                    FacilityType.BLACKSMITH: meta.get_facility_level("blacksmith"),
                    FacilityType.ALCHEMY_LAB: meta.get_facility_level("alchemy_lab"),
                    FacilityType.STORAGE: meta.get_facility_level("storage"),
                    FacilityType.SHOP: meta.get_facility_level("shop")
                }
                logger.info(f"마을 시설 초기화: 메타 진행에서 로드 (주방 Lv.{initial_levels[FacilityType.KITCHEN]})")
        except:
            # Config 또는 메타 진행 초기화 전이면 기본값 사용
            initial_levels = {
                FacilityType.KITCHEN: 1,
                FacilityType.BLACKSMITH: 1,
                FacilityType.ALCHEMY_LAB: 1,
                FacilityType.STORAGE: 1,
                FacilityType.SHOP: 1
            }
            logger.warning("Config/Meta 미초기화 - 마을 시설 기본 레벨(1)로 시작")
        
        self.facilities: Dict[FacilityType, Facility] = {
            f_type: Facility(f_type, level=initial_levels[f_type])
            for f_type in FacilityType
        }
        
        # 허브 영구 저장소 (게임 오버 시에도 보존되는 아이템)
        # 모든 아이템을 직렬화된 형태로 저장
        self.hub_storage: List[Dict[str, Any]] = []  # List[serialize_item(item) 결과]

        # 마을 창고 저장소 (플레이어가 직접 보관하는 아이템)
        self.storage_inventory: List[Dict[str, Any]] = []  # 창고에 보관된 아이템들
        
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
            # Lv 1: +0, Lv 2: +4, Lv 3: +8, Lv 4: +12 (무게 20% 감소는 레벨 4 추가 보너스로 별도 구현 가능)
            bonus_weight = (facility.level - 1) * 4
            
            # 인벤토리 객체의 storage_bonus 속성에 직접 설정
            if hasattr(player, 'inventory'):
                if hasattr(player.inventory, 'storage_bonus'):
                    player.inventory.storage_bonus = bonus_weight
                    logger.info(f"창고 보너스 적용: +{bonus_weight}kg (창고 Lv.{facility.level})")
                else:
                    logger.warning("인벤토리에 storage_bonus 속성이 없습니다")
            else:
                logger.warning("플레이어에 inventory 속성이 없습니다")
                
    def apply_all_effects(self, player: Any):
        """모든 시설 효과 적용 (게임 로드 시 호출)"""
        for facility in self.facilities.values():
            self._apply_facility_effect(facility, player)

    def store_construction_materials(self, player_inventory: Dict[str, int]) -> Dict[str, int]:
        """
        게임 오버 시 플레이어의 건축 자재를 허브 저장소로 이동 (레거시 메서드)
        
        Args:
            player_inventory: 플레이어 인벤토리 {item_id: count}
            
        Returns:
            저장된 자재 목록 {item_id: count}
        """
        # 이 메서드는 더 이상 사용되지 않지만 호환성을 위해 유지
        # 실제로는 store_all_materials_from_inventory를 사용해야 함
        logger.warning("store_construction_materials는 레거시 메서드입니다. store_all_materials_from_inventory를 사용하세요.")
        return {}
    
    def store_all_materials_from_inventory(self, inventory: Any) -> Dict[str, int]:
        """
        게임 오버 시 인벤토리의 모든 재료 아이템을 허브 저장소로 이동
        
        Args:
            inventory: Inventory 객체
            
        Returns:
            저장된 재료 목록 {item_id: count}
        """
        from src.gathering.ingredient import IngredientDatabase
        from src.persistence.save_system import serialize_item
        
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
                # 허브 저장소에 추가 (직렬화해서 저장)
                quantity = getattr(slot, 'quantity', 1)
                item = slot.item
                for _ in range(quantity):
                    serialized = serialize_item(item)
                    self.hub_storage.append(serialized)
                
                stored_materials[item_id] = stored_materials.get(item_id, 0) + quantity
                logger.info(f"허브 저장소에 보관 (게임오버): {ingredient.name} x{quantity}")
        
        return stored_materials

    
    def get_hub_storage(self) -> List[Dict[str, Any]]:
        """허브 저장소 내용 가져오기"""
        return self.hub_storage.copy()

    def get_storage_inventory(self) -> List[Dict[str, Any]]:
        """마을 창고 인벤토리 가져오기"""
        return self.storage_inventory.copy()

    def store_item_to_storage(self, item: Any) -> bool:
        """아이템을 마을 창고에 저장"""
        from src.persistence.save_system import serialize_item

        try:
            serialized_item = serialize_item(item)
            self.storage_inventory.append(serialized_item)
            logger.info(f"마을 창고에 아이템 저장: {getattr(item, 'name', '알 수 없는 아이템')}")
            return True
        except Exception as e:
            logger.error(f"마을 창고 저장 실패: {e}")
            return False

    def retrieve_item_from_storage(self, index: int) -> Optional[Any]:
        """마을 창고에서 아이템 꺼내기"""
        from src.persistence.save_system import deserialize_item

        if 0 <= index < len(self.storage_inventory):
            try:
                serialized_item = self.storage_inventory.pop(index)
                item = deserialize_item(serialized_item)
                logger.info(f"마을 창고에서 아이템 꺼냄: {getattr(item, 'name', '알 수 없는 아이템')}")
                return item
            except Exception as e:
                logger.error(f"마을 창고 아이템 꺼내기 실패: {e}")
                return None
        else:
            logger.warning(f"잘못된 창고 인덱스: {index}")
            return None
    
    def clear_runtime_storage(self):
        """
        런타임 임시 저장소 비우기 (게임 오버 시)
        재료가 아닌 아이템(요리, 장비, 소모품 등)은 제거하고, 재료만 유지
        """
        from src.gathering.ingredient import IngredientDatabase

        # === hub_storage 처리 (하위 호환성) ===
        hub_items_to_keep = []
        hub_removed_count = 0

        for item_data in self.hub_storage:
            item_id = item_data.get("item_id", "")
            ingredient = IngredientDatabase.get_ingredient(item_id)
            if ingredient:
                # 재료 아이템은 유지
                hub_items_to_keep.append(item_data)
            else:
                # 재료가 아닌 아이템(요리, 장비, 소모품 등)은 제거
                hub_removed_count += 1
                item_name = item_data.get("name", item_id)
                logger.info(f"게임오버: hub_storage에서 재료가 아닌 아이템 제거 - {item_name}")

        # 재료만 남김
        self.hub_storage = hub_items_to_keep

        # === storage_inventory 처리 (마을 창고) ===
        storage_items_to_keep = []
        storage_removed_count = 0

        for item_data in self.storage_inventory:
            item_id = item_data.get("item_id", "")
            ingredient = IngredientDatabase.get_ingredient(item_id)
            if ingredient:
                # 재료 아이템은 유지
                storage_items_to_keep.append(item_data)
            else:
                # 재료가 아닌 아이템(요리, 장비, 소모품 등)은 제거
                storage_removed_count += 1
                item_name = item_data.get("name", item_id)
                logger.info(f"게임오버: 마을 창고에서 재료가 아닌 아이템 제거 - {item_name}")

        # 재료만 남김
        self.storage_inventory = storage_items_to_keep

        total_removed = hub_removed_count + storage_removed_count
        total_kept = len(hub_items_to_keep) + len(storage_items_to_keep)

        if total_removed > 0:
            logger.info(f"런타임 저장소 초기화 완료: {total_removed}개의 아이템 제거, {total_kept}개의 재료 유지")
            logger.info(f"  - hub_storage: {hub_removed_count}개 제거, {len(hub_items_to_keep)}개 유지")
            logger.info(f"  - 마을 창고: {storage_removed_count}개 제거, {len(storage_items_to_keep)}개 유지")
        else:
            logger.info("런타임 저장소 초기화 완료: 모든 아이템이 재료입니다")

    def to_dict(self) -> Dict[str, Any]:
        """저장용 딕셔너리 변환 - 시설 레벨은 메타 진행에 저장됨"""
        return {
            # "facilities": {...},  # REMOVED - 이제 메타 진행에 저장
            "hub_storage": self.hub_storage.copy(),
            "storage_inventory": self.storage_inventory.copy()  # 마을 창고 아이템 추가
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
        
        # 허브 저장소 복원 (마이그레이션 포함)
        if "hub_storage" in data:
            storage_data = data["hub_storage"]

            # 기존 형태 ({item_id: count})인 경우 마이그레이션
            if isinstance(storage_data, dict):
                from src.gathering.ingredient import IngredientDatabase
                from src.persistence.save_system import serialize_item

                # 딕셔너리 형태를 리스트 형태로 변환
                manager.hub_storage = []
                for item_id, count in storage_data.items():
                    ingredient = IngredientDatabase.get_ingredient(item_id)
                    if ingredient:
                        # 재료는 직렬화해서 저장
                        for _ in range(count):
                            serialized = serialize_item(ingredient)
                            manager.hub_storage.append(serialized)

                logger.info(f"허브 저장소 마이그레이션 완료: {len(storage_data)}종류의 재료 → {len(manager.hub_storage)}개 아이템")
            elif isinstance(storage_data, list):
                # 새로운 형태 (List[Dict])인 경우
                manager.hub_storage = storage_data.copy()
                logger.info(f"허브 저장소 복원: {len(manager.hub_storage)}개의 아이템")
            else:
                logger.warning(f"알 수 없는 hub_storage 형태: {type(storage_data)}")
                manager.hub_storage = []

        # 마을 창고 인벤토리 복원
        if "storage_inventory" in data:
            storage_inv_data = data["storage_inventory"]
            if isinstance(storage_inv_data, list):
                manager.storage_inventory = storage_inv_data.copy()
                logger.info(f"마을 창고 복원: {len(manager.storage_inventory)}개의 아이템")
            else:
                logger.warning(f"알 수 없는 storage_inventory 형태: {type(storage_inv_data)}")
                manager.storage_inventory = []
        else:
            manager.storage_inventory = []
        
        return manager

# 강력한 싱글톤 구현 (클래스 기반)
class TownManagerSingleton(TownManager):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 싱글톤이므로 __init__은 한 번만 호출
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True
            print(f"[TOWN_MANAGER] 싱글톤 TownManager 생성: id={id(self)}")

def get_town_manager() -> TownManager:
    """TownManager 싱글톤 인스턴스 반환"""
    instance = TownManagerSingleton()

    # DEBUG: 호출 추적
    import sys
    frame = sys._getframe(1)
    caller_name = frame.f_code.co_name if frame else "unknown"
    filename = frame.f_code.co_filename.split('\\')[-1] if frame else "unknown"
    print(f"[TOWN_MANAGER] 호출 from {filename}:{caller_name}, id={id(instance)}, storage={len(instance.get_storage_inventory())}")

    return instance
