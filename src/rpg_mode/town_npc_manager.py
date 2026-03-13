"""
마을 NPC 매니저

town_npcs.yaml 데이터를 로드하고 NPC 정보를 제공하는 싱글턴 매니저.
"""

import os
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.core.logger import get_logger
from src.core.paths import get_project_root

logger = get_logger("town_npc_mgr")

# 지역 ID → 마을 YAML 키 매핑
REGION_TO_TOWN_KEY = {
    "forgotten_forest": "silvana",
    "twilight_desert": "mirage",
    "abyss_cavern": "deephome",
    "storm_plateau": "skyhold",
    "eternal_glacier": "frosthaven",
    "war_lands": "belfort",
    "starlight_throne": "astra",
}

# NPC 역할별 이름 색상
NPC_ROLE_COLORS = {
    "촌장": (255, 215, 0),       # 금색
    "약초사": (100, 200, 100),    # 녹색
    "대장장이": (255, 120, 50),   # 주황
    "여관 주인": (200, 180, 100), # 따뜻한 갈색
    "음유시인": (180, 150, 255),  # 보라
    "상인": (255, 200, 100),      # 노란색
    "점술사": (200, 100, 255),    # 진보라
    "무희": (255, 150, 200),      # 분홍
    "학자": (150, 200, 255),      # 하늘색
    "광부장": (180, 140, 100),    # 갈색
    "양조사": (200, 160, 80),     # 맥주색
    "기술자": (150, 180, 200),    # 은색
    "원로": (255, 215, 0),        # 금색
    "정찰병": (100, 180, 100),    # 녹색
    "바람걷기": (200, 230, 255),  # 하늘
    "궁수": (180, 220, 150),      # 연녹
    "주술사": (180, 100, 200),    # 보라
    "현자": (200, 200, 255),      # 은하늘
    "사냥꾼": (160, 140, 100),    # 갈색
    "연금술사": (200, 150, 255),  # 연보라
    "안내인": (150, 200, 180),    # 민트
    "사령관": (255, 80, 80),      # 빨강
    "군의관": (255, 200, 200),    # 연분홍
    "노병": (180, 150, 130),      # 회갈색
    "첩보원": (120, 120, 150),    # 회색
    "별의 현자": (255, 255, 200), # 밝은 금
    "별의 대장장이": (255, 180, 100),
    "별의 수호자": (200, 220, 255),
    "예언자": (220, 200, 255),
    "방랑자": (180, 200, 180),
}


@dataclass
class NPCData:
    """개별 NPC 데이터"""
    npc_id: str
    name: str
    role: str
    personality: str = ""
    backstory: str = ""
    location: str = ""
    town_key: str = ""
    region: str = ""

    # 대화
    greeting: str = ""
    idle_lines: List[str] = field(default_factory=list)
    story_dialogues: List[Dict] = field(default_factory=list)
    quest_dialogues: List[Dict] = field(default_factory=list)

    # 상점/서비스
    shop: Optional[Dict] = None
    services: List[Dict] = field(default_factory=list)


class TownNPCManager:
    """마을 NPC 데이터 매니저 (싱글턴)"""

    def __init__(self):
        self._loaded = False
        self._npcs: Dict[str, NPCData] = {}  # npc_id → NPCData
        self._town_npcs: Dict[str, List[str]] = {}  # town_key → [npc_id, ...]
        self._raw_data: Dict = {}

    def _ensure_loaded(self):
        """필요 시 YAML 로드"""
        if self._loaded:
            return
        self._load_yaml()

    def _load_yaml(self):
        """town_npcs.yaml 로드"""
        try:
            import yaml
            yaml_path = os.path.join(
                str(get_project_root()),
                "data", "rpg_mode", "town_npcs.yaml"
            )
            if not os.path.exists(yaml_path):
                logger.warning(f"town_npcs.yaml 없음: {yaml_path}")
                self._loaded = True
                return

            with open(yaml_path, "r", encoding="utf-8") as f:
                self._raw_data = yaml.safe_load(f) or {}

            town_npcs_data = self._raw_data.get("town_npcs", {})

            for town_key, town_data in town_npcs_data.items():
                if town_key == "global_npc_relationships":
                    continue
                if not isinstance(town_data, dict):
                    continue

                town_name = town_data.get("town_name", town_key)
                region_name = town_data.get("region", "")
                npcs_list = town_data.get("npcs", [])

                npc_ids = []
                for npc_raw in npcs_list:
                    if not isinstance(npc_raw, dict):
                        continue
                    npc_id = npc_raw.get("id", "")
                    if not npc_id:
                        continue

                    # 활동/이벤트 NPC는 맵에 배치하지 않음
                    if "_act" in npc_id or "_ev" in npc_id:
                        continue

                    dialogues = npc_raw.get("dialogues", {})
                    npc = NPCData(
                        npc_id=npc_id,
                        name=npc_raw.get("name", "???"),
                        role=npc_raw.get("role", "주민"),
                        personality=npc_raw.get("personality", ""),
                        backstory=npc_raw.get("backstory", ""),
                        location=npc_raw.get("location", ""),
                        town_key=town_key,
                        region=region_name,
                        greeting=dialogues.get("greeting", ""),
                        idle_lines=dialogues.get("idle", []) or [],
                        story_dialogues=dialogues.get("story_related", []) or [],
                        quest_dialogues=dialogues.get("quest_dialogues", []) or [],
                        shop=npc_raw.get("shop"),
                        services=npc_raw.get("services", []) or [],
                    )
                    self._npcs[npc_id] = npc
                    npc_ids.append(npc_id)

                self._town_npcs[town_key] = npc_ids
                logger.debug(f"마을 '{town_key}' NPC {len(npc_ids)}명 로드")

            self._loaded = True
            logger.info(f"NPC 데이터 로드 완료: {len(self._npcs)}명, {len(self._town_npcs)}개 마을")

        except Exception as e:
            logger.error(f"NPC 데이터 로드 실패: {e}")
            self._loaded = True

    def get_npc(self, npc_id: str) -> Optional[NPCData]:
        """NPC ID로 데이터 조회"""
        self._ensure_loaded()
        return self._npcs.get(npc_id)

    def get_town_npc_ids(self, town_key: str) -> List[str]:
        """마을의 NPC ID 목록 (맵 배치용 NPC만)"""
        self._ensure_loaded()
        return self._town_npcs.get(town_key, [])

    def get_region_npc_ids(self, region_id: str) -> List[str]:
        """지역 ID로 NPC ID 목록 조회"""
        town_key = REGION_TO_TOWN_KEY.get(region_id, "")
        return self.get_town_npc_ids(town_key)

    def get_npc_dialog_lines(self, npc_id: str, current_chapter: str = "") -> List[str]:
        """NPC의 현재 대화 라인 목록 반환 (인사 + idle + 챕터별)"""
        npc = self.get_npc(npc_id)
        if not npc:
            return ["..."]

        lines = []

        # 인사말
        if npc.greeting:
            lines.append(npc.greeting)

        # 챕터 관련 대사
        if current_chapter and npc.story_dialogues:
            for sd in npc.story_dialogues:
                if sd.get("chapter") == current_chapter:
                    chapter_lines = sd.get("lines", [])
                    lines.extend(chapter_lines)
                    break

        # idle 대사에서 랜덤 1개
        if npc.idle_lines:
            lines.append(random.choice(npc.idle_lines))

        # 최소 1줄은 보장
        if not lines:
            lines.append(f"({npc.name}이(가) 고개를 끄덕인다.)")

        return lines

    def get_npc_name_color(self, npc_id: str) -> tuple:
        """NPC의 이름 색상 반환"""
        npc = self.get_npc(npc_id)
        if not npc:
            return (255, 200, 50)

        # 역할 기반 색상
        for role_keyword, color in NPC_ROLE_COLORS.items():
            if role_keyword in npc.role:
                return color

        return (255, 200, 50)  # 기본 NPC 색상

    def get_npc_display_name(self, npc_id: str) -> str:
        """NPC 표시 이름 (이름 + 역할)"""
        npc = self.get_npc(npc_id)
        if not npc:
            return "???"
        return f"{npc.name} ({npc.role})"

    def get_npc_region(self, npc_id: str) -> str:
        """NPC가 속한 지역 ID 반환 (예: forgotten_forest)"""
        npc = self.get_npc(npc_id)
        if not npc:
            return ""
        for region_id, town_key in REGION_TO_TOWN_KEY.items():
            if town_key == npc.town_key:
                return region_id
        return ""


# ── 싱글턴 ──
_instance: Optional[TownNPCManager] = None


def get_town_npc_manager() -> TownNPCManager:
    """TownNPCManager 싱글턴 반환"""
    global _instance
    if _instance is None:
        _instance = TownNPCManager()
    return _instance
