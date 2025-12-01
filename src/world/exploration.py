"""
월드 탐험 시스템

플레이어가 던전을 돌아다니며 적과 조우하고 기믹과 상호작용
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import time
import heapq

from src.world.dungeon_generator import DungeonMap
from src.world.tile import Tile, TileType
from src.world.fov import FOVSystem
from src.core.logger import get_logger, Loggers
from src.core.event_bus import event_bus, Events
from src.audio import play_sfx

# ExplorationEvent를 먼저 정의하여 import 순서 문제 방지
class ExplorationEvent(Enum):
    """탐험 이벤트"""
    NONE = "none"
    COMBAT = "combat"
    ITEM_FOUND = "item_found"
    TRAP_TRIGGERED = "trap_triggered"
    TELEPORT = "teleport"
    TELEPORTER_FOUND = "teleporter_found"  # 텔레포터 발견 (선택 메뉴 표시용)
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
    BUILDING_INTERACTION = "building_interaction"  # 마을 건물 상호작용


# 클래스 정의 전에 미리 참조하여 지역 변수 충돌 방지
_EXPLORATION_EVENT_NONE = ExplorationEvent.NONE
_EXPLORATION_EVENT_COMBAT = ExplorationEvent.COMBAT
_EXPLORATION_EVENT_ITEM_FOUND = ExplorationEvent.ITEM_FOUND
_EXPLORATION_EVENT_TRAP_TRIGGERED = ExplorationEvent.TRAP_TRIGGERED


logger = get_logger(Loggers.WORLD)


@dataclass
class Enemy:
    """적 엔티티"""
    x: int
    y: int
    level: int
    name: str = "적"  # 적 이름
    is_boss: bool = False
    id: Optional[str] = None  # 고유 ID (멀티플레이 동기화용)

    # AI 상태
    spawn_x: int = None  # 생성 위치 X
    spawn_y: int = None  # 생성 위치 Y
    is_chasing: bool = False  # 추적 중
    chase_turns: int = 0  # 추적 턴 수
    max_chase_turns: int = 15  # 최대 추적 턴
    max_chase_distance: int = 15  # 최대 추적 거리 (이 거리 이상 벌어지면 포기)
    detection_range: int = 5  # 플레이어 감지 거리

    # 고급 AI 시스템
    reinforcement_called: bool = False  # 증원을 불렀는지
    last_reinforcement_turn: int = 0  # 마지막 증원 호출 턴
    reinforcement_cooldown: int = 10  # 증원 쿨다운 (턴)

    encirclement_role: str = "none"  # "leader" 또는 "flanker" 또는 "none"
    is_minion: bool = False  # 보스의 수하 여부
    leader_id: Optional[str] = None  # 보스 ID (수하일 경우)

    morale: float = 100.0  # 사기 (0-100, 낮을수록 포기할 확률 높음)
    last_hp_ratio: float = 1.0  # 이전 HP 비율 (증원 판단용)

    # 신호 시스템
    signal_sent: bool = False  # 신호를 보냈는지
    signal_position_x: Optional[int] = None  # 신호를 보낸 위치 X
    signal_position_y: Optional[int] = None  # 신호를 보낸 위치 Y
    signal_range: int = 20  # 신호 감지 범위 (20칸)
    signal_cooldown: int = 15  # 신호 쿨다운
    last_signal_turn: int = 0  # 마지막 신호 턴

    # 시간 기반 이동 시스템
    last_move_time: float = 0.0  # 마지막 이동 시간 (초)
    move_interval: float = 0.3  # 이동 간격 (0.3초 = 초당 ~3.3회) - 플레이어(0.2초)보다 느림

    # 도망 후 정지 시스템
    stunned_until: float = 0.0  # 정지 종료 시간 (초, 0이면 정지 안 함)

    def __post_init__(self):
        if self.spawn_x is None:
            self.spawn_x = self.x
        if self.spawn_y is None:
            self.spawn_y = self.y
        # 고유 ID가 없으면 생성 (spawn 위치 기반)
        if self.id is None:
            import uuid
            self.id = f"enemy_{self.spawn_x}_{self.spawn_y}_{uuid.uuid4().hex[:8]}"


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
            "save_slot": None,
            "next_dungeon_floor": max(floor_number + 1, 1)  # 다음 던전 층 번호 (기본값: 현재 층+1 또는 1)
        }
        # game_stats에 next_dungeon_floor가 없으면 추가
        if "next_dungeon_floor" not in self.game_stats:
            self.game_stats["next_dungeon_floor"] = max(floor_number + 1, 1)

        # 인벤토리 초기화 확인 로그
        logger.error(f"[INIT] ExplorationSystem 초기화 - 인벤토리: {self.inventory}")
        if self.inventory is not None:
            logger.error(f"[INIT] 인벤토리 타입: {type(self.inventory)}, 슬롯: {len(self.inventory.slots)}, 골드: {self.inventory.gold}G")
        else:
            logger.error(f"[INIT] [WARNING] 인벤토리가 None입니다!")

        # 마을 여부 확인 (던전에 is_town 플래그가 있는 경우)
        if hasattr(dungeon, 'is_town') and dungeon.is_town:
            self.is_town = True
            logger.info("[INIT] 마을 맵으로 인식됨 - 적 스폰 건너뜀")
            # 마을에서는 적 스폰하지 않음
            self.enemies = []
        else:
            self.is_town = False
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

        # 장비 착용/해제 이벤트 구독 (시야 업데이트용)
        event_bus.subscribe(Events.EQUIPMENT_EQUIPPED, self._on_equipment_changed)
        event_bus.subscribe(Events.EQUIPMENT_UNEQUIPPED, self._on_equipment_changed)

        # 발소리 SFX 간격 추적 (최소 5초)
        self.last_footstep_time = 0.0
        
        # 환경 효과 시간 추적 (시간당 지속 피해용)
        import time
        self.last_environment_effect_time = time.time()
        self.environment_effect_interval = 3.0  # 3초마다 체크
        
        # 환경 효과 메시지 표시 추적 (스팸 방지용)
        self.last_effect_tile = None  # 마지막으로 효과 메시지를 표시한 타일 위치
        self.last_effect_types = set()  # 마지막으로 표시한 효과 타입들

        # 시간 기반 이동 시스템: 충돌 추적 (적과 플레이어가 같은 위치에서 만날 때)
        self.collision_enemy = None  # 플레이어와 충돌한 적

        logger.info(f"탐험 시작: 층 {self.floor_number}, 위치 ({self.player.x}, {self.player.y})")

    def update_fov(self):
        """시야 업데이트"""
        # 마을에서는 모든 타일을 보이게 함
        if hasattr(self, 'is_town') and self.is_town:
            # 모든 타일을 visible과 explored로 설정
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    tile = self.dungeon.get_tile(x, y)
                    if tile:
                        tile.visible = True
                        tile.explored = True
            # explored_tiles에도 추가
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    self.explored_tiles.add((x, y))
            logger.debug("[update_fov] 마을: 모든 타일을 보이게 설정")
            return
        
        # 이전 visible 초기화
        self.fov_system.clear_visibility(self.dungeon)

        # 기본 시야 반지름 (3)
        base_radius = 3
        
        # 파티 멤버들의 시야 보너스 합산
        vision_bonus = 0
        skill_bonus = 0  # 스킬/특성/보너스 시야 증가
        
        if self.player.party:
            for member in self.player.party:
                # 장비 효과로 인한 vision_bonus 확인
                member_vision_bonus = getattr(member, 'vision_bonus', 0)
                if member_vision_bonus > 0:
                    member_name = getattr(member, 'name', getattr(member, 'character_name', 'Unknown'))
                    logger.info(f"{member_name} vision_bonus: {member_vision_bonus}")
                vision_bonus += member_vision_bonus
                
                # 직업 보너스에서 시야 증가 확인 (예: 무당의 vision_range: 2.0)
                from src.character.character_loader import get_bonuses
                # Character 객체는 character_class를, PartyMember 객체는 job_name을 사용
                character_class = getattr(member, 'character_class', None)
                if character_class is None:
                    # PartyMember 객체인 경우 job_name 사용
                    character_class = getattr(member, 'job_name', None)
                
                if character_class:
                    bonuses = get_bonuses(character_class)
                    if bonuses and 'vision_range' in bonuses:
                        vision_range_bonus = bonuses.get('vision_range', 0)
                        if isinstance(vision_range_bonus, (int, float)):
                            skill_bonus += int(vision_range_bonus)
                
        # 최종 시야 반지름 계산: 기본 3 + 장비 vision_bonus + 스킬/특성/보너스
        final_radius = base_radius + vision_bonus + skill_bonus
        logger.info(f"[update_fov] 시야 계산: 기본={base_radius}, vision_bonus={vision_bonus}, skill_bonus={skill_bonus}, 최종={final_radius}")
        
        # 특성의 "시야 범위 2배" 같은 곱셈 효과 적용
        vision_multiplier = 1.0
        if self.player.party:
            from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
            trait_manager = get_trait_effect_manager()
            
            for member in self.player.party:
                if hasattr(member, 'active_traits') and member.active_traits:
                    for trait in member.active_traits:
                        trait_id = getattr(trait, 'id', '') if hasattr(trait, 'id') else str(trait)
                        effects = trait_manager.get_trait_effects(trait_id)
                        
                        for effect in effects:
                            # vision_range 타겟 스탯을 가진 STAT_MULTIPLIER 효과 확인
                            if (effect.effect_type == TraitEffectType.STAT_MULTIPLIER and 
                                effect.target_stat == "vision_range"):
                                # 곱셈 효과 적용 (예: 2.0배)
                                vision_multiplier *= effect.value
                                logger.debug(f"{member.name} 특성 {trait_id}: 시야 {effect.value}배")
        
        # 곱셈 적용
        final_radius = int(final_radius * vision_multiplier)
        
        # 환경 효과 시야 수정 (플레이어가 있는 타일 기준)
        if hasattr(self.dungeon, 'environment_effect_manager') and not (hasattr(self, 'is_town') and self.is_town):
            env_vision_modifier = self.dungeon.environment_effect_manager.get_vision_modifier(
                self.player, self.player.x, self.player.y
            )
            final_radius = int(final_radius * env_vision_modifier)
        
        # 최소 1, 최대 10
        final_radius = max(1, min(10, final_radius))
        
        logger.debug(f"시야 계산: 기본={base_radius}, 장비보너스={vision_bonus}, 스킬보너스={skill_bonus}, 곱셈={vision_multiplier}, 최종={final_radius}")

        # FOV 계산
        visible = self.fov_system.compute_fov(
            self.dungeon,
            self.player.x,
            self.player.y,
            final_radius
        )

        # 탐험한 타일 누적
        self.explored_tiles.update(visible)

    def _on_equipment_changed(self, data: Dict[str, Any]):
        """장비 착용/해제 시 시야 업데이트"""
        # 파티 멤버의 장비가 변경되었으면 시야 재계산
        character = data.get("character")
        if character and character in self.player.party:
            self.update_fov()

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
        # 플레이어 방향 업데이트 (필드 스킬용)
        self.player.dx = dx
        self.player.dy = dy

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
        # Debug: 적 충돌 체크
        if enemy:
            logger.info(f"[전투 트리거] 플레이어가 적 위치로 이동 시도: ({new_x}, {new_y}) - 적: {enemy.name}")
            # 플레이어는 이동하지 않고 전투만 트리거
            combat_result = self._trigger_combat_with_enemy(enemy)
            # Debug: 전투 결과
            return combat_result

        # 이동 발소리 (간헐적으로만 재생, 최소 5초 간격)
        current_time = time.time()
        time_since_last_footstep = current_time - self.last_footstep_time
        
        # 최소 5초 간격이 지났고 5% 확률로 발소리 재생
        if time_since_last_footstep >= 5.0 and random.random() < 0.05:  # 5% 확률
            play_sfx("world", "footstep", volume_multiplier=0.5)
            self.last_footstep_time = current_time
        
        # 이동
        self.player.x = new_x
        self.player.y = new_y

        # FOV 업데이트
        self.update_fov()

        # 타일 이벤트 체크
        tile = self.dungeon.get_tile(new_x, new_y)
        result = self._check_tile_event(tile)
        
        # 환경 효과 적용 (마을이 아닌 경우만)
        # 이동 시 즉시 데미지를 주는 효과 적용 (불타는 바닥 등)
        if hasattr(self.dungeon, 'environment_effect_manager') and not (hasattr(self, 'is_town') and self.is_town):
            effect_manager = None
            if hasattr(self.dungeon, 'environment_effect_manager'):
                effect_manager = self.dungeon.environment_effect_manager
            elif hasattr(self.dungeon, 'environmental_effect_manager'):
                effect_manager = self.dungeon.environmental_effect_manager
            
            if effect_manager and self.player.party:
                # 타일 효과 정보 가져오기
                effects = effect_manager.get_effects_at_tile(new_x, new_y)
                
                # 새로운 타일로 이동했거나 효과가 변경된 경우 효과 정보 표시
                current_tile = (new_x, new_y)
                current_effect_types = {effect.effect_type for effect in effects}
                
                # 타일이 변경되었거나 효과가 변경된 경우에만 정보 표시
                if current_tile != self.last_effect_tile or current_effect_types != self.last_effect_types:
                    if effects:
                        effect_names = [effect.name for effect in effects]
                        effect_info = f"[환경 효과] {', '.join(effect_names)}"
                        if result.message:
                            result.message = f"{result.message}\n{effect_info}"
                        else:
                            result.message = effect_info
                    
                    # 마지막 타일 및 효과 타입 업데이트
                    self.last_effect_tile = current_tile
                    self.last_effect_types = current_effect_types
                
                # 이동 시 즉시 데미지를 주는 효과 적용 (불타는 바닥 등)
                effect_messages = []
                for member in self.player.party:
                    messages = effect_manager.apply_tile_effects(
                        member, new_x, new_y, is_movement=True
                    )
                    if messages:
                        effect_messages.extend(messages)
                
                # 효과 메시지가 있으면 결과에 추가 (데미지/회복 메시지)
                if effect_messages:
                    # 여러 메시지가 있으면 첫 번째 것만 표시하거나 모두 합침
                    if result.message:
                        result.message = f"{result.message}\n{effect_messages[0]}"
                    else:
                        result.message = effect_messages[0]
                
                # 시간당 지속 피해 체크 (독 늪 등)
                current_time = time.time()
                time_since_last_check = current_time - self.last_environment_effect_time
                
                if time_since_last_check >= self.environment_effect_interval:
                    # 시간 간격이 지나면 시간당 지속 피해 적용
                    dot_messages = []
                    for member in self.player.party:
                        messages = effect_manager.apply_tile_effects(
                            member, new_x, new_y, is_movement=False  # 시간당 피해
                        )
                        if messages:
                            dot_messages.extend(messages)
                    
                    # 지속 피해 메시지 추가
                    if dot_messages:
                        if result.message:
                            result.message = f"{result.message}\n{dot_messages[0]}"
                        else:
                            result.message = dot_messages[0]
                    
                    # 시간 업데이트
                    self.last_environment_effect_time = current_time

        # 적 이동은 이제 시간 기반 시스템으로 처리됨
        # on_update 콜백에서 _move_all_enemies()가 지속적으로 호출됨
        # 플레이어와 적이 시간 기반으로 독립적으로 움직임

        # NPC 이동 (플레이어 이동 후)
        self._move_npcs()

        # 적 움직임 후 플레이어 위치에 적이 있는지 다시 체크
        # 싱글플레이어: 플레이어 위치에 적이 있으면 전투 시작
        # 멀티플레이어: MultiplayerExplorationSystem에서 봇이 트리거하는 경우도 처리됨
        enemy_at_player = self.get_enemy_at(self.player.x, self.player.y)
        if enemy_at_player:
            logger.info(f"[전투 트리거] 적이 플레이어 위치로 이동: ({self.player.x}, {self.player.y}) - 적: {enemy_at_player.name}")
            return self._trigger_combat_with_enemy(enemy_at_player)

        return result

    def update_environmental_effects(self) -> Optional[str]:
        """
        플레이어가 현재 타일에 머물러 있을 때 환경 효과 업데이트
        
        Returns:
            효과 메시지 (있으면)
        """
        # 마을이 아닌 경우만
        if hasattr(self, 'is_town') and self.is_town:
            return None
        
        # 환경 효과 관리자 확인
        effect_manager = None
        if hasattr(self.dungeon, 'environment_effect_manager'):
            effect_manager = self.dungeon.environment_effect_manager
        elif hasattr(self.dungeon, 'environmental_effect_manager'):
            effect_manager = self.dungeon.environmental_effect_manager
        
        if not effect_manager or not self.player.party:
            return None
        
        # 시간 간격 체크
        import time
        current_time = time.time()
        time_since_last_check = current_time - self.last_environment_effect_time
        
        if time_since_last_check >= self.environment_effect_interval:
            # 시간 간격이 지나면 시간당 지속 피해/회복 적용
            dot_messages = []
            for member in self.player.party:
                messages = effect_manager.apply_tile_effects(
                    member, self.player.x, self.player.y, is_movement=False
                )
                if messages:
                    dot_messages.extend(messages)
            
            # 시간 업데이트
            self.last_environment_effect_time = current_time
            
            # 메시지 반환
            if dot_messages:
                return dot_messages[0]
        
        return None

    def _check_tile_event(self, tile: Tile) -> ExplorationResult:
        """타일 이벤트 확인"""
        # 마을 건물 상호작용 체크 (우선순위 높음, 적과 조우와 동일한 방식)
        if hasattr(self, 'is_town') and self.is_town:
            # 타일에 building 속성이 있으면 건물 상호작용
            if hasattr(tile, 'building') and tile.building:
                building = tile.building
                logger.info(f"[건물 조우] {building.name}에 도달했습니다. (위치: {self.player.x}, {self.player.y})")
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.BUILDING_INTERACTION,
                    message=f"🏛 {building.name}에 도착했습니다",
                    data={
                        "building": building,
                        "building_type": building.building_type.value,
                        "building_name": building.name
                    }
                )
            # 타일의 char가 건물 심볼인 경우도 확인
            elif hasattr(tile, 'char') and tile.char in ['K', 'B', 'A', 'S', 'Q', '$', 'I', 'G', 'F']:
                # town_map에서 건물 찾기
                if hasattr(self, 'town_map') and self.town_map:
                    building = self.town_map.get_building_at(self.player.x, self.player.y)
                    if building:
                        logger.info(f"[건물 조우] {building.name}에 도달했습니다. (위치: {self.player.x}, {self.player.y})")
                        return ExplorationResult(
                            success=True,
                            event=ExplorationEvent.BUILDING_INTERACTION,
                            message=f"🏛 {building.name}에 도착했습니다",
                            data={
                                "building": building,
                                "building_type": building.building_type.value,
                                "building_name": building.name
                            }
                        )
        
        if tile.tile_type == TileType.TRAP:
            return self._handle_trap(tile)

        elif tile.tile_type == TileType.TELEPORTER:
            return self._handle_teleporter(tile)

        elif tile.tile_type == TileType.LAVA:
            return self._handle_lava(tile)

        elif tile.tile_type == TileType.HEALING_SPRING:
            return self._handle_healing_spring(tile)

        # 올라가는 계단 제거됨 (마을로 돌아갈 수 없음)
        # elif tile.tile_type == TileType.STAIRS_UP: 제거

        elif tile.tile_type == TileType.STAIRS_DOWN:
            # 30층 진입 체크 (20층 클리어 필요)
            if self.floor_number == 29:  # 29층에서 30층으로 가려고 할 때
                from src.story.story_system import get_story_system
                story_system = get_story_system()
                if not story_system.sephiroth_defeated:
                    # 30층 진입 불가
                    play_sfx("world", "error")
                    return ExplorationResult(
                        success=False,
                        event=ExplorationEvent.LOCKED_DOOR,
                        message="━━━━━━━━━━━━━━━━━━━━━━━━━━\n??? : \"20층의 시련을 먼저 극복하라.\"\n━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )

            play_sfx("world", "stairs_down")
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

        elif tile.tile_type == TileType.DROPPED_ITEM:
            return self._handle_dropped_item(tile)

        elif tile.tile_type == TileType.GOLD:
            return self._handle_gold(tile)

        # BOSS_ROOM 이벤트 제거 (요청에 따라)
        # elif tile.tile_type == TileType.BOSS_ROOM:
        #     # 보스방 진입 시 주변 보스를 찾아서 전투 시작
        #     # BOSS_ROOM 영역 내 또는 근처의 보스 찾기
        #     boss_enemy = None
        #     for enemy in self.enemies:
        #         if enemy.is_boss:
        #             # 플레이어 주변 5칸 이내의 보스 찾기
        #             distance = abs(enemy.x - self.player.x) + abs(enemy.y - self.player.y)
        #             if distance <= 5:
        #                 boss_enemy = enemy
        #                 break
        #
        #     # 보스를 찾았으면 전투 시작
        #     if boss_enemy:
        #         logger.info(f"[보스방 진입] 층 보스 발견! {boss_enemy.name}와의 전투 시작!")
        #         return self._trigger_combat_with_enemy(boss_enemy)
        #     else:
        #         # 보스가 없으면 (이미 처치했거나) 경고 메시지만 표시
        #         return ExplorationResult(
        #             success=True,
        #             event=ExplorationEvent.BOSS_ROOM,
        #             message="⚠ 보스의 기운이 느껴집니다..."
        #         )

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
            return self._handle_trap(tile)

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

    def check_and_harvest(self, x: int, y: int, player_id: Optional[str] = None) -> Optional[Tuple[Dict[str, int], str]]:
        """
        위치에서 채집 시도 및 실행
        
        Args:
            x: X 좌표
            y: Y 좌표
            player_id: 채집하는 플레이어 ID
            
        Returns:
            (획득한 아이템 딕셔너리, 채집물 타입 문자열) 또는 None
        """
        if not hasattr(self.dungeon, 'harvestables'):
            return None
            
        for harvestable in self.dungeon.harvestables:
            if harvestable.x == x and harvestable.y == y:
                # 아직 채집 안 된 경우에만
                if harvestable.can_harvest(player_id):
                    # 자동 채집 실행
                    results = harvestable.harvest(player_id)
                    if results:
                        return results, harvestable.object_type.value
        return None

    def _handle_trap(self, tile: Tile) -> ExplorationResult:
        """함정 처리"""
        damage = tile.trap_damage

        # 함정 발동 SFX
        play_sfx("world", "trap_trigger")
        
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
            # 텔레포터 발견 이벤트 반환 (선택 메뉴 표시용)
            logger.info(f"텔레포터 발견: {tile.teleport_target}")

            return ExplorationResult(
                success=True,
                event=ExplorationEvent.TELEPORTER_FOUND,
                message="🌀 텔레포터를 발견했습니다! 텔레포트하시겠습니까?",
                data={"target": tile.teleport_target, "tile": tile}
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
        play_sfx("character", "hp_heal")
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

        # 아이템 생성 실패 시 처리
        if item is None:
            logger.warning("[CHEST] 아이템 생성 실패 - 상자가 비어있음")
            tile.tile_type = TileType.FLOOR
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.CHEST_FOUND,
                message="📦 보물상자를 열었지만 비어있었다..."
            )
        
        # 디버그 로그
        logger.warning(f"[CHEST] 보물상자 처리 시작: {item.name}")
        logger.warning(f"[CHEST] 인벤토리 존재 여부: {self.inventory is not None}")
        if self.inventory is not None:
            logger.warning(f"[CHEST] 인벤토리 슬롯 수: {len(self.inventory.slots)}")
            logger.warning(f"[CHEST] 현재 무게: {self.inventory.current_weight}kg / {self.inventory.max_weight}kg")

        # 보물상자 열기 SFX
        play_sfx("world", "chest_open")
        
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

        # 아이템 획득 SFX
        play_sfx("item", "get_item")

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

        # 아이템 발견 SFX
        play_sfx("world", "item_discover")
        
        # 성공: 아이템 획득
        logger.info(f"아이템 획득: {item.name}")

        # 아이템 획득 SFX
        play_sfx("item", "get_item")

        # 아이템 제거
        tile.tile_type = TileType.FLOOR
        tile.loot_id = None
        
        # 멀티플레이어: 아이템 획득 동기화
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
            if hasattr(self, 'network_manager') and self.network_manager:
                from src.multiplayer.protocol import MessageBuilder
                import asyncio
                try:
                    item_pickup_msg = MessageBuilder.item_picked_up(
                        x=self.player.x,
                        y=self.player.y
                    )
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.network_manager.broadcast(item_pickup_msg))
                    else:
                        loop.run_until_complete(self.network_manager.broadcast(item_pickup_msg))
                    logger.debug(f"아이템 획득 동기화 메시지 전송: ({self.player.x}, {self.player.y})")
                except Exception as e:
                    logger.error(f"아이템 획득 동기화 메시지 전송 실패: {e}", exc_info=True)

        # 아이템 획득 이벤트 발행 (진동용)
        event_bus.publish(Events.WORLD_ITEM_PICKUP, {"item": item, "player": self.player})

        return ExplorationResult(
            success=True,
            event=ExplorationEvent.ITEM_FOUND,
            message=f"✨ 아이템 발견! {item.name} 획득!",
            data={"item": item}
        )

    def _handle_dropped_item(self, tile: Tile) -> ExplorationResult:
        """드롭된 아이템 처리"""
        if not tile.dropped_item:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="아이템이 없습니다"
            )
        
        item = tile.dropped_item
        
        # 인벤토리에 추가
        if self.inventory is None:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message=f"✨ {item.name} 발견! 하지만 인벤토리가 없어서 가져갈 수 없다..."
            )
        
        success = self.inventory.add_item(item)
        
        if not success:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message=f"✨ {item.name} 발견! 하지만 인벤토리가 가득 차서 가져갈 수 없다..."
            )
        
        # 아이템 발견 SFX
        play_sfx("world", "item_discover")
        play_sfx("item", "get_item")
        
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        logger.info(f"드롭된 아이템 획득: {item_name}")
        
        # 타일 정리
        tile.tile_type = TileType.FLOOR
        tile.dropped_item = None
        
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.ITEM_FOUND,
            message=f"✨ {item_name} 획득!",
            data={"item": item}
        )

    def _handle_gold(self, tile: Tile) -> ExplorationResult:
        """드롭된 골드 처리"""
        if tile.gold_amount <= 0:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="골드가 없습니다"
            )
        
        gold_amount = tile.gold_amount
        
        # 인벤토리에 골드 추가
        if self.inventory is None:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message=f"💰 {gold_amount}G 발견! 하지만 인벤토리가 없어서 가져갈 수 없다..."
            )
        
        self.inventory.gold += gold_amount
        
        # 골드 획득 SFX
        play_sfx("world", "item_discover")
        play_sfx("item", "get_item")
        
        logger.info(f"드롭된 골드 획득: {gold_amount}G")
        
        # 타일 정리
        tile.tile_type = TileType.FLOOR
        tile.gold_amount = 0
        
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.ITEM_FOUND,
            message=f"💰 {gold_amount}G 획득!",
            data={"gold": gold_amount}
        )

    def _handle_key(self, tile: Tile) -> ExplorationResult:
        """열쇠 처리"""
        key_id = tile.key_id or "key_unknown"
        
        # 열쇠 획득 SFX
        play_sfx("world", "key_pickup")
        
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
            play_sfx("world", "door_unlock")
            play_sfx("world", "door_open")
            tile.unlock()
            logger.info(f"문 잠금 해제: {key_id}")

            # 문 열기 이벤트 발행 (진동용)
            event_bus.publish(Events.WORLD_DOOR_OPEN, {"tile": tile, "key_id": key_id, "player": self.player})

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
                pass  # 주변 적 추가

        # 주변 적 수에 따라 전투 적 수 결정 (최대 4마리)
        nearby_count = len(combat_enemies)

        if nearby_count == 1:
            # 1마리 조우: 1~3마리 전투
            num_enemies = random.randint(1, 3)
        elif nearby_count == 2:
            # 2마리 조우: 2~4마리 전투
            num_enemies = random.randint(2, 4)
        elif nearby_count == 3:
            # 3마리 조우: 3~4마리 전투
            num_enemies = random.randint(3, 4)
        else:
            # 4마리 이상 조우: 4마리 전투 (최대)
            num_enemies = 4

        has_boss = any(e.is_boss for e in combat_enemies)

        # Debug: 전투 생성 (맵 엔티티 → 실제 전투)
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
                "enemies": combat_enemies,  # 전투 승리 후 제거할 적 엔티티 전달 (실제 참여한 적들)
                "combat_position": (self.player.x, self.player.y),  # 전투 시작 위치
                "dungeon": self.dungeon  # 던전 맵 정보
            }
        )

    def descend_floor(self):
        """다음 층으로"""
        self.floor_number += 1
        logger.info(f"층 이동: {self.floor_number}층")

        # 최대 도달 층수 업데이트
        if self.floor_number > self.game_stats.get("max_floor_reached", 1):
            self.game_stats["max_floor_reached"] = self.floor_number
            logger.info(f"새로운 최대 도달 층수: {self.floor_number}층")

        # 새 던전 생성 필요
        # (이건 외부에서 처리)
        # 참고: 퀘스트 게시판과 상점 리뉴얼은 마을로 복귀할 때만 수행됨 (main.py의 renew_town_services 함수)

    def ascend_floor(self):
        """이전 층으로"""
        if self.floor_number > 1:
            self.floor_number -= 1
            logger.info(f"층 이동: {self.floor_number}층")

    def stun_nearby_enemies(self, position: Tuple[int, int], duration: float = 5.0, range_tiles: int = 10):
        """
        도망 후 주변 적들을 일시정지시킴

        Args:
            position: 전투 위치 (x, y)
            duration: 정지 지속 시간 (초)
            range_tiles: 정지 적용 범위 (타일)
        """
        import time
        current_time = time.time()
        stun_end_time = current_time + duration

        px, py = position
        stunned_count = 0

        for enemy in self.enemies:
            distance = abs(enemy.x - px) + abs(enemy.y - py)
            if distance <= range_tiles:
                enemy.stunned_until = stun_end_time
                enemy.is_chasing = False  # 추적 중단
                stunned_count += 1

        if stunned_count > 0:
            logger.info(f"도망 성공! 주변 {stunned_count}마리 적 {duration}초 동안 정지")

    def _spawn_enemies(self):
        """적 배치"""
        from src.world.enemy_generator import EnemyGenerator
        import random

        # 마을에서는 적 스폰하지 않음
        if hasattr(self, 'is_town') and self.is_town:
            logger.info("[_spawn_enemies] 마을에서는 적을 스폰하지 않습니다.")
            self.enemies = []  # 적 리스트 초기화
            return

        # 층 수에 따라 적 수 결정 (7 + 층*0.3, 최대 12마리)
        base_enemies = 7
        additional = int(self.floor_number * 0.3)  # 층 * 0.3
        num_enemies = min(12, base_enemies + additional)  # 최대 12마리

        # 플레이어 시작 위치 주변을 제외한 바닥 타일에 적 배치
        possible_positions = []
        for x in range(self.dungeon.width):
            for y in range(self.dungeon.height):
                tile = self.dungeon.get_tile(x, y)
                if (tile and tile.tile_type == TileType.FLOOR and
                    abs(x - self.player.x) > 3 and abs(y - self.player.y) > 3):
                    possible_positions.append((x, y))

        # 보스 먼저 배치 (층마다 한 마리씩 꼭 생성)
        if possible_positions:

            # 5층마다 층 보스 (더 강력함), 그 외에는 일반 보스
            is_floor_boss = (self.floor_number % 5 == 0)
            boss = EnemyGenerator.generate_boss(self.floor_number, is_floor_boss=is_floor_boss)

            # 보스를 위한 위치 선택
            if is_floor_boss and self.dungeon.stairs_down:
                # 5층마다: 계단 근처에 보스 배치
                stairs_x, stairs_y = self.dungeon.stairs_down

                # 계단 주변을 BOSS_ROOM 타일로 둘러싸기 (5x5 영역)
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        check_x, check_y = stairs_x + dx, stairs_y + dy
                        if 0 <= check_x < self.dungeon.width and 0 <= check_y < self.dungeon.height:
                            tile = self.dungeon.get_tile(check_x, check_y)
                            # 계단 자체는 제외, 벽도 제외
                            if tile and tile.tile_type == TileType.FLOOR:
                                tile.tile_type = TileType.BOSS_ROOM

                # 보스는 계단에서 2~3칸 떨어진 곳에 배치
                boss_candidates = []
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        distance = abs(dx) + abs(dy)
                        if 2 <= distance <= 3:  # 계단에서 2~3칸 거리
                            boss_x, boss_y = stairs_x + dx, stairs_y + dy
                            if 0 <= boss_x < self.dungeon.width and 0 <= boss_y < self.dungeon.height:
                                tile = self.dungeon.get_tile(boss_x, boss_y)
                                if tile and tile.tile_type == TileType.BOSS_ROOM:
                                    if (boss_x, boss_y) in possible_positions:
                                        boss_candidates.append((boss_x, boss_y))

                # 보스 배치
                if boss_candidates:
                    boss_x, boss_y = random.choice(boss_candidates)
                    boss_enemy = Enemy(x=boss_x, y=boss_y, level=self.floor_number, is_boss=True)
                    boss_enemy.name = boss.name
                    self.enemies.append(boss_enemy)
                    if (boss_x, boss_y) in possible_positions:
                        possible_positions.remove((boss_x, boss_y))
                    logger.info(f"[_spawn_enemies] [WARNING] 층 보스 배치: {boss_enemy.name} at ({boss_x}, {boss_y}) [계단 봉쇄!]")
                else:
                    # 후보가 없으면 일반 위치에 배치
                    boss_positions = [pos for pos in possible_positions if pos[0] > self.dungeon.width // 3]
                    if not boss_positions:
                        boss_positions = possible_positions
                    if boss_positions:
                        boss_x, boss_y = random.choice(boss_positions)
                        boss_enemy = Enemy(x=boss_x, y=boss_y, level=self.floor_number, is_boss=True)
                        boss_enemy.name = boss.name
                        self.enemies.append(boss_enemy)
                        possible_positions.remove((boss_x, boss_y))
                        logger.warning(f"[_spawn_enemies] 층 보스 배치 (계단 근처 배치 실패): {boss_enemy.name} at ({boss_x}, {boss_y})")
            else:
                # 일반 층: 랜덤 위치에 보스 배치 (BOSS_ROOM 타일 없음)
                boss_positions = [pos for pos in possible_positions if pos[0] > self.dungeon.width // 3]
                if not boss_positions:
                    boss_positions = possible_positions

                if boss_positions:
                    boss_x, boss_y = random.choice(boss_positions)
                    boss_enemy = Enemy(x=boss_x, y=boss_y, level=self.floor_number, is_boss=True)
                    boss_enemy.name = boss.name
                    self.enemies.append(boss_enemy)
                    possible_positions.remove((boss_x, boss_y))
                    logger.info(f"[_spawn_enemies] 보스 배치: {boss_enemy.name} at ({boss_x}, {boss_y})")

        # 나머지 일반 적 배치
        if possible_positions:
            remaining_enemies = num_enemies - len(self.enemies)
            if remaining_enemies > 0:
                spawn_positions = random.sample(possible_positions, min(remaining_enemies, len(possible_positions)))

                # 보스가 있으면 수하로 배치할 일반 적 선택
                boss_enemy = None
                minion_count = 0

                for boss in self.enemies:
                    if boss.is_boss:
                        boss_enemy = boss
                        break

                # 보스 수하 배치 (보스 주변 2~3칸)
                if boss_enemy:
                    minion_candidates = []
                    for x, y in spawn_positions:
                        distance = abs(x - boss_enemy.x) + abs(y - boss_enemy.y)
                        if 2 <= distance <= 4:  # 보스 주변 2~4칸
                            minion_candidates.append((x, y))

                    # 최대 2마리의 수하 배치
                    num_minions = min(2, len(minion_candidates))
                    minion_positions = random.sample(minion_candidates, num_minions) if minion_candidates else []

                    for x, y in minion_positions:
                        minion = Enemy(x=x, y=y, level=self.floor_number)
                        minion.is_minion = True
                        minion.leader_id = boss_enemy.id
                        self.enemies.append(minion)
                        spawn_positions.remove((x, y))
                        minion_count += 1
                        logger.info(f"[_spawn_enemies] 보스 수하 배치: {minion.name} (리더: {boss_enemy.name})")

                # 나머지 위치에 일반 적 배치
                for x, y in spawn_positions:
                    enemy = Enemy(x=x, y=y, level=self.floor_number)
                    self.enemies.append(enemy)

        logger.info(f"[_spawn_enemies] 적 {len(self.enemies)}마리 배치 완료 (요청: {num_enemies}마리, 가능한 위치: {len(possible_positions)}개)")
        if len(self.enemies) == 0:
            logger.warning(f"[_spawn_enemies] [WARNING] 적이 스폰되지 않았습니다! possible_positions: {len(possible_positions)}개")
        for i, enemy in enumerate(self.enemies[:5]):  # 처음 5마리만 로그
            logger.info(f"[_spawn_enemies] 적 {i+1}: {enemy.name} ({'보스' if enemy.is_boss else '일반'}) 위치 ({enemy.x}, {enemy.y})")

    def get_enemy_at(self, x: int, y: int) -> Optional[Enemy]:
        """특정 위치의 적 가져오기"""
        # logger.warning(f"[DEBUG] get_enemy_at({x}, {y}) 호출 - 현재 적 {len(self.enemies)}마리")
        for enemy in self.enemies:
            if enemy.x == x and enemy.y == y:
                # 죽은 적은 무시 (이동 가능, 상호작용 불가)
                if not getattr(enemy, 'is_alive', True):
                    continue
                # logger.warning(f"[DEBUG] 적 발견! at ({x}, {y})")
                return enemy
        return None

    def _is_player_at(self, x: int, y: int) -> bool:
        """해당 위치에 플레이어(봇 포함)가 있는지 확인"""
        # 로컬 플레이어 (죽었으면 무시)
        if self.player.x == x and self.player.y == y:
            # 파티 전멸 확인
            all_dead = True
            if hasattr(self.player, 'party'):
                for member in self.player.party:
                    if getattr(member, 'is_alive', True) and getattr(member, 'current_hp', 0) > 0:
                        all_dead = False
                        break
            if not all_dead:
                return True
            
        # 멀티플레이 세션 플레이어
        if hasattr(self, 'session') and self.session:
            for pid, p in self.session.players.items():
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    if p.x == x and p.y == y:
                        # 죽은 플레이어는 무시 (통과 가능)
                        # Player 객체에서 파티 정보 확인 필요
                        # 여기서는 단순화를 위해 살아있다고 가정하되, 실제로는 파티 상태 확인 필요
                        # TODO: 멀티플레이어 파티 상태 동기화 확인
                        return True
        return False

    def remove_enemy(self, enemy: Enemy):
        """적 제거 (전투 승리 후)"""
        if enemy in self.enemies:
            self.enemies.remove(enemy)
            logger.info(f"적 제거: ({enemy.x}, {enemy.y})")

    def _move_all_enemies(self):
        """모든 적 움직임 처리 - 시간 기반 시스템"""
        import time

        if not self.enemies:
            return

        # 새로운 프레임에서 이전 충돌 초기화
        self.collision_enemy = None

        current_time = time.time()

        # 각 적에 대해 이동 간격을 체크하고 이동
        moved_count = 0
        for enemy in self.enemies:
            # 시간 기반 이동 체크: 마지막 이동 이후 설정된 간격이 지났는지 확인
            if current_time - enemy.last_move_time >= enemy.move_interval:
                self._move_enemy(enemy)
                enemy.last_move_time = current_time
                moved_count += 1

                # 이미 충돌한 적이 있으면 더 이상 진행하지 않음 (먼저 충돌한 적과 전투)
                if self.collision_enemy:
                    break

        if moved_count > 0:
            logger.debug(f"[적 이동] {moved_count}마리 적 이동 완료 (시간: {current_time:.2f})")

    def _move_enemy(self, enemy: Enemy):
        """단일 적 움직임 - 고급 AI 시스템 포함"""
        import time

        # 정지 상태 확인 (도망 후)
        current_time = time.time()
        if enemy.stunned_until > current_time:
            # 정지 중이면 움직이지 않음
            return

        # 수하인 경우 보스를 따름
        if enemy.is_minion and enemy.leader_id:
            self._minion_follow_boss(enemy)
            return

        # 플레이어와의 거리 계산
        distance = abs(enemy.x - self.player.x) + abs(enemy.y - self.player.y)

        logger.debug(f"[적 이동] {enemy.name} 위치=({enemy.x}, {enemy.y}), 플레이어 위치=({self.player.x}, {self.player.y}), 거리={distance}, 감지범위={enemy.detection_range}")

        # 플레이어 감지
        if distance <= enemy.detection_range:
            if not enemy.is_chasing:
                logger.info(f"[적 이동] [WARNING] {enemy.name}이(가) 플레이어 감지! (거리: {distance}) - 추적 시작")
                enemy.chase_turns = 0  # 처음 감지할 때만 카운터 리셋
            enemy.is_chasing = True
            enemy.morale = min(100.0, enemy.morale + 5.0)  # 추적 중이면 사기 증가

            # 보스인 경우 수하들도 참전
            if enemy.is_boss:
                self._boss_summon_minions(enemy)

        # 추적 중일 때
        if enemy.is_chasing:
            enemy.chase_turns += 1

            # 포기 조건 판단 (사기 기반 + 전술적 재평가)
            should_retreat = self._should_enemy_retreat(enemy, distance)

            if should_retreat:
                enemy.is_chasing = False
                enemy.chase_turns = 0
                enemy.morale = max(0.0, enemy.morale - 20.0)  # 포기하면 사기 감소
                logger.info(f"적 {enemy.name}이(가) 추적 포기 (사기: {enemy.morale:.1f}, 거리: {distance})")

                # 증원 호출 여부 판단 (포기 전에)
                if enemy.reinforcement_called is False:
                    self._try_call_reinforcement(enemy)

            # 추적 중이면 플레이어 방향으로 이동
            if enemy.is_chasing:
                self._move_enemy_towards(enemy, self.player.x, self.player.y)

                # 포위 전략: 다른 적들에게 신호 전달
                self._coordinate_encirclement(enemy)

        # 추적하지 않을 때
        if not enemy.is_chasing:
            # 원래 위치로 복귀
            if enemy.x != enemy.spawn_x or enemy.y != enemy.spawn_y:
                self._move_enemy_towards(enemy, enemy.spawn_x, enemy.spawn_y)

            # 사기 회복 (휴식 중)
            enemy.morale = min(100.0, enemy.morale + 2.0)

        # 적 이동 후 플레이어와의 충돌 확인 (시간 기반 이동 시스템에서 필요)
        if enemy.x == self.player.x and enemy.y == self.player.y:
            logger.info(f"[전투 트리거] 적이 플레이어와 충돌: {enemy.name} at ({enemy.x}, {enemy.y})")
            # 충돌 적 저장 (world_ui.py에서 감지하여 전투 트리거)
            self.collision_enemy = enemy

    def _find_path_astar(self, start_x: int, start_y: int, goal_x: int, goal_y: int, max_steps: int = 20) -> Optional[List[Tuple[int, int]]]:
        """
        A* 알고리즘으로 경로 찾기

        Args:
            start_x, start_y: 시작 위치
            goal_x, goal_y: 목표 위치
            max_steps: 최대 탐색 깊이 (성능 최적화)

        Returns:
            경로 리스트 [(x1, y1), (x2, y2), ...] 또는 None
        """
        def heuristic(x, y):
            """휴리스틱 함수: 맨하탄 거리"""
            return abs(x - goal_x) + abs(y - goal_y)

        # 우선순위 큐: (f_score, counter, x, y)
        open_set = []
        counter = 0  # 같은 f_score일 때 순서 보장
        heapq.heappush(open_set, (heuristic(start_x, start_y), counter, start_x, start_y))

        # 방문한 노드와 비용 추적
        came_from = {}
        g_score = {(start_x, start_y): 0}
        visited = set()

        # 4방향 이동 (게임은 대각선 이동 미지원)
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1)  # 상하좌우만
        ]

        while open_set and len(visited) < max_steps * max_steps:
            _, _, current_x, current_y = heapq.heappop(open_set)

            if (current_x, current_y) in visited:
                continue

            visited.add((current_x, current_y))

            # 목표 도달
            if current_x == goal_x and current_y == goal_y:
                # 경로 역추적
                path = []
                current = (current_x, current_y)
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append((start_x, start_y))
                path.reverse()
                return path

            # 이웃 노드 탐색
            for dx, dy in directions:
                neighbor_x = current_x + dx
                neighbor_y = current_y + dy

                # 범위 체크
                if (neighbor_x, neighbor_y) in visited:
                    continue

                # 이동 가능 여부 확인
                if not self.dungeon.is_walkable(neighbor_x, neighbor_y):
                    continue

                # 다른 적이 있는지 확인 (다른 적이 있으면 우회)
                if self.get_enemy_at(neighbor_x, neighbor_y):
                    continue

                # 비용 계산 (4방향 이동, 모두 동일 비용)
                tentative_g_score = g_score[(current_x, current_y)] + 1.0

                if (neighbor_x, neighbor_y) not in g_score or tentative_g_score < g_score[(neighbor_x, neighbor_y)]:
                    # 더 좋은 경로 찾음
                    came_from[(neighbor_x, neighbor_y)] = (current_x, current_y)
                    g_score[(neighbor_x, neighbor_y)] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbor_x, neighbor_y)
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor_x, neighbor_y))

        # 경로를 찾을 수 없음
        return None

    def _move_enemy_towards(self, enemy: Enemy, target_x: int, target_y: int):
        """적을 목표 위치로 한 칸 이동 (A* 경로 찾기 이용)"""
        # 목표 재설정: 가장 가까운 플레이어(봇 포함) 찾기
        target = self._find_nearest_target(enemy)
        if target:
            target_x, target_y = target.x, target.y

        old_x, old_y = enemy.x, enemy.y

        # 목표에 이미 도착했는가?
        if enemy.x == target_x and enemy.y == target_y:
            return

        # A* 경로 찾기 시도
        path = self._find_path_astar(enemy.x, enemy.y, target_x, target_y)

        if path and len(path) > 1:
            # 경로가 있으면 다음 지점으로 이동
            next_x, next_y = path[1]
            new_x, new_y = next_x, next_y
        else:
            # 경로가 없으면 맨하탄 거리 기반 대체 이동
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
            if random.random() < 0.5 and dx != 0:
                new_x, new_y = enemy.x + dx, enemy.y
            elif dy != 0:
                new_x, new_y = enemy.x, enemy.y + dy
            elif dx != 0:
                new_x, new_y = enemy.x + dx, enemy.y
            else:
                return

        # 이동 가능 여부 확인
        if self.dungeon.is_walkable(new_x, new_y):
            # 플레이어 위치로 이동하려고 하면 전투 트리거
            player_at_target = self._is_player_at(new_x, new_y)
            if player_at_target:
                # 적이 플레이어 위치로 이동하려고 함 - 전투 트리거
                enemy.x = new_x
                enemy.y = new_y
                logger.info(f"[적 이동] {enemy.name}이(가) 플레이어 위치로 이동 - 전투 트리거 예정")
                return

            # 다른 적과 겹치지 않는지 확인
            enemy_at_target = self.get_enemy_at(new_x, new_y)

            if not enemy_at_target:
                enemy.x = new_x
                enemy.y = new_y
                logger.debug(f"[적 이동] {enemy.name} 이동: ({old_x}, {old_y}) -> ({new_x}, {new_y})")
            else:
                logger.debug(f"[적 이동] {enemy.name} 이동 실패: 목표 타일이 차있음 ({new_x}, {new_y})")
        else:
            logger.debug(f"[적 이동] {enemy.name} 이동 실패: 목표 타일이 이동 불가능 ({new_x}, {new_y})")

    def _minion_follow_boss(self, minion: Enemy):
        """수하가 보스를 따라다님

        Args:
            minion: 수하 적
        """
        # 보스 찾기
        boss = None
        for enemy in self.enemies:
            if enemy.id == minion.leader_id:
                boss = enemy
                break

        if not boss:
            # 보스를 찾을 수 없으면 일반 적처럼 행동
            minion.is_minion = False
            minion.leader_id = None
            self._move_enemy(minion)
            return

        # 보스와의 거리
        boss_distance = abs(minion.x - boss.x) + abs(minion.y - boss.y)

        # 보스가 추적 중이면 같이 참전
        if boss.is_chasing:
            minion.is_chasing = True
            minion.chase_turns = 0
            minion.morale = 80.0  # 보스와 함께이면 사기 높음

            # 보스 주변을 떠나지 말기
            if boss_distance > 8:
                # 보스 쪽으로 이동
                self._move_enemy_towards(minion, boss.x, boss.y)
            else:
                # 플레이어 쪽으로 이동
                self._move_enemy_towards(minion, self.player.x, self.player.y)
                logger.debug(f"[수하] {minion.name}이(가) 리더 {boss.name}과 함께 추적")
        else:
            # 보스가 추적 안 함: 보스 근처 유지
            if boss_distance > 5:
                self._move_enemy_towards(minion, boss.x, boss.y)
            minion.is_chasing = False

    def _boss_summon_minions(self, boss: Enemy):
        """보스가 주변 수하들을 소집

        Args:
            boss: 보스 적
        """
        # 이미 소집 상태면 중복 호출 방지
        if boss.reinforcement_called:
            return

        boss.reinforcement_called = True

        # 보스의 수하들 찾기
        minions = []
        for enemy in self.enemies:
            if enemy.leader_id == boss.id and enemy.is_minion:
                distance = abs(enemy.x - boss.x) + abs(enemy.y - boss.y)
                minions.append((distance, enemy))

        if minions:
            logger.info(f"[보스 소집] {boss.name}이(가) {len(minions)}명의 수하를 이끌고 전투 개시!")
            # 모든 수하가 참전
            for _, minion in minions:
                minion.is_chasing = True
                minion.chase_turns = 0
                minion.morale = 100.0  # 최고 사기
                logger.info(f"[보스 소집] {minion.name}이(가) {boss.name}의 소집에 응답!")

    def _should_enemy_retreat(self, enemy: Enemy, distance: int) -> bool:
        """적이 후퇴해야 하는지 판단 (사기 + 전술적 재평가)

        Returns:
            True if enemy should retreat, False otherwise
        """
        # 조건 1: 너무 오래 추적
        if enemy.chase_turns > enemy.max_chase_turns:
            return True

        # 조건 2: 플레이어가 너무 멀리 도망감
        if distance > enemy.max_chase_distance:
            return True

        # 조건 3: 사기가 매우 낮음 (20% 이하 + 우세하지 못함)
        if enemy.morale < 20.0:
            # 아군 개수 확인
            nearby_allies = len(self._get_nearby_enemies(enemy, detection_range=10))
            allied_strength = nearby_allies  # 단순히 개수로 판단

            # 플레이어 파티 크기
            enemy_strength = len(self.player.party)

            if allied_strength <= enemy_strength:
                return True

        # 조건 4: 매우 약해짐 (HP 50% 이하) + 도움을 받지 못함
        if hasattr(enemy, 'hp') and hasattr(enemy, 'max_hp'):
            hp_ratio = enemy.hp / enemy.max_hp if enemy.max_hp > 0 else 1.0
            if hp_ratio < 0.5:
                # 증원 온 것이 없으면 도망
                nearby_allies = len(self._get_nearby_enemies(enemy, detection_range=7))
                if nearby_allies < 2:  # 자신 포함 1명이면 혼자라는 뜻
                    return True

        return False

    def _try_call_reinforcement(self, enemy: Enemy):
        """신호 기반 증원 시스템

        적이 신호를 보내면 신호 범위 내의 다른 적들이 응답
        """
        # 신호 쿨다운 확인
        current_turn = self.current_turn if hasattr(self, 'current_turn') else 0
        if current_turn - enemy.last_signal_turn < enemy.signal_cooldown:
            return  # 쿨다운 중

        # 신호 전송
        enemy.signal_sent = True
        enemy.signal_position_x = enemy.x
        enemy.signal_position_y = enemy.y
        enemy.last_signal_turn = current_turn

        logger.info(f"[신호 시스템] {enemy.name}이(가) ({enemy.x}, {enemy.y})에서 구조 신호를 보냈습니다!")

        # 신호를 받을 수 있는 적 찾기 (신호 범위 내)
        responders = []
        for other_enemy in self.enemies:
            if other_enemy is enemy:
                continue

            # 신호 범위 확인
            signal_distance = abs(other_enemy.x - enemy.signal_position_x) + abs(other_enemy.y - enemy.signal_position_y)
            if signal_distance <= enemy.signal_range:
                # 아직 추적하지 않고 있는 적만 응답
                if not other_enemy.is_chasing:
                    responders.append(other_enemy)

        # 응답한 적들 정렬 (가까운 순)
        responders.sort(key=lambda e: abs(e.x - enemy.signal_position_x) + abs(e.y - enemy.signal_position_y))

        # 최대 3마리까지 응답
        responding_enemies = responders[:3]

        if responding_enemies:
            logger.info(f"[신호 시스템] {len(responding_enemies)}마리 적이 신호에 응답했습니다!")

            for responder in responding_enemies:
                responder.is_chasing = True
                responder.chase_turns = 0
                responder.morale = 85.0  # 신호에 응답한 적들의 사기
                logger.info(f"[신호 시스템] {responder.name}이(가) {enemy.name}의 신호에 응답하여 출동!")

    def _coordinate_encirclement(self, leader: Enemy):
        """포위 전략: 추적 중인 적들이 플레이어 주변에 포지셔닝

        리더 적이 플레이어를 추적 중일 때, 근처 적들이 플레이어를
        다양한 방향에서 포위하도록 유도
        """
        if leader.encirclement_role != "leader":
            leader.encirclement_role = "leader"  # 첫 주자가 리더 역할

        # 주변 적들 찾기
        nearby_enemies = self._get_nearby_enemies(leader, detection_range=12)

        for ally in nearby_enemies:
            if ally is leader:
                continue  # 자신 제외

            # 이미 추적 중이면 포위 역할 할당
            if ally.is_chasing:
                if ally.encirclement_role == "none":
                    ally.encirclement_role = "flanker"
                    logger.debug(f"[포위 전략] {ally.name}이(가) 옆날개 역할 시작")

                # 옆날개 역할: 플레이어 주변의 다른 위치로 포지셔닝
                self._move_enemy_to_flanking_position(ally, leader)

    def _move_enemy_to_flanking_position(self, flanker: Enemy, leader: Enemy):
        """포위 적을 옆날개 위치로 이동

        리더의 반대편 또는 옆쪽으로 이동하도록 유도
        """
        player_x, player_y = self.player.x, self.player.y
        leader_x, leader_y = leader.x, leader.y
        flanker_x, flanker_y = flanker.x, flanker.y

        # 리더에서 플레이어로의 방향 벡터
        dx = player_x - leader_x
        dy = player_y - leader_y

        # 수직 방향의 포지션 선택 (좌측 또는 우측)
        # 왼쪽 (ccw 90도) 또는 오른쪽 (cw 90도)
        use_left_flank = (flanker_x + flanker_y) % 2 == 0

        if use_left_flank:
            # 왼쪽 옆날개: dy 방향으로 이동
            target_x = player_x - dy
            target_y = player_y + dx
        else:
            # 오른쪽 옆날개: 반대쪽
            target_x = player_x + dy
            target_y = player_y - dx

        # 목표 위치가 유효한지 확인
        if self.dungeon.is_walkable(target_x, target_y):
            self._move_enemy_towards(flanker, target_x, target_y)
        else:
            # 목표가 불가능하면 플레이어 주변 어디든 이동
            self._move_enemy_towards(flanker, player_x, player_y)

    def _get_nearby_enemies(self, enemy: Enemy, detection_range: int = 10) -> List[Enemy]:
        """주변 일정 거리 내의 다른 적들 반환

        Args:
            enemy: 기준 적
            detection_range: 탐지 범위

        Returns:
            거리 순으로 정렬된 적 리스트 (가까운 순)
        """
        nearby = []

        for other_enemy in self.enemies:
            if other_enemy is enemy:
                continue

            distance = abs(enemy.x - other_enemy.x) + abs(enemy.y - other_enemy.y)
            if distance <= detection_range:
                nearby.append((distance, other_enemy))

        # 거리 순으로 정렬
        nearby.sort(key=lambda x: x[0])
        return [e for _, e in nearby]

    def _find_nearest_target(self, enemy: Enemy) -> Any:
        """적에게 가장 가까운 대상(플레이어 또는 봇) 찾기"""
        targets = []
        
        # 1. 로컬 플레이어
        targets.append(self.player)
        
        # 2. 멀티플레이 세션 플레이어들 (봇 포함)
        if hasattr(self, 'session') and self.session:
            for pid, p in self.session.players.items():
                # 로컬 플레이어는 이미 추가했으므로 제외 (PID 비교가 안전하지만 객체 비교도 가능)
                if pid != getattr(self.player, 'player_id', None):
                    targets.append(p)
                    
        # 가장 가까운 타겟 찾기
        nearest = None
        min_dist = float('inf')
        
        for t in targets:
            if hasattr(t, 'x') and hasattr(t, 'y'):
                dist = abs(enemy.x - t.x) + abs(enemy.y - t.y)
                if dist < min_dist:
                    min_dist = dist
                    nearest = t
                    
        return nearest

    def _is_player_at(self, x: int, y: int) -> bool:
        """해당 위치에 플레이어(봇 포함)가 있는지 확인"""
        # 로컬 플레이어
        if self.player.x == x and self.player.y == y:
            return True
            
        # 멀티플레이 세션 플레이어
        if hasattr(self, 'session') and self.session:
            for pid, p in self.session.players.items():
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    if p.x == x and p.y == y:
                        return True
        return False

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
        
        # 스위치 SFX
        if tile.switch_active:
            play_sfx("world", "switch_on")
        else:
            play_sfx("world", "switch_off")
        
        # 스위치가 제어하는 대상 처리 (예: 문 열기)
        if tile.switch_target:
            # switch_target이 문 ID인 경우 해당 문 열기
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    target_tile = self.dungeon.get_tile(x, y)
                    if target_tile and target_tile.key_id == tile.switch_target:
                        if target_tile.tile_type == TileType.LOCKED_DOOR:
                            play_sfx("world", "door_unlock")
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
            play_sfx("world", "pressure_plate")
            tile.switch_active = True
            
            # 압력판이 제어하는 대상 처리
            if tile.switch_target:
                for y in range(self.dungeon.height):
                    for x in range(self.dungeon.width):
                        target_tile = self.dungeon.get_tile(x, y)
                        if target_tile and target_tile.key_id == tile.switch_target:
                            if target_tile.tile_type == TileType.LOCKED_DOOR:
                                play_sfx("world", "door_unlock")
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
        play_sfx("world", "lever")
        tile.switch_active = not tile.switch_active
        
        # 레버가 제어하는 대상 처리
        if tile.switch_target:
            for y in range(self.dungeon.height):
                for x in range(self.dungeon.width):
                    target_tile = self.dungeon.get_tile(x, y)
                    if target_tile and target_tile.key_id == tile.switch_target:
                        if target_tile.tile_type == TileType.LOCKED_DOOR:
                            play_sfx("world", "door_unlock")
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
        """시공 연구자 NPC (선택지 제공)"""
        tile.npc_interacted = True
        
        # 선택지가 있는 NPC로 처리 (UI에서 선택지 제공)
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NPC_INTERACTION,
            message="시공 연구자: '시공교란의 원인을 조사 중입니다. 도움이 필요하신가요?'\n어떤 도움을 받으시겠습니까?",
            data={"npc_subtype": "time_researcher", "has_choices": True}
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
        """상인 NPC (선택지 제공: 구매/판매)"""
        if not self.inventory:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NPC_INTERACTION,
                message="상인: '인벤토리가 없어서 거래할 수 없습니다.'",
                data={"npc_subtype": "merchant"}
            )
        
        # 선택지가 있는 NPC로 처리 (UI에서 구매/판매 선택)
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NPC_INTERACTION,
            message="상인: '안녕하세요! 무엇을 도와드릴까요?'\n어떤 서비스를 원하시나요?",
            data={"npc_subtype": "merchant", "has_choices": True}
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
        """신비한 상인 NPC (선택지 제공: 구매/판매)"""
        if not self.inventory:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NPC_INTERACTION,
                message="신비한 상인: '인벤토리가 없어서 거래할 수 없습니다.'",
                data={"npc_subtype": "mysterious_merchant"}
            )
        
        # 선택지가 있는 NPC로 처리 (UI에서 구매/판매 선택)
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NPC_INTERACTION,
            message="신비한 상인: '시공의 힘이 깃든 물건들을 팝니다...'\n어떤 서비스를 원하시나요?",
            data={"npc_subtype": "mysterious_merchant", "has_choices": True}
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

    def _move_npcs(self):
        """모든 NPC 움직임 처리 (랜덤 배회)"""
        # 던전 전체를 스캔하여 NPC 타일 찾기
        npc_positions = []
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                tile = self.dungeon.get_tile(x, y)
                if tile and tile.tile_type == TileType.NPC:
                    npc_positions.append((x, y, tile))
        
        # 각 NPC를 랜덤하게 이동
        for x, y, npc_tile in npc_positions:
            # NPC는 상호작용하지 않은 경우에만 이동 (상인 등은 제외)
            if npc_tile.npc_interacted:
                continue
            
            # 30% 확률로 이동 (적보다 덜 자주 이동)
            if random.random() < 0.3:
                directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
                random.shuffle(directions)  # 랜덤 순서
                
                for dx, dy in directions:
                    new_x = x + dx
                    new_y = y + dy
                    
                    # 이동 가능한 위치인지 확인
                    if self.dungeon.is_walkable(new_x, new_y):
                        new_tile = self.dungeon.get_tile(new_x, new_y)
                        # 다른 NPC나 적, 플레이어와 겹치지 않도록 체크
                        if (new_tile and new_tile.tile_type != TileType.NPC and
                            not self.get_enemy_at(new_x, new_y) and
                            (new_x, new_y) != (self.player.x, self.player.y)):
                            
                            # 기존 위치를 FLOOR로 변경
                            self.dungeon.set_tile(x, y, TileType.FLOOR)
                            
                            # 새 위치에 NPC 배치
                            self.dungeon.set_tile(
                                new_x, new_y,
                                TileType.NPC,
                                npc_id=npc_tile.npc_id,
                                npc_type=npc_tile.npc_type,
                                npc_subtype=npc_tile.npc_subtype,
                                npc_interacted=npc_tile.npc_interacted
                            )
                            logger.debug(f"NPC 이동: {npc_tile.npc_subtype} ({x}, {y}) -> ({new_x}, {new_y})")
                            break  # 이동 성공하면 중단

    def _handle_altar(self, tile: Tile) -> ExplorationResult:
        """제단 처리 (버프/회복)"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 제단입니다."
            )

        # 제단 축복 SFX
        play_sfx("character", "hp_heal")
        play_sfx("character", "status_buff")
        
        # 파티 전체 회복 및 버프
        if self.player and self.player.party:
            for member in self.player.party:
                if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                    member.current_hp = min(member.current_hp + member.max_hp // 2, member.max_hp)
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = min(member.current_mp + member.max_mp // 2, member.max_mp)

        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="제단의 축복을 받았습니다! HP와 MP가 회복되었습니다."
        )

    def _handle_shrine(self, tile: Tile) -> ExplorationResult:
        """신전 처리 (회복/보상)"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 신전입니다."
            )

        # 신전 축복 SFX
        play_sfx("character", "hp_heal")
        play_sfx("character", "status_buff")
        
        # 파티 전체 완전 회복
        if self.player and self.player.party:
            for member in self.player.party:
                if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                    member.current_hp = member.max_hp
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = member.max_mp
                # 상태이상 제거
                if hasattr(member, 'status_manager'):
                    member.status_manager.clear_all_effects()

        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="신전의 축복을 받았습니다! 모든 상태가 회복되었습니다."
        )

    def _handle_portal(self, tile: Tile) -> ExplorationResult:
        """포털 처리 (텔레포트)"""
        if not tile.teleport_target:
            # 랜덤 위치로 텔레포트
            import random
            if self.dungeon.rooms:
                target_room = random.choice(self.dungeon.rooms)
                target_x = random.randint(target_room.x1 + 1, target_room.x2 - 1)
                target_y = random.randint(target_room.y1 + 1, target_room.y2 - 1)
                tile.teleport_target = (target_x, target_y)

        if tile.teleport_target:
            play_sfx("world", "teleport")
            self.player.x, self.player.y = tile.teleport_target
            self.update_fov()
            return ExplorationResult(
                success=True,
                event=ExplorationEvent.NONE,
                message="포털을 통해 다른 곳으로 이동했습니다!"
            )

        return ExplorationResult(
            success=False,
            event=ExplorationEvent.NONE,
            message="포털이 작동하지 않습니다."
        )

    def _handle_crystal(self, tile: Tile) -> ExplorationResult:
        """크리스탈 처리 (MP 회복)"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 크리스탈입니다."
            )

        # 크리스탈 SFX
        play_sfx("character", "mp_heal")
        
        # 파티 전체 MP 회복
        if self.player and self.player.party:
            for member in self.player.party:
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = member.max_mp

        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="크리스탈의 힘으로 MP가 완전히 회복되었습니다!"
        )

    def _handle_mana_well(self, tile: Tile) -> ExplorationResult:
        """마나 샘 처리 (MP 회복)"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 마나 샘입니다."
            )

        # 마나 샘 SFX
        play_sfx("character", "mp_heal")
        
        # 파티 전체 MP 회복 (일부)
        if self.player and self.player.party:
            for member in self.player.party:
                if hasattr(member, 'current_mp') and hasattr(member, 'max_mp'):
                    member.current_mp = min(member.current_mp + member.max_mp // 3, member.max_mp)

        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="마나 샘에서 MP를 회복했습니다!"
        )

    def _handle_magic_circle(self, tile: Tile) -> ExplorationResult:
        """마법진 처리 (랜덤 효과)"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 마법진입니다."
            )

        import random
        effect = random.choice(["heal", "buff", "teleport"])
        
        if effect == "heal":
            if self.player and self.player.party:
                for member in self.player.party:
                    if hasattr(member, 'current_hp') and hasattr(member, 'max_hp'):
                        member.current_hp = min(member.current_hp + member.max_hp // 2, member.max_hp)
            message = "마법진이 파티를 치유했습니다!"
        elif effect == "buff":
            # 버프 효과는 추후 구현
            message = "마법진의 힘이 느껴집니다... (버프 효과 미구현)"
        else:  # teleport
            if self.dungeon.rooms:
                target_room = random.choice(self.dungeon.rooms)
                target_x = random.randint(target_room.x1 + 1, target_room.x2 - 1)
                target_y = random.randint(target_room.y1 + 1, target_room.y2 - 1)
                self.player.x, self.player.y = target_x, target_y
                self.update_fov()
                message = "마법진이 당신을 다른 곳으로 이동시켰습니다!"

        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message=message
        )

    def _handle_sacrifice_altar(self, tile: Tile) -> ExplorationResult:
        """희생 제단 처리 (HP 소모하여 보상)"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 제단입니다."
            )

        # 플레이어 HP의 25% 소모하여 골드 획득
        if self.player:
            hp_cost = max(1, self.player.max_hp // 4)
            if self.player.current_hp > hp_cost:
                self.player.current_hp -= hp_cost
                gold_gained = hp_cost * 2
                if self.inventory:
                    self.inventory.add_gold(gold_gained)
                tile.used = True
                return ExplorationResult(
                    success=True,
                    event=ExplorationEvent.NONE,
                    message=f"제단에 HP {hp_cost}를 희생하여 골드 {gold_gained}을 얻었습니다!"
                )
            else:
                return ExplorationResult(
                    success=False,
                    event=ExplorationEvent.NONE,
                    message="HP가 부족하여 제단을 사용할 수 없습니다."
                )

        return ExplorationResult(
            success=False,
            event=ExplorationEvent.NONE,
            message="제단을 사용할 수 없습니다."
        )

    def _handle_treasure_map(self, tile: Tile) -> ExplorationResult:
        """보물 지도 처리"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 보물 지도입니다."
            )

        # 보물 위치 힌트 제공 (미구현)
        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="보물 지도를 발견했습니다! (기능 미구현)"
        )

    def _handle_riddle_stone(self, tile: Tile) -> ExplorationResult:
        """수수께끼 돌 처리"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 사용한 수수께끼 돌입니다."
            )

        # 수수께끼 풀기 (미구현)
        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="수수께끼 돌을 발견했습니다! (기능 미구현)"
        )

    def _handle_pedestal(self, tile: Tile) -> ExplorationResult:
        """받침대 처리 (아이템 올려놓기)"""
        # 아이템 올려놓기 기능 (미구현)
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="받침대를 발견했습니다! (기능 미구현)"
        )

    def _handle_button(self, tile: Tile) -> ExplorationResult:
        """버튼 처리"""
        if hasattr(tile, 'used') and tile.used:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 누른 버튼입니다."
            )

        # 버튼 SFX
        play_sfx("world", "button")
        
        # 버튼 활성화 (미구현)
        tile.used = True
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="버튼을 눌렀습니다! (기능 미구현)"
        )

    def _handle_secret_door(self, tile: Tile) -> ExplorationResult:
        """비밀 문 처리"""
        if hasattr(tile, 'revealed') and tile.revealed:
            return ExplorationResult(
                success=False,
                event=ExplorationEvent.NONE,
                message="이미 발견한 비밀 문입니다."
            )

        # 비밀 문 발견 및 열기
        play_sfx("world", "door_open")
        tile.revealed = True
        tile.walkable = True
        tile.transparent = True
        tile.tile_type = TileType.DOOR
        return ExplorationResult(
            success=True,
            event=ExplorationEvent.NONE,
            message="비밀 문을 발견했습니다!"
        )
