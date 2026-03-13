"""
청크 기반 레이지 타일 맵

3000x3000 (9백만 타일) 맵을 64x64 청크 단위로 레이지 생성.
플레이어 주변 청크만 메모리에 유지 (LRU 캐시).
접근하지 않은 영역은 타일 객체가 아예 생성되지 않는다.
"""

from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple

from src.world.tile import TileType, Tile
from src.world.dungeon_generator import DungeonMap

CHUNK_SIZE = 64
MAX_CHUNKS = 128  # 최대 128 청크 = ~524K 타일 in memory


class _LazyRow:
    """tiles[y] 프록시 - tiles[y][x] 접근 시 청크 자동 생성"""
    __slots__ = ('_map', '_y')

    def __init__(self, tile_map: 'LazyTileMap', y: int):
        self._map = tile_map
        self._y = y

    def __getitem__(self, x: int) -> Tile:
        return self._map._get_tile(x, self._y)

    def __setitem__(self, x: int, value):
        self._map._set_tile(x, self._y, value)


class LazyTileMap:
    """
    청크 기반 레이지 타일 맵.

    tiles[y][x] 형태로 접근 가능하며, 접근된 64x64 청크만 생성한다.
    LRU 캐시로 최대 MAX_CHUNKS개의 청크만 메모리에 유지.
    """

    def __init__(
        self,
        width: int,
        height: int,
        terrain_fn: Callable[[int, int], TileType],
        features: Dict[Tuple[int, int], TileType],
        npc_id_map: Optional[Dict[Tuple[int, int], str]] = None,
    ):
        self.width = width
        self.height = height
        self._terrain_fn = terrain_fn
        self._features = features  # 미리 계산된 피처 좌표 → TileType
        self._npc_id_map = npc_id_map or {}  # NPC 좌표 → NPC ID
        self._chunks: OrderedDict = OrderedDict()
        self._overrides: Dict[Tuple[int, int], Tile] = {}

    def __getitem__(self, y: int) -> _LazyRow:
        return _LazyRow(self, y)

    def __len__(self) -> int:
        return self.height

    def _get_tile(self, x: int, y: int) -> Tile:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return Tile(TileType.VOID, x, y)

        chunk_key = (x // CHUNK_SIZE, y // CHUNK_SIZE)

        if chunk_key not in self._chunks:
            self._generate_chunk(chunk_key)
        else:
            self._chunks.move_to_end(chunk_key)

        return self._chunks[chunk_key][(y % CHUNK_SIZE)][(x % CHUNK_SIZE)]

    def _set_tile(self, x: int, y: int, value):
        """런타임 타일 수정"""
        tile = value if isinstance(value, Tile) else Tile(value, x, y)

        self._overrides[(x, y)] = tile

        chunk_key = (x // CHUNK_SIZE, y // CHUNK_SIZE)
        if chunk_key in self._chunks:
            self._chunks[chunk_key][y % CHUNK_SIZE][x % CHUNK_SIZE] = tile

    def set_override(self, x: int, y: int, tile: Tile):
        """타일 오버라이드 (DungeonMap.set_tile 호환)"""
        self._set_tile(x, y, tile)

    def _generate_chunk(self, chunk_key: Tuple[int, int]):
        """64x64 청크를 레이지 생성"""
        # LRU 캐시 초과 시 가장 오래된 청크 제거
        while len(self._chunks) >= MAX_CHUNKS:
            self._chunks.popitem(last=False)

        cx, cy = chunk_key
        x0 = cx * CHUNK_SIZE
        y0 = cy * CHUNK_SIZE

        chunk = []
        for ly in range(CHUNK_SIZE):
            row = []
            wy = y0 + ly
            for lx in range(CHUNK_SIZE):
                wx = x0 + lx

                if wx >= self.width or wy >= self.height:
                    row.append(Tile(TileType.VOID, wx, wy))
                    continue

                # 1) 런타임 오버라이드
                override = self._overrides.get((wx, wy))
                if override is not None:
                    row.append(override)
                    continue

                # 2) 미리 계산된 피처 (마을, 도로, 강 등)
                feat = self._features.get((wx, wy))
                if feat is not None:
                    tile = Tile(feat, wx, wy)
                    tile.explored = True
                    # NPC 타일이면 npc_id 설정
                    if feat == TileType.NPC:
                        npc_id = self._npc_id_map.get((wx, wy))
                        if npc_id:
                            tile.npc_id = npc_id
                    row.append(tile)
                    continue

                # 3) 노이즈 기반 지형 (결정적)
                tile_type = self._terrain_fn(wx, wy)
                tile = Tile(tile_type, wx, wy)
                tile.explored = True
                row.append(tile)

            chunk.append(row)

        # 채집 타임스탬프 기반 리젠 체크 (RPGDungeonMap에서만 사용)
        self._apply_harvest_state_to_chunk(chunk_key, chunk)

        self._chunks[chunk_key] = chunk

    def _apply_harvest_state_to_chunk(self, chunk_key: Tuple[int, int], chunk):
        """청크 생성 시 채집 상태를 적용/리젠 처리"""
        # RPGDungeonMap의 harvest_timestamps 참조
        # LazyTileMap은 독립이므로, RPGDungeonMap이 이 콜백을 설정
        if not hasattr(self, '_harvest_check_fn') or self._harvest_check_fn is None:
            return

        self._harvest_check_fn(chunk_key, chunk)


class RPGDungeonMap(DungeonMap):
    """
    RPG 오픈월드용 DungeonMap.

    부모의 _initialize_tiles()를 건너뛰고 LazyTileMap을 사용.
    9백만 타일을 한번에 만들지 않으므로 즉시 생성 가능.
    """

    # 채집 리젠 시간: 3일 (초)
    HARVEST_REGEN_SECONDS = 259200  # 3 * 24 * 3600

    def __init__(self, width: int, height: int, lazy_tiles: LazyTileMap):
        self._lazy_tiles = lazy_tiles
        super().__init__(width, height)
        self.tiles = lazy_tiles
        # 채집 타임스탬프: {(x,y): unix_timestamp}
        # 채집한 좌표와 시간을 기록하여 3일 후 리젠
        self.harvest_timestamps: Dict[Tuple[int, int], float] = {}
        # LazyTileMap에 채집 상태 콜백 등록
        lazy_tiles._harvest_check_fn = self._check_harvest_regen_for_chunk

    def _initialize_tiles(self):
        """타일 초기화 건너뜀 - LazyTileMap 사용"""
        pass

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_tile(self, x: int, y: int, tile_type: TileType, **kwargs):
        if 0 <= x < self.width and 0 <= y < self.height:
            tile = Tile(tile_type, x, y, **kwargs)
            tile.explored = True
            self.tiles.set_override(x, y, tile)

    def is_walkable(self, x: int, y: int) -> bool:
        tile = self.get_tile(x, y)
        return tile is not None and tile.walkable and not tile.locked

    # ── 채집 리젠 시스템 ──

    def record_harvest(self, x: int, y: int):
        """채집 타임스탬프 기록"""
        import time
        self.harvest_timestamps[(x, y)] = time.time()

    def cleanup_expired_harvests(self):
        """3일 경과한 타임스탬프 삭제 (세이브 전 호출 권장)"""
        import time
        now = time.time()
        expired = [
            key for key, ts in self.harvest_timestamps.items()
            if now - ts >= self.HARVEST_REGEN_SECONDS
        ]
        for key in expired:
            del self.harvest_timestamps[key]

    def _check_harvest_regen_for_chunk(self, chunk_key, chunk):
        """
        청크 생성 시 채집 상태 적용/리젠 처리.
        LazyTileMap._generate_chunk()에서 콜백으로 호출됨.
        """
        import time
        now = time.time()
        cx, cy = chunk_key
        x0 = cx * CHUNK_SIZE
        y0 = cy * CHUNK_SIZE

        # 이 청크 범위의 타임스탬프만 빠르게 필터
        expired_keys = []
        for (tx, ty), ts in self.harvest_timestamps.items():
            if x0 <= tx < x0 + CHUNK_SIZE and y0 <= ty < y0 + CHUNK_SIZE:
                if now - ts >= self.HARVEST_REGEN_SECONDS:
                    # 3일 경과: 리젠 완료
                    expired_keys.append((tx, ty))
                else:
                    # 아직 리젠 안됨: harvested 상태 복원
                    ly = ty - y0
                    lx = tx - x0
                    if 0 <= ly < len(chunk) and 0 <= lx < len(chunk[ly]):
                        tile = chunk[ly][lx]
                        if tile:
                            tile.mark_harvested()

        for key in expired_keys:
            del self.harvest_timestamps[key]
