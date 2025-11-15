"""
던전 생성기

BSP 알고리즘을 사용한 절차적 던전 생성
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import random

from src.world.tile import Tile, TileType
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.WORLD)


@dataclass
class Rect:
    """사각형 영역"""
    x: int
    y: int
    width: int
    height: int

    @property
    def x1(self) -> int:
        return self.x

    @property
    def y1(self) -> int:
        return self.y

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> Tuple[int, int]:
        """중심점"""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def intersects(self, other: 'Rect') -> bool:
        """다른 사각형과 겹치는지 확인"""
        return (
            self.x1 <= other.x2 and
            self.x2 >= other.x1 and
            self.y1 <= other.y2 and
            self.y2 >= other.y1
        )


@dataclass
class BSPNode:
    """BSP 트리 노드"""
    rect: Rect
    left: Optional['BSPNode'] = None
    right: Optional['BSPNode'] = None
    room: Optional[Rect] = None  # 실제 방 (rect보다 작음)


class DungeonMap:
    """던전 맵"""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: List[List[Tile]] = []
        self.rooms: List[Rect] = []
        self.corridors: List[Tuple[int, int]] = []

        # 특수 위치
        self.stairs_up: Optional[Tuple[int, int]] = None
        self.stairs_down: Optional[Tuple[int, int]] = None
        self.keys: List[Tuple[int, int, str]] = []  # (x, y, key_id)
        self.locked_doors: List[Tuple[int, int, str]] = []  # (x, y, key_id)
        self.teleporters: Dict[Tuple[int, int], Tuple[int, int]] = {}  # src -> dst
        self.boss_room: Optional[Rect] = None

        # 채집 오브젝트
        self.harvestables: List[Any] = []  # HarvestableObject 리스트

        # 타일 초기화
        self._initialize_tiles()

    def _initialize_tiles(self):
        """타일 초기화 (모두 VOID로)"""
        self.tiles = [
            [Tile(TileType.VOID, x, y) for x in range(self.width)]
            for y in range(self.height)
        ]

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        """타일 가져오기"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_tile(self, x: int, y: int, tile_type: TileType, **kwargs):
        """타일 설정"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = Tile(tile_type, x, y, **kwargs)

    def is_walkable(self, x: int, y: int) -> bool:
        """이동 가능 여부"""
        tile = self.get_tile(x, y)
        return tile is not None and tile.walkable and not tile.locked


class DungeonGenerator:
    """던전 생성기"""

    def __init__(
        self,
        width: int = 80,
        height: int = 50,
        min_room_size: int = 5,
        max_room_size: int = 12,
        max_depth: int = 4
    ):
        self.width = width
        self.height = height
        self.min_room_size = min_room_size
        self.max_room_size = max_room_size
        self.max_depth = max_depth

    def generate(self, floor_number: int = 1) -> DungeonMap:
        """
        던전 생성

        Args:
            floor_number: 층 번호

        Returns:
            DungeonMap
        """
        logger.info(f"던전 생성 시작: {self.width}x{self.height}, 층 {floor_number}")

        dungeon = DungeonMap(self.width, self.height)

        # BSP로 방 생성
        root = BSPNode(Rect(0, 0, self.width, self.height))
        self._split_node(root, 0)
        self._create_rooms(root, dungeon)

        # 복도로 방 연결
        self._connect_rooms(root, dungeon)

        # 벽 생성
        self._create_walls(dungeon)

        # 계단 배치
        self._place_stairs(dungeon)

        # 기믹 배치
        self._place_gimmicks(dungeon, floor_number)

        # 채집 오브젝트 배치
        self._place_harvestables(dungeon, floor_number)

        logger.info(f"던전 생성 완료: {len(dungeon.rooms)}개 방")
        return dungeon

    def _split_node(self, node: BSPNode, depth: int):
        """BSP 노드 분할"""
        if depth >= self.max_depth:
            return

        rect = node.rect

        # 최소 크기 체크
        can_split_horizontally = rect.height >= self.min_room_size * 2
        can_split_vertically = rect.width >= self.min_room_size * 2

        if not can_split_horizontally and not can_split_vertically:
            return

        # 분할 방향 결정
        if can_split_horizontally and can_split_vertically:
            split_horizontally = random.choice([True, False])
        elif can_split_horizontally:
            split_horizontally = True
        else:
            split_horizontally = False

        # 분할
        if split_horizontally:
            # 수평 분할
            split_pos = random.randint(
                rect.y + self.min_room_size,
                rect.y + rect.height - self.min_room_size
            )
            node.left = BSPNode(Rect(rect.x, rect.y, rect.width, split_pos - rect.y))
            node.right = BSPNode(Rect(rect.x, split_pos, rect.width, rect.y + rect.height - split_pos))
        else:
            # 수직 분할
            split_pos = random.randint(
                rect.x + self.min_room_size,
                rect.x + rect.width - self.min_room_size
            )
            node.left = BSPNode(Rect(rect.x, rect.y, split_pos - rect.x, rect.height))
            node.right = BSPNode(Rect(split_pos, rect.y, rect.x + rect.width - split_pos, rect.height))

        # 재귀 분할
        if node.left:
            self._split_node(node.left, depth + 1)
        if node.right:
            self._split_node(node.right, depth + 1)

    def _create_rooms(self, node: BSPNode, dungeon: DungeonMap):
        """방 생성"""
        if node.left or node.right:
            # 중간 노드 - 자식 처리
            if node.left:
                self._create_rooms(node.left, dungeon)
            if node.right:
                self._create_rooms(node.right, dungeon)
        else:
            # 리프 노드 - 방 생성
            rect = node.rect

            # 방 크기 랜덤 (공간보다 작게)
            # 최소값과 최대값이 올바른 범위인지 확인
            max_width = max(self.min_room_size, min(self.max_room_size, rect.width - 2))
            max_height = max(self.min_room_size, min(self.max_room_size, rect.height - 2))

            room_width = random.randint(self.min_room_size, max_width)
            room_height = random.randint(self.min_room_size, max_height)

            # 방 위치 랜덤 (경계 체크)
            max_x_offset = max(1, rect.width - room_width - 1)
            max_y_offset = max(1, rect.height - room_height - 1)

            room_x = rect.x + random.randint(1, max_x_offset)
            room_y = rect.y + random.randint(1, max_y_offset)

            room = Rect(room_x, room_y, room_width, room_height)
            node.room = room
            dungeon.rooms.append(room)

            # 바닥 타일 생성
            for y in range(room.y1, room.y2):
                for x in range(room.x1, room.x2):
                    dungeon.set_tile(x, y, TileType.FLOOR)

    def _connect_rooms(self, node: BSPNode, dungeon: DungeonMap):
        """방들을 복도로 연결"""
        if node.left and node.right:
            # 두 자식의 중심점 연결
            left_center = self._get_room_center(node.left)
            right_center = self._get_room_center(node.right)

            if left_center and right_center:
                self._create_corridor(dungeon, left_center, right_center)

            # 재귀 연결
            self._connect_rooms(node.left, dungeon)
            self._connect_rooms(node.right, dungeon)

    def _get_room_center(self, node: BSPNode) -> Optional[Tuple[int, int]]:
        """노드의 방 중심점 가져오기"""
        if node.room:
            return node.room.center
        elif node.left:
            return self._get_room_center(node.left)
        elif node.right:
            return self._get_room_center(node.right)
        return None

    def _create_corridor(
        self,
        dungeon: DungeonMap,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ):
        """복도 생성 (L자 형태)"""
        x1, y1 = start
        x2, y2 = end

        # 중간 지점 결정 (L자)
        if random.choice([True, False]):
            # 수평 먼저
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if dungeon.get_tile(x, y1).tile_type == TileType.VOID:
                    dungeon.set_tile(x, y1, TileType.FLOOR)
                    dungeon.corridors.append((x, y1))

            for y in range(min(y1, y2), max(y1, y2) + 1):
                if dungeon.get_tile(x2, y).tile_type == TileType.VOID:
                    dungeon.set_tile(x2, y, TileType.FLOOR)
                    dungeon.corridors.append((x2, y))
        else:
            # 수직 먼저
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if dungeon.get_tile(x1, y).tile_type == TileType.VOID:
                    dungeon.set_tile(x1, y, TileType.FLOOR)
                    dungeon.corridors.append((x1, y))

            for x in range(min(x1, x2), max(x1, x2) + 1):
                if dungeon.get_tile(x, y2).tile_type == TileType.VOID:
                    dungeon.set_tile(x, y2, TileType.FLOOR)
                    dungeon.corridors.append((x, y2))

    def _create_walls(self, dungeon: DungeonMap):
        """벽 생성 (바닥 주변)"""
        for y in range(dungeon.height):
            for x in range(dungeon.width):
                tile = dungeon.get_tile(x, y)
                if tile.tile_type == TileType.VOID:
                    # 인접한 타일 중 바닥이 있으면 벽으로
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        neighbor = dungeon.get_tile(nx, ny)
                        if neighbor and neighbor.tile_type in [TileType.FLOOR, TileType.DOOR]:
                            dungeon.set_tile(x, y, TileType.WALL)
                            break

    def _place_stairs(self, dungeon: DungeonMap):
        """계단 배치"""
        if not dungeon.rooms:
            return

        # 올라가는 계단 - 첫 번째 방
        first_room = dungeon.rooms[0]
        x, y = first_room.center
        dungeon.set_tile(x, y, TileType.STAIRS_UP)
        dungeon.stairs_up = (x, y)

        # 내려가는 계단 - 마지막 방
        last_room = dungeon.rooms[-1]
        x, y = last_room.center
        dungeon.set_tile(x, y, TileType.STAIRS_DOWN)
        dungeon.stairs_down = (x, y)

    def _place_gimmicks(self, dungeon: DungeonMap, floor_number: int):
        """기믹 배치"""
        if len(dungeon.rooms) < 3:
            return

        # 난이도에 따라 기믹 개수 증가
        num_keys = min(3, 1 + floor_number // 3)
        num_traps = min(10, 2 + floor_number)
        num_chests = min(5, 1 + floor_number // 2)
        num_teleporters = min(4, floor_number // 5)

        # 열쇠와 잠긴 문
        self._place_keys_and_locks(dungeon, num_keys)

        # 함정
        self._place_traps(dungeon, num_traps)

        # 보물상자
        self._place_chests(dungeon, num_chests)

        # 떨어진 아이템/장비
        num_items = min(15, 3 + floor_number // 2)
        self._place_items(dungeon, num_items)

        # 텔레포터
        self._place_teleporters(dungeon, num_teleporters)

        # 용암 (위험 지역)
        if floor_number >= 3:
            self._place_lava(dungeon, floor_number)

        # 치유의 샘
        if random.random() < 0.3:
            self._place_healing_spring(dungeon)

        # 보스룸 (마지막 층 또는 5층마다)
        if floor_number % 5 == 0:
            self._place_boss_room(dungeon)

    def _place_keys_and_locks(self, dungeon: DungeonMap, num_keys: int):
        """열쇠와 잠긴 문 배치"""
        for i in range(num_keys):
            key_id = f"key_{i}"

            # 랜덤 방에 열쇠 배치
            key_room = random.choice(dungeon.rooms[:-2])  # 마지막 2개 방 제외
            key_pos = self._get_random_floor_pos(dungeon, key_room)
            if key_pos:
                dungeon.set_tile(key_pos[0], key_pos[1], TileType.KEY, key_id=key_id)
                dungeon.keys.append((key_pos[0], key_pos[1], key_id))

            # 복도에 잠긴 문 배치
            if len(dungeon.corridors) > 10:
                lock_pos = random.choice(dungeon.corridors[-len(dungeon.corridors)//2:])
                dungeon.set_tile(
                    lock_pos[0], lock_pos[1],
                    TileType.LOCKED_DOOR,
                    key_id=key_id,
                    locked=True
                )
                dungeon.locked_doors.append((lock_pos[0], lock_pos[1], key_id))

    def _place_traps(self, dungeon: DungeonMap, num_traps: int):
        """함정 배치"""
        for _ in range(num_traps):
            room = random.choice(dungeon.rooms)
            pos = self._get_random_floor_pos(dungeon, room)
            if pos:
                damage = random.randint(5, 20)
                dungeon.set_tile(pos[0], pos[1], TileType.TRAP, trap_damage=damage)

    def _place_chests(self, dungeon: DungeonMap, num_chests: int):
        """보물상자 배치"""
        for i in range(num_chests):
            room = random.choice(dungeon.rooms)
            pos = self._get_random_floor_pos(dungeon, room)
            if pos:
                loot_id = f"chest_{i}"
                dungeon.set_tile(pos[0], pos[1], TileType.CHEST, loot_id=loot_id)

    def _place_items(self, dungeon: DungeonMap, num_items: int):
        """떨어진 아이템/장비 배치"""
        for i in range(num_items):
            room = random.choice(dungeon.rooms)
            pos = self._get_random_floor_pos(dungeon, room)
            if pos:
                item_id = f"item_{i}"
                dungeon.set_tile(pos[0], pos[1], TileType.ITEM, loot_id=item_id)

    def _place_teleporters(self, dungeon: DungeonMap, num_pairs: int):
        """텔레포터 배치 (쌍으로)"""
        for _ in range(num_pairs):
            if len(dungeon.rooms) < 2:
                break

            # 두 방 선택
            room1, room2 = random.sample(dungeon.rooms, 2)

            pos1 = self._get_random_floor_pos(dungeon, room1)
            pos2 = self._get_random_floor_pos(dungeon, room2)

            if pos1 and pos2:
                dungeon.set_tile(pos1[0], pos1[1], TileType.TELEPORTER, teleport_target=pos2)
                dungeon.set_tile(pos2[0], pos2[1], TileType.TELEPORTER, teleport_target=pos1)
                dungeon.teleporters[pos1] = pos2
                dungeon.teleporters[pos2] = pos1

    def _place_lava(self, dungeon: DungeonMap, floor_number: int):
        """용암 배치"""
        num_lava = min(5, floor_number // 2)
        for _ in range(num_lava):
            room = random.choice(dungeon.rooms)
            # 방 가장자리에 용암
            if random.choice([True, False]):
                # 가로
                y = random.choice([room.y1, room.y2 - 1])
                for x in range(room.x1, room.x2):
                    if random.random() < 0.5:
                        dungeon.set_tile(x, y, TileType.LAVA)
            else:
                # 세로
                x = random.choice([room.x1, room.x2 - 1])
                for y in range(room.y1, room.y2):
                    if random.random() < 0.5:
                        dungeon.set_tile(x, y, TileType.LAVA)

    def _place_healing_spring(self, dungeon: DungeonMap):
        """치유의 샘 배치"""
        room = random.choice(dungeon.rooms)
        pos = self._get_random_floor_pos(dungeon, room)
        if pos:
            dungeon.set_tile(pos[0], pos[1], TileType.HEALING_SPRING)

    def _place_boss_room(self, dungeon: DungeonMap):
        """보스룸 배치"""
        if not dungeon.rooms:
            return

        # 마지막 방을 보스룸으로
        boss_room = dungeon.rooms[-1]
        dungeon.boss_room = boss_room

        # 입구에 경고 타일
        cx, cy = boss_room.center
        dungeon.set_tile(cx, cy - 2, TileType.BOSS_ROOM)

    def _get_random_floor_pos(
        self,
        dungeon: DungeonMap,
        room: Rect,
        avoid_center: bool = False
    ) -> Optional[Tuple[int, int]]:
        """방 안의 랜덤 바닥 위치"""
        attempts = 0
        while attempts < 20:
            x = random.randint(room.x1, room.x2 - 1)
            y = random.randint(room.y1, room.y2 - 1)

            tile = dungeon.get_tile(x, y)
            if tile and tile.tile_type == TileType.FLOOR:
                if avoid_center:
                    cx, cy = room.center
                    if abs(x - cx) < 2 and abs(y - cy) < 2:
                        attempts += 1
                        continue
                return (x, y)

            attempts += 1

        return None

    def _place_harvestables(self, dungeon: DungeonMap, floor_number: int):
        """
        채집 오브젝트 배치

        Args:
            dungeon: 던전 맵
            floor_number: 층 번호
        """
        try:
            from src.gathering.harvestable import HarvestableGenerator, HarvestableType, HarvestableObject

            # 층별 개수 결정 (8~15개로 대폭 증가)
            count = random.randint(8, 15)

            # 채집 오브젝트 생성
            harvestables = HarvestableGenerator.generate_for_floor(floor_number, count)

            # 방에 배치
            for harvestable in harvestables:
                if not dungeon.rooms:
                    break

                # 랜덤 방 선택
                room = random.choice(dungeon.rooms)
                pos = self._get_random_floor_pos(dungeon, room, avoid_center=True)

                if pos:
                    harvestable.x, harvestable.y = pos
                    dungeon.harvestables.append(harvestable)

            # 요리솥 배치 (3층당 1번 = 약 33% 확률)
            if random.random() < 0.33 or floor_number % 3 == 0:
                room = random.choice(dungeon.rooms) if dungeon.rooms else None
                if room:
                    pos = self._get_random_floor_pos(dungeon, room, avoid_center=False)
                    if pos:
                        cooking_pot = HarvestableObject(
                            object_type=HarvestableType.COOKING_POT,
                            x=pos[0],
                            y=pos[1]
                        )
                        dungeon.harvestables.append(cooking_pot)
                        logger.info(f"요리솥 배치: {pos}")

            logger.info(f"채집 오브젝트 {len(dungeon.harvestables)}개 배치")

        except ImportError as e:
            logger.warning(f"채집 시스템 로드 실패: {e}")
