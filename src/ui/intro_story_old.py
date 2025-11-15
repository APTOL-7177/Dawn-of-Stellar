"""
인트로 스토리 시스템 - Dawn of Stellar

게임 시작 시 보여지는 스토리 인트로
다양한 화면 효과로 몰입도 향상
"""

import tcod
import tcod.console
import tcod.event
import time
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


@dataclass
class StoryLine:
    """스토리 라인"""
    text: str
    color: Tuple[int, int, int] = (255, 255, 255)  # 기본 흰색
    delay: float = 0.05  # 타이핑 딜레이
    pause: float = 1.5   # 라인 후 일시정지
    effect: str = "typing"  # typing, fade_in, flash, glitch


class IntroStorySystem:
    """인트로 스토리 시스템"""

    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.screen_width = console.width
        self.screen_height = console.height
        self.skip_requested = False
        self.logger = logger

    def show_intro(self) -> bool:
        """
        인트로 스토리 표시

        Returns:
            True: 정상 완료, False: 스킵됨
        """
        # 인트로 BGM 재생
        try:
            from src.audio import play_bgm
            play_bgm("intro", loop=False, fade_in=True)
            logger.info("인트로 BGM 재생")
        except Exception as e:
            logger.warning(f"인트로 BGM 재생 실패: {e}")

        # 스토리 라인들
        story_lines = self._get_story_lines()

        # 페이드 인 효과
        self._fade_in()

        # 현재 화면에 표시할 라인들
        current_lines = []
        last_clear_index = -1

        # 스토리 진행
        for i, line in enumerate(story_lines):
            if self._check_skip():
                logger.info("인트로 스킵됨")
                return False

            # 새 섹션 시작 시 화면 클리어 (빈 줄이 나오면)
            if line.text == "" and len(current_lines) > 0:
                self.console.clear()
                current_lines = []
                last_clear_index = i

            # 라인 표시
            if line.effect == "typing":
                self._show_typing_effect(line, len(current_lines))
            elif line.effect == "fade_in":
                self._show_fade_in_line(line, len(current_lines))
            elif line.effect == "flash":
                self._show_flash_line(line, len(current_lines))
            elif line.effect == "glitch":
                self._show_glitch_line(line, len(current_lines))

            if line.text != "":
                current_lines.append(line)

            # 화면이 너무 차면 클리어
            if len(current_lines) > 8:
                self.console.clear()
                current_lines = []

            # 일시정지
            if self._wait_with_skip_check(line.pause):
                logger.info("인트로 스킵됨")
                return False

        # 마지막 메시지
        if not self._show_continue_prompt():
            logger.info("인트로 스킵됨")
            return False

        # 페이드 아웃
        self._fade_out()

        logger.info("인트로 정상 완료")
        return True

    def _get_story_lines(self) -> List[StoryLine]:
        """스토리 라인 목록 - 현장감 있는 1인칭 시점"""
        return [
            # 시작
            StoryLine(
                "별빛의 여명",
                color=(255, 215, 0),  # 금색
                delay=0.08,
                pause=2.0,
                effect="fade_in"
            ),
            StoryLine(
                "Dawn of Stellar",
                color=(200, 200, 255),  # 연한 청색
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 현장 1: 연구소
            StoryLine(
                "시공간 연구소 제어실.",
                color=(220, 220, 220),
                delay=0.04,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "2157년 3월 15일. 오전 9시 27분.",
                color=(200, 200, 200),
                delay=0.03,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "당신은 모니터를 응시하고 있다.",
                color=(180, 180, 180),
                delay=0.03,
                pause=1.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 현장 2: 경고
            StoryLine(
                "삐- 삐- 삐-",
                color=(255, 150, 50),
                delay=0.15,
                pause=1.0,
                effect="flash"
            ),
            StoryLine(
                "경고음.",
                color=(255, 100, 100),
                delay=0.04,
                pause=1.2,
                effect="typing"
            ),
            StoryLine(
                "시공간 게이트의 에너지 수치가 급상승한다.",
                color=(255, 150, 100),
                delay=0.03,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "\"제어 시스템 오류! 게이트 출력 157%!\"",
                color=(255, 200, 100),
                delay=0.03,
                pause=1.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 현장 3: 긴급 상황
            StoryLine(
                "바닥이 흔들린다.",
                color=(255, 100, 100),
                delay=0.04,
                pause=1.0,
                effect="typing"
            ),
            StoryLine(
                "공기가 일그러진다.",
                color=(255, 80, 80),
                delay=0.04,
                pause=1.0,
                effect="typing"
            ),
            StoryLine(
                "눈앞에 보라색 균열이 갈라진다.",
                color=(200, 100, 255),
                delay=0.03,
                pause=1.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            # 글리치 효과 - 시공 붕괴
            StoryLine(
                "[ ! ! !  차 원  균 열  감 지 ! ! ! ]",
                color=(255, 50, 50),
                delay=0.08,
                pause=1.5,
                effect="glitch"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 현장 4: 혼돈
            StoryLine(
                "균열에서 빛이 쏟아져 나온다.",
                color=(255, 255, 200),
                delay=0.03,
                pause=1.2,
                effect="typing"
            ),
            StoryLine(
                "과거의 유령들.",
                color=(150, 200, 255),
                delay=0.04,
                pause=1.0,
                effect="typing"
            ),
            StoryLine(
                "미래의 그림자들.",
                color=(150, 200, 255),
                delay=0.04,
                pause=1.0,
                effect="typing"
            ),
            StoryLine(
                "다른 차원의 존재들.",
                color=(200, 150, 255),
                delay=0.03,
                pause=1.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 현장 5: 의식 상실
            StoryLine(
                "눈부신 섬광.",
                color=(255, 255, 255),
                delay=0.04,
                pause=1.0,
                effect="flash"
            ),
            StoryLine(
                "귀청을 찢는 굉음.",
                color=(255, 100, 100),
                delay=0.04,
                pause=1.0,
                effect="typing"
            ),
            StoryLine(
                "의식이 흐려진다...",
                color=(150, 150, 150),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.5),

            # 깨어남
            StoryLine(
                "...",
                color=(100, 100, 100),
                delay=0.2,
                pause=1.0,
                effect="typing"
            ),
            StoryLine(
                "눈을 뜬다.",
                color=(150, 150, 150),
                delay=0.04,
                pause=1.5,
                effect="fade_in"
            ),
            StoryLine(
                "낯선 장소.",
                color=(200, 200, 200),
                delay=0.04,
                pause=1.2,
                effect="typing"
            ),
            StoryLine(
                "당신의 모험이 시작된다.",
                color=(255, 255, 255),
                delay=0.03,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 제목 반복
            StoryLine(
                "별빛의 여명",
                color=(255, 215, 0),
                delay=0.06,
                pause=3.0,
                effect="flash"
            ),
        ]

    def _show_typing_effect(self, line: StoryLine, line_index: int):
        """타이핑 효과"""
        y = self.screen_height // 2 - 10 + line_index * 2

        displayed_text = ""
        for char in line.text:
            if self._check_skip():
                # 스킵 시 전체 텍스트 즉시 표시
                self.console.print(
                    (self.screen_width - len(line.text)) // 2,
                    y,
                    line.text,
                    fg=line.color
                )
                self.context.present(self.console)
                return

            displayed_text += char
            self.console.print(
                (self.screen_width - len(line.text)) // 2,
                y,
                displayed_text,
                fg=line.color
            )
            self.context.present(self.console)
            time.sleep(line.delay)

    def _show_fade_in_line(self, line: StoryLine, line_index: int):
        """페이드 인 효과"""
        y = self.screen_height // 2 - 10 + line_index * 2
        x = (self.screen_width - len(line.text)) // 2

        # 10단계 페이드 인
        for alpha in range(0, 11):
            if self._check_skip():
                self.console.print(x, y, line.text, fg=line.color)
                self.context.present(self.console)
                return

            brightness = alpha / 10.0
            faded_color = tuple(int(c * brightness) for c in line.color)
            self.console.print(x, y, line.text, fg=faded_color)
            self.context.present(self.console)
            time.sleep(0.05)

    def _show_flash_line(self, line: StoryLine, line_index: int):
        """깜빡임 효과"""
        y = self.screen_height // 2 - 10 + line_index * 2
        x = (self.screen_width - len(line.text)) // 2

        # 3번 깜빡임
        for _ in range(3):
            if self._check_skip():
                self.console.print(x, y, line.text, fg=line.color)
                self.context.present(self.console)
                return

            # 밝게
            self.console.print(x, y, line.text, fg=line.color)
            self.context.present(self.console)
            time.sleep(0.2)

            # 어둡게
            dark_color = tuple(c // 3 for c in line.color)
            self.console.print(x, y, line.text, fg=dark_color)
            self.context.present(self.console)
            time.sleep(0.2)

        # 최종적으로 밝게
        self.console.print(x, y, line.text, fg=line.color)
        self.context.present(self.console)

    def _show_glitch_line(self, line: StoryLine, line_index: int):
        """글리치 효과"""
        y = self.screen_height // 2 - 10 + line_index * 2
        x = (self.screen_width - len(line.text)) // 2

        # 글리치 문자들
        glitch_chars = ['█', '▓', '▒', '░', '▄', '▀', '■', '□']

        # 5번 글리치
        for _ in range(5):
            if self._check_skip():
                self.console.print(x, y, line.text, fg=line.color)
                self.context.present(self.console)
                return

            # 랜덤 글리치 텍스트
            glitched = ''.join(
                random.choice(glitch_chars) if random.random() < 0.3 else c
                for c in line.text
            )
            self.console.print(x, y, glitched, fg=line.color)
            self.context.present(self.console)
            time.sleep(0.1)

        # 원본 텍스트
        self.console.print(x, y, line.text, fg=line.color)
        self.context.present(self.console)

    def _fade_in(self):
        """화면 페이드 인"""
        for alpha in range(0, 11):
            if self._check_skip():
                return

            brightness = alpha / 10.0
            bg_color = tuple(int(0 * brightness) for _ in range(3))

            # 배경 채우기
            for y in range(self.screen_height):
                for x in range(self.screen_width):
                    self.console.rgb["bg"][y, x] = bg_color

            self.context.present(self.console)
            time.sleep(0.05)

    def _fade_out(self):
        """화면 페이드 아웃"""
        for alpha in range(10, -1, -1):
            if self._check_skip():
                self.console.clear()
                self.context.present(self.console)
                return

            brightness = alpha / 10.0

            # 모든 텍스트를 어둡게
            for y in range(self.screen_height):
                for x in range(self.screen_width):
                    current_fg = self.console.rgb["fg"][y, x]
                    faded_fg = tuple(int(c * brightness) for c in current_fg)
                    self.console.rgb["fg"][y, x] = faded_fg

            self.context.present(self.console)
            time.sleep(0.05)

        self.console.clear()
        self.context.present(self.console)

    def _show_continue_prompt(self) -> bool:
        """
        계속 진행 프롬프트

        Returns:
            True: 정상 진행 (Enter 누르거나 타임아웃), False: 스킵
        """
        prompt = "Press Enter to continue..."
        y = self.screen_height - 3
        x = (self.screen_width - len(prompt)) // 2

        # 깜빡이는 프롬프트
        for _ in range(10):  # 최대 10번 깜빡임
            if self._check_skip():
                return True

            # 밝게
            self.console.print(x, y, prompt, fg=(200, 200, 200))
            self.context.present(self.console)
            if self._wait_with_skip_check(0.5):
                return True

            # 어둡게
            self.console.print(x, y, prompt, fg=(100, 100, 100))
            self.context.present(self.console)
            if self._wait_with_skip_check(0.5):
                return True

        return True  # 타임아웃 - 정상 진행

    def _check_skip(self) -> bool:
        """스킵 체크 (Enter 키)"""
        for event in tcod.event.get():
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.RETURN or event.sym == tcod.event.KeySym.KP_ENTER:
                    self.skip_requested = True
                    return True
            elif isinstance(event, tcod.event.Quit):
                self.skip_requested = True
                return True

        return self.skip_requested

    def _wait_with_skip_check(self, duration: float) -> bool:
        """
        대기하면서 스킵 체크

        Returns:
            True: 스킵됨, False: 정상 대기
        """
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_skip():
                return True
            time.sleep(0.01)
        return False


def show_intro_story(console: tcod.console.Console, context: tcod.context.Context) -> bool:
    """
    인트로 스토리 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        True: 정상 완료, False: 스킵됨
    """
    intro = IntroStorySystem(console, context)
    return intro.show_intro()
