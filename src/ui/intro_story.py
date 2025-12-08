"""
인트로 스토리 시스템 - Dawn of Stellar

게임 시작 시 보여지는 스토리 인트로
story_system_example.py의 일반 인트로 기반 + 다양한 시각 효과
"""

import tcod
import tcod.console
import tcod.event
import time
import random
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.core.logger import get_logger, Loggers
from src.ui.input_handler import unified_input_handler, GameAction


logger = get_logger(Loggers.SYSTEM)


@dataclass
class StoryLine:
    """스토리 라인"""
    text: str
    color: Tuple[int, int, int] = (255, 255, 255)  # 기본 흰색
    delay: float = 0.05  # 타이핑 딜레이
    pause: float = 1.0   # 라인 후 일시정지
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
        """스토리 라인 목록 - 게임 인트로 스토리"""
        return [
            # 타이틀
            StoryLine(
                "별빛의 여명",
                color=(255, 215, 0),
                delay=0.08,
                pause=2.0,
                effect="fade_in"
            ),
            StoryLine(
                "Dawn of Stellar",
                color=(200, 200, 255),
                delay=0.06,
                pause=2.5,
                effect="flash"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            # 평화로운 시작
            StoryLine(
                "서기 2157년...",
                color=(220, 220, 220),
                delay=0.1,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.3),

            StoryLine(
                "인류는 마침내 평화를 이루었다.",
                color=(200, 200, 200),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "전쟁은 역사책 속 이야기가 되었고,",
                color=(180, 180, 180),
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "질병과 기아는 과거의 악몽이 되었다.",
                color=(180, 180, 180),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.0),

            # 황금시대
            StoryLine(
                "인류는 별들 사이를 여행하며",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "우주 곳곳에 문명의 씨앗을 퍼뜨렸다.",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "이것이... 황금시대였다.",
                color=(255, 215, 0),
                delay=0.08,
                pause=2.2,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            # 차원 항해의 꿈
            StoryLine(
                "그들은 더 큰 꿈을 꾸었다.",
                color=(255, 255, 0),
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.3),

            StoryLine(
                "차원을 넘어,",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.2,
                effect="typing"
            ),
            StoryLine(
                "무한한 가능성의 세계로...",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=0.3),

            StoryLine(
                "영원한 평화의 내일을 향해.",
                color=(0, 255, 255),
                delay=0.06,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.8),

            StoryLine(
                "하지만 그 날 밤...",
                color=(255, 255, 0),
                delay=0.08,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "별들이 떨어지기 시작했다.",
                color=(255, 215, 0),
                delay=0.08,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "하늘이 갈라졌다.",
                color=(255, 0, 0),
                delay=0.08,
                pause=1.8,
                effect="flash"
            ),
            StoryLine(
                "대지가 진동했다.",
                color=(255, 0, 0),
                delay=0.08,
                pause=1.8,
                effect="flash"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "세계는 산산조각 났다.",
                color=(255, 0, 0),
                delay=0.08,
                pause=2.2,
                effect="flash"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "시간의 강이 역류했다.",
                color=(255, 0, 255),
                delay=0.08,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "과거와 미래가 뒤섞이며",
                color=(255, 0, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "현실의 경계가 흐려졌다.",
                color=(255, 0, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "공간의 법칙이 무너지고,",
                color=(0, 150, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "차원의 벽이 산산조각 났다.",
                color=(0, 150, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "그 모든 것은...",
                color=(200, 0, 0),
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "누군가의 야망 때문이었다.",
                color=(200, 0, 0),
                delay=0.08,
                pause=2.2,
                effect="flash"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "영원을 꿈꾼 자,",
                color=(150, 0, 0),
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "신이 되려 한 자의 탐욕이",
                color=(150, 0, 0),
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "세상을 삼켜버렸다.",
                color=(150, 0, 0),
                delay=0.08,
                pause=2.5,
                effect="flash"
            ),

            # 빈 줄
            StoryLine("", pause=1.8),

            StoryLine(
                "시간 속에 갇힌 영혼이 있다.",
                color=(0, 150, 255),
                delay=0.08,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "끝없이 반복되는 악몽...",
                color=(100, 100, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "열 만 번의 절망...",
                color=(100, 100, 255),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "천 개의 영혼이 그를 짓눌렀다.",
                color=(100, 100, 255),
                delay=0.06,
                pause=2.2,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "세계는 조각났다.",
                color=(200, 200, 200),
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "과거의 전사가 미래의 땅을 걷고,",
                color=(180, 180, 180),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "미래의 과학자가 고대의 유적을 헤맨다.",
                color=(180, 180, 180),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "죽은 자가 살아 걸어다니고,",
                color=(255, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "태어나지 않은 자가 이미 늙어간다.",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "모든 것이 무너졌다.",
                color=(255, 0, 0),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "희망도, 미래도, 아무것도...",
                color=(200, 0, 0),
                delay=0.08,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.8),

            StoryLine(
                "하지만...",
                color=(255, 255, 0),
                delay=0.1,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "어둠 속에서도",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "걸어가는 자가 있다.",
                color=(0, 255, 255),
                delay=0.08,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "당신이다.",
                color=(255, 215, 0),
                delay=0.1,
                pause=2.2,
                effect="flash"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "열 만 번의 밤을 끝낼 자,",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "갇힌 영혼을 해방시킬 자,",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "어둠을 뚫고 새벽을 맞이할 자.",
                color=(0, 255, 255),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "시간은 누구에게나 똑같이 흐른다.",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=0.8),

            StoryLine(
                "영원을 꿈꾸는 자에게도,",
                color=(200, 200, 200),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "불꽃처럼 타오르는 자에게도.",
                color=(200, 200, 200),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "하지만 그 안에서 만드는 건",
                color=(255, 255, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "우리의 선택이다.",
                color=(255, 255, 0),
                delay=0.08,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.8),

            StoryLine(
                "가장 긴 밤 끝에는",
                color=(0, 150, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "반드시 새벽이 온다.",
                color=(0, 150, 255),
                delay=0.06,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "가장 깊은 어둠 속에서도",
                color=(0, 200, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "빛은 길을 찾아낸다.",
                color=(0, 200, 255),
                delay=0.06,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "별이 떨어진 자리에",
                color=(255, 215, 0),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "꽃을 피워낼 것이다.",
                color=(255, 215, 0),
                delay=0.08,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.8),

            StoryLine(
                "열 만 번째 밤이 시작된다.",
                color=(200, 200, 255),
                delay=0.08,
                pause=2.2,
                effect="typing"
            ),

            # 빈 줄
            StoryLine("", pause=1.2),

            StoryLine(
                "하지만 이번엔 다를 것이다.",
                color=(255, 255, 0),
                delay=0.08,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=1.5),

            StoryLine(
                "별빛의 여명은",
                color=(255, 215, 0),
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "포기하지 않는 자에게 찾아온다.",
                color=(255, 215, 0),
                delay=0.08,
                pause=3.0,
                effect="fade_in"
            ),

            # 빈 줄
            StoryLine("", pause=2.0),

            StoryLine(
                "별빛의 여명",
                color=(255, 215, 0),
                delay=0.08,
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

        # 5회 글리치
        for _ in range(5):
            if self._check_skip():
                self.console.print(x, y, line.text, fg=line.color)
                self.context.present(self.console)
                return

            # 글리치 텍스트 생성
            glitched_text = ''.join(
                random.choice(glitch_chars) if random.random() < 0.3 else c
                for c in line.text
            )

            self.console.print(x, y, glitched_text, fg=line.color)
            self.context.present(self.console)
            time.sleep(0.08)

        # 최종적으로 원본 텍스트
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
        """스킵 체크 (Enter 키 또는 A 버튼)"""
        # 게임패드 버튼 직접 확인 (가장 안정적인 방법)
        try:
            import pygame
            pygame.event.pump()
            # 연결된 게임패드가 있으면 A 버튼 (버튼 0) 확인
            joystick_count = pygame.joystick.get_count()
            if joystick_count > 0:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                if joystick.get_button(0):  # A 버튼
                    self.skip_requested = True
                    return True
        except Exception as e:
            # pygame 관련 에러 무시하고 키보드 입력으로 진행
            pass

        # 키보드 입력 확인
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
