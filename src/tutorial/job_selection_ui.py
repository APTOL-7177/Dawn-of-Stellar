"""
튜토리얼 완료 직업 선택 UI
Dawn of Stellar - 시공의 여명

튜토리얼 완료 보상으로 해금 직업을 선택하는 UI입니다.
"""

import tcod
import tcod.console
import tcod.event
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from src.core.event_bus import event_bus
from src.core.logger import get_logger, Loggers
from src.ui.input_handler import unified_input_handler, GameAction


logger = get_logger(Loggers.UI)


@dataclass
class JobChoiceInfo:
    """직업 선택지 정보"""
    id: str
    name: str
    description: str
    story_reason: str
    recommended: bool = False
    preview_skills: List[str] = None
    
    def __post_init__(self):
        if self.preview_skills is None:
            self.preview_skills = []


class JobSelectionUI:
    """
    직업 선택 UI
    
    튜토리얼 완료 시 표시되는 직업 선택 화면입니다.
    시간술사가 기본 추천으로 표시됩니다.
    """
    
    # 색상 상수
    COLOR_TITLE = (255, 215, 0)  # 금색
    COLOR_SELECTED = (0, 255, 255)  # 시안
    COLOR_NORMAL = (200, 200, 200)
    COLOR_RECOMMENDED = (0, 255, 0)  # 녹색
    COLOR_DESCRIPTION = (180, 180, 180)
    COLOR_STORY = (255, 200, 100)  # 주황색
    COLOR_SKILL = (100, 200, 255)  # 하늘색
    
    def __init__(
        self,
        console: tcod.console.Console,
        context: tcod.context.Context,
        choices: List[JobChoiceInfo],
        timeout: float = 30.0
    ):
        self.console = console
        self.context = context
        self.choices = choices
        self.timeout = timeout
        
        self.screen_width = console.width
        self.screen_height = console.height
        
        self.selected_index = 0
        self.confirmed = False
        self.timed_out = False
        self.start_time = 0.0
        
        # 추천 직업을 기본 선택으로
        for i, choice in enumerate(choices):
            if choice.recommended:
                self.selected_index = i
                break
    
    def show(self, on_select: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        직업 선택 UI 표시
        
        Args:
            on_select: 선택 완료 시 콜백
            
        Returns:
            선택된 직업 ID (None이면 타임아웃으로 기본 선택)
        """
        self.start_time = time.time()
        
        logger.info("직업 선택 UI 표시")
        
        while not self.confirmed:
            # 타임아웃 확인
            elapsed = time.time() - self.start_time
            if elapsed >= self.timeout:
                self.timed_out = True
                break
            
            # 화면 렌더링
            self._render(self.timeout - elapsed)
            self.context.present(self.console)
            
            # 입력 처리
            for event in tcod.event.wait(timeout=0.1):
                if isinstance(event, tcod.event.Quit):
                    return None
                    
                if isinstance(event, tcod.event.KeyDown):
                    self._handle_key(event)
        
        # 선택된 직업
        selected_job = self.choices[self.selected_index].id
        
        if self.timed_out:
            logger.info(f"타임아웃으로 기본 선택: {selected_job}")
        else:
            logger.info(f"직업 선택 완료: {selected_job}")
        
        # 콜백 호출
        if on_select:
            on_select(selected_job)
        
        # 선택 완료 연출
        self._show_selection_effect()
        
        return selected_job
    
    def _render(self, remaining_time: float) -> None:
        """화면 렌더링"""
        self.console.clear()
        
        # 배경 효과 (시공 느낌)
        self._draw_background()
        
        # 타이틀
        title = "★ 각성할 힘을 선택하세요 ★"
        self.console.print(
            (self.screen_width - len(title)) // 2,
            3,
            title,
            fg=self.COLOR_TITLE
        )
        
        # 설명
        desc = "튜토리얼 완료 보상으로 해금 직업 1개를 무료로 획득합니다."
        self.console.print(
            (self.screen_width - len(desc)) // 2,
            5,
            desc,
            fg=self.COLOR_DESCRIPTION
        )
        
        # 남은 시간
        time_text = f"남은 시간: {int(remaining_time)}초"
        time_color = (255, 255, 0) if remaining_time > 10 else (255, 100, 100)
        self.console.print(
            self.screen_width - len(time_text) - 3,
            3,
            time_text,
            fg=time_color
        )
        
        # 선택지 박스
        box_width = 60
        box_height = len(self.choices) * 8 + 4
        box_x = (self.screen_width - box_width) // 2
        box_y = 8
        
        self._draw_box(box_x, box_y, box_width, box_height)
        
        # 각 선택지 렌더링
        for i, choice in enumerate(self.choices):
            self._render_choice(choice, i, box_x + 2, box_y + 2 + i * 8)
        
        # 조작 안내
        help_y = box_y + box_height + 2
        self.console.print(
            box_x,
            help_y,
            "↑↓: 선택 이동  Enter: 확정  (시간 초과 시 추천 직업 자동 선택)",
            fg=(150, 150, 150)
        )
    
    def _render_choice(
        self,
        choice: JobChoiceInfo,
        index: int,
        x: int,
        y: int
    ) -> None:
        """선택지 렌더링"""
        is_selected = index == self.selected_index
        
        # 선택 표시
        marker = "▶ " if is_selected else "  "
        
        # 직업 이름
        name_color = self.COLOR_SELECTED if is_selected else self.COLOR_NORMAL
        if choice.recommended:
            name_text = f"{marker}{choice.name} [추천]"
            if not is_selected:
                name_color = self.COLOR_RECOMMENDED
        else:
            name_text = f"{marker}{choice.name}"
        
        self.console.print(x, y, name_text, fg=name_color)
        
        # 설명 (선택된 경우만 상세)
        if is_selected:
            # 설명
            desc_lines = self._wrap_text(choice.description, 50)
            for i, line in enumerate(desc_lines[:2]):
                self.console.print(x + 2, y + 1 + i, line, fg=self.COLOR_DESCRIPTION)
            
            # 스토리 이유
            story_y = y + 3
            self.console.print(
                x + 2,
                story_y,
                f"◆ {choice.story_reason}",
                fg=self.COLOR_STORY
            )
            
            # 미리보기 스킬
            if choice.preview_skills:
                skill_y = story_y + 2
                self.console.print(x + 2, skill_y, "주요 스킬:", fg=self.COLOR_SKILL)
                skills_text = ", ".join(choice.preview_skills[:3])
                self.console.print(x + 12, skill_y, skills_text, fg=self.COLOR_SKILL)
        else:
            # 간단한 설명만
            short_desc = choice.description.split('\n')[0][:45]
            self.console.print(x + 2, y + 1, short_desc + "...", fg=(120, 120, 120))
    
    def _draw_background(self) -> None:
        """배경 효과"""
        import random
        
        # 시공 파티클 효과
        for _ in range(20):
            x = random.randint(0, self.screen_width - 1)
            y = random.randint(0, self.screen_height - 1)
            char = random.choice(['·', '∙', '•', '◦'])
            color = (
                random.randint(30, 80),
                random.randint(50, 100),
                random.randint(80, 150)
            )
            self.console.print(x, y, char, fg=color)
    
    def _draw_box(self, x: int, y: int, width: int, height: int) -> None:
        """박스 그리기"""
        # 상단
        self.console.print(x, y, "╔" + "═" * (width - 2) + "╗", fg=self.COLOR_SELECTED)
        
        # 중간
        for i in range(1, height - 1):
            self.console.print(x, y + i, "║", fg=self.COLOR_SELECTED)
            self.console.print(x + width - 1, y + i, "║", fg=self.COLOR_SELECTED)
        
        # 하단
        self.console.print(x, y + height - 1, "╚" + "═" * (width - 2) + "╝", fg=self.COLOR_SELECTED)
    
    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """텍스트 줄바꿈"""
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())
        return lines
    
    def _handle_key(self, event: tcod.event.KeyDown) -> None:
        """키 입력 처리"""
        if event.sym == tcod.event.KeySym.UP:
            self.selected_index = (self.selected_index - 1) % len(self.choices)
        elif event.sym == tcod.event.KeySym.DOWN:
            self.selected_index = (self.selected_index + 1) % len(self.choices)
        elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            self.confirmed = True
        elif event.sym == tcod.event.KeySym.ESCAPE:
            # ESC는 추천 직업으로 자동 선택
            for i, choice in enumerate(self.choices):
                if choice.recommended:
                    self.selected_index = i
                    break
            self.confirmed = True
    
    def _show_selection_effect(self) -> None:
        """선택 완료 연출"""
        selected = self.choices[self.selected_index]
        
        # 화면 플래시
        for _ in range(3):
            self.console.clear()
            
            # 선택된 직업 이름 크게 표시
            title = f"★ {selected.name} 해금! ★"
            self.console.print(
                (self.screen_width - len(title)) // 2,
                self.screen_height // 2 - 2,
                title,
                fg=self.COLOR_TITLE
            )
            
            # 스토리 이유
            self.console.print(
                (self.screen_width - len(selected.story_reason)) // 2,
                self.screen_height // 2,
                selected.story_reason,
                fg=self.COLOR_STORY
            )
            
            self.context.present(self.console)
            time.sleep(0.3)
            
            self.console.clear()
            self.context.present(self.console)
            time.sleep(0.1)
        
        # 최종 표시
        self.console.clear()
        
        title = f"★ {selected.name} 해금! ★"
        self.console.print(
            (self.screen_width - len(title)) // 2,
            self.screen_height // 2 - 2,
            title,
            fg=self.COLOR_TITLE
        )
        
        self.console.print(
            (self.screen_width - len(selected.story_reason)) // 2,
            self.screen_height // 2,
            selected.story_reason,
            fg=self.COLOR_STORY
        )
        
        continue_text = "Press any key to continue..."
        self.console.print(
            (self.screen_width - len(continue_text)) // 2,
            self.screen_height // 2 + 4,
            continue_text,
            fg=(150, 150, 150)
        )
        
        self.context.present(self.console)
        
        # 아무 키나 대기
        for event in tcod.event.wait():
            if isinstance(event, (tcod.event.KeyDown, tcod.event.MouseButtonDown)):
                break


def show_job_selection(
    console: tcod.console.Console,
    context: tcod.context.Context,
    on_select: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """
    직업 선택 UI를 표시하는 헬퍼 함수
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        on_select: 선택 완료 콜백
        
    Returns:
        선택된 직업 ID
    """
    # 기본 선택지
    choices = [
        JobChoiceInfo(
            id="time_mage",
            name="시간술사",
            description="시간을 조작하여 전장을 지배하는 시공의 마법사.\n타임라인 시스템으로 과거/현재/미래를 넘나든다.",
            story_reason="시공 균열 봉인으로 시간의 힘이 각성했다.",
            recommended=True,
            preview_skills=["시간 정지 (Stop)", "시간 역행 (Rewind)", "가속 (Haste)"]
        ),
        JobChoiceInfo(
            id="dimensionist",
            name="차원술사",
            description="차원과 확률을 조작하는 시공간의 지배자.\n평행 우주의 힘으로 불가능을 가능으로.",
            story_reason="차원 항해 기술의 부작용으로 공간 조작력이 각성했다.",
            recommended=False,
            preview_skills=["차원 도약", "확률 왜곡", "평행 소환"]
        ),
        JobChoiceInfo(
            id="hacker",
            name="해커",
            description="시스템을 해킹하여 적을 약화시키는 전투 전문가.\n미래 기술로 적의 능력을 무력화.",
            story_reason="미래 기술과의 접촉으로 시스템 해킹 능력이 각성했다.",
            recommended=False,
            preview_skills=["시스템 침투", "바이러스", "방화벽"]
        )
    ]
    
    ui = JobSelectionUI(console, context, choices)
    return ui.show(on_select)
