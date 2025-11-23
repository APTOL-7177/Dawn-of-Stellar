"""
창고 UI

아이템을 보관하고 출고할 수 있는 UI
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any, Dict

from src.equipment.inventory import Inventory
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.audio import play_sfx
from src.gathering.ingredient import IngredientDatabase, IngredientCategory


logger = get_logger("storage_ui")


class StorageUI:
    """창고 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        inventory: Inventory,
        hub_storage: Dict[str, int],
        town_manager: Any,
        context: Any = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.hub_storage = hub_storage.copy()  # 복사본 사용
        self.town_manager = town_manager
        self.context = context  # context 저장
        
        # 선택된 탭 (0: 보관함, 1: 인벤토리)
        self.current_tab = 0
        self.tabs = ["보관함", "인벤토리"]
        
        # 커서 위치
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 15
        
        self.closed = False
        
        # 보관함 아이템 목록 (건설 자재만)
        self.storage_items = self._get_storage_items()
        
        logger.info(f"창고 열기 - 보관 아이템: {len(self.storage_items)}종류")

    def _get_storage_items(self) -> List[tuple]:
        """보관함 아이템 목록 가져오기 (건설 자재만)"""
        items = []
        for item_id, count in self.hub_storage.items():
            ingredient = IngredientDatabase.get_ingredient(item_id)
            if ingredient and ingredient.category == IngredientCategory.CONSTRUCTION:
                items.append((item_id, count, ingredient))
        return sorted(items, key=lambda x: x[2].name if x[2] else x[0])

    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        current_list = self.storage_items if self.current_tab == 0 else self.inventory.slots
        
        if action == GameAction.MOVE_LEFT:
            self.current_tab = max(0, self.current_tab - 1)
            self.cursor = 0
            self.scroll_offset = 0
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_RIGHT:
            self.current_tab = min(len(self.tabs) - 1, self.current_tab + 1)
            self.cursor = 0
            self.scroll_offset = 0
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_UP:
            if current_list:
                self.cursor = max(0, self.cursor - 1)
                if self.cursor < self.scroll_offset:
                    self.scroll_offset = self.cursor
                play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_DOWN:
            if current_list:
                self.cursor = min(len(current_list) - 1, self.cursor + 1)
                if self.cursor >= self.scroll_offset + self.max_visible:
                    self.scroll_offset = self.cursor - self.max_visible + 1
                play_sfx("ui", "cursor_move")
        
        elif action == GameAction.CONFIRM:
            if current_list and 0 <= self.cursor < len(current_list):
                if self.current_tab == 0:  # 보관함에서 출고
                    item_id, count, ingredient = current_list[self.cursor]
                    # 출고 로직은 나중에 구현
                    logger.info(f"보관함에서 출고: {ingredient.name if ingredient else item_id} x{count}")
                elif self.current_tab == 1:  # 인벤토리에서 보관
                    slot = current_list[self.cursor]
                    if slot and slot.item:
                        # 건설 자재만 보관 가능
                        ingredient = IngredientDatabase.get_ingredient(slot.item.item_id)
                        if ingredient and ingredient.category == IngredientCategory.CONSTRUCTION:
                            # 수량 선택
                            if self.context:
                                from src.ui.quantity_selector_ui import select_quantity
                                selected_qty = select_quantity(tcod.console.Console(self.screen_width, self.screen_height, order="F"), self.context, ingredient.name, slot.quantity)
                            else:
                                # context가 없으면 전부 보관
                                selected_qty = slot.quantity
                            
                            if selected_qty:
                                # 보관 로직 - 직접 구현
                                item_id = slot.item.item_id
                                
                                # 현재 storage에 추가
                                if item_id in self.hub_storage:
                                    self.hub_storage[item_id] += selected_qty
                                else:
                                    self.hub_storage[item_id] = selected_qty
                                
                                # town_manager의 storage 업데이트
                                if hasattr(self.town_manager, 'hub_storage'):
                                    self.town_manager.hub_storage = self.hub_storage.copy()
                                
                                # 인벤토리에서 수량만큼 감소
                                if selected_qty >= slot.quantity:
                                    # 전부 보관
                                    self.inventory.remove_item_by_slot(self.cursor)
                                else:
                                    # 일부만 보관
                                    slot.quantity -= selected_qty
                                
                                # UI 업데이트
                                self.storage_items = self._get_storage_items()
                                play_sfx("ui", "confirm")
                                logger.info(f"건설 자재 보관 완료: {ingredient.name} x{selected_qty}")
                        else:
                            play_sfx("ui", "cursor_cancel")
                            logger.info("건설 자재만 보관 가능합니다")
        
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            play_sfx("ui", "cursor_cancel")
            self.closed = True
            return True
        
        return False

    def render(self, console: tcod.console.Console):
        """렌더링"""
        console.clear()
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = "=== 창고 ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 215, 0))
        
        # 탭
        tab_y = 4
        tab_x = 5
        for i, tab_name in enumerate(self.tabs):
            if i == self.current_tab:
                console.print(tab_x + i * 20, tab_y, f"[{tab_name}]", fg=(255, 255, 100))
            else:
                console.print(tab_x + i * 20, tab_y, f" {tab_name} ", fg=(150, 150, 150))
        
        # 현재 선택된 리스트
        current_list = self.storage_items if self.current_tab == 0 else self.inventory.slots
        list_y = 7
        
        # 아이템 목록
        visible_items = current_list[self.scroll_offset:self.scroll_offset + self.max_visible]
        
        if not visible_items:
            message = "보관된 아이템이 없습니다." if self.current_tab == 0 else "인벤토리가 비어있습니다."
            console.print(10, list_y, message, fg=(150, 150, 150))
        else:
            for i, item_data in enumerate(visible_items):
                y = list_y + i
                cursor_index = self.scroll_offset + i
                
                # 커서
                if cursor_index == self.cursor:
                    console.print(3, y, "►", fg=(255, 255, 100))
                
                # 아이템 표시
                if self.current_tab == 0:  # 보관함
                    item_id, count, ingredient = item_data
                    name = ingredient.name if ingredient else item_id
                    color = (255, 255, 255) if cursor_index == self.cursor else (200, 200, 200)
                    console.print(5, y, f"{name} x{count}", fg=color)
                else:  # 인벤토리
                    slot = item_data
                    if slot and slot.item:
                        name = slot.item.name
                        quantity = f" x{slot.quantity}" if slot.quantity > 1 else ""
                        color = (255, 255, 255) if cursor_index == self.cursor else (200, 200, 200)
                        console.print(5, y, f"{name}{quantity}", fg=color)
        
        # 안내 메시지
        help_y = self.screen_height - 2
        help_text = "←→: 탭 변경  ↑↓: 선택  Z: 보관/출고  X: 닫기"
        console.print(2, help_y, help_text, fg=Colors.GRAY)


def open_storage(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory: Inventory,
    hub_storage: Dict[str, int],
    town_manager: Any
):
    """창고 열기"""
    ui = StorageUI(console.width, console.height, inventory, hub_storage, town_manager, context)
    handler = InputHandler()
    
    logger.info("창고 열기")
    
    while not ui.closed:
        ui.render(console)
        context.present(console)
        
        for event in tcod.event.wait():
            action = handler.dispatch(event)
            
            if action:
                ui.handle_input(action)
            
            if isinstance(event, tcod.event.Quit):
                ui.closed = True
                break

