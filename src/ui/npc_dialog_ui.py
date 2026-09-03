"""
NPC 대화 UI

NPC와의 대화 및 선택지 처리 (타이핑 효과, 연출 포함)
"""

import time
import tcod.console
import tcod.event
from dataclasses import dataclass
from typing import Optional, List, Any, Callable

from src.ui.input_handler import GameAction, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion
from src.ui.tcod_display import Colors
from src.ui.visual_tokens import rgb
from src.core.logger import get_logger
from src.audio import play_sfx

logger = get_logger("npc_dialog")

# NPC 이름 색상
NPC_NAME_COLORS = {
    "selena": (0, 200, 255),
    "karnos": (255, 100, 100),
    "mira": (255, 200, 100),
    "tord": (100, 200, 100),
    "lina": (255, 150, 200),
    "릴리": (255, 200, 255),
    "크리스": (200, 220, 255),
    "세피로스": (255, 215, 0),
    "카인": (180, 50, 50),
}


class NPCChoice:
    """NPC 선택지"""
    def __init__(self, text: str, callback: Callable[[], Any] = None):
        self.text = text
        self.callback = callback


@dataclass(frozen=True, slots=True)
class DialogPointerResult:
    action: GameAction | None = None
    choice_index: int | None = None
    hovered_choice: int | None = None
    tooltip: str | None = None


def _wrap_text(text: str, max_width: int) -> list:
    """텍스트 줄바꿈"""
    if len(text) <= max_width:
        return [text]
    result = []
    words = text.split()
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_width:
            if current:
                result.append(current)
            current = word
        else:
            current += (" " if current else "") + word
    if current:
        result.append(current)
    return result if result else [""]


def _flush_events():
    """입력 이벤트 큐 비우기"""
    for _ in tcod.event.get():
        pass
    try:
        import pygame
        pygame.event.pump()
        pygame.event.clear()
    except Exception:
        pass
    unified_input_handler.clear_input_state()


def _dialog_pointer_regions(
    bx: int,
    box_y: int,
    box_width: int,
    box_height: int,
    display_line_count: int,
    choices: list[NPCChoice] | None,
    typing_done: bool,
) -> tuple[PointerRegion, ...]:
    if choices and typing_done:
        choice_y = box_y + 2 + display_line_count + 1
        return tuple(
            PointerRegion(
                region_id=f"choice:{index}",
                x=bx + 4,
                y=choice_y + index,
                width=max(4, box_width - 8),
                height=1,
                command=GameAction.CONFIRM,
                tooltip=choice.text,
            )
            for index, choice in enumerate(choices)
        )
    return (
        PointerRegion(
            region_id="advance",
            x=bx,
            y=box_y,
            width=box_width,
            height=box_height,
            command=GameAction.CONFIRM,
            tooltip="대화를 진행합니다" if typing_done else "타이핑을 즉시 완료합니다",
        ),
    )


def _dialog_pointer_result(
    event: PointerEvent,
    regions: tuple[PointerRegion, ...],
    has_choices: bool,
) -> DialogPointerResult:
    dispatcher = PointerDispatcher(regions)
    dispatch = dispatcher.dispatch(event)
    region = dispatcher.region_at(event.position)
    region_id = dispatch.hovered_region_id or (region.region_id if region else None)
    hovered_choice = _choice_index_from_region(region_id)
    if event.kind is PointerEventKind.HOVER:
        return DialogPointerResult(hovered_choice=hovered_choice, tooltip=dispatch.tooltip)
    if event.kind is PointerEventKind.WHEEL:
        return DialogPointerResult(action=dispatch.action)
    if event.kind is not PointerEventKind.CLICK:
        return DialogPointerResult()
    if event.button is PointerButton.RIGHT:
        return DialogPointerResult(action=GameAction.CANCEL)
    if event.button is not PointerButton.LEFT:
        return DialogPointerResult()
    if has_choices and hovered_choice is not None:
        return DialogPointerResult(action=GameAction.CONFIRM, choice_index=hovered_choice)
    return DialogPointerResult(action=GameAction.CONFIRM)


def _choice_index_from_region(region_id: str | None) -> int | None:
    if region_id is None or not region_id.startswith("choice:"):
        return None
    return int(region_id.split(":", 1)[1])


def _poll_action(regions: tuple[PointerRegion, ...], has_choices: bool):
    """키보드/게임패드 액션 폴링. (action, quit_requested) 반환"""
    try:
        import pygame
        pygame.event.pump()
    except Exception:
        pass

    kbd_action = None
    quit_req = False

    for event in tcod.event.get():
        action = unified_input_handler.process_tcod_event(event)
        if action:
            kbd_action = action
        pointer_event = unified_input_handler.process_pointer_event(event)
        if pointer_event is not None:
            pointer_result = _dialog_pointer_result(pointer_event, regions, has_choices)
            if pointer_result.action is not None or pointer_result.hovered_choice is not None or pointer_result.tooltip:
                return pointer_result, quit_req
        if isinstance(event, tcod.event.Quit):
            quit_req = True

    if kbd_action:
        return DialogPointerResult(action=kbd_action), quit_req

    gp = unified_input_handler.get_action()
    return DialogPointerResult(action=gp), quit_req


def run_npc_dialog(
    console: tcod.console.Console,
    context: tcod.context.Context,
    npc_name: str = "???",
    dialog_lines: Optional[List[str]] = None,
    choices: Optional[List['NPCChoice']] = None,
    effect: str = None,
    npc_id: str = None,
) -> Optional[int]:
    """show_npc_dialog 호환 래퍼 - dialog_lines(리스트)를 받아 처리"""
    if dialog_lines:
        for line in dialog_lines:
            show_npc_dialog(console, context, npc_name=npc_name,
                            dialog_text=line, choices=None, effect=effect, npc_id=npc_id)
    if choices:
        return show_npc_dialog(console, context, npc_name=npc_name,
                               dialog_text="", choices=choices, effect=effect, npc_id=npc_id)
    return None


def show_npc_dialog(
    console: tcod.console.Console,
    context: tcod.context.Context,
    npc_name: str,
    dialog_text: str,
    choices: Optional[List[NPCChoice]] = None,
    effect: str = None,       # "shake" | "flash" | "slow" | None
    npc_id: str = None,       # NPC 색상용 ID
) -> Optional[int]:
    """
    NPC 대화 창 표시 (타이핑 효과 + 연출)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        npc_name: NPC 이름
        dialog_text: 대화 텍스트 (여러 줄 가능, \\n으로 구분)
        choices: 선택지 리스트 (None이면 확인만 가능)
        effect: 특수 효과 ("shake", "flash", "slow")
        npc_id: NPC 색상용 ID

    Returns:
        선택된 선택지 인덱스 (None이면 취소)
    """
    # NPC 이름 색상
    name_color = NPC_NAME_COLORS.get(npc_id, Colors.UI_BORDER) if npc_id else Colors.UI_BORDER

    # 텍스트 준비
    raw_lines = dialog_text.split('\n')
    has_choices = choices and len(choices) > 0
    selected_index = 0 if has_choices else None

    # 박스 크기 계산
    max_w = max(len(l) for l in raw_lines) if raw_lines else 0
    if has_choices:
        max_w = max(max_w, max(len(c.text) for c in choices))
    box_width = min(max_w + 10, console.width - 20)
    inner_w = box_width - 4

    display_lines = []
    for line in raw_lines:
        display_lines.extend(_wrap_text(line, inner_w))

    total_chars = sum(len(dl) for dl in display_lines)

    box_height = len(display_lines) + 6
    if has_choices:
        box_height += len(choices) + 1

    box_x = (console.width - box_width) // 2
    box_y = (console.height - box_height) // 2

    # 타이핑 속도 (slow 효과: 2배 느림)
    typing_speed = 0.06 if effect == "slow" else 0.03

    # 입력 큐 비우기
    _flush_events()
    time.sleep(0.1)
    _flush_events()

    # 상태 변수
    revealed = 0
    last_char_time = time.time()
    typing_done = False

    # shake 효과 상태
    shake_start = time.time() if effect == "shake" else 0.0
    shake_dur = 0.3

    # flash 효과 상태
    flash_start = 0.0
    flash_fired = False
    flash_dur = 0.2

    # ▼ 깜빡임 상태
    ind_timer = time.time()
    ind_visible = True
    hovered_choice: int | None = None
    pointer_tooltip: str | None = None

    while True:
        now = time.time()

        # --- 타이핑 진행 ---
        if not typing_done:
            dt = now - last_char_time
            if dt >= typing_speed:
                add = int(dt / typing_speed)
                old_rev = revealed
                revealed = min(revealed + add, total_chars)
                last_char_time = now

                # 5글자마다 효과음
                if revealed // 5 > old_rev // 5:
                    play_sfx("ui", "cursor_move")

                if revealed >= total_chars:
                    typing_done = True
                    if effect == "flash" and not flash_fired:
                        flash_start = now
                        flash_fired = True

        # shake 오프셋 계산
        shake_ox = 0
        if effect == "shake" and (now - shake_start) < shake_dur:
            shake_ox = [1, -1, 1, -1, 1, -1][int((now - shake_start) / 0.05) % 6]

        # flash 텍스트 색상
        txt_color = Colors.UI_TEXT
        if effect == "flash" and flash_fired and (now - flash_start) < flash_dur:
            txt_color = (255, 255, 255)

        # ▼ 깜빡임 토글 (0.5초 주기)
        if typing_done and (now - ind_timer) >= 0.5:
            ind_visible = not ind_visible
            ind_timer = now

        # === 렌더링 ===
        bx = box_x + shake_ox

        # 반투명 배경
        for dy in range(box_height):
            for dx in range(box_width):
                px_ = bx + dx
                if 0 <= px_ < console.width:
                    console.print(px_, box_y + dy, " ", bg=(20, 20, 20))

        # 대화 상자 프레임
        console.draw_frame(
            bx, box_y, box_width, box_height,
            "",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # NPC 이름 (고유 색상)
        console.print(bx + 2, box_y, f" {npc_name} ", fg=name_color)

        # 대화 텍스트 (타이핑 효과)
        y = box_y + 2
        counted = 0
        for dline in display_lines:
            vis = min(len(dline), max(0, revealed - counted))
            if vis > 0:
                console.print(bx + 2, y, dline[:vis], fg=txt_color)
            counted += len(dline)
            y += 1

        # 선택지 (타이핑 완료 후)
        if has_choices and typing_done:
            yc = box_y + 2 + len(display_lines) + 1
            for i, ch in enumerate(choices):
                is_hovered = i == hovered_choice
                is_selected = i == selected_index
                if is_selected:
                    console.draw_rect(bx + 3, yc, box_width - 6, 1, ord(" "), bg=rgb("state.active"))
                elif is_hovered:
                    console.draw_rect(bx + 3, yc, box_width - 6, 1, ord(" "), bg=rgb("state.hover"))
                pfx = "> " if is_selected else ("~ " if is_hovered else "  ")
                fg = Colors.UI_TEXT_SELECTED if is_selected else (rgb("state.focus") if is_hovered else Colors.UI_TEXT)
                console.print(bx + 4, yc, f"{pfx}{ch.text}", fg=fg)
                yc += 1

        # ▼ 깜빡이는 진행 표시기
        if typing_done and ind_visible and not has_choices:
            console.print(
                bx + box_width - 3, box_y + box_height - 3,
                "▼", fg=(255, 255, 100)
            )

        # 안내 메시지
        hy = box_y + box_height - 2
        if has_choices and typing_done:
            ht = "↑↓/Wheel: 선택  Left/Z: 확인  Right/X: 취소"
        elif typing_done:
            ht = "Left/Z: 확인  Right/X: 취소"
        else:
            ht = "Left/Z: 스킵  Right/X: 취소"
        console.print(bx + (box_width - len(ht)) // 2, hy, ht, fg=Colors.GRAY)
        if pointer_tooltip:
            tip = pointer_tooltip[: box_width - 6]
            console.print(bx + 3, max(box_y + 1, hy - 1), tip, fg=rgb("accent.amber"), bg=rgb("state.tooltip"))

        context.present(console)

        # === 입력 처리 ===
        regions = _dialog_pointer_regions(bx, box_y, box_width, box_height, len(display_lines), choices, typing_done)
        pointer_result, quit_r = _poll_action(regions, bool(has_choices))
        action = pointer_result.action
        if pointer_result.hovered_choice is not None:
            hovered_choice = pointer_result.hovered_choice
            selected_index = pointer_result.hovered_choice
        pointer_tooltip = pointer_result.tooltip
        if pointer_result.choice_index is not None:
            selected_index = pointer_result.choice_index
        if quit_r:
            return None

        if not typing_done:
            # 타이핑 중: Z로 즉시 완료 (스킵)
            if action == GameAction.CONFIRM:
                revealed = total_chars
                typing_done = True
                if effect == "flash" and not flash_fired:
                    flash_start = time.time()
                    flash_fired = True
            elif action in (GameAction.CANCEL, GameAction.ESCAPE):
                play_sfx("ui", "cursor_cancel")
                return None
        else:
            # 타이핑 완료: 입력 대기
            if has_choices:
                if action == GameAction.MOVE_UP:
                    selected_index = max(0, selected_index - 1)
                elif action == GameAction.MOVE_DOWN:
                    selected_index = min(len(choices) - 1, selected_index + 1)
                elif action == GameAction.CONFIRM:
                    play_sfx("ui", "cursor_confirm")
                    if choices[selected_index].callback:
                        try:
                            choices[selected_index].callback()
                        except Exception as e:
                            logger.error(f"NPC 선택지 콜백 오류: {e}")
                    return selected_index
                elif action in (GameAction.CANCEL, GameAction.ESCAPE):
                    play_sfx("ui", "cursor_cancel")
                    return None
            else:
                if action == GameAction.CONFIRM:
                    play_sfx("ui", "cursor_confirm")
                    return 0
                elif action in (GameAction.CANCEL, GameAction.ESCAPE):
                    play_sfx("ui", "cursor_cancel")
                    return None

        time.sleep(0.016)


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
