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
    
    # AI 생성
    add_ai_commentary("AI 초기화 중...")
    try:
        ai = create_auto_play_ai(model="qwen3:0.6b", style=PlayStyle.BALANCED)
        add_ai_commentary("✅ AI 준비 완료!")
    except Exception as e:
        add_ai_commentary(f"❌ AI 초기화 실패: {e}")
        logger.error(f"AI 초기화 실패: {e}")
        set_ai_mode(False)
        return {"success": False, "error": str(e)}
    
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
        
        for char in party:
            # LLM 추천 사용 가능하면 사용
            if ai_instance and hasattr(ai_instance, 'recommend_equipment'):
                try:
                    recommendations = ai_instance.recommend_equipment(char, list(inv.items))
                    for slot, rec in recommendations.items():
                        item = rec['item']
                        current_equip = char.equipment.get(slot)
                        
                        # 기존 장비를 인벤토리로
                        if current_equip:
                            inv.add_item(current_equip)
                        
                        char.equip_item(slot, item)
                        inv.remove_item(item)
                        equipped_count += 1
                        logger.debug(f"{char.name}: {slot} 장착 - {rec['reason']}")
                    continue
                except Exception as e:
                    logger.debug(f"LLM 장비 추천 실패, 규칙 기반 사용: {e}")
            
            # 규칙 기반 폴백
            for item in list(inv.items):
                item_type = getattr(item, 'item_type', None)
                if not item_type or item_type.value not in ['weapon', 'armor', 'accessory']:
                    continue
                
                slot = item_type.value
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
                    char.equip_item(slot, item)
                    inv.remove_item(item)
                    equipped_count += 1
        
        return equipped_count
    
    # 초기 장비 장착 (LLM 추천 사용)
    try:
        equipped_count = auto_equip_best_gear(character_party, inventory, ai)
        if equipped_count > 0:
            add_ai_commentary(f"🛡️ 장비 {equipped_count}개 장착!")
    except Exception as e:
        logger.warning(f"자동 장비 장착 실패: {e}")
    
    # 막힌 상태 감지용
    stuck_counter = [0]
    last_position = [None]
    current_path = []  # A* 경로 캐시
    
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
        """AI가 탐험 입력 결정"""
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
                    stuck_counter[0] = 0  # 리셋
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
            
            # 채집 오브젝트 자동 채집 (Z 두번 필요)
            if hasattr(current_dungeon, 'harvestables'):
                for harvestable in current_dungeon.harvestables:
                    if harvestable.x == px and harvestable.y == py:
                        if hasattr(harvestable, 'can_harvest') and harvestable.can_harvest(None):
                            log_action(f"채집: {harvestable.object_type.value}")
                            add_ai_commentary(f"🌿 {harvestable.object_type.value} 채집!")
                            return GameAction.CONFIRM  # 첫 번째 Z - 두 번째는 다음 프레임에서
            
            # 바닥 아이템 자동 줍기
            if hasattr(exploration_sys, 'floor_items'):
                for floor_item in exploration_sys.floor_items:
                    if floor_item.get('x') == px and floor_item.get('y') == py:
                        item_name = floor_item.get('item', {})
                        if hasattr(item_name, 'name'):
                            item_name = item_name.name
                        log_action(f"줍기: {item_name}")
                        add_ai_commentary(f"📦 아이템 획득!")
                        return GameAction.CONFIRM
            
            # 계단 위치 확인
            stairs_pos = current_dungeon.stairs_down if hasattr(current_dungeon, 'stairs_down') else None
            is_town = hasattr(exploration_sys, 'is_town') and exploration_sys.is_town
            
            # 계단 위에 있으면 바로 진입
            if stairs_pos and (px, py) == stairs_pos:
                current_path.clear()
                if is_town:
                    log_action("마을: 던전 입구 도착!")
                    add_ai_commentary("🚪 던전 입구!")
                else:
                    log_action("다음 층으로!")
                    add_ai_commentary("⬇️ 다음 층!")
                return GameAction.CONFIRM
            
            # 적이 근처에 있으면 우선 전투
            if exploration_sys.enemies:
                closest = min(exploration_sys.enemies, 
                    key=lambda e: abs(e.x - px) + abs(e.y - py))
                dist = abs(closest.x - px) + abs(closest.y - py)
                if dist <= 5:  # 시야 내 적
                    # 적 방향으로 이동
                    if closest.y < py:
                        return GameAction.MOVE_UP
                    elif closest.y > py:
                        return GameAction.MOVE_DOWN
                    elif closest.x < px:
                        return GameAction.MOVE_LEFT
                    elif closest.x > px:
                        return GameAction.MOVE_RIGHT
            
            # LLM이 이동 경로 직접 결정
            if not current_path:
                # LLM에게 탐험 상태 전달
                ai_state = ExplorationState(
                    current_floor=floor_number,
                    current_position=(px, py),
                    visible_tiles=[],
                    discovered_rooms=len(current_dungeon.rooms) if hasattr(current_dungeon, 'rooms') else 5,
                    total_rooms=10,
                    nearby_enemies=[e.name for e in exploration_sys.enemies 
                                  if abs(e.x - px) <= 5 and abs(e.y - py) <= 5],
                    nearby_items=[],
                    nearby_exits=[],
                    party_hp_percent=party_hp,
                    party_mp_percent=party_mp,
                    has_healing_point=False,
                    floor_type="town" if is_town else "dungeon",
                    stairs_down_position=stairs_pos,
                    unexplored_directions=[(0, -1), (0, 1), (-1, 0), (1, 0)]  # 모든 방향 미탐험으로 설정
                )
                
                # LLM 이동 결정 - 디버깅 로그 추가
                try:
                    action = ai.decide_exploration_action(ai_state)
                    set_ai_action(f"🎯 LLM: {action.reasoning}")
                    log_action(f"LLM 탐험: {action.action_type} - {action.reasoning}")
                except Exception as e:
                    log_bug("LLMExplorationError", str(e))
                    # 폴백: 랜덤 이동
                    import random
                    return random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT])
                
                # LLM이 직접 이동 방향 결정
                if action.action_type == "move" and action.direction:
                    dx, dy = action.direction
                    if dy < 0:
                        return GameAction.MOVE_UP
                    elif dy > 0:
                        return GameAction.MOVE_DOWN
                    elif dx < 0:
                        return GameAction.MOVE_LEFT
                    elif dx > 0:
                        return GameAction.MOVE_RIGHT
                elif action.action_type == "move" and action.target_position:
                    # 목표 위치가 있으면 A* 경로
                    path = astar_pathfind(current_dungeon, (px, py), action.target_position)
                    current_path.extend(path)
                    log_action(f"LLM 경로: {action.target_position} ({len(path)}스텝)")
                elif action.action_type == "rest":
                    return GameAction.CONFIRM  # 휴식
                elif action.action_type == "interact":
                    return GameAction.CONFIRM  # 상호작용
            
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
            
            # 경로 없으면 랜덤 이동
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
        """AI가 전투 입력 결정"""
        import traceback
        try:
            # LLMPlayerBot 직접 생성하여 사용
            from src.multiplayer.llm_player_bot import create_llm_bot
            bot = create_llm_bot(current_char.name, getattr(current_char, 'job_id', 'warrior'), ai.config.model, ai.config.play_style)
            
            # 전투 상태 변환
            from src.multiplayer.llm_player_bot import GameStateConverter
            combat_state = GameStateConverter.from_combat_manager(combat_manager, current_char, inv)
            
            # LLM 전투 결정
            action = bot.decide_combat_action(combat_state)
            
            action_name = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)
            log_action(f"전투: {current_char.name} -> {action_name}")
            set_ai_action(f"⚔️ {action_name}")
            
            # LLM 액션을 GameAction으로 변환
            from src.combat.bot_action import BotActionType
            
            if action.action_type == BotActionType.ATTACK:
                # 공격 - 기본 선택
                return GameAction.CONFIRM
            elif action.action_type == BotActionType.SKILL:
                # 스킬 사용
                if action.target_skill:
                    # 스킬 메뉴에서 선택
                    return GameAction.CONFIRM
                return GameAction.CONFIRM
            elif action.action_type == BotActionType.ITEM:
                # 아이템 사용
                return GameAction.CANCEL  # 아이템 메뉴로
            elif action.action_type == BotActionType.DEFEND:
                # 방어
                return GameAction.CANCEL
            elif action.action_type == BotActionType.FLEE:
                # 도망
                return GameAction.CANCEL
            
            return GameAction.CONFIRM
        except Exception as e:
            log_bug("CombatAIError", str(e), traceback.format_exc())
            return GameAction.CONFIRM
    
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
                
                # 전투 후 장비 업그레이드 체크 (LLM 추천 사용)
                try:
                    upgrade_count = auto_equip_best_gear(character_party, inventory, ai)
                    if upgrade_count > 0:
                        add_ai_commentary(f"⬆️ 장비 {upgrade_count}개 업그레이드!")
                except:
                    pass
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
            
            add_ai_commentary(f"🏔️ {floor_number}층 진입!")
            play_bgm = True
    
    # 정리
    ai.shutdown()
    set_ai_mode(False)
    logger.info("AI 관전 모드 종료")
    
    return {"success": True, "stats": game_stats}
