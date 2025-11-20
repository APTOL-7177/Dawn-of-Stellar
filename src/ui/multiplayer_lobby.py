"""
멀티플레이 로비 UI

인원 모집 화면 - 호스트는 서버를 시작하고 클라이언트들이 연결될 때까지 대기
"""

import tcod.console
import tcod.event
from typing import Optional, Dict, Any, List
import time

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.player import MultiplayerPlayer
from src.audio import play_bgm


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
    """멀티플레이 로비 화면"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        session: MultiplayerSession,
        network_manager: Any,
        local_player_id: str,
        is_host: bool
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            session: 멀티플레이 세션
            network_manager: 네트워크 매니저 (HostNetworkManager 또는 ClientNetworkManager)
            local_player_id: 로컬 플레이어 ID
            is_host: 호스트 여부
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.session = session
        self.network_manager = network_manager
        self.local_player_id = local_player_id
        self.is_host = is_host
        
        self.logger = get_logger("multiplayer.lobby")
        self.completed = False
        self.cancelled = False
        
        # 깜빡이는 텍스트용
        self.blink_timer = 0.0
    
    def update(self, delta_time: float = 0.1):
        """로비 업데이트 (깜빡임 등)"""
        self.blink_timer += delta_time
        if self.blink_timer >= 2.0:
            self.blink_timer = 0.0
    
    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리
        
        Returns:
            완료 여부 (모든 플레이어 준비 완료 시 True)
        """
        if action == GameAction.CANCEL:
            self.cancelled = True
            return True
        
        # 호스트만 시작 가능 (ESC로 취소만 가능)
        if action == GameAction.CONFIRM and self.is_host:
            # 최소 1명 (호스트)이면 시작 가능
            if len(self.session.players) >= 1:
                self.completed = True
                return True
        
        return False
    
    def render(self, console: tcod.console.Console):
        """로비 화면 렌더링"""
        # 배경
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = "멀티플레이 로비" if not self.is_host else "멀티플레이 호스트"
        console.print(
            self.screen_width // 2 - len(title) // 2,
            5,
            title,
            fg=Colors.WHITE
        )
        
        # 접속 정보 (호스트만)
        if self.is_host and hasattr(self.network_manager, 'local_ip'):
            ip_text = f"접속 주소: {self.network_manager.local_ip}:{self.network_manager.port}"
            console.print(
                self.screen_width // 2 - len(ip_text) // 2,
                7,
                ip_text,
                fg=Colors.UI_TEXT
            )
        
        # 플레이어 목록
        y = 10
        console.print(
            self.screen_width // 2 - 20,
            y,
            "─" * 40,
            fg=Colors.UI_BORDER
        )
        y += 2
        
        console.print(
            self.screen_width // 2 - 15,
            y,
            f"플레이어 ({len(self.session.players)}/{self.session.max_players})",
            fg=Colors.UI_TEXT
        )
        y += 2
        
        # 각 플레이어 정보 표시
        for player_id, player in self.session.players.items():
            is_local = player_id == self.local_player_id
            prefix = "▶ " if is_local else "  "
            host_mark = " [호스트]" if player.is_host else ""
            status = "준비 완료" if hasattr(player, 'ready') and player.ready else "대기 중"
            
            player_line = f"{prefix}{player.player_name}{host_mark} - {status}"
            color = Colors.UI_TEXT_SELECTED if is_local else Colors.UI_TEXT
            
            console.print(
                self.screen_width // 2 - 25,
                y,
                player_line,
                fg=color
            )
            y += 1
        
        # 빈 슬롯 표시
        for _ in range(self.session.max_players - len(self.session.players)):
            console.print(
                self.screen_width // 2 - 25,
                y,
                "  [빈 슬롯]",
                fg=Colors.DARK_GRAY
            )
            y += 1
        
        y += 2
        console.print(
            self.screen_width // 2 - 20,
            y,
            "─" * 40,
            fg=Colors.UI_BORDER
        )
        y += 2
        
        # 캐릭터 할당 정보
        player_count = len(self.session.players)
        local_allocation = get_character_allocation(player_count, self.is_host)
        total_needed = 4  # 항상 총 4명 필요
        
        info_lines = [
            f"플레이어 수: {player_count}명",
            f"각 플레이어 캐릭터 할당:",
        ]
        
        if player_count == 1:
            info_lines.append("  • 1인: 4명")
        elif player_count == 2:
            info_lines.append("  • 각 2명씩 (총 4명)")
        elif player_count == 3:
            info_lines.append("  • 호스트: 2명")
            info_lines.append("  • 나머지: 각 1명씩")
        elif player_count == 4:
            info_lines.append("  • 각 1명씩 (총 4명)")
        
        info_lines.append("")
        info_lines.append(f"당신: {local_allocation}명 선택 가능")
        
        for i, line in enumerate(info_lines):
            console.print(
                self.screen_width // 2 - 25,
                y,
                line,
                fg=Colors.UI_TEXT
            )
            y += 1
        
        y += 2
        
        # 안내 메시지
        if self.is_host:
            # 깜빡이는 "시작" 메시지
            if int(self.blink_timer * 2) % 2 == 0:
                if player_count >= 1:
                    start_msg = "ENTER: 게임 시작"
                    console.print(
                        self.screen_width // 2 - len(start_msg) // 2,
                        y,
                        start_msg,
                        fg=Colors.UI_TEXT_SELECTED
                    )
            
            cancel_msg = "ESC: 취소"
            console.print(
                self.screen_width // 2 - len(cancel_msg) // 2,
                y + 2,
                cancel_msg,
                fg=Colors.UI_TEXT
            )
        else:
            wait_msg = "호스트가 게임을 시작할 때까지 기다려주세요..."
            if int(self.blink_timer * 3) % 2 == 0:
                console.print(
                    self.screen_width // 2 - len(wait_msg) // 2,
                    y,
                    wait_msg,
                    fg=Colors.UI_TEXT
                )
            
            cancel_msg = "ESC: 나가기"
            console.print(
                self.screen_width // 2 - len(cancel_msg) // 2,
                y + 2,
                cancel_msg,
                fg=Colors.UI_TEXT
            )


def show_multiplayer_lobby(
    console: tcod.console.Console,
    context: tcod.context.Context,
    session: MultiplayerSession,
    network_manager: Any,
    local_player_id: str,
    is_host: bool
) -> Optional[Dict[str, Any]]:
    """
    멀티플레이 로비 화면 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        session: 멀티플레이 세션
        network_manager: 네트워크 매니저
        local_player_id: 로컬 플레이어 ID
        is_host: 호스트 여부
        
    Returns:
        완료 시 딕셔너리 {"completed": True, "cancelled": False} 또는
        취소 시 {"completed": False, "cancelled": True} 또는 None
    """
    # 멀티플레이 로비 BGM 재생
    try:
        play_bgm("party_setup", loop=True)
        logger.info("멀티플레이 로비 BGM 재생")
    except Exception as e:
        logger.warning(f"멀티플레이 로비 BGM 재생 실패: {e}")
    
    lobby = MultiplayerLobby(
        screen_width=console.width,
        screen_height=console.height,
        session=session,
        network_manager=network_manager,
        local_player_id=local_player_id,
        is_host=is_host
    )
    
    handler = InputHandler()
    last_time = time.time()
    
    while True:
        current_time = time.time()
        delta_time = current_time - last_time
        last_time = current_time
        
        # 로비 업데이트
        lobby.update(delta_time)
        
        # 렌더링
        lobby.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait(timeout=0.05):
            if isinstance(event, tcod.event.Quit):
                return {"completed": False, "cancelled": True}
            
            context.convert_event(event)
            action = handler.dispatch(event)
            
            if action:
                if lobby.handle_input(action):
                    if lobby.cancelled:
                        return {"completed": False, "cancelled": True}
                    elif lobby.completed:
                        return {
                            "completed": True,
                            "cancelled": False,
                            "player_count": len(session.players),
                            "local_allocation": get_character_allocation(
                                len(session.players),
                                is_host
                            )
                        }
        
        # 세션 상태 확인 (플레이어 추가/제거 감지)
        # 네트워크 매니저가 이미 세션을 업데이트하고 있을 것임

