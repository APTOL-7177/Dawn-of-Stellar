"""
RPG 모드 챕터/스토리 시스템

지역 탐험 진행에 따라 메인 챕터가 해금되고, 스토리 이벤트가 트리거된다.
사이드 퀘스트, 연쇄 퀘스트도 이 시스템에서 생성/관리한다.
"""

import yaml
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pathlib import Path

from src.core.logger import get_logger
from src.core.paths import get_project_root

logger = get_logger("rpg_chapter")


@dataclass
class ChapterEvent:
    """챕터 내 스토리 이벤트"""
    title: str
    description: str


@dataclass
class ChapterInfo:
    """챕터 정보"""
    chapter_id: str
    title: str
    description: str
    region: str
    unlock_condition: Optional[str]  # 해금 조건 (보스 처치, 지역 도달 등)
    min_floor: int = 0  # 레거시 호환용
    level_req: int = 1
    objectives: List[str] = field(default_factory=list)
    events: List[ChapterEvent] = field(default_factory=list)

    @property
    def chapter_number(self) -> int:
        """챕터 번호 (1~10)"""
        try:
            return int(self.chapter_id.replace("rpg_ch", ""))
        except ValueError:
            return 0


@dataclass
class SideQuest:
    """사이드 퀘스트 정보"""
    quest_id: str
    quest_type: str  # kill, explore, fetch, escort, investigate, puzzle, craft, defend, hunt, delivery, rescue, collect, arena, cooking, alchemy, chain
    title: str
    description: str
    region: str
    level_req: int = 1
    rewards: str = ""
    objectives: List[str] = field(default_factory=list)
    prerequisite: Optional[str] = None  # 선행 퀘스트 ID
    chain_next: Optional[str] = None  # 연쇄 퀘스트 다음 ID
    collect_count: int = 0  # collect 타입 수집 개수


@dataclass
class ChainQuest:
    """연쇄 퀘스트 (여러 지역에 걸친 대형 퀘스트라인)"""
    chain_id: str
    title: str
    description: str
    quests: List[SideQuest] = field(default_factory=list)


@dataclass
class RPGProgress:
    """RPG 모드 진행 상태"""
    unlocked_regions: Set[str] = field(default_factory=lambda: {"forgotten_forest"})
    defeated_bosses: Set[str] = field(default_factory=set)
    completed_chapters: Set[str] = field(default_factory=set)
    completed_quests: Set[str] = field(default_factory=set)
    active_quests: Set[str] = field(default_factory=set)
    current_chapter: int = 0
    current_region: str = "forgotten_forest"
    play_time: float = 0.0
    battles_won: int = 0
    lily_affinity: int = 0
    lily_conversations_seen: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unlocked_regions": list(self.unlocked_regions),
            "defeated_bosses": list(self.defeated_bosses),
            "completed_chapters": list(self.completed_chapters),
            "completed_quests": list(self.completed_quests),
            "active_quests": list(self.active_quests),
            "current_chapter": self.current_chapter,
            "current_region": self.current_region,
            "play_time": self.play_time,
            "battles_won": self.battles_won,
            "lily_affinity": self.lily_affinity,
            "lily_conversations_seen": list(self.lily_conversations_seen),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RPGProgress":
        return RPGProgress(
            unlocked_regions=set(data.get("unlocked_regions", ["forgotten_forest"])),
            defeated_bosses=set(data.get("defeated_bosses", [])),
            completed_chapters=set(data.get("completed_chapters", [])),
            completed_quests=set(data.get("completed_quests", [])),
            active_quests=set(data.get("active_quests", [])),
            current_chapter=data.get("current_chapter", 0),
            current_region=data.get("current_region", "forgotten_forest"),
            play_time=data.get("play_time", 0.0),
            battles_won=data.get("battles_won", 0),
            lily_affinity=data.get("lily_affinity", 0),
            lily_conversations_seen=set(data.get("lily_conversations_seen", [])),
        )


class RPGChapterSystem:
    """RPG 챕터/스토리 관리"""

    def __init__(self):
        self.chapters: List[ChapterInfo] = []
        self.side_quests: Dict[str, List[SideQuest]] = {}  # region_id → quests
        self.chain_quests: List[ChainQuest] = []
        self._load_config()

    def _load_config(self):
        """rpg_config.yaml에서 챕터/퀘스트 데이터 로드"""
        config_path = get_project_root() / "data" / "rpg_mode" / "rpg_config.yaml"
        if not config_path.exists():
            logger.warning(f"RPG 설정 파일 없음: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # 챕터 로드
            for ch_data in data.get("chapters", []):
                events = []
                for ev in ch_data.get("events", []):
                    events.append(ChapterEvent(
                        title=ev.get("title", ""),
                        description=ev.get("description", ""),
                    ))
                self.chapters.append(ChapterInfo(
                    chapter_id=ch_data["id"],
                    title=ch_data["title"],
                    description=ch_data["description"],
                    region=ch_data.get("region", ""),
                    unlock_condition=ch_data.get("unlock_condition"),
                    min_floor=ch_data.get("min_floor", 0),
                    level_req=ch_data.get("level_req", 1),
                    objectives=ch_data.get("objectives", []),
                    events=events,
                ))

            # 사이드 퀘스트 로드
            for region_id, quests in data.get("side_quests", {}).items():
                self.side_quests[region_id] = []
                for q in quests:
                    self.side_quests[region_id].append(self._parse_quest(q, region_id))

            # 연쇄 퀘스트 로드
            for chain_data in data.get("chain_quests", []):
                chain = ChainQuest(
                    chain_id=chain_data.get("chain_id", ""),
                    title=chain_data.get("title", ""),
                    description=chain_data.get("description", ""),
                )
                for q in chain_data.get("quests", []):
                    region = q.get("region", "")
                    quest = self._parse_quest(q, region)
                    chain.quests.append(quest)
                    # 연쇄 퀘스트도 해당 지역 사이드 퀘스트에 추가
                    if region not in self.side_quests:
                        self.side_quests[region] = []
                    self.side_quests[region].append(quest)
                self.chain_quests.append(chain)

            total_side = sum(len(v) for v in self.side_quests.values())
            logger.info(f"RPG 설정 로드: {len(self.chapters)}개 챕터, "
                        f"{total_side}개 사이드 퀘스트, "
                        f"{len(self.chain_quests)}개 연쇄 퀘스트")

        except Exception as e:
            logger.error(f"RPG 설정 로드 실패: {e}")

    def _parse_quest(self, q: Dict[str, Any], region_id: str) -> SideQuest:
        """퀘스트 데이터 딕셔너리를 SideQuest로 변환"""
        return SideQuest(
            quest_id=q["id"],
            quest_type=q["type"],
            title=q["title"],
            description=q["description"],
            region=region_id,
            level_req=q.get("level_req", 1),
            rewards=q.get("rewards", ""),
            objectives=q.get("objectives", []),
            prerequisite=q.get("prerequisite"),
            chain_next=q.get("chain_next"),
            collect_count=q.get("collect_count", 0),
        )

    def check_chapter_triggers(self, progress: RPGProgress) -> List[ChapterInfo]:
        """
        현재 진행도에서 새로 해금된 챕터를 확인한다.

        Returns:
            새로 해금된 챕터 리스트
        """
        newly_unlocked = []
        for chapter in self.chapters:
            if chapter.chapter_id in progress.completed_chapters:
                continue

            if self._is_chapter_unlocked(chapter, progress):
                newly_unlocked.append(chapter)

        return newly_unlocked

    def _is_chapter_unlocked(self, chapter: ChapterInfo, progress: RPGProgress) -> bool:
        """챕터 해금 조건 확인"""
        cond = chapter.unlock_condition
        if cond is None:
            # 조건 없음 = 자동 해금
            return True

        # 지역_floor_N 형태: 해당 지역 해금 + 전투 승리 N회 이상 필요
        if "_floor_" in cond:
            parts = cond.rsplit("_floor_", 1)
            region_id = parts[0]
            if region_id not in progress.unlocked_regions:
                return False
            # floor 숫자만큼 전투 승리가 필요
            try:
                required_battles = int(parts[1])
            except (ValueError, IndexError):
                required_battles = 1
            if progress.battles_won < required_battles:
                return False
            # 이전 챕터가 완료되어야 순차 진행 가능
            prev_chapter_num = chapter.chapter_number - 1
            if prev_chapter_num > 0:
                return progress.current_chapter >= prev_chapter_num
            return True

        # 보스 처치 조건
        if cond.endswith("_boss_defeated"):
            region_id = cond.replace("_boss_defeated", "")
            return region_id in progress.defeated_bosses

        return False

    def get_quests_for_region(self, region_id: str, progress: RPGProgress) -> List[SideQuest]:
        """
        지역의 수행 가능한 사이드 퀘스트 목록.
        선행 퀘스트가 있으면 그것이 완료되어야 표시된다.

        Returns:
            수행 가능한 퀘스트 리스트
        """
        all_quests = self.side_quests.get(region_id, [])
        available = []
        for q in all_quests:
            if q.quest_id in progress.completed_quests:
                continue
            if q.quest_id in progress.active_quests:
                continue
            # 선행 퀘스트 확인
            if q.prerequisite and q.prerequisite not in progress.completed_quests:
                continue
            available.append(q)
        return available

    def get_active_quests(self, progress: RPGProgress) -> List[SideQuest]:
        """현재 진행 중인 퀘스트 목록"""
        active = []
        for region_quests in self.side_quests.values():
            for q in region_quests:
                if q.quest_id in progress.active_quests:
                    active.append(q)
        return active

    def get_quest_by_id(self, quest_id: str) -> Optional[SideQuest]:
        """퀘스트 ID로 퀘스트 검색"""
        for region_quests in self.side_quests.values():
            for q in region_quests:
                if q.quest_id == quest_id:
                    return q
        return None

    def accept_quest(self, quest_id: str, progress: RPGProgress) -> bool:
        """퀘스트 수락"""
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            return False
        if quest.quest_id in progress.completed_quests:
            return False
        if quest.prerequisite and quest.prerequisite not in progress.completed_quests:
            return False
        progress.active_quests.add(quest_id)
        logger.info(f"퀘스트 수락: {quest.title}")
        return True

    def complete_quest(self, quest_id: str, progress: RPGProgress) -> Optional[SideQuest]:
        """퀘스트 완료. 연쇄 퀘스트면 다음 퀘스트 반환."""
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            return None
        progress.active_quests.discard(quest_id)
        progress.completed_quests.add(quest_id)
        logger.info(f"퀘스트 완료: {quest.title}")
        # 연쇄 퀘스트 다음 단계 반환
        if quest.chain_next:
            return self.get_quest_by_id(quest.chain_next)
        return None

    def get_chain_quest_progress(self, chain_id: str, progress: RPGProgress) -> Dict[str, Any]:
        """연쇄 퀘스트 진행 상황"""
        for chain in self.chain_quests:
            if chain.chain_id == chain_id:
                total = len(chain.quests)
                completed = sum(1 for q in chain.quests
                                if q.quest_id in progress.completed_quests)
                current = None
                for q in chain.quests:
                    if q.quest_id in progress.active_quests:
                        current = q
                        break
                    if q.quest_id not in progress.completed_quests:
                        current = q
                        break
                return {
                    "chain_id": chain_id,
                    "title": chain.title,
                    "total": total,
                    "completed": completed,
                    "current_quest": current,
                }
        return {}

    def on_boss_defeated(self, region_id: str, progress: RPGProgress):
        """
        보스 처치 시 호출. 다음 지역 해금 및 챕터 체크.
        """
        progress.defeated_bosses.add(region_id)

        # 다음 지역 해금
        from src.rpg_mode.rpg_world_config import REGION_MAP
        region = REGION_MAP.get(region_id)
        if region and region.next_region_id:
            progress.unlocked_regions.add(region.next_region_id)
            logger.info(f"새 지역 해금: {region.next_region_id}")

        # 챕터 트리거 체크
        new_chapters = self.check_chapter_triggers(progress)
        for ch in new_chapters:
            progress.current_chapter = max(progress.current_chapter, ch.chapter_number)
            logger.info(f"새 챕터 해금: {ch.title}")

    def get_chapter_title(self, chapter_number: int) -> str:
        """챕터 번호로 제목 반환"""
        for ch in self.chapters:
            if ch.chapter_number == chapter_number:
                return ch.title
        return f"챕터 {chapter_number}"

    def get_chapter_info(self, chapter_number: int) -> Optional[ChapterInfo]:
        """챕터 번호로 전체 정보 반환"""
        for ch in self.chapters:
            if ch.chapter_number == chapter_number:
                return ch
        return None

    def get_total_quest_count(self) -> int:
        """전체 사이드 퀘스트 수"""
        return sum(len(v) for v in self.side_quests.values())

    def get_completion_stats(self, progress: RPGProgress) -> Dict[str, Any]:
        """완료율 통계"""
        total_quests = self.get_total_quest_count()
        completed_quests = len(progress.completed_quests)
        total_chapters = len(self.chapters)
        completed_chapters = len(progress.completed_chapters)
        return {
            "total_quests": total_quests,
            "completed_quests": completed_quests,
            "quest_completion": completed_quests / max(1, total_quests) * 100,
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "chapter_completion": completed_chapters / max(1, total_chapters) * 100,
            "total_bosses": 7,
            "defeated_bosses": len(progress.defeated_bosses),
            "play_time_hours": progress.play_time / 3600,
        }
