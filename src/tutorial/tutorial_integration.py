"""
튜토리얼 통합 - 스토리 시스템과 메인 게임 통합
"""

import tcod
import tcod.console
import time
from typing import Optional

from src.tutorial.tutorial_manager import get_tutorial_manager
from src.tutorial.tutorial_ui import TutorialUI
from src.tutorial.tutorial_step import TutorialMessage
from src.story.story_system import get_story_system
from src.ui.intro_story import show_intro_story
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class TutorialIntegration:
    """
    튜토리얼 통합 시스템

    스토리 시스템과 튜토리얼을 연결하고,
    메인 게임 루프에 통합합니다.
    """

    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.tutorial_manager = get_tutorial_manager()
        self.tutorial_ui = TutorialUI(console)
        self.story_system = get_story_system()

        # 상태
        self.tutorial_started = False
        self.intro_shown = False

    def start_game_with_tutorial(self, skip_intro: bool = False) -> bool:
        """
        튜토리얼과 함께 게임 시작

        Args:
            skip_intro: 인트로 스킵 여부

        Returns:
            성공 여부
        """
        # 인트로 스토리 표시
        if not skip_intro and not self.intro_shown:
            logger.info("인트로 스토리 시작")
            intro_result = show_intro_story(self.console, self.context)
            self.intro_shown = True

            if not intro_result:
                logger.info("인트로 스킵됨")

        # 튜토리얼 시작 여부 묻기
        if not self.tutorial_started:
            if self._ask_start_tutorial():
                logger.info("튜토리얼 시작")
                return self.tutorial_manager.start_tutorial()
            else:
                logger.info("튜토리얼 건너뜀")
                return False

        return True

    def _ask_start_tutorial(self) -> bool:
        """
        튜토리얼 시작 여부 묻기

        Returns:
            시작 여부
        """
        self.console.clear()

        # 질문 표시
        question = "튜토리얼을 시작하시겠습니까?"
        description = "초보자에게 권장합니다. (Y/N)"

        q_x = (self.console.width - len(question)) // 2
        d_x = (self.console.width - len(description)) // 2

        self.console.print(q_x, self.console.height // 2 - 1, question, fg=(255, 255, 255))
        self.console.print(d_x, self.console.height // 2 + 1, description, fg=(200, 200, 200))

        self.context.present(self.console)

        # 입력 대기
        while True:
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.y:
                        return True
                    elif event.sym == tcod.event.KeySym.n:
                        return False
                    elif event.sym == tcod.event.KeySym.ESCAPE:
                        return False
                elif isinstance(event, tcod.event.Quit):
                    return False

    def show_tutorial_intro(self) -> None:
        """튜토리얼 인트로 메시지 표시"""
        self.console.clear()

        # 튜토리얼 인트로
        intro_messages = [
            TutorialMessage(
                text="차원 항해사 훈련 프로그램 시작",
                color=(0, 255, 255),
                pause=2.0,
                effect="fade_in"
            ),
            TutorialMessage(
                text="이 훈련은 당신이 시공간을 항해하는 데 필요한 기본 능력을 가르칩니다.",
                color=(255, 255, 255),
                pause=2.5,
                effect="typing"
            ),
            TutorialMessage(
                text="각 단계를 완료하면 다음 단계로 진행됩니다.",
                color=(255, 255, 255),
                pause=2.0,
                effect="typing"
            ),
            TutorialMessage(
                text="언제든 ESC 키를 눌러 튜토리얼을 건너뛸 수 있습니다.",
                color=(255, 255, 0),
                pause=2.0,
                effect="typing"
            ),
            TutorialMessage(
                text="준비되셨나요? 훈련을 시작합니다!",
                color=(255, 215, 0),
                pause=2.0,
                effect="flash"
            ),
        ]

        for message in intro_messages:
            self._show_message_with_effect(message)
            if self._wait_with_skip_check(message.pause):
                break

    def _show_message_with_effect(self, message: TutorialMessage) -> None:
        """메시지를 효과와 함께 표시"""
        y = self.console.height // 2
        x = (self.console.width - len(message.text)) // 2

        if message.effect == "typing":
            # 타이핑 효과
            for i in range(len(message.text) + 1):
                self.console.clear()
                self.console.print(x, y, message.text[:i], fg=message.color)
                self.context.present(self.console)
                time.sleep(0.05)

        elif message.effect == "fade_in":
            # 페이드 인 효과
            for alpha in range(0, 11):
                self.console.clear()
                brightness = alpha / 10.0
                faded_color = tuple(int(c * brightness) for c in message.color)
                self.console.print(x, y, message.text, fg=faded_color)
                self.context.present(self.console)
                time.sleep(0.05)

        elif message.effect == "flash":
            # 깜빡임 효과
            for _ in range(3):
                self.console.clear()
                self.console.print(x, y, message.text, fg=message.color)
                self.context.present(self.console)
                time.sleep(0.2)

                self.console.clear()
                dark_color = tuple(c // 3 for c in message.color)
                self.console.print(x, y, message.text, fg=dark_color)
                self.context.present(self.console)
                time.sleep(0.2)

            self.console.clear()
            self.console.print(x, y, message.text, fg=message.color)
            self.context.present(self.console)

        else:
            # 기본 표시
            self.console.clear()
            self.console.print(x, y, message.text, fg=message.color)
            self.context.present(self.console)

    def _wait_with_skip_check(self, duration: float) -> bool:
        """
        대기하면서 스킵 체크

        Returns:
            True: 스킵됨, False: 정상 대기
        """
        start_time = time.time()
        while time.time() - start_time < duration:
            for event in tcod.event.get():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.ESCAPE:
                        return True
                elif isinstance(event, tcod.event.Quit):
                    return True
            time.sleep(0.01)
        return False

    def update_tutorial(self, delta_time: float) -> None:
        """
        튜토리얼 업데이트 (메인 게임 루프에서 호출)

        Args:
            delta_time: 프레임 시간
        """
        if not self.tutorial_manager.is_active:
            return

        # 튜토리얼 매니저 업데이트
        self.tutorial_manager.update(delta_time)

        # UI 업데이트
        self.tutorial_ui.update(delta_time)

    def render_tutorial_ui(self) -> None:
        """튜토리얼 UI 렌더링 (메인 게임 루프에서 호출)"""
        if not self.tutorial_manager.is_active or not self.tutorial_manager.current_step:
            return

        # 튜토리얼 패널 렌더링
        self.tutorial_ui.render_tutorial_panel(
            self.tutorial_manager.current_step,
            show_objective=True,
            show_hints=True
        )

        # UI 강조 요소 렌더링
        for highlight in self.tutorial_manager.current_step.ui_highlights:
            self.tutorial_ui.highlight_ui_element(highlight)

    def handle_tutorial_input(self, event: tcod.event.Event) -> bool:
        """
        튜토리얼 관련 입력 처리

        Args:
            event: TCOD 이벤트

        Returns:
            이벤트를 처리했는지 여부
        """
        if not self.tutorial_manager.is_active:
            return False

        if isinstance(event, tcod.event.KeyDown):
            # ESC로 튜토리얼 건너뛰기
            if event.sym == tcod.event.KeySym.ESCAPE:
                if self._confirm_skip_tutorial():
                    self.tutorial_manager.skip_all_tutorials()
                    logger.info("튜토리얼 건너뜀")
                    return True

        return False

    def _confirm_skip_tutorial(self) -> bool:
        """
        튜토리얼 건너뛰기 확인

        Returns:
            건너뛰기 확인 여부
        """
        self.console.clear()

        question = "튜토리얼을 건너뛰시겠습니까?"
        warning = "나중에 설정에서 다시 볼 수 있습니다. (Y/N)"

        q_x = (self.console.width - len(question)) // 2
        w_x = (self.console.width - len(warning)) // 2

        self.console.print(q_x, self.console.height // 2 - 1, question, fg=(255, 255, 0))
        self.console.print(w_x, self.console.height // 2 + 1, warning, fg=(200, 200, 200))

        self.context.present(self.console)

        # 입력 대기
        while True:
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.y:
                        return True
                    elif event.sym == tcod.event.KeySym.n or event.sym == tcod.event.KeySym.ESCAPE:
                        return False
                elif isinstance(event, tcod.event.Quit):
                        return True


def show_tutorial_intro_with_story(
    console: tcod.console.Console,
    context: tcod.context.Context,
    skip_intro_story: bool = False
) -> TutorialIntegration:
    """
    스토리와 튜토리얼 인트로 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        skip_intro_story: 인트로 스토리 스킵 여부

    Returns:
        TutorialIntegration 인스턴스
    """
    integration = TutorialIntegration(console, context)
    integration.start_game_with_tutorial(skip_intro=skip_intro_story)
    return integration
