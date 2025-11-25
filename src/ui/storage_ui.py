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
        hub_storage: List[Dict[str, Any]],  # 하위 호환성용 (사용하지 않음)
        town_manager: Any,
        context: Any = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.hub_storage = hub_storage.copy() if hub_storage is not None else []  # 하위 호환성 (사용하지 않음)
        self.town_manager = town_manager
        self.context = context  # context 저장

        # 마을 창고 인벤토리 사용 (필수)
        self.storage_inventory = []
        if hasattr(town_manager, 'get_storage_inventory'):
            self.storage_inventory = town_manager.get_storage_inventory().copy()
            logger.info(f"마을 창고 초기화: {len(self.storage_inventory)}개 아이템")
        else:
            logger.warning("town_manager에 get_storage_inventory 메서드가 없습니다. 하위 호환 모드로 작동합니다.")
            # 하위 호환성: hub_storage 사용
            if hasattr(town_manager, 'get_hub_storage'):
                self.storage_inventory = town_manager.get_hub_storage().copy()
                logger.info(f"하위 호환 모드: hub_storage 사용 ({len(self.storage_inventory)}개 아이템)")
        
        # 선택된 탭 (0: 보관함, 1: 인벤토리)
        self.current_tab = 0
        self.tabs = ["보관함", "인벤토리"]
        
        # 커서 위치
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 15
        
        self.closed = False
        
        # 보관함 아이템 목록 (모든 아이템)
        self.storage_items = self._get_storage_items()
        
        logger.info(f"창고 열기 - 보관 아이템: {len(self.storage_items)}종류")

    def _get_storage_items(self) -> List[tuple]:
        """보관함 아이템 목록 가져오기 (모든 아이템)"""
        from src.persistence.save_system import deserialize_item

        # 마을 창고 우선 사용, 없으면 hub_storage 사용
        storage_source = self.storage_inventory if self.storage_inventory else self.hub_storage

        # 아이템을 item_id별로 그룹화
        item_groups = {}  # {item_id: [(item_data, index), ...]}

        for idx, item_data in enumerate(storage_source):
            item_id = item_data.get("item_id", "")
            if item_id not in item_groups:
                item_groups[item_id] = []
            item_groups[item_id].append((item_data, idx))

        # 그룹화된 아이템을 리스트로 변환
        items = []
        for item_id, group in item_groups.items():
            count = len(group)
            # 첫 번째 아이템으로 객체 생성 (이름 표시용)
            try:
                first_item = deserialize_item(group[0][0])
                item_name = getattr(first_item, 'name', item_id)
                ingredient = IngredientDatabase.get_ingredient(item_id) if IngredientDatabase.get_ingredient(item_id) else None
            except Exception as e:
                logger.warning(f"아이템 역직렬화 실패: {item_id} - {e}")
                item_name = item_id
                ingredient = None

            items.append((item_id, count, ingredient, item_name, group))  # group은 출고 시 사용

        return sorted(items, key=lambda x: (x[3] if len(x) > 3 and x[3] else (x[2].name if x[2] else x[0])))

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
                    item_data = current_list[self.cursor]
                    if len(item_data) >= 5:
                        item_id, count, ingredient, item_name, group = item_data
                    else:
                        # 호환성을 위한 폴백
                        item_id, count, ingredient = item_data[:3]
                        item_name = ingredient.name if ingredient else item_id
                        group = None
                    
                    # 수량 선택
                    if self.context:
                        from src.ui.quantity_selector_ui import select_quantity
                        selected_qty = select_quantity(tcod.console.Console(self.screen_width, self.screen_height, order="F"), self.context, item_name, count)
                        # 취소했으면 None 반환
                        if selected_qty is None:
                            play_sfx("ui", "cursor_cancel")
                            return False
                    else:
                        # context가 없으면 전부 출고
                        selected_qty = count
                    
                    if selected_qty and selected_qty > 0:
                        if not group:
                            play_sfx("ui", "cursor_cancel")
                            logger.warning("출고할 아이템 데이터를 찾을 수 없습니다")
                            return False
                        from src.persistence.save_system import deserialize_item
                        
                        # 인벤토리에 추가 시도
                        added_count = 0
                        indices_to_remove = []  # 제거할 인덱스 (역순으로)
                        
                        # 선택한 수량만큼 역직렬화해서 인벤토리에 추가
                        for i in range(min(selected_qty, len(group))):
                            item_data_dict, storage_idx = group[i]
                            try:
                                item = deserialize_item(item_data_dict)
                                if self.inventory.add_item(item):
                                    added_count += 1
                                    indices_to_remove.append(storage_idx)
                                else:
                                    # 인벤토리 가득 참
                                    break
                            except Exception as e:
                                logger.error(f"아이템 역직렬화 실패: {item_id} - {e}", exc_info=True)
                                break
                        
                        if added_count > 0:
                            # 마을 창고에서 제거 (우선순위)
                            if self.storage_inventory is not None:
                                # town_manager의 storage_inventory에서 제거
                                if hasattr(self.town_manager, 'retrieve_item_from_storage'):
                                    removed_count = 0
                                    for _ in range(added_count):
                                        try:
                                            # 마지막 아이템부터 제거 (LIFO)
                                            if len(self.storage_inventory) > 0:
                                                self.storage_inventory.pop()
                                                removed_count += 1
                                        except Exception as e:
                                            logger.error(f"창고 아이템 제거 실패: {e}")
                                            break
                                    logger.info(f"마을 창고에서 {removed_count}개 아이템 제거")
                                else:
                                    logger.warning("town_manager에 retrieve_item_from_storage 메서드가 없습니다")
                                    # 폴백: 직접 리스트에서 제거
                                    indices_to_remove.sort(reverse=True)
                                    for idx in indices_to_remove:
                                        if 0 <= idx < len(self.storage_inventory):
                                            del self.storage_inventory[idx]
                            else:
                                # 하위 호환성: hub_storage 사용
                                indices_to_remove.sort(reverse=True)
                                for idx in indices_to_remove:
                                    if 0 <= idx < len(self.hub_storage):
                                        del self.hub_storage[idx]

                                if hasattr(self.town_manager, 'hub_storage'):
                                    self.town_manager.hub_storage = self.hub_storage.copy()

                            # UI 업데이트
                            self.storage_items = self._get_storage_items()
                            play_sfx("ui", "confirm")
                            logger.info(f"아이템 출고 완료: {item_name} x{added_count}")
                            return False  # UI 갱신을 위해 반복 계속
                        else:
                            play_sfx("ui", "cursor_cancel")
                            logger.info("인벤토리가 가득 찼습니다")
                    else:
                        # selected_qty가 0이거나 유효하지 않음
                        play_sfx("ui", "cursor_cancel")
                        logger.info("출고할 수량이 없습니다")
                elif self.current_tab == 1:  # 인벤토리에서 보관
                    slot = current_list[self.cursor]
                    if slot and slot.item:
                        # 모든 아이템 보관 가능
                        from src.persistence.save_system import serialize_item
                        
                        item = slot.item
                        item_name = getattr(item, 'name', slot.item.item_id)
                        
                        # 수량 선택
                        if self.context:
                            from src.ui.quantity_selector_ui import select_quantity
                            selected_qty = select_quantity(tcod.console.Console(self.screen_width, self.screen_height, order="F"), self.context, item_name, slot.quantity)
                            # 취소했으면 None 반환
                            if selected_qty is None:
                                play_sfx("ui", "cursor_cancel")
                                return False
                        else:
                            # context가 없으면 전부 보관
                            selected_qty = slot.quantity
                        
                        if selected_qty and selected_qty > 0:
                            # 보관 로직 - 아이템을 직렬화해서 저장
                            items_to_store = []
                            
                            # 수량만큼 직렬화
                            for _ in range(selected_qty):
                                try:
                                    serialized = serialize_item(item)
                                    items_to_store.append(serialized)
                                except Exception as e:
                                    logger.error(f"아이템 직렬화 실패: {item_name} - {e}", exc_info=True)
                                    break
                            
                            if items_to_store:
                                # 마을 창고에 추가 (우선순위)
                                if self.storage_inventory is not None:
                                    self.storage_inventory.extend(items_to_store)
                                    # town_manager의 storage_inventory 업데이트
                                    if hasattr(self.town_manager, 'store_item_to_storage'):
                                        # 개별 아이템으로 저장 (메서드 재사용)
                                        stored_count = 0
                                        for serialized_item in items_to_store:
                                            try:
                                                from src.persistence.save_system import deserialize_item
                                                item = deserialize_item(serialized_item)
                                                if self.town_manager.store_item_to_storage(item):
                                                    stored_count += 1
                                            except Exception as e:
                                                logger.error(f"창고 저장 실패: {e}")
                                        logger.info(f"마을 창고에 {stored_count}개 아이템 저장")
                                    else:
                                        logger.warning("town_manager에 store_item_to_storage 메서드가 없습니다")
                                else:
                                    # 하위 호환성: hub_storage 사용
                                    self.hub_storage.extend(items_to_store)
                                    if hasattr(self.town_manager, 'hub_storage'):
                                        self.town_manager.hub_storage = self.hub_storage.copy()

                                # 인벤토리에서 수량만큼 감소
                                if selected_qty >= slot.quantity:
                                    # 전부 보관
                                    self.inventory.remove_item(self.cursor, slot.quantity)
                                else:
                                    # 일부만 보관
                                    self.inventory.remove_item(self.cursor, selected_qty)

                                # UI 업데이트
                                self.storage_items = self._get_storage_items()
                                play_sfx("ui", "confirm")
                                logger.info(f"아이템 보관 완료: {item_name} x{len(items_to_store)}")
                                return False  # UI 갱신을 위해 반복 계속
                            else:
                                play_sfx("ui", "cursor_cancel")
                                logger.warning(f"아이템 보관 실패: {item_name}")
                        else:
                            # selected_qty가 0이거나 유효하지 않음
                            play_sfx("ui", "cursor_cancel")
                            logger.info("보관할 수량이 없습니다")
        
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
                    if len(item_data) >= 5:
                        item_id, count, ingredient, item_name, group = item_data
                        name = item_name
                    else:
                        # 호환성을 위한 폴백
                        item_id, count, ingredient = item_data[:3]
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
    hub_storage: Optional[List[Dict[str, Any]]],  # 하위 호환성용 (사용하지 않음)
    town_manager: Any
):
    """창고 열기"""
    ui = StorageUI(console.width, console.height, inventory, hub_storage, town_manager, context)
    handler = InputHandler()
    
    logger.info("창고 열기")
    
    try:
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
    finally:
        # UI 종료 시 town_manager의 storage를 최종 상태로 동기화
        if ui.storage_inventory is not None:
            # 마을 창고가 사용된 경우, 이미 town_manager에 동기화되어 있으므로 추가 동기화 불필요
            logger.info(f"창고 UI 종료: 마을 창고 사용됨 ({len(ui.storage_inventory)}개 아이템)")
        elif hasattr(ui.town_manager, 'hub_storage'):
            # 하위 호환성: hub_storage 동기화
            ui.town_manager.hub_storage = ui.hub_storage.copy()
            logger.info(f"창고 UI 종료: town_manager.hub_storage 동기화 완료 ({len(ui.town_manager.hub_storage)}개 아이템)")
        else:
            logger.warning("창고 UI 종료: 저장소 동기화 실패.")
    
    logger.info("창고 닫기")

