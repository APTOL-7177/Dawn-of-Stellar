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
        """스토리 라인 목록 - story_system_example.py 일반 인트로 기반"""
        return [
            # 메인 타이틀
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
                pause=3.0,
                effect="flash"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 스토리 시작
            StoryLine(
                "서기 2157년, 지구...",
                color=(220, 220, 220),
                delay=0.1,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "인류는 마침내 수백 년의 꿈을 이루어냈다.",
                color=(200, 200, 200),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "전쟁은 역사책 속 이야기가 되었고,",
                color=(180, 180, 180),
                delay=0.05,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "질병과 기아는 과거의 악몽이 되었다.",
                color=(180, 180, 180),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 차원 항해 기술
            StoryLine(
                "그리고 마침내... 차원 항해 기술이 완성되었다.",
                color=(0, 255, 255),  # 시안
                delay=0.08,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 실험의 날
            StoryLine(
                "스텔라 연구소, 차원 항해 실험실...",
                color=(220, 220, 220),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "\"모든 시스템 정상. 차원 엔진 가동 준비 완료.\"",
                color=(0, 255, 0),  # 녹색
                delay=0.04,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "\"역사적인 순간입니다. 인류 최초의 차원 도약을 시작합니다.\"",
                color=(0, 255, 0),
                delay=0.04,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 연구원들
            StoryLine(
                "연구원들의 흥분된 목소리가 실험실을 가득 채웠다.",
                color=(200, 200, 200),
                delay=0.05,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "수십 년간의 연구와 준비가 이 순간을 위함이었다.",
                color=(200, 200, 200),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 불길한 예감
            StoryLine(
                "하지만 그 누구도 예상하지 못한 일이",
                color=(255, 255, 0),  # 노란색
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "조용히 어둠 속에서 꿈틀거리고 있었다...",
                color=(255, 255, 0),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 재앙의 시작 - 카운트다운
            StoryLine(
                "\"차원 게이트 개방... 3... 2... 1...\"",
                color=(255, 255, 0),
                delay=0.1,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            # 이상 발생
            StoryLine(
                "하지만 첫 번째 차원 도약 실험에서...",
                color=(200, 200, 200),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "아무도 예상하지 못한 일이 벌어졌다.",
                color=(255, 0, 0),  # 빨간색
                delay=0.08,
                pause=2.5,
                effect="flash"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            # 경고
            StoryLine(
                "\"경고! 차원 공명 현상 발생!\"",
                color=(255, 0, 0),
                delay=0.06,
                pause=1.5,
                effect="flash"
            ),
            StoryLine(
                "\"시공간 매트릭스가 불안정합니다!\"",
                color=(255, 0, 0),
                delay=0.06,
                pause=1.5,
                effect="flash"
            ),
            StoryLine(
                "\"실험 중단! 즉시 실험을 중단하세요!\"",
                color=(255, 0, 0),
                delay=0.06,
                pause=2.0,
                effect="flash"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            # 대재앙 - 글리치 효과
            StoryLine(
                "시공간 교란 발생!",
                color=(255, 0, 0),
                delay=0.2,
                pause=3.0,
                effect="glitch"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 재앙의 묘사
            StoryLine(
                "하늘이 갈라지고, 대지가 진동했다.",
                color=(255, 0, 0),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "차원의 경계가 산산조각 나면서",
                color=(200, 200, 200),
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "과거, 현재, 미래의 모든 시대가 뒤섞이기 시작했다.",
                color=(200, 200, 200),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 시간의 왜곡
            StoryLine(
                "시간의 흐름이 왜곡되기 시작했다...",
                color=(255, 0, 255),  # 마젠타
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "어떤 곳에서는 시간이 거꾸로 흐르고,",
                color=(255, 0, 255),
                delay=0.06,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "어떤 곳에서는 시간이 완전히 멈춰버렸다.",
                color=(255, 0, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 공간의 왜곡
            StoryLine(
                "공간의 법칙이 무너지면서",
                color=(0, 150, 255),  # 파란색
                delay=0.08,
                pause=1.8,
                effect="typing"
            ),
            StoryLine(
                "중력이 제멋대로 변하고,",
                color=(0, 150, 255),
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "거리의 개념 자체가 의미를 잃었다.",
                color=(0, 150, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 현실의 붕괴
            StoryLine(
                "현실 자체가 일그러지면서",
                color=(255, 0, 0),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "물질과 에너지의 경계가 흐려졌다.",
                color=(255, 0, 0),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 혼돈의 세계
            StoryLine(
                "그리고... 세상은 완전히 달라졌다.",
                color=(255, 255, 255),
                delay=0.08,
                pause=3.0,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 시공간 혼돈
            StoryLine(
                "시공간의 혼돈 속에서",
                color=(200, 200, 200),
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "모든 것이 불가능해 보이는 일들이 현실이 되었다.",
                color=(200, 200, 200),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 과거와 미래의 융합
            StoryLine(
                "과거의 지혜와 미래의 기술이 만나고,",
                color=(255, 255, 0),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "서로 다른 시대의 법칙들이 충돌한다.",
                color=(255, 255, 0),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 희망의 메시지
            StoryLine(
                "하지만 그 혼돈 속에서도",
                color=(0, 150, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "새로운 가능성들이 태어나고 있었다.",
                color=(0, 150, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 상반되는 상황들 - 혼돈에서 새로운 가능성으로
            StoryLine(
                "미래의 과학자가 돌도끼로 실험을 한다.",
                color=(255, 0, 0),  # 빨간색 (문제)
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "모든 것이 뒤섞인 채로 새로운 질서를 찾기 시작한다.",
                color=(255, 255, 0),  # 노란색 (희망)
                delay=0.05,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            StoryLine(
                "그리스의 철학자가 고장난 컴퓨터 앞에서 좌절하지만,",
                color=(255, 0, 0),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "AI와 함께 새로운 진리를 탐구한다.",
                color=(255, 255, 0),
                delay=0.05,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            StoryLine(
                "해적이 우주선 조종법을 몰라 표류하지만,",
                color=(255, 0, 0),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "성간 항해의 새로운 길을 개척해낸다.",
                color=(255, 255, 0),
                delay=0.05,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=0.5),

            StoryLine(
                "기사가 레이저 검에 당황하면서도,",
                color=(255, 0, 0),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "과거의 기사도와 미래의 기술을 융합해낸다.",
                color=(255, 255, 0),
                delay=0.05,
                pause=1.8,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            StoryLine(
                "모든 것이 혼란스럽지만,",
                color=(255, 0, 0),
                delay=0.05,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "새로운 가능성들이 태어나고 있었다.",
                color=(255, 255, 0),
                delay=0.05,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.5),

            # 주인공의 등장
            StoryLine(
                "그리고 그 혼돈 속에서, 당신이 있다.",
                color=(0, 255, 255),  # 시안
                delay=0.08,
                pause=2.0,
                effect="fade_in"
            ),
            StoryLine(
                "당신은 차원 항해사로서",
                color=(0, 255, 255),
                delay=0.06,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "이 혼돈의 세계에서 길을 찾아야 한다.",
                color=(0, 255, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 세계의 모순
            StoryLine(
                "과거의 기억이 미래의 예언이 된다.",
                color=(255, 0, 255),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),
            StoryLine(
                "죽은 자가 살아서 걸어다니고,",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "태어나지 않은 자가 이미 늙어간다.",
                color=(255, 255, 255),
                delay=0.06,
                pause=3.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.5),

            # 주인공의 역할
            StoryLine(
                "그리고... 이 모든 혼돈의 한복판에",
                color=(0, 255, 255),
                delay=0.08,
                pause=2.5,
                effect="typing"
            ),
            StoryLine(
                "당신이 서 있다.",
                color=(0, 255, 255),
                delay=0.08,
                pause=3.0,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 사명
            StoryLine(
                "당신은 차원 항해사...",
                color=(255, 255, 0),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "시공간을 넘나들 수 있는 유일한 존재.",
                color=(255, 255, 0),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),
            StoryLine(
                "이 혼돈의 세계에서 질서를 찾을 수 있는",
                color=(255, 255, 0),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "마지막 희망.",
                color=(255, 255, 0),
                delay=0.08,
                pause=3.0,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 임무
            StoryLine(
                "시공간 교란의 진정한 원인을 찾아야 한다.",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "뒤섞인 시대들을 제자리로 돌려놓아야 한다.",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "무너진 현실의 법칙을 다시 세워야 한다.",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 동료의 필요성
            StoryLine(
                "하지만 그 여정은 결코 쉽지 않을 것이다.",
                color=(255, 0, 0),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "혼자서는 절대 불가능한 일이다.",
                color=(255, 0, 0),
                delay=0.06,
                pause=2.5,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 동료와 함께
            StoryLine(
                "시공을 초월한 동료들을 만나야 한다.",
                color=(0, 255, 0),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "각기 다른 시대에서 온 영웅들과 함께",
                color=(0, 255, 0),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "이 불가능해 보이는 임무를 완수해야 한다.",
                color=(0, 255, 0),
                delay=0.06,
                pause=3.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.5),

            # 모험의 시작
            StoryLine(
                "시공의 미로를 탐험하고",
                color=(0, 150, 255),
                delay=0.05,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "시대를 초월한 동료들과 함께",
                color=(0, 255, 0),
                delay=0.05,
                pause=1.5,
                effect="typing"
            ),
            StoryLine(
                "운명의 실타래를 바로잡을 수 있을까?",
                color=(255, 255, 0),
                delay=0.05,
                pause=3.0,
                effect="typing"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 의문
            StoryLine(
                "혹시 당신이 그 해답을 가지고 있는 건 아닐까?",
                color=(255, 255, 255),
                delay=0.06,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "아니면... 당신 자신이 그 해답인 건 아닐까?",
                color=(255, 255, 0),
                delay=0.08,
                pause=3.0,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.5),

            # 에필로그
            StoryLine(
                "모험이 시작된다...",
                color=(255, 255, 255),
                delay=0.1,
                pause=2.5,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 마지막 메시지들
            StoryLine(
                "시공을 초월한 영웅들의 이야기",
                color=(0, 255, 255),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "혼돈 속에서 피어나는 희망",
                color=(0, 255, 255),
                delay=0.08,
                pause=2.0,
                effect="typing"
            ),
            StoryLine(
                "그리고 당신의 전설이 시작된다",
                color=(255, 255, 0),
                delay=0.08,
                pause=3.0,
                effect="fade_in"
            ),

            # 빈 줄 - 화면 클리어
            StoryLine("", pause=1.0),

            # 제목 반복
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
