"""
RPG 모드 월드 설정

7개 대륙(지역), 오픈월드 대맵 구조
각 지역은 하나의 매우 큰 맵 + 서브 던전으로 구성
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# ── 하나의 심리스 월드맵 크기 (원신 스타일) ──
# 모든 7개 지역이 이 하나의 맵 안에 자연스럽게 배치된다.
RPG_WORLD_WIDTH = 3000
RPG_WORLD_HEIGHT = 3000


@dataclass
class SubDungeon:
    """지역 내 서브 던전 (보스방, 히든 던전 등)"""
    dungeon_id: str
    name: str
    description: str
    width: int = 60
    height: int = 40
    rooms: int = 8
    enemy_level_bonus: int = 0  # 지역 기본 레벨 대비 보너스
    is_boss_dungeon: bool = False
    is_hidden: bool = False
    required_chapter: Optional[str] = None  # 해금에 필요한 챕터


@dataclass
class RegionConfig:
    """지역 설정 - 오픈월드"""
    region_id: str
    name: str
    description: str
    level_min: int
    level_max: int
    biome: str  # 바이옴 타입 (기존 biome_0~9 매핑)

    # 보스 정보
    boss_name: str = ""
    boss_level: int = 0

    # 서브 던전
    sub_dungeons: List[SubDungeon] = field(default_factory=list)

    # 해금되는 챕터
    chapter_ids: List[str] = field(default_factory=list)

    # 다음 지역 해금 조건 (이 지역 보스 처치)
    next_region_id: Optional[str] = None

    # NPC 수
    npc_count: int = 5
    quest_giver_count: int = 3

    # 마을 이름
    town_name: str = ""


# 7개 대륙 정의 - 오픈월드
REGIONS: List[RegionConfig] = [
    RegionConfig(
        region_id="forgotten_forest",
        name="잊혀진 숲",
        description="고대의 나무들이 우거진 신비로운 숲. 잔향 차원에 도착한 크리스가 처음 발을 딛는 곳.",
        level_min=1, level_max=12,
        biome="biome_0",
        boss_name="숲의 수호자 엔트리아", boss_level=12,
        npc_count=6, quest_giver_count=3,
        town_name="숲의 마을 실바나",
        next_region_id="twilight_desert",
        chapter_ids=["rpg_ch1", "rpg_ch2"],
        sub_dungeons=[
            SubDungeon("ff_boss", "엔트리아의 정원", "숲 깊은 곳의 수호자가 잠든 곳",
                       width=50, height=35, rooms=6, is_boss_dungeon=True),
            SubDungeon("ff_hidden", "뿌리의 미궁", "고대 나무 뿌리 아래 숨겨진 던전",
                       width=45, height=30, rooms=5, enemy_level_bonus=9, is_hidden=True),
        ],
    ),
    RegionConfig(
        region_id="twilight_desert",
        name="황혼의 사막",
        description="끝없이 펼쳐진 황금빛 사막. 고대 문명의 유적이 모래 아래 잠들어 있다.",
        level_min=10, level_max=22,
        biome="biome_1",
        boss_name="사막의 군주 스콜피온", boss_level=22,
        npc_count=5, quest_giver_count=3,
        town_name="오아시스 마을 미라지",
        next_region_id="abyss_cavern",
        chapter_ids=["rpg_ch3"],
        sub_dungeons=[
            SubDungeon("td_ruins", "고대 유적 지하", "모래 아래 잠든 고대 문명의 유적",
                       width=55, height=35, rooms=7),
            SubDungeon("td_boss", "전갈왕의 둥지", "사막 깊은 곳의 거대 전갈 소굴",
                       width=50, height=35, rooms=6, is_boss_dungeon=True),
            SubDungeon("td_hidden", "신기루의 오아시스", "사막 한가운데 숨겨진 비밀 오아시스",
                       width=40, height=30, rooms=5, enemy_level_bonus=4, is_hidden=True),
        ],
    ),
    RegionConfig(
        region_id="abyss_cavern",
        name="심연의 동굴",
        description="땅 깊은 곳으로 이어지는 거대한 지하 세계. 어둠 속에서 무언가의 목소리가 들린다.",
        level_min=20, level_max=32,
        biome="biome_2",
        boss_name="심연의 눈 아비소스", boss_level=32,
        npc_count=4, quest_giver_count=3,
        town_name="동굴 마을 딥홈",
        next_region_id="storm_plateau",
        chapter_ids=["rpg_ch4"],
        sub_dungeons=[
            SubDungeon("ac_deep", "심연 최하층", "동굴 깊은 곳의 미탐사 구역",
                       width=55, height=40, rooms=8),
            SubDungeon("ac_boss", "아비소스의 시선", "심연의 눈이 지켜보는 곳",
                       width=50, height=35, rooms=6, is_boss_dungeon=True),
            SubDungeon("ac_hidden1", "수정 동굴", "빛나는 수정으로 가득한 히든 던전",
                       width=45, height=30, rooms=5, enemy_level_bonus=5, is_hidden=True),
            SubDungeon("ac_hidden2", "고대 연구실", "잊혀진 연구 시설",
                       width=40, height=25, rooms=4, enemy_level_bonus=4, is_hidden=True),
        ],
    ),
    RegionConfig(
        region_id="storm_plateau",
        name="폭풍의 고원",
        description="하늘과 맞닿은 높은 고원. 끊임없는 번개와 폭풍이 몰아치는 위험한 땅.",
        level_min=30, level_max=42,
        biome="biome_4",
        boss_name="뇌신 볼타르크", boss_level=42,
        npc_count=4, quest_giver_count=3,
        town_name="고원 마을 스카이홀드",
        next_region_id="eternal_glacier",
        chapter_ids=["rpg_ch5"],
        sub_dungeons=[
            SubDungeon("sp_peak", "뇌운봉", "번개가 쏟아지는 고원의 정상",
                       width=50, height=35, rooms=6),
            SubDungeon("sp_boss", "볼타르크의 제단", "뇌신이 깃든 고대 제단",
                       width=50, height=35, rooms=6, is_boss_dungeon=True),
            SubDungeon("sp_hidden", "구름 위의 섬", "폭풍 너머 숨겨진 떠다니는 섬",
                       width=45, height=30, rooms=5, enemy_level_bonus=5, is_hidden=True),
        ],
    ),
    RegionConfig(
        region_id="eternal_glacier",
        name="영원의 빙원",
        description="시간이 멈춘 듯한 얼어붙은 세계. 타임라인의 잔해가 얼음 속에 갇혀 있다.",
        level_min=40, level_max=52,
        biome="biome_5",
        boss_name="빙결의 여왕 글라시아", boss_level=52,
        npc_count=4, quest_giver_count=4,
        town_name="빙원 마을 프로스트헤이븐",
        next_region_id="war_lands",
        chapter_ids=["rpg_ch6"],
        sub_dungeons=[
            SubDungeon("eg_frozen", "얼어붙은 신전", "시간이 멈춘 고대 신전",
                       width=55, height=40, rooms=7),
            SubDungeon("eg_boss", "글라시아의 옥좌", "빙원의 여왕이 잠든 곳",
                       width=50, height=35, rooms=6, is_boss_dungeon=True),
            SubDungeon("eg_hidden1", "시간의 균열", "타임라인 잔해가 모인 차원의 틈",
                       width=45, height=30, rooms=5, enemy_level_bonus=5, is_hidden=True),
            SubDungeon("eg_hidden2", "기억의 호수", "얼어붙은 기억이 잠든 지하 호수",
                       width=40, height=25, rooms=4, enemy_level_bonus=4, is_hidden=True),
        ],
    ),
    RegionConfig(
        region_id="war_lands",
        name="전쟁의 대지",
        description="차원 전쟁의 흔적이 남은 황폐한 대지. 카인의 실험 잔해가 곳곳에 널려 있다.",
        level_min=50, level_max=65,
        biome="biome_7",
        boss_name="전쟁 인형 벨리거", boss_level=65,
        npc_count=5, quest_giver_count=4,
        town_name="전장 기지 벨포트",
        next_region_id="starlight_throne",
        chapter_ids=["rpg_ch7", "rpg_ch8"],
        sub_dungeons=[
            SubDungeon("wl_lab", "카인의 연구실", "카인이 사용했던 차원 연구 시설",
                       width=55, height=40, rooms=7),
            SubDungeon("wl_rift", "차원의 균열", "차원이 찢어진 전쟁터",
                       width=50, height=35, rooms=6),
            SubDungeon("wl_boss", "벨리거의 격납고", "최강의 전쟁 병기가 대기하는 곳",
                       width=55, height=40, rooms=7, is_boss_dungeon=True),
            SubDungeon("wl_hidden1", "잊혀진 전장", "과거 차원 전쟁의 기록이 남은 곳",
                       width=45, height=30, rooms=5, enemy_level_bonus=5, is_hidden=True),
            SubDungeon("wl_hidden2", "병기 공장", "아직 가동 중인 고대 병기 공장",
                       width=50, height=35, rooms=6, enemy_level_bonus=6, is_hidden=True),
        ],
    ),
    RegionConfig(
        region_id="starlight_throne",
        name="별빛의 왕좌",
        description="잔향 차원의 중심. 세피로스와 카인의 잔향이 왕좌를 차지하기 위해 다투는 최종 지역.",
        level_min=60, level_max=80,
        biome="biome_9",
        boss_name="잔향의 카인", boss_level=80,
        npc_count=5, quest_giver_count=5,
        town_name="별빛 마을 아스트라",
        next_region_id=None,  # 최종 지역
        chapter_ids=["rpg_ch9", "rpg_ch10"],
        sub_dungeons=[
            SubDungeon("st_memory", "세피로스의 기억", "세피로스의 잔향이 남긴 기억의 공간",
                       width=55, height=40, rooms=7),
            SubDungeon("st_throne", "시간의 왕좌", "카인이 재건하려는 왕좌의 방",
                       width=60, height=40, rooms=8),
            SubDungeon("st_boss", "잔향의 최심부", "최종 결전의 장소",
                       width=60, height=45, rooms=8, is_boss_dungeon=True),
            SubDungeon("st_hidden1", "별빛 결정 동굴", "차원 안정화의 열쇠가 잠든 곳",
                       width=50, height=35, rooms=6, enemy_level_bonus=8, is_hidden=True),
            SubDungeon("st_hidden2", "타임라인의 끝", "10만 번의 반복이 끝나는 곳",
                       width=55, height=40, rooms=7, enemy_level_bonus=10, is_hidden=True),
        ],
    ),
]

# region_id → RegionConfig 인덱스
REGION_MAP: Dict[str, RegionConfig] = {r.region_id: r for r in REGIONS}


def get_enemy_level_for_region(region: RegionConfig, progress: float = 0.5) -> int:
    """
    지역 내 탐험 진행도에 따른 적 레벨 계산.
    progress: 0.0(입구) ~ 1.0(최심부)
    """
    level = region.level_min + int(progress * (region.level_max - region.level_min))
    return max(1, level)


def get_region_order() -> List[str]:
    """지역 해금 순서 반환"""
    return [r.region_id for r in REGIONS]


def get_next_region(current_region_id: str) -> Optional[RegionConfig]:
    """현재 지역의 다음 지역을 반환"""
    region = REGION_MAP.get(current_region_id)
    if region and region.next_region_id:
        return REGION_MAP.get(region.next_region_id)
    return None
