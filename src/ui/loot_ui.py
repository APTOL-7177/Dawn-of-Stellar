"""
전리품 UI

전투 승리 후 아이템 획득 화면
- 좌/우 키로 전리품↔인벤토리 전환
- Z로 아이템 획득/파괴
- ESC로 닫기 (남은 아이템 파괴)
"""

import tcod.console
import tcod.event
from typing import List, Dict, Any, Optional
import time

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.equipment.inventory import Inventory
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("loot_ui")


class LootUI:
    """전리품 획득 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        loot_items: List[Any],
        inventory: Inventory,
        player_id: Optional[str] = None,
        network_manager: Optional[Any] = None,
        is_multiplayer: bool = False
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            loot_items: 전리품 아이템 리스트
            inventory: 플레이어 인벤토리
            player_id: 플레이어 ID (멀티플레이용)
            network_manager: 네트워크 매니저 (멀티플레이용)
            is_multiplayer: 멀티플레이 여부
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.loot_items = list(loot_items)  # 복사본 (수정 가능)
        self.inventory = inventory
        self.player_id = player_id
        self.network_manager = network_manager
        self.is_multiplayer = is_multiplayer

        # 현재 패널 (0: 전리품, 1: 인벤토리)
        self.current_panel = 0
        
        # 각 패널 선택 인덱스
        self.loot_index = 0
        self.inv_index = 0
        
        # 스크롤 오프셋
        self.loot_scroll = 0
        self.inv_scroll = 0
        self.max_visible = 12
        
        # 완료 여부
        self.completed = False
        
        # 교체 모드
        self.swap_mode = False
        self.swap_item = None  # 교체할 전리품

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리
        
        Returns:
            완료 여부
        """
        if action == GameAction.ESCAPE or action == GameAction.CANCEL:
            play_sfx("ui", "cursor_cancel")
            # 남은 아이템 파괴 (로그만 남김)
            if self.loot_items:
                logger.info(f"전리품 {len(self.loot_items)}개 파괴됨")
            self.completed = True
            return True
        
        # 좌/우 키로 패널 전환
        if action == GameAction.MOVE_LEFT:
            if self.swap_mode:
                # 교체 모드 취소
                self.swap_mode = False
                self.swap_item = None
                play_sfx("ui", "cursor_cancel")
            else:
                self.current_panel = 0
                play_sfx("ui", "cursor_move")
            return False
        
        if action == GameAction.MOVE_RIGHT:
            if not self.swap_mode:
                self.current_panel = 1
                play_sfx("ui", "cursor_move")
            return False
        
        # 상/하 키로 선택 이동
        if action == GameAction.MOVE_UP:
            if self.current_panel == 0:
                self._move_selection(-1, is_loot=True)
            else:
                self._move_selection(-1, is_loot=False)
            return False
        
        if action == GameAction.MOVE_DOWN:
            if self.current_panel == 0:
                self._move_selection(1, is_loot=True)
            else:
                self._move_selection(1, is_loot=False)
            return False
        
        # Z (확인) 키로 아이템 획득/교체/파괴
        if action == GameAction.CONFIRM:
            if self.current_panel == 0:
                # 전리품 패널에서 Z
                self._try_claim_item()
            else:
                # 인벤토리 패널에서 Z
                if self.swap_mode:
                    # 교체 모드: 선택한 인벤토리 아이템과 교체
                    self._perform_swap()
                else:
                    # 아이템 파괴
                    self._destroy_inventory_item()
            return False
        
        return False

    def _move_selection(self, delta: int, is_loot: bool):
        """선택 이동"""
        if is_loot:
            if not self.loot_items:
                return
            self.loot_index = max(0, min(len(self.loot_items) - 1, self.loot_index + delta))
            # 스크롤 조정
            if self.loot_index < self.loot_scroll:
                self.loot_scroll = self.loot_index
            elif self.loot_index >= self.loot_scroll + self.max_visible:
                self.loot_scroll = self.loot_index - self.max_visible + 1
        else:
            slots = self.inventory.slots
            if not slots:
                return
            self.inv_index = max(0, min(len(slots) - 1, self.inv_index + delta))
            # 스크롤 조정
            if self.inv_index < self.inv_scroll:
                self.inv_scroll = self.inv_index
            elif self.inv_index >= self.inv_scroll + self.max_visible:
                self.inv_scroll = self.inv_index - self.max_visible + 1
        
        play_sfx("ui", "cursor_move")

    def _try_claim_item(self):
        """전리품 획득 시도"""
        if not self.loot_items or self.loot_index >= len(self.loot_items):
            play_sfx("ui", "cursor_error")
            return
        
        item = self.loot_items[self.loot_index]
        item_weight = getattr(item, 'weight', 0.5)
        
        # 무게 체크
        if not self.inventory.can_add_item(item):
            # 무게 초과 - 교체 모드로 전환
            play_sfx("ui", "cursor_error")
            self.swap_mode = True
            self.swap_item = item
            self.current_panel = 1  # 인벤토리 패널로 전환
            logger.info(f"무게 초과: {item.name} ({item_weight}kg) - 교체 모드")
            return
        
        # 획득 성공
        self.inventory.add_item(item)
        self.loot_items.pop(self.loot_index)
        
        # 인덱스 조정
        if self.loot_index >= len(self.loot_items) and self.loot_index > 0:
            self.loot_index -= 1
        
        play_sfx("ui", "item_pickup")
        logger.info(f"아이템 획득: {item.name}")
        
        # 전리품이 모두 없어지면 완료
        if not self.loot_items:
            self.completed = True

    def _perform_swap(self):
        """아이템 교체 수행"""
        if not self.swap_item or not self.inventory.slots:
            play_sfx("ui", "cursor_error")
            return
        
        if self.inv_index >= len(self.inventory.slots):
            play_sfx("ui", "cursor_error")
            return
        
        # 인벤토리에서 아이템 제거
        removed_item = self.inventory.remove_item(self.inv_index)
        
        if removed_item:
            # 전리품 추가
            self.inventory.add_item(self.swap_item)
            
            # 전리품 리스트에서 제거
            if self.swap_item in self.loot_items:
                self.loot_items.remove(self.swap_item)
            
            # 제거된 아이템은 파괴됨
            logger.info(f"아이템 교체: {self.swap_item.name} ← {removed_item.name} (파괴)")
            play_sfx("ui", "item_pickup")
        
        # 교체 모드 종료
        self.swap_mode = False
        self.swap_item = None
        self.current_panel = 0
        
        # 인덱스 조정
        if self.loot_index >= len(self.loot_items) and self.loot_index > 0:
            self.loot_index -= 1
        
        # 전리품이 모두 없어지면 완료
        if not self.loot_items:
            self.completed = True

    def _destroy_inventory_item(self):
        """인벤토리 아이템 파괴"""
        if not self.inventory.slots or self.inv_index >= len(self.inventory.slots):
            play_sfx("ui", "cursor_error")
            return
        
        removed_item = self.inventory.remove_item(self.inv_index)
        if removed_item:
            logger.info(f"아이템 파괴: {removed_item.name}")
            play_sfx("ui", "item_destroy")
            
            # 인덱스 조정
            if self.inv_index >= len(self.inventory.slots) and self.inv_index > 0:
                self.inv_index -= 1

    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        if self.swap_mode:
            title = "⚠ 무게 초과! 교체할 아이템 선택 ⚠"
            title_color = (255, 100, 100)
        else:
            title = "💎 전리품 획득 💎"
            title_color = Colors.UI_TEXT_SELECTED
        
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=title_color
        )
        
        # 현재 무게 표시
        weight_text = f"가방: {self.inventory.current_weight:.1f}/{self.inventory.max_weight:.1f}kg"
        weight_color = (255, 100, 100) if self.inventory.current_weight >= self.inventory.max_weight * 0.9 else (200, 200, 200)
        console.print(
            self.screen_width - len(weight_text) - 3,
            2,
            weight_text,
            fg=weight_color
        )
        
        panel_width = (self.screen_width - 6) // 2
        left_x = 3
        right_x = left_x + panel_width + 2
        panel_top = 5
        panel_height = self.screen_height - 10
        
        # 왼쪽: 전리품 패널
        self._render_panel(
            console,
            left_x, panel_top, panel_width, panel_height,
            "전리품",
            self.loot_items,
            self.loot_index,
            self.loot_scroll,
            is_selected=(self.current_panel == 0 and not self.swap_mode)
        )
        
        # 오른쪽: 인벤토리 패널
        inv_items = [slot.item for slot in self.inventory.slots] if self.inventory.slots else []
        self._render_panel(
            console,
            right_x, panel_top, panel_width, panel_height,
            "인벤토리",
            inv_items,
            self.inv_index,
            self.inv_scroll,
            is_selected=(self.current_panel == 1 or self.swap_mode)
        )
        
        # 도움말
        if self.swap_mode:
            help_text = "◀▶ 취소 | ▲▼ 선택 | Z 교체 | ESC 닫기"
        else:
            help_text = "◀▶ 패널전환 | ▲▼ 선택 | Z 획득 | ESC 닫기"
        
        console.print(
            (self.screen_width - len(help_text)) // 2,
            self.screen_height - 3,
            help_text,
            fg=Colors.GRAY
        )

    def _render_panel(
        self,
        console: tcod.console.Console,
        x: int, y: int, width: int, height: int,
        title: str,
        items: List[Any],
        selected_index: int,
        scroll_offset: int,
        is_selected: bool
    ):
        """패널 렌더링"""
        # 테두리 색상
        border_color = Colors.UI_TEXT_SELECTED if is_selected else Colors.GRAY
        
        # 테두리
        for i in range(width):
            console.print(x + i, y, "─", fg=border_color)
            console.print(x + i, y + height - 1, "─", fg=border_color)
        for i in range(height):
            console.print(x, y + i, "│", fg=border_color)
            console.print(x + width - 1, y + i, "│", fg=border_color)
        console.print(x, y, "┌", fg=border_color)
        console.print(x + width - 1, y, "┐", fg=border_color)
        console.print(x, y + height - 1, "└", fg=border_color)
        console.print(x + width - 1, y + height - 1, "┘", fg=border_color)
        
        # 제목
        title_text = f" {title} ({len(items)}) "
        console.print(
            x + (width - len(title_text)) // 2,
            y,
            title_text,
            fg=border_color
        )
        
        # 아이템 리스트
        if not items:
            console.print(
                x + 2, y + 2,
                "(비어있음)",
                fg=Colors.DARK_GRAY
            )
            return
        
        visible_items = items[scroll_offset:scroll_offset + self.max_visible]
        for i, item in enumerate(visible_items):
            item_y = y + 2 + i
            actual_index = scroll_offset + i
            
            # 선택 표시
            if is_selected and actual_index == selected_index:
                prefix = "▶ "
                item_color = Colors.UI_TEXT_SELECTED
            else:
                prefix = "  "
                item_rarity = getattr(item, 'rarity', None)
                if item_rarity:
                    item_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
                else:
                    item_color = Colors.UI_TEXT
            
            # 아이템 이름
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            item_weight = getattr(item, 'weight', 0.5)
            
            # 이름 자르기
            max_name_len = width - 12
            if len(item_name) > max_name_len:
                item_name = item_name[:max_name_len-2] + ".."
            
            item_text = f"{prefix}{item_name} ({item_weight:.1f}kg)"
            console.print(x + 1, item_y, item_text[:width-2], fg=item_color)
        
        # 스크롤 표시
        if len(items) > self.max_visible:
            scroll_text = f"({scroll_offset + 1}-{min(scroll_offset + self.max_visible, len(items))}/{len(items)})"
            console.print(
                x + (width - len(scroll_text)) // 2,
                y + height - 2,
                scroll_text,
                fg=Colors.DARK_GRAY
            )


def show_loot_screen(
    console: tcod.console.Console,
    context: tcod.context.Context,
    loot_items: List[Any],
    inventory: Inventory,
    player_id: Optional[str] = None,
    network_manager: Optional[Any] = None,
    is_multiplayer: bool = False
) -> List[Any]:
    """
    전리품 획득 화면 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        loot_items: 전리품 아이템 리스트
        inventory: 플레이어 인벤토리
        player_id: 플레이어 ID (멀티플레이용)
        network_manager: 네트워크 매니저 (멀티플레이용)
        is_multiplayer: 멀티플레이 여부
        
    Returns:
        획득한 아이템 리스트
    """
    if not loot_items:
        logger.info("전리품 없음 - 전리품 화면 생략")
        return []
    
    ui = LootUI(
        console.width,
        console.height,
        loot_items,
        inventory,
        player_id,
        network_manager,
        is_multiplayer
    )
    
    logger.info(f"전리품 화면 표시: {len(loot_items)}개 아이템")
    
    import pygame
    
    # 입력 큐 비우기
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()
    
    time.sleep(0.1)
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()
    
    initial_item_count = len(loot_items)
    
    while not ui.completed:
        # 렌더링
        ui.render(console)
        context.present(console)
        
        # pygame 이벤트 업데이트
        try:
            pygame.event.pump()
        except:
            pass
        
        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                keyboard_processed = True
                ui.handle_input(action)
            
            if isinstance(event, tcod.event.Quit):
                ui.completed = True
                break
        
        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                ui.handle_input(gamepad_action)
        
        time.sleep(0.01)
    
    # 획득한 아이템 수 계산
    claimed_count = initial_item_count - len(ui.loot_items)
    logger.info(f"전리품 화면 종료: {claimed_count}개 획득, {len(ui.loot_items)}개 파괴")
    
    return []  # 이미 인벤토리에 추가됨

