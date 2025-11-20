import tcod.console
import tcod.event
from typing import Optional, Dict, Any

from src.ui.input_handler import InputHandler, GameAction
from src.ui.tcod_display import Colors, render_space_background
from src.ui.cursor_menu import TextInputBox
from src.core.logger import get_logger
from src.audio import play_sfx

logger = get_logger("multiplayer_join_ui")


def show_join_game_screen(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> Optional[Dict[str, Any]]:
    """
    멀티플레이 게임 참가 UI를 표시하고 호스트 주소 및 포트를 입력받습니다.
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        
    Returns:
        선택된 호스트 정보 (mode, host_address, port) 또는 취소 시 None
    """
    handler = InputHandler()
    screen_width = console.width
    screen_height = console.height
    
    # 두 입력 박스를 더 넓게 배치 (간격 확보)
    box_width = 40
    box_height = 6
    box_spacing = 3  # 박스 사이 간격
    
    ip_input = TextInputBox(
        title="호스트 IP 주소 입력",
        prompt="IP 주소:",
        max_length=15,
        x=(screen_width - box_width) // 2,
        y=(screen_height - (box_height * 2 + box_spacing)) // 2,
        width=box_width,
        default_text="127.0.0.1"  # 기본값으로 localhost 설정
    )
    
    port_input = TextInputBox(
        title="호스트 포트 입력",
        prompt="포트:",
        max_length=5,
        x=(screen_width - box_width) // 2,
        y=(screen_height - (box_height * 2 + box_spacing)) // 2 + box_height + box_spacing,
        width=box_width,
        default_text="5000"
    )
    
    current_input = ip_input  # 현재 입력 중인 박스
    
    while True:
        # 렌더링
        render_space_background(console, screen_width, screen_height)
        
        # 제목
        title = "게임 참가"
        console.print(
            (screen_width - len(title)) // 2,
            5,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )
        
        # 먼저 두 입력 박스를 모두 렌더링 (비활성화 상태로)
        # IP 입력 박스 렌더링
        ip_input.render(console)
        # 포트 입력 박스 렌더링
        port_input.render(console)
        
        # 그 다음 활성화된 박스의 테두리만 다시 그리기 (강조)
        if current_input == ip_input:
            # IP 활성화: 밝은 노란색 테두리로 덮어쓰기
            console.draw_frame(
                ip_input.x, ip_input.y, ip_input.width, 6,
                ip_input.title,
                fg=Colors.YELLOW,
                bg=Colors.UI_BG
            )
        elif current_input == port_input:
            # 포트 활성화: 밝은 노란색 테두리로 덮어쓰기
            console.draw_frame(
                port_input.x, port_input.y, port_input.width, 6,
                port_input.title,
                fg=Colors.YELLOW,
                bg=Colors.UI_BG
            )
        
        # 안내 메시지
        help_text = "Tab: 포트/IP 전환  Enter: 연결  ESC: 취소"
        console.print(
            (screen_width - len(help_text)) // 2,
            screen_height - 3,
            help_text,
            fg=Colors.GRAY
        )
        
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)
            
            # 문자 입력 처리
            if isinstance(event, tcod.event.KeyDown):
                # IP 입력 중
                if current_input == ip_input:
                    if event.sym == tcod.event.KeySym.BACKSPACE:
                        ip_input.handle_backspace()
                    elif event.sym == tcod.event.KeySym.TAB:
                        # 포트 입력으로 전환
                        current_input = port_input
                        logger.debug("포트 입력으로 전환")
                    elif len(ip_input.text) < ip_input.max_length:
                        # ASCII 문자 범위 (32~126: 공백, 숫자, 영문, 특수문자)
                        if 32 <= event.sym <= 126:
                            char = chr(event.sym)
                            # 모든 문자 허용 (IP 주소용: 숫자, 점, 콜론 등)
                            ip_input.handle_char_input(char)
                # 포트 입력 중
                elif current_input == port_input:
                    if event.sym == tcod.event.KeySym.BACKSPACE:
                        port_input.handle_backspace()
                    elif event.sym == tcod.event.KeySym.TAB:
                        # IP 입력으로 전환
                        current_input = ip_input
                        logger.debug("IP 입력으로 전환")
                    elif len(port_input.text) < port_input.max_length:
                        # 숫자만 허용 (48~57: '0'~'9')
                        if 48 <= event.sym <= 57:
                            char = chr(event.sym)
                            port_input.handle_char_input(char)
            
            if action:
                # IP 입력 중
                if current_input == ip_input:
                    if action == GameAction.CONFIRM:
                        # 포트 입력으로 전환
                        if ip_input.text.strip():
                            current_input = port_input
                            logger.info(f"IP 입력 완료: {ip_input.text}")
                            play_sfx("ui", "cursor_move")
                        else:
                            logger.warning("IP 주소를 입력해주세요")
                            play_sfx("ui", "cursor_error")
                            continue
                    elif action == GameAction.CANCEL:
                        logger.info("게임 참가 취소")
                        return None
                
                # 포트 입력 중
                elif current_input == port_input:
                    if action == GameAction.CONFIRM:
                        # 연결 시도
                        host_address = ip_input.text.strip()
                        port_text = port_input.text.strip()
                        
                        if not host_address:
                            logger.warning("IP 주소를 입력해주세요")
                            current_input = ip_input
                            play_sfx("ui", "cursor_error")
                            continue
                        
                        if not port_text:
                            port_text = "5000"
                        
                        try:
                            port = int(port_text)
                            if not (1 <= port <= 65535):
                                raise ValueError("포트 번호는 1~65535 사이여야 합니다")
                        except ValueError as e:
                            logger.error(f"잘못된 포트 번호: {e}")
                            # 에러 메시지 표시
                            error_msg = f"오류: {str(e)}"
                            console.print(
                                (screen_width - len(error_msg)) // 2,
                                screen_height - 5,
                                error_msg,
                                fg=Colors.RED
                            )
                            context.present(console)
                            import time
                            time.sleep(1)
                            play_sfx("ui", "cursor_error")
                            continue
                        
                        logger.info(f"게임 참가 시도: {host_address}:{port}")
                        play_sfx("ui", "cursor_select")
                        return {
                            "mode": "client",
                            "host_address": host_address,
                            "port": port
                        }
                    
                    elif action == GameAction.CANCEL:
                        logger.info("게임 참가 취소")
                        return None
            
            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None
