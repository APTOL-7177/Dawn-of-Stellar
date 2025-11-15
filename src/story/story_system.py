"""
Dawn of Stellar - 스토리 시스템 (간소화 버전)

시공교란 컨셉의 스토리
"""

from typing import List
from dataclasses import dataclass


@dataclass
class StorySegment:
    """스토리 세그먼트"""
    text: str
    pause: float = 1.0  # 세그먼트 후 일시정지
    color: str = "white"


class StorySystem:
    """게임 스토리 시스템"""

    def __init__(self):
        self.current_chapter: int = 0
        self.story_seen: bool = False

        # 세피로스 관련 플래그들
        self.sephiroth_encountered: bool = False
        self.sephiroth_defeated: bool = False
        self.true_ending_unlocked: bool = False
        self.glitch_mode: bool = False

    def set_sephiroth_encountered(self, encountered: bool = True):
        """세피로스 조우 상태 설정"""
        self.sephiroth_encountered = encountered
        if encountered:
            self.glitch_mode = True

    def set_sephiroth_defeated(self, defeated: bool = True):
        """세피로스 처치 상태 설정"""
        self.sephiroth_defeated = defeated
        if defeated:
            self.true_ending_unlocked = True

    def is_glitch_mode(self) -> bool:
        """글리치 모드 활성화 여부"""
        return self.sephiroth_encountered and not self.sephiroth_defeated

    def is_true_ending_mode(self) -> bool:
        """진 엔딩 모드 활성화 여부"""
        return self.true_ending_unlocked

    def get_opening_story(self) -> List[StorySegment]:
        """오프닝 스토리"""
        return [
            StorySegment(
                "서기 2157년, 지구...",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "인류는 마침내 수백 년의 꿈을 이루어냈다.",
                pause=0.3,
                color="white"
            ),
            StorySegment(
                "\n전쟁은 역사책 속 이야기가 되었고,",
                pause=0.3,
                color="white"
            ),
            StorySegment(
                "기아와 질병도 먼 과거의 흔적만 남았다.",
                pause=0.3,
                color="white"
            ),
            StorySegment(
                "인류는 마침내 별들 사이를 여행하며,",
                pause=0.3,
                color="white"
            ),
            StorySegment(
                "우주 곳곳에 문명의 씨앗을 퍼뜨리기 시작했다.",
                pause=1.0,
                color="white"
            ),
            StorySegment(
                "\n이것이... 황금시대의 시작이었다.",
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n그러나, 어떤 빛이 강렬할수록",
                pause=0.5,
                color="white"
            ),
            StorySegment(
                "그 그림자 또한 짙어지는 법...",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\n『 시공교란 감지 』",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "『 원인 불명 』",
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "『 타임라인 붕괴 진행 중... 』",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\n당신은 시공의 틈새에서 깨어난다.",
                pause=1.5,
                color="cyan"
            ),
            StorySegment(
                "기억은 흐릿하고, 현실은 불안정하다.",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "\n단 하나만이 확실하다—",
                pause=0.5,
                color="white"
            ),
            StorySegment(
                "\n이 세계를 구하려면,",
                pause=0.3,
                color="white"
            ),
            StorySegment(
                "시간의 흐름을 되돌려야 한다.",
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n─── Dawn of Stellar ───",
                pause=3.0,
                color="cyan"
            ),
        ]

    def get_sephiroth_encounter_story(self) -> List[StorySegment]:
        """세피로스 조우 스토리"""
        return [
            StorySegment(
                "\n\n이곳은... 어디인가?",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n공기가 무겁다.",
                pause=1.0,
                color="white"
            ),
            StorySegment(
                "시간의 흐름이 왜곡되고 있다.",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n\n그리고... 그 '존재'가 있다.",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n「 ─── 」",
                pause=1.0,
                color="dark"
            ),
            StorySegment(
                "\n긴 은발, 한 손의 검.",
                pause=1.0,
                color="white"
            ),
            StorySegment(
                "절대적인 파괴의 상징.",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\n세피로스.",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n\"네가... 시간을 되돌리려 하는 자인가.\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"무의미한 저항이다.\"",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\n\"이 세계는 이미 끝났다.\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n그의 검이 빛난다─",
                pause=1.0,
                color="white"
            ),
        ]

    def get_sephiroth_defeat_story(self) -> List[StorySegment]:
        """세피로스 격파 스토리"""
        return [
            StorySegment(
                "\n\n...불가능한 일이 일어났다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n세피로스가 무릎을 꿇는다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n\"...어째서...?\"",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\n\"어째서 네가... 나를...?\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\n그의 몸이 빛의 입자로 흩어지기 시작한다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n\"...아직 끝나지 않았다.\"",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\n\"시간은... 되돌릴 수 없어...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"하지만... 너라면...\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n마지막 한 마디를 남기고, 그는 사라진다.",
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n\n시공의 균열이 서서히 닫히기 시작한다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n시간의 흐름이 정상으로 돌아온다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n\n당신은 세계를 구했다.",
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n─── True Ending ───",
                pause=5.0,
                color="cyan"
            ),
        ]

    def get_floor_message(self, floor: int) -> str:
        """층별 메시지"""
        messages = {
            1: "여정의 시작",
            5: "시간의 균열이 느껴진다...",
            10: "무언가 강력한 존재의 기운이...",
            14: "경고: 강력한 적의 기운!",
            15: "??? - 시공의 틈새 ???",
        }
        return messages.get(floor, f"{floor}층")


# 전역 스토리 시스템 인스턴스
_story_system = None


def get_story_system() -> StorySystem:
    """스토리 시스템 싱글톤 가져오기"""
    global _story_system
    if _story_system is None:
        _story_system = StorySystem()
    return _story_system
