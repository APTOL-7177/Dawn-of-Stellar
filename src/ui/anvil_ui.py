from typing import Optional, List
import tcod

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.input_handler import InputHandler, GameAction
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
        item.current_durability = item.max_durability
        
        # 스탯 업데이트
        if self.inventory.party:
            for member in self.inventory.party:
                for slot, equipped in member.equipment.items():
                    if equipped == item:
                        member.update_equipment_stats(slot)
                        
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
    handler = InputHandler()
    
    while True:
        ui.render(console)
        context.present(console)
        
        for event in tcod.event.wait():
            action = handler.dispatch(event)
            if action:
                if ui.handle_input(action):
                    return
            
            if isinstance(event, tcod.event.Quit):
                raise SystemExit()

