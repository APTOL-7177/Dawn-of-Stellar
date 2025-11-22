"""
봇 인벤토리 UI
"""

import tcod
import tcod.event
from typing import Optional, Any

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger

logger = get_logger("bot_inventory_ui")

class BotInventoryUI:
    """봇 인벤토리 UI"""
    
    def __init__(self, bot: Any):
        self.bot = bot
        self.selected_index = 0
        self.scroll_offset = 0
        self.items_per_page = 15
        
    def render(self, console: tcod.console.Console):
        """렌더링"""
        width = 60
        height = 40
        x = (console.width - width) // 2
        y = (console.height - height) // 2
        
        # 프레임 그리기
        console.draw_frame(
            x, y, width, height,
            title=f" {self.bot.bot_name}의 인벤토리 ",
            fg=Colors.WHITE,
            bg=Colors.BLACK
        )
        
        # 봇 정보 표시
        inventory = self._get_inventory()
        if not inventory:
            console.print(x + 2, y + 2, "인벤토리를 확인할 수 없습니다.", fg=Colors.RED)
            return
            
        console.print(x + 2, y + 2, f"골드: {inventory.gold} G", fg=Colors.YELLOW)
        console.print(x + 2, y + 3, f"무게: {inventory.current_weight:.1f} / {inventory.max_weight:.1f} kg", fg=Colors.CYAN)
        
        # 구분선
        console.print(x + 1, y + 4, "─" * (width - 2), fg=Colors.GRAY)
        
        # 아이템 목록
        items = inventory.slots
        
        if not items:
            console.print(x + 2, y + 6, "비어 있음", fg=Colors.GRAY)
        else:
            # 스크롤 처리
            start_idx = self.scroll_offset
            end_idx = min(start_idx + self.items_per_page, len(items))
            
            for i in range(start_idx, end_idx):
                item_idx = i
                slot = items[item_idx]
                item = slot.item
                quantity = slot.quantity
                
                # 표시 위치
                line_y = y + 6 + (i - start_idx) * 2
                
                # 선택 하이라이트
                if i == self.selected_index:
                    console.print(x + 2, line_y, ">", fg=Colors.YELLOW)
                    name_color = Colors.WHITE
                else:
                    name_color = Colors.GRAY
                
                # 아이템 이름 및 수량
                item_name = getattr(item, 'name', 'Unknown Item')
                console.print(x + 4, line_y, f"{item_name} x{quantity}", fg=name_color)
                
                # 아이템 설명 (선택된 경우)
                if i == self.selected_index:
                    desc = getattr(item, 'description', '')
                    console.print(x + 4, line_y + 1, f"  {desc[:50]}", fg=Colors.DARK_GRAY)

        # 하단 도움말
        console.print(x + 2, y + height - 2, "ESC: 닫기  방향키: 이동  E: 아이템 가져오기", fg=Colors.GRAY)

    def handle_input(self, event: tcod.event.Event) -> bool:
        """
        입력 처리
        Returns: True if should close
        """
        if isinstance(event, tcod.event.KeyDown):
            if event.sym == tcod.event.KeySym.ESCAPE:
                return True
            
            inventory = self._get_inventory()
            if not inventory:
                return False
                
            num_items = len(inventory.slots)
            
            if event.sym == tcod.event.KeySym.UP:
                self.selected_index = max(0, self.selected_index - 1)
                # 스크롤 조정
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
            
            elif event.sym == tcod.event.KeySym.DOWN:
                self.selected_index = min(num_items - 1, self.selected_index + 1)
                # 스크롤 조정
                if self.selected_index >= self.scroll_offset + self.items_per_page:
                    self.scroll_offset = self.selected_index - self.items_per_page + 1
            
            elif event.sym == tcod.event.KeySym.e:
                # 아이템 가져오기 (구현 필요)
                # self._take_item_from_bot()
                pass
                
        return False

    def _get_inventory(self):
        """봇 인벤토리 객체 가져오기"""
        if hasattr(self.bot, 'bot_inventory'):
            return self.bot.bot_inventory
        # 봇 인벤토리가 없으면 캐릭터 인벤토리 시도 (구조에 따라 다름)
        if hasattr(self.bot, 'inventory'):
            return self.bot.inventory
        return None

def open_bot_inventory_ui(console, context, bot, on_update=None):
    """봇 인벤토리 UI 열기 함수"""
    ui = BotInventoryUI(bot)
    
    while True:
        # 백그라운드 업데이트 실행
        if on_update:
            on_update()

        tcod.console.Console.clear(console)
        
        # 배경 (기존 화면)은 유지하고 위에 그리기 위해 clear 대신 덮어쓰기 방식 사용 가능
        # 하지만 간단하게 구현하기 위해 clear 후 다시 그리는 방식 사용
        # (실제 게임에서는 WorldUI 렌더링 후 이 UI 렌더링 필요)
        
        ui.render(console)
        context.present(console)
        
        # 논블로킹 대기 (0.05초 타임아웃)
        for event in tcod.event.wait(timeout=0.05):
            if ui.handle_input(event):
                return
            
            # 창 닫기 이벤트
            if isinstance(event, tcod.event.Quit):
                raise SystemExit()

