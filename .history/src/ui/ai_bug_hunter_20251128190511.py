"""
AI 버그 헌터 - AI 관전 모드를 사용한 자동 버그 탐지

ai_spectate_mode.py의 래퍼입니다.
싱글플레이의 AI 관전 모드가 곧 버그 헌터입니다.
"""

import tcod.console
from typing import Optional, Dict, Any

from src.core.logger import get_logger


logger = get_logger("ai_bug_hunter")


@dataclass
class BugReport:
    """버그 리포트"""
    timestamp: str
    error_type: str
    error_message: str
    traceback: str
    game_state: Dict[str, Any]
    action_history: List[str]
    floor: int = 0
    turn: int = 0


@dataclass
class BugHunterStats:
    """버그 헌터 통계"""
    games_played: int = 0
    floors_explored: int = 0
    battles_fought: int = 0
    errors_found: int = 0
    warnings_found: int = 0
    run_time_seconds: float = 0.0
    bugs: List[BugReport] = field(default_factory=list)


class AIBugHunter:
    """AI 버그 헌터"""
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.stats = BugHunterStats()
        self.action_history: List[str] = []
        self.current_game_state: Dict[str, Any] = {}
        self.running = False
        self.start_time = 0.0
        
        # 버그 리포트 저장 경로
        self.report_dir = Path("logs/bug_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # AI 초기화
        self.ai = None
        self.party = None
        self.inventory = None
        self.exploration = None
        self.floor_number = 1
    
    def _init_ai(self):
        """AI 초기화"""
        from src.multiplayer.llm_player_bot import create_auto_play_ai, PlayStyle
        try:
            self.ai = create_auto_play_ai(model="qwen3:0.6b", style=PlayStyle.BALANCED)
            logger.info("AI 버그 헌터: LLM AI 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"AI 초기화 실패: {e}")
            self._record_bug("AIInitError", str(e), traceback.format_exc())
            return False
    
    def _init_party(self):
        """파티 자동 구성"""
        from src.multiplayer.llm_player_bot import get_available_jobs
        from src.character.character import Character
        
        try:
            available_jobs = get_available_jobs()
            party_choices = self.ai.recommend_party(available_jobs, 4)
            
            self.party = []
            for choice in party_choices:
                char = Character(
                    name=choice.character_name,
                    character_class=choice.job_id,
                    level=1
                )
                char.experience = 0
                char.current_hp = char.max_hp
                char.current_mp = char.max_mp
                self.party.append(char)
            
            self._log_action(f"파티 구성: {[c.name for c in self.party]}")
            return True
        except Exception as e:
            logger.error(f"파티 구성 실패: {e}")
            self._record_bug("PartySetupError", str(e), traceback.format_exc())
            return False
    
    def _init_game(self):
        """게임 초기화"""
        from src.equipment.inventory import Inventory
        from src.world.dungeon_generator import DungeonGenerator
        from src.world.exploration import ExplorationSystem
        from src.core.difficulty import DifficultySystem, DifficultyLevel, set_difficulty_system
        from src.core.config import get_config
        
        try:
            # 인벤토리
            self.inventory = Inventory(base_weight=10.0, party=self.party)
            self.inventory.add_gold(200)
            
            # 난이도
            config = get_config()
            difficulty_system = DifficultySystem(config)
            difficulty_system.set_difficulty(DifficultyLevel.NORMAL)
            set_difficulty_system(difficulty_system)
            
            # 게임 통계
            self.game_stats = {
                "enemies_defeated": 0,
                "max_floor_reached": 1,
                "floors_cleared": 0,
                "battles_won": 0,
                "battles_lost": 0
            }
            
            # 던전
            self.floor_number = 1
            generator = DungeonGenerator(self.floor_number)
            dungeon = generator.generate()
            self.exploration = ExplorationSystem(dungeon, self.party, self.floor_number, self.inventory, self.game_stats)
            
            self._log_action(f"게임 초기화 완료: {self.floor_number}층")
            return True
        except Exception as e:
            logger.error(f"게임 초기화 실패: {e}")
            self._record_bug("GameInitError", str(e), traceback.format_exc())
            return False
    
    def _log_action(self, action: str):
        """행동 로그"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {action}"
        self.action_history.append(log_entry)
        logger.info(f"[BugHunter] {action}")
        
        # 최대 100개 유지
        if len(self.action_history) > 100:
            self.action_history.pop(0)
    
    def _update_game_state(self):
        """게임 상태 스냅샷"""
        try:
            self.current_game_state = {
                "floor": self.floor_number,
                "party": [
                    {
                        "name": c.name,
                        "job": c.character_class,
                        "hp": f"{c.current_hp}/{c.max_hp}",
                        "mp": f"{c.current_mp}/{c.max_mp}",
                        "alive": c.is_alive
                    } for c in self.party
                ] if self.party else [],
                "gold": self.inventory.gold if self.inventory else 0,
                "stats": self.game_stats if hasattr(self, 'game_stats') else {},
                "position": (self.exploration.player.x, self.exploration.player.y) if self.exploration else (0, 0)
            }
        except Exception as e:
            self.current_game_state = {"error": str(e)}
    
    def _record_bug(self, error_type: str, message: str, tb: str):
        """버그 기록"""
        self._update_game_state()
        
        bug = BugReport(
            timestamp=datetime.now().isoformat(),
            error_type=error_type,
            error_message=message,
            traceback=tb,
            game_state=self.current_game_state,
            action_history=self.action_history[-20:],  # 최근 20개
            floor=self.floor_number,
            turn=len(self.action_history)
        )
        
        self.stats.bugs.append(bug)
        self.stats.errors_found += 1
        
        # 즉시 파일로 저장
        bug_file = self.report_dir / f"bug_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{error_type}.json"
        with open(bug_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(bug), f, indent=2, ensure_ascii=False)
        
        logger.error(f"🐛 버그 발견! {error_type}: {message}")
        logger.error(f"   저장됨: {bug_file}")
    
    def _ai_exploration_input(self, exploration_sys, party, inv) -> GameAction:
        """AI 탐험 입력"""
        from src.multiplayer.llm_player_bot import ExplorationState
        
        try:
            alive = [c for c in party if c.is_alive]
            if not alive:
                return None
            
            party_hp = sum(c.current_hp / c.max_hp * 100 for c in alive) / len(alive)
            party_mp = sum(c.current_mp / c.max_mp * 100 for c in alive) / len(alive)
            
            nearby_enemies = []
            if hasattr(exploration_sys, 'enemies'):
                nearby_enemies = [
                    e.name for e in exploration_sys.enemies 
                    if abs(e.x - exploration_sys.player.x) <= 5 
                    and abs(e.y - exploration_sys.player.y) <= 5
                ]
            
            state = ExplorationState(
                current_floor=self.floor_number,
                current_position=(exploration_sys.player.x, exploration_sys.player.y),
                visible_tiles=[],
                discovered_rooms=0,
                total_rooms=5,
                nearby_enemies=nearby_enemies,
                nearby_items=[],
                nearby_exits=[],
                party_hp_percent=party_hp,
                party_mp_percent=party_mp,
                has_healing_point=False,
                floor_type="dungeon",
                stairs_down_position=None
            )
            
            action = self.ai.decide_exploration_action(state)
            self._log_action(f"탐험: {action.action_type} - {action.reasoning}")
            
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
            
            import random
            return random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT])
        
        except Exception as e:
            self._record_bug("ExplorationAIError", str(e), traceback.format_exc())
            import random
            return random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT])
    
    def _ai_combat_input(self, ui, combat_manager, current_char, inv) -> GameAction:
        """AI 전투 입력"""
        from src.multiplayer.llm_player_bot import GameStateConverter
        
        try:
            combat_state = GameStateConverter.from_combat_manager(combat_manager, current_char, inv)
            bot = self.ai.create_combat_bot(current_char)
            action = bot.decide_combat_action(combat_state)
            
            action_name = action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)
            self._log_action(f"전투: {current_char.name} -> {action_name}")
            
            return GameAction.CONFIRM
        except Exception as e:
            self._record_bug("CombatAIError", str(e), traceback.format_exc())
            return GameAction.CONFIRM
    
    def run(self, max_games: int = 10, max_floors_per_game: int = 10) -> BugHunterStats:
        """
        버그 헌팅 실행
        
        Args:
            max_games: 최대 게임 횟수
            max_floors_per_game: 게임당 최대 층 수
        """
        self.running = True
        self.start_time = time.time()
        
        self._render_status("AI 버그 헌터 시작...")
        
        # AI 초기화
        if not self._init_ai():
            return self.stats
        
        for game_num in range(max_games):
            if not self.running:
                break
            
            self._render_status(f"게임 {game_num + 1}/{max_games} 시작")
            self.action_history.clear()
            
            # 파티/게임 초기화
            if not self._init_party() or not self._init_game():
                continue
            
            self.stats.games_played += 1
            
            # 게임 루프
            try:
                self._run_single_game(max_floors_per_game)
            except Exception as e:
                self._record_bug("GameLoopError", str(e), traceback.format_exc())
            
            self._render_status(f"게임 {game_num + 1} 완료")
        
        # 정리
        self.stats.run_time_seconds = time.time() - self.start_time
        self._save_final_report()
        
        if self.ai:
            self.ai.shutdown()
        
        self.running = False
        return self.stats
    
    def _run_single_game(self, max_floors: int):
        """단일 게임 실행"""
        from src.ui.world_ui import run_exploration
        from src.ui.combat_ui import run_combat, CombatState
        from src.world.dungeon_generator import DungeonGenerator
        from src.world.exploration import ExplorationSystem
        from src.world.enemy_generator import EnemyGenerator
        
        play_bgm = True
        
        for floor_attempt in range(max_floors):
            if not self.running:
                break
            
            # 파티 전멸 체크
            alive_count = sum(1 for c in self.party if c.is_alive)
            if alive_count == 0:
                self._log_action("파티 전멸!")
                break
            
            self._render_status(f"층 {self.floor_number} 탐험 중...")
            
            try:
                # 탐험
                result, data = run_exploration(
                    self.console, self.context, self.exploration,
                    self.inventory, self.party,
                    play_bgm_on_start=play_bgm,
                    ai_input_provider=self._ai_exploration_input
                )
                
                play_bgm = False
                
                # ESC로 종료
                if result == "quit":
                    self._log_action("사용자 종료 요청")
                    self.running = False
                    break
                
                # 전투
                elif result == "combat":
                    self.stats.battles_fought += 1
                    num_enemies = data.get("num_enemies", 1)
                    
                    try:
                        enemy_gen = EnemyGenerator(self.floor_number)
                        enemies = enemy_gen.generate_enemies(num_enemies)
                        
                        self._log_action(f"전투 시작: vs {[e.name for e in enemies]}")
                        
                        combat_result, is_game_over = run_combat(
                            self.console, self.context, self.party, enemies,
                            self.inventory, dungeon=self.exploration.dungeon,
                            ai_input_provider=self._ai_combat_input
                        )
                        
                        if combat_result == CombatState.VICTORY:
                            self.game_stats["battles_won"] += 1
                            self._log_action("전투 승리!")
                        else:
                            self._log_action(f"전투 결과: {combat_result}")
                            if is_game_over:
                                break
                    except Exception as e:
                        self._record_bug("CombatError", str(e), traceback.format_exc())
                
                # 층 이동
                elif result == "floor_down":
                    self.floor_number += 1
                    self.stats.floors_explored += 1
                    self._log_action(f"{self.floor_number}층 진입")
                    
                    try:
                        generator = DungeonGenerator(self.floor_number)
                        dungeon = generator.generate()
                        self.exploration = ExplorationSystem(dungeon, self.party, self.floor_number, self.inventory, self.game_stats)
                        play_bgm = True
                    except Exception as e:
                        self._record_bug("FloorGenerationError", str(e), traceback.format_exc())
                        break
                
            except Exception as e:
                self._record_bug("ExplorationError", str(e), traceback.format_exc())
    
    def _render_status(self, message: str):
        """상태 화면 렌더링"""
        self.console.clear()
        
        # 제목
        self.console.print(2, 1, "🐛 AI 버그 헌터", fg=(255, 200, 100))
        self.console.print(2, 2, "[ESC] 종료", fg=(150, 150, 150))
        
        # 현재 상태
        self.console.print(2, 4, f"📍 {message}", fg=(200, 200, 255))
        
        # 통계
        self.console.print(2, 7, "📊 통계", fg=(255, 215, 0))
        self.console.print(4, 8, f"게임: {self.stats.games_played}", fg=(200, 200, 200))
        self.console.print(4, 9, f"층 탐험: {self.stats.floors_explored}", fg=(200, 200, 200))
        self.console.print(4, 10, f"전투: {self.stats.battles_fought}", fg=(200, 200, 200))
        self.console.print(4, 11, f"🐛 버그 발견: {self.stats.errors_found}", fg=(255, 100, 100))
        
        # 최근 행동
        self.console.print(2, 14, "📜 최근 행동", fg=(255, 215, 0))
        for i, action in enumerate(self.action_history[-8:]):
            self.console.print(4, 15 + i, action[:60], fg=(150, 150, 150))
        
        # 최근 버그
        if self.stats.bugs:
            self.console.print(40, 7, "🐛 최근 버그", fg=(255, 100, 100))
            for i, bug in enumerate(self.stats.bugs[-3:]):
                self.console.print(42, 8 + i, f"{bug.error_type}: {bug.error_message[:30]}", fg=(255, 150, 150))
        
        self.context.present(self.console)
        
        # ESC 체크
        for event in tcod.event.get():
            if isinstance(event, tcod.event.Quit):
                self.running = False
            elif isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.ESCAPE:
                    self.running = False
    
    def _save_final_report(self):
        """최종 리포트 저장"""
        report_file = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "games_played": self.stats.games_played,
                "floors_explored": self.stats.floors_explored,
                "battles_fought": self.stats.battles_fought,
                "errors_found": self.stats.errors_found,
                "run_time_seconds": self.stats.run_time_seconds
            },
            "bugs_summary": [
                {
                    "type": bug.error_type,
                    "message": bug.error_message,
                    "floor": bug.floor
                } for bug in self.stats.bugs
            ]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"버그 헌터 리포트 저장: {report_file}")
        logger.info(f"총 {self.stats.errors_found}개 버그 발견, {self.stats.games_played}게임, {self.stats.floors_explored}층 탐험")


def run_ai_bug_hunter(console: tcod.console.Console, context: tcod.context.Context) -> Optional[Dict[str, Any]]:
    """
    AI 버그 헌터 실행
    
    Returns:
        결과 딕셔너리
    """
    hunter = AIBugHunter(console, context)
    stats = hunter.run(max_games=5, max_floors_per_game=10)
    
    return {
        "games_played": stats.games_played,
        "floors_explored": stats.floors_explored,
        "bugs_found": stats.errors_found,
        "run_time": stats.run_time_seconds
    }
