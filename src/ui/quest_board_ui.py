"""
퀘스트 게시판 UI

사용 가능한 퀘스트를 보고 수락할 수 있는 UI
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.quest.quest_manager import QuestManager, Quest
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("quest_ui")


class QuestBoardUI:
    """퀘스트 게시판 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        quest_manager: QuestManager,
        player_level: int
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.quest_manager = quest_manager
        self.player_level = player_level
        
        # 퀘스트 목록
        self.available_quests = quest_manager.get_available_quests()
        self.active_quests = quest_manager.get_active_quests()
        
        # 선택된 탭 (0: 사용 가능, 1: 진행 중)
        self.current_tab = 0
        self.tabs = ["사용 가능한 퀘스트", "진행 중인 퀘스트"]
        
        # 커서 위치
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 10
        
        self.closed = False
        
        # 퀘스트가 없으면 생성
        if not self.available_quests:
            quest_manager.generate_quests(player_level, count=5)
            self.available_quests = quest_manager.get_available_quests()
        
        logger.info(f"퀘스트 게시판 열기 - 사용 가능: {len(self.available_quests)}개, 진행 중: {len(self.active_quests)}개")

    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        current_list = self.available_quests if self.current_tab == 0 else self.active_quests
        
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
                quest = current_list[self.cursor]
                
                if self.current_tab == 0:  # 사용 가능한 퀘스트 수락
                    if self.quest_manager.accept_quest(quest.quest_id):
                        self.available_quests = self.quest_manager.get_available_quests()
                        self.active_quests = self.quest_manager.get_active_quests()
                        self.cursor = min(self.cursor, len(self.available_quests) - 1)
                        if self.cursor < 0:
                            self.cursor = 0
                        play_sfx("ui", "confirm")
                        logger.info(f"퀘스트 수락: {quest.name}")
                    else:
                        play_sfx("ui", "cursor_cancel")
                        logger.warning("퀘스트 수락 실패 (활성 퀘스트 가득 참)")
                # 진행 중인 퀘스트는 수락 불가 (정보만 보기)
        
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
        title = "=== 퀘스트 게시판 ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 215, 0))
        
        # 탭
        tab_y = 4
        tab_x = 5
        for i, tab_name in enumerate(self.tabs):
            if i == self.current_tab:
                console.print(tab_x + i * 30, tab_y, f"[{tab_name}]", fg=(255, 255, 100))
            else:
                console.print(tab_x + i * 30, tab_y, f" {tab_name} ", fg=(150, 150, 150))
        
        # 현재 선택된 리스트
        current_list = self.available_quests if self.current_tab == 0 else self.active_quests
        list_y = 7
        
        # 퀘스트 목록
        visible_quests = current_list[self.scroll_offset:self.scroll_offset + self.max_visible]
        
        if not visible_quests:
            message = "퀘스트가 없습니다." if self.current_tab == 0 else "진행 중인 퀘스트가 없습니다."
            console.print(10, list_y, message, fg=(150, 150, 150))
        else:
            for i, quest in enumerate(visible_quests):
                y = list_y + i
                cursor_index = self.scroll_offset + i
                
                # 커서
                if cursor_index == self.cursor:
                    console.print(3, y, "►", fg=(255, 255, 100))
                
                # 퀘스트 이름
                color = (255, 255, 255) if cursor_index == self.cursor else (200, 200, 200)
                console.print(5, y, quest.name, fg=color)
                
                # 난이도 표시
                difficulty_colors = {
                    "easy": (100, 255, 100),
                    "normal": (255, 255, 100),
                    "hard": (255, 150, 100),
                    "legendary": (255, 100, 100)
                }
                difficulty_color = difficulty_colors.get(quest.difficulty.value, (255, 255, 255))
                console.print(self.screen_width - 30, y, f"[{quest.difficulty.value.upper()}]", fg=difficulty_color)
                
                # 진행 중인 퀘스트는 진행률 표시
                if self.current_tab == 1:
                    progress_text = f"진행: "
                    for obj in quest.objectives:
                        progress_text += f"{obj.progress_text} "
                    console.print(5, y + 1, progress_text, fg=(150, 255, 150))
        
        # 선택된 퀘스트 상세 정보
        if current_list and 0 <= self.cursor < len(current_list):
            quest = current_list[self.cursor]
            detail_y = list_y + self.max_visible + 2
            
            console.print(3, detail_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
            detail_y += 1
            
            # 설명
            console.print(5, detail_y, quest.description, fg=Colors.UI_TEXT)
            detail_y += 2
            
            # 목표
            console.print(5, detail_y, "목표:", fg=(255, 200, 100))
            detail_y += 1
            for obj in quest.objectives:
                status = "✓" if obj.is_complete else " "
                console.print(7, detail_y, f"{status} {obj.description} ({obj.progress_text})", 
                            fg=(100, 255, 100) if obj.is_complete else Colors.UI_TEXT)
                detail_y += 1
            
            # 보상
            detail_y += 1
            console.print(5, detail_y, f"보상: {quest.reward}", fg=(255, 215, 0))
        
        # 안내 메시지
        help_y = self.screen_height - 2
        if self.current_tab == 0:
            help_text = "←→: 탭 변경  ↑↓: 선택  Z: 수락  X: 닫기"
        else:
            help_text = "←→: 탭 변경  ↑↓: 선택  X: 닫기"
        console.print(2, help_y, help_text, fg=Colors.GRAY)


def open_quest_board(
    console: tcod.console.Console,
    context: tcod.context.Context,
    quest_manager: Optional[QuestManager] = None,
    player_level: int = 1
):
    """퀘스트 게시판 열기"""
    from src.quest.quest_manager import get_quest_manager
    
    # QuestManager 인스턴스 가져오기
    if quest_manager is None:
        quest_manager = get_quest_manager()
    
    ui = QuestBoardUI(console.width, console.height, quest_manager, player_level)
    handler = InputHandler()
    
    logger.info("퀘스트 게시판 열기")
    
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

