"""
튜토리얼 시스템 v2
Dawn of Stellar

실제 던전 플레이 + 봇 조언자 방식
15층까지 가이드 모드로 진행
"""

import tcod
import tcod.console
import tcod.event
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from src.core.logger import get_logger, Loggers
from src.audio import play_bgm, play_sfx
from src.ui.input_handler import iter_game_input, poll_game_input, GameAction

# 새로운 튜토리얼 시스템
from src.tutorial.tutorial_bot import (
    TutorialBot, 
    get_tutorial_bot, 
    reset_tutorial_bot,
    BotMessage,
    BotPersonality
)
from src.tutorial.tutorial_mode import (
    TutorialModeConfig,
    TutorialProgress,
    get_tutorial_config,
    get_tutorial_progress,
    start_tutorial_mode,
    end_tutorial_mode,
    is_tutorial_mode,
)


logger = get_logger(Loggers.SYSTEM)


# =============================================================================
# 색상 상수
# =============================================================================

class Colors:
    """UI 색상"""
    TITLE = (255, 215, 0)
    BOT_SELENA = (0, 200, 255)
    BOT_KARNOS = (255, 100, 100)
    BOT_MIRA = (255, 200, 100)
    HINT = (150, 150, 150)
    WARNING = (255, 200, 0)
    NORMAL = (255, 255, 255)


BOT_COLORS = {
    BotPersonality.SELENA: Colors.BOT_SELENA,
    BotPersonality.KARNOS: Colors.BOT_KARNOS,
    BotPersonality.MIRA: Colors.BOT_MIRA,
}

BOT_NAMES = {
    BotPersonality.SELENA: "셀레나",
    BotPersonality.KARNOS: "카르노",
    BotPersonality.MIRA: "미라",
}


# =============================================================================
# 봇 UI 렌더러
# =============================================================================

class BotUIRenderer:
    """
    봇 조언 UI 렌더러
    
    화면 하단에 봇 메시지를 표시합니다.
    """
    
    BOX_HEIGHT = 4
    BOX_PADDING = 1
    
    def __init__(self, console: tcod.console.Console):
        self.console = console
        self.bot = get_tutorial_bot()
    
    def render(self):
        """봇 메시지 렌더링"""
        if not is_tutorial_mode():
            return
        
        message = self.bot.get_current_message()
        if not message:
            return
        
        # 박스 위치 계산 (화면 하단)
        box_y = self.console.height - self.BOX_HEIGHT - 1
        box_width = self.console.width - 4
        box_x = 2
        
        # 반투명 배경 (어두운 색)
        for y in range(box_y, box_y + self.BOX_HEIGHT):
            for x in range(box_x, box_x + box_width):
                self.console.rgb["bg"][y, x] = (20, 20, 40)
        
        # 테두리
        border_color = BOT_COLORS.get(message.personality, Colors.BOT_SELENA)
        self.console.draw_frame(
            box_x, box_y, box_width, self.BOX_HEIGHT,
            fg=border_color,
            bg=(20, 20, 40)
        )
        
        # NPC 이름
        npc_name = BOT_NAMES.get(message.personality, "봇")
        self.console.print(
            box_x + 2, box_y,
            f"[ {npc_name} ]",
            fg=border_color
        )
        
        # 메시지 텍스트 (줄바꿈 처리)
        text = message.text
        max_width = box_width - 4
        
        # 간단한 줄바꿈
        lines = []
        current_line = ""
        for word in text.split():
            test = f"{current_line} {word}".strip()
            if len(test) <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        # 텍스트 출력 (최대 2줄)
        for i, line in enumerate(lines[:2]):
            self.console.print(
                box_x + 2, box_y + 1 + i,
                line,
                fg=Colors.NORMAL
            )


# =============================================================================
# 튜토리얼 시작 화면
# =============================================================================

def show_tutorial_intro(console: tcod.console.Console, 
                        context: tcod.context.Context) -> bool:
    """
    튜토리얼 시작 화면 표시
    
    Returns:
        True: 시작, False: 취소
    """
    console.clear()
    
    # 타이틀
    title = "★ 튜토리얼 모드 ★"
    console.print(
        (console.width - len(title)) // 2,
        console.height // 2 - 8,
        title,
        fg=Colors.TITLE
    )
    
    # 설명
    lines = [
        "",
        "실제 던전을 플레이하며 게임을 배웁니다.",
        "",
        "=== 튜토리얼 모드 특징 ===",
        "",
        "• 적이 약하고 회복이 많습니다",
        "• 패배해도 자동으로 부활합니다",
        "• 똑똑한 봇이 실시간으로 조언합니다",
        "• 15층까지 클리어하면 완료!",
        "",
        "=== 보상 ===",
        "",
        "• 완료 시 직업 1개 해금",
        "• 별의 파편 보너스",
        "",
        "",
        "[Z] 시작  [ESC] 취소"
    ]
    
    y = console.height // 2 - 5
    for line in lines:
        color = Colors.NORMAL
        if "===" in line:
            color = Colors.WARNING
        elif "•" in line:
            color = Colors.BOT_SELENA
        elif "[Z]" in line:
            color = Colors.HINT
        
        console.print(
            (console.width - len(line)) // 2,
            y,
            line,
            fg=color
        )
        y += 1
    
    context.present(console)
    
    # 입력 대기
    while True:
        for action, event in iter_game_input():
            if event and isinstance(event, tcod.event.Quit):
                return False
            if action == GameAction.CONFIRM:
                return True
            if action in (GameAction.CANCEL, GameAction.ESCAPE):
                return False


def show_tutorial_complete(console: tcod.console.Console,
                           context: tcod.context.Context):
    """튜토리얼 완료 화면"""
    progress = get_tutorial_progress()
    
    console.clear()
    
    # 타이틀
    title = "★ 튜토리얼 완료! ★"
    console.print(
        (console.width - len(title)) // 2,
        console.height // 2 - 8,
        title,
        fg=Colors.TITLE
    )
    
    # 통계
    lines = [
        "",
        f"클리어 층수: {len(progress.cleared_floors)}층",
        f"총 전투: {progress.total_combats}회",
        f"승리: {progress.victories}회",
        f"부활 사용: {progress.revives_used}회",
        "",
        "=== 획득 보상 ===",
        "",
        "• 직업 해금: 시간술사",
        "• 별의 파편: 50개",
        "",
        "",
        "이제 본격적인 던전 탐험을 시작하세요!",
        "",
        "[Z] 메인 메뉴로"
    ]
    
    y = console.height // 2 - 4
    for line in lines:
        color = Colors.NORMAL
        if "===" in line:
            color = Colors.WARNING
        elif "•" in line:
            color = Colors.BOT_SELENA
        elif "클리어" in line or "승리" in line:
            color = Colors.TITLE
        
        console.print(
            (console.width - len(line)) // 2,
            y,
            line,
            fg=color
        )
        y += 1
    
    try:
        play_sfx("me", "Fanfare1")
    except:
        pass
    
    context.present(console)
    
    # 입력 대기
    while True:
        for action, event in iter_game_input():
            if event and isinstance(event, tcod.event.Quit):
                return
            if action == GameAction.CONFIRM:
                return


# =============================================================================
# 튜토리얼 모드 시작/종료
# =============================================================================

def run_story_tutorial(console: tcod.console.Console,
                       context: tcod.context.Context) -> Dict[str, Any]:
    """
    튜토리얼 모드 시작
    
    실제 던전으로 진입하되 튜토리얼 설정 적용
    
    Returns:
        결과 딕셔너리
    """
    result = {
        "completed": False,
        "job_unlocked": None,
        "rewards": {"stellar_fragments": 0}
    }
    
    # 시작 화면
    if not show_tutorial_intro(console, context):
        return result
    
    # 튜토리얼 모드 활성화
    config = start_tutorial_mode()
    bot = reset_tutorial_bot()
    
    logger.info("=== 튜토리얼 모드 시작 ===")
    
    # 실제 게임 시작은 main.py에서 처리
    # 여기서는 플래그만 설정하고 반환
    result["tutorial_started"] = True
    result["config"] = config.to_dict()
    
    return result


def on_tutorial_complete() -> Dict[str, Any]:
    """
    튜토리얼 완료 처리
    
    15층 클리어 시 호출
    """
    result = {
        "completed": True,
        "job_unlocked": "time_mage",
        "rewards": {"stellar_fragments": 50}
    }
    
    # 보상 적용 (exactly-once: 이미 해금 시 무지급)
    try:
        from src.persistence.meta_progress import (
            get_meta_progress,
            save_meta_progress,
        )
        meta = get_meta_progress()

        if meta.grant_job_unlock_reward("time_mage", 50):
            save_meta_progress()
            logger.info("직업 해금 + 별의 파편 +50: time_mage")
    except Exception as e:
        logger.error(f"보상 적용 실패: {e}")
    
    # 튜토리얼 모드 종료 (completed=True로 재입장 방지)
    end_tutorial_mode(completed=True)

    logger.info("=== 튜토리얼 완료 ===")
    
    return result


# =============================================================================
# 하위 호환성
# =============================================================================

# 기존 코드와의 호환성을 위한 별칭
StoryTutorialRunner = None  # 더 이상 사용하지 않음
StoryTutorialPlayer = None
YAMLStoryRunner = None

def get_story_runner():
    return None

def initialize_story_runner(*args, **kwargs):
    return None
