"""
골드 상점 UI - 골드로 아이템 구매

M 메뉴에서 언제든지 접근 가능한 기본 상점
맵의 상인 NPC는 특별한 아이템이나 할인 가격으로 제공
"""

from enum import Enum
from typing import List, Optional, Dict
import tcod
import random

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers
from src.audio import play_sfx
from src.equipment.item_system import (
    Consumable, Equipment, ItemType, ItemRarity, EquipSlot,
    CONSUMABLE_TEMPLATES, WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES
)
from src.ui.cursor_menu import CursorMenu, MenuItem


logger = get_logger(Loggers.UI)

# 층별 상점 아이템 캐시 (층 번호 -> 아이템 딕셔너리)
_shop_items_cache: Dict[int, Dict] = {}


def get_inflation_multiplier(floor_level: int) -> float:
    """
    층수에 따른 골드 인플레이션 배율 계산
    
    Args:
        floor_level: 현재 층수
    
    Returns:
        인플레이션 배율 (1층=1.0, 층당 25% 증가)
    """
    # 1층: 1.0x, 2층: 1.25x, 3층: 1.5x, 5층: 2.0x, 10층: 3.25x
    return 1.0 + (floor_level - 1) * 0.25


class ShopState(Enum):
    """상점 상태"""
    SHOPPING = "shopping"
    REFORGE_SELECT = "reforge_select"
    REPAIR_SELECT = "repair_select"


class GoldShopTab(Enum):
    """상점 탭"""
    CONSUMABLES = "소모품"
    EQUIPMENT = "장비"
    SPECIAL = "특수 아이템"
    SERVICE = "서비스"


class GoldShopItem:
    """골드 상점 아이템"""

    def __init__(self, name: str, description: str, price: int, item_obj=None, item_type: str = "consumable", stock: int = 1):
        self.name = name
        self.description = description
        self.price = price
        self.item_obj = item_obj  # 실제 아이템 객체
        self.item_type = item_type  # "consumable", "equipment", "special", "service"
        self.stock = stock  # 재고 (0이면 매진, -1이면 무제한)


def refresh_shop():
    """상점 아이템 캐시 초기화 (새로운 아이템 입고)"""
    global _shop_items_cache
    _shop_items_cache.clear()
    logger.info("상점 아이템 캐시 초기화 완료 (새로운 물품 입고 준비)")


def get_gold_shop_items(floor_level: int = 1, shop_level: int = 1) -> dict:
    """
    골드 상점 아이템 목록 생성 (층별로 캐싱됨)

    Args:
        floor_level: 현재 층수 (장비 등급 결정)
        shop_level: 상점 레벨 (1~4, 레벨에 따라 혜택 제공)

    Returns:
        탭별 아이템 딕셔너리
    """
    global _shop_items_cache
    
    # 캐시 키에 shop_level 포함 (레벨별로 다른 아이템 제공)
    cache_key = (floor_level, shop_level)
    
    # 캐시 확인: 같은 층과 상점 레벨에서는 같은 아이템 반환
    if cache_key in _shop_items_cache:
        logger.debug(f"상점 아이템 캐시 사용 (층 {floor_level}, 상점 레벨 {shop_level})")
        return _shop_items_cache[cache_key]
    
    items = {
        GoldShopTab.CONSUMABLES: [],
        GoldShopTab.EQUIPMENT: [],
        GoldShopTab.SPECIAL: [],
        GoldShopTab.SERVICE: []
    }
    
    # 층별로 고정된 시드를 사용하는 별도의 Random 인스턴스 생성
    # 전역 random 상태를 변경하지 않도록 독립적인 인스턴스 사용
    # refresh_shop 호출 시 캐시가 지워지므로 새로운 아이템이 생성됨 (시간 기반 시드 추가 가능)
    import time
    seed = floor_level * 12345 + int(time.time())  # 시간 기반 시드 추가로 매번 다르게
    floor_random = random.Random(seed)  # 층별 + 시간별 고유 시드

    # === 소모품 (회복 아이템) ===
    # 실제 게임의 CONSUMABLE_TEMPLATES에서 아이템 가져오기
    from src.equipment.item_system import CONSUMABLE_TEMPLATES
    
    # 기본 소모품 풀 (모든 레벨에서 사용 가능)
    base_consumable_pool = []
    for item_id, template in CONSUMABLE_TEMPLATES.items():
        # 기본 가격은 sell_price 사용
        base_price = template.get("sell_price", 50)
        base_consumable_pool.append((item_id, base_price))
    
    # 상점 레벨에 따른 풀 필터링
    # Lv.1: 기본 소모품만 (COMMON, UNCOMMON)
    # Lv.2+: 모든 소모품 포함 (RARE, EPIC 등도 추가)
    if shop_level >= 2:
        all_consumable_items = base_consumable_pool.copy()
    else:
        # Lv.1: COMMON, UNCOMMON만
        from src.equipment.item_system import ItemRarity
        all_consumable_items = [
            (item_id, price) for item_id, price in base_consumable_pool
            if CONSUMABLE_TEMPLATES[item_id].get("rarity") in [ItemRarity.COMMON, ItemRarity.UNCOMMON]
        ]
    
    # 아이템 종류 수 결정: Lv.1은 5종류, Lv.2+는 8종류
    if shop_level >= 2:
        num_consumables = floor_random.randint(8, 12)  # 8~12종류
    else:
        num_consumables = floor_random.randint(5, 7)  # 5~7종류
    
    consumable_items = floor_random.sample(all_consumable_items, min(num_consumables, len(all_consumable_items)))

    # 인플레이션 배율 계산
    inflation = get_inflation_multiplier(floor_level)
    
    # 상점 레벨 4: 가격 20% 할인
    discount_multiplier = 0.8 if shop_level >= 4 else 1.0
    
    for item_id, price in consumable_items:
        # ItemGenerator를 사용하여 일관된 아이템 생성 (스택 문제 해결)
        from src.equipment.item_system import ItemGenerator
        try:
            consumable = ItemGenerator.create_consumable(item_id)
        except (ValueError, KeyError):
            # 템플릿이 없으면 스킵
            continue
        
        # 인플레이션 적용 가격 계산
        inflated_price = int(price * inflation * discount_multiplier)
        
        # 소모품 재고: 1~3개 랜덤 (Lv.3 이상이면 1.5배 또는 2배)
        base_stock = floor_random.randint(1, 3)
        if shop_level >= 3:
            stock_multiplier = floor_random.choice([1.5, 2.0])
            stock = max(1, int(base_stock * stock_multiplier))
        else:
            stock = base_stock
        
        items[GoldShopTab.CONSUMABLES].append(
            GoldShopItem(
                consumable.name,
                consumable.description,
                inflated_price,
                consumable,
                "consumable",
                stock=stock
            )
        )

    # === 장비 (층수에 맞는 장비) ===
    # 실제 게임의 WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES에서 아이템 가져오기
    from src.equipment.item_system import WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES, ItemRarity
    
    # 층수에 맞는 장비 필터링
    all_equipment_pools = []
    
    # 모든 템플릿을 합침
    all_templates = {}
    all_templates.update(WEAPON_TEMPLATES)
    all_templates.update(ARMOR_TEMPLATES)
    all_templates.update(ACCESSORY_TEMPLATES)
    
    # 층수에 맞는 레벨 제한 계산 (층당 레벨 1 증가 가정)
    # 최소 레벨은 1로 보장 (마을/대장간에서도 기본 장비 판매 가능)
    max_level = max(1, floor_level)
    
    for item_id, template in all_templates.items():
        level_req = template.get("level_requirement", 1)
        rarity = template.get("rarity", ItemRarity.COMMON)
        
        # 층수에 맞는 장비만 선택
        if level_req <= max_level:
            # 가격은 sell_price 사용
            base_price = template.get("sell_price", 100)
            all_equipment_pools.append((item_id, base_price, template))
    
    # 상점 레벨에 따른 아이템 종류 수 결정
    # Lv.1: 4~5종류, Lv.2+: 6~8종류
    if shop_level >= 2:
        num_equipment = floor_random.randint(6, 8)
    else:
        num_equipment = floor_random.randint(4, 5)
    
    # 랜덤 선택 (장비 풀이 비어있지 않은 경우에만)
    if len(all_equipment_pools) > 0:
        selected_equipment = floor_random.sample(
            list(range(len(all_equipment_pools))), 
            min(num_equipment, len(all_equipment_pools))
        )
        equipment_items = [all_equipment_pools[i] for i in selected_equipment]
    else:
        # 장비 풀이 비어있으면 빈 리스트 반환
        logger.warning(f"장비 풀이 비어있습니다. (floor_level: {floor_level}, max_level: {max_level})")
        equipment_items = []

    for item_id, base_price, template in equipment_items:
        # 인플레이션 적용 가격 계산 (Lv.4 할인 적용)
        price = int(base_price * inflation * discount_multiplier)
        
        # ItemGenerator를 사용하여 일관된 아이템 생성
        from src.equipment.item_system import ItemGenerator, ItemType, EquipSlot
        
        try:
            if item_id in WEAPON_TEMPLATES:
                equipment = ItemGenerator.create_weapon(item_id, add_random_affixes=True)
            elif item_id in ARMOR_TEMPLATES:
                equipment = ItemGenerator.create_armor(item_id, add_random_affixes=True)
            elif item_id in ACCESSORY_TEMPLATES:
                equipment = ItemGenerator.create_accessory(item_id, add_random_affixes=True)
            else:
                continue
            
            # 장비 재고: 1개 고정 (Lv.3 이상이면 1.5배 또는 2배)
            if shop_level >= 3:
                stock = floor_random.choice([1, 2])  # 1개 또는 2개
            else:
                stock = 1
            
            items[GoldShopTab.EQUIPMENT].append(
                GoldShopItem(equipment.name, equipment.description, price, equipment, "equipment", stock=stock)
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"장비 생성 실패 ({item_id}): {e}")
            continue

    # === 특수 아이템 ===
    # 실제 게임의 CONSUMABLE_TEMPLATES에서 특수 아이템 필터링
    # 특수 아이템: town_portal, phoenix_down 등 특수 효과 아이템
    special_item_ids = [
        "town_portal", "phoenix_down", "dungeon_key",
        "barrier_crystal", "haste_crystal", "power_tonic", "defense_elixir",
        "regen_crystal", "mp_regen_crystal", "status_cleanse", "revive_crystal",
        "poison_bomb", "thunder_grenade", "acid_flask", "smoke_bomb"
    ]
    
    # 실제 템플릿에 존재하는 특수 아이템만 필터링
    all_special_items = []
    for item_id in special_item_ids:
        if item_id in CONSUMABLE_TEMPLATES:
            template = CONSUMABLE_TEMPLATES[item_id]
            base_price = template.get("sell_price", 200)
            all_special_items.append((item_id, base_price))
    
    # 상점 레벨에 따른 아이템 종류 수 결정
    # Lv.1: 3~4종류, Lv.2+: 5~6종류
    if shop_level >= 2:
        num_special = floor_random.randint(5, 6)
    else:
        num_special = floor_random.randint(3, 4)
    
    special_items = floor_random.sample(all_special_items, min(num_special, len(all_special_items)))

    for item_id, base_price in special_items:
        # 인플레이션 적용 가격 계산 (Lv.4 할인 적용)
        price = int(base_price * inflation * discount_multiplier)
        
        # ItemGenerator를 사용하여 일관된 아이템 생성 (스택 문제 해결)
        from src.equipment.item_system import ItemGenerator
        try:
            consumable = ItemGenerator.create_consumable(item_id)
        except (ValueError, KeyError):
            # 템플릿이 없으면 스킵
            continue
        
        # 특수 아이템 재고: 1~3개 랜덤 (Lv.3 이상이면 1.5배 또는 2배)
        base_stock = floor_random.randint(1, 3)
        if shop_level >= 3:
            stock_multiplier = floor_random.choice([1.5, 2.0])
            stock = max(1, int(base_stock * stock_multiplier))
        else:
            stock = base_stock
        
        items[GoldShopTab.SPECIAL].append(
            GoldShopItem(consumable.name, consumable.description, price, consumable, "special", stock=stock)
        )

    # === 서비스 항목 ===
    # 인플레이션 배율 계산
    service_inflation = get_inflation_multiplier(floor_level)
    reforge_base_price = 250
    reforge_price = int(reforge_base_price * service_inflation)
    
    items[GoldShopTab.SERVICE].append(
        GoldShopItem(
            "장비 수리",
            "보유한 모든 장비의 내구도를 수리합니다. 비용은 손상도에 따라 달라집니다.",
            0,  # 가격은 동적 계산
            None,
            "service_repair",
            stock=-1  # 무제한
        )
    )
    items[GoldShopTab.SERVICE].append(
        GoldShopItem(
            f"장비 재연마",
            f"장비의 추가 옵션을 무작위로 변경합니다. (비용: {reforge_price} G)",
            reforge_price,
            None,
            "service_reforge",
            stock=-1  # 무제한
        )
    )

    # 캐시에 저장 (깊은 복사하여 원본 보호)
    import copy
    cached_items = {
        GoldShopTab.CONSUMABLES: copy.deepcopy(items[GoldShopTab.CONSUMABLES]),
        GoldShopTab.EQUIPMENT: copy.deepcopy(items[GoldShopTab.EQUIPMENT]),
        GoldShopTab.SPECIAL: copy.deepcopy(items[GoldShopTab.SPECIAL]),
        GoldShopTab.SERVICE: copy.deepcopy(items[GoldShopTab.SERVICE])
    }
    _shop_items_cache[cache_key] = cached_items
    
    logger.info(f"상점 아이템 생성 완료 (층 {floor_level}, 상점 레벨 {shop_level}): 소모품 {len(items[GoldShopTab.CONSUMABLES])}개, 장비 {len(items[GoldShopTab.EQUIPMENT])}개, 특수 {len(items[GoldShopTab.SPECIAL])}개, 서비스 {len(items[GoldShopTab.SERVICE])}개")
    
    return items


class GoldShopUI:
    """골드 상점 UI"""

    def __init__(self, screen_width: int, screen_height: int, inventory, floor_level: int = 1, shop_type: str = "shop"):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.floor_level = floor_level
        self.shop_type = shop_type  # "shop" 또는 "blacksmith"

        # TownManager를 통해 상점 레벨 가져오기
        from src.town.town_manager import get_town_manager
        town_manager = get_town_manager()
        from src.town.town_manager import FacilityType
        shop_facility = town_manager.get_facility(FacilityType.SHOP)
        shop_level = shop_facility.level if shop_facility else 1

        # 상점 아이템
        self.shop_items = get_gold_shop_items(floor_level, shop_level)

        # UI 상태
        self.state = ShopState.SHOPPING
        
        # shop_type에 따라 사용 가능한 탭 설정
        if shop_type == "blacksmith":
            # 대장간: 장비와 서비스만 표시 (소모품, 특수 아이템 제거)
            self.tabs = [GoldShopTab.EQUIPMENT, GoldShopTab.SERVICE]
        else:
            # 상점: 소모품과 특수 아이템만 표시 (장비, 서비스 제거)
            self.tabs = [GoldShopTab.CONSUMABLES, GoldShopTab.SPECIAL]
        
        self.current_tab = self.tabs[0]  # 첫 번째 탭 선택
        self.tab_index = 0
        
        # 재고가 있는 첫 번째 아이템으로 선택
        current_items = self.shop_items[self.current_tab]
        valid_items = [i for i, item in enumerate(current_items) if item.stock != 0]
        self.selected_index = valid_items[0] if valid_items else 0
        
        # 재연마 메뉴
        self.reforge_menu: Optional[CursorMenu] = None
        # 수리 메뉴
        self.repair_menu: Optional[CursorMenu] = None

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Returns:
            True: 상점 종료
        """
        # 수리 선택 상태
        if self.state == ShopState.REPAIR_SELECT:
            if self.repair_menu:
                if action == GameAction.MOVE_UP:
                    self.repair_menu.move_cursor_up()
                elif action == GameAction.MOVE_DOWN:
                    self.repair_menu.move_cursor_down()
                elif action == GameAction.CONFIRM:
                    # 수리 실행 후 메뉴 갱신을 위해 결과 확인
                    result = self.repair_menu.execute_selected()
                    if result == "refresh":
                        self._handle_repair() # 메뉴 갱신
                    elif result == "close":
                        self.state = ShopState.SHOPPING
                        self.repair_menu = None
                elif action == GameAction.ESCAPE or action == GameAction.CANCEL:
                    self.state = ShopState.SHOPPING
                    self.repair_menu = None
                    play_sfx("ui", "cursor_cancel")
            return False

        # 재연마 선택 상태
        if self.state == ShopState.REFORGE_SELECT:
            if self.reforge_menu:
                if action == GameAction.MOVE_UP:
                    self.reforge_menu.move_cursor_up()
                elif action == GameAction.MOVE_DOWN:
                    self.reforge_menu.move_cursor_down()
                elif action == GameAction.CONFIRM:
                    self.reforge_menu.execute_selected()
                    # 재연마 후 쇼핑 상태로 복귀 (성공 여부 상관없이)
                    self.state = ShopState.SHOPPING
                    self.reforge_menu = None
                elif action == GameAction.ESCAPE or action == GameAction.CANCEL:
                    self.state = ShopState.SHOPPING
                    self.reforge_menu = None
                    play_sfx("ui", "cursor_cancel")
            return False

        # 일반 쇼핑 상태
        if action == GameAction.MOVE_LEFT:
            # 탭 이동
            self.tab_index = max(0, self.tab_index - 1)
            self.current_tab = self.tabs[self.tab_index]
            # 재고가 있는 첫 번째 아이템으로 선택
            current_items = self.shop_items[self.current_tab]
            valid_items = [i for i, item in enumerate(current_items) if item.stock != 0]
            self.selected_index = valid_items[0] if valid_items else 0

        elif action == GameAction.MOVE_RIGHT:
            # 탭 이동
            self.tab_index = min(len(self.tabs) - 1, self.tab_index + 1)
            self.current_tab = self.tabs[self.tab_index]
            # 재고가 있는 첫 번째 아이템으로 선택
            current_items = self.shop_items[self.current_tab]
            valid_items = [i for i, item in enumerate(current_items) if item.stock != 0]
            self.selected_index = valid_items[0] if valid_items else 0

        elif action == GameAction.MOVE_UP:
            current_items = self.shop_items[self.current_tab]
            # 재고가 있는 아이템만 세기
            valid_items = [i for i, item in enumerate(current_items) if item.stock != 0]
            if valid_items:
                current_pos = valid_items.index(self.selected_index) if self.selected_index in valid_items else 0
                new_pos = max(0, current_pos - 1)
                self.selected_index = valid_items[new_pos]

        elif action == GameAction.MOVE_DOWN:
            current_items = self.shop_items[self.current_tab]
            # 재고가 있는 아이템만 세기
            valid_items = [i for i, item in enumerate(current_items) if item.stock != 0]
            if valid_items:
                current_pos = valid_items.index(self.selected_index) if self.selected_index in valid_items else 0
                new_pos = min(len(valid_items) - 1, current_pos + 1)
                self.selected_index = valid_items[new_pos]

        elif action == GameAction.CONFIRM:
            # 아이템 구매
            self._purchase_item()

        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            # 상점 닫기
            play_sfx("ui", "cursor_cancel")
            return True

        return False

    def _purchase_item(self):
        """아이템 구매 또는 서비스 이용"""
        current_items = self.shop_items[self.current_tab]

        if not current_items:
            logger.warning("구매할 아이템이 없습니다")
            return

        selected_item = current_items[self.selected_index]

        # 서비스 항목 처리
        if selected_item.item_type == "service_repair":
            self._handle_repair()
            return
        elif selected_item.item_type == "service_reforge":
            self._handle_reforge()
            return

        # 재고 확인
        if selected_item.stock <= 0:
            logger.warning(f"{selected_item.name}은(는) 매진되었습니다")
            return

        # 골드 확인
        if self.inventory.gold < selected_item.price:
            logger.warning(f"골드가 부족합니다. (필요: {selected_item.price}G, 보유: {self.inventory.gold}G)")
            return

        # 인벤토리 공간 확인 (서비스 제외)
        if selected_item.item_type != "service" and not self.inventory.can_add_item(selected_item.item_obj):
            logger.warning("인벤토리가 가득 찼습니다")
            return

        # 구매
        import copy
        item_to_add = copy.deepcopy(selected_item.item_obj)
        self.inventory.remove_gold(selected_item.price)
        self.inventory.add_item(item_to_add)
        
        # 재고 감소
        selected_item.stock -= 1

        logger.info(f"구매 완료: {selected_item.name} ({selected_item.price}G) - 재고: {selected_item.stock}개")

    def _handle_repair(self):
        """장비 수리 서비스 (선택 수리)"""
        items_to_repair = []
        
        # 수리 대상 수집 함수
        def collect_repairable_items(item, owner_name, slot_name=""):
            if item and hasattr(item, 'current_durability') and hasattr(item, 'max_durability'):
                missing = item.max_durability - item.current_durability
                if missing > 0:
                    # 비용 계산
                    multiplier = 1.0
                    rarity_name = getattr(item.rarity, 'name', 'COMMON')
                    if rarity_name == 'UNCOMMON': multiplier = 1.5
                    elif rarity_name == 'RARE': multiplier = 2.0
                    elif rarity_name == 'EPIC': multiplier = 3.0
                    elif rarity_name == 'LEGENDARY': multiplier = 5.0
                    
                    # 인플레이션 적용 비용 계산
                    base_cost = int(missing * 2 * multiplier)
                    cost = int(base_cost * get_inflation_multiplier(self.floor_level))
                    items_to_repair.append({
                        "item": item,
                        "cost": cost,
                        "missing": missing,
                        "owner": owner_name,
                        "slot": slot_name
                    })

        # 인벤토리 내 장비
        for slot in self.inventory.slots:
            collect_repairable_items(slot.item, "인벤토리")
                    
        # 장착 중인 장비 (파티원)
        if self.inventory.party:
            for member in self.inventory.party:
                for slot_name, item in member.equipment.items():
                    collect_repairable_items(item, member.name, slot_name)

        if not items_to_repair:
            # 수리할 것이 없으면 알림 후 복귀
            # 하지만 메뉴가 떠있어야 하므로 빈 메뉴 대신 메시지만 출력하고 상태 변경 안함
            # 만약 메뉴 갱신 중이었다면...
            if self.state == ShopState.REPAIR_SELECT:
                # 메뉴 닫기
                self.state = ShopState.SHOPPING
                self.repair_menu = None
            logger.info("수리할 장비가 없습니다.")
            return

        # 메뉴 아이템 생성
        menu_items = []
        for data in items_to_repair:
            item = data["item"]
            cost = data["cost"]
            owner = data["owner"]
            
            # 텍스트: [주인] 아이템명 (내구도/최대) - 비용G
            text = f"[{owner}] {item.name} ({item.current_durability}/{item.max_durability}) - {cost}G"
            
            # 콜백
            action = lambda i=item, c=cost, o=data.get("owner_obj"): self._execute_repair_single(i, c)
            
            menu_items.append(MenuItem(text, action=action))

        menu_items.append(MenuItem("돌아가기", action=lambda: "close"))

        # 커서 메뉴 생성
        self.repair_menu = CursorMenu(
            title="수리할 장비 선택",
            items=menu_items,
            x=(self.screen_width - 70) // 2,
            y=(self.screen_height - 30) // 2,
            width=70,
            show_description=False
        )
        self.state = ShopState.REPAIR_SELECT

    def _execute_repair_single(self, item, cost):
        """단일 장비 수리 실행"""
        if self.inventory.gold < cost:
            logger.warning(f"골드가 부족합니다. (필요: {cost}G)")
            return "fail"

        self.inventory.remove_gold(cost)
        item.current_durability = item.max_durability
        
        # 파티원이 장착 중인 경우 스탯 업데이트 (어느 파티원인지 찾아서 업데이트)
        if self.inventory.party:
            for member in self.inventory.party:
                for slot_name, equipped_item in member.equipment.items():
                    if equipped_item == item:
                        member.update_equipment_stats(slot_name)
                        
        logger.info(f"{item.name} 수리 완료. (비용: {cost}G)")
        play_sfx("ui", "repair_success")
        return "refresh"

    def _handle_reforge(self):
        """장비 재연마 서비스 (메뉴 생성)"""
        reforgeable_items = []
        
        # 인벤토리 아이템
        for i, slot in enumerate(self.inventory.slots):
            item = slot.item
            if item.item_type in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY] and item.rarity != ItemRarity.UNIQUE:
                reforgeable_items.append(item)
                
        # 장착 중인 아이템 (파티원)
        if self.inventory.party:
            for member in self.inventory.party:
                for slot_name, item in member.equipment.items():
                    if item and item.item_type in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY] and item.rarity != ItemRarity.UNIQUE:
                        reforgeable_items.append(item)

        if not reforgeable_items:
            logger.warning("재연마할 수 있는 장비가 없습니다.")
            return

        # 메뉴 아이템 생성
        menu_items = []
        for item in reforgeable_items:
            # 아이템 이름 + 현재 옵션 요약
            affix_desc = f" ({len(item.affixes)}옵션)" if item.affixes else " (옵션 없음)"
            text = f"[{item.rarity.display_name}] {item.name}{affix_desc}"
            
            # 콜백 함수 (클로저 주의: item을 인자로 바인딩)
            action = lambda i=item: self._execute_reforge(i)
            
            menu_items.append(MenuItem(text, action=action))

        menu_items.append(MenuItem("돌아가기", action=lambda: None))

        # 인플레이션 적용 재연마 비용 계산
        reforge_cost = int(250 * get_inflation_multiplier(self.floor_level))

        # 커서 메뉴 생성
        self.reforge_menu = CursorMenu(
            title=f"재연마할 장비 선택 (비용: {reforge_cost}G)",
            items=menu_items,
            x=(self.screen_width - 60) // 2,
            y=(self.screen_height - 30) // 2,
            width=60,
            show_description=False
        )
        self.state = ShopState.REFORGE_SELECT

    def _execute_reforge(self, item):
        """재연마 실행"""
        # 인플레이션 적용 비용 계산
        cost = int(250 * get_inflation_multiplier(self.floor_level))
        if self.inventory.gold < cost:
            logger.warning(f"골드가 부족합니다. (필요: {cost}G)")
            return

        self.inventory.remove_gold(cost)
        
        from src.equipment.item_system import ItemGenerator
        success, msg = ItemGenerator.reforge_item(item)
        
        if success:
            logger.info(f"{item.name} 재연마 성공! {msg}")
            play_sfx("ui", "upgrade_success")
            
            # 파티원이 장착 중인 경우 스탯 업데이트 필요
            if self.inventory.party:
                for member in self.inventory.party:
                    for slot_name, equipped_item in member.equipment.items():
                        if equipped_item == item:
                            member.update_equipment_stats(slot_name)
                            logger.debug(f"{member.name}의 {item.name} 스탯 업데이트됨")
        else:
            logger.warning(f"재연마 실패: {msg}")

    def render(self, console: tcod.console.Console):
        """상점 렌더링"""
        # 모달 메뉴 렌더링 (상태에 따라)
        if self.state == ShopState.REFORGE_SELECT and self.reforge_menu:
            self.reforge_menu.render(console)
            return
        elif self.state == ShopState.REPAIR_SELECT and self.repair_menu:
            self.repair_menu.render(console)
            return

        # 배경 어둡게
        for y in range(self.screen_height):
            for x in range(self.screen_width):
                console.print(x, y, " ", bg=(0, 0, 0))

        # 상점 박스
        shop_width = 70
        shop_height = 40
        shop_x = (self.screen_width - shop_width) // 2
        shop_y = (self.screen_height - shop_height) // 2

        # 박스 그리기
        self._draw_box(console, shop_x, shop_y, shop_width, shop_height)

        # 제목
        title = "=== 상점 ==="
        console.print(
            shop_x + (shop_width - len(title)) // 2,
            shop_y + 2,
            title,
            fg=(255, 215, 0)  # 금색
        )

        # 골드 표시
        gold_text = f"보유 골드: {self.inventory.gold}G"
        console.print(
            shop_x + shop_width - len(gold_text) - 2,
            shop_y + 2,
            gold_text,
            fg=(255, 215, 0)
        )

        # 탭 메뉴
        tab_y = shop_y + 4
        tab_x = shop_x + 2
        for i, tab in enumerate(self.tabs):
            if tab == self.current_tab:
                console.print(tab_x, tab_y, f"[{tab.value}]", fg=(255, 255, 100))
            else:
                console.print(tab_x, tab_y, f" {tab.value} ", fg=(150, 150, 150))
            tab_x += len(tab.value) + 4

        # 구분선
        for x in range(1, shop_width - 1):
            console.print(shop_x + x, shop_y + 5, "─", fg=(100, 100, 100))

        # 아이템 목록
        current_items = self.shop_items[self.current_tab]
        item_y = shop_y + 7

        for i, item in enumerate(current_items):
            # 재고가 0이면 건너뛰기 (매진 아이템은 표시하지 않음, -1은 무제한)
            if item.stock == 0:
                continue
                
            if i == self.selected_index:
                # 선택된 아이템
                console.print(shop_x + 2, item_y, "►", fg=(255, 255, 100))
                
                # 아이템 이름과 재고
                if item.stock > 1:
                    item_name = f"{item.name} (재고: {item.stock})"
                else:
                    item_name = item.name
                console.print(shop_x + 4, item_y, item_name, fg=(255, 255, 100))

                # 가격 (골드 부족 시 빨간색, 재고 없으면 회색)
                if item.stock != 0:  # 0이 아니면 (양수 또는 -1 무제한)
                    price_color = (255, 255, 100) if self.inventory.gold >= item.price else (255, 100, 100)
                else:
                    price_color = (100, 100, 100)
                console.print(shop_x + shop_width - 12, item_y, f"{item.price}G", fg=price_color)
            else:
                # 일반 아이템
                # 아이템 이름과 재고
                if item.stock > 1:
                    item_name = f"{item.name} (재고: {item.stock})"
                else:
                    item_name = item.name
                console.print(shop_x + 4, item_y, item_name, fg=(200, 200, 200))
                console.print(shop_x + shop_width - 12, item_y, f"{item.price}G", fg=(200, 200, 200))

            item_y += 1

        # 선택된 아이템 설명
        if current_items and self.selected_index < len(current_items):
            selected_item = current_items[self.selected_index]
            # 재고가 있는 아이템만 설명 표시 (0이 아니면, -1은 무제한)
            if selected_item.stock != 0:
                desc_y = shop_y + shop_height - 8

                console.print(shop_x + 2, desc_y, "[ 설명 ]", fg=(150, 200, 255))
                desc_y += 1

                # 설명 텍스트 (여러 줄 가능)
                desc_lines = self._wrap_text(selected_item.description, shop_width - 6)
                for line in desc_lines:
                    console.print(shop_x + 4, desc_y, line, fg=(200, 200, 200))
                    desc_y += 1

        # 조작법
        help_text = "←→: 탭 이동  ↑↓: 아이템 선택  Enter: 구매  ESC: 닫기"
        console.print(
            shop_x + (shop_width - len(help_text)) // 2,
            shop_y + shop_height - 2,
            help_text,
            fg=(150, 150, 150)
        )

    def _draw_box(self, console: tcod.console.Console, x: int, y: int, width: int, height: int):
        """박스 테두리 그리기"""
        # 모서리
        console.print(x, y, "┌", fg=(200, 200, 200))
        console.print(x + width - 1, y, "┐", fg=(200, 200, 200))
        console.print(x, y + height - 1, "└", fg=(200, 200, 200))
        console.print(x + width - 1, y + height - 1, "┘", fg=(200, 200, 200))

        # 가로선
        for i in range(1, width - 1):
            console.print(x + i, y, "─", fg=(200, 200, 200))
            console.print(x + i, y + height - 1, "─", fg=(200, 200, 200))

        # 세로선
        for i in range(1, height - 1):
            console.print(x, y + i, "│", fg=(200, 200, 200))
            console.print(x + width - 1, y + i, "│", fg=(200, 200, 200))

        # 내부 채우기
        for dy in range(1, height - 1):
            for dx in range(1, width - 1):
                console.print(x + dx, y + dy, " ", bg=(20, 20, 40))

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """텍스트를 최대 너비에 맞춰 여러 줄로 나눔"""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= max_width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines


def open_gold_shop(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory,
    floor_level: int = 1,
    shop_type: str = "shop"
):
    """
    골드 상점 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리
        floor_level: 현재 층수 (장비 등급 결정)
        shop_type: 상점 종류 ("shop" 또는 "blacksmith")
    """
    shop_ui = GoldShopUI(console.width, console.height, inventory, floor_level, shop_type)
    handler = InputHandler()

    logger.info("골드 상점 열림")

    while True:
        # 렌더링
        shop_ui.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                should_close = shop_ui.handle_input(action)
                if should_close:
                    logger.info("골드 상점 닫음")
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
