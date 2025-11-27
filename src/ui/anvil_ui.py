from typing import Optional, List
import tcod

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.core.logger import get_logger, Loggers
from src.audio import play_sfx
from src.ui.tcod_display import render_popup_background

logger = get_logger(Loggers.UI)

class AnvilUI:
    """모루 상호작용 UI"""

    def __init__(self, screen_width: int, screen_height: int, inventory, target_tile):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.target_tile = target_tile
        self.menu: Optional[CursorMenu] = None
        self._init_menu()

    def _init_menu(self):
        """메뉴 초기화"""
        if getattr(self.target_tile, 'used', False):
            # 이미 사용한 모루
            self.menu = CursorMenu(
                title="망가진 모루",
                items=[MenuItem("이 모루는 더 이상 사용할 수 없습니다.", action=lambda: "close")],
                x=(self.screen_width - 50) // 2,
                y=(self.screen_height - 10) // 2,
                width=50,
                show_description=False
            )
            return

        # 수리 가능한 장비 수집
        repairable_items = []
        
        def add_item(item, owner):
            if item and hasattr(item, 'current_durability') and hasattr(item, 'max_durability'):
                if item.current_durability < item.max_durability:
                    repairable_items.append((item, owner))

        # 인벤토리
        for slot in self.inventory.slots:
            add_item(slot.item, "인벤토리")
            
        # 파티원
        if self.inventory.party:
            for member in self.inventory.party:
                for _, item in member.equipment.items():
                    add_item(item, member.name)

        if not repairable_items:
            self.menu = CursorMenu(
                title="모루 (수리할 장비 없음)",
                items=[MenuItem("수리할 장비가 없습니다.", action=lambda: "close")],
                x=(self.screen_width - 50) // 2,
                y=(self.screen_height - 10) // 2,
                width=50,
                show_description=False
            )
            return

        # 메뉴 아이템 생성
        menu_items = []
        for item, owner in repairable_items:
            text = f"[{owner}] {item.name} ({item.current_durability}/{item.max_durability})"
            
            # 콜백: 수리 실행 -> 타일 사용 처리 -> 닫기
            action = lambda i=item: self._repair_item(i)
            menu_items.append(MenuItem(text, action=action))

        menu_items.append(MenuItem("나가기", action=lambda: "close"))

        self.menu = CursorMenu(
            title="모루: 장비 수리 (1회 한정)",
            items=menu_items,
            x=(self.screen_width - 60) // 2,
            y=(self.screen_height - 20) // 2,
            width=60,
            show_description=False
        )

    def _repair_item(self, item):
        """아이템 수리"""
        # 아이템이 어디에 있는지 확인 (장착되어 있는지, 인벤토리에 있는지)
        item_location = None  # "equipped" or "inventory"
        item_owner = None
        item_slot = None
        
        # 장착된 아이템인지 확인
        if self.inventory.party:
            for member in self.inventory.party:
                for slot, equipped in member.equipment.items():
                    if equipped == item:
                        item_location = "equipped"
                        item_owner = member
                        item_slot = slot
                        break
                if item_location:
                    break
        
        # 인벤토리에 있는 아이템인지 확인
        if not item_location:
            for slot in self.inventory.slots:
                if slot.item == item:
                    item_location = "inventory"
                    break
        
        # 아이템 수리
        item.current_durability = item.max_durability
        
        # 스탯 업데이트: 장착된 아이템인 경우만
        if item_location == "equipped" and item_owner and item_slot:
            item_owner.update_equipment_stats(item_slot)
        
        # 내구도가 0이었던 아이템이 인벤토리에 있고, 해당 파티원의 슬롯이 비어있으면 자동 재장착 시도
        # 모든 파티원을 확인하여 해당 아이템의 슬롯 타입과 일치하는 비어있는 슬롯을 찾음
        if item_location == "inventory" and self.inventory.party:
            from src.equipment.item_system import EquipSlot
            item_equip_slot = getattr(item, 'equip_slot', None)
            if item_equip_slot:
                # 슬롯 이름 결정
                slot_name = None
                if hasattr(item_equip_slot, 'value'):
                    slot_value = item_equip_slot.value
                    slot_name = slot_value if isinstance(slot_value, str) else None
                elif isinstance(item_equip_slot, str):
                    slot_name = item_equip_slot
                elif hasattr(item_equip_slot, 'name'):
                    # EquipSlot enum 직접 매핑
                    slot_map = {
                        EquipSlot.WEAPON: "weapon",
                        EquipSlot.ARMOR: "armor",
                        EquipSlot.ACCESSORY: "accessory"
                    }
                    slot_name = slot_map.get(item_equip_slot)
                
                # 모든 파티원 중 해당 슬롯이 비어있는 파티원을 찾아 자동 재장착 시도
                if slot_name:
                    for member in self.inventory.party:
                        if not member.equipment.get(slot_name):
                            try:
                                # equip_item 메서드가 있으면 사용
                                if hasattr(member, 'equip_item'):
                                    if member.equip_item(item):
                                        # 인벤토리에서 아이템 제거
                                        for inv_slot in self.inventory.slots:
                                            if inv_slot.item == item:
                                                self.inventory.slots.remove(inv_slot)
                                                break
                                        logger.info(f"{item.name}이(가) {member.name}에게 수리 후 자동으로 재장착되었습니다.")
                                        break
                                else:
                                    # 직접 장착
                                    member.equipment[slot_name] = item
                                    member.update_equipment_stats(slot_name)
                                    # 인벤토리에서 아이템 제거
                                    for inv_slot in self.inventory.slots:
                                        if inv_slot.item == item:
                                            self.inventory.slots.remove(inv_slot)
                                            break
                                    logger.info(f"{item.name}이(가) {member.name}에게 수리 후 자동으로 재장착되었습니다.")
                                    break
                            except Exception as e:
                                logger.warning(f"자동 재장착 실패: {e}")
                        
        # 모루 사용 처리
        self.target_tile.used = True
        
        logger.info(f"모루에서 {item.name} 수리 완료.")
        play_sfx("ui", "repair_success")
        return "close"

    def render(self, console: tcod.console.Console):
        """렌더링"""
        if self.menu:
            # 배경을 어둡게 처리 (팝업 효과)
            console.draw_rect(0, 0, self.screen_width, self.screen_height, 0, bg=(0, 0, 0), bg_blend=tcod.BKGND_ALPHA(200))
            self.menu.render(console)

    def handle_input(self, action: GameAction) -> bool:
        """입력 처리. True 반환 시 종료"""
        if not self.menu:
            return True
            
        if action == GameAction.MOVE_UP:
            self.menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            result = self.menu.execute_selected()
            if result == "close":
                return True
        elif action == GameAction.ESCAPE or action == GameAction.CANCEL:
            return True
            
        return False

def open_anvil_ui(console, context, inventory, target_tile):
    """모루 UI 열기"""
    ui = AnvilUI(console.width, console.height, inventory, target_tile)
    
    while True:
        ui.render(console)
        context.present(console)
        
        for event in tcod.event.wait():
            action = unified_input_handler.process_tcod_event(event)
            if action:
                if ui.handle_input(action):
                    return
            
            if isinstance(event, tcod.event.Quit):
                raise SystemExit()

