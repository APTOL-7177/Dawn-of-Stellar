"""
골드 상점 UI - 골드로 아이템 구매

M 메뉴에서 언제든지 접근 가능한 기본 상점
맵의 상인 NPC는 특별한 아이템이나 할인 가격으로 제공
"""

from enum import Enum
from typing import List, Optional
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers
from src.equipment.item_system import (
    Consumable, Equipment, ItemType, ItemRarity, EquipSlot,
    CONSUMABLE_TEMPLATES, WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES
)


logger = get_logger(Loggers.UI)


class GoldShopTab(Enum):
    """상점 탭"""
    CONSUMABLES = "소모품"
    EQUIPMENT = "장비"
    SPECIAL = "특수 아이템"


class GoldShopItem:
    """골드 상점 아이템"""

    def __init__(self, name: str, description: str, price: int, item_obj=None, item_type: str = "consumable"):
        self.name = name
        self.description = description
        self.price = price
        self.item_obj = item_obj  # 실제 아이템 객체
        self.item_type = item_type  # "consumable", "equipment", "special"


def get_gold_shop_items(floor_level: int = 1) -> dict:
    """
    골드 상점 아이템 목록 생성

    Args:
        floor_level: 현재 층수 (장비 등급 결정)

    Returns:
        탭별 아이템 딕셔너리
    """
    items = {
        GoldShopTab.CONSUMABLES: [],
        GoldShopTab.EQUIPMENT: [],
        GoldShopTab.SPECIAL: []
    }

    # === 소모품 (회복 아이템) ===
    # 템플릿에서 소모품 생성
    consumable_items = [
        ("health_potion", 50),
        ("mega_health_potion", 120),
        ("super_health_potion", 250),
        ("mana_potion", 60),
        ("mega_mana_potion", 140),
        ("elixir", 500),
        # BRV/상처 관련 소모품
        ("wound_salve", 80),
        ("greater_wound_salve", 180),
        ("phoenix_tears", 450),
        ("brave_crystal", 200),
        ("mega_brave_crystal", 400),
    ]

    for item_id, price in consumable_items:
        if item_id in CONSUMABLE_TEMPLATES:
            template = CONSUMABLE_TEMPLATES[item_id]
            consumable = Consumable(
                item_id=item_id,
                name=template["name"],
                description=template["description"],
                item_type=ItemType.CONSUMABLE,
                rarity=template["rarity"],
                effect_type=template["effect_type"],
                effect_value=template["effect_value"],
                sell_price=template["sell_price"]
            )
            items[GoldShopTab.CONSUMABLES].append(
                GoldShopItem(
                    consumable.name,
                    consumable.description,
                    price,
                    consumable,
                    "consumable"
                )
            )

    # === 장비 (층수에 맞는 장비) ===
    # floor_level에 따라 적절한 등급의 장비 제공
    equipment_items = []

    if floor_level <= 3:
        # 초반 (1~3층): 기본 장비
        equipment_items = [
            ("iron_sword", 100),
            ("wooden_staff", 120),
            ("hunting_bow", 90),
            ("leather_armor", 80),
            ("health_ring", 100),
            ("mana_ring", 100),
            ("apprentice_robe", 110),
            ("iron_greatsword", 150),
        ]
    elif floor_level <= 7:
        # 중반 (4~7층): 중급 장비
        equipment_items = [
            ("steel_sword", 300),
            ("crystal_staff", 350),
            ("longbow", 280),
            ("chainmail", 250),
            ("battle_mage_robe", 320),
            ("regeneration_ring", 380),
            ("wisdom_tome", 400),
            ("vampire_dagger", 420),
            ("eagle_eye_amulet", 350),  # +1 시야
        ]
    elif floor_level <= 12:
        # 후반 (8~12층): 고급 장비
        equipment_items = [
            ("mithril_sword", 800),
            ("archmagus_staff", 900),
            ("assassin_dagger", 750),
            ("plate_armor", 700),
            ("phoenix_ring", 850),
            ("sorcerer_vestments", 880),
            ("elemental_scepter", 920),
            ("lifesteal_blade", 1000),
            ("berserker_axe", 950),
            ("far_sight_lens", 700),  # +1 시야
            ("wound_ward_armor", 850),  # 상처 감소
        ]
    else:
        # 최후반 (13층+): 최상급 장비
        equipment_items = [
            ("dragon_slayer", 2500),
            ("excalibur", 5000),
            ("staff_of_cosmos", 3000),
            ("dragon_armor", 2000),
            ("ring_of_gods", 2500),
            ("elemental_master_robe", 2800),
            ("meteor_staff", 3500),
            ("apocalypse_blade", 4500),
            ("owls_pendant", 2000),  # +2 시야
            ("immortal_ring", 3200),  # 상처 면역
        ]

    for item_id, price in equipment_items:
        # 무기 템플릿 확인
        if item_id in WEAPON_TEMPLATES:
            template = WEAPON_TEMPLATES[item_id]
            equipment = Equipment(
                item_id=item_id,
                name=template["name"],
                description=template["description"],
                item_type=ItemType.WEAPON,
                rarity=template["rarity"],
                level_requirement=template["level_requirement"],
                base_stats=template["base_stats"],
                sell_price=template["sell_price"],
                equip_slot=EquipSlot.WEAPON,
                unique_effect=template.get("unique_effect")  # 특수 효과 추가
            )
            items[GoldShopTab.EQUIPMENT].append(
                GoldShopItem(equipment.name, equipment.description, price, equipment, "equipment")
            )
        # 방어구 템플릿 확인
        elif item_id in ARMOR_TEMPLATES:
            template = ARMOR_TEMPLATES[item_id]
            equipment = Equipment(
                item_id=item_id,
                name=template["name"],
                description=template["description"],
                item_type=ItemType.ARMOR,
                rarity=template["rarity"],
                level_requirement=template["level_requirement"],
                base_stats=template["base_stats"],
                sell_price=template["sell_price"],
                equip_slot=EquipSlot.ARMOR,
                unique_effect=template.get("unique_effect")  # 특수 효과 추가
            )
            items[GoldShopTab.EQUIPMENT].append(
                GoldShopItem(equipment.name, equipment.description, price, equipment, "equipment")
            )
        # 장신구 템플릿 확인
        elif item_id in ACCESSORY_TEMPLATES:
            template = ACCESSORY_TEMPLATES[item_id]
            equipment = Equipment(
                item_id=item_id,
                name=template["name"],
                description=template["description"],
                item_type=ItemType.ACCESSORY,
                rarity=template["rarity"],
                level_requirement=template["level_requirement"],
                base_stats=template["base_stats"],
                sell_price=template["sell_price"],
                equip_slot=EquipSlot.ACCESSORY,
                unique_effect=template.get("unique_effect")  # 특수 효과 추가
            )
            items[GoldShopTab.EQUIPMENT].append(
                GoldShopItem(equipment.name, equipment.description, price, equipment, "equipment")
            )

    # === 특수 아이템 ===
    special_items = [
        ("town_portal", 200),
        ("dungeon_key", 150),
        ("phoenix_down", 350),
        ("revival_essence", 400),
        ("wound_cure_essence", 350),
        ("brv_shield_elixir", 280),
    ]

    for item_id, price in special_items:
        if item_id in CONSUMABLE_TEMPLATES:
            template = CONSUMABLE_TEMPLATES[item_id]
            consumable = Consumable(
                item_id=item_id,
                name=template["name"],
                description=template["description"],
                item_type=ItemType.CONSUMABLE,
                rarity=template["rarity"],
                effect_type=template["effect_type"],
                effect_value=template["effect_value"],
                sell_price=template["sell_price"]
            )
            items[GoldShopTab.SPECIAL].append(
                GoldShopItem(consumable.name, consumable.description, price, consumable, "special")
            )

    return items


class GoldShopUI:
    """골드 상점 UI"""

    def __init__(self, screen_width: int, screen_height: int, inventory, floor_level: int = 1):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.floor_level = floor_level

        # 상점 아이템
        self.shop_items = get_gold_shop_items(floor_level)

        # UI 상태
        self.current_tab = GoldShopTab.CONSUMABLES
        self.selected_index = 0
        self.tabs = list(GoldShopTab)
        self.tab_index = 0

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Returns:
            True: 상점 종료
        """
        if action == GameAction.MOVE_LEFT:
            # 탭 이동
            self.tab_index = max(0, self.tab_index - 1)
            self.current_tab = self.tabs[self.tab_index]
            self.selected_index = 0

        elif action == GameAction.MOVE_RIGHT:
            # 탭 이동
            self.tab_index = min(len(self.tabs) - 1, self.tab_index + 1)
            self.current_tab = self.tabs[self.tab_index]
            self.selected_index = 0

        elif action == GameAction.MOVE_UP:
            current_items = self.shop_items[self.current_tab]
            self.selected_index = max(0, self.selected_index - 1)

        elif action == GameAction.MOVE_DOWN:
            current_items = self.shop_items[self.current_tab]
            self.selected_index = min(len(current_items) - 1, self.selected_index + 1)

        elif action == GameAction.CONFIRM:
            # 아이템 구매
            self._purchase_item()

        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            # 상점 닫기
            return True

        return False

    def _purchase_item(self):
        """아이템 구매"""
        current_items = self.shop_items[self.current_tab]

        if not current_items:
            logger.warning("구매할 아이템이 없습니다")
            return

        selected_item = current_items[self.selected_index]

        # 골드 확인
        if self.inventory.gold < selected_item.price:
            logger.warning(f"골드가 부족합니다. (필요: {selected_item.price}G, 보유: {self.inventory.gold}G)")
            return

        # 인벤토리 공간 확인
        if not self.inventory.can_add_item():
            logger.warning("인벤토리가 가득 찼습니다")
            return

        # 구매
        self.inventory.remove_gold(selected_item.price)
        self.inventory.add_item(selected_item.item_obj)

        logger.info(f"구매 완료: {selected_item.name} ({selected_item.price}G)")

    def render(self, console: tcod.console.Console):
        """상점 렌더링"""
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
            if i == self.selected_index:
                # 선택된 아이템
                console.print(shop_x + 2, item_y, "►", fg=(255, 255, 100))
                console.print(shop_x + 4, item_y, item.name, fg=(255, 255, 100))

                # 가격 (골드 부족 시 빨간색)
                price_color = (255, 255, 100) if self.inventory.gold >= item.price else (255, 100, 100)
                console.print(shop_x + shop_width - 12, item_y, f"{item.price}G", fg=price_color)
            else:
                # 일반 아이템
                console.print(shop_x + 4, item_y, item.name, fg=(200, 200, 200))
                console.print(shop_x + shop_width - 12, item_y, f"{item.price}G", fg=(200, 200, 200))

            item_y += 1

        # 선택된 아이템 설명
        if current_items:
            selected_item = current_items[self.selected_index]
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
    floor_level: int = 1
):
    """
    골드 상점 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리
        floor_level: 현재 층수 (장비 등급 결정)
    """
    shop_ui = GoldShopUI(console.width, console.height, inventory, floor_level)
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
