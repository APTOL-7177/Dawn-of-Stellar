"""
RPG 오픈월드 맵 생성기 (청크 기반 레이지 로딩)

3000x3000 맵을 한번에 생성하지 않고:
1) 피처 좌표만 사전 계산 (마을, 도로, 강, 산맥 등) → ~10만개 좌표, ~수 MB
2) 지형은 노이즈 함수로 실시간 결정적 생성
3) 플레이어 주변 64x64 청크만 메모리에 로드 (LazyTileMap)
"""

import math
import random
from typing import List, Tuple, Dict, Optional, Set

from src.world.tile import TileType, Tile
from src.rpg_mode.rpg_world_config import REGIONS, RegionConfig, RPG_WORLD_WIDTH, RPG_WORLD_HEIGHT
from src.rpg_mode.lazy_tile_map import LazyTileMap, RPGDungeonMap
from src.core.logger import get_logger

logger = get_logger("rpg_world_gen")


# ── 지역별 주 지형 타일 ──

_REGION_TERRAIN = {
    "forgotten_forest": {
        "primary": TileType.DEEP_FOREST,
        "secondary": TileType.GRASS,
        "accent": TileType.TALL_GRASS,
        "scatter": TileType.FLOWER,
        "dry": TileType.ROCK,
        "obstacle": TileType.WALL,
    },
    "twilight_desert": {
        "primary": TileType.SAND,
        "secondary": TileType.GRASS,       # 오아시스 풀밭
        "accent": TileType.CACTUS,
        "scatter": TileType.ROCK,
        "dry": TileType.SAND,
        "obstacle": TileType.MOUNTAIN,
    },
    "abyss_cavern": {
        "primary": TileType.SWAMP,
        "secondary": TileType.DEEP_FOREST,
        "accent": TileType.SHALLOW_WATER,
        "scatter": TileType.MUSHROOM,
        "dry": TileType.FLOOR,
        "obstacle": TileType.WALL,
    },
    "storm_plateau": {
        "primary": TileType.GRASS,
        "secondary": TileType.TALL_GRASS,
        "accent": TileType.FLOWER,
        "scatter": TileType.ROCK,
        "dry": TileType.SAND,
        "obstacle": TileType.MOUNTAIN,
    },
    "eternal_glacier": {
        "primary": TileType.SNOW,
        "secondary": TileType.ICE_FLOOR,
        "accent": TileType.SHALLOW_WATER,   # 빙하 녹은 물
        "scatter": TileType.ROCK,
        "dry": TileType.SNOW,
        "obstacle": TileType.MOUNTAIN,
    },
    "war_lands": {
        "primary": TileType.SCORCHED_EARTH,
        "secondary": TileType.SAND,
        "accent": TileType.LAVA,
        "scatter": TileType.RUINS,
        "dry": TileType.DEAD_TREE,
        "obstacle": TileType.WALL,
    },
    "starlight_throne": {
        "primary": TileType.CRYSTAL_GRASS,
        "secondary": TileType.GRASS,
        "accent": TileType.CRYSTAL,
        "scatter": TileType.STAR_MOSS,
        "dry": TileType.SNOW,
        "obstacle": TileType.MOUNTAIN,
    },
}


# ── 노이즈 함수 ──

def _value_noise_2d(x: float, y: float, seed: int = 0) -> float:
    """간단한 값 노이즈 (0.0~1.0)"""
    n = int(x * 73 + y * 179 + seed * 337) & 0x7FFFFFFF
    n = (n >> 13) ^ n
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0x7FFFFFFF
    return n / 2147483647.0


def _smoothed_noise(x: float, y: float, scale: float, octaves: int = 4, seed: int = 0) -> float:
    """다중 옥타브 값 노이즈로 부드러운 지형 생성"""
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0

    for _ in range(octaves):
        ix = int(x * frequency / scale)
        iy = int(y * frequency / scale)
        fx = (x * frequency / scale) - ix
        fy = (y * frequency / scale) - iy

        v00 = _value_noise_2d(ix, iy, seed)
        v10 = _value_noise_2d(ix + 1, iy, seed)
        v01 = _value_noise_2d(ix, iy + 1, seed)
        v11 = _value_noise_2d(ix + 1, iy + 1, seed)

        fx = (1 - math.cos(fx * math.pi)) * 0.5
        fy = (1 - math.cos(fy * math.pi)) * 0.5

        top = v00 * (1 - fx) + v10 * fx
        bottom = v01 * (1 - fx) + v11 * fx
        v = top * (1 - fy) + bottom * fy

        value += v * amplitude
        max_amp += amplitude
        amplitude *= 0.5
        frequency *= 2.0
        seed += 1000

    return value / max_amp


# ── 지역 배치 (보로노이 분할) ──

_REGION_CENTERS = {
    "forgotten_forest": (0.15, 0.25),
    "storm_plateau":    (0.45, 0.18),
    "eternal_glacier":  (0.78, 0.15),
    "twilight_desert":  (0.18, 0.55),
    "abyss_cavern":     (0.45, 0.50),
    "war_lands":        (0.75, 0.50),
    "starlight_throne": (0.50, 0.80),
}


def _get_region_for_point(x: int, y: int, width: int, height: int) -> str:
    """좌표가 어느 지역에 속하는지 결정 (보로노이 분할)"""
    nx = x / width
    ny = y / height
    min_dist = float("inf")
    closest = "forgotten_forest"
    for region_id, (cx, cy) in _REGION_CENTERS.items():
        dist = (nx - cx) ** 2 + (ny - cy) ** 2
        if dist < min_dist:
            min_dist = dist
            closest = region_id
    return closest


# ── 지형 타입 결정 (순수 함수 - 타일 객체 없이) ──

def _compute_terrain_type(x: int, y: int, w: int, h: int, seed: int) -> TileType:
    """노이즈 기반으로 (x, y) 지형 타입을 결정. 결정적 함수."""
    region_id = _get_region_for_point(x, y, w, h)
    terrain = _REGION_TERRAIN.get(region_id, _REGION_TERRAIN["forgotten_forest"])

    elevation = _smoothed_noise(x, y, 80.0, octaves=4, seed=seed)
    moisture = _smoothed_noise(x, y, 100.0, octaves=3, seed=seed + 500)
    detail = _smoothed_noise(x, y, 20.0, octaves=2, seed=seed + 1000)
    scatter = _smoothed_noise(x, y, 12.0, octaves=2, seed=seed + 1500)

    # ── 높은 고도: 장애물 ──
    if elevation > 0.82:
        return terrain["obstacle"]
    if elevation > 0.74:
        return terrain["obstacle"] if detail > 0.55 else terrain["secondary"]
    if elevation > 0.68:
        # 고지대-중간 전이: 바위/건조 지형 섞기
        return terrain["dry"] if detail > 0.6 else terrain["secondary"]

    # ── 낮은 고도: 물 ──
    if elevation < 0.07:
        return TileType.WATER
    if elevation < 0.14:
        return TileType.SHALLOW_WATER if moisture > 0.4 else terrain["secondary"]

    # ── 지역 경계 블렌딩 ──
    nx, ny = x / w, y / h
    min_dist = float("inf")
    second_dist = float("inf")
    closest_id = region_id
    for rid, (cx, cy) in _REGION_CENTERS.items():
        dist = (nx - cx) ** 2 + (ny - cy) ** 2
        if dist < min_dist:
            second_dist = min_dist
            min_dist = dist
        elif dist < second_dist:
            second_dist = dist
    # 경계 근처면 두 지역 타일 혼합
    blend_ratio = min_dist / max(second_dist, 0.001)
    if blend_ratio > 0.7 and detail > 0.55:
        # 경계 근처: 인접 지역의 primary 타일이 섞임
        return terrain["secondary"]

    # ── 장식 산포 (scatter 노이즈) ──
    if scatter > 0.78 and detail > 0.5:
        return terrain.get("scatter", terrain["accent"])

    # ── 디테일 기반 악센트 ──
    if detail > 0.72:
        return terrain["accent"]
    if detail > 0.65 and moisture > 0.5:
        return terrain["scatter"] if "scatter" in terrain else terrain["accent"]

    # ── 습도 기반 secondary ──
    if moisture > 0.62 and elevation < 0.45:
        return terrain["secondary"]
    if moisture > 0.55 and elevation < 0.35:
        # 습한 저지대: secondary와 accent 혼합
        return terrain["secondary"] if detail < 0.5 else terrain["accent"]

    # ── 건조 지역 ──
    if moisture < 0.22:
        return terrain.get("dry", terrain["primary"])
    if moisture < 0.32 and elevation > 0.5:
        return terrain.get("dry", terrain["secondary"])

    # ── 중간 고도에서 미세 변화 ──
    if 0.4 < elevation < 0.55 and 0.35 < detail < 0.45:
        return terrain["secondary"]

    return terrain["primary"]


_WALKABLE_TYPES = frozenset({
    TileType.FLOOR, TileType.GRASS, TileType.TALL_GRASS,
    TileType.SAND, TileType.SNOW, TileType.ICE_FLOOR,
    TileType.DEEP_FOREST, TileType.SWAMP, TileType.PATH,
    TileType.TOWN, TileType.CRYSTAL,
    TileType.FLOWER, TileType.ROCK, TileType.DEAD_TREE,
    TileType.MUSHROOM, TileType.CACTUS, TileType.RUINS,
    TileType.STAR_MOSS, TileType.SCORCHED_EARTH, TileType.CRYSTAL_GRASS,
})


def _is_walkable_type(tile_type: TileType) -> bool:
    return tile_type in _WALKABLE_TYPES


def _find_walkable_near_noise(
    cx: int, cy: int, w: int, h: int, seed: int,
    features: Optional[Dict] = None, radius: int = 50,
) -> Tuple[int, int]:
    """노이즈 기반으로 이동 가능한 위치 탐색 (타일 객체 없이)"""
    for r in range(radius):
        for dx in range(-r, r + 1):
            for dy in [-r, r]:
                px, py = cx + dx, cy + dy
                if 0 <= px < w and 0 <= py < h:
                    if features and (px, py) in features:
                        continue
                    tt = _compute_terrain_type(px, py, w, h, seed)
                    if _is_walkable_type(tt):
                        return px, py
            for dy in range(-r + 1, r):
                for dx_v in [-r, r]:
                    px, py = cx + dx_v, cy + dy
                    if 0 <= px < w and 0 <= py < h:
                        if features and (px, py) in features:
                            continue
                        tt = _compute_terrain_type(px, py, w, h, seed)
                        if _is_walkable_type(tt):
                            return px, py
    return max(1, min(w - 2, cx)), max(1, min(h - 2, cy))


# ══════════════════════════════════════════════════════════
#  피처 사전 계산 (타일 객체를 만들지 않고 좌표만 계산)
# ══════════════════════════════════════════════════════════

_PROTECTED_TILES = frozenset({
    TileType.TOWN, TileType.NPC, TileType.CAMPFIRE, TileType.PATH,
    TileType.SHOP, TileType.HEALING_SPRING, TileType.CAVE_ENTRANCE,
    TileType.KITCHEN, TileType.BLACKSMITH, TileType.ALCHEMY_LAB,
    TileType.STORAGE_BUILDING, TileType.QUEST_BOARD, TileType.INN,
    TileType.GUILD_HALL, TileType.FOUNTAIN, TileType.SIGNPOST, TileType.BRIDGE,
})


def _precalc_settlements(
    features: Dict[Tuple[int, int], TileType],
    spawn_points: Dict[str, Tuple[int, int]],
    npc_id_map: Dict[Tuple[int, int], str],
    w: int, h: int, seed: int,
):
    """각 지역에 마을 배치 (좌표만 계산), NPC ID 매핑 포함"""
    rng = random.Random(seed + 4000)

    _BUILDING_LAYOUT = [
        (0,   0,  TileType.FOUNTAIN),
        (0,  -5,  TileType.QUEST_BOARD),
        (-6, -3,  TileType.KITCHEN),
        ( 6, -3,  TileType.BLACKSMITH),
        (-6,  1,  TileType.ALCHEMY_LAB),
        ( 6,  1,  TileType.STORAGE_BUILDING),
        (-5,  5,  TileType.SHOP),
        ( 0,  5,  TileType.INN),
        ( 5,  5,  TileType.GUILD_HALL),
        ( 2, -1,  TileType.HEALING_SPRING),
        ( 0,  8,  TileType.CAMPFIRE),
    ]

    town_radius = 12
    building_types = frozenset(tt for _, _, tt in _BUILDING_LAYOUT)

    for region in REGIONS:
        cx_ratio, cy_ratio = _REGION_CENTERS[region.region_id]
        cx = int(cx_ratio * w)
        cy = int(cy_ratio * h)

        town_x, town_y = _find_walkable_near_noise(cx, cy, w, h, seed, features, radius=50)

        # 1) 마을 영역 (원형) - TOWN + PATH 경계
        for dy in range(-town_radius, town_radius + 1):
            for dx in range(-town_radius, town_radius + 1):
                dist = abs(dx) + abs(dy)
                px, py = town_x + dx, town_y + dy
                if 0 <= px < w and 0 <= py < h and dist <= town_radius + 3:
                    if dist >= town_radius + 2:
                        features[(px, py)] = TileType.PATH
                    else:
                        features[(px, py)] = TileType.TOWN

        # 2) 마을 내부 도로 (십자형)
        for d in range(-town_radius, town_radius + 1):
            px_v, py_v = town_x, town_y + d
            if 0 <= px_v < w and 0 <= py_v < h:
                features[(px_v, py_v)] = TileType.PATH
            px_h, py_h = town_x + d, town_y
            if 0 <= px_h < w and 0 <= py_h < h:
                features[(px_h, py_h)] = TileType.PATH

        # 3) 건물 배치
        for dx, dy, tile_type in _BUILDING_LAYOUT:
            bx, by = town_x + dx, town_y + dy
            if 0 <= bx < w and 0 <= by < h:
                features[(bx, by)] = tile_type
                for adj_dx in (-1, 0, 1):
                    for adj_dy in (-1, 0, 1):
                        if adj_dx == 0 and adj_dy == 0:
                            continue
                        ax, ay = bx + adj_dx, by + adj_dy
                        if 0 <= ax < w and 0 <= ay < h:
                            existing = features.get((ax, ay))
                            if existing not in building_types and existing != TileType.PATH:
                                features[(ax, ay)] = TileType.TOWN

        # 4) NPC 배치 (town_npcs.yaml의 NPC ID 할당)
        from src.rpg_mode.town_npc_manager import get_town_npc_manager, REGION_TO_TOWN_KEY
        npc_mgr = get_town_npc_manager()
        town_key = REGION_TO_TOWN_KEY.get(region.region_id, "")
        town_npc_ids = npc_mgr.get_town_npc_ids(town_key)

        npc_positions = [
            (-3, -3), (3, -3), (-3, 3), (3, 3),
            (-2, 0), (2, 0), (0, -2), (0, 3),
            (-4, -1), (4, -1), (-4, 2), (4, 2),
        ]
        placed_npcs = 0
        for ndx, ndy in npc_positions:
            if placed_npcs >= region.npc_count:
                break
            nx, ny = town_x + ndx, town_y + ndy
            if 0 <= nx < w and 0 <= ny < h:
                if features.get((nx, ny)) == TileType.TOWN:
                    features[(nx, ny)] = TileType.NPC
                    # NPC ID 매핑 (YAML 데이터 연결)
                    if placed_npcs < len(town_npc_ids):
                        npc_id_map[(nx, ny)] = town_npc_ids[placed_npcs]
                    placed_npcs += 1

        # 5) 이정표
        sign_x, sign_y = town_x, town_y + town_radius + 1
        if 0 <= sign_x < w and 0 <= sign_y < h:
            features[(sign_x, sign_y)] = TileType.SIGNPOST

        spawn_points[region.region_id] = (town_x, town_y)
        logger.info(f"  마을 계산: {region.name} ({town_x}, {town_y})")


def _precalc_roads(
    features: Dict[Tuple[int, int], TileType],
    water_set: Set[Tuple[int, int]],
    spawn_points: Dict[str, Tuple[int, int]],
    w: int, h: int, seed: int,
):
    """지역 간 도로 좌표 계산"""
    rng = random.Random(seed + 7000)
    connections = [
        ("forgotten_forest", "storm_plateau"),
        ("forgotten_forest", "twilight_desert"),
        ("storm_plateau", "eternal_glacier"),
        ("storm_plateau", "abyss_cavern"),
        ("twilight_desert", "abyss_cavern"),
        ("abyss_cavern", "war_lands"),
        ("eternal_glacier", "war_lands"),
        ("abyss_cavern", "starlight_throne"),
        ("war_lands", "starlight_throne"),
    ]

    for r1, r2 in connections:
        if r1 not in spawn_points or r2 not in spawn_points:
            continue
        x1, y1 = spawn_points[r1]
        x2, y2 = spawn_points[r2]
        _precalc_road_line(features, water_set, x1, y1, x2, y2, w, h, rng)


def _precalc_road_line(
    features: Dict[Tuple[int, int], TileType],
    water_set: Set[Tuple[int, int]],
    x1: int, y1: int, x2: int, y2: int,
    w: int, h: int, rng: random.Random,
):
    """두 지점 사이의 도로 좌표 계산"""
    mid_x = (x1 + x2) // 2 + rng.randint(-100, 100)
    mid_y = (y1 + y2) // 2 + rng.randint(-100, 100)
    waypoints = [(x1, y1), (mid_x, mid_y), (x2, y2)]

    road_w = 2
    for i in range(len(waypoints) - 1):
        sx, sy = waypoints[i]
        ex, ey = waypoints[i + 1]
        steps = max(abs(ex - sx), abs(ey - sy)) + 1
        for step in range(steps):
            t = step / max(1, steps - 1)
            px = int(sx + (ex - sx) * t)
            py = int(sy + (ey - sy) * t)
            for dy in range(-road_w, road_w + 1):
                for dx in range(-road_w, road_w + 1):
                    rx, ry = px + dx, py + dy
                    if not (0 <= rx < w and 0 <= ry < h):
                        continue
                    existing = features.get((rx, ry))
                    if existing in _PROTECTED_TILES:
                        continue
                    if (rx, ry) in water_set:
                        features[(rx, ry)] = TileType.BRIDGE
                    else:
                        features[(rx, ry)] = TileType.PATH


def _precalc_water(
    water_set: Set[Tuple[int, int]],
    shallow_set: Set[Tuple[int, int]],
    w: int, h: int, seed: int,
):
    """강과 호수 좌표 계산 (타일 객체 없이)"""
    rng = random.Random(seed + 2000)

    # 큰 강 2~3개
    num_rivers = rng.randint(2, 3)
    for i in range(num_rivers):
        if rng.random() < 0.5:
            rx, ry = rng.randint(0, w - 1), 0
        else:
            rx, ry = 0, rng.randint(0, h - 1)
        river_width = rng.randint(2, 4)
        for step in range(max(w, h) * 2):
            if rx < 0 or rx >= w or ry < 0 or ry >= h:
                break
            for dw in range(-river_width, river_width + 1):
                wx = rx + dw if rng.random() < 0.5 else rx
                wy = ry + dw if rng.random() >= 0.5 else ry
                if 0 <= wx < w and 0 <= wy < h:
                    water_set.add((wx, wy))
            dx = rng.choice([-1, 0, 0, 1, 1])
            dy = rng.choice([0, 1, 1, 1, 0])
            rx += dx
            ry += dy

    # 호수 5~8개
    num_lakes = rng.randint(5, 8)
    for _ in range(num_lakes):
        lx = rng.randint(w // 10, w * 9 // 10)
        ly = rng.randint(h // 10, h * 9 // 10)
        lake_r = rng.randint(15, 40)
        for dy in range(-lake_r, lake_r + 1):
            for dx in range(-lake_r, lake_r + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= lake_r:
                    px, py = lx + dx, ly + dy
                    if 0 <= px < w and 0 <= py < h:
                        if dist <= lake_r * 0.7:
                            water_set.add((px, py))
                        else:
                            shallow_set.add((px, py))


def _precalc_mountains(
    mountain_set: Set[Tuple[int, int]],
    w: int, h: int, seed: int,
):
    """산맥 좌표 계산"""
    rng = random.Random(seed + 3000)
    num_ranges = rng.randint(3, 4)
    for _ in range(num_ranges):
        mx = float(rng.randint(w // 5, w * 4 // 5))
        my = float(rng.randint(h // 5, h * 4 // 5))
        length = rng.randint(200, 600)
        angle = rng.uniform(0, math.pi * 2)
        for step in range(length):
            mtn_width = rng.randint(3, 8)
            cos_a = math.cos(angle + math.pi / 2)
            sin_a = math.sin(angle + math.pi / 2)
            for dw in range(-mtn_width, mtn_width + 1):
                px = int(mx + dw * cos_a)
                py = int(my + dw * sin_a)
                if 0 <= px < w and 0 <= py < h:
                    mountain_set.add((px, py))
            mx += math.cos(angle) * 2
            my += math.sin(angle) * 2
            angle += rng.uniform(-0.15, 0.15)


def get_dungeon_entrance_map(
    seed: int, w: int, h: int,
) -> Dict[Tuple[int, int], Tuple["RegionConfig", "SubDungeon"]]:
    """
    타일 좌표 → (RegionConfig, SubDungeon) 매핑을 반환한다.
    _precalc_dungeon_entrances()와 동일한 RNG 로직으로 좌표를 재현한다.
    """
    result: Dict[Tuple[int, int], Tuple[RegionConfig, SubDungeon]] = {}
    # _precalc_dungeon_entrances와 동일하게 features를 축적하여 좌표 일관성 유지
    features: Dict[Tuple[int, int], TileType] = {}
    rng = random.Random(seed + 5000)
    for region in REGIONS:
        cx_ratio, cy_ratio = _REGION_CENTERS[region.region_id]
        cx = int(cx_ratio * w)
        cy = int(cy_ratio * h)
        for sub in region.sub_dungeons:
            offset_x = rng.randint(-300, 300)
            offset_y = rng.randint(-300, 300)
            dx = max(10, min(w - 10, cx + offset_x))
            dy = max(10, min(h - 10, cy + offset_y))
            ex, ey = _find_walkable_near_noise(dx, dy, w, h, seed, features, radius=30)
            result[(ex, ey)] = (region, sub)
            # _precalc_dungeon_entrances와 동일하게 features 축적
            if (ex, ey) not in features:
                features[(ex, ey)] = TileType.CAVE_ENTRANCE
            if 0 <= ex + 1 < w and (ex + 1, ey) not in features:
                features[(ex + 1, ey)] = TileType.SIGNPOST
    return result


def _precalc_dungeon_entrances(
    features: Dict[Tuple[int, int], TileType],
    w: int, h: int, seed: int,
):
    """서브 던전 입구 좌표 계산"""
    rng = random.Random(seed + 5000)
    for region in REGIONS:
        cx_ratio, cy_ratio = _REGION_CENTERS[region.region_id]
        cx = int(cx_ratio * w)
        cy = int(cy_ratio * h)
        for sub in region.sub_dungeons:
            offset_x = rng.randint(-300, 300)
            offset_y = rng.randint(-300, 300)
            dx = max(10, min(w - 10, cx + offset_x))
            dy = max(10, min(h - 10, cy + offset_y))
            ex, ey = _find_walkable_near_noise(dx, dy, w, h, seed, features, radius=30)
            if (ex, ey) not in features:
                features[(ex, ey)] = TileType.CAVE_ENTRANCE
            if 0 <= ex + 1 < w and (ex + 1, ey) not in features:
                features[(ex + 1, ey)] = TileType.SIGNPOST


def _precalc_campfires(
    features: Dict[Tuple[int, int], TileType],
    w: int, h: int, seed: int,
):
    """캠프파이어 좌표 계산"""
    rng = random.Random(seed + 6000)
    spacing = 200
    for y in range(spacing, h - spacing, spacing):
        for x in range(spacing, w - spacing, spacing):
            if rng.random() < 0.3:
                fx, fy = _find_walkable_near_noise(x, y, w, h, seed, features, radius=20)
                if (fx, fy) not in features:
                    features[(fx, fy)] = TileType.CAMPFIRE


# ══════════════════════════════════════════════════════════
#  메인 생성 함수
# ══════════════════════════════════════════════════════════

def generate_rpg_world(
    width: int = RPG_WORLD_WIDTH,
    height: int = RPG_WORLD_HEIGHT,
    seed: Optional[int] = None,
) -> Tuple[RPGDungeonMap, Dict[str, Tuple[int, int]]]:
    """
    RPG 오픈월드 맵 생성 (청크 기반 레이지 로딩)

    1단계: 피처 좌표 사전 계산 (~수 초)
    2단계: LazyTileMap 생성 (즉시)
    실제 타일 객체는 접근 시에만 64x64 청크 단위로 생성됨.
    """
    if seed is None:
        seed = random.randint(0, 999999)

    logger.info(f"RPG 월드 생성 시작: {width}x{height}, seed={seed}")

    spawn_points: Dict[str, Tuple[int, int]] = {}

    # ── 1단계: 피처 좌표 사전 계산 ──
    # 물/산맥은 별도 셋으로 먼저 계산 (도로와의 교차 처리를 위해)
    water_set: Set[Tuple[int, int]] = set()
    shallow_set: Set[Tuple[int, int]] = set()
    mountain_set: Set[Tuple[int, int]] = set()

    logger.info("피처 계산: 수계...")
    _precalc_water(water_set, shallow_set, width, height, seed)
    logger.info(f"  강/호수 {len(water_set) + len(shallow_set):,}개 좌표")

    logger.info("피처 계산: 산맥...")
    _precalc_mountains(mountain_set, width, height, seed)
    logger.info(f"  산맥 {len(mountain_set):,}개 좌표")

    # 피처 딕셔너리 (좌표 → TileType, 우선순위 순서로 추가)
    features: Dict[Tuple[int, int], TileType] = {}

    # NPC 위치 → NPC ID 매핑 (마을 NPC용)
    npc_id_map: Dict[Tuple[int, int], str] = {}

    # 최고 우선순위: 마을/거점
    logger.info("피처 계산: 마을...")
    _precalc_settlements(features, spawn_points, npc_id_map, width, height, seed)

    # 도로 (마을 → 마을, 물 위는 다리)
    logger.info("피처 계산: 도로...")
    _precalc_roads(features, water_set, spawn_points, width, height, seed)

    # 던전 입구
    logger.info("피처 계산: 던전 입구...")
    _precalc_dungeon_entrances(features, width, height, seed)

    # 캠프파이어
    logger.info("피처 계산: 캠프파이어...")
    _precalc_campfires(features, width, height, seed)

    # 낮은 우선순위: 산맥 (기존 피처와 겹치지 않는 곳만)
    for pos in mountain_set:
        if pos not in features:
            features[pos] = TileType.MOUNTAIN

    # 최저 우선순위: 물 (기존 피처와 겹치지 않는 곳만)
    for pos in water_set:
        if pos not in features:
            features[pos] = TileType.WATER
    for pos in shallow_set:
        if pos not in features:
            features[pos] = TileType.SHALLOW_WATER

    logger.info(f"피처 계산 완료: 총 {len(features):,}개 좌표")

    # ── 2단계: 레이지 타일 맵 생성 (즉시) ──
    def terrain_fn(x: int, y: int) -> TileType:
        return _compute_terrain_type(x, y, width, height, seed)

    lazy_tiles = LazyTileMap(width, height, terrain_fn, features, npc_id_map)
    dungeon = RPGDungeonMap(width, height, lazy_tiles)

    # 시작 위치 설정
    start = spawn_points.get("forgotten_forest", (width // 6, height // 4))
    dungeon.player_start = start
    dungeon.stairs_up = None
    dungeon.stairs_down = None
    dungeon.generation_seed = seed

    logger.info(f"RPG 월드 생성 완료: 시작={start}")
    return dungeon, spawn_points
