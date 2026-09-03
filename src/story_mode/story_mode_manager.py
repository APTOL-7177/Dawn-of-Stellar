"""
스토리 모드 매니저
Dawn of Stellar - 별빛의 여명

스토리 모드의 진입, 챕터 전환, 세이브/로드를 총괄합니다.
5막 42챕터 구성 (15~20시간 분량)
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import tcod.console
import tcod.event
from src.ui.input_handler import poll_game_input, GameAction

from src.core.logger import get_logger
from src.audio import play_bgm

logger = get_logger("story_mode")

SAVE_PATH = Path("user_data/story_progress.json")

# =============================================================================
# 5막 42챕터 구조
# =============================================================================

# 막(Act) 정보
ACT_INFO = {
    "act1": {"title": "제1막", "subtitle": "시공의 각성", "color": (100, 200, 255)},
    "act2": {"title": "제2막", "subtitle": "전사의 길", "color": (255, 100, 100)},
    "act3": {"title": "제3막", "subtitle": "세계의 비밀", "color": (100, 255, 100)},
    "act4": {"title": "제4막", "subtitle": "시간의 미궁", "color": (255, 200, 100)},
    "act5": {"title": "제5막", "subtitle": "별빛의 여명", "color": (200, 150, 255)},
}

# 챕터 순서 (42개)
CHAPTER_ORDER = [
    # ── 제1막: 시공의 각성 (기초) ── 8챕터
    "act1_prologue",
    "act1_ch1",
    "act1_ch2",
    "act1_ch3",
    "act1_ch4",      # NEW: 경험의 보상
    "act1_ch5",      # was act1_ch4: 어둠의 복도
    "act1_ch6",      # NEW: 기억의 보존
    "act1_boss",
    # ── 제2막: 전사의 길 (전투 심화) ── 8챕터
    "act2_ch1",
    "act2_ch2",
    "act2_ch3",
    "act2_ch4",      # NEW: 소지품 정리
    "act2_ch5",      # was act2_ch4: 방어의 기술
    "act2_ch6",      # was act2_ch5: 팀워크의 힘
    "act2_ch7",      # NEW: 도전의 강도
    "act2_boss",
    # ── 제3막: 세계의 비밀 (시스템) ── 10챕터
    "act3_ch1",
    "act3_ch2",      # NEW: 강화의 기술
    "act3_ch3",      # was act3_ch2: 아이템의 지혜
    "act3_ch4",      # NEW: 연금술의 세계
    "act3_ch5",      # was act3_ch3: 리나의 주방
    "act3_ch6",      # NEW: 폭발의 기술
    "act3_ch7",      # was act3_ch4: 재료 사냥꾼
    "act3_ch8",      # NEW: 상인의 길
    "act3_ch9",      # was act3_ch5: 상처와 치유
    "act3_boss",
    # ── 제4막: 시간의 미궁 (던전/퀘스트) ── 8챕터
    "act4_ch1",
    "act4_ch2",
    "act4_ch3",
    "act4_ch4",      # NEW: 모험가의 전당
    "act4_ch5",      # was act4_ch4: 직업의 각성
    "act4_ch6",      # was act4_ch5: 기믹의 진수
    "act4_ch7",      # NEW: 전사들의 편대
    "act4_boss",
    # ── 제5막: 별빛의 여명 (종결) ── 8챕터
    "act5_ch1",
    "act5_ch2",
    "act5_ch3",
    "act5_ch4",      # NEW: 시간의 심판
    "act5_ch5",      # was act5_ch4: 10만 번째 밤
    "act5_ch6",      # NEW: 함께하는 모험
    "act5_ch7",      # was act5_ch5: 최후의 시련
    "act5_finale",
]

# 챕터 메타 정보 (42개)
CHAPTER_META = {
    # ═══════════════════════════════════════════════════════════════
    # 제1막: 시공의 각성 — 기본 조작과 세계관 도입
    # ═══════════════════════════════════════════════════════════════
    "act1_prologue": {
        "title": "1-프롤로그",
        "subtitle": "시공에서 깨어나다",
        "npc_guide": "selena",
        "act": "act1",
        "learning": "이동, 상호작용(Z/X), 맵 타일 읽기",
    },
    "act1_ch1": {
        "title": "1-1장",
        "subtitle": "첫 번째 전투",
        "npc_guide": "karnos",
        "act": "act1",
        "learning": "ATB 게이지의 작동 원리, 행동 선택",
    },
    "act1_ch2": {
        "title": "1-2장",
        "subtitle": "용기의 일격",
        "npc_guide": "karnos",
        "act": "act1",
        "learning": "BRV 공격과 HP 공격의 전략적 사용",
    },
    "act1_ch3": {
        "title": "1-3장",
        "subtitle": "부서지는 갑옷",
        "npc_guide": "karnos",
        "act": "act1",
        "learning": "BREAK 시스템, 보너스 BRV, 연계 공격",
    },
    "act1_ch4": {
        "title": "1-4장",
        "subtitle": "경험의 보상",
        "npc_guide": "karnos",
        "act": "act1",
        "learning": "경험치 획득, 레벨업 시스템, 스탯 성장",
    },
    "act1_ch5": {
        "title": "1-5장",
        "subtitle": "어둠의 복도",
        "npc_guide": "selena",
        "act": "act1",
        "learning": "던전 탐험 기초, 시야(FOV), 아이템 줍기",
    },
    "act1_ch6": {
        "title": "1-6장",
        "subtitle": "기억의 보존",
        "npc_guide": "selena",
        "act": "act1",
        "learning": "저장/로드 시스템, 자동저장 vs 수동저장",
    },
    "act1_boss": {
        "title": "1-보스",
        "subtitle": "시간의 파수꾼",
        "npc_guide": "selena",
        "act": "act1",
        "learning": "보스전 전략, ATB+BRV 종합 활용",
    },
    # ═══════════════════════════════════════════════════════════════
    # 제2막: 전사의 길 — 전투 시스템 심화
    # ═══════════════════════════════════════════════════════════════
    "act2_ch1": {
        "title": "2-1장",
        "subtitle": "미라의 수업",
        "npc_guide": "mira",
        "act": "act2",
        "learning": "스킬 사용, MP 관리, 캐스팅 타이밍",
    },
    "act2_ch2": {
        "title": "2-2장",
        "subtitle": "불꽃과 얼음",
        "npc_guide": "mira",
        "act": "act2",
        "learning": "속성 상성 (화/빙/뢰/수/지/풍/성/암), 약점 공략",
    },
    "act2_ch3": {
        "title": "2-3장",
        "subtitle": "동료의 합류",
        "npc_guide": "karnos",
        "act": "act2",
        "learning": "2인 파티 전투, 턴 순서 관리",
    },
    "act2_ch4": {
        "title": "2-4장",
        "subtitle": "소지품 정리",
        "npc_guide": "tord",
        "act": "act2",
        "learning": "인벤토리 관리, 무게 시스템, 아이템 정리",
    },
    "act2_ch5": {
        "title": "2-5장",
        "subtitle": "방어의 기술",
        "npc_guide": "karnos",
        "act": "act2",
        "learning": "방어, 도주, 위기 관리 전략",
    },
    "act2_ch6": {
        "title": "2-6장",
        "subtitle": "팀워크의 힘",
        "npc_guide": "selena",
        "act": "act2",
        "learning": "팀워크 게이지, 합체기, 연계 전략",
    },
    "act2_ch7": {
        "title": "2-7장",
        "subtitle": "도전의 강도",
        "npc_guide": "selena",
        "act": "act2",
        "learning": "난이도 설정 (5단계), 보상 차이",
    },
    "act2_boss": {
        "title": "2-보스",
        "subtitle": "왜곡된 장군",
        "npc_guide": "karnos",
        "act": "act2",
        "learning": "다수 적 상대, 스킬+파티 종합 전투",
    },
    # ═══════════════════════════════════════════════════════════════
    # 제3막: 세계의 비밀 — 장비/요리/아이템 시스템
    # ═══════════════════════════════════════════════════════════════
    "act3_ch1": {
        "title": "3-1장",
        "subtitle": "토르드의 대장간",
        "npc_guide": "tord",
        "act": "act3",
        "learning": "장비 장착, 무기/방어구/장신구 시스템",
    },
    "act3_ch2": {
        "title": "3-2장",
        "subtitle": "강화의 기술",
        "npc_guide": "tord",
        "act": "act3",
        "learning": "대장간 강화, 재연마(접사 변경), 내구도 시스템",
    },
    "act3_ch3": {
        "title": "3-3장",
        "subtitle": "아이템의 지혜",
        "npc_guide": "tord",
        "act": "act3",
        "learning": "포션, 에테르, 전투 아이템 활용",
    },
    "act3_ch4": {
        "title": "3-4장",
        "subtitle": "연금술의 세계",
        "npc_guide": "mira",
        "act": "act3",
        "learning": "연금술 레시피, 포션 제작, 걸작 시스템",
    },
    "act3_ch5": {
        "title": "3-5장",
        "subtitle": "리나의 주방",
        "npc_guide": "lina",
        "act": "act3",
        "learning": "요리 시스템, 4슬롯 냄비 조합, 요리솥 보너스",
    },
    "act3_ch6": {
        "title": "3-6장",
        "subtitle": "폭발의 기술",
        "npc_guide": "lina",
        "act": "act3",
        "learning": "폭탄 제작, 범위 공격, 전략적 활용",
    },
    "act3_ch7": {
        "title": "3-7장",
        "subtitle": "재료 사냥꾼",
        "npc_guide": "lina",
        "act": "act3",
        "learning": "채집, 필드 스킬, 요리 버프 전투 활용",
    },
    "act3_ch8": {
        "title": "3-8장",
        "subtitle": "상인의 길",
        "npc_guide": "tord",
        "act": "act3",
        "learning": "골드 상점, 별조각 상점, 경제 시스템",
    },
    "act3_ch9": {
        "title": "3-9장",
        "subtitle": "상처와 치유",
        "npc_guide": "selena",
        "act": "act3",
        "learning": "상처 시스템, 영구 HP 감소, 치유 전략",
    },
    "act3_boss": {
        "title": "3-보스",
        "subtitle": "차원의 미식가",
        "npc_guide": "lina",
        "act": "act3",
        "learning": "장비+요리+아이템 종합 전투",
    },
    # ═══════════════════════════════════════════════════════════════
    # 제4막: 시간의 미궁 — 던전/퀘스트/직업 시스템
    # ═══════════════════════════════════════════════════════════════
    "act4_ch1": {
        "title": "4-1장",
        "subtitle": "던전의 법칙",
        "npc_guide": "selena",
        "act": "act4",
        "learning": "함정, 잠긴 문, 열쇠, 비밀 통로",
    },
    "act4_ch2": {
        "title": "4-2장",
        "subtitle": "어둠 속의 빛",
        "npc_guide": "selena",
        "act": "act4",
        "learning": "FOV 심화, 적 AI(추적/포위), 회피 전략",
    },
    "act4_ch3": {
        "title": "4-3장",
        "subtitle": "의뢰인의 부탁",
        "npc_guide": "mira",
        "act": "act4",
        "learning": "퀘스트 시스템, 현상금/수집/탐험 퀘스트",
    },
    "act4_ch4": {
        "title": "4-4장",
        "subtitle": "모험가의 전당",
        "npc_guide": "selena",
        "act": "act4",
        "learning": "길드 홀, 도전과제, 마일스톤 보상",
    },
    "act4_ch5": {
        "title": "4-5장",
        "subtitle": "직업의 각성",
        "npc_guide": "karnos",
        "act": "act4",
        "learning": "35개 직업 소개, 기믹 시스템 기초",
    },
    "act4_ch6": {
        "title": "4-6장",
        "subtitle": "기믹의 진수",
        "npc_guide": "mira",
        "act": "act4",
        "learning": "직업 기믹 심화, 스탠스/게이지/변신 등",
    },
    "act4_ch7": {
        "title": "4-7장",
        "subtitle": "전사들의 편대",
        "npc_guide": "karnos",
        "act": "act4",
        "learning": "파티 구성 UI, 역할 분담 전략",
    },
    "act4_boss": {
        "title": "4-보스",
        "subtitle": "미궁의 수호자",
        "npc_guide": "selena",
        "act": "act4",
        "learning": "다층 던전 종합, 퀘스트+전투 복합",
    },
    # ═══════════════════════════════════════════════════════════════
    # 제5막: 별빛의 여명 — 최종 도전과 결말
    # ═══════════════════════════════════════════════════════════════
    "act5_ch1": {
        "title": "5-1장",
        "subtitle": "상태이상의 전쟁",
        "npc_guide": "mira",
        "act": "act5",
        "learning": "110+종 상태이상, 버프/디버프 전략",
    },
    "act5_ch2": {
        "title": "5-2장",
        "subtitle": "별의 파편",
        "npc_guide": "selena",
        "act": "act5",
        "learning": "메타 진행, 별조각, 직업 해금, 패시브",
    },
    "act5_ch3": {
        "title": "5-3장",
        "subtitle": "시공의 전사들",
        "npc_guide": "karnos",
        "act": "act5",
        "learning": "3~4인 파티 고급 전투, 복합 전략",
    },
    "act5_ch4": {
        "title": "5-4장",
        "subtitle": "시간의 심판",
        "npc_guide": "selena",
        "act": "act5",
        "learning": "보스 기믹/타이머, 패턴 공략",
    },
    "act5_ch5": {
        "title": "5-5장",
        "subtitle": "10만 번째 밤",
        "npc_guide": "selena",
        "act": "act5",
        "learning": "세피로스 배경 스토리, 시공 교란의 진실",
    },
    "act5_ch6": {
        "title": "5-6장",
        "subtitle": "함께하는 모험",
        "npc_guide": "selena",
        "act": "act5",
        "learning": "2~4인 협동 멀티플레이 소개 (WebSocket 호스트-클라이언트, 선점 전리품, 창고 공유)",
    },
    "act5_ch7": {
        "title": "5-7장",
        "subtitle": "최후의 시련",
        "npc_guide": "karnos",
        "act": "act5",
        "learning": "5층 미니 던전, 연속 보스전",
    },
    "act5_finale": {
        "title": "5-피날레",
        "subtitle": "별빛의 여명",
        "npc_guide": "selena",
        "act": "act5",
        "learning": "직업 선택, 메인 게임 전환, 최종 보상",
    },
}


class StoryModeResult(Enum):
    """스토리 모드 결과"""
    COMPLETED = "completed"
    CHAPTER_COMPLETED = "chapter_completed"
    QUIT_TO_MENU = "quit_to_menu"
    TRANSITION_TO_GAME = "transition_to_game"


@dataclass
class ChapterState:
    """챕터 진행 상태"""
    completed: bool = False
    play_time: float = 0.0
    skipped: bool = False

    def to_dict(self) -> dict:
        return {
            "completed": self.completed,
            "play_time": self.play_time,
            "skipped": self.skipped,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChapterState":
        return cls(
            completed=data.get("completed", False),
            play_time=data.get("play_time", 0.0),
            skipped=data.get("skipped", False),
        )


@dataclass
class StoryModeProgress:
    """스토리 모드 진행 상태"""
    completed_chapters: List[str] = field(default_factory=list)
    current_chapter: Optional[str] = None
    chapter_states: Dict[str, ChapterState] = field(default_factory=dict)
    selected_job: Optional[str] = None
    total_play_time: float = 0.0

    def is_chapter_unlocked(self, chapter_id: str) -> bool:
        """챕터 잠금 해제 여부"""
        idx = CHAPTER_ORDER.index(chapter_id) if chapter_id in CHAPTER_ORDER else -1
        if idx <= 0:
            return True
        prev = CHAPTER_ORDER[idx - 1]
        return prev in self.completed_chapters

    def is_chapter_completed(self, chapter_id: str) -> bool:
        """챕터 완료 여부"""
        return chapter_id in self.completed_chapters

    def complete_chapter(self, chapter_id: str, play_time: float = 0.0, skipped: bool = False):
        """챕터 완료 처리"""
        if chapter_id not in self.completed_chapters:
            self.completed_chapters.append(chapter_id)
        self.chapter_states[chapter_id] = ChapterState(
            completed=True, play_time=play_time, skipped=skipped
        )
        idx = CHAPTER_ORDER.index(chapter_id) if chapter_id in CHAPTER_ORDER else -1
        if idx >= 0 and idx + 1 < len(CHAPTER_ORDER):
            self.current_chapter = CHAPTER_ORDER[idx + 1]
        else:
            self.current_chapter = None

    def get_next_chapter(self) -> Optional[str]:
        """다음 진행할 챕터"""
        if self.current_chapter:
            return self.current_chapter
        for ch in CHAPTER_ORDER:
            if ch not in self.completed_chapters:
                return ch
        return None

    def is_all_completed(self) -> bool:
        """전체 완료 여부"""
        return all(ch in self.completed_chapters for ch in CHAPTER_ORDER)

    def get_current_act(self) -> Optional[str]:
        """현재 진행 중인 막"""
        next_ch = self.get_next_chapter()
        if next_ch:
            return CHAPTER_META.get(next_ch, {}).get("act", "act1")
        return None

    def to_dict(self) -> dict:
        return {
            "completed_chapters": self.completed_chapters,
            "current_chapter": self.current_chapter,
            "chapter_states": {
                k: v.to_dict() for k, v in self.chapter_states.items()
            },
            "selected_job": self.selected_job,
            "total_play_time": self.total_play_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StoryModeProgress":
        # v2 → v3 마이그레이션: 챕터 ID 변경 (30→42챕터 확장)
        _OLD_TO_NEW_ID = {
            "act1_ch4": "act1_ch5",
            "act2_ch4": "act2_ch5",
            "act2_ch5": "act2_ch6",
            "act3_ch2": "act3_ch3",
            "act3_ch3": "act3_ch5",
            "act3_ch4": "act3_ch7",
            "act3_ch5": "act3_ch9",
            "act4_ch4": "act4_ch5",
            "act4_ch5": "act4_ch6",
            "act5_ch4": "act5_ch5",
            "act5_ch5": "act5_ch7",
        }
        version = data.get("version", "1.0.0")
        version_parts = [int(x) for x in version.split(".")]
        if version_parts < [3, 0, 0]:
            # completed_chapters 마이그레이션
            old_completed = data.get("completed_chapters", [])
            data["completed_chapters"] = [
                _OLD_TO_NEW_ID.get(ch, ch) for ch in old_completed
            ]
            # current_chapter 마이그레이션
            cur = data.get("current_chapter")
            if cur and cur in _OLD_TO_NEW_ID:
                data["current_chapter"] = _OLD_TO_NEW_ID[cur]
            # chapter_states 마이그레이션
            old_states = data.get("chapter_states", {})
            new_states = {}
            for k, v in old_states.items():
                new_key = _OLD_TO_NEW_ID.get(k, k)
                new_states[new_key] = v
            data["chapter_states"] = new_states

        progress = cls()
        progress.completed_chapters = data.get("completed_chapters", [])
        progress.current_chapter = data.get("current_chapter")
        progress.selected_job = data.get("selected_job")
        progress.total_play_time = data.get("total_play_time", 0.0)
        for k, v in data.get("chapter_states", {}).items():
            progress.chapter_states[k] = ChapterState.from_dict(v)
        return progress


class StoryModeManager:
    """
    스토리 모드 총괄 매니저

    5막 42챕터 구성, 15~20시간 분량
    """

    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.progress = StoryModeProgress()

    def run(self) -> StoryModeResult:
        """스토리 모드 메인 루프"""
        self.load_progress()
        play_bgm("main_menu")

        while True:
            from src.story_mode.chapter_select_ui import run_chapter_select
            selected = run_chapter_select(
                self.console, self.context, self.progress
            )

            if selected is None:
                return StoryModeResult.QUIT_TO_MENU

            if selected == "__skip_all__":
                for ch in CHAPTER_ORDER:
                    self.progress.complete_chapter(ch, skipped=True)
                self.save_progress()
                logger.info("전체 챕터 스킵 - 메인 게임 전환")
                return StoryModeResult.TRANSITION_TO_GAME

            # 막 전환 연출
            meta = CHAPTER_META.get(selected, {})
            current_act = meta.get("act", "act1")
            self._show_act_transition_if_needed(selected, current_act)

            # 챕터 실행
            from src.story_mode.chapter_runner import ChapterRunner
            runner = ChapterRunner(self.console, self.context)
            # 보상 exactly-once 판단용: 실행 직전의 진행 상태 스냅샷
            runner._last_progress = self.progress

            chapter_start = time.time()
            result = runner.run_chapter(selected, self.progress)
            chapter_time = time.time() - chapter_start

            if result == "completed":
                self.progress.complete_chapter(selected, play_time=chapter_time)
                self.progress.total_play_time += chapter_time
                self.save_progress()
                logger.info(f"챕터 '{selected}' 완료 ({chapter_time:.1f}초)")

                if selected == "act5_finale":
                    logger.info("피날레 완료 - 메인 게임 전환")
                    return StoryModeResult.TRANSITION_TO_GAME

            elif result == "skipped":
                self.progress.complete_chapter(selected, play_time=0, skipped=True)
                self.save_progress()
                logger.info(f"챕터 '{selected}' 스킵")

            elif result == "quit":
                self.save_progress()
                return StoryModeResult.QUIT_TO_MENU

    def _show_act_transition_if_needed(self, chapter_id: str, act_id: str):
        """새 막 시작 시 전환 연출 - 드라마틱한 Act 전환"""
        # 해당 막의 첫 챕터인 경우만
        act_first_chapters = {
            "act1": "act1_prologue",
            "act2": "act2_ch1",
            "act3": "act3_ch1",
            "act4": "act4_ch1",
            "act5": "act5_ch1",
        }
        if chapter_id != act_first_chapters.get(act_id):
            return
        # 이미 완료한 막이면 스킵
        if self.progress.is_chapter_completed(chapter_id):
            return

        act_info = ACT_INFO.get(act_id, {})
        title = act_info.get("title", "")
        subtitle = act_info.get("subtitle", "")
        color = act_info.get("color", (200, 200, 255))

        import math
        import random

        w, h = self.console.width, self.console.height
        cx, cy = w // 2, h // 2

        # Act별 고유 모티브 문자
        act_motifs = {
            "act1": ["✦", "★", "+", "*"],              # 각성 - 별빛
            "act2": ["◆", "★", "+", ">"],              # 전투 - 무기
            "act3": ["◆", "◇", "✦", "*"],              # 비밀 - 보석
            "act4": ["※", "◆", "+", "·"],              # 미궁 - 미로
            "act5": ["★", "☆", "✦", "+"],              # 여명 - 별
        }
        motifs = act_motifs.get(act_id, ["✦", "★", "+", "·"])

        # Act별 고유 부제 (분위기 텍스트)
        act_taglines = {
            "act1": "시간의 균열 너머, 새로운 여정이 시작된다...",
            "act2": "검을 들어라. 진정한 전사의 길이 열린다...",
            "act3": "세계의 이면에 감춰진 비밀을 밝혀라...",
            "act4": "끝없는 미궁 속에서 진실을 찾아라...",
            "act5": "마지막 밤이 밝아온다. 별빛의 여명이여...",
        }
        tagline = act_taglines.get(act_id, "")

        # 파티클 생성
        particles = []
        for _ in range(50):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.0)
            particles.append({
                "x": cx,
                "y": cy,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed * 0.5,
                "char": random.choice(motifs),
                "delay": random.uniform(0, 0.8),
                "life": random.uniform(2.0, 4.0),
            })

        # 링 확장 효과용
        ring_chars = "═══════════════════════════════"

        start = time.time()
        total_duration = 6.0  # 기존 4초 → 6초

        while time.time() - start < total_duration:
            elapsed = time.time() - start

            # Phase 1 (0~1.5s): 어둠에서 중앙 빛 출현
            # Phase 2 (1.5~3s): 링 확장 + 파티클 폭발 + 타이틀
            # Phase 3 (3~5s): 부제 + 태그라인 등장
            # Phase 4 (5~6s): 페이드아웃

            self.console.clear()

            # 배경: Act 색조 그라데이션 (점진적)
            bg_alpha = min(1.0, elapsed / 2.0)
            fade_out = max(0.0, 1.0 - max(0, elapsed - 5.0)) if elapsed > 5.0 else 1.0
            for y in range(h):
                t = y / max(1, h - 1)
                # 중앙에서 빛이 퍼지는 효과
                dist_from_center = abs(y - cy) / max(1, cy)
                center_glow = max(0, 1.0 - dist_from_center) * bg_alpha * 0.15 * fade_out
                r = int((3 + color[0] * center_glow) * fade_out)
                g = int((3 + color[1] * center_glow) * fade_out)
                b = int((8 + color[2] * center_glow) * fade_out)
                r, g, b = min(255, r), min(255, g), min(255, b)
                for x in range(w):
                    self.console.rgb[y, x] = (ord(" "), (r, g, b), (r, g, b))

            b = min(1.0, elapsed / 1.5) * fade_out

            # Phase 1: 중앙 빛점 (0~1.5s)
            if elapsed < 2.0:
                glow_size = int(elapsed * 3)
                glow_b = b * 0.3
                for dy in range(-glow_size, glow_size + 1):
                    for dx in range(-glow_size * 2, glow_size * 2 + 1):
                        gx, gy = cx + dx, cy + dy
                        if 0 <= gx < w and 0 <= gy < h:
                            dist = math.sqrt(dx * dx / 4 + dy * dy)
                            if dist < glow_size:
                                intensity = (1.0 - dist / max(1, glow_size)) * glow_b
                                gc = (min(255, int(color[0] * intensity * 0.3)),
                                      min(255, int(color[1] * intensity * 0.3)),
                                      min(255, int(color[2] * intensity * 0.3)))
                                self.console.rgb["bg"][gy, gx] = gc

            # Phase 2: 확장 링 (1.0s~)
            if elapsed > 1.0:
                ring_t = elapsed - 1.0
                ring_radius = int(ring_t * 8)
                ring_alpha = max(0, 1.0 - ring_t / 3.0) * fade_out

                if ring_alpha > 0 and ring_radius < 40:
                    # 수평 링
                    for dx in range(-ring_radius, ring_radius + 1):
                        rx = cx + dx
                        if 0 <= rx < w:
                            # 상단
                            ry_top = cy - int(ring_radius * 0.3)
                            ry_bot = cy + int(ring_radius * 0.3)
                            rc = (min(255, int(color[0] * ring_alpha * 0.4)),
                                  min(255, int(color[1] * ring_alpha * 0.4)),
                                  min(255, int(color[2] * ring_alpha * 0.4)))
                            if 0 <= ry_top < h:
                                self.console.print(rx, ry_top, "─", fg=rc)
                            if 0 <= ry_bot < h:
                                self.console.print(rx, ry_bot, "─", fg=rc)

            # 파티클 렌더링 (1.0s~)
            if elapsed > 0.8:
                for p in particles:
                    pt = elapsed - 0.8 - p["delay"]
                    if pt <= 0 or pt > p["life"]:
                        continue
                    life_ratio = pt / p["life"]
                    px = int(p["x"] + p["vx"] * pt * 8)
                    py = int(p["y"] + p["vy"] * pt * 8)
                    if 0 <= px < w and 0 <= py < h:
                        pa = (1.0 - life_ratio) * fade_out
                        pc = (min(255, int(color[0] * pa)),
                              min(255, int(color[1] * pa)),
                              min(255, int(color[2] * pa)))
                        if sum(pc) > 15:
                            self.console.print(px, py, p["char"], fg=pc)

            # 타이틀 (1.5s~)
            if elapsed > 1.2:
                title_alpha = min(1.0, (elapsed - 1.2) / 0.8) * fade_out
                # 장식선
                deco = "═" * 34
                dc = title_alpha * 0.4
                deco_c = (int(color[0] * dc), int(color[1] * dc), int(color[2] * dc))
                self.console.print(cx - 17, cy - 3, deco, fg=deco_c)

                # 코너
                cc = (int(color[0] * dc * 0.8), int(color[1] * dc * 0.8), int(color[2] * dc * 0.8))
                self.console.print(cx - 18, cy - 3, "╔", fg=cc)
                self.console.print(cx + 17, cy - 3, "╗", fg=cc)
                self.console.print(cx - 18, cy + 3, "╚", fg=cc)
                self.console.print(cx + 17, cy + 3, "╝", fg=cc)
                for dy in range(cy - 2, cy + 3):
                    if 0 <= dy < h:
                        self.console.print(cx - 18, dy, "║", fg=cc)
                        self.console.print(cx + 17, dy, "║", fg=cc)

                # 타이틀 텍스트 (큰 글씨 느낌)
                tc = (min(255, int(color[0] * title_alpha)),
                      min(255, int(color[1] * title_alpha)),
                      min(255, int(color[2] * title_alpha)))
                self.console.print((w - len(title)) // 2, cy - 1, title, fg=tc)

                # 서브타이틀
                sc = (min(255, int(255 * title_alpha * 0.9)),
                      min(255, int(255 * title_alpha * 0.9)),
                      min(255, int(255 * title_alpha * 0.8)))
                self.console.print((w - len(subtitle)) // 2, cy + 1, subtitle, fg=sc)

                self.console.print(cx - 17, cy + 3, deco, fg=deco_c)

            # 태그라인 (3s~)
            if elapsed > 3.0:
                tag_alpha = min(1.0, (elapsed - 3.0) / 1.0) * fade_out
                tc = (int(200 * tag_alpha * 0.6),
                      int(200 * tag_alpha * 0.6),
                      int(220 * tag_alpha * 0.6))
                self.console.print((w - len(tagline)) // 2, cy + 5, tagline, fg=tc)

            # 스킵 안내 (2s~)
            if elapsed > 2.0:
                skip_blink = 0.4 + 0.3 * math.sin(elapsed * 2.5)
                skip_text = "아무 키: 건너뛰기"
                self.console.print(
                    (w - len(skip_text)) // 2, h - 2,
                    skip_text,
                    fg=(int(80 * skip_blink), int(80 * skip_blink), int(100 * skip_blink)),
                )

            self.context.present(self.console)

            for action, event in poll_game_input():
                if action is not None and elapsed > 1.0:
                    return
                elif event and isinstance(event, tcod.event.Quit) and elapsed > 1.0:
                    return
            time.sleep(0.016)

    def save_progress(self) -> bool:
        """진행 저장"""
        temporary_path = None
        try:
            SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = self.progress.to_dict()
            data["version"] = "3.0.0"
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=SAVE_PATH.parent,
                prefix=f".{SAVE_PATH.name}.",
                suffix=".tmp",
                delete=False,
            ) as f:
                temporary_path = Path(f.name)
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, SAVE_PATH)
            logger.info("스토리 모드 진행 저장 완료")
            return True
        except (OSError, TypeError, ValueError) as e:
            logger.error(f"스토리 모드 저장 실패: {e}")
            return False
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def load_progress(self) -> bool:
        """진행 로드"""
        try:
            if SAVE_PATH.exists():
                with open(SAVE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.progress = StoryModeProgress.from_dict(data)
                logger.info(
                    f"스토리 모드 진행 로드: "
                    f"완료 {len(self.progress.completed_chapters)}/{len(CHAPTER_ORDER)} 챕터"
                )
            else:
                self.progress = StoryModeProgress()
            return True
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            quarantine_path = SAVE_PATH.with_name(
                f"{SAVE_PATH.name}.corrupt-{int(time.time() * 1000)}"
            )
            try:
                os.replace(SAVE_PATH, quarantine_path)
                logger.error(f"손상된 스토리 모드 진행을 격리했습니다: {quarantine_path}")
            except OSError as quarantine_error:
                logger.error(f"손상된 스토리 모드 진행 격리 실패: {quarantine_error}")
            logger.error(f"스토리 모드 로드 실패: {e}")
            return False
