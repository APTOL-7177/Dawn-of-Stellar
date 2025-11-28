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
    
    exploration = ExplorationSystem(dungeon, character_party, floor_number, inventory, game_stats)
    exploration.is_town = True
    exploration.town_map = town_map
    exploration.town_manager = town_manager
    
    # 플레이어 스폰 위치 설정
    spawn_x, spawn_y = town_map.player_spawn
    exploration.player.x = spawn_x
    exploration.player.y = spawn_y
    
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
    
    # 자동 장비 장착
    try:
        equipped_count = 0
        for char in character_party:
            for item in list(inventory.items):
                # 장비 아이템인지 확인
                item_type = getattr(item, 'item_type', None)
                if item_type and item_type.value in ['weapon', 'armor', 'accessory']:
                    slot = item_type.value
                    # 해당 슬롯이 비어있으면 장착
                    if not char.equipment.get(slot):
                        char.equip_item(slot, item)
                        inventory.remove_item(item)
                        equipped_count += 1
                        break  # 한 캐릭터당 한 번만
        if equipped_count > 0:
            add_ai_commentary(f"🛡️ 장비 {equipped_count}개 장착!")
    except Exception as e:
        logger.warning(f"자동 장비 장착 실패: {e}")
    
    # 막힌 상태 감지용
    stuck_counter = [0]
    last_position = [None]
    
    # AI 탐험 입력 제공 콜백
    def ai_exploration_input(exploration_sys, party, inv) -> GameAction:
        """AI가 탐험 입력 결정"""
        nonlocal floor_number, dungeon, exploration
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
                if stuck_counter[0] >= 10:
                    log_bug("StuckDetected", f"AI가 {current_pos}에서 {stuck_counter[0]}턴 동안 막힘", 
                           game_state={"position": current_pos, "floor": floor_number})
                    stuck_counter[0] = 0
                    # 랜덤 방향으로 탈출 시도
                    return random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT])
            else:
                stuck_counter[0] = 0
            last_position[0] = current_pos
            
            # 파티 상태 계산
            alive = [c for c in party if c.is_alive]
            if not alive:
                return None
            
            party_hp = sum(c.current_hp / c.max_hp * 100 for c in alive) / len(alive)
            party_mp = sum(c.current_mp / c.max_mp * 100 for c in alive) / len(alive)
            
            # 탐험 상태 구성
            state = ExplorationState(
                current_floor=floor_number,
                current_position=(exploration_sys.player.x, exploration_sys.player.y),
                visible_tiles=[],
                discovered_rooms=0,
                total_rooms=5,
                nearby_enemies=[e.name for e in exploration_sys.enemies 
                              if abs(e.x - exploration_sys.player.x) <= 5 
                              and abs(e.y - exploration_sys.player.y) <= 5],
                nearby_items=[],
                nearby_exits=[],
                party_hp_percent=party_hp,
                party_mp_percent=party_mp,
                has_healing_point=False,
                floor_type="dungeon",
                stairs_down_position=current_dungeon.stairs_down if hasattr(current_dungeon, 'stairs_down') else None
            )
            
            # 현재 위치
            px, py = exploration_sys.player.x, exploration_sys.player.y
            
            # 채집 오브젝트 자동 채집
            if hasattr(current_dungeon, 'harvestables'):
                for harvestable in current_dungeon.harvestables:
                    if harvestable.x == px and harvestable.y == py:
                        if hasattr(harvestable, 'can_harvest') and harvestable.can_harvest(None):
                            log_action(f"채집: {harvestable.object_type.value}")
                            add_ai_commentary(f"🌿 {harvestable.object_type.value} 채집!")
                            return GameAction.CONFIRM
            
            # 마을 모드: 건물/계단 탐색
            is_town = hasattr(exploration_sys, 'is_town') and exploration_sys.is_town
            
            if is_town:
                # 계단 위치 (던전 입구)
                stairs_pos = current_dungeon.stairs_down if hasattr(current_dungeon, 'stairs_down') else None
                
                # 계단 위에 있으면 바로 진입
                if stairs_pos and (px, py) == stairs_pos:
                    log_action("마을: 던전 입구 도착!")
                    add_ai_commentary("🚪 던전 입구!")
                    return GameAction.CONFIRM
                
                # 목표: 계단으로 직접 이동 (A* 스타일)
                if stairs_pos:
                    sx, sy = stairs_pos
                    # 가장 가까워지는 방향 선택
                    best_move = None
                    best_dist = abs(px - sx) + abs(py - sy)
                    
                    for game_action, dx, dy in [
                        (GameAction.MOVE_UP, 0, -1),
                        (GameAction.MOVE_DOWN, 0, 1),
                        (GameAction.MOVE_LEFT, -1, 0),
                        (GameAction.MOVE_RIGHT, 1, 0),
                    ]:
                        nx, ny = px + dx, py + dy
                        tile = current_dungeon.get_tile(nx, ny)
                        if tile and tile.walkable:
                            new_dist = abs(nx - sx) + abs(ny - sy)
                            if new_dist < best_dist:
                                best_dist = new_dist
                                best_move = game_action
                    
                    if best_move:
                        return best_move
            
            # AI 행동 결정 (LLM)
            action = ai.decide_exploration_action(state)
            set_ai_action(f"💭 {action.reasoning}")
            log_action(f"탐험: {action.action_type} - {action.reasoning}")
            
            # GameAction으로 변환
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
            elif action.action_type == "fight":
                # 적이 있는 방향으로 이동
                if exploration_sys.enemies:
                    closest = min(exploration_sys.enemies, 
                        key=lambda e: abs(e.x - exploration_sys.player.x) + abs(e.y - exploration_sys.player.y))
                    if closest.y < exploration_sys.player.y:
                        return GameAction.MOVE_UP
                    elif closest.y > exploration_sys.player.y:
                        return GameAction.MOVE_DOWN
                    elif closest.x < exploration_sys.player.x:
                        return GameAction.MOVE_LEFT
                    else:
                        return GameAction.MOVE_RIGHT
            
            # 이동 가능한 방향 찾기
            px, py = exploration_sys.player.x, exploration_sys.player.y
            possible_moves = []
            
            directions = [
                (GameAction.MOVE_UP, 0, -1),
                (GameAction.MOVE_DOWN, 0, 1),
                (GameAction.MOVE_LEFT, -1, 0),
                (GameAction.MOVE_RIGHT, 1, 0),
            ]
            
            for game_action, dx, dy in directions:
                nx, ny = px + dx, py + dy
                tile = current_dungeon.get_tile(nx, ny)
                if tile and tile.walkable:
                    possible_moves.append((game_action, dx, dy))
            
            if possible_moves:
                # 계단이 있으면 계단 방향 우선
                if hasattr(current_dungeon, 'stairs_down') and current_dungeon.stairs_down:
                    sx, sy = current_dungeon.stairs_down
                    for game_action, dx, dy in possible_moves:
                        # 계단 방향으로 가까워지면 우선
                        nx, ny = px + dx, py + dy
                        if abs(nx - sx) + abs(ny - sy) < abs(px - sx) + abs(py - sy):
                            return game_action
                
                # 랜덤 선택
                return random.choice(possible_moves)[0]
            
            # 모든 방향이 막힘 - 버그로 기록
            log_bug("NoValidMoves", f"위치 ({px}, {py})에서 이동 불가", 
                   game_state={"position": (px, py), "floor": floor_number})
            
            # 그래도 시도
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
            # 전투 상태 가져오기
            combat_state = GameStateConverter.from_combat_manager(combat_manager, current_char, inv)
            bot = ai.create_combat_bot(current_char)
            action = bot.decide_combat_action(combat_state)
            
            action_name = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)
            log_action(f"전투: {current_char.name} -> {action_name}")
            set_ai_action(f"💭 {action_name}")
            
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
            enemy_gen = EnemyGenerator(floor_number)
            enemies = enemy_gen.generate_enemies(num_enemies)
            
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
            else:
                add_ai_commentary("� 전투 패배...")
                if is_game_over:
                    game_stats["battles_lost"] += 1
                    break
        
        elif result == "floor_down":
            # 다음 층으로
            from src.world.dungeon_generator import DungeonGenerator
            
            if floor_number == 0:
                # 마을(0층)에서 던전(1층)으로
                floor_number = 1
                add_ai_commentary("⚔️ 던전으로 출발!")
            else:
                # 던전 내 층 이동
                floor_number += 1
                game_stats["floors_cleared"] += 1
            
            game_stats["max_floor_reached"] = max(game_stats["max_floor_reached"], floor_number)
            
            generator = DungeonGenerator(floor_number)
            dungeon = generator.generate()
            exploration = ExplorationSystem(dungeon, character_party, floor_number, inventory, game_stats)
            
            add_ai_commentary(f"🏔️ {floor_number}층 진입!")
            play_bgm = True
    
    # 정리
    ai.shutdown()
    set_ai_mode(False)
    logger.info("AI 관전 모드 종료")
    
    return {"success": True, "stats": game_stats}
