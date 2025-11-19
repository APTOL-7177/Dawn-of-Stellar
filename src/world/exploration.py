"""
월드 탐험 시스템

플레이어가 던전을 돌아다니며 적과 조우하고 기믹과 상호작용
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random

from src.world.dungeon_generator import DungeonMap
from src.world.tile import Tile, TileType
from src.world.fov import FOVSystem
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.WORLD)


class ExplorationEvent(Enum):
    """탐험 이벤트"""
    NONE = "none"
    COMBAT = "combat"
    ITEM_FOUND = "item_found"
    TRAP_TRIGGERED = "trap_triggered"
    TELEPORT = "teleport"
    HEAL = "heal"
    STAIRS_UP = "stairs_up"
    STAIRS_DOWN = "stairs_down"
    LOCKED_DOOR = "locked_door"
    KEY_FOUND = "key_found"
    CHEST_FOUND = "chest_found"
    BOSS_ROOM = "boss_room"
    PUZZLE_SOLVED = "puzzle_solved"
    SWITCH_ACTIVATED = "switch_activated"
    NPC_INTERACTION = "npc_interaction"


@dataclass
class Enemy:
    """적 엔티티"""
    x: int
    y: int
    level: int
    name: str = "적"  # 적 이름
    is_boss: bool = False

    # AI 상태
    spawn_x: int = None  # 생성 위치 X
    spawn_y: int = None  # 생성 위치 Y
    is_chasing: bool = False  # 추적 중
    chase_turns: int = 0  # 추적 턴 수
    max_chase_turns: int = 15  # 최대 추적 턴
    max_chase_distance: int = 15  # 최대 추적 거리 (이 거리 이상 벌어지면 포기)
    detection_range: int = 5  # 플레이어 감지 거리

    def __post_init__(self):
        if self.spawn_x is None:
            self.spawn_x = self.x
        if self.spawn_y is None:
            self.spawn_y = self.y


@dataclass
class Player:
    """플레이어 정보"""
    x: int
    y: int
    party: List[Any]  # 파티원 리스트
    inventory: List[str] = None  # 아이템
    keys: List[str] = None  # 열쇠
    fov_radius: int = 3  # 시야 반지름

    def __post_init__(self):
        if self.inventory is None:
            self.inventory = []
        if self.keys is None:
            self.keys = []


@dataclass
class ExplorationResult:
    """탐험 결과"""
    success: bool
    event: ExplorationEvent
    message: str = ""
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class ExplorationSystem:
    """탐험 시스템"""

    def __init__(self, dungeon: DungeonMap, party: List[Any], floor_number: int = 1, inventory=None, game_stats=None):
        self.dungeon = dungeon

        # 플레이어 스폰 위치 결정 (계단이 아닌 첫 번째 방의 안전한 위치)
        spawn_x, spawn_y = 5, 5  # 기본값
        if dungeon.rooms:
            first_room = dungeon.rooms[0]
            # 방의 중심에서 약간 떨어진 랜덤 위치
            import random
            spawn_x = first_room.x + random.randint(2, max(2, first_room.width - 3))
            spawn_y = first_room.y + random.randint(2, max(2, first_room.height - 3))

            # 계단과 겹치지 않도록 확인
            if dungeon.stairs_up and (spawn_x, spawn_y) == dungeon.stairs_up:
                spawn_x += 1
            if dungeon.stairs_down and (spawn_x, spawn_y) == dungeon.stairs_down:
                spawn_x += 1

        self.player = Player(
            x=spawn_x,
            y=spawn_y,
            party=party
        )
        self.fov_system = FOVSystem(default_radius=3)
        self.floor_number = floor_number
        self.explored_tiles = set()
        self.enemies: List[Enemy] = []  # 적 리스트
        self.inventory = inventory  # 인벤토리 추가

        # 게임 통계 (로그라이크 정산용)
        self.game_stats = game_stats if game_stats is not None else {
            "enemies_defeated": 0,
            "max_floor_reached": floor_number,
            "total_gold_earned": 0,
            "total_exp_earned": 0,
            "save_slot": None
        }

        # 인벤토리 초기화 확인 로그
        logger.error(f"[INIT] ExplorationSystem 초기화 - 인벤토리: {self.inventory}")
        if self.inventory is not None:
            logger.error(f"[INIT] 인벤토리 타입: {type(self.inventory)}, 슬롯: {len(self.inventory.slots)}, 골드: {self.inventory.gold}G")
        else:
            logger.error(f"[INIT] ⚠️ 인벤토리가 None입니다!")

        # 채집 오브젝트 확인
        harvestables_count = len(dungeon.harvestables) if hasattr(dungeon, 'harvestables') else 0
        logger.warning(f"[INIT] 던전 채집 오브젝트: {harvestables_count}개")
        if hasattr(dungeon, 'harvestables') and dungeon.harvestables:
            for i, h in enumerate(dungeon.harvestables[:3]):  # 처음 3개만 로깅
                logger.warning(f"[INIT]   {i+1}. {h.object_type.value} at ({h.x}, {h.y}), harvested={h.harvested}")

        # 적 배치
        self._spawn_enemies()

        # 초기 FOV 계산
        self.update_fov()

        logger.info(f"탐험 시작: 층 {self.floor_number}, 위치 ({self.player.x}, {self.player.y})")

    def update_fov(self):
        """시야 업데이트"""
        # 이전 visible 초기화
        self.fov_system.clear_visibility(self.dungeon)

        # FOV 계산
        visible = self.fov_system.compute_fov(
            self.dungeon,
            self.player.x,
            self.player.y,
            self.player.fov_radius
        )

        # 탐험한 타일 누적
        self.explored_tiles.update(visible)

    def can_move(self, dx: int, dy: int) -> bool:
        """이동 가능 여부"""
        new_x = self.player.x + dx
        new_y = self.player.y + dy

        return self.dungeon.is_walkable(new_x, new_y)

    def move_player(self, dx: int, dy: int) -> ExplorationResult:
        """
        플레이어 이동

        Args:
            dx: X 방향 이동량
            dy: Y 방향 이동량

        Returns:
            ExplorationResult
        """
        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # 이동 가능 체크
        if not self.dungeon.is_walkable(new_x, new_y):
            tile = self.dungeon.get_tile(new_x, new_y)
            if tile and tile.tile_type == TileType.LOCKED_DOOR:
                return self._handle_locked_door(tile)
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이동할 수 없습니다"
            )

        # 적과의 충돌 확인 (이동 전에!)
        enemy = self.get_enemy_at(new_x, new_y)
        logger.warning(f"[DEBUG] 적 충돌 체크 at ({new_x}, {new_y}): enemy={enemy is not None}")
        if enemy:
            logger.warning(f"[DEBUG] 적 발견! 전투 트리거 at ({enemy.x}, {enemy.y})")
            # 플레이어는 이동하지 않고 전투만 트리거
            combat_result = self._trigger_combat_with_enemy(enemy)
            logger.warning(f"[DEBUG] 전투 결과: event={combat_result.event}")
            return combat_result

        # 이동
        self.player.x = new_x
        self.player.y = new_y

        # FOV 업데이트
        self.update_fov()

        # 타일 이벤트 체크
        tile = self.dungeon.get_tile(new_x, new_y)
        result = self._check_tile_event(tile)

        # 플레이어가 움직인 후 모든 적 움직임
        self._move_all_enemies()

        # 적 움직임 후 플레이어 위치에 적이 있는지 다시 체크
        enemy_at_player = self.get_enemy_at(self.player.x, self.player.y)
        if enemy_at_player:
            logger.warning(f"[DEBUG] 적이 플레이어에게 접근! 전투 시작")
            return self._trigger_combat_with_enemy(enemy_at_player)

        return result

    def _check_tile_event(self, tile: Tile) -> ExplorationResult:
        """타일 이벤트 확인"""
        if tile.tile_type == TileType.TRAP:
            return self._handle_trap(tile)

        elif tile.tile_type == TileType.TELEPORTER:
            return self._handle_teleporter(tile)

        elif tile.tile_type == TileType.LAVA:
            return self._handle_lava(tile)

        elif tile.tile_type == TileType.HEALING_SPRING:
            return self._handle_healing_spring(tile)

        elif tile.tile_type == TileType.STAIRS_UP:
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.STAIRS_UP,
                message="위층으로 올라가는 계단입니다"
            )

        elif tile.tile_type == TileType.STAIRS_DOWN:
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.STAIRS_DOWN,
                message="아래층으로 내려가는 계단입니다"
            )

        elif tile.tile_type == TileType.CHEST:
            return self._handle_chest(tile)

        elif tile.tile_type == TileType.KEY:
            return self._handle_key(tile)

        elif tile.tile_type == TileType.ITEM:
            return self._handle_item(tile)

        elif tile.tile_type == TileType.BOSS_ROOM:
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.BOSS_ROOM,
                message="⚠ 보스의 기운이 느껴집니다..."
            )

        elif tile.tile_type == TileType.PUZZLE:
            return self._handle_puzzle(tile)

        elif tile.tile_type == TileType.SWITCH:
            return self._handle_switch(tile)

        elif tile.tile_type == TileType.PRESSURE_PLATE:
            return self._handle_pressure_plate(tile)

        elif tile.tile_type == TileType.LEVER:
            return self._handle_lever(tile)

        elif tile.tile_type == TileType.NPC:
            return self._handle_npc(tile)

        elif tile.tile_type == TileType.SHOP:
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NONE,
                message="상점입니다. (상호작용 미구현)"
            )

        elif tile.tile_type == TileType.ALTAR:
            return self._handle_altar(tile)

        elif tile.tile_type == TileType.SHRINE:
            return self._handle_shrine(tile)

        elif tile.tile_type == TileType.PORTAL:
            return self._handle_portal(tile)

        elif tile.tile_type == TileType.SPIKE_TRAP:
            return self._handle_trap(tile)

        elif tile.tile_type == TileType.POISON_GAS:
            return self._handle_poison_gas(tile)

        elif tile.tile_type == TileType.ICE_FLOOR:
            return self._handle_ice_floor(tile)

        elif tile.tile_type == TileType.FIRE_TRAP:
            return self._handle_trap(tile)

        elif tile.tile_type == TileType.SECRET_DOOR:
            return self._handle_secret_door(tile)

        elif tile.tile_type == TileType.BUTTON:
            return self._handle_button(tile)

        elif tile.tile_type == TileType.PEDESTAL:
            return self._handle_pedestal(tile)

        elif tile.tile_type == TileType.CRYSTAL:
            return self._handle_crystal(tile)

        elif tile.tile_type == TileType.MANA_WELL:
            return self._handle_mana_well(tile)

        elif tile.tile_type == TileType.TREASURE_MAP:
            return self._handle_treasure_map(tile)

        elif tile.tile_type == TileType.RIDDLE_STONE:
            return self._handle_riddle_stone(tile)

        elif tile.tile_type == TileType.MAGIC_CIRCLE:
            return self._handle_magic_circle(tile)

        elif tile.tile_type == TileType.SACRIFICE_ALTAR:
            return self._handle_sacrifice_altar(tile)

        # 랜덤 전투 조우 제거 (이제 적 엔티티와의 충돌로만 전투 발생)

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message=""
        )

    def _handle_trap(self, tile: Tile) -> ExplorationResult:
        """함정 처리"""
        damage = tile.trap_damage

        # 파티원들에게 데미지
        for member in self.player.party:
            if hasattr(member, 'take_damage'):
                member.take_damage(damage)

        logger.info(f"함정 발동! 파티 전체 {damage} 데미지")

        # 타일 제거 (일회용)
        tile.tile_type = TileType.FLOOR
        tile.trap_damage = 0

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.TRAP_TRIGGERED,
            message=f"💥 함정! 파티 전체 {damage} 데미지!",
            data={"damage": damage}
        )

    def _handle_teleporter(self, tile: Tile) -> ExplorationResult:
        """텔레포터 처리"""
        if tile.teleport_target:
            self.player.x, self.player.y = tile.teleport_target
            self.update_fov()

            logger.info(f"텔레포트: {tile.teleport_target}")

            return ExplorationResult(
                success=True,
                event=ExplorationEvent.TELEPORT,
                message="🌀 텔레포트!",
                data={"target": tile.teleport_target}
            )

        return ExplorationResult(success=True, event=ExplorationEvent.NONE)

    def _handle_lava(self, tile: Tile) -> ExplorationResult:
        """용암 처리"""
        damage = tile.trap_damage

        for member in self.player.party:
            if hasattr(member, 'take_damage'):
                member.take_damage(damage)

        logger.info(f"용암 데미지: {damage}")

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.TRAP_TRIGGERED,
            message=f"🔥 뜨거워! {damage} 화상 데미지!",
            data={"damage": damage}
        )

    def _handle_healing_spring(self, tile: Tile) -> ExplorationResult:
        """치유의 샘 처리"""
        heal_amount = 50

        for member in self.player.party:
            if hasattr(member, 'heal'):
                member.heal(heal_amount)

        logger.info(f"치유의 샘: {heal_amount} HP 회복")

        # 일회용
        tile.tile_type = TileType.FLOOR

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.HEAL,
            message=f"💧 치유의 샘! 파티 전체 {heal_amount} HP 회복!",
            data={"heal": heal_amount}
        )

    def _handle_chest(self, tile: Tile) -> ExplorationResult:
        """보물상자 처리"""
        from src.equipment.item_system import ItemGenerator
        import random

        # 보물상자: 50% 확률로 전투용 아이템, 50% 확률로 일반 아이템
        if random.random() < 0.5:
            # 전투용 아이템 생성
            from src.combat.experience_system import RewardCalculator
            item = RewardCalculator._generate_combat_consumable_drop()
        else:
            # 랜덤 아이템 생성 (보물상자는 보스 드롭 취급)
            item = ItemGenerator.create_random_drop(self.floor_number, boss_drop=True)

        # 디버그 로그
        logger.warning(f"[CHEST] 보물상자 처리 시작: {item.name}")
        logger.warning(f"[CHEST] 인벤토리 존재 여부: {self.inventory is not None}")
        if self.inventory is not None:
            logger.warning(f"[CHEST] 인벤토리 슬롯 수: {len(self.inventory.slots)}")
            logger.warning(f"[CHEST] 현재 무게: {self.inventory.current_weight}kg / {self.inventory.max_weight}kg")

        # 인벤토리에 추가
        if self.inventory is not None:
            success = self.inventory.add_item(item)
            logger.warning(f"[CHEST] add_item 결과: {success}")
            if not success:
                logger.warning(f"인벤토리 가득 참! {item.name} 버려짐")
                return ExplorationResult(
                    success=False,
                    event=ExplorationEvent.NONE,
                    message=f"📦 보물상자 발견! 하지만 인벤토리가 가득 차서 {item.name}을(를) 버렸다..."
                )
        else:
            logger.error(f"[CHEST] 인벤토리가 None입니다!")

        logger.info(f"보물상자 획득: {item.name}")

        # 상자 제거
        tile.tile_type = TileType.FLOOR
        tile.loot_id = None

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.CHEST_FOUND,
            message=f"📦 보물상자 발견! {item.name} 획득!",
            data={"item": item}
        )

    def _handle_item(self, tile: Tile) -> ExplorationResult:
        """떨어진 아이템 처리"""
        from src.equipment.item_system import ItemGenerator
        from src.combat.experience_system import RewardCalculator
        import random

        # 필드 아이템: 30% 확률로 전투용 아이템, 70% 확률로 일반 아이템
        if random.random() < 0.3:
            # 전투용 아이템 생성
            item = RewardCalculator._generate_combat_consumable_drop()
        else:
            # 랜덤 아이템 생성 (일반 드롭)
            item = ItemGenerator.create_random_drop(self.floor_number, boss_drop=False)

        # 디버그 로그
        logger.warning(f"[ITEM] 아이템 처리 시작: {item.name}")
        logger.warning(f"[ITEM] 인벤토리 존재 여부: {self.inventory is not None}")
        if self.inventory is not None:
            logger.warning(f"[ITEM] 인벤토리 슬롯 수: {len(self.inventory.slots)}")
            logger.warning(f"[ITEM] 현재 무게: {self.inventory.current_weight}kg / {self.inventory.max_weight}kg")

        # 인벤토리에 추가
        if self.inventory is None:
            logger.error(f"[ITEM] 인벤토리가 None입니다!")
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message=f"✨ 아이템 발견! 하지만 인벤토리가 없어서 {item.name}을(를) 가져갈 수 없다..."
            )

        success = self.inventory.add_item(item)
        logger.warning(f"[ITEM] add_item 결과: {success}")

        if not success:
            logger.warning(f"인벤토리 가득 참! {item.name} 버려짐")
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message=f"✨ 아이템 발견! 하지만 인벤토리가 가득 차서 {item.name}을(를) 버렸다..."
            )

        # 성공: 아이템 획득
        logger.info(f"아이템 획득: {item.name}")

        # 아이템 제거
        tile.tile_type = TileType.FLOOR
        tile.loot_id = None

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.ITEM_FOUND,
            message=f"✨ 아이템 발견! {item.name} 획득!",
            data={"item": item}
        )

    def _handle_key(self, tile: Tile) -> ExplorationResult:
        """열쇠 처리"""
        key_id = tile.key_id or "key_unknown"
        self.player.keys.append(key_id)

        logger.info(f"열쇠 획득: {key_id}")

        # 열쇠 제거
        tile.tile_type = TileType.FLOOR
        tile.key_id = None

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.KEY_FOUND,
            message=f"열쇠 발견! {key_id} 획득!",
            data={"key": key_id}
        )

    def _handle_locked_door(self, tile: Tile) -> ExplorationResult:
        """잠긴 문 처리"""
        key_id = tile.key_id

        if key_id in self.player.keys:
            # 열쇠가 있으면 문 열기
            tile.unlock()
            logger.info(f"문 잠금 해제: {key_id}")

            return ExplorationResult(
                success=True,
                event=ExplorationEvent.LOCKED_DOOR,
                message=f"🔓 문을 열었습니다! ({key_id})"
            )
        else:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.LOCKED_DOOR,
                message=f"🔒 잠겨있습니다. {key_id}가 필요합니다.",
                data={"required_key": key_id}
            )

    def _trigger_combat(self) -> ExplorationResult:
        """전투 조우 (랜덤)"""
        # Config에서 적 수 범위 가져오기
        from src.core.config import get_config
        import random
        config = get_config()
        min_enemies = config.get("world.dungeon.enemy_count.min_enemies", 2)
        max_enemies = config.get("world.dungeon.enemy_count.max_enemies", 4)

        # 랜덤하게 적 수 결정 (2-4마리)
        num_enemies = random.randint(min_enemies, max_enemies)

        logger.info(f"전투 조우! 적 {num_enemies}명")

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.COMBAT,
            message=f"⚔ 적 출현! {num_enemies}마리!",
            data={"num_enemies": num_enemies, "floor": self.floor_number}
        )

    def _trigger_combat_with_enemy(self, enemy: Enemy) -> ExplorationResult:
        """적 엔티티와의 전투"""
        # 충돌한 적을 기준으로 주변 적들도 수집 (전투 후 제거용)
        combat_enemies = [enemy]

        # 주변 가까운 거리(3칸) 내의 적들 수집
        combat_range = 3
        for other_enemy in self.enemies:
            if other_enemy == enemy:
                continue

            distance = abs(other_enemy.x - enemy.x) + abs(other_enemy.y - enemy.y)
            if distance <= combat_range:
                combat_enemies.append(other_enemy)
                logger.warning(f"[DEBUG] 주변 적 추가: ({other_enemy.x}, {other_enemy.y}), 거리={distance}")

        logger.warning(f"[DEBUG] 맵 엔티티: {len(combat_enemies)}마리")

        # Config에서 적 수 범위 가져오기
        from src.core.config import get_config
        config = get_config()
        min_enemies = config.get("world.dungeon.enemy_count.min_enemies", 2)
        max_enemies = config.get("world.dungeon.enemy_count.max_enemies", 4)

        # 실제 전투 적 수는 항상 config 기준 (2-4마리)
        # 맵 엔티티 수와 무관하게 추가 적이 소환됨
        num_enemies = random.randint(min_enemies, max_enemies)

        has_boss = any(e.is_boss for e in combat_enemies)

        logger.warning(f"[DEBUG] 전투 생성: 맵 엔티티 {len(combat_enemies)}마리 → 실제 전투 {num_enemies}마리 (추가 적 소환)")
        logger.info(f"적과 조우! {num_enemies}마리 (레벨 {enemy.level})")

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.COMBAT,
            message=f"⚔ 적과 조우! {num_enemies}마리" + (" (보스 포함!)" if has_boss else ""),
            data={
                "num_enemies": num_enemies,
                "floor": self.floor_number,
                "enemy_level": enemy.level,  # 조우한 적의 레벨 전달
                "is_boss": has_boss,
                "enemies": combat_enemies  # 전투 승리 후 제거할 적 엔티티 전달 (실제 참여한 적들)
            }
        )

    def descend_floor(self):
        """다음 층으로"""
        self.floor_number += 1
        logger.info(f"층 이동: {self.floor_number}층")

        # 새 던전 생성 필요
        # (이건 외부에서 처리)

    def ascend_floor(self):
        """이전 층으로"""
        if self.floor_number > 1:
            self.floor_number -= 1
            logger.info(f"층 이동: {self.floor_number}층")

    def _spawn_enemies(self):
        """적 배치"""
        # 층 수에 따라 적 수 결정 (4-15마리로 감소)
        base_enemies = 4
        additional = self.floor_number * 1
        num_enemies = min(15, base_enemies + additional)

        # 플레이어 시작 위치 주변을 제외한 바닥 타일에 적 배치
        possible_positions = []
        for x in range(self.dungeon.width):
            for y in range(self.dungeon.height):
                tile = self.dungeon.get_tile(x, y)
                if (tile and tile.tile_type == TileType.FLOOR and
                    abs(x - self.player.x) > 3 and abs(y - self.player.y) > 3):
                    possible_positions.append((x, y))

        # 랜덤하게 적 배치
        if possible_positions:
            spawn_positions = random.sample(possible_positions, min(num_enemies, len(possible_positions)))
            for x, y in spawn_positions:
                enemy = Enemy(x=x, y=y, level=self.floor_number)
                self.enemies.append(enemy)

        logger.warning(f"[DEBUG] 적 {len(self.enemies)}마리 배치 완료")
        for i, enemy in enumerate(self.enemies[:5]):  # 처음 5마리만 로그
            logger.warning(f"[DEBUG] 적 {i+1}: 위치 ({enemy.x}, {enemy.y})")

    def get_enemy_at(self, x: int, y: int) -> Optional[Enemy]:
        """특정 위치의 적 가져오기"""
        logger.warning(f"[DEBUG] get_enemy_at({x}, {y}) 호출 - 현재 적 {len(self.enemies)}마리")
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                logger.warning(f"[DEBUG] 적 발견! at ({x}, {y})")
                return enemy
        return None

    def remove_enemy(self, enemy: Enemy):
        """적 제거 (전투 승리 후)"""
        if enemy in self.enemies:
            self.enemies.remove(enemy)
            logger.info(f"적 제거: ({enemy.x}, {enemy.y})")

    def _move_all_enemies(self):
        """모든 적 움직임 처리"""
        for enemy in self.enemies:
            self._move_enemy(enemy)

    def _move_enemy(self, enemy: Enemy):
        """단일 적 움직임"""
        # 플레이어와의 거리 계산
        distance = abs(enemy.x - self.player.x) + abs(enemy.y - self.player.y)

        # 플레이어 감지
        if distance <= enemy.detection_range:
            enemy.is_chasing = True
            enemy.chase_turns = 0

        # 추적 중일 때
        if enemy.is_chasing:
            enemy.chase_turns += 1

            # 포기 조건 1: 너무 오래 추적
            if enemy.chase_turns > enemy.max_chase_turns:
                enemy.is_chasing = False
                enemy.chase_turns = 0
                logger.debug(f"적 {enemy.name}이(가) 추적 포기 (시간 초과)")

            # 포기 조건 2: 플레이어가 너무 멀리 도망감
            elif distance > enemy.max_chase_distance:
                enemy.is_chasing = False
                enemy.chase_turns = 0
                logger.debug(f"적 {enemy.name}이(가) 추적 포기 (거리: {distance} > {enemy.max_chase_distance})")

            # 추적 중이면 플레이어 방향으로 이동
            if enemy.is_chasing:
                self._move_enemy_towards(enemy, self.player.x, self.player.y)

        # 추적하지 않을 때
        if not enemy.is_chasing:
            # 원래 위치로 복귀
            if enemy.x != enemy.spawn_x or enemy.y != enemy.spawn_y:
                self._move_enemy_towards(enemy, enemy.spawn_x, enemy.spawn_y)

    def _move_enemy_towards(self, enemy: Enemy, target_x: int, target_y: int):
        """적을 목표 위치로 한 칸 이동"""
        # 이동 방향 결정 (맨하탄 거리 기반)
        dx = 0
        dy = 0

        if enemy.x < target_x:
            dx = 1
        elif enemy.x > target_x:
            dx = -1

        if enemy.y < target_y:
            dy = 1
        elif enemy.y > target_y:
            dy = -1

        # 대각선 이동 or 직선 이동 선택
        # 50% 확률로 X축 우선, 50% 확률로 Y축 우선
        if random.random() < 0.5 and dx != 0:
            new_x, new_y = enemy.x + dx, enemy.y
        elif dy != 0:
            new_x, new_y = enemy.x, enemy.y + dy
        elif dx != 0:
            new_x, new_y = enemy.x + dx, enemy.y
        else:
            return  # 이미 목표 위치에 도착

        # 이동 가능 여부 확인
        if self.dungeon.is_walkable(new_x, new_y):
            # 다른 적과 겹치지 않는지 확인
            # 플레이어 위치도 피함 (적이 플레이어 위로 이동하면 전투가 트리거되므로)
            if not self.get_enemy_at(new_x, new_y) and not (new_x == self.player.x and new_y == self.player.y):
                enemy.x = new_x
                enemy.y = new_y

    def _handle_puzzle(self, tile: Tile) -> ExplorationResult:
        """퍼즐 처리"""
        import random
        from src.core.logger import get_logger
        logger = get_logger("exploration")
        
        logger.info(f"퍼즐 타일 접근: 해결 여부={tile.puzzle_solved}")
        
        if tile.puzzle_solved:
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NONE,
                message="이미 해결된 퍼즐입니다."
            )

        # 간단한 퍼즐: 숫자 맞추기 (1-9)
        puzzle_answer = tile.puzzle_type or str(random.randint(1, 9))
        
        # 퍼즐 해결 (간단하게 자동 해결로 구현, 나중에 UI 추가 가능)
        tile.puzzle_solved = True
        logger.info(f"퍼즐 해결! 답: {puzzle_answer}")
        
        # 보상: 골드 또는 아이템
        reward_type = random.choice(["gold", "item"])
        if reward_type == "gold":
            gold_amount = random.randint(50, 200) * self.floor_number
            if self.inventory:
                self.inventory.add_gold(gold_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.PUZZLE_SOLVED,
                message=f"퍼즐 해결! {gold_amount} 골드 획득!",
                data={"gold": gold_amount}
            )
        else:
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number)
            if self.inventory:
                if self.inventory.add_item(item):
                    return ExplorationResult(
                        success=True,
                        event=ExplorationEvent.PUZZLE_SOLVED,
                        message=f"퍼즐 해결! {item.name} 획득!",
                        data={"item": item}
                    )
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.PUZZLE_SOLVED,
                message="퍼즐 해결! (인벤토리 가득 참)"
            )

    def _handle_switch(self, tile: Tile) -> ExplorationResult:
        """스위치 처리"""
        tile.switch_active = not tile.switch_active
        
        # 스위치가 제어하는 대상 처리 (예: 문 열기)
        if tile.switch_target:
            # switch_target이 문 ID인 경우 해당 문 열기
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    target_tile = self.dungeon.get_tile(x, y)
                    if target_tile and target_tile.key_id == tile.switch_target:
                        if target_tile.tile_type == TileType.LOCKED_DOOR:
                            target_tile.unlock()
                            logger.info(f"스위치로 문 열림: {tile.switch_target}")

        status = "활성화" if tile.switch_active else "비활성화"
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.SWITCH_ACTIVATED,
            message=f"스위치 {status}!",
            data={"active": tile.switch_active}
        )

    def _handle_pressure_plate(self, tile: Tile) -> ExplorationResult:
        """압력판 처리 (자동 활성화)"""
        if not tile.switch_active:
            tile.switch_active = True
            
            # 압력판이 제어하는 대상 처리
            if tile.switch_target:
                for y in range(self.dungeon.height):
                    for x in range(self.dungeon.width):
                        target_tile = self.dungeon.get_tile(x, y)
                        if target_tile and target_tile.key_id == tile.switch_target:
                            if target_tile.tile_type == TileType.LOCKED_DOOR:
                                target_tile.unlock()
                                logger.info(f"압력판으로 문 열림: {tile.switch_target}")

            return ExplorationResult(
                success=True,
                event=ExplorationEvent.SWITCH_ACTIVATED,
                message="압력판이 눌렸습니다!",
                data={"active": True}
            )
        return ExplorationResult(success=True, event=ExplorationEvent.NONE, message="")

    def _handle_lever(self, tile: Tile) -> ExplorationResult:
        """레버 처리"""
        tile.switch_active = not tile.switch_active
        
        # 레버가 제어하는 대상 처리
        if tile.switch_target:
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    target_tile = self.dungeon.get_tile(x, y)
                    if target_tile and target_tile.key_id == tile.switch_target:
                        if target_tile.tile_type == TileType.LOCKED_DOOR:
                            target_tile.unlock()
                            logger.info(f"레버로 문 열림: {tile.switch_target}")

        status = "당김" if tile.switch_active else "원위치"
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.SWITCH_ACTIVATED,
            message=f"레버를 {status}!",
            data={"active": tile.switch_active}
        )

    def _handle_npc(self, tile: Tile) -> ExplorationResult:
        """NPC 처리 - 스토리 기반 다양한 NPC 타입"""
        import random
        npc_type = tile.npc_type or "neutral"
        npc_subtype = tile.npc_subtype or "generic"
        npc_id = tile.npc_id or "unknown_npc"
        
        # 이미 상호작용한 NPC 처리
        if tile.npc_interacted and npc_subtype not in ["merchant", "mysterious_merchant", "time_mage"]:
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message="NPC는 이미 당신과 대화했습니다.",
                data={"npc_type": npc_type, "already_interacted": True}
            )
        
        # NPC 서브타입별 처리
        if npc_subtype == "time_researcher":
            return self._handle_time_researcher(tile)
        elif npc_subtype == "timeline_survivor":
            return self._handle_timeline_survivor(tile)
        elif npc_subtype == "space_explorer":
            return self._handle_space_explorer(tile)
        elif npc_subtype == "merchant":
            return self._handle_merchant(tile)
        elif npc_subtype == "refugee":
            return self._handle_refugee(tile)
        elif npc_subtype == "time_thief":
            return self._handle_time_thief(tile)
        elif npc_subtype == "distortion_entity":
            return self._handle_distortion_entity(tile)
        elif npc_subtype == "betrayer":
            return self._handle_betrayer(tile)
        elif npc_subtype == "mysterious_merchant":
            return self._handle_mysterious_merchant(tile)
        elif npc_subtype == "time_mage":
            return self._handle_time_mage(tile)
        elif npc_subtype == "future_self":
            return self._handle_future_self(tile)
        elif npc_subtype == "corrupted_survivor":
            return self._handle_corrupted_survivor(tile)
        elif npc_subtype == "ancient_guardian":
            return self._handle_ancient_guardian(tile)
        elif npc_subtype == "void_wanderer":
            return self._handle_void_wanderer(tile)
        
        # 기본 타입 처리 (하위 호환성)
        if npc_type == "helpful":
            return self._handle_helpful_npc(tile)
        elif npc_type == "harmful":
            return self._handle_harmful_npc(tile)
        else:  # neutral
            return self._handle_neutral_npc(tile)
    
    def _handle_time_researcher(self, tile: Tile) -> ExplorationResult:
        """시공 연구자 NPC"""
        import random
        tile.npc_interacted = True
        
        # 연구자가 시공교란에 대한 정보 제공
        help_type = random.choice(["info_heal", "info_item", "info_mp"])
        
        if help_type == "info_heal":
            heal_amount = 80 + self.floor_number * 15
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 연구자: '시공교란의 원인을 조사 중입니다. 이 치유 물약을 받으세요.'\n파티가 {heal_amount} HP 회복했습니다!",
                data={"npc_subtype": "time_researcher", "heal": heal_amount}
            )
        elif help_type == "info_item":
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number + 2)
            if self.inventory and self.inventory.add_item(item):
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"시공 연구자: '타임라인 붕괴를 막기 위한 장비입니다. 받으세요.'\n{item.name}을(를) 획득했습니다!",
                    data={"npc_subtype": "time_researcher", "item": item}
                )
        else:  # info_mp
            mp_amount = 30 + self.floor_number * 5
            for member in self.player.party:
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = min(member.max_mp, member.current_mp + mp_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 연구자: '마나 회복제입니다. 시공 마법에 유용할 것입니다.'\n파티가 {mp_amount} MP 회복했습니다!",
                data={"npc_subtype": "time_researcher", "mp": mp_amount}
            )
    
    def _handle_timeline_survivor(self, tile: Tile) -> ExplorationResult:
        """타임라인 붕괴 생존자 NPC"""
        import random
        tile.npc_interacted = True
        
        help_type = random.choice(["story_heal", "story_gold", "story_warning"])
        
        if help_type == "story_heal":
            heal_amount = 60 + self.floor_number * 10
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"생존자: '우리는 타임라인 붕괴에서 살아남았습니다. 이 작은 도움을 받으세요.'\n파티가 {heal_amount} HP 회복했습니다!",
                data={"npc_subtype": "timeline_survivor", "heal": heal_amount}
            )
        elif help_type == "story_gold":
            gold_amount = random.randint(30, 80) * self.floor_number
            if self.inventory:
                self.inventory.add_gold(gold_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"생존자: '더 이상 필요 없는 골드입니다. 받으세요.'\n{gold_amount} 골드를 획득했습니다!",
                data={"npc_subtype": "timeline_survivor", "gold": gold_amount}
            )
        else:  # story_warning
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message="생존자: '조심하세요. 시공의 균열이 점점 커지고 있습니다. 강력한 존재가 깨어나고 있어요...'",
                data={"npc_subtype": "timeline_survivor", "warning": True}
            )
    
    def _handle_space_explorer(self, tile: Tile) -> ExplorationResult:
        """우주 탐험가 NPC"""
        import random
        tile.npc_interacted = True
        
        help_type = random.choice(["explorer_item", "explorer_info", "explorer_heal"])
        
        if help_type == "explorer_item":
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number + 1)
            if self.inventory and self.inventory.add_item(item):
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"우주 탐험가: '우주 여행 중 발견한 물건입니다. 받으세요.'\n{item.name}을(를) 획득했습니다!",
                    data={"npc_subtype": "space_explorer", "item": item}
                )
        elif help_type == "explorer_info":
            gold_amount = random.randint(40, 120) * self.floor_number
            if self.inventory:
                self.inventory.add_gold(gold_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"우주 탐험가: '황금시대의 유물입니다. 받으세요.'\n{gold_amount} 골드를 획득했습니다!",
                data={"npc_subtype": "space_explorer", "gold": gold_amount}
            )
        else:  # explorer_heal
            heal_amount = 70 + self.floor_number * 12
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"우주 탐험가: '우주 의료 기술입니다. 도움이 될 것입니다.'\n파티가 {heal_amount} HP 회복했습니다!",
                data={"npc_subtype": "space_explorer", "heal": heal_amount}
            )
    
    def _handle_merchant(self, tile: Tile) -> ExplorationResult:
        """상인 NPC (중립, 반복 상호작용 가능)"""
        import random
        
        # 상인은 항상 골드를 받고 아이템을 판매
        if not self.inventory:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NPC_INTERACTION,
                message="상인: '인벤토리가 없어서 거래할 수 없습니다.'",
                data={"npc_subtype": "merchant"}
            )
        
        # 간단한 거래: 골드를 주면 아이템 제공
        cost = random.randint(50, 150) * self.floor_number
        
        if self.inventory.gold >= cost:
            self.inventory.gold -= cost
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number)
            if self.inventory.add_item(item):
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"상인: '좋은 거래입니다!'\n{cost} 골드를 지불하고 {item.name}을(를) 구매했습니다!",
                    data={"npc_subtype": "merchant", "cost": cost, "item": item}
                )
            else:
                self.inventory.gold += cost  # 환불
                return ExplorationResult(
                    success=False,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message="상인: '인벤토리가 가득 찼습니다.'",
                    data={"npc_subtype": "merchant"}
                )
        else:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"상인: '골드가 부족합니다. {cost} 골드가 필요합니다.' (보유: {self.inventory.gold})",
                data={"npc_subtype": "merchant", "required": cost}
            )
    
    def _handle_refugee(self, tile: Tile) -> ExplorationResult:
        """난민 NPC"""
        import random
        tile.npc_interacted = True
        
        help_type = random.choice(["refugee_small_heal", "refugee_small_gold"])
        
        if help_type == "refugee_small_heal":
            heal_amount = 30 + self.floor_number * 5
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"난민: '고마워요... 작은 도움이라도 드릴게요.'\n파티가 {heal_amount} HP 회복했습니다!",
                data={"npc_subtype": "refugee", "heal": heal_amount}
            )
        else:  # refugee_small_gold
            gold_amount = random.randint(10, 30) * self.floor_number
            if self.inventory:
                self.inventory.add_gold(gold_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"난민: '이건 제가 가진 전부예요... 받으세요.'\n{gold_amount} 골드를 획득했습니다!",
                data={"npc_subtype": "refugee", "gold": gold_amount}
            )
    
    def _handle_time_thief(self, tile: Tile) -> ExplorationResult:
        """시공 도적 NPC (손해)"""
        import random
        tile.npc_interacted = True
        
        harm_type = random.choice(["thief_gold", "thief_damage"])
        
        if harm_type == "thief_gold":
            if self.inventory:
                stolen_gold = min(self.inventory.gold, random.randint(100, 300) * self.floor_number)
                self.inventory.gold = max(0, self.inventory.gold - stolen_gold)
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"시공 도적: '하하하! 시공의 틈새를 이용해 골드를 훔쳤다!'\n{stolen_gold} 골드를 잃었습니다!",
                    data={"npc_subtype": "time_thief", "gold_lost": stolen_gold}
                )
        else:  # thief_damage
            damage = 30 + self.floor_number * 8
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 도적: '시공 마법으로 공격한다!'\n파티가 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "time_thief", "damage": damage}
            )
    
    def _handle_distortion_entity(self, tile: Tile) -> ExplorationResult:
        """타임라인 왜곡체 NPC (손해)"""
        import random
        tile.npc_interacted = True
        
        harm_type = random.choice(["distortion_damage", "distortion_curse"])
        
        if harm_type == "distortion_damage":
            damage = 40 + self.floor_number * 10
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"타임라인 왜곡체: '시공의 힘으로 공격한다...'\n파티가 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "distortion_entity", "damage": damage}
            )
        else:  # distortion_curse
            if self.inventory:
                stolen_gold = min(self.inventory.gold, random.randint(80, 200))
                self.inventory.gold = max(0, self.inventory.gold - stolen_gold)
            damage = 20 + self.floor_number * 5
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"타임라인 왜곡체: '시공의 저주를 걸었다...'\n{stolen_gold if self.inventory else 0} 골드를 잃고 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "distortion_entity", "gold_lost": stolen_gold if self.inventory else 0, "damage": damage}
            )
    
    def _handle_betrayer(self, tile: Tile) -> ExplorationResult:
        """배신자 NPC (복합: 처음엔 도움, 나중엔 손해)"""
        import random
        
        if not tile.npc_interacted:
            # 첫 상호작용: 도움
            tile.npc_interacted = True
            heal_amount = 100 + self.floor_number * 20
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"배신자: '도와드리겠습니다!'\n파티가 {heal_amount} HP 회복했습니다! (하지만 뭔가 수상합니다...)",
                data={"npc_subtype": "betrayer", "heal": heal_amount, "first_interaction": True}
            )
        else:
            # 두 번째 상호작용: 배신
            damage = 50 + self.floor_number * 15
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            if self.inventory:
                stolen_gold = min(self.inventory.gold, random.randint(150, 400))
                self.inventory.gold = max(0, self.inventory.gold - stolen_gold)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"배신자: '하하하! 속았지!'\n파티가 {damage} 데미지를 입고 {stolen_gold if self.inventory else 0} 골드를 잃었습니다!",
                data={"npc_subtype": "betrayer", "damage": damage, "gold_lost": stolen_gold if self.inventory else 0}
            )
    
    def _handle_mysterious_merchant(self, tile: Tile) -> ExplorationResult:
        """신비한 상인 NPC (복합: 비싼 거래)"""
        import random
        
        if not self.inventory:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NPC_INTERACTION,
                message="신비한 상인: '인벤토리가 없어서 거래할 수 없습니다.'",
                data={"npc_subtype": "mysterious_merchant"}
            )
        
        cost = random.randint(200, 500) * self.floor_number
        
        if self.inventory.gold >= cost:
            self.inventory.gold -= cost
            from src.equipment.item_system import ItemGenerator
            # 더 좋은 아이템 제공
            item = ItemGenerator.create_random_drop(self.floor_number + 3)
            if self.inventory.add_item(item):
                # 추가 보너스: HP 회복
                heal_amount = 50 + self.floor_number * 10
                for member in self.player.party:
                    if hasattr(member, 'heal'):
                        member.heal(heal_amount)
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"신비한 상인: '시공의 힘이 깃든 물건입니다...'\n{cost} 골드를 지불하고 {item.name}을(를) 구매했습니다! 파티가 {heal_amount} HP 회복했습니다!",
                    data={"npc_subtype": "mysterious_merchant", "cost": cost, "item": item, "heal": heal_amount}
                )
            else:
                self.inventory.gold += cost
                return ExplorationResult(
                    success=False,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message="신비한 상인: '인벤토리가 가득 찼습니다.'",
                    data={"npc_subtype": "mysterious_merchant"}
                )
        else:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"신비한 상인: '골드가 부족합니다. {cost} 골드가 필요합니다.' (보유: {self.inventory.gold})",
                data={"npc_subtype": "mysterious_merchant", "required": cost}
            )
    
    def _handle_time_mage(self, tile: Tile) -> ExplorationResult:
        """시공 마법사 NPC (복합: 강력한 도움과 손해)"""
        import random
        
        # 시공 마법사는 매번 다른 효과
        effect_type = random.choice(["powerful_heal", "powerful_mp", "time_damage", "time_curse"])
        
        if effect_type == "powerful_heal":
            heal_amount = 150 + self.floor_number * 25
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 마법사: '시간을 되돌려 치유합니다...'\n파티가 {heal_amount} HP 회복했습니다!",
                data={"npc_subtype": "time_mage", "heal": heal_amount}
            )
        elif effect_type == "powerful_mp":
            mp_amount = 50 + self.floor_number * 10
            for member in self.player.party:
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = min(member.max_mp, member.current_mp + mp_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 마법사: '시공의 마나를 전달합니다...'\n파티가 {mp_amount} MP 회복했습니다!",
                data={"npc_subtype": "time_mage", "mp": mp_amount}
            )
        elif effect_type == "time_damage":
            damage = 60 + self.floor_number * 15
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 마법사: '시공의 힘이 불안정합니다... 죄송합니다!'\n파티가 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "time_mage", "damage": damage}
            )
        else:  # time_curse
            if self.inventory:
                stolen_gold = min(self.inventory.gold, random.randint(100, 250))
                self.inventory.gold = max(0, self.inventory.gold - stolen_gold)
            damage = 40 + self.floor_number * 10
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"시공 마법사: '시공의 저주가 발동했습니다!'\n{stolen_gold if self.inventory else 0} 골드를 잃고 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "time_mage", "gold_lost": stolen_gold if self.inventory else 0, "damage": damage}
            )
    
    def _handle_future_self(self, tile: Tile) -> ExplorationResult:
        """미래의 자신 NPC (복합: 특별한 상호작용)"""
        import random
        tile.npc_interacted = True
        
        effect_type = random.choice(["future_warning", "future_gift", "future_curse"])
        
        if effect_type == "future_warning":
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message="미래의 자신: '나는 미래의 너다. 조심해라. 시공교란의 진실은... 너의 선택에 달려있다.'",
                data={"npc_subtype": "future_self", "warning": True}
            )
        elif effect_type == "future_gift":
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number + 5)
            heal_amount = 100 + self.floor_number * 20
            if self.inventory and self.inventory.add_item(item):
                for member in self.player.party:
                    if hasattr(member, 'heal'):
                        member.heal(heal_amount)
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"미래의 자신: '이것은 미래에서 가져온 선물이다.'\n{item.name}을(를) 획득하고 파티가 {heal_amount} HP 회복했습니다!",
                    data={"npc_subtype": "future_self", "item": item, "heal": heal_amount}
                )
        else:  # future_curse
            damage = 30 + self.floor_number * 8
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"미래의 자신: '미래를 바꾸려는 시도는 위험하다...'\n파티가 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "future_self", "damage": damage}
            )
    
    def _handle_corrupted_survivor(self, tile: Tile) -> ExplorationResult:
        """시공 교란 피해자 NPC (복합: 도움과 손해)"""
        import random
        tile.npc_interacted = True
        
        # 도움과 손해를 동시에
        heal_amount = 60 + self.floor_number * 10
        damage = 20 + self.floor_number * 5
        
        for member in self.player.party:
            if hasattr(member, 'heal'):
                member.heal(heal_amount)
            if hasattr(member, 'take_damage'):
                member.take_damage(damage)
        
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NPC_INTERACTION,
            message=f"시공 교란 피해자: '시공의 힘이... 불안정해...'\n파티가 {heal_amount} HP 회복했지만 {damage} 데미지도 입었습니다!",
            data={"npc_subtype": "corrupted_survivor", "heal": heal_amount, "damage": damage}
        )
    
    def _handle_ancient_guardian(self, tile: Tile) -> ExplorationResult:
        """고대 수호자 NPC (도움)"""
        import random
        tile.npc_interacted = True
        
        help_type = random.choice(["guardian_blessing", "guardian_item", "guardian_wisdom"])
        
        if help_type == "guardian_blessing":
            heal_amount = 120 + self.floor_number * 20
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            mp_amount = 40 + self.floor_number * 8
            for member in self.player.party:
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = min(member.max_mp, member.current_mp + mp_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"고대 수호자: '고대의 축복을 받으라.'\n파티가 {heal_amount} HP와 {mp_amount} MP 회복했습니다!",
                data={"npc_subtype": "ancient_guardian", "heal": heal_amount, "mp": mp_amount}
            )
        elif help_type == "guardian_item":
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number + 4)
            if self.inventory and self.inventory.add_item(item):
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"고대 수호자: '고대의 유물을 받으라.'\n{item.name}을(를) 획득했습니다!",
                    data={"npc_subtype": "ancient_guardian", "item": item}
                )
        else:  # guardian_wisdom
            gold_amount = random.randint(100, 200) * self.floor_number
            if self.inventory:
                self.inventory.add_gold(gold_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"고대 수호자: '고대의 지혜는 이렇게 전해진다.'\n{gold_amount} 골드를 획득했습니다!",
                data={"npc_subtype": "ancient_guardian", "gold": gold_amount}
            )
    
    def _handle_void_wanderer(self, tile: Tile) -> ExplorationResult:
        """공허 방랑자 NPC (복합: 랜덤 효과)"""
        import random
        tile.npc_interacted = True
        
        effect_type = random.choice(["void_heal", "void_damage", "void_item", "void_nothing"])
        
        if effect_type == "void_heal":
            heal_amount = 80 + self.floor_number * 15
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"공허 방랑자: '공허에서 온 치유...'\n파티가 {heal_amount} HP 회복했습니다!",
                data={"npc_subtype": "void_wanderer", "heal": heal_amount}
            )
        elif effect_type == "void_damage":
            damage = 50 + self.floor_number * 12
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"공허 방랑자: '공허의 손길...'\n파티가 {damage} 데미지를 입었습니다!",
                data={"npc_subtype": "void_wanderer", "damage": damage}
            )
        elif effect_type == "void_item":
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number + 2)
            if self.inventory and self.inventory.add_item(item):
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"공허 방랑자: '공허에서 발견한 물건...'\n{item.name}을(를) 획득했습니다!",
                    data={"npc_subtype": "void_wanderer", "item": item}
                )
        else:  # void_nothing
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message="공허 방랑자: '...' (아무 일도 일어나지 않았습니다)",
                data={"npc_subtype": "void_wanderer"}
            )
    
    def _handle_helpful_npc(self, tile: Tile) -> ExplorationResult:
        """기본 도움 NPC (하위 호환성)"""
        import random
        tile.npc_interacted = True
        help_type = random.choice(["heal", "item", "gold"])
        
        if help_type == "heal":
            heal_amount = 50 + self.floor_number * 10
            for member in self.player.party:
                if hasattr(member, 'heal'):
                    member.heal(heal_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"친절한 NPC가 파티를 {heal_amount} HP 회복시켜줬습니다!",
                data={"npc_type": "helpful", "heal": heal_amount}
            )
        elif help_type == "item":
            from src.equipment.item_system import ItemGenerator
            item = ItemGenerator.create_random_drop(self.floor_number)
            if self.inventory and self.inventory.add_item(item):
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NPC_INTERACTION,
                    message=f"친절한 NPC가 {item.name}을(를) 주었습니다!",
                    data={"npc_type": "helpful", "item": item}
                )
        else:  # gold
            gold_amount = random.randint(20, 100) * self.floor_number
            if self.inventory:
                self.inventory.add_gold(gold_amount)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"친절한 NPC가 {gold_amount} 골드를 주었습니다!",
                data={"npc_type": "helpful", "gold": gold_amount}
            )
    
    def _handle_harmful_npc(self, tile: Tile) -> ExplorationResult:
        """기본 손해 NPC (하위 호환성)"""
        import random
        tile.npc_interacted = True
        harm_type = random.choice(["damage", "curse"])
        
        if harm_type == "damage":
            damage = 20 + self.floor_number * 5
            for member in self.player.party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(damage)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"악의적인 NPC가 파티에게 {damage} 데미지를 입혔습니다!",
                data={"npc_type": "harmful", "damage": damage}
            )
        else:  # curse
            if self.inventory:
                stolen_gold = min(self.inventory.gold, random.randint(50, 200))
                self.inventory.gold = max(0, self.inventory.gold - stolen_gold)
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NPC_INTERACTION,
                message=f"악의적인 NPC가 {stolen_gold if self.inventory else 0} 골드를 훔쳤습니다!",
                data={"npc_type": "harmful", "gold_lost": stolen_gold if self.inventory else 0}
            )
    
    def _handle_neutral_npc(self, tile: Tile) -> ExplorationResult:
        """기본 중립 NPC (하위 호환성)"""
        tile.npc_interacted = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NPC_INTERACTION,
            message="NPC와 대화했습니다. (특별한 일은 없었습니다)",
            data={"npc_type": "neutral"}
        )
