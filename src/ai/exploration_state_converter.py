"""
탐험 상태 변환기 - ExplorationState 구성 로직 재사용 모듈

src/multiplayer/ai_bot.py의 _get_llm_ai_move() 내부에 인라인으로 작성된
FOV 기반 시야 분석, 위험 타일 스캔, 미탐험 방향 감지 로직을
재사용 가능한 정적 메서드로 추출합니다.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.core.logger import get_logger
from src.multiplayer.llm_player_bot import ExplorationState

logger = get_logger("ai.exploration_state_converter")


class ExplorationStateConverter:
    """
    탐험 컨텍스트를 ExplorationState 데이터클래스로 변환하는 정적 유틸리티

    ai_bot.py 및 기타 모듈에서 공통으로 사용할 수 있도록
    모든 메서드를 정적(static)으로 제공합니다.
    """

    # 탐험 탐지 반경 (타일 단위)
    SCAN_RADIUS: int = 5
    # 결과 목록 최대 크기 (프롬프트 길이 제한)
    MAX_ENEMIES: int = 10
    MAX_ITEMS: int = 10
    MAX_VISIBLE_TILES: int = 50
    MAX_HAZARDS: int = 10
    MAX_OBJECTS: int = 10
    MAX_HEALING_ITEMS: int = 5

    @staticmethod
    def from_exploration(
        exploration: Any,
        player_pos: Tuple[int, int],
        party: List[Any],
        inventory: Any,
        floor_number: int,
    ) -> ExplorationState:
        """
        탐험 객체와 파티/인벤토리 정보로부터 ExplorationState 생성

        Args:
            exploration: Exploration 객체 (dungeon, enemies, fov_map 등 보유)
            player_pos:  현재 플레이어 좌표 (x, y)
            party:       파티 캐릭터 리스트 (current_hp, max_hp, current_mp, max_mp 속성 보유)
            inventory:   인벤토리 객체 (items, gold 속성 보유)
            floor_number: 현재 층 번호

        Returns:
            완성된 ExplorationState 인스턴스
        """
        current_x, current_y = player_pos

        # 파티 평균 HP/MP 계산
        party_hp_pct, party_mp_pct = ExplorationStateConverter._calc_party_vitals(party)

        # FOV/거리 기반 주변 적 목록
        nearby_enemies = ExplorationStateConverter._detect_nearby_enemies(
            exploration, current_x, current_y
        )

        # 미탐험 이동 가능 방향
        unexplored_directions = ExplorationStateConverter._detect_unexplored_directions(
            exploration, current_x, current_y
        )

        # 위험 타일 및 오브젝트 스캔
        hazard_tiles, objects = ExplorationStateConverter._scan_dungeon_tiles(
            exploration, current_x, current_y
        )

        # 회복 아이템 목록
        healing_items = ExplorationStateConverter._collect_healing_items(inventory)

        # 현재 골드
        gold = getattr(inventory, "gold", 0) if inventory else 0

        state = ExplorationState(
            current_floor=floor_number,
            current_position=player_pos,
            visible_tiles=[],                           # FOV 원시 타일은 생략 (프롬프트 비대화 방지)
            discovered_rooms=ExplorationStateConverter._estimate_discovered_rooms(exploration),
            total_rooms=10,                             # 기본값; dungeon에 total_rooms 속성이 있으면 덮어씀
            nearby_enemies=nearby_enemies[: ExplorationStateConverter.MAX_ENEMIES],
            nearby_items=[],                            # 향후 아이템 감지 로직 추가 가능
            nearby_exits=[],
            party_hp_percent=party_hp_pct,
            party_mp_percent=party_mp_pct,
            has_healing_point=False,
            floor_type="dungeon",
            stairs_down_position=ExplorationStateConverter._find_stairs(exploration, "down"),
            stairs_up_position=ExplorationStateConverter._find_stairs(exploration, "up"),
            unexplored_directions=unexplored_directions if unexplored_directions else [(0, -1), (0, 1), (-1, 0), (1, 0)],
            hazard_tiles=hazard_tiles[: ExplorationStateConverter.MAX_HAZARDS],
            objects=objects[: ExplorationStateConverter.MAX_OBJECTS],
            healing_items=healing_items[: ExplorationStateConverter.MAX_HEALING_ITEMS],
            gold=gold,
        )

        # total_rooms 오버라이드 (dungeon 속성 우선)
        if exploration and hasattr(exploration, "dungeon") and exploration.dungeon:
            dungeon = exploration.dungeon
            if hasattr(dungeon, "total_rooms"):
                state.total_rooms = dungeon.total_rooms

        logger.debug(
            f"ExplorationState 생성: floor={floor_number}, pos={player_pos}, "
            f"enemies={len(state.nearby_enemies)}, hazards={len(state.hazard_tiles)}, "
            f"objects={len(state.objects)}"
        )
        return state

    # -------------------------------------------------------------------------
    # 내부 헬퍼 메서드
    # -------------------------------------------------------------------------

    @staticmethod
    def _calc_party_vitals(party: List[Any]) -> Tuple[float, float]:
        """
        파티 평균 HP/MP 퍼센트 계산

        Returns:
            (hp_percent, mp_percent) — 0.0 ~ 100.0 범위
        """
        alive = [
            c for c in party
            if hasattr(c, "is_alive") and c.is_alive
        ]
        if not alive:
            alive = party or []

        if not alive:
            return 100.0, 100.0

        def safe_pct(cur_attr: str, max_attr: str, member: Any) -> float:
            cur = getattr(member, cur_attr, 0)
            mx = getattr(member, max_attr, 0)
            return (cur / mx * 100.0) if mx > 0 else 100.0

        hp_pct = sum(safe_pct("current_hp", "max_hp", c) for c in alive) / len(alive)
        mp_pct = sum(safe_pct("current_mp", "max_mp", c) for c in alive) / len(alive)
        return round(hp_pct, 1), round(mp_pct, 1)

    @staticmethod
    def _detect_nearby_enemies(
        exploration: Any,
        cx: int,
        cy: int,
    ) -> List[str]:
        """
        FOV 시야 또는 거리 기반으로 근처 적 감지

        FOV 맵이 있으면 시야 내 적만 포함,
        없으면 SCAN_RADIUS 이내 적을 거리 기반으로 포함합니다.

        Returns:
            "적이름@(x,y)" 형식의 문자열 목록
        """
        if not exploration or not hasattr(exploration, "enemies"):
            return []

        radius = ExplorationStateConverter.SCAN_RADIUS
        result: List[str] = []

        fov_map = getattr(exploration, "fov_map", None)
        if fov_map and hasattr(fov_map, "visible"):
            # FOV 기반 감지
            for enemy in exploration.enemies:
                try:
                    if fov_map.visible[enemy.x, enemy.y]:
                        result.append(f"{enemy.name}@({enemy.x},{enemy.y})")
                except (IndexError, AttributeError):
                    pass
        else:
            # 거리 기반 감지 (폴백)
            for enemy in exploration.enemies:
                ex = getattr(enemy, "x", None)
                ey = getattr(enemy, "y", None)
                if ex is not None and ey is not None:
                    if abs(ex - cx) <= radius and abs(ey - cy) <= radius:
                        result.append(f"{enemy.name}@({ex},{ey})")

        return result

    @staticmethod
    def _detect_unexplored_directions(
        exploration: Any,
        cx: int,
        cy: int,
    ) -> List[Tuple[int, int]]:
        """
        인접 4방향 중 걷기 가능하고 미탐험된 방향 목록 반환

        Returns:
            (dx, dy) 튜플 목록 (예: [(0, -1), (1, 0)])
        """
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        if not exploration:
            return []

        dungeon = getattr(exploration, "dungeon", None)
        if not dungeon or not hasattr(dungeon, "get_tile"):
            return []

        result: List[Tuple[int, int]] = []
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            tile = dungeon.get_tile(nx, ny)
            if tile and getattr(tile, "walkable", False) and not getattr(tile, "explored", True):
                result.append((dx, dy))

        return result

    @staticmethod
    def _scan_dungeon_tiles(
        exploration: Any,
        cx: int,
        cy: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        SCAN_RADIUS 범위 내 위험 타일 및 오브젝트 수집

        Returns:
            (hazard_tiles, objects)
            hazard_tiles: [{"pos": (x,y), "type": str, "damage": int}]
            objects:      [{"pos": (x,y), "type": str, "interactable": bool}]
        """
        hazard_tiles: List[Dict[str, Any]] = []
        objects: List[Dict[str, Any]] = []

        if not exploration:
            return hazard_tiles, objects

        dungeon = getattr(exploration, "dungeon", None)
        if not dungeon or not hasattr(dungeon, "get_tile"):
            return hazard_tiles, objects

        radius = ExplorationStateConverter.SCAN_RADIUS
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                tx, ty = cx + dx, cy + dy
                tile = dungeon.get_tile(tx, ty)
                if tile is None:
                    continue

                # 위험 타일 감지 (damage 속성이 양수인 타일)
                tile_damage = getattr(tile, "damage", 0)
                if tile_damage > 0:
                    hazard_tiles.append({
                        "pos":    (tx, ty),
                        "type":   getattr(tile, "tile_type", "hazard"),
                        "damage": tile_damage,
                    })

                # 보물상자 오브젝트 감지
                if getattr(tile, "has_chest", False):
                    objects.append({
                        "pos":          (tx, ty),
                        "type":         "chest",
                        "interactable": True,
                    })

        # 채집 오브젝트 (dungeon.harvestables)
        harvestables = getattr(dungeon, "harvestables", [])
        for h in harvestables:
            hx = getattr(h, "x", None)
            hy = getattr(h, "y", None)
            if hx is None or hy is None:
                continue
            if abs(hx - cx) <= radius and abs(hy - cy) <= radius:
                obj_type = h.object_type.value if hasattr(h, "object_type") and hasattr(h.object_type, "value") else "harvestable"
                objects.append({
                    "pos":          (hx, hy),
                    "type":         obj_type,
                    "interactable": True,
                })

        return hazard_tiles, objects

    @staticmethod
    def _collect_healing_items(inventory: Any) -> List[Dict[str, Any]]:
        """
        인벤토리에서 회복 아이템 목록 추출

        Returns:
            [{"name": str, "heal": int, "count": int}] 형식의 목록
        """
        if not inventory:
            return []

        result: List[Dict[str, Any]] = []
        for item in getattr(inventory, "items", []):
            heal_amount = getattr(item, "heal_amount", 0)
            if heal_amount > 0:
                result.append({
                    "name":  getattr(item, "name", "Unknown"),
                    "heal":  heal_amount,
                    "count": getattr(item, "count", 1),
                })
        return result

    @staticmethod
    def _estimate_discovered_rooms(exploration: Any) -> int:
        """
        탐험된 위치 수로 발견된 방 수 추정

        Returns:
            추정 방 수 (탐험 위치 10개당 방 1개로 환산)
        """
        if not exploration:
            return 0

        explored = getattr(exploration, "explored_positions", None)
        if explored is None:
            return 0

        count = len(explored)
        return max(1, count // 10)

    @staticmethod
    def _find_stairs(exploration: Any, direction: str) -> Optional[Tuple[int, int]]:
        """
        계단 위치 탐색

        Args:
            exploration: Exploration 객체
            direction:   "up" 또는 "down"

        Returns:
            계단 좌표 (x, y) 또는 None
        """
        if not exploration:
            return None

        attr_map = {
            "down": ["stairs_down", "stairs_down_pos", "exit_pos"],
            "up":   ["stairs_up", "stairs_up_pos", "entrance_pos"],
        }

        for attr in attr_map.get(direction, []):
            val = getattr(exploration, attr, None)
            if val is not None:
                # (x, y) 튜플이거나 x/y 속성을 가진 객체 모두 처리
                if isinstance(val, tuple) and len(val) == 2:
                    return val
                if hasattr(val, "x") and hasattr(val, "y"):
                    return (val.x, val.y)

        return None
