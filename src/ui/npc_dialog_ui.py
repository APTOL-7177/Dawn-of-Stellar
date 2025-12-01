"""
NPC 대화 UI

NPC와의 대화 및 선택지 처리
"""

import tcod.console
import tcod.event
from typing import Optional, List, Dict, Any, Callable

from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.ui.tcod_display import Colors
from src.core.logger import get_logger
from src.audio import play_sfx

logger = get_logger("npc_dialog")


class NPCChoice:
    """NPC 선택지"""
    def __init__(self, text: str, callback: Callable[[], Any] = None):
        self.text = text
        self.callback = callback


def show_npc_dialog(
    console: tcod.console.Console,
    context: tcod.context.Context,
    npc_name: str,
    dialog_text: str,
    choices: Optional[List[NPCChoice]] = None,
    ai_auto_select: bool = None  # AI 모드: 자동 선택
) -> Optional[int]:
    """
    NPC 대화 창 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        npc_name: NPC 이름
        dialog_text: 대화 텍스트 (여러 줄 가능, \n으로 구분)
        choices: 선택지 리스트 (None이면 확인만 가능)
        ai_auto_select: AI 모드 자동 선택 (None이면 ai_spectate_mode에서 확인)
    
    Returns:
        선택된 선택지 인덱스 (None이면 취소)
    """
    # AI 관전 모드 체크
    if ai_auto_select is None:
        try:
            from src.ui.ai_spectate_mode import is_ai_mode
            ai_auto_select = is_ai_mode()
        except:
            ai_auto_select = False
    
    # AI 모드면 자동 처리
    if ai_auto_select:
        import time
        time.sleep(0.3)  # 잠시 대기 (화면 표시용)
        if choices and len(choices) > 0:
            # 첫 번째 선택지 자동 선택
            if choices[0].callback:
                try:
                    choices[0].callback()
                except Exception as e:
                    logger.warning(f"AI 자동 선택 콜백 오류: {e}")
            return 0
        return 0
    
    # 대화 텍스트를 줄 단위로 분리
    dialog_lines = dialog_text.split('\n')
    
    # 선택지가 있으면 선택 모드, 없으면 확인만 가능
    has_choices = choices and len(choices) > 0
    selected_index = 0 if has_choices else None
    
    # 박스 크기 계산
    max_line_width = max(len(line) for line in dialog_lines) if dialog_lines else 0
    if has_choices:
        max_choice_width = max(len(choice.text) for choice in choices)
        max_line_width = max(max_line_width, max_choice_width)
    
    box_width = min(max_line_width + 10, console.width - 20)
    box_height = len(dialog_lines) + 6
    if has_choices:
        box_height += len(choices) + 1
    
    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2

    # 입력 큐 비우기 (이전 입력 방지)
    import time
    for _ in tcod.event.get():
        pass
    try:
        import pygame
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
        import pygame
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()

    while True:
        # 기존 화면은 이미 렌더링되어 있다고 가정
        # 대화 상자만 오버레이
        
        # 반투명 배경 (TCOD는 직접 투명도 지원하지 않으므로 어두운 배경)
        for dy in range(box_height):
            for dx in range(box_width):
                console.print(box_x + dx, box_y + dy, " ", bg=(20, 20, 20))
        
        # 대화 상자
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            npc_name,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )
        
        # 대화 텍스트 출력
        y = box_y + 2
        for line in dialog_lines:
            # 긴 줄 자동 줄바꿈
            if len(line) > box_width - 4:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 > box_width - 4:
                        if current_line:
                            console.print(box_x + 2, y, current_line[:box_width - 4], fg=Colors.UI_TEXT)
                            y += 1
                        current_line = word
                    else:
                        current_line += (" " if current_line else "") + word
                if current_line:
                    console.print(box_x + 2, y, current_line[:box_width - 4], fg=Colors.UI_TEXT)
                    y += 1
            else:
                console.print(box_x + 2, y, line, fg=Colors.UI_TEXT)
                y += 1
        
        # 선택지 출력
        if has_choices:
            y += 1
            for i, choice in enumerate(choices):
                if i == selected_index:
                    prefix = "> "
                    fg_color = Colors.UI_TEXT_SELECTED
                else:
                    prefix = "  "
                    fg_color = Colors.UI_TEXT
                
                console.print(box_x + 4, y, f"{prefix}{choice.text}", fg=fg_color)
                y += 1
        
        # 안내 메시지
        help_y = box_y + box_height - 2
        if has_choices:
            help_text = "↑↓: 선택  Z: 확인  X: 취소"
        else:
            help_text = "Z: 확인  X: 취소"
        
        console.print(
            box_x + (box_width - len(help_text)) // 2,
            help_y,
            help_text,
            fg=Colors.GRAY
        )
        
        context.present(console)
        
        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass
        
        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                keyboard_processed = True
            
            if has_choices:
                if action == GameAction.MOVE_UP:
                    selected_index = max(0, selected_index - 1)
                elif action == GameAction.MOVE_DOWN:
                    selected_index = min(len(choices) - 1, selected_index + 1)
                elif action == GameAction.CONFIRM:
                    # 선택된 선택지의 콜백 실행
                    if choices[selected_index].callback:
                        try:
                            choices[selected_index].callback()
                        except Exception as e:
                            logger.error(f"NPC 선택지 콜백 실행 오류: {e}")
                    return selected_index
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    play_sfx("ui", "cursor_cancel")
                    return None
            else:
                if action == GameAction.CONFIRM:
                    return 0
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    play_sfx("ui", "cursor_cancel")
                    return None
            
            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None
        
        # 게임패드 입력 처리 (키보드 입력이 없었을 때만)
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if has_choices:
                    if gamepad_action == GameAction.MOVE_UP:
                        selected_index = max(0, selected_index - 1)
                    elif gamepad_action == GameAction.MOVE_DOWN:
                        selected_index = min(len(choices) - 1, selected_index + 1)
                    elif gamepad_action == GameAction.CONFIRM:
                        if choices[selected_index].callback:
                            try:
                                choices[selected_index].callback()
                            except Exception as e:
                                logger.error(f"NPC 선택지 콜백 실행 오류: {e}")
                        return selected_index
                    elif gamepad_action == GameAction.CANCEL or gamepad_action == GameAction.ESCAPE:
                        play_sfx("ui", "cursor_cancel")
                        return None
                else:
                    if gamepad_action == GameAction.CONFIRM:
                        return 0
                    elif gamepad_action == GameAction.CANCEL or gamepad_action == GameAction.ESCAPE:
                        play_sfx("ui", "cursor_cancel")
                        return None
        
        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)


def render_story_sequence(console: tcod.console.Console, context: Any, story_segments: List[Any], logger: Any) -> None:
    """
    스토리 시퀀스 렌더링 (타이핑 효과)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        story_segments: 스토리 세그먼트 리스트
        logger: 로거
    """
    import time

    # 스토리 BGM 재생 (위험한 분위기)
    from src.audio import play_bgm
    play_bgm("danger", loop=False, fade_in=True)

    for i, segment in enumerate(story_segments):
        # 스토리 텍스트 준비
        text = segment.text
        lines = text.split('\n')

        start_y = (console.height - len(lines)) // 2

        # 색상 설정
        if segment.color == "yellow":
            color = (255, 255, 100)
        elif segment.color == "dark":
            color = (100, 100, 100)
        elif segment.color == "red":
            color = (255, 50, 50)
        else:
            color = (255, 255, 255)

        # === 타이핑 효과 ===
        typing_speed = 0.03  # 문자당 초
        skip_typing = False
        completed_lines = []
        current_line_idx = 0
        current_text = ""

        for line_idx, line in enumerate(lines):
            for char_idx, char in enumerate(line):
                current_text += char

                # 화면 그리기
                console.clear()

                # 완성된 줄들
                for j, completed_line in enumerate(completed_lines):
                    x = (console.width - len(completed_line)) // 2
                    y = start_y + j
                    console.print(x, y, completed_line, fg=color)

                # 현재 타이핑 중인 줄
                x = (console.width - len(line)) // 2
                y = start_y + len(completed_lines)
                console.print(x, y, current_text, fg=color)

                # 진행 표시
                progress_text = f"[{i+1}/{len(story_segments)}] Space: 스킵"
                console.print(
                    (console.width - len(progress_text)) // 2,
                    console.height - 2,
                    progress_text,
                    fg=(150, 150, 150)
                )

                context.present(console)

                # Space/Enter로 타이핑 스킵 체크
                skip_start = time.time()
                while time.time() - skip_start < typing_speed:
                    for event in tcod.event.get():
                        if isinstance(event, tcod.event.KeyDown):
                            if event.sym == tcod.event.K_SPACE or event.sym == tcod.event.K_RETURN:
                                skip_typing = True
                                break
                    if skip_typing:
                        break
                    time.sleep(0.01)

                if skip_typing:
                    break

            # 현재 줄 완성
            completed_lines.append(line)
            current_text = ""

            if skip_typing:
                break

        # 타이핑 스킵 시 모든 텍스트 즉시 표시
        console.clear()
        for j, line in enumerate(lines):
            x = (console.width - len(line)) // 2
            y = start_y + j
            console.print(x, y, line, fg=color)

        # 진행 표시 (하단)
        progress_text = f"[{i+1}/{len(story_segments)}] Space: 다음"
        console.print(
            (console.width - len(progress_text)) // 2,
            console.height - 2,
            progress_text,
            fg=(150, 150, 150)
        )

        # 화면 업데이트
        context.present(console)

        # Space 키로 다음 진행 (또는 자동 진행)
        auto_advance_time = max(2.0, segment.pause * 2)  # 최소 2초, 기본 pause의 2배
        start_time = time.time()

        while time.time() - start_time < auto_advance_time:
            # 입력 확인
            for event in tcod.event.get():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.K_SPACE or event.sym == tcod.event.K_RETURN:
                        # 즉시 다음으로
                        break
            else:
                time.sleep(0.05)
                continue
            break

    logger.info("스토리 시퀀스 재생 완료")
