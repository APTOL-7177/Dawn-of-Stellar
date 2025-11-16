"""
튜토리얼 UI - 튜토리얼 시각적 표현
"""

import tcod
import tcod.console
import time
import math
from typing import Tuple, Optional, List

from src.tutorial.tutorial_step import TutorialStep, TutorialMessage, UIHighlight
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.UI)


class TutorialUI:
    """
    튜토리얼 UI

    튜토리얼 메시지, 목표, 힌트, UI 강조 등을 화면에 표시합니다.
    """

    def __init__(self, console: tcod.console.Console):
        self.console = console
        self.screen_width = console.width
        self.screen_height = console.height

        # UI 설정
        self.panel_x = self.screen_width - 35
        self.panel_y = 2
        self.panel_width = 33
        self.panel_height = 20

        # 애니메이션
        self.pulse_time = 0.0
        self.typing_index = 0
        self.typing_timer = 0.0
        self.typing_speed = 0.05  # 초/글자

        # 현재 표시 중인 메시지
        self.current_message: Optional[TutorialMessage] = None
        self.message_complete = False

    def render_tutorial_panel(
        self,
        tutorial: TutorialStep,
        show_objective: bool = True,
        show_hints: bool = True
    ) -> None:
        """
        튜토리얼 패널 렌더링

        Args:
            tutorial: 현재 튜토리얼 단계
            show_objective: 목표 표시 여부
            show_hints: 힌트 표시 여부
        """
        # 패널 배경
        self._draw_panel_background()

        # 타이틀
        self._draw_title(tutorial.title)

        y = self.panel_y + 3

        # 목표
        if show_objective:
            y = self._draw_objective(tutorial.objective, y)

        # 진행률 (선택적)
        y = self._draw_progress_bar(tutorial, y)

        # 힌트
        if show_hints:
            hints = tutorial.get_current_hints()
            if hints:
                y = self._draw_hints(hints, y)

        # 스킵 안내
        y = self._draw_skip_instruction(tutorial.skippable, y)

    def _draw_panel_background(self) -> None:
        """패널 배경 그리기"""
        for y in range(self.panel_y, self.panel_y + self.panel_height):
            for x in range(self.panel_x, self.panel_x + self.panel_width):
                if y < self.screen_height and x < self.screen_width:
                    # 테두리
                    if (x == self.panel_x or x == self.panel_x + self.panel_width - 1 or
                        y == self.panel_y or y == self.panel_y + self.panel_height - 1):
                        self.console.print(x, y, "█", fg=(100, 100, 100), bg=(0, 0, 0))
                    else:
                        self.console.rgb["bg"][y, x] = (20, 20, 30)

    def _draw_title(self, title: str) -> None:
        """타이틀 그리기"""
        title_text = f"[ {title} ]"
        x = self.panel_x + (self.panel_width - len(title_text)) // 2
        self.console.print(x, self.panel_y + 1, title_text, fg=(255, 215, 0))

    def _draw_objective(self, objective: str, start_y: int) -> int:
        """목표 그리기"""
        self.console.print(self.panel_x + 2, start_y, "목표:", fg=(255, 255, 0))

        # 여러 줄로 나누기
        words = objective.split()
        lines = []
        current_line = ""
        max_width = self.panel_width - 4

        for word in words:
            if len(current_line) + len(word) + 1 <= max_width:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())

        y = start_y + 1
        for line in lines:
            if y < self.panel_y + self.panel_height - 1:
                self.console.print(self.panel_x + 2, y, line, fg=(200, 200, 200))
                y += 1

        return y + 1

    def _draw_progress_bar(self, tutorial: TutorialStep, start_y: int) -> int:
        """진행률 바 그리기 (선택적)"""
        # 간단한 진행률 표시 (완료 여부만)
        if tutorial.is_completed:
            status_text = "✓ 완료"
            status_color = (0, 255, 0)
        else:
            status_text = "○ 진행 중"
            status_color = (255, 255, 0)

        self.console.print(
            self.panel_x + 2,
            start_y,
            status_text,
            fg=status_color
        )

        return start_y + 2

    def _draw_hints(self, hints: List, start_y: int) -> int:
        """힌트 그리기"""
        if not hints:
            return start_y

        self.console.print(self.panel_x + 2, start_y, "힌트:", fg=(0, 255, 255))
        y = start_y + 1

        for hint in hints:
            # 여러 줄로 나누기
            words = hint.text.split()
            lines = []
            current_line = ""
            max_width = self.panel_width - 4

            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += word + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())

            for line in lines:
                if y < self.panel_y + self.panel_height - 2:
                    self.console.print(
                        self.panel_x + 2,
                        y,
                        f"• {line}",
                        fg=(150, 150, 150)
                    )
                    y += 1

        return y + 1

    def _draw_skip_instruction(self, skippable: bool, start_y: int) -> int:
        """스킵 안내 그리기"""
        if not skippable:
            return start_y

        # 화면 하단에 표시
        y = self.panel_y + self.panel_height - 2
        skip_text = "[ESC] 건너뛰기"

        # 펄스 효과
        brightness = 0.7 + 0.3 * math.sin(self.pulse_time * 2)
        color = tuple(int(c * brightness) for c in (200, 200, 200))

        self.console.print(
            self.panel_x + (self.panel_width - len(skip_text)) // 2,
            y,
            skip_text,
            fg=color
        )

        return y + 1

    def show_message(
        self,
        message: TutorialMessage,
        center_screen: bool = True
    ) -> None:
        """
        메시지 표시 (타이핑 효과 등)

        Args:
            message: 표시할 메시지
            center_screen: 화면 중앙에 표시할지 여부
        """
        self.current_message = message
        self.typing_index = 0
        self.message_complete = False

        if center_screen:
            y = self.screen_height // 2

            # 메시지를 여러 줄로 나누기
            words = message.text.split()
            lines = []
            current_line = ""
            max_width = self.screen_width - 20

            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += word + " "
                else:
                    lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())

            # 각 줄 표시
            for i, line in enumerate(lines):
                x = (self.screen_width - len(line)) // 2
                display_text = line[:self.typing_index] if i == len(lines) - 1 else line
                self.console.print(x, y + i, display_text, fg=message.color)

    def update_message_typing(self, delta_time: float) -> bool:
        """
        메시지 타이핑 효과 업데이트

        Returns:
            메시지 완료 여부
        """
        if not self.current_message or self.message_complete:
            return True

        self.typing_timer += delta_time
        if self.typing_timer >= self.typing_speed:
            self.typing_timer = 0.0
            self.typing_index += 1

            if self.typing_index >= len(self.current_message.text):
                self.message_complete = True
                return True

        return False

    def highlight_ui_element(self, highlight: UIHighlight) -> None:
        """
        UI 요소 강조

        Args:
            highlight: 강조할 UI 요소 정보
        """
        if highlight.x is not None and highlight.y is not None:
            # 특정 위치 강조
            self._draw_highlight_box(
                highlight.x,
                highlight.y,
                3,
                3,
                highlight.color,
                highlight.pulse
            )

            # 설명 표시
            if highlight.description:
                self._draw_description(
                    highlight.x,
                    highlight.y - 1,
                    highlight.description
                )

    def _draw_highlight_box(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Tuple[int, int, int],
        pulse: bool = False
    ) -> None:
        """강조 박스 그리기"""
        # 펄스 효과
        if pulse:
            brightness = 0.6 + 0.4 * math.sin(self.pulse_time * 3)
            color = tuple(int(c * brightness) for c in color)

        # 박스 테두리
        for bx in range(x - 1, x + width + 1):
            if 0 <= bx < self.screen_width:
                if 0 <= y - 1 < self.screen_height:
                    self.console.print(bx, y - 1, "═", fg=color)
                if 0 <= y + height < self.screen_height:
                    self.console.print(bx, y + height, "═", fg=color)

        for by in range(y, y + height):
            if 0 <= by < self.screen_height:
                if 0 <= x - 1 < self.screen_width:
                    self.console.print(x - 1, by, "║", fg=color)
                if 0 <= x + width < self.screen_width:
                    self.console.print(x + width, by, "║", fg=color)

    def _draw_description(self, x: int, y: int, description: str) -> None:
        """설명 텍스트 그리기"""
        # 배경 박스
        desc_width = len(description) + 2
        desc_x = max(0, min(x - desc_width // 2, self.screen_width - desc_width))

        if 0 <= y < self.screen_height:
            # 배경
            for dx in range(desc_width):
                if 0 <= desc_x + dx < self.screen_width:
                    self.console.rgb["bg"][y, desc_x + dx] = (40, 40, 60)

            # 텍스트
            self.console.print(desc_x + 1, y, description, fg=(255, 255, 255))

    def show_completion_message(self, message: str, reward_exp: int = 0, reward_gold: int = 0) -> None:
        """
        완료 메시지 표시

        Args:
            message: 완료 메시지
            reward_exp: 보상 경험치
            reward_gold: 보상 골드
        """
        # 중앙에 큰 메시지 박스
        box_width = 50
        box_height = 8
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경
        for y in range(box_y, box_y + box_height):
            for x in range(box_x, box_x + box_width):
                if 0 <= y < self.screen_height and 0 <= x < self.screen_width:
                    self.console.rgb["bg"][y, x] = (30, 30, 50)

        # 테두리
        for x in range(box_x, box_x + box_width):
            if 0 <= x < self.screen_width:
                if 0 <= box_y < self.screen_height:
                    self.console.print(x, box_y, "═", fg=(255, 215, 0))
                if 0 <= box_y + box_height - 1 < self.screen_height:
                    self.console.print(x, box_y + box_height - 1, "═", fg=(255, 215, 0))

        # 완료 메시지
        title = "✓ 튜토리얼 완료!"
        title_x = box_x + (box_width - len(title)) // 2
        self.console.print(title_x, box_y + 2, title, fg=(0, 255, 0))

        # 메시지
        msg_x = box_x + (box_width - len(message)) // 2
        self.console.print(msg_x, box_y + 4, message, fg=(255, 255, 255))

        # 보상
        if reward_exp > 0 or reward_gold > 0:
            reward_text = f"경험치 +{reward_exp}  골드 +{reward_gold}"
            reward_x = box_x + (box_width - len(reward_text)) // 2
            self.console.print(reward_x, box_y + 6, reward_text, fg=(255, 215, 0))

    def update(self, delta_time: float) -> None:
        """UI 애니메이션 업데이트"""
        self.pulse_time += delta_time

    def clear_tutorial_ui(self) -> None:
        """튜토리얼 UI 지우기"""
        # 패널 영역만 지우기
        for y in range(self.panel_y, min(self.panel_y + self.panel_height, self.screen_height)):
            for x in range(self.panel_x, min(self.panel_x + self.panel_width, self.screen_width)):
                self.console.rgb["bg"][y, x] = (0, 0, 0)
                self.console.print(x, y, " ")
