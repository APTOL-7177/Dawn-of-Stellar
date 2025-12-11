"""
퀘스트 게시판 UI

사용 가능한 퀘스트를 보고 수락할 수 있는 UI
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
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
        player_level: int,
        player: Any = None,
        current_floor: int = 0,
        inventory: Any = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.quest_manager = quest_manager
        self.player_level = player_level
        self.player = player
        self.current_floor = current_floor
        self.inventory = inventory  # 실제 Inventory 객체
        
        # 퀘스트 목록
        self.available_quests = quest_manager.get_available_quests()
        self.active_quests = quest_manager.get_active_quests()
        
        # 선택된 탭 (0: 사용 가능, 1: 진행 중)
        self.current_tab = 0
        self.tabs = ["사용 가능한 퀘스트", "진행 중인 퀘스트"]
        
        # 커서 위치
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 8  # 진행 중인 퀘스트는 더 많은 공간 필요하므로 감소
        
        self.closed = False
        
        # 퀘스트가 없으면 생성
        if not self.available_quests:
            quest_manager.generate_quests(player_level, count=5)
            self.available_quests = quest_manager.get_available_quests()
        
        # 퀘스트 게시판을 열 때마다 완료 체크 (안전장치)
        quest_manager.check_all_quests_completion()
        self.active_quests = quest_manager.get_active_quests()  # 완료 체크 후 다시 가져오기
        
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
                    if self.quest_manager.accept_quest(quest.quest_id, self.current_floor):
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
                elif self.current_tab == 1:  # 진행 중인 퀘스트 완료 처리
                    if quest.is_complete:
                        if self.player is None:
                            logger.error("플레이어 객체가 없어 퀘스트 완료를 처리할 수 없습니다.")
                            play_sfx("ui", "cursor_cancel")
                        elif self.quest_manager.complete_quest(quest.quest_id, self.player, self.inventory):
                            self.active_quests = self.quest_manager.get_active_quests()
                            self.cursor = min(self.cursor, len(self.active_quests) - 1)
                            if self.cursor < 0:
                                self.cursor = 0
                            play_sfx("ui", "item_get")
                            logger.info(f"퀘스트 완료 보상 수령: {quest.name} - 보상: {quest.reward}")
                            # 실제 게임에서는 여기에 보상 팝업 UI 표시
                        else:
                            play_sfx("ui", "cursor_cancel")
                    else:
                        play_sfx("ui", "cursor_cancel")
        
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            play_sfx("ui", "cursor_cancel")
            self.closed = True
            return True
        
        return False

    def render(self, console: tcod.console.Console):
        """렌더링"""
        console.clear()
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 렌더링 전에 완료 체크 (진행 중인 퀘스트 탭일 때만)
        if self.current_tab == 1:
            self.quest_manager.check_all_quests_completion()
            self.active_quests = self.quest_manager.get_active_quests()
        
        # 제목
        title = "=== 퀘스트 게시판 ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 215, 0))
        
        # 탭
        tab_y = 4
        tab_x = 5
        for i, tab_name in enumerate(self.tabs):
            if i == self.current_tab:
                console.print(tab_x + i * 30, tab_y, f"{tab_name}", fg=(255, 255, 100))
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
                # 진행 중인 퀘스트는 더 많은 공간 필요 (진행도 표시)
                item_spacing = 4 if self.current_tab == 1 else 2
                y = list_y + i * item_spacing
                cursor_index = self.scroll_offset + i
                
                # 커서
                if cursor_index == self.cursor:
                    console.print(3, y, "►", fg=(255, 255, 100))
                
                # 퀘스트 이름 (길이 제한 - 진행도와 겹치지 않도록)
                color = (255, 255, 255) if cursor_index == self.cursor else (200, 200, 200)
                # 퀘스트 이름 길이 제한
                max_name_width = min(45, self.screen_width - 40)  # 오른쪽에 난이도 표시 공간 확보
                quest_name = quest.name[:max_name_width] if len(quest.name) > max_name_width else quest.name
                console.print(5, y, quest_name, fg=color)
                
                # 난이도 표시
                difficulty_colors = {
                    "easy": (100, 255, 100),
                    "normal": (255, 255, 100),
                    "hard": (255, 150, 100),
                    "legendary": (255, 100, 100)
                }
                difficulty_color = difficulty_colors.get(quest.difficulty.value, (255, 255, 255))
                console.print(self.screen_width - 30, y, f"{quest.difficulty.value.upper()}", fg=difficulty_color)
                
                # 진행 중인 퀘스트는 진행률 표시 (퀘스트 이름 아래 별도 줄로)
                if self.current_tab == 1:
                    if quest.is_complete:
                        # 완료된 퀘스트는 특별 표시
                        console.print(5, y + 2, " 완료됨 - Z키로 보상 수령", fg=(255, 215, 0))
                    else:
                        progress_text = f"진행: "
                        for obj in quest.objectives:
                            progress_text += f"{obj.progress_text} "
                        # 진행도 텍스트 길이 제한
                        max_progress_width = self.screen_width - 10
                        if len(progress_text) > max_progress_width:
                            progress_text = progress_text[:max_progress_width - 3] + "..."
                        # y + 2로 이동하여 퀘스트 이름(y)과 확실히 분리
                        console.print(5, y + 2, progress_text, fg=(150, 255, 150))
        
        # 선택된 퀘스트 상세 정보
        if current_list and 0 <= self.cursor < len(current_list):
            quest = current_list[self.cursor]
            
            # 하단에 고정 (전체 높이에서 역산)
            # 도움말이 height-2, 보상이 height-4, 목표가 그 위..
            # 넉넉하게 공간 확보
            detail_base_y = self.screen_height - 12
            
            # 구분선
            console.print(3, detail_base_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
            
            current_y = detail_base_y + 2
            
            # 설명
            console.print(5, current_y, f"설명: {quest.description}", fg=Colors.UI_TEXT)
            current_y += 2
            
            # 목표
            console.print(5, current_y, "목표:", fg=(255, 200, 100))
            # 목표는 옆에 나열하거나 한 줄에 하나씩
            # 공간이 부족할 수 있으므로 한 줄에 표시 시도
            objective_text = ""
            for i, obj in enumerate(quest.objectives):
                status_str = "(완료)" if obj.is_complete else "(진행중)"
                if i > 0:
                    objective_text += " / "
                objective_text += f"{obj.description} {status_str}"
            
            console.print(11, current_y, objective_text, fg=Colors.UI_TEXT)
            current_y += 2
            
            # 보상 (맨 밑에 가깝게)
            console.print(5, current_y, f"보상: {quest.reward}", fg=(255, 215, 0))
        
        # 안내 메시지
        help_y = self.screen_height - 2
        if self.current_tab == 0:
            help_text = "←→: 탭 변경  ↑↓: 선택  Z: 수락  X: 닫기"
        else:
            help_text = "←→: 탭 변경  ↑↓: 선택  Z: 완료된 퀘스트 보상 수령  X: 닫기"
        console.print(2, help_y, help_text, fg=Colors.GRAY)


def open_quest_board(
    console: tcod.console.Console,
    context: tcod.context.Context,
    quest_manager: Optional[QuestManager] = None,
    player_level: int = 1,
    player: Any = None,
    current_floor: int = 0,
    inventory: Any = None
):
    """퀘스트 게시판 열기"""
    from src.quest.quest_manager import get_quest_manager
    
    # QuestManager 인스턴스 가져오기
    if quest_manager is None:
        quest_manager = get_quest_manager()
    
    ui = QuestBoardUI(console.width, console.height, quest_manager, player_level, player, current_floor, inventory)
    
    logger.info("퀘스트 게시판 열기")

    import time
    import pygame

    # 입력 큐 비우기 (이전 입력 방지)
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass

    # 게임패드/키보드 입력 상태 초기화
    unified_input_handler.clear_input_state()

    # 딜레이 후 다시 이벤트 큐 비우기
    time.sleep(0.1)
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()

    while not ui.closed:
        ui.render(console)
        context.present(console)
        
        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
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
                ui.closed = True
                break
        
        # 게임패드 입력 처리
        if not keyboard_processed and not ui.closed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                ui.handle_input(gamepad_action)
        
        # CPU 사용률 낮추기
        time.sleep(0.01)

