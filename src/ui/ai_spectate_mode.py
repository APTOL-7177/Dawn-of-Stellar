"""
AI 관전 모드 - AI가 자동으로 게임을 플레이하는 것을 관전

Features:
- AI 파티 자동 구성
- AI 전투 자동 진행
- AI 탐험 자동 진행
- AI 판단 해설 실시간 표시
- 실제 게임 화면과 연동
"""

import tcod.console
import tcod.event
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

from src.core.logger import get_logger
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler


logger = get_logger("ai_spectate")


# AI 해설을 저장할 전역 변수 (게임 UI에서 접근)
_ai_commentary: List[str] = []
_ai_current_action: str = ""
_ai_mode_enabled: bool = False

# 버그 헌터 로그
_bug_reports: List[Dict] = []
_action_history: List[str] = []


def add_ai_commentary(text: str):
    """AI 해설 추가 (게임 어디서든 호출 가능)"""
    global _ai_commentary
    _ai_commentary.append(text)
    if len(_ai_commentary) > 8:
        _ai_commentary.pop(0)
    logger.info(f"[AI] {text}")


def get_ai_commentary() -> List[str]:
    """AI 해설 목록 반환"""
    return _ai_commentary.copy()


def set_ai_action(action: str):
    """현재 AI 행동 설정"""
    global _ai_current_action
    _ai_current_action = action


def get_ai_action() -> str:
    """현재 AI 행동 반환"""
    return _ai_current_action


def is_ai_mode() -> bool:
    """AI 모드 여부"""
    return _ai_mode_enabled


def set_ai_mode(enabled: bool):
    """AI 모드 설정"""
    global _ai_mode_enabled, _ai_commentary, _bug_reports, _action_history
    _ai_mode_enabled = enabled
    if enabled:
        _ai_commentary = []
        _bug_reports = []
        _action_history = []


def log_bug(error_type: str, message: str, tb: str = "", game_state: Dict = None):
    """버그 기록"""
    import json
    from pathlib import Path
    from datetime import datetime
    
    global _bug_reports, _action_history
    
    bug = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "error_message": message,
        "traceback": tb,
        "game_state": game_state or {},
        "action_history": _action_history[-20:]
    }
    _bug_reports.append(bug)
    
    # 즉시 파일로 저장
    report_dir = Path("logs/bug_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    bug_file = report_dir / f"bug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{error_type}.json"
    
    with open(bug_file, 'w', encoding='utf-8') as f:
        json.dump(bug, f, indent=2, ensure_ascii=False)
    
    logger.error(f"🐛 버그 발견! {error_type}: {message}")
    logger.error(f"   저장됨: {bug_file}")
    add_ai_commentary(f"🐛 {error_type}: {message[:30]}")


def log_action(action: str):
    """행동 기록"""
    from datetime import datetime
    global _action_history
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    _action_history.append(f"[{timestamp}] {action}")
    
    if len(_action_history) > 100:
        _action_history.pop(0)


def get_bug_count() -> int:
    """발견된 버그 수"""
    return len(_bug_reports)


@dataclass
class AICommentary:
    """AI 해설"""
    text: str
    timestamp: float
    category: str = "action"  # action, thinking, warning, success


class AISpectateUI:
    """AI 관전 UI"""
    
    def __init__(self, console: tcod.console.Console):
        self.console = console
        self.commentary_log: List[AICommentary] = []
        self.max_log_size = 10
        self.current_action = ""
        self.ai_thinking = ""
        self.stats = {
            "battles_won": 0,
            "battles_lost": 0,
            "floors_cleared": 0,
            "current_floor": 1
        }
        
    def add_commentary(self, text: str, category: str = "action"):
        """해설 추가"""
        self.commentary_log.append(AICommentary(
            text=text,
            timestamp=time.time(),
            category=category
        ))
        if len(self.commentary_log) > self.max_log_size:
            self.commentary_log.pop(0)
    
    def render_commentary_panel(self, x: int, y: int, width: int, height: int):
        """해설 패널 렌더링"""
        # 패널 배경
        for dy in range(height):
            for dx in range(width):
                self.console.print(x + dx, y + dy, " ", bg=(20, 20, 30))
        
        # 제목
        title = "🤖 AI 해설"
        self.console.print(x + 1, y, title, fg=(255, 215, 0))
        
        # 해설 로그
        log_y = y + 2
        for i, comment in enumerate(self.commentary_log[-8:]):
            if log_y + i >= y + height - 1:
                break
            
            # 카테고리별 색상
            if comment.category == "thinking":
                color = (150, 150, 255)  # 파란색 - 생각
                prefix = "💭"
            elif comment.category == "warning":
                color = (255, 200, 100)  # 노란색 - 경고
                prefix = "⚠️"
            elif comment.category == "success":
                color = (100, 255, 100)  # 녹색 - 성공
                prefix = "✅"
            else:
                color = (200, 200, 200)  # 회색 - 일반
                prefix = "▶"
            
            # 텍스트 자르기
            max_text_len = width - 4
            text = comment.text[:max_text_len]
            
            self.console.print(x + 1, log_y + i, f"{prefix} {text}", fg=color)
    
    def render_stats_panel(self, x: int, y: int, width: int):
        """통계 패널 렌더링"""
        self.console.print(x, y, f"🏆 승리: {self.stats['battles_won']}", fg=(100, 255, 100))
        self.console.print(x, y + 1, f"💀 패배: {self.stats['battles_lost']}", fg=(255, 100, 100))
        self.console.print(x, y + 2, f"🏔️ 현재 층: {self.stats['current_floor']}", fg=(200, 200, 255))
    
    def render_current_action(self, x: int, y: int):
        """현재 행동 표시"""
        if self.current_action:
            self.console.print(x, y, f"현재: {self.current_action}", fg=(255, 255, 255))
        if self.ai_thinking:
            self.console.print(x, y + 1, f"생각: {self.ai_thinking[:40]}...", fg=(150, 150, 255))


def run_ai_spectate_mode(console: tcod.console.Console, context: tcod.context.Context) -> Dict[str, Any]:
    """
    AI 관전 모드 실행 - 실제 게임 화면 사용
    
    Returns:
        결과 딕셔너리
    """
    from src.multiplayer.llm_player_bot import (
        create_auto_play_ai,
        get_available_jobs,
        PlayStyle,
        GameStateConverter,
        ExplorationState
    )
    from src.core.config import get_config
    from src.persistence.meta_progress import get_meta_progress
    from src.ui.input_handler import GameAction
    
    logger.info("AI 관전 모드 시작 (실제 게임 화면)")
    set_ai_mode(True)
    add_ai_commentary("🤖 AI 관전 모드 시작!")
    
    # AutoPlayAI 인스턴스 생성 - 즉시 LLM 연동 테스트
    ai = None
    use_llm = True

    try:
        from src.multiplayer.llm_player_bot import create_auto_play_ai, PlayStyle
        ai = create_auto_play_ai(model="qwen3:0.6b", style=PlayStyle.BALANCED)
        add_ai_commentary("🤖 LLM AI 초기화 성공!")
        logger.info("[AI] LLM AutoPlayAI 생성 완료")

        # 즉시 LLM 연동 테스트
        add_ai_commentary("🧪 LLM 연동 테스트 중...")
        test_state = ExplorationState(
            current_floor=0,
            current_position=(0, 0),
            visible_tiles=[],
            discovered_rooms=1,
            total_rooms=5,
            nearby_enemies=[],
            nearby_items=[],
            nearby_exits=[],
            party_hp_percent=100,
            party_mp_percent=100,
            has_healing_point=False,
            floor_type="town",
            stairs_down_position=(1, 1),
            unexplored_directions=[(0, 1), (1, 0)]
        )
        test_action = ai.decide_exploration_action(test_state)
        add_ai_commentary(f"✅ LLM 연동 성공! {test_action.reasoning}")
        logger.info(f"[AI] LLM 연동 테스트 성공: {test_action.action_type}")

    except Exception as e:
        logger.warning(f"[AI] LLM 초기화 실패: {e}")
        add_ai_commentary("⚠️ LLM 연동 실패 - 규칙 기반 AI로 진행합니다")
        add_ai_commentary(f"💡 {str(e)[:40]}")
        use_llm = False
        ai = None  # LLM AI 비활성화
        logger.info("[AI] 규칙 기반 AI 모드로 전환")

    add_ai_commentary("✅ AI 준비 완료!")
    
    # 파티 자동 구성
    add_ai_commentary("파티 구성 중...")
    available_jobs = get_available_jobs()
    party_choices = ai.recommend_party(available_jobs, 4)
    
    for choice in party_choices:
        add_ai_commentary(f"👤 {choice.character_name} ({choice.job_id})")
    
    # Character 객체 생성
    from src.character.character import Character
    character_party = []
    for choice in party_choices:
        char = Character(
            name=choice.character_name,
            character_class=choice.job_id,
            level=1
        )
        char.experience = 0
        char.current_hp = char.max_hp
        char.current_mp = char.max_mp
        character_party.append(char)
    
    add_ai_commentary(f"✅ 파티 구성 완료 ({len(character_party)}명)")
    
    # 패시브 자동 선택
    try:
        from src.ui.passive_selection import PassiveSelectionUI
        passive_ui = PassiveSelectionUI(console.width, console.height)
        passives_data = [
            {"id": p.id, "name": p.name, "cost": p.cost, "description": p.description, "unlocked": p.unlocked}
            for p in passive_ui.all_passives
        ]
        party_job_ids = [c.job_id for c in party_choices]
        selected_passives = ai.recommend_passives(passives_data, party_job_ids)
        
        if selected_passives:
            add_ai_commentary(f"🎯 패시브: {', '.join(selected_passives[:2])}...")
            for passive_id in selected_passives:
                for char in character_party:
                    char.activate_trait(passive_id)
    except Exception as e:
        logger.warning(f"패시브 선택 실패: {e}")
    
    # 인벤토리 생성
    from src.equipment.inventory import Inventory
    inventory = Inventory(base_weight=10.0, party=character_party)
    inventory.add_gold(200)
    
    # 난이도 설정 (보통)
    from src.core.difficulty import DifficultySystem, DifficultyLevel, set_difficulty_system
    config = get_config()
    difficulty_system = DifficultySystem(config)
    difficulty_system.set_difficulty(DifficultyLevel.NORMAL)
    set_difficulty_system(difficulty_system)
    
    # 게임 통계
    game_stats = {
        "enemies_defeated": 0,
        "max_floor_reached": 1,
        "floors_cleared": 0,
        "battles_won": 0,
        "battles_lost": 0,
        "next_dungeon_floor": 1
    }
    
    # 마을 시스템 초기화
    from src.town.town_manager import TownManager
    from src.town.town_map import TownMap, create_town_dungeon_map
    from src.world.exploration import ExplorationSystem
    
    town_manager = TownManager()
    town_map = TownMap()
    add_ai_commentary("🏘️ 마을에서 시작!")
    
    # 마을 던전맵 생성
    dungeon = create_town_dungeon_map(town_map)
    floor_number = 0  # 마을은 0층
    
    # 마을 전체 시야 활성화
    for y in range(dungeon.height):
        for x in range(dungeon.width):
            tile = dungeon.get_tile(x, y)
            if tile:
                tile.explored = True
                tile.visible = True
    
    logger.info(f"[AI] 마을 맵 생성: {dungeon.width}x{dungeon.height}, 계단: {dungeon.stairs_down}")
    
    exploration = ExplorationSystem(dungeon, character_party, floor_number, inventory, game_stats)
    exploration.is_town = True
    exploration.town_map = town_map
    exploration.town_manager = town_manager
    
    # 플레이어 스폰 위치 설정
    spawn_x, spawn_y = town_map.player_spawn
    exploration.player.x = spawn_x
    exploration.player.y = spawn_y
    
    # 스폰 위치 타일 확인
    spawn_tile = dungeon.get_tile(spawn_x, spawn_y)
    logger.info(f"[AI] 스폰 위치 ({spawn_x}, {spawn_y}): walkable={spawn_tile.walkable if spawn_tile else 'None'}")
    
    add_ai_commentary(f"📍 마을 ({spawn_x}, {spawn_y})에서 시작!")
    
    # 마을에서 초기 장비 지급 (실제 게임처럼)
    try:
        from src.character.upgrade_applier import UpgradeApplier
        from src.persistence.meta_progress import get_meta_progress
        meta = get_meta_progress()
        UpgradeApplier.give_starting_equipment(character_party, meta_progress=meta, is_host=True)
        add_ai_commentary("🗡️ 초기 장비 지급!")
    except Exception as e:
        logger.warning(f"초기 장비 지급 실패: {e}")
    
    def auto_equip_best_gear(party, inv, ai_instance=None):
        """
        최적 장비 자동 장착 (LLM 추천 or 규칙 기반)
        - 직업별 스탯 우선순위 고려
        - 내구도 고려
        - 더 좋은 장비로 자동 교체
        """
        equipped_count = 0

        # 인벤토리에서 모든 아이템 추출
        available_items = []
        if hasattr(inv, 'slots'):
            for slot in inv.slots:
                if slot.item:
                    for _ in range(slot.quantity):
                        available_items.append(slot.item)

        for char in party:
            # LLM 추천 사용 가능하면 사용
            if ai_instance and hasattr(ai_instance, 'recommend_equipment'):
                try:
                    recommendations = ai_instance.recommend_equipment(char, available_items)
                    for slot_name, rec in recommendations.items():
                        item = rec['item']
                        current_equip = char.equipment.get(slot_name)

                        # 기존 장비를 인벤토리로
                        if current_equip:
                            inv.add_item(current_equip)

                        char.equip_item(slot_name, item)
                        inv.remove_item(item)
                        equipped_count += 1
                        logger.debug(f"{char.name}: {slot_name} 장착 - {rec.get('reason', 'LLM 추천')}")
                    continue
                except Exception as e:
                    logger.debug(f"LLM 장비 추천 실패, 규칙 기반 사용: {e}")

            # 규칙 기반 폴백
            for item in available_items:
                item_type = getattr(item, 'item_type', None)
                if not item_type:
                    continue

                # item_type이 enum인 경우 value 사용
                type_str = item_type.value if hasattr(item_type, 'value') else str(item_type)
                if type_str not in ['weapon', 'armor', 'accessory']:
                    continue

                slot = type_str
                current_equip = char.equipment.get(slot)

                # 새 장비 스탯 계산
                new_power = 0
                if hasattr(item, 'stats'):
                    new_power = sum(item.stats.values()) if isinstance(item.stats, dict) else 0
                elif hasattr(item, 'physical_attack'):
                    new_power = getattr(item, 'physical_attack', 0) + getattr(item, 'magic_attack', 0)

                # 새 장비 내구도
                new_durability = getattr(item, 'durability', 100)

                should_equip = False

                if not current_equip:
                    should_equip = True
                else:
                    current_power = 0
                    if hasattr(current_equip, 'stats'):
                        current_power = sum(current_equip.stats.values()) if isinstance(current_equip.stats, dict) else 0
                    elif hasattr(current_equip, 'physical_attack'):
                        current_power = getattr(current_equip, 'physical_attack', 0) + getattr(current_equip, 'magic_attack', 0)

                    current_durability = getattr(current_equip, 'durability', 100)

                    # 현재 장비 내구도가 10% 이하면 교체
                    if current_durability <= 10:
                        should_equip = True
                    # 새 장비가 더 강하면 교체
                    elif new_power > current_power and new_durability > 20:
                        should_equip = True

                if should_equip:
                    if current_equip:
                        inv.add_item(current_equip)
                    try:
                        char.equip_item(slot, item)
                        inv.remove_item(item)
                        equipped_count += 1
                        logger.debug(f"{char.name}: {slot} 장착 (규칙 기반)")
                    except Exception as e:
                        logger.debug(f"{char.name} 장비 장착 실패: {e}")

        return equipped_count
    
    # 초기 장비 장착 (LLM 추천 사용, 또는 규칙 기반)
    try:
        ai_instance = ai if (ai and use_llm) else None
        equipped_count = auto_equip_best_gear(character_party, inventory, ai_instance)
        if equipped_count > 0:
            add_ai_commentary(f"🛡️ 장비 {equipped_count}개 장착!")
    except Exception as e:
        logger.warning(f"자동 장비 장착 실패: {e}")
    
    # 막힌 상태 감지용
    stuck_counter = [0]
    last_position = [None]
    current_path = []  # A* 경로 캐시

    # 채집 상태 추적 (2번 입력 필요)
    pending_harvest = [None]  # (x, y) or None

    # ===== 맵 메모리 (이미 방문한 지역 기록) =====
    explored_tiles = set()  # 방문한 타일 좌표
    discovered_rooms = []   # 발견한 방들
    explored_by_layer = {}  # 층별 탐험 기록
    
    def astar_pathfind(dungeon_map, start, goal):
        """A* 경로 찾기 알고리즘"""
        import heapq
        
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if current == goal:
                # 경로 복원
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                return path[::-1]
            
            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                tile = dungeon_map.get_tile(neighbor[0], neighbor[1])
                
                if not tile or not tile.walkable:
                    continue
                
                tentative_g = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return []  # 경로 없음
    
    # AI 탐험 입력 제공 콜백
    def ai_exploration_input(exploration_sys, party, inv) -> GameAction:
        """AI가 탐험 입력 결정 - LLM 중심"""
        nonlocal floor_number, dungeon, exploration, current_path
        import traceback
        import random

        # exploration_sys의 던전 사용 (최신 맵)
        current_dungeon = exploration_sys.dungeon if hasattr(exploration_sys, 'dungeon') else dungeon

        try:
            # 현재 위치 확인
            current_pos = (exploration_sys.player.x, exploration_sys.player.y)

            # 막힌 상태 감지
            if last_position[0] == current_pos:
                stuck_counter[0] += 1
                if stuck_counter[0] > 10:
                    log_bug("StuckInPlace", f"같은 위치에 갇힘: {current_pos}",
                           game_state={"position": current_pos, "floor": floor_number})
                    stuck_counter[0] = 0
            else:
                stuck_counter[0] = 0
                last_position[0] = current_pos

            # 파티 상태 계산
            alive = [c for c in party if c.is_alive]
            if not alive:
                return None

            party_hp = sum(c.current_hp / c.max_hp * 100 for c in alive) / len(alive)
            party_mp = sum(c.current_mp / c.max_mp * 100 for c in alive) / len(alive)

            # 현재 위치
            px, py = exploration_sys.player.x, exploration_sys.player.y

            # ===== 방문 타일 기록 =====
            explored_tiles.add((px, py))

            # 계단 위치 확인
            stairs_pos = current_dungeon.stairs_down if hasattr(current_dungeon, 'stairs_down') else None
            is_town = hasattr(exploration_sys, 'is_town') and exploration_sys.is_town

            # ===== 채집 상태 체크 (2번 입력 필요) =====
            # 같은 위치에서 채집 중이면 계속 CONFIRM
            if pending_harvest[0] == (px, py):
                log_action("🌿 채집 진행 중 (2번째 입력)")
                pending_harvest[0] = None  # 초기화
                return GameAction.CONFIRM

            # 현재 위치에 채집 오브젝트가 있으면
            if hasattr(current_dungeon, 'harvestables'):
                for harvestable in current_dungeon.harvestables:
                    if harvestable.x == px and harvestable.y == py:
                        if hasattr(harvestable, 'can_harvest') and harvestable.can_harvest(None):
                            # 첫 번째 입력
                            if pending_harvest[0] != (px, py):
                                log_action(f"🌿 채집 시작: {harvestable.object_type.value}")
                                pending_harvest[0] = (px, py)
                                add_ai_commentary(f"🌿 {harvestable.object_type.value} 채집!")
                                return GameAction.CONFIRM

            # 채집 상태 아니면 초기화
            if pending_harvest[0]:
                pending_harvest[0] = None

            # ===== 마을에서는 바로 계단으로 (LLM 스킵) =====
            if is_town and stairs_pos:
                sx, sy = stairs_pos
                # 계단으로의 거리
                dist_to_stairs = abs(sx - px) + abs(sy - py)

                if dist_to_stairs == 0:
                    # 계단 위에 있음
                    log_action("🚪 마을: 계단 진입!")
                    add_ai_commentary("⬇️ 던전 입구!")
                    return GameAction.CONFIRM
                else:
                    # 계단으로 이동 (LLM 안 씀)
                    dx = 1 if sx > px else (-1 if sx < px else 0)
                    dy = 1 if sy > py else (-1 if sy < py else 0)

                    if dy < 0:
                        return GameAction.MOVE_UP
                    elif dy > 0:
                        return GameAction.MOVE_DOWN
                    elif dx < 0:
                        return GameAction.MOVE_LEFT
                    elif dx > 0:
                        return GameAction.MOVE_RIGHT

            # ===== 적 감지 (A* 경로 사용) =====
            nearby_enemies_list = []
            closest_enemy = None
            closest_dist = float('inf')

            if hasattr(exploration_sys, 'fov_map') and exploration_sys.fov_map:
                for e in exploration_sys.enemies:
                    if exploration_sys.fov_map.visible[e.x, e.y]:
                        nearby_enemies_list.append(e)
                        dist = abs(e.x - px) + abs(e.y - py)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_enemy = e
            else:
                # FOV 없으면 거리 기반
                for e in exploration_sys.enemies:
                    if abs(e.x - px) <= 5 and abs(e.y - py) <= 5:
                        nearby_enemies_list.append(e)
                        dist = abs(e.x - px) + abs(e.y - py)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_enemy = e

            # 가까운 적이 있으면 A* 경로로 추적
            using_enemy_path = False
            if closest_enemy and closest_dist <= 15 and not current_path:  # 시야 범위 내
                # 적으로의 A* 경로 계산
                enemy_pos = (closest_enemy.x, closest_enemy.y)
                path = astar_pathfind(current_dungeon, (px, py), enemy_pos)

                if path:
                    current_path.extend(path)
                    using_enemy_path = True
                    log_action(f"👾 적 추적: {closest_enemy.name}@({closest_enemy.x},{closest_enemy.y}) - 경로: {len(path)}스텝")
                    add_ai_commentary(f"👾 {closest_enemy.name} 추적 중!")

            # LLM이 이동 경로 직접 결정 (던전에서만, 경로 없을 때, LLM이 활성화된 경우만)
            # 적이 있어도 상관없음 - LLM에게 적 정보를 전달하면 됨
            if not current_path and ai and use_llm and not is_town and not using_enemy_path:
                # 실제 시야(FOV) 내의 정보 수집
                visible_tiles = []
                nearby_items = []
                nearby_exits = []
                unexplored_directions = []

                # FOV 계산 및 시야 정보 추출 (시야에 보인 것 = 탐험함)
                if hasattr(exploration_sys, 'fov_map') and exploration_sys.fov_map:
                    for y in range(exploration_sys.fov_map.height):
                        for x in range(exploration_sys.fov_map.width):
                            if exploration_sys.fov_map.visible[x, y]:
                                # ⭐ 시야에 보인 타일은 자동으로 탐험한 것으로 간주
                                explored_tiles.add((x, y))

                                tile = current_dungeon.get_tile(x, y)
                                if tile:
                                    tile_info = {
                                        'x': x, 'y': y,
                                        'walkable': tile.walkable,
                                        'explored': tile.explored or True,  # 시야에 보인 것 = 탐험함
                                        'visited': True,  # 시야 내 = 방문함
                                        'type': 'floor' if tile.walkable else 'wall'
                                    }
                                    # 특수 타일 표시
                                    if hasattr(tile, 'is_stairs_down') and tile.is_stairs_down:
                                        tile_info['type'] = 'stairs_down'
                                    elif hasattr(tile, 'is_stairs_up') and tile.is_stairs_up:
                                        tile_info['type'] = 'stairs_up'
                                    elif hasattr(tile, 'has_chest') and tile.has_chest:
                                        tile_info['type'] = 'chest'

                                    visible_tiles.append(tile_info)

                # 시야 내의 적과 아이템 수집
                nearby_enemies = [f"{e.name}@({e.x},{e.y})" for e in nearby_enemies_list]

                # 바닥 아이템
                if hasattr(exploration_sys, 'floor_items'):
                    for floor_item in exploration_sys.floor_items:
                        fx, fy = floor_item.get('x', 0), floor_item.get('y', 0)
                        # 시야 체크
                        is_visible = False
                        if hasattr(exploration_sys, 'fov_map') and exploration_sys.fov_map:
                            is_visible = exploration_sys.fov_map.visible[fx, fy]
                        else:
                            is_visible = abs(fx - px) <= 3 and abs(fy - py) <= 3

                        if is_visible:
                            item_name = floor_item.get('item', {})
                            if hasattr(item_name, 'name'):
                                item_name = item_name.name
                            nearby_items.append(f"{item_name}@({fx},{fy})")

                # 채집 오브젝트
                if hasattr(current_dungeon, 'harvestables'):
                    for harvestable in current_dungeon.harvestables:
                        is_visible = False
                        if hasattr(exploration_sys, 'fov_map') and exploration_sys.fov_map:
                            is_visible = exploration_sys.fov_map.visible[harvestable.x, harvestable.y]
                        else:
                            is_visible = abs(harvestable.x - px) <= 3 and abs(harvestable.y - py) <= 3

                        if is_visible:
                            nearby_items.append(f"{harvestable.object_type.value}@({harvestable.x},{harvestable.y})")

                # 미탐험 방향 감지 (시야 내 미탐험 타일들)
                # 1) 현재 위치 인접 타일 체크 (빠른 길 찾기용)
                directions = [(0, -1, "up"), (0, 1, "down"), (-1, 0, "left"), (1, 0, "right")]
                for dx, dy, dir_name in directions:
                    nx, ny = px + dx, py + dy
                    tile = current_dungeon.get_tile(nx, ny)
                    # 방문 가능 && 아직 탐험 안 한 곳
                    if tile and tile.walkable:
                        already_visited = (nx, ny) in explored_tiles
                        # 아직 방문한 적 없는 곳만 미탐험으로 표시
                        if not already_visited:
                            unexplored_directions.append((dx, dy))

                # ✅ 시야에 보인 것 = 이미 탐험한 것으로 간주 (688번에서 explored_tiles에 추가됨)
                # 따라서 unexplored_directions는 비어있을 수 있음 (기본값으로 4방향 사용)

                # 계단 위치
                stairs_visible = False
                if stairs_pos:
                    sx, sy = stairs_pos
                    if hasattr(exploration_sys, 'fov_map') and exploration_sys.fov_map:
                        stairs_visible = exploration_sys.fov_map.visible[sx, sy]
                    else:
                        stairs_visible = abs(sx - px) <= 5 and abs(sy - py) <= 5

                # 발견한 방 수
                discovered_rooms = len([t for t in visible_tiles if not t.get('walkable', True)])

                # LLM에게 탐험 상태 전달
                ai_state = ExplorationState(
                    current_floor=floor_number,
                    current_position=(px, py),
                    visible_tiles=visible_tiles[:50],  # 최대 50개 (LLM 토큰 절약)
                    discovered_rooms=discovered_rooms,
                    total_rooms=len(current_dungeon.rooms) if hasattr(current_dungeon, 'rooms') else 10,
                    nearby_enemies=nearby_enemies[:10],  # 최대 10개
                    nearby_items=nearby_items[:10],  # 최대 10개
                    nearby_exits=nearby_exits,
                    party_hp_percent=party_hp,
                    party_mp_percent=party_mp,
                    has_healing_point=stairs_visible if stairs_pos else False,
                    floor_type="town" if is_town else "dungeon",
                    stairs_down_position=stairs_pos if stairs_visible else None,
                    unexplored_directions=unexplored_directions if unexplored_directions else [(0, -1), (0, 1), (-1, 0), (1, 0)]
                )

                # LLM 이동 결정
                try:
                    log_action(f"🤖 LLM 호출: 위치({px}, {py}) - 근처적: {len(nearby_enemies_list)}")
                    logger.info(f"[AI] 🤖 LLM 호출 중... (근처 적 {len(nearby_enemies_list)}마리)")

                    action = ai.decide_exploration_action(ai_state)

                    set_ai_action(f"🎯 LLM: {action.reasoning}")
                    log_action(f"✅ LLM 응답: {action.action_type} - {action.reasoning}")
                    add_ai_commentary(f"💭 {action.reasoning[:50]}")
                    logger.info(f"[AI] ✅ LLM 결정: {action.action_type}")

                    # 현재 위치의 상호작용 가능 여부 확인
                    has_item_here = False
                    has_harvest_here = False
                    has_stairs_here = (px, py) == stairs_pos if stairs_pos else False

                    # 현재 위치 아이템 확인
                    if hasattr(exploration_sys, 'floor_items'):
                        for floor_item in exploration_sys.floor_items:
                            if floor_item.get('x') == px and floor_item.get('y') == py:
                                has_item_here = True
                                break

                    # 현재 위치 채집 확인
                    if hasattr(current_dungeon, 'harvestables'):
                        for harvestable in current_dungeon.harvestables:
                            if harvestable.x == px and harvestable.y == py:
                                if hasattr(harvestable, 'can_harvest') and harvestable.can_harvest(None):
                                    has_harvest_here = True
                                    break

                    # LLM이 interact/rest라고 했거나 움직이지 않으려고 했으면 현재 위치 상호작용 처리
                    should_interact = (action.action_type == "interact" or
                                     action.action_type == "rest" or
                                     (action.action_type == "move" and action.direction == (0, 0)))

                    # ===== 현재 위치 특수 상황 처리 (LLM 결정 우선) =====
                    if should_interact:
                        # 우선순위: 계단 > 아이템 > 채집
                        if has_stairs_here:
                            log_action("🚪 LLM 결정: 계단 진입")
                            add_ai_commentary("⬇️ 계단으로!")
                            return GameAction.CONFIRM

                        if has_item_here:
                            log_action("📦 LLM 결정: 아이템 줍기")
                            add_ai_commentary("🎁 아이템 획득!")
                            return GameAction.CONFIRM

                        if has_harvest_here:
                            log_action("🌿 LLM 결정: 채집")
                            add_ai_commentary("🌿 채집!")
                            return GameAction.CONFIRM

                    # ===== 계단이 근처이고 LLM이 특정 결정 못 했으면 자동 진입 =====
                    if has_stairs_here and action.action_type in ["rest", "interact"]:
                        log_action("🚪 자동: 계단 진입")
                        add_ai_commentary("⬇️ 계단으로!")
                        return GameAction.CONFIRM

                    # ===== LLM 이동 결정 =====
                    if action.action_type == "move" and action.direction and action.direction != (0, 0):
                        dx, dy = action.direction
                        log_action(f"📍 LLM 이동: ({dx}, {dy})")
                        if dy < 0:
                            return GameAction.MOVE_UP
                        elif dy > 0:
                            return GameAction.MOVE_DOWN
                        elif dx < 0:
                            return GameAction.MOVE_LEFT
                        elif dx > 0:
                            return GameAction.MOVE_RIGHT

                    elif action.action_type == "move" and action.target_position:
                        tx, ty = action.target_position
                        log_action(f"🎯 LLM 목표: ({tx}, {ty})")
                        path = astar_pathfind(current_dungeon, (px, py), action.target_position)
                        if path:
                            current_path.extend(path)
                            log_action(f"🛤️ 경로 생성: {len(path)}스텝")
                        else:
                            # 경로 없으면 목표 방향으로
                            tx, ty = action.target_position
                            dx = 1 if tx > px else (-1 if tx < px else 0)
                            dy = 1 if ty > py else (-1 if ty < py else 0)
                            if dy < 0:
                                return GameAction.MOVE_UP
                            elif dy > 0:
                                return GameAction.MOVE_DOWN
                            elif dx < 0:
                                return GameAction.MOVE_LEFT
                            elif dx > 0:
                                return GameAction.MOVE_RIGHT

                    elif action.action_type == "fight":
                        log_action("⚔️ LLM 전투 결정")
                        # 가장 가까운 적으로
                        if exploration_sys.enemies:
                            closest = min(exploration_sys.enemies,
                                key=lambda e: abs(e.x - px) + abs(e.y - py))
                            dx = 1 if closest.x > px else (-1 if closest.x < px else 0)
                            dy = 1 if closest.y > py else (-1 if closest.y < py else 0)
                            if dy < 0:
                                return GameAction.MOVE_UP
                            elif dy > 0:
                                return GameAction.MOVE_DOWN
                            elif dx < 0:
                                return GameAction.MOVE_LEFT
                            elif dx > 0:
                                return GameAction.MOVE_RIGHT

                except Exception as e:
                    log_bug("LLMExplorationError", str(e))
                    log_action(f"❌ LLM 실패: {str(e)[:50]}")
                    add_ai_commentary(f"🔧 LLM 에러 - 규칙 기반으로 전환")
            
            # ===== 경로 따라가기 (적 추적) =====
            if current_path:
                next_pos = current_path[0]
                dx = next_pos[0] - px
                dy = next_pos[1] - py

                tile = current_dungeon.get_tile(next_pos[0], next_pos[1])
                if tile and tile.walkable:
                    current_path.pop(0)

                    if dy < 0:
                        return GameAction.MOVE_UP
                    elif dy > 0:
                        return GameAction.MOVE_DOWN
                    elif dx < 0:
                        return GameAction.MOVE_LEFT
                    elif dx > 0:
                        return GameAction.MOVE_RIGHT
                else:
                    current_path.clear()

            # ===== 경로 끝에 도달했을 때 (적이 있으면 전투 시작) =====
            # 경로가 비었고 closest_enemy가 있고 인접하면 전투 시작
            if not current_path and closest_enemy:
                dist_to_enemy = abs(closest_enemy.x - px) + abs(closest_enemy.y - py)
                if dist_to_enemy <= 1:
                    # 적과 인접! → 전투 개시
                    log_action(f"⚔️ 적 도달! {closest_enemy.name}과 전투!")
                    add_ai_commentary(f"⚔️ 전투 시작!")
                    # 전투는 자동으로 시작되므로, 여기서는 아무 행동도 하지 않음
                    # (다음 프레임에서 전투 시스템이 활성화됨)
                    return GameAction.CONFIRM  # 일단 CONFIRM으로 전투 유도

            # 경로 없으면 LLM 호출 또는 랜덤 이동
            import random
            directions = [
                (GameAction.MOVE_UP, 0, -1),
                (GameAction.MOVE_DOWN, 0, 1),
                (GameAction.MOVE_LEFT, -1, 0),
                (GameAction.MOVE_RIGHT, 1, 0),
            ]
            
            possible_moves = []
            for game_action, dx, dy in directions:
                nx, ny = px + dx, py + dy
                tile = current_dungeon.get_tile(nx, ny)
                if tile and tile.walkable:
                    possible_moves.append(game_action)
            
            if possible_moves:
                return random.choice(possible_moves)
            
            # 모든 방향이 막힘 - 버그로 기록
            log_bug("NoValidMoves", f"위치 ({px}, {py})에서 이동 불가", 
                   game_state={"position": (px, py), "floor": floor_number})
            
            return random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT])
        
        except Exception as e:
            log_bug("ExplorationAIError", str(e), traceback.format_exc())
            import random
            return random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT])
    
    # AI 전투 입력 제공 콜백
    def ai_combat_input(ui, combat_manager, current_char, inv) -> GameAction:
        """AI가 전투 입력 결정 - LLM 중심"""
        import traceback
        log_action(f"⚔️ AI 전투 입력: {current_char.name}")
        logger.info(f"[COMBAT] ⚔️ AI 전투 입력 호출: {current_char.name} (AI={ai is not None}, USE_LLM={use_llm})")

        # LLM 사용 가능한 경우
        if ai and use_llm:
            try:
                from src.multiplayer.llm_player_bot import GameStateConverter, ActionType

                logger.info(f"[COMBAT] 전투 상태 변환 중...")
                combat_state = GameStateConverter.from_combat_manager(combat_manager, current_char, inv)
                logger.info(f"[COMBAT] ✅ 전투 상태 변환 완료")

                # LLM 전투 결정
                log_action(f"🤖 LLM 전투 호출: {current_char.name}")
                logger.info(f"[COMBAT] 🤖 LLM 전투 봇 생성 중...")
                bot = ai.create_combat_bot(current_char)
                logger.info(f"[COMBAT] 🤖 LLM 호출 중...")
                action = bot.decide_combat_action(combat_state)
                logger.info(f"[COMBAT] ✅ LLM 응답 받음")
                action_name = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)

                log_action(f"✅ LLM 전투 결정: {action_name}")
                set_ai_action(f"⚔️ {action_name}")
                reasoning = getattr(action, 'reasoning', '')
                if reasoning:
                    add_ai_commentary(f"⚔️ {current_char.name}: {reasoning[:40]}")
                else:
                    add_ai_commentary(f"⚔️ {current_char.name}: {action_name}")

                # LLM 액션을 GameAction으로 변환
                # ===== 중요: LLM의 결정을 실제로 반영 =====
                if action.action_type in [ActionType.BRV_ATTACK, ActionType.HP_ATTACK]:
                    log_action("💥 LLM 공격 실행")
                    return GameAction.CONFIRM  # 공격 선택

                elif action.action_type == ActionType.SKILL:
                    # LLM이 스킬을 선택했으면
                    skill_id = getattr(action, 'skill_id', None)
                    log_action(f"✨ LLM 스킬 선택: {skill_id}")
                    # 스킬 메뉴로 진입 (MENU 또는 특정 키)
                    # 근데 메뉴 시스템 상 제약이 있으니, 일단 CONFIRM으로 스킬 메뉴 진입 시도
                    return GameAction.CONFIRM

                elif action.action_type == ActionType.ITEM:
                    # 아이템 사용
                    log_action("📦 LLM 아이템 사용")
                    return GameAction.CANCEL  # 아이템 메뉴로

                elif action.action_type == ActionType.DEFEND:
                    # 방어
                    log_action("🛡️ LLM 방어 선택")
                    return GameAction.CANCEL  # 방어 메뉴로

                elif action.action_type == ActionType.FLEE:
                    # 도망
                    log_action("💨 LLM 도망 선택")
                    return GameAction.CANCEL  # 도망 메뉴로

                else:
                    log_action(f"⚠️ LLM 알 수 없는 액션: {action_name}")
                    return GameAction.CONFIRM

            except Exception as e:
                logger.error(f"[COMBAT] ❌ LLM 전투 실패: {str(e)}")
                logger.error(f"[COMBAT] 스택 트레이스:\n{traceback.format_exc()}")
                log_action(f"❌ LLM 전투 실패: {str(e)[:50]}")
                log_bug("LLMCombatError", str(e), traceback.format_exc())
                add_ai_commentary(f"🔧 LLM 오류 - 기본 공격으로")

        # ===== 규칙 기반 폴백 또는 LLM 비활성화 =====
        log_action(f"📋 규칙 기반 AI: {current_char.name}")
        logger.info(f"[COMBAT] 📋 규칙 기반 AI 사용 (AI={ai}, USE_LLM={use_llm})")

        # 기본 우선순위: 긴급 상황 > 힐 > 버프 > 공격
        try:
            alive_chars = [c for c in combat_manager.party if c.is_alive]

            # 1. 파티 전멸 위기 → 힐 (HP < 20% 이상 있으면)
            critical_hp = sum(1 for c in alive_chars if c.current_hp / c.max_hp < 0.3)
            if critical_hp >= len(alive_chars) // 2:
                log_action("🆘 규칙: 긴급 힐 필요")
                logger.info(f"[COMBAT] 🆘 긴급 힐 필요 (파티 위기)")
                return GameAction.CONFIRM

            # 2. 자신의 HP 위험 → 힐 또는 방어
            if current_char.current_hp / current_char.max_hp < 0.2:
                log_action("❤️ 규칙: 자신 체력 위험")
                logger.info(f"[COMBAT] ❤️ 자신 체력 위험 ({current_char.current_hp}/{current_char.max_hp})")
                return GameAction.CANCEL  # 방어 선택

            # 3. 일반 전투 → 공격
            log_action("⚔️ 규칙: 일반 공격")
            logger.info(f"[COMBAT] ⚔️ 기본 공격 선택")
            return GameAction.CONFIRM
        except Exception as e:
            logger.error(f"[COMBAT] ❌ 규칙 기반 AI 오류: {str(e)}")
            logger.error(f"[COMBAT] 스택 트레이스:\n{traceback.format_exc()}")
            log_action(f"❌ 규칙 AI 오류: {str(e)[:30]}")
            return GameAction.CONFIRM  # 일단 CONFIRM으로 진행
    
    # 실제 게임 UI 사용하여 탐험/전투 루프
    from src.ui.world_ui import run_exploration
    from src.ui.combat_ui import run_combat, CombatState
    from src.world.enemy_generator import EnemyGenerator
    
    running = True
    play_bgm = True
    
    while running:
        # 파티 전멸 체크
        alive_count = sum(1 for c in character_party if c.is_alive)
        if alive_count == 0:
            add_ai_commentary("💀 파티 전멸!")
            game_stats["battles_lost"] += 1
            break
        
        # 실제 탐험 UI 실행 (AI 입력 사용)
        result, data = run_exploration(
            console, context, exploration, inventory, character_party,
            play_bgm_on_start=play_bgm,
            ai_input_provider=ai_exploration_input
        )
        
        play_bgm = False  # 이후 전투 복귀 시 BGM 재생 안함
        
        if result == "quit":
            add_ai_commentary("관전 종료")
            break
        
        elif result == "combat":
            # 전투 시작
            num_enemies = data.get("num_enemies", 1)
            enemies = EnemyGenerator.generate_enemies(floor_number, num_enemies)
            
            add_ai_commentary(f"⚔️ 전투 시작! ({len(enemies)}마리)")
            
            # 실제 전투 UI 실행 (AI 입력 사용)
            combat_result, is_game_over = run_combat(
                console, context, character_party, enemies, inventory,
                dungeon=dungeon,
                ai_input_provider=ai_combat_input
            )
            
            if combat_result == CombatState.VICTORY:
                game_stats["battles_won"] += 1
                game_stats["enemies_defeated"] += len(enemies)
                add_ai_commentary("✅ 전투 승리!")
                
                # 맵에서 적 제거
                if data.get("enemies"):
                    for enemy in data["enemies"]:
                        if enemy in exploration.enemies:
                            exploration.enemies.remove(enemy)
                
                # 전투 후 장비 업그레이드 체크 (LLM 추천 사용, 또는 규칙 기반)
                try:
                    ai_instance = ai if (ai and use_llm) else None
                    upgrade_count = auto_equip_best_gear(character_party, inventory, ai_instance)
                    if upgrade_count > 0:
                        add_ai_commentary(f"⬆️ 장비 {upgrade_count}개 업그레이드!")
                except Exception as e:
                    logger.warning(f"장비 업그레이드 실패: {e}")
            else:
                add_ai_commentary("� 전투 패배...")
                if is_game_over:
                    game_stats["battles_lost"] += 1
                    break
        
        elif result == "floor_down":
            # 다음 층으로
            from src.world.dungeon_generator import DungeonGenerator
            from src.world.exploration import ExplorationSystem

            if floor_number == 0:
                # 마을(0층)에서 던전(1층)으로
                floor_number = 1
                add_ai_commentary("⚔️ 던전으로 출발!")
            else:
                # 던전 내 층 이동
                floor_number += 1
                game_stats["floors_cleared"] += 1

            game_stats["max_floor_reached"] = max(game_stats["max_floor_reached"], floor_number)

            # 새 던전 생성
            logger.info(f"[AI] 던전 생성 시작: {floor_number}층")
            generator = DungeonGenerator(width=80, height=50)
            dungeon = generator.generate(floor_number=floor_number)
            logger.info(f"[AI] 던전 생성 완료: {dungeon.width}x{dungeon.height}, 방 {len(dungeon.rooms)}개")

            # 새 탐험 시스템 생성
            exploration = ExplorationSystem(dungeon, character_party, floor_number, inventory, game_stats)
            logger.info(f"[AI] 탐험 시스템 생성: 플레이어 위치 ({exploration.player.x}, {exploration.player.y})")

            # 막힌 상태 및 경로 초기화
            stuck_counter[0] = 0
            last_position[0] = None
            current_path.clear()

            # ===== 새 층의 맵 메모리 초기화 =====
            explored_tiles.clear()
            discovered_rooms.clear()
            explored_by_layer[floor_number] = set()

            add_ai_commentary(f"🏔️ {floor_number}층 진입!")
            play_bgm = True
    
    # 정리
    if ai and use_llm:
        try:
            ai.shutdown()
        except Exception as e:
            logger.warning(f"AI 종료 실패: {e}")

    set_ai_mode(False)
    logger.info("AI 관전 모드 종료")

    return {"success": True, "stats": game_stats}
