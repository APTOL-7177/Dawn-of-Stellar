"""
멀티플레이 메뉴

멀티플레이 모드 선택 및 세션 설정
"""

import tcod.console
import tcod.event
from typing import Optional, Dict, Any
from enum import Enum

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.audio import play_sfx, play_bgm


class MultiplayerMenuResult(Enum):
    """멀티플레이 메뉴 결과"""
    HOST_GAME = "host_game"  # 호스트로 게임 시작
    JOIN_GAME = "join_game"  # 게임 참가
    BACK = "back"  # 뒤로가기


class MultiplayerMenu:
    """멀티플레이 메뉴"""
    
    def __init__(self, screen_width: int, screen_height: int):
        """초기화"""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("multiplayer.menu")
        
        # 메뉴 상태
        self.result: Optional[MultiplayerMenuResult] = None
        
        # 메뉴 생성
        self._create_menu()
    
    def _create_menu(self):
        """메뉴 생성"""
        menu_items = [
            MenuItem(
                text="방 만들기 (호스트)",
                action=self._host_game,
                description="새로운 멀티플레이 세션을 호스트로 시작합니다"
            ),
            MenuItem(
                text="방 참가하기 (클라이언트)",
                action=self._join_game,
                description="다른 플레이어의 방에 참가합니다"
            ),
            MenuItem(
                text="뒤로가기",
                action=self._back,
                description="메인 메뉴로 돌아갑니다"
            ),
        ]
        
        menu_width = 50
        menu_x = (self.screen_width - menu_width) // 2
        menu_y = self.screen_height // 2 - 5
        
        self.menu = CursorMenu(
            title="멀티플레이",
            items=menu_items,
            x=menu_x,
            y=menu_y,
            width=menu_width,
            show_description=True
        )
    
    def _host_game(self) -> None:
        """호스트 게임 시작"""
        self.logger.info("호스트 게임 선택")
        play_sfx("ui", "confirm")
        self.result = MultiplayerMenuResult.HOST_GAME
    
    def _join_game(self) -> None:
        """게임 참가"""
        self.logger.info("게임 참가 선택")
        play_sfx("ui", "confirm")
        self.result = MultiplayerMenuResult.JOIN_GAME
    
    def _back(self) -> None:
        """뒤로가기"""
        self.logger.info("뒤로가기 선택")
        play_sfx("ui", "cancel")
        self.result = MultiplayerMenuResult.BACK
    
    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리
        
        Args:
            action: 게임 액션
            
        Returns:
            메뉴가 종료되었으면 True
        """
        if action == GameAction.MOVE_UP:
            self.menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            self.menu.execute_selected()
            return self.result is not None
        elif action == GameAction.ESCAPE:
            self.result = MultiplayerMenuResult.BACK
            return True
        
        return False
    
    def render(self, console: tcod.console.Console) -> None:
        """렌더링"""
        # 배경
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 메뉴 렌더링
        self.menu.render(console)
        
        # 안내 메시지
        info_y = self.screen_height - 5
        console.print(
            self.screen_width // 2,
            info_y,
            "↑ ↓: 이동, Z: 선택, ESC: 뒤로가기",
            fg=Colors.GRAY,
            alignment=tcod.constants.CENTER
        )


def show_multiplayer_menu(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> Optional[Dict[str, Any]]:
    """
    멀티플레이 메뉴 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        
    Returns:
        선택 결과 (None이면 취소)
    """
    menu = MultiplayerMenu(console.width, console.height)
    handler = InputHandler()
    
    # BGM 재생 (메인 메뉴와 동일)
    play_bgm("main_menu", loop=True)
    
    while True:
        # 이벤트 처리
        for event in tcod.event.wait():
            context.convert_event(event)
            
            action = handler.dispatch(event)
            if action:
                if menu.handle_input(action):
                    break
            
            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None
        
        # 렌더링
        console.clear()
        menu.render(console)
        context.present(console)
        
        # 결과 처리
        if menu.result:
            if menu.result == MultiplayerMenuResult.BACK:
                return None
            elif menu.result == MultiplayerMenuResult.HOST_GAME:
                # 호스트 게임 설정 화면 (향후 구현)
                return {
                    "mode": "host",
                    "result": menu.result.value
                }
            elif menu.result == MultiplayerMenuResult.JOIN_GAME:
                # 게임 참가 화면
                from src.ui.multiplayer_join_ui import show_join_game_screen
                join_result = show_join_game_screen(console, context)
                if join_result:
                    return join_result
                # 취소된 경우 None 반환하여 메뉴로 돌아감
    
    return None

