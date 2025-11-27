"""
멀티플레이 캐릭터 재할당 UI

불러온 세이브의 캐릭터들을 현재 접속한 플레이어들에게 재할당하는 UI
"""

import tcod.console
import tcod.event
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors, render_space_background
from src.core.logger import get_logger
from src.audio import play_sfx

logger = get_logger("multiplayer.reassignment")


@dataclass
class CharacterAssignment:
    """캐릭터 할당 정보"""
    character_index: int  # 불러온 캐릭터 인덱스
    character_name: str
    original_player_id: Optional[str]  # 원래 플레이어 ID
    assigned_player_id: Optional[str]  # 재할당된 플레이어 ID


class MultiplayerCharacterReassignmentUI:
    """멀티플레이 캐릭터 재할당 UI"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        loaded_characters: List[Dict[str, Any]],
        current_players: List[Dict[str, Any]]
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.loaded_characters = loaded_characters  # 불러온 캐릭터 정보 (player_id 포함)
        self.current_players = current_players  # 현재 접속한 플레이어 정보
        
        # 캐릭터 할당 정보
        self.assignments: List[CharacterAssignment] = []
        for idx, char in enumerate(loaded_characters):
            self.assignments.append(CharacterAssignment(
                character_index=idx,
                character_name=char.get("name", "캐릭터"),
                original_player_id=char.get("player_id"),
                assigned_player_id=None
            ))
        
        # 자동 할당 시도 (같은 player_id가 있으면 자동 연결)
        self._auto_assign()
        
        # 현재 선택된 캐릭터 인덱스
        self.selected_character_index = 0
        self.completed = False
        self.cancelled = False
        
        # 플레이어 선택 메뉴
        self.player_menu: Optional[CursorMenu] = None
        self._create_player_menu()
    
    def _auto_assign(self):
        """자동 할당: 같은 player_id가 있으면 자동 연결"""
        auto_assigned_count = 0
        for assignment in self.assignments:
            if assignment.original_player_id:
                # 같은 player_id를 가진 현재 플레이어 찾기
                for player in self.current_players:
                    if player.get("player_id") == assignment.original_player_id:
                        assignment.assigned_player_id = assignment.original_player_id
                        auto_assigned_count += 1
                        logger.info(
                            f"자동 할당: {assignment.character_name} -> "
                            f"플레이어 {player.get('player_name', assignment.original_player_id)}"
                        )
                        break
        
        # 모든 캐릭터가 자동 할당되었으면 완료 처리
        if auto_assigned_count == len(self.assignments) and len(self.assignments) > 0:
            logger.info("모든 캐릭터가 자동 할당되었습니다")
            # 완료 처리는 사용자가 확인할 수 있도록 약간의 지연 후
            # 또는 즉시 완료 처리하지 않고 사용자가 확인할 수 있도록
    
    def _create_player_menu(self):
        """플레이어 선택 메뉴 생성"""
        menu_items = []
        
        # "할당 안 함" 옵션 추가
        menu_items.append(MenuItem(
            text="할당 안 함",
            value=None,
            description="이 캐릭터를 아무 플레이어에게도 할당하지 않습니다"
        ))
        
        # 현재 접속한 플레이어 목록
        for player in self.current_players:
            player_id = player.get("player_id")
            player_name = player.get("player_name", "플레이어")
            
            # 이미 할당된 캐릭터 수 확인
            assigned_count = sum(1 for a in self.assignments if a.assigned_player_id == player_id)
            
            # 할당 가능 여부 (플레이어당 최대 4명)
            is_available = assigned_count < 4
            
            menu_items.append(MenuItem(
                text=f"{player_name} ({assigned_count}명)",
                value=player_id,
                description=f"이 캐릭터를 {player_name}에게 할당합니다",
                enabled=is_available
            ))
        
        self.player_menu = CursorMenu(
            title="플레이어 선택",
            items=menu_items,
            x=40,
            y=10,
            width=35,
            show_description=True
        )
    
    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        if action == GameAction.MOVE_UP:
            if self.player_menu:
                self.player_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            if self.player_menu:
                self.player_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            if self.player_menu:
                selected_item = self.player_menu.get_selected_item()
                if selected_item and selected_item.enabled:
                    # 현재 선택된 캐릭터에 플레이어 할당
                    assignment = self.assignments[self.selected_character_index]
                    assignment.assigned_player_id = selected_item.value
                    logger.info(
                        f"캐릭터 할당: {assignment.character_name} -> "
                        f"{'할당 안 함' if selected_item.value is None else f'플레이어 {selected_item.value}'}"
                    )
                    
                    # 플레이어 메뉴 갱신 (할당된 수 반영)
                    self._create_player_menu()
                    
                    # 다음 캐릭터로 이동
                    if self.selected_character_index < len(self.assignments) - 1:
                        self.selected_character_index += 1
                    else:
                        # 마지막 캐릭터까지 할당 완료 - 모든 캐릭터 할당 확인
                        # 모든 캐릭터가 할당되었는지 확인 (할당 안 함도 포함)
                        all_assigned = all(a.assigned_player_id is not None for a in self.assignments)
                        if all_assigned:
                            # 모든 캐릭터가 할당됨 (할당 안 함 포함) - 완료
                            self.completed = True
                            return True
                        else:
                            # 아직 할당되지 않은 캐릭터가 있으면 첫 번째로 돌아가기
                            self.selected_character_index = 0
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            play_sfx("ui", "cursor_cancel")
            self.cancelled = True
            return True
        
        return False
    
    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = "캐릭터 재할당"
        console.print(
            self.screen_width // 2 - len(title) // 2,
            2,
            title,
            fg=Colors.WHITE
        )
        
        # 안내 메시지
        info = "불러온 캐릭터를 현재 접속한 플레이어에게 할당하세요"
        console.print(
            self.screen_width // 2 - len(info) // 2,
            4,
            info,
            fg=Colors.UI_TEXT
        )
        
        # 캐릭터 목록 (왼쪽)
        console.print(5, 6, "불러온 캐릭터:", fg=Colors.UI_TEXT)
        for idx, assignment in enumerate(self.assignments):
            y = 8 + idx
            char_data = self.loaded_characters[assignment.character_index]
            char_name = char_data.get("name", "캐릭터")
            job_name = char_data.get("job_name", "직업")
            assigned_player = None
            
            if assignment.assigned_player_id:
                for player in self.current_players:
                    if player.get("player_id") == assignment.assigned_player_id:
                        assigned_player = player.get("player_name", "플레이어")
                        break
            
            # 선택된 캐릭터 표시
            prefix = "▶" if idx == self.selected_character_index else " "
            
            # 할당 상태 표시
            if assigned_player:
                status = f"→ {assigned_player}"
                status_color = (100, 255, 100)  # 초록색
            else:
                status = "→ 미할당"
                status_color = Colors.DARK_GRAY
            
            console.print(5, y, f"{prefix} {char_name} ({job_name})", fg=Colors.UI_TEXT)
            console.print(35, y, status, fg=status_color)
        
        # 플레이어 선택 메뉴 (오른쪽)
        if self.player_menu:
            self.player_menu.render(console)
        
        # 현재 선택된 캐릭터 정보
        if self.selected_character_index < len(self.assignments):
            assignment = self.assignments[self.selected_character_index]
            char_data = self.loaded_characters[assignment.character_index]
            
            info_y = 28
            console.print(5, info_y, f"현재 선택: {assignment.character_name}", fg=Colors.UI_TEXT_SELECTED)
            if assignment.original_player_id:
                console.print(5, info_y + 1, f"원래 플레이어: {assignment.original_player_id}", fg=Colors.UI_TEXT)
        
        # 도움말
        help_text = "↑↓: 이동  Z: 할당  X: 취소"
        console.print(
            self.screen_width // 2 - len(help_text) // 2,
            self.screen_height - 2,
            help_text,
            fg=Colors.DARK_GRAY
        )
    
    def get_assignments(self) -> Dict[str, List[int]]:
        """
        할당 결과 반환
        
        Returns:
            {player_id: [character_index, ...]} 형태의 딕셔너리
        """
        result = {}
        for assignment in self.assignments:
            if assignment.assigned_player_id:
                if assignment.assigned_player_id not in result:
                    result[assignment.assigned_player_id] = []
                result[assignment.assigned_player_id].append(assignment.character_index)
        return result


def show_character_reassignment(
    console: tcod.console.Console,
    context: tcod.context.Context,
    loaded_characters: List[Dict[str, Any]],
    current_players: List[Dict[str, Any]]
) -> Optional[Dict[str, List[int]]]:
    """
    캐릭터 재할당 UI 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        loaded_characters: 불러온 캐릭터 정보 리스트 (각각 player_id 포함)
        current_players: 현재 접속한 플레이어 정보 리스트
        
    Returns:
        {player_id: [character_index, ...]} 형태의 할당 결과 (취소 시 None)
    """
    ui = MultiplayerCharacterReassignmentUI(
        screen_width=console.width,
        screen_height=console.height,
        loaded_characters=loaded_characters,
        current_players=current_players
    )
    
    logger.info(f"캐릭터 재할당 UI 시작: {len(loaded_characters)}명 캐릭터, {len(current_players)}명 플레이어")
    
    # 모든 캐릭터가 자동 할당되었는지 확인
    all_auto_assigned = all(
        a.assigned_player_id is not None 
        for a in ui.assignments
    ) if ui.assignments else False
    
    if all_auto_assigned and len(ui.assignments) > 0:
        # 모든 캐릭터가 자동 할당되었으면 확인 메시지 표시 후 완료
        logger.info("모든 캐릭터가 자동 할당되었습니다 - 확인 후 진행합니다")
        # 사용자가 확인할 수 있도록 잠시 대기 (또는 자동 완료)
        ui.completed = True
    else:
        # 수동 할당 필요
        while not ui.completed and not ui.cancelled:
            # 렌더링
            ui.render(console)
            context.present(console)
            
            # 입력 처리
            for event in tcod.event.wait():
                action = unified_input_handler.process_tcod_event(event)
                
                if action:
                    if ui.handle_input(action):
                        break
                
                # 윈도우 닫기
                if isinstance(event, tcod.event.Quit):
                    return None
    
    if ui.cancelled:
        logger.info("캐릭터 재할당 취소")
        return None
    
    assignments = ui.get_assignments()
    logger.info(f"캐릭터 재할당 완료: {len(assignments)}명 플레이어에게 할당")
    return assignments

