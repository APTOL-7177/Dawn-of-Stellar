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
    
    def __init__(self, bot_list: list, current_index: int = 0):
        self.bot_list = bot_list
        self.current_index = current_index
        self.bot = self.bot_list[self.current_index] if self.bot_list else None
        
        self.selected_index = 0
        self.scroll_offset = 0
        self.items_per_page = 15
        
        logger.info(f"BotInventoryUI 초기화: bot={self.bot}, total_bots={len(self.bot_list)}")

    def next_bot(self):
        """다음 봇으로 전환"""
        if not self.bot_list:
            return
        
        self.current_index = (self.current_index + 1) % len(self.bot_list)
        self.bot = self.bot_list[self.current_index]
        # 봇이 바뀌면 선택 초기화
        self.selected_index = 0
        self.scroll_offset = 0
        logger.info(f"봇 전환: {self.bot}")

    def prev_bot(self):
        """이전 봇으로 전환"""
        if not self.bot_list:
            return
        
        self.current_index = (self.current_index - 1) % len(self.bot_list)
        self.bot = self.bot_list[self.current_index]
        # 봇이 바뀌면 선택 초기화
        self.selected_index = 0
        self.scroll_offset = 0
        logger.info(f"봇 전환 (이전): {self.bot}")
        
    def render(self, console: tcod.console.Console):
        """렌더링"""
        width = 60
        height = 40
        x = (console.width - width) // 2
        y = (console.height - height) // 2
        
        # 봇 이름 안전하게 가져오기
        bot_name = getattr(self.bot, 'bot_name', getattr(self.bot, 'name', 'Unknown Bot'))
        
        # 프레임 그리기
        console.draw_frame(
            x, y, width, height,
            title=f" {bot_name}의 인벤토리 ",
            fg=Colors.WHITE,
            bg=Colors.BLACK
        )
        
        # 봇 정보 표시
        inventory = self._get_inventory()
        if inventory is None:
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
            
            # 봇 전환 키 (인벤토리 유무와 상관없이 작동해야 함)
            if event.sym == tcod.event.KeySym.N2 or event.sym == tcod.event.KeySym.KP_2:
                self.next_bot()
                return False
            
            elif event.sym == tcod.event.KeySym.RIGHT:
                self.next_bot()
                return False
                
            elif event.sym == tcod.event.KeySym.LEFT:
                self.prev_bot()
                return False

            # 인벤토리 조작 키 (인벤토리가 있어야 함)
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
        # 1. bot.bot_inventory
        if hasattr(self.bot, 'bot_inventory'):
            return self.bot.bot_inventory
            
        # 2. bot.inventory
        if hasattr(self.bot, 'inventory'):
            return self.bot.inventory
            
        # 3. bot.character.inventory (캐릭터 객체 내부)
        if hasattr(self.bot, 'character') and hasattr(self.bot.character, 'inventory'):
            return self.bot.character.inventory
            
        # 4. bot_manager.get_inventory(bot_id) 등 외부 참조가 필요할 수도 있음
        # (여기서는 봇 객체만으로 해결 시도)
        
        logger.warning(f"봇 인벤토리를 찾을 수 없음. 봇 속성: {dir(self.bot)}")
        if hasattr(self.bot, 'character'):
            logger.warning(f"봇 캐릭터 속성: {dir(self.bot.character)}")
            
        return None

def open_bot_inventory_ui(console, context, bot_list, current_index=0, on_update=None):
    """봇 인벤토리 UI 열기 함수"""
    logger.info(f"open_bot_inventory_ui 시작: {len(bot_list)} bots")
    try:
        ui = BotInventoryUI(bot_list, current_index)
        
        while True:
            # 백그라운드 업데이트 실행
            if on_update:
                on_update()

            tcod.console.Console.clear(console)
            
            try:
                ui.render(console)
            except Exception as e:
                logger.error(f"BotInventoryUI 렌더링 오류: {e}", exc_info=True)
                console.print(2, 2, f"렌더링 오류: {e}", fg=Colors.RED)
            
            context.present(console)
            
            # 논블로킹 대기 (0.05초 타임아웃)
            for event in tcod.event.wait(timeout=0.05):
                if ui.handle_input(event):
                    logger.info("open_bot_inventory_ui 종료 (사용자 입력)")
                    return
                
                # 창 닫기 이벤트
                if isinstance(event, tcod.event.Quit):
                    raise SystemExit()
    except Exception as e:
        logger.error(f"open_bot_inventory_ui 치명적 오류: {e}", exc_info=True)
    finally:
        logger.info("open_bot_inventory_ui 함수 리턴")

