"""
튜토리얼 전용 던전 - 스토리 모드용 안전한 맵

특징:
- 적이 매우 약함 (절대 못 깰 수가 없음)
- NPC 힌트 지점
- 회복 포인트
- 실패해도 바로 재시도
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from src.world.dungeon_generator import DungeonMap
from src.world.tile import Tile, TileType


@dataclass
class StoryMapMarker:
    """스토리 맵 마커 (NPC, 적, 이벤트 위치)"""
    x: int
    y: int
    marker_type: str  # "npc", "enemy", "heal", "event", "exit"
    data: dict = field(default_factory=dict)


class TutorialDungeon:
    """튜토리얼 전용 작은 던전"""

    @staticmethod
    def create_movement_tutorial() -> DungeonMap:
        """이동 튜토리얼용 던전 (작은 방)"""
        width, height = 20, 15
        dungeon = DungeonMap(width, height)

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 작은 방 만들기 (중앙)
        room_x1, room_y1 = 5, 5
        room_x2, room_y2 = 15, 10

        for y in range(room_y1, room_y2):
            for x in range(room_x1, room_x2):
                dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 시작 위치 저장
        start_x, start_y = 7, 7

        # 목표 지점 (출구)
        exit_x, exit_y = 13, 7
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        # 시작/출구 위치를 속성으로 저장
        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)

        return dungeon

    @staticmethod
    def create_combat_tutorial() -> DungeonMap:
        """전투 튜토리얼용 던전 (적 배치)"""
        width, height = 25, 18
        dungeon = DungeonMap(width, height)

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 전투 방 (더 넓게)
        room_x1, room_y1 = 5, 5
        room_x2, room_y2 = 20, 13

        for y in range(room_y1, room_y2):
            for x in range(room_x1, room_x2):
                dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 시작 위치
        start_x, start_y = 7, 9

        # 출구 (전투 후 사용)
        exit_x, exit_y = 18, 13
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)

        return dungeon

    @staticmethod
    def create_skill_tutorial() -> DungeonMap:
        """스킬 튜토리얼용 던전"""
        width, height = 30, 20
        dungeon = DungeonMap(width, height)

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 큰 전투 방
        room_x1, room_y1 = 5, 5
        room_x2, room_y2 = 25, 15

        for y in range(room_y1, room_y2):
            for x in range(room_x1, room_x2):
                dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 시작 위치
        start_x, start_y = 10, 10

        # 보물 상자 (스킬 연습용)
        dungeon.tiles[10][20] = Tile(TileType.CHEST, 20, 10)

        # 출구
        exit_x, exit_y = 22, 14
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)

        return dungeon

    # =========================================================================
    # 튜토리얼 플레이 전용 맵 (각 튜토리얼 단계별)
    # =========================================================================

    @staticmethod
    def create_interaction_tutorial() -> DungeonMap:
        """상호작용 튜토리얼용 던전 (25x15) - NPC와 오브젝트가 있는 마을 광장"""
        width, height = 25, 15
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 방 1: 시작방 (NPC 안내)
        TutorialDungeon._create_room(dungeon, 2, 2, 8, 6)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(7, 3, "npc", {
            "name": "guide", "dialogue": "Z키로 오브젝트와 상호작용하세요!"
        }))

        # 복도: 시작방 → 오브젝트 방
        for x in range(10, 14):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # 방 2: 오브젝트 방
        TutorialDungeon._create_room(dungeon, 13, 2, 10, 10)
        # CHEST
        dungeon.tiles[4][17] = Tile(TileType.CHEST, 17, 4)
        # DOOR
        dungeon.tiles[7][15] = Tile(TileType.DOOR, 15, 7)
        # HEALING_SPRING
        dungeon.tiles[9][19] = Tile(TileType.HEALING_SPRING, 19, 9)

        # 출구
        exit_x, exit_y = 21, 6
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon

    @staticmethod
    def create_atb_tutorial() -> DungeonMap:
        """ATB 튜토리얼용 던전 (25x18) - 훈련장 아레나"""
        width, height = 25, 18
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 원형 아레나
        cx, cy = 12, 9
        radius = 6
        for y in range(height):
            for x in range(width):
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if dist <= radius:
                    dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        start_x, start_y = cx, cy + radius - 2

        # NPC (ATB 설명)
        markers.append(StoryMapMarker(cx - 2, cy, "npc", {
            "name": "trainer", "dialogue": "ATB 게이지가 차면 행동할 수 있습니다!"
        }))

        # 적 스폰 1곳
        markers.append(StoryMapMarker(cx + 3, cy - 2, "enemy", {
            "name": "훈련용 인형", "hp": 25, "brv": 30, "attack": 2, "weak": True
        }))

        # 회복 포인트 2개
        heal_positions = [(cx - radius + 2, cy), (cx + radius - 2, cy)]
        for hx, hy in heal_positions:
            if 0 <= hx < width and 0 <= hy < height and dungeon.tiles[hy][hx].walkable:
                dungeon.tiles[hy][hx] = Tile(TileType.HEALING_SPRING, hx, hy)
                markers.append(StoryMapMarker(hx, hy, "heal", {"amount": 999}))

        # 출구
        exit_x, exit_y = cx, cy - radius + 1
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon

    @staticmethod
    def create_brave_tutorial() -> DungeonMap:
        """BRV/HP 튜토리얼용 던전 (25x18) - BRV/HP 연습장"""
        width, height = 25, 18
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 방 1: 연습방 (NPC + 약한 적)
        TutorialDungeon._create_room(dungeon, 2, 2, 10, 7)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(4, 3, "npc", {
            "name": "trainer", "dialogue": "BRV를 0으로 만들면 BREAK! 이후 HP 공격!"
        }))
        markers.append(StoryMapMarker(9, 5, "enemy", {
            "name": "BRV 허수아비", "hp": 10, "brv": 50, "attack": 1, "weak": True
        }))

        # 복도
        for x in range(12, 15):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # 방 2: 실전방 (강한 적)
        TutorialDungeon._create_room(dungeon, 14, 2, 9, 10)
        markers.append(StoryMapMarker(18, 6, "enemy", {
            "name": "강화 인형", "hp": 30, "brv": 80, "attack": 3, "weak": True
        }))

        # 회복 포인트
        dungeon.tiles[9][16] = Tile(TileType.HEALING_SPRING, 16, 9)
        markers.append(StoryMapMarker(16, 9, "heal", {"amount": 999}))

        # 출구
        exit_x, exit_y = 20, 10
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon

    @staticmethod
    def create_job_tutorial() -> DungeonMap:
        """직업 튜토리얼용 던전 (30x20) - 직업 전환의 전당"""
        width, height = 30, 20
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 중앙 홀
        TutorialDungeon._create_room(dungeon, 10, 6, 10, 8)

        # 중앙 ALTAR (직업 변경 제단)
        dungeon.tiles[10][15] = Tile(TileType.ALTAR, 15, 10)

        start_x, start_y = 15, 12

        # 4개 방 (상하좌우)
        # 위: 전사 훈련관
        TutorialDungeon._create_room(dungeon, 12, 1, 6, 4)
        for y in range(5, 6):
            dungeon.tiles[y][15] = Tile(TileType.FLOOR, 15, y)
        markers.append(StoryMapMarker(15, 2, "npc", {
            "name": "warrior_trainer", "dialogue": "전사는 높은 HP와 방어력으로 전열을 지키는 근접 딜러입니다."
        }))

        # 아래: 성직자 훈련관
        TutorialDungeon._create_room(dungeon, 12, 15, 6, 4)
        for y in range(14, 15):
            dungeon.tiles[y][15] = Tile(TileType.FLOOR, 15, y)
        markers.append(StoryMapMarker(15, 17, "npc", {
            "name": "cleric_trainer", "dialogue": "성직자는 치유와 정화 마법으로 파티의 생명선 역할을 합니다."
        }))

        # 왼쪽: 아크메이지 훈련관
        TutorialDungeon._create_room(dungeon, 3, 7, 6, 6)
        for x in range(9, 10):
            dungeon.tiles[10][x] = Tile(TileType.FLOOR, x, 10)
        markers.append(StoryMapMarker(5, 9, "npc", {
            "name": "archmage_trainer", "dialogue": "아크메이지는 강력한 광역 원소 마법의 대가입니다."
        }))

        # 오른쪽: 도적 훈련관
        TutorialDungeon._create_room(dungeon, 21, 7, 6, 6)
        for x in range(20, 21):
            dungeon.tiles[10][x] = Tile(TileType.FLOOR, x, 10)
        markers.append(StoryMapMarker(24, 9, "npc", {
            "name": "rogue_trainer", "dialogue": "도적은 빠른 속도와 치명타, 은신으로 적을 기습합니다."
        }))

        # 출구
        exit_x, exit_y = 15, 6
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon

    @staticmethod
    def create_cooking_tutorial() -> DungeonMap:
        """요리 튜토리얼용 던전 (30x20) - 야외 요리 캠프"""
        width, height = 30, 20
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 시작방: NPC 설명
        TutorialDungeon._create_room(dungeon, 2, 2, 8, 6)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(7, 3, "npc", {
            "name": "chef", "dialogue": "재료를 모아 요리솥에서 요리해보세요!"
        }))

        # 복도: 시작방 → 요리 구역
        for x in range(10, 14):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # 중앙 요리 구역 (넓은 야외)
        TutorialDungeon._create_room(dungeon, 13, 2, 15, 16)

        # 재료 배치 (INGREDIENT 타일)
        ingredient_positions = [
            (16, 5, "monster_meat"),   # 고기
            (20, 5, "magic_herb"),     # 약초
            (16, 10, "red_mushroom"),  # 버섯
            (20, 10, "berry"),         # 베리
        ]
        for ix, iy, ing_id in ingredient_positions:
            dungeon.tiles[iy][ix] = Tile(TileType.INGREDIENT, ix, iy)
            markers.append(StoryMapMarker(ix, iy, "ingredient", {"ingredient_id": ing_id}))

        # 요리솥 위치 (마커로 표시)
        cooking_pot_x, cooking_pot_y = 22, 8
        dungeon.tiles[cooking_pot_y][cooking_pot_x] = Tile(TileType.ALTAR, cooking_pot_x, cooking_pot_y)
        markers.append(StoryMapMarker(cooking_pot_x, cooking_pot_y, "cooking_pot", {}))

        # 회복 포인트
        dungeon.tiles[14][16] = Tile(TileType.HEALING_SPRING, 16, 14)
        markers.append(StoryMapMarker(16, 14, "heal", {"amount": 999}))

        # 출구
        exit_x, exit_y = 25, 15
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        # harvestables 리스트에 요리솥 추가
        if not hasattr(dungeon, 'harvestables'):
            dungeon.harvestables = []

        from src.gathering.harvestable import HarvestableObject, HarvestableType
        dungeon.harvestables.append(HarvestableObject(
            object_type=HarvestableType.COOKING_POT,
            x=cooking_pot_x,
            y=cooking_pot_y,
        ))

        return dungeon

    @staticmethod
    def create_alchemy_tutorial() -> DungeonMap:
        """연금술 튜토리얼용 던전 (30x20) - 연금술 실험실"""
        width, height = 30, 20
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 시작방: NPC 설명
        TutorialDungeon._create_room(dungeon, 2, 2, 8, 6)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(7, 3, "npc", {
            "name": "alchemist", "dialogue": "재료를 모아 연금술 테이블에서 제작하세요!"
        }))

        # 복도
        for x in range(10, 14):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # 실험실 방 (넓음)
        TutorialDungeon._create_room(dungeon, 13, 2, 15, 16)

        # 연금술 재료 배치
        ingredient_positions = [
            (16, 5, "magic_herb"),      # 마법 허브
            (20, 5, "blue_mushroom"),    # 푸른 버섯
            (16, 10, "red_mushroom"),    # 붉은 버섯
            (20, 10, "monster_meat"),    # 몬스터 고기
        ]
        for ix, iy, ing_id in ingredient_positions:
            dungeon.tiles[iy][ix] = Tile(TileType.INGREDIENT, ix, iy)
            markers.append(StoryMapMarker(ix, iy, "ingredient", {"ingredient_id": ing_id}))

        # 연금술 테이블 (ALTAR 타일 + alchemy_table 마커)
        alchemy_x, alchemy_y = 22, 8
        dungeon.tiles[alchemy_y][alchemy_x] = Tile(TileType.ALTAR, alchemy_x, alchemy_y)
        markers.append(StoryMapMarker(alchemy_x, alchemy_y, "alchemy_table", {}))

        # 크리스탈 (마나 회복 분위기)
        dungeon.tiles[4][25] = Tile(TileType.CRYSTAL, 25, 4)
        dungeon.tiles[14][25] = Tile(TileType.CRYSTAL, 25, 14)

        # 출구
        exit_x, exit_y = 25, 15
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon

    @staticmethod
    def create_party_tutorial() -> DungeonMap:
        """파티 관리 튜토리얼용 던전 (25x15) - 파티 관리 훈련소"""
        width, height = 25, 15
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 시작방: NPC 파티 설명
        TutorialDungeon._create_room(dungeon, 2, 2, 8, 6)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(7, 3, "npc", {
            "name": "party_guide", "dialogue": "파티원의 상태를 확인하고 인벤토리를 관리해보세요!"
        }))

        # 복도
        for x in range(10, 14):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # 관리 방: CHEST(인벤토리 체험) + HEALING_SPRING + 정보판
        TutorialDungeon._create_room(dungeon, 13, 2, 10, 10)
        dungeon.tiles[4][17] = Tile(TileType.CHEST, 17, 4)
        markers.append(StoryMapMarker(17, 4, "inventory_chest", {}))
        dungeon.tiles[8][17] = Tile(TileType.HEALING_SPRING, 17, 8)
        markers.append(StoryMapMarker(17, 8, "heal", {"amount": 999}))
        markers.append(StoryMapMarker(20, 6, "npc", {
            "name": "stats_guide", "dialogue": "캐릭터의 HP, BRV, 스킬 등을 확인할 수 있습니다."
        }))

        exit_x, exit_y = 21, 6
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers
        return dungeon

    @staticmethod
    def create_equipment_tutorial() -> DungeonMap:
        """장비/대장간 튜토리얼용 던전 (30x18) - 대장간"""
        width, height = 30, 18
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 시작방: NPC
        TutorialDungeon._create_room(dungeon, 2, 2, 8, 6)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(7, 3, "npc", {
            "name": "blacksmith", "dialogue": "장비를 주워서 착용하고, 모루에서 수리해보세요!"
        }))

        # 복도
        for x in range(10, 14):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # 장비 구역: ITEM 타일 3개 (검, 방패, 갑옷)
        TutorialDungeon._create_room(dungeon, 13, 2, 15, 14)

        item_positions = [
            (16, 5, "sword"),
            (20, 5, "shield"),
            (16, 9, "armor"),
        ]
        for ix, iy, item_type in item_positions:
            dungeon.tiles[iy][ix] = Tile(TileType.ITEM, ix, iy)
            markers.append(StoryMapMarker(ix, iy, "equipment_item", {"item_type": item_type}))

        # 모루 (대장간)
        anvil_x, anvil_y = 22, 8
        dungeon.tiles[anvil_y][anvil_x] = Tile(TileType.ANVIL, anvil_x, anvil_y)
        markers.append(StoryMapMarker(anvil_x, anvil_y, "anvil", {}))

        # 인벤토리 상자 (인벤토리 열기 체험)
        dungeon.tiles[12][18] = Tile(TileType.CHEST, 18, 12)
        markers.append(StoryMapMarker(18, 12, "inventory_chest", {}))

        exit_x, exit_y = 25, 13
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers
        return dungeon

    @staticmethod
    def create_dungeon_exploration_tutorial() -> DungeonMap:
        """던전 탐험 튜토리얼용 (35x22) - 미니 던전 종합 실습"""
        width, height = 35, 22
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 방 1: 시작방
        TutorialDungeon._create_room(dungeon, 2, 2, 8, 6)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(7, 3, "npc", {
            "name": "selena", "dialogue": "모든 것을 활용해 던전을 탐험해보세요!"
        }))

        # 복도 1 (오른쪽)
        for x in range(10, 15):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)
        dungeon.tiles[5][12] = Tile(TileType.DOOR, 12, 5)

        # 방 2: 보물방
        TutorialDungeon._create_room(dungeon, 14, 2, 10, 8)
        dungeon.tiles[4][18] = Tile(TileType.CHEST, 18, 4)
        dungeon.tiles[6][20] = Tile(TileType.CHEST, 20, 6)
        markers.append(StoryMapMarker(18, 4, "chest", {}))
        markers.append(StoryMapMarker(20, 6, "chest", {}))
        dungeon.tiles[7][16] = Tile(TileType.TRAP, 16, 7)

        # 복도 2 (아래쪽)
        for y in range(10, 14):
            dungeon.tiles[y][18] = Tile(TileType.FLOOR, 18, y)

        # 방 3: 회복 + 재료
        TutorialDungeon._create_room(dungeon, 13, 13, 12, 7)
        dungeon.tiles[15][16] = Tile(TileType.HEALING_SPRING, 16, 15)
        markers.append(StoryMapMarker(16, 15, "heal", {"amount": 999}))
        dungeon.tiles[16][20] = Tile(TileType.INGREDIENT, 20, 16)
        markers.append(StoryMapMarker(20, 16, "ingredient", {"ingredient_id": "magic_herb"}))
        dungeon.tiles[17][18] = Tile(TileType.CRYSTAL, 18, 17)

        # 복도 3 (오른쪽으로)
        for x in range(25, 30):
            dungeon.tiles[16][x] = Tile(TileType.FLOOR, x, 16)

        # 방 4: 출구방
        TutorialDungeon._create_room(dungeon, 25, 14, 8, 6)
        markers.append(StoryMapMarker(28, 15, "npc", {
            "name": "karnos", "dialogue": "잘했다! 이제 진짜 모험을 시작해라."
        }))

        exit_x, exit_y = 30, 19
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers
        return dungeon

    # =========================================================================
    # 스토리 전용 던전 (실전처럼 플레이, 하지만 절대 못깰 수 없음)
    # =========================================================================

    @staticmethod
    def create_story_dungeon() -> Tuple[DungeonMap, List[StoryMapMarker]]:
        """
        스토리 튜토리얼 전용 던전
        
        실제 게임과 똑같이 탐험하지만:
        - 적이 매우 약함
        - 회복 포인트 많음
        - NPC가 도움
        
        Returns:
            (던전 맵, 마커 리스트)
        """
        width, height = 40, 25
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []
        
        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False
        
        # ===== 방 1: 시작 방 (NPC 셀레나) =====
        TutorialDungeon._create_room(dungeon, 2, 2, 10, 8)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(8, 4, "npc", {"name": "selena", "dialogue": "여기서 시작이에요!"}))
        
        # ===== 복도 1: 시작방 → 전투방 =====
        for x in range(10, 15):
            dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)
        
        # ===== 방 2: 첫 전투 방 (약한 적) =====
        TutorialDungeon._create_room(dungeon, 14, 2, 12, 10)
        markers.append(StoryMapMarker(19, 6, "enemy", {
            "name": "시간 파편",
            "hp": 20,
            "brv": 30,
            "attack": 3,
            "weak": True
        }))
        markers.append(StoryMapMarker(16, 8, "heal", {"amount": 999}))  # 완전 회복
        
        # ===== 복도 2: 전투방 → 보스방 =====
        for y in range(10, 15):
            dungeon.tiles[y][20] = Tile(TileType.FLOOR, 20, y)
        
        # ===== 방 3: 미니 보스 방 =====
        TutorialDungeon._create_room(dungeon, 15, 14, 12, 8)
        markers.append(StoryMapMarker(21, 17, "enemy", {
            "name": "왜곡된 기억",
            "hp": 50,
            "brv": 50,
            "attack": 5,
            "boss": True,
            "weak": True  # 그래도 약함
        }))
        markers.append(StoryMapMarker(17, 19, "heal", {"amount": 999}))
        markers.append(StoryMapMarker(18, 15, "npc", {"name": "karnos", "dialogue": "잘하고 있다!"}))
        
        # ===== 출구 =====
        exit_x, exit_y = 24, 20
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)
        markers.append(StoryMapMarker(exit_x, exit_y, "exit", {}))
        
        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers  # 마커 저장
        
        return dungeon, markers
    
    @staticmethod
    def create_story_combat_arena() -> Tuple[DungeonMap, List[StoryMapMarker]]:
        """
        전투 연습 아레나
        
        적과 반복 전투 가능, 회복 포인트 풍부
        """
        width, height = 30, 20
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []
        
        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False
        
        # 큰 원형 아레나
        center_x, center_y = 15, 10
        radius = 8
        
        for y in range(height):
            for x in range(width):
                dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                if dist <= radius:
                    dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)
        
        # 시작 위치 (아레나 입구)
        start_x, start_y = center_x, center_y + radius - 2
        
        # NPC (카르노스 - 전투 마스터)
        markers.append(StoryMapMarker(center_x - 3, center_y, "npc", {
            "name": "karnos",
            "dialogue": "여기서 전투를 연습해라."
        }))
        
        # 적 스폰 포인트들 (약한 적)
        enemy_positions = [
            (center_x + 3, center_y - 2),
            (center_x - 2, center_y - 3),
            (center_x + 4, center_y + 2),
        ]
        for i, (ex, ey) in enumerate(enemy_positions):
            markers.append(StoryMapMarker(ex, ey, "enemy", {
                "name": f"훈련용 인형 {i+1}",
                "hp": 30,
                "brv": 40,
                "attack": 2,
                "weak": True,
                "respawn": True  # 재등장
            }))
        
        # 회복 포인트들
        heal_positions = [
            (center_x, center_y - radius + 2),
            (center_x - radius + 2, center_y),
            (center_x + radius - 2, center_y),
        ]
        for hx, hy in heal_positions:
            if dungeon.tiles[hy][hx].walkable:
                markers.append(StoryMapMarker(hx, hy, "heal", {"amount": 999}))
        
        # 출구 (위쪽)
        exit_x, exit_y = center_x, center_y - radius + 1
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)
        markers.append(StoryMapMarker(exit_x, exit_y, "exit", {}))
        
        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers
        
        return dungeon, markers
    
    # =========================================================================
    # 프롤로그/스토리 커스텀 맵 (테마별)
    # =========================================================================

    @staticmethod
    def create_prologue_awakening() -> "Tuple[DungeonMap, List[StoryMapMarker]]":
        """
        프롤로그: 시공의 틈새 (25x20)

        어둡고 신비로운 차원의 틈새.
        좁은 시작 공간 → 빛나는 복도 → 넓은 출구 방
        """
        width, height = 25, 20
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 시작 방 (좁은 공간, 5x4)
        TutorialDungeon._create_room(dungeon, 2, 2, 5, 4)
        start_x, start_y = 4, 4
        # 시작점 크리스탈
        dungeon.tiles[3][3] = Tile(TileType.CRYSTAL, 3, 3)

        # 복도 (좁음 → 점차 넓어짐)
        for x in range(7, 14):
            dungeon.tiles[4][x] = Tile(TileType.FLOOR, x, 4)
            if x >= 10:
                dungeon.tiles[3][x] = Tile(TileType.FLOOR, x, 3)
                dungeon.tiles[5][x] = Tile(TileType.FLOOR, x, 5)

        # NPC 셀레나 (복도 중간)
        markers.append(StoryMapMarker(10, 4, "npc", {"name": "selena", "dialogue": "이쪽으로 오세요."}))

        # 출구 방 (넓은 공간, 9x8)
        TutorialDungeon._create_room(dungeon, 14, 1, 9, 10)

        # 힐링 스프링 (출구 전)
        dungeon.tiles[5][18] = Tile(TileType.HEALING_SPRING, 18, 5)
        markers.append(StoryMapMarker(18, 5, "heal", {"amount": 999}))

        # 출구
        exit_x, exit_y = 20, 5
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)
        markers.append(StoryMapMarker(exit_x, exit_y, "exit", {}))

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon, markers

    @staticmethod
    def create_combat_training_arena() -> "Tuple[DungeonMap, List[StoryMapMarker]]":
        """
        전투 훈련: 고대의 훈련장 (30x22)

        원형 중앙 아레나 + 4개 모서리 기둥, 관전석 느낌 벽 패턴
        """
        width, height = 30, 22
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # 원형 아레나
        cx, cy = 15, 11
        radius = 8
        for y in range(height):
            for x in range(width):
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if dist <= radius:
                    dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)

        # 4 모서리 기둥 (벽으로 되돌림)
        pillar_offsets = [(-4, -4), (4, -4), (-4, 4), (4, 4)]
        for ox, oy in pillar_offsets:
            px_, py_ = cx + ox, cy + oy
            if 0 <= px_ < width and 0 <= py_ < height:
                dungeon.tiles[py_][px_] = Tile(TileType.WALL, px_, py_)
                dungeon.tiles[py_][px_].walkable = False
                dungeon.tiles[py_][px_].transparent = False

        # 중앙 제단
        dungeon.tiles[cy][cx] = Tile(TileType.ALTAR, cx, cy)

        # 시작 위치 (아레나 아래)
        start_x, start_y = cx, cy + radius - 2

        # NPC 카르노스
        markers.append(StoryMapMarker(cx - 3, cy, "npc", {
            "name": "karnos", "dialogue": "여기서 전투를 연습해라."
        }))

        # 적 스폰 포인트 (2곳)
        markers.append(StoryMapMarker(cx + 3, cy - 2, "enemy_spawn", {
            "name": "훈련용 인형", "weak": True
        }))
        markers.append(StoryMapMarker(cx - 2, cy - 3, "enemy_spawn", {
            "name": "훈련용 인형", "weak": True
        }))

        # 힐링 스프링 (양쪽)
        hl = cx - radius + 2
        hr = cx + radius - 2
        dungeon.tiles[cy][hl] = Tile(TileType.HEALING_SPRING, hl, cy)
        dungeon.tiles[cy][hr] = Tile(TileType.HEALING_SPRING, hr, cy)
        markers.append(StoryMapMarker(hl, cy, "heal", {"amount": 999}))
        markers.append(StoryMapMarker(hr, cy, "heal", {"amount": 999}))

        # 출구 (위쪽)
        exit_x, exit_y = cx, cy - radius + 1
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)
        markers.append(StoryMapMarker(exit_x, exit_y, "exit", {}))

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon, markers

    @staticmethod
    def create_dungeon_basics() -> "Tuple[DungeonMap, List[StoryMapMarker]]":
        """
        던전 기초: 붕괴된 유적 (40x25)

        시공 교란으로 반쯤 무너진 고대 유적.
        3개 방 + 2개 복도 (문 포함)
        방1: 입구 (NPC 셀레나)
        방2: 보물방 (CHEST + TRAP)
        방3: 출구방 (HEALING_SPRING + STAIRS_DOWN)
        """
        width, height = 40, 25
        dungeon = DungeonMap(width, height)
        markers: List[StoryMapMarker] = []

        # 전체를 벽으로
        for y in range(height):
            for x in range(width):
                dungeon.tiles[y][x] = Tile(TileType.WALL, x, y)
                dungeon.tiles[y][x].walkable = False
                dungeon.tiles[y][x].transparent = False

        # ===== 방 1: 입구 (10x8) =====
        TutorialDungeon._create_room(dungeon, 2, 2, 10, 8)
        start_x, start_y = 5, 5
        markers.append(StoryMapMarker(8, 4, "npc", {
            "name": "selena", "dialogue": "이 유적을 탐험해봐요!"
        }))

        # ===== 복도 1: 방1 → 방2 (문 포함) =====
        for x in range(12, 18):
            dungeon.tiles[6][x] = Tile(TileType.FLOOR, x, 6)
        dungeon.tiles[6][14] = Tile(TileType.DOOR, 14, 6)

        # ===== 방 2: 보물방 (10x8) =====
        TutorialDungeon._create_room(dungeon, 18, 2, 10, 8)
        # 보물 상자
        dungeon.tiles[4][23] = Tile(TileType.CHEST, 23, 4)
        markers.append(StoryMapMarker(23, 4, "chest", {}))
        # 함정 하나
        dungeon.tiles[7][21] = Tile(TileType.TRAP, 21, 7)
        markers.append(StoryMapMarker(21, 7, "trap", {}))

        # ===== 복도 2: 방2 → 방3 (아래로, 문 포함) =====
        for y in range(10, 16):
            dungeon.tiles[y][23] = Tile(TileType.FLOOR, 23, y)
        dungeon.tiles[12][23] = Tile(TileType.DOOR, 23, 12)

        # ===== 방 3: 출구방 (12x7) =====
        TutorialDungeon._create_room(dungeon, 17, 16, 12, 7)
        # 힐링 스프링
        dungeon.tiles[19][20] = Tile(TileType.HEALING_SPRING, 20, 19)
        markers.append(StoryMapMarker(20, 19, "heal", {"amount": 999}))
        # 출구
        exit_x, exit_y = 25, 19
        dungeon.tiles[exit_y][exit_x] = Tile(TileType.STAIRS_DOWN, exit_x, exit_y)
        dungeon.stairs_down = (exit_x, exit_y)
        markers.append(StoryMapMarker(exit_x, exit_y, "exit", {}))

        dungeon.start_pos = (start_x, start_y)
        dungeon.exit_pos = (exit_x, exit_y)
        dungeon.story_markers = markers

        return dungeon, markers

    @staticmethod
    def _create_room(dungeon: DungeonMap, x1: int, y1: int, width: int, height: int):
        """방 생성 헬퍼"""
        for y in range(y1, y1 + height):
            for x in range(x1, x1 + width):
                if 0 <= x < dungeon.width and 0 <= y < dungeon.height:
                    dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)
