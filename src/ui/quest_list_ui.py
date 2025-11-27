"""
퀘스트 목록 UI

현재 진행 중인 퀘스트와 진행 상황을 보여줌
"""

import tcod.console
import tcod.event
from typing import List, Any

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("quest_list_ui")


def open_quest_list(
    console: tcod.console.Console,
    context: tcod.context.Context,
    quest_manager: Any
):
    """
    퀘스트 목록 UI 열기
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        quest_manager: QuestManager 인스턴스
    """
    active_quests = quest_manager.get_active_quests()
    cursor = 0
    scroll_offset = 0
    max_visible = 8  # 간격이 커져서 보이는 개수 감소
    
    # 퀘스트 목록을 열 때마다 완료 체크 (안전장치)
    quest_manager.check_all_quests_completion()
    active_quests = quest_manager.get_active_quests()  # 완료 체크 후 다시 가져오기
    
    logger.info(f"퀘스트 목록 열기 - 활성 퀘스트: {len(active_quests)}개")
    
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
                
                if progress_parts:
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
        help_text = "↑↓: 선택  Z: 확인  X: 닫기"
        console.print((console.width - len(help_text)) // 2, console.height - 2, help_text, fg=Colors.GRAY)
        
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait():
            action = unified_input_handler.process_tcod_event(event)
            
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
            
            elif action == GameAction.CONFIRM or action == GameAction.CANCEL or action == GameAction.ESCAPE:
                play_sfx("ui", "cursor_cancel")
                return
            
            if isinstance(event, tcod.event.Quit):
                return
