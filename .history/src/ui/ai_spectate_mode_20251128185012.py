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
    global _ai_mode_enabled, _ai_commentary
    _ai_mode_enabled = enabled
    if enabled:
        _ai_commentary = []


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
    AI 관전 모드 실행 - 실제 게임과 연동
    
    Returns:
        결과 딕셔너리
    """
    from src.multiplayer.llm_player_bot import (
        create_auto_play_ai,
        get_available_jobs,
        PlayStyle,
        GameStateConverter,
        get_bot_action_for_combat
    )
    from src.core.config import get_config
    from src.persistence.meta_progress import get_meta_progress
    
    logger.info("AI 관전 모드 시작 (실제 게임 연동)")
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
        "max_floor_reached": 0,
        "floors_cleared": 0,
        "battles_won": 0,
        "battles_lost": 0
    }
    
    # 던전 생성 (1층부터 시작)
    from src.world.dungeon_generator import DungeonGenerator
    from src.world.exploration import ExplorationSystem
    
    floor_number = 1
    generator = DungeonGenerator(floor_number)
    dungeon = generator.generate()
    exploration = ExplorationSystem(dungeon, character_party, floor_number, inventory, game_stats)
    
    add_ai_commentary(f"🏔️ {floor_number}층 진입!")
    
    # 게임 루프
    running = True
    ai_action_delay = 0.5  # AI 행동 간 딜레이 (초)
    last_action_time = time.time()
    
    while running:
        # ESC 키로 종료
        for event in tcod.event.get():
            if isinstance(event, tcod.event.Quit):
                running = False
            elif isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.ESCAPE:
                    running = False
                    add_ai_commentary("관전 종료")
        
        if not running:
            break
        
        # AI 행동 딜레이
        current_time = time.time()
        if current_time - last_action_time < ai_action_delay:
            # 화면 렌더링만 하고 대기
            _render_ai_game(console, context, exploration, character_party, game_stats)
            time.sleep(0.05)
            continue
        
        last_action_time = current_time
        
        # 파티 전멸 체크
        alive_count = sum(1 for c in character_party if c.is_alive)
        if alive_count == 0:
            add_ai_commentary("💀 파티 전멸!")
            game_stats["battles_lost"] += 1
            running = False
            break
        
        # AI 탐험 행동 결정
        from src.multiplayer.llm_player_bot import ExplorationState
        
        # 탐험 상태 구성
        party_hp = sum(c.current_hp / c.max_hp * 100 for c in character_party if c.is_alive) / max(alive_count, 1)
        party_mp = sum(c.current_mp / c.max_mp * 100 for c in character_party if c.is_alive) / max(alive_count, 1)
        
        explore_state = ExplorationState(
            current_floor=floor_number,
            current_position=(exploration.player.x, exploration.player.y),
            visible_tiles=[],
            discovered_rooms=len([r for r in dungeon.rooms if any(
                (x, y) in exploration.explored_tiles 
                for x in range(r.x, r.x + r.width) 
                for y in range(r.y, r.y + r.height)
            )]) if hasattr(dungeon, 'rooms') else 0,
            total_rooms=len(dungeon.rooms) if hasattr(dungeon, 'rooms') else 5,
            nearby_enemies=[e.name for e in exploration.enemies if abs(e.x - exploration.player.x) <= 3 and abs(e.y - exploration.player.y) <= 3],
            nearby_items=[],
            nearby_exits=[],
            party_hp_percent=party_hp,
            party_mp_percent=party_mp,
            has_healing_point=False,
            floor_type="dungeon",
            stairs_down_position=dungeon.stairs_down if hasattr(dungeon, 'stairs_down') else None
        )
        
        # AI 행동 결정
        action = ai.decide_exploration_action(explore_state)
        set_ai_action(f"{action.action_type}: {action.reasoning}")
        
        # 행동 실행
        if action.action_type == "move" and action.direction:
            dx, dy = action.direction
            new_x = exploration.player.x + dx
            new_y = exploration.player.y + dy
            
            # 이동 가능 여부 확인
            if 0 <= new_x < dungeon.width and 0 <= new_y < dungeon.height:
                if dungeon.tiles[new_y][new_x].walkable:
                    exploration.player.x = new_x
                    exploration.player.y = new_y
                    exploration.explored_tiles.add((new_x, new_y))
                    
                    # 적과 조우 체크
                    for enemy in exploration.enemies:
                        if enemy.x == new_x and enemy.y == new_y:
                            add_ai_commentary(f"⚔️ {enemy.name}과 전투!")
                            
                            # 전투 실행
                            combat_result = _run_ai_combat(
                                console, context, ai, 
                                character_party, enemy, inventory, game_stats
                            )
                            
                            if combat_result == "victory":
                                game_stats["battles_won"] += 1
                                game_stats["enemies_defeated"] += 1
                                exploration.enemies.remove(enemy)
                                add_ai_commentary("✅ 전투 승리!")
                            elif combat_result == "defeat":
                                game_stats["battles_lost"] += 1
                                add_ai_commentary("💀 전투 패배...")
                            break
                    
                    # 계단 체크
                    if hasattr(dungeon, 'stairs_down') and (new_x, new_y) == dungeon.stairs_down:
                        floor_number += 1
                        game_stats["floors_cleared"] += 1
                        game_stats["max_floor_reached"] = max(game_stats["max_floor_reached"], floor_number)
                        add_ai_commentary(f"🏔️ {floor_number}층 진입!")
                        
                        # 새 던전 생성
                        generator = DungeonGenerator(floor_number)
                        dungeon = generator.generate()
                        exploration = ExplorationSystem(dungeon, character_party, floor_number, inventory, game_stats)
        
        elif action.action_type == "rest":
            # 휴식
            for char in character_party:
                if char.is_alive:
                    char.current_hp = min(char.max_hp, char.current_hp + char.max_hp // 4)
                    char.current_mp = min(char.max_mp, char.current_mp + char.max_mp // 4)
            add_ai_commentary("💤 휴식으로 회복")
        
        elif action.action_type == "fight":
            # 가장 가까운 적에게 이동
            if exploration.enemies:
                closest = min(exploration.enemies, 
                    key=lambda e: abs(e.x - exploration.player.x) + abs(e.y - exploration.player.y))
                dx = 1 if closest.x > exploration.player.x else (-1 if closest.x < exploration.player.x else 0)
                dy = 1 if closest.y > exploration.player.y else (-1 if closest.y < exploration.player.y else 0)
                exploration.player.x += dx
                exploration.player.y += dy
        
        # 화면 렌더링
        _render_ai_game(console, context, exploration, character_party, game_stats)
    
    # 정리
    ai.shutdown()
    set_ai_mode(False)
    logger.info("AI 관전 모드 종료")
    
    return {"success": True, "stats": game_stats}


def _render_ai_game(console, context, exploration, party, stats):
    """AI 게임 화면 렌더링"""
    console.clear()
    
    # 제목
    console.print(1, 0, "🤖 AI 관전 모드 [ESC: 종료]", fg=(255, 215, 0))
    
    # 미니맵 (좌상단)
    map_offset_x = 2
    map_offset_y = 2
    view_radius = 15
    
    px, py = exploration.player.x, exploration.player.y
    dungeon = exploration.dungeon
    
    for dy in range(-view_radius, view_radius + 1):
        for dx in range(-view_radius, view_radius + 1):
            x, y = px + dx, py + dy
            screen_x = map_offset_x + dx + view_radius
            screen_y = map_offset_y + dy + view_radius
            
            if screen_x >= 35 or screen_y >= 35:
                continue
            
            if 0 <= x < dungeon.width and 0 <= y < dungeon.height:
                tile = dungeon.tiles[y][x]
                if (x, y) == (px, py):
                    console.print(screen_x, screen_y, "@", fg=(255, 255, 0))
                elif any(e.x == x and e.y == y for e in exploration.enemies):
                    console.print(screen_x, screen_y, "E", fg=(255, 0, 0))
                elif hasattr(dungeon, 'stairs_down') and (x, y) == dungeon.stairs_down:
                    console.print(screen_x, screen_y, ">", fg=(0, 255, 255))
                elif tile.walkable:
                    console.print(screen_x, screen_y, ".", fg=(50, 50, 50))
                else:
                    console.print(screen_x, screen_y, "#", fg=(80, 80, 80))
    
    # 파티 상태 (우상단)
    console.print(40, 2, "📦 파티 상태", fg=(200, 200, 255))
    for i, char in enumerate(party):
        hp_pct = int(char.current_hp / char.max_hp * 100) if char.max_hp > 0 else 0
        color = (100, 255, 100) if hp_pct > 50 else ((255, 200, 100) if hp_pct > 25 else (255, 100, 100))
        status = "" if char.is_alive else " [사망]"
        console.print(40, 3 + i, f"{char.name}: HP {hp_pct}%{status}", fg=color)
    
    # 통계 (우측)
    console.print(40, 9, f"🏔️ 층: {stats.get('max_floor_reached', 1)}", fg=(200, 200, 255))
    console.print(40, 10, f"⚔️ 승리: {stats.get('battles_won', 0)}", fg=(100, 255, 100))
    console.print(40, 11, f"💀 패배: {stats.get('battles_lost', 0)}", fg=(255, 100, 100))
    console.print(40, 12, f"👹 처치: {stats.get('enemies_defeated', 0)}", fg=(255, 200, 100))
    
    # AI 해설 (하단)
    console.print(2, 36, "💭 AI 해설", fg=(150, 150, 255))
    for i, text in enumerate(get_ai_commentary()[-5:]):
        console.print(2, 37 + i, text[:50], fg=(180, 180, 180))
    
    # 현재 행동
    action = get_ai_action()
    if action:
        console.print(2, 43, f"▶ {action[:60]}", fg=(255, 255, 255))
    
    context.present(console)


def _run_ai_combat(console, context, ai, party, enemy, inventory, stats) -> str:
    """AI 전투 실행 (간소화 버전)"""
    from src.combat.combat_manager import CombatManager
    from src.multiplayer.llm_player_bot import GameStateConverter
    
    # 적 캐릭터 생성
    from src.character.character import Character
    enemy_char = Character(name=enemy.name, character_class="enemy", level=enemy.level)
    enemy_char.is_boss = enemy.is_boss
    
    # 전투 매니저 생성
    combat = CombatManager(allies=party, enemies=[enemy_char], inventory=inventory)
    
    add_ai_commentary(f"전투 시작: vs {enemy.name}")
    
    max_turns = 50
    turn = 0
    
    while not combat.is_battle_over() and turn < max_turns:
        turn += 1
        
        # 현재 행동자 가져오기
        current = combat.get_current_actor()
        if not current:
            combat.advance_turn()
            continue
        
        # 아군이면 AI 결정
        if current in party:
            try:
                combat_state = GameStateConverter.from_combat_manager(combat, current, inventory)
                bot = ai.create_combat_bot(current)
                action = bot.decide_combat_action(combat_state)
                
                add_ai_commentary(f"{current.name}: {action.action_type.value}")
                
                # 간단한 행동 실행
                if action.action_type.value == "brv_attack":
                    combat.execute_action(current, "brv_attack", target=enemy_char)
                elif action.action_type.value == "hp_attack":
                    combat.execute_action(current, "hp_attack", target=enemy_char)
                else:
                    combat.execute_action(current, "brv_attack", target=enemy_char)
            except Exception as e:
                logger.warning(f"AI 전투 결정 오류: {e}")
                combat.execute_action(current, "brv_attack", target=enemy_char)
        else:
            # 적 행동 (간단히)
            target = next((c for c in party if c.is_alive), None)
            if target:
                combat.execute_action(current, "brv_attack", target=target)
        
        combat.advance_turn()
        
        # 화면 업데이트 (빠르게)
        console.clear()
        console.print(30, 20, f"⚔️ 전투 중... 턴 {turn}", fg=(255, 200, 100))
        console.print(30, 22, f"{enemy.name} HP: {enemy_char.current_hp}/{enemy_char.max_hp}", fg=(255, 100, 100))
        context.present(console)
        time.sleep(0.1)
    
    # 결과 판정
    if enemy_char.current_hp <= 0 or not enemy_char.is_alive:
        return "victory"
    elif all(not c.is_alive for c in party):
        return "defeat"
    else:
        return "draw"
