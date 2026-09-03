"""
퀘스트 목록 UI

현재 진행 중인 퀘스트와 진행 상황을 보여줌
"""

import tcod.console
import tcod.event
from typing import List, Any

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("quest_list_ui")


def quest_list_pointer_regions(active_quests: List[Any], scroll_offset: int, max_visible: int, width: int) -> tuple[PointerRegion, ...]:
    regions: list[PointerRegion] = []
    for index, quest in enumerate(active_quests[scroll_offset:scroll_offset + max_visible]):
        actual_index = scroll_offset + index
        enabled = bool(getattr(quest, "is_complete", False))
        regions.append(PointerRegion(f"quest:{actual_index}", 5, 7 + index * 6, width - 10, 5, GameAction.CONFIRM, quest_list_tooltip(quest, enabled), enabled=enabled))
    return tuple(regions)


def quest_list_tooltip(quest: Any, enabled: bool) -> str:
    status = "보상 수령 가능" if enabled else "완료 조건을 아직 만족하지 않았습니다."
    description = getattr(quest, "description", "")
    return " | ".join(part for part in (getattr(quest, "name", "퀘스트"), description, status) if part)


def handle_quest_list_pointer_event(event: PointerEvent, regions: tuple[PointerRegion, ...]) -> PointerDispatchResult:
    if event.kind is PointerEventKind.WHEEL:
        action = GameAction.MOVE_UP if event.wheel_delta > 0 else GameAction.MOVE_DOWN if event.wheel_delta < 0 else None
        return PointerDispatchResult(event=event, action=action)
    if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
        return PointerDispatchResult(event=event, action=GameAction.CANCEL, value=True)
    result = PointerDispatcher(regions).dispatch(event)
    region = next((candidate for candidate in regions if candidate.contains(event.position)), None)
    region_id = result.hovered_region_id or (region.region_id if region else None)
    if event.kind is PointerEventKind.HOVER and region_id and result.tooltip is None:
        return PointerDispatchResult(event=event, hovered_region_id=region_id, tooltip=region.tooltip if region else None)
    if event.kind is PointerEventKind.CLICK and event.button is PointerButton.LEFT:
        return PointerDispatchResult(event=event, action=GameAction.CONFIRM, value=region.enabled if region else False, hovered_region_id=region_id, tooltip=result.tooltip if result.tooltip else region.tooltip if region else None)
    return result


def open_quest_list(
    console: tcod.console.Console,
    context: tcod.context.Context,
    quest_manager: Any,
    player: Any = None,
    inventory: Any = None
):
    """
    퀘스트 목록 UI 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        quest_manager: QuestManager 인스턴스
        player: 플레이어 객체 (보상 수령용)
        inventory: 인벤토리 객체 (골드 보상용)
    """
    active_quests = quest_manager.get_active_quests()
    cursor = 0
    scroll_offset = 0
    max_visible = 8  # 간격이 커져서 보이는 개수 감소
    
    # 퀘스트 목록을 열 때마다 완료 체크 (안전장치)
    quest_manager.check_all_quests_completion()
    active_quests = quest_manager.get_active_quests()  # 완료 체크 후 다시 가져오기
    
    logger.info(f"퀘스트 목록 열기 - 활성 퀘스트: {len(active_quests)}개")

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        render_space_background(console, console.width, console.height)
        
        # 제목
        title = "=== 진행 중인 퀘스트 ==="
        console.print((console.width - len(title)) // 2, 2, title, fg=(255, 215, 0))
        
        # 퀘스트 개수 표시
        count_text = f"({len(active_quests)} / {quest_manager.max_active_quests})"
        console.print((console.width - len(count_text)) // 2, 4, count_text, fg=(150, 150, 150))
        
        if not active_quests:
            message = "진행 중인 퀘스트가 없습니다."
            console.print((console.width - len(message)) // 2, 10, message, fg=(150, 150, 150))
        else:
            # 퀘스트 목록
            list_y = 7
            visible_quests = active_quests[scroll_offset:scroll_offset + max_visible]
            
            for i, quest in enumerate(visible_quests):
                y = list_y + i * 6  # 간격을 5에서 6으로 증가
                cursor_index = scroll_offset + i
                
                # 커서
                if cursor_index == cursor:
                    console.print(3, y, "►", fg=(255, 255, 100))
                
                # 퀘스트 이름 (길이 제한 - 진행도와 겹치지 않도록)
                name_color = (255, 255, 100) if cursor_index == cursor else (200, 200, 200)
                # 퀘스트 이름 길이 제한 (진행도와 겹치지 않도록 충분히 짧게)
                max_name_width = min(45, console.width - 20)
                quest_name = quest.name[:max_name_width] if len(quest.name) > max_name_width else quest.name
                console.print(5, y, quest_name, fg=name_color)
                
                # 퀘스트 타입 및 난이도
                type_text = f"[{quest.quest_type.value}] {quest.difficulty.value.upper()}"
                console.print(5, y + 1, type_text, fg=(150, 150, 150))
                
                # 진행 상황 (타입/레벨 아래에 별도 줄로 표시 - y + 3에서 확실히 분리)
                progress_parts = []
                if hasattr(quest, 'objectives'):
                    # objectives를 사용하는 경우
                    for obj in quest.objectives:
                        progress_parts.append(f"{obj.description}: {obj.progress_text}")
                elif hasattr(quest, 'progress'):
                    # progress 딕셔너리를 사용하는 경우 (레거시)
                    for key, value in quest.progress.items():
                        if hasattr(quest, 'requirements') and key in quest.requirements:
                            required = quest.requirements[key]
                            current = value
                            progress_parts.append(f"{key}: {current}/{required}")

                if quest.is_complete:
                    console.print(5, y + 3, " 완료됨 - Z키로 보상 수령", fg=(255, 215, 0))
                elif progress_parts:
                    # 진행도 텍스트 앞에 라벨 추가하여 명확하게 표시
                    progress_text = "진행: " + " | ".join(progress_parts)
                    # 텍스트가 너무 길면 자르기
                    max_progress_width = console.width - 10
                    if len(progress_text) > max_progress_width:
                        progress_text = progress_text[:max_progress_width - 3] + "..."
                    # 진행도를 y + 3으로 이동하여 퀘스트 이름(y)과 타입(y+1)과 확실히 분리
                    console.print(5, y + 3, progress_text, fg=(100, 200, 100))
                
                # 보상 (진행도 아래로 이동)
                if hasattr(quest, 'rewards'):
                    rewards = quest.rewards
                    reward_text = f"보상: "
                    reward_parts = []
                    if 'gold' in rewards and rewards['gold'] > 0:
                        reward_parts.append(f"{rewards['gold']}G")
                    if 'exp' in rewards and rewards['exp'] > 0:
                        reward_parts.append(f"{rewards['exp']}EXP")
                    if 'star_fragments' in rewards and rewards['star_fragments'] > 0:
                        reward_parts.append(f"{rewards['star_fragments']}★")
                    if reward_parts:
                        reward_text += ", ".join(reward_parts)
                        # 진행도가 있으면 y + 4, 없으면 y + 3
                        reward_y = y + 4 if progress_parts else y + 3
                        console.print(5, reward_y, reward_text, fg=(255, 215, 0))
        
        # 도움말
        help_text = "↑↓: 선택  Z: 보상 수령  X: 닫기"
        console.print((console.width - len(help_text)) // 2, console.height - 2, help_text, fg=Colors.GRAY)
        
        context.present(console)
        
        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass
        
        # 입력 처리 함수
        def process_action(action):
            nonlocal cursor, scroll_offset, active_quests
            if action == GameAction.MOVE_UP:
                if active_quests:
                    cursor = max(0, cursor - 1)
                    if cursor < scroll_offset:
                        scroll_offset = cursor
                    play_sfx("ui", "cursor_move")
            elif action == GameAction.MOVE_DOWN:
                if active_quests:
                    cursor = min(len(active_quests) - 1, cursor + 1)
                    if cursor >= scroll_offset + max_visible:
                        scroll_offset = cursor - max_visible + 1
                    play_sfx("ui", "cursor_move")
            elif action == GameAction.CONFIRM:
                if active_quests and 0 <= cursor < len(active_quests):
                    quest = active_quests[cursor]
                    if quest.is_complete and player is not None:
                        if quest_manager.complete_quest(quest.quest_id, player, inventory):
                            active_quests = quest_manager.get_active_quests()
                            cursor = min(cursor, max(0, len(active_quests) - 1))
                            play_sfx("ui", "item_get")
                            logger.info(f"퀘스트 완료 보상 수령: {quest.name} - 보상: {quest.reward}")
                        else:
                            play_sfx("ui", "cursor_cancel")
                    else:
                        play_sfx("ui", "cursor_cancel")
                else:
                    play_sfx("ui", "cursor_cancel")
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                play_sfx("ui", "cursor_cancel")
                return True
            return False
        
        # 키보드 입력 처리
        keyboard_processed = False
        pointer_regions = quest_list_pointer_regions(active_quests, scroll_offset, max_visible, console.width)
        for event in tcod.event.get():
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event is not None:
                pointer_result = handle_quest_list_pointer_event(pointer_event, pointer_regions)
                if pointer_result.hovered_region_id and pointer_result.hovered_region_id.startswith("quest:"):
                    cursor = int(pointer_result.hovered_region_id.split(":", 1)[1])
                    if cursor < scroll_offset:
                        scroll_offset = cursor
                if pointer_result.action:
                    keyboard_processed = True
                    if process_action(pointer_result.action):
                        return
                continue

            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                keyboard_processed = True
                if process_action(action):
                    return
            
            if isinstance(event, tcod.event.Quit):
                return
        
        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if process_action(gamepad_action):
                    return
        
        # CPU 사용률 낮추기
        import time
        time.sleep(0.01)
