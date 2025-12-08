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
        
        # 카인 관련 플래그들
        self.cain_defeated: bool = False

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

    def set_cain_defeated(self, defeated: bool = True):
        """카인 처치 상태 설정"""
        self.cain_defeated = defeated

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
                "\n\n공간이 일그러지며 현실이 무너져내린다...",
                pause=0.5,
                color="red"
            ),
            StorySegment(
                "【 WARNING: 20층 - 시공의 틈새 】",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "시간과 공간의 경계가 사라진다...\n",
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "\n이곳은... 어디인가?",
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
                "\n긴 흑발, 한 손의 창.",
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
                "\n\"10만 번... 10만 번이나 봤다...\"",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\n\"인류의 멸망을...\"",
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
                "\n\n시간의 모래가 빠르게 흘러내린다...",
                pause=0.5,
                color="yellow"
            ),
            StorySegment(
                "⚠️  경고: 7분 30초 안에 격파 필요  ⚠️",
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "\n운명의 순간이 다가온다...\n",
                pause=1.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n그의 창과 눈동자가 붉게 빛난다─",
                pause=1.0,
                color="red"
            ),
        ]

    def get_sephiroth_defeat_story(self) -> List[StorySegment]:
        """세피로스 격파 스토리"""
        return [
            StorySegment(
                "\n\n승리의 빛이 세상을 감싼다...",
                pause=0.5,
                color="cyan"
            ),
            StorySegment(
                "【 세피로스 격파 】",
                pause=1.5,
                color="cyan"
            ),
            StorySegment(
                "영웅의 시대가 열리다...\n",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "\n\n...불가능한 일이 일어났다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n세피로스가 무릎을 꿇는다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n\"...감사하다...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"...너는 포기하지 않았구나...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"...10만 번의 타임라인 중에서...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"...단 한 번도 본 적 없는 미래...\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n그의 몸이 빛의 입자로 흩어지기 시작한다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n\"...이제야 쉴 수 있겠어...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"...별빛의 여명...\"",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "\n\"...드디어 찾아왔구나...\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n마지막 미소를 지으며, 그는 사라진다.",
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n\n새로운 평화가 찾아온다...\n",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "\n시공의 균열이 서서히 닫히기 시작한다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n시간의 흐름이 정상으로 돌아온다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n1,000개의 영혼이 안식을 찾는다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n당신은 세계를 구했다.",
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n그리고... 한 영혼을 해방시켰다.",
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n별들의 여명이 밝아온다...",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "【 TRUE ENDING 】",
                pause=3.0,
                color="cyan"
            ),
            StorySegment(
                "─ Dawn of Stellar ─",
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "희망의 빛이 영원히 빛난다...",
                pause=5.0,
                color="cyan"
            ),
        ]

    def get_sephiroth_timeout_story(self) -> List[StorySegment]:
        """세피로스 타임오버 스토리 (7분 30초 초과)"""
        return [
            StorySegment(
                "\n\n시간의 벽이 무너져내린다...",
                pause=0.5,
                color="red"
            ),
            StorySegment(
                "【 타임라인 붕괴 】",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "세계가 영원히 사라진다...\n",
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "\n\n세피로스가 완전히 각성한다.",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\n\"...늦었어...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\"...나는 이제 멈출 수 없어...\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\"...미안하다...\"",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "\n\n시공간이 무너지기 시작한다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n과거와 미래가 뒤섞인다.",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n차원의 경계가 사라진다.",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n\n모든 것이 무(無)로 돌아간다.",
                pause=3.0,
                color="dark"
            ),
            StorySegment(
                "\n\n어둠이 모든 것을 삼킨다...",
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "【 GAME OVER 】",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "타임라인 붕괴 - 시공 붕괴로 인한 멸망",
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "영원한 어둠 속으로...",
                pause=5.0,
                color="red"
            ),
        ]

    def get_cain_encounter_story(self) -> List[StorySegment]:
        """카인 조우 스토리 (30층)"""
        return [
            StorySegment(
                "\n\n시간의 심장부에 도달했다...",
                pause=0.5,
                color="dark"
            ),
            StorySegment(
                "【 WARNING: 30층 - 시간의 왕좌 】",
                pause=1.5,
                color="dark"
            ),
            StorySegment(
                "시간의 심장이 고동치기 시작한다...\n",
                pause=1.0,
                color="dark"
            ),
            StorySegment(
                "\n시공간이 왜곡되어 있다.",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n무수한 타임라인의 잔해들이 떠다닌다.",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n\n그리고... 중앙의 거대한 왕좌.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n그 위에 앉아있는 남자.",
                pause=2.5,
                color="dark"
            ),
            StorySegment(
                "\n\n닥터 아벨 카인.",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n\"오, 세피로스를 죽인 자인가.\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"흥미롭군. 10만 번의 타임라인 중 이런 경우는 처음이야.\"",
                pause=2.5,
                color="dark"
            ),
            StorySegment(
                "\n\n\"나는 아벨 카인.\"",
                pause=1.5,
                color="dark"
            ),
            StorySegment(
                "\n\"세피로스의 창조자이자...\"",
                pause=1.5,
                color="dark"
            ),
            StorySegment(
                "\n\"모든 비극의 설계자지.\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n\"세피로스가 10만 번 고통받은 것은...\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"내가 원했기 때문이야.\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n\"그 덕분에 나는 시간을 초월했어.\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"나는 이제 신이야.\"",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n시간의 시계가 빠르게 흘러간다...",
                pause=0.5,
                color="yellow"
            ),
            StorySegment(
                "⚠️  경고: 4분 안에 격파 필요  ⚠️",
                pause=2.0,
                color="yellow"
            ),
            StorySegment(
                "운명의 시간이 흘러간다...\n",
                pause=1.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n\"4분을 주지. 날 죽여봐.\"",
                pause=1.5,
                color="dark"
            ),
            StorySegment(
                "\n\"하하하하!\"",
                pause=1.0,
                color="red"
            ),
        ]

    def get_cain_defeat_story(self) -> List[StorySegment]:
        """카인 격파 스토리 (트루 엔딩)"""
        return [
            StorySegment(
                "\n\n시간의 흐름이 멈추었다...",
                pause=0.5,
                color="cyan"
            ),
            StorySegment(
                "【 카인 격파 】",
                pause=1.5,
                color="cyan"
            ),
            StorySegment(
                "새로운 미래가 열리다...\n",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "\n\n카인이 무릎을 꿇는다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n\"...불가능해... 내가... 질 리가...\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"...난 모든 미래를 봤는데...\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"...이 결말은... 없었어...\"",
                pause=2.5,
                color="dark"
            ),
            StorySegment(
                "\n\n그의 몸이 시공간의 왜곡과 함께 무너진다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n\"...세피로스... 네가 옳았어...\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"...영원히 사는 것보다...\"",
                pause=1.5,
                color="dark"
            ),
            StorySegment(
                "\n\"...불꽃처럼 타오르는 게...\"",
                pause=1.5,
                color="dark"
            ),
            StorySegment(
                "\n\"...더... 아름다울지도...\"",
                pause=2.5,
                color="dark"
            ),
            StorySegment(
                "\n\n그는 희미하게 웃으며 소멸한다.",
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n\n시간의 왕좌가 무너진다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n모든 타임라인의 왜곡이 해소된다.",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n\n시간의 균열이 서서히 아문다...\n",
                pause=1.0,
                color="white"
            ),
            StorySegment(
                "\n세피로스의 목소리가 들린다...",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n\"...고마워...\"",
                pause=1.5,
                color="cyan"
            ),
            StorySegment(
                "\n\"...이제... 모든 것이... 끝났어...\"",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n\"...별빛의 여명은...\"",
                pause=1.5,
                color="cyan"
            ),
            StorySegment(
                "\n\"...네가 가져왔어...\"",
                pause=2.5,
                color="cyan"
            ),
            StorySegment(
                "\n\n새로운 시대의 서막이 열린다...\n",
                pause=1.0,
                color="yellow"
            ),
            StorySegment(
                "\n2169년, 시공간은 안정되었다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n인류는 두 번째 황금시대를 맞이했다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n그리고 사람들은 전설을 이야기한다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n시공의 틈새를 넘어,",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n신이 된 악마를 쓰러뜨린,",
                pause=1.5,
                color="white"
            ),
            StorySegment(
                "\n이름 없는 영웅의 이야기를.",
                pause=2.5,
                color="white"
            ),
            StorySegment(
                "\n\n\"별빛의 여명은, 가장 긴 밤 끝에서 찾아온다.\"",
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "\n\n별빛이 영원히 빛난다...",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "【 PERFECT ENDING 】",
                pause=3.0,
                color="cyan"
            ),
            StorySegment(
                "─ Dawn of Stellar ─",
                pause=3.0,
                color="yellow"
            ),
            StorySegment(
                "희망이 세상을 가득 채운다...",
                pause=5.0,
                color="cyan"
            ),
        ]

    def get_cain_timeout_story(self) -> List[StorySegment]:
        """카인 타임오버 스토리 (4분 초과)"""
        return [
            StorySegment(
                "\n\n시간의 균열이 커진다...",
                pause=0.5,
                color="red"
            ),
            StorySegment(
                "【 시공 소멸 】",
                pause=1.5,
                color="red"
            ),
            StorySegment(
                "세계가 무너져내린다...\n",
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "\n\n카인이 웃으며 일어선다.",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\n\"시간이 없어지는군.\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"재밌었어. 하지만 여기까지야.\"",
                pause=2.5,
                color="dark"
            ),
            StorySegment(
                "\n\n카인이 손가락을 튕긴다.",
                pause=2.0,
                color="white"
            ),
            StorySegment(
                "\n\n모든 타임라인이 동시에 붕괴한다.",
                pause=2.5,
                color="red"
            ),
            StorySegment(
                "\n\n\"모든 가능성이 사라졌어.\"",
                pause=2.0,
                color="dark"
            ),
            StorySegment(
                "\n\"과거도, 현재도, 미래도... 전부 무(無)로.\"",
                pause=2.5,
                color="dark"
            ),
            StorySegment(
                "\n\n시간의 흐름이 영원히 멈춘다...\n",
                pause=1.0,
                color="cyan"
            ),
            StorySegment(
                "\n세피로스의 목소리가 들린다...",
                pause=2.0,
                color="cyan"
            ),
            StorySegment(
                "\n\"...미안해... 내가... 더 강했어야 했는데...\"",
                pause=2.5,
                color="cyan"
            ),
            StorySegment(
                "\n\n모든 것이 어둠에 삼켜진다.",
                pause=3.0,
                color="dark"
            ),
            StorySegment(
                "\n\n어둠이 모든 존재를 집어삼킨다...",
                pause=1.0,
                color="red"
            ),
            StorySegment(
                "【 GAME OVER 】",
                pause=2.0,
                color="red"
            ),
            StorySegment(
                "시공 소멸 - 모든 타임라인 붕괴",
                pause=3.0,
                color="red"
            ),
            StorySegment(
                "영원한 공허 속으로...",
                pause=5.0,
                color="red"
            ),
        ]

    @staticmethod
    def from_dict(data: dict) -> 'StorySystem':
        """딕셔너리에서 스토리 시스템 복원"""
        system = StorySystem()
        system.current_chapter = data.get("current_chapter", 0)
        system.story_seen = data.get("story_seen", False)
        system.sephiroth_encountered = data.get("sephiroth_encountered", False)
        system.sephiroth_defeated = data.get("sephiroth_defeated", False)
        system.true_ending_unlocked = data.get("true_ending_unlocked", False)
        system.glitch_mode = data.get("glitch_mode", False)
        
        # 카인 처치 여부 복원 (추가 속성)
        system.cain_defeated = data.get("cain_defeated", False)
        
        return system

    def to_dict(self) -> dict:
        """스토리 시스템 상태를 딕셔너리로 변환"""
        return {
            "current_chapter": self.current_chapter,
            "story_seen": self.story_seen,
            "sephiroth_encountered": self.sephiroth_encountered,
            "sephiroth_defeated": self.sephiroth_defeated,
            "true_ending_unlocked": self.true_ending_unlocked,
            "glitch_mode": self.glitch_mode,
            "cain_defeated": getattr(self, 'cain_defeated', False)
        }

    def get_floor_message(self, floor: int) -> str:
        """층별 메시지"""
        messages = {
            1: "여정의 시작",
            5: "시간의 균열이 느껴진다...",
            10: "무언가 강력한 존재의 기운이...",
            14: "경고: 강력한 적의 기운!",
            15: "??? - 시공의 틈새 ???",
            19: "⚠️ 경고: 최종 보스 직전 ⚠️",
            20: "【 20층 - 시공의 틈새 】",
            29: "⚠️⚠️ 경고: 진정한 악의 기운! ⚠️⚠️",
            30: "【 30층 - 시간의 왕좌 】",
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
