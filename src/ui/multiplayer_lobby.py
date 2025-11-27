"""
멀티플레이 로비 UI

인원 모집 화면 - 호스트는 서버를 시작하고 클라이언트들이 연결될 때까지 대기
"""

import tcod.console
import tcod.event
from typing import Optional, Dict, Any, List
import time
import random

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.core.logger import get_logger
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.player import MultiplayerPlayer
from src.audio import play_bgm, play_sfx


logger = get_logger("multiplayer.lobby")


def get_character_allocation(player_count: int, is_host: bool) -> int:
    """
    플레이어 수에 따른 캐릭터 할당 계산
    
    Args:
        player_count: 현재 플레이어 수 (1~4)
        is_host: 호스트 여부
        
    Returns:
        해당 플레이어가 선택할 수 있는 캐릭터 수
        
    할당 규칙:
        - 1인: 4명 (1인당 4명)
        - 2인: 각 2명 (2인당 2명씩 = 총 4명)
        - 3인: 호스트 2명, 나머지 1명씩 (2 + 1 + 1 = 총 4명)
        - 4인: 각 1명 (1인당 1명씩 = 총 4명)
    """
    if player_count == 1:
        return 4
    elif player_count == 2:
        return 2
    elif player_count == 3:
        return 2 if is_host else 1
    elif player_count == 4:
        return 1
    else:
        logger.warning(f"알 수 없는 플레이어 수: {player_count}")
        return 1


class MultiplayerLobby:
    """멀티플레이 로비 UI 클래스"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        session: MultiplayerSession,
        network_manager: Any,
        local_player_id: str,
        is_host: bool,
        dungeon_data_check: Optional[Dict[str, Any]] = None,
        lobby_complete_check: Optional[Dict[str, Any]] = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.session = session
        self.network_manager = network_manager
        self.local_player_id = local_player_id
        self.is_host = is_host
        self.dungeon_data_check = dungeon_data_check
        self.lobby_complete_check = lobby_complete_check
        
        self.completed = False
        self.cancelled = False
        self.host_disconnected = False
    
    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        if action == GameAction.CONFIRM:
            # 호스트만 게임 시작 가능
            if self.is_host:
                if len(self.session.players) >= 1:
                    self.completed = True
                    return True
            return False
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.cancelled = True
            return True
        
        return False
    
    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = "멀티플레이 로비"
        console.print(
            self.screen_width // 2 - len(title) // 2,
            5,
            title,
            fg=Colors.WHITE
        )
        
        # 호스트 정보
        if self.is_host:
            host_info = f"호스트: {self.network_manager.local_ip}:{self.network_manager.port}"
            console.print(
                self.screen_width // 2 - len(host_info) // 2,
                8,
                host_info,
                fg=Colors.UI_TEXT
            )
        
        # 플레이어 목록
        y = 12
        console.print(
            self.screen_width // 2 - 15,
            y,
            "플레이어 목록",
            fg=Colors.UI_TEXT
        )
        y += 2
        
        console.print(
            self.screen_width // 2 - 15,
            y,
            f"플레이어 ({len(self.session.players)}/{self.session.max_players})",
            fg=Colors.UI_TEXT
        )
        y += 2
        
        for player_id, player in self.session.players.items():
            player_name = getattr(player, 'player_name', 'Unknown')
            is_host_player = getattr(player, 'is_host', False)
            
            name_text = player_name
            if is_host_player:
                name_text += " (호스트)"
            if player_id == self.local_player_id:
                name_text += " [나]"
            
            console.print(
                self.screen_width // 2 - 15,
                y,
                name_text,
                fg=Colors.UI_TEXT_SELECTED if player_id == self.local_player_id else Colors.UI_TEXT
            )
            y += 1
        
        # 안내 메시지
        if self.is_host:
            help_text = "Enter: 게임 시작  ESC: 취소"
            console.print(
                self.screen_width // 2 - len(help_text) // 2,
                self.screen_height - 3,
                help_text,
                fg=Colors.UI_TEXT
            )
        else:
            help_text = "호스트가 게임을 시작할 때까지 대기 중..."
            console.print(
                self.screen_width // 2 - len(help_text) // 2,
                self.screen_height - 3,
                help_text,
                fg=Colors.DARK_GRAY
            )


def show_multiplayer_lobby(
    console: tcod.console.Console,
    context: tcod.context.Context,
    session: MultiplayerSession,
    network_manager: Any,
    local_player_id: str,
    is_host: bool,
    dungeon_data_check: Optional[Dict[str, Any]] = None,
    lobby_complete_check: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    멀티플레이 로비 화면 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        session: 멀티플레이 세션
        network_manager: 네트워크 매니저
        local_player_id: 로컬 플레이어 ID
        is_host: 호스트 여부
        dungeon_data_check: 던전 데이터 확인용 딕셔너리 (클라이언트용)
        lobby_complete_check: 로비 완료 확인용 딕셔너리 (클라이언트용)
    
    Returns:
        로비 결과 딕셔너리
    """
    from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
    from src.multiplayer.protocol import MessageType
    
    # 멀티플레이 로비 BGM 재생
    try:
        play_bgm("multiplayer_lobby", loop=True)
        logger.info("멀티플레이 로비 BGM 재생")
    except Exception as e:
        logger.warning(f"멀티플레이 로비 BGM 재생 실패: {e}")
    
    ui = MultiplayerLobby(
        screen_width=console.width,
        screen_height=console.height,
        session=session,
        network_manager=network_manager,
        local_player_id=local_player_id,
        is_host=is_host,
        dungeon_data_check=dungeon_data_check,
        lobby_complete_check=lobby_complete_check
    )
    
    
    # 클라이언트: 로비 완료 메시지 핸들러 등록
    if not is_host and lobby_complete_check is not None:
        def handle_lobby_complete(message: Any, sender_id: Optional[str] = None):
            """로비 완료 메시지 처리"""
            lobby_complete_check["value"] = True
            logger.info("로비 완료 메시지 수신")
        
        network_manager.register_handler(MessageType.LOBBY_COMPLETE, handle_lobby_complete)
    
    while not ui.completed and not ui.cancelled and not ui.host_disconnected:
        # 클라이언트: 던전 데이터 확인
        if not is_host and dungeon_data_check is not None:
            if dungeon_data_check.get("dungeon_data") is not None:
                ui.completed = True
                break
        
        # 클라이언트: 로비 완료 확인
        if not is_host and lobby_complete_check is not None:
            if lobby_complete_check.get("value", False):
                ui.completed = True
                break
        
        # 렌더링
        ui.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait(timeout=0.1):
            if isinstance(event, tcod.event.Quit):
                ui.cancelled = True
                break
            
            context.convert_event(event)
            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                if ui.handle_input(action):
                    break
        
        # 연결 상태 확인
        if not is_host:
            from src.multiplayer.network import ConnectionState
            if network_manager.connection_state == ConnectionState.DISCONNECTED:
                ui.host_disconnected = True
                break
    
    # 결과 반환
    player_count = len(session.players)
    local_allocation = get_character_allocation(player_count, is_host)
    
    return {
        "completed": ui.completed,
        "cancelled": ui.cancelled,
        "host_disconnected": ui.host_disconnected,
        "player_count": player_count,
        "local_allocation": local_allocation
    }


