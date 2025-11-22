"""
인벤토리 UI

아이템 확인, 사용, 장비 착용
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any
from enum import Enum

from src.equipment.inventory import Inventory
from src.equipment.item_system import Item, Equipment, Consumable, ItemType
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.ui.cursor_menu import CursorMenu, MenuItem
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("inventory_ui")


class InventoryMode(Enum):
    """인벤토리 모드"""
    BROWSE = "browse"  # 둘러보기
    USE_ITEM = "use_item"  # 아이템 사용
    EQUIP = "equip"  # 장비 착용
    SELECT_TARGET = "select_target"  # 대상 선택
    CHARACTER_EQUIPMENT = "character_equipment"  # 캐릭터 장비 보기
    UNEQUIP = "unequip"  # 장비 해제
    CONFIRM_DESTROY = "confirm_destroy"  # 파괴 확인
    DROP_ITEM = "drop_item"  # 아이템 드롭
    DROP_GOLD = "drop_gold"  # 골드 드롭


class InventoryUI:
    """인벤토리 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        inventory: Inventory,
        party: List[Any],
        exploration: Optional[Any] = None
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            inventory: 인벤토리
            party: 파티 멤버 리스트
            exploration: 탐험 시스템 (드롭 위치를 알기 위해)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.party = party
        self.exploration = exploration

        self.mode = InventoryMode.BROWSE
        self.cursor = 0  # 아이템 커서
        self.scroll_offset = 0
        self.max_visible = 15  # 한 번에 표시할 아이템 수

        # 필터
        self.filter_type: Optional[ItemType] = None

        # 선택된 아이템/대상
        self.selected_item_index: Optional[int] = None
        self.target_cursor = 0

        # 정렬 메뉴
        self.sort_menu: Optional[CursorMenu] = None

        # 캐릭터 장비 관리
        self.selected_character_index: Optional[int] = None
        self.equipment_cursor = 0  # weapon, armor, accessory 선택
        self.equipment_slots = ["weapon", "armor", "accessory"]

        # 파괴 확인
        self.confirm_destroy_item: Optional[int] = None
        self.confirm_yes = False
        self.destroy_quantity: int = 1  # 파괴할 개수
        self.destroy_quantity_input_mode: bool = False  # 개수 입력 모드

        # 드롭 관련
        self.drop_item_index: Optional[int] = None
        self.drop_quantity: int = 1
        self.drop_quantity_input_mode: bool = False
        self.drop_gold_amount: int = 0
        self.drop_gold_input_mode: bool = False

        # 장비 비교 모드
        self.show_comparison = False

        self.closed = False

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            닫기 여부
        """
        # 정렬 메뉴가 열려있으면 우선 처리
        if self.sort_menu:
            return self._handle_sort_menu(action)

        if self.mode == InventoryMode.BROWSE:
            return self._handle_browse(action)
        elif self.mode == InventoryMode.USE_ITEM or self.mode == InventoryMode.EQUIP:
            return self._handle_use_or_equip(action)
        elif self.mode == InventoryMode.SELECT_TARGET:
            return self._handle_target_select(action)
        elif self.mode == InventoryMode.CHARACTER_EQUIPMENT:
            return self._handle_character_equipment(action)
        elif self.mode == InventoryMode.UNEQUIP:
            return self._handle_unequip(action)
        elif self.mode == InventoryMode.CONFIRM_DESTROY:
            return self._handle_confirm_destroy(action)
        elif self.mode == InventoryMode.DROP_ITEM:
            return self._handle_drop_item(action)
        elif self.mode == InventoryMode.DROP_GOLD:
            return self._handle_drop_gold(action)

        return False

    def _handle_browse(self, action: GameAction) -> bool:
        """둘러보기 모드 입력"""
        if action == GameAction.MOVE_UP:
            self.cursor = max(0, self.cursor - 1)
            self._update_scroll()
            self.show_comparison = False
        elif action == GameAction.MOVE_DOWN:
            # 필터링된 아이템 수 기준으로 커서 이동
            filtered_count = self._get_filtered_item_count()
            self.cursor = min(filtered_count - 1, self.cursor + 1)
            self._update_scroll()
            self.show_comparison = False
        elif action == GameAction.USE_CONSUMABLE:
            # F 키: 음식/소비품 직접 사용 (첫 번째 캐릭터에게 바로 사용)
            if len(self.inventory) > 0:
                # 필터링된 인덱스를 원래 인덱스로 변환
                actual_index = self._get_actual_slot_index(self.cursor)
                item = self.inventory.get_item(actual_index)
                if item:
                    # CookedFood 타입 확인
                    from src.cooking.recipe import CookedFood

                    if isinstance(item, (Consumable, CookedFood)):
                        # 첫 번째 캐릭터에게 바로 사용
                        target = self.party[0] if self.party else None
                        if target:
                            success = self.inventory.use_consumable(actual_index, target)
                            if success:
                                item_name = getattr(item, 'name', '알 수 없는 아이템')
                                logger.info(f"{item_name} 사용 완료 (대상: {target.name})")
                                # 인덱스 조정
                                if self.cursor >= len(self.inventory):
                                    self.cursor = max(0, len(self.inventory) - 1)
                        else:
                            logger.warning("사용할 대상이 없습니다")
        elif action == GameAction.CONFIRM:
            # 아이템 사용/장착
            if len(self.inventory) > 0:
                # 필터링된 인덱스를 원래 인덱스로 변환
                actual_index = self._get_actual_slot_index(self.cursor)
                item = self.inventory.get_item(actual_index)
                if item:
                    # CookedFood 타입 확인
                    from src.cooking.recipe import CookedFood

                    self.selected_item_index = actual_index

                    if isinstance(item, Equipment):
                        # 장비 아이템: 장착 모드로 전환
                        self.mode = InventoryMode.EQUIP
                        self.show_comparison = False
                    elif isinstance(item, (Consumable, CookedFood)):
                        # CookedFood는 바로 사용 (아군 전체에 효과)
                        from src.cooking.recipe import CookedFood
                        if isinstance(item, CookedFood):
                            # 음식은 타겟 선택 없이 바로 사용
                            target = self.party[0] if self.party else None  # 더미 타겟
                            success = self.inventory.use_consumable(actual_index, target)
                            if success:
                                item_name = getattr(item, 'name', '알 수 없는 아이템')
                                logger.info(f"{item_name} 사용 완료 (아군 전체)")
                                # 인덱스 조정
                                if self.cursor >= len(self.inventory):
                                    self.cursor = max(0, len(self.inventory) - 1)
                        else:
                            # 일반 소비품: 사용 모드로 전환
                            self.mode = InventoryMode.USE_ITEM
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            play_sfx("ui", "cursor_cancel")
            self.closed = True
            return True
        elif action == GameAction.MOVE_LEFT:
            # 필터 변경
            self._change_filter(-1)
            self.show_comparison = False
        elif action == GameAction.MOVE_RIGHT:
            # 필터 변경
            self._change_filter(1)
            self.show_comparison = False
        elif action == GameAction.MENU:
            # 정렬 메뉴 ('M' 키)
            self._open_sort_menu()
            self.show_comparison = False
        elif action == GameAction.OPEN_CHARACTER:
            # 캐릭터 장비 보기 ('C' 키)
            self.mode = InventoryMode.CHARACTER_EQUIPMENT
            self.target_cursor = 0
            self.show_comparison = False
        elif action == GameAction.INVENTORY_DESTROY:
            # 아이템 파괴 ('V' 키)
            if len(self.inventory) > 0:
                self.confirm_destroy_item = self.cursor
                self.mode = InventoryMode.CONFIRM_DESTROY
                self.confirm_yes = False
                self.show_comparison = False
        elif action == GameAction.INVENTORY_DROP:
            # 아이템 드롭 ('D' 키)
            if len(self.inventory) > 0 and self.exploration:
                actual_index = self._get_actual_slot_index(self.cursor)
                self.drop_item_index = actual_index
                self.drop_quantity = 1
                self.drop_quantity_input_mode = False
                self.mode = InventoryMode.DROP_ITEM
                self.show_comparison = False
        elif action == GameAction.INVENTORY_DROP_GOLD:
            # 골드 드롭 ('G' 키)
            if self.exploration and self.inventory.gold > 0:
                self.drop_gold_amount = 0
                self.drop_gold_input_mode = True
                self.mode = InventoryMode.DROP_GOLD

        return False

    def _handle_use_or_equip(self, action: GameAction) -> bool:
        """아이템 사용/장착 모드 입력"""
        from src.cooking.recipe import CookedFood
        item = self.inventory.get_item(self.selected_item_index)
        
        # CookedFood인 경우 타겟 선택 없이 바로 사용 (아군 전체에 효과)
        if isinstance(item, CookedFood):
            if action == GameAction.CONFIRM:
                # 음식은 아군 전체에게 효과 적용 (target은 무시됨)
                target = self.party[0] if self.party else None  # 더미 타겟
                success = self.inventory.use_consumable(self.selected_item_index, target)
                if success:
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    logger.info(f"{item_name} 사용 완료 (아군 전체)")
                    # 인덱스 조정
                    if self.cursor >= len(self.inventory):
                        self.cursor = max(0, len(self.inventory) - 1)
                
                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.selected_item_index = None
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소: 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.selected_item_index = None
            return False
        
        # 일반 소비품/장비는 기존처럼 타겟 선택
        if action == GameAction.MOVE_UP:
            self.target_cursor = max(0, self.target_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.target_cursor = min(len(self.party) - 1, self.target_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 대상에게 사용/장착
            target = self.party[self.target_cursor]
            item = self.inventory.get_item(self.selected_item_index)

            # CookedFood 타입 확인
            from src.cooking.recipe import CookedFood

            if isinstance(item, (Consumable, CookedFood)):
                # 소비 아이템 또는 요리 사용
                success = self.inventory.use_consumable(self.selected_item_index, target)
                if success:
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    logger.info(f"{item_name} 사용 완료")
                    # 인덱스 조정
                    if self.cursor >= len(self.inventory):
                        self.cursor = max(0, len(self.inventory) - 1)
            elif isinstance(item, Equipment):
                # 장비 착용
                self._equip_item(target, item)

            # 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None

        return False

    def _handle_target_select(self, action: GameAction) -> bool:
        """대상 선택 모드 입력"""
        # USE_ITEM과 동일
        return self._handle_use_or_equip(action)

    def _handle_character_equipment(self, action: GameAction) -> bool:
        """캐릭터 장비 보기 모드"""
        if action == GameAction.MOVE_UP:
            self.target_cursor = max(0, self.target_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.target_cursor = min(len(self.party) - 1, self.target_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 캐릭터 선택 → 장비 해제 모드로
            self.selected_character_index = self.target_cursor
            self.mode = InventoryMode.UNEQUIP
            self.equipment_cursor = 0
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.mode = InventoryMode.BROWSE
            self.selected_character_index = None

        return False

    def _handle_unequip(self, action: GameAction) -> bool:
        """장비 해제 모드"""
        if action == GameAction.MOVE_UP:
            self.equipment_cursor = max(0, self.equipment_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.equipment_cursor = min(len(self.equipment_slots) - 1, self.equipment_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 장비 해제
            character = self.party[self.selected_character_index]
            slot = self.equipment_slots[self.equipment_cursor]

            # 장비가 있는지 확인
            if character.equipment.get(slot):
                item = character.unequip_item(slot)
                if item:
                    # 인벤토리에 추가
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    char_name = getattr(character, 'name', '알 수 없는 캐릭터')
                    if self.inventory.add_item(item):
                        logger.info(f"{char_name}: {item_name} 해제 → 인벤토리")
                    else:
                        # 인벤토리 가득 참 - 다시 장착
                        character.equip_item(slot, item)
                        logger.warning(f"인벤토리 가득 참! {item_name} 해제 실패")
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 캐릭터 선택 모드로 복귀
            self.mode = InventoryMode.CHARACTER_EQUIPMENT
            self.selected_character_index = None

        return False

    def _handle_confirm_destroy(self, action: GameAction) -> bool:
        """아이템 파괴 확인"""
        item = self.inventory.get_item(self.confirm_destroy_item) if self.confirm_destroy_item is not None else None
        if not item:
            self.mode = InventoryMode.BROWSE
            return False
        
        # 스택 가능 여부 확인
        from src.gathering.ingredient import Ingredient
        from src.cooking.recipe import CookedFood
        is_stackable = not isinstance(item, Equipment)
        slot = self.inventory.slots[self.confirm_destroy_item] if self.confirm_destroy_item < len(self.inventory.slots) else None
        max_quantity = slot.quantity if slot else 1
        
        # 개수 입력 모드
        if self.destroy_quantity_input_mode and is_stackable:
            if action == GameAction.MOVE_UP:
                self.destroy_quantity = min(max_quantity, self.destroy_quantity + 1)
            elif action == GameAction.MOVE_DOWN:
                self.destroy_quantity = max(1, self.destroy_quantity - 1)
            elif action == GameAction.MOVE_LEFT:
                self.destroy_quantity = max(1, self.destroy_quantity - 10)
            elif action == GameAction.MOVE_RIGHT:
                self.destroy_quantity = min(max_quantity, self.destroy_quantity + 10)
            elif action == GameAction.CONFIRM:
                # 개수 입력 완료 - 파괴 실행
                destroy_qty = self.destroy_quantity
                self.inventory.remove_item(self.confirm_destroy_item, destroy_qty)
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                logger.info(f"{item_name} {destroy_qty}개 파괴됨")

                # 커서 조정
                if self.cursor >= len(self.inventory) and len(self.inventory) > 0:
                    self.cursor = max(0, len(self.inventory) - 1)
                elif len(self.inventory) == 0:
                    self.cursor = 0

                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.confirm_destroy_item = None
                self.destroy_quantity = 1
                self.destroy_quantity_input_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 개수 입력 취소
                self.destroy_quantity_input_mode = False
                self.destroy_quantity = 1
            return False
        
        # 일반 확인 모드
        if action == GameAction.MOVE_LEFT:
            self.confirm_yes = True
        elif action == GameAction.MOVE_RIGHT:
            self.confirm_yes = False
        elif action == GameAction.CONFIRM:
            if self.confirm_yes:
                # 스택형 아이템이고 개수 입력이 필요하면 개수 입력 모드로
                if is_stackable and max_quantity > 1:
                    self.destroy_quantity_input_mode = True
                    self.destroy_quantity = min(max_quantity, self.destroy_quantity)
                    return False
                
                # 파괴 실행 (비스택형이거나 1개만 있는 경우)
                destroy_qty = 1
                self.inventory.remove_item(self.confirm_destroy_item, destroy_qty)
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                logger.info(f"{item_name} 파괴됨")

                # 커서 조정
                if self.cursor >= len(self.inventory) and len(self.inventory) > 0:
                    self.cursor = max(0, len(self.inventory) - 1)
                elif len(self.inventory) == 0:
                    self.cursor = 0

                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.confirm_destroy_item = None
                self.destroy_quantity = 1
                self.destroy_quantity_input_mode = False
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.mode = InventoryMode.BROWSE
            self.confirm_destroy_item = None
            self.destroy_quantity = 1
            self.destroy_quantity_input_mode = False

        return False

    def _handle_drop_item(self, action: GameAction) -> bool:
        """아이템 드롭 모드 입력"""
        if self.drop_item_index is None or not self.exploration:
            self.mode = InventoryMode.BROWSE
            return False
        
        item = self.inventory.get_item(self.drop_item_index)
        if not item:
            self.mode = InventoryMode.BROWSE
            return False
        
        # 스택 가능 여부 확인
        slot = self.inventory.slots[self.drop_item_index]
        is_stackable = slot.quantity > 1
        max_quantity = slot.quantity
        
        # 개수 입력 모드
        if self.drop_quantity_input_mode:
            if action == GameAction.MOVE_UP:
                self.drop_quantity = min(max_quantity, self.drop_quantity + 1)
            elif action == GameAction.MOVE_DOWN:
                self.drop_quantity = max(1, self.drop_quantity - 1)
            elif action == GameAction.MOVE_LEFT:
                self.drop_quantity = max(1, self.drop_quantity - 10)
            elif action == GameAction.MOVE_RIGHT:
                self.drop_quantity = min(max_quantity, self.drop_quantity + 10)
            elif action == GameAction.CONFIRM:
                # 드롭 실행
                drop_qty = self.drop_quantity
                dropped_item = self.inventory.remove_item(self.drop_item_index, drop_qty)
                if dropped_item:
                    # 플레이어 위치에 아이템 드롭
                    player_x = self.exploration.player.x
                    player_y = self.exploration.player.y
                    tile = self.exploration.dungeon.get_tile(player_x, player_y)
                    if tile:
                        from src.world.tile import TileType
                    tile.tile_type = TileType.DROPPED_ITEM
                    tile.dropped_item = dropped_item
                    item_name = getattr(dropped_item, 'name', '알 수 없는 아이템')
                    
                    # 멀티플레이어: 드롭한 플레이어 ID 설정
                    dropped_by_player_id = None
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'local_player_id'):
                            dropped_by_player_id = self.exploration.local_player_id
                        elif hasattr(self.exploration, 'session') and self.exploration.session:
                            dropped_by_player_id = getattr(self.exploration.session, 'local_player_id', None)
                    tile.dropped_by_player_id = dropped_by_player_id
                    
                    logger.info(f"{item_name} {drop_qty}개 드롭됨 ({player_x}, {player_y}) by {dropped_by_player_id}")
                    
                    # 멀티플레이어: 드롭 동기화
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'network_manager') and self.exploration.network_manager:
                            from src.multiplayer.protocol import MessageBuilder
                            import asyncio
                            try:
                                # 아이템 데이터 직렬화
                                item_data = {
                                    "name": item_name,
                                    "item_id": getattr(dropped_item, 'item_id', None),
                                    "item_type": getattr(dropped_item, 'item_type', None).value if hasattr(getattr(dropped_item, 'item_type', None), 'value') else str(getattr(dropped_item, 'item_type', None)),
                                }
                                drop_msg = MessageBuilder.item_dropped(player_x, player_y, item_data, dropped_by_player_id)
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    asyncio.create_task(self.exploration.network_manager.broadcast(drop_msg))
                                else:
                                    loop.run_until_complete(self.exploration.network_manager.broadcast(drop_msg))
                                logger.debug(f"아이템 드롭 동기화 메시지 전송: ({player_x}, {player_y})")
                            except Exception as e:
                                logger.error(f"아이템 드롭 동기화 메시지 전송 실패: {e}", exc_info=True)
                
                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.drop_item_index = None
                self.drop_quantity = 1
                self.drop_quantity_input_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.drop_quantity_input_mode = False
                self.drop_quantity = 1
            return False
        
        # 일반 확인 모드
        if is_stackable and max_quantity > 1:
            # 개수 입력 모드로 전환
            self.drop_quantity_input_mode = True
            self.drop_quantity = 1
        else:
            # 바로 드롭
            dropped_item = self.inventory.remove_item(self.drop_item_index, 1)
            if dropped_item:
                player_x = self.exploration.player.x
                player_y = self.exploration.player.y
                tile = self.exploration.dungeon.get_tile(player_x, player_y)
                if tile:
                    from src.world.tile import TileType
                    tile.tile_type = TileType.DROPPED_ITEM
                    tile.dropped_item = dropped_item
                    item_name = getattr(dropped_item, 'name', '알 수 없는 아이템')
                    logger.info(f"{item_name} 드롭됨 ({player_x}, {player_y})")
                    
                    # 멀티플레이어: 드롭 동기화
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'network_manager') and self.exploration.network_manager:
                            from src.multiplayer.protocol import MessageBuilder
                            import asyncio
                            try:
                                # 아이템 데이터 직렬화
                                item_data = {
                                    "name": item_name,
                                    "item_id": getattr(dropped_item, 'item_id', None),
                                    "item_type": getattr(dropped_item, 'item_type', None).value if hasattr(getattr(dropped_item, 'item_type', None), 'value') else str(getattr(dropped_item, 'item_type', None)),
                                }
                                drop_msg = MessageBuilder.item_dropped(player_x, player_y, item_data)
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    asyncio.create_task(self.exploration.network_manager.broadcast(drop_msg))
                                else:
                                    loop.run_until_complete(self.exploration.network_manager.broadcast(drop_msg))
                                logger.debug(f"아이템 드롭 동기화 메시지 전송: ({player_x}, {player_y})")
                            except Exception as e:
                                logger.error(f"아이템 드롭 동기화 메시지 전송 실패: {e}", exc_info=True)
            
            # 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.drop_item_index = None
            self.drop_quantity = 1
        
        if action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.mode = InventoryMode.BROWSE
            self.drop_item_index = None
            self.drop_quantity = 1
            self.drop_quantity_input_mode = False
        
        return False

    def _handle_drop_gold(self, action: GameAction) -> bool:
        """골드 드롭 모드 입력"""
        if not self.exploration:
            self.mode = InventoryMode.BROWSE
            return False
        
        max_gold = self.inventory.gold
        
        # 골드 입력 모드
        if self.drop_gold_input_mode:
            if action == GameAction.MOVE_UP:
                self.drop_gold_amount = min(max_gold, self.drop_gold_amount + 1)
            elif action == GameAction.MOVE_DOWN:
                self.drop_gold_amount = max(0, self.drop_gold_amount - 1)
            elif action == GameAction.MOVE_LEFT:
                self.drop_gold_amount = max(0, self.drop_gold_amount - 10)
            elif action == GameAction.MOVE_RIGHT:
                self.drop_gold_amount = min(max_gold, self.drop_gold_amount + 10)
            elif action == GameAction.CONFIRM:
                # 골드 드롭 실행
                if self.drop_gold_amount > 0 and self.drop_gold_amount <= max_gold:
                    self.inventory.gold -= self.drop_gold_amount
                    # 플레이어 위치에 골드 드롭
                    player_x = self.exploration.player.x
                    player_y = self.exploration.player.y
                    tile = self.exploration.dungeon.get_tile(player_x, player_y)
                    if tile:
                        from src.world.tile import TileType
                        tile.tile_type = TileType.GOLD
                        tile.gold_amount = self.drop_gold_amount
                        
                        # 멀티플레이어: 드롭한 플레이어 ID 설정
                        dropped_by_player_id = None
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'local_player_id'):
                                dropped_by_player_id = self.exploration.local_player_id
                            elif hasattr(self.exploration, 'session') and self.exploration.session:
                                dropped_by_player_id = getattr(self.exploration.session, 'local_player_id', None)
                        tile.dropped_by_player_id = dropped_by_player_id
                        
                        logger.info(f"골드 {self.drop_gold_amount}G 드롭됨 ({player_x}, {player_y}) by {dropped_by_player_id}")
                        
                        # 멀티플레이어: 골드 드롭 동기화
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'network_manager') and self.exploration.network_manager:
                                from src.multiplayer.protocol import MessageBuilder
                                import asyncio
                                try:
                                    gold_msg = MessageBuilder.gold_dropped(player_x, player_y, self.drop_gold_amount, dropped_by_player_id)
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        asyncio.create_task(self.exploration.network_manager.broadcast(gold_msg))
                                    else:
                                        loop.run_until_complete(self.exploration.network_manager.broadcast(gold_msg))
                                    logger.debug(f"골드 드롭 동기화 메시지 전송: ({player_x}, {player_y}) {self.drop_gold_amount}G")
                                except Exception as e:
                                    logger.error(f"골드 드롭 동기화 메시지 전송 실패: {e}", exc_info=True)
                
                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.drop_gold_amount = 0
                self.drop_gold_input_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.mode = InventoryMode.BROWSE
                self.drop_gold_amount = 0
                self.drop_gold_input_mode = False
            return False
        
        return False

    def _handle_sort_menu(self, action: GameAction) -> bool:
        """정렬 메뉴 처리"""
        if action == GameAction.MOVE_UP:
            if self.sort_menu:
                self.sort_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            if self.sort_menu:
                self.sort_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            if self.sort_menu:
                selected = self.sort_menu.get_selected_item()
                if selected:
                    sort_type = selected.data
                    if sort_type == "rarity":
                        self.inventory.sort_by_rarity()
                        logger.info("인벤토리 정렬: 등급순")
                    elif sort_type == "type":
                        self.inventory.sort_by_type()
                        logger.info("인벤토리 정렬: 타입순")
                    elif sort_type == "name":
                        self.inventory.sort_by_name()
                        logger.info("인벤토리 정렬: 이름순")

                    # 커서 초기화
                    self.cursor = 0
                    self.scroll_offset = 0

                self.sort_menu = None
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.sort_menu = None

        return False

    def _update_scroll(self):
        """스크롤 업데이트"""
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.cursor - self.max_visible + 1

    def _get_filtered_item_count(self) -> int:
        """필터링된 아이템 수 반환"""
        count = 0
        from src.cooking.recipe import CookedFood
        for slot in self.inventory.slots:
            # CookedFood는 소비품으로 취급
            if isinstance(slot.item, CookedFood):
                current_type = ItemType.CONSUMABLE
            else:
                current_type = getattr(slot.item, 'item_type', ItemType.CONSUMABLE)

            if self.filter_type is None or current_type == self.filter_type:
                count += 1
        return count

    def _get_actual_slot_index(self, filtered_index: int) -> int:
        """필터링된 인덱스를 원래 인벤토리 인덱스로 변환"""
        visible_items = []
        from src.cooking.recipe import CookedFood
        for i, slot in enumerate(self.inventory.slots):
            # CookedFood는 소비품으로 취급
            if isinstance(slot.item, CookedFood):
                current_type = ItemType.CONSUMABLE
            else:
                current_type = getattr(slot.item, 'item_type', ItemType.CONSUMABLE)

            if self.filter_type is None or current_type == self.filter_type:
                visible_items.append(i)

        if 0 <= filtered_index < len(visible_items):
            return visible_items[filtered_index]
        return filtered_index  # 범위 밖이면 그대로 반환

    def _change_filter(self, direction: int):
        """필터 변경"""
        filters = [None, ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY, ItemType.CONSUMABLE]

        if self.filter_type is None:
            current_idx = 0
        else:
            current_idx = filters.index(self.filter_type)

        new_idx = (current_idx + direction) % len(filters)
        self.filter_type = filters[new_idx]

        # 커서 초기화 및 스크롤 업데이트
        self.cursor = 0
        self.scroll_offset = 0
        self._update_scroll()  # 화면 스크롤 업데이트

        logger.debug(f"필터 변경: {self.filter_type}")

    def _open_sort_menu(self):
        """정렬 메뉴 열기"""
        items = [
            MenuItem(text="등급순", description="전설 → 일반", enabled=True, value="rarity"),
            MenuItem(text="타입순", description="무기 → 소비품", enabled=True, value="type"),
            MenuItem(text="이름순", description="가나다순", enabled=True, value="name"),
        ]

        self.sort_menu = CursorMenu(
            title="정렬",
            items=items,
            x=30,
            y=15,
            width=25
        )

    def _equip_item(self, character: Any, item: Equipment):
        """장비 착용"""
        # 레벨 제한 체크
        char_level = getattr(character, 'level', 1)
        item_level_req = getattr(item, 'level_requirement', 1)
        
        if item_level_req > char_level:
            char_name = getattr(character, 'name', '알 수 없는 캐릭터')
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            logger.warning(f"{char_name}은(는) 레벨 {item_level_req} 이상이어야 {item_name}을(를) 장착할 수 있습니다. (현재 레벨: {char_level})")
            return  # 레벨 부족으로 장착 실패

        # 장비 슬롯 결정 (안전하게 처리)
        equip_slot = getattr(item, 'equip_slot', None)
        if equip_slot and hasattr(equip_slot, 'value'):
            slot_name = equip_slot.value  # "weapon", "armor", "accessory"
        else:
            # equip_slot이 없으면 item_type에 따라 결정
            from src.equipment.item_system import ItemType
            item_type = getattr(item, 'item_type', None)
            if item_type == ItemType.WEAPON:
                slot_name = "weapon"
            elif item_type == ItemType.ARMOR:
                slot_name = "armor"
            elif item_type == ItemType.ACCESSORY:
                slot_name = "accessory"
            else:
                # 기본값으로 weapon 사용
                slot_name = "weapon"
                logger.warning(f"아이템 {getattr(item, 'name', '알 수 없는 아이템')}의 equip_slot을 확인할 수 없어 weapon 슬롯으로 설정합니다.")
        
        # 슬롯 이름 검증
        if slot_name not in ["weapon", "armor", "accessory"]:
            logger.error(f"잘못된 장비 슬롯: {slot_name} (아이템: {getattr(item, 'name', '알 수 없는 아이템')})")
            return

        # 캐릭터 이름 미리 가져오기
        char_name = getattr(character, 'name', '알 수 없는 캐릭터')

        # 기존 장비 해제
        old_item = character.equipment.get(slot_name)
        if old_item:
            # 인벤토리에 되돌림
            self.inventory.add_item(old_item)
            old_item_name = getattr(old_item, 'name', '알 수 없는 아이템')
            logger.info(f"{char_name}: {old_item_name} 해제")

        # 새 장비 착용
        character.equip_item(slot_name, item)
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        logger.info(f"{char_name}: {item_name} 착용")

        # 인벤토리에서 제거
        self.inventory.remove_item(self.selected_item_index)

    def render(self, console: tcod.console.Console):
        """인벤토리 화면 렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목
        title = "인벤토리"
        console.print(
            (self.screen_width - len(title)) // 2,
            1,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 골드
        gold_text = f"골드: {self.inventory.gold}G"
        console.print(
            self.screen_width - len(gold_text) - 2,
            1,
            gold_text,
            fg=(255, 215, 0)
        )

        # 필터 표시
        filter_text = "전체"
        if self.filter_type == ItemType.WEAPON:
            filter_text = "무기"
        elif self.filter_type == ItemType.ARMOR:
            filter_text = "방어구"
        elif self.filter_type == ItemType.ACCESSORY:
            filter_text = "악세서리"
        elif self.filter_type == ItemType.CONSUMABLE:
            filter_text = "소비품"

        console.print(
            5,
            3,
            f"필터: {filter_text} (← →)",
            fg=Colors.GRAY
        )

        # 무게 정보
        current = self.inventory.current_weight
        maximum = self.inventory.max_weight
        weight_percent = (current / maximum * 100) if maximum > 0 else 0

        weight_color = Colors.UI_TEXT
        if weight_percent >= 90:
            weight_color = (255, 100, 100)  # 빨강 (거의 가득)
        elif weight_percent >= 70:
            weight_color = (255, 255, 100)  # 노랑 (많이 참)

        console.print(
            self.screen_width - 30,
            3,
            f"무게: {current}kg/{maximum}kg ({int(weight_percent)}%)",
            fg=weight_color
        )

        # 무게 제한 세부 내역 (작게 표시)
        if hasattr(self.inventory, 'weight_breakdown'):
            breakdown = self.inventory.weight_breakdown
            detail_text = (
                f"기본{int(breakdown['base'])} "
                f"+파티{int(breakdown['party_count'])} "
                f"+힘{int(breakdown['strength_bonus'])} "
                f"+Lv{int(breakdown['level_bonus'])}"
            )
            console.print(
                self.screen_width - 30,
                4,
                detail_text,
                fg=Colors.DARK_GRAY
            )

        # 아이템 목록
        y = 5
        console.print(5, y, "─" * 70, fg=Colors.UI_BORDER)
        y += 1

        # 필터링
        visible_items = []
        from src.cooking.recipe import CookedFood
        for i, slot in enumerate(self.inventory.slots):
            # CookedFood는 소비품으로 취급
            if isinstance(slot.item, CookedFood):
                current_type = ItemType.CONSUMABLE
            else:
                # 안전하게 item_type 속성 접근 (기본값 CONSUMABLE)
                current_type = getattr(slot.item, 'item_type', ItemType.CONSUMABLE)

            if self.filter_type is None or current_type == self.filter_type:
                visible_items.append((i, slot))

        # 스크롤된 아이템 표시
        for idx, (slot_idx, slot) in enumerate(visible_items[self.scroll_offset:self.scroll_offset + self.max_visible]):
            item = slot.item
            # 필터링된 리스트의 인덱스로 선택 확인
            filtered_idx = self.scroll_offset + idx
            is_selected = (self.cursor == filtered_idx and self.mode == InventoryMode.BROWSE)

            # 선택 표시
            prefix = "►" if is_selected else " "

            # 아이템 이름 (등급 색상) - 안전하게 rarity 접근
            item_rarity = getattr(item, 'rarity', None)
            if item_rarity:
                rarity_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
            else:
                rarity_color = Colors.UI_TEXT
            item_name = getattr(item, 'name', '알 수 없는 아이템')

            # 수량 표시 (스택형 아이템은 항상 표시, 1개일 때도 표시)
            from src.gathering.ingredient import Ingredient
            from src.cooking.recipe import CookedFood
            is_stackable = not isinstance(item, Equipment)
            if is_stackable:
                item_name += f" x{slot.quantity}"

            # 레벨 요구사항
            if hasattr(item, 'level_requirement') and item.level_requirement > 1:
                item_name += f" (Lv.{item.level_requirement})"

            console.print(
                5,
                y,
                f"{prefix} {item_name}",
                fg=rarity_color if is_selected else Colors.UI_TEXT
            )

            y += 1

        # 스크롤 표시
        if len(visible_items) > self.max_visible:
            scroll_info = f"(↑↓: {self.scroll_offset + 1}-{min(self.scroll_offset + self.max_visible, len(visible_items))} / {len(visible_items)})"
            console.print(5, y, scroll_info, fg=Colors.DARK_GRAY)
            y += 1

        # 아이템 상세 정보
        y += 1
        if len(self.inventory) > 0:
            item = self.inventory.get_item(self.cursor)
            if item:
                self._render_item_details(console, item, 5, y)

        # 대상 선택 모드
        if self.mode in [InventoryMode.USE_ITEM, InventoryMode.EQUIP]:
            self._render_target_selection(console)

        # 캐릭터 장비 보기 모드
        if self.mode == InventoryMode.CHARACTER_EQUIPMENT:
            self._render_character_selection(console, "장비 보기")

        # 장비 해제 모드
        if self.mode == InventoryMode.UNEQUIP:
            self._render_equipment_unequip(console)

        # 파괴 확인 모드
        if self.mode == InventoryMode.CONFIRM_DESTROY:
            self._render_destroy_confirm(console)

        # 드롭 모드
        if self.mode == InventoryMode.DROP_ITEM:
            self._render_drop_item(console)
        elif self.mode == InventoryMode.DROP_GOLD:
            self._render_drop_gold(console)

        # 정렬 메뉴
        if self.sort_menu:
            self.sort_menu.render(console)

        # 장비 비교 (BROWSE 모드에서만)
        if self.mode == InventoryMode.BROWSE and self.show_comparison and len(self.inventory) > 0:
            item = self.inventory.get_item(self.cursor)
            if item and isinstance(item, Equipment):
                self._render_equipment_comparison(console, item)

        # 도움말
        help_y = self.screen_height - 2
        if self.mode == InventoryMode.BROWSE:
            help_text = "F: 먹기  Z: 사용/비교  C: 캐릭터 장비  V: 파괴  D: 드롭  G: 골드드롭  M: 정렬  ←→: 필터  X: 닫기"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.CHARACTER_EQUIPMENT:
            help_text = "↑↓: 캐릭터 선택  Z: 확인  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.UNEQUIP:
            help_text = "↑↓: 장비 슬롯 선택  Z: 해제  X: 뒤로"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.CONFIRM_DESTROY:
            # 개수 입력 모드인지 확인
            if self.destroy_quantity_input_mode:
                help_text = "↑↓: ±1  ←→: ±10  Z: 확인  X: 취소"
            else:
                help_text = "←→: 선택  Z: 확인/개수선택  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.DROP_ITEM:
            if self.drop_quantity_input_mode:
                help_text = "↑↓: ±1  ←→: ±10  Z: 드롭  X: 취소"
            else:
                help_text = "Z: 드롭  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.DROP_GOLD:
            if self.drop_gold_input_mode:
                help_text = f"↑↓: ±1  ←→: ±10  Z: 드롭 ({self.drop_gold_amount}G)  X: 취소"
            else:
                help_text = "골드 액수 입력 중..."
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode in [InventoryMode.USE_ITEM, InventoryMode.EQUIP]:
            help_text = "↑↓: 대상 선택  Z: 확인  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)

    def _render_item_details(self, console: tcod.console.Console, item: Item, x: int, y: int):
        """아이템 상세 정보 렌더링"""
        console.print(x, y, "─" * 70, fg=Colors.UI_BORDER)
        y += 1

        # 이름 + 등급 (안전하게 rarity 접근)
        item_rarity = getattr(item, 'rarity', None)
        if item_rarity:
            rarity_name = getattr(item_rarity, 'display_name', '일반')
            rarity_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
        else:
            rarity_name = '일반'
            rarity_color = Colors.UI_TEXT

        item_name = getattr(item, 'name', '알 수 없는 아이템')
        console.print(
            x,
            y,
            f"{item_name} [{rarity_name}]",
            fg=rarity_color
        )
        y += 1

        # 설명
        console.print(x, y, item.description, fg=Colors.DARK_GRAY)
        y += 1

        # 무게
        console.print(x, y, f"무게: {item.weight}kg", fg=Colors.DARK_GRAY)
        y += 1

        # 장비 정보
        if isinstance(item, Equipment):
            y += 1
            console.print(x, y, "기본 스탯:", fg=Colors.UI_TEXT)
            y += 1

            # 스탯 이름 한글 매핑
            stat_names = {
                "hp": "HP",
                "mp": "MP",
                "physical_attack": "물리 공격력",
                "physical_defense": "물리 방어력",
                "magic_attack": "마법 공격력",
                "magic_defense": "마법 방어력",
                "speed": "속도",
                "accuracy": "명중률",
                "evasion": "회피율",
                "luck": "행운",
                "strength": "힘",
                "defense": "방어력",
                "magic": "마력",
                "spirit": "정신력",
                "init_brv": "초기 BRV",
                "max_brv": "최대 BRV",
            }
            
            for stat_name, value in item.base_stats.items():
                if value != 0:
                    display_stat = stat_names.get(stat_name, stat_name.upper())
                    console.print(x + 2, y, f"{display_stat}: +{int(value)}", fg=rarity_color)
                    y += 1

            # unique_effect에서 재생 스탯 등 추출하여 표시
            if hasattr(item, 'unique_effect') and item.unique_effect:
                # unique_effect 파싱 (간단한 파싱)
                unique_stats = {}
                for effect_str in item.unique_effect.split("|"):
                    if ":" in effect_str:
                        effect_name, value_str = effect_str.split(":", 1)
                        effect_name = effect_name.strip()
                        try:
                            value = float(value_str.strip())
                            # 재생 스탯 등 기본 스탯 섹션에 표시할 효과들
                            if effect_name == "mp_regen":
                                unique_stats["MP 재생"] = int(value)
                            elif effect_name == "hp_regen":
                                # 퍼센트일 수 있음 (0.05 = 5%)
                                if value < 1:
                                    unique_stats["HP 재생"] = f"{int(value * 100)}%"
                                else:
                                    unique_stats["HP 재생"] = int(value)
                            elif effect_name == "wound_regen":
                                unique_stats["상처 회복"] = int(value)
                        except ValueError:
                            pass
                
                # 추출한 스탯 표시
                for stat_name, value in unique_stats.items():
                    console.print(x + 2, y, f"{stat_name}: +{value}", fg=rarity_color)
                    y += 1

            # 접사
            if item.affixes:
                y += 1
                console.print(x, y, "추가 효과:", fg=Colors.UI_TEXT_SELECTED)
                y += 1

                for affix in item.affixes:
                    # get_description() 메서드를 사용하여 올바른 형식으로 표시
                    affix_desc = affix.get_description()
                    console.print(x + 2, y, affix_desc, fg=(150, 255, 150))
                    y += 1

            # 유니크 효과
            if hasattr(item, 'unique_effect') and item.unique_effect:
                y += 1
                console.print(x, y, f"유니크: {item.unique_effect}", fg=(255, 100, 255))

        # 소비품 정보
        elif isinstance(item, Consumable):
            y += 1
            effect_desc = {
                "heal_hp": f"HP {item.effect_value} 회복",
                "heal_mp": f"MP {item.effect_value} 회복",
                "heal_both": f"HP/MP {item.effect_value} 회복",
                "revive": f"HP {item.effect_value}로 부활",
                "cure_status": "모든 상태이상 치료"
            }

            desc = effect_desc.get(item.effect_type, "효과 불명")
            console.print(x, y, f"효과: {desc}", fg=Colors.UI_TEXT)
        
        # 요리 음식 정보 (CookedFood)
        else:
            from src.cooking.recipe import CookedFood
            if isinstance(item, CookedFood):
                y += 1
                console.print(x, y, "효과 (아군 전체 적용):", fg=Colors.UI_TEXT_SELECTED)
                y += 1
                
                # HP 회복
                hp_restore = getattr(item, 'hp_restore', 0)
                if hp_restore > 0:
                    console.print(x + 2, y, f"HP +{hp_restore} 회복", fg=(100, 255, 100))
                    y += 1
                
                # MP 회복
                mp_restore = getattr(item, 'mp_restore', 0)
                if mp_restore > 0:
                    console.print(x + 2, y, f"MP +{mp_restore} 회복", fg=(100, 200, 255))
                    y += 1
                
                # 최대 HP 보너스
                max_hp_bonus = getattr(item, 'max_hp_bonus', 0)
                if max_hp_bonus > 0:
                    console.print(x + 2, y, f"최대 HP +{max_hp_bonus} (일시적)", fg=(255, 200, 100))
                    y += 1
                
                # 최대 MP 보너스
                max_mp_bonus = getattr(item, 'max_mp_bonus', 0)
                if max_mp_bonus > 0:
                    console.print(x + 2, y, f"최대 MP +{max_mp_bonus} (일시적)", fg=(200, 150, 255))
                    y += 1
                
                # 버프 정보
                buff_type = getattr(item, 'buff_type', None)
                buff_duration = getattr(item, 'buff_duration', 0)
                if buff_type and buff_duration > 0:
                    y += 1
                    console.print(x, y, "버프 효과:", fg=Colors.UI_TEXT_SELECTED)
                    y += 1
                    
                    # 버프 타입 한글 매핑
                    buff_names = {
                        "attack": "공격력",
                        "defense": "방어력",
                        "speed": "속도",
                        "magic": "마법 공격력"
                    }
                    buff_name = buff_names.get(buff_type, buff_type)
                    buff_value = 0.2  # 기본 20% (inventory.py에서 사용하는 값과 동일)
                    
                    console.print(
                        x + 2, y,
                        f"{buff_name} +{int(buff_value * 100)}% ({buff_duration}턴)",
                        fg=(255, 255, 100)
                    )
                    y += 1
                
                # 독 효과 (실패 요리)
                is_poison = getattr(item, 'is_poison', False)
                poison_damage = getattr(item, 'poison_damage', 0)
                if is_poison and poison_damage > 0:
                    y += 1
                    console.print(
                        x, y,
                        f"⚠ 독! 피해 {poison_damage}",
                        fg=(255, 100, 100)
                    )
                    y += 1

    def _render_target_selection(self, console: tcod.console.Console):
        """대상 선택 UI"""
        # 중앙에 대상 선택 창
        box_width = 40
        box_height = 10 + len(self.party)
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 박스
        console.draw_frame(
            box_x,
            box_y,
            box_width,
            box_height,
            "대상 선택",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 파티 멤버 목록
        y = box_y + 2
        for i, character in enumerate(self.party):
            is_selected = (i == self.target_cursor)
            prefix = "►" if is_selected else " "

            char_name = getattr(character, 'name', str(character))
            char_hp = getattr(character, 'current_hp', 0)
            char_max_hp = getattr(character, 'max_hp', 1)

            console.print(
                box_x + 2,
                y,
                f"{prefix} {char_name}",
                fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
            )

            console.print(
                box_x + 20,
                y,
                f"HP {char_hp}/{char_max_hp}",
                fg=Colors.GRAY
            )

            y += 1


    def _render_character_selection(self, console: tcod.console.Console, title: str):
        """캐릭터 선택 UI"""
        box_width = 50
        box_height = 10 + len(self.party)
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            title,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        y = box_y + 2
        for i, character in enumerate(self.party):
            is_selected = (i == self.target_cursor)
            prefix = "►" if is_selected else " "

            char_name = getattr(character, 'name', str(character))
            char_class = getattr(character, 'character_class', '???')
            char_level = getattr(character, 'level', 1)

            console.print(
                box_x + 2, y,
                f"{prefix} {char_name} (Lv.{char_level} {char_class})",
                fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
            )
            y += 1

    def _render_equipment_unequip(self, console: tcod.console.Console):
        """장비 해제 UI"""
        if self.selected_character_index is None:
            return

        character = self.party[self.selected_character_index]
        char_name = getattr(character, 'name', str(character))

        box_width = 60
        box_height = 18
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            f"{char_name}의 장비",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        y = box_y + 2
        slot_names = {
            "weapon": "무기",
            "armor": "방어구",
            "accessory": "악세서리"
        }

        for i, slot in enumerate(self.equipment_slots):
            is_selected = (i == self.equipment_cursor)
            prefix = "►" if is_selected else " "

            item = character.equipment.get(slot)
            if item:
                item_name = getattr(item, 'name', '???')
                rarity_color = getattr(getattr(item, 'rarity', None), 'color', Colors.UI_TEXT)
            else:
                item_name = "(없음)"
                rarity_color = Colors.DARK_GRAY

            console.print(
                box_x + 2, y,
                f"{prefix} {slot_names.get(slot, slot)}: ",
                fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
            )

            console.print(
                box_x + 15, y,
                item_name,
                fg=rarity_color
            )

            # 장비 스탯 표시
            if item and is_selected:
                y += 1
                if hasattr(item, 'base_stats'):
                    stat_texts = []
                    for stat_name, value in item.base_stats.items():
                        if value != 0:
                            stat_texts.append(f"{stat_name}+{value}")
                    if stat_texts:
                        console.print(
                            box_x + 4, y,
                            " ".join(stat_texts[:4]),  # 최대 4개
                            fg=Colors.GRAY
                        )
            y += 2

    def _render_drop_item(self, console: tcod.console.Console):
        """아이템 드롭 대화상자"""
        if self.drop_item_index is None:
            return
        
        item = self.inventory.get_item(self.drop_item_index)
        if not item:
            return
        
        slot = self.inventory.slots[self.drop_item_index]
        max_quantity = slot.quantity
        
        box_width = 50
        box_height = 8 if self.drop_quantity_input_mode else 6
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "아이템 드롭",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )
        
        y = box_y + 2
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        console.print(box_x + 2, y, f"{item_name}을(를) 드롭하시겠습니까?", fg=Colors.UI_TEXT)
        y += 1
        
        if self.drop_quantity_input_mode:
            console.print(box_x + 2, y, f"개수: {self.drop_quantity}/{max_quantity}", fg=Colors.UI_TEXT_SELECTED)
            y += 1
            console.print(box_x + 2, y, "↑↓: ±1  ←→: ±10", fg=Colors.GRAY)
        else:
            if max_quantity > 1:
                console.print(box_x + 2, y, "Z: 개수 선택", fg=Colors.GRAY)
            else:
                console.print(box_x + 2, y, "Z: 드롭", fg=Colors.GRAY)
    
    def _render_drop_gold(self, console: tcod.console.Console):
        """골드 드롭 대화상자"""
        max_gold = self.inventory.gold
        
        box_width = 50
        box_height = 8
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "골드 드롭",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )
        
        y = box_y + 2
        console.print(box_x + 2, y, f"보유 골드: {max_gold}G", fg=Colors.UI_TEXT)
        y += 1
        console.print(box_x + 2, y, f"드롭할 골드: {self.drop_gold_amount}G", fg=Colors.UI_TEXT_SELECTED)
        y += 1
        console.print(box_x + 2, y, "↑↓: ±1  ←→: ±10", fg=Colors.GRAY)
        y += 1
        console.print(box_x + 2, y, "Z: 드롭  X: 취소", fg=Colors.GRAY)

    def _render_destroy_confirm(self, console: tcod.console.Console):
        """파괴 확인 대화상자"""
        if self.confirm_destroy_item is None:
            return

        item = self.inventory.get_item(self.confirm_destroy_item)
        if not item:
            return

        # 스택 가능 여부 확인
        from src.gathering.ingredient import Ingredient
        from src.cooking.recipe import CookedFood
        is_stackable = not isinstance(item, Equipment)
        slot = self.inventory.slots[self.confirm_destroy_item] if self.confirm_destroy_item < len(self.inventory.slots) else None
        max_quantity = slot.quantity if slot else 1

        # 박스 크기 조정 (개수 입력 모드면 더 크게)
        if self.destroy_quantity_input_mode and is_stackable:
            box_height = 12
        else:
            box_height = 10

        box_width = 55
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "아이템 파괴",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 경고 메시지
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        
        # 개수 입력 모드
        if self.destroy_quantity_input_mode and is_stackable:
            msg = f"'{item_name}'을(를) 몇 개 파괴하시겠습니까?"
            console.print(
                box_x + (box_width - len(msg)) // 2,
                box_y + 3,
                msg,
                fg=(255, 100, 100)
            )
            
            # 개수 표시
            qty_msg = f"개수: {self.destroy_quantity} / {max_quantity}"
            console.print(
                box_x + (box_width - len(qty_msg)) // 2,
                box_y + 5,
                qty_msg,
                fg=Colors.UI_TEXT_SELECTED
            )
            
            # 조작법
            controls = "↑↓: ±1  ←→: ±10  Z: 확인  X: 취소"
            console.print(
                box_x + (box_width - len(controls)) // 2,
                box_y + 7,
                controls,
                fg=Colors.GRAY
            )
        else:
            if is_stackable and max_quantity > 1:
                msg = f"'{item_name}' (보유: {max_quantity}개)을(를) 파괴하시겠습니까?"
            else:
                msg = f"'{item_name}'을(를) 파괴하시겠습니까?"
            console.print(
                box_x + (box_width - len(msg)) // 2,
                box_y + 3,
                msg,
                fg=(255, 100, 100)
            )

            console.print(
                box_x + (box_width - 30) // 2,
                box_y + 4,
                "이 작업은 되돌릴 수 없습니다!",
                fg=Colors.GRAY
            )

            # 스택형 아이템이면 개수 선택 안내
            if is_stackable and max_quantity > 1:
                console.print(
                    box_x + (box_width - 25) // 2,
                    box_y + 5,
                    "Z: 개수 선택",
                    fg=Colors.GRAY
                )

            # YES / NO 버튼
            y = box_y + 7
            yes_color = Colors.UI_TEXT_SELECTED if self.confirm_yes else Colors.UI_TEXT
            no_color = Colors.UI_TEXT_SELECTED if not self.confirm_yes else Colors.UI_TEXT

            console.print(
                box_x + 15, y,
                "[ 예 ]" if self.confirm_yes else "  예  ",
                fg=yes_color
            )

            console.print(
                box_x + 30, y,
                "[아니오]" if not self.confirm_yes else " 아니오 ",
                fg=no_color
            )

    def _render_equipment_comparison(self, console: tcod.console.Console, new_item: Equipment):
        """장비 비교 UI"""
        box_width = 70
        box_height = 25
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "장비 비교",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        y = box_y + 2

        # 새 아이템 정보
        console.print(
            box_x + 2, y,
            "인벤토리 아이템:",
            fg=Colors.UI_TEXT_SELECTED
        )
        y += 1

        # 안전하게 rarity 접근
        new_item_name = getattr(new_item, 'name', '알 수 없는 아이템')
        new_item_rarity = getattr(new_item, 'rarity', None)
        if new_item_rarity:
            rarity_display = getattr(new_item_rarity, 'display_name', '일반')
            rarity_color = getattr(new_item_rarity, 'color', Colors.UI_TEXT)
        else:
            rarity_display = '일반'
            rarity_color = Colors.UI_TEXT

        item_name = f"{new_item_name} [{rarity_display}]"
        console.print(
            box_x + 4, y,
            item_name,
            fg=rarity_color
        )
        y += 2

        # 스탯 표시
        if hasattr(new_item, 'base_stats'):
            for stat_name, value in new_item.base_stats.items():
                if value != 0:
                    console.print(
                        box_x + 4, y,
                        f"{stat_name}: +{value}",
                        fg=Colors.UI_TEXT
                    )
                    y += 1

        y += 1

        # 각 캐릭터의 현재 장비와 비교
        console.print(
            box_x + 2, y,
            "파티 현재 장비:",
            fg=Colors.UI_TEXT_SELECTED
        )
        y += 1

        slot = new_item.equip_slot.value
        for character in self.party:
            char_name = getattr(character, 'name', '???')
            current_item = character.equipment.get(slot)

            if current_item:
                console.print(
                    box_x + 4, y,
                    f"{char_name}: {getattr(current_item, 'name', '???')}",
                    fg=Colors.UI_TEXT
                )
                y += 1

                # 스탯 차이 표시
                if hasattr(new_item, 'base_stats') and hasattr(current_item, 'base_stats'):
                    for stat_name in new_item.base_stats.keys():
                        new_val = new_item.base_stats.get(stat_name, 0)
                        old_val = current_item.base_stats.get(stat_name, 0)
                        diff = new_val - old_val

                        if diff != 0:
                            diff_color = (100, 255, 100) if diff > 0 else (255, 100, 100)
                            diff_text = f"+{diff}" if diff > 0 else str(diff)
                            console.print(
                                box_x + 6, y,
                                f"{stat_name}: {diff_text}",
                                fg=diff_color
                            )
                            y += 1
            else:
                console.print(
                    box_x + 4, y,
                    f"{char_name}: (없음)",
                    fg=Colors.DARK_GRAY
                )
                y += 1

            y += 1


def open_inventory(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory: Inventory,
    party: List[Any],
    exploration: Optional[Any] = None,
    on_update: Optional[Any] = None
) -> None:
    """
    인벤토리 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리
        party: 파티 멤버
        exploration: 탐험 시스템 (드롭 기능용)
        on_update: 매 프레임 호출할 업데이트 함수 (봇 등 백그라운드 로직용)
    """
    ui = InventoryUI(console.width, console.height, inventory, party, exploration)
    handler = InputHandler()

    logger.info("인벤토리 열기")

    while not ui.closed:
        # 백그라운드 업데이트 실행
        if on_update:
            on_update()

        # 렌더링
        ui.render(console)
        context.present(console)

        # 입력 처리 (논블로킹)
        for event in tcod.event.wait(timeout=0.05):
            action = handler.dispatch(event)

            if action:
                if ui.handle_input(action):
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                ui.closed = True
                return

    logger.info("인벤토리 닫기")
