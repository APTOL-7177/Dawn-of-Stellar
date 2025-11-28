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
    
    @staticmethod
    def _create_room(dungeon: DungeonMap, x1: int, y1: int, width: int, height: int):
        """방 생성 헬퍼"""
        for y in range(y1, y1 + height):
            for x in range(x1, x1 + width):
                if 0 <= x < dungeon.width and 0 <= y < dungeon.height:
                    dungeon.tiles[y][x] = Tile(TileType.FLOOR, x, y)
