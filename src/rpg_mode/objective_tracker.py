"""
RPG 모드 현재 목표 추적 시스템

화면 상단에 현재 해야 할 일을 상시 표시한다.
"""

from dataclasses import dataclass
from typing import Optional

from src.core.logger import get_logger

logger = get_logger("objective_tracker")


@dataclass
class ObjectiveState:
    """현재 목표 상태"""
    main_text: str           # "보스 던전을 찾아 클리어하세요"
    sub_text: str = ""       # "엔트리아의 정원을 찾아보세요"
    chapter_number: int = 0
    chapter_title: str = ""


# 챕터별 기본 목표 텍스트
_CHAPTER_OBJECTIVES = {
    0: ("마을을 둘러보고 동굴을 탐험하세요", "릴리와 함께 마을 시설을 확인해보세요"),
    1: ("잊혀진 숲을 탐험하세요", "동굴에서 레벨을 올리고 보스에 도전하세요"),
    2: ("황혼의 사막으로 이동하세요", "사막의 유적에 숨겨진 비밀을 찾으세요"),
    3: ("심연의 동굴을 탐험하세요", "동굴 깊은 곳의 속삭임을 따라가세요"),
    4: ("폭풍의 고원으로 향하세요", "폭풍의 근원을 찾으세요"),
    5: ("영원의 빙원을 탐험하세요", "얼어붙은 시간 속의 진실을 찾으세요"),
    6: ("전쟁의 대지로 이동하세요", "카인의 흔적을 추적하세요"),
    7: ("별빛의 왕좌를 향해 나아가세요", "최종 결전을 준비하세요"),
    8: ("세피로스를 만나세요", "잔향의 진실을 마주하세요"),
    9: ("별빛의 왕좌에서 카인과 대면하세요", "최후의 전투를 준비하세요"),
    10: ("카인을 물리치세요", "이 세계의 운명을 결정하세요"),
}

# 지역별 보스 관련 목표
_BOSS_OBJECTIVES = {
    "forgotten_forest": "보스 '엔트리아의 정원'을 찾아 클리어하세요",
    "twilight_desert": "보스 '스콜피온의 소굴'을 찾아 클리어하세요",
    "abyss_cavern": "보스 '아비소스의 심연'을 찾아 클리어하세요",
    "storm_plateau": "보스 '볼타르크의 둥지'를 찾아 클리어하세요",
    "eternal_glacier": "보스 '글라시아의 왕궁'을 찾아 클리어하세요",
    "war_lands": "보스 '벨리거의 전장'을 찾아 클리어하세요",
    "starlight_throne": "최종 보스 '잔향의 카인'과 대면하세요",
}


class RPGObjectiveTracker:
    """RPG 모드 현재 목표 추적기"""

    def __init__(self, chapter_system=None):
        self.chapter_system = chapter_system
        self.current = ObjectiveState(main_text="마을을 둘러보세요")
        self._override_text: Optional[str] = None

    def set_override(self, text: str):
        """임시 목표 텍스트 오버라이드 (이벤트 중)"""
        self._override_text = text

    def clear_override(self):
        """오버라이드 해제"""
        self._override_text = None

    def update(self, progress) -> ObjectiveState:
        """진행 상태에 따라 현재 목표 업데이트"""
        ch = progress.current_chapter
        region = progress.current_region

        # 챕터 제목
        chapter_title = ""
        if self.chapter_system:
            ch_info = self.chapter_system.get_chapter_info(ch)
            if ch_info:
                chapter_title = ch_info.title

        # 오버라이드가 있으면 그것을 표시
        if self._override_text:
            self.current = ObjectiveState(
                main_text=self._override_text,
                chapter_number=ch,
                chapter_title=chapter_title,
            )
            return self.current

        # 현재 지역 보스를 잡았는지 확인
        if region in progress.defeated_bosses:
            # 보스 잡음 → 다음 지역으로 이동 안내
            main = "다음 지역으로 이동하세요"
            sub = "지역 허브(ESC)에서 새 지역을 선택할 수 있습니다"
        elif region in _BOSS_OBJECTIVES:
            # 보스 미처치 → 보스 안내
            main = _BOSS_OBJECTIVES[region]
            sub = "동굴(O)에서 레벨을 올리고 보스에 도전하세요"
        else:
            # 기본 챕터 목표
            objectives = _CHAPTER_OBJECTIVES.get(ch, ("탐험을 계속하세요", ""))
            main = objectives[0]
            sub = objectives[1] if len(objectives) > 1 else ""

        self.current = ObjectiveState(
            main_text=main,
            sub_text=sub,
            chapter_number=ch,
            chapter_title=chapter_title,
        )
        return self.current
