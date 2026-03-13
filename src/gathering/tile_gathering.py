"""
타일 기반 채집 시스템 (RPG 오픈월드용)

자연 지형 타일(꽃, 버섯, 바위 등)을 직접 채집하여 재료를 획득.
지역(region) + 타일타입 조합으로 루트 테이블이 결정된다.

모든 자연 타일이 채집 가능한 것은 아니다.
좌표 기반 해시로 약 15%의 타일만 "풍성한(rich)" 상태로 채집 가능하며,
이는 결정적(deterministic)이라 매번 같은 위치가 채집 가능하다.
"""

import random
from typing import Dict, List, Tuple, Set

from src.world.tile import TileType, Tile
from src.core.logger import get_logger

logger = get_logger("tile_gathering")

# ── 채집 가능 타일 희소성 설정 ──
# 좌표 해시 기반으로 이 비율만큼만 채집 가능 (0.0 ~ 1.0)
HARVEST_DENSITY = 0.05  # 5%의 자연 타일만 채집 가능
_HARVEST_HASH_SEED = 48271  # 결정적 해시용 시드


def _is_rich_tile(x: int, y: int) -> bool:
    """
    좌표 기반 결정적 해시로 이 타일이 '풍성한' 채집 포인트인지 판별.
    전체 자연 타일의 약 15%만 True를 반환한다.
    """
    # 간단한 해시 함수 (결정적, 분포 균일)
    h = ((x * 7919) ^ (y * 104729) ^ _HARVEST_HASH_SEED) & 0xFFFFFFFF
    h = ((h * 2654435761) >> 16) & 0xFFFF
    return (h % 1000) < int(HARVEST_DENSITY * 1000)


# ── 채집 가능한 타일 타입 집합 ──

HARVESTABLE_TILE_TYPES: Set[TileType] = {
    TileType.FLOWER,
    TileType.MUSHROOM,
    TileType.ROCK,
    TileType.TALL_GRASS,
    TileType.SHALLOW_WATER,
    TileType.CACTUS,
    TileType.DEAD_TREE,
    TileType.RUINS,
    TileType.STAR_MOSS,
    TileType.CRYSTAL_GRASS,
    TileType.DEEP_FOREST,
}

# 문자열 값 집합 (세이브/로드 시 비교용)
HARVESTABLE_TILE_TYPE_VALUES: Set[str] = {t.value for t in HARVESTABLE_TILE_TYPES}


# ── 타일타입별 기본 루트 테이블 ──
# 형식: (ingredient_id, min_qty, max_qty, drop_rate)

_BASE_LOOT: Dict[TileType, List[Tuple[str, int, int, float]]] = {
    TileType.FLOWER: [
        ("flower_petal", 1, 2, 0.8),
        ("magic_herb", 0, 1, 0.3),
        ("mana_blossom", 0, 1, 0.15),
        ("honey", 0, 1, 0.2),
    ],
    TileType.MUSHROOM: [
        ("red_mushroom", 1, 2, 0.7),
        ("blue_mushroom", 0, 1, 0.4),
        ("ginger", 0, 1, 0.3),
        ("truffle", 0, 1, 0.1),
    ],
    TileType.ROCK: [
        ("stone", 1, 2, 0.7),
        ("iron_ore", 0, 1, 0.3),
        ("salt", 0, 1, 0.25),
        ("gunpowder", 0, 1, 0.15),
        ("bomb_casing", 0, 1, 0.1),
        ("sulfur", 0, 1, 0.1),
        ("crystal_shard", 0, 1, 0.1),
    ],
    TileType.TALL_GRASS: [
        ("carrot", 0, 2, 0.5),
        ("potato", 0, 2, 0.5),
        ("onion", 0, 1, 0.4),
        ("tea_leaf", 0, 1, 0.2),
        ("spice", 0, 1, 0.15),
        ("rice", 0, 1, 0.2),
    ],
    TileType.SHALLOW_WATER: [
        ("fish", 1, 2, 0.6),
        ("shellfish", 0, 2, 0.4),
        ("water", 1, 3, 0.8),
        ("pure_water", 0, 1, 0.2),
        ("glass_vial", 0, 1, 0.15),
        ("fuse", 0, 1, 0.1),
    ],
    TileType.CACTUS: [
        ("desert_cactus", 1, 1, 0.7),
        ("water", 0, 2, 0.5),
        ("spice", 0, 1, 0.3),
    ],
    TileType.DEAD_TREE: [
        ("wood", 1, 2, 0.7),
        ("stick", 0, 2, 0.5),
        ("metal_scrap", 0, 1, 0.2),
    ],
    TileType.RUINS: [
        ("metal_scrap", 0, 2, 0.5),
        ("iron_ore", 0, 1, 0.3),
        ("obsidian", 0, 1, 0.15),
        ("bomb_casing", 0, 1, 0.15),
    ],
    TileType.STAR_MOSS: [
        ("mana_blossom", 0, 1, 0.4),
        ("magic_herb", 0, 1, 0.5),
        ("mandrake", 0, 1, 0.1),
    ],
    TileType.CRYSTAL_GRASS: [
        ("crystal_shard", 0, 1, 0.5),
        ("mana_blossom", 0, 1, 0.3),
        ("glass_vial", 0, 1, 0.2),
    ],
    TileType.DEEP_FOREST: [
        ("wood", 1, 2, 0.6),
        ("berry", 0, 2, 0.5),
        ("apple", 0, 1, 0.3),
        ("egg", 0, 1, 0.2),
        ("ginger", 0, 1, 0.25),
    ],
}


# ── 지역별 보너스 드롭 (기본 테이블에 추가) ──

_REGION_BONUS_LOOT: Dict[str, List[Tuple[str, int, int, float]]] = {
    "forgotten_forest": [
        ("mandrake", 0, 1, 0.05),
        ("golden_apple", 0, 1, 0.03),
    ],
    "twilight_desert": [
        ("sand_truffle", 0, 1, 0.05),
        ("fire_essence", 0, 1, 0.03),
    ],
    "abyss_cavern": [
        ("slime_jelly", 0, 1, 0.1),
        ("obsidian", 0, 1, 0.05),
    ],
    "storm_plateau": [
        ("lightning_essence", 0, 1, 0.03),
    ],
    "eternal_glacier": [
        ("ice_essence", 0, 1, 0.05),
        ("ice", 0, 2, 0.15),
    ],
    "war_lands": [
        ("gunpowder", 0, 1, 0.1),
        ("metal_scrap", 0, 1, 0.1),
    ],
    "starlight_throne": [
        ("mithril_ore", 0, 1, 0.03),
        ("crystal_shard", 0, 1, 0.1),
    ],
}


# ── 타일 타입별 한국어 이름 ──

_TILE_HARVEST_NAMES: Dict[TileType, str] = {
    TileType.FLOWER: "꽃",
    TileType.MUSHROOM: "버섯",
    TileType.ROCK: "바위",
    TileType.TALL_GRASS: "키 큰 풀",
    TileType.SHALLOW_WATER: "얕은 물가",
    TileType.CACTUS: "선인장",
    TileType.DEAD_TREE: "마른 나무",
    TileType.RUINS: "폐허",
    TileType.STAR_MOSS: "별이끼",
    TileType.CRYSTAL_GRASS: "수정 풀밭",
    TileType.DEEP_FOREST: "울창한 숲",
}


def is_harvestable_tile(tile_type: TileType) -> bool:
    """채집 가능한 타일 타입인지 확인 (타입만 체크, 좌표 희소성 미포함)"""
    return tile_type in HARVESTABLE_TILE_TYPES


def can_harvest_tile_at(x: int, y: int, tile_type: TileType) -> bool:
    """
    해당 좌표의 타일이 채집 가능한지 확인 (타입 + 좌표 희소성 체크)

    모든 자연 타일이 채집 가능한 것은 아니며,
    좌표 해시 기반으로 약 15%만 '풍성한' 채집 포인트로 판정된다.
    """
    if tile_type not in HARVESTABLE_TILE_TYPES:
        return False
    return _is_rich_tile(x, y)


def get_tile_harvest_name(tile_type: TileType) -> str:
    """타일 타입의 한국어 채집 이름 반환"""
    return _TILE_HARVEST_NAMES.get(tile_type, "채집물")


def harvest_tile(tile: Tile, region_id: str) -> Dict[str, int]:
    """
    타일 채집 실행

    Args:
        tile: 채집할 타일
        region_id: 현재 지역 ID (예: "forgotten_forest")

    Returns:
        획득한 재료 딕셔너리 {ingredient_id: quantity}
    """
    if tile.harvested:
        return {}

    if not can_harvest_tile_at(tile.x, tile.y, tile.tile_type):
        return {}

    # 타일을 채집됨 상태로 변경
    tile.mark_harvested()

    # 기본 루트 테이블
    loot_entries = list(_BASE_LOOT.get(tile.tile_type, []))

    # 지역 보너스 루트 추가
    region_bonus = _REGION_BONUS_LOOT.get(region_id, [])
    loot_entries.extend(region_bonus)

    # 드롭 롤링
    results: Dict[str, int] = {}

    for ingredient_id, min_qty, max_qty, drop_rate in loot_entries:
        if random.random() < drop_rate:
            qty = random.randint(min_qty, max_qty) if max_qty > 0 else 0
            if qty > 0:
                results[ingredient_id] = results.get(ingredient_id, 0) + qty

    logger.info(
        f"타일 채집: ({tile.x}, {tile.y}) {tile.tile_type.value} "
        f"지역={region_id} 결과={results}"
    )

    return results
