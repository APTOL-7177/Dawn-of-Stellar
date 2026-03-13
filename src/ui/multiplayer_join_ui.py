import tcod.console
import tcod.event
import sys
from typing import Optional, Dict, Any

from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.ui.tcod_display import Colors, render_space_background
from src.ui.cursor_menu import TextInputBox
from src.core.logger import get_logger
from src.audio import play_sfx

logger = get_logger("multiplayer_join_ui")


def _get_clipboard() -> Optional[str]:
    """클립보드 텍스트 가져오기"""
    # Windows: PowerShell (안정적, Ctrl+V 시에만 호출되므로 지연 허용)
    if sys.platform == "win32":
        try:
            import subprocess
            p = subprocess.run(
                ["powershell", "-noprofile", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=3,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            if p.returncode == 0 and p.stdout.strip():
                return p.stdout.strip()
        except Exception:
            pass

    # 폴백: tkinter
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text.strip() if text else None
    except Exception:
        pass

    return None


def _parse_address(text: str):
    """
    IP:포트 형식 파싱

    지원 형식:
        - "192.168.1.100:5000"  → ("192.168.1.100", 5000)
        - "192.168.1.100"       → ("192.168.1.100", 5000)  기본 포트
        - ":5001"               → ("127.0.0.1", 5001)      localhost
        - "5000"                → ("127.0.0.1", 5000)      포트만

    Returns:
        (host, port) 또는 에러 시 (None, error_message)
    """
    text = text.strip()
    if not text:
        return None, "주소를 입력해주세요"

    host = "127.0.0.1"
    port = 5000

    if ":" in text:
        parts = text.rsplit(":", 1)
        ip_part = parts[0].strip()
        port_part = parts[1].strip()

        if ip_part:
            host = ip_part
        if port_part:
            try:
                port = int(port_part)
            except ValueError:
                return None, f"잘못된 포트: '{port_part}'"
    else:
        # 콜론 없음: 숫자만이면 포트, 아니면 IP
        if text.isdigit():
            port = int(text)
        else:
            host = text

    if not (1 <= port <= 65535):
        return None, f"포트 범위 초과: {port} (1~65535)"

    return (host, port), None


def show_join_game_screen(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> Optional[Dict[str, Any]]:
    """
    멀티플레이 게임 참가 UI (단일 입력 박스, IP:포트 형식)
    """
    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    screen_width = console.width
    screen_height = console.height

    box_width = 44
    addr_input = TextInputBox(
        title="서버 주소 입력",
        prompt="IP:포트 (예: 192.168.1.100:5000)",
        max_length=30,
        x=(screen_width - box_width) // 2,
        y=screen_height // 2 - 4,
        width=box_width,
        default_text="127.0.0.1:5000"
    )

    error_msg = ""
    error_timer = 0

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

        # 입력 박스 (기본 렌더)
        addr_input.render(console)

        # 활성 테두리 강조
        console.draw_frame(
            addr_input.x, addr_input.y, addr_input.width, 6,
            addr_input.title,
            fg=Colors.YELLOW,
            bg=Colors.UI_BG
        )
        # 프롬프트
        console.print(
            addr_input.x + 2,
            addr_input.y + 1,
            addr_input.prompt,
            fg=Colors.UI_TEXT
        )
        # 입력 필드
        input_bg_width = addr_input.width - 4
        console.draw_rect(
            addr_input.x + 2,
            addr_input.y + 3,
            input_bg_width,
            1,
            ord(" "),
            bg=Colors.DARK_GRAY
        )
        display_text = addr_input.text + "_"
        console.print(
            addr_input.x + 3,
            addr_input.y + 3,
            display_text[:input_bg_width - 2],
            fg=Colors.WHITE
        )

        # 형식 안내
        hint_y = addr_input.y + 7
        hints = [
            "IP:포트  예) 192.168.1.100:5000",
            "IP만    예) 192.168.1.100 (포트 5000)",
            "포트만  예) 5001 (localhost:5001)",
        ]
        for i, hint in enumerate(hints):
            console.print(
                (screen_width - len(hint)) // 2,
                hint_y + i,
                hint,
                fg=(80, 80, 100)
            )

        # 에러 메시지
        if error_timer > 0:
            console.print(
                (screen_width - len(error_msg)) // 2,
                screen_height - 5,
                error_msg,
                fg=Colors.RED
            )
            error_timer -= 1

        # 안내
        help_text = "Enter: 연결  ESC: 취소"
        console.print(
            (screen_width - len(help_text)) // 2,
            screen_height - 3,
            help_text,
            fg=Colors.GRAY
        )

        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            # ESC
            if isinstance(event, tcod.event.KeyDown) and event.sym == tcod.event.KeySym.ESCAPE:
                logger.info("게임 참가 취소 (ESC)")
                play_sfx("ui", "cursor_cancel")
                return None

            if isinstance(event, tcod.event.Quit):
                return None

            action = unified_input_handler.process_tcod_event(event)

            if isinstance(event, tcod.event.KeyDown):
                # Enter 키 직접 처리 (CONFIRM 액션과 별도)
                if event.sym == tcod.event.KeySym.RETURN:
                    action = GameAction.CONFIRM
                elif event.sym == tcod.event.KeySym.BACKSPACE:
                    addr_input.handle_backspace()
                elif event.sym == tcod.event.KeySym.v and (event.mod & tcod.event.KMOD_CTRL):
                    # Ctrl+V 붙여넣기
                    paste_text = _get_clipboard()
                    if paste_text:
                        # 기존 텍스트 지우고 붙여넣기 (주소 전체 교체)
                        addr_input.text = ""
                        for ch in paste_text:
                            if len(addr_input.text) < addr_input.max_length:
                                addr_input.handle_char_input(ch)
                        logger.info(f"클립보드 붙여넣기: {paste_text}")
                elif len(addr_input.text) < addr_input.max_length:
                    if 32 <= event.sym <= 126:
                        char = chr(event.sym)
                        addr_input.handle_char_input(char)

            if action == GameAction.CONFIRM:
                result, err = _parse_address(addr_input.text)
                if err:
                    error_msg = err
                    error_timer = 90
                    play_sfx("ui", "cursor_error")
                    logger.warning(f"주소 파싱 실패: {err}")
                    continue

                host, port = result
                logger.info(f"게임 참가 시도: {host}:{port}")
                play_sfx("ui", "cursor_select")
                return {
                    "mode": "client",
                    "host_address": host,
                    "port": port
                }
